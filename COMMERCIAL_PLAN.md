# DiSpace - Piano commerciale e moduli

## Visione

Un'unica piattaforma modulare che accompagna l'azienda dalla fiera al cliente finale. Ogni cliente può attivare uno, due o tre piani in base alle esigenze. L'upgrade è istantaneo e non richiede di cambiare applicazione.

## I tre piani

### Piano Base — Lead Capture + Report

Scopo: capire chi è il cliente che hai davanti.

- Scatta o carica biglietti da visita, volantini e brochure dal telefono.
- Estrazione dati con OCR + intelligenza artificiale.
- Arricchimento tramite ricerca web (Tavily, Brave, Serper, Bing).
- Report commerciale strutturato: profilo azienda, prodotti, social, fonti.
- Archivio contatti permanente con ricerca ed export JSON/CSV.
- Note per ogni contatto.

**Questo è il nucleo fondamentale**: senza report non c'è valore.

### Piano Pro — Proposte commerciali per il singolo cliente

Scopo: trasformare il report in azione verso quel cliente specifico.

Tutto il piano Base più:

- Profilo "La mia azienda" con descrizione, prodotti, valori, target e tono.
- Generazione proposte commerciali personalizzate per il singolo contatto:
  - messaggio WhatsApp;
  - email commerciale;
  - proposta formale da presentare;
  - story/post social relativo al cliente.
- L'IA usa il profilo aziendale + le note per personalizzare le proposte.

### Piano Premium — Campagne di marketing per l'azienda

Scopo: fare marketing per l'azienda che usa l'app, non solo per i singoli contatti.

Tutto il piano Pro più:

- Analisi del target ideale dell'azienda proprietaria.
- Campagne pubblicitarie per l'azienda, basate sui contatti in archivio e sui prodotti.
- Generazione di contenuti multipli: post, story, annunci, email di campagna.
- Stima del budget pubblicitario reale per canale (Google, Meta, LinkedIn, ecc.).
- Calcolo CPC/CPM/CPA stimato in base al settore e alla località.
- Pianificazione e pubblicazione sui social (dove le API lo permettono).
- Analytics di campagna.

Il Premium non paga la pubblicità al posto del cliente: la progetta e calcola quanto costa, poi il cliente decide il budget.

## Attivazione dei piani

Ogni istanza Railway può essere configurata con la variabile d'ambiente `PLAN`:

```env
PLAN=base        # lead capture + report
PLAN=pro         # + proposte commerciali per singolo cliente
PLAN=premium     # + campagne marketing per l'azienda
```

L'app nasconde automaticamente i pulsanti e le sezioni non inclusi nel piano attivo. I dati e il profilo azienda restano sempre salvati.

## Prezzi abbonamento consigliati

| Piano | Prezzo mensile | Destinatari |
|-------|----------------|-------------|
| Base | 29 € | Piccole aziende, singole fiere |
| Pro | 59 € | Aziende B2B con vendita diretta |
| Premium | 149 € + budget ads | Aziende con team marketing e budget pubblicitario |

## Costi di funzionamento

Vedi `COST_ANALYSIS.md` per il dettaglio dei costi reali di IA, ricerca web e hosting per ogni piano.

## Prossimi passi tecnici

1. Confermare i tre piani e i prezzi.
2. Implementare il calcolatore di budget pubblicitario nel Premium.
3. Aggiungere le API di pubblicazione sui social dove possibile.
4. Creare una dashboard con analytics e ROI stimato.
