# Ticket Wizard per Department — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guided inline ticket creation wizard that walks users through department-specific questions before calling Claude to create the Jira ticket.

**Architecture:** Department scripts live as markdown files in `docs/departments/`. The frontend drives the wizard (no API call per step), collecting all answers before sending one final request to `/chat` with `wizard_completed: true`. The backend intercepts any `create_ticket` call that arrives without this flag and returns `{"type": "start_wizard"}` instead.

**Tech Stack:** Flask (Python), Vanilla JS, Jinja2 templates, Anthropic Claude API

**Spec:** `docs/superpowers/specs/2026-04-21-ticket-wizard-design.md`

---

## Chunk 1: Department files + backend API routes

**Files:**
- Create: `docs/departments/its.md`
- Create: `docs/departments/ops.md`
- Modify: `app.py` — add 4 routes and a helper

---

### Task 1: Create initial department scripts

- [ ] **Step 1: Create `docs/departments/its.md`**

```markdown
# ITS — Ticket vragen

1. Wat is het betrokken systeem of de applicatie?
2. Beschrijf het probleem zo concreet mogelijk.
3. Sinds wanneer doet het probleem zich voor?
4. Hoeveel gebruikers worden getroffen?
5. Is er al iets geprobeerd om het op te lossen?
```

- [ ] **Step 2: Create `docs/departments/ops.md`**

```markdown
# OPS — Ticket vragen

1. Op welke machine of locatie doet het probleem zich voor?
2. Beschrijf het probleem zo concreet mogelijk.
3. Sinds wanneer is dit het geval?
4. Heeft er recent een wijziging plaatsgevonden (update, installatie, verplaatsing)?
5. Wat is de impact op de productie?
```

- [ ] **Step 3: Verify files exist**

```bash
ls docs/departments/
```
Expected: `its.md  ops.md`

- [ ] **Step 4: Commit**

```bash
git add docs/departments/
git commit -m "feat: add initial department question scripts (ITS, OPS)"
```

---

### Task 2: Add department API routes to `app.py`

Add these imports at the top of `app.py` (after existing imports):
```python
import re
```

Add a helper function and 4 routes. Insert the helper before the `if __name__ == "__main__":` block:

- [ ] **Step 1: Add `_departments_dir()` helper**

```python
def _departments_dir() -> Path:
    return Path(__file__).parent / "docs" / "departments"
```

- [ ] **Step 2: Add `GET /api/departments` route**

```python
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
```

- [ ] **Step 3: Add `GET /api/departments/<slug>` route**

```python
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
```

- [ ] **Step 4: Add `POST /admin/departments/save` route**

```python
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
```

- [ ] **Step 5: Add `DELETE /admin/departments/<slug>` route**

```python
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
```

- [ ] **Step 6: Add `start_wizard` intercept to `/chat` route**

The current `/chat` route (app.py lines 48–91) appends the user message on line 61, calls `claude.chat()` on line 67, then checks `result["type"]` starting at line 72. The intercept must be inserted **between line 67 and line 72** — i.e., immediately after `result = claude.chat(...)` and before `if result["type"] == "confirmation_required":`.

Replace the block starting at line 64 (`try:`) through line 87 with this updated version:

```python
    try:
        user_role = session["user"].get("role", "beperkt")
        log.debug("USER: %s ROLE: %s", session["user"].get("email"), user_role)
        result = claude.chat(messages=session["messages"], role=user_role, user=session["user"])
    except Exception as e:
        log.error("Claude chat error: %s\n%s", e, traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    # If Claude wants to create_ticket but the wizard wasn't used, redirect to wizard
    wizard_completed = data.get("wizard_completed", False)
    if (not wizard_completed
            and result.get("type") == "confirmation_required"
            and result.get("tool_name") == "create_ticket"):
        session["messages"].pop()  # undo the user message appended above
        session.modified = True
        return jsonify({"type": "start_wizard", "suggested_department": None})

    if result["type"] == "confirmation_required":
        action_id = str(uuid.uuid4())
        session["pending_action"] = {
            "id": action_id,
            "tool_name": result["tool_name"],
            "tool_id": result["tool_id"],
            "tool_input": result["tool_input"],
            "assistant_content": result["assistant_content"],
            "messages_at_confirmation": result["messages_at_confirmation"],
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
```

- [ ] **Step 7: Smoke test the API**

