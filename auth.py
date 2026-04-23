import os, re
from pathlib import Path


_AUTHORIZED_USERS_CACHE: list[dict] | None = None

def _load_authorized_users() -> list[dict]:
    global _AUTHORIZED_USERS_CACHE
    if _AUTHORIZED_USERS_CACHE is not None:
        return _AUTHORIZED_USERS_CACHE
    path = Path(__file__).parent / "gebruikers.md"
    users = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(.+?)\s*\|\s*([\w.\-+]+@[\w.\-]+)\s*\|\s*(.+?)\s*\|", line)
        if m:
            users.append({
                "display_name": m.group(1),
                "email": m.group(2).lower(),
                "locatie": m.group(3).strip(),
            })
    _AUTHORIZED_USERS_CACHE = users
    return users


def _nt_username() -> str:
    return os.environ.get("USERNAME", "").lower().replace(" ", ".")

def _nt_display_name() -> str:
    raw = os.environ.get("USERNAME", "")
    if not raw:
        return "Onbekende gebruiker"
    return " ".join(part.capitalize() for part in raw.replace(".", " ").split())


DEMO_BEPERKT_USERS = [
    {"display_name": "Jan Medewerker", "email": "jan.medewerker@sterima.be", "role": "beperkt"},
]

def get_all_users() -> list[dict]:
    authorized = _load_authorized_users()
    result = [{"display_name": u["display_name"], "email": u["email"], "locatie": u.get("locatie", ""), "role": "admin"} for u in authorized]
    for u in DEMO_BEPERKT_USERS:
        if not any(x["email"] == u["email"] for x in result):
            result.append(u)
    nt = _nt_username()
    domain = os.getenv("AD_DOMAIN", "sterima.be")
    nt_email = f"{nt}@{domain}"
    if not any(u["email"] == nt_email for u in result):
        result.append({"display_name": nt, "email": nt_email, "locatie": "", "role": "beperkt"})
    return result

def get_current_user() -> dict:
    nt_user = _nt_username()
    if not nt_user:
        return {
            "display_name": "Anoniem",
            "email": "anoniem@sterima.be",
            "locatie": "",
            "role": "beperkt",
        }
    authorized = _load_authorized_users()
    match = next((u for u in authorized if u["email"].split("@")[0] == nt_user), None)
    if match:
        return {
            "display_name": match["display_name"],
            "email": match["email"],
            "locatie": match.get("locatie", ""),
            "role": "admin",
        }
    domain = os.getenv("AD_DOMAIN", "sterima.be")
    return {
        "display_name": _nt_display_name(),
        "email": f"{nt_user}@{domain}",
        "locatie": "",
        "role": "beperkt",
    }
