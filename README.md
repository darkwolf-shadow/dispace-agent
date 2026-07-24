# Piattaforma Lead Capture AI per Eventi

## Visione
Una piattaforma mobile-first che permette a team commerciali di catturare lead durante eventi, fiere e incontri scansionando biglietti da visita o documenti con la fotocamera del telefono. L’AI estrae i dati rilevanti, li arricchisce con informazioni web e social, costruisce un profilo e genera proposte commerciali, contenuti di marketing e azioni di contatto (email, WhatsApp, social).

## Obiettivi
- Cattura zero-friction da camera del telefono.
- Estrazione dati accurata con OCR + LLM.
- Enrichment automatico: web, social, aziende.
- Segmentazione per preferenze, abitudini e buyer persona.
- Generazione proposte commerciali, mail, WhatsApp, stories Instagram, annunci social.
- Gestione campagne e pubblicità per la ditta proprietaria.

## Architettura generale

```text
[Mobile / Web App] --(foto/documento)--> [API Gateway / Backend]
                                      |
                                      v
                          [OCR Engine + AI Extraction]
                                      |
                                      v
                          [Database + File Storage]
                                      |
                    +-----------------+-----------------+
                    |                 |                 |
              [Web Search]      [Social Enrichment]  [Segmentation]
                    |                 |                 |
                    +-----------------+-----------------+
                                      |
                              [Profiling & Report]
                                      |
                    +-----------------+-----------------+
              [Content Gen]    [Campaign Mgmt]    [Ads Orchestration]
                    |                 |                 |
                    v                 v                 v
             [Mail/Stories]    [WhatsApp/SMS]    [Social Ads APIs]
```

## Flussi input/output

### Input
1. **Camera del telefono**: foto di biglietti da visita, documenti, brochure, QR code.
2. **Upload file**: PDF, JPG, PNG, vCard.
3. **Inserimento manuale**: dati inseriti da operatore.
4. **Integrazioni**: API CRM, event registration, badge scanner.

### Output
1. **Contatto qualificato** con dati strutturati (nome, azienda, ruolo, email, telefono, sito, indirizzo).
2. **Report soggetto/azienda** aggiornato con web, social, news, attività.
3. **Segmentazione**: tag, punteggio lead, preferenze, abitudini, buyer persona.
4. **Proposte commerciali** generate automaticamente.
5. **Contenuti**: mail personalizzate, messaggi WhatsApp, stories Instagram, post social.
6. **Campagne**: mailing list, sequenze, campagne social e ads (Meta, LinkedIn, X, Google Ads).
7. **Dashboard**: analytics, KPI, pipeline lead.

## Stack tecnologico consigliato

### Frontend
- **Progressive Web App (PWA)**: React + Vite + TypeScript + Workbox.
  - Accesso camera via MediaDevices API.
  - Offline sync e installazione come app.
- **Alternativa nativa**: **Expo (React Native)** per accesso nativo camera, push e store.

### Backend
- **Python 3.12 + FastAPI**: API ad alte prestazioni, OpenAPI automatico.
- **Celery + Redis**: task asincroni (OCR, enrichment, content generation).
- **SQLAlchemy / Pydantic**: modelli dati e validazione.
- **Alembic**: migrazioni database.

### OCR & AI Extraction
- **Tesseract OCR** (open source) per riconoscimento testo base.
- **Google Cloud Vision API** o **Azure AI Document Intelligence** per OCR avanzato su biglietti da visita.
- **OpenAI GPT-4o / GPT-4 Vision** o **Anthropic Claude 3.5 Sonnet** per estrazione strutturata campi.
- **LayoutLM / Donut** come modelli open/locali opzionali.

### Database & Storage
- **PostgreSQL 16** con **pgvector** per dati strutturati ed embedding semantici.
- **Redis**: cache, coda, sessioni.
- **MinIO / AWS S3**: storage immagini e documenti.

### Web & Social Enrichment
- **Tavily API**, **SerpAPI**, **Bing Web Search API** per ricerca web.
- **Clearbit**, **Apollo.io**, **Hunter.io** per dati aziendali e contatti.
- **LinkedIn Sales Navigator / API** (richiede partnership), **Meta Graph API**, **X API v2**, **Instagram Basic Display**.
- **Playwright / Scrapy** per scraping etico con proxy rotanti (Bright Data, Oxylabs) **solo dove consentito dai ToS**.

### Segmentazione & Profiling
- **scikit-learn** per clustering e scoring.
- **pgvector + OpenAI/Anthropic embeddings** per similarità semantica.
- **n8n / Make.com** per workflow di segmentazione.

### Content Generation & Marketing Automation
- **OpenAI / Anthropic** per copywriting mail, proposte, post.
- **SendGrid / Mailgun** per email transazionali e newsletter.
- **WhatsApp Business API** (via Meta Business, Twilio o 360dialog) per messaggi.
- **Canva API**, **Adobe APIs** o strumenti grafici generativi per stories/post.
- **Buffer / Hootsuite / Meta Marketing API** per publishing social.
- **HubSpot / ActiveCampaign / Brevo** per marketing automation.

