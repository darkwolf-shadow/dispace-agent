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
const notesSection = document.getElementById('notes-section');
const noteForm = document.getElementById('note-form');
const btnCloseNotes = document.getElementById('btn-close-notes');
const socialSection = document.getElementById('social-section');
const socialForm = document.getElementById('social-form');
const socialFile = document.getElementById('social-file');
const socialPlatform = document.getElementById('social-platform');
const socialPreview = document.getElementById('social-preview');
const socialImagePreview = document.getElementById('social-image-preview');
const socialCaption = document.getElementById('social-caption');
const socialHashtags = document.getElementById('social-hashtags');
const btnSaveSocial = document.getElementById('btn-save-social');
const btnApproveSocial = document.getElementById('btn-approve-social');
const btnPublishSocial = document.getElementById('btn-publish-social');
const btnCancelSocial = document.getElementById('btn-cancel-social');
const btnRefreshSocial = document.getElementById('btn-refresh-social');
const socialCredentialSelect = document.getElementById('social-credential');
const socialPostsList = document.getElementById('social-posts-list');
const credentialForm = document.getElementById('credential-form');
const credPlatform = document.getElementById('cred-platform');
const credLabel = document.getElementById('cred-label');
const credToken = document.getElementById('cred-token');
const credExtra = document.getElementById('cred-extra');
const credentialsList = document.getElementById('credentials-list');

let currentBlob = null;
let currentContactId = null;
let currentSocialPostId = null;

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

async function loadNotes() {
  if (!currentContactId) return;
  try {
    const res = await apiFetch(`${API}/contacts/${currentContactId}/notes`);
    if (!res.ok) throw new Error(await res.text());
    const notes = await res.json();
    const list = document.getElementById('notes-list');
    if (!notes.length) {
      list.innerHTML = '<p>Nessuna nota.</p>';
      return;
    }
    list.innerHTML = notes.map(n => `
      <div class="note-item">
        <strong>${n.note_type}</strong> <small>${new Date(n.created_at).toLocaleString()}</small>
        <p>${n.content || ''}</p>
        ${n.file_path ? `<small>File: ${n.file_path.split('/').pop()}</small>` : ''}
        <button onclick="deleteNote(${n.id})">Elimina</button>
      </div>
    `).join('');
  } catch (err) {
    console.error('Errore note:', err.message);
  }
}

