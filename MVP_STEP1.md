# Step 1 - MVP Capture

Questo branch contiene lo scaffold e il primo MVP della piattaforma DiSpace.

## Cosa include
- **Backend** FastAPI con endpoint per upload biglietti da visita, OCR, estrazione contatti e salvataggio in PostgreSQL.
- **Frontend** PWA base con accesso camera, scatto, upload file e visualizzazione contatti.
- **Docker Compose** per avviare backend, database PostgreSQL e Redis.

## Avvio rapido

1. Copia `.env.example` in `.env` e opzionalmente inserisci `OPENAI_API_KEY`.
2. Avvia i servizi:
   ```bash
   docker-compose up --build
   ```
3. Apri il browser su `http://localhost:8000`.

## Endpoint principali
- `POST /upload` - carica un'immagine e restituisce il contatto estratto.
- `POST /contacts` - crea un contatto manualmente.
- `GET /contacts` - lista contatti.
- `GET /contacts/{id}` - dettaglio contatto.
- `GET /health` - health check.

## Note
- L'OCR usa Tesseract (installato nel container backend).
- L'estrazione dei campi è basata su regex; se si configura `OPENAI_API_KEY`, si può estendere con GPT-4o.
- Il frontend è montato come volume in `/app/frontend` e servito dal backend.

## Prossimi step
- Integrare estrazione con LLM per accuratezza superiore.
- Aggiungere enrichment web/social.
- Aggiungere autenticazione utente e gestione eventi.
