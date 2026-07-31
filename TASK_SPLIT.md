# DiSpace - Schema di compiti: cosa fa Devin e cosa fa Fabio

## Cose che Devin può fare in autonomia

| Attività | Stato | Note |
|----------|-------|------|
| Modificare backend/frontend, aggiungere funzioni, fix bug | ✅ | Già in corso |
| Deploy su Railway, gestire variabili d'ambiente | ✅ | Token Railway fornito |
| Generare QR code e link di test | ✅ | Già fatto |
| Integrare API OpenRouter, Tavily, ricerca web | ✅ | Già funzionante |
| Strutturare piani Base/Pro/Premium con feature flags | ✅ | Completato |
| Aggiungere modulo Social Post (generazione + pubblicazione) | ✅ | Completato |
| Implementare pubblicazione automatica per Telegram/Facebook/WhatsApp | ✅ | Backend pronto |
| Calcolare costi stimati per piani e API | ✅ | In `COST_ANALYSIS.md` |
| Scrivere guide e documentazione tecniche | ✅ | Questo file e gli altri `.md` |

## Cose che deve fare Fabio (non possono essere fatte da Devin)

| Attività | Perché serve | Note |
|----------|--------------|------|
| Creare account sviluppatore Meta | Per pubblicare su Facebook/Instagram via API | https://developers.facebook.com |
| Creare/verificare Pagina Facebook Fattoria Il Capitano | Necessaria per collegare Instagram Business e generare token | Deve essere admin della pagina |
| Convertire account Instagram in Business/Creator e collegarlo alla Pagina | Instagram Graph API richiede account professionali | Si fa da app Instagram o da Meta Business Suite |
| Completare **Page Publishing Authorization** se richiesta | Meta può bloccare la pubblicazione finché non verifica identità | Richiede documenti/reale persona |
| Richiedere permessi avanzati e passare **App Review** (Meta) | Senza questo l'app pubblica solo per gli admin della pagina | Richiede screencast e descrizione dell'uso |
| Fornire Page Access Token e ID pagina/IG | Devin li inserisce in variabili/credenziali app | Token temporaneo dal Graph API Explorer, poi stabile via OAuth |
| Decidere prezzi finali abbonamenti | Devin ha calcolato costi, ma prezzi commerciali spettano a Fabio | Base €29/Pro €59/Premium €149 indicativi |
| Fornire API key extra se servono (Serper, Brave, Bing) | Tavily è già attiva, ma per fallback servono chiavi | Facoltativo |
| Testare con biglietti reali da telefono | Solo Fabio può verificare qualità OCR sui suoi biglietti | Fornire feedback iterativo |
| Aprire conto Stripe/PayPal per abbonamenti | Devin non gestisce pagamenti | Necessario per vendita piani |

## Schema operativo consigliato

### Fase 1 — Testare il Base (già online)
1. Fabio scatta 5-10 biglietti reali con l'app.
2. Fabio verifica quali dati trova e quali mancano.
3. Devin migliora OCR/prompt in base al feedback.

### Fase 2 — Collegare Meta per Facebook/Instagram
1. Fabio crea/verifica Pagina Facebook e Instagram Business.
2. Fabio crea app su Meta for Developers.
3. Fabio genera Page Access Token dal Graph API Explorer.
4. Fabio passa token e ID pagina a Devin.
5. Devin configura credenziali e testa pubblicazione.

### Fase 3 — Sistemare Pro e Premium
1. Fabio definisce prodotti/valori azienda nella sezione "La mia azienda".
2. Fabio testa proposte WhatsApp/email per alcuni contatti.
3. Devin aggiusta prompt e template.
4. Fabio carica foto/volantini in Social Post.
5. Devin migliora caption e flusso di approvazione.

### Fase 4 — Commercializzazione
1. Fabio decide prezzi e nome commerciale.
2. Devin genera pagina landing/prezzi e sistema di abbonamenti.
3. Fabio apre conto Stripe/PayPal e collega API key.
4. Devin integra pagamenti.

## Cosa serve subito per andare avanti

Per collegare Facebook/Instagram, Fabio deve fornire:
- URL della Pagina Facebook esistente (o indicare se va creata)
- Se l'account Instagram è già Business/Creator
- Token di accesso Meta (temporaneo) e ID pagina, oppure accesso temporaneo all'account sviluppatore Meta

Senza questi dati, la pubblicazione automatica su Meta rimane in bozza e si può usare solo Telegram (facile) o copia/incolla manuale.