### AI Agents
- **LangChain / LangGraph** per orchestrazione agenti.
- **crewAI** per workflow multi-agente (ricercatore, copywriter, advertiser).
- **AutoGen** come alternativa Microsoft.

### DevOps
- **Docker + Docker Compose** in sviluppo.
- **GitHub Actions** per CI/CD.
- **Prometheus + Grafana** o **Langfuse / Langsmith** per monitoraggio AI.
- **Sentry** per error tracking.

## Moduli funzionali

### 1. Capture Module
- Accesso camera Web/MediaDevices API.
- Scatto automatico quando rileva un rettangolo (edge detection).
- Preview, crop manuale, multi-page.
- Salvataggio su S3 con metadati.

### 2. OCR & Data Extraction
- Rilevamento lingua, correzione skew, binarizzazione.
- Estrazione campi: nome, cognome, azienda, ruolo, email, telefono, sito, indirizzo, LinkedIn.
- Validazione email/telefono, normalizzazione indirizzi.
- Feedback umano per correzioni (active learning).

### 3. Enrichment Engine
- Ricerca web del soggetto/azienda.
- Raccolta dati da social (LinkedIn, X, Instagram, Facebook).
- Estrazione logo, colori aziendali, settore, dipendenti, fatturato.
- Aggregazione news e attività recenti.

### 4. Profiling & Segmentation
- Calcolo lead score (BANT, intenti, engagement).
- Tag automatici (settore, ruolo, geografia, interessi).
- Clustering per campagne.
- Ricerca similitudini nel database storico.

### 5. Proposal & Content Generator
- Template proposte commerciali personalizzabili.
- Generazione testo con LLM dati azienda + lead.
- A/B test di varianti.
- Anteprima e approvazione umana.

### 6. Campaign & Ads Manager
- Mailing list dinamiche (filtri per tag, data, evento).
- Sequenze email e WhatsApp (drip campaigns).
- Pianificazione post/stories Instagram.
- Integrazione API pubblicitarie Meta, LinkedIn, Google Ads per creazione/ottimizzazione campagne.

### 7. Admin & Analytics
- Dashboard eventi, lead, conversioni.
- ROI campagne.
- Report esportabili (PDF, CSV, Excel).
- Gestione utenti e permessi.

## Sicurezza, privacy e compliance
- Cifratura at-rest e in-transit (TLS 1.3).
- Consenso GDPR per acquisizione e trattamento dati.
- Anonimizzazione dati sensibili in log.
- Retention policy configurabile.
- Audit trail.
- Consent management per marketing (opt-in/opt-out).

## Roadmap

### Fase 0 - Discovery (settimane 1-2)
- Workshop requisiti, scelta stack definitiva, analisi costi API.
- Definizione flussi utente e wireframe.
- Setup progetto, repo, CI/CD, ambiente dev.

### Fase 1 - MVP Capture (settimane 3-6)
- PWA con accesso camera.
- Upload e storage documenti.
- OCR base (Tesseract / Google Vision).
- Estrazione campi con LLM.
- Salvataggio contatti in PostgreSQL.
- Dashboard base.

### Fase 2 - Enrichment & Reporting (settimane 7-12)
- Integrazione web search.
- Social enrichment (LinkedIn, X, Instagram, Facebook).
- Report automatico soggetto/azienda.
- Segmentazione base e lead scoring.
- GDPR & privacy.

### Fase 3 - Marketing Automation (settimane 13-18)
- Generazione proposte commerciali.
- Templating email e WhatsApp.
- Mailing list dinamiche.
- Sequenze di contatto.
- Integrazione CRM (HubSpot, Pipedrive, Salesforce).

### Fase 4 - Content & Social Ads (settimane 19-26)
- Generazione contenuti social (Instagram stories, post).
- WhatsApp Business API broadcast.
- Integrazione Meta Marketing API / LinkedIn Ads.
- A/B testing e ottimizzazione.
- Agenti IA per orchestrazione campagne.

### Fase 5 - Scale & Optimize (settimane 27+)
- Mobile app nativa (Expo).
- Modelli LLM fine-tuned/fine-tuning locale.
- Analytics avanzate e forecasting.
- Multi-tenant e white-label.
- Integrazioni marketplace.

## Stima costi operativi mensili (indicativa, a scalare)

| Voce | Costo indicativo mensile |
|------|--------------------------|
| Cloud hosting (piccolo/medium) | €100 - €500 |
| API OCR (Google Vision / Azure) | €50 - €500 |
| API LLM (OpenAI / Anthropic) | €200 - €1.500+ |
| Web search API (Tavily / SerpAPI) | €50 - €300 |
| Social enrichment API (Apollo / Clearbit) | €100 - €500 |
| Email / SMS / WhatsApp | pay-per-use |
| Advertising spend | budget utente |

## Repository e proposta
- **Repo**: `https://github.com/<organizzazione>/<repo>`
- **Docs tecniche**: cartella `/docs`
- **API spec**: OpenAPI generato automaticamente da FastAPI.

## Prossimi passi
1. Approvare stack e scope MVP.
2. Creare repo e scaffold progetto.
3. Sviluppare prototipo camera + OCR in 2-3 settimane.
4. Testare con campione reale di biglietti.
5. Iterare su enrichment e marketing.
