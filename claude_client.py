import os, json, time, logging
import httpx
import anthropic
from pathlib import Path
from dotenv import load_dotenv
from tool_definitions import TOOLS
from tools import dispatch_tool

log = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env", override=True)

def _load_ticket_flow() -> str:
    path = Path(__file__).parent / "docs" / "ticket_creation_flow.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""

def _load_algemene_regels() -> str:
    path = Path(__file__).parent / "docs" / "algemene_regels.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""

def _load_selectie() -> str:
    path = Path(__file__).parent / "docs" / "selectie.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""

TICKET_FLOW = _load_ticket_flow()

TICKET_CREATION_INSTRUCTION = """
Bij ticketaanmaak — volg altijd deze stappen:
1. Zoek eerst via get_open_tickets of er al een OPEN ticket bestaat voor hetzelfde probleem (vermijd duplicaten)
2. Zoek ook in Confluence of er een bekende oplossing is
3. NIET zoeken in opgeloste/gesloten tickets bij het aanmaken van een nieuw ticket
4. Als er al een open ticket bestaat: meld dit aan de gebruiker en vraag of ze toch een nieuw ticket willen
5. Als geen open ticket gevonden: start een dialoog op basis van de ticket creation flow
6. Stel de verplichte velden één voor één via gerichte vragen (samenvatting, beschrijving, prioriteit, entiteit, categorie)
7. Gebruik de checklist voor de juiste categorie om extra info op te vragen
8. Toon een samenvatting en vraag bevestiging vóór je create_ticket aanroept
"""

# Hardcoded defaults — used as fallback when prompts.json is missing or incomplete
SYSTEM_PROMPT_ADMIN = """Je bent een AI-assistent voor het Sterima/Pollet support team.

Toegestane acties (admin):
- Jira tickets opvragen, aanmaken, toewijzen, van status wijzigen, commentaar toevoegen
- Oplossingen zoeken in Confluence en opgeloste Jira tickets
- Kennisartikelen schrijven in Confluence

Richtlijnen:
- Antwoord altijd in het Nederlands, beknopt (max 3-4 bullet points)
- Geen emoji's gebruiken
- Bij ALLE schrijfacties (create_ticket, assign_ticket, add_comment, update_status, create_confluence_page): zet ALTIJD requires_confirmation=true
- Toon bij Smart Assign altijd een confidence % met uitleg
- Vermeld altijd de bron (ticket ID, Confluence URL)
- Voor eigen tickets: gebruik get_my_tickets met het e-mailadres van de ingelogde gebruiker

Oplossing zoeken:
- Zoek altijd in BEIDE bronnen: search_jira (opgeloste tickets) én search_confluence
- Als niets gevonden: stel voor om een nieuw Jira ticket aan te maken"""

SYSTEM_PROMPT_BEPERKT = """Je bent een AI-assistent voor het Sterima/Pollet support team.

Toegestane acties:
- Eigen tickets opvragen via get_my_tickets (gebruik altijd het e-mailadres van de ingelogde gebruiker)
- Nieuwe Jira tickets aanmaken
- Oplossingen zoeken in Confluence

Niet toegestaan:
- Alle tickets van een project opvragen
- Tickets toewijzen, van status wijzigen of commentaar toevoegen

Richtlijnen:
- Antwoord altijd in het Nederlands, beknopt (max 3-4 bullet points)
- Bij create_ticket: zet ALTIJD requires_confirmation=true
- Geen emoji's gebruiken
- Vermeld altijd de bron (ticket ID of Confluence URL)

Oplossing zoeken:
- Zoek in search_confluence
- Als niets gevonden: stel voor om een nieuw Jira ticket aan te maken"""


def _load_prompts() -> dict:
    """Load prompts from prompts.json; fall back to hardcoded defaults."""
    path = Path(__file__).parent / "prompts.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "admin": data.get("admin") or SYSTEM_PROMPT_ADMIN,
            "beperkt": data.get("beperkt") or SYSTEM_PROMPT_BEPERKT,
        }
    except Exception as e:
        log.warning("Could not load prompts.json (%s) — using defaults", e)
        return {"admin": SYSTEM_PROMPT_ADMIN, "beperkt": SYSTEM_PROMPT_BEPERKT}


PROMPTS = _load_prompts()

WRITE_TOOLS = {"assign_ticket", "add_comment", "update_status", "create_confluence_page", "create_ticket"}
ADMIN_ONLY_TOOLS = {"assign_ticket", "add_comment", "update_status", "get_open_tickets", "get_resolved_tickets", "search_jira"}


