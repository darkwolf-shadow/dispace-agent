# Step 3 - Marketing Automation

Questo branch aggiunge la generazione automatica di contenuti di marketing e la gestione delle campagne.

## Cosa include
- **Template engine**: CRUD template per proposte commerciali, email, WhatsApp, post LinkedIn, stories Instagram.
- **Seed default**: al primo avvio vengono creati 4 template di default.
- **Generazione per contatto**: `POST /contacts/{id}/generate/{kind}` genera proposte/messaggi personalizzati sostituendo i placeholder `{name}`, `{company}`, `{role}`, `{email}`, `{phone}`, `{website}`, `{address}`, `{linkedin}`. Se `OPENAI_API_KEY` o `OPENROUTER_API_KEY` è configurata, il testo viene migliorato tramite LLM.
- **Mailing list dinamica**: `GET /mailing-list` con filtri per tag, punteggio minimo e azienda.
- **Campagne**: `POST /campaigns` per creare campagne, `POST /campaigns/{id}/run` per generare contenuti per tutti i contatti che soddisfano i filtri.
- **Contenuti generati**: `GET /generated-contents` per revisionare bozze prima dell'invio.
- **Frontend**: sezione Marketing con creazione campagne, lista campagne, contenuti generati e pulsanti rapidi per ogni contatto.

## Endpoint principali
- `GET /templates`, `POST /templates`, `GET/PUT/DELETE /templates/{id}`
- `POST /contacts/{id}/generate/{kind}` (kind: `proposal`, `email`, `whatsapp`, `social`, `story`)
- `GET /mailing-list?tag=...&min_score=...&company=...`
- `POST /campaigns`, `GET /campaigns`, `POST /campaigns/{id}/run`
- `GET /generated-contents`

## Note
- L’invio effettivo di email, WhatsApp e post social non è ancora implementato; questa fase genera bozze pronte per essere inviate in Step 4.
- Per generazione con LLM, configura `OPENAI_API_KEY` o `OPENROUTER_API_KEY`.
