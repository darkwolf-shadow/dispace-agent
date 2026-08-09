# Mangiafuoco

App mobile per catturare foto, audio, note e posizione dal telefono e inviarle al backend DiSpace. L'obiettivo è nutrire l'agente personale (OpenClaw/Steve) con memorie reali.

## Tecnologia

Costruita con **Capacitor**: la stessa app è un sito web (`www/`) che viene impacchettato come app Android.

## Installazione sviluppo

```bash
cd mangiafuoco
npm install
npx cap sync
```

## Aprire in Android Studio

```bash
npx cap open android
```

## Generare APK di debug

```bash
npx cap sync
cd android
./gradlew assembleDebug
```

L'APK si trova in `android/app/build/outputs/apk/debug/app-debug.apk`.

## Installare sul telefono via ADB

1. Abilita **Opzioni sviluppatore** e **Debug USB** sul telefono.
2. Collega il telefono al computer con il cavo USB.
3. Esegui:

```bash
adb devices
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

## Usare dal browser (test rapido)

I file in `www/` possono essere aperti anche dal browser su PC o telefono:

```bash
npx serve www
```

La fotocamera in browser potrebbe non funzionare su tutti i dispositivi; per il test completo serve la versione Android.

## Funzionalità attuali

- Scatta foto dalla fotocamera.
- Registra audio dal microfono.
- Trascrizione vocale diretta in nota.
- Scrive note testuali.
- Aggiunge tag e didascalia.
- Invia i dati al backend `/mangiafuoco/memories`.
- Invia anche al bot Telegram `@mangiafuocobot`.
- Mostra le memorie recenti.
- Hotword "Mangiafuoco" a schermo spento (app Android).
- Apri altre app, impostazioni e dialogo disinstallazione (app Android).

## Backend

L'app si appoggia al backend DiSpace su Railway:
`https://dispace-agent-production.up.railway.app/mangiafuoco/memories`

## Prossimi passi

- [x] Integrare invio diretto al bot Telegram.
- [x] Hotword "Mangiafuoco" e controllo telefono.
- [ ] Ricerca semantica sulle memorie.
- [ ] Elaborazione audio locale per ridurre i dati inviati.
- [ ] Possibilità di ospitare un piccolo agente in locale sul telefono.

## Documentazione per sviluppatori e agenti

- `AGENT_SETUP.md` — guida completa per installare Android Studio e buildare l'APK.
- `VOICE_AND_CONTROL.md` — architettura per hotword, comandi vocali e controllo del telefono, con i limiti tecnici.
