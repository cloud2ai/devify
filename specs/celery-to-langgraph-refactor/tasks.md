# Implementation Plan - Celery to LangGraph Refactoring

本实施计划将 Email Processing 工作流从 Celery task chain 重构为 LangGraph 架构。每个任务都是可执行的编码步骤,按照增量方式构建。

## Task List

- [ ] 1. Review existing base infrastructure
  - Review `threadline/agents/checkpoint_manager.py`
  - Review `threadline/agents/nodes/base_node.py`
  - Verify checkpoint configuration matches requirements (24h TTL, Redis)
  - Verify base node class has all required lifecycle methods
  - Make adjustments if needed for Email Processing requirements
  - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.2, 7.3_

- [ ] 2. Define EmailState structure
  - Create `threadline/agents/email_state.py` (reference `speechtotext_state.py`)
  - Define `NodeError` TypedDict
  - Define `EmailState` TypedDict with core, result, and fixed fields
  - Map fields from `EmailMessage` model to `EmailState`
  - Include attachment information as list of dicts
  - _Requirements: 2.1, 2.2, 2.5_

- [ ] 3. Implement State helper functions
  - In `email_state.py`, implement `create_email_state()` function
  - Implement `add_node_error()` function
  - Implement `has_node_errors()` function
  - Implement `get_node_errors_by_name()` function
  - Implement `get_all_node_names_with_errors()` function
  - Implement `clear_node_errors_by_name()` function
  - Write unit tests for all helper functions
  - _Requirements: 2.3, 2.4, 6.1, 6.4_

- [ ] 4. Implement WorkflowPrepareNode for Email Processing
  - Create `threadline/agents/nodes/email_workflow_prepare.py`
  - Extend `BaseLangGraphNode` class
  - Implement `before_processing()` to load EmailMessage from database
  - Implement `execute_processing()` to map model fields to State
  - Update database status to PROCESSING (skip in force mode)
  - Implement `after_processing()` to validate critical fields
  - Handle EmailMessage.DoesNotExist exception
  - Write unit tests with mocked database
  - _Requirements: 3.3_

- [ ] 5. Implement WorkflowFinalizeNode for Email Processing
  - Create `threadline/agents/nodes/email_workflow_finalize.py`
  - Extend `BaseLangGraphNode` class
  - Override `can_enter_node()` to always return True
  - Implement `before_processing()` to load EmailMessage
  - Implement `execute_processing()` to check node_errors
  - Implement `_sync_data_to_database()` method with atomic transaction
  - Sync all result fields: summary, llm_content, attachments OCR
  - Create EmailIssue if issue_key exists
  - Update status to SUCCESS/FAILED (skip in force mode)
  - Write unit tests for sync logic
  - _Requirements: 3.4, 6.2, 6.3_

- [ ] 6. Implement OCRNode for image processing
  - Create `threadline/agents/nodes/ocr_node.py`
  - Extend `BaseLangGraphNode` class
  - Migrate logic from `threadline/tasks/ocr.py`
  - Implement `can_enter_node()` to check for image attachments
  - Implement `execute_processing()` to process images with OCR
  - Read attachments from State, update with ocr_content
  - Only operate on State, no database access
  - Write unit tests with mocked OCR utility
  - _Requirements: 3.5_

- [ ] 7. Implement LLMAttachmentNode for OCR post-processing
  - Create `threadline/agents/nodes/llm_attachment_node.py`
  - Extend `BaseLangGraphNode` class
  - Migrate logic from `threadline/tasks/llm_attachment.py`
  - Implement `can_enter_node()` to check for OCR content
  - Implement `execute_processing()` to process OCR results with LLM
  - Update attachments with llm_ocr_content in State
  - Write unit tests with mocked LLM utility
  - _Requirements: 3.5_

- [ ] 8. Implement LLMEmailNode for email content processing
  - Create `threadline/agents/nodes/llm_email_node.py`
  - Extend `BaseLangGraphNode` class
  - Migrate logic from `threadline/tasks/llm_email.py`
  - Implement `can_enter_node()` to check for email content
  - Implement `execute_processing()` to process email with LLM
  - Write llm_processed_content to State
  - Write unit tests with mocked LLM utility
  - _Requirements: 3.5_

- [ ] 9. Implement SummaryNode for email summarization
  - Create `threadline/agents/nodes/email_summary_node.py`
  - Extend `BaseLangGraphNode` class
  - Migrate logic from `threadline/tasks/llm_summary.py`
  - Implement `can_enter_node()` to check for LLM results
  - Implement `execute_processing()` to generate summary
  - Write summary_title, summary_content, summary_priority to State
  - Write unit tests with mocked LLM utility
  - _Requirements: 3.5_

- [ ] 10. Implement IssueNode for JIRA issue creation
  - Create `threadline/agents/nodes/issue_node.py`
  - Extend `BaseLangGraphNode` class
  - Migrate logic from `threadline/tasks/issue.py`
  - Implement `can_enter_node()` to check for summary
  - Implement `execute_processing()` to create JIRA issue
  - Write issue_key and issue_url to State
  - Write unit tests with mocked JIRA API
  - _Requirements: 3.5_

- [ ] 11. Create email processing workflow graph
  - Update `threadline/agents/workflow.py` for Email Processing
  - Import all Email node classes and EmailState
  - Implement `create_email_processing_graph()` function
  - Create StateGraph with EmailState
  - Add all 7 nodes to graph
  - Define edges with parallel execution pattern
  - Configure parallel branches: OCR path and Email path
  - Configure convergence at summary_node
  - Compile graph with Redis checkpointer
  - Use `@lru_cache` decorator for graph caching
  - _Requirements: 4.1, 4.3_

