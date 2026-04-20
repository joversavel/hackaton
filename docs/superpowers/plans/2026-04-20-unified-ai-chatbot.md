# Unified AI Workspace Assistant — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flask webchatbot die via Claude tool use Jira tickets onderzoekt, assigneert en Confluence kennisartikelen schrijft, met bevestigingsflow voor alle schrijfacties.

**Architecture:** Flask backend met Claude API (tool use loop). Alle Atlassian + SharePoint operaties zijn Python functies die als Claude tools geregistreerd zijn. Schrijfacties vereisen gebruikersbevestiging via een `/confirm` POST endpoint, gescheiden van de SSE chatstream.

**Tech Stack:** Python 3.11+, Flask, Anthropic SDK (`claude-sonnet-4-6`), Atlassian REST API v3, Microsoft Graph API v1.0, Vanilla JS frontend.

---

## File Map

| Bestand | Verantwoordelijkheid | Team |
|---|---|---|
| `requirements.txt` | Python dependencies | Iedereen |
| `.env.example` | Credential template | Iedereen |
| `.gitignore` | `.env` + `__pycache__` uitsluiten | Iedereen |
| `tool_definitions.py` | TOOLS lijst — gedeeld contract Team 1 & 2 | Team 1 |
| `tools/__init__.py` | Tool dispatcher: naam → functie | Team 2 |
| `tools/jira_tools.py` | Jira REST API: 6 functies + mock fallback | Team 2 |
| `tools/confluence_tools.py` | Confluence REST API: 2 functies + mock fallback | Team 2 |
| `tools/sharepoint_tools.py` | Graph API: 3 functies + mock fallback | Team 2 |
| `fixtures/jira_mock.json` | Jira testdata (10–15 tickets) | Team 2 |
| `fixtures/confluence_mock.json` | Confluence testpagina's | Team 2 |
| `fixtures/sharepoint_mock.json` | SharePoint testdocumenten | Team 3 |
| `claude_client.py` | Claude API client + tool use loop + prompt caching | Team 1 |
| `auth.py` | Mock login, 3 gebruikers, sessie beheer | Team 3 |
| `app.py` | Flask routes: `/`, `/chat`, `/confirm`, `/login`, `/logout` | Team 3 |
| `templates/chat.html` | Chat UI — HTML structuur | Team 3 |
| `static/chat.js` | SSE client, bevestigingsdialoog, berichten renderen | Team 3 |
| `tests/test_jira_tools.py` | Unit tests Jira functies (mock HTTP) | Team 2 |
| `tests/test_confluence_tools.py` | Unit tests Confluence functies | Team 2 |
| `tests/test_sharepoint_tools.py` | Unit tests SharePoint functies | Team 2 |
| `tests/test_claude_client.py` | Tests tool use loop + bevestigingsdetectie | Team 1 |
| `tests/test_auth.py` | Tests login/logout/sessie | Team 3 |

---

## Chunk 1: Project Bootstrap

> Iedereen samen — uur 1. Eén persoon doet dit, rest kloont na push.

### Task 1: Repo structuur + dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `tools/__init__.py`
- Create: `fixtures/.gitkeep`

- [ ] **Stap 1: Maak `requirements.txt`**

```
flask
flask-session
anthropic
requests
python-dotenv
pytest
pytest-mock
```

- [ ] **Stap 2: Maak `.env.example`**

```
ANTHROPIC_API_KEY=
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=
JIRA_API_TOKEN=
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
SHAREPOINT_SITE_ID=
FLASK_SECRET_KEY=change-me-in-production
USE_MOCK_DATA=false
```

- [ ] **Stap 3: Maak `.gitignore`**

```
.env
__pycache__/
*.pyc
*.pyo
flask_session/
.pytest_cache/
```

- [ ] **Stap 4: Maak lege `tools/__init__.py`**

```python
# dispatcher wordt ingevuld in Task 8
```

- [ ] **Stap 5: Installeer dependencies**

```bash
pip install -r requirements.txt
```

Verwacht: alle packages geïnstalleerd zonder errors.

- [ ] **Stap 6: Commit**

```bash
git add requirements.txt .env.example .gitignore tools/__init__.py
git commit -m "chore: project bootstrap — dependencies en structuur"
```

---

## Chunk 2: Tool Definities (Team 1)

> Gedeeld contract tussen Team 1 en Team 2. Team 1 schrijft dit; Team 2 implementeert de functies.

### Task 2: `tool_definitions.py` — Claude tool schemas

**Files:**
- Create: `tool_definitions.py`

- [ ] **Stap 1: Schrijf de TOOLS lijst**

