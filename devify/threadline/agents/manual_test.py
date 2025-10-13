"""
Manual test script for LangGraph Email Processing Workflow

This script provides manual testing utilities to verify the workflow
functionality before running automated tests.

Usage:
    python manage.py shell
    >>> from threadline.agents.manual_test import *
    >>> test_workflow_graph_creation()
    >>> test_email_state_creation()
    >>> test_node_instantiation()
"""

import logging
from django.contrib.auth.models import User
from threadline.models import EmailMessage
from threadline.agents.email_state import create_email_state
from threadline.agents.workflow import create_email_processing_graph
from threadline.agents.nodes.workflow_prepare import WorkflowPrepareNode
from threadline.agents.nodes.ocr_node import OCRNode
from threadline.agents.nodes.llm_attachment_node import LLMAttachmentNode
from threadline.agents.nodes.llm_email_node import LLMEmailNode
from threadline.agents.nodes.summary_node import SummaryNode
from threadline.agents.nodes.issue_node import IssueNode
from threadline.agents.nodes.workflow_finalize import WorkflowFinalizeNode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_workflow_graph_creation():
    """Test 1: Verify workflow graph can be created and compiled."""
    print("\n" + "="*70)
    print("TEST 1: Workflow Graph Creation")
    print("="*70)

    try:
        graph = create_email_processing_graph()
        print("✅ Workflow graph created successfully")
        print(f"   Graph type: {type(graph)}")
        print(f"   Graph has nodes: {hasattr(graph, 'nodes')}")
        return True
    except Exception as e:
        print(f"❌ Failed to create workflow graph: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_state_creation():
    """Test 2: Verify EmailState can be created with proper structure."""
    print("\n" + "="*70)
    print("TEST 2: EmailState Creation")
    print("="*70)

    try:
        state = create_email_state(
            email_id="test-email-123",
            user_id="test-user-456",
            force=False
        )

        print("✅ EmailState created successfully")
        print(f"   Email ID: {state.get('id')}")
        print(f"   User ID: {state.get('user_id')}")
        print(f"   Force mode: {state.get('force')}")
        print(f"   Node errors: {state.get('node_errors')}")
        print(f"   Issue fields present: issue_id={state.get('issue_id')}, "
              f"issue_url={state.get('issue_url')}, "
              f"issue_metadata={state.get('issue_metadata')}")
        print(f"   Issue prepare data: {state.get('issue_prepare_data')}")
        return True
    except Exception as e:
        print(f"❌ Failed to create EmailState: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_instantiation():
    """Test 3: Verify all nodes can be instantiated."""
    print("\n" + "="*70)
    print("TEST 3: Node Instantiation")
    print("="*70)

    nodes = {
        'WorkflowPrepareNode': WorkflowPrepareNode,
        'OCRNode': OCRNode,
        'LLMAttachmentNode': LLMAttachmentNode,
        'LLMEmailNode': LLMEmailNode,
        'SummaryNode': SummaryNode,
        'IssueNode': IssueNode,
        'WorkflowFinalizeNode': WorkflowFinalizeNode,
    }

    results = {}
    for node_name, node_class in nodes.items():
        try:
            node = node_class()
            print(f"✅ {node_name}: instantiated successfully")
            print(f"   - node_name: {node.node_name}")
            print(f"   - has can_enter_node: {hasattr(node, 'can_enter_node')}")
            print(f"   - has execute_processing: {hasattr(node, 'execute_processing')}")
            results[node_name] = True
        except Exception as e:
            print(f"❌ {node_name}: failed - {e}")
            results[node_name] = False

    success_count = sum(results.values())
    total_count = len(results)
    print(f"\n   Summary: {success_count}/{total_count} nodes instantiated successfully")
    return success_count == total_count


def test_workflow_with_real_email(email_id=None):
    """
    Test 4: Execute workflow with a real email (optional).

    Args:
        email_id: Optional email ID to test with. If None, will find the
                 first FETCHED email.
    """
    print("\n" + "="*70)
    print("TEST 4: Workflow Execution with Real Email")
    print("="*70)

    if email_id is None:
        try:
            from threadline.state_machine import EmailStatus
            email = EmailMessage.objects.filter(
                status=EmailStatus.FETCHED.value
            ).first()

            if not email:
                print("⚠️  No FETCHED emails found for testing")
                print("   You can manually specify an email_id:")
                print("   >>> test_workflow_with_real_email('your-email-id')")
                return False

            email_id = str(email.id)
            print(f"   Found email: {email_id}")
            print(f"   Subject: {email.subject}")
        except Exception as e:
            print(f"❌ Error finding test email: {e}")
            return False

    try:
        from threadline.agents.workflow import (
            execute_email_processing_workflow
        )
        from threadline.models import EmailMessage

        print(f"\n   Executing workflow for email: {email_id}")
        print("   This may take a while...")

        email = EmailMessage.objects.get(id=email_id)
        result = execute_email_processing_workflow(email, force=False)

        if result['success']:
            print("\n✅ Workflow executed successfully!")
            print(f"   Result keys: {list(result.keys())}")
            print(f"   Has node errors: {result['result'].get('node_errors', {}) if result.get('result') else 'N/A'}")
        else:
            print(f"\n❌ Workflow execution failed")
            print(f"   Error: {result.get('error')}")

        return result['success']
    except Exception as e:
        print(f"\n❌ Workflow execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_celery_task_import():
    """Test 5: Verify Celery tasks can be imported."""
    print("\n" + "="*70)
    print("TEST 5: Celery Task Import")
    print("="*70)

    try:
        from threadline.tasks import process_email_workflow
        print("✅ process_email_workflow imported successfully")
        print(f"   Task name: {process_email_workflow.name}")

        from threadline.tasks import retry_failed_email_workflow
        print("✅ retry_failed_email_workflow imported successfully")
        print(f"   Task name: {retry_failed_email_workflow.name}")

        return True
    except Exception as e:
        print(f"❌ Failed to import Celery tasks: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests(include_workflow_execution=False):
    """
    Run all manual tests.

    Args:
        include_workflow_execution: If True, includes actual workflow execution
                                   with a real email (slower)
    """
    print("\n" + "="*70)
    print("LANGGRAPH EMAIL WORKFLOW - MANUAL TEST SUITE")
    print("="*70)

    results = {}

    # Test 1: Graph creation
    results['graph_creation'] = test_workflow_graph_creation()

    # Test 2: State creation
    results['state_creation'] = test_email_state_creation()

    # Test 3: Node instantiation
    results['node_instantiation'] = test_node_instantiation()

    # Test 4: Workflow execution (optional)
    if include_workflow_execution:
        results['workflow_execution'] = test_workflow_with_real_email()

    # Test 5: Celery task import
    results['celery_import'] = test_celery_task_import()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed_count = sum(results.values())
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")

    return passed_count == total_count


# Quick test commands
def quick_test():
    """Run quick tests (without workflow execution)."""
    return run_all_tests(include_workflow_execution=False)


def full_test():
    """Run all tests including workflow execution."""
    return run_all_tests(include_workflow_execution=True)


if __name__ == "__main__":
    print("This script should be run from Django shell:")
    print("  python manage.py shell")
    print("  >>> from threadline.agents.manual_test import *")
    print("  >>> quick_test()  # Fast tests only")
    print("  >>> full_test()   # Include workflow execution")
