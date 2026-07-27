"""GitHub Issues handler used by Relay smart delivery."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote, urlparse

import requests
from django.conf import settings
from threadline.utils.issues.jira_utils import render_summary

logger = logging.getLogger(__name__)

GITHUB_API_ROOT = "https://api.github.com"
GITHUB_WEB_ROOT = "https://github.com"
REQUEST_TIMEOUT_SECONDS = 15
GITHUB_ISSUE_BODY_MAX_LENGTH = 65_536
GITHUB_ISSUE_TRUNCATION_NOTICE = (
    "\n\n> [!NOTE]\n"
    "> This issue body was truncated because it exceeded GitHub's issue body limit.\n"
)
REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?/[A-Za-z0-9_.-]+$"
)
IMAGE_PLACEHOLDER_PATTERN = re.compile(r"\[IMAGE:\s*([^\]]+)\]")


def _string_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"GitHub {field_name} must be a list of strings")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"GitHub {field_name} must be a list of strings")
        normalized = item.strip()
        if normalized not in result:
            result.append(normalized)
    return result


def validate_github_config(config: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Validate and normalize the public Relay GitHub config contract."""
    raw_config = config or {}
    github_config = raw_config.get("github", raw_config)
    if not isinstance(github_config, Mapping):
        raise ValueError("GitHub config must be an object")

    repo = str(github_config.get("repo") or "").strip()
    if not REPOSITORY_PATTERN.fullmatch(repo):
        raise ValueError("GitHub repo must use the owner/name format")

    token = str(github_config.get("token") or "").strip()
    if not token:
        raise ValueError("GitHub token is required")

    return {
        "repo": repo,
        "token": token,
        "labels": _string_list(github_config.get("labels"), field_name="labels"),
        "assignees": _string_list(
            github_config.get("assignees"), field_name="assignees"
        ),
    }


