# Atlante dei dati

Sito di esplorazione di tutti i valori contenuti nel repository. La struttura segue tre passi: **tema** (dieci aree), **indicatore** (scheda con andamento, mappa, classifica e tabella) e **territorio** (profilo di un paese o di una regione). La pagina `scheda-fvg.html` è la scheda "Italia e Friuli Venezia Giulia a confronto con l'Europa".

## Contenuto

| Famiglia | Fonte | Lotti | Copertura nel repository |
|---|---|---|---|
| Indicatori nazionali | Banca Mondiale, WDI (Indicatori di sviluppo mondiale): 150 indicatori | 1 e 2 | completa: 217 paesi e 49 aggregati, dal 1960 |
| Regioni europee | Eurostat: 5 dataset demografici dei lotti 1 e 2 (21 serie più 3 quote per età calcolate) e 105 dataset regionali scaricati dall’API di Eurostat (269 indicatori su popolazione e proiezioni, economia, lavoro, istruzione, ricerca, salute, condizioni di vita, digitale, turismo, trasporti, agricoltura, ambiente, imprese), file originali in `open data/Eurostat regionale/` | 1 e 2; API | completa per i territori pubblicati: livelli NUTS da 0 a 3, dal 1990 (o dall’inizio della serie); le proiezioni arrivano al 2100 |
| Indici regionali e fondi europei | Commissione europea, DG REGIO (piattaforma cohesiondata, trovata su data.europa.eu): 9 dataset, 83 indicatori (indice di competitività RCI 2.0, indice di progresso sociale EU-SPI 2020 e 2024, indice di qualità delle istituzioni EQI, monitor regionale di genere 2021, gas serra regionali e intensità carbonica stimati dal JRC, pagamenti dei fondi europei per regione, energia rinnovabile da sole e vento per provincia), file originali in `open data/Commissione europea cohesiondata/` | nessuno (fuori dai lotti) | regioni NUTS 2 dell’Unione europea (province NUTS 3 per le rinnovabili); indici con pochi anni, gas serra dal 1990, fondi dal 1989 |
| Insiemi di dati completi | FAOSTAT (61 insiemi di dati: produzione e valore della produzione, commercio e indici del commercio, bilanci alimentari e conti di approvvigionamento, prezzi alla produzione e al consumo, tassi di cambio, terreni, fertilizzanti, pesticidi, emissioni, foreste, popolazione, lavoro, sicurezza alimentare, investimenti, indicatori macroeconomici, di genere e degli Obiettivi di sviluppo sostenibile e altri), OMS (Osservatorio mondiale della salute, 1.031 serie), OCSE (3 flussi su istruzione), ONU (14 tavole dell’annuario statistico), FMI (3 insiemi del cruscotto climatico), data.europa.eu (indicatori comunali di Karlsruhe) | 3–18, 20–24, 27–30 | completa: tutti i paesi e gli aggregati pubblicati dalla fonte; ogni serie è un file separato in `dati/archivi/<lotto>_<insieme>/` |
| Matrici bilaterali (vista Partner) | FAOSTAT: TM, commercio di prodotti agricoli per paese partner (52.410.630 osservazioni, 1986–2024, 195 dichiaranti, 220 partner); RFM, commercio di fertilizzanti per paese partner (5.565.289 osservazioni, 1990–2024, 217 dichiaranti, 247 partner); EA, flussi di sviluppo verso l’agricoltura per donatore (13.020.275 osservazioni, 1973–2023, 231 destinatari, 149 donatori) | 31, 19, 26 | completa: tutti gli archivi della fonte; un file compresso per dichiarante o destinatario in `dati/partner/<insieme>/` |

Gli archivi originali completi di tutti i lotti (1.543 file, 18 GB) stanno su Google Drive, indicati in `open data/Open data internazionali  indice completo dei lotti 1-31 su Drive.csv`. Le tre matrici bilaterali (lotti 19, 26 e 31: 7,6 GB di archivi scaricati) sono lette integralmente dagli archivi su Drive e hanno una vista dedicata, la vista Partner; le vecchie versioni parziali di RFM ed EA fra gli insiemi di dati sono state tolte. Quattro insiemi dei lotti 4, 10, 12 e 13 (MDDW, RLIS, HS, HCES) sono organizzati per indagine, con una sola osservazione per serie, e non sono rappresentabili come serie annuali: sono elencati come esclusi nella pagina "Fonti e metodo". Il lotto 25 (FDIQ) non contiene valori.

