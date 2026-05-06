from types import SimpleNamespace

from threadline.agents.nodes.workflow_prepare import WorkflowPrepareNode


def _build_email(**kwargs):
    defaults = {
        "id": 1,
        "user_id": 2,
        "message_id": "<message@example.com>",
        "subject": "Subject",
        "sender": "sender@example.com",
        "recipients": "recipient@example.com",
        "received_at": None,
        "html_content": "",
        "text_content": "",
        "summary_title": None,
        "summary_content": None,
        "summary_data": None,
        "llm_content": None,
        "metadata": None,
        "created_at": None,
        "updated_at": None,
        "merged_into_id": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_email_state_preserves_business_metadata_for_normal_email():
    node = WorkflowPrepareNode()
    node.email = _build_email(metadata={"keywords": ["alpha"]})

    state = node._build_email_state(
        state={},
        prompt_config={},
        issue_config={},
        max_attachments=None,
        attachments_data=[],
        issue_id=None,
        issue_url=None,
        issue_metadata=None,
        summary_data=None,
        todos_data=[],
    )

    assert state["metadata"] == {"keywords": ["alpha"]}


def test_strip_runtime_metadata_removes_processing_progress():
    node = WorkflowPrepareNode()

    cleaned = node._strip_runtime_metadata(
        {
            "processing_progress": {"percent": 20},
            "keywords": ["alpha"],
        }
    )

    assert cleaned == {"keywords": ["alpha"]}
