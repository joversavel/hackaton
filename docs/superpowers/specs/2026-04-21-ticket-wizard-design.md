# Ticket Creation Wizard per Department — Design Spec
**Date:** 2026-04-21
**Project:** Helpdesk AI — Sterima/Pollet Hackathon

---

## Overview

A guided ticket creation wizard that walks users through department-specific questions inline in the chat. Each department (ITS, OPS, etc.) has its own question script stored as a markdown file. Admins can manage these scripts via the admin page without touching code.

---

## 1. Data & Storage

Department scripts live in `docs/departments/` — one `.md` file per department:

```
docs/departments/
  its.md
  ops.md
  ...
```

**File format:**
```markdown
# ITS — Ticket vragen

1. Wat is het betrokken systeem of de applicatie?
2. Beschrijf het probleem zo concreet mogelijk.
3. Sinds wanneer doet het probleem zich voor?
4. Hoeveel gebruikers worden getroffen?
5. Is er al iets geprobeerd om het op te lossen?
```

- Files are always stored **lowercase** (e.g. `its.md`, never `ITS.md`). Cross-platform safe.
- The display name is read from the first `#` heading in the file.
- File names must match `[a-z0-9_]+` only (alphanumeric + underscores). The admin UI validates and rejects anything else.
- No database required — plain files, editable by admins.

---

## 2. Wizard Flow

### Trigger
- **Button:** A "Nieuw ticket" button in the chat header, always visible. Clicking it immediately starts the wizard regardless of chat state. If no departments are configured, the wizard shows "Geen afdelingen geconfigureerd — contacteer een admin." and closes.
- **Claude detection:** When the user types something that implies ticket creation (e.g. "maak een ticket aan") without using the button, the normal `/chat` call is made. If Claude would call `create_ticket` **and** the request does not include `wizard_completed: true`, the backend intercepts this in the `/chat` route before executing the tool and returns:
  ```json
  {"type": "start_wizard", "suggested_department": null}
  ```
  The frontend recognizes `type === "start_wizard"` (same response shape as normal `/chat` responses, with a new type value) and triggers the wizard. The original user message is discarded — the wizard starts fresh.

The frontend sends `wizard_completed: true` as a top-level field in the POST body to `/chat` only after the user has completed all wizard steps. The backend checks: if `wizard_completed` is not `true` and Claude's response contains a `create_ticket` tool call, short-circuit and return `start_wizard`.

### Step-by-step (inline in chat)
```
Bot:  "Voor welke afdeling is dit ticket?"
      [ITS]  [OPS]  [...]   ← clickable chips

User clicks "ITS"

Bot:  "Vraag 1/5: Wat is het betrokken systeem of de applicatie?"
      [Annuleren]
User: types answer → Enter

Bot:  "Vraag 2/5: Beschrijf het probleem zo concreet mogelijk."
...

Bot:  "Vraag 5/5: Is er al iets geprobeerd?"
User: types answer

→ Frontend sends ONE message to /chat with wizard_completed=true:
  "Maak een ticket aan voor ITS met de volgende informatie:
   - Systeem: [answer 1]
   - Probleem: [answer 2]
   - Sinds: [answer 3]
   - Getroffen gebruikers: [answer 4]
   - Al geprobeerd: [answer 5]"

Claude responds with usual confirmation_required type (no special handling needed)
User confirms → ticket created in Jira
```

### Wizard state (in `chat.js`)
```js
let wizardState = {
  active: false,
  department: null,    // slug string, e.g. "its"
  questions: [],       // string[], parsed from markdown via parseQuestions()
  answers: [],         // string[], one per question answered so far
  currentStep: 0       // index into questions[]
}
```

- Wizard state lives in a JS module-level variable — not in sessionStorage. A page refresh resets the wizard. Acceptable for demo scope.
- During an active wizard, the send button handler checks `wizardState.active` first. If true, the typed text is treated as a wizard answer, **not** sent to Claude.
- An "Annuleren" chip is shown after each question. Cancelling resets `wizardState` and posts "Ticketaanmaak geannuleerd." as a bot message, returning to normal chat.
- **Wizard Q&A does not appear in `session["messages"]` on the backend** — wizard question/answer turns are rendered in the chat UI but never POSTed to `/chat`. Only the single final aggregated message is sent to `/chat` (with `wizard_completed: true`). This prevents context duplication.

