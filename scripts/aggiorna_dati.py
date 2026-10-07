#!/usr/bin/env python3
"""Aggiorna l'Atlante dalle fonti che si possono riscaricare in automatico, un quarto alla volta.

Le fonti sono divise in quattro gruppi: ogni lunedì il flusso «Aggiorna i dati» ne aggiorna uno,
scelto contando le settimane da lunedì 5 gennaio 2026, così in quattro settimane tutto il sito è aggiornato.

- Gruppo 1: anagrafe degli amministratori locali (sindaci, giunte, consigli, enti, elezioni),
  servizi sanitari, siti inquinati, elezioni comunali, patrimonio, protezione civile, partecipate.
- Gruppo 2: turismo comunale e strutture ricettive, agriturismi, fattorie didattiche, biologico.
- Gruppo 3: commercio comunale, redditi, lavoro, scambi con l'estero, veicoli.
- Gruppo 4: rifiuti, stazioni meteo, ciclovie, rete viaria (e, nel flusso, le opere pubbliche
  OpenCUP e il controllo delle fonti da aggiornare a mano).

Per ogni foglio scarica il CSV dal portale dati.friuliveneziagiulia.it (o i JSON dell'anagrafe
degli amministratori), collega ogni riga al suo comune, tiene solo le colonne già pubblicate
(così telefoni, email, partite IVA e indirizzi dei privati restano fuori anche se la fonte li
aggiunge), riscrive il file in dati/ e aggiorna dentro index.html l'indice dei fogli (righe,
data, conteggi per comune) e i totali per comune usati da registro, grafici e scheda.

Se un foglio non si scarica o cambia struttura, lo lascia com'è e lo segnala: non scrive mai dati
incompleti. Usa solo la libreria standard di Python.

Uso: python scripts/aggiorna_dati.py [--gruppo N | --tutti] [--prova] [--quale-gruppo]
  --gruppo N  aggiorna il gruppo N (da 1 a 4); senza opzioni, il gruppo della settimana
  --tutti     aggiorna tutti i gruppi
  --prova     non scrive nulla: confronta i dati della fonte con quelli pubblicati
  --quale-gruppo  scrive soltanto il numero del gruppo di questa settimana
"""
import base64, csv, datetime, gzip, io, json, math, re, sys, time, unicodedata, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINA = RADICE / 'index.html'
PORTALE = 'https://www.dati.friuliveneziagiulia.it/api/views/{}/rows.csv?accessType=DOWNLOAD'
ANAGRAFE = 'https://elezioniamministratori.regione.fvg.it/distribuzione/json/'

