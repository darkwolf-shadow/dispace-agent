# Guida passo passo: mettere l'app su Railway

Questa guida ti spiega, passo dopo passo, come creare un account su Railway e mettere online l'applicazione DiSpace Lead Capture.

## Cosa ti serve

- Un indirizzo email.
- Un account GitHub (lo hai già).
- Il repository del progetto: `darkwolf-shadow/dispace-agent`.
- Circa 10 minuti di tempo.

## Passo 1: creare l'account su Railway

1. Apri il sito [https://railway.com](https://railway.com).
2. Clicca sul pulsante **"Get Started"** o **"Sign Up"** in alto a destra.
3. Scegli **"Continue with GitHub"**.
4. Autorizza Railway a leggere i tuoi repository.
5. Se ti chiede il piano, scegli il piano **"Free"** (o "Trial").

Dopo la registrazione vedrai la dashboard di Railway.

## Passo 2: creare un nuovo progetto

1. Dalla dashboard di Railway, clicca sul pulsante **"New Project"** (Nuovo progetto).
2. Scegli **"Deploy from GitHub repo"**.
3. Cerca e seleziona il repository `darkwolf-shadow/dispace-agent`.
4. Railway inizierà a scaricare il codice.

## Passo 3: scegliere il piano gratuito

1. Nella schermata del servizio, clicca su **Settings**.
2. Cerca la sezione **"Service Plan"**.
3. Seleziona il piano **"Free"** (0 euro al mese).
4. Conferma.

Con il piano gratuito hai circa 1 dollaro di credito mensile. Basta per tenere accesa una piccola applicazione come la nostra.

## Passo 4: impostare le variabili d'ambiente

Le variabili d'ambiente sono le impostazioni che Railway passa all'applicazione. Per configurarle:

1. Nella pagina del tuo servizio, clicca sulla scheda **"Variables"**.
2. Clicca su **"New Variable"** o **"+"**.
3. Inserisci le variabili una per una, come nella tabella sotto.
4. Alla fine clicca su **"Deploy"** per salvare e riavviare.

### Variabili da inserire

| Nome | Valore da inserire | Spiegazione |
|------|--------------------|-------------|
| `APP_USERNAME` | admin | L'utente per entrare nell'app. Puoi scegliere quello che vuoi. |
| `APP_PASSWORD` | una password sicura | La password per entrare nell'app. Scegli tu una password. |
| `DATABASE_URL` | `sqlite:////app/data/dispace.db` | Dove viene salvato il database. |
| `UPLOADS_DIR` | `/app/data/uploads` | Dove vengono salvate le foto dei biglietti. |
| `OPENROUTER_API_KEY` | (opzionale) | La chiave di OpenRouter per l'intelligenza artificiale. |
| `TAVILY_API_KEY` | (opzionale) | La chiave per la ricerca su internet. |
| `OPENAI_API_KEY` | (opzionale) | Se preferisci OpenAI al posto di OpenRouter. |

Non inserire spazi prima o dopo i valori.

## Passo 5: aggiungere il disco per i dati

Se non aggiungi un disco, i contatti e le foto vengono cancellati ogni volta che l'app si aggiorna.

1. Nella pagina del servizio, clicca sulla scheda **"Volumes"** (o "Storage").
2. Clicca su **"New Volume"**.
3. Scegli il percorso di montaggio: `/app/data`.
4. Scegli la dimensione **0,5 GB** (basta per iniziare).
5. Clicca su **"Save"**.

In questo modo tutti i dati e le immagini vengono salvati in modo permanente.

## Passo 6: avviare il deploy

1. Torna alla scheda **"Deploy"**.
2. Clicca sul pulsante **"Deploy"**.
3. Railway inizia a costruire l'immagine Docker. Questa fase può richiedere qualche minuto perché installa Tesseract e le librerie Python.
4. Quando lo stato diventa verde, l'applicazione è online.

## Passo 7: aprire l'applicazione

1. Nella scheda **"Deploy"** o **"Settings"**, cerca l'indirizzo assegnato a caso dal servizio, per esempio `nome-progetto.railway.app`.
2. Clicca sul link per aprirlo.
3. Vedi la pagina di login.
4. Inserisci l'utente e la password che hai scelto al passo 4.
5. Puoi usare l'applicazione dal telefono.

## Passo 8: collegare un dominio personale (opzionale, in futuro)

Quando vuoi, puoi collegare un sottodominio come `app.fattoriailcapitano.com`:

1. Compra o usa un dominio che possiedi.
2. Nel pannello di controllo del dominio (Aruba, Cloudflare, eccetera), crea un record di tipo **CNAME** che punta a `nome-progetto.railway.app`.
3. In Railway, nella sezione **"Settings" > "Domains"**, aggiungi il tuo dominio.
4. Attendi qualche minuto che si propaghino le modifiche.

## Cosa succede dopo

- Ogni volta che modifichi il codice e fai un push su GitHub, Railway aggiorna automaticamente l'app.
- Se il credito gratuito finisce, l'app si ferma fino al mese successivo.
- Se vuoi più risorse, puoi passare al piano "Hobby" (circa 5 dollari al mese).

## Costi stimati per iniziare

| Servizio | Costo mensile |
|----------|---------------|
| Piano Railway Free | 0 dollari |
| Volume da 0,5 GB | incluso nel piano Free |
| Traffico dati | incluso per piccoli volumi |
| Totale iniziale | 0 dollari |

## Domande frequenti

**Dove finiscono i miei dati?**
I dati sono salvati nel file SQLite dentro il disco `/app/data` del server Railway. Solo tu puoi accedervi tramite l'applicazione.

**Posso usare il telefono?**
Sì, apri l'indirizzo dal browser del telefono, inserisci login e password, e concedi il permesso della fotocamera.

**Posso usare più telefoni contemporaneamente?**
Sì, basta che ogni persona abbia l'utente e la password.

**Cosa succede se chiudo il browser?**
I dati restano salvati sul server. Quando riapri l'app e fai il login, trovi tutti i contatti.
