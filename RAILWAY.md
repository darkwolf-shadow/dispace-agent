# Guida deploy su Railway

Questa guida spiega come mettere l'applicazione online con Railway in modo gratuito o quasi.

## Cosa serve

1. Un account su [Railway](https://railway.com).
2. Questo repository caricato su GitHub.
3. Le variabili d'ambiente configurate nel pannello di Railway.

## Piano gratuito

- Costo: 0 euro al mese.
- Include circa 1 dollaro di credito mensile da usare per le risorse.
- Risorse disponibili con il piano gratuito: 0,5 GB di RAM, 1 processore, 1 GB di spazio temporaneo, 0,5 GB di spazio disco persistente.
- Il servizio resta sempre acceso e ha un indirizzo tipo `nome-progetto.railway.app`.

## Passaggi

1. Crea un account su Railway con il piano gratuito.
2. Crea un nuovo progetto e scegli "Deploy from GitHub repo".
3. Seleziona il repository `darkwolf-shadow/dispace-agent`.
4. Railway rileverà automaticamente il file `railway.json` e userà il Dockerfile nella cartella `backend`.
5. Nel pannello "Variables" del servizio, aggiungi queste variabili:

```
APP_USERNAME=admin
APP_PASSWORD=una_password_sicura
DATABASE_URL=sqlite:////app/data/dispace.db
UPLOADS_DIR=/app/data/uploads
OPENROUTER_API_KEY=la_tua_chiave_se_hai
TAVILY_API_KEY=la_tua_chiave_se_hai
OPENAI_API_KEY=la_tua_chiave_se_hai
```

6. Aggiungi un volume persistente dal pannello "Volumes", montato sul percorso `/app/data`, con dimensione 0,5 GB. In questo modo i contatti e le immagini caricate non si perdono quando l'app viene aggiornata.
7. Avvia il deploy. Il primo avvio può richiedere alcuni minuti perché viene installato Tesseract.
8. Una volta attivo, apri l'indirizzo assegnato da Railway. Vedrai la pagina di login.

## Login

La pagina iniziale chiede utente e password. Solo chi conosce le credenziali può entrare.

L'utente predefinito si imposta con le variabili `APP_USERNAME` e `APP_PASSWORD`.

## Limiti del piano gratuito

- Se superi il credito mensile, il servizio si ferma fino al mese successivo.
- Lo spazio su disco è limitato a 0,5 GB: basta per molti biglietti da visita, ma se carichi molte foto potrebbe terminare.
- Il piano gratuito non è adatto a molti utenti contemporanei.

## Quando passare a un piano a pagamento

- Quando l'app ha più utenti o più dati.
- Quando serve un database PostgreSQL più robusto.
- Quando si vuole usare un dominio personalizzato come app.fattoriailcapitano.com.