def requires_confirmation(tool_use: dict) -> bool:
    return (
        tool_use.get("name") in WRITE_TOOLS
        and tool_use.get("input", {}).get("requires_confirmation") is True
    )


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            http_client=httpx.Client(verify=False)
        )
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    def _create_message(self, system_prompt, allowed_tools, messages, retries=3, ticket_flow: str = ""):
        system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
        algemene_regels = _load_algemene_regels()
        if algemene_regels:
            system.append({
                "type": "text",
                "text": "--- ALGEMENE REGELS (altijd volgen) ---\n" + algemene_regels,
                "cache_control": {"type": "ephemeral"}
            })
        selectie = _load_selectie()
        if selectie:
            system.append({
                "type": "text",
                "text": "--- TICKET SELECTIE RICHTLIJNEN ---\n" + selectie,
                "cache_control": {"type": "ephemeral"}
            })
        if ticket_flow:
            system.append({
                "type": "text",
                "text": TICKET_CREATION_INSTRUCTION + "\n\n--- TICKET CREATION FLOW DOCUMENT ---\n" + ticket_flow,
                "cache_control": {"type": "ephemeral"}
            })
        for attempt in range(retries):
            try:
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=system,
                    tools=allowed_tools,
                    messages=messages,
                    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
                )
            except anthropic.RateLimitError as e:
                wait = 2 ** attempt * 5
                log.warning("Rate limit hit, wachten %ss (poging %s/%s)", wait, attempt + 1, retries)
                time.sleep(wait)
        raise anthropic.RateLimitError("Rate limit na %s pogingen" % retries, response=None, body=None)

    def chat(self, messages: list, role: str = "admin", user: dict = None) -> dict:
        system_prompt = PROMPTS.get("admin", SYSTEM_PROMPT_ADMIN) if role == "admin" else PROMPTS.get("beperkt", SYSTEM_PROMPT_BEPERKT)
        if user:
            system_prompt += f"\n\nIngelogde gebruiker: {user['display_name']} ({user['email']})"
        allowed_tools = TOOLS if role == "admin" else [t for t in TOOLS if t["name"] not in ADMIN_ONLY_TOOLS]
        response = self._create_message(system_prompt, allowed_tools, messages, ticket_flow=TICKET_FLOW)
        log.debug("STOP REASON: %s | CONTENT: %s", response.stop_reason, [b.type for b in response.content])
        if response.stop_reason == "tool_use":
            tool_blocks = [b for b in response.content if b.type == "tool_use"]
            assistant_content = [
                {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
                if b.type == "tool_use" else {"type": "text", "text": b.text}
                for b in response.content
            ]

            confirm_block = next(
                (b for b in tool_blocks if requires_confirmation({"name": b.name, "input": b.input})), None
            )
            if confirm_block:
                return {
                    "type": "confirmation_required",
                    "tool_name": confirm_block.name,
                    "tool_id": confirm_block.id,
                    "tool_input": confirm_block.input,
                    "assistant_content": assistant_content,
                    "messages_at_confirmation": messages,
                    "message": f"Wil je dat ik **{confirm_block.name}** uitvoer met: {confirm_block.input}?"
                }

            tool_results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": str(dispatch_tool(b.name, b.input))}
                for b in tool_blocks
            ]
            follow_up = messages + [
                {"role": "assistant", "content": assistant_content},
                {"role": "user", "content": tool_results}
            ]
            return self.chat(follow_up, role=role, user=user)

        text = next((b.text for b in response.content if b.type == "text"), "").strip()
        if not text and response.stop_reason == "end_turn":
            followup = self._create_message(
                system_prompt,
                allowed_tools,
                messages + [{"role": "assistant", "content": [{"type": "text", "text": " "}]},
                            {"role": "user", "content": "Geef een korte samenvatting van wat je hebt gevonden."}],
                ticket_flow=TICKET_FLOW
            )
            text = next((b.text for b in followup.content if b.type == "text"), "Geen resultaat gevonden.").strip()
        return {"type": "text", "text": text or "Geen resultaat gevonden."}

    def execute_confirmed_tool(self, tool_name: str, tool_id: str, tool_input: dict, messages_at_confirmation: list, assistant_content: list, role: str = "admin", user: dict = None) -> dict:
        confirmed_result = dispatch_tool(tool_name, tool_input)
        tool_results = []
        for block in assistant_content:
            if block["type"] != "tool_use":
                continue
            if block["id"] == tool_id:
                tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": str(confirmed_result)})
            else:
                other = dispatch_tool(block["name"], block["input"])
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": str(other)})
        follow_up = messages_at_confirmation + [
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": tool_results}
        ]
        return self.chat(follow_up, role=role, user=user)