Start Flask: `python app.py`
Open browser and log in, then in another tab:
- Visit `http://localhost:5000/api/departments` → expect JSON array with ITS and OPS
- Visit `http://localhost:5000/api/departments/its` → expect markdown text

- [ ] **Step 8: Commit**

```bash
git add app.py
git commit -m "feat: add department API routes + wizard intercept in /chat"
```

---

## Chunk 2: Frontend wizard (chat.js + chat.html button)

**Files:**
- Modify: `static/chat.js` — add wizard state machine
- Modify: `templates/chat.html` — add "Nieuw ticket" button

---

### Task 3: Add "Nieuw ticket" button to chat header

In `templates/chat.html`, find the header `<div class="user-info">` section and add the button as the **first** element inside it (before the avatar):

- [ ] **Step 1: Add CSS for the new button**

Inside the `<style>` block, after the `.admin-btn` rule, add:

```css
.new-ticket-btn {
  background: #1e2535;
  border: 1px solid #2d3748;
  color: #94a3b8;
  padding: 5px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.78rem;
  font-family: inherit;
  font-weight: 500;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.new-ticket-btn:hover { background: #252f40; color: #cbd5e1; border-color: #6366f1; }
```

- [ ] **Step 2: Add the button in the header**

In the `<div class="user-info">` block, add as first child:

```html
<button class="new-ticket-btn" onclick="startWizard()">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
  Nieuw ticket
</button>
```

- [ ] **Step 3: Commit**

```bash
git add templates/chat.html
git commit -m "feat: add Nieuw ticket button to chat header"
```

---

### Task 4: Implement wizard state machine in chat.js

Replace the entire `static/chat.js` with the updated version below. Key additions: `wizardState`, `parseQuestions()`, `startWizard()`, `showDepartmentPicker()`, `showWizardQuestion()`, `handleWizardAnswer()`, `finishWizard()`, `cancelWizard()`. The existing `addMessage`, `showTyping`, `hideTyping`, `showConfirmation`, `handleConfirm` functions are preserved unchanged.

- [ ] **Step 1: Add wizard state and parseQuestions at top of chat.js**

After the first 3 `const` lines, add:

```js
let wizardState = {
  active: false,
  department: null,
  questions: [],
  answers: [],
  currentStep: 0
};

function parseQuestions(markdown) {
  const lines = markdown.split('\n');
  const pairs = [];
  for (const line of lines) {
    const m = line.match(/^(\d+)\.\s+(.+)/);
    if (m) pairs.push({ n: parseInt(m[1]), text: m[2].trim() });
  }
  pairs.sort((a, b) => a.n - b.n);
  const questions = pairs.map(p => p.text);
  return questions.length > 0 ? questions : ['Beschrijf het probleem.'];
}
```

- [ ] **Step 2: Add department picker UI function**

```js
function showDepartmentPicker(departments, suggestedSlug) {
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.id = 'dept-picker';

  if (departments.length === 0) {
    div.textContent = 'Geen afdelingen geconfigureerd — contacteer een admin.';
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return;
  }

  const chips = departments.map(d =>
    `<button class="dept-chip${d.slug === suggestedSlug ? ' active' : ''}" onclick="selectDepartment('${d.slug}')">${d.name}</button>`
  ).join('');

  div.innerHTML = `<span>Voor welke afdeling is dit ticket?</span><div class="dept-chips">${chips}</div>`;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}
```

- [ ] **Step 3: Add `startWizard()` function**

```js
async function startWizard(suggestedSlug) {
  if (wizardState.active) return;
  sendBtn.disabled = true;
  try {
    const resp = await fetch('/api/departments');
    const departments = await resp.json();
    showDepartmentPicker(departments, suggestedSlug || null);
    wizardState.active = true;
    wizardState.department = null;
    wizardState.questions = [];
    wizardState.answers = [];
    wizardState.currentStep = 0;
  } catch (e) {
    addMessage('Fout bij laden van afdelingen: ' + e.message, 'assistant');
  } finally {
    sendBtn.disabled = false;
  }
}
```

- [ ] **Step 4: Add `selectDepartment()` function**

