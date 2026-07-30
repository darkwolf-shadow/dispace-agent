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
const companyForm = document.getElementById('company-form');
const companySection = document.getElementById('company-section');
const btnOpenCompany = document.getElementById('btn-open-company');
const btnCloseCompany = document.getElementById('btn-close-company');
const btnEnrichCompany = document.getElementById('btn-enrich-company');

let currentBlob = null;
let currentContactId = null;

async function startCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    btnSnap.textContent = 'Fotocamera non supportata';
    return;
  }
  const constraints = [
    { video: { facingMode: { exact: 'environment' } } },
    { video: { facingMode: 'environment' } },
    { video: true },
  ];
  let lastErr = null;
  for (const c of constraints) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia(c);
      video.srcObject = stream;
      await video.play();
      btnSnap.disabled = false;
      btnSnap.textContent = 'Scatta';
      return;
    } catch (err) {
      lastErr = err;
    }
  }
  console.error('Camera error:', lastErr);
  btnSnap.textContent = 'Permetti la fotocamera e ricarica';
  alert('Non riesco ad accedere alla fotocamera. Assicurati di aver dato il permesso e che il sito sia aperto in HTTPS.');
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
  currentContactId = contact.id || null;
  const submitBtn = contactForm.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.textContent = currentContactId ? 'Aggiorna contatto' : 'Salva contatto';
  }
  document.getElementById('c-name').value = contact.name || '';
  document.getElementById('c-company').value = contact.company || '';
  document.getElementById('c-role').value = contact.role || '';
  document.getElementById('c-email').value = contact.email || '';
  document.getElementById('c-phone').value = contact.phone || '';
  document.getElementById('c-website').value = contact.website || '';
  document.getElementById('c-address').value = contact.address || '';
  document.getElementById('c-linkedin').value = contact.linkedin || '';
  const extra = contact.extra || {};
  const extraLines = Object.entries(extra)
    .filter(([k, v]) => v !== null && v !== undefined && String(v).trim() && String(v).trim().toLowerCase() !== 'null')
    .map(([k, v]) => `${k}: ${v}`);
  document.getElementById('c-extra').value = extraLines.length ? extraLines.join('\n') : '';
  const rawEl = document.getElementById('raw-text');
  if (rawEl) rawEl.textContent = contact.raw_text || '';
}

function getFormData() {
  const extraText = document.getElementById('c-extra').value.trim();
  const extra = {};
  if (extraText) {
    for (const line of extraText.split('\n')) {
      const [k, ...rest] = line.split(':');
      if (k && rest.length) extra[k.trim()] = rest.join(':').trim();
    }
  }
  return {
    name: document.getElementById('c-name').value || null,
    company: document.getElementById('c-company').value || null,
    role: document.getElementById('c-role').value || null,
    email: document.getElementById('c-email').value || null,
    phone: document.getElementById('c-phone').value || null,
    website: document.getElementById('c-website').value || null,
    address: document.getElementById('c-address').value || null,
    linkedin: document.getElementById('c-linkedin').value || null,
    extra: Object.keys(extra).length ? extra : null,
  };
}

async function uploadFiles(items, filename = 'card.jpg') {
  statusSection.style.display = 'block';
  resultSection.style.display = 'none';

  const formData = new FormData();
  const files = Array.isArray(items) ? items : [items];
  for (const item of files) {
    const blob = item.blob || item;
    const name = item.filename || filename;
    formData.append('files', blob, name);
  }

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
    const url = currentContactId ? `${API}/contacts/${currentContactId}` : `${API}/contacts`;
    const method = currentContactId ? 'PUT' : 'POST';
    const res = await apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    alert(currentContactId ? 'Contatto aggiornato' : 'Contatto salvato');
    resultSection.style.display = 'none';
    await loadContacts();
  } catch (err) {
    alert('Errore salvataggio: ' + err.message);
  }
}

