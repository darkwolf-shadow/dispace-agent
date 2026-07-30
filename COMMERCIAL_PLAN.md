# DiSpace - Piano commerciale e moduli

## Visione

Un'unica piattaforma modulare per aziende che partecipano a fiere, eventi e manifestazioni. Ogni cliente può attivare uno, due o tre moduli in base alle esigenze, con upgrade semplice che non richiede cambiare applicazione.

## Architettura modulare

| Modulo | Nome piano | Descrizione |
|--------|-----------|-------------|
| 1 | **Base - Lead Capture** | Cattura contatti da biglietti da visita, volantini e brochure con OCR + AI. Archivio contatti, export, note base. |
| 2 | **Pro - Marketing & Proposte** | Arricchimento contatti, report commerciali, proposte WhatsApp/email/story, note e documenti. |
| 3 | **Premium - Campagne & Social** | Campagne multicanale automatiche, social scheduler, analytics, dashboard commerciale. |

## Cosa può fare ogni livello

### Livello 1 - Base (Lead Capture)

- Scatta o carica biglietti da visita e volantini dal telefono.
- Estrazione dati con OCR + intelligenza artificiale.
- Archivio contatti permanente con ricerca.
- Campi principali: nome, azienda, ruolo, email, telefono, sito, indirizzo, LinkedIn.
- Note base per ogni contatto.
- Esporta contatti in JSON/CSV.
- Multisede: ogni cliente ha la propria istanza isolata.

### Livello 2 - Pro (Marketing Automation)

Tutto il livello Base più:

- Arricchimento contatti tramite ricerca web (Tavily, Brave, Serper, Bing).
- Report commerciale strutturato con profilo azienda, prodotti, presenza online, fonti.
- Profilo "La mia azienda" con descrizione, prodotti, valori, target e tono.
- Generazione proposte commerciali: email, WhatsApp, social story.
- Note e documenti per ogni contatto (appuntamenti, telefonate, contratti).
- L'IA usa note e profilo azienda per personalizzare report e proposte.

### Livello 3 - Premium (Campagne & Social Hub)

Tutto il livello Pro più:

- Campagne marketing multicanale: seleziona contatti per tag/score e genera contenuti in blocco.
- Invio email tramite integrazione con servizi SMTP/send API.
- Pianificazione post/story per social (Instagram, Facebook, LinkedIn) con anteprima.
- Analytics: aperture, click, risposte, conversioni.
- Dashboard commerciale con pipeline e task di follow-up.
- Integrazione con CRM esterni (HubSpot, Pipedrive, Zoho) tramite webhook/API.

## Attivazione dei moduli

Ogni istanza Railway può essere configurata con variabili d'ambiente che abilitano i piani:

```env
PLAN=base        # abilita solo Lead Capture
PLAN=pro         # abilita Lead Capture + Marketing
PLAN=premium     # abilita tutto
```

I moduli sono indipendenti:

- Un cliente può partire con `base`, poi passare a `pro` senza reinstallare.
- Un cliente può attivare `premium` da subito se ha bisogno di campagne e social.
- Per vendere separatamente, si creano istanze con `PLAN` diverso.

## Prezzi indicativi mensili

| Piano | Prezzo | Destinatari |
|-------|--------|-------------|
| Base | 29 €/mese | Piccole aziende, singole fiere |
| Pro | 79 €/mese | Aziende con vendita B2B e network costante |
| Premium | 199 €/mese | Aziende con team marketing e social attivo |

I prezzi sono indicativi. Ogni piano include un numero di contatti e di generazioni AI; oltre si aggiungono crediti.

## Proposta commerciale

DiSpace viene presentata come **un'unica piattaforma crescente**:

- Ogni cliente vede solo le funzioni del piano attivato.
- L'upgrade è istantaneo: basta cambiare `PLAN` nel pannello Railway.
- Non serve cambiare URL, account o dati: il contatto e l'azienda restano gli stessi.
- L'upsell è naturale: chi inizia con la cattura contatti può aggiungere le proposte commerciali e poi le campagne.

## Prossimi passi tecnici

1. Aggiungere la variabile `PLAN` nel backend e nel frontend.
2. Nascondere i pulsanti e gli endpoint non inclusi nel piano attivo.
3. Creare il modulo Premium con campagne multicanale e social scheduler.
4. Aggiungere una pagina di impostazioni del piano per ogni cliente.

## Note

- Ogni cliente ha una propria istanza Railway isolata.
- Il modello "un'istanza per cliente" mantiene dati separati e semplifica la fatturazione.
- In futuro si può valutare un'architettura multi-tenant se il numero di clienti cresce molto.