```python
# tool_definitions.py
TOOLS = [
    {
        "name": "get_open_tickets",
        "description": "Haal open Jira tickets op voor een project. Geeft een lijst van tickets met id, summary, status en assignee.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Jira project key, bijv. PROJ"}
            },
            "required": []
        }
    },
    {
        "name": "get_resolved_tickets",
        "description": "Haal opgeloste Jira tickets op voor historiekanalyse. Gebruikt JQL status=Done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Jira project key"},
                "max_results": {"type": "integer", "description": "Max aantal resultaten (default 20)"}
            },
            "required": []
        }
    },
    {
        "name": "create_ticket",
        "description": "Maak een nieuw Jira ticket aan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Titel van het ticket"},
                "description": {"type": "string", "description": "Uitgebreide beschrijving"},
                "project": {"type": "string", "description": "Jira project key"}
            },
            "required": ["summary", "project"]
        }
    },
    {
        "name": "assign_ticket",
        "description": "Wijs een Jira ticket toe aan een medewerker. ALTIJD requires_confirmation=true instellen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Jira ticket ID, bijv. PROJ-42"},
                "assignee": {"type": "string", "description": "Naam of account ID van de assignee"},
                "requires_confirmation": {"type": "boolean", "description": "Moet true zijn"}
            },
            "required": ["ticket_id", "assignee"]
        }
    },
    {
        "name": "add_comment",
        "description": "Voeg een comment toe aan een Jira ticket. ALTIJD requires_confirmation=true instellen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Jira ticket ID"},
                "comment": {"type": "string", "description": "Inhoud van het comment (markdown)"},
                "requires_confirmation": {"type": "boolean", "description": "Moet true zijn"}
            },
            "required": ["ticket_id", "comment"]
        }
    },
    {
        "name": "update_status",
        "description": "Update de status van een Jira ticket. ALTIJD requires_confirmation=true instellen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Jira ticket ID"},
                "status": {"type": "string", "description": "Nieuwe status, bijv. 'In Progress', 'Done'"},
                "requires_confirmation": {"type": "boolean", "description": "Moet true zijn"}
            },
            "required": ["ticket_id", "status"]
        }
    },
    {
        "name": "search_confluence",
        "description": "Zoek in de Confluence kennisbank op basis van een zoekopdracht.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Zoekterm of beschrijving van het probleem"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_confluence_page",
        "description": "Maak een nieuw kennisartikel aan in Confluence. ALTIJD requires_confirmation=true instellen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titel van het kennisartikel"},
                "content": {"type": "string", "description": "Inhoud in storage format (HTML of wiki markup)"},
                "space_key": {"type": "string", "description": "Confluence space key"},
                "requires_confirmation": {"type": "boolean", "description": "Moet true zijn"}
            },
            "required": ["title", "content", "space_key"]
        }
    },
    {
        "name": "search_sharepoint",
        "description": "Zoek documenten en pagina's in SharePoint.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Zoekterm"}
            },
            "required": ["query"]
        }
    },
]
```

- [ ] **Stap 2: Verifieer dat de lijst importeerbaar is**

```bash
python -c "from tool_definitions import TOOLS; print(len(TOOLS), 'tools geladen')"
```

Verwacht: `9 tools geladen`

- [ ] **Stap 3: Commit**

```bash
git add tool_definitions.py
git commit -m "feat: tool_definitions — gedeeld Claude tool use schema (9 tools)"
```

---

## Chunk 3: Integratie Tools — Jira (Team 2)

### Task 3: Jira mock fixtures

**Files:**
- Create: `fixtures/jira_mock.json`

- [ ] **Stap 1: Schrijf `fixtures/jira_mock.json`**

```json
{
  "open_tickets": [
    {"id": "PROJ-1", "summary": "Login pagina laadt niet op Safari", "status": "Open", "assignee": null, "description": "Gebruiker meldt dat de loginpagina vastloopt op Safari 17.", "created": "2026-04-15"},
    {"id": "PROJ-2", "summary": "API timeout bij grote exports", "status": "In Progress", "assignee": "jan.peeters", "description": "Export van meer dan 1000 rijen geeft een 504 Gateway Timeout.", "created": "2026-04-16"},
    {"id": "PROJ-3", "summary": "Email notificaties worden niet verstuurd", "status": "Open", "assignee": null, "description": "Sinds de update van 12 april komen er geen welkomstmails meer aan.", "created": "2026-04-17"},
    {"id": "PROJ-4", "summary": "Dashboard cijfers kloppen niet", "status": "Open", "assignee": null, "description": "Omzetcijfers in het dashboard wijken af van de database.", "created": "2026-04-18"},
    {"id": "PROJ-5", "summary": "SSL certificaat verloopt volgende week", "status": "Open", "assignee": null, "description": "Certificaat voor api.sterima.be verloopt op 27 april.", "created": "2026-04-19"}
  ],
  "resolved_tickets": [
    {"id": "PROJ-98", "summary": "Login timeout na 30 seconden", "status": "Done", "assignee": "sophie.claes", "resolution": "Session timeout config verhoogd naar 60 min. Getest en gedeployed.", "resolved_at": "2026-03-10", "resolution_time_hours": 3},
    {"id": "PROJ-97", "summary": "API 500 error bij null payload", "status": "Done", "assignee": "jan.peeters", "resolution": "Null check toegevoegd in request validator.", "resolved_at": "2026-03-08", "resolution_time_hours": 1.5},
    {"id": "PROJ-96", "summary": "Email template gebroken na update", "status": "Done", "assignee": "marie.dubois", "resolution": "Template variabelen aangepast na SMTP library upgrade.", "resolved_at": "2026-02-28", "resolution_time_hours": 2},
    {"id": "PROJ-95", "summary": "Dashboard laadt niet op Firefox", "status": "Done", "assignee": "sophie.claes", "resolution": "CSS grid fallback toegevoegd voor Firefox 115.", "resolved_at": "2026-02-20", "resolution_time_hours": 4},
    {"id": "PROJ-94", "summary": "Export timeout bij 500+ rijen", "status": "Done", "assignee": "jan.peeters", "resolution": "Paginering toegevoegd, max 500 rijen per request.", "resolved_at": "2026-02-15", "resolution_time_hours": 5}
  ],
  "team_members": [
    {"name": "Jan Peeters", "account_id": "jan.peeters", "specialties": ["API", "backend", "exports"], "avg_resolution_hours": 2.5},
    {"name": "Sophie Claes", "account_id": "sophie.claes", "specialties": ["frontend", "login", "CSS"], "avg_resolution_hours": 3.5},
    {"name": "Marie Dubois", "account_id": "marie.dubois", "specialties": ["email", "notifications", "templates"], "avg_resolution_hours": 2.0}
  ]
}
```

- [ ] **Stap 2: Commit**

