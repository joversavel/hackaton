import os, json, uuid, logging, traceback, re
from pathlib import Path
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, Response
from dotenv import load_dotenv
from auth import get_current_user, get_all_users
from claude_client import ClaudeClient, PROMPTS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env", override=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

# Server-side opslag: berichten en pending actions buiten de cookie
_message_store: dict[str, list] = {}
_pending_store: dict[str, dict] = {}

def _sid() -> str:
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

def _get_messages() -> list:
    return _message_store.get(_sid(), [])

def _set_messages(msgs: list):
    _message_store[_sid()] = msgs

def _get_pending() -> dict | None:
    return _pending_store.get(_sid())

def _set_pending(action: dict | None):
    sid = _sid()
    if action is None:
        _pending_store.pop(sid, None)
    else:
        _pending_store[sid] = action

claude = ClaudeClient()
log.debug("API key loaded: %s", bool(os.getenv("ANTHROPIC_API_KEY")))


@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    jira_base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    return render_template("chat.html", user=session["user"], all_users=get_all_users(), jira_base_url=jira_base)


@app.route("/login")
def login():
    user = get_current_user()
    session.permanent = False
    session["user"] = user
    _set_messages([])
    _set_pending(None)
    session.modified = True
    return redirect(url_for("index"))


@app.route("/do-login", methods=["POST"])
def do_login():
    email = request.get_json().get("email", "").lower()
    user = next((u for u in get_all_users() if u["email"] == email), None)
    if not user:
        return jsonify({"ok": False}), 404
    session.permanent = False
    session["user"] = user
    _set_messages([])
    _set_pending(None)
    session.modified = True
    return jsonify({"ok": True})


@app.route("/switch-user", methods=["POST"])
def switch_user():
    email = request.get_json().get("email", "").lower()
    user = next((u for u in get_all_users() if u["email"] == email), None)
    if not user:
        return jsonify({"ok": False}), 404
    session["user"] = user
    _set_messages([])
    _set_pending(None)
    session.modified = True
    return jsonify({"ok": True})


