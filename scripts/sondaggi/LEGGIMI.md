# Osservatorio sondaggi: come funziona

Sezione riservata `sondaggi/` dell'Atlante FVG: archivio dei sondaggi politici ed elettorali pubblicati in
Italia e in Friuli Venezia Giulia, per istituto, con grafici, schede, fonti e un pannello di gestione.
Tutto il codice sta in `scripts/sondaggi/`, la configurazione in `dati/sondaggi/`, i dati nel ramo
`sondaggi-dati` (cifrati), il flusso pianificato in `.github/workflows/sondaggi.yml`.

## Architettura

| Pezzo | Dove | Che cosa fa |
|---|---|---|
| Pagina riservata | `sondaggi/index.html` | cancello identico alle altre sezioni riservate: la parola d'ordine deriva la chiave (PBKDF2, 300.000 giri) e decifra `contenuto.json`; la chiave resta in `sessionStorage` finché la scheda è aperta |
| Frammento cifrato | `sondaggi/contenuto.json` | struttura, stile (`frammento.html`) e programma (`app.js`) compilati da `compila_pagina.py` con `scripts/cifra_pagina.js` |
| Archivio dei dati | ramo `sondaggi-dati`, `archivio.json` | un solo documento JSON compresso e cifrato (AES-GCM) con la stessa chiave della pagina; la pagina lo scarica da `raw.githubusercontent.com` |
| Stato delle fonti | ramo `sondaggi-dati`, `stato.json` | avanzamento del recupero storico, ultimo tentativo e ultimo esito per fonte |
| Revisioni e caricamenti | ramo `sondaggi-dati`, `revisioni/`, `caricati/` | file cifrati scritti dal pannello (correzioni, approvazioni, scarti, fonti, istituti, serie, documenti caricati) |
| Flusso | `.github/workflows/sondaggi.yml` | ogni giorno alle 6 (Europe/Rome) e a richiesta («Aggiorna adesso»); modalità incrementale, storico, ricontrollo |
| Orchestratore | `aggiorna.py` | applica le revisioni, esegue i connettori con tempo massimo, ricalcola riepiloghi e serie, riscrive archivio e stato |
| Connettori | `fonti/*.py` | una fonte ciascuno: `scenaripolitici`, `wikipedia`, `demos`, `swg`, `wayback_portale`, `caricamenti` |
| Estrazione | `estrai.py` | righe «Nome valore», tabelle HTML e PDF, righe PDF per coordinate, OCR (RapidOCR), nota informativa, controlli di coerenza |
| Soggetti | `soggetti.py`, `dati/sondaggi/soggetti.json` | partiti, liste, coalizioni con alias e periodo di validità; nessuna fusione automatica fra soggetti diversi |
| Istituti | `dati/sondaggi/istituti.json` | registro degli istituti con alias; cresce da solo con i nomi letti |
| Archivio (logica) | `archivio.py` | inserimento, stato, coda «da verificare», doppioni fra fonti (gemelli), revisioni manuali protette |
| Serie | `serie.py` | serie comparabili per istituto, tipo, elezione, territorio, testo della domanda, unità e denominatore |
| Restrizioni | `dati/sondaggi/restrizioni.json` | periodi di silenzio (legge 28/2000, art. 8) e blocchi configurabili su grafici, tabelle ed esportazioni |
| Prove | `prove/sondaggi.js` | Chromium: cancello, parola errata, apertura, viste, coda esclusa dai grafici, separazione dei territori, esportazioni, telefono |

## Modello dei dati (archivio.json)

