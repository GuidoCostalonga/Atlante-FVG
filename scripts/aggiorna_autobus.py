#!/usr/bin/env python3
"""Aggiorna la rete degli autobus TPL FVG mostrata nella sezione «Autobus».

Scarica da BusOne il GTFS (formato aperto per gli orari del trasporto pubblico) di TPL FVG,
proietta fermate e percorsi sul disegno della mappa, assegna ogni fermata al suo comune con
i confini di dati/_mappe_0.txt e riscrive dati/_tpl_0.txt. Arrivi e mezzi in viaggio non
passano di qui: la pagina li legge al momento dal flusso in tempo reale.

Il file viene riscritto solo se cambiano fermate o percorsi, non per la sola data della
versione. Se il download fallisce o il GTFS è incompleto, il file resta com'è.

Usa solo la libreria standard di Python.
Uso: python scripts/aggiorna_autobus.py [cartella con il GTFS già estratto]
"""
import base64, collections, csv, gzip, io, json, math, sys, time, urllib.request, zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / 'dati' / '_tpl_0.txt'
MAPPE = RADICE / 'dati' / '_mappe_0.txt'
GTFS = 'https://proxy.busone.app/TPLFVG/gtfs.zip'
# BusOne chiede di identificarsi: si dichiara la pagina e l'uso senza scopo di lucro
INTESTAZIONI = {'User-Agent': 'AtlanteFVG/1.0 (+https://costalonga.org/Atlante-FVG/)', 'X-BusOne-Client': 'Atlante dei Comuni FVG (https://costalonga.org/Atlante-FVG/)', 'X-BusOne-Use': 'nonprofit'}
# tolleranza in metri nella semplificazione dei tracciati: abbastanza fine da seguire le vie ingrandendo la mappa
TOLLERANZA = 8
FILE_GTFS = ['routes.txt', 'trips.txt', 'stops.txt', 'stop_times.txt', 'shapes.txt', 'feed_info.txt']
# stessa trasformazione di scripts/aggiorna_dati.py: UTM fuso 33 → disegno della mappa
FX = [0.9981337794975602, -0.07416881054833876, 87284.31391544109]
FY = [-0.0731952954966455, -0.9967836423904924, 5175818.401653809]


def utm(lat, lon, zona=33):
    a = 6378137.0; f = 1 / 298.257223563; k0 = 0.9996; e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    lon0 = math.radians((zona - 1) * 6 - 180 + 3); la = math.radians(lat); lo = math.radians(lon)
    N = a / math.sqrt(1 - e2 * math.sin(la) ** 2); T = math.tan(la) ** 2; C = ep2 * math.cos(la) ** 2; A = math.cos(la) * (lo - lon0)
    M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * la - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * la)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * la) - (35 * e2 ** 3 / 3072) * math.sin(6 * la))
    x = k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120) + 500000
    y = k0 * (M + N * math.tan(la) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24 + (61 - 58 * T + T * T + 600 * C - 330 * ep2) * A ** 6 / 720))
    return x, y


def xy(lat, lon):
    E, N = utm(float(lat), float(lon))
    return FX[0] * E + FX[1] * N + FX[2], FY[0] * E + FY[1] * N + FY[2]


def dentro(x, y, anelli):
    c = False
    for r in anelli:
        n = len(r) // 2; j = n - 1
        for i in range(n):
            xi, yi, xj, yj = r[2 * i], r[2 * i + 1], r[2 * j], r[2 * j + 1]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                c = not c
            j = i
    return c


def semplifica(p, eps):
    """Douglas-Peucker: toglie i punti che si scostano dalla linea meno di eps metri."""
    if len(p) < 3:
        return p
    tieni = [False] * len(p); tieni[0] = tieni[-1] = True; pila = [(0, len(p) - 1)]
    while pila:
        a, b = pila.pop(); ax, ay = p[a]; bx, by = p[b]; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy; dm = -1; im = None
        for i in range(a + 1, b):
            # distanza dal segmento, non dalla retta: così restano i tratti di andata e ritorno sulla stessa via
            t = max(0, min(1, ((p[i][0] - ax) * dx + (p[i][1] - ay) * dy) / L2)) if L2 else 0
            d = math.hypot(p[i][0] - ax - t * dx, p[i][1] - ay - t * dy)
            if d > dm:
                dm = d; im = i
        if dm > eps:
            tieni[im] = True; pila += [(a, im), (im, b)]
    return [q for q, k in zip(p, tieni) if k]


def leggi_b64(p):
    return json.loads(gzip.decompress(base64.b64decode(p.read_text())))


def scarica():
    errore = None
    for tentativo in range(3):
        try:
            req = urllib.request.Request(GTFS, headers=INTESTAZIONI)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # rete instabile: riprova
            errore = e
            time.sleep(10 * (tentativo + 1))
    raise errore


def apri_gtfs(origine):
    if origine:
        cartella = Path(origine)
        return lambda nome: io.StringIO((cartella / nome).read_text(encoding='utf-8-sig'))
    z = zipfile.ZipFile(io.BytesIO(scarica()))
    mancano = [n for n in FILE_GTFS if n not in z.namelist()]
    if mancano:
        raise ValueError('GTFS incompleto, mancano ' + ', '.join(mancano))
    return lambda nome: io.StringIO(z.read(nome).decode('utf-8-sig'))


