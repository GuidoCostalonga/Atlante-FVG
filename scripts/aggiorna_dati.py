#!/usr/bin/env python3
"""Aggiorna l'Atlante con i dati aperti della Regione FVG che cambiano spesso.

Per ogni foglio dell'elenco FOGLI scarica il CSV dal portale dati.friuliveneziagiulia.it,
collega ogni riga al suo comune, toglie i dati di contatto dei privati, riscrive il file
in dati/ e aggiorna dentro index.html l'indice dei fogli (righe, data, conteggi per comune)
e i totali per comune usati da registro e scheda. Ricalcola anche i punti della mappa dei
servizi per farmacie, guardie mediche, residenze per anziani e punti di accesso a internet.

Usa solo la libreria standard di Python. Se un foglio non si scarica o cambia struttura,
lo lascia com'è e lo segnala: non scrive mai dati incompleti.
"""
import base64, csv, datetime, gzip, io, json, math, re, sys, time, unicodedata, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINA = RADICE / 'index.html'
PORTALE = 'https://www.dati.friuliveneziagiulia.it/api/views/{}/rows.csv?accessType=DOWNLOAD'

# foglio: (identificativo sul portale, colonne del comune [(colonna, metodo)], colonne da togliere)
# metodo: c = codice ISTAT, n = nome del comune, s = nome alla fine dell'indirizzo, m = sede e comuni serviti
FOGLI = {
    'Farmacie': ('jbxd-m6xe', [('idComune', 'c'), ('comune', 'n')], []),
    'Guardie_mediche': ('my2j-r3t4', 'm', []),
    'Residenze_anziani': ('vw6s-ayge', [('citta', 'n')], []),
    'Punti_WiFi': ('53ur-f9mj', [('Indirizzo', 's')], []),
    'Turismo_comunale': ('7eps-cpgr', [('COMUNE_CODICE', 'c'), ('COMUNE', 'n')], []),
    'Siti_inquinati_2025': ('ti84-itu7', [('DENCOMUNE', 'n')], []),
    'Elezioni_comunali_2026': ('ivm2-pa4q', [('Codice Istat Comune', 'c'), ('Nome Comune', 'n')], []),
    'Demanio_culturale': ('8vuc-s3dm', [('Comune', 'n')], []),
    'Patrimonio_disponibile': ('2b6s-pcam', [('Comune', 'n')], []),
    'Patrimonio_indisponibile': ('26im-zbgz', [('Comune', 'n')], []),
    'Affittacamere': ('6var-2hht', [('COMUNE', 'n')], ['EMAIL', 'SITO']),
    'Bed_and_Breakfast': ('jzsu-f86x', [('COMUNE', 'n')], ['EMAIL', 'SITO']),
    'Marina_Resort': ('6xk5-2p3e', [('COMUNE', 'n')], ['EMAIL', 'SITO']),
    'Campeggi': ('c2n8-qhph', [('COMUNE', 'n')], ['EMAIL', 'SITO']),
    'Alloggi_agrituristici': ('yg8e-47jy', [('COMUNE', 'n')], ['EMAIL', 'SITO']),
    'Ricettivita_sociale': ('csiv-njht', [('COMUNE', 'n')], ['EMAIL', 'SITO']),
    'Alberghi_diffusi': ('69j3-9hcp', [('comune', 'n')], ['email', 'sito']),
    'Alberghi_RTA': ('fiiw-i5su', [('comune', 'n')], ['email', 'sito']),
}
# nomi storici o abbreviati che indicano un comune attuale (fusioni e abbreviazioni evidenti)
ALIAS = {'TERZODIAQUILEIA': "Terzo d'Aquileia", 'FIUMICELLO': 'Fiumicello Villa Vicentina', 'VILLAVICENTINA': 'Fiumicello Villa Vicentina',
         'VALVASONE': 'Valvasone Arzene', 'ARZENE': 'Valvasone Arzene', 'REANADELROIALE': 'Reana del Rojale', 'CAMPOLONGOALTORRE': 'Campolongo Tapogliano',
         'TAPOGLIANO': 'Campolongo Tapogliano', 'TREPPOCARNICO': 'Treppo Ligosullo', 'LIGOSULLO': 'Treppo Ligosullo', 'RIVIGNANO': 'Rivignano Teor',
         'TEOR': 'Rivignano Teor', 'SPILMBERGO': 'Spilimbergo', 'COLLOREDODIMTEALBANO': 'Colloredo di Monte Albano', 'COLLOREDODIMA': 'Colloredo di Monte Albano',
         'BUIA': 'Buja', 'FIUMICELLOVILLAV': 'Fiumicello Villa Vicentina', 'SGIORGIORICHINVELDA': 'San Giorgio della Richinvelda',
         'SMARTINOTAGLIAMENTO': 'San Martino al Tagliamento', 'SGIORGIODINOGARO': 'San Giorgio di Nogaro', 'SPIETROALNATISONE': 'San Pietro al Natisone',
         'MALBORGHETTO': 'Malborghetto Valbruna', 'FORGARIA': 'Forgaria nel Friuli', 'GEMONA': 'Gemona del Friuli', 'LIGNANO': 'Lignano Sabbiadoro',
         'PALAZZOLODELSTELLA': 'Palazzolo dello Stella', 'CASARSADDELIZIA': 'Casarsa della Delizia', 'CASTELNOVO': 'Castelnovo del Friuli'}
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