Mappe: Natural Earth 1:50 milioni (paesi, continenti, regioni del mondo) e GISCO NUTS 2024 1:10 milioni (regioni europee, © EuroGeographics per i confini amministrativi).

## Pagine

| Indirizzo | Pagina |
|---|---|
| `#/` | prima pagina: ricerca, temi, indicatori in evidenza, confronti pronti, schede |
| `#/tema/<tema>` | un tema con i suoi indicatori raggruppati per sottogruppo, valore più recente per l'Italia o il Friuli Venezia Giulia (il tema Regioni europee ha 21 sottogruppi) |
| `#/i/<codice>` | esplorazione di un indicatore: viste Andamento, Mappa, Classifica, Tabella; parametri `v` (vista), `t` (territori), `y` (anno), `area`, `liv`, `pae`, `log`, `ult`, `n`, `o`, `z` (periodo ingrandito) |
| `#/t/<territorio>` | profilo di un paese, di un aggregato o di una regione europea |
| `#/confronta?t=<tema>&g=<territori>` | tabella di confronto: righe = indicatori, colonne = territori |
| `#/archivi` e `#/archivi/<file>` | insiemi di dati FAOSTAT, OMS, OCSE, ONU, FMI e data.europa.eu: elenco per argomento, ricerca fra le serie |
| `#/partner/<insieme>` | vista Partner delle matrici bilaterali FAOSTAT (`TM`, `RFM`, `EA`): scelta del dichiarante o destinatario, del prodotto o scopo, dell’elemento e dell’anno; mappa dei partner o donatori colorata per valore, tabella ordinabile con contrassegni e note della fonte; parametri `t` (territorio), `p` (prodotto o scopo), `e` (elemento), `a` (anno) |
| `#/fonti` | fonti, metodo e copertura: Banca Mondiale, Eurostat, Commissione europea, FAOSTAT, OMS, OCSE, ONU, FMI; insiemi parziali ed esclusi |

## Funzioni

- **Ricerca unica** nella barra in alto (tasto `/`): temi, indicatori (anche con il nome inglese o il codice), paesi, regioni europee, archivi, pagine.
- **Menù a tendina** Temi e Schede; su telefono un unico menù.
- **Andamento**: rotellina del mouse, pizzico sullo schermo, trascinamento sul grafico, pulsanti + e − sul grafico o navigatore sotto il grafico ingrandiscono un periodo; doppio clic o pulsante ripristinano l'intero periodo. Gli altri territori restano in grigio sullo sfondo.
- **Mappa**: mondo, continenti o regioni e province europee (livello NUTS e paese a scelta), con ingrandimento fino a 28 volte a pulsanti, rotellina, pizzico e doppio clic, trascinamento per spostare; scala logaritmica e "ultimo dato disponibile" quando servono.
- **Classifica**: prime 10, 25, 50 o tutte le voci, ordine crescente o decrescente, selezionati evidenziati anche fuori classifica.
- **Tabella**: valore dell'anno, dato di dieci anni prima, variazione, posizione; ordinabile; selezione con caselle.
- **Linea del tempo** con riproduzione a velocità scelta, anno in grande nella scena.
- **Confronti pronti**: Friuli Venezia Giulia e vicini, province del Friuli Venezia Giulia, regioni italiane, Italia e grandi paesi europei, Italia e vicini, grandi economie del mondo, regioni del mondo.
- **Vista Partner**: per un paese, i valori di ciascun partner (o donatore) su mappa ingrandibile e in tabella; un clic su un paese della mappa o della tabella ne apre i partner. Raggiungibile dalla voce Partner del menù, dalla pagina Insiemi di dati e dalla ricerca: scrivendo un paese con «commercio», «esportazioni», «fertilizzanti» o «aiuti» (per esempio «Italia commercio») si apre direttamente la vista di quel paese.
- **Scarica CSV** e **copia il collegamento** della vista corrente.
- **Profili** con indicatori in evidenza, posizione in classifica e andamento degli ultimi trent'anni (file precalcolati in `dati/profili/`).
- **Scheda Friuli Venezia Giulia**: `scheda-fvg.html`, testi e grafici calcolati dai file di dati al caricamento della pagina; anche qui grafici a linee e mappa si ingrandiscono con rotellina, pizzico e pulsanti.

## Pubblicazione