@app.route("/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401

    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Leeg bericht"}), 400

    messages = _get_messages()
    messages.append({"role": "user", "content": user_message})
    _set_messages(messages)

    try:
        user_role = session["user"].get("role", "beperkt")
        log.debug("USER: %s ROLE: %s", session["user"].get("email"), user_role)
        result = claude.chat(messages=messages, role=user_role, user=session["user"])
    except Exception as e:
        log.error("Claude chat error: %s\n%s", e, traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    if result["type"] == "confirmation_required":
        action_id = str(uuid.uuid4())
        _set_pending({
            "id": action_id,
            "tool_name": result["tool_name"],
            "tool_id": result["tool_id"],
            "tool_input": result["tool_input"],
            "assistant_content": result["assistant_content"],
            "messages_at_confirmation": result["messages_at_confirmation"],
        })
        return jsonify({
            "type": "confirmation_required",
            "action_id": action_id,
            "message": result["message"]
        })

    messages.append({"role": "assistant", "content": result["text"]})
    _set_messages(messages)
    return jsonify({"type": "text", "message": result["text"]})


@app.route("/confirm", methods=["POST"])
def confirm():
    if "user" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401

    data = request.get_json()
    action_id = data.get("action_id")
    confirmed = data.get("confirmed", False)

    pending = _get_pending()
    if not pending or pending["id"] != action_id:
        return jsonify({"error": "Geen geldige actie"}), 400

    _set_pending(None)

    if not confirmed:
        return jsonify({"type": "text", "message": "Actie geannuleerd."})

    try:
        result = claude.execute_confirmed_tool(
            tool_name=pending["tool_name"],
            tool_id=pending["tool_id"],
            tool_input=pending["tool_input"],
            messages_at_confirmation=pending["messages_at_confirmation"],
            assistant_content=pending["assistant_content"],
            role=session["user"].get("role", "beperkt"),
            user=session["user"]
        )
    except Exception as e:
        log.error("execute_confirmed_tool error: %s\n%s", e, traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    log.info("confirm result type=%s for tool=%s", result.get("type"), pending["tool_name"])

    if result.get("type") == "confirmation_required":
        new_action_id = str(uuid.uuid4())
        _set_pending({
            "id": new_action_id,
            "tool_name": result["tool_name"],
            "tool_id": result["tool_id"],
            "tool_input": result["tool_input"],
            "assistant_content": result["assistant_content"],
            "messages_at_confirmation": result["messages_at_confirmation"],
        })
        if pending["tool_name"] == "create_ticket":
            _set_messages([])
        return jsonify({
            "type": "confirmation_required",
            "action_id": new_action_id,
            "message": result["message"]
        })

    response_text = result.get("text") or "Actie uitgevoerd."
    log.info("confirm response for %s: %s", pending["tool_name"], response_text[:200])

    if pending["tool_name"] == "create_ticket":
        _set_messages([])
    else:
        msgs = _get_messages()
        msgs.append({"role": "assistant", "content": response_text})
        _set_messages(msgs)
    return jsonify({"type": "text", "message": response_text})


@app.route("/admin")
def admin():
    if "user" not in session or session["user"].get("role") != "admin":
        return redirect(url_for("index"))
    return render_template("admin.html", user=session["user"], all_users=get_all_users(), prompts=PROMPTS)


@app.route("/save-prompts", methods=["POST"])
def save_prompts():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403

    data = request.get_json()
    admin_prompt = data.get("admin", "").strip()
    beperkt_prompt = data.get("beperkt", "").strip()

    if not admin_prompt or not beperkt_prompt:
        return jsonify({"ok": False, "error": "Lege prompt niet toegestaan"}), 400

    prompts_path = Path(__file__).parent / "prompts.json"
    try:
        prompts_path.write_text(
            json.dumps({"admin": admin_prompt, "beperkt": beperkt_prompt}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        # Reload into the live module-level dict so changes take effect immediately
        import claude_client
        claude_client.PROMPTS["admin"] = admin_prompt
        claude_client.PROMPTS["beperkt"] = beperkt_prompt
        # Update the local reference imported at startup
        PROMPTS["admin"] = admin_prompt
        PROMPTS["beperkt"] = beperkt_prompt
    except Exception as e:
        log.error("save-prompts error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True})


def _algemene_regels_path() -> Path:
    return Path(__file__).parent / "docs" / "algemene_regels.md"


@app.route("/api/algemene_regels")
def api_algemene_regels():
    if "user" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401
    path = _algemene_regels_path()
    text = path.read_text(encoding="utf-8").strip() if path.exists() else ""
    return text, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/admin/algemene_regels/save", methods=["POST"])
def save_algemene_regels():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Inhoud mag niet leeg zijn"}), 400
    _algemene_regels_path().write_text(content, encoding="utf-8")
    import claude_client
    claude_client.invalidate_cache("algemene_regels", content)
    return jsonify({"ok": True})


def _selectie_path() -> Path:
    return Path(__file__).parent / "docs" / "selectie.md"


@app.route("/api/selectie")
def api_selectie():
    if "user" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401
    path = _selectie_path()
    text = path.read_text(encoding="utf-8").strip() if path.exists() else "Voor welke afdeling wil je een ticket aanmaken?"
    return text, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/admin/selectie/save", methods=["POST"])
def save_selectie():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Inhoud mag niet leeg zijn"}), 400
    _selectie_path().write_text(content, encoding="utf-8")
    import claude_client
    claude_client.invalidate_cache("selectie", content)
    return jsonify({"ok": True})


def _security_path() -> Path:
    return Path(__file__).parent / "docs" / "security.md"


@app.route("/api/security")
def api_security():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"error": "Niet toegestaan"}), 403
    path = _security_path()
    text = path.read_text(encoding="utf-8").strip() if path.exists() else ""
    return text, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/admin/security/save", methods=["POST"])
def save_security():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Inhoud mag niet leeg zijn"}), 400
    _security_path().write_text(content, encoding="utf-8")
    import claude_client
    claude_client.invalidate_cache("security", content)
    return jsonify({"ok": True})


def _departments_dir() -> Path:
    return Path(__file__).parent / "docs" / "departments"


def _kb_dir() -> Path:
    return Path(__file__).parent / "docs" / "KB"


def _kb_slug_valid(slug: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_\-]+$', slug))


@app.route("/admin/kb")
def admin_kb():
    if "user" not in session or session["user"].get("role") != "admin":
        return redirect(url_for("index"))
    return render_template("admin_kb.html", user=session["user"])


@app.route("/api/kb")
def api_kb_list():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"error": "Niet toegestaan"}), 403
    d = _kb_dir()
    result = []
    if d.exists():
        for f in sorted(d.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            title = next((l.lstrip("# ").strip() for l in lines if l.startswith("# ")), f.stem)
            systeem = ""
            for l in lines:
                if l.startswith("**Systeem:**"):
                    systeem = l.replace("**Systeem:**", "").strip()
                    break
            result.append({
                "slug": f.stem,
                "title": title,
                "systeem": systeem,
                "lines": len(lines),
            })
    return jsonify(result)


@app.route("/api/kb/<slug>")
def api_kb_file(slug):
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"error": "Niet toegestaan"}), 403
    if not _kb_slug_valid(slug):
        return jsonify({"error": "Ongeldige bestandsnaam"}), 400
    path = _kb_dir() / f"{slug}.md"
    if not path.exists():
        return jsonify({"error": "Niet gevonden"}), 404
    return path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/admin/kb/save", methods=["POST"])
def save_kb():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    data = request.get_json()
    slug = (data.get("slug") or "").strip()
    content = (data.get("content") or "").strip()
    if not _kb_slug_valid(slug):
        return jsonify({"ok": False, "error": "Ongeldige bestandsnaam (a-z, A-Z, 0-9, - en _)"}), 400
    if not content:
        return jsonify({"ok": False, "error": "Inhoud mag niet leeg zijn"}), 400
    d = _kb_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.md").write_text(content, encoding="utf-8")
    import claude_client
    claude_client.reload_kb_cache()
    return jsonify({"ok": True})


@app.route("/admin/kb/upload", methods=["POST"])
def upload_kb():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"ok": False, "error": "Geen bestand"}), 400
    filename = Path(uploaded.filename).name
    if not filename.lower().endswith(".md"):
        return jsonify({"ok": False, "error": "Alleen .md bestanden toegestaan"}), 400
    slug = filename[:-3]
    if not _kb_slug_valid(slug):
        return jsonify({"ok": False, "error": "Ongeldige bestandsnaam"}), 400
    d = _kb_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_bytes(uploaded.read())
    import claude_client
    claude_client.reload_kb_cache()
    return jsonify({"ok": True, "slug": slug})


