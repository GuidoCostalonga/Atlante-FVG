#!/usr/bin/env python3
"""Prepara gli orari delle linee TPL FVG per la pagina orari/ dell'Atlante.

Dal GTFS (formato aperto degli orari del trasporto pubblico) di TPL FVG pubblicato da BusOne scrive:
- dati/orari/indice.txt: versione e validità, giorni coperti, calendario dei servizi (un bit per giorno),
  fermate (nome, comune, codice della fermata, latitudine, longitudine, linee che vi passano),
  linee (numero, nome, colori, tipo, file, numero di corse, capolinea, codice del percorso);
- dati/orari/<codice del percorso>.txt: per ogni percorso le sequenze di fermate e le corse
  [sequenza, servizio, partenza in minuti dalla mezzanotte, minuti fra una fermata e la successiva...].

I file sono JSON compressi con gzip e scritti in base64, come gli altri dati dell'Atlante, e vengono
riscritti solo se cambiano. Se il download fallisce o il GTFS è incompleto, gli orari restano quelli di prima.
Usa solo la libreria standard di Python.
Uso: python scripts/aggiorna_orari.py [cartella con il GTFS già estratto]
"""
import base64, collections, csv, datetime, gzip, io, json, re, sys, time, urllib.request, zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CARTELLA = RADICE / 'dati' / 'orari'
MAPPE = RADICE / 'dati' / '_mappe_0.txt'
TPL = RADICE / 'dati' / '_tpl_0.txt'
GTFS = 'https://proxy.busone.app/TPLFVG/gtfs.zip'
INTESTAZIONI = {'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/)', 'X-BusOne-Client': 'Atlante dei Comuni FVG (https://atlantefvg.it/)', 'X-BusOne-Use': 'nonprofit'}
NECESSARI = ['routes.txt', 'trips.txt', 'stops.txt', 'stop_times.txt', 'calendar_dates.txt', 'feed_info.txt']


def leggi_b64(p):
    return json.loads(gzip.decompress(base64.b64decode(p.read_text())))


def scrivi_b64(p, o):
    testo = base64.b64encode(gzip.compress(json.dumps(o, ensure_ascii=False, separators=(',', ':')).encode(), 9, mtime=0)).decode()
    if p.exists() and p.read_text() == testo:
        return False
    p.write_text(testo)
    return True


def apri_gtfs(origine):
    if origine:
        cartella = Path(origine)
        return lambda nome: io.StringIO((cartella / nome).read_text(encoding='utf-8-sig'))
    errore = None
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(GTFS, headers=INTESTAZIONI), timeout=300) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            break
        except Exception as e:  # rete instabile: riprova
            errore = e; time.sleep(10 * (tentativo + 1))
    else:
        raise errore
    mancano = [n for n in NECESSARI if n not in z.namelist()]
    if mancano:
        raise ValueError('GTFS incompleto, mancano ' + ', '.join(mancano))
    return lambda nome: io.StringIO(z.read(nome).decode('utf-8-sig'))


def minuti(t):
    h, m, *_ = t.split(':')
    return int(h) * 60 + int(m)


