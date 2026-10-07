#!/usr/bin/env python3
"""Posizione delle scuole dell'elenco regionale 2026/27, ricavata dall'indirizzo con Nominatim (OpenStreetMap).

L'elenco ufficiale delle scuole (foglio Scuole_2026_27) ha indirizzo e comune ma non le coordinate. Questo script interroga
Nominatim una volta per scuola (una richiesta al secondo, come chiede il servizio) e salva dati/scuole_coord.json con
codice meccanografico, coordinate, precisione dichiarata dal servizio e indirizzo riconosciuto. La posizione è «dall'indirizzo,
da verificare»: la pagina dei servizi lo scrive accanto a ogni scuola. Le scuole che il servizio non trova restano senza
coordinate e compaiono solo nell'elenco. Uso: python scripts/geocodifica_scuole.py
"""
import base64, gzip, json, re, time, urllib.parse, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / 'dati' / 'scuole_coord.json'
UA = {'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/; info@atlantefvg.it)'}
BOX = (12.3, 45.55, 13.95, 46.7)  # longitudine e latitudine minime e massime della regione


def main():
    testo = (RADICE / 'index.html').read_text(encoding='utf-8')
    man = json.loads(re.search(r'^const MAN = (.*);$', testo, re.M).group(1))
    f = next(x for x in man['manifest'] if x['id'] == 'Scuole_2026_27')
    rows = []
    for fn in f['files']:
        rows += json.loads(gzip.decompress(base64.b64decode((RADICE / fn).read_text())))['rows']
    c = {n: i for i, n in enumerate(f['cols'])}
    vecchie = json.loads(USCITA.read_text(encoding='utf-8')) if USCITA.exists() else {}
    out = dict(vecchie.get('scuole', {}))
    trovate = 0
    for r in rows:
        cod = r[c['Codice meccanografico']]
        if cod in out and out[cod].get('lat'):
            trovate += 1; continue
        indirizzo, comune = (r[c['Indirizzo']] or '').strip(), (r[c['Comune']] or '').strip()
        q = f'{indirizzo}, {comune.title()}, Friuli Venezia Giulia'
        url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'format': 'jsonv2', 'limit': 1, 'countrycodes': 'it', 'q': q, 'viewbox': ','.join(map(str, BOX)), 'bounded': 1})
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as risp:
                ris = json.loads(risp.read().decode())
        except Exception as e:
            ris = []; print('errore', cod, e)
        if ris:
            p = ris[0]
            out[cod] = {'lat': round(float(p['lat']), 6), 'lon': round(float(p['lon']), 6), 'precisione': p.get('addresstype') or p.get('type'), 'riconosciuto': p.get('display_name', '')[:160], 'cercato': q}
            trovate += 1
        else:
            out[cod] = {'lat': None, 'lon': None, 'precisione': None, 'riconosciuto': None, 'cercato': q}
        time.sleep(1.1)
    USCITA.write_text(json.dumps({'fonte': 'Nominatim (OpenStreetMap), ricerca per indirizzo; dati © OpenStreetMap contributors, ODbL', 'generato': time.strftime('%Y-%m-%d'), 'nota': 'Posizione ricavata dall\'indirizzo dell\'elenco regionale 2026/27: approssimata e da verificare; le scuole non trovate hanno coordinate nulle.', 'scuole': out}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Scuole: {trovate} con posizione su {len(rows)}.')


if __name__ == '__main__':
    main()