# foglio: (collegamento ai comuni, gruppo); l'indirizzo sul portale è quello indicato come fonte nell'indice dei fogli
# collegamento: elenco di (colonna, metodo) con metodo c = codice ISTAT, n = nome del comune,
# s = nome alla fine dell'indirizzo; 'm' = sede e comuni serviti; 't' = nome del comune cercato nel testo
FOGLI = {
    # gruppo 1: servizi, ambiente, elezioni comunali, patrimonio
    'Farmacie': ([('idComune', 'c'), ('comune', 'n')], 1),
    'Parafarmacie_2024': ([('codice_comune', 'c'), ('comune', 'n')], 1),
    'Guardie_mediche': ('m', 1),
    'Residenze_anziani': ([('citta', 'n')], 1),
    'Punti_WiFi': ([('Indirizzo', 's')], 1),
    'Siti_inquinati_2025': ([('DENCOMUNE', 'n')], 1),
    'Protezione_civile': ([('Località', 'n')], 1),
    'Elezioni_comunali_2026': ([('Codice Istat Comune', 'c'), ('Nome Comune', 'n')], 1),
    'Elezioni_comunali_2025': ([('Codice Istat Comune', 'c'), ('Nome Comune', 'n')], 1),
    'Elezioni_comunali_2024': ([('Codice Istat Comune', 'c'), ('Nome Comune', 'n')], 1),
    'Demanio_culturale': ([('Comune', 'n')], 1),
    'Patrimonio_disponibile': ([('Comune', 'n')], 1),
    'Patrimonio_indisponibile': ([('Comune', 'n')], 1),
    'Partecipate_2024': ('t', 1),
    # gruppo 2: turismo e agricoltura
    'Turismo_comunale': ([('COMUNE_CODICE', 'c'), ('COMUNE', 'n')], 2),
    'Affittacamere': ([('COMUNE', 'n')], 2),
    'Bed_and_Breakfast': ([('COMUNE', 'n')], 2),
    'Marina_Resort': ([('COMUNE', 'n')], 2),
    'Campeggi': ([('COMUNE', 'n')], 2),
    'Alloggi_agrituristici': ([('COMUNE', 'n')], 2),
    'Ricettivita_sociale': ([('COMUNE', 'n')], 2),
    'Alberghi_diffusi': ([('comune', 'n')], 2),
    'Alberghi_RTA': ([('comune', 'n')], 2),
    'Agriturismi_2017': ([('Comune', 'n')], 2),
    'Fattorie_didattiche_2017': ([('COMUNE', 'n')], 2),
    'Operatori_biologici_2020': ([('Indirizzo Azienda', 's')], 2),
    # gruppo 3: commercio, economia, veicoli
    'Commercio_Udine': ([('Comune Codice', 'c')], 3),
    'Commercio_Gemonese_2025': ([('Comune Codice', 'c')], 3),
    'Commercio_Pravisdomini': ([('Comune Codice', 'c')], 3),
    'Commercio_Chions': ([('Comune Codice', 'c')], 3),
    'Commercio_Azzano': ([('Comune Codice', 'c')], 3),
    'Commercio_Canal_Ferro': ([('Comune Codice', 'c')], 3),
    'Commercio_Cordenons': ([('Comune Codice', 'c')], 3),
    'Commercio_Tavagnacco': ([('Comune Codice', 'c')], 3),
    'Commercio_Treppo_Grande': ([('Comune Codice', 'c')], 3),
    'Commercio_Buja': ([('Comune Codice', 'c')], 3),
    'Commercio_Caneva': ([('Comune Codice', 'c')], 3),
    'Commercio_San_Daniele': ([('Comune Codice', 'c')], 3),
    'Centri_commerciali_2025': ([('Comune Codice', 'c')], 3),
    'Commercio_ambulante_2025': ([('Comune Codice', 'c')], 3),
    'Redditi_IRPEF_2018': ([('Codice Istat Comune', 'c')], 3),
    'Occupati_2007_2018': ('t', 3),
    'Disoccupati_2007_2018': ('t', 3),
    'Export_2014_2018': ('t', 3),
    'Import_2014_2018': ('t', 3),
    'Autovetture_2020': ([('Comune', 'n')], 3),
    'Veicoli_2017': ([('COMUNE', 'n')], 3),
    'Radon_scuole_ARPA': ([('COMUNE', 'n')], 1),
    'Parchi_e_giardini': ([('COMUNE', 'n')], 4),
    'Rifugi_alpini': ([('COMUNE', 'n')], 2),
    # gruppo 4: rifiuti, meteo, mobilità
    'Rifiuti_comunali': ([('CODICE ISTAT', 'c'), ('COMUNE', 'n')], 4),
    'Indicatori_rifiuti': ([('CODICE ISTAT', 'c'), ('COMUNE', 'n')], 4),
    'Impianti_rifiuti_2020': ([('Comune', 'n')], 4),
    'Stazioni_idrometeo_2019': ([('Comune', 'n')], 4),
    'Sensori_meteo_2019': ('t', 4),
    'Ciclovie_2020': ('t', 4),
    'Piste_ciclabili': ('t', 4),
    'Rete_viaria': ('t', 4),
}
GRUPPO_ANAGRAFE = 1
# correzioni già applicate nell'archivio e da riapplicare a ogni aggiornamento
# Rifiuti_comunali: la fonte scrive l'anno come 2.013 (separatore delle migliaia letto come decimale)
CORREZIONI = {('Rifiuti_comunali', 'ANNO'): lambda v: int(round(v * 1000)) if isinstance(v, (int, float)) and 1.9 < v < 2.2 else v}
# i testi più lunghi di una cella di Excel sono conservati nel foglio Testi_estesi e richiamati con questo rimando
RIMANDO = 'TESTO ESTESO CONSERVATO INTEGRALMENTE nel foglio Testi_estesi'
# nomi storici o abbreviati che indicano un comune attuale (fusioni e abbreviazioni evidenti)
ALIAS = {'TERZODIAQUILEIA': "Terzo d'Aquileia", 'FIUMICELLO': 'Fiumicello Villa Vicentina', 'VILLAVICENTINA': 'Fiumicello Villa Vicentina',
         'VALVASONE': 'Valvasone Arzene', 'ARZENE': 'Valvasone Arzene', 'REANADELROIALE': 'Reana del Rojale', 'CAMPOLONGOALTORRE': 'Campolongo Tapogliano',
         'TAPOGLIANO': 'Campolongo Tapogliano', 'TREPPOCARNICO': 'Treppo Ligosullo', 'LIGOSULLO': 'Treppo Ligosullo', 'RIVIGNANO': 'Rivignano Teor',
         'TEOR': 'Rivignano Teor', 'SPILMBERGO': 'Spilimbergo', 'COLLOREDODIMTEALBANO': 'Colloredo di Monte Albano', 'COLLOREDODIMA': 'Colloredo di Monte Albano',
         'BUIA': 'Buja', 'FIUMICELLOVILLAV': 'Fiumicello Villa Vicentina', 'SGIORGIORICHINVELDA': 'San Giorgio della Richinvelda',
         'SMARTINOTAGLIAMENTO': 'San Martino al Tagliamento', 'SGIORGIODINOGARO': 'San Giorgio di Nogaro', 'SPIETROALNATISONE': 'San Pietro al Natisone',
         'MALBORGHETTO': 'Malborghetto Valbruna', 'FORGARIA': 'Forgaria nel Friuli', 'GEMONA': 'Gemona del Friuli', 'LIGNANO': 'Lignano Sabbiadoro',
         'PALAZZOLODELSTELLA': 'Palazzolo dello Stella', 'CASARSADDELIZIA': 'Casarsa della Delizia', 'CASTELNOVO': 'Castelnovo del Friuli',
         'PRATA': 'Prata di Pordenone', 'ERTOCASSO': 'Erto e Casso', 'FORGARIADELFRIULI': 'Forgaria nel Friuli', 'PASSONS': 'Pasian di Prato',
         'PASSONSDIPASIANDIPRATO': 'Pasian di Prato'}
