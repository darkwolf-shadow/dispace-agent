# Controllo vocale e accesso al telefono

## Obiettivo

Mangiafuoco deve poter essere attivato da comandi vocali (es. "Hey Mangiafuoco" o "Hey Steve") e usare il microfono per registrare note, foto o comandi.

## Cosa si può fare subito

### 1. Riconoscimento vocale con pulsante (già presente)

- Tieni premuto o premi "Registra audio".
- Parla.
- Il testo trascritto viene inviato come memoria.

### 2. Hotword "Hey Mangiafuoco" a schermo spento

Serve un plugin nativo che ascolti continuamente il microfono. Opzioni:

- **@capacitor-community/porcupine-wake-word**: motore hotword offline di Picovoice. Richiede un file `.ppn` per ogni parola chiave. Gratis per sviluppo personale.
- **Servizio Android in foreground**: implementazione nativa con `SpeechRecognizer` o Porcupine che tiene il microfono attivo e avvia l'app.

Requisiti:

- Permesso `RECORD_AUDIO`.
- Permesso `FOREGROUND_SERVICE` e `FOREGROUND_SERVICE_MICROPHONE` (Android 14+).
- Impostare un servizio in background per ascoltare anche con schermo spento.
- Limitazione: Android blocca l'accesso al microfono da processi in background pesanti; serve un servizio foreground con notifica.

### 3. Eseguire comandi sul telefono

Da un'app Android si può:

- **Aprire altre app**: usando `Intent` con il package name (es. aprire WhatsApp, Fotocamera).
- **Leggere lo schermo / cliccare automaticamente**: richiede un `AccessibilityService` che l'utente deve attivare manualmente in **Impostazioni → Accessibilità**.
- **Modificare impostazioni rapide**: richiede `WRITE_SETTINGS` o `WRITE_SECURE_SETTINGS`, concesso solo ad app di sistema o con ADB.
- **Disinstallare altre app**: normalmente non permesso. Si può solo aprire la pagina di disinstallazione di sistema.
- **Cancellare file/cronologia/cache**: richiede permessi di archiviazione, ma non si possono cancellare dati di altre app.

## Cosa NON si può fare senza permessi speciali

- Disinstallare app di sistema.
- Modificare impostazioni profonde del sistema senza root.
- Controllare il telefono completamente senza che l'utente confermi.

## Roadmap suggerita

1. **Fase A** (ora): hotword con pulsante e riconoscimento vocale.
2. **Fase B**: hotword a schermo spento con Porcupine + servizio foreground.
3. **Fase C**: `AccessibilityService` per leggere e interagire con altre app (su richiesta esplicita).
4. **Fase D**: comandi avanzati (apri app, impostazioni) tramite `Intent`.

## Plugin da integrare

- `@capgo/capacitor-speech-recognition` per riconoscimento vocale.
- `@capacitor-community/porcupine-wake-word` per hotword offline.

## Nota legale/privacy

L'ascolto continuo e il controllo del telefono devono essere chiaramente comunicati all'utente. Android richiede notifiche visibili per servizi in background che usano microfono.
