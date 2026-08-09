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
const btnSpeech = document.getElementById('btn-speech');
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

const MangiafuocoControl = window.Capacitor && Capacitor.registerPlugin ? Capacitor.registerPlugin('MangiafuocoControl') : null;
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

let speechListener = null;
let isSpeechNative = false;

async function startSpeech() {
  const native = window.Capacitor && Capacitor.isNativePlatform();
  if (native) {
    try {
      const SpeechRecognition = window.Capacitor.Plugins.SpeechRecognition;
      if (!SpeechRecognition) throw new Error('Plugin SpeechRecognition non trovato. Esegui npx cap sync.');
      isSpeechNative = true;
      const perm = await SpeechRecognition.requestPermissions();
      if (perm && perm.permission && perm.permission !== 'granted') {
        setStatus('Permesso microfono negato per il riconoscimento vocale.', true);
        return;
      }
      const { available } = await SpeechRecognition.available();
      if (!available) {
        setStatus('Riconoscimento vocale non disponibile su questo dispositivo.', true);
        return;
      }
      setStatus('Ascolto... parla ora');
      btnSpeech.textContent = 'Ferma';
      btnSpeech.onclick = stopSpeech;
      currentBlob = null;
      currentType = 'note';
      photoPreview.style.display = 'none';
      audioPreview.style.display = 'none';
      videoPreview.style.display = 'none';
      btnSend.disabled = true;
      captionInput.value = '';

      speechListener = await SpeechRecognition.addListener('partialResults', (event) => {
        const text = event.matches && event.matches[0] ? event.matches[0] : '';
        if (text) captionInput.value = text;
      });
      await SpeechRecognition.start({ language: 'it-IT', partialResults: true, popup: false });
    } catch (err) {
      setStatus('Errore riconoscimento vocale: ' + err.message, true);
      btnSpeech.textContent = 'Parla (testo)';
      btnSpeech.onclick = startSpeech;
    }
  } else {
    // Fallback Web Speech API for browser testing
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setStatus('Riconoscimento vocale non supportato nel browser.', true);
      return;
    }
    const recognition = new SR();
    recognition.lang = 'it-IT';
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onresult = (e) => {
      const transcript = Array.from(e.results)
        .map(r => r[0].transcript)
        .join('');
      captionInput.value = transcript;
    };
    recognition.onerror = (e) => setStatus('Errore: ' + e.error, true);
    recognition.onend = () => {
      currentType = 'note';
      btnSend.disabled = false;
      updatePreviewEmpty();
      setStatus('Trascrizione completata.');
      btnSpeech.textContent = 'Parla (testo)';
      btnSpeech.onclick = startSpeech;
    };
    setStatus('Ascolto... parla ora');
    currentType = 'note';
    photoPreview.style.display = 'none';
    audioPreview.style.display = 'none';
    videoPreview.style.display = 'none';
    recognition.start();
    btnSpeech.textContent = 'Ferma';
    btnSpeech.onclick = () => { recognition.stop(); };
  }
}

async function stopSpeech() {
  if (isSpeechNative) {
    try {
      const SpeechRecognition = window.Capacitor.Plugins.SpeechRecognition;
      await SpeechRecognition.stop();
      if (speechListener) {
        await speechListener.remove();
        speechListener = null;
      }
      setStatus('Trascrizione completata.');
      currentType = 'note';
      btnSend.disabled = false;
      updatePreviewEmpty();
    } catch (err) {
      setStatus('Errore stop: ' + err.message, true);
    }
  }
  btnSpeech.textContent = 'Parla (testo)';
  btnSpeech.onclick = startSpeech;
}

const btnVoiceCommand = document.getElementById('btn-voice-command');
const btnOpenWhatsapp = document.getElementById('btn-open-whatsapp');
const btnOpenSettings = document.getElementById('btn-open-settings');
const btnUninstall = document.getElementById('btn-uninstall');
const uninstallInput = document.getElementById('uninstall-package');
const controlStatus = document.getElementById('control-status');

function setControlStatus(msg, isError = false) {
  if (controlStatus) {
    controlStatus.textContent = msg;
    controlStatus.className = 'status ' + (isError ? 'error' : '');
  }
}

let voiceCommandListener = null;
let voiceCommandRecognizer = null;

