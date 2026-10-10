# Atti di indirizzo del Consiglio regionale

La banca dati del Consiglio (`AttiIndirizzoRicerca.aspx`) è un'applicazione ASP.NET: le ricerche e l'apertura delle
schede avvengono con «postback» di modulo, quindi la raccolta usa un browser automatico (Playwright con Chromium) e
la libreria standard di Python per le schede, che hanno un indirizzo stabile con l'identificativo dell'atto.

Passi, da eseguire dalla cartella `scripts/consiglio/` (il proxy della sessione va passato come `HTTPS_PROXY`):

1. `node raccogli_atti.js Mozione id_mozioni.json` e `node raccogli_atti.js Odg id_odg.json`: per ogni atto della
   XIII legislatura raccolgono l'indirizzo della scheda (circa 25 secondi per pagina di dieci atti).
2. `node raccogli_stati.js Mozione stati_mozioni.json` e `node raccogli_stati.js Odg stati_odg.json`: per ciascuno
   dei quattro stati (presentato in attesa di esame, esaminato e approvato, esaminato e non approvato, ritirato)
   raccolgono numero e data degli atti.
3. `python3 -I leggi_dettagli.py id_mozioni.json mozioni_dett.json`: legge ogni scheda di mozione (titolo, data,
   proponenti, assessore competente, testo depositato); `python3 -I leggi_dettagli_odg.py id_odg.json odg_dett.json`
   legge le schede degli ordini del giorno, che hanno un'altra struttura (disegno di legge di riferimento, legge
   approvata, esito della votazione, testo in PDF, firme aggiunte). Con `--continua` riprendono dai mancanti.
4. `node raccogli_gruppi.js`: composizione dei gruppi consiliari (presidente, vicepresidente, segretario, componenti;
   per il Gruppo misto le forze politiche citate nel testo).
5. `python3 -I ../aggiorna_consiglio.py <cartella con i file raccolti>`: unisce tutto in `dati/consiglio_atti.json`.

Interpellanze e interrogazioni (`ricerca.aspx`) non sono ancora raccolte.