def costruisci(apri):
    routes = list(csv.DictReader(apri('routes.txt')))
    trips = list(csv.DictReader(apri('trips.txt')))
    stops = {r['stop_id']: r for r in csv.DictReader(apri('stops.txt'))}
    info = list(csv.DictReader(apri('feed_info.txt')))
    versione = (info[0].get('feed_version') or '') if info else ''
    # calendario: giorni coperti e, per ogni servizio, i giorni in cui circola
    servizi = collections.defaultdict(set)
    for r in csv.DictReader(apri('calendar_dates.txt')):
        if r['exception_type'] == '1':
            servizi[r['service_id']].add(r['date'])
        else:
            servizi[r['service_id']].discard(r['date'])
    giorni = sorted({d for s in servizi.values() for d in s})
    gi = {d: i for i, d in enumerate(giorni)}
    SID = sorted(servizi); SIX = {s: i for i, s in enumerate(SID)}
    bit = []
    for s in SID:
        b = bytearray((len(giorni) + 7) // 8)
        for d in servizi[s]:
            b[gi[d] // 8] |= 1 << (gi[d] % 8)
        bit.append(base64.b64encode(bytes(b)).decode())
    # passaggi alle fermate di ogni corsa
    passaggi = collections.defaultdict(list)
    for r in csv.DictReader(apri('stop_times.txt')):
        t = r['departure_time'] or r['arrival_time']
        if t:
            passaggi[r['trip_id']].append((int(r['stop_sequence']), r['stop_id'], minuti(t)))
    # comune di ogni fermata, dalla rete degli autobus già calcolata (stessa fonte, stessi stop_id)
    comune = {}
    if TPL.exists():
        for f in leggi_b64(TPL)['fermate']:
            comune[f[4]] = f[3]
    FERMATE, FIX = [], {}
    def fid(s):
        if s not in FIX:
            FIX[s] = len(FERMATE); st = stops.get(s, {})
            try:
                lat, lon = round(float(st['stop_lat']), 5), round(float(st['stop_lon']), 5)
            except (KeyError, ValueError):
                lat = lon = None
            FERMATE.append([st.get('stop_name', s), comune.get(s, -1), s, lat, lon, []])
        return FIX[s]
    per_rotta = collections.defaultdict(list)
    for t in trips:
        if t['trip_id'] in passaggi and t['service_id'] in SIX:
            per_rotta[t['route_id']].append(t)
    linee, file_linee = [], {}
    for n, ro in enumerate(sorted(routes, key=lambda r: (r['route_short_name'], r['route_long_name'], r['route_id']))):
        ts = per_rotta.get(ro['route_id'], [])
        if not ts:
            continue
        seq, SQX, corse = [], {}, []
        for t in ts:
            p = sorted(passaggi[t['trip_id']])
            chiave = tuple(fid(s) for _, s, _ in p)
            for f in chiave:
                if len(linee) not in FERMATE[f][5]:
                    FERMATE[f][5].append(len(linee))
            if chiave not in SQX:
                SQX[chiave] = len(seq); seq.append(list(chiave))
            orari = [m for _, _, m in p]
            corse.append([SQX[chiave], SIX[t['service_id']], orari[0]] + [b - a for a, b in zip(orari, orari[1:])])
        # la fonte ripete alcune corse identiche (stessa sequenza, stesso servizio, stessi orari): se ne tiene una
        corse = [list(c) for c in sorted({tuple(c) for c in corse}, key=lambda c: (c[2], c[0], c[1]))]
        # direzione: ultima fermata della sequenza più frequente (in alcune linee la destinazione indicata dalla fonte è la partenza)
        principale = collections.Counter(c[0] for c in corse).most_common(1)[0][0]
        capolinea = FERMATE[seq[principale][-1]][0]
        # nome stabile, ricavato dal codice del percorso: le settimane successive si riscrivono solo i file cambiati
        nome_file = re.sub(r'[^a-z0-9]+', '-', ro['route_id'].lower()).strip('-') + '.txt'
        file_linee[nome_file] = {'s': seq, 'c': corse}
        linee.append([ro['route_short_name'], ro['route_long_name'], ro['route_color'] or '155E9E', ro['route_text_color'] or 'FFFFFF',
                      int(ro['route_type'] or 3), nome_file, len(corse), capolinea, ro['route_id']])
    # nomi dei comuni nell'ordine dell'Atlante, per indicare il comune di ogni fermata
    m = re.search(r'^const DB = (.*);$', (RADICE / 'index.html').read_text(encoding='utf-8'), re.M)
    nomi = [c['n'] for c in json.loads(m.group(1))['c']] if m else []
    indice = {'versione': versione, 'comuni': nomi, 'fonte': 'TPL FVG tramite BusOne (https://busone.app)', 'giorni': giorni, 'servizi': bit, 'fermate': FERMATE, 'linee': linee}
    return indice, file_linee


def main():
    try:
        indice, file_linee = costruisci(apri_gtfs(sys.argv[1] if len(sys.argv) > 1 else None))
    except Exception as e:
        print(f'Orari: non aggiornati ({e}). Restano quelli di prima.')
        return 0
    corse = sum(len(f['c']) for f in file_linee.values())
    if len(indice['linee']) < 100 or corse < 10000 or not indice['giorni']:
        print(f"Orari: GTFS sospetto ({len(indice['linee'])} linee, {corse} corse). Restano quelli di prima.")
        return 0
    CARTELLA.mkdir(parents=True, exist_ok=True)
    cambiati = sum(scrivi_b64(CARTELLA / nome, o) for nome, o in file_linee.items())
    vecchi = [p for p in CARTELLA.glob('*.txt') if p.name != 'indice.txt' and p.name not in file_linee]
    for p in vecchi:
        p.unlink()
    nuovo_indice = scrivi_b64(CARTELLA / 'indice.txt', indice)
    g = indice['giorni']
    print(f"Orari: versione {indice['versione']}, validi dal {g[0]} al {g[-1]}, {len(indice['linee'])} linee e {corse} corse; "
          f"{cambiati} file di linea riscritti, {len(vecchi)} tolti{', indice aggiornato' if nuovo_indice else ''}.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
