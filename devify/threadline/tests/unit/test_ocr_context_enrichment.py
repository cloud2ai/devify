"""Unit tests for OCR context enrichment in email workflow nodes."""

from threadline.agents.nodes.llm_attachment_node import LLMAttachmentNode


def test_llm_attachment_node_builds_ocr_context_from_state():
    node = LLMAttachmentNode()

    context = node._build_ocr_context(
        {
            "subject": "Bug report for OCR",
            "sender": "alice@example.com",
            "recipients": "support@example.com",
            "received_at": "2025-04-15T09:30:00+00:00",
            "text_content": (
                "Hi team,\n"
                "Please check the screenshot below.\n"
                "[IMAGE: dashboard.png]\n"
                "\n"
                "Thanks,\n"
                "Alice\n"
                "Sent from my iPhone\n"
            ),
        }
    )

    assert context is not None
    assert "Subject: Bug report for OCR" in context
    assert "Sender: alice@example.com" in context
    assert "Recipients: support@example.com" in context
    assert "Please check the screenshot below." in context
    assert "Conversation body:" in context


def test_llm_attachment_node_ignores_llm_summary_when_raw_text_exists():
    node = LLMAttachmentNode()

    context = node._build_ocr_context(
        {
            "subject": "Bug report for OCR",
            "sender": "alice@example.com",
            "recipients": "support@example.com",
            "received_at": "2025-04-15T09:30:00+00:00",
            "text_content": (
                "Hi team,\n"
                "Please check the screenshot below.\n"
                "[IMAGE: dashboard.png]\n"
            ),
            "llm_content": (
                "Organized conversation summary:\n"
                "- The user reported a dashboard issue.\n"
                "- The screenshot should be checked."
            ),
        }
    )

    assert context is not None
    assert "Organized conversation summary:" not in context
    assert "Please check the screenshot below." in context


