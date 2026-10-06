# Atlante dei Comuni del Friuli Venezia Giulia

Pagina pubblicata su [costalonga.org/Atlante-FVG](https://costalonga.org/Atlante-FVG/).

I 215 comuni del Friuli Venezia Giulia comune per comune: popolazione, amministratori,
Terzo settore, sport, cultura, servizi sanitari, scuole, turismo, redditi e ambiente.
Con le mappe dei comuni (oltre 30 indicatori, 15 cartine dell'Annuario e 8 strati di servizi),
la mappa delle regioni d'Italia (24 cartine), il confronto fra quattro comuni, la scheda di
ogni comune stampabile in PDF e l'archivio completo: 136 fogli e quasi 450.000 righe,
filtrabili per provincia, per comune, per testo e colonna per colonna.

## Come è fatta

| File | Contenuto |
|---|---|
| `index.html` | La pagina: HTML, stile e programma in un solo file, con i dati riassuntivi dei comuni incorporati |
| `dati/*.txt` | Un file per foglio del database (i fogli più grandi sono divisi in parti). Ogni file è JSON compresso con gzip e codificato in base64; la pagina lo scarica e lo decomprime solo quando il foglio viene aperto |
| `dati/_mappe_0.txt` | Confini di comuni, province, regione e regioni italiane, con le classi delle 41 cartine dell'Annuario (stessa codifica degli altri file) |
| `dati/_punti_0.txt` | Punti della mappa dei servizi (farmacie, guardie mediche, residenze per anziani, fermate, accessi a internet, impianti dei rifiuti, stazioni meteo) già proiettati sul disegno della mappa |
| `scripts/aggiorna_dati.py` | Aggiornamento automatico dei dati aperti regionali che cambiano spesso |
| `.github/workflows/aggiorna-dati.yml` | Esegue l'aggiornamento ogni lunedì e pubblica le novità |
| `.nojekyll` | Dice a GitHub Pages di servire i file così come sono |

Ogni file di dati contiene le righe del foglio (`rows`) e, quando il foglio ha una colonna
del comune, l'indice del comune collegato a ciascuna riga (`k`), nello stesso ordine dei
comuni del foglio «Comuni».

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

## Aggiornamento automatico

Ogni lunedì `scripts/aggiorna_dati.py` riscarica dal portale dei dati aperti della Regione 18 fogli che cambiano
spesso (farmacie, guardie mediche, residenze per anziani, accessi a internet, turismo, siti inquinati, elezioni
comunali 2026, patrimonio regionale, strutture ricettive), ricollega le righe ai comuni, toglie i contatti dei privati,
ricalcola conteggi e punti della mappa e pubblica solo se qualcosa è cambiato. Se un foglio non si scarica o cambia
struttura resta com'è. Si può avviare a mano da Actions, «Aggiorna i dati aperti», «Run workflow».

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
