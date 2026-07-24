const API = window.location.origin.includes('localhost') ? 'http://localhost:8000' : '';

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
    const res = await fetch(`${API}/upload`, { method: 'POST', body: formData });
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
    const res = await fetch(`${API}/contacts`, {
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

async function loadContacts() {
  try {
    const res = await fetch(`${API}/contacts`);
    const contacts = await res.json();
    contactsList.innerHTML = contacts.map(c => `
      <li>
        <strong>${c.name || 'Sconosciuto'}</strong>
        ${c.company ? `<span>${c.company}</span>` : ''}
        ${c.email ? `<br><small>${c.email}</small>` : ''}
        ${c.phone ? `<small> · ${c.phone}</small>` : ''}
      </li>
    `).join('');
  } catch (err) {
    contactsList.innerHTML = `<li>Errore caricamento: ${err.message}</li>`;
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

startCamera();
loadContacts();
