#!/usr/bin/env python3
"""Controlla se le fonti da aggiornare a mano hanno pubblicato una versione nuova.

Alcuni fogli dell'archivio vengono da file che non si possono riscaricare e rielaborare in
automatico (Annuario statistico regionale, elenco delle scuole, RUNTS, ISTAT, CONI e simili).
Per queste fonti lo script legge le intestazioni della risposta (data di modifica ed etichetta di
versione, con la dimensione) e le confronta con quelle salvate in dati/fonti_manuali.json. Se
qualcosa è cambiato, lo elenca: il foglio va aggiornato a mano. Le fonti che non dichiarano né
data né versione sono indicate come «non verificabili».

Scrive il riepilogo anche in fonti_da_aggiornare.md, che il flusso del lunedì usa per aprire o
aggiornare una segnalazione su GitHub. Usa solo la libreria standard di Python.
"""
import json, re, sys, urllib.error, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
STATO = RADICE / 'dati' / 'fonti_manuali.json'
# fogli che i flussi automatici già aggiornano: non vanno controllati qui
AUTOMATICI = re.compile(r'dati\.friuliveneziagiulia\.it/api/views|elezioniamministratori\.regione\.fvg\.it|busone|opencup|socrata', re.I)
UA = {'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/)'}


def intestazioni(url):
    for metodo in ('HEAD', 'GET'):
        try:
            req = urllib.request.Request(url, headers=UA, method=metodo)
            with urllib.request.urlopen(req, timeout=60) as r:
                # la sola dimensione non basta: le pagine dinamiche cambiano a ogni lettura
                h = {k: r.headers.get(k) for k in ('Last-Modified', 'ETag') if r.headers.get(k)}
                if h and r.headers.get('Content-Length'):
                    h['Content-Length'] = r.headers.get('Content-Length')
                return r.status, h
        except urllib.error.HTTPError as e:
            if metodo == 'GET' or e.code not in (403, 405, 501):
                return e.code, {}
        except Exception as e:  # rete, certificati, tempo scaduto
            if metodo == 'GET':
                return 0, {'errore': str(e)[:120]}
    return 0, {}


def main():
    html = (RADICE / 'index.html').read_text(encoding='utf-8')
    man = json.loads(re.search(r'^const MAN = (.*);$', html, re.M).group(1).replace('<\\/', '</'))
    fonti = {}
    for f in man['manifest']:
        u = (f.get('fonte') or '').strip().split()[0] if (f.get('fonte') or '').strip() else ''
        if u.startswith('http') and not AUTOMATICI.search(u):
            fonti.setdefault(u, []).append(f['id'])
    vecchio = json.loads(STATO.read_text(encoding='utf-8')) if STATO.exists() else {}
    nuovo, cambiate, non_verificabili, errori = {}, [], [], []
    for u, fogli in sorted(fonti.items()):
        st, h = intestazioni(u)
        if st != 200:
            errori.append((u, fogli, st or h.get('errore', 'nessuna risposta')))
            nuovo[u] = vecchio.get(u, {})
            continue
        nuovo[u] = h
        if not h:
            non_verificabili.append((u, fogli))
        elif u in vecchio and vecchio[u] and vecchio[u] != h:
            cambiate.append((u, fogli, vecchio[u], h))
    STATO.write_text(json.dumps(nuovo, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    r = [f'Fonti da aggiornare a mano controllate: {len(fonti)}.']
    if cambiate:
        r.append('\nFonti con una versione nuova (i fogli indicati vanno aggiornati a mano):')
        r += [f'- {", ".join(fg)}: {u} (prima {json.dumps(a, ensure_ascii=False)}, ora {json.dumps(b, ensure_ascii=False)})' for u, fg, a, b in cambiate]
    if errori:
        r.append('\nFonti che non hanno risposto:')
        r += [f'- {", ".join(fg)}: {u} (risposta {e})' for u, fg, e in errori]
    if non_verificabili:
        r.append('\nFonti che non dichiarano data o versione (non verificabili in automatico):')
        r += [f'- {", ".join(fg)}: {u}' for u, fg in non_verificabili]
    testo = '\n'.join(r)
    print(testo)
    (RADICE / 'fonti_da_aggiornare.md').write_text(testo + '\n' if cambiate else '', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
