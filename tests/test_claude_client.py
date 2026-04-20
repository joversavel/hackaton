import os, pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault("ANTHROPIC_API_KEY", "fake-key")

from claude_client import ClaudeClient, requires_confirmation

def test_requires_confirmation_detects_write_tools():
    tool_use = {"name": "assign_ticket", "input": {"ticket_id": "PROJ-1", "assignee": "jan", "requires_confirmation": True}}
    assert requires_confirmation(tool_use) is True

def test_requires_confirmation_false_for_read_tools():
    tool_use = {"name": "get_open_tickets", "input": {}}
    assert requires_confirmation(tool_use) is False

def test_requires_confirmation_false_when_flag_absent():
    tool_use = {"name": "assign_ticket", "input": {"ticket_id": "PROJ-1", "assignee": "jan"}}
    assert requires_confirmation(tool_use) is False

def test_claude_client_initializes():
    client = ClaudeClient()
    assert client is not None

def test_chat_returns_text_response():
    fake_resp = MagicMock()
    fake_resp.stop_reason = "end_turn"
    fake_resp.content = [MagicMock(type="text", text="Hallo!")]
    fake_resp.usage = MagicMock(input_tokens=10, output_tokens=5)

    with patch("claude_client.anthropic.Anthropic") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.beta.prompt_caching.messages.create.return_value = fake_resp
        client = ClaudeClient()
        result = client.chat(messages=[{"role": "user", "content": "test"}])
    assert result["type"] == "text"
    assert result["text"] == "Hallo!"

def test_chat_detects_confirmation_needed():
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "assign_ticket"
    tool_block.id = "tool-123"
    tool_block.input = {"ticket_id": "PROJ-1", "assignee": "jan", "requires_confirmation": True}

    fake_resp = MagicMock()
    fake_resp.stop_reason = "tool_use"
    fake_resp.content = [tool_block]
    fake_resp.usage = MagicMock(input_tokens=10, output_tokens=5)

    with patch("claude_client.anthropic.Anthropic") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.beta.prompt_caching.messages.create.return_value = fake_resp
        client = ClaudeClient()
        result = client.chat(messages=[{"role": "user", "content": "wijs ticket toe"}])
    assert result["type"] == "confirmation_required"
    assert result["tool_name"] == "assign_ticket"
