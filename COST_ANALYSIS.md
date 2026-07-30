# DiSpace - Analisi costi reali per piano

## Ipotesi di partenza

I costi che seguono sono calcolati al netto del tempo di sviluppo e si riferiscono solo al funzionamento dell'applicazione una volta online. I prezzi sono aggiornati al 2026 e possono cambiare.

## Costo delle chiamate AI e ricerca web

### OpenRouter GPT-4o-mini

Prezzo: **$0,15 per 1 milione di token in input**, **$0,60 per 1 milione di token in output**.

| Operazione | Input token | Output token | Costo stimato |
|------------|-------------|--------------|---------------|
| Estrazione dati da immagine (vision) | ~1.500 (testo + immagine) | ~700 | **~$0,0006** |
| Report commerciale (arrichisci) | ~4.000 | ~900 | **~$0,0011** |
| Proposta commerciale (WhatsApp/email/story) | ~1.500 | ~700 | **~$0,0006** |
| Campagna marketing per l'azienda | ~3.000 | ~1.200 | **~$0,0012** |

### Tavily ricerca web

- **Keyless**: gratuita con limiti giornalieri/mensili.
- **Con API key**: 1.000 crediti gratis al mese, poi da **$0,005 a $0,008 per credito**.
- Ogni operazione "Arricchisci" esegue circa 4-5 ricerche = **4-5 crediti**.
- Costo stimato a pagamento per ogni "Arricchisci": **~$0,03 - $0,04**.

## Costo per piano, per contatto

### Piano Base

Operazioni incluse:

1. Fotografa e legge il biglietto (OCR + AI vision).
2. Arricchisce con ricerca web.
3. Genera il report commerciale.

| Voce | Costo stimato |
|------|---------------|
| OCR/AI vision | $0,0006 |
| Ricerca web Tavily | $0,03 - $0,04 |
| Report commerciale | $0,0011 |
| **Totale per biglietto** | **~$0,032 - $0,042** |

Quindi, per ogni biglietto scansionato, il costo reale di funzionamento è di circa **3-4 centesimi di dollaro**.

### Piano Pro

Include Base più:

- Proposta commerciale personalizzata per il cliente (WhatsApp/email).
- Proposta commerciale formale da presentare.
- Story o post social relativo al singolo cliente.

| Voce | Costo stimato |
|------|---------------|
| Base | $0,032 - $0,042 |
| Proposta WhatsApp/email | $0,0006 |
| Proposta commerciale | $0,0006 |
| Story social | $0,0006 |
| **Totale per contatto** | **~$0,034 - $0,044** |

Anche il Pro costa poco in più rispetto al Base, perché le proposte richiedono poche chiamate AI.

### Piano Premium

Include Pro più:

- Campagne di marketing per l'azienda, non per il singolo cliente.
- Calcolo del budget pubblicitario su canali a pagamento (Google, Meta, LinkedIn).
- Stima CPC/CPM/CPA in base al settore e alla località.
- Generazione di contenuti multipli per la campagna.

| Voce | Costo stimato |
|------|---------------|
| Analisi di marketing per l'azienda | $0,001 - $0,003 |
| Generazione contenuti campagna (per 10 pezzi) | $0,006 - $0,010 |
| Stima costi pubblicitari | $0,001 - $0,002 |
| **Totale IA per campagna** | **~$0,01 - $0,015** |

I costi veri del Premium non sono nelle chiamate AI, ma nel **budget pubblicitario** che il cliente spende su Google, Meta, LinkedIn, ecc. L'app non paga quel budget: lo calcola e lo propone.

## Costi fissi mensili

| Voce | Costo stimato |
|------|---------------|
| Hosting Railway (piano gratuito attivo) | $0 |
| Volume dati 500 MB | $0 |
| Tavily keyless (entro limiti) | $0 |
| OpenRouter (si paga solo l'uso) | a consumo |

Per una versione professionale su Railway:

| Voce | Costo stimato |
|------|---------------|
| Hosting Railway (1 GB RAM, volume persistente) | ~$5 - $15/mese |
| Tavily piano a pagamento (4.000 crediti) | $30/mese |
| OpenRouter | a consumo |

## Abbonamenti consigliati per coprire i costi

Ipotesi: ogni cliente usa l'app per 100 biglietti/mese e qualche campagna Premium.

| Piano | Costo IA mensile stimato | Hosting quota | Prezzo abbonamento consigliato |
|-------|--------------------------|---------------|-------------------------------|
| Base | ~$3 - $4 | $1-2 | **29 €/mese** |
| Pro | ~$4 - $5 | $2-3 | **59 €/mese** |
| Premium | ~$5 - $10 IA + solo calcolo budget ads | $3-5 | **149 €/mese + budget ads a parte** |

## Margini

- **Base**: venduto a 29 €, costa 3-4 € in IA. Margine alto.
- **Pro**: venduto a 59 €, costa 4-5 € in IA. Margine alto.
- **Premium**: venduto a 149 €, costo IA basso, valore aggiunto nel consulenza/calcolo budget. Il budget pubblicitario rimane del cliente.

## Nota importante

Questi numeri si riferiscono ai costi di piattaforma. Il costo di sviluppo, manutenzione e supporto va calcolato a parte. I prezzi di abbonamento qui sono indicativi e possono essere aggiustati in base al mercato.
