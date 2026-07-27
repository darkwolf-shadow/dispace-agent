const API = window.location.host.includes('localhost') ? window.location.origin : '';

async function apiFetch(url, opts = {}) {
  opts.credentials = opts.credentials || 'include';
  opts.headers = opts.headers || {};
  const auth = localStorage.getItem('dispace_auth');
  if (auth) {
    opts.headers['Authorization'] = 'Basic ' + auth;
  }
  return fetch(url, opts);
}

const video = document.getElementById('camera');
const preview = document.getElementById('preview');
const btnSnap = document.getElementById('btn-snap');
const btnRetake = document.getElementById('btn-retake');
const btnUpload = document.getElementById('btn-upload');
const fileInput = document.getElementById('file-input');
const statusSection = document.getElementById('status-section');
const resultSection = document.getElementById('result-section');
const contactForm = document.getElementById('contact-form');
const contactsList = document.getElementById('contacts-list');
const btnRefresh = document.getElementById('btn-refresh');
const campaignForm = document.getElementById('campaign-form');
const campaignsList = document.getElementById('campaigns-list');
const contentsList = document.getElementById('contents-list');
const btnRefreshContents = document.getElementById('btn-refresh-contents');

let currentBlob = null;

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    video.srcObject = stream;
    btnSnap.disabled = false;
  } catch (err) {
    console.error('Camera error:', err);
    btnSnap.disabled = true;
    btnSnap.textContent = 'Camera non disponibile';
  }
}

function snap() {
  const width = video.videoWidth;
  const height = video.videoHeight;
  preview.width = width;
  preview.height = height;
  const ctx = preview.getContext('2d');
  ctx.drawImage(video, 0, 0, width, height);

  preview.style.display = 'block';
  video.style.display = 'none';
  btnSnap.style.display = 'none';
  btnRetake.style.display = 'inline-block';
  btnUpload.style.display = 'inline-block';

  preview.toBlob(blob => { currentBlob = blob; }, 'image/jpeg', 0.9);
}

function retake() {
  preview.style.display = 'none';
  video.style.display = 'block';
  btnSnap.style.display = 'inline-block';
  btnRetake.style.display = 'none';
  btnUpload.style.display = 'none';
  currentBlob = null;
  resultSection.style.display = 'none';
}

function fillForm(contact) {
  document.getElementById('c-name').value = contact.name || '';
  document.getElementById('c-company').value = contact.company || '';
  document.getElementById('c-role').value = contact.role || '';
  document.getElementById('c-email').value = contact.email || '';
  document.getElementById('c-phone').value = contact.phone || '';
  document.getElementById('c-website').value = contact.website || '';
  document.getElementById('c-address').value = contact.address || '';
  document.getElementById('c-linkedin').value = contact.linkedin || '';
}

function getFormData() {
  return {
    name: document.getElementById('c-name').value || null,
    company: document.getElementById('c-company').value || null,
    role: document.getElementById('c-role').value || null,
    email: document.getElementById('c-email').value || null,
    phone: document.getElementById('c-phone').value || null,
    website: document.getElementById('c-website').value || null,
    address: document.getElementById('c-address').value || null,
    linkedin: document.getElementById('c-linkedin').value || null,
  };
}

