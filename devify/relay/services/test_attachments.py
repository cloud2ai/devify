from __future__ import annotations

import base64
import binascii
import os
import tempfile
from typing import Any


BUILTIN_TEST_ATTACHMENT = {
    "filename": "builtin-test-image.png",
    "content_type": "image/png",
    "base64": (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5P6WQAAAAASUVORK5CYII="
    ),
}


def build_test_attachments(
    raw_attachments: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not raw_attachments:
        return [], []
    if not isinstance(raw_attachments, list):
        raise ValueError("attachments must be an array")

    attachments: list[dict[str, Any]] = []
    temp_paths: list[str] = []
    for index, item in enumerate(raw_attachments):
        if not isinstance(item, dict):
            raise ValueError(f"attachments[{index}] must be an object")

        filename = (
            item.get("filename")
            or item.get("safe_filename")
            or f"test-attachment-{index + 1}"
        )
        content_type = item.get("content_type") or "application/octet-stream"
        base64_data = item.get("base64") or item.get("data") or item.get("content") or ""
        if not base64_data:
            raise ValueError(f"attachments[{index}] is missing base64 content")

        try:
            file_bytes = base64.b64decode(base64_data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"attachments[{index}] base64 content is invalid") from exc

        suffix = os.path.splitext(filename)[1]
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        )
        try:
            temp_file.write(file_bytes)
            temp_file.flush()
        finally:
            temp_file.close()

        temp_paths.append(temp_file.name)
        attachments.append(
            {
                "filename": filename,
                "safe_filename": filename,
                "content_type": content_type,
                "file_size": len(file_bytes),
                "file_path": temp_file.name,
                "is_image": content_type.startswith("image/"),
            }
        )

    return attachments, temp_paths
