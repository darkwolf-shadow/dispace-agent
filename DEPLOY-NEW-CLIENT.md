# Come creare una nuova istanza per un altro cliente

Ogni azienda ha la propria installazione isolata. Questo garantisce dati separati e personalizzazione indipendente.

## Passaggi

1. **Fork del repository**
   - Vai su GitHub, apri `darkwolf-shadow/dispace-agent`.
   - Clicca **Fork** e scegli l'account del cliente o un account separato.

2. **Crea un nuovo progetto su Railway**
   - Accedi a [railway.com](https://railway.com).
   - Crea un nuovo progetto collegato al fork appena creato.
   - Scegli il piano gratuito o uno a pagamento in base alle esigenze.

3. **Configura le variabili d'ambiente**
   Nelle impostazioni del servizio, aggiungi:
   - `DATABASE_URL=sqlite:////app/data/dispace.db`
   - `UPLOADS_DIR=/app/data/uploads`
   - `OPENROUTER_API_KEY=<chiave del cliente>`
   - `TAVILY_API_KEY=<chiave del cliente>` (opzionale)
   - `APP_TITLE=Nome app del cliente`
   - `OWNER_NAME=Nome azienda cliente`
   - `DISABLE_AUTH=true` (solo in fase di prova)

4. **Aggiungi il volume**
   - Nella scheda **Volume** di Railway aggiungi un disco da almeno 0,5 GB.
   - Montalo su `/app/data`.

5. **Avvia il deploy**
   - Railway costruisce l'immagine Docker e avvia il backend.
   - Ottieni l'indirizzo pubblico e condividilo con il cliente.

6. **Personalizza il profilo azienda**
   - Apri l'app.
   - Compila la sezione **La mia azienda** con descrizione, prodotti, valori e tono.
   - Ora l'app genererà report e proposte commerciali coerenti con il nuovo cliente.

## Note

- Ogni istanza ha il proprio database e i propri file.
- I costi sono separati per ogni progetto Railway.
- Per rinnovare il modello o le istruzioni di vendita, basta aggiornare il profilo azienda senza toccare il codice.