### Question parsing
`parseQuestions(markdown)` lives in **`chat.js`** (frontend only). Algorithm:
1. Split markdown into lines.
2. Extract lines matching `/^\d+\.\s+(.+)/` — capture the text after `N. `.
3. Sort by the numeric prefix.
4. Gaps are allowed (1, 3, 5 is valid).
5. If zero questions are found, fall back to `["Beschrijf het probleem."]`.

The backend does not parse questions — it only serves raw markdown via `/api/departments/<slug>`.

---

## 3. Backend API

New routes added to `app.py`:

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/api/departments` | Any authenticated user | List department display names and slugs |
| `GET` | `/api/departments/<slug>` | Any authenticated user | Return raw markdown of one department script |
| `POST` | `/admin/departments/save` | Admin only | Save/create a department script |
| `DELETE` | `/admin/departments/<slug>` | Admin only | Delete a department script |

`/api/departments*` — public to any authenticated session (needed by the wizard frontend).
`/admin/departments/*` — admin-only, same guard as the existing `/admin` route.

**`/api/departments` response:**
```json
[
  {"slug": "its", "name": "ITS — Ticket vragen"},
  {"slug": "ops", "name": "OPS — Ticket vragen"}
]
```
If `docs/departments/` is empty or missing, returns `[]`.

**`/admin/departments/save` body:**
```json
{"slug": "its", "content": "# ITS — Ticket vragen\n\n1. ..."}
```
Slug is validated against `[a-z0-9_]+` before writing. Returns `{"ok": true}` or `{"error": "..."}`.

**DELETE behavior:** Immediately removes the file. Active wizards using that department (in-browser) complete normally since the data is already in frontend memory. No soft delete.

---

## 4. Admin Page — "Afdelingen" Tab

A new tab added to `admin.html` alongside the existing "Prompts" tab.

**Tab layout:**
```
[ Prompts ]  [ Afdelingen ]

Afdelingen:
  ITS    [Bewerken]  [Verwijderen]
  OPS    [Bewerken]  [Verwijderen]
  [+ Nieuwe afdeling]

Inline editor (on Bewerken):
  Naam: [ ITS          ]   ← validates [a-z0-9_]+ on save, shown as lowercase
  ┌─────────────────────────────────┐
  │ # ITS — Ticket vragen           │
  │                                 │
  │ 1. Wat is het systeem?          │
  │ 2. Beschrijf het probleem.      │
  └─────────────────────────────────┘
  [Opslaan]  [Annuleren]
```

- "Verwijderen" shows a confirmation prompt before deleting.
- After saving, the list refreshes via GET `/api/departments`.

---

## 5. Error Handling

- **Empty department list:** Show "Geen afdelingen geconfigureerd — contacteer een admin." as a bot message and reset wizard state. The "Nieuw ticket" button remains enabled.
- **Malformed markdown** (no numbered questions found): Fall back to a single open-ended question: "Beschrijf het probleem."
- **Network error mid-wizard:** Show error message in chat, keep wizard state so user can retry the failed step.
- **Cancel at any step:** Reset wizard state, post "Ticketaanmaak geannuleerd." as a bot message, return to normal chat.
- **Invalid slug on save:** Admin UI rejects input not matching `[a-z0-9_]+` with an inline validation message before sending to backend.

---

## 6. Files Changed

| File | Change |
|------|--------|
| `app.py` | Add `/api/departments`, `/api/departments/<slug>`, `/admin/departments/save`, `/admin/departments/<slug>` routes |
| `static/chat.js` | Add `wizardState`, `parseQuestions()`, department chip UI, question flow, answer collection, `wizard_completed` flag |
| `templates/chat.html` | Add "Nieuw ticket" button in header |
| `templates/admin.html` | Add "Afdelingen" tab with inline editor |
| `docs/departments/its.md` | Initial ITS question script |
| `docs/departments/ops.md` | Initial OPS question script |
| `claude_client.py` | No changes needed |
