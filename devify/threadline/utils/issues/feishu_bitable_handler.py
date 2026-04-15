"""
Feishu Bitable issue handler.

This module creates a single record in a Feishu Bitable table using the
configured table/app token and field mappings.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List

import requests

import lark_oapi as lark
from lark_oapi.api.bitable.v1.model import (
    AppTableRecord as LarkAppTableRecord,
    CreateAppTableRecordRequest,
    ListAppTableRequest,
    UpdateAppTableRecordRequest,
)
from lark_oapi.api.drive.v1.model import (
    UploadAllFileRequest,
    UploadAllFileRequestBody,
)
from lark_oapi.core.model import RequestOption

logger = logging.getLogger(__name__)


MAX_RETRIES = 3
RETRY_DELAY = 1
DEFAULT_BASE_URL = "https://open.feishu.cn/open-apis"
DEFAULT_TOKEN_URL = (
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
)
DEFAULT_TABLES_URL = "/bitable/v1/apps/{app_token}/tables"
DEFAULT_RECORDS_URL = "/bitable/v1/apps/{app_token}/tables/{table_id}/records"
DEFAULT_RECORD_URL = (
    "/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
)
DEFAULT_UPLOAD_URL = "/drive/v1/files/upload_all"


class FeishuBitableIssueHandler:
    """
    Handler for creating Feishu Bitable records.

    The handler mirrors the Jira handler interface so the workflow can
    switch between engines without special casing the caller.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.feishu_config = config.get("feishu_bitable") or {}

        self.base_url = self.feishu_config.get("base_url", DEFAULT_BASE_URL)
        self.app_token = self.feishu_config.get("app_token")
        self.table_name = self.feishu_config.get("table_name")
        self.table_id = self.feishu_config.get("table_id")
        self.default_table_name = self.feishu_config.get("default_table_name")
        self.record_url_template = self.feishu_config.get(
            "record_url_template"
        )
        self.attachment_field_name = self.feishu_config.get(
            "attachment_field_name", "附件"
        )
        self.image_field_name = self.feishu_config.get(
            "image_field_name", self.attachment_field_name
        )
        self.attachment_upload_parent_type = self.feishu_config.get(
            "attachment_upload_parent_type", "bitable"
        )
        self.image_upload_parent_type = self.feishu_config.get(
            "image_upload_parent_type", self.attachment_upload_parent_type
        )
        self.attachment_upload_parent_node = self.feishu_config.get(
            "attachment_upload_parent_node"
        )
        self.attachment_upload_parent_folder_token = self.feishu_config.get(
            "attachment_upload_parent_folder_token"
        )
        self.field_mappings = self.feishu_config.get("field_mappings", {})
        self.app_id = self.feishu_config.get("app_id")
        self.app_secret = self.feishu_config.get("app_secret")
        self.tenant_access_token = self.feishu_config.get(
            "tenant_access_token"
        )

        self._cached_token = None
        self._cached_token_expire_at = 0.0
        self._cached_tables: Dict[str, str] | None = None
        self._sdk_client = None

        if not self.app_token:
            logger.warning("Feishu Bitable app_token is not configured")
        if (
            not self.table_name
            and not self.table_id
            and not self.default_table_name
        ):
            logger.warning("Feishu Bitable table identifier is not configured")

    def get_issue_url(self, record_id: str) -> str:
        """
        Build a record URL for the created Feishu Bitable record.
        """
        table_id = self._resolve_table_id()

        if self.record_url_template:
            return self.record_url_template.format(
                app_token=self.app_token,
                table_id=table_id,
                record_id=record_id,
            )

        return (
            f"{self.base_url}/bitable/v1/apps/{self.app_token}"
            f"/tables/{table_id}/records/{record_id}"
        )

    def create_issue(
        self,
        issue_data: Dict[str, Any],
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
        force: bool = False,
    ) -> str:
        """
        Create a Feishu Bitable record.

        Args:
            issue_data: Issue data dictionary
            email_data: Email data dictionary
            attachments: Attachment metadata list
            force: Unused, kept for interface compatibility

        Returns:
            str: Created record id
        """
        payload_fields = self._build_record_fields(
            issue_data=issue_data,
            email_data=email_data,
            attachments=attachments,
            include_attachments=True,
        )

        if not payload_fields:
            raise ValueError(
                "No Feishu Bitable fields were generated from the settings"
            )

        table_id = self._resolve_table_id()
        url = self.base_url + DEFAULT_RECORDS_URL.format(
            app_token=self.app_token,
            table_id=table_id,
        )

        response_data = self._post_with_retry(url, {"fields": payload_fields})
        record_id = self._extract_record_id(response_data)

        if not record_id:
            raise ValueError(
                f"Feishu Bitable create record response missing record id: "
                f"{response_data}"
            )

        logger.info(
            "Created Feishu Bitable record %s in table %s",
            record_id,
            table_id,
        )
        return record_id

    def upload_attachments(
        self, issue_key: str, attachments: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Feishu attachments are uploaded during record creation.

        This method remains as a compatibility hook so callers can invoke it
        unconditionally without causing a second update pass.
        """
        attachments = attachments or []
        if not attachments:
            return {
                "uploaded_count": 0,
                "skipped_count": 0,
            }

        attachment_field_name = (
            self.attachment_field_name or self.image_field_name
        )
        if not attachment_field_name:
            logger.info(
                "No Feishu attachment field configured for record %s",
                issue_key,
            )
            return {
                "uploaded_count": 0,
                "skipped_count": len(attachments),
            }

        logger.info(
            "Feishu attachment upload already happened during record "
            "creation for record %s",
            issue_key,
        )
        return {
            "uploaded_count": 0,
            "skipped_count": len(attachments),
        }

    def _build_record_fields(
        self,
        issue_data: Dict[str, Any],
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
        include_attachments: bool = True,
    ) -> Dict[str, Any]:
        """
        Map workflow data to Feishu table fields.

        The configuration uses a mapping of:
        table field name -> source key from the synthesized source data.
        """
        source_data = {
            "title": issue_data.get("title"),
            "description": issue_data.get("description"),
            "priority": issue_data.get("priority"),
            "feishu_priority": self._normalize_priority_for_feishu(
                issue_data.get("priority")
            ),
            "feishu_status": "未开始",
            "email_id": email_data.get("id"),
            "email_id_str": (
                str(email_data.get("id"))
                if email_data.get("id") is not None
                else None
            ),
            "subject": email_data.get("subject"),
            "summary_title": email_data.get("summary_title"),
            "summary_content": email_data.get("summary_content"),
            "llm_content": email_data.get("llm_content"),
            "metadata": email_data.get("metadata"),
            "attachment_count": len(attachments or []),
            "engine": "feishu_bitable",
        }

        mappings = self.field_mappings
        payload_fields: Dict[str, Any] = {}

        for field_name, source_key in mappings.items():
            if not source_key:
                continue

            value = source_data.get(source_key)
            value = self._normalize_field_value(value)
            if value is None or value == "":
                continue
            payload_fields[field_name] = value

        if include_attachments:
            attachment_payload = self._build_attachment_payload(attachments)
            payload_fields.update(attachment_payload)

        return payload_fields

    def _normalize_field_value(self, value: Any) -> Any:
        """
        Normalize complex values for Feishu payloads.

        Complex values are serialized to JSON strings so they can be safely
        stored in plain text fields when the table schema does not use a
        dedicated structured type.
        """
        if value is None:
            return None

        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None

        if isinstance(value, (int, float, bool)):
            return value

        if isinstance(value, (list, dict)):
            if not value:
                return None
            return json.dumps(value, ensure_ascii=False)

        cleaned = str(value).strip()
        return cleaned or None

    def _normalize_priority_for_feishu(self, value: Any) -> str | None:
        """
        Convert internal priority values into Feishu single-select labels.
        """
        if value is None:
            return None

        normalized = str(value).strip().lower()
        mapping = {
            "high": "高",
            "urgent": "高",
            "medium": "中",
            "normal": "中",
            "low": "低",
        }
        return mapping.get(normalized, str(value).strip() or None)

    def _build_attachment_payload(
        self,
        attachments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Upload local files and map them into a single attachment field.

        Images and documents share the same attachment field in Feishu
        Bitable, so the handler keeps one upload flow and one target field.
        """
        if not attachments:
            return {}

        payload_fields: Dict[str, Any] = {}
        attachment_field_name = (
            self.attachment_field_name or self.image_field_name
        )

        if attachment_field_name:
            file_tokens = self._upload_attachments_to_tokens(
                attachments,
                parent_type=self.attachment_upload_parent_type,
                parent_node=self._resolve_attachment_parent_node(),
            )
            if file_tokens:
                payload_fields[attachment_field_name] = file_tokens

        return payload_fields

    def _upload_attachments_to_tokens(
        self,
        attachments: List[Dict[str, Any]],
        parent_type: str,
        parent_node: str | None = None,
    ) -> List[Dict[str, str]]:
        """
        Upload local files to Feishu and return attachment field values.
        """
        uploaded: List[Dict[str, str]] = []

        for attachment in attachments:
            file_path = attachment.get("file_path")
            if not file_path:
                logger.warning(
                    "Skipping attachment without file_path: %s",
                    attachment.get("filename"),
                )
                continue

            if not os.path.exists(file_path):
                logger.warning(
                    "Skipping attachment with missing file_path: %s",
                    file_path,
                )
                continue

            try:
                resolved_parent_node = (
                    parent_node or self._resolve_attachment_parent_node()
                )
                file_token = self._upload_single_file(
                    file_path=file_path,
                    file_name=(
                        attachment.get("safe_filename")
                        or attachment.get("filename")
                        or file_path.rsplit("/", 1)[-1]
                    ),
                    parent_type=parent_type,
                    parent_node=resolved_parent_node,
                )
                uploaded.append({"file_token": file_token})
            except Exception as exc:
                logger.warning(
                    "Failed to upload attachment %s: %s",
                    attachment.get("filename") or file_path,
                    exc,
                )

        return uploaded

    def _update_record_fields(
        self,
        record_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing Feishu Bitable record with the provided fields.
        """
        table_id = self._resolve_table_id()

        if self._sdk_available():
            return self._update_record_via_sdk(
                table_id=table_id,
                record_id=record_id,
                fields=fields,
            )

        url = (
            f"{self.base_url}"
            f"/bitable/v1/apps/{self.app_token}"
            f"/tables/{table_id}/records/{record_id}"
        )
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

        response = requests.put(
            url,
            headers=headers,
            json={"fields": fields},
            timeout=15,
        )

        response_text = response.text
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code >= 400 or data.get("code") not in (0, None):
            raise ValueError(
                self._format_response_error(
                    self._build_error_details(
                        response=response,
                        response_text=response_text,
                        response_json=data,
                    )
                )
            )

        return data

    def _update_record_via_sdk(
        self,
        table_id: str,
        record_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing Feishu Bitable record using the official SDK.
        """
        client = self._get_sdk_client()
        if (
            client is None
            or UpdateAppTableRecordRequest is None
            or LarkAppTableRecord is None
        ):
            raise ValueError("Feishu SDK is unavailable")

        request = (
            UpdateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(table_id)
            .record_id(record_id)
            .request_body(LarkAppTableRecord.builder().fields(fields).build())
            .build()
        )
        response = client.bitable.v1.app_table_record.update(
            request,
            self._get_sdk_request_option(),
        )
        if not response.success():
            raise ValueError(
                self._format_sdk_response_error(
                    response,
                    "Failed to update Feishu Bitable record",
                )
            )

        return {
            "code": response.code,
            "data": {
                "record": {
                    "record_id": record_id,
                }
            },
        }

    def _resolve_attachment_parent_node(self) -> str:
        """
        Resolve the configured parent node token used for attachment uploads.
        """
        explicit_parent_node = (
            self.attachment_upload_parent_node or ""
        ).strip()
        if explicit_parent_node:
            return explicit_parent_node

        parent_type = (self.attachment_upload_parent_type or "").strip()
        if parent_type in {"bitable", "bitable_file"}:
            if self.app_token:
                return self.app_token

            legacy_folder_token = (
                self.attachment_upload_parent_folder_token or ""
            ).strip()
            if legacy_folder_token:
                return legacy_folder_token

            raise ValueError(
                "Feishu bitable attachment upload requires app_token or "
                "feishu_bitable.attachment_upload_parent_node"
            )

        folder_token = (
            self.attachment_upload_parent_folder_token or ""
        ).strip()
        if folder_token:
            return folder_token

        raise ValueError(
            "Feishu attachment upload requires "
            "feishu_bitable.attachment_upload_parent_node or "
            "feishu_bitable.attachment_upload_parent_folder_token"
        )

    def _upload_single_file(
        self,
        file_path: str,
        file_name: str,
        parent_type: str,
        parent_node: str | None = None,
    ) -> str:
        """
        Upload a single file to Feishu and return file_token.
        """
        with open(file_path, "rb") as file_obj:
            file_bytes = file_obj.read()
            file_obj.seek(0)

            if self._sdk_available():
                return self._upload_single_file_via_sdk(
                    file_obj=file_obj,
                    file_bytes=file_bytes,
                    file_name=file_name,
                    parent_type=parent_type,
                    parent_node=parent_node,
                )

        url = f"{self.base_url}{DEFAULT_UPLOAD_URL}"
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
        }
        if not parent_node:
            raise ValueError(
                "Feishu attachment upload requires a parent node token"
            )

        form_data = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": str(len(file_bytes)),
        }
        files = {
            "file": (file_name, file_bytes),
        }

        response = requests.post(
            url,
            headers=headers,
            data=form_data,
            files=files,
            timeout=30,
        )

        response_text = response.text
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code >= 400 or data.get("code") not in (0, None):
            raise ValueError(
                self._format_response_error(
                    self._build_error_details(
                        response=response,
                        response_text=response_text,
                        response_json=data,
                    )
                )
            )

        file_token = data.get("data", {}).get("file_token")
        if not file_token:
            raise ValueError(
                f"Feishu upload response missing file_token: {data}"
            )

        return file_token

    def _sdk_available(self) -> bool:
        return True

    def _get_sdk_client(self):
        """
        Build and cache a Lark client when the official SDK is installed.
        """
        if not self._sdk_available():
            return None

        if self._sdk_client is not None:
            return self._sdk_client

        builder = lark.Client.builder().log_level(lark.LogLevel.WARNING)
        if self.app_id and self.app_secret:
            builder = builder.app_id(self.app_id).app_secret(self.app_secret)
        if self.tenant_access_token:
            builder = builder.enable_set_token(True)

        self._sdk_client = builder.build()
        return self._sdk_client

    def _get_sdk_request_option(self):
        """
        Build a request option for manual tenant token usage.
        """
        if not self._sdk_available():
            return None

        option = RequestOption()
        if self.tenant_access_token:
            option.tenant_access_token = self.tenant_access_token
        return option

    def _format_sdk_response_error(self, response: Any, prefix: str) -> str:
        """
        Format a SDK response failure into a human readable message.
        """
        log_id = getattr(response, "get_log_id", lambda: None)()
        code = getattr(response, "code", None)
        msg = getattr(response, "msg", None)
        return f"{prefix}: code={code}, msg={msg}, log_id={log_id}"

    def _list_tables_via_sdk(self) -> Dict[str, str]:
        """
        List Feishu Bitable tables using the official SDK.
        """
        client = self._get_sdk_client()
        if client is None or ListAppTableRequest is None:
            raise ValueError("Feishu SDK is unavailable")

        tables: Dict[str, str] = {}
        page_token: str | None = None

        while True:
            request_builder = (
                ListAppTableRequest.builder()
                .app_token(self.app_token)
                .page_size(200)
            )
            if page_token:
                request_builder = request_builder.page_token(page_token)

            response = client.bitable.v1.app_table.list(
                request_builder.build(),
                self._get_sdk_request_option(),
            )
            if not response.success():
                raise ValueError(
                    self._format_sdk_response_error(
                        response,
                        "Failed to list Feishu tables",
                    )
                )

            items = (response.data.items or []) if response.data else []
            for item in items:
                if item.name and item.table_id:
                    tables[item.name] = item.table_id

            if not response.data or not response.data.has_more:
                break

            page_token = response.data.page_token
            if not page_token:
                break

        return tables

    def _create_record_via_sdk(
        self,
        table_id: str,
        payload_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a Feishu Bitable record using the official SDK.
        """
        client = self._get_sdk_client()
        if (
            client is None
            or CreateAppTableRecordRequest is None
            or LarkAppTableRecord is None
        ):
            raise ValueError("Feishu SDK is unavailable")

        request = (
            CreateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(table_id)
            .request_body(
                LarkAppTableRecord.builder().fields(payload_fields).build()
            )
            .build()
        )
        response = client.bitable.v1.app_table_record.create(
            request,
            self._get_sdk_request_option(),
        )
        if not response.success():
            raise ValueError(
                self._format_sdk_response_error(
                    response,
                    "Failed to create Feishu Bitable record",
                )
            )

        record = response.data.record if response.data else None
        record_id = record.record_id if record and record.record_id else None
        return {
            "code": response.code,
            "data": {
                "record": {
                    "record_id": record_id,
                }
            },
        }

    def _upload_single_file_via_sdk(
        self,
        file_obj,
        file_bytes: bytes,
        file_name: str,
        parent_type: str,
        parent_node: str | None = None,
    ) -> str:
        """
        Upload a single file using the official SDK and return file_token.
        """
        client = self._get_sdk_client()
        if (
            client is None
            or UploadAllFileRequest is None
            or UploadAllFileRequestBody is None
        ):
            raise ValueError("Feishu SDK is unavailable")

        if not parent_node:
            raise ValueError(
                "Feishu attachment upload requires a parent folder token"
            )

        try:
            file_obj.seek(0)
            request = (
                UploadAllFileRequest.builder()
                .request_body(
                    UploadAllFileRequestBody.builder()
                    .file_name(file_name)
                    .parent_type(parent_type)
                    .parent_node(parent_node)
                    .size(len(file_bytes))
                    .file(file_obj)
                    .build()
                )
                .build()
            )
            response = client.drive.v1.file.upload_all(
                request,
                self._get_sdk_request_option(),
            )
            if not response.success():
                raise ValueError(
                    self._format_sdk_response_error(
                        response,
                        (
                            "Feishu upload failed for "
                            f"{file_name} with parent_node={parent_node}"
                        ),
                    )
                )

            file_token = response.data.file_token if response.data else None
            if not file_token:
                raise ValueError(
                    f"Feishu upload response missing file_token: {response}"
                )

            return file_token
        except Exception as exc:
            logger.warning(
                "Feishu upload failed for %s with parent_node=%s: %s",
                file_name,
                parent_node,
                exc,
            )
            raise

    def _resolve_table_id(self) -> str:
        """
        Resolve the target table id from configuration.

        Prefer explicit table_id for backward compatibility, otherwise look
        up the configured table name in the app's table list.
        """
        table_name = self.table_name or self.default_table_name
        if table_name:
            tables = self._get_tables()
            table_id = tables.get(table_name)
            if not table_id:
                raise ValueError(
                    f"Feishu Bitable table name not found: {table_name}. "
                    f"Available tables: {', '.join(sorted(tables.keys()))}"
                )

            return table_id

        if self.table_id:
            return self.table_id

        if not table_name:
            raise ValueError(
                "Feishu Bitable requires either table_id or table_name"
            )

    def _get_tables(self) -> Dict[str, str]:
        """
        Fetch and cache the available table names for the app.
        """
        if self._cached_tables is not None:
            return self._cached_tables

        if self._sdk_available():
            tables = self._list_tables_via_sdk()
            self._cached_tables = tables
            return tables

        url = (
            f"{self.base_url}"
            f"{DEFAULT_TABLES_URL.format(app_token=self.app_token)}"
        )
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {self._get_access_token()}"},
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        if data.get("code") not in (0, None):
            raise ValueError(f"Failed to list Feishu tables: {data}")

        tables: Dict[str, str] = {}
        for item in data.get("data", {}).get("items", []):
            name = item.get("name")
            table_id = item.get("table_id")
            if name and table_id:
                tables[name] = table_id

        self._cached_tables = tables
        return tables

    def _get_access_token(self) -> str:
        """
        Resolve the tenant access token.

        The handler accepts either a static `tenant_access_token` or an
        `app_id`/`app_secret` pair for on-demand token fetching.
        """
        if self.tenant_access_token:
            return self.tenant_access_token

        if self._cached_token and time.time() < self._cached_token_expire_at:
            return self._cached_token

        if not self.app_id or not self.app_secret:
            raise ValueError(
                "Feishu Bitable requires either tenant_access_token or "
                "app_id/app_secret"
            )

        response = requests.post(
            DEFAULT_TOKEN_URL,
            json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        if data.get("code") not in (0, None):
            raise ValueError(
                f"Failed to get Feishu tenant access token: {data}"
            )

        token = data.get("tenant_access_token")
        expire = data.get("expire", 0)
        if not token:
            raise ValueError(
                "Feishu token response missing tenant_access_token"
            )

        self._cached_token = token
        self._cached_token_expire_at = time.time() + max(expire - 60, 0)
        return token

    def _post_with_retry(
        self,
        url: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send a Feishu API request with a small retry loop.
        """
        if self._sdk_available():
            table_id = self._resolve_table_id()
            return self._create_record_via_sdk(
                table_id,
                payload.get("fields", {}),
            )

        last_error: Exception | None = None
        last_error_details: Dict[str, Any] | None = None
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=15,
                )

                response_text = response.text
                try:
                    data = response.json()
                except ValueError:
                    data = {}

                if response.status_code >= 400:
                    last_error_details = self._build_error_details(
                        response=response,
                        response_text=response_text,
                        response_json=data,
                    )
                    raise ValueError(
                        self._format_response_error(last_error_details)
                    )

                if data.get("code") not in (0, None):
                    last_error_details = self._build_error_details(
                        response=response,
                        response_text=response_text,
                        response_json=data,
                    )
                    raise ValueError(
                        self._format_response_error(last_error_details)
                    )

                return data

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Feishu Bitable request failed on attempt %s/%s: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    exc,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        raise ValueError(
            f"Failed to create Feishu Bitable record after retries: "
            f"{last_error}. Details: {last_error_details}"
        )

    def _build_error_details(
        self,
        response: requests.Response,
        response_text: str,
        response_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Collect the most useful response details for debugging.
        """
        return {
            "status_code": response.status_code,
            "request_id": (
                response.headers.get("X-Request-Id")
                or response.headers.get("x-request-id")
            ),
            "response_text": response_text,
            "response_json": response_json,
        }

    def _format_response_error(self, error_details: Dict[str, Any]) -> str:
        """
        Format a Feishu API failure for easier debugging.
        """
        response_json = error_details.get("response_json") or {}
        code = response_json.get("code")
        msg = response_json.get("msg")
        status_code = error_details.get("status_code")
        request_id = error_details.get("request_id")
        response_text = error_details.get("response_text")

        parts = [f"Feishu Bitable API error", f"status={status_code}"]

        if code is not None:
            parts.append(f"code={code}")
        if msg:
            parts.append(f"msg={msg}")
        if request_id:
            parts.append(f"request_id={request_id}")
        if response_text:
            parts.append(f"body={response_text}")

        return "; ".join(parts)

    def _extract_record_id(self, response_data: Dict[str, Any]) -> str | None:
        """
        Extract the record id from the Feishu response payload.
        """
        data = response_data.get("data", {})
        if isinstance(data, dict):
            record = data.get("record")
            if isinstance(record, dict):
                return record.get("record_id") or record.get("id")

            return (
                data.get("record_id")
                or data.get("id")
                or data.get("recordId")
            )

        return response_data.get("record_id") or response_data.get("id")