class GitHubIssueHandler:
    """Create and update GitHub issues from Relay snapshots."""

    def __init__(
        self,
        config: Mapping[str, Any] | None,
        *,
        session: requests.Session | None = None,
    ) -> None:
        github_config = validate_github_config(config)
        self.repo = github_config["repo"]
        self.token = github_config["token"]
        self.labels = github_config["labels"]
        self.assignees = github_config["assignees"]
        self.session = session or requests.Session()

    @property
    def issues_api_url(self) -> str:
        return f"{GITHUB_API_ROOT}/repos/{self.repo}/issues"

    def get_issue_url(self, issue_number: str | int) -> str:
        normalized_number = self._normalize_issue_number(issue_number)
        return f"{GITHUB_WEB_ROOT}/{self.repo}/issues/{normalized_number}"

    def create_issue(
        self,
        issue_data: Dict[str, Any],
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
        force: bool = False,
    ) -> str:
        del force
        payload = self._build_payload(issue_data, email_data, attachments)
        response_data = self._request("POST", self.issues_api_url, payload)
        return self._extract_issue_number(response_data)

    def update_issue(
        self,
        issue_number: str | int,
        summary: str | None = None,
        issue_data: Dict[str, Any] | None = None,
        email_data: Dict[str, Any] | None = None,
        attachments: List[Dict[str, Any]] | None = None,
        force: bool = False,
    ) -> str:
        del force
        normalized_number = self._normalize_issue_number(issue_number)
        resolved_issue_data = dict(issue_data or {})
        if summary:
            resolved_issue_data["title"] = summary
        payload = self._build_payload(
            resolved_issue_data,
            email_data or {},
            attachments or [],
        )
        response_data = self._request(
            "PATCH",
            f"{self.issues_api_url}/{normalized_number}",
            payload,
        )
        return self._extract_issue_number(response_data)

    def _build_payload(
        self,
        issue_data: Dict[str, Any],
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        title = str(
            issue_data.get("title")
            or email_data.get("summary_title")
            or email_data.get("subject")
            or "Relay delivery"
        ).strip()
        if not title:
            raise ValueError("GitHub issue title is required")

        body = self._truncate_body(
            self._build_body(issue_data, email_data, attachments)
        )
        return {
            "title": title[:256],
            "body": body,
            "labels": self.labels,
            "assignees": self.assignees,
        }

    def _build_body(
        self,
        issue_data: Dict[str, Any],
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
    ) -> str:
        summary_data = email_data.get("summary_data")
        todos = email_data.get("todos")
        language = self._normalize_language(email_data.get("language"))
        if summary_data or todos:
            body = render_summary(summary_data, todos, language).strip()
        else:
            body = str(
                issue_data.get("description")
                or email_data.get("summary_content")
                or email_data.get("llm_content")
                or ""
            ).strip()

        attachment_urls = {
            str(
                attachment.get("safe_filename") or attachment.get("filename") or ""
            ): self._public_attachment_url(attachment)
            for attachment in attachments or []
        }
        attachment_urls = {
            filename: url
            for filename, url in attachment_urls.items()
            if filename and url
        }
        referenced_filenames: set[str] = set()

        def replace_image(match: re.Match) -> str:
            filename = match.group(1).strip()
            url = attachment_urls.get(filename)
            if not url:
                return match.group(0)
            referenced_filenames.add(filename)
            return f"![{filename}]({url})"

        body = IMAGE_PLACEHOLDER_PATTERN.sub(replace_image, body)

        attachment_lines: list[str] = []
        for attachment in attachments or []:
            filename = str(
                attachment.get("safe_filename")
                or attachment.get("filename")
                or "attachment"
            )
            if filename in referenced_filenames:
                continue
            url = attachment_urls.get(filename)
            if not url:
                continue
            label = str(attachment.get("filename") or filename)
            if attachment.get("is_image"):
                attachment_lines.append(f"![{label}]({url})")
            else:
                attachment_lines.append(f"- [{label}]({url})")

        if attachment_lines:
            body = self._append_section(body, "Attachments", attachment_lines)

        related_issue_keys = email_data.get("related_issue_keys") or []
        related_lines = [
            f"- #{self._normalize_issue_number(issue_number)}"
            for issue_number in related_issue_keys
        ]
        if related_lines:
            body = self._append_section(body, "Related issues", related_lines)

        return body

    @staticmethod
    def _truncate_body(body: str) -> str:
        if len(body) <= GITHUB_ISSUE_BODY_MAX_LENGTH:
            return body

        content_limit = GITHUB_ISSUE_BODY_MAX_LENGTH - len(
            GITHUB_ISSUE_TRUNCATION_NOTICE
        )
        return body[:content_limit] + GITHUB_ISSUE_TRUNCATION_NOTICE

    @staticmethod
    def _append_section(body: str, heading: str, lines: list[str]) -> str:
        section = f"## {heading}\n\n" + "\n".join(lines)
        return f"{body}\n\n{section}".strip() if body else section

    @staticmethod
    def _normalize_language(value: Any) -> str:
        normalized = str(value or "en").strip().lower()
        if normalized in {"chinese", "zh", "zh-cn", "zh_hans"}:
            return "zh"
        if normalized in {"spanish", "es"}:
            return "es"
        return "en"

    @staticmethod
    def _public_attachment_url(attachment: Mapping[str, Any]) -> str:
        explicit_url = str(attachment.get("url") or "").strip()
        if explicit_url:
            parsed_url = urlparse(explicit_url)
            if parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
                return explicit_url

        file_path = str(attachment.get("file_path") or "")
        base_url = str(getattr(settings, "ATTACHMENT_BASE_URL", "") or "").rstrip("/")
        storage_dir = str(getattr(settings, "EMAIL_ATTACHMENT_DIR", "") or "")
        if not file_path or not base_url or not storage_dir:
            return ""

        try:
            relative_path = (
                Path(file_path).resolve().relative_to(Path(storage_dir).resolve())
            )
        except (OSError, ValueError):
            return ""

        return f"{base_url}/attachments/{quote(str(relative_path), safe='/')}"

    def _request(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = self.session.request(
            method,
            url,
            json=payload,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response_data = response.json()
        except ValueError as exc:
            raise ValueError("GitHub API returned an invalid JSON response") from exc

        if response.status_code >= 400:
            message = (
                response_data.get("message")
                if isinstance(response_data, Mapping)
                else "request failed"
            )
            raise ValueError(
                f"GitHub API request failed ({response.status_code}): {message}"
            )
        if not isinstance(response_data, Mapping):
            raise ValueError("GitHub API returned an invalid response")
        return dict(response_data)

    @staticmethod
    def _extract_issue_number(response_data: Mapping[str, Any]) -> str:
        return GitHubIssueHandler._normalize_issue_number(response_data.get("number"))

    @staticmethod
    def _normalize_issue_number(issue_number: Any) -> str:
        normalized = str(issue_number or "").strip()
        if not normalized.isdigit() or int(normalized) <= 0:
            raise ValueError("GitHub issue number must be a positive integer")
        return normalized