```js
async function selectDepartment(slug) {
  const picker = document.getElementById('dept-picker');
  if (picker) picker.remove();

  addMessage(slug.toUpperCase(), 'user');
  showTyping();

  try {
    const resp = await fetch(`/api/departments/${slug}`);
    if (!resp.ok) throw new Error('Afdeling niet gevonden');
    const markdown = await resp.text();
    const questions = parseQuestions(markdown);
    wizardState.department = slug;
    wizardState.questions = questions;
    wizardState.answers = [];
    wizardState.currentStep = 0;
  } catch (e) {
    hideTyping();
    addMessage('Fout bij laden van vragen: ' + e.message, 'assistant');
    cancelWizard();
    return;
  }

  hideTyping();
  showWizardQuestion();
}
```

- [ ] **Step 5: Add `showWizardQuestion()` function**

```js
function showWizardQuestion() {
  const { currentStep, questions } = wizardState;
  const total = questions.length;
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.innerHTML =
    `<span style="color:#64748b;font-size:0.78rem;">Vraag ${currentStep + 1}/${total}</span><br>` +
    `${questions[currentStep]}` +
    `<br><br><button class="dept-chip cancel-chip" onclick="cancelWizard()">Annuleren</button>`;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  input.focus();
}
```

- [ ] **Step 6: Add `cancelWizard()` function**

```js
function cancelWizard() {
  wizardState = { active: false, department: null, questions: [], answers: [], currentStep: 0 };
  addMessage('Ticketaanmaak geannuleerd.', 'assistant');
  sendBtn.disabled = false;
  input.focus();
}
```

- [ ] **Step 7: Add `finishWizard()` function**

```js
async function finishWizard() {
  const { department, questions, answers } = wizardState;
  wizardState = { active: false, department: null, questions: [], answers: [], currentStep: 0 };

  const lines = questions.map((q, i) => `- ${q.replace(/\?$/, '')}: ${answers[i]}`).join('\n');
  const finalMessage = `Maak een ticket aan voor ${department.toUpperCase()} met de volgende informatie:\n${lines}`;

  addMessage(finalMessage, 'user');
  sendBtn.disabled = true;
  showTyping();

  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: finalMessage, wizard_completed: true })
    });
    const data = await resp.json();
    hideTyping();

    if (data.error) {
      addMessage('Fout: ' + data.error, 'assistant');
    } else if (data.type === 'confirmation_required') {
      showConfirmation(data.action_id, data.message);
    } else if (data.type === 'start_wizard') {
      addMessage('Kan je de afdeling opnieuw selecteren?', 'assistant');
      startWizard(data.suggested_department);
    } else {
      addMessage(data.message || '(leeg antwoord)', 'assistant');
    }
  } catch (e) {
    hideTyping();
    addMessage('Netwerkfout: ' + e.message, 'assistant');
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}
```

- [ ] **Step 8: Update `sendMessage()` to intercept wizard answers**

Replace the existing `sendMessage()` function with:

```js
async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  // Wizard mode: treat input as answer to current question
  if (wizardState.active && wizardState.department) {
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    wizardState.answers.push(text);
    wizardState.currentStep++;
    if (wizardState.currentStep < wizardState.questions.length) {
      showWizardQuestion();
    } else {
      await finishWizard();
    }
    return;
  }

  // Normal chat mode
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

    if (data.error) {
      addMessage('Fout: ' + data.error, 'assistant');
    } else if (data.type === 'confirmation_required') {
      showConfirmation(data.action_id, data.message);
    } else if (data.type === 'start_wizard') {
      startWizard(data.suggested_department);
    } else {
      addMessage(data.message || '(leeg antwoord)', 'assistant');
    }
  } catch (e) {
    hideTyping();
    addMessage('Netwerkfout: ' + e.message, 'assistant');
    console.error(e);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}
```

- [ ] **Step 9: Add wizard CSS to chat.html**

In the `<style>` block of `chat.html`, add after `.btn-cancel` rule:

```css
.dept-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.dept-chip {
  background: #1e2535;
  border: 1px solid #2d3748;
  color: #94a3b8;
  padding: 5px 14px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.82rem;
  font-family: inherit;
  transition: all 0.15s;
}
.dept-chip:hover { background: #252f40; color: #cbd5e1; border-color: #6366f1; }
.dept-chip.active { background: #1e2a4a; border-color: #6366f1; color: #818cf8; }
.cancel-chip { color: #f87171; border-color: #7f1d1d; background: #1a0f0f; }
.cancel-chip:hover { background: #2d1515; border-color: #f87171; color: #fca5a5; }
```