def test_llm_attachment_node_includes_ocr_context(monkeypatch):
    node = LLMAttachmentNode()
    state = {
        "attachments": [
            {
                "id": "att-1",
                "filename": "dashboard.png",
                "safe_filename": "dashboard.png",
                "is_image": True,
                "ocr_content": "The screenshot shows a login form and an error banner.",
                "ocr_cleaned_content": None,
                "llm_content": None,
            }
        ],
        "prompt_config": {
            "ocr_cleanup_prompt": "Clean the OCR text before interpretation.",
            "ocr_prompt": "Use the conversation background to interpret the image."
        },
        "subject": "Bug report for OCR",
        "sender": "alice@example.com",
        "recipients": "support@example.com",
        "received_at": "2025-04-15T09:30:00+00:00",
        "text_content": "The user says the dashboard login is failing.",
        "force": False,
    }

    captured = {}

    def fake_call_and_track(
        prompt,
        content=None,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
    ):
        captured.setdefault("calls", []).append(
            {
                "prompt": prompt,
                "content": content,
                "json_mode": json_mode,
                "node_name": node_name,
            }
        )

        if len(captured["calls"]) == 1:
            return (
                "Cleaned OCR: login form and error banner.",
                {
                    "model": "test-model",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            )

        return (
            "The image likely shows a login issue relevant to the dashboard.",
            {
                "model": "test-model",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

    monkeypatch.setattr(
        "threadline.agents.nodes.llm_attachment_node.LLMTracker.call_and_track",
        fake_call_and_track,
    )

    updated_state = node.execute_processing(state)

    assert len(captured["calls"]) == 2
    assert (
        captured["calls"][0]["prompt"]
        == state["prompt_config"]["ocr_cleanup_prompt"]
    )
    assert captured["calls"][0]["content"] == (
        "The screenshot shows a login form and an error banner."
    )
    assert captured["calls"][1]["prompt"] == state["prompt_config"]["ocr_prompt"]
    assert "Conversation context:" in captured["calls"][1]["content"]
    assert (
        "The user says the dashboard login is failing."
        in captured["calls"][1]["content"]
    )
    assert "Image reference:" in captured["calls"][1]["content"]
    assert (
        "Original filename: dashboard.png"
        in captured["calls"][1]["content"]
    )
    assert "Cleaned OCR content:" in captured["calls"][1]["content"]
    assert (
        "Cleaned OCR: login form and error banner."
        in captured["calls"][1]["content"]
    )
    assert updated_state["attachments"][0]["ocr_cleaned_content"] == (
        "Cleaned OCR: login form and error banner."
    )
    assert updated_state["attachments"][0]["llm_content"] == (
        "The image likely shows a login issue relevant to the dashboard."
    )


def test_llm_attachment_node_falls_back_to_ocr_only(monkeypatch):
    node = LLMAttachmentNode()
    state = {
        "attachments": [
            {
                "id": "att-2",
                "filename": "diagram.png",
                "safe_filename": "diagram.png",
                "is_image": True,
                "ocr_content": "Network diagram with service names.",
                "ocr_cleaned_content": None,
                "llm_content": None,
            }
        ],
        "prompt_config": {
            "ocr_cleanup_prompt": "Clean the OCR text before interpretation.",
            "ocr_prompt": "Use the conversation background to interpret the image."
        },
        "force": False,
    }

    captured = {}

    def fake_call_and_track(
        prompt,
        content=None,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
    ):
        captured.setdefault("calls", []).append(
            {
                "prompt": prompt,
                "content": content,
                "json_mode": json_mode,
                "node_name": node_name,
            }
        )

        if len(captured["calls"]) == 1:
            return (
                "Cleaned OCR: network diagram with service names.",
                {
                    "model": "test-model",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            )

        return (
            "The image appears to be a network diagram.",
            {
                "model": "test-model",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

    monkeypatch.setattr(
        "threadline.agents.nodes.llm_attachment_node.LLMTracker.call_and_track",
        fake_call_and_track,
    )

    updated_state = node.execute_processing(state)

    assert len(captured["calls"]) == 2
    assert (
        captured["calls"][0]["prompt"]
        == state["prompt_config"]["ocr_cleanup_prompt"]
    )
    assert captured["calls"][0]["content"] == (
        "Network diagram with service names."
    )
    assert "Conversation context:" not in captured["calls"][1]["content"]
    assert "Image reference:" in captured["calls"][1]["content"]
    assert (
        "Original filename: diagram.png"
        in captured["calls"][1]["content"]
    )
    assert "Cleaned OCR content:" in captured["calls"][1]["content"]
    assert (
        "Cleaned OCR: network diagram with service names."
        in captured["calls"][1]["content"]
    )
    assert updated_state["attachments"][0]["ocr_cleaned_content"] == (
        "Cleaned OCR: network diagram with service names."
    )
    assert updated_state["attachments"][0]["llm_content"] == (
        "The image appears to be a network diagram."
    )


def test_llm_attachment_node_works_without_cleanup_prompt(monkeypatch):
    node = LLMAttachmentNode()
    state = {
        "attachments": [
            {
                "id": "att-3",
                "filename": "note.png",
                "safe_filename": "note.png",
                "is_image": True,
                "ocr_content": "Need to reschedule the meeting to Friday.",
                "ocr_cleaned_content": None,
                "llm_content": None,
            }
        ],
        "prompt_config": {
            "ocr_prompt": "Use the conversation background to interpret the image."
        },
        "subject": "Meeting reschedule",
        "sender": "alice@example.com",
        "recipients": "support@example.com",
        "received_at": "2025-04-15T09:30:00+00:00",
        "text_content": "The team is discussing availability.",
        "force": False,
    }

    captured = {}

    def fake_call_and_track(
        prompt,
        content=None,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
    ):
        captured.setdefault("calls", []).append(
            {
                "prompt": prompt,
                "content": content,
                "json_mode": json_mode,
                "node_name": node_name,
            }
        )
        return (
            "The OCR text suggests a meeting reschedule request.",
            {
                "model": "test-model",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

    monkeypatch.setattr(
        "threadline.agents.nodes.llm_attachment_node.LLMTracker.call_and_track",
        fake_call_and_track,
    )

    updated_state = node.execute_processing(state)

    assert len(captured["calls"]) == 1
    assert captured["calls"][0]["prompt"] == state["prompt_config"]["ocr_prompt"]
    assert "Conversation context:" in captured["calls"][0]["content"]
    assert "Image reference:" in captured["calls"][0]["content"]
    assert "Original filename: note.png" in captured["calls"][0]["content"]
    assert "Cleaned OCR content:" in captured["calls"][0]["content"]
    assert (
        "Need to reschedule the meeting to Friday."
        in captured["calls"][0]["content"]
    )
    assert updated_state["attachments"][0]["ocr_cleaned_content"] == (
        "Need to reschedule the meeting to Friday."
    )
    assert updated_state["attachments"][0]["llm_content"] == (
        "The OCR text suggests a meeting reschedule request."
    )


def test_llm_attachment_node_reuses_cached_cleaned_content(monkeypatch):
    node = LLMAttachmentNode()
    state = {
        "attachments": [
            {
                "id": "att-4",
                "filename": "report.png",
                "safe_filename": "report.png",
                "is_image": True,
                "ocr_content": "Raw OCR content that should not be re-cleaned.",
                "ocr_cleaned_content": "Cached OCR cleaned content.",
                "llm_content": None,
            }
        ],
        "prompt_config": {
            "ocr_cleanup_prompt": "Clean the OCR text before interpretation.",
            "ocr_prompt": "Explain why the image was sent in the conversation."
        },
        "subject": "Weekly report",
        "sender": "alice@example.com",
        "recipients": "support@example.com",
        "received_at": "2025-04-15T09:30:00+00:00",
        "text_content": "The sender is sharing evidence for the KPI discussion.",
        "force": False,
    }

    captured = {}

    def fake_call_and_track(
        prompt,
        content=None,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
    ):
        captured.setdefault("calls", []).append(
            {
                "prompt": prompt,
                "content": content,
            }
        )
        return (
            "The image was inserted to support the KPI discussion.",
            {
                "model": "test-model",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

    monkeypatch.setattr(
        "threadline.agents.nodes.llm_attachment_node.LLMTracker.call_and_track",
        fake_call_and_track,
    )

    updated_state = node.execute_processing(state)

    assert len(captured["calls"]) == 1
    assert captured["calls"][0]["prompt"] == state["prompt_config"]["ocr_prompt"]
    assert "Cached OCR cleaned content." in captured["calls"][0]["content"]
    assert updated_state["attachments"][0]["ocr_cleaned_content"] == (
        "Cached OCR cleaned content."
    )
    assert updated_state["attachments"][0]["llm_content"] == (
        "The image was inserted to support the KPI discussion."
    )