def scarica(ident):
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(PORTALE.format(ident), timeout=120) as r:
                return r.read().decode('utf-8-sig')
        except Exception as e:  # rete instabile: riprova
            errore = e
            time.sleep(5 * (tentativo + 1))
    raise errore


def main():
    html = PAGINA.read_text(encoding='utf-8')
    m_db, DB = riga_js(html, 'DB')
    m_man, MAN = riga_js(html, 'MAN')
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

    def per_nome(v):
        if v in (None, ''):
            return None
        k = norm(v)
        if k in perno:
            return perno[k]
        k = perno.get(norm(str(v).split('/')[0].split(' - ')[0].split('(')[0]))
        return k if k is not None else perno.get(norm(str(v).split('-')[0]))

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
        return None

    metodi = {'c': per_codice, 'n': per_nome, 's': per_indirizzo}
    oggi = datetime.date.today().isoformat()
    indice = {f['id']: f for f in MAN['manifest']}
    cambiati, problemi = [], []
    for foglio, (ident, mappa, togli) in FOGLI.items():
        f = indice.get(foglio)
        if not f:
            problemi.append(f'{foglio}: non è nell\'indice della pagina')
            continue
        try:
            testo = scarica(ident)
        except Exception as e:
            problemi.append(f'{foglio}: scaricamento non riuscito ({e})')
            continue
        righe = list(csv.reader(io.StringIO(testo)))
        if len(righe) < 2:
            problemi.append(f'{foglio}: il file scaricato è vuoto')
            continue
        intest = [unicodedata.normalize('NFC', h) for h in righe[0]]
        if sorted(c for c in intest if c not in togli) != sorted(f['cols']):
            problemi.append(f'{foglio}: le colonne sono cambiate, foglio lasciato com\'è')
            continue
        tieni = [intest.index(c) for c in f['cols']]
        vecchio = leggi_dati(f['files'][0]) if len(f['files']) == 1 else None
        # ogni colonna mantiene il tipo che ha già nell'archivio (testo o numero)
        testo_col = [False] * len(tieni)
        if vecchio:
            for j in range(len(tieni)):
                valori = [r[j] for r in vecchio['rows'][:500] if j < len(r) and r[j] is not None]
                testo_col[j] = bool(valori) and all(isinstance(v, str) for v in valori)
        nuove, chiavi = [], []
        for r in righe[1:]:
            if not any(x.strip() for x in r):
                continue
            r = (r + [''] * len(intest))[:len(intest)]
            riga = [(r[j] if r[j].strip() != '' else None) if testo_col[n] else numero(r[j]) for n, j in enumerate(tieni)]
            if mappa == 'm':
                idx = [j for j, c in enumerate(intest) if c == 'comune/id' or (c.startswith('comunicompresi/') and c.endswith('/id'))]
                ks = sorted({k for k in (per_codice(r[j]) for j in idx if r[j].strip()) if k is not None})
                if not ks:
                    k0 = per_nome(r[intest.index('comune/comune')])
                    ks = [k0] if k0 is not None else []
                chiave = ks if len(ks) > 1 else (ks[0] if ks else -1)
            else:
                chiave = None
                for col, met in mappa:
                    v = r[intest.index(col)]
                    if v.strip():
                        chiave = metodi[met](v)
                    if chiave is not None:
                        break
                chiave = -1 if chiave is None else chiave
            nuove.append(riga)
            chiavi.append(chiave)
        if len(nuove) < 0.5 * f['righe']:
            problemi.append(f'{foglio}: {len(nuove)} righe contro {f["righe"]} attese, foglio lasciato com\'è')
            continue
        nuovo = {'rows': nuove, 'k': chiavi}
        if vecchio == nuovo:
            continue
        scrivi_dati(f['files'][0], nuovo)
        f['righe'] = len(nuove)
        f['cons'] = oggi
        conteggio = {}
        for k in chiavi:
            for kk in (k if isinstance(k, list) else [k]):
                if kk >= 0:
                    conteggio[str(kk)] = conteggio.get(str(kk), 0) + 1
        MAN['conteggi'][foglio] = conteggio
        cambiati.append(f'{foglio}: {len(nuove)} righe')

    if not cambiati:
        print('Nessun foglio cambiato.')
        for p in problemi:
            print('ATTENZIONE', p)
        return 0

    # totali per comune usati da registro, indicatori e scheda
    def righe_di(foglio):
        f = indice[foglio]
        o = leggi_dati(f['files'][0])
        return f['cols'], o['rows'], o['k']
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

    # punti della mappa dei servizi
    punti_file = RADICE / 'dati' / '_punti_0.txt'
    if punti_file.exists():
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
    m_man, _ = riga_js(html, 'MAN')
    html = sostituisci_js(html, m_man, MAN)
    PAGINA.write_text(html, encoding='utf-8')
    print('Fogli aggiornati:')
    for c in cambiati:
        print(' ', c)
    for p in problemi:
        print('ATTENZIONE', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
