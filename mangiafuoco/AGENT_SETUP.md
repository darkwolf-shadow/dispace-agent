# Istruzioni per gli agenti: build APK con Android Studio

Questa guida serve a un agente (Devin Web, Devin locale, Claude, ecc.) per installare Android Studio, aprire il progetto Mangiafuoco e buildare l'APK.

## Prerequisiti

- Windows, macOS o Linux con almeno 8 GB di RAM.
- Connessione internet.
- Repo `darkwolf-shadow/dispace-agent`, branch `step3-marketing`.

## 1. Clona il repo

```bash
git clone https://github.com/darkwolf-shadow/dispace-agent.git
cd dispace-agent/mangiafuoco
```

## 2. Installa Node.js e npm

Usa la versione LTS consigliata: Node 20.

- Windows: scarica da https://nodejs.org/dist/v20.19.0/node-v20.19.0-x64.msi
- macOS/Linux: usare `nvm` o il package manager di sistema.

Verifica:

```bash
node -v
npm -v
```

## 3. Installa dipendenze Capacitor

```bash
npm install
```

## 4. Installa Android Studio

- Scarica da https://developer.android.com/studio
- Installa con le impostazioni predefinite.
- Durante il primo avvio, installa:
  - Android SDK
  - Android SDK Platform
  - Android Virtual Device (opzionale, per testare)

## 5. Sincronizza la piattaforma Android

```bash
npx cap sync
```

## 6. Apri il progetto in Android Studio

```bash
npx cap open android
```

Se `npx cap open` non funziona, apri manualmente la cartella `mangiafuoco/android` in Android Studio.

## 7. Builda l'APK di debug

Da Android Studio:

1. Attendi il sync Gradle.
2. Menu: **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
3. L'APK finisce in `mangiafuoco/android/app/build/outputs/apk/debug/app-debug.apk`.

Da terminale (dentro `mangiafuoco/android`):

```bash
./gradlew assembleDebug
```

Su Windows PowerShell:

```powershell
.\gradlew.bat assembleDebug
```

## 8. Installa l'APK sul telefono

### Via cavo USB e ADB

1. Sul telefono: **Impostazioni → Informazioni sul telefono → premi 7 volte Numero build** per attivare le opzioni sviluppatore.
2. Entra in **Opzioni sviluppatore** e attiva **Debug USB**.
3. Collega il telefono al PC con il cavo USB.
4. Da Android Studio premi **Run** (icona triangolo verde) oppure da terminale:

```bash
adb devices
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Su Windows PowerShell:

```powershell
adb devices
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

### Via file condiviso

1. Copia `app-debug.apk` sul telefono (email, Telegram, Google Drive, cavo).
2. Sul telefono apri il file e conferma l'installazione.
3. Se richiesto, permetti l'installazione da "fonti sconosciute".

## 9. Aggiornare l'app dopo modifiche

Se cambi i file web (`mangiafuoco/www`), esegui:

```bash
npx cap sync
```

Poi builda e reinstalla l'APK.

## Note

- Se Gradle chiede di accettare licenze, esegui `sdkmanager --licenses` dalla cartella `sdk`.
- Se Android Studio segnala errori su Java, imposta JDK 17 in **File → Settings → Build, Execution, Deployment → Build Tools → Gradle → Gradle JDK**.
