# Controllo vocale e accesso al telefono

## Obiettivo

Mangiafuoco deve poter essere attivato con comandi vocali su richiesta e poter controllare il telefono, ma senza rimanere sempre in ascolto in background.

## Cosa è implementato

### 1. Riconoscimento vocale con pulsante

- Pulsante **"Parla (testo)"**: trascrive in italiano e mette il testo nella didascalia.
- Pulsante **"Tieni premuto: comando vocale"**: tieni premuto, parla, rilascia. L'app esegue il comando senza lasciare il microfono acceso.

### 2. Comandi vocali riconosciuti

Dopo aver premuto e rilasciato il pulsante comandi, l'app cerca parole chiave nel testo:

- **"whatsapp"** → apre WhatsApp
- **"telegram"** → apre Telegram
- **"impostazioni"** / **"opzioni"** → apre le Impostazioni di Android
- **"foto"** / **"scatta"** → scatta una foto
- **"registra"** / **"audio"** → inizia a registrare un audio
- **"nota"** / **"scrivi"** → prepara una nota testuale
- **"disinstalla <package name>"** → apre il dialogo di disinstallazione
- **"mangiafuoco"** / **"apri"** → conferma ascolto

Il microfono si accende solo mentre tieni premuto il pulsante. Non c'è nessun servizio in background.

### 3. Controllo manuale del telefono

Plugin Capacitor nativo `MangiafuocoControl` con pulsanti per:

- `openApp({ packageName })`: apre un'app installata (es. `com.whatsapp`).
- `openSettings({ action })`: apre la schermata Impostazioni.
- `uninstallApp({ packageName })`: apre il dialogo di sistema per disinstallare un'app.

## Permessi Android necessari

- `RECORD_AUDIO`
- `CAMERA`
- `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION`
- `QUERY_ALL_PACKAGES` (per trovare app da aprire)

Non servono più permessi per servizi in foreground, wake lock o ascolto continuo.

## Limiti

- **Disinstallazione**: non può rimuovere app in silenzio; apre solo il dialogo di sistema e tu devi confermare.
- **Modificare impostazioni profonde**: senza root si può solo aprire la pagina giusta, non cambiare automaticamente i valori.
- **Riconoscimento vocale**: usa il sistema Android. Se non c'è il motore offline, può usare la rete.