- [ ] **Step 10: Manual test wizard flow**

Start Flask and open the chat. Test:
1. Click "Nieuw ticket" → dept picker appears with ITS/OPS chips
2. Click ITS → first question appears
3. Type an answer, press Enter → next question appears
4. Click "Annuleren" → "Ticketaanmaak geannuleerd." appears, normal chat resumes
5. Run full ITS wizard (5 answers) → Claude receives aggregated message, shows confirmation
6. Type "maak een ticket aan" in normal chat → wizard is triggered automatically

- [ ] **Step 11: Commit**

```bash
git add static/chat.js templates/chat.html
git commit -m "feat: inline ticket creation wizard with department picker"
```

---

## Chunk 3: Admin page — Afdelingen tab

**Files:**
- Modify: `templates/admin.html` — add tab navigation + departments editor section

---

### Task 5: Add Afdelingen tab to admin.html

The admin page currently has a 2-column grid (Gebruikers | Prompt editor). We'll add tab navigation at the top and a new full-width departments section that appears when the "Afdelingen" tab is active.

- [ ] **Step 1: Add tab CSS to admin.html `<style>` block**

After the `.save-status.err` rule, add:

```css
/* ── TABS ── */
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 1px solid #1e2535;
  padding-bottom: 0;
}

.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #64748b;
  padding: 8px 18px 10px;
  font-size: 0.88rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.tab-btn:hover { color: #cbd5e1; }
.tab-btn.active { color: #818cf8; border-bottom-color: #6366f1; }

/* ── DEPARTMENTS ── */
.dept-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }

.dept-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #0f1117;
  border: 1px solid #1e2535;
  border-radius: 10px;
  padding: 12px 16px;
}

.dept-row-name { font-weight: 500; color: #e2e8f0; font-size: 0.88rem; }
.dept-row-slug { font-size: 0.76rem; color: #64748b; margin-top: 2px; }
.dept-row-actions { display: flex; gap: 8px; }

.dept-action-btn {
  background: #1e2535;
  border: 1px solid #2d3748;
  color: #94a3b8;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.78rem;
  font-family: inherit;
  transition: all 0.15s;
}
.dept-action-btn:hover { background: #252f40; color: #cbd5e1; }
.dept-action-btn.danger { border-color: #7f1d1d; color: #f87171; }
.dept-action-btn.danger:hover { background: #2d1515; }

.dept-editor {
  background: #0f1117;
  border: 1px solid #6366f1;
  border-radius: 12px;
  padding: 18px;
  margin-bottom: 16px;
  display: none;
}
.dept-editor.visible { display: block; }

.dept-editor-row { margin-bottom: 14px; }
.dept-editor-label {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}
.dept-editor-input {
  width: 100%;
  background: #161b27;
  border: 1px solid #2d3748;
  border-radius: 8px;
  color: #e2e8f0;
  font-family: inherit;
  font-size: 0.85rem;
  padding: 8px 12px;
  outline: none;
  transition: border-color 0.2s;
}
.dept-editor-input:focus { border-color: #6366f1; }
.dept-editor-textarea {
  width: 100%;
  background: #161b27;
  border: 1px solid #2d3748;
  border-radius: 8px;
  color: #cbd5e1;
  font-family: 'Inter', monospace;
  font-size: 0.82rem;
  line-height: 1.6;
  padding: 10px 12px;
  resize: vertical;
  min-height: 160px;
  outline: none;
  transition: border-color 0.2s;
}
.dept-editor-textarea:focus { border-color: #6366f1; }
.dept-editor-error { color: #f87171; font-size: 0.8rem; margin-top: 6px; display: none; }
.dept-editor-error.visible { display: block; }

.add-dept-btn {
  background: transparent;
  border: 1px dashed #2d3748;
  color: #64748b;
  padding: 10px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.85rem;
  font-family: inherit;
  width: 100%;
  transition: all 0.15s;
}
.add-dept-btn:hover { border-color: #6366f1; color: #818cf8; background: #0f1117; }
```

- [ ] **Step 2: Replace the `<div class="page-content">` block in admin.html**

Replace the entire `<div class="page-content">` block (from `<div class="page-content">` through the closing `</div>` before `<script>`) with:

