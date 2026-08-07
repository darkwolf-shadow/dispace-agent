# Architettura proposta: telefono come sensore esteso per l'agente

## Obiettivo

Trasformare lo smartphone in un "sensore esteso" per l'agente AI (OpenClaw/Steve):
- Catturare foto, audio brevi, video clip, posizione GPS e note vocali.
- Estrarre informazioni rilevanti direttamente sul telefono o sul server.
- Alimentare un database RAG (Retrieval-Augmented Generation) reale per l'agente.
- Mantenere separati l'archivio aziendale (contatti, biglietti, documenti) e il RAG di memoria/agente.

## Differenza rispetto a DiSpace Lead Capture

| Aspetto | DiSpace esistente | Nuova app di memoria |
|---------|-------------------|----------------------|
| Tipo | PWA sul browser | App nativa sul telefono |
| Dati | Biglietti da visita, volantini, note manuali | Foto, audio, video, GPS, contesto quotidiano |
| Scopo | Lead generation e marketing | Arricchire la memoria dell'agente |
| Trigger | Utente scatta o carica | Utente avvia una cattura (non sorveglianza continua) |
| Backend | Railway + SQLite | Stesso Railway, ma con vettori per RAG |

## Architettura generale

```
┌──────────────────────────────────────────────────────────────────────┐
│                         SMARTPHONE                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Fotocamera   │  │ Microfono    │  │ GPS          │              │
│  └───────┬──────┘  └───────┬──────┘  └───────┬──────┘              │
│          │                 │                 │                       │
│  ┌───────▼─────────────────▼─────────────────▼──────┐              │
│  │  App mobile (Flutter / React Native / Capacitor) │              │
│  │   - Acquisizione su richiesta                     │              │
│  │   - OCR on-device (ML Kit)                        │              │
│  │   - Speech-to-text on-device (Whisper tiny/ML Kit)│              │
│  │   - Compressione e metadati                        │              │
│  └─────────────────────┬─────────────────────────────┘              │
└──────────────────────┼──────────────────────────────────────────────┘
                       │
                       ▼ HTTP/REST o WebSocket
┌──────────────────────────────────────────────────────────────────────┐
│                         BACKEND (Railway)                            │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  FastAPI                                                     │   │
│  │   - Riceve snippet testuali, foto, audio, metadati          │   │
│  │   - Estrae entità, summary, tags con LLM                     │   │
│  │   - Salva su SQLite/Postgres                                │   │
│  └──────────────────────┬───────────────────────────────────────┘   │
│                         │                                            │
│  ┌──────────────────────▼──────────────────────────────────────┐   │
│  │  Vector DB (ChromaDB / FAISS / pgvector)                    │   │
│  │   - Indicizza testo e metadati per ricerca semantica        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  DiSpace Lead Capture (esistente)                          │   │
│  │   - Contatti, note, documenti, profilo azienda             │   │
│  └────────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼ API
┌──────────────────────────────────────────────────────────────────────┐
│                         AGENTE (OpenClaw / Steve)                    │
│  - Interroga il RAG delle memorie                                    │
│  - Combina memorie con conoscenza azienda e contatti                 │
│  - Risponde su Telegram/Discord                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Componenti principali

### 1. App mobile

L'app deve essere **nativa** (Flutter, React Native o Kotlin/Swift) perché una PWA non può:
- accedere a tutti i sensori in background;
- catturare audio/video continuamente;
- comprimere file prima dell'upload in modo efficiente.

Funzionalità:
- Pulsante per avviare/fermare una sessione di cattura.
- Cattura foto e video brevi.
- Registrazione audio con durata configurabile (es. 30-60 secondi).
- Lettura GPS e timestamp.
- OCR locale per estrarre testo dalle immagini.
- Speech-to-text locale per trascrivere audio.
- Invio dei dati estratti (testo + metadati + eventuale media compresso) al backend.

### 2. Backend

Endpoint proposti:
- `POST /memories` — riceve un nuovo snippet (testo, audio, immagine, metadati).
- `GET /memories?q=...` — ricerca semantica.
- `GET /memories/{id}` — dettaglio memoria.
- `DELETE /memories/{id}` — elimina memoria.
- `POST /memories/{id}/summarize` — rigenera riassunto.

Modello dati proposto (`Memory`):
- `id`, `type` (photo, audio, video, note, location)
- `text` (testo estratto o trascrizione)
- `summary` (riassunto generato da LLM)
- `entities` (persone, luoghi, oggetti estratti)
- `tags`
- `gps_lat`, `gps_lon`
- `created_at`, `source_device`
- `media_url` (opzionale, per immagini/audio compressi)
- `embedding` (vettore per ricerca semantica)

### 3. Vector DB / RAG

- Usare **ChromaDB** o **FAISS** per semplicità su Railway (poco spazio).
- Oppure **pgvector** se si passa a PostgreSQL.
- Gli embedding si generano con modelli leggeri (`sentence-transformers/all-MiniLM-L6-v2` o via API OpenAI/Ollama).

### 4. Integrazione con Telegram/Discord

- Il telefono può inviare direttamente al bot Telegram già esistente (Steve).
- Il backend può avere un webhook che riceve i messaggi dal bot.
- L'agente interroga il backend per recuperare memorie rilevanti.

### 5. Integrazione con DiSpace esistente

- Aggiungere un endpoint condiviso `/rag` o `/knowledge`.
- DiSpace continua a gestire contatti, note, marketing.
- La nuova app alimenta il RAG di memoria quotidiana.
- L'agente può interrogare entrambi: contatti aziendali + memorie personali.

## Ottimizzazione dati

Per non saturare Railway (500 MB):
- Non inviare flussi video continui.
- Sul telefono si estrae testo/audio e si invia solo:
  - testo trascrito/estratto;
  - metadati (GPS, timestamp, tags);
  - thumbnail o foto compressa, non video interi.
- I video/audio grezzi restano sul telefono o vengono eliminati dopo l'estrazione.

## Privacy e consenso

- L'utente deve premere un pulsante per catturare: nessuna registrazione continua nascosta.
- I dati sono archiviati in modo personale e separati da quelli aziendali.
- Possibilità di cancellare singole memorie o tutto l'archivio.

## Strada consigliata per iniziare

1. **Fase 1**: creare un'app mobile minima (anche solo Android) con:
   - pulsante "Cattura foto + descrizione";
   - pulsante "Registra audio 30s";
   - invio a un endpoint `/memories` su Railway.
2. **Fase 2**: backend che riceve i dati, li riassume con LLM e li indicizza in ChromaDB.
3. **Fase 3**: agente OpenClaw/Steve interroga `/memories?q=...` per rispondere in base alla memoria.
4. **Fase 4**: integrazione con DiSpace per combinare memorie personali e dati aziendali.

## Tecnologie consigliate

| Componente | Tecnologia consigliata |
|------------|------------------------|
| App mobile | Flutter o React Native |
| OCR on-device | Google ML Kit |
| Speech-to-text | Whisper tiny on-device o ML Kit Speech |
| Backend | FastAPI (stesso di DiSpace) |
| Database | SQLite + ChromaDB (iniziale) |
| Embedding | `sentence-transformers` via API o locale |
| LLM | OpenRouter / Gemini |
| Comunicazione agente | Telegram bot / REST API |

## Domande aperte

1. Vuoi che l'app mobile sia un'app Android nativa o una PWA avanzata?
2. I dati devono essere personali (solo per te) o condivisibili con l'azienda?
3. Preferisci inviare i dati al backend Railway o direttamente al bot Telegram?
4. Quanto spazio/archiviazione sul telefono è accettabile?
