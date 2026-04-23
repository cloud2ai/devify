"""
Unit tests for prompt config runtime metadata preservation.
"""

import pytest

from threadline.utils.prompt_config_manager import PromptConfigManager


class TestPromptConfigManager:
    @pytest.fixture
    def prompt_config_dir(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "threadline"
        prompts_dir = config_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        (config_dir / "languages.yaml").write_text(
            """
languages:
  - code: en-US
    name: English
    native_name: English
  - code: zh-CN
    name: Chinese
    native_name: 简体中文
""".strip(),
            encoding="utf-8",
        )
        (config_dir / "scenarios.yaml").write_text(
            """
default_prompt_file: prompts/default.yaml
scenarios:
  chat:
    prompt_file: prompts/chat.yaml
""".strip(),
            encoding="utf-8",
        )
        (prompts_dir / "default.yaml").write_text(
            """
common:
  summary_prompt: "Summarize in {language}. Ignore image analysis marked as irrelevant/noise. Keep diagnostic details."
  image_intent_prompt: "Describe why the image was inserted in {language}. Keep the response fully in {language}. If you use headings or labels, write them in {language}. Mark logos or unrelated images as irrelevant/noise. Preserve error text and surrounding conversation context. Keep the original language of key image text whenever possible. Do not translate quoted image text unless explicitly necessary."
""".strip(),
            encoding="utf-8",
        )
        (prompts_dir / "chat.yaml").write_text(
            """
common:
  email_content_prompt: "Respond in {language}"
""".strip(),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            "threadline.utils.prompt_config_manager.settings.THREADLINE_CONFIG_PATH",
            str(config_dir),
        )
        monkeypatch.setattr(
            "threadline.utils.prompt_config_manager.settings.DEFAULT_LANGUAGE",
            "en-US",
        )
        return config_dir

    def test_get_prompt_config_preserves_language_and_scene(
        self,
        prompt_config_dir,
    ):
        manager = PromptConfigManager()

        config = manager.get_prompt_config("chat", "zh")

        assert config["language"] == "zh-CN"
        assert config["scene"] == "chat"
        assert config["summary_prompt"].startswith("Summarize in ")
        assert "irrelevant/noise" in config["summary_prompt"]
        assert "Keep diagnostic details" in config["summary_prompt"]
        assert config["image_intent_prompt"].startswith(
            "Describe why the image was inserted in "
        )
        assert "Keep the response fully in" in config["image_intent_prompt"]
        assert "irrelevant/noise" in config["image_intent_prompt"]
        assert "Preserve error text" in config["image_intent_prompt"]
        assert "Keep the original language" in config["image_intent_prompt"]
        assert (
            "surrounding conversation context" in config["image_intent_prompt"]
        )
        assert "key image text" in config["image_intent_prompt"]
        assert (
            "Do not translate quoted image text"
            in config["image_intent_prompt"]
        )
        assert "headings or labels" in config["image_intent_prompt"]
        assert config["email_content_prompt"].startswith("Respond in ")
