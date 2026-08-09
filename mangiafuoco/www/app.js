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
let audioChunks = [];
let recordingStartTime = null;
let recordingInterval = null;
let isAudioRecording = false;
let isSpeechListening = false;
let isNativeAudioRecording = false;
let speechListener = null;
let voiceCommandListener = null;
let voiceCommandRecognizer = null;

const MAX_RECORDING_SECONDS = 60;

function isNative() {
  return typeof window !== 'undefined' && !!window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function' && window.Capacitor.isNativePlatform();
}

function getNativePlugin(name) {
  if (!isNative()) return null;
  const cap = window.Capacitor;
  const plugins = cap.Plugins || {};
  if (plugins[name]) return plugins[name];
  if (typeof cap.registerPlugin === 'function') return cap.registerPlugin(name);
  return null;
}

const MangiafuocoControl = getNativePlugin('MangiafuocoControl');

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

function base64ToBlob(base64, mimeType) {
  const byteString = atob(base64);
  const ab = new ArrayBuffer(byteString.length);
  const ia = new Uint8Array(ab);
  for (let i = 0; i < byteString.length; i++) {
    ia[i] = byteString.charCodeAt(i);
  }
  return new Blob([ab], { type: mimeType });
}

async function takePhoto() {
  try {
    let blob = null;
    if (isNative()) {
      const Camera = getNativePlugin('Camera');
      if (!Camera) throw new Error('Plugin fotocamera non trovato. Esegui npx cap sync e ricompila l\'app.');
      const photo = await Camera.getPhoto({
        resultType: 'uri',
        source: 'CAMERA',
        quality: 85,
      });
      if (!photo || !photo.webPath) throw new Error('Nessuna foto catturata.');
      const res = await fetch(photo.webPath);
      blob = await res.blob();
      if (blob) await showBlob(blob, 'image');
    } else {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.capture = 'environment';
      input.style.position = 'fixed';
      input.style.opacity = '0';
      input.style.top = '-1000px';
      input.style.left = '-1000px';
      document.body.appendChild(input);
      input.addEventListener('change', async (ev) => {
        const files = ev.target.files || input.files;
        if (files && files[0]) {
          await showBlob(files[0], 'image');
        }
        document.body.removeChild(input);
      }, { once: true });
      input.click();
    }
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

function getSupportedMimeType() {
  const types = ['audio/webm', 'audio/mp4', 'audio/mpeg', 'audio/ogg'];
  if (typeof MediaRecorder === 'undefined') return null;
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return null;
}

async function toggleAudio() {
  if (isAudioRecording) {
    await stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  try {
    if (isNative()) {
      const VoiceRecorder = getNativePlugin('VoiceRecorder');
      if (!VoiceRecorder) throw new Error('Registratore audio nativo non trovato. Esegui npx cap sync e ricompila l\'app.');
      const can = await VoiceRecorder.canDeviceVoiceRecord();
      if (!can || !can.value) throw new Error('Questo dispositivo non può registrare audio.');
      const perm = await VoiceRecorder.requestAudioRecordingPermission();
      if (!perm || !perm.value) throw new Error('Permesso microfono negato. Abilitalo nelle impostazioni dell\'app.');
      await VoiceRecorder.startRecording();
      isNativeAudioRecording = true;
      isAudioRecording = true;
      startRecordingUI();
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Microfono non supportato in questo browser.');
    }
    if (typeof MediaRecorder === 'undefined') {
      throw new Error('Registrazione audio non supportata su questo dispositivo. Prova dall\'app Android.');
    }
    const mimeType = getSupportedMimeType();
    if (!mimeType) {
      throw new Error('Nessun formato audio supportato dal browser.');
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType });
    audioChunks = [];
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: mimeType });
      await showBlob(blob, 'audio');
      stream.getTracks().forEach(t => t.stop());
    };
    mediaRecorder.onerror = (e) => {
      setStatus('Errore registrazione: ' + e.message, true);
    };
    mediaRecorder.start(1000);
    isNativeAudioRecording = false;
    isAudioRecording = true;
    startRecordingUI();
  } catch (err) {
    isAudioRecording = false;
    setStatus('Errore microfono: ' + err.message, true);
    stopRecordingUI();
  }
}

