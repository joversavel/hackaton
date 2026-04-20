# Unified AI Workspace Assistant — Web Chatbot
**Design Spec · AI Hackathon 2026 · 2026-04-20**

---

## Doel

Een AI-gestuurde webchatbot (Flask) die interne en externe gebruikers in natuurlijke taal laat communiceren met Jira, Confluence en SharePoint. De bot kan tickets onderzoeken, smart assignen, oplossingen zoeken en kennisartikelen schrijven — aangedreven door Claude via tool use.

---

## Architectuur

```
Browser (chat UI)
    │  HTTP POST /chat  (of SSE stream)
    ▼
Flask App (Python 3.11+)
    │  sessie-gebaseerde authenticatie (mock login)
    │
    ├─► Claude API  (claude-sonnet-4-6)
    │       │  tool_use beslissing
    │       ▼
    │   Python Tool Functies
    │       │
    │       ├── Atlassian REST API
    │       │     Jira:       get_open_tickets, get_resolved_tickets, create_ticket,
    │       │                 assign_ticket, add_comment, update_status
    │       │     Confluence: search_confluence, create_confluence_page
    │       │
    │       └── Microsoft Graph API
    │             SharePoint: search_sharepoint, get_document, list_site_pages
    │
    └─► JSON / SSE response → chat UI
```

**Bevestigingsflow:** Elke schrijfoperatie (assign, comment toevoegen, status update, nieuwe pagina) toont eerst een bevestigingsstap in de chat. Claude voert geen mutaties uit zonder expliciete gebruikersbevestiging.

**Technisch protocol bevestiging:**
1. Claude geeft een `tool_use` response terug met `"requires_confirmation": true` in de tool input
2. Flask slaat de pending actie op in de server-side sessie (`session["pending_action"]`)
3. Frontend toont een bevestigingsdialoog met Ja/Nee knoppen
4. Gebruiker klikt Ja → frontend stuurt `POST /confirm` met `action_id`
5. Flask haalt pending actie op uit sessie, voert de tool call alsnog uit, wist sessie-entry
6. SSE en bevestiging zijn gescheiden flows: SSE stream eindigt na het tonen van de bevestigingsvraag; `/confirm` is een gewone POST

---

## Team Verdeling (6 personen, 3 teams van 2)

| Team | Verantwoordelijkheid |
|---|---|
| **Team 1 — AI & Claude** | Claude API client, tool use definitie, prompt engineering, Smart Assign logica, kennisartikel generatie, model keuze (sonnet vs opus) |
| **Team 2 — Integraties** | Atlassian REST API (Jira + Confluence), Microsoft Graph API (SharePoint), alle Python tool functies, bevestigingsflow |
| **Team 3 — Flask UI & Auth** | Flask app structuur, chat interface (HTML/CSS/JS), sessie login met mock gebruikers, streaming responses, Azure App Registration voor Graph API |

**Gedeeld:** GitHub repo + feature branches per team, demo data voorbereiding (Team 1 + 2), dry run demo (iedereen).

---

## De 5 Demo Scenario's

### Scenario 1 — Jira Overzicht
- Gebruiker: "Toon me de open tickets"
- Bot roept `get_open_tickets()` aan
- Toont lijst met tickets; niet-toegewezen gemarkeerd
- **Doel:** bewijzen dat de bot live Jira data leest

### Scenario 2 — Ticket Aanmaken + Smart Assign
- Gebruiker beschrijft een probleem in gewone taal
- Bot roept `create_ticket()` aan, analyseert historiek via `get_resolved_tickets()` (JQL: `status=Done`)
- Claude selecteert beste kandidaat met confidence % en uitleg
- Na bevestiging: `assign_ticket()` uitgevoerd
- **Output:** ticket zichtbaar in Jira met assignee en oplossingsvoorstel als comment

