from types import SimpleNamespace
from unittest.mock import Mock, patch

from threadline.utils.issues.jira_client import JiraClient


def _build_client():
    with patch("threadline.utils.issues.jira_client.JIRA") as jira_cls:
        jira_instance = Mock()
        jira_instance.myself.return_value = {"name": "tester"}
        jira_cls.return_value = jira_instance
        client = JiraClient(
            jira_url="https://jira.example.com/",
            username="user",
            password="token",
        )
    return client, jira_instance


def test_search_issues_translates_pagination_args():
    client, jira_instance = _build_client()

    client.search_issues("project = DEV", max_results=50, start_at=100)

    jira_instance.search_issues.assert_called_once_with(
        "project = DEV",
        maxResults=50,
        startAt=100,
    )


def test_get_project_components_handles_missing_optional_fields():
    client, jira_instance = _build_client()
    jira_instance.project.return_value = SimpleNamespace(
        components=[
            SimpleNamespace(
                name="Backend",
                assigneeType="PROJECT_DEFAULT",
                isAssigneeTypeValid=True,
            )
        ]
    )

    components = client.get_project_components("DEV")

    assert components == [
        {
            "name": "Backend",
            "description": "",
            "lead": None,
            "assignee_type": "PROJECT_DEFAULT",
            "is_assignee_type_valid": True,
        }
    ]


def test_get_issue_attachment_fingerprints_reads_issue_fields():
    client, jira_instance = _build_client()
    jira_instance.issue.return_value = SimpleNamespace(
        fields=SimpleNamespace(
            attachment=[
                SimpleNamespace(id="10001", filename="demo.png", size=16),
                SimpleNamespace(id="10002", filename="note.txt", size=8),
            ]
        )
    )

    fingerprints = client.get_issue_attachment_fingerprints("REQ-1")

    assert fingerprints == [
        "jira_id:10001",
        "name:demo.png:16",
        "jira_id:10002",
        "name:note.txt:8",
    ]
