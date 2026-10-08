# Atlante dei Comuni del Friuli Venezia Giulia

Pagina pubblicata su [atlantefvg.it](https://atlantefvg.it/). Il vecchio indirizzo costalonga.org/Atlante-FVG rimanda qui.

I 215 comuni del Friuli Venezia Giulia comune per comune: popolazione, amministratori,
Terzo settore, sport, cultura, servizi sanitari, scuole, turismo, redditi e ambiente.
Con le mappe dei comuni (oltre 30 indicatori, 15 cartine dell'Annuario e 8 strati di servizi),
la mappa delle regioni d'Italia (24 cartine), la mappa degli autobus con linee, fermate e arrivi in tempo reale, il confronto fra sei comuni, la scheda di
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

## Il mio Comune, ricerca degli indicatori, confronto e link

- **Il mio Comune.** Nella pagina iniziale il filtro territoriale e «Il mio Comune» stanno in un solo blocco con un solo
  selettore: il pulsante con la stella (sotto il filtro territoriale e nella scheda del comune) salva il comune preferito in `localStorage` (chiave `atlante-fvg:mio-comune`, il nome del comune nell'indirizzo,
  per esempio `porcia`): nessuna registrazione, nessun invio. Il riquadro della pagina iniziale mostra provincia, residenti al
  31 dicembre 2025 e i collegamenti a scheda, meteo (`meteo/#porcia`), autobus e confronto; si cambia con il selettore e si toglie
  con «Rimuovi». Il preferito non imposta mai il filtro territoriale: contano la scelta esplicita e i collegamenti con `?comune=`.
  Se la memoria del browser non è disponibile il sito funziona e il comune vale finché la pagina resta aperta.
- **Ricerca degli indicatori.** Nella pagina Mappe il campo «Cerca un indicatore» filtra il selettore per nome e argomento,
  senza badare a maiuscole e accenti, mantiene i gruppi, annuncia il numero di risultati ai lettori di schermo, mostra un
  messaggio con il comando «Cancella la ricerca» quando non trova nulla; Invio apre il primo risultato, Esc cancella.
  L'indicatore mostrato sulla mappa resta scelto anche se non corrisponde alla ricerca (voce «In mappa»).
- **Confronto.** Fino a sei comuni (costante `CF_MAX`). A confronto vuoto compaiono «Confronta il mio Comune» (con il
  preferito e i tre comuni della provincia con popolazione più vicina) e un esempio (Roveredo in Piano, Porcia, Cordenons,
  San Quirino); «Azzera confronto» svuota i selettori; la scelta resta passando ad altre sezioni e dopo il ricaricamento
  (`sessionStorage`, solo nella scheda del browser in uso). L'intestazione con i nomi dei comuni e la colonna degli indicatori
  restano ferme mentre si scorre la tabella.
- **Link.** «Copia link» e «Condividi» (solo dove il sistema offre la condivisione) nelle mappe e nel confronto; il link
  conserva pagina, indicatore, livello, filtro territoriale e comuni a confronto. Senza accesso agli appunti compare una
  finestra con il link da copiare a mano. **Indietro e Avanti** ripristinano pagina, comune, indicatore e confronto
  dell'indirizzo; i parametri mancanti o non validi si ignorano.
- **Telefono.** Sui dispositivi touch ogni comando è alto almeno 44 pixel; il pizzico a due dita sulle mappe, descritto in
  «Grafica e uso sul telefono», resta e un dito continua a far scorrere la pagina.

Prova dei percorsi: `SITE=<cartella del sito> CHROMIUM=<chrome> node prove/percorsi.js` (vedi l'intestazione del file).

## Dossier del comune in PDF

Nella scheda di ogni comune il pulsante «Crea dossier PDF» apre una finestra di scelta e poi la stampa del browser («Salva come PDF»). Si scelgono gli argomenti (popolazione, economia e redditi, bilancio comunale, turismo, associazioni e Terzo settore, servizi, opere pubbliche, elezioni, rischio idrogeologico), fino a tre comuni di confronto (proposti quelli già nel confronto, altrimenti i tre della provincia con popolazione più vicina), le medie della provincia e della regione e i grafici.

Il documento è in A4 con testo selezionabile, pagine numerate («pagina N di M» nel piè di pagina), tabelle che non si spezzano fra le righe e intestazioni ripetute. Per ogni indicatore: valore del comune, comuni di confronto, medie territoriali, posto in regione, periodo e fonte; poi le opere più grandi, le liste più votate, i grafici a barre (comune, confronto, medie) e le serie storiche della scheda; in coda fonti, periodi e note di metodo. «n.d.» è un dato non disponibile, «0» un valore pari a zero, «non calc.» una media che i dati non permettono di calcolare correttamente.

**Medie territoriali.** Non sono mai la media semplice dei valori comunali: la regola di ogni indicatore sta nella tabella `AGG` del modello (somma per i totali; numeratore totale su denominatore totale per rapporti e percentuali; media ponderata con il peso indicato, per esempio i contribuenti per il reddito medio o i residenti al 1° gennaio 2024 per la spesa per abitante). Le ponderazioni che sono un'approssimazione lo dichiarano nella nota. Gli indicatori senza regola (affluenze, variazione del reddito, previsioni ISTAT) restano «non calc.». Le stesse medie sono usate dal confronto.

Prova: `node prove/dossier.js` (apre le opzioni, esclude un argomento, genera il PDF di controllo e verifica confronto, medie, note e ritorno alla pagina normale).

## Confronto avanzato

Nella pagina Confronto, oltre alla tabella dei sei comuni:

- **Comune di riferimento** (il primo scelto, modificabile): ogni altro comune mostra lo scostamento assoluto e percentuale dal riferimento; per gli indicatori in percentuale lo scostamento è in punti.
- **Medie della provincia del riferimento e del FVG**, calcolate con la stessa tabella `AGG` del dossier (somma, numeratore su denominatore, media ponderata), mai come media semplice dei valori comunali; il metodo compare passando sul valore e nelle colonne «Metodo» dei download. «non calc.» segnala le medie che i dati non permettono.
- **Scelta degli indicatori** (pannello «Scegli gli indicatori»), grafici a barre per i primi dodici scelti (oro il riferimento, blu gli altri, grigio le medie), con testo alternativo.
- **Esportazioni**: CSV ed Excel con medie, metodo e scostamenti; PNG dei grafici composto con titolo, legenda, fonti, marchio e data, in tre formati (documenti A4 orizzontale, presentazioni 16:9, social quadrato) tramite `esportaImmagine`.
- **Comuni di taglia simile** con criteri dichiarati e modificabili: popolazione più vicina (rapporto fra le popolazioni più vicino a 1), stessa provincia, stessa zona altimetrica e stesso grado di urbanizzazione (classificazioni ISTAT dall'Annuario 2026, cartine 1.2 e 1.4), eventualmente anche la densità. Se i criteri lasciano pochi comuni si allargano uno alla volta e il messaggio lo dice. I criteri restano salvati sul dispositivo e valgono anche per «Confronta il mio Comune» e per il dossier.
- Lo stato (riferimento, scostamenti, medie, grafici, indicatori) è nell'indirizzo: `rif`, `scost`, `medie`, `grafici`, `ind`.

Prova: `node prove/confronto.js`.

## Serie storiche e mappe nel tempo

- **Scheda del comune**: il grafico dei residenti 2002-2026 ha i selettori «Dal» e «Al» e mostra la variazione assoluta e percentuale dell'intervallo scelto; il grafico dei conti riporta la variazione della spesa corrente per abitante fra il primo e l'ultimo rendiconto disponibile. Gli anni senza dato non sono stimati né interpolati. Per i comuni nati da fusioni (Campolongo Tapogliano, Rivignano Teor, Valvasone Arzene, Fiumicello Villa Vicentina, Treppo Ligosullo) e per Sappada, passata dal Veneto nel 2017, la scheda dice che la serie è ricostruita dalla fonte sui confini attuali (tabella `FUSIONI`).
- **Mappe**: due indicatori nuovi, «Residenti al 1° gennaio (anno scelto)» e «Variazione dei residenti fra due anni», con i selettori dell'anno in mappa e dell'anno di confronto, lo scambio dei due anni e il passaggio alla mappa della variazione. Con «Stesse soglie per i due anni» (opzione predefinita) le classi della legenda sono calcolate sui valori di tutti e due gli anni, così le due mappe si confrontano a colpo d'occhio; si può togliere. Lo stato è nell'indirizzo (`anno`, `anno2`, `soglie=libere`).
- La sola serie con definizione e territorio comparabili per tutti i 215 comuni è quella dei residenti (Annuario 2026, tavola 19.4, ricostruzione intercensuaria ISTAT fino al 2019). Le altre serie della scheda (rendiconti 2018-2023, presenze 2022-2025, raccolta differenziata 1998-2017, opere per anno) restano grafici per comune, senza mappa per anno.

Prova: `node prove/serie.js`.

## Mappe e grafici esportabili

- **Mappa dei comuni e delle regioni**: menu «Scarica l'immagine» con formato (documenti A4 orizzontale 2000×1414, presentazioni 16:9 1920×1080, social quadrato 1080×1080) e scarico in **PNG** o in **SVG**. Lo SVG (`svgMappaCompleta`) è un documento autonomo con titolo, sottotitolo (territorio, unità, periodo), mappa con i 215 comuni, legenda, fonte, marchio e data, testi veri e modificabili, logo incorporato; il PNG è composto da `esportaImmagine` con gli stessi elementi. Nessun comando dell'interfaccia finisce nell'immagine; i nomi dei file portano l'indicatore e, per la serie storica, gli anni.
- **Grafici della scheda del comune** (residenti, conti, opere per anno, presenze, raccolta differenziata): pulsante «Scarica PNG» sotto ogni grafico, con titolo, comune, periodo, fonte e marchio.
- **Grafici del confronto**: vedi il paragrafo sul confronto avanzato.
- La base cartografica dei confini è quella dell'Atlante (`dati/_mappe_0.txt`); le mappe stradali e satellitari delle pagine Stradario, Orari e Servizi hanno attribuzioni obbligatorie (OpenStreetMap, Esri) e non si esportano da qui.

Prova: `node prove/immagini.js` (SVG e tre PNG della mappa, PNG di un grafico; immagini controllate a occhio).

## Cosa è cambiato (registro degli aggiornamenti)

La pagina `aggiornamenti/` elenca ogni modifica pubblicata con data, tipo (nuovi dati, correzione, metodo, funzione nuova), origine (automatica o redazionale), dati o servizi interessati con il collegamento alla sezione, descrizione e, quando il flusso li registra, i valori di prima e di dopo con la differenza (righe dei fogli, fermate e percorsi della rete, voci dei bandi). In fondo, per ogni foglio dell'archivio, l'ultima consultazione della fonte e il periodo dei dati dichiarato nell'indice.

Il registro è `dati/aggiornamenti.json`, costruito da `scripts/registro_aggiornamenti.py` leggendo la storia del repository (`git log --first-parent`): parte dalla prima versione pubblicata (6 ottobre 2026) e non ricostruisce nulla a mano. I flussi automatici scaricano la storia completa (`fetch-depth: 0`), rigenerano il registro dopo aver scritto il messaggio dell'aggiornamento e lo includono nello stesso commit prima di pubblicarlo. Dopo una modifica redazionale si rigenera con `python scripts/registro_aggiornamenti.py` (il commit in corso entra al prossimo giro, oppure si passa `--messaggio` e `--corpo`).

Prova: `node prove/aggiornamenti.js`.

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
- Pagina Mappe: indicatore e comune sulla stessa riga, mappa subito visibile, legenda a lato della mappa su desktop (sopra la mappa solo a schermo intero) e
  sotto sul telefono, indicatore in un solo campo con ricerca ed elenco, scheda del comune selezionato con nome, valore, unità e posizione (sul telefono in un pannello
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
pagina, riporta la propria fonte e la data di consultazione. L'archivio statistico è una raccolta
di dati con date di riferimento diverse. Arrivi degli autobus e bollettini di allerta vengono
consultati al momento; i dati sulla qualità dell'aria sono medie giornaliere validate, pubblicate
con ritardo.

## Altre fonti aggiunte il 6 ottobre 2026

| Contenuto | Fonte | Fogli |
|---|---|---|
| Rischio idrogeologico per comune: frane (2024) e alluvioni (2020), con residenti, famiglie, edifici, imprese e beni culturali esposti | ISPRA, piattaforma IdroGEO | `Rischio_idrogeologico_ISPRA` |
| Rendiconti comunali 2018-2023: spese per missione, programma e titolo; entrate per titolo e tipologia (84 comuni) | Portale dei dati aperti della Regione FVG | `Bilanci_rendiconto_spese`, `Bilanci_rendiconto_entrate`, `Bilanci_comunali_sintesi` |
| Elezioni regionali 2023: liste, presidente, affluenza | Portale dei dati aperti della Regione FVG | `Elezioni_regionali_2023_*` |
| Elezioni europee 2024 e Camera 2022 per comune | Ministero dell'interno, Eligendo | `Elezioni_europee_2024`, `Elezioni_camera_2022` |
| Radon nelle scuole e in altri luoghi (1.394 punti, stato del radon per ciascuno), parchi e giardini del patrimonio culturale (226), rifugi alpini escursionistici (44, senza gli indirizzi di posta elettronica). Aggiunti l'8 ottobre 2026, licenza IODL (Italian Open Data License) | Portale dei dati aperti della Regione FVG (ARPA FVG, SIRPAC, Direzione attività produttive) | `Radon_scuole_ARPA`, `Parchi_e_giardini`, `Rifugi_alpini` |

I tre fogli dell'8 ottobre si aggiornano con la rotazione settimanale (gruppi 1, 4 e 2). Si può aggiornare un solo foglio, o più separati da virgola, con `python scripts/aggiorna_dati.py --foglio Nome1,Nome2` (con `--prova` non scrive nulla). Prova: `node prove/fogli.js`.

Nei rendiconti alcune viste regionali ripetono le stesse righe (una, intitolata a Ragogna, contiene i dati di
Roveredo in Piano): i doppioni sono tolti tenendo una riga per anno, comune e voce di bilancio.

## Qualità dei dati e registro degli errori (fase 2)

- **Fonti e accesso**: ogni integrazione nuova dichiara la fonte ufficiale, come si legge (esportazione CSV, pagine, dataset), la copertura, la frequenza e i limiti, nella pagina stessa, in Metodo e fonti e in questo file.
- **Controlli**: i finanziamenti controllano duplicati (chiave della riga), importi non numerici, date non valide, estremi mancanti ed esportazioni senza intestazione, e tengono un registro degli errori nell'indice (`dati/finanziamenti_indice.json`, `controlli` ed `errori`), con l'elenco delle finestre di date che il portale non ha servito e dei mesi senza dati. I bandi scartano le voci duplicate, validano le date e segnalano le pagine non lette. Le opere raggruppano le righe per CUP. I servizi riportano le scuole senza posizione.
- **Ultima versione valida**: ogni flusso lascia i dati di prima quando la fonte non risponde o il risultato sembra incompleto (bandi: meno di 20 voci o meno del 40% di prima; finanziamenti: nessuna esportazione valida; opere: meno di 20.000 progetti; dati aperti: meno della metà delle righe).
- **Dati non aggiornati**: la pagina «Cosa è cambiato» ha la tabella «Stato dei flussi automatici» con l'ultima lettura di ogni servizio e l'avviso «dati forse non aggiornati» quando la lettura è più vecchia del previsto; la pagina dei finanziamenti elenca i mesi senza dati.
- **Nessun dato dimostrativo**: tutte le pagine leggono file prodotti dalle fonti; quando una fonte non è accessibile la pagina lo dice e rimanda alla fonte. Nessuna chiave o credenziale è nel codice (i flussi usano solo il `GITHUB_TOKEN` fornito da GitHub).
- **Controllo del rilascio**: `scripts/controlla_rilascio.py` verifica anche i file nuovi (`bandi.json`, `aggiornamenti.json`, `opere_meta.json`, `comuni_slug.json`, `finanziamenti_indice.json`, `servizi.json`).

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
La fermata di partenza si sceglie dalla tendina oppure toccandola sulla mappa del percorso (Leaflet con lo sfondo di
OpenStreetMap, caricati solo quando si sceglie una linea; sul telefono la mappa si muove con due dita, un dito scorre la
pagina). Dalla pagina Autobus ci si arriva con «Orari delle linee», con «Orari di questa linea» per la linea scelta e, dal
pannello di una fermata toccata sulla mappa, con «Orari delle partenze da qui»: la pagina Orari elenca allora le linee che
passano da quella fermata. Nell'indirizzo la fermata è indicata con il suo codice (`?fermata=01001`), lo stesso della rete
degli autobus.

I dati vengono dallo stesso GTFS di TPL FVG distribuito da BusOne. `scripts/aggiorna_orari.py` lo scarica ogni lunedì
insieme alla rete degli autobus e scrive `dati/orari/indice.txt` (validità, calendario dei servizi giorno per giorno,
fermate con il loro comune, linee) e un file per percorso in `dati/orari/`, chiamato con il codice del percorso; riscrive
solo i file cambiati e toglie quelli dei percorsi soppressi. Se il download fallisce o il GTFS sembra incompleto (meno di
100 linee o di 10.000 corse), gli orari restano quelli di prima. La fonte ripete alcune corse identiche: se ne tiene una.
Nella versione del 6 ottobre 2026 gli orari valgono dal 5 ottobre 2026 al 31 gennaio 2027. Per i giorni fuori da questo
periodo la pagina non mostra orari e rimanda a [tplfvg.it](https://tplfvg.it).

## Bandi e contributi del Friuli Venezia Giulia

La pagina `bandi/` mostra i bandi, gli avvisi e gli atti pubblicati nella sezione «Bandi e avvisi» della Regione Autonoma Friuli Venezia Giulia. Per ogni voce si leggono l'elenco ufficiale e la pagina del bando (`scripts/aggiorna_bandi.py`, ogni mattina con `.github/workflows/aggiorna-bandi.yml`): titolo, struttura e servizio, date, testo, campi con etichetta scritti dalla struttura (destinatari, attività finanziabile, requisiti, spese ammissibili, dotazione, contributo, modalità e termini, riferimenti normativi), allegati con formato, data di ultima verifica. Le etichette variano da bando a bando e molti non ne hanno: la scheda lo dice («non riportato in forma strutturata nella pagina ufficiale: vedi il bando») e rimanda al bando e agli allegati, dove fanno fede requisiti e importi.

- **Filtri**: parola chiave (titolo, testo, campi), settore (dalla struttura regionale), struttura, stato (aperti e in apertura, solo aperti, solo in apertura, solo scaduti, tutti), tipo (si presenta domanda; atti ed esiti: graduatorie, elenchi di beneficiari, riparti, concessioni già deliberate; altri avvisi), scadenza (entro 7, 30, 90 giorni), territorio (comune nominato nel titolo o nei destinatari), destinatari (Comuni, altri enti pubblici, associazioni e Terzo settore, imprese, cittadini), misure contributive (indicazione della Regione), preferiti, Centri per l'impiego e Collocamento mirato. Lo stato è nell'indirizzo.
- **Classificazioni dell'Atlante**, dichiarate nella pagina come indicative: destinatari dal campo della pagina o da parole chiave del titolo (`DESTINATARI` nello script); settore dalla struttura (`SETTORI`); tipo da parole del titolo (`classifica`); «in apertura» quando il testo indica una data di avvio delle domande successiva a oggi; comune collegato solo se nominato espressamente, mai dedotto dalla sede della struttura. Un bando «si presenta domanda» è distinto da un atto che assegna contributi già deliberati.
- **Preferiti** salvati sul dispositivo (`localStorage`, chiave `atlante-fvg:bandi-preferiti`) con filtro dedicato; **calendario ICS** per il singolo bando e per tutte le scadenze visibili (eventi di un giorno alla scadenza, con il collegamento alla pagina ufficiale).
- **Scheda del comune**: collegamento «Bandi che nominano il comune». L'elenco dei comuni con nome e slug per le pagine autonome è `dati/comuni_slug.json`.
- **Limiti**: solo l'elenco della Regione (niente Stato, Unione europea, PNRR, GAL, fondazioni); le voci che rimandano al portale `bandiformazione.regione.fvg.it` non hanno il dettaglio; dotazione e contributo massimo compaiono solo se la pagina li scrive con un'etichetta. Se la lettura fallisce o l'elenco sembra incompleto restano i dati di prima; le pagine non lette sono segnalate.
- **Prova**: `node prove/bandi.js`.

## Osservatorio delle opere pubbliche

La pagina `opere/` mostra i lavori pubblici con CUP localizzati in Friuli Venezia Giulia dai dati OpenCUP già presenti nell'archivio (`dati/Opere_pubbliche_OpenCUP_*.txt`, letti nel browser; `dati/opere_meta.json` con data dei dati, colonne e file, scritto da `scripts/aggiorna_opere.py`). Una scheda per CUP (le righe per progetto e comune sono raggruppate: la stessa opera non si conta due volte) con descrizione, comuni, ente responsabile, settore e categoria, costo e finanziamento previsti, fonti di copertura dichiarate, stato amministrativo del CUP, anno della decisione e data del CUP, fonte e data dell'ultimo aggiornamento, collegamento all'archivio dei finanziamenti con lo stesso CUP. Ricerca per descrizione, CUP o ente, comune, anno, stato, settore, solo opere in un comune; totali con il criterio di conteggio (si sommano solo le opere in un solo comune con costo noto); CSV.

Avvertenze scritte nella pagina: lo stato del CUP non dice se i lavori sono iniziati o finiti e l'Atlante non lo deduce; date previste ed effettive di inizio e fine lavori non sono nella fonte; il costo è quello previsto alla decisione. Collegamento dalla scheda del comune («Schede delle opere di…»). Prova: `node prove/opere.js`.

## Finanziamenti regionali (atti di concessione)

La pagina `finanziamenti/` è l'archivio dei vantaggi economici concessi dalla Regione e dagli enti che pubblicano nella sua Amministrazione trasparente (Comuni, aziende sanitarie, ERSA, FVG Plus, Consiglio regionale e altri), sezione «Concessione e attribuzione di vantaggi economici» (articoli 26 e 27 del decreto legislativo 33/2013; articolo 7 della legge regionale 7/2014). `scripts/aggiorna_finanziamenti.py` esporta il CSV ufficiale a finestre di dieci giorni (il server rifiuta gli intervalli lunghi e spesso risponde 502 o 503: si riprova, si spezza a cinque giorni, e le finestre non scaricate restano elencate nell'indice), scrive un file per mese di pubblicazione in `dati/fin/AAAA-MM.txt` (stesso formato compresso degli altri fogli) e l'indice `dati/finanziamenti_indice.json` (mesi, totali, enti, settori, controlli, registro degli errori, esito dell'ultima lettura). Il flusso `.github/workflows/aggiorna-finanziamenti.yml` lo esegue ogni mercoledì sugli ultimi quaranta giorni; con `--da` si ricarica un periodo.

- **Una riga = un beneficiario in un atto**; gli atti con più beneficiari sono collegati dalla chiave (ente, anno, numero) e contati una volta. Le righe identiche esportate due volte sono scartate e contate nei controlli.
- **Fasi**: la fonte pubblica importo concesso ed erogato; stanziamenti e impegni non sono pubblicati e non si deducono. I totali sommano solo importi dello stesso tipo sulle righe filtrate e il criterio è scritto nella pagina.
- **Territorio** solo con criterio documentato, mostrato accanto al valore: ente concedente = Comune; CUP localizzato in OpenCUP (se in più comuni, importo non ripartito); comune nominato nell'oggetto. Mai dalla sede del beneficiario. Gli atti regionali senza comune restano «ambito regionale o non indicato».
- **Persone fisiche**: nome e codice fiscale non ripubblicati (restano ente, finalità, importo). **Settore**: classificazione indicativa da parole chiave (`SETTORI`).
- **Collegamenti**: ricerca sul portale per numero e anno dell'atto, atto di concessione e bando quando la fonte dà il collegamento, scheda dell'opera per i CUP presenti in OpenCUP.
- **Controlli**: righe lette, duplicati scartati, importi non numerici, date mancanti, estremi assenti; tutto nell'indice e in fondo alla pagina. Se il portale non risponde restano i dati di prima e la pagina lo dice.
- Prova: `node prove/finanziamenti_pagina.js`.

## Servizi sul territorio

La pagina `servizi/` mette su una sola mappa (Leaflet, tessere OpenStreetMap) i punti con coordinate già nell'archivio: farmacie (con telefono e orari del dataset regionale), parafarmacie, guardie mediche, residenze per anziani, scuole statali (sedi degli istituti 2026/27, posizione ricavata dall'indirizzo con Nominatim e dichiarata «da verificare»: `scripts/geocodifica_scuole.py`, `dati/scuole_coord.json`) e fermate degli autobus (rete TPL FVG, con il collegamento agli orari). `scripts/prepara_servizi.py` costruisce `dati/servizi.json` con fonte e data di consultazione per categoria e il centro di ogni comune; gira ogni lunedì con i dati aperti. Gli impianti sportivi del registro CONI non hanno indirizzo e restano fuori.

Si parte da un comune, da un indirizzo (Photon, limitato alla regione), da un punto toccato sulla mappa o dalla posizione del dispositivo, chiesta solo premendo il pulsante e mai inviata all'Atlante né messa nell'indirizzo della pagina. L'elenco a fianco dà i servizi più vicini con la distanza **in linea d'aria**: percorsi stradali e tempi di viaggio non sono mostrati perché non c'è un servizio di calcolo integrato, e la pagina lo scrive. Lo stato (categorie, punto, comune) è nell'indirizzo. Prova: `node prove/servizi.js`.

## Stradario

La pagina `stradario/` è la versione regionale della «Mappa di Roveredo in Piano» di costalonga.org: mappa stradale
(OpenStreetMap) e satellitare (Esri) di tutto il Friuli Venezia Giulia, ricerca di vie, piazze e luoghi con il
geocodificatore Photon (dati OpenStreetMap, limitato ai confini della regione, senza le fermate dell'autobus), scelta
rapida di uno dei 215 comuni, posizione del telefono e collegamento condivisibile. Aperta con `?comune=<nome>` parte già
centrata sul comune con il segnaposto e il cartellino; un punto scelto resta nell'indirizzo come `#latitudine,longitudine,zoom`.
`scripts/genera_stradario.py` la genera prendendo i comuni, con le coordinate, dalla pagina Meteo. Mappa e ricerca sono
scaricate dal browser di chi visita la pagina; la posizione, se richiesta, resta sul dispositivo.

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
Il flusso `.github/workflows/aggiorna-opere.yml` lo esegue il 4 di ogni mese. **Chi finanzia le opere.** Dagli stessi dati si ricavano, per i progetti decisi negli ultimi cinque anni e localizzati in un solo
comune, la quota del costo previsto che sta in progetti con la Regione, lo Stato o l'Unione europea fra le fonti di copertura, e
la quota coperta dal solo comune (campi `finReg`, `finSta`, `finUE`, `finCom` di `const EXTRA`; riquadro nella scheda del comune,
righe del confronto, indicatori delle mappe). Una copertura può avere più fonti insieme e OpenCUP non dice quanto dà ciascuna:
le quote non si sommano a cento e non sono importi versati dagli enti. Si ricalcolano senza scaricare nulla con
`python scripts/aggiorna_opere.py --da-foglio`; con l'aggiornamento mensile si aggiornano da soli. Prova: `node prove/finanziamenti.js`.
**Serie storiche nella scheda del comune.** Due grafici nuovi: «Conti del comune negli anni» (spesa corrente e investimenti impegnati per abitante, dal foglio `Bilanci_comunali_sintesi`, letto quando si apre la scheda; compare con almeno due anni) e «Opere pubbliche decise ogni anno» (campo `opAnni` di `const EXTRA`: progetti e costo previsto per anno della decisione, ultimi dieci anni, solo progetti nel solo comune; l'anno in corso è parziale). Ogni grafico ha il testo alternativo con tutti i valori.
Non sono stati usati OpenCoesione (rifiuta gli accessi dall'estero, come Italia Domani) né il portale dati regionale, che non ha elenchi di contributi.
I dati non distinguono i progetti PNRR: il
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

- Totale dei residenti al 31 dicembre 2025: 1.193.496, uguale nel volume «Regione in cifre 2026»
  (tavole 1.1 e 19.2), nella somma dei 215 comuni e nel bilancio demografico mensile ISTAT 2025
  (dato provvisorio, letto il 6 ottobre 2026 su https://demo.istat.it/app/?i=D7B&l=it). Il 1.194.496 compare
  solo nella «Sintesi dei dati» di cinque pagine del 21 settembre 2026 e non trova riscontro.
- Nel foglio Rifiuti_comunali del file originale l'anno è memorizzato come decimale
  (1,998 al posto di 1998; 2 al posto di 2000): la pagina lo mostra come anno intero.
- Le righe intestate a comuni poi fusi sono attribuite al comune attuale; quelle intestate a
  frazioni, a voci «NON DEFINITO» o a località fuori regione restano senza comune.
- Nei fogli senza colonna del comune il filtro cerca il nome del comune nel testo.

Realizzato da Guido Costalonga.

## Revisione dell'8 ottobre 2026: criticità di lettura su computer e telefono

- **Confronto**: i sei selettori portano il testo breve «Comune 1…6»; i comandi (Azzera, Comuni di taglia simile) compaiono solo
  dopo la scelta e le azioni secondarie stanno nel menu «Condividi e scarica» (link, condivisione, copia per Excel, CSV, Excel);
  senza comuni resta un messaggio compatto al posto della tabella, senza altezza minima; se il filtro territoriale ha un comune,
  l'avvio propone «X e i comuni di taglia simile».
- **Pagina iniziale**: «Il mio Comune» e il filtro territoriale sono un solo blocco con un solo selettore; i servizi aggiornati
  sono raggruppati per tema (Trasporti e strade, Meteo e ambiente, Risorse pubbliche, Territorio), ogni gruppo su una riga.
- **Mappe**: legenda nella colonna a lato su desktop, così non copre il Tarvisiano; un solo campo «Indicatore» con ricerca ed elenco
  a tendina (`#cercaInd` con ruolo combobox, `#listaInd`; il `select` nascosto resta il portatore dello stato); etichette allineate;
  sul telefono il riquadro segue le proporzioni della regione (10/9) e i nomi dei capoluoghi sono più grandi; «Servizi sulla
  mappa» con la descrizione sotto il titolo nelle colonne strette; esportazioni nel menu «Scarica l'immagine».
- **Archivio**: righe su una sola riga (valori troncati con il testo completo al passaggio e nel dettaglio della riga), ombra sui
  bordi e avviso «la tabella continua a destra» quando serve (classe `scorri-x`, usata anche nel confronto); la fonte è mostrata
  con un nome leggibile (`descriviFonte`, titoli del portale dei dati aperti letti dal foglio `Catalogo_OpenData`); i nomi dei
  fogli nell'elenco laterale vanno a capo.
- **Autobus**: «Linee con più corse» spiega che il riquadro colorato è il numero della linea e mostra a destra le corse
  programmate; sotto la mappa sono elencate le linee che proseguono fuori regione (`tpLineeFuori`, tracciato oltre il riquadro
  delle fermate regionali).
- **Filtro territoriale compatto** nelle pagine Metodo, Autobus e Allerte e aria: una riga con lo stato e il pulsante «Scegli un
  comune» / «Cambia» che apre i campi (`FILTRO_COMPATTO`).

## Colori delle liste nelle mappe elettorali (8 ottobre 2026)

Le tre mappe «Lista più votata» (regionali 2023, europee 2024, politiche 2022) e l'elenco «Come ha votato» nella scheda del
comune usano colori vicini a quelli consueti dei partiti (`COLORI_LISTE`, `coloreLista`): blu scuro Fratelli d'Italia, verde Lega,
azzurro Forza Italia, azzurro chiaro per le civiche del centrodestra (Fedriga Presidente, Autonomia Responsabile), rosso Partito
Democratico, rosa e cremisi per Alleanza Verdi e Sinistra e Open Sinistra, giallo Movimento 5 Stelle, magenta Azione e Italia Viva,
giallo scuro Patto per l'Autonomia, arancione tenue per le civiche del centrosinistra, arancione Slovenska Skupnost, grigio SVP. Riferimento: i codici del modulo
«Partiti/Configurazione» di Wikipedia in italiano, letti l'8 ottobre 2026; le liste non riconosciute prendono i colori neutri della
tavolozza `CAT`. L'indicatore «Anno delle prossime elezioni comunali» resta con la tavolozza neutra.

## Sezione riservata «Elezioni regionali e comunali» (8 ottobre 2026)

La pagina `elezioni/` ospita il cruscotto delle elezioni regionali (2008, 2013, 2018, 2023) e comunali nei 215 comuni, con
intestazione, piè di pagina, colori e caratteri dell'Atlante. I contenuti non stanno in chiaro nel repository: il file
`elezioni/contenuto.json` è il frammento HTML (stile, dati, codice) compresso con gzip e cifrato con AES-GCM a 256 bit; la chiave
deriva dalla parola d'ordine con PBKDF2 (SHA-256, 300.000 giri, sale casuale). La pagina scarica il file, deriva la chiave nel
browser con WebCrypto, decifra, decomprime e inserisce il frammento; la parola d'ordine non viene mai trasmessa. La chiave resta in
`sessionStorage` (`atlante-fvg:elezioni-chiave`) finché la scheda è aperta; «Chiudi la sezione riservata» la cancella.
La pagina è `noindex`, non è nella sitemap ed è raggiungibile dalla pagina iniziale (gruppo «Voto») e dal menu «Altro».

Come aggiornare il contenuto (il file sorgente in chiaro non va mai pubblicato):
```
python3 -I scripts/prepara_elezioni.py <cruscotto.html> /tmp/frammento.html
PAROLA='…' node scripts/cifra_pagina.js /tmp/frammento.html elezioni/contenuto.json
```
Due funzioni sono state aggiunte dall'Atlante al cruscotto (`scripts/prefliste.js`, innestato da `prepara_elezioni.py`): nella lente della mappa
«Preferenze di un candidato» un campo di ricerca per nome accanto all'elenco; la sezione «Le preferenze di una lista, comune per comune»
(circoscrizione e lista a scelta: per ogni comune i voti alla lista, le preferenze a ciascun candidato e i totali di riga e di colonna, con
scarico in CSV; per il 2013 e il 2008 solo i totali di circoscrizione, come pubblica la fonte).
`prepara_elezioni.py` confina lo stile sotto `#elezioni`, lo porta alla tavolozza dell'Atlante (le variabili di base sono quelle di
`pagine.css`), rinomina le classi che si scontrano con lo stile comune (`campo`, `nota`), toglie intestazione propria, tema scuro
e scarico della pagina, e corregge i riferimenti al documento. Limite: una parola d'ordine breve resiste poco a un attacco a forza
bruta condotto fuori dal browser; la protezione serve a tenere la sezione fuori dalla consultazione pubblica, non a custodire segreti.
