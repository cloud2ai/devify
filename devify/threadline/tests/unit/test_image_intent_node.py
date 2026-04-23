"""Unit tests for multimodal image intent processing."""

from threadline.agents.nodes.image_intent_node import ImageIntentNode


def test_image_intent_node_builds_multimodal_messages(tmp_path, monkeypatch):
    node = ImageIntentNode()
    image_path = tmp_path / "screenshot.png"
    image_path.write_bytes(b"fake-png-bytes")

    state = {
        "attachments": [
            {
                "id": "att-1",
                "filename": "screenshot.png",
                "safe_filename": "screenshot.png",
                "is_image": True,
                "file_size": 10,
                "file_path": str(image_path),
                "llm_content": None,
            }
        ],
        "prompt_config": {
            "image_intent_prompt": "Explain why the user inserted the image.",
        },
        "subject": "Bug report",
        "sender": "alice@example.com",
        "recipients": "support@example.com",
        "received_at": "2025-04-15T09:30:00+00:00",
        "text_content": "The screenshot shows the login error.",
        "force": False,
        "image_llm_config_uuid": "11111111-1111-1111-1111-111111111111",
    }

    captured = {}

    def fake_call_messages_and_track(
        messages,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
        model_uuid=None,
    ):
        captured["messages"] = messages
        captured["node_name"] = node_name
        captured["model_uuid"] = model_uuid
        return (
            "The image likely documents a login error for support review.",
            {
                "model": "test-model",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

    monkeypatch.setattr(
        "threadline.agents.nodes.image_intent_node.LLMTracker.call_messages_and_track",
        fake_call_messages_and_track,
    )

    updated_state = node.execute_processing(state)

    assert captured["node_name"] == "image_intent_node"
    assert captured["model_uuid"] == state["image_llm_config_uuid"]
    assert len(captured["messages"]) == 2
    assert captured["messages"][0]["role"] == "system"
    assert (
        captured["messages"][0]["content"]
        == state["prompt_config"]["image_intent_prompt"]
    )
    user_blocks = captured["messages"][1]["content"]
    assert any(
        block.get("type") == "text"
        and "Conversation context:" in block.get("text", "")
        for block in user_blocks
    )
    assert any(
        block.get("type") == "text"
        and "Original filename: screenshot.png" in block.get("text", "")
        for block in user_blocks
    )
    assert any(block.get("type") == "image_url" for block in user_blocks)
    image_block = next(
        block for block in user_blocks if block.get("type") == "image_url"
    )
    assert image_block["image_url"]["url"].startswith("data:image/png;base64,")
    assert updated_state["attachments"][0]["llm_content"] == (
        "The image likely documents a login error for support review."
    )


def test_image_intent_node_falls_back_to_ocr_prompt(tmp_path, monkeypatch):
    node = ImageIntentNode()
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(b"fake-png-bytes")

    state = {
        "attachments": [
            {
                "id": "att-2",
                "filename": "diagram.png",
                "safe_filename": "diagram.png",
                "is_image": True,
                "file_size": 10,
                "file_path": str(image_path),
                "llm_content": None,
            }
        ],
        "prompt_config": {
            "ocr_prompt": "Infer the purpose of the image.",
        },
        "force": False,
        "image_llm_config_uuid": "22222222-2222-2222-2222-222222222222",
    }

    captured = {}

    def fake_call_messages_and_track(
        messages,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
        model_uuid=None,
    ):
        captured["messages"] = messages
        return (
            "The image likely supports a discussion about system design.",
            {
                "model": "test-model",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

    monkeypatch.setattr(
        "threadline.agents.nodes.image_intent_node.LLMTracker.call_messages_and_track",
        fake_call_messages_and_track,
    )

    updated_state = node.execute_processing(state)

    assert (
        captured["messages"][0]["content"]
        == state["prompt_config"]["ocr_prompt"]
    )
    assert updated_state["attachments"][0]["llm_content"] == (
        "The image likely supports a discussion about system design."
    )


def test_image_intent_node_requires_image_llm_config():
    node = ImageIntentNode()
    state = {
        "attachments": [
            {
                "id": "att-3",
                "filename": "diagram.png",
                "safe_filename": "diagram.png",
                "is_image": True,
                "file_size": 10,
                "file_path": "/tmp/diagram.png",
                "llm_content": None,
            }
        ],
        "prompt_config": {
            "image_intent_prompt": "Explain the image.",
        },
        "force": False,
    }

    updated_state = node.execute_processing(state)

    assert "node_errors" in updated_state
    assert "image_intent_node" in updated_state["node_errors"]
