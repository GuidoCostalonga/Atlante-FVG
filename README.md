# Atlante dei Comuni del Friuli Venezia Giulia

Pagina pubblicata su [atlantefvg.it](https://atlantefvg.it/). Il vecchio indirizzo costalonga.org/Atlante-FVG rimanda qui.

I 215 comuni del Friuli Venezia Giulia comune per comune: popolazione, amministratori,
Terzo settore, sport, cultura, servizi sanitari, scuole, turismo, redditi e ambiente.
Con le mappe dei comuni (oltre 30 indicatori, 15 cartine dell'Annuario e 8 strati di servizi),
la mappa delle regioni d'Italia (24 cartine), la mappa degli autobus con linee, fermate e arrivi in tempo reale, il confronto fra quattro comuni, la scheda di
ogni comune stampabile in PDF e l'archivio completo: 136 fogli e quasi 450.000 righe,
filtrabili per provincia, per comune, per testo e colonna per colonna.

## Come è fatta

| File | Contenuto |
|---|---|
| `index.html` | La pagina: HTML, stile e programma in un solo file, con i dati riassuntivi dei comuni incorporati |
| `dati/*.txt` | Un file per foglio del database (i fogli più grandi sono divisi in parti). Ogni file è JSON compresso con gzip e codificato in base64; la pagina lo scarica e lo decomprime solo quando il foglio viene aperto |
| `dati/_mappe_0.txt` | Confini di comuni, province, regione e regioni italiane, con le classi delle 41 cartine dell'Annuario (stessa codifica degli altri file) |
| `dati/_punti_0.txt` | Punti della mappa dei servizi (farmacie, guardie mediche, residenze per anziani, fermate, accessi a internet, impianti dei rifiuti, stazioni meteo) già proiettati sul disegno della mappa |
| `dati/_tpl_0.txt` | Rete degli autobus TPL FVG (Trasporto pubblico locale del Friuli Venezia Giulia): fermate con il loro comune e percorsi con il tracciato stradale (semplificato a 8 metri), già proiettati sul disegno della mappa |
| `scripts/aggiorna_autobus.py` | Aggiornamento automatico della rete degli autobus |
| `c/<comune>/index.html` | Una pagina per comune, solo per l'anteprima nelle condivisioni (titolo e residenti del comune): rimanda subito a `?comune=<comune>`. Creata da `scripts/pagine_comuni.py`, insieme a `sitemap.xml` e `robots.txt` |
| `scripts/aggiorna_dati.py` | Aggiornamento automatico dei dati aperti regionali che cambiano spesso |
| `.github/workflows/aggiorna-dati.yml` | Esegue l'aggiornamento ogni lunedì e pubblica le novità |
| `favicon.ico`, `favicon-32.png`, `icona-192.png`, `apple-touch-icon.png` | Icona del sito (la cartina del logo) per le schede del browser e per la schermata Home dei telefoni |
| `anteprima.jpg` | Immagine di anteprima (1200 × 630) mostrata da WhatsApp, Facebook e dagli altri social quando si condivide il collegamento |
| `CNAME` | Dominio della pagina, atlantefvg.it |
| `.nojekyll` | Dice a GitHub Pages di servire i file così come sono |

Ogni file di dati contiene le righe del foglio (`rows`) e, quando il foglio ha una colonna
del comune, l'indice del comune collegato a ciascuna riga (`k`), nello stesso ordine dei
comuni del foglio «Comuni».

## Collegamento diretto a un comune

Ogni comune ha il suo indirizzo: `https://atlantefvg.it/?comune=roveredo-in-piano` apre la pagina con il comune già
scelto nel filtro e la sua scheda aperta. Quando si sceglie un comune, l'indirizzo nella barra del browser si aggiorna da
solo. Il pulsante «Condividi il comune» nella scheda manda invece `https://atlantefvg.it/c/roveredo-in-piano/`, che
mostra nell'anteprima di WhatsApp il nome e i residenti del comune e apre una pagina con i dati principali e il
pulsante per la scheda completa.
Se l'indirizzo indica anche una pagina (`?pagina=mappe&comune=sacile`), il comune resta scelto nel filtro ma la scheda
non si apre da sola.

## Ricerche condivisibili e download

L'indirizzo conserva il comune (o la provincia), la pagina e i filtri della pagina aperta, così chi riceve il collegamento
vede la stessa vista. Il pulsante «Condividi questa vista» copia l'indirizzo, «Azzera tutti i filtri» riporta tutto
allo stato iniziale.

| Parametro | Pagina | Esempio |
|---|---|---|
| `comune`, `provincia` | tutte | `comune=roveredo-in-piano`, `provincia=PN` |
| `livello`, `indicatore` | mappe | `livello=regioni`, `indicatore=tribAb` |
| `confronta`, `mostra` | confronto | `confronta=udine,pordenone`, `mostra=rapporto` (oppure `assoluti`) |
| `voto`, `ordina` | comuni | `voto=2027`, `ordina=-p25` |
| `foglio`, `cerca`, `colonne` | archivio | `foglio=Farmacie&cerca=comunale&colonne={"2":{"sel":"206"}}` |

Registro, tabella della mappa, confronto e fogli dell'archivio si scaricano in **CSV** (virgola come separatore, punto
decimale, UTF-8) ed **Excel** (libreria SheetJS caricata solo al clic). Si scaricano solo le righe filtrate. Nel CSV
ogni riga porta tre colonne finali con fonte, periodo dei dati e condizioni di riutilizzo; nel file Excel le stesse
informazioni stanno nel foglio «Informazioni». Riutilizzo: vale la licenza della fonte; per i dati aperti della Regione le
licenze in uso sono IODL 2.0 e CC BY 4.0 (verificato sul catalogo regionale il 6 ottobre 2026).

## Motori di ricerca e prestazioni

- **Pagine statiche** generate da `scripts/pagine_comuni.py`, leggibili senza eseguire il programma della pagina:
  `c/<comune>/` (dati principali con la fonte di ogni riga, percorso, comuni di taglia simile), `provincia/<nome>/`
  (elenco dei comuni) e una pagina per argomento (`mappe/`, `confronto/`, `autobus/`, `ambiente/`, `comuni/`,
  `archivio/`, `metodo/`) con il pulsante che apre la pagina interattiva. Non rimandano più da sole all'Atlante.
- Ogni pagina ha titolo e descrizione propri, un solo H1, indirizzo canonico, percorso (breadcrumb) e dati strutturati
  schema.org: `BreadcrumbList` ovunque, `Dataset` su `archivio/` (senza licenza unica, che le fonti non hanno),
  `WebSite` sulla pagina principale. Gli indirizzi con parametri (`?comune=`, `?pagina=`, filtri) hanno come canonico
  `https://atlantefvg.it/`: si indicizzano le pagine statiche, non le combinazioni di filtri.
- `sitemap.xml` con 227 indirizzi e data dell'ultimo aggiornamento dei dati; `robots.txt` senza esclusioni.
- **Stile e icone compilati** dentro `index.html` con `scripts/compila_stile.js` (Tailwind CSS 3.4.19, Lucide 0.469:
  solo le 111 icone usate). Chart.js si scarica solo al primo grafico. Misura su telefono simulato (Pixel 7, rete 4G
  lenta, processore rallentato quattro volte): spostamenti del layout da 0,405 a 0, tempo bloccato da circa 5 a circa
  1,3 secondi. Dopo una modifica allo stile: `npm i --no-save tailwindcss@3.4.19 lucide@0.469.0` e
  `node scripts/compila_stile.js`.
- **Controlli dopo il rilascio**: `scripts/controlla_rilascio.py` (flusso «Controlli dopo il rilascio», a ogni
  pubblicazione e ogni martedì) verifica reindirizzamenti da http e www, sitemap, titoli e descrizioni unici, H1,
  canonici, dati strutturati, collegamenti interni, file di dati e servizi esterni.

## Segnalazioni, correzioni e statistiche

- **Segnala un errore** (per posta o via WhatsApp al +39 328 369 2227): nella scheda di ogni comune, sotto le mappe, nel confronto, nel dettaglio di ogni riga
  dell'archivio, nella pagina Metodo e in fondo a ogni pagina statica. Apre un messaggio per `info@atlantefvg.it` con
  l'indirizzo della pagina (filtri compresi), il dato di cui si parla e la versione dei dati.
- **Registro delle correzioni**: `dati/correzioni.json`, mostrato in Metodo e fonti (pagina interattiva e `metodo/`).
  Per ogni dato corretto si aggiunge una voce con `data` (AAAA-MM-GG), `dato`, `prima`, `dopo`, `fonte` (indirizzo
  completo), poi si rigenerano le pagine con `python scripts/pagine_comuni.py`.
- **Statistiche** con GoatCounter (`guidocostalonga.goatcounter.com`): niente cookie, nessun indirizzo IP conservato.
  Pagine viste (`/?pagina=...` e indirizzi delle pagine statiche) ed eventi: `ricerca/comune-scelto` (mai il testo
  scritto), `filtro/...`, `mappa/<indicatore>`, `confronto/<n>-comuni`, `archivio/<foglio>`, `download/<tabella>/<formato>`,
  `condividi/vista`, `segnala-errore/<dove>`, `errore/caricamento`, `errore/programma`. L'informativa è in Metodo e fonti.

## Grafica e uso sul telefono

- Atlante editoriale: fondo avorio uniforme, blu profondo per struttura e pagina attiva, oro per gli accenti; titoli in
  Source Serif 4 con maiuscole e minuscole normali, testi in Plus Jakarta Sans (16 px sul telefono, nessun testo
  essenziale sotto i 12 px); comandi uniformi: principali blu, secondari con bordo, di servizio come collegamenti.
- Intestazione compatta senza orologio. Su desktop le pagine stanno in una barra essenziale con la pagina attiva su
  fondo blu; su telefono e tablet quattro voci («Inizio», «Mappe», «Comuni», «Altro»): «Altro» apre Confronto,
  Archivio, Autobus, Allerte e aria, Metodo e fonti. Gli aggiornamenti sono una riga con i dettagli a richiesta.
- Pagina iniziale: titolo, ricerca «Cerca il tuo comune» e sagoma vettoriale del Friuli Venezia Giulia con i confini
  comunali (ricavata da `dati/_mappe_0.txt` e semplificata); la ricerca dell'intestazione compare solo dopo lo scorrimento.
  Le tre azioni principali stanno sotto il riquadro blu; i numeri regionali sono cifre grandi, note e fonti a richiesta.
- Filtro territoriale: barra compatta con il comune per primo; provincia secondaria (sul telefono dentro «Opzioni»);
  «Togli il filtro», «Azzera tutti i filtri» e «Condividi questa vista» raccolti in «Opzioni».
- Pagina Mappe: indicatore e comune sulla stessa riga, mappa subito visibile, legenda sopra la mappa su desktop e
  sotto sul telefono, scheda del comune selezionato con nome, valore, unità e posizione (sul telefono in un pannello
  dal basso), classifica compatta, servizi spenti all'avvio, istruzioni in «Come usare la mappa».
- **Gesti sulle mappe** (comuni e regioni, autobus con le vie, allerte, aria), un solo modulo `collegaGesti` con
  Pointer Events: due dita ingrandiscono e riducono centrando sul punto medio e spostano la mappa, senza ingrandire la
  pagina; un dito fa scorrere la pagina (a schermo intero sposta la mappa); mouse con rotella e trascinamento;
  pulsanti +, −, ripristina e schermo intero; limiti di zoom; un trascinamento o un pizzico non selezionano mai un
  comune; rotazione e interruzioni chiudono il gesto senza perdere l'inquadratura. Lo zoom del browser resta libero
  fuori dalle mappe. Prove automatiche: `prove/gesti.js` (28 controlli con eventi multitocco di Chromium).

## Accessibilità e movimento

- Fuoco da tastiera ben visibile (bordo blu scuro e alone dorato); intestazioni del registro ordinabili anche con Invio.
- Tabelle con intestazioni di riga e di colonna; sul telefono la prima colonna di registro e confronto resta ferma.
- Ogni mappa ha accanto la tabella con gli stessi valori; i grafici hanno un testo alternativo con i loro numeri.
- Animazioni brevi solo all'apertura di menu, schede e sezioni; i grafici si animano solo la prima volta; con la
  preferenza di sistema «movimento ridotto» non si muove nulla.
- Caricamento (rotella), assenza di dati (icona informativa) ed errore (triangolo rosso) hanno tre aspetti diversi.
- Controllo automatico con axe-core 4.10 sulle pagine principali: nessuna violazione grave o critica al 6 ottobre 2026.

## Trasparenza dei dati

- **Metodo e fonti** (`?pagina=metodo`): versioni e date di aggiornamento di ogni gruppo di dati, come leggere zero, dato non
  disponibile, non applicabile e non aggiornato, i tre tipi di collegamento ai comuni, la copertura dei bilanci, le fonti con i
  collegamenti alla documentazione originale e tutte le avvertenze.
- Sotto la barra delle pagine una riga indica lo **stato dei dati**: versione dell'archivio e ultimo aggiornamento automatico
  nelle pagine statistiche, ultima lettura e stato del servizio (attivo, in attesa, non risponde) nelle pagine in tempo reale.
- Sotto ogni mappa: fonte con collegamento, periodo, unità e copertura (comuni con il dato su 215).
- **Collegamenti ai comuni**: certo (codice ISTAT), ricostruito (nome del comune o indirizzo), nel testo (da verificare,
  escluso dai conteggi della scheda e del filtro).
- **Sindaci**: nel registro e nella scheda c'è la data di aggiornamento dell'anagrafe; se è ferma da oltre due anni rispetto
  all'acquisizione del 5 ottobre 2026 il dato è segnato «DA VERIFICARE».
- **Bilanci**: per ogni comune gli anni dei rendiconti di spesa e di entrata pubblicati (`EXTRA.E[i].bil`); dove manca il
  rendiconto la pagina scrive «non pubblicato», non zero.

## Fonti e data

I dati vengono dal file «Database Friuli Venezia Giulia», acquisito il 5 ottobre 2026 da
fonti pubbliche: Annuario statistico regionale 2026, portale dei dati aperti della Regione
FVG, anagrafe regionale degli amministratori locali, elenco RUNTS (Registro unico nazionale
del Terzo settore), ISTAT (Istituto nazionale di statistica) e altre. Ogni foglio, nella
pagina, riporta la propria fonte e la data di consultazione. È una fotografia a quella data,
non un collegamento in tempo reale.

## Altre fonti aggiunte il 6 ottobre 2026

| Contenuto | Fonte | Fogli |
|---|---|---|
| Rischio idrogeologico per comune: frane (2024) e alluvioni (2020), con residenti, famiglie, edifici, imprese e beni culturali esposti | ISPRA, piattaforma IdroGEO | `Rischio_idrogeologico_ISPRA` |
| Rendiconti comunali 2018-2023: spese per missione, programma e titolo; entrate per titolo e tipologia (84 comuni) | Portale dei dati aperti della Regione FVG | `Bilanci_rendiconto_spese`, `Bilanci_rendiconto_entrate`, `Bilanci_comunali_sintesi` |
| Elezioni regionali 2023: liste, presidente, affluenza | Portale dei dati aperti della Regione FVG | `Elezioni_regionali_2023_*` |
| Elezioni europee 2024 e Camera 2022 per comune | Ministero dell'interno, Eligendo | `Elezioni_europee_2024`, `Elezioni_camera_2022` |

Nei rendiconti alcune viste regionali ripetono le stesse righe (una, intitolata a Ragogna, contiene i dati di
Roveredo in Piano): i doppioni sono tolti tenendo una riga per anno, comune e voce di bilancio.

## Autobus

Linee e fermate vengono dai dati GTFS (formato aperto per gli orari del trasporto pubblico) di TPL FVG,
redistribuiti gratuitamente per usi non commerciali da [BusOne](https://busone.app); la data della versione in uso
compare sotto la mappa.
Per ogni linea e direzione è disegnato il percorso più frequente. Gli arrivi alla fermata e la posizione dei mezzi
sono letti dal browser di chi visita la pagina, al momento, dal flusso in tempo reale di TPL FVG tramite BusOne:
compaiono solo le corse già partite dal capolinea. Gli orari completi delle linee sono nella pagina
[Orari](https://atlantefvg.it/orari/), descritta più sotto; i treni non sono compresi.

Ingrandendo la mappa degli autobus compare sotto le linee la mappa delle vie di
[OpenStreetMap](https://www.openstreetmap.org/copyright) (© contributori di OpenStreetMap), scaricata dal browser di
chi visita la pagina. Ogni riquadro della mappa è agganciato al disegno con le stesse coordinate delle fermate.

## Orari degli autobus

La pagina `orari/` mostra l'orario programmato di ogni linea TPL FVG: si sceglie la linea, la direzione, il giorno e la
fermata e si leggono le partenze, con la prossima evidenziata e il dettaglio di ogni corsa fermata per fermata.
Dalla pagina Autobus ci si arriva con «Orari delle linee» e, per la linea scelta, con «Orari di questa linea».

I dati vengono dallo stesso GTFS di TPL FVG distribuito da BusOne. `scripts/aggiorna_orari.py` lo scarica ogni lunedì
insieme alla rete degli autobus e scrive `dati/orari/indice.txt` (validità, calendario dei servizi giorno per giorno,
fermate con il loro comune, linee) e un file per percorso in `dati/orari/`, chiamato con il codice del percorso; riscrive
solo i file cambiati e toglie quelli dei percorsi soppressi. Se il download fallisce o il GTFS sembra incompleto (meno di
100 linee o di 10.000 corse), gli orari restano quelli di prima. La fonte ripete alcune corse identiche: se ne tiene una.
Nella versione del 6 ottobre 2026 gli orari valgono dal 5 ottobre 2026 al 31 gennaio 2027. Per i giorni fuori da questo
periodo la pagina non mostra orari e rimanda a [tplfvg.it](https://tplfvg.it).

## Meteo e Catasto

Due applicazioni già pubblicate su costalonga.org sono portate nell'Atlante con la sua grafica; contenuti, fonti e
funzioni restano quelli dell'originale.

| Pagina | Origine | Come si aggiorna |
|---|---|---|
| `meteo/`: previsioni dei 215 comuni, collegata dalla scheda di ogni comune e dalla pagina delle allerte | repository `GuidoCostalonga/meteo` | `python scripts/porta_meteo.py <index.html della pagina Meteo FVG>` |
| `catasto/`: foglio e particella sulla mappa, con la cartografia dell'Agenzia delle Entrate | repository `GuidoCostalonga/catasto-map` (solo la parte che gira nel browser) | `python scripts/porta_catasto.py <cartella del repository catasto-map>` |

I due programmi sostituiscono intestazione, colori e caratteri, cambiano indirizzi e anteprime in atlantefvg.it e
si fermano con un errore se l'originale cambia nei punti da adattare. Il catasto passa dal proxy Cloudflare
`catasto-map-proxy`, che deve avere `https://atlantefvg.it` fra le origini ammesse (`ALLOWED_ORIGINS`): senza, la mappa
si vede ma l'identificazione della particella non risponde.

## Opere pubbliche

Dai dati aperti [OpenCUP](https://www.opencup.gov.it) (Presidenza del Consiglio dei ministri, DIPE, licenza CC BY 4.0),
archivio del Nord Est aggiornato ogni mese. `scripts/aggiorna_opere.py` lo scarica (circa 900 MB), lo legge senza estrarlo
e tiene solo i lavori pubblici (natura 03) localizzati in Friuli Venezia Giulia. Produce il foglio `Opere_pubbliche_OpenCUP`
(una riga per progetto e comune) e, per ogni comune in `const EXTRA`, il riepilogo della scheda e della mappa: progetti decisi
negli ultimi cinque anni, costo previsto e costo per abitante (solo progetti localizzati nel solo comune), i sei più grandi.
Il flusso `.github/workflows/aggiorna-opere.yml` lo esegue il 4 di ogni mese. I dati non distinguono i progetti PNRR: il
portale Italia Domani non è raggiungibile dai server dell'aggiornamento automatico, che sono fuori dall'Italia.

## Allerte meteo e qualità dell'aria

Sono lette al momento dal browser di chi visita la pagina, senza passare dal repository.

| Contenuto | Fonte | Aggiornamento |
|---|---|---|
| Allerta di oggi e di domani per le quattro zone del Friuli Venezia Giulia (idrogeologica, idraulica, temporali) | Bollettino di criticità nazionale del Dipartimento della Protezione civile, [pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica](https://github.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica), file `files/all/latest_all.zip` (licenza CC BY 4.0) | Ogni giorno verso le 16 |
| PM10, PM2,5, biossido di azoto e ozono per centralina | ARPA FVG sul portale dei dati aperti della Regione (dataset `qp5k-6pvm`, `d63p-pqpr`, `ke9b-p6z2`, `7vnx-28uy`) | Dati validati, circa una settimana di ritardo |

Dal bollettino la pagina scarica solo l'indice dell'archivio e le due tabelle delle zone (poche decine di KB) con richieste
parziali; se il browser non le permette, scarica l'archivio intero (4,6 MB). La zona d'allerta di ogni comune è fissata
nella pagina (`ZONA_COM`) secondo gli elenchi dei comuni del bollettino del 6 ottobre 2026: 45 comuni nella zona A,
61 nella B, 102 nella C, 7 nella D.

## Aggiornamento automatico

Ogni lunedì il flusso «Aggiorna i dati» aggiorna **un quarto delle fonti a rotazione**: in quattro settimane tutto ciò
che si può riscaricare in automatico è aggiornato. Il gruppo lo sceglie `scripts/aggiorna_dati.py`, contando le
settimane da lunedì 5 gennaio 2026 (`--quale-gruppo` lo stampa; `--gruppo N`, `--tutti` e `--prova` per le prove).

| Gruppo | Fonti |
|---|---|
| 1 | Anagrafe regionale degli amministratori (amministratori, enti locali, elezioni; nel registro sindaco, data di aggiornamento, prossime elezioni, incarichi), farmacie, parafarmacie, guardie mediche, residenze per anziani, accessi a internet, siti inquinati, protezione civile, elezioni comunali 2024, 2025 e 2026, patrimonio regionale, partecipate |
| 2 | Turismo comunale (con arrivi, presenze e serie per anno del registro e della scheda), strutture ricettive, agriturismi, fattorie didattiche, operatori biologici |
| 3 | Commercio di 13 comuni, centri commerciali, commercio ambulante, redditi IRPEF, lavoro, scambi con l'estero, veicoli |
| 4 | Rifiuti, stazioni e sensori meteo, ciclovie, piste ciclabili, rete viaria, opere pubbliche OpenCUP e controllo delle fonti da aggiornare a mano |

- 55 fogli del portale dei dati aperti della Regione e 3 dell'anagrafe degli amministratori: lo script tiene solo le
  colonne già pubblicate, così i contatti dei privati restano fuori anche se la fonte li aggiunge; ricollega le righe ai
  comuni (anche quelli fusi o scritti in forma abbreviata), ricalcola conteggi, totali del registro e punti della mappa.
  Prova del 6 ottobre 2026: tutti i 58 fogli si ricostruiscono identici dalla fonte, salvo 10 righe che ora risultano
  collegate al loro comune.
- La rete degli autobus (`scripts/aggiorna_autobus.py`) si controlla ogni lunedì, perché gli orari cambiano in date
  precise; il file si riscrive solo se cambiano fermate o percorsi.
- Fonti da aggiornare a mano (Annuario statistico, scuole, ISTAT, ISPRA, CONI, RUNTS, FIDAL, Consiglio regionale):
  `scripts/controlla_fonti.py`, nel gruppo 4, confronta data e versione dichiarate dal sito con quelle salvate in
  `dati/fonti_manuali.json` e, se sono cambiate, apre o aggiorna su GitHub la segnalazione «Fonti da aggiornare a mano».
  RUNTS, FIDAL e Consiglio regionale non dichiarano né data né versione: vanno controllati a vista.
- Si pubblica solo se qualcosa è cambiato. Se un foglio non si scarica o cambia struttura resta com'è e l'esito lo
  segnala. Si può avviare a mano da Actions, «Aggiorna i dati», «Run workflow», scegliendo il gruppo o «tutti».

## Dati personali

Dall'archivio sono tolti telefoni, email, PEC, siti, indirizzi, partite IVA e nomi dei rappresentanti legali di
associazioni, imprese e strutture ricettive. Restano i nomi di enti e imprese come iscritti nei registri pubblici e
i dati di amministratori, uffici e servizi pubblici.

## Seconda fonte: «Regione FVG Dati»

Dalla banca dati «Regione FVG Dati» (versione 5 del 16 settembre 2026, file fornito
dall'autore) sono stati aggiunti solo i contenuti assenti dal database:

| Contenuto | Fogli |
|---|---|
| Integrazioni ISTAT: età, stranieri, bilancio demografico 2025, serie 2002-2026, previsioni al 2050, cittadinanze | `RC26_Int_19_1` … `RC26_Int_19_6` |
| Redditi IRPEF 2024 per comune (Dipartimento delle Finanze) | `RC26_Int_13_1` |
| Piano economico finanziario dei rifiuti e servizio idrico (AUSIR) | `RC26_Int_2_1`, `RC26_Int_2_2`, `RC26_Int_4_1` |
| Terzo settore, sport e cultura per comune | `RC26_Int_16_1`, `RC26_Int_18_1`, `RC26_Int_18_2` |
| Società sportive del Registro CONI 2.0 (1.537) | `Sport_CONI_2026` |
| Associazioni culturali censite (178) | `Associazioni_culturali_2026` |
| Dati di dettaglio del RUNTS (volontari, dipendenti, PEC, forma giuridica) e 18 enti in più | `RUNTS_dettagli_set_2026` |
| Tre tavole dell'Annuario assenti dai fogli C26 | `RC26_Tav_4_4_completa`, `RC26_Tav_4_5_bis`, `RC26_Tav_7_3_bis` |
| Cartine dell'Annuario trascritte per comune e per regione | `Cartine_comunali_2026`, `Cartine_regionali_2026` |
| Glossario e presentazione dei capitoli | `Glossario_Annuario_2026`, `Annuario_2026_capitoli` |

Le altre 293 tavole e grafici dell'Annuario erano già nei fogli C26 e non sono stati
duplicati. Le classi delle cartine sono state lette dall'immagine pubblicata.

## Avvertenze

- Totale dei residenti al 31 dicembre 2025: la tavola 19.2 dell'Annuario dà 1.193.496, la
  sintesi «Regione in cifre 2026» dà 1.194.496. *DA VERIFICARE*: la pagina usa la tavola.
- Nel foglio Rifiuti_comunali del file originale l'anno è memorizzato come decimale
  (1,998 al posto di 1998; 2 al posto di 2000): la pagina lo mostra come anno intero.
- Le righe intestate a comuni poi fusi sono attribuite al comune attuale; quelle intestate a
  frazioni, a voci «NON DEFINITO» o a località fuori regione restano senza comune.
- Nei fogli senza colonna del comune il filtro cerca il nome del comune nel testo.

Realizzato da Guido Costalonga.