async function stopRecording() {
  try {
    if (isNative() && isNativeAudioRecording) {
      const VoiceRecorder = getNativePlugin('VoiceRecorder');
      if (!VoiceRecorder) throw new Error('Registratore audio nativo non trovato.');
      const result = await VoiceRecorder.stopRecording();
      const value = result && result.value ? result.value : {};
      if (value.recordDataBase64) {
        const mimeType = value.mimeType || 'audio/aac';
        const blob = base64ToBlob(value.recordDataBase64, mimeType);
        await showBlob(blob, 'audio');
      } else if (value.path) {
        const res = await fetch(value.path);
        const blob = await res.blob();
        await showBlob(blob, 'audio');
      } else {
        throw new Error('Nessun audio registrato.');
      }
    } else if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  } catch (err) {
    setStatus('Errore arresto registrazione: ' + err.message, true);
  }
  isAudioRecording = false;
  isNativeAudioRecording = false;
  stopRecordingUI();
}

function startRecordingUI() {
  recordingStartTime = Date.now();
  recordingIndicator.style.display = 'flex';
  recordingTimer.textContent = '00:00';
  recordingProgress.style.width = '0%';
  btnAudio.textContent = 'Ferma registrazione';
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
  if (!statusEl.className.includes('error')) {
    setStatus('Registrazione completata.');
  }
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

function getFileExtension() {
  if (currentType === 'image') return 'jpg';
  if (!currentBlob || !currentBlob.type) return 'webm';
  const type = currentBlob.type.toLowerCase();
  if (type.includes('aac') || type.includes('mp4')) return 'm4a';
  if (type.includes('webm')) return 'webm';
  if (type.includes('ogg')) return 'ogg';
  if (type.includes('wav')) return 'wav';
  return 'webm';
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
    const ext = getFileExtension();
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

async function toggleSpeech() {
  if (isSpeechListening) {
    await stopSpeech();
  } else {
    await startSpeech();
  }
}

async function startSpeech() {
  try {
    isSpeechListening = true;
    btnSpeech.textContent = 'Ferma';
    if (isNative()) {
      const SpeechRecognition = getNativePlugin('SpeechRecognition');
      if (!SpeechRecognition) throw new Error('Plugin riconoscimento vocale non trovato. Esegui npx cap sync.');
      const perm = await SpeechRecognition.requestPermissions();
      const status = perm && (perm.speechRecognition || perm.permission);
      if (status && status !== 'granted') {
        throw new Error('Permesso microfono negato per la dettatura.');
      }
      const available = await SpeechRecognition.available();
      if (!available || !available.available) {
        throw new Error('Riconoscimento vocale non disponibile su questo dispositivo.');
      }
      setStatus('Ascolto... parla ora');
      currentBlob = null;
      currentType = 'note';
      photoPreview.style.display = 'none';
      audioPreview.style.display = 'none';
      videoPreview.style.display = 'none';
      btnSend.disabled = true;
      captionInput.value = '';

      speechListener = await SpeechRecognition.addListener('partialResults', (event) => {
        const text = event && event.matches && event.matches[0] ? event.matches[0] : '';
        if (text) captionInput.value = text;
      });
      await SpeechRecognition.start({ language: 'it-IT', partialResults: true, popup: false });
    } else {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        throw new Error('Riconoscimento vocale non supportato nel browser.');
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
        isSpeechListening = false;
        btnSpeech.textContent = 'Dettatura vocale';
        currentType = 'note';
        btnSend.disabled = false;
        updatePreviewEmpty();
        setStatus('Trascrizione completata.');
      };
      setStatus('Ascolto... parla ora');
      currentType = 'note';
      photoPreview.style.display = 'none';
      audioPreview.style.display = 'none';
      videoPreview.style.display = 'none';
      recognition.start();
    }
  } catch (err) {
    isSpeechListening = false;
    btnSpeech.textContent = 'Dettatura vocale';
    setStatus('Errore riconoscimento vocale: ' + err.message, true);
  }
}

async function stopSpeech() {
  try {
    if (isNative()) {
      const SpeechRecognition = getNativePlugin('SpeechRecognition');
      if (SpeechRecognition) {
        await SpeechRecognition.stop();
      }
      if (speechListener) {
        await speechListener.remove();
        speechListener = null;
      }
    }
  } catch (err) {
    setStatus('Errore stop: ' + err.message, true);
  }
  isSpeechListening = false;
  btnSpeech.textContent = 'Dettatura vocale';
  setStatus('Trascrizione completata.');
  currentType = 'note';
  btnSend.disabled = false;
  updatePreviewEmpty();
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
  if (!isNative()) { setControlStatus('Comandi vocali solo nell\'app Android.', true); return; }
  try {
    const SpeechRecognition = getNativePlugin('SpeechRecognition');
    if (!SpeechRecognition) throw new Error('Plugin riconoscimento vocale non trovato.');

    const perm = await SpeechRecognition.requestPermissions();
    const status = perm && (perm.speechRecognition || perm.permission);
    if (status && status !== 'granted') {
      setControlStatus('Permesso microfono negato.', true);
      return;
    }
    const available = await SpeechRecognition.available();
    if (!available || !available.available) {
      setControlStatus('Riconoscimento vocale non disponibile.', true);
      return;
    }

    setControlStatus('Tieni premuto e parla...');
    btnVoiceCommand.textContent = 'Sto ascoltando...';
    btnVoiceCommand.classList.add('listening');

    voiceCommandListener = await SpeechRecognition.addListener('partialResults', (event) => {
      const text = event && event.matches && event.matches[0] ? event.matches[0] : '';
      if (text) setControlStatus('Ascolto: ' + text);
    });

    await SpeechRecognition.start({ language: 'it-IT', partialResults: true, popup: false });
  } catch (err) {
    setControlStatus('Errore: ' + err.message, true);
    btnVoiceCommand.textContent = 'Comando vocale (tieni premuto)';
    btnVoiceCommand.classList.remove('listening');
  }
}

async function stopVoiceCommand() {
  if (!isNative()) return;
  try {
    const SpeechRecognition = getNativePlugin('SpeechRecognition');
    if (voiceCommandListener) {
      await voiceCommandListener.remove();
      voiceCommandListener = null;
    }
    if (SpeechRecognition) {
      const result = await SpeechRecognition.stop();
      const text = result && result.matches && result.matches[0] ? result.matches[0] : '';
      if (text) {
        setControlStatus('Hai detto: ' + text);
        await executeCommand(text);
      } else {
        setControlStatus('Nessun comando rilevato.');
      }
    }
  } catch (err) {
    setControlStatus('Errore stop: ' + err.message, true);
  }
  btnVoiceCommand.textContent = 'Comando vocale (tieni premuto)';
  btnVoiceCommand.classList.remove('listening');
}

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
    btnVoiceCommand.textContent = 'Comando vocale (tieni premuto)';
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
  if (isNative()) {
    if (!MangiafuocoControl) { setControlStatus('Controllo telefono non disponibile.', true); return; }
    try { await MangiafuocoControl.openApp({ packageName: 'com.whatsapp' }); setControlStatus('Apertura WhatsApp...'); } catch (err) { setControlStatus(err.message, true); }
  } else {
    window.open('https://wa.me/', '_blank');
    setControlStatus('Apertura WhatsApp nel browser...');
  }
}

