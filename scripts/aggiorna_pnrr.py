#!/usr/bin/env python3
"""Progetti del PNRR (Piano nazionale di ripresa e resilienza) localizzati in Friuli Venezia Giulia.

Fonte: gli open data di OpenPNRR (Fondazione Openpolis), che ripubblicano i dati ufficiali di Italia Domani e ReGiS
(il portale ufficiale rifiuta gli accessi dall'estero). File usati: progetti.csv (un progetto per CUP, con i
finanziamenti), progetti_territori.csv (localizzazione per comune con codice ISTAT). I pagamenti non vengono usati:
nel file le righe non sono riconducibili con certezza a importi cumulati per progetto.

Scrive:
- dati/pnrr/progetti_N.txt: fogli (JSON compressi con gzip, in base64) con una riga per progetto localizzato in regione;
- dati/pnrr_meta.json: data dei dati, file, colonne, conteggi;
- dati/pnrr_cup.json: elenco dei CUP dei progetti PNRR in regione (per il contrassegno nella pagina delle opere);
- in «const EXTRA» di index.html, per ogni comune: pnN (progetti localizzati nel comune), pnSolo (di questi, quelli
  localizzati nel solo comune), pnFin (finanziamento PNRR dei progetti nel solo comune), pnFinAb (per abitante),
  pnTop (i sei più finanziati nel solo comune).

Uso: python3 scripts/aggiorna_pnrr.py [--cartella <cartella con progetti.csv e progetti_territori.csv>] [--aggiornati AAAA-MM-GG]
Senza --cartella scarica i file da openpnrr.s3.amazonaws.com (circa 140 MB). Usa solo la libreria standard di Python.
"""
import base64, collections, csv, gzip, json, re, sys, time, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINA = RADICE / 'index.html'
DATI = RADICE / 'dati'
BASE = 'https://openpnrr.s3.amazonaws.com/media/'
FILE = ['progetti.csv', 'progetti_territori.csv']
PROVINCE = ('030', '031', '032', '093')
MISSIONI = {'M1': 'Digitalizzazione, innovazione, competitività, cultura e turismo', 'M2': 'Rivoluzione verde e transizione ecologica', 'M3': 'Infrastrutture per una mobilità sostenibile',
            'M4': 'Istruzione e ricerca', 'M5': 'Inclusione e coesione', 'M6': 'Salute', 'M7': 'REPowerEU'}
COLONNE = ['CUP', 'Titolo', 'Missione e componente', 'Misura', 'Soggetto attuatore', 'Finanziamento PNRR (euro)', 'Finanziamento totale (euro)', 'Comuni', 'Territori in Italia', 'Codice locale del progetto']
RIGHE_PER_FILE = 2000


def riga_js(testo, nome):
    m = re.search(r'^const %s = (.*);$' % nome, testo, re.M)
    if not m:
        raise SystemExit(f'Riga const {nome} non trovata in index.html')
    return m, json.loads(m.group(1).replace('<\\/', '</'))


