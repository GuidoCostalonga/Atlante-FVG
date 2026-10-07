#!/usr/bin/env python3
"""Prepara dati/servizi.json per la pagina «Servizi sul territorio»: i punti con coordinate dei fogli già nell'archivio.

Categorie: farmacie, parafarmacie, guardie mediche (continuità assistenziale), residenze per anziani, scuole statali
(posizione dall'indirizzo, da verificare: dati/scuole_coord.json, scritto da geocodifica_scuole.py) e fermate degli autobus
(rete TPL FVG di dati/_tpl_0.txt, riportate dalle coordinate della mappa a latitudine e longitudine). Per ogni categoria si
riportano fonte e data di consultazione prese dall'indice dei fogli; contatti e orari compaiono solo se la fonte ufficiale li
pubblica. Gli impianti sportivi non hanno indirizzo nei dati disponibili e restano fuori. Scrive anche il centro di ogni
comune, per centrare la mappa. Uso: python scripts/prepara_servizi.py
"""
import base64, gzip, json, math, re, time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FX = [0.9981337794975602, -0.07416881054833876, 87284.31391544109]
FY = [-0.0731952954966455, -0.9967836423904924, 5175818.401653809]


def leggi(fn):
    return json.loads(gzip.decompress(base64.b64decode((RADICE / fn).read_text())))


def utm_inverso(x, y, zona=33):
    a = 6378137.0; f = 1 / 298.257223563; k0 = 0.9996; e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2)); lon0 = math.radians((zona - 1) * 6 - 180 + 3)
    M = y / k0; mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    phi1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
    N1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2); T1 = math.tan(phi1) ** 2; C1 = ep2 * math.cos(phi1) ** 2
    R1 = a * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5; D = (x - 500000) / (N1 * k0)
    lat = phi1 - (N1 * math.tan(phi1) / R1) * (D * D / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * D ** 4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * ep2 - 3 * C1 * C1) * D ** 6 / 720)
    lon = lon0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * ep2 + 24 * T1 * T1) * D ** 5 / 120) / math.cos(phi1)
    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)


def mappa_inversa(px, py):
    """Dalle coordinate della mappa (affine di UTM 33) a latitudine e longitudine."""
    a, b, c = FX; d, e, f = FY
    det = a * e - b * d; X = (e * (px - c) - b * (py - f)) / det; Y = (-d * (px - c) + a * (py - f)) / det
    return utm_inverso(X, Y)


def orari_farmacia(fasce):
    """Le fasce del dataset sono date e ore complete («06/10/2026 08:30:00»): si riportano per giorno, con l'orario senza secondi."""
    import re as _re
    per_giorno = {}
    for da, a in fasce:
        m1, m2 = _re.match(r'(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})', str(da)), _re.match(r'(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})', str(a or ''))
        if not m1:
            continue
        giorno = f'{int(m1[1])} {MESI[int(m1[2]) - 1]}'
        per_giorno.setdefault(giorno, []).append(f'{int(m1[4])}:{m1[5]}' + (f'–{int(m2[4])}:{m2[5]}' if m2 else ''))
    return '; '.join(f'{g}: {", ".join(v)}' for g, v in per_giorno.items()) or None


MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def num(v):
    try:
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def main():
    testo = (RADICE / 'index.html').read_text(encoding='utf-8')
    man = json.loads(re.search(r'^const MAN = (.*);$', testo, re.M).group(1))
    db = json.loads(re.search(r'^const DB = (.*);$', testo, re.M).group(1))
    slugs = {c['n']: s for c, s in zip(db['c'], [x['slug'] for x in json.loads((RADICE / 'dati' / 'comuni_slug.json').read_text(encoding='utf-8'))])}
    istat_slug = {x['id']: x['slug'] for x in json.loads((RADICE / 'dati' / 'comuni_slug.json').read_text(encoding='utf-8'))}
    idx_slug = [istat_slug.get(i) for i in man['istat']]
    def foglio(n):
        f = next(x for x in man['manifest'] if x['id'] == n); rows, ks = [], []
        for fn in f['files']:
            d = leggi(fn); rows += d['rows']; ks += d.get('k', [])
        return f, {c: i for i, c in enumerate(f['cols'])}, rows, ks
    cat, punti = [], []
    def aggiungi(idc, nome, f, nota=''):
        cat.append({'id': idc, 'nome': nome, 'fonte': f['fonte'], 'consultazione': f.get('cons'), 'nota': nota})
    # farmacie: orari pubblicati dalla fonte (fasce del giorno)
    f, c, rows, ks = foglio('Farmacie'); aggiungi('farmacie', 'Farmacie', f, 'Telefono e orari sono quelli del dataset regionale: gli orari si riferiscono ai giorni indicati, letti alla data di consultazione.')
    for r, k in zip(rows, ks):
        lat, lon = num(r[c['latitudine']]), num(r[c['longitudine']])
        if lat and lon:
            orari = orari_farmacia([(r[c[f'orari/{j}/da']], r[c[f'orari/{j}/a']]) for j in range(6) if f'orari/{j}/da' in c and r[c[f'orari/{j}/da']]])
            punti.append(['farmacie', lat, lon, r[c['insegna']] or r[c['ragioneSociale']], r[c['indirizzo']] or '', idx_slug[k] if k >= 0 else None, {'telefono': r[c['telefono']] or None, 'orari': orari or None}])
    f, c, rows, ks = foglio('Parafarmacie_2024'); aggiungi('parafarmacie', 'Parafarmacie', f)
    for r, k in zip(rows, ks):
        lat, lon = num(r[c['latitudine']]), num(r[c['longitudine']])
        if lat and lon:
            punti.append(['parafarmacie', lat, lon, r[c['sito_logistico']], r[c['indirizzo']] or '', idx_slug[k] if k >= 0 else None, {}])
    f, c, rows, ks = foglio('Guardie_mediche'); aggiungi('guardie', 'Guardie mediche (continuità assistenziale)', f, 'Telefono e orari sono quelli del dataset regionale.')
    for r, k in zip(rows, ks):
        lat, lon = num(r[c['latitudine']]), num(r[c['longitudine']])
        if lat and lon:
            orari = '; '.join(f'{k2}: {r[c[k2]]}' for k2 in ('feriale', 'prefestivo', 'festivo') if k2 in c and r[c[k2]])
            kk = k[0] if isinstance(k, list) else k
            punti.append(['guardie', lat, lon, 'Guardia medica ' + (r[c['comune/comune']] or ''), ((r[c['via']] or '') + (' presso ' + r[c['presso']] if r[c['presso']] else '')).strip(), idx_slug[kk] if kk is not None and kk >= 0 else None, {'telefono': r[c['telefono']] or None, 'orari': orari or None, 'azienda': r[c['azienda']] or None}])
    f, c, rows, ks = foglio('Residenze_anziani'); aggiungi('rsa', 'Residenze per anziani', f)
    for r, k in zip(rows, ks):
        lat, lon = num(r[c['lat']]), num(r[c['longit']])
        if lat and lon:
            punti.append(['rsa', lat, lon, r[c['denominazione']], f"{r[c['indirizzo']] or ''} {r[c['n_civ']] or ''}".strip(), idx_slug[k] if k >= 0 else None, {'telefono': r[c['telefono']] or None, 'tipologia': r[c['tipologia']] or None, 'posti': r[c['pl_tot']]}])
    f, c, rows, ks = foglio('Scuole_2026_27')
    sc = RADICE / 'dati' / 'scuole_coord.json'
    coord = json.loads(sc.read_text(encoding='utf-8'))['scuole'] if sc.exists() else {}
    aggiungi('scuole', 'Scuole statali (sedi degli istituti) 2026/27', f, 'Posizione ricavata dall\'indirizzo con Nominatim (OpenStreetMap): approssimata e da verificare. Solo le sedi principali degli istituti statali di lingua italiana.')
    senza = 0
    for r, k in zip(rows, ks):
        p = coord.get(r[c['Codice meccanografico']])
        if p and p.get('lat'):
            punti.append(['scuole', p['lat'], p['lon'], f"{r[c['Tipo istituto']] or ''} {r[c['Denominazione']] or ''}".strip().title(), (r[c['Indirizzo']] or '').title(), idx_slug[k] if k >= 0 else None, {'codice': r[c['Codice meccanografico']], 'precisione': p.get('precisione'), 'daVerificare': True}])
        else:
            senza += 1
    # fermate degli autobus
    tpl = leggi('dati/_tpl_0.txt')
    cat.append({'id': 'fermate', 'nome': 'Fermate degli autobus', 'fonte': tpl.get('fonte', 'TPL FVG, dati GTFS') + ', versione ' + str(tpl.get('versione', '')), 'consultazione': None, 'nota': 'Coordinate riportate dalla mappa dell\'Atlante alla latitudine e longitudine; gli orari si aprono nella pagina Orari.'})
    for s in tpl['fermate']:
        lat, lon = mappa_inversa(s[0], s[1])
        punti.append(['fermate', lat, lon, s[2], '', idx_slug[s[3]] if isinstance(s[3], int) and 0 <= s[3] < len(idx_slug) else None, {'id': s[4], 'linee': len(s[5]) if isinstance(s[5], list) else None}])
    # centro di ogni comune dalle geometrie della mappa
    geo = leggi('dati/_mappe_0.txt'); centri = {}
    for cm in geo['comuni']:
        xs, ys = [], []
        for ring in cm['r']:
            xs += ring[0::2]; ys += ring[1::2]
        if xs:
            centri[idx_slug[cm['c']]] = list(mappa_inversa(sum(xs) / len(xs), sum(ys) / len(ys)))
    out = {'generato': time.strftime('%Y-%m-%d'), 'categorie': cat, 'punti': punti, 'comuni': centri,
           'nota': 'Distanze calcolate in linea d\'aria. Percorsi stradali e tempi di viaggio non sono mostrati perché non c\'è un servizio di calcolo integrato. Gli impianti sportivi del registro CONI non hanno un indirizzo nei dati disponibili e non compaiono sulla mappa.',
           'scuoleSenzaPosizione': senza}
    (RADICE / 'dati' / 'servizi.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    import collections
    print('Servizi:', dict(collections.Counter(p[0] for p in punti)), 'scuole senza posizione', senza, 'comuni', len(centri), 'dimensione', (RADICE / 'dati' / 'servizi.json').stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    main()
