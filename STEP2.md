# Step 2 - Enrichment & Reporting

Questo branch aggiunge l’arricchimento automatico dei contatti e la generazione di report.

## Cosa include
- **Database**: nuovi campi `tags`, `score`, `report`, `source_links`, `social_links`, `enriched_at` sul modello `Contact`.
- **Web search**: integrazione Tavily (con `TAVILY_API_KEY`) e fallback su DuckDuckGo (`duckduckgo-search`).
- **Social enrichment**: rilevamento automatico di link LinkedIn, X/Twitter, Facebook, Instagram dai risultati di ricerca.
- **Report generator**: generazione di report testuali con OpenAI (`OPENAI_API_KEY`) oppure template statico.
- **Segmentazione base**: scoring del lead (0-100) e tag automatici in base alla completezza dei dati.
- **Endpoint API**:
  - `POST /contacts/{id}/enrich` - arricchisce un contatto e genera report.
  - `GET /contacts/{id}/report` - restituisce il report del contatto.
  - `GET /segments` - restituisce segmenti automatici (hot leads, enriched, tag counts).
- **Frontend**: pulsanti "Arricchisci" e "Report" per ogni contatto; visualizzazione score, tag e report.

## Variabili d’ambiente
Aggiungi al `.env`:
```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=          # opzionale, per endpoint compatibili OpenAI
OPENROUTER_API_KEY=sk-or-...
TAVILY_API_KEY=tvly-...
CLEARBIT_API_KEY=...
```
`OPENROUTER_API_KEY` ha la precedenza su `OPENAI_API_KEY` e usa `https://openrouter.ai/api/v1`.
Se nessuna chiave è configurata, l’enrichment usa DuckDuckGo e genera report statici.

## Note
- Il modello `JSONString` custom serializza `tags`, `source_links` e `social_links` come JSON nel database.
- Lo scoring è basico (completezza dati + arricchimento); in Step 3 si integrerà con intenti e engagement.