- [ ] 12. Implement workflow execution function
  - In `workflow.py`, implement `execute_email_processing_workflow()`
  - Validate EmailMessage exists
  - Create initial EmailState using `create_email_state()`
  - Configure checkpoint with thread_id and checkpoint_ns
  - Invoke graph with initial state and config
  - Check final state for errors
  - Return result dict with success, has_errors, error_nodes, state
  - _Requirements: 4.2, 4.4_

- [ ] 13. Create Celery task compatibility wrapper
  - Update `threadline/tasks/chain_orchestrator.py`
  - Keep existing `process_email_chain()` task signature
  - Import `execute_email_processing_workflow`
  - Delegate task execution to workflow
  - Return email_id for compatibility
  - Add deprecation warning comment
  - Verify task registration in Celery
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 14. Write integration tests for workflow execution
  - Create test file `tests/agents/test_email_workflow_integration.py`
  - Create fixtures for mock EmailMessage
  - Test complete workflow success path
  - Test workflow with node failures
  - Test force mode behavior
  - Test checkpoint save and recovery
  - Test parallel node execution
  - Verify final database state
  - _Requirements: 9.4_

- [ ] 15. Write integration tests for Celery wrapper
  - Create test file `tests/test_celery_wrapper.py`
  - Test `process_email_chain()` task execution
  - Verify compatibility with existing API endpoints
  - Verify compatibility with admin actions
  - Verify return value format
  - _Requirements: 8.5, 9.4_

- [ ] 16. Simplify EmailMessage status machine
  - Update `threadline/state_machine.py`
  - Define simplified `EmailStatus` enum with 5 core states
  - Define `EMAIL_STATE_MACHINE` transitions
  - Remove intermediate processing states
  - Document state transition rules
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 17. Create database migration for status field
  - Generate Django migration for EmailMessage.status field
  - Add data migration to convert old statuses to new statuses
  - Map OCR_SUCCESS → PROCESSING
  - Map LLM_*_SUCCESS → PROCESSING
  - Map ISSUE_SUCCESS → PROCESSING
  - Map *_PROCESSING → PROCESSING
  - Test migration on development database
  - _Requirements: 5.1, 5.2_

- [ ] 18. Simplify reset stuck emails scheduler
  - Update `schedule_reset_stuck_processing_emails()` in `tasks/scheduler.py`
  - Remove `STUCK_STATUS_RESET_MAP` dictionary
  - Change query to only check PROCESSING status
  - Simplify reset logic to PROCESSING → FAILED
  - Add optional force mode retry
  - Update logging messages
  - Write unit tests for scheduler
  - _Requirements: 5.4, 8.5_

- [ ] 19. Write end-to-end tests with real database
  - Create test file `tests/agents/test_email_e2e.py`
  - Use `@pytest.mark.django_db` decorator
  - Create test EmailMessage with attachments
  - Execute complete workflow
  - Verify database state after workflow
  - Test recovery after failure
  - Test force mode reprocessing
  - _Requirements: 9.4_

- [ ] 20. Write performance tests for workflow
  - Create test file `tests/agents/test_email_performance.py`
  - Test workflow execution time
  - Test checkpoint save/load overhead
  - Compare with original Celery implementation
  - Verify parallel execution performance improvement
  - Assert execution time within acceptable limits
  - _Requirements: 9.4_

- [ ] 21. Update workflow documentation
  - Add module docstrings to all new files
  - Document node responsibilities and dependencies
  - Document State fields and their purposes
  - Create workflow diagram in docstring using Mermaid
  - Document checkpoint configuration
  - Follow project coding standards (English comments, no inline comments)
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 22. Add workflow logging infrastructure
  - Add structured logging to all nodes
  - Log node entry, exit, and errors
  - Log workflow start and completion
  - Use consistent log format: `[node_name] message`
  - Configure log levels appropriately
  - _Requirements: 8.5_

- [ ] 23. Configure feature flag for gradual rollout
  - Add `USE_LANGGRAPH_EMAIL_WORKFLOW` setting to Django settings
  - Update `process_email_chain()` to check feature flag
  - Route to LangGraph or Celery based on flag
  - Default to False for backward compatibility
  - Document feature flag usage
  - _Requirements: 8.3_

- [ ] 24. Run linter and fix code style issues
  - Run `flake8` or `ruff` on all new files in `agents/`
  - Fix import order (stdlib, third-party, local)
  - Fix line length violations (max 73 chars)
  - Remove unused imports
  - Fix docstring formatting
  - Verify PEP 8 compliance
  - _Requirements: 10.5, 10.6_

- [ ] 25. Run all unit tests and verify coverage
  - Execute `pytest tests/agents/` for agent tests
  - Verify test coverage > 90% for new code
  - Fix any failing tests
  - Add missing test cases
  - _Requirements: 9.4_

- [ ] 26. Run all integration tests
  - Execute integration test suite
  - Verify workflow execution with mocked services
  - Verify checkpoint recovery
  - Verify error handling
  - _Requirements: 9.4_

- [ ] 27. Run end-to-end tests
  - Execute E2E test suite with real database
  - Verify complete workflow with real EmailMessage
  - Verify database state changes
  - Verify attachment processing
  - Verify issue creation
  - _Requirements: 9.4_

- [ ] 28. Verify backward compatibility with existing system
  - Test API endpoints calling `process_email_chain()`
  - Test admin actions triggering email processing
  - Test schedulers triggering email processing
  - Verify return value format matches original
  - Verify no changes needed in calling code
  - _Requirements: 8.1, 8.5_