- `istituti{id}`: nome, alias, sito, fonti, conteggi, prima e ultima rilevazione.
- `fonti{id}` e `statoFonti{id}`: registro e stato (ultimo tentativo, ultimo riuscito, errore, avanzamento).
- `rilevazioni{id}`: `fonte`, `riferimento` (identificativo presso la fonte), `titolo`, `istituto`, `committente`,
  `editore`, `inizio`, `fine`, `pubblicato`, `criterioData` (`interviste` o `pubblicazione`), `territorio`
  {tipo, nome, codice}, `popolazione`, `campione`, `sottocampione`, `metodo`, `ponderazione`, `nota`,
  `erroreDichiarato` (solo se dichiarato), `livello` (`primaria`/`secondaria`), `urls`, `documenti`
  [{url, tipo, titolo, rif, testo}], `domande`, `limiti`, `stato`, `motiviCoda`, `gemelli`, `principale`,
  `protetta`, `revisioni`, `acquisito`, `primaAcquisizione`, `ultimaAcquisizione`, `storico`.
- Domanda: `tipo` (voto, fiducia, priorita, economia, servizi, tema, scenario, altro), `elezione`, `turno`,
  `scenario`, `testo` originale, `scala`, `unita` (%, punteggio, saldo, seggi), `denominatore` (validi o
  totale), `indecisi`, `astenuti`, `risposte` [{soggetto, testo, valore, min, max, variazione}], `origine`
  (tabella, testo, ocr, titolo, manuale), `controlli` {ok, motivi, somma, …}, `rif`, `documento`.
- `serie{id}`: punti (rilevazione, domanda, data) per serie comparabile, con buchi oltre 180 giorni.
- `coda{id}`: voci «da verificare» con motivi, fonte, esecuzione.
- `revisioni[]`: revisioni applicate (file, tipo, quando, esito); `esecuzioni[]`: registro (ultime 200);
  `ultimoTentativo`, `ultimoRiuscito`, `ultimaRilevazione`.

I dati mancanti sono `null`, mai zero. I nomi originali dei partiti restano nel campo `testo` di ogni risposta;
`soggetto` è l'identificativo del dizionario se il riconoscimento è certo per quel periodo, altrimenti `null`.

## Stati e regole di importazione

| Stato | Quando | Nei grafici |
|---|---|---|
| `verificata` | approvata o corretta da una persona (protetta dagli aggiornamenti) | sì |
| `automatica` | valori estratti da una fonte primaria con controlli superati | sì |
| `secondaria` | valori ripresi da una fonte secondaria (Wikipedia, titoli di Scenari Politici) con controlli superati | sì, segnalata |
| `senza_valori` | solo metadati e documenti (per esempio immagini non lette) | no |
| `da_verificare` | controlli non superati, OCR di grafici non elettorali, istituto non riconosciuto, fonte cambiata dopo una verifica | no |
| `scartata` | scartata a mano | no |

Controlli sulle intenzioni di voto: almeno quattro soggetti riconosciuti, nessun soggetto ripetuto, somma fra
97 e 101,5 (o pari al totale con indecisi e schede bianche dichiarati), poche righe non riconosciute. Le
tabelle di Wikipedia omettono i partiti minori: per loro la somma non è vincolante sotto 85 è comunque
respinta.

Doppioni fra fonti: stesso istituto, stessa data (fine interviste o pubblicazione), stesso territorio e stessa
elezione formano un gruppo (`gemelli`); una sola rilevazione è `principale` nei grafici (prima verificata, poi
automatica, poi secondaria; a pari stato la fonte primaria). Tutte restano consultabili nella scheda.

## Esecuzione

```
python3 scripts/sondaggi/aggiorna.py --cartella <copia del ramo sondaggi-dati> --modalita incrementale|storico|ricontrollo [--fonti a,b] [--limite N] [--senza-ocr] [--minuti 25]
PAROLA='…' python3 scripts/sondaggi/compila_pagina.py        # ricompila sondaggi/contenuto.json (sale conservato)
SITE=. ARCHIVIO=<archivio.json cifrato> PAROLA='…' node prove/sondaggi.js
```

Senza `SONDAGGI_PAROLA`/`MONITOR_PAROLA` nell'ambiente l'archivio viene scritto solo compresso (per le prove).
Librerie: cryptography, pdfplumber, pypdfium2, rapidocr_onnxruntime, beautifulsoup4, lxml, openpyxl, pillow, numpy.

## Fonti: che cosa è raggiungibile e che cosa no

