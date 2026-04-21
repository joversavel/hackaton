import json, os, requests
from pathlib import Path


def _adf_to_text(node) -> str:
    if not node or not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = [_adf_to_text(c) for c in node.get("content", [])]
    return " ".join(p for p in parts if p)

def _mock_data():
    path = Path(__file__).parent.parent / "fixtures" / "jira_mock.json"
    return json.loads(path.read_text())

def _jira_search(jql: str, fields: str, max_results: int = 10) -> list:
    resp = requests.post(
        f"{_jira_base()}/rest/api/3/search/jql",
        headers=_headers(), auth=_auth(),
        json={"jql": jql, "maxResults": max_results, "fields": fields.split(",")}
    )
    resp.raise_for_status()
    return resp.json().get("issues", [])

REQUEST_TYPE_MAP = {
    "infrastructure/hardware problem": "34",
    "application problem": "39",
    "request new hardware": "37",
    "request access": "38",
    "security/phished/mimecast issue": "60",
    "ai questions": "129",
    "domain transfer": "61",
    "new employee": "33",
    "leaving user form": "59",
    "request smartphone": "65",
    "wms or dynaman problem": "36",
    "request a change": "62",
    "emailed request": "7",
    "hardware problem": "40",
}

def _jira_base():
    return os.getenv("JIRA_BASE_URL", "")

def _auth():
    return (os.getenv("JIRA_EMAIL", ""), os.getenv("JIRA_API_TOKEN", ""))

def _headers():
    return {"Accept": "application/json", "Content-Type": "application/json"}

def get_ticket(ticket_id: str) -> dict:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return {"id": ticket_id, "summary": "Mock ticket", "status": "Open", "description": "Mock beschrijving"}
    resp = requests.get(
        f"{_jira_base()}/rest/api/3/issue/{ticket_id}",
        headers=_headers(), auth=_auth(),
        params={"fields": "summary,status,assignee,reporter,description,comment,priority,created,updated"},
        verify=False
    )
    if not resp.ok:
        return {"error": f"Ticket {ticket_id} niet gevonden ({resp.status_code})"}
    f = resp.json()["fields"]
    comments = f.get("comment", {}).get("comments", [])
    return {
        "id": ticket_id,
        "summary": f["summary"],
        "status": f["status"]["name"],
        "priority": (f.get("priority") or {}).get("name"),
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "reporter": (f.get("reporter") or {}).get("displayName"),
        "description": _adf_to_text(f.get("description") or {})[:500],
        "comments": [
            {"author": c["author"]["displayName"], "body": _adf_to_text(c["body"])[:200]}
            for c in comments[-3:]
        ],
        "created": f.get("created", "")[:10],
        "updated": f.get("updated", "")[:10],
    }

def get_my_tickets(email: str, project: str = None) -> list:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return _mock_data()["open_tickets"]
    jql = f'(assignee = "{email}" OR reporter = "{email}") AND status != Done ORDER BY created DESC'
    if project:
        jql = f'project={project} AND {jql}'
    issues = _jira_search(jql, "summary,status,assignee,reporter,description")
    return [
        {
            "id": i["key"],
            "summary": i["fields"]["summary"],
            "status": i["fields"]["status"]["name"],
            "assignee": (i["fields"]["assignee"] or {}).get("displayName"),
            "reporter": (i["fields"].get("reporter") or {}).get("displayName"),
            "description": _adf_to_text(i["fields"].get("description") or {})[:150]
        }
        for i in issues
    ]

def get_open_tickets(project: str = None) -> list:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return _mock_data()["open_tickets"]
    jql = "status != Done ORDER BY created DESC"
    if project:
        jql = f"project={project} AND {jql}"
    issues = _jira_search(jql, "summary,status,assignee,description")
    return [
        {
            "id": i["key"],
            "summary": i["fields"]["summary"],
            "status": i["fields"]["status"]["name"],
            "assignee": (i["fields"]["assignee"] or {}).get("displayName"),
            "description": _adf_to_text(i["fields"].get("description") or {})[:150]
        }
        for i in issues
    ]