```html
<div class="page-content">
  <div class="page-title">Beheer</div>

  <!-- Tab bar -->
  <div class="tab-bar">
    <button class="tab-btn active" id="tab-overzicht" onclick="showTab('overzicht')">Overzicht</button>
    <button class="tab-btn" id="tab-afdelingen" onclick="showTab('afdelingen')">Afdelingen</button>
  </div>

  <!-- Tab: Overzicht (existing 2-col grid) -->
  <div id="panel-overzicht">
    <div class="admin-grid">

      <!-- LEFT: Users -->
      <div class="card">
        <div class="card-title">
          <span class="card-title-dot"></span>
          Gebruikers
        </div>
        <table class="users-table">
          <thead>
            <tr>
              <th>Naam</th>
              <th>E-mail</th>
              <th>Rol</th>
            </tr>
          </thead>
          <tbody>
            {% for u in all_users %}
            <tr>
              <td class="name">{{ u.display_name }}</td>
              <td class="email">{{ u.email }}</td>
              <td><span class="role-badge {{ u.role }}">{{ u.role }}</span></td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <!-- RIGHT: Prompt editor -->
      <div class="card">
        <div class="card-title">
          <span class="card-title-dot"></span>
          Prompt editor
        </div>

        <div class="prompt-group">
          <label class="prompt-label" for="prompt-admin">Admin prompt</label>
          <textarea id="prompt-admin" class="prompt-textarea" rows="8">{{ prompts.admin }}</textarea>
        </div>

        <div class="prompt-group">
          <label class="prompt-label" for="prompt-beperkt">Beperkt prompt</label>
          <textarea id="prompt-beperkt" class="prompt-textarea" rows="8">{{ prompts.beperkt }}</textarea>
        </div>

        <div class="save-row">
          <button class="save-btn" id="save-btn" onclick="savePrompts()">Opslaan</button>
          <span class="save-status" id="save-status"></span>
        </div>
      </div>

    </div>
  </div>

  <!-- Tab: Afdelingen -->
  <div id="panel-afdelingen" style="display:none;">
    <div class="card" style="max-width:680px;">
      <div class="card-title">
        <span class="card-title-dot"></span>
        Afdeling scripts
      </div>

      <div id="dept-list" class="dept-list">
        <!-- populated by JS -->
      </div>

      <!-- Inline editor (hidden by default) -->
      <div class="dept-editor" id="dept-editor">
        <div class="dept-editor-row">
          <label class="dept-editor-label">Naam (slug)</label>
          <input type="text" id="dept-slug" class="dept-editor-input" placeholder="its" maxlength="40">
          <div class="dept-editor-error" id="dept-slug-error"></div>
        </div>
        <div class="dept-editor-row">
          <label class="dept-editor-label">Inhoud (markdown)</label>
          <textarea id="dept-content" class="dept-editor-textarea"></textarea>
        </div>
        <div style="display:flex;gap:8px;">
          <button class="save-btn" onclick="saveDepartment()">Opslaan</button>
          <button class="dept-action-btn" onclick="closeDeptEditor()">Annuleren</button>
          <span class="save-status" id="dept-save-status" style="margin-left:4px;"></span>
        </div>
      </div>

      <button class="add-dept-btn" onclick="openDeptEditor(null)">+ Nieuwe afdeling</button>
    </div>
  </div>

</div>
```

- [ ] **Step 3: Add admin JS functions to `<script>` block**

Append these functions to the existing `<script>` block (after the `showStatus` function):

```js
// ── TAB NAVIGATION ──
function showTab(name) {
  ['overzicht', 'afdelingen'].forEach(t => {
    document.getElementById('panel-' + t).style.display = t === name ? '' : 'none';
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
  });
  if (name === 'afdelingen') loadDepartments();
}

// ── DEPARTMENTS ──
let editingSlug = null; // null = new, string = existing slug being edited

async function loadDepartments() {
  const list = document.getElementById('dept-list');
  list.innerHTML = '<span style="color:#64748b;font-size:0.85rem;">Laden...</span>';
  try {
    const resp = await fetch('/api/departments');
    const depts = await resp.json();
    if (depts.length === 0) {
      list.innerHTML = '<span style="color:#64748b;font-size:0.85rem;">Geen afdelingen geconfigureerd.</span>';
      return;
    }
    list.innerHTML = depts.map(d => `
      <div class="dept-row">
        <div>
          <div class="dept-row-name">${d.name}</div>
          <div class="dept-row-slug">${d.slug}</div>
        </div>
        <div class="dept-row-actions">
          <button class="dept-action-btn" onclick="openDeptEditor('${d.slug}')">Bewerken</button>
          <button class="dept-action-btn danger" onclick="deleteDepartment('${d.slug}')">Verwijderen</button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = '<span style="color:#f87171;font-size:0.85rem;">Fout bij laden: ' + e.message + '</span>';
  }
}