| Fonte | Esito verificato il 13 ottobre 2026 | Uso |
|---|---|---|
| sondaggipoliticoelettorali.it (portale ufficiale) | **non raggiungibile**: timeout dal computer di GitHub (Azure) e dall'ambiente di lavoro; probabile blocco geografico | copie della Wayback Machine (vecchio sito 2002–2013); caricamento manuale dei documenti dal pannello |
| scenaripolitici.com | raggiungibile (wp-json, 8.048 articoli dal 2009) | metadati, immagini, OCR delle tabelle, valori nei titoli; sondaggi propri sul Friuli Venezia Giulia |
| Wikipedia (en, it) | raggiungibile (API) | tabelle per elezione con riferimento alla pubblicazione originale |
| demos.it | raggiungibile | Atlante Politico, Osservatorio Nord Est, nota informativa in testo, grafici in OCR |
| swg.it | raggiungibile | Radar settimanale (PDF): orientamenti di voto letti dalla pagina, nota informativa |
| termometropolitico.it | **non raggiungibile** in automatico: verifica anti automatismi (Cloudflare), non aggirata | i suoi valori arrivano da Wikipedia e Scenari Politici |
| istituti (Ipsos, Tecnè, Euromedia, Piepoli, Noto, Ixè, Winpoll, Eumetra, Bidimedia, Demopolis…) | siti raggiungibili, formati eterogenei, senza archivi strutturati dei sondaggi | non ancora collegati: i loro sondaggi entrano dalle ripubblicazioni, da Wikipedia e dai caricamenti |

Il pannello mostra queste informazioni in «Fonti». Per leggere il portale ufficiale servirebbe un esecutore in
Italia (runner autogestito di GitHub Actions su un computer dell'utente): il connettore si può aggiungere
quando quell'esecutore esiste.

## Pannello di gestione

Le azioni del pannello producono revisioni cifrate (`revisioni/*.json`) e documenti cifrati (`caricati/*.json`)
nel ramo `sondaggi-dati`, scritte con l'interfaccia di GitHub e un token personale a grana fine (permessi
Contents e Actions in scrittura sul solo repository) che resta nella sessione del browser. Senza token il file
cifrato viene scaricato e va caricato a mano nel ramo. «Aggiorna adesso» avvia il flusso (workflow_dispatch).
Il flusso applica le revisioni al giro successivo: una rilevazione corretta o approvata diventa `verificata` e
`protetta`, e gli aggiornamenti automatici non la sovrascrivono più (se la fonte cambia, la novità finisce in
coda come «fonte cambiata dopo la verifica manuale»).

## Protezione

La pagina e l'archivio sono cifrati: senza la parola d'ordine i file pubblici (`contenuto.json`, il ramo
`sondaggi-dati`) sono illeggibili. È una protezione crittografica, non una sessione su un server: il sito è
statico (GitHub Pages) e non esiste un servizio che possa negare la richiesta a chi non è autorizzato; chi
scarica i file cifrati può tentare la parola fuori linea (PBKDF2 a 300.000 giri rallenta, ma una parola corta
resta debole). Le funzioni di gestione che scrivono dati passano dall'autenticazione di GitHub (token
personale), quindi sono protette lato server. Per avere revoca per utente, registro degli accessi e nessun
file cifrato pubblico servirebbe un componente server (per esempio un Worker con archivio chiave-valore e
accesso su dominio dedicato): è una scelta architetturale e di costo che non è stata presa qui.

## Restrizioni alla diffusione

`dati/sondaggi/restrizioni.json` definisce la regola generale (quindici giorni prima del voto fino alla
chiusura dei seggi, articolo 8 della legge 22 febbraio 2000, n. 28), le consultazioni a cui applicarla e
periodi espliciti. In quei giorni la pagina non mostra grafici e tabelle delle intenzioni di voto e degli
scenari per il territorio e la consultazione indicati, e le esportazioni di quei valori sono bloccate;
l'archivio li conserva. La parola d'ordine non è considerata un'esenzione: la regola è configurabile ma
attiva per impostazione predefinita.
