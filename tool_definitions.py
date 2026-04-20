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