@app.route("/admin/kb/<slug>", methods=["DELETE"])
def delete_kb(slug):
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    if not _kb_slug_valid(slug):
        return jsonify({"ok": False, "error": "Ongeldige bestandsnaam"}), 400
    path = _kb_dir() / f"{slug}.md"
    if not path.exists():
        return jsonify({"ok": False, "error": "Niet gevonden"}), 404
    path.unlink()
    import claude_client
    claude_client.reload_kb_cache()
    return jsonify({"ok": True})


@app.route("/api/departments")
def api_departments():
    if "user" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401
    d = _departments_dir()
    result = []
    if d.exists():
        for f in sorted(d.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            heading = next(
                (line.lstrip("# ").strip() for line in content.splitlines() if line.startswith("# ")),
                f.stem.upper()
            )
            result.append({"slug": f.stem, "name": heading})
    return jsonify(result)


@app.route("/api/departments/<slug>")
def api_department(slug):
    if "user" not in session:
        return jsonify({"error": "Niet ingelogd"}), 401
    if not re.match(r'^[a-z0-9_]+$', slug):
        return jsonify({"error": "Ongeldige slug"}), 400
    path = _departments_dir() / f"{slug}.md"
    if not path.exists():
        return jsonify({"error": "Niet gevonden"}), 404
    return path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/admin/departments/save", methods=["POST"])
def save_department():
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    data = request.get_json()
    slug = (data.get("slug") or "").strip().lower()
    content = (data.get("content") or "").strip()
    if not re.match(r'^[a-z0-9_]+$', slug):
        return jsonify({"ok": False, "error": "Ongeldige naam (alleen a-z, 0-9, _)"}), 400
    if not content:
        return jsonify({"ok": False, "error": "Inhoud mag niet leeg zijn"}), 400
    d = _departments_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.md").write_text(content, encoding="utf-8")
    return jsonify({"ok": True})


@app.route("/admin/departments/<slug>", methods=["DELETE"])
def delete_department(slug):
    if "user" not in session or session["user"].get("role") != "admin":
        return jsonify({"ok": False, "error": "Niet toegestaan"}), 403
    if not re.match(r'^[a-z0-9_]+$', slug):
        return jsonify({"ok": False, "error": "Ongeldige slug"}), 400
    path = _departments_dir() / f"{slug}.md"
    if not path.exists():
        return jsonify({"ok": False, "error": "Niet gevonden"}), 404
    path.unlink()
    return jsonify({"ok": True})


@app.route("/api/history")
def api_history():
    if "user" not in session:
        return jsonify([])
    msgs = [m for m in _get_messages() if isinstance(m.get("content"), str)]
    return jsonify([{"role": m["role"], "content": m["content"]} for m in msgs])


@app.route("/new-chat", methods=["POST"])
def new_chat():
    if "user" not in session:
        return jsonify({"ok": False}), 401
    _set_messages([])
    _set_pending(None)
    return jsonify({"ok": True})


@app.route("/logout")
def logout():
    sid = session.get("sid")
    if sid:
        _message_store.pop(sid, None)
        _pending_store.pop(sid, None)
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
