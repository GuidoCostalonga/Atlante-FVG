#!/usr/bin/env python3
"""Porta nella pagina le comunità linguistiche tutelate, comune per comune.

Legge la tavola 21.1 dell'Annuario statistico regionale 2026 («Comuni con presenza di comunità linguistiche»,
situazione al 31 dicembre 2025, fonte ISTAT, ARLeF e Regione), già nell'archivio in dati/C26_21_comunitalinguistich_0.txt,
e scrive per ogni comune, in «const EXTRA» di index.html, il campo «ling» con il nome ufficiale nelle lingue tutelate:
f = friulano, s = sloveno, t = tedesco. I comuni senza tutela non hanno il campo.
Per Paluzza la tutela del tedesco riguarda la sola frazione di Timau: il nome resta quello della frazione, come nella fonte.

Uso: python3 scripts/aggiorna_lingue.py [--prova]
"""
import base64, gzip, json, re, sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINA = RADICE / 'index.html'
FOGLIO = RADICE / 'dati' / 'C26_21_comunitalinguistich_0.txt'


def leggi_tavola():
    dati = json.loads(gzip.decompress(base64.b64decode(FOGLIO.read_text().strip())))
    righe = [r for r in dati['rows'] if str(r[0]).startswith('Tav_21_1')]
    if not righe:
        raise SystemExit('Nel foglio manca la tavola 21.1')
    lingua, per_comune = None, {}
    for r in righe:
        celle = [c for c in r[3:] if c is not None]
        if len(celle) == 1 and isinstance(celle[0], str):
            t = celle[0].lower()
            if t.startswith('comuni con presenza di cittadini di lingua slovena'): lingua = 's'
            elif t.startswith('comuni friulanofoni'): lingua = 'f'
            elif t.startswith('comuni germanofoni'): lingua = 't'
            continue
        # ogni riga porta fino a due comuni: codice, nome italiano, nome nell'altra lingua
        for k in range(0, len(celle) - 2, 3):
            cod, nome_it, nome_altro = celle[k], celle[k + 1], celle[k + 2]
            if not isinstance(cod, int) or not lingua: continue
            nome = re.sub(r'\s*\n\s*', ' ', str(nome_altro)).strip()
            per_comune.setdefault(f'{cod:06d}', {})[lingua] = nome
    return per_comune


def main():
    prova = '--prova' in sys.argv
    tav = leggi_tavola()
    html = PAGINA.read_text(encoding='utf-8')
    m_man = re.search(r'^const MAN = (.*);$', html, re.M)
    istat = json.loads(m_man.group(1).replace('<\\/', '</'))['istat']
    m = re.search(r'^const EXTRA = (.*);$', html, re.M)
    extra = json.loads(m.group(1).replace('<\\/', '</'))
    mancanti = [c for c in tav if c not in istat]
    if mancanti:
        raise SystemExit(f'Codici ISTAT della tavola non trovati fra i comuni: {mancanti}')
    n = {'f': 0, 's': 0, 't': 0}
    for i, cod in enumerate(istat):
        e = extra['E'].setdefault(str(i), {})
        if cod in tav:
            e['ling'] = {k: tav[cod][k] for k in ('f', 's', 't') if k in tav[cod]}
            for k in e['ling']: n[k] += 1
        else:
            e.pop('ling', None)
    print(f"comuni con tutela: friulano {n['f']}, sloveno {n['s']}, tedesco {n['t']}, in totale {len(tav)}")
    if prova:
        return
    testo = json.dumps(extra, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    PAGINA.write_text(html[:m.start(1)] + testo + html[m.end(1):], encoding='utf-8')
    print('index.html aggiornato')


if __name__ == '__main__':
    main()