async function openSettings() {
  if (isNative()) {
    if (!MangiafuocoControl) { setControlStatus('Controllo telefono non disponibile.', true); return; }
    try { await MangiafuocoControl.openSettings({}); setControlStatus('Apertura impostazioni...'); } catch (err) { setControlStatus(err.message, true); }
  } else {
    setControlStatus('Impostazioni del telefono apribili solo dall\'app Android.', true);
  }
}

async function uninstallPackage() {
  if (isNative()) {
    if (!MangiafuocoControl) { setControlStatus('Controllo telefono non disponibile.', true); return; }
    const pkg = uninstallInput && uninstallInput.value.trim();
    if (!pkg) { setControlStatus('Inserisci un package name.', true); return; }
    try { await MangiafuocoControl.uninstallApp({ packageName: pkg }); setControlStatus('Apertura dialogo disinstallazione...'); } catch (err) { setControlStatus(err.message, true); }
  } else {
    setControlStatus('Disinstallazione disponibile solo dall\'app Android.', true);
  }
}

btnPhoto.addEventListener('click', takePhoto);
btnAudio.addEventListener('click', toggleAudio);
btnSpeech.addEventListener('click', toggleSpeech);
btnNote.addEventListener('click', addNote);
btnSend.addEventListener('click', sendMemory);
btnCancel.addEventListener('click', resetPreview);
btnRefresh.addEventListener('click', loadMemories);
if (btnClearPreview) btnClearPreview.addEventListener('click', resetPreview);
if (btnOpenWhatsapp) btnOpenWhatsapp.addEventListener('click', openWhatsapp);
if (btnOpenSettings) btnOpenSettings.addEventListener('click', openSettings);
if (btnUninstall) btnUninstall.addEventListener('click', uninstallPackage);

if (btnVoiceCommand) {
  const start = (e) => { e.preventDefault(); if (isNative()) startVoiceCommand(); else startBrowserVoiceCommand(); };
  const stop = (e) => { e.preventDefault(); if (isNative()) stopVoiceCommand(); else stopBrowserVoiceCommand(); };
  btnVoiceCommand.addEventListener('pointerdown', start);
  btnVoiceCommand.addEventListener('pointerup', stop);
  btnVoiceCommand.addEventListener('pointerleave', stop);
  btnVoiceCommand.addEventListener('pointercancel', stop);
}

loadMemories();