### Scenario 3 — Oplossing Zoeken
- Gebruiker: "Hoe lossen we [probleem] op?"
- Bot roept `search_confluence()` en `search_sharepoint()` aan
- Claude vergelijkt resultaten met tickethistoriek
- **Output:** concrete aanpak met slaagkans %, bronnen vermeld

### Scenario 4 — Auto-Resolve (één commando)
- Gebruiker: "Los ticket PROJ-42 op"
- Bot analyseert ticket, stelt assignee + oplossing voor
- Na bevestiging: `assign_ticket()` + `add_comment()` + `update_status()` in één flow
- **Output:** ticket volledig verwerkt vanuit één chat bericht

### Scenario 5 — Kennisborging
- Gebruiker: "Schrijf een kennisartikel voor de oplossing van PROJ-42"
- Claude genereert gestructureerd artikel op basis van ticket + comments
- Na bevestiging: `create_confluence_page()` gepubliceerd
- **Output:** nieuwe Confluence pagina live beschikbaar

---

## Technische Vereisten

### Backend
| Component | Technologie |
|---|---|
| Webframework | Flask (Python 3.11+) |
| AI Engine | Anthropic SDK — `claude-sonnet-4-6` (snelheid) / `claude-opus-4-7` (complexe redenering) |
| Atlassian integratie | Atlassian REST API v3 (Jira Cloud + Confluence Cloud) |
| SharePoint integratie | Microsoft Graph API v1.0 |
| Authenticatie gebruiker | Flask-Session + hardcoded mock gebruikers |
| Authenticatie Graph API | Azure App Registration (client credentials flow) |
| Configuratie | `python-dotenv` — `.env` bestand (nooit in git) |
| Streaming | `text/event-stream` (SSE) voor live typing effect |

### Python Dependencies (`requirements.txt`)
```
flask
flask-session
anthropic
requests
python-dotenv
```

### Credentials (`.env`)
```
ANTHROPIC_API_KEY=
JIRA_BASE_URL=          # https://yourcompany.atlassian.net
JIRA_EMAIL=
JIRA_API_TOKEN=
CONFLUENCE_BASE_URL=    # https://yourcompany.atlassian.net/wiki
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
SHAREPOINT_SITE_ID=
FLASK_SECRET_KEY=
```

### Frontend
- Vanilla HTML/CSS/JavaScript (geen framework)
- Chat UI: berichtgeschiedenis, typing indicator, bevestigingsdialoog voor schrijfacties
- Responsive layout, werkend op desktop browser

### Demo Omgeving
- Jira project met 10–15 testtickets (variatie in types, assignees, statussen, historiek); fallback: `fixtures/jira_mock.json` als Atlassian auth faalt — **eigenaar: Team 2**
- Confluence space met 5+ kennisartikelen als kennisbank; fallback: `fixtures/confluence_mock.json` — **eigenaar: Team 2**
- SharePoint site met testdocumenten; fallback: `fixtures/sharepoint_mock.json` als Graph API auth faalt — **eigenaar: Team 3**
- 3 mock gebruikers voor login (bijv. support, developer, manager) — **eigenaar: Team 3**

---

## Projectstructuur

```
hackaton/
├── app.py                  # Flask entry point, routes
├── claude_client.py        # Claude API client + tool use loop
├── tools/
│   ├── jira_tools.py       # Jira REST API functies
│   ├── confluence_tools.py # Confluence REST API functies
│   └── sharepoint_tools.py # Microsoft Graph API functies
├── templates/
│   └── chat.html           # Chat UI
├── static/
│   └── chat.js             # Frontend JS
├── auth.py                 # Mock login / sessie beheer
├── requirements.txt
├── .env.example            # Template zonder echte waarden
└── .gitignore              # .env uitsluiten
```

---

## Tool Definities (Claude tool_use schema)

Team 1 en Team 2 werken tegen deze gedeelde interface. Parameters zijn bindend — wijzig alleen in overleg.

