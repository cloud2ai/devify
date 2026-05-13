"""
Unit tests for the threadline settings initialization command.
"""

from threadline.management.commands.init_threadline_settings import Command


class TestInitThreadlineSettings:
    def test_deep_merge_dicts_merges_nested_configuration(self):
        command = Command()

        base = {
            "enable": True,
            "issue_engine": "jira",
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "update",
            "fields": {
                "summary_config": {"default": "title"},
                "priority_config": {"default": "high"},
            },
            "feishu_bitable": {
                "base_url": "https://open.feishu.cn/open-apis",
                "field_mappings": {
                    "任务简述": "title",
                },
            },
        }
        override = {
            "auto_merge_strategy": "update",
            "retry_issue_strategy": "new",
            "fields": {
                "priority_config": {"default": "medium"},
                "description_config": {"default": "summary_content"},
            },
            "feishu_bitable": {
                "field_mappings": {
                    "备注": "llm_content",
                },
            },
        }

        merged = command._deep_merge_dicts(base, override)

        assert merged["enable"] is True
        assert merged["issue_engine"] == "jira"
        assert merged["auto_merge_strategy"] == "update"
        assert merged["manual_merge_strategy"] == "linked"
        assert merged["retry_issue_strategy"] == "new"
        assert merged["fields"]["summary_config"]["default"] == "title"
        assert merged["fields"]["priority_config"]["default"] == "medium"
        assert merged["fields"]["description_config"]["default"] == "summary_content"
        assert merged["feishu_bitable"]["base_url"] == "https://open.feishu.cn/open-apis"
        assert merged["feishu_bitable"]["field_mappings"]["任务简述"] == "title"
        assert merged["feishu_bitable"]["field_mappings"]["备注"] == "llm_content"