```bash
git add fixtures/jira_mock.json
git commit -m "feat: jira mock fixtures — 5 open + 5 resolved tickets + team data"
```

### Task 4: `tools/jira_tools.py`

**Files:**
- Create: `tools/jira_tools.py`
- Create: `tests/test_jira_tools.py`

- [ ] **Stap 1: Schrijf de failing tests**

```python
# tests/test_jira_tools.py
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
    with patch("tools.jira_tools.requests.get", return_value=mock_jira_response(fake)):
        result = get_open_tickets()
    assert isinstance(result, list)
    assert result[0]["id"] == "PROJ-1"


def test_get_open_tickets_marks_unassigned():
    fake = {"issues": [{"key": "PROJ-1", "fields": {"summary": "Test", "status": {"name": "Open"}, "assignee": None}}]}
    with patch("tools.jira_tools.requests.get", return_value=mock_jira_response(fake)):
        result = get_open_tickets()
    assert result[0]["assignee"] is None


def test_get_resolved_tickets_uses_done_jql():
    fake = {"issues": []}
    with patch("tools.jira_tools.requests.get", return_value=mock_jira_response(fake)) as mock_get:
        get_resolved_tickets(project="PROJ")
    call_params = mock_get.call_args
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
```

- [ ] **Stap 2: Run tests — verifieer dat ze falen**

```bash
pytest tests/test_jira_tools.py -v
```

Verwacht: `ModuleNotFoundError` of `ImportError` (tools/jira_tools.py bestaat nog niet).

- [ ] **Stap 3: Implementeer `tools/jira_tools.py`**

```python
# tools/jira_tools.py
import json, os, requests
from pathlib import Path

JIRA_BASE = os.getenv("JIRA_BASE_URL", "")
AUTH = (os.getenv("JIRA_EMAIL", ""), os.getenv("JIRA_API_TOKEN", ""))
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

def _mock_data():
    path = Path(__file__).parent.parent / "fixtures" / "jira_mock.json"
    return json.loads(path.read_text())

def get_open_tickets(project: str = None) -> list:
    if USE_MOCK:
        return _mock_data()["open_tickets"]
    jql = "status != Done"
    if project:
        jql = f"project={project} AND {jql}"
    resp = requests.get(
        f"{JIRA_BASE}/rest/api/3/search",
        headers=HEADERS, auth=AUTH,
        params={"jql": jql, "maxResults": 50, "fields": "summary,status,assignee,description"}
    )
    resp.raise_for_status()
    issues = resp.json().get("issues", [])
    return [
        {
            "id": i["key"],
            "summary": i["fields"]["summary"],
            "status": i["fields"]["status"]["name"],
            "assignee": (i["fields"]["assignee"] or {}).get("displayName"),
            "description": i["fields"].get("description", "")
        }
        for i in issues
    ]

def get_resolved_tickets(project: str = None, max_results: int = 20) -> list:
    if USE_MOCK:
        return _mock_data()["resolved_tickets"]
    jql = "status=Done ORDER BY resolutiondate DESC"
    if project:
        jql = f"project={project} AND {jql}"
    resp = requests.get(
        f"{JIRA_BASE}/rest/api/3/search",
        headers=HEADERS, auth=AUTH,
        params={"jql": jql, "maxResults": max_results, "fields": "summary,status,assignee,comment,resolutiondate,resolution"}
    )
    resp.raise_for_status()
    issues = resp.json().get("issues", [])
    return [
        {
            "id": i["key"],
            "summary": i["fields"]["summary"],
            "assignee": (i["fields"]["assignee"] or {}).get("displayName"),
            "resolution": next(
                (c["body"] for c in i["fields"].get("comment", {}).get("comments", [])[-1:]),
                ""
            ),
            "resolved_at": i["fields"].get("resolutiondate", "")
        }
        for i in issues
    ]

def create_ticket(summary: str, project: str, description: str = "") -> dict:
    if USE_MOCK:
        return {"id": "PROJ-NEW", "summary": summary, "status": "Open"}
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": summary,
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]},
            "issuetype": {"name": "Bug"}
        }
    }
    resp = requests.post(f"{JIRA_BASE}/rest/api/3/issue", headers=HEADERS, auth=AUTH, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return {"id": data["key"], "summary": summary, "status": "Open"}

def assign_ticket(ticket_id: str, assignee: str, requires_confirmation: bool = True) -> dict:
    if USE_MOCK:
        return {"success": True, "ticket_id": ticket_id, "assignee": assignee}
    resp = requests.put(
        f"{JIRA_BASE}/rest/api/3/issue/{ticket_id}/assignee",
        headers=HEADERS, auth=AUTH,
        json={"accountId": assignee}
    )
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id, "assignee": assignee}

def add_comment(ticket_id: str, comment: str, requires_confirmation: bool = True) -> dict:
    if USE_MOCK:
        return {"success": True, "ticket_id": ticket_id}
    payload = {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}}
    resp = requests.post(f"{JIRA_BASE}/rest/api/3/issue/{ticket_id}/comment", headers=HEADERS, auth=AUTH, json=payload)
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id}

def update_status(ticket_id: str, status: str, requires_confirmation: bool = True) -> dict:
    if USE_MOCK:
        return {"success": True, "ticket_id": ticket_id, "status": status}
    transitions_resp = requests.get(f"{JIRA_BASE}/rest/api/3/issue/{ticket_id}/transitions", headers=HEADERS, auth=AUTH)
    transitions_resp.raise_for_status()
    transitions = transitions_resp.json().get("transitions", [])
    match = next((t for t in transitions if t["name"].lower() == status.lower()), None)
    if not match:
        available = [t["name"] for t in transitions]
        return {"success": False, "error": f"Status '{status}' niet gevonden. Beschikbaar: {available}"}
    resp = requests.post(
        f"{JIRA_BASE}/rest/api/3/issue/{ticket_id}/transitions",
        headers=HEADERS, auth=AUTH,
        json={"transition": {"id": match["id"]}}
    )
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id, "status": status}
```

