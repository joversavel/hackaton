import os
import anthropic
from tool_definitions import TOOLS
from tools import dispatch_tool

SYSTEM_PROMPT = """Je bent een AI-assistent voor het Sterima support team. Je helpt medewerkers met:
- Jira tickets onderzoeken, aanmaken en toewijzen
- Oplossingen zoeken in Confluence en SharePoint
- Kennisartikelen schrijven

Richtlijnen:
- Antwoord altijd in het Nederlands, beknopt (max 3-4 bullet points)
- Bij schrijfacties (assign, comment, status update, nieuwe pagina): zet ALTIJD requires_confirmation=true
- Toon bij Smart Assign altijd een confidence % met uitleg
- Vermeld altijd de bron (ticket ID, Confluence URL) bij je antwoord"""

WRITE_TOOLS = {"assign_ticket", "add_comment", "update_status", "create_confluence_page", "create_ticket"}


def requires_confirmation(tool_use: dict) -> bool:
    return (
        tool_use.get("name") in WRITE_TOOLS
        and tool_use.get("input", {}).get("requires_confirmation") is True
    )


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    def chat(self, messages: list) -> dict:
        response = self.client.beta.prompt_caching.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            tool_block = next((b for b in response.content if b.type == "tool_use"), None)
            if tool_block:
                tool_input = tool_block.input
                if requires_confirmation({"name": tool_block.name, "input": tool_input}):
                    return {
                        "type": "confirmation_required",
                        "tool_name": tool_block.name,
                        "tool_id": tool_block.id,
                        "tool_input": tool_input,
                        "message": f"Wil je dat ik **{tool_block.name}** uitvoer met: {tool_input}?"
                    }
                result = dispatch_tool(tool_block.name, tool_input)
                follow_up = messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": str(result)}]}
                ]
                return self.chat(follow_up)

        text = next((b.text for b in response.content if b.type == "text"), "")
        return {"type": "text", "text": text}

    def execute_confirmed_tool(self, tool_name: str, tool_input: dict, messages: list) -> dict:
        result = dispatch_tool(tool_name, tool_input)
        follow_up = messages + [
            {"role": "user", "content": f"Actie uitgevoerd: {result}. Bevestig kort aan de gebruiker."}
        ]
        return self.chat(follow_up)