Questa cartella è l'unica origine dell'Atlante. È pubblicata su due domini, ciascuno dal proprio repository:

| Indirizzo | Repository | Cartella |
|---|---|---|
| [costalonga.org/atlante](https://costalonga.org/atlante/) | GuidoCostalonga/GuidoCostalonga.github.io | `atlante/` |
| [atlantefvg.it/atlante](https://atlantefvg.it/atlante/) | GuidoCostalonga/Atlante-FVG | `atlante/` |

In entrambi i repository il flusso `.github/workflows/sincronizza-atlante.yml` controlla ogni ora l'ultimo commit di `main` che ha toccato `atlante/` qui; se è nuovo copia la cartella, pubblica e chiede a GitHub Pages di ripubblicare il sito (l'ultimo commit copiato è scritto in `.github/origine-atlante.txt`). Ogni aggiornamento della base dati va quindi fatto qui: entro un'ora compare sui due domini. Una modifica fatta direttamente in uno dei due siti verrebbe sovrascritta alla sincronizzazione successiva. La sincronizzazione si può avviare anche a mano dalla scheda Actions di ciascun repository.

## Aprire il sito

```
cd atlante
python3 -m http.server 8000
```

poi aprire `http://localhost:8000`.

## Struttura

| Percorso | Contenuto |
|---|---|
| `index.html`, `stile.css` | pagina e stile |
| `nucleo.js` | temi, sottogruppi, stato, formati, caricamento dati, ricerca, componenti, instradamento |
| `grafici.js` | viste Andamento, Mappa, Classifica, Tabella e scarico CSV |
| `partner.js` | vista Partner delle matrici bilaterali |
| `pagine.js` | prima pagina, tema, esplorazione, profilo, confronto, archivi, fonti, avvio |
| `scheda-fvg.html`, `scheda.js` | scheda "Italia e Friuli Venezia Giulia a confronto con l'Europa" |
| `dati/meta.json` | indicatori, territori (paesi, aggregati, regioni NUTS, codici storici e aggregati FAOSTAT), regioni del mondo, catalogo degli archivi |
| `dati/panoramica.json` | per ogni indicatore: valore più recente, posizione e andamento per Italia, Friuli Venezia Giulia, Unione europea e mondo (prima pagina e pagine dei temi) |
| `dati/profili/<territorio>.json` | indicatori in evidenza di ciascun territorio (pagine dei profili) |
| `dati/indicatori/<codice>.json` | Banca Mondiale: valori annuali per territorio; `null` = dato mancante |
| `dati/eurostat/<codice>.json` | Eurostat e Commissione europea (DG REGIO): valori annuali per territorio NUTS (chiavi `EU:<codice NUTS>`) |
| `dati/archivi/<lotto>_<insieme>.json` | catalogo delle serie di un insieme di dati (etichetta, unità, periodo, numero di territori, dimensioni originali) |
| `dati/archivi/<lotto>_<insieme>/<n>.json.gz` | una serie: valori annuali per territorio e contrassegni della fonte per osservazione, compressi gzip e letti dal browser al momento dell’apertura |
| `dati/partner.json` | catalogo della vista Partner: insiemi, prodotti e scopi, elementi (nome originale ed etichetta italiana), unità, anni, territori con numero di osservazioni, partner e donatori con nome e ISO3, contrassegni della fonte |
| `dati/partner/<insieme>/<ISO3 o FAO_codice>.json.gz` | un dichiarante (TM, RFM) o destinatario (EA): per ogni serie `prodotto\|elemento` e per ogni partner o donatore il primo anno, i valori annuali e un carattere per anno con il contrassegno della fonte (`-` anno assente, `_` riga senza contrassegno); gzip livello 9 con data azzerata |
| `dati/note/<codice>.json` | note e stati originali della fonte per osservazione |
| `dati/mondo.topo.json`, `dati/nuts.topo.json` | confini semplificati |
| `strumenti/` | script di estrazione e generazione |

## Regole sui valori

- Nessun valore stimato, interpolato o ricostruito; i dati mancanti restano tali e sono contati in ogni vista.
- Due sole elaborazioni, entrambe indicate come calcolate: le quote di popolazione per età Eurostat (classe d'età divisa per totale, stesso territorio e anno, per 100) e i due totali dei pagamenti dei fondi europei (somma dei sette fondi per regione e anno; i pagamenti dello stesso fondo e anno divisi su due periodi di programmazione sono sommati anche nelle serie per fondo).
- Gli indicatori che la fonte stessa dichiara stimati, modellati o proiettati (gas serra regionali e potenziale rinnovabile del JRC, spesa modellata dei fondi, erosione del suolo, proiezioni di popolazione) portano il campo `stima`, mostrato in evidenza nella scheda.
- Negli insiemi di dati l'identità SHA256 della fonte comprende il territorio: le serie sono raggruppate per dimensioni originali (prodotto, elemento, sesso, età eccetera) e unità per confrontare i paesi. Il contrassegno di ogni osservazione (ufficiale, stima, imputato, previsione) è conservato e mostrato nelle note della tabella.
- Vista Partner: ogni valore è quello della riga originale per la coppia dichiarante e partner (o destinatario e donatore). Nessuna somma sui partner, nessun saldo: importazioni ed esportazioni restano elementi separati; i contrassegni della fonte sono sempre visibili in tabella, nel riquadro della mappa e nella nota sotto la tabella.
- Gli insiemi con una sola osservazione per serie o con più di 50.000 serie non sono generati e vengono elencati come esclusi.
- Decimali arrotondati a 6 cifre significative per la visualizzazione; conteggi interi esatti.

## Rigenerare i dati

```
cd atlante/strumenti
# 1. decomprimere gli ZIP dei lotti 1 e 2 in una cartella (PAESI/ e AGGREGATI/)
python3 estrai_eurostat.py <cartella lotti 1-2> /tmp/eurostat.json
# 2. tabella dei codici area FAOSTAT -> ISO3 (dai dizionari dei lotti 20 e 21 e dai confini Natural Earth)
python3 mappa_aree_faostat.py "<Lotto 21  dizionari originali FAOSTAT.xlsx>" <ne50.geojson> aree_faostat.json
# 3. decomprimere gli ZIP dei lotti (da Google Drive o dal repository) in <cartella>/L03, L04, ... L28
python3 estrai_lotti.py <cartella> /tmp/estratti aree_faostat.json [--lotti=3,4]   # scrive /tmp/estratti/L<nn>_<insieme>.json
# 4. indicatori regionali dall'API di Eurostat: i file TSV compressi stanno in "open data/Eurostat regionale/"
#    (--scarica li scarica di nuovo se mancano, insieme a liste di codici e indice)
python3 estrai_eurostat_api.py "../../open data/Eurostat regionale" /tmp/eurostat_api.json
# 5. indici e serie della Commissione europea (DG REGIO): i CSV e le schede stanno in "open data/Commissione europea cohesiondata/"
python3 estrai_regio.py "../../open data/Commissione europea cohesiondata" /tmp/regio.json
# 6. generare i file del sito
python3 genera_dati.py --cache /tmp/grezzi.json --eurostat /tmp/eurostat.json --eurostat-api /tmp/eurostat_api.json --regio /tmp/regio.json --insiemi /tmp/estratti
```

Matrici bilaterali (vista Partner): `estrai_partner.py` legge un file Excel alla volta e scrive un paese appena ne ha letto tutte le parti; il lotto 31 si tratta a blocchi di circa 25 archivi (scaricare, decomprimere, estrarre, cancellare), perché i file di un paese diviso fra due blocchi vengono completati al passaggio successivo. I cataloghi parziali accumulati fra i blocchi sono conservati in `strumenti/cataloghi_partner/`.

```
cd atlante
python3 strumenti/scarica_lotti.py "../open data/Open data internazionali  indice completo dei lotti 1-31 su Drive.csv" <cartella> 19
python3 -I strumenti/estrai_partner.py RFM <cartella>/L19 dati/partner strumenti/aree_faostat.json strumenti/cataloghi_partner/cat_RFM.json
# stesso schema per EA (lotto 26) e per TM (lotto 31, blocco per blocco sullo stesso catalogo cat_TM.json)
python3 strumenti/genera_partner.py . strumenti/cataloghi_partner/cat_RFM.json strumenti/cataloghi_partner/cat_EA.json strumenti/cataloghi_partner/cat_TM.json
```

Confini NUTS: scaricare da GISCO `NUTS_RG_10M_2024_4326_LEVL_{0,1,2,3}.json`, ridurre le proprietà a `id`, `n`, `l`, `c` (codice ISO3 del paese) e unire con `mapshaper -simplify 35% keep-shapes -o format=topojson quantization=1e5`.
