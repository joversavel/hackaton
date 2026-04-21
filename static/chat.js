const chatContainer = document.getElementById('chat-container');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');

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

function showDepartmentPicker(departments, suggestedSlug) {
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.id = 'dept-picker';

  if (departments.length === 0) {
    div.textContent = 'Geen afdelingen geconfigureerd — contacteer een admin.';
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    wizardState.active = false;
    return;
  }

  const chips = departments.map(d =>
    `<button class="dept-chip${d.slug === suggestedSlug ? ' active' : ''}" onclick="selectDepartment('${d.slug}')">${d.name}</button>`
  ).join('');

  div.innerHTML = `<span>Voor welke afdeling wil je een ticket aanmaken?</span><div class="dept-chips">${chips}</div>`;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function startWizard(suggestedSlug) {
  if (wizardState.active) return;
  sendBtn.disabled = true;
  wizardState = { active: true, department: null, questions: [], answers: [], currentStep: 0 };
  try {
    const resp = await fetch('/api/departments');
    const departments = await resp.json();
    showDepartmentPicker(departments, suggestedSlug || null);
  } catch (e) {
    addMessage('Fout bij laden van afdelingen: ' + e.message, 'assistant');
    wizardState.active = false;
  } finally {
    sendBtn.disabled = false;
  }
}

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

function cancelWizard() {
  wizardState = { active: false, department: null, questions: [], answers: [], currentStep: 0 };
  addMessage('Ticketaanmaak geannuleerd.', 'assistant');
  sendBtn.disabled = false;
  input.focus();
}

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

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  // Wizard mode: treat input as answer to current question
  if (wizardState.active && wizardState.department) {
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

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

addMessage('Hallo! Ik ben de Sterima AI assistent. Hoe kan ik je helpen?\n\nVoorbeelden:\n- "Toon open tickets"\n- "Maak een ticket voor login probleem"\n- "Zoek oplossing voor API timeout"', 'assistant');