def scarica(cartella):
    cartella.mkdir(parents=True, exist_ok=True)
    for f in FILE:
        dest = cartella / f
        if dest.exists():
            continue
        print(f'scarico {f}…')
        with urllib.request.urlopen(urllib.request.Request(BASE + f, headers={'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/)'}), timeout=600) as r:
            dest.write_bytes(r.read())
    return cartella


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main():
    args = sys.argv[1:]
    cartella = Path(args[args.index('--cartella') + 1]) if '--cartella' in args else scarica(Path('/tmp') / 'openpnrr')
    aggiornati = args[args.index('--aggiornati') + 1] if '--aggiornati' in args else ''
    testo = PAGINA.read_text(encoding='utf-8')
    m_ex, extra = riga_js(testo, 'EXTRA')
    _, db = riga_js(testo, 'DB')
    _, man = riga_js(testo, 'MAN')
    indice = {c: i for i, c in enumerate(man['istat'])}
    nome = {c['id']: c['n'] for c in db['c']}
    residenti = {c['id']: c.get('p25') for c in db['c']}

    # localizzazioni: territori in tutta Italia per CUP e comuni della regione
    tutti, fvg = collections.Counter(), collections.defaultdict(set)
    with open(cartella / 'progetti_territori.csv', encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            tutti[r['cup']] += 1
            if r['istat_id'][:3] in PROVINCE and r['istat_id'] in indice:
                fvg[r['cup']].add(r['istat_id'])
    progetti = {}
    with open(cartella / 'progetti.csv', encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            if r['cup'] in fvg:
                progetti[r['cup']] = r
    mancanti = [c for c in fvg if c not in progetti]
    if mancanti:
        print(f'avviso: {len(mancanti)} CUP localizzati in regione senza riga nel file dei progetti')
    if len(progetti) < 1000:
        raise SystemExit(f'troppo pochi progetti ({len(progetti)}): i file sembrano incompleti, nulla è stato scritto')

    righe = []
    for cup, r in sorted(progetti.items(), key=lambda x: -num(x[1]['finanziamento_pnrr'])):
        mc = r['codice_misura'][:4]
        righe.append([cup, r['titolo'].strip(), mc, f"{r['codice_misura']} {r['descrizione'].strip()}", r['soggetto_attuatore_denominazione'].strip(),
                      round(num(r['finanziamento_pnrr']), 2), round(num(r['finanziamento_totale']), 2), sorted(nome[c] for c in fvg[cup]), tutti[cup], r['codice_locale_progetto']])
    for vecchio in DATI.glob('pnrr/progetti_*.txt'):
        vecchio.unlink()
    files = []
    for k in range(0, len(righe), RIGHE_PER_FILE):
        p = DATI / 'pnrr' / f'progetti_{k // RIGHE_PER_FILE}.txt'
        p.write_text(base64.b64encode(gzip.compress(json.dumps({'cols': COLONNE, 'rows': righe[k:k + RIGHE_PER_FILE]}, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), 9)).decode('ascii'))
        files.append(f'dati/pnrr/{p.name}')
    (DATI / 'pnrr_cup.json').write_text(json.dumps(sorted(progetti), separators=(',', ':')))

    # riepilogo per comune
    per_com = collections.defaultdict(list)
    for cup in progetti:
        for c in fvg[cup]:
            per_com[c].append(cup)
    tot_fin = 0.0
    for istat, i in indice.items():
        e = extra['E'].setdefault(str(i), {})
        for vecchio in ('pnN', 'pnSolo', 'pnFin', 'pnFinAb', 'pnTop'):
            e.pop(vecchio, None)
        lista = per_com.get(istat, [])
        solo = [c for c in lista if tutti[c] == 1]
        fin = sum(num(progetti[c]['finanziamento_pnrr']) for c in solo)
        tot_fin += fin
        top = sorted(solo, key=lambda c: -num(progetti[c]['finanziamento_pnrr']))[:6]
        e['pnN'] = len(lista); e['pnSolo'] = len(solo); e['pnFin'] = round(fin)
        e['pnFinAb'] = round(fin / residenti[istat], 1) if residenti.get(istat) else None
        e['pnTop'] = [[progetti[c]['titolo'].strip()[:160], progetti[c]['codice_misura'][:4] + ' · ' + progetti[c]['descrizione'].strip()[:70], round(num(progetti[c]['finanziamento_pnrr'])), progetti[c]['soggetto_attuatore_denominazione'].strip()[:80], c] for c in top]
    extra['pnrr'] = {'aggiornati': aggiornati, 'letti': time.strftime('%Y-%m-%d'), 'progetti': len(progetti)}
    testo = testo[:m_ex.start(1)] + json.dumps(extra, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + testo[m_ex.end(1):]
    PAGINA.write_text(testo, encoding='utf-8')
    meta = {'aggiornati': aggiornati, 'letti': time.strftime('%Y-%m-%d'), 'progetti': len(progetti), 'comuni': len(per_com), 'finanziamentoPnrrSoloComune': round(tot_fin),
            'finanziamentoPnrrTotale': round(sum(num(r['finanziamento_pnrr']) for r in progetti.values())), 'files': files, 'cols': COLONNE, 'missioni': MISSIONI,
            'fonte': 'OpenPNRR (Fondazione Openpolis), open data da Italia Domani e ReGiS', 'indirizzo': 'https://openpnrr.it/opendata/'}
    (DATI / 'pnrr_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"progetti PNRR in regione: {len(progetti)} in {len(per_com)} comuni; nel solo comune: {sum(1 for c in progetti if tutti[c] == 1)}; finanziamento PNRR totale {meta['finanziamentoPnrrTotale']:,} euro, di cui nel solo comune {round(tot_fin):,}; file: {len(files)}")


if __name__ == '__main__':
    main()