def search_jira(query: str, project: str = None, max_results: int = 10) -> list:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        tickets = _mock_data()["resolved_tickets"]
        q = query.lower()
        return [t for t in tickets if q in t.get("summary", "").lower() or q in t.get("resolution", "").lower()] or tickets[:2]
    jql = f'text ~ "{query}" AND status=Done ORDER BY resolutiondate DESC'
    if project:
        jql = f'project={project} AND {jql}'
    issues = _jira_search(jql, "summary,status,assignee,comment,resolutiondate", max_results)
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

def get_resolved_tickets(project: str = None, max_results: int = 20) -> list:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return _mock_data()["resolved_tickets"]
    jql = "status=Done ORDER BY resolutiondate DESC"
    if project:
        jql = f"project={project} AND {jql}"
    issues = _jira_search(jql, "summary,status,assignee,comment,resolutiondate,resolution", max_results)
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

def create_ticket(summary: str, project: str, description: str = "", request_type: str = "", requires_confirmation: bool = True) -> dict:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return {"id": "PROJ-NEW", "summary": summary, "status": "Open", "request_type": request_type}

    service_desk_id = os.getenv("JIRA_SERVICE_DESK_ID", "")
    request_type_id = REQUEST_TYPE_MAP.get(request_type.lower().strip()) if request_type else None

    if service_desk_id and request_type_id:
        payload = {
            "serviceDeskId": service_desk_id,
            "requestTypeId": request_type_id,
            "requestFieldValues": {
                "summary": summary,
                "description": description,
            }
        }
        resp = requests.post(
            f"{_jira_base()}/rest/servicedeskapi/request",
            headers=_headers(), auth=_auth(), json=payload, verify=False
        )
        if resp.ok:
            data = resp.json()
            return {"id": data["issueKey"], "summary": summary, "status": "Open", "request_type": request_type}
        return {"success": False, "error": resp.json()}

    # Fallback: regular API without request type
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": summary,
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]},
            "issuetype": {"name": "[System] Service request"}
        }
    }
    resp = requests.post(f"{_jira_base()}/rest/api/3/issue", headers=_headers(), auth=_auth(), json=payload, verify=False)
    if not resp.ok:
        return {"success": False, "error": resp.json()}
    data = resp.json()
    return {"id": data["key"], "summary": summary, "status": "Open"}

def assign_ticket(ticket_id: str, assignee: str, requires_confirmation: bool = True) -> dict:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return {"success": True, "ticket_id": ticket_id, "assignee": assignee}
    resp = requests.put(
        f"{_jira_base()}/rest/api/3/issue/{ticket_id}/assignee",
        headers=_headers(), auth=_auth(),
        json={"accountId": assignee}
    )
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id, "assignee": assignee}

def add_comment(ticket_id: str, comment: str, requires_confirmation: bool = True) -> dict:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return {"success": True, "ticket_id": ticket_id}
    payload = {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}}
    resp = requests.post(f"{_jira_base()}/rest/api/3/issue/{ticket_id}/comment", headers=_headers(), auth=_auth(), json=payload)
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id}

def update_status(ticket_id: str, status: str, requires_confirmation: bool = True) -> dict:
    if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
        return {"success": True, "ticket_id": ticket_id, "status": status}
    transitions_resp = requests.get(f"{_jira_base()}/rest/api/3/issue/{ticket_id}/transitions", headers=_headers(), auth=_auth())
    transitions_resp.raise_for_status()
    transitions = transitions_resp.json().get("transitions", [])
    match = next((t for t in transitions if t["name"].lower() == status.lower()), None)
    if not match:
        available = [t["name"] for t in transitions]
        return {"success": False, "error": f"Status '{status}' niet gevonden. Beschikbaar: {available}"}
    resp = requests.post(
        f"{_jira_base()}/rest/api/3/issue/{ticket_id}/transitions",
        headers=_headers(), auth=_auth(),
        json={"transition": {"id": match["id"]}}
    )
    resp.raise_for_status()
    return {"success": True, "ticket_id": ticket_id, "status": status}
