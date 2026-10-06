# Atlante dei Comuni del Friuli Venezia Giulia

Pagina pubblicata su [costalonga.org/Atlante-FVG](https://costalonga.org/Atlante-FVG/).

I 215 comuni del Friuli Venezia Giulia comune per comune: popolazione, amministratori,
Terzo settore, servizi sanitari, scuole, turismo e ambiente. In più, l'archivio completo
del «Database Friuli Venezia Giulia»: 104 fogli e 345.716 righe, con tutte le colonne,
filtrabili per provincia, per comune, per testo e colonna per colonna.

## Come è fatta

| File | Contenuto |
|---|---|
| `index.html` | La pagina: HTML, stile e programma in un solo file, con i dati riassuntivi dei comuni incorporati |
| `dati/*.txt` | Un file per foglio del database (i fogli più grandi sono divisi in parti). Ogni file è JSON compresso con gzip e codificato in base64; la pagina lo scarica e lo decomprime solo quando il foglio viene aperto |
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

## Avvertenze

- Totale dei residenti al 31 dicembre 2025: la tavola 19.2 dell'Annuario dà 1.193.496, la
  sintesi «Regione in cifre 2026» dà 1.194.496. *DA VERIFICARE*: la pagina usa la tavola.
- Nel foglio Rifiuti_comunali del file originale l'anno è memorizzato come decimale
  (1,998 al posto di 1998; 2 al posto di 2000): la pagina lo mostra come anno intero.
- Le righe intestate a comuni poi fusi sono attribuite al comune attuale; quelle intestate a
  frazioni, a voci «NON DEFINITO» o a località fuori regione restano senza comune.
- Nei fogli senza colonna del comune il filtro cerca il nome del comune nel testo.

Realizzato da Guido Costalonga.