async function openDeptEditor(slug) {
  editingSlug = slug;
  const editor = document.getElementById('dept-editor');
  const slugInput = document.getElementById('dept-slug');
  const contentArea = document.getElementById('dept-content');
  document.getElementById('dept-slug-error').className = 'dept-editor-error';
  document.getElementById('dept-save-status').className = 'save-status';

  if (slug) {
    slugInput.value = slug;
    slugInput.readOnly = true;
    try {
      const resp = await fetch('/api/departments/' + slug);
      contentArea.value = await resp.text();
    } catch (e) {
      contentArea.value = '';
    }
  } else {
    slugInput.value = '';
    slugInput.readOnly = false;
    contentArea.value = '# Nieuwe afdeling — Ticket vragen\n\n1. \n2. \n3. ';
  }

  editor.className = 'dept-editor visible';
  slugInput.focus();
}

function closeDeptEditor() {
  document.getElementById('dept-editor').className = 'dept-editor';
  editingSlug = null;
}

async function saveDepartment() {
  const slug = document.getElementById('dept-slug').value.trim().toLowerCase();
  const content = document.getElementById('dept-content').value.trim();
  const errEl = document.getElementById('dept-slug-error');
  const statusEl = document.getElementById('dept-save-status');

  if (!/^[a-z0-9_]+$/.test(slug)) {
    errEl.textContent = 'Alleen a-z, 0-9 en _ toegestaan.';
    errEl.className = 'dept-editor-error visible';
    return;
  }
  errEl.className = 'dept-editor-error';

  try {
    const resp = await fetch('/admin/departments/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug, content })
    });
    const data = await resp.json();
    if (data.ok) {
      statusEl.textContent = 'Opgeslagen.';
      statusEl.className = 'save-status visible ok';
      setTimeout(() => {
        closeDeptEditor();
        loadDepartments();
      }, 800);
    } else {
      statusEl.textContent = data.error || 'Opslaan mislukt.';
      statusEl.className = 'save-status visible err';
    }
  } catch (e) {
    statusEl.textContent = 'Netwerkfout.';
    statusEl.className = 'save-status visible err';
  }
}

async function deleteDepartment(slug) {
  if (!confirm(`Afdeling "${slug}" verwijderen?`)) return;
  try {
    const resp = await fetch('/admin/departments/' + slug, { method: 'DELETE' });
    const data = await resp.json();
    if (data.ok) loadDepartments();
  } catch (e) {
    alert('Verwijderen mislukt: ' + e.message);
  }
}
```

- [ ] **Step 4: Manual test admin Afdelingen tab**

Start Flask, open `/admin` as admin user. Test:
1. Click "Afdelingen" tab → ITS and OPS appear in the list
2. Click "Bewerken" on ITS → editor opens with existing content
3. Edit content, click "Opslaan" → "Opgeslagen." appears, list refreshes
4. Click "+ Nieuwe afdeling" → empty editor with slug field editable
5. Enter slug `finance`, add markdown questions, save → `finance.md` created
6. Click "Verwijderen" on finance → confirmation dialog, then removed from list
7. Test invalid slug ("IT-S") → inline error shown, no request sent

- [ ] **Step 5: Commit**

```bash
git add templates/admin.html
git commit -m "feat: Afdelingen tab in admin page with inline editor"
```

---

## Final verification

- [ ] Full end-to-end test: open chat, type "ik wil een ticket maken" → wizard starts automatically
- [ ] Full end-to-end test: click "Nieuw ticket" → select OPS → answer all questions → Claude shows confirmation → confirm → ticket created in Jira
- [ ] Admin: add a new department "hr" with 3 questions → wizard shows it in the picker → delete it
- [ ] Switch to "beperkt" user → wizard works (it only calls `create_ticket` which is allowed)

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat: ticket wizard complete — department picker, inline flow, admin management"
```