def costruisci(apri):
    geo = leggi_b64(MAPPE)
    confini = []
    for c in geo['comuni']:
        xs = [v for r in c['r'] for v in r[0::2]]; ys = [v for r in c['r'] for v in r[1::2]]
        confini.append((c['c'], c['r'], (min(xs), min(ys), max(xs), max(ys))))

    def comune(x, y):
        for i, r, (a, b, c, d) in confini:
            if a <= x <= c and b <= y <= d and dentro(x, y, r):
                return i
        return -1

    routes = {r['route_id']: r for r in csv.DictReader(apri('routes.txt'))}
    trips = {r['trip_id']: r for r in csv.DictReader(apri('trips.txt'))}
    stops = {r['stop_id']: r for r in csv.DictReader(apri('stops.txt'))}
    seq = collections.defaultdict(list)
    for r in csv.DictReader(apri('stop_times.txt')):
        seq[r['trip_id']].append((int(r['stop_sequence']), r['stop_id']))

    # fermate: [x, y, nome, indice del comune (-1 fuori regione), stop_id, [indici delle linee]]
    SID = list(stops); SIX = {s: i for i, s in enumerate(SID)}
    F = []
    for s in SID:
        x, y = xy(stops[s]['stop_lat'], stops[s]['stop_lon'])
        F.append([round(x), round(y), stops[s]['stop_name'], comune(x, y), s])

    # percorsi: [numero, nome, colore, colore del testo, tipo, [fermate del percorso più frequente], tracciato, corse, route_id]
    RID = sorted(routes, key=lambda r: (routes[r]['route_short_name'], r)); RIX = {r: i for i, r in enumerate(RID)}
    schema = collections.defaultdict(collections.Counter); tracciato = collections.defaultdict(collections.Counter)
    servite = collections.defaultdict(set); corse = collections.Counter()
    for tid, lst in seq.items():
        t = trips.get(tid)
        if not t:
            continue
        st = tuple(s for _, s in sorted(lst)); schema[t['route_id']][st] += 1; corse[t['route_id']] += 1
        tracciato[(t['route_id'], st)][t['shape_id']] += 1
        for s in st:
            servite[s].add(RIX[t['route_id']])
    usati = set(); P = []
    for r in RID:
        ro = routes[r]
        base = [ro['route_short_name'], ro['route_long_name'], ro['route_color'] or '155E9E', ro['route_text_color'] or 'FFFFFF', int(ro['route_type'])]
        if not schema[r]:
            P.append(base + [[], None, 0, r]); continue
        st, _ = schema[r].most_common(1)[0]
        sh = tracciato[(r, st)].most_common(1)[0][0]; usati.add(sh)
        P.append(base + [[SIX[s] for s in st], sh, corse[r], r])

    punti = collections.defaultdict(list)
    for r in csv.DictReader(apri('shapes.txt')):
        if r['shape_id'] in usati:
            punti[r['shape_id']].append((int(r['shape_pt_sequence']), float(r['shape_pt_lat']), float(r['shape_pt_lon'])))
    SH = {}
    for sid, l in punti.items():
        l.sort(); q = semplifica([xy(a, b) for _, a, b in l], TOLLERANZA)
        SH[sid] = [v for x, y in q for v in (round(x), round(y))]
    for p in P:
        p[6] = SH.get(p[6])
    for i, f in enumerate(F):
        f.append(sorted(servite.get(SID[i], ())))

    info = list(csv.DictReader(apri('feed_info.txt')))
    versione = (info[0].get('feed_version') or '') if info else ''
    return {'fermate': F, 'percorsi': P, 'fonte': 'BusOne (https://busone.app) e TPL FVG', 'versione': versione}


def main():
    try:
        nuovo = costruisci(apri_gtfs(sys.argv[1] if len(sys.argv) > 1 else None))
    except Exception as e:
        print(f'Autobus: rete non aggiornata ({e}). Resta la versione precedente.')
        return
    F, P = nuovo['fermate'], nuovo['percorsi']
    # controllo di plausibilità: una rete molto più piccola indica un file guasto, non un taglio di linee
    vecchio = leggi_b64(USCITA) if USCITA.exists() else None
    if len(F) < 1000 or sum(1 for p in P if p[5]) < 100 or (vecchio and len(F) < 0.7 * len(vecchio['fermate'])):
        print(f'Autobus: GTFS sospetto ({len(F)} fermate, {len(P)} percorsi). Resta la versione precedente.')
        return
    if vecchio and vecchio['fermate'] == F and vecchio['percorsi'] == P:
        print(f"Autobus: nessuna novità (versione {nuovo['versione']}).")
        return
    dati = json.dumps(nuovo, ensure_ascii=False, separators=(',', ':')).encode()
    USCITA.write_text(base64.b64encode(gzip.compress(dati, 9, mtime=0)).decode())
    prima = f"{len(vecchio['fermate'])} fermate e {len(vecchio['percorsi'])} percorsi" if vecchio else 'nessun file'
    print(f"Autobus: rete aggiornata alla versione {nuovo['versione']}: {len(F)} fermate e {len(P)} percorsi (prima {prima}).")


if __name__ == '__main__':
    main()