- [ ] **Stap 4: Run tests — verifieer dat ze slagen**

```bash
pytest tests/test_jira_tools.py -v
```

Verwacht: alle 6 tests PASS.

- [ ] **Stap 5: Commit**

```bash
git add tools/jira_tools.py tests/test_jira_tools.py
git commit -m "feat: jira tools — 6 functies met mock fallback, alle tests groen"
```

---

## Chunk 4: Integratie Tools — Confluence + SharePoint (Team 2)

### Task 5: Confluence fixtures + `tools/confluence_tools.py`

**Files:**
- Create: `fixtures/confluence_mock.json`
- Create: `tools/confluence_tools.py`
- Create: `tests/test_confluence_tools.py`

- [ ] **Stap 1: Schrijf `fixtures/confluence_mock.json`**

```json
{
  "pages": [
    {
      "id": "123456",
      "title": "Oplossing: Login timeout problemen",
      "body": "## Probleem\nGebruikers worden uitgelogd na 30 seconden inactiviteit.\n\n## Oplossing\nSession timeout verhoogd in `application.yml`: `server.servlet.session.timeout=3600`. Herstart applicatie server na wijziging.\n\n## Verificatie\nLog in en wacht 5 minuten — sessie blijft actief.",
      "url": "https://yourcompany.atlassian.net/wiki/spaces/PROJ/pages/123456",
      "last_modified": "2026-03-10"
    },
    {
      "id": "123457",
      "title": "Oplossing: API timeout bij grote data exports",
      "body": "## Probleem\nExports van meer dan 500 rijen resulteren in een 504 Gateway Timeout.\n\n## Oplossing\nPaginering geïmplementeerd. Gebruik `?page=1&size=500` parameter. Zie `ExportController.java` voor implementatie.\n\n## Verificatie\nTest met 1000 rijen export — moet in 2 requests van 500 voltooien.",
      "url": "https://yourcompany.atlassian.net/wiki/spaces/PROJ/pages/123457",
      "last_modified": "2026-02-15"
    },
    {
      "id": "123458",
      "title": "Handleiding: Email notificaties configureren",
      "body": "## SMTP Configuratie\nVereiste omgevingsvariabelen:\n- `SMTP_HOST`: smtp.office365.com\n- `SMTP_PORT`: 587\n- `SMTP_USER`: noreply@sterima.be\n\n## Testen\nGebruik de `/admin/test-email` endpoint om een testmail te sturen.",
      "url": "https://yourcompany.atlassian.net/wiki/spaces/PROJ/pages/123458",
      "last_modified": "2026-01-20"
    }
  ]
}
```

- [ ] **Stap 2: Schrijf failing tests**

```python
# tests/test_confluence_tools.py
import os, pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault("CONFLUENCE_BASE_URL", "https://test.atlassian.net/wiki")
os.environ.setdefault("JIRA_EMAIL", "test@test.com")
os.environ.setdefault("JIRA_API_TOKEN", "fake-token")
os.environ.setdefault("CONFLUENCE_SPACE_KEY", "PROJ")
os.environ.setdefault("USE_MOCK_DATA", "false")

from tools.confluence_tools import search_confluence, create_confluence_page


def mock_resp(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def test_search_confluence_returns_list():
    fake = {"results": [{"id": "1", "title": "Test", "body": {"storage": {"value": "inhoud"}}, "_links": {"webui": "/page/1"}}]}
    with patch("tools.confluence_tools.requests.get", return_value=mock_resp(fake)):
        result = search_confluence(query="login")
    assert isinstance(result, list)
    assert result[0]["title"] == "Test"


def test_create_confluence_page_returns_url():
    fake = {"id": "999", "_links": {"webui": "/page/999"}}
    with patch("tools.confluence_tools.requests.post", return_value=mock_resp(fake)):
        result = create_confluence_page(title="Test", content="<p>test</p>", space_key="PROJ")
    assert "url" in result


def test_search_confluence_mock_fallback(monkeypatch):
    monkeypatch.setenv("USE_MOCK_DATA", "true")
    result = search_confluence(query="login")
    assert isinstance(result, list)
    assert len(result) > 0
```

- [ ] **Stap 3: Run tests — verifieer falen**

```bash
pytest tests/test_confluence_tools.py -v
```

Verwacht: `ImportError` (bestand bestaat nog niet).

- [ ] **Stap 4: Implementeer `tools/confluence_tools.py`**

```python
# tools/confluence_tools.py
import json, os, requests
from pathlib import Path

CONF_BASE = os.getenv("CONFLUENCE_BASE_URL", "")
AUTH = (os.getenv("JIRA_EMAIL", ""), os.getenv("JIRA_API_TOKEN", ""))
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

def _mock_data():
    path = Path(__file__).parent.parent / "fixtures" / "confluence_mock.json"
    return json.loads(path.read_text())

def search_confluence(query: str) -> list:
    if USE_MOCK:
        pages = _mock_data()["pages"]
        q = query.lower()
        return [p for p in pages if q in p["title"].lower() or q in p["body"].lower()] or pages[:2]
    resp = requests.get(
        f"{CONF_BASE}/rest/api/content/search",
        headers=HEADERS, auth=AUTH,
        params={"cql": f'text ~ "{query}" AND type=page', "limit": 5, "expand": "body.storage"}
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "body": r.get("body", {}).get("storage", {}).get("value", "")[:500],
            "url": CONF_BASE + r.get("_links", {}).get("webui", "")
        }
        for r in results
    ]

def create_confluence_page(title: str, content: str, space_key: str, requires_confirmation: bool = True) -> dict:
    if USE_MOCK:
        return {"success": True, "title": title, "url": f"{CONF_BASE}/spaces/{space_key}/pages/mock-new"}
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": content, "representation": "storage"}}
    }
    resp = requests.post(f"{CONF_BASE}/rest/api/content", headers=HEADERS, auth=AUTH, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return {
        "success": True,
        "title": title,
        "url": CONF_BASE + data.get("_links", {}).get("webui", "")
    }
```