# trasformazione dalle coordinate UTM fuso 33 al disegno della mappa (verificata: 414 farmacie su 417 cadono nel proprio comune)
FX = [0.9981337794975602, -0.07416881054833876, 87284.31391544109]
FY = [-0.0731952954966455, -0.9967836423904924, 5175818.401653809]
STRATI = {'farmacie': 'Farmacie', 'guardie': 'Guardie_mediche', 'rsa': 'Residenze_anziani', 'wifi': 'Punti_WiFi'}


def norm(s):
    return re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper())


def normsp(s):
    return ' ' + re.sub(r'[^A-Z]+', ' ', unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()).strip() + ' '


def leggi_dati(p):
    return json.loads(gzip.decompress(base64.b64decode((RADICE / p).read_text().strip())))


def scrivi_dati(p, o):
    (RADICE / p).write_text(base64.b64encode(gzip.compress(json.dumps(o, ensure_ascii=False, separators=(',', ':')).encode(), 9)).decode())


def riga_js(html, nome):
    m = re.search(r'^const ' + nome + r' = (.*);$', html, re.M)
    if not m:
        raise SystemExit(f'Nella pagina manca la riga «const {nome}»')
    return m, json.loads(m.group(1).replace('<\\/', '</'))


def sostituisci_js(html, m, valore):
    testo = json.dumps(valore, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return html[:m.start(1)] + testo + html[m.end(1):]


def numero(v):
    v = v.strip()
    if v == '':
        return None
    if re.fullmatch(r'-?(0|[1-9]\d*)', v):
        return int(v)
    if re.fullmatch(r'-?(0|[1-9]\d*)\.\d+', v):
        return float(v)
    return v


def utm(lat, lon, zona=33):
    a = 6378137.0; f = 1 / 298.257223563; k0 = 0.9996; e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    lon0 = math.radians((zona - 1) * 6 - 180 + 3); la = math.radians(lat); lo = math.radians(lon)
    N = a / math.sqrt(1 - e2 * math.sin(la) ** 2); T = math.tan(la) ** 2; C = ep2 * math.cos(la) ** 2; A = math.cos(la) * (lo - lon0)
    M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * la - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * la)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * la) - (35 * e2 ** 3 / 3072) * math.sin(6 * la))
    x = k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120) + 500000
    y = k0 * (M + N * math.tan(la) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24 + (61 - 58 * T + T * T + 600 * C - 330 * ep2) * A ** 6 / 720))
    return x, y