async function saveNote(e) {
  e.preventDefault();
  if (!currentContactId) return;
  const formData = new FormData();
  formData.append('note_type', document.getElementById('note-type').value);
  formData.append('content', document.getElementById('note-content').value);
  const file = document.getElementById('note-file').files[0];
  if (file) formData.append('file', file);
  try {
    const res = await apiFetch(`${API}/contacts/${currentContactId}/notes`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error(await res.text());
    document.getElementById('note-content').value = '';
    document.getElementById('note-file').value = '';
    await loadNotes();
  } catch (err) {
    alert('Errore nota: ' + err.message);
  }
}

window.showNotes = async function(id) {
  currentContactId = id;
  notesSection.style.display = 'block';
  await loadNotes();
};

window.deleteNote = async function(noteId) {
  if (!currentContactId || !confirm('Vuoi eliminare questa nota?')) return;
  try {
    const res = await apiFetch(`${API}/contacts/${currentContactId}/notes/${noteId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    await loadNotes();
  } catch (err) {
    alert('Errore eliminazione nota: ' + err.message);
  }
};

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
            ${hasFeature('enrich') ? `<button onclick="enrichContact(${c.id})">Arricchisci</button>` : ''}
            ${hasFeature('report') ? `<button onclick="showReport(${c.id})">Report</button>` : ''}
            <button onclick="showNotes(${c.id})">Note</button>
            ${hasFeature('proposal') ? `<button onclick="generateForContact(${c.id}, 'proposal')">Proposta</button>` : ''}
            ${hasFeature('whatsapp') ? `<button onclick="generateForContact(${c.id}, 'whatsapp')">WhatsApp</button>` : ''}
            ${hasFeature('story') ? `<button onclick="generateForContact(${c.id}, 'story')">Story</button>` : ''}
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

let socialCredentials = [];

async function loadSocialCredentials() {
  try {
    const res = await apiFetch(`${API}/social-credentials`);
    if (!res.ok) throw new Error(await res.text());
    socialCredentials = await res.json();
    credentialsList.innerHTML = socialCredentials.map(c => `
      <li><strong>${c.platform}</strong> ${c.label || ''} <small>${c.extra || ''}</small>
        <button class="btn-danger" onclick="deleteCredential(${c.id})">Elimina</button>
      </li>
    `).join('');
    populateCredentialSelect();
  } catch (err) {
    credentialsList.innerHTML = `<li>Errore: ${err.message}</li>`;
  }
}

function populateCredentialSelect() {
  if (!socialCredentialSelect) return;
  const platform = socialPlatform.value;
  socialCredentialSelect.innerHTML = socialCredentials
    .filter(c => c.platform === platform)
    .map(c => `<option value="${c.id}">${c.label || c.platform} ${c.extra || ''}</option>`)
    .join('');
}

window.deleteCredential = async function(id) {
  if (!confirm('Eliminare credenziale?')) return;
  try {
    const res = await apiFetch(`${API}/social-credentials/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    await loadSocialCredentials();
  } catch (err) { alert('Errore: ' + err.message); }
};

async function saveCredential(e) {
  e.preventDefault();
  const data = {
    platform: credPlatform.value,
    label: credLabel.value,
    access_token: credToken.value,
    extra: credExtra.value,
  };
  try {
    const res = await apiFetch(`${API}/social-credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    credentialForm.reset();
    await loadSocialCredentials();
  } catch (err) { alert('Errore credenziale: ' + err.message); }
}

async function publishSocialPost() {
  if (!currentSocialPostId) return;
  const credentialId = socialCredentialSelect.value;
  if (!credentialId) { alert('Seleziona una credenziale social'); return; }
  try {
    await saveSocialPost();
    const res = await apiFetch(`${API}/social-posts/${currentSocialPostId}/publish?credential_id=${credentialId}`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    alert('Pubblicato! Risposta: ' + JSON.stringify(data.result));
    await loadSocialPosts();
  } catch (err) {
    alert('Errore pubblicazione: ' + err.message);
  }
}

if (socialPlatform) socialPlatform.addEventListener('change', populateCredentialSelect);

async function generateSocialPost(e) {
  e.preventDefault();
  const file = socialFile.files[0];
  if (!file) { alert('Seleziona una foto o un video'); return; }
  const formData = new FormData();
  formData.append('platform', socialPlatform.value);
  formData.append('media_type', file.type.startsWith('video') ? 'video' : 'image');
  formData.append('file', file);
  try {
    const res = await apiFetch(`${API}/social-posts`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error(await res.text());
    const post = await res.json();
    currentSocialPostId = post.id;
    socialCaption.value = post.caption || '';
    socialHashtags.value = post.hashtags || '';
    if (file.type.startsWith('image')) {
      socialImagePreview.src = URL.createObjectURL(file);
      socialImagePreview.style.display = 'block';
    } else {
      socialImagePreview.style.display = 'none';
    }
    socialPreview.style.display = 'block';
    await loadSocialPosts();
  } catch (err) {
    alert('Errore generazione social: ' + err.message);
  }
}

async function saveSocialPost() {
  if (!currentSocialPostId) return;
  const data = {
    caption: socialCaption.value,
    hashtags: socialHashtags.value,
  };
  try {
    const res = await apiFetch(`${API}/social-posts/${currentSocialPostId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    alert('Bozza salvata');
    await loadSocialPosts();
  } catch (err) {
    alert('Errore salvataggio: ' + err.message);
  }
}

async function approveSocialPost() {
  if (!currentSocialPostId) return;
  await saveSocialPost();
  try {
    const res = await apiFetch(`${API}/social-posts/${currentSocialPostId}/approve`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    alert('Post approvato. Per ora non è pubblicato automaticamente: puoi copiare testo e immagine.')
    await loadSocialPosts();
  } catch (err) {
    alert('Errore approvazione: ' + err.message);
  }
}

function resetSocialForm() {
  socialPreview.style.display = 'none';
  socialImagePreview.style.display = 'none';
  socialForm.reset();
  currentSocialPostId = null;
}

async function loadSocialPosts() {
  try {
    const res = await apiFetch(`${API}/social-posts`);
    if (!res.ok) throw new Error(await res.text());
    const posts = await res.json();
    socialPostsList.innerHTML = posts.map(p => `
      <li>
        <strong>${p.platform}</strong> - ${p.status}
        <br><small>${p.created_at}</small>
        <p>${(p.caption || '').substring(0, 80)}...</p>
        ${p.media_path ? `<button onclick="viewSocialPost(${p.id})">Apri</button>` : ''}
        <button class="btn-danger" onclick="deleteSocialPost(${p.id})">Elimina</button>
      </li>
    `).join('');
  } catch (err) {
    socialPostsList.innerHTML = `<li>Errore: ${err.message}</li>`;
  }
}

window.viewSocialPost = async function(id) {
  try {
    const res = await apiFetch(`${API}/social-posts`);
    if (!res.ok) throw new Error(await res.text());
    const posts = await res.json();
    const post = posts.find(p => p.id === id);
    if (!post) return;
    currentSocialPostId = post.id;
    socialPlatform.value = post.platform;
    socialCaption.value = post.caption || '';
    socialHashtags.value = post.hashtags || '';
    if (post.media_path) {
      socialImagePreview.src = `${API}/${post.media_path}`;
      socialImagePreview.style.display = 'block';
    }
    socialPreview.style.display = 'block';
    window.scrollTo(0, socialPreview.offsetTop);
  } catch (err) {
    alert('Errore: ' + err.message);
  }
};

window.deleteSocialPost = async function(id) {
  if (!confirm('Vuoi eliminare questo post?')) return;
  try {
    const res = await apiFetch(`${API}/social-posts/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    await loadSocialPosts();
  } catch (err) {
    alert('Errore eliminazione: ' + err.message);
  }
};

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

if (noteForm) noteForm.addEventListener('submit', saveNote);
if (btnCloseNotes) btnCloseNotes.addEventListener('click', () => { notesSection.style.display = 'none'; });

if (socialForm) socialForm.addEventListener('submit', generateSocialPost);
if (btnSaveSocial) btnSaveSocial.addEventListener('click', saveSocialPost);
if (btnApproveSocial) btnApproveSocial.addEventListener('click', approveSocialPost);
if (btnPublishSocial) btnPublishSocial.addEventListener('click', publishSocialPost);
if (btnCancelSocial) btnCancelSocial.addEventListener('click', resetSocialForm);
if (btnRefreshSocial) btnRefreshSocial.addEventListener('click', loadSocialPosts);
if (credentialForm) credentialForm.addEventListener('submit', saveCredential);

const loginSection = document.getElementById('login-section');
const mainApp = document.getElementById('main-app');
const btnLogin = document.getElementById('btn-login');
const loginError = document.getElementById('login-error');

let appFeatures = [];

function hasFeature(feature) {
  return appFeatures.includes(feature);
}

function applyPlanUI(cfg) {
  const companyBtn = document.getElementById('btn-open-company');
  if (companyBtn) companyBtn.style.display = hasFeature('company_profile') ? 'inline-block' : 'none';
  const marketingSection = document.getElementById('marketing-section');
  if (marketingSection) marketingSection.style.display = hasFeature('campaigns') ? 'block' : 'none';
  const socialSection = document.getElementById('social-section');
  if (socialSection) socialSection.style.display = hasFeature('social_scheduler') ? 'block' : 'none';
}

async function loadConfig() {
  try {
    const res = await apiFetch(`${API}/config`);
    if (!res.ok) return;
    const cfg = await res.json();
    appFeatures = cfg.features || [];
    const titleEl = document.querySelector('header h1');
    if (titleEl && cfg.app_title) titleEl.textContent = cfg.app_title;
    const ownerEl = document.getElementById('owner-name');
    if (ownerEl && cfg.owner_name) ownerEl.textContent = cfg.owner_name;
    applyPlanUI(cfg);
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
  loadSocialPosts();
  loadSocialCredentials();
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
