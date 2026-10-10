#!/usr/bin/env python3
"""Copertura del trasporto pubblico per comune, dagli orari TPL FVG già scaricati.

Legge dati/orari/indice.txt e i file dei percorsi (prodotti da scripts/aggiorna_orari.py dal GTFS di TPL FVG
pubblicato da BusOne) e calcola, per ogni comune, quante corse di autobus toccano almeno una fermata del
comune in un giorno: la mediana dei giorni feriali (lunedì-venerdì), dei sabati e delle domeniche nel
periodo coperto dagli orari. Conta inoltre le linee che servono il comune in un giorno feriale (mediana)
e le fermate con sede nel comune. Le fermate senza comune noto non entrano nel conto.

Scrive in «const EXTRA» di index.html, per ogni comune, il campo «tp»:
  {fer, sab, dom, linee, ferm, v (versione degli orari), da, a (primo e ultimo giorno coperto)}.
Usa solo la libreria standard di Python.
Uso: python3 scripts/aggiorna_trasporto.py [--prova]
"""
import base64, collections, datetime, gzip, json, re, statistics, sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINA = RADICE / 'index.html'
ORARI = RADICE / 'dati' / 'orari'


def leggi(p):
    return json.loads(gzip.decompress(base64.b64decode(p.read_text().strip())))


def calcola():
    ind = leggi(ORARI / 'indice.txt')
    giorni, comuni, fermate = ind['giorni'], ind['comuni'], ind['fermate']
    ng, nc = len(giorni), len(comuni)
    servizi = [base64.b64decode(s) for s in ind['servizi']]
    attivi = [[g for g in range(ng) if (b[g >> 3] >> (g & 7)) & 1] for b in servizi]
    settimana = [datetime.date(int(g[:4]), int(g[4:6]), int(g[6:])).weekday() for g in giorni]
    corse = [[0] * ng for _ in range(nc)]
    linee = [[set() for _ in range(ng)] for _ in range(nc)]
    ferm = [0] * nc
    for f in fermate:
        if f[1] >= 0: ferm[f[1]] += 1
    for li, l in enumerate(ind['linee']):
        d = leggi(ORARI / l[5])
        for c in d['c']:
            toccati = set(fermate[x][1] for x in d['s'][c[0]] if fermate[x][1] >= 0)
            for g in attivi[c[1]]:
                for cm in toccati:
                    corse[cm][g] += 1; linee[cm][g].add(li)
    fer = [g for g in range(ng) if settimana[g] < 5]
    sab = [g for g in range(ng) if settimana[g] == 5]
    dom = [g for g in range(ng) if settimana[g] == 6]
    med = lambda v: int(statistics.median(v)) if v else 0
    out = []
    for i in range(nc):
        out.append({'fer': med([corse[i][g] for g in fer]), 'sab': med([corse[i][g] for g in sab]), 'dom': med([corse[i][g] for g in dom]),
                    'linee': med([len(linee[i][g]) for g in fer]), 'ferm': ferm[i], 'v': ind['versione'], 'da': giorni[0], 'a': giorni[-1]})
    return comuni, out


def main():
    prova = '--prova' in sys.argv
    comuni, valori = calcola()
    html = PAGINA.read_text(encoding='utf-8')
    m_db = re.search(r'^const DB = (.*);$', html, re.M)
    nomi = [c['n'] for c in json.loads(m_db.group(1).replace('<\\/', '</'))['c']]
    m = re.search(r'^const EXTRA = (.*);$', html, re.M)
    extra = json.loads(m.group(1).replace('<\\/', '</'))
    # l'indice degli orari usa i comuni nell'ordine dell'Atlante (DB.c): si verifica con i nomi
    if nomi != comuni:
        raise SystemExit('L\'ordine dei comuni negli orari non coincide con quello della pagina')
    for i, v in enumerate(valori):
        extra['E'].setdefault(str(i), {})['tp'] = v
    zeri = [comuni[i] for i, v in enumerate(valori) if v['fer'] == 0]
    print(f"comuni: {len(comuni)}; corse feriali mediane: min {min(v['fer'] for v in valori)}, mediana {statistics.median(v['fer'] for v in valori)}, max {max(v['fer'] for v in valori)}; senza corse feriali: {zeri or 'nessuno'}; senza corse la domenica: {sum(1 for v in valori if v['dom'] == 0)}")
    if prova: return
    testo = json.dumps(extra, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    PAGINA.write_text(html[:m.start(1)] + testo + html[m.end(1):], encoding='utf-8')
    print('index.html aggiornato')


if __name__ == '__main__':
    main()
