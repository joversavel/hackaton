import json, os, pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault("JIRA_BASE_URL", "https://test.atlassian.net")
os.environ.setdefault("JIRA_EMAIL", "test@test.com")
os.environ.setdefault("JIRA_API_TOKEN", "fake-token")
os.environ.setdefault("USE_MOCK_DATA", "false")

from tools.jira_tools import get_open_tickets, get_resolved_tickets, create_ticket, assign_ticket, add_comment, update_status


def mock_jira_response(data):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def test_get_open_tickets_returns_list():
    fake = {"issues": [{"key": "PROJ-1", "fields": {"summary": "Test", "status": {"name": "Open"}, "assignee": None}}]}
    with patch("tools.jira_tools.requests.post", return_value=mock_jira_response(fake)):
        result = get_open_tickets()
    assert isinstance(result, list)
    assert result[0]["id"] == "PROJ-1"


def test_get_open_tickets_marks_unassigned():
    fake = {"issues": [{"key": "PROJ-1", "fields": {"summary": "Test", "status": {"name": "Open"}, "assignee": None}}]}
    with patch("tools.jira_tools.requests.post", return_value=mock_jira_response(fake)):
        result = get_open_tickets()
    assert result[0]["assignee"] is None


def test_get_resolved_tickets_uses_done_jql():
    fake = {"issues": []}
    with patch("tools.jira_tools.requests.post", return_value=mock_jira_response(fake)) as mock_post:
        get_resolved_tickets(project="PROJ")
    call_params = mock_post.call_args
    assert "status=Done" in str(call_params)


def test_create_ticket_returns_ticket_id():
    fake = {"key": "PROJ-10", "id": "10010"}
    with patch("tools.jira_tools.requests.post", return_value=mock_jira_response(fake)):
        result = create_ticket(summary="Test ticket", project="PROJ")
    assert result["id"] == "PROJ-10"


def test_assign_ticket_calls_correct_endpoint():
    m = MagicMock()
    m.status_code = 204
    m.raise_for_status = MagicMock()
    with patch("tools.jira_tools.requests.put", return_value=m) as mock_put:
        assign_ticket(ticket_id="PROJ-1", assignee="jan.peeters")
    assert "PROJ-1" in str(mock_put.call_args)


def test_get_open_tickets_mock_fallback(monkeypatch):
    monkeypatch.setenv("USE_MOCK_DATA", "true")
    result = get_open_tickets()
    assert isinstance(result, list)
    assert len(result) > 0
