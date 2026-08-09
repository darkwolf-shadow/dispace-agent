# Controllo vocale e accesso al telefono

## Obiettivo

Mangiafuoco deve poter essere attivato da comandi vocali (es. "Mangiafuoco") e usare il microfono per registrare note, foto o comandi. Inoltre deve poter aprire altre app e le impostazioni del telefono.

## Cosa è implementato

### 1. Riconoscimento vocale con pulsante

- Pulsante **"Parla (testo)"**: usa `@capgo/capacitor-speech-recognition` (o Web Speech API nel browser) per trascrivere in italiano e mettere il testo nella didascalia.

### 2. Hotword "Mangiafuoco" a schermo spento

- Usa il modello offline **Vosk** (`vosk-model-small-it`) con un `MangiafuocoHotwordService` in foreground.
- Il servizio ascolta continuamente il microfono anche quando l'app è in background o lo schermo è spento.
- Quando il modello riconosce la parola **"mangiafuoco"**, il servizio:
  - manda un broadcast all'app;
  - riporta l'app in primo piano;
  - può avviare la registrazione vocale (configurabile in `app.js`).
- Il modello viene scaricato automaticamente da Gradle durante il primo build.

### 3. Controllo del telefono

Plugin Capacitor nativo `MangiafuocoControl` con metodi:

- `openApp({ packageName })`: apre un'app installata (es. `com.whatsapp`).
- `openSettings({ action })`: apre la schermata impostazioni di Android (o una schermata specifica).
- `uninstallApp({ packageName })`: apre il dialogo di disinstallazione di sistema per un'app.
- `startHotword({ keyword })` / `stopHotword()`: avvia/ferma l'ascolto hotword.

## Permessi Android necessari

- `RECORD_AUDIO`
- `CAMERA`
- `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION`
- `FOREGROUND_SERVICE` e `FOREGROUND_SERVICE_MICROPHONE`
- `WAKE_LOCK`
- `QUERY_ALL_PACKAGES` (per trovare e aprire altre app)
- `REQUEST_INSTALL_PACKAGES` (per installare aggiornamenti APK, opzionale)

## Limiti

- **Disinstallazione**: non può rimuovere app in silenzio; apre solo il dialogo di sistema e l'utente deve confermare.
- **Modificare impostazioni profonde**: senza root o permessi di sistema non si possono cambiare impostazioni automaticamente; si può solo aprire la pagina giusta.
- **Hotword Vosk**: funziona offline ma consuma più batteria di un motore hotword dedicato come Porcupine. In futuro si può sostituire con Porcupine per maggiore efficienza.

## Note tecniche

- Il plugin `MangiafuocoControl` è registrato manualmente in `MainActivity`.
- `MangiafuocoHotwordService` è un `Service` Android con `foregroundServiceType="microphone"` e notifica persistente.
- Il modello Vosk viene scaricato al primo build da `https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip` tramite un task Gradle in `app/build.gradle`.