- [ ] **Stap 5: Run tests — verifieer slagen**

```bash
pytest tests/test_confluence_tools.py -v
```

Verwacht: alle 3 tests PASS.

- [ ] **Stap 6: Commit**

```bash
git add fixtures/confluence_mock.json tools/confluence_tools.py tests/test_confluence_tools.py
git commit -m "feat: confluence tools — search + create page, mock fallback, tests groen"
```

### Task 6: SharePoint fixtures + `tools/sharepoint_tools.py`

**Files:**
- Create: `fixtures/sharepoint_mock.json`
- Create: `tools/sharepoint_tools.py`
- Create: `tests/test_sharepoint_tools.py`

- [ ] **Stap 1: Schrijf `fixtures/sharepoint_mock.json`**

```json
{
  "documents": [
    {
      "id": "doc-001",
      "name": "Technische Handleiding API Integratie.docx",
      "summary": "Stap-voor-stap handleiding voor het integreren met de Sterima REST API. Bevat authenticatie, endpoints en foutcodes.",
      "url": "https://sterima.sharepoint.com/sites/tech/docs/api-handleiding",
      "last_modified": "2026-03-01"
    },
    {
      "id": "doc-002",
      "name": "Serverinfrastructuur Overzicht 2026.pdf",
      "summary": "Overzicht van alle productieservers, load balancers en database clusters. Inclusief contactpersonen per component.",
      "url": "https://sterima.sharepoint.com/sites/tech/docs/infra-2026",
      "last_modified": "2026-01-15"
    },
    {
      "id": "doc-003",
      "name": "Incident Response Playbook.docx",
      "summary": "Procedures voor het afhandelen van productie-incidenten. P1 escalatie, communicatietemplate en rollback instructies.",
      "url": "https://sterima.sharepoint.com/sites/tech/docs/incident-playbook",
      "last_modified": "2026-02-10"
    }
  ]
}
```

- [ ] **Stap 2: Schrijf failing tests**

```python
# tests/test_sharepoint_tools.py
import os, pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault("AZURE_TENANT_ID", "fake-tenant")
os.environ.setdefault("AZURE_CLIENT_ID", "fake-client")
os.environ.setdefault("AZURE_CLIENT_SECRET", "fake-secret")
os.environ.setdefault("SHAREPOINT_SITE_ID", "fake-site")
os.environ.setdefault("USE_MOCK_DATA", "false")

from tools.sharepoint_tools import search_sharepoint, _get_graph_token


def mock_resp(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def test_search_sharepoint_returns_list():
    token_resp = {"access_token": "fake-token"}
    search_resp = {"value": [{"name": "Test.docx", "id": "1", "webUrl": "https://sp.com/test", "lastModifiedDateTime": "2026-01-01"}]}
    with patch("tools.sharepoint_tools.requests.post", return_value=mock_resp(token_resp)):
        with patch("tools.sharepoint_tools.requests.get", return_value=mock_resp(search_resp)):
            result = search_sharepoint(query="API")
    assert isinstance(result, list)


def test_search_sharepoint_mock_fallback(monkeypatch):
    monkeypatch.setenv("USE_MOCK_DATA", "true")
    result = search_sharepoint(query="handleiding")
    assert isinstance(result, list)
    assert len(result) > 0
```

- [ ] **Stap 3: Run tests — verifieer falen**

```bash
pytest tests/test_sharepoint_tools.py -v
```

Verwacht: `ImportError`.

- [ ] **Stap 4: Implementeer `tools/sharepoint_tools.py`**

```python
# tools/sharepoint_tools.py
import json, os, requests
from pathlib import Path

TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
SITE_ID = os.getenv("SHAREPOINT_SITE_ID", "")
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

def _mock_data():
    path = Path(__file__).parent.parent / "fixtures" / "sharepoint_mock.json"
    return json.loads(path.read_text())

def _get_graph_token() -> str:
    resp = requests.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default"
        }
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def search_sharepoint(query: str) -> list:
    if USE_MOCK:
        docs = _mock_data()["documents"]
        q = query.lower()
        return [d for d in docs if q in d["name"].lower() or q in d["summary"].lower()] or docs[:2]
    token = _get_graph_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drive/root/search(q='{query}')",
        headers=headers, params={"$select": "name,id,webUrl,lastModifiedDateTime", "$top": 5}
    )
    resp.raise_for_status()
    items = resp.json().get("value", [])
    return [
        {
            "id": i["id"],
            "name": i["name"],
            "url": i.get("webUrl", ""),
            "last_modified": i.get("lastModifiedDateTime", "")
        }
        for i in items
    ]

def get_document(document_id: str) -> dict:
    if USE_MOCK:
        docs = _mock_data()["documents"]
        return next((d for d in docs if d["id"] == document_id), {})
    token = _get_graph_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drive/items/{document_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()

def list_site_pages() -> list:
    if USE_MOCK:
        return _mock_data()["documents"]
    token = _get_graph_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/pages", headers=headers)
    resp.raise_for_status()
    return resp.json().get("value", [])
```

- [ ] **Stap 5: Run tests — verifieer slagen**

```bash
pytest tests/test_sharepoint_tools.py -v
```

