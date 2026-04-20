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
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
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
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
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
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
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
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return {"success": True, "ticket_id": ticket_id, "assignee": assignee}
    resp = requests.put(
        f"{JIRA_BASE}/rest/api/3/issue/{ticket_id}/assignee",
        headers=HEADERS, auth=AUTH,
        json={"accountId": assignee}
    )
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id, "assignee": assignee}

def add_comment(ticket_id: str, comment: str, requires_confirmation: bool = True) -> dict:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return {"success": True, "ticket_id": ticket_id}
    payload = {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}}
    resp = requests.post(f"{JIRA_BASE}/rest/api/3/issue/{ticket_id}/comment", headers=HEADERS, auth=AUTH, json=payload)
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id}

def update_status(ticket_id: str, status: str, requires_confirmation: bool = True) -> dict:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
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
