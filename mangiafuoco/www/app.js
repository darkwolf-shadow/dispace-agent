const API = 'https://dispace-agent-production.up.railway.app';

const previewBox = document.getElementById('preview-box');
const photoPreview = document.getElementById('photo-preview');
const audioPreview = document.getElementById('audio-preview');
const videoPreview = document.getElementById('video-preview');
const previewEmpty = document.getElementById('preview-empty');
const recordingIndicator = document.getElementById('recording-indicator');
const recordingTimer = document.getElementById('recording-timer');
const recordingProgress = document.getElementById('recording-progress');
const captionInput = document.getElementById('caption');
const tagsInput = document.getElementById('tags');
const btnPhoto = document.getElementById('btn-photo');
const btnAudio = document.getElementById('btn-audio');
const btnNote = document.getElementById('btn-note');
const btnSend = document.getElementById('btn-send');
const btnCancel = document.getElementById('btn-cancel');
const btnRefresh = document.getElementById('btn-refresh');
const btnClearPreview = document.getElementById('btn-clear-preview');
const sendTelegram = document.getElementById('send-telegram');
const statusEl = document.getElementById('status');
const memoriesList = document.getElementById('memories-list');

let currentBlob = null;
let currentType = null;
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let recordingInterval = null;

const MAX_RECORDING_SECONDS = 60;

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.className = 'status ' + (isError ? 'error' : '');
}

function updatePreviewEmpty() {
  const hasPreview = photoPreview.style.display !== 'none' ||
    audioPreview.style.display !== 'none' ||
    videoPreview.style.display !== 'none' ||
    currentType === 'note';
  previewEmpty.style.display = hasPreview ? 'none' : 'block';
  btnClearPreview.style.display = hasPreview ? 'inline-block' : 'none';
}

function resetPreview() {
  currentBlob = null;
  currentType = null;
  photoPreview.style.display = 'none';
  photoPreview.src = '';
  audioPreview.style.display = 'none';
  audioPreview.src = '';
  videoPreview.style.display = 'none';
  videoPreview.src = '';
  captionInput.value = '';
  tagsInput.value = '';
  if (sendTelegram) sendTelegram.checked = false;
  btnSend.disabled = true;
  setStatus('');
  updatePreviewEmpty();
}

async function takePhoto() {
  try {
    let blob = null;
    if (window.Capacitor && Capacitor.isNativePlatform()) {
      const { Camera } = await import('@capacitor/camera');
      const photo = await Camera.getPhoto({
        resultType: 'uri',
        source: 'CAMERA',
        quality: 85,
      });
      const res = await fetch(photo.webPath);
      blob = await res.blob();
    } else {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.capture = 'environment';
      input.onchange = async () => {
        blob = input.files[0];
        await showBlob(blob, 'image');
      };
      input.click();
      return;
    }
    if (blob) await showBlob(blob, 'image');
  } catch (err) {
    setStatus('Errore fotocamera: ' + err.message, true);
  }
}

async function showBlob(blob, type) {
  currentBlob = blob;
  currentType = type;
  const url = URL.createObjectURL(blob);
  if (type === 'image') {
    photoPreview.src = url;
    photoPreview.style.display = 'block';
    audioPreview.style.display = 'none';
    videoPreview.style.display = 'none';
  } else if (type === 'audio') {
    audioPreview.src = url;
    audioPreview.style.display = 'block';
    photoPreview.style.display = 'none';
    videoPreview.style.display = 'none';
  } else if (type === 'video') {
    videoPreview.src = url;
    videoPreview.style.display = 'block';
    photoPreview.style.display = 'none';
    audioPreview.style.display = 'none';
  }
  btnSend.disabled = false;
  updatePreviewEmpty();
}

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const s = (totalSeconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      await showBlob(blob, 'audio');
      stream.getTracks().forEach(t => t.stop());
      stopRecordingUI();
    };
    mediaRecorder.start(1000);
    startRecordingUI();
  } catch (err) {
    setStatus('Errore microfono: ' + err.message, true);
  }
}

function startRecordingUI() {
  recordingStartTime = Date.now();
  recordingIndicator.style.display = 'flex';
  recordingTimer.textContent = '00:00';
  recordingProgress.style.width = '0%';
  btnAudio.textContent = 'Ferma registrazione';
  btnAudio.onclick = stopRecording;
  setStatus('Registrazione in corso...');
  recordingInterval = setInterval(() => {
    const elapsed = Date.now() - recordingStartTime;
    recordingTimer.textContent = formatTime(elapsed);
    const pct = Math.min((elapsed / (MAX_RECORDING_SECONDS * 1000)) * 100, 100);
    recordingProgress.style.width = pct + '%';
    if (elapsed >= MAX_RECORDING_SECONDS * 1000) {
      stopRecording();
    }
  }, 500);
}

function stopRecordingUI() {
  if (recordingInterval) clearInterval(recordingInterval);
  recordingInterval = null;
  recordingIndicator.style.display = 'none';
  btnAudio.textContent = 'Registra audio';
  btnAudio.onclick = startRecording;
  setStatus('Registrazione completata.');
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
}

function addNote() {
  currentBlob = null;
  currentType = 'note';
  photoPreview.style.display = 'none';
  audioPreview.style.display = 'none';
  videoPreview.style.display = 'none';
  btnSend.disabled = false;
  updatePreviewEmpty();
  setStatus('Scrivi la nota e premi Invia.');
  captionInput.focus();
}

async function sendMemory() {
  const caption = captionInput.value.trim();
  const tags = tagsInput.value.trim();
  if (!currentBlob && currentType !== 'note') {
    setStatus('Nessun contenuto da inviare', true);
    return;
  }
  if (currentType === 'note' && !caption) {
    setStatus('Scrivi una nota prima di inviare', true);
    return;
  }

  const formData = new FormData();
  formData.append('type', currentType);
  formData.append('caption', caption);
  formData.append('tags', tags);
  formData.append('source', 'mangiafuoco');
  formData.append('send_to_telegram', sendTelegram.checked ? 'true' : 'false');
  if (currentBlob) {
    const ext = currentType === 'image' ? 'jpg' : 'webm';
    formData.append('file', currentBlob, `capture.${ext}`);
  }

  setStatus('Invio in corso...');
  btnSend.disabled = true;
  try {
    const res = await fetch(`${API}/mangiafuoco/memories`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    setStatus('Memoria inviata! ID: ' + data.id);
    resetPreview();
    await loadMemories();
  } catch (err) {
    setStatus('Errore invio: ' + err.message, true);
    btnSend.disabled = false;
  }
}

async function loadMemories() {
  try {
    const res = await fetch(`${API}/mangiafuoco/memories`);
    if (!res.ok) throw new Error(await res.text());
    const items = await res.json();
    memoriesList.innerHTML = items.map(m => `
      <li>
        <strong>${m.type}</strong> <small>${new Date(m.created_at).toLocaleString()}</small>
        <p>${(m.caption || '').substring(0, 80)}...</p>
        ${m.tags ? `<small>tag: ${m.tags}</small>` : ''}
      </li>
    `).join('');
  } catch (err) {
    memoriesList.innerHTML = '<li>Errore caricamento: ' + err.message + '</li>';
  }
}

btnPhoto.addEventListener('click', takePhoto);
btnAudio.addEventListener('click', startRecording);
btnNote.addEventListener('click', addNote);
btnSend.addEventListener('click', sendMemory);
btnCancel.addEventListener('click', resetPreview);
btnRefresh.addEventListener('click', loadMemories);
if (btnClearPreview) btnClearPreview.addEventListener('click', resetPreview);

loadMemories();