function normalizeText(text) {
  return text.toLowerCase()
    .replace(/[^a-zàèéìòù0-9\s]/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
}

async function executeCommand(text) {
  const cmd = normalizeText(text);
  setControlStatus('Comando: "' + cmd + '"');

  if (cmd.includes('whatsapp')) {
    if (!MangiafuocoControl) { setControlStatus('Solo app Android.', true); return; }
    await MangiafuocoControl.openApp({ packageName: 'com.whatsapp' });
    setControlStatus('Apertura WhatsApp...');
  } else if (cmd.includes('telegram')) {
    if (!MangiafuocoControl) { setControlStatus('Solo app Android.', true); return; }
    await MangiafuocoControl.openApp({ packageName: 'org.telegram.messenger' });
    setControlStatus('Apertura Telegram...');
  } else if (cmd.includes('impostazioni') || cmd.includes('opzioni')) {
    if (!MangiafuocoControl) { setControlStatus('Solo app Android.', true); return; }
    await MangiafuocoControl.openSettings({});
    setControlStatus('Apertura Impostazioni...');
  } else if (cmd.includes('foto') || cmd.includes('scatta')) {
    await takePhoto();
    setControlStatus('Scatto foto...');
  } else if (cmd.includes('registra') || cmd.includes('audio')) {
    await startRecording();
    setControlStatus('Registrazione audio...');
  } else if (cmd.includes('nota') || cmd.includes('scrivi')) {
    addNote();
    captionInput.focus();
    setControlStatus('Pronto per la nota.');
  } else if (cmd.includes('disinstalla') || cmd.includes('elimina')) {
    if (!MangiafuocoControl) { setControlStatus('Solo app Android.', true); return; }
    const words = cmd.split(' ');
    const idx = words.findIndex(w => w === 'disinstalla' || w === 'elimina');
    const pkg = words.slice(idx + 1).join(' ').trim();
    if (pkg) {
      await MangiafuocoControl.uninstallApp({ packageName: pkg.replace(/\s/g, '') });
      setControlStatus('Apertura dialogo disinstallazione per ' + pkg);
    } else {
      setControlStatus('Ripeti: "disinstalla" seguito dal package name.', true);
    }
  } else if (cmd.includes('mangiafuoco') || cmd.includes('apri')) {
    setControlStatus('Sono qui. Cosa facciamo?');
  } else {
    setControlStatus('Comando non riconosciuto: "' + cmd + '"', true);
  }
}

async function startVoiceCommand() {
  if (!window.Capacitor) { setControlStatus('Comandi vocali solo nell\\'app Android.', true); return; }
  try {
    const SpeechRecognition = window.Capacitor.Plugins.SpeechRecognition;
    if (!SpeechRecognition) throw new Error('Plugin SpeechRecognition non trovato.');

    const perm = await SpeechRecognition.requestPermissions();
    if (perm && perm.permission && perm.permission !== 'granted') {
      setControlStatus('Permesso microfono negato.', true);
      return;
    }
    const { available } = await SpeechRecognition.available();
    if (!available) {
      setControlStatus('Riconoscimento vocale non disponibile.', true);
      return;
    }

    setControlStatus('Tieni premuto e parla...');
    btnVoiceCommand.textContent = 'Sto ascoltando...';
    btnVoiceCommand.classList.add('listening');

    voiceCommandListener = await SpeechRecognition.addListener('partialResults', (event) => {
      const text = event.matches && event.matches[0] ? event.matches[0] : '';
      if (text) setControlStatus('Ascolto: ' + text);
    });

    await SpeechRecognition.start({ language: 'it-IT', partialResults: true, popup: false });
  } catch (err) {
    setControlStatus('Errore: ' + err.message, true);
    btnVoiceCommand.textContent = 'Tieni premuto: comando vocale';
    btnVoiceCommand.classList.remove('listening');
  }
}

async function stopVoiceCommand() {
  if (!window.Capacitor) return;
  try {
    const SpeechRecognition = window.Capacitor.Plugins.SpeechRecognition;
    if (voiceCommandListener) {
      await voiceCommandListener.remove();
      voiceCommandListener = null;
    }
    const result = await SpeechRecognition.stop();
    const text = result && result.matches && result.matches[0] ? result.matches[0] : '';
    if (text) {
      setControlStatus('Hai detto: ' + text);
      await executeCommand(text);
    } else {
      setControlStatus('Nessun comando rilevato.');
    }
  } catch (err) {
    setControlStatus('Errore stop: ' + err.message, true);
  }
  btnVoiceCommand.textContent = 'Tieni premuto: comando vocale';
  btnVoiceCommand.classList.remove('listening');
}

// Browser fallback for voice command (hold button + Web Speech API)
function startBrowserVoiceCommand() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { setControlStatus('Riconoscimento vocale non supportato.', true); return; }
  voiceCommandRecognizer = new SR();
  voiceCommandRecognizer.lang = 'it-IT';
  voiceCommandRecognizer.interimResults = true;
  voiceCommandRecognizer.continuous = false;
  voiceCommandRecognizer.onerror = (e) => setControlStatus('Errore: ' + e.error, true);
  voiceCommandRecognizer.onend = async () => {
    const text = voiceCommandRecognizer && voiceCommandRecognizer.lastResult ? voiceCommandRecognizer.lastResult : '';
    if (text) await executeCommand(text);
    btnVoiceCommand.textContent = 'Tieni premuto: comando vocale';
    btnVoiceCommand.classList.remove('listening');
  };
  voiceCommandRecognizer.onresult = (e) => {
    const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
    voiceCommandRecognizer.lastResult = transcript;
    setControlStatus('Ascolto: ' + transcript);
  };
  voiceCommandRecognizer.start();
  btnVoiceCommand.textContent = 'Sto ascoltando...';
  btnVoiceCommand.classList.add('listening');
  setControlStatus('Tieni premuto e parla...');
}

function stopBrowserVoiceCommand() {
  if (voiceCommandRecognizer) {
    voiceCommandRecognizer.stop();
    voiceCommandRecognizer = null;
  }
}

async function openWhatsapp() {
  if (!MangiafuocoControl) { setControlStatus('Solo app Android.', true); return; }
  try { await MangiafuocoControl.openApp({ packageName: 'com.whatsapp' }); setControlStatus('Apertura WhatsApp...'); } catch (err) { setControlStatus(err.message, true); }
}

async function openSettings() {
  if (!MangiafuocoControl) { setControlStatus('Solo app Android.', true); return; }
  try { await MangiafuocoControl.openSettings({}); setControlStatus('Apertura impostazioni...'); } catch (err) { setControlStatus(err.message, true); }
}

async function uninstallPackage() {
  if (!MangiafuocoControl) { setControlStatus('Solo app Android.', true); return; }
  const pkg = uninstallInput && uninstallInput.value.trim();
  if (!pkg) { setControlStatus('Inserisci un package name.', true); return; }
  try { await MangiafuocoControl.uninstallApp({ packageName: pkg }); setControlStatus('Apertura dialogo disinstallazione...'); } catch (err) { setControlStatus(err.message, true); }
}

btnPhoto.addEventListener('click', takePhoto);
btnAudio.addEventListener('click', startRecording);
btnSpeech.addEventListener('click', startSpeech);
btnNote.addEventListener('click', addNote);
btnSend.addEventListener('click', sendMemory);
btnCancel.addEventListener('click', resetPreview);
btnRefresh.addEventListener('click', loadMemories);
if (btnClearPreview) btnClearPreview.addEventListener('click', resetPreview);
if (btnOpenWhatsapp) btnOpenWhatsapp.addEventListener('click', openWhatsapp);
if (btnOpenSettings) btnOpenSettings.addEventListener('click', openSettings);
if (btnUninstall) btnUninstall.addEventListener('click', uninstallPackage);

if (btnVoiceCommand) {
  const isNative = window.Capacitor && Capacitor.isNativePlatform();
  const start = (e) => { e.preventDefault(); if (isNative) startVoiceCommand(); else startBrowserVoiceCommand(); };
  const stop = (e) => { e.preventDefault(); if (isNative) stopVoiceCommand(); else stopBrowserVoiceCommand(); };
  btnVoiceCommand.addEventListener('pointerdown', start);
  btnVoiceCommand.addEventListener('pointerup', stop);
  btnVoiceCommand.addEventListener('pointerleave', stop);
  btnVoiceCommand.addEventListener('pointercancel', stop);
}

loadMemories();