Verwacht: alle 2 tests PASS.

- [ ] **Stap 6: Maak tool dispatcher in `tools/__init__.py`**

```python
# tools/__init__.py
from tools.jira_tools import (
    get_open_tickets, get_resolved_tickets, create_ticket,
    assign_ticket, add_comment, update_status
)
from tools.confluence_tools import search_confluence, create_confluence_page
from tools.sharepoint_tools import search_sharepoint, get_document, list_site_pages

TOOL_FUNCTIONS = {
    "get_open_tickets": get_open_tickets,
    "get_resolved_tickets": get_resolved_tickets,
    "create_ticket": create_ticket,
    "assign_ticket": assign_ticket,
    "add_comment": add_comment,
    "update_status": update_status,
    "search_confluence": search_confluence,
    "create_confluence_page": create_confluence_page,
    "search_sharepoint": search_sharepoint,
}

def dispatch_tool(name: str, inputs: dict) -> dict:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return {"error": f"Onbekende tool: {name}"}
    return fn(**inputs)
```

- [ ] **Stap 7: Test dispatcher**

```bash
python -c "from tools import dispatch_tool; import os; os.environ['USE_MOCK_DATA']='true'; print(dispatch_tool('get_open_tickets', {}))"
```

Verwacht: lijst van mock tickets geprint.

- [ ] **Stap 8: Commit**

```bash
git add fixtures/sharepoint_mock.json tools/sharepoint_tools.py tools/__init__.py tests/test_sharepoint_tools.py
git commit -m "feat: sharepoint tools + tool dispatcher — alle integraties compleet"
```

---

## Chunk 5: Claude Client (Team 1)

### Task 7: `claude_client.py` — tool use loop + prompt caching

**Files:**
- Create: `claude_client.py`
- Create: `tests/test_claude_client.py`

- [ ] **Stap 1: Schrijf failing tests**

```python
# tests/test_claude_client.py
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
```

- [ ] **Stap 2: Run tests — verifieer falen**

```bash
pytest tests/test_claude_client.py -v
```

Verwacht: `ImportError` (claude_client.py bestaat nog niet).

- [ ] **Stap 3: Implementeer `claude_client.py`**

```python
# claude_client.py
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
```

- [ ] **Stap 4: Run tests — verifieer slagen**

```bash
pytest tests/test_claude_client.py -v
```

Verwacht: alle 6 tests PASS.

- [ ] **Stap 5: Commit**

```bash
git add claude_client.py tests/test_claude_client.py
git commit -m "feat: claude client — tool use loop, bevestigingsdetectie, prompt caching"
```

---

## Chunk 6: Flask App + Auth (Team 3)

### Task 8: `auth.py` — mock login

**Files:**
- Create: `auth.py`
- Create: `tests/test_auth.py`

- [ ] **Stap 1: Schrijf failing tests**

```python
# tests/test_auth.py
import os, pytest
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from auth import MOCK_USERS, check_credentials, get_user

def test_check_credentials_valid():
    assert check_credentials("support", "support123") is True

def test_check_credentials_invalid():
    assert check_credentials("support", "verkeerd") is False

def test_check_credentials_unknown_user():
    assert check_credentials("onbekend", "wachtwoord") is False

def test_get_user_returns_user_info():
    user = get_user("developer")
    assert user is not None
    assert user["role"] == "developer"

def test_get_user_unknown_returns_none():
    assert get_user("onbekend") is None

def test_mock_users_has_three_users():
    assert len(MOCK_USERS) == 3
```

- [ ] **Stap 2: Run tests — verifieer falen**

```bash
pytest tests/test_auth.py -v
```

Verwacht: `ImportError`.

- [ ] **Stap 3: Implementeer `auth.py`**

```python
# auth.py
MOCK_USERS = {
    "support": {
        "password": "support123",
        "role": "support",
        "display_name": "Support Medewerker",
        "jira_account": "support.user"
    },
    "developer": {
        "password": "dev123",
        "role": "developer",
        "display_name": "Developer",
        "jira_account": "developer.user"
    },
    "manager": {
        "password": "manager123",
        "role": "manager",
        "display_name": "Manager",
        "jira_account": "manager.user"
    }
}

def check_credentials(username: str, password: str) -> bool:
    user = MOCK_USERS.get(username)
    return user is not None and user["password"] == password

def get_user(username: str) -> dict | None:
    return MOCK_USERS.get(username)
```

- [ ] **Stap 4: Run tests — verifieer slagen**

```bash
pytest tests/test_auth.py -v
```

Verwacht: alle 6 tests PASS.

- [ ] **Stap 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: auth — mock login met 3 gebruikers, tests groen"
```

### Task 9: `app.py` — Flask routes

**Files:**
- Create: `app.py`

- [ ] **Stap 1: Implementeer `app.py`**

```python
# app.py
import os, json, uuid
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, Response, stream_with_context
from dotenv import load_dotenv
from auth import check_credentials, get_user
from claude_client import ClaudeClient

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

claude = ClaudeClient()


