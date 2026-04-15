"""
Unit tests for Feishu Bitable issue handling.
"""

import json

import pytest
from unittest.mock import Mock, patch

from threadline.utils.issues.issue_factory import normalize_issue_engine
from threadline.utils.issues import get_issue_handler
from threadline.utils.issues.feishu_bitable_handler import (
    FeishuBitableIssueHandler,
)


class TestFeishuBitableIssueHandler:
    @pytest.fixture
    def feishu_config(self):
        return {
            "enable": True,
            "issue_engine": "feishu_bitable",
            "feishu_bitable": {
                "base_url": "https://open.feishu.cn/open-apis",
                "tenant_access_token": "tenant-token",
                "app_token": "bascn123",
                "table_id": "tbl123",
                "attachment_upload_parent_folder_token": "folder-token-123",
                "field_mappings": {
                    "标题": "title",
                    "描述": "description",
                    "优先级": "priority",
                    "邮件主题": "subject",
                    "元数据": "metadata",
                },
            },
        }

    @pytest.fixture
    def handler(self, feishu_config, monkeypatch):
        handler = FeishuBitableIssueHandler(feishu_config)
        monkeypatch.setattr(handler, "_sdk_available", lambda: False)
        return handler

    def test_factory_returns_feishu_handler(self, feishu_config):
        handler = get_issue_handler(feishu_config)
        assert isinstance(handler, FeishuBitableIssueHandler)

    def test_factory_accepts_feishu_bitable_engine(self, feishu_config):
        feishu_config["issue_engine"] = "feishu_bitable"
        handler = get_issue_handler(feishu_config)
        assert isinstance(handler, FeishuBitableIssueHandler)

    def test_normalize_issue_engine_preserves_canonical_name(self):
        assert normalize_issue_engine("feishu_bitable") == "feishu_bitable"

    @patch("threadline.utils.issues.feishu_bitable_handler.requests.post")
    def test_create_issue_maps_fields_and_returns_record_id(
        self,
        mock_post,
        handler,
    ):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_response.text = "{\"code\":0}"
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "record": {
                    "record_id": "rec123",
                }
            },
        }
        mock_post.return_value = mock_response

        record_id = handler.create_issue(
            issue_data={
                "title": "New issue",
                "description": "Description body",
                "priority": "High",
            },
            email_data={
                "id": "email-1",
                "subject": "Subject line",
                "metadata": {"scene": "product_issue"},
            },
            attachments=[],
        )

        assert record_id == "rec123"
        assert mock_post.call_count == 1
        called_url = mock_post.call_args.args[0]
        assert called_url.endswith(
            "/bitable/v1/apps/bascn123/tables/tbl123/records"
        )

        called_payload = mock_post.call_args.kwargs["json"]
        assert called_payload["fields"]["标题"] == "New issue"
        assert called_payload["fields"]["描述"] == "Description body"
        assert called_payload["fields"]["优先级"] == "High"
        assert called_payload["fields"]["邮件主题"] == "Subject line"
        assert called_payload["fields"]["元数据"] == json.dumps(
            {"scene": "product_issue"},
            ensure_ascii=False,
        )

    def test_get_issue_url_uses_template_when_configured(self, handler):
        handler.record_url_template = (
            "https://example.feishu.cn/base/{app_token}?table={table_id}"
            "&record={record_id}"
        )
        url = handler.get_issue_url("rec123")
        assert "rec123" in url
        assert "bascn123" in url

    @patch("threadline.utils.issues.feishu_bitable_handler.requests.post")
    def test_create_issue_uploads_attachment_tokens(
        self,
        mock_post,
        handler,
        tmp_path,
    ):
        attachment_file = tmp_path / "demo.pdf"
        attachment_file.write_bytes(b"demo-bytes")

        upload_response = Mock()
        upload_response.raise_for_status.return_value = None
        upload_response.status_code = 200
        upload_response.text = "{\"code\":0}"
        upload_response.json.return_value = {
            "code": 0,
            "data": {
                "file_token": "file-token-123",
            },
        }

        create_response = Mock()
        create_response.raise_for_status.return_value = None
        create_response.status_code = 200
        create_response.text = "{\"code\":0}"
        create_response.json.return_value = {
            "code": 0,
            "data": {
                "record": {
                    "record_id": "rec123",
                }
            },
        }

        mock_post.side_effect = [upload_response, create_response]

        record_id = handler.create_issue(
            issue_data={
                "title": "New issue",
                "description": "Description body",
                "priority": "High",
            },
            email_data={
                "id": "email-1",
                "subject": "Subject line",
                "metadata": {"scene": "product_issue"},
            },
            attachments=[
                {
                    "file_path": str(attachment_file),
                    "filename": "demo.pdf",
                }
            ],
        )

        assert record_id == "rec123"
        assert mock_post.call_count == 2
        upload_payload = mock_post.call_args_list[0].kwargs["data"]
        assert upload_payload["file_name"] == "demo.pdf"
        assert upload_payload["parent_type"] == "bitable"
        assert upload_payload["parent_node"] == "bascn123"

        create_payload = mock_post.call_args_list[1].kwargs["json"]
        assert create_payload["fields"]["附件"] == [
            {"file_token": "file-token-123"}
        ]

    def test_upload_attachments_is_noop_for_feishu(
        self,
        handler,
    ):
        result = handler.upload_attachments(
            issue_key="rec123",
            attachments=[{"filename": "a.png"}],
        )
        assert result == {
            "uploaded_count": 0,
            "skipped_count": 1,
        }

    def test_resolve_attachment_parent_node_uses_app_token_for_bitable_uploads(
        self,
        handler,
    ):
        assert handler._resolve_attachment_parent_node() == "bascn123"

    def test_resolve_attachment_parent_node_can_fall_back_to_folder_token(
        self,
        feishu_config,
    ):
        feishu_config["feishu_bitable"]["attachment_upload_parent_type"] = (
            "explorer"
        )
        handler = FeishuBitableIssueHandler(feishu_config)
        assert handler._resolve_attachment_parent_node() == "folder-token-123"