```python
TOOLS = [
  {"name": "get_open_tickets",     "description": "Haal open Jira tickets op",                  "input_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": []}},
  {"name": "get_resolved_tickets", "description": "Haal opgeloste Jira tickets op voor historiek","input_schema": {"type": "object", "properties": {"project": {"type": "string"}, "max_results": {"type": "integer"}}, "required": []}},
  {"name": "create_ticket",        "description": "Maak een nieuw Jira ticket aan",              "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}, "description": {"type": "string"}, "project": {"type": "string"}}, "required": ["summary", "project"]}},
  {"name": "assign_ticket",        "description": "Wijs een ticket toe — vereist bevestiging",   "input_schema": {"type": "object", "properties": {"ticket_id": {"type": "string"}, "assignee": {"type": "string"}, "requires_confirmation": {"type": "boolean"}}, "required": ["ticket_id", "assignee"]}},
  {"name": "add_comment",          "description": "Voeg comment toe aan Jira ticket — vereist bevestiging","input_schema": {"type": "object", "properties": {"ticket_id": {"type": "string"}, "comment": {"type": "string"}, "requires_confirmation": {"type": "boolean"}}, "required": ["ticket_id", "comment"]}},
  {"name": "update_status",        "description": "Update Jira ticket status — vereist bevestiging","input_schema": {"type": "object", "properties": {"ticket_id": {"type": "string"}, "status": {"type": "string"}, "requires_confirmation": {"type": "boolean"}}, "required": ["ticket_id", "status"]}},
  {"name": "search_confluence",    "description": "Zoek in Confluence kennisbank",               "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
  {"name": "create_confluence_page","description": "Maak Confluence kennisartikel — vereist bevestiging","input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "space_key": {"type": "string"}, "requires_confirmation": {"type": "boolean"}}, "required": ["title", "content", "space_key"]}},
  {"name": "search_sharepoint",    "description": "Zoek documenten in SharePoint",               "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]
```

---

## Prompt Caching

Claude API ondersteunt prompt caching. De systeemprompt (met tool definities en context) wordt gecached om latentie en kosten te verlagen bij herhaalde calls. Implementatie in `claude_client.py` via `cache_control: {"type": "ephemeral"}` op de systeemprompt.

---

## Smart Assign Logica

Claude analyseert per nieuw ticket:
1. **Inhoud** — component, fouttype, trefwoorden
2. **Historiek** — wie loste gelijkaardige tickets eerder op? (`get_resolved_tickets` via JQL `status=Done`)
3. **Resultaat** — beste kandidaat + confidence %, alternatief, kant-en-klaar oplossingsvoorstel

Output altijd met uitleg ("Jan heeft 3 van de 4 laatste database-gerelateerde tickets opgelost in gemiddeld 2u").

---

## Hackathon Tijdlijn (10 uur)

| Uur | Activiteit |
|---|---|
| 1–2 | Setup: repo, `.env`, credentials, API-toegang testen per team |
| 3–5 | Core bouwen parallel: Team 1 → Claude tools, Team 2 → API functies, Team 3 → Flask UI |
| 6–7 | End-to-end koppeling: Flask ↔ Claude ↔ Jira/Confluence/SharePoint |
| 8 | Scenario's testen + debuggen |
| 9 | Dry run volledige demo flow |
| 10 | Buffer + presentatie voorbereiding |

---

## Definition of Done

- [ ] **Scenario 1:** Bot toont live Jira-overzicht met niet-toegewezen tickets gemarkeerd
- [ ] **Scenario 2:** Nieuw ticket aangemaakt + Smart Assign met confidence % zichtbaar in chat
- [ ] **Scenario 3:** Bot geeft oplossingsvoorstel met slaagkans op basis van Confluence + SharePoint
- [ ] **Scenario 4:** Auto-Resolve voltooit ticket end-to-end na één bevestiging
- [ ] **Scenario 5:** Kennisartikel gepubliceerd in Confluence vanuit chat
- [ ] Mock login werkend met 3 gebruikers
- [ ] Geen credentials in git
- [ ] Bevestigingsstap aanwezig voor alle schrijfacties