@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", user=get_user(session["username"]))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if check_credentials(username, password):
            session["username"] = username
            session["messages"] = []
            return redirect(url_for("index"))
        error = "Ongeldige gebruikersnaam of wachtwoord"
    return render_template("chat.html", login_mode=True, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/chat", methods=["POST"])
def chat():
    if "username" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401

    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Leeg bericht"}), 400

    if "messages" not in session:
        session["messages"] = []

    session["messages"].append({"role": "user", "content": user_message})
    session.modified = True

    result = claude.chat(messages=session["messages"])

    if result["type"] == "confirmation_required":
        action_id = str(uuid.uuid4())
        session["pending_action"] = {
            "id": action_id,
            "tool_name": result["tool_name"],
            "tool_input": result["tool_input"],
            "messages_snapshot": list(session["messages"])
        }
        session.modified = True
        return jsonify({
            "type": "confirmation_required",
            "action_id": action_id,
            "message": result["message"]
        })

    session["messages"].append({"role": "assistant", "content": result["text"]})
    session.modified = True
    return jsonify({"type": "text", "message": result["text"]})


@app.route("/confirm", methods=["POST"])
def confirm():
    if "username" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401

    data = request.get_json()
    action_id = data.get("action_id")
    confirmed = data.get("confirmed", False)

    pending = session.get("pending_action")
    if not pending or pending["id"] != action_id:
        return jsonify({"error": "Geen geldige actie"}), 400

    session.pop("pending_action", None)
    session.modified = True

    if not confirmed:
        return jsonify({"type": "text", "message": "Actie geannuleerd."})

    result = claude.execute_confirmed_tool(
        tool_name=pending["tool_name"],
        tool_input=pending["tool_input"],
        messages=pending["messages_snapshot"]
    )
    session["messages"].append({"role": "assistant", "content": result.get("text", "Actie uitgevoerd.")})
    session.modified = True
    return jsonify({"type": "text", "message": result.get("text", "Actie uitgevoerd.")})


if __name__ == "__main__":
    app.run(debug=True)
```

- [ ] **Stap 2: Verifieer dat de app opstart**

```bash
python -c "from app import app; print('Flask app geladen')"
```

Verwacht: `Flask app geladen` zonder errors.

- [ ] **Stap 3: Commit**

```bash
git add app.py
git commit -m "feat: flask app — /chat, /confirm, /login, /logout routes"
```

---

## Chunk 7: Chat UI (Team 3)

### Task 10: `templates/chat.html` + `static/chat.js`

**Files:**
- Create: `templates/chat.html`
- Create: `static/chat.js`

- [ ] **Stap 1: Schrijf `templates/chat.html`**

```html
<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sterima AI Assistent</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; height: 100vh; display: flex; flex-direction: column; }
    header { background: #1a73e8; color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
    header h1 { font-size: 1.2rem; font-weight: 600; }
    header .user-info { font-size: 0.85rem; opacity: 0.9; }
    header a { color: white; text-decoration: none; margin-left: 16px; font-size: 0.85rem; opacity: 0.8; }
    .chat-container { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 12px; }
    .message { max-width: 75%; padding: 12px 16px; border-radius: 18px; line-height: 1.5; font-size: 0.95rem; }
    .message.user { background: #1a73e8; color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
    .message.assistant { background: white; color: #333; align-self: flex-start; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .message.assistant ul { margin: 8px 0 0 16px; }
    .message.assistant li { margin: 4px 0; }
    .confirmation-card { background: #fff8e1; border: 1px solid #f9a825; border-radius: 12px; padding: 16px; max-width: 75%; align-self: flex-start; }
    .confirmation-card p { margin-bottom: 12px; font-size: 0.95rem; }
    .confirmation-card .buttons { display: flex; gap: 8px; }
    .btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
    .btn-confirm { background: #1a73e8; color: white; }
    .btn-cancel { background: #e0e0e0; color: #333; }
    .btn:hover { opacity: 0.85; }
    .typing { align-self: flex-start; padding: 12px 16px; background: white; border-radius: 18px; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .typing span { display: inline-block; width: 8px; height: 8px; background: #999; border-radius: 50%; margin: 0 2px; animation: bounce 1.2s infinite; }
    .typing span:nth-child(2) { animation-delay: 0.2s; }
    .typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
    .input-area { padding: 16px 24px; background: white; border-top: 1px solid #e0e0e0; display: flex; gap: 12px; }
    #message-input { flex: 1; padding: 12px 16px; border: 1px solid #e0e0e0; border-radius: 24px; font-size: 0.95rem; outline: none; }
    #message-input:focus { border-color: #1a73e8; }
    #send-btn { padding: 12px 24px; background: #1a73e8; color: white; border: none; border-radius: 24px; cursor: pointer; font-size: 0.95rem; font-weight: 500; }
    #send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Login form */
    .login-wrapper { display: flex; justify-content: center; align-items: center; height: 100vh; }
    .login-card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 100%; max-width: 380px; }
    .login-card h2 { margin-bottom: 8px; color: #1a73e8; }
    .login-card p { color: #666; margin-bottom: 24px; font-size: 0.9rem; }
    .form-group { margin-bottom: 16px; }
    .form-group label { display: block; margin-bottom: 6px; font-size: 0.9rem; color: #555; }
    .form-group input { width: 100%; padding: 10px 14px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem; }
    .login-btn { width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; margin-top: 8px; }
    .error-msg { color: #d32f2f; font-size: 0.85rem; margin-top: 8px; }
  </style>
</head>
<body>

{% if login_mode %}
<div class="login-wrapper">
  <div class="login-card">
    <h2>Sterima AI</h2>
    <p>Log in om de AI assistent te gebruiken</p>
    <form method="POST" action="/login">
      <div class="form-group">
        <label>Gebruikersnaam</label>
        <input type="text" name="username" required autofocus>
      </div>
      <div class="form-group">
        <label>Wachtwoord</label>
        <input type="password" name="password" required>
      </div>
      <button type="submit" class="login-btn">Inloggen</button>
      {% if error %}<p class="error-msg">{{ error }}</p>{% endif %}
    </form>
  </div>
</div>

{% else %}
<header>
  <h1>Sterima AI Assistent</h1>
  <div class="user-info">
    {{ user.display_name }} ({{ user.role }})
    <a href="/logout">Uitloggen</a>
  </div>
</header>
<div class="chat-container" id="chat-container"></div>
<div class="input-area">
  <input type="text" id="message-input" placeholder="Typ je vraag... (bijv. 'Toon open tickets')" autocomplete="off">
  <button id="send-btn">Verstuur</button>
</div>
<script src="/static/chat.js"></script>
{% endif %}

</body>
</html>
```

- [ ] **Stap 2: Schrijf `static/chat.js`**

```javascript
// static/chat.js
const chatContainer = document.getElementById('chat-container');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');

function addMessage(text, role) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return div;
}

function showTyping() {
  const div = document.createElement('div');
  div.className = 'typing';
  div.id = 'typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function hideTyping() {
  const t = document.getElementById('typing-indicator');
  if (t) t.remove();
}

function showConfirmation(actionId, message) {
  const card = document.createElement('div');
  card.className = 'confirmation-card';
  card.id = `confirm-${actionId}`;
  card.innerHTML = `
    <p>${message}</p>
    <div class="buttons">
      <button class="btn btn-confirm" onclick="handleConfirm('${actionId}', true)">Ja, uitvoeren</button>
      <button class="btn btn-cancel" onclick="handleConfirm('${actionId}', false)">Annuleren</button>
    </div>
  `;
  chatContainer.appendChild(card);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function handleConfirm(actionId, confirmed) {
  const card = document.getElementById(`confirm-${actionId}`);
  if (card) card.remove();

  showTyping();
  sendBtn.disabled = true;

  try {
    const resp = await fetch('/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action_id: actionId, confirmed })
    });
    const data = await resp.json();
    hideTyping();
    addMessage(data.message, 'assistant');
  } catch (e) {
    hideTyping();
    addMessage('Er is een fout opgetreden.', 'assistant');
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  addMessage(text, 'user');
  input.value = '';
  sendBtn.disabled = true;
  showTyping();

  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await resp.json();
    hideTyping();

    if (data.type === 'confirmation_required') {
      showConfirmation(data.action_id, data.message);
    } else {
      addMessage(data.message, 'assistant');
    }
  } catch (e) {
    hideTyping();
    addMessage('Er is een fout opgetreden. Probeer opnieuw.', 'assistant');
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Welkomstbericht
addMessage('Hallo! Ik ben de Sterima AI assistent. Hoe kan ik je helpen?\n\nVoorbeelden:\n- "Toon open tickets"\n- "Maak een ticket voor login probleem"\n- "Zoek oplossing voor API timeout"', 'assistant');
```

- [ ] **Stap 3: Test de volledige app lokaal**

```bash
USE_MOCK_DATA=true python app.py
```

Open browser op `http://localhost:5000`. Log in met `support` / `support123`. Stuur het bericht "Toon open tickets".

Verwacht: chatbot antwoord met lijst van mock tickets.

- [ ] **Stap 4: Commit**

```bash
git add templates/chat.html static/chat.js
git commit -m "feat: chat UI — login, chat interface, bevestigingsdialoog"
```

---

## Chunk 8: End-to-End Integratie + Demo

### Task 11: Alle tests draaien + end-to-end validatie

- [ ] **Stap 1: Run alle unit tests**

```bash
pytest tests/ -v
```

Verwacht: alle tests PASS. Fix eventuele failures voor je verder gaat.

- [ ] **Stap 2: Test Scenario 1 — Jira Overzicht (mock)**

```bash
USE_MOCK_DATA=true python app.py
```

In browser: login → stuur "Toon alle open tickets"
Verwacht: lijst met 5 mock tickets, niet-toegewezen gemarkeerd.

- [ ] **Stap 3: Test Scenario 2 — Smart Assign (mock)**

Stuur: "Maak een ticket aan voor het probleem dat de login niet werkt op Safari, wijs de juiste persoon toe"
Verwacht: Claude maakt ticket aan, analyseert historiek, stelt Sophie Claes voor met confidence %, toont bevestigingsdialoog.

Klik "Ja, uitvoeren" → ticket aangemaakt in mock.

- [ ] **Stap 4: Test Scenario 3 — Oplossing Zoeken (mock)**

Stuur: "Hoe lossen we een API timeout op bij grote exports?"
Verwacht: Claude zoekt in Confluence + SharePoint mock, geeft concrete aanpak met bronnen en slaagkans %.

- [ ] **Stap 5: Test Scenario 4 — Auto-Resolve (mock)**

Stuur: "Los ticket PROJ-2 op"
Verwacht: Claude stelt assignee + oplossing + status "Done" voor. **Let op:** de tool use loop verwerkt één actie per beurt — auto-resolve kan 2–3 bevestigingsrondes vragen (assign → comment → status). Dit is normaal gedrag; de demo presenter weet dit van tevoren.

- [ ] **Stap 6: Test Scenario 5 — Kennisborging (mock)**

Stuur: "Schrijf een kennisartikel voor de oplossing van ticket PROJ-2"
Verwacht: Claude genereert artikel, toont bevestigingsdialoog, publiceert na Ja.

- [ ] **Stap 7: Schakel over naar live credentials**

Pas `.env` aan met echte waarden. Zet `USE_MOCK_DATA=false`. Hertest scenario 1 (Jira Overzicht) live.

- [ ] **Stap 8: Final commit + tag**

```bash
git add .
git commit -m "feat: end-to-end integratie — alle 5 scenario's gevalideerd"
git tag v1.0-demo
```

---

## Snelle Referentie — Opstarten

```bash
# Installeer
pip install -r requirements.txt
cp .env.example .env
# Vul .env in met credentials

# Mock modus (geen echte credentials nodig)
USE_MOCK_DATA=true python app.py

# Live modus
python app.py
```

Login: `support` / `support123` | `developer` / `dev123` | `manager` / `manager123`

URL: http://localhost:5000