def punto(lat, lon):
    try:
        lat, lon = float(str(lat).replace(',', '.')), float(str(lon).replace(',', '.'))
    except (TypeError, ValueError):
        return None
    if not (45.4 < lat < 46.8 and 12.1 < lon < 14.1):
        return None
    E, N = utm(lat, lon)
    return round(FX[0] * E + FX[1] * N + FX[2]), round(FY[0] * E + FY[1] * N + FY[2])


def scarica(url):
    errore = None
    for tentativo in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/)'})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read().decode('utf-8-sig')
        except Exception as e:  # rete instabile: riprova
            errore = e
            time.sleep(5 * (tentativo + 1))
    raise errore


def spazi(c):
    """Nome di colonna confrontabile: la fonte a volte aggiunge o toglie spazi."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', c)).strip()


def gruppo_della_settimana(giorno=None):
    # settimane contate da lunedì 5 gennaio 2026: la rotazione resta regolare anche negli anni di 53 settimane
    return ((giorno or datetime.date.today()) - datetime.date(2026, 1, 5)).days // 7 % 4 + 1


def geometria(col, v):
    return col == 'the_geom' or (isinstance(v, str) and re.match(r'^(MULTI)?(LINESTRING|POLYGON)', v) is not None)


def conta_testo(cols, rows, nomi):
    """Come il filtro della pagina per i fogli senza colonna del comune: righe che nominano il comune nel testo."""
    testi = [' \u0001 '.join('' if v is None or geometria(c, v) else str(v) for c, v in zip(cols, r)).lower() for r in rows]
    out = {}
    for i, n in enumerate(nomi):
        q = n.lower()
        k = sum(1 for t in testi if q in t)
        if k:
            out[str(i)] = k
    return out


def main():
    argomenti = sys.argv[1:]
    if '--quale-gruppo' in argomenti:
        print(gruppo_della_settimana())
        return 0
    prova = '--prova' in argomenti
    solo = set(argomenti[argomenti.index('--foglio') + 1].split(',')) if '--foglio' in argomenti else set()
    if solo:
        gruppi = set()  # un foglio per volta (anche più, separati da virgola): nessun gruppo intero e niente anagrafe
    elif '--tutti' in argomenti:
        gruppi = {1, 2, 3, 4}
    elif '--gruppo' in argomenti:
        gruppi = {int(argomenti[argomenti.index('--gruppo') + 1])}
    else:
        gruppi = {gruppo_della_settimana()}
    if solo:
        print(f"Fogli da aggiornare: {', '.join(sorted(solo))}{' (prova: nulla viene scritto)' if prova else ''}")
    else:
        print(f"{'Gruppi' if len(gruppi) > 1 else 'Gruppo'} da aggiornare: {', '.join(map(str, sorted(gruppi)))}{' (prova: nulla viene scritto)' if prova else ''}")

    html = PAGINA.read_text(encoding='utf-8')
    m_db, DB = riga_js(html, 'DB')
    m_man, MAN = riga_js(html, 'MAN')
    m_ser, SERIE = riga_js(html, 'SERIE')
    comuni = DB['c']
    perno = {}
    for i, c in enumerate(comuni):
        perno[norm(c['n'])] = i
        for alt in str(c['ml']).split('/'):
            perno.setdefault(norm(alt), i)
    for k, v in ALIAS.items():
        perno.setdefault(k, perno[norm(v)])
    percodice = {int(c['id']): i for i, c in enumerate(comuni)}
    suffissi = sorted(((normsp(c['n']).strip(), i) for i, c in enumerate(comuni)), key=lambda x: -len(x[0]))
    # i fogli seguono l'ordine dei comuni nell'indice (MAN.istat), che può differire da quello di DB.c
    nomi_man = [next(c['n'] for c in comuni if c['id'] == i) for i in MAN['istat']]

    def per_nome(v):
        if v in (None, ''):
            return None
        k = norm(v)
        if k in perno:
            return perno[k]
        k = perno.get(norm(str(v).split('/')[0].split(' - ')[0].split('(')[0]))
        if k is None:
            k = perno.get(norm(str(v).split('-')[0]))
        n = norm(v)
        if k is None and n.startswith('S'):
            # «S. Martino al Tagliamento», «S. Giorgio...»: abbreviazione di San, Santa, Santo
            k = next((perno[p + n[1:]] for p in ('SAN', 'SANTA', 'SANTO', 'SANT') if p + n[1:] in perno), None)
        if k is None and len(n) >= 10:
            # nomi troncati dalla fonte («FIUMICELLO VILLA VICENTIN»): vale solo se l'inizio indica un comune solo
            cand = {i for nome, i in perno.items() if nome.startswith(n)}
            k = cand.pop() if len(cand) == 1 else None
        return k

    def per_codice(v):
        try:
            return percodice.get(int(str(v).strip()))
        except ValueError:
            return None

    def per_indirizzo(v):
        if v in (None, ''):
            return None
        if ',' in str(v):
            k = per_nome(str(v).split(',')[-1])
            if k is not None:
                return k
        s = normsp(v).rstrip()
        for nome, i in suffissi:
            if s.endswith(' ' + nome) or s.strip() == nome:
                return i
        # nomi storici dei comuni fusi in fondo all'indirizzo («... FIUMICELLO»)
        parole = s.split()
        for n in (1, 2, 3):
            fine = norm(''.join(parole[-n:])) if len(parole) >= n else ''
            if fine in ALIAS:
                return perno.get(fine)
        return None

    metodi = {'c': per_codice, 'n': per_nome, 's': per_indirizzo}
    oggi = datetime.date.today().isoformat()
    indice = {f['id']: f for f in MAN['manifest']}
    cambiati, problemi, uguali = [], [], []

    def leggi_foglio(f):
        parti = [leggi_dati(x) for x in f['files']]
        righe = [r for p in parti for r in p['rows']]
        chiavi = [k for p in parti for k in p['k']] if parti and 'k' in parti[0] else None
        return righe, chiavi

    def scrivi_foglio(foglio, f, nuove, chiavi, vecchie, vecchie_k):
        """Confronta con il foglio pubblicato e, se è cambiato, lo riscrive (diviso nello stesso numero di file)."""
        if nuove == vecchie and chiavi == vecchie_k:
            uguali.append(foglio)
            return
        if prova:
            diverse = sum(1 for a, b in zip(nuove, vecchie) if a != b) + abs(len(nuove) - len(vecchie))
            kd = sum(1 for a, b in zip(chiavi or [], vecchie_k or []) if a != b)
            cambiati.append(f'{foglio}: {len(nuove)} righe (prima {len(vecchie)}), {diverse} righe diverse, {kd} collegamenti ai comuni diversi')
            return
        n = len(f['files'])
        passo = math.ceil(len(nuove) / n) if nuove else 0
        for j, nome in enumerate(f['files']):
            o = {'rows': nuove[j * passo:(j + 1) * passo]}
            if chiavi is not None:
                o['k'] = chiavi[j * passo:(j + 1) * passo]
            scrivi_dati(nome, o)
        f['righe'] = len(nuove)
        f['cons'] = oggi
        if chiavi is not None:
            conteggio = {}
            for k in chiavi:
                for kk in (k if isinstance(k, list) else [k]):
                    if kk >= 0:
                        conteggio[str(kk)] = conteggio.get(str(kk), 0) + 1
        else:
            conteggio = conta_testo(f['cols'], nuove, nomi_man)
        MAN['conteggi'][foglio] = conteggio
        cambiati.append(f'{foglio}: {len(nuove)} righe (prima {len(vecchie)})')

    # 1. fogli del portale dei dati aperti
    for foglio, (mappa, gruppo) in FOGLI.items():
        if (foglio not in solo) if solo else (gruppo not in gruppi):
            continue
        f = indice.get(foglio)
        ident = re.search(r'/api/views/([a-z0-9]{4}-[a-z0-9]{4})/', (f or {}).get('fonte') or '')
        if not f or not ident:
            problemi.append(f'{foglio}: non è nell\'indice della pagina o non ha l\'indirizzo del portale')
            continue
        try:
            testo = scarica(PORTALE.format(ident.group(1)))
        except Exception as e:
            problemi.append(f'{foglio}: scaricamento non riuscito ({e})')
            continue
        righe = list(csv.reader(io.StringIO(testo)))
        if len(righe) < 2:
            problemi.append(f'{foglio}: il file scaricato è vuoto')
            continue
        intest = [spazi(h) for h in righe[0]]
        mancano = [c for c in f['cols'] if spazi(c) not in intest]
        if mancano:
            problemi.append(f'{foglio}: nella fonte mancano le colonne {", ".join(mancano)}, foglio lasciato com\'è')
            continue
        # solo le colonne già pubblicate: quelle nuove della fonte (per esempio contatti dei privati) restano fuori
        tieni = [intest.index(spazi(c)) for c in f['cols']]
        vecchie, vecchie_k = leggi_foglio(f)
        # ogni colonna mantiene il tipo che ha già nell'archivio (testo o numero)
        testo_col, dieci = [False] * len(tieni), [False] * len(tieni)
        for j in range(len(tieni)):
            valori = [r[j] for r in vecchie if j < len(r) and r[j] is not None]
            testo_col[j] = bool(valori) and all(isinstance(v, str) for v in valori)
            # alcuni fogli dell'archivio hanno i decimali arrotondati a dieci cifre: si mantiene la stessa forma
            decimali = [len(repr(v).split('.')[1]) for v in valori if isinstance(v, float) and 'e' not in repr(v)]
            dieci[j] = bool(decimali) and max(decimali) <= 10
        nuove, chiavi = [], []
        for r in righe[1:]:
            if not any(x.strip() for x in r):
                continue
            r = (r + [''] * len(intest))[:len(intest)]
            riga = [(r[j] if r[j].strip() != '' else None) if testo_col[n] else numero(r[j]) for n, j in enumerate(tieni)]
            for n, c in enumerate(f['cols']):
                if dieci[n] and isinstance(riga[n], float):
                    riga[n] = round(riga[n], 10)
                if (foglio, c) in CORREZIONI:
                    riga[n] = CORREZIONI[(foglio, c)](riga[n])
                if isinstance(riga[n], str) and len(riga[n]) > 32767:
                    vecchio = vecchie[len(nuove)][n] if len(nuove) < len(vecchie) else None
                    if isinstance(vecchio, str) and vecchio.startswith(RIMANDO):
                        riga[n] = vecchio
            if mappa == 'm':
                idx = [j for j, c in enumerate(intest) if c == 'comune/id' or (c.startswith('comunicompresi/') and c.endswith('/id'))]
                ks = sorted({k for k in (per_codice(r[j]) for j in idx if r[j].strip()) if k is not None})
                if not ks:
                    k0 = per_nome(r[intest.index('comune/comune')])
                    ks = [k0] if k0 is not None else []
                chiave = ks if len(ks) > 1 else (ks[0] if ks else -1)
            elif mappa == 't':
                chiave = None
            else:
                chiave = None
                for col, met in mappa:
                    v = r[intest.index(spazi(col))]
                    if v.strip():
                        chiave = metodi[met](v)
                    if chiave is not None:
                        break
                chiave = -1 if chiave is None else chiave
            nuove.append(riga)
            chiavi.append(chiave)
        if mappa == 't':
            chiavi = None
        if len(nuove) < 0.5 * f['righe']:
            problemi.append(f'{foglio}: {len(nuove)} righe contro {f["righe"]} attese, foglio lasciato com\'è')
            continue
        scrivi_foglio(foglio, f, nuove, chiavi, vecchie, vecchie_k)

    # 2. anagrafe regionale degli amministratori locali: tre fogli e i dati del registro
    anagrafe = False
    if GRUPPO_ANAGRAFE in gruppi:
        try:
            enti = json.loads(scarica(ANAGRAFE + 'enti_locali.json'))
            elez = json.loads(scarica(ANAGRAFE + 'elezioni.json'))
            amm = json.loads(scarica(ANAGRAFE + 'amministratori_locali.json'))
        except Exception as e:
            enti = None
            problemi.append(f'Anagrafe degli amministratori: scaricamento non riuscito ({e})')
        if enti is not None:
            fe, fl, fa = indice['Enti_locali_anagrafe'], indice['Elezioni_anagrafe'], indice['Amministratori_locali']
            vuoto = lambda v: None if v in (None, '') else v
            r_enti = [[vuoto(e.get(c)) for c in fe['cols']] for e in enti]
            k_enti = [per_nome(e.get('nome_struttura')) for e in enti]
            k_enti = [-1 if k is None else k for k in k_enti]
            per_struttura = {e.get('id_struttura'): k for e, k in zip(enti, k_enti)}
            r_elez = [[vuoto(e.get(c)) for c in fl['cols']] for e in elez]
            k_elez = [per_struttura.get(e.get('id_struttura'), -1) for e in elez]
            agg = {k: e.get('dati_aggiornati_al') for e, k in zip(enti, k_enti) if k >= 0}
            fonte = ANAGRAFE + 'amministratori_locali.json'
            k_amm = [per_nome(a.get('nome_struttura')) for a in amm]
            k_amm = [-1 if k is None else k for k in k_amm]
            # i dati di nascita della fonte non entrano mai nell'archivio
            r_amm = [[a.get('nome_struttura'), a.get('cognome'), a.get('nome'), a.get('carica'), 'Sì' if a.get('giunta_comunale') else 'No',
                      vuoto(a.get('lista')), vuoto(a.get('data_elezione')), vuoto(a.get('data_inizio_carica')), a.get('id_elezione'),
                      vuoto(a.get('titolo_di_studio')), vuoto(a.get('professione')), agg.get(k), fonte] for a, k in zip(amm, k_amm)]
            if len(enti) < 200 or len(amm) < 0.7 * fa['righe'] or fa['cols'][:4] != ['Comune', 'Cognome', 'Nome', 'Carica']:
                problemi.append(f'Anagrafe degli amministratori: {len(enti)} enti e {len(amm)} incarichi, dati sospetti, fogli lasciati come sono')
            else:
                for foglio, f, rr, kk in (('Enti_locali_anagrafe', fe, r_enti, k_enti), ('Elezioni_anagrafe', fl, r_elez, k_elez), ('Amministratori_locali', fa, r_amm, k_amm)):
                    vecchie, vecchie_k = leggi_foglio(f)
                    scrivi_foglio(foglio, f, rr, kk, vecchie, vecchie_k)
                # registro: sindaco, data di aggiornamento, prossime elezioni, numero di incarichi, incarichi per tipo
                nuovo = {i: {'sin': None, 'agg': None, 'el': None, 'inc': 0} for i in range(len(comuni))}
                for e, k in zip(enti, k_enti):
                    if k >= 0:
                        nuovo[k]['agg'] = e.get('dati_aggiornati_al'); nuovo[k]['el'] = e.get('prossime_elezioni')
                cariche = {}
                for a, k in zip(amm, k_amm):
                    cariche[a.get('carica')] = cariche.get(a.get('carica'), 0) + 1
                    if k >= 0:
                        nuovo[k]['inc'] += 1
                        if a.get('carica') == 'sindaco':
                            nuovo[k]['sin'] = f"{a.get('cognome')} {a.get('nome')}"
                vecchio_reg = [{c: x.get(c) for c in ('sin', 'agg', 'el', 'inc')} for x in comuni]
                if [nuovo[i] for i in range(len(comuni))] != vecchio_reg or cariche != DB['meta'].get('cariche'):
                    diversi = sum(1 for i in range(len(comuni)) if nuovo[i] != vecchio_reg[i])
                    if prova:
                        cambiati.append(f'Registro degli amministratori: {diversi} comuni con sindaco, data, elezioni o incarichi diversi')
                    else:
                        for i, c in enumerate(comuni):
                            c.update(nuovo[i])
                        DB['meta']['cariche'] = cariche
                        anagrafe = True
                        cambiati.append(f'Registro degli amministratori: {diversi} comuni aggiornati')

    if prova:
        print(f'Uguali alla fonte: {len(uguali)} fogli.')
        for c in cambiati:
            print('DIVERSO', c)
        for p in problemi:
            print('ATTENZIONE', p)
        return 0
    if not cambiati:
        print(f'Nessun foglio cambiato ({len(uguali)} controllati, uguali alla fonte).')
        for p in problemi:
            print('ATTENZIONE', p)
        return 0

    # 3. totali per comune usati da registro, indicatori, grafici e scheda
    def righe_di(foglio):
        f = indice[foglio]
        rr, kk = leggi_foglio(f)
        return f['cols'], rr, kk
    toccati = {c.split(':')[0] for c in cambiati}
    if toccati & {'Farmacie', 'Residenze_anziani', 'Siti_inquinati_2025'}:
        for c in comuni:
            for campo in ('fa', 'rsa', 'rpl', 'si', 'sia'):
                c[campo] = 0
        cols, rows, ks = righe_di('Farmacie')
        for k in ks:
            if k >= 0:
                comuni[k]['fa'] += 1
        cols, rows, ks = righe_di('Residenze_anziani')
        for r, k in zip(rows, ks):
            if k >= 0:
                comuni[k]['rsa'] += 1
                comuni[k]['rpl'] += int(r[cols.index('pl_tot')] or 0)
        cols, rows, ks = righe_di('Siti_inquinati_2025')
        for r, k in zip(rows, ks):
            if k >= 0:
                comuni[k]['si'] += 1
                if r[cols.index('STATO_PRATICA_DIZ')] != 'Archiviata':
                    comuni[k]['sia'] += 1
        DB['meta']['siti'] = {}
        for r in rows:
            s = r[cols.index('STATO_PRATICA_DIZ')]
            DB['meta']['siti'][s] = DB['meta']['siti'].get(s, 0) + 1
    if 'Turismo_comunale' in toccati:
        # arrivi e presenze del 2025, presenze straniere, presenze per provincia e serie per anno della scheda
        cols, rows, ks = righe_di('Turismo_comunale')
        ia, ip, im, ian = cols.index('ARRIVI'), cols.index('PRESENZE'), cols.index('ITALIANI_STRANIERI'), cols.index('ANNO')
        for c in comuni:
            c['ar'] = c['pr'] = c['prs'] = 0
        tprov, serie = {}, {}
        for r, k in zip(rows, ks):
            if k < 0:
                continue
            anno = str(r[ian])
            if anno == '2025':
                comuni[k]['ar'] += r[ia] or 0; comuni[k]['pr'] += r[ip] or 0
                if r[im] == 'Stranieri':
                    comuni[k]['prs'] += r[ip] or 0
            pv = comuni[k]['pv']
            tprov.setdefault(anno, {}); tprov[anno][pv] = tprov[anno].get(pv, 0) + (r[ip] or 0)
            serie.setdefault(str(k), {}); serie[str(k)][anno] = serie[str(k)].get(anno, 0) + (r[ip] or 0)
        DB['meta']['tprov'] = {a: tprov.get(a, v) for a, v in DB['meta']['tprov'].items()}
        SERIE['tur'] = {k: serie.get(k, {}) for k in SERIE['tur']}

    # 4. punti della mappa dei servizi
    punti_file = RADICE / 'dati' / '_punti_0.txt'
    if punti_file.exists() and toccati & set(STRATI.values()):
        P = leggi_dati('dati/_punti_0.txt')
        for L in P['layers']:
            foglio = STRATI.get(L['id'])
            if not foglio:
                continue
            cols, rows, ks = righe_di(foglio)
            pts = []
            for r, k in zip(rows, ks):
                g = lambda n: r[cols.index(n)]
                if L['id'] == 'wifi':
                    mm = re.match(r'POINT \(([-\d.]+) ([-\d.]+)\)', str(g('Coordinate punto') or ''))
                    q = punto(mm.group(2), mm.group(1)) if mm else None
                    nome, extra = g('Indirizzo'), ''
                elif L['id'] == 'farmacie':
                    q = punto(g('latitudine'), g('longitudine'))
                    nome, extra = g('insegna'), ', '.join(str(x) for x in (g('indirizzo'), g('telefono')) if x)
                elif L['id'] == 'guardie':
                    q = punto(g('latitudine'), g('longitudine'))
                    nome, extra = 'Guardia medica · ' + str(g('presso') or g('via')), f"Feriali {g('feriale')}; numero {g('telefono')}"
                else:
                    q = punto(g('lat'), g('longit'))
                    nome, extra = g('denominazione'), f"{g('tipologia')} · {g('pl_tot')} posti letto"
                if q:
                    kk = k[0] if isinstance(k, list) else k
                    pts.append([q[0], q[1], str(nome or ''), kk, str(extra or '')])
            L['pts'] = pts
        scrivi_dati('dati/_punti_0.txt', P)

    html = sostituisci_js(html, m_db, DB)
    for nome, valore in (('MAN', MAN), ('SERIE', SERIE)):
        m, _ = riga_js(html, nome)
        html = sostituisci_js(html, m, valore)
    PAGINA.write_text(html, encoding='utf-8')
    print('Fogli aggiornati:')
    for c in cambiati:
        print(' ', c)
    print(f'Uguali alla fonte: {len(uguali)} fogli.')
    for p in problemi:
        print('ATTENZIONE', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