async function uploadBlob(blob, filename = 'card.jpg') {
  statusSection.style.display = 'block';
  resultSection.style.display = 'none';

  const formData = new FormData();
  formData.append('file', blob, filename);

  try {
    const res = await apiFetch(`${API}/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error(await res.text());
    const contact = await res.json();
    fillForm(contact);
    statusSection.style.display = 'none';
    resultSection.style.display = 'block';
    await loadContacts();
    return contact;
  } catch (err) {
    statusSection.style.display = 'none';
    alert('Errore upload: ' + err.message);
  }
}

async function saveContactManual(e) {
  e.preventDefault();
  const data = getFormData();
  try {
    const res = await apiFetch(`${API}/contacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    alert('Contatto salvato');
    resultSection.style.display = 'none';
    await loadContacts();
  } catch (err) {
    alert('Errore salvataggio: ' + err.message);
  }
}

async function enrichContact(id) {
  try {
    const res = await apiFetch(`${API}/contacts/${id}/enrich`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const contact = await res.json();
    alert(`Arricchito: score ${contact.score}\nTag: ${(contact.tags || []).join(', ')}`);
    await loadContacts();
  } catch (err) {
    alert('Errore enrichment: ' + err.message);
  }
}

async function showReport(id) {
  try {
    const res = await apiFetch(`${API}/contacts/${id}/report`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    document.getElementById('report-text').textContent = data.report || 'Nessun report';
    document.getElementById('report-section').style.display = 'block';
  } catch (err) {
    alert('Errore report: ' + err.message);
  }
}

async function loadContacts() {
  try {
    const res = await apiFetch(`${API}/contacts`);
    const contacts = await res.json();
    contactsList.innerHTML = contacts.map(c => `
      <li>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;">
          <div>
            <strong>${c.name || 'Sconosciuto'}</strong>
            ${c.company ? `<span>${c.company}</span>` : ''}
            ${c.email ? `<br><small>${c.email}</small>` : ''}
            ${c.phone ? `<small> · ${c.phone}</small>` : ''}
            ${c.score ? `<br><small>Score: ${c.score}</small>` : ''}
            ${c.tags ? `<br><small>${c.tags.join(', ')}</small>` : ''}
          </div>
          <div class="actions">
            <button onclick="enrichContact(${c.id})">Arricchisci</button>
            <button onclick="showReport(${c.id})">Report</button>
            <button onclick="generateForContact(${c.id}, 'proposal')">Proposta</button>
            <button onclick="generateForContact(${c.id}, 'whatsapp')">WhatsApp</button>
            <button onclick="generateForContact(${c.id}, 'story')">Story</button>
          </div>
        </div>
      </li>
    `).join('');
  } catch (err) {
    contactsList.innerHTML = `<li>Errore caricamento: ${err.message}</li>`;
  }
}

window.enrichContact = enrichContact;
window.showReport = showReport;
window.generateForContact = generateForContact;

async function generateForContact(id, kind) {
  try {
    const res = await apiFetch(`${API}/contacts/${id}/generate/${kind}`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const content = await res.json();
    document.getElementById('report-text').textContent = `[${content.kind.toUpperCase()}]\n\nOggetto: ${content.subject || 'N/D'}\n\n${content.body}`;
    document.getElementById('report-section').style.display = 'block';
    await loadGeneratedContents();
  } catch (err) {
    alert('Errore generazione: ' + err.message);
  }
}

async function createCampaign(e) {
  e.preventDefault();
  const data = {
    name: document.getElementById('cmp-name').value,
    channel: document.getElementById('cmp-channel').value,
    template_id: document.getElementById('cmp-template-id').value || null,
  };
  try {
    const res = await apiFetch(`${API}/campaigns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    campaignForm.reset();
    await loadCampaigns();
  } catch (err) {
    alert('Errore campagna: ' + err.message);
  }
}

async function loadCampaigns() {
  try {
    const res = await apiFetch(`${API}/campaigns`);
    const campaigns = await res.json();
    campaignsList.innerHTML = campaigns.map(c => `
      <li>
        <strong>${c.name}</strong> (${c.channel}) - ${c.status}
        <br><small>Generati: ${c.generated_count}</small>
        <button onclick="runCampaign(${c.id})">Esegui</button>
      </li>
    `).join('');
  } catch (err) {
    campaignsList.innerHTML = `<li>Errore: ${err.message}</li>`;
  }
}

window.runCampaign = async function(id) {
  try {
    const res = await apiFetch(`${API}/campaigns/${id}/run`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const generated = await res.json();
    alert(`Generati ${generated.length} contenuti`);
    await loadCampaigns();
    await loadGeneratedContents();
  } catch (err) {
    alert('Errore esecuzione: ' + err.message);
  }
};

async function loadGeneratedContents() {
  try {
    const res = await apiFetch(`${API}/generated-contents`);
    const contents = await res.json();
    contentsList.innerHTML = contents.map(c => `
      <li>
        <strong>${c.kind} - ${c.channel || 'generic'}</strong>
        <br><small>${(c.subject || c.body).substring(0, 80)}...</small>
      </li>
    `).join('');
  } catch (err) {
    contentsList.innerHTML = `<li>Errore: ${err.message}</li>`;
  }
}

btnSnap.addEventListener('click', snap);
btnRetake.addEventListener('click', retake);
btnUpload.addEventListener('click', () => currentBlob && uploadBlob(currentBlob));
fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) uploadBlob(file, file.name);
});
contactForm.addEventListener('submit', saveContactManual);
btnRefresh.addEventListener('click', loadContacts);
campaignForm.addEventListener('submit', createCampaign);
btnRefreshContents.addEventListener('click', loadGeneratedContents);

document.getElementById('btn-close-report').addEventListener('click', () => {
  document.getElementById('report-section').style.display = 'none';
});

const loginSection = document.getElementById('login-section');
const mainApp = document.getElementById('main-app');
const btnLogin = document.getElementById('btn-login');
const loginError = document.getElementById('login-error');

function showApp() {
  if (loginSection) loginSection.style.display = 'none';
  if (mainApp) mainApp.style.display = 'block';
  startCamera();
  loadContacts();
  loadCampaigns();
  loadGeneratedContents();
}

async function doLogin() {
  const user = document.getElementById('login-user').value.trim();
  const pass = document.getElementById('login-pass').value;
  if (!user || !pass) {
    loginError.textContent = 'Inserisci utente e password';
    return;
  }
  const token = btoa(user + ':' + pass);
  loginError.textContent = 'Controllo in corso...';
  const res = await fetch(`${API}/login`, { headers: { 'Authorization': 'Basic ' + token } });
  if (res.ok) {
    localStorage.setItem('dispace_auth', token);
    showApp();
  } else {
    loginError.textContent = 'Utente o password errati';
  }
}

const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    doLogin();
  });
}

const showPass = document.getElementById('show-pass');
if (showPass) {
  showPass.addEventListener('change', () => {
    const passInput = document.getElementById('login-pass');
    passInput.type = showPass.checked ? 'text' : 'password';
  });
}

// Accesso libero: avvia subito l'applicazione
showApp();