async function enrichContact(id) {
  try {
    document.getElementById('report-text').textContent = 'Arricchimento in corso, attendi...';
    document.getElementById('report-section').style.display = 'block';
    const res = await apiFetch(`${API}/contacts/${id}/enrich`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const contact = await res.json();
    document.getElementById('report-text').textContent = contact.report || `Score: ${contact.score}\nTag: ${(contact.tags || []).join(', ')}`;
    await loadContacts();
  } catch (err) {
    document.getElementById('report-text').textContent = 'Errore enrichment: ' + err.message;
    alert('Errore enrichment: ' + err.message);
  }
}

async function loadCompanyProfile() {
  try {
    const res = await apiFetch(`${API}/company-profile`);
    if (!res.ok) throw new Error(await res.text());
    const profile = await res.json();
    for (const key of ['name', 'description', 'products', 'services', 'values', 'target', 'channels', 'website', 'email', 'phone', 'address', 'tone']) {
      const el = document.getElementById(`cp-${key}`);
      if (el) el.value = profile[key] || '';
    }
  } catch (err) {
    console.error('Errore caricamento profilo azienda:', err.message);
  }
}

async function saveCompanyProfile(e) {
  e.preventDefault();
  const data = {};
  for (const key of ['name', 'description', 'products', 'services', 'values', 'target', 'channels', 'website', 'email', 'phone', 'address', 'tone']) {
    const el = document.getElementById(`cp-${key}`);
    if (el) data[key] = el.value.trim() || null;
  }
  try {
    const res = await apiFetch(`${API}/company-profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    alert('Profilo azienda salvato');
  } catch (err) {
    alert('Errore salvataggio profilo: ' + err.message);
  }
}

async function enrichCompanyProfile() {
  const website = document.getElementById('cp-website').value.trim();
  if (!website) {
    alert('Inserisci prima il sito web dell\'azienda');
    return;
  }
  btnEnrichCompany.disabled = true;
  btnEnrichCompany.textContent = 'Lettura in corso...';
  try {
    const res = await apiFetch(`${API}/company-profile/enrich?website=${encodeURIComponent(website)}`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const profile = await res.json();
    for (const key of ['name', 'description', 'products', 'services', 'values', 'target', 'channels', 'website', 'email', 'phone', 'address', 'tone']) {
      const el = document.getElementById(`cp-${key}`);
      if (el) el.value = profile[key] || '';
    }
    alert('Profilo arricchito dal sito web');
  } catch (err) {
    alert('Errore arricchimento azienda: ' + err.message);
  } finally {
    btnEnrichCompany.disabled = false;
    btnEnrichCompany.textContent = 'Arricchisci da sito';
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
            ${c.address ? `<br><small>${c.address}</small>` : ''}
            ${c.extra ? `<br><small>${Object.entries(c.extra).filter(([k,v]) => v !== null && String(v).trim() && String(v).trim().toLowerCase() !== 'null').map(([k,v]) => `${k}: ${v}`).join(', ')}</small>` : ''}
            ${c.score ? `<br><small>Score: ${c.score}</small>` : ''}
            ${c.tags ? `<br><small>${c.tags.join(', ')}</small>` : ''}
          </div>
          <div class="actions">
            <button onclick="enrichContact(${c.id})">Arricchisci</button>
            <button onclick="showReport(${c.id})">Report</button>
            <button onclick="generateForContact(${c.id}, 'proposal')">Proposta</button>
            <button onclick="generateForContact(${c.id}, 'whatsapp')">WhatsApp</button>
            <button onclick="generateForContact(${c.id}, 'story')">Story</button>
            <button class="btn-danger" onclick="deleteContact(${c.id})">Elimina</button>
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

window.deleteContact = async function(id) {
  if (!confirm('Vuoi eliminare questo contatto?')) return;
  try {
    const res = await apiFetch(`${API}/contacts/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    await loadContacts();
  } catch (err) {
    alert('Errore eliminazione: ' + err.message);
  }
};

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

btnSnap.addEventListener('click', () => {
  if (!video.srcObject) {
    startCamera();
  } else {
    snap();
  }
});
btnRetake.addEventListener('click', retake);
btnUpload.addEventListener('click', () => currentBlob && uploadFiles(currentBlob));
fileInput.addEventListener('change', e => {
  const files = e.target.files;
  if (files.length) {
    const items = Array.from(files).map(file => ({ blob: file, filename: file.name }));
    uploadFiles(items);
  }
});
contactForm.addEventListener('submit', saveContactManual);
btnRefresh.addEventListener('click', loadContacts);
btnRefreshContents.addEventListener('click', loadGeneratedContents);

document.getElementById('btn-export-json').addEventListener('click', () => {
  window.location.href = `${API}/contacts/export?format=json`;
});
document.getElementById('btn-export-csv').addEventListener('click', () => {
  window.location.href = `${API}/contacts/export?format=csv`;
});
if (companyForm) companyForm.addEventListener('submit', saveCompanyProfile);
if (btnOpenCompany) btnOpenCompany.addEventListener('click', () => { companySection.style.display = 'flex'; loadCompanyProfile(); });
if (btnCloseCompany) btnCloseCompany.addEventListener('click', () => { companySection.style.display = 'none'; });
if (btnEnrichCompany) btnEnrichCompany.addEventListener('click', enrichCompanyProfile);

document.getElementById('btn-close-report').addEventListener('click', () => {
  document.getElementById('report-section').style.display = 'none';
});

const loginSection = document.getElementById('login-section');
const mainApp = document.getElementById('main-app');
const btnLogin = document.getElementById('btn-login');
const loginError = document.getElementById('login-error');

async function loadConfig() {
  try {
    const res = await apiFetch(`${API}/config`);
    if (!res.ok) return;
    const cfg = await res.json();
    const titleEl = document.querySelector('header h1');
    if (titleEl && cfg.app_title) titleEl.textContent = cfg.app_title;
    const ownerEl = document.getElementById('owner-name');
    if (ownerEl && cfg.owner_name) ownerEl.textContent = cfg.owner_name;
  } catch (err) {
    console.error('Config error:', err.message);
  }
}

function showApp() {
  if (loginSection) loginSection.style.display = 'none';
  if (mainApp) mainApp.style.display = 'block';
  loadContacts();
  loadGeneratedContents();
  loadCompanyProfile();
  loadConfig();
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
