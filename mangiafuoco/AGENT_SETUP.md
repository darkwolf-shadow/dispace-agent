# Istruzioni per gli agenti: build APK con Android Studio

Questa guida serve a un agente (Devin Web, Devin locale, Claude, ecc.) per installare Android Studio, aprire il progetto Mangiafuoco e buildare l'APK.

## Prerequisiti

- Windows, macOS o Linux con almeno 8 GB di RAM.
- Connessione internet.
- Repo `darkwolf-shadow/dispace-agent`, branch `master`.

## 1. Clona il repo

```bash
git clone https://github.com/darkwolf-shadow/dispace-agent.git
cd dispace-agent/mangiafuoco
```

## 2. Installa Node.js e npm

Usa la versione LTS richiesta: Node 22 (Capacitor 8.5+ richiede Node >= 22).

- Windows: scarica da https://nodejs.org/dist/v22.18.0/node-v22.18.0-x64.msi
- macOS/Linux: usare `nvm` o il package manager di sistema (`nvm install 22`).

Verifica:

```bash
node -v   # deve essere v22.x
npm -v
```

## 3. Installa dipendenze Capacitor

```bash
npm install --legacy-peer-deps
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

Se da errori di permessi o di `minSdk`, controlla che `mangiafuoco/android/variables.gradle` abbia `minSdkVersion = 24`.

## 6. Apri il progetto in Android Studio

```bash
npx cap open android
```

Se `npx cap open` non funziona, apri manualmente la cartella `mangiafuoco/android` in Android Studio.

## 7. Builda l'APK di debug

Da Android Studio:

1. Se Gradle chiede di aggiornare Android Gradle Plugin (AGP), accetta.
2. Attendi il sync Gradle (scarica le dipendenze al primo avvio).
3. Menu: **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
4. L'APK finisce in `mangiafuoco/android/app/build/outputs/apk/debug/app-debug.apk`.

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

- **Nessun servizio in background**: l'app non ascolta continuamente. Il microfono si attiva solo mentre premi e tieni premuto il pulsante **"Comando vocale (tieni premuto)"**.
- Permessi richiesti dall'app:
  - **Microfono** (per registrazione audio, dettatura e comando vocale)
  - **Fotocamera** (per scattare foto)
  - **Posizione** (opzionale, per geotag nelle memorie)
  - **Cerca app installate** (`QUERY_ALL_PACKAGES`, per aprire app come WhatsApp e gestire il telefono)
- Dopo l'installazione, apri l'app e concedi tutti i permessi richiesti.
- **Comandi vocali**: tieni premuto il pulsante "Comando vocale", pronuncia una frase chiave (es. "apri WhatsApp", "foto", "impostazioni"), rilascia.
- **Disinstalla app**: inserisci il *package name* (es. `com.facebook.katana`) e premi il pulsante corrispondente.
- Se Gradle chiede di accettare licenze, esegui `sdkmanager --licenses` dalla cartella `sdk`.
- Se Android Studio segnala errori su Java, imposta JDK 21 in **File → Settings → Build, Execution, Deployment → Build Tools → Gradle → Gradle JDK** (il plugin voice recorder richiede Java 21).
