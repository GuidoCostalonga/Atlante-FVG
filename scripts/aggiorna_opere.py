#!/usr/bin/env python3
"""Aggiorna le opere pubbliche dei comuni del Friuli Venezia Giulia dai dati aperti OpenCUP.

OpenCUP (Presidenza del Consiglio dei ministri, Dipartimento per la programmazione e il coordinamento
della politica economica) pubblica ogni mese tutti i CUP (Codici unici di progetto) per area geografica.
Lo script scarica l'archivio del Nord Est (circa 900 MB), lo legge in flusso senza estrarlo, tiene solo
le righe del Friuli Venezia Giulia (codice regione 06) con natura «Realizzazione di lavori pubblici»
(codice 03) e ne ricava:

- il foglio d'archivio `Opere_pubbliche_OpenCUP`, una riga per progetto e comune;
- per ogni comune, dentro `const EXTRA` di index.html, il riepilogo per la scheda e la mappa.

Un progetto compare più volte nei file OpenCUP quando ha più fonti di finanziamento o più comuni: qui resta
una riga per progetto e comune, con le fonti unite. Nei totali di un comune entrano solo i progetti decisi negli ultimi cinque anni
(in OpenCUP «attivo» vuol dire solo «non chiuso», e molti progetti vecchi restano aperti) e solo quelli localizzati
in quel comune soltanto, perché OpenCUP non dice come dividere il costo fra più comuni.

Usa solo la libreria standard di Python. Se il download fallisce o i dati non sono plausibili, non cambia nulla.
Uso: python scripts/aggiorna_opere.py [archivio zip già scaricato]
"""
import base64, collections, csv, gzip, html, io, json, math, re, sys, tempfile, time, urllib.request, zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINA = RADICE / 'index.html'
DATI = RADICE / 'dati'
FOGLIO = 'Opere_pubbliche_OpenCUP'
DETTAGLIO = 'https://www.opencup.gov.it/portale/web/opencup/dettaglio-opendata-nord-est'
UA = {'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/)'}
RIGHE_PER_FILE = 20000
COLONNE = ['Comune', 'CUP', 'Descrizione', 'Anno della decisione', 'Stato', 'Costo (euro)', 'Finanziamento (euro)', 'Settore',
           'Categoria', 'Copertura finanziaria', 'Soggetto titolare', 'Comuni coinvolti', 'Data del CUP']
MESI = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}


def scarica(url, dest=None):
    errore = None
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
                if dest is None:
                    return r.read()
                with open(dest, 'wb') as f:
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            return dest
                        f.write(b)
        except Exception as e:  # rete instabile: riprova
            errore = e
            time.sleep(20 * (tentativo + 1))
    raise errore


def numero(s):
    try:
        return float(str(s).replace(',', '.'))
    except ValueError:
        return None


def data_cup(s):
    m = re.match(r'(\d{1,2})-([A-Z]{3})-(\d{4})$', s or '')
    return f'{m.group(3)}-{MESI.get(m.group(2), "01")}-{int(m.group(1)):02d}' if m else (s or '')


# caratteri Windows (virgolette e apostrofi tipografici) arrivati come codici di controllo
SOSTITUZIONI = str.maketrans({'\x91': '‘', '\x92': '’', '\x93': '“', '\x94': '”', '\x96': '-', '\x97': '-', '\x85': '…', '\x80': '€'})


def pulisci(s):
    return re.sub(r'\s+', ' ', (s or '').translate(SOSTITUZIONI)).strip()


def riga_js(testo, nome):
    m = re.search(r'^const %s = (.*);$' % nome, testo, re.M)
    if not m:
        raise SystemExit(f'Riga const {nome} non trovata in index.html')
    return m, json.loads(m.group(1))


def main():
    testo = PAGINA.read_text(encoding='utf-8')
    m_man, man = riga_js(testo, 'MAN')
    _, db = riga_js(testo, 'DB')
    m_ex, extra = riga_js(testo, 'EXTRA')
    indice = {c: i for i, c in enumerate(man['istat'])}
    residenti = {c['id']: c.get('p25') for c in db['c']}

    try:
        pagina = scarica(DETTAGLIO).decode('utf-8', 'replace')
        aggiornati = re.search(r'aggiornati al:\s*(?:<[^>]*>\s*)*(\d{4}-\d{2}-\d{2})', pagina)
        aggiornati = aggiornati.group(1) if aggiornati else ''
        if len(sys.argv) > 1:
            archivio = sys.argv[1]
        else:
            link = re.search(r'href="([^"]*OpendataCsvNordEst\.zip[^"]*)"', pagina)
            if not link:
                raise ValueError('collegamento all\'archivio del Nord Est non trovato')
            archivio = scarica(html.unescape(link.group(1)), Path(tempfile.gettempdir()) / 'opencup_nordest.zip')
        z = zipfile.ZipFile(archivio)
    except Exception as e:
        print(f'Opere pubbliche: dati non aggiornati ({e}). Resta la versione precedente.')
        return

    csv.field_size_limit(10 ** 8)
    progetti = {}  # (cup, comune) -> riga
    comuni_cup = collections.defaultdict(set)
    for nome in sorted(n for n in z.namelist() if n.lower().endswith('.csv')):
        with z.open(nome) as f:
            r = csv.reader(io.TextIOWrapper(f, encoding='utf-8', errors='replace', newline=''), delimiter=';')
            h = next(r)
            I = {k: h.index(k) for k in ['CUP', 'CODICE_REGIONE', 'CODICE_NATURA_INTERVENTO', 'CODICE_COMUNE', 'DESCRIZIONE_INTERVENTO', 'DESCRIZIONE_SINTETICA_CUP',
                                         'ANNO_DECISIONE', 'STATO_PROGETTO', 'COSTO_PROGETTO', 'FINANZIAMENTO_PROGETTO', 'SETTORE_INTERVENTO', 'CATEGORIA_INTERVENTO',
                                         'COPERTURA_FINANZIARIA', 'SOGGETTO_TITOLARE', 'DATA_GENERAZIONE_CUP']}
            for row in r:
                if len(row) < len(h) or row[I['CODICE_REGIONE']] != '06' or row[I['CODICE_NATURA_INTERVENTO']] != '03':
                    continue
                cup, com = row[I['CUP']], row[I['CODICE_COMUNE']]
                comuni_cup[cup].add(com)
                chiave = (cup, com)
                if chiave in progetti:
                    progetti[chiave]['cop'].add(pulisci(row[I['COPERTURA_FINANZIARIA']]))
                    continue
                descr = pulisci(row[I['DESCRIZIONE_INTERVENTO']]) or pulisci(row[I['DESCRIZIONE_SINTETICA_CUP']].split('*')[0])
                progetti[chiave] = {'cup': cup, 'com': com, 'descr': descr, 'anno': row[I['ANNO_DECISIONE']], 'stato': pulisci(row[I['STATO_PROGETTO']]),
                                    'costo': numero(row[I['COSTO_PROGETTO']]), 'fin': numero(row[I['FINANZIAMENTO_PROGETTO']]),
                                    'sett': pulisci(row[I['SETTORE_INTERVENTO']]), 'cat': pulisci(row[I['CATEGORIA_INTERVENTO']]),
                                    'cop': {pulisci(row[I['COPERTURA_FINANZIARIA']])}, 'tit': pulisci(row[I['SOGGETTO_TITOLARE']]),
                                    'data': data_cup(row[I['DATA_GENERAZIONE_CUP']])}
    n_cup = len(comuni_cup)
    nel_fvg = sum(1 for p in progetti.values() if p['com'] in indice)
    if n_cup < 20000 or nel_fvg < 20000:
        print(f'Opere pubbliche: dati sospetti ({n_cup} progetti, {nel_fvg} righe con comune). Resta la versione precedente.')
        return

    # foglio d'archivio
    nomi = {c['id']: c['n'] for c in db['c']}
    elenco = sorted(progetti.values(), key=lambda p: (nomi.get(p['com'], 'zzz'), -(int(p['anno']) if p['anno'].isdigit() else 0), p['cup']))
    righe, chiavi = [], []
    for p in elenco:
        n_com = len([c for c in comuni_cup[p['cup']] if c != '-1'])
        righe.append([nomi.get(p['com'], 'Più comuni o non indicato'), p['cup'], p['descr'], int(p['anno']) if p['anno'].isdigit() else p['anno'],
                      p['stato'].capitalize(), p['costo'], p['fin'], p['sett'].capitalize(), p['cat'].capitalize(),
                      ', '.join(sorted(c.lower() for c in p['cop'] if c)), p['tit'], n_com or None, p['data']])
        chiavi.append(indice.get(p['com'], -1))
    for vecchio in DATI.glob(f'{FOGLIO}_*.txt'):
        vecchio.unlink()
    files = []
    for n, a in enumerate(range(0, len(righe), RIGHE_PER_FILE)):
        payload = {'rows': righe[a:a + RIGHE_PER_FILE], 'k': chiavi[a:a + RIGHE_PER_FILE]}
        dati = gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode(), 9, mtime=0)
        fn = f'dati/{FOGLIO}_{n}.txt'
        (RADICE / fn).write_text(base64.b64encode(dati).decode())
        files.append(fn)
    voce = {'id': FOGLIO, 'ambito': 'Governo e settore pubblico', 'righe': len(righe), 'cols': COLONNE,
            'descr': 'Lavori pubblici con CUP (Codice unico di progetto) localizzati in Friuli Venezia Giulia: descrizione, anno della decisione, '
                     'stato, costo e finanziamento, settore, fonti di copertura, ente titolare. Una riga per progetto e comune; '
                     '«Comuni coinvolti» indica su quanti comuni insiste il progetto. Valori in euro.',
            'fonte': f'OpenCUP, Presidenza del Consiglio dei ministri (DIPE), open data Nord Est aggiornati al {aggiornati or "ultimo rilascio"}, licenza CC BY 4.0',
            'cons': time.strftime('%Y-%m-%d'), 'files': files, 'coll': 'colonna: Comune'}
    man['manifest'] = [f for f in man['manifest'] if f['id'] != FOGLIO] + [voce]
    conteggi = collections.Counter(k for k in chiavi if k >= 0)
    man['conteggi'][FOGLIO] = {str(k): v for k, v in conteggi.items()}

    # riepilogo per comune
    anno_rif = int(time.strftime('%Y'))
    per_com = collections.defaultdict(list)
    for p in progetti.values():
        if p['com'] in indice:
            per_com[p['com']].append(p)
    for istat, i in indice.items():
        lista = per_com.get(istat, [])
        attivi = [p for p in lista if p['stato'] == 'ATTIVO']
        # «attivo» in OpenCUP vuol dire solo «non chiuso»: per i totali contano i progetti decisi negli ultimi cinque anni
        recenti = [p for p in lista if p['anno'].isdigit() and int(p['anno']) >= anno_rif - 4]
        solo = [p for p in recenti if len(comuni_cup[p['cup']] - {'-1'}) == 1 and p['costo']]
        costo = sum(p['costo'] for p in solo)
        top = sorted(solo, key=lambda p: -p['costo'])[:6]
        e = extra['E'].setdefault(str(i), {})
        for vecchia in ('opC', 'opAb', 'opMulti'):
            e.pop(vecchia, None)
        e['opA'] = len(attivi)
        e['opR'] = len(recenti)
        e['opRC'] = round(costo)
        e['opRAb'] = round(costo / residenti[istat], 1) if residenti.get(istat) else None
        e['opRMulti'] = len(recenti) - len(solo) - len([p for p in recenti if len(comuni_cup[p['cup']] - {'-1'}) == 1 and not p['costo']])
        e['opTop'] = [[p['descr'][:160], int(p['anno']), round(p['costo']), p['sett'].capitalize(), p['stato'].capitalize(), p['cup']] for p in top]
    extra['opere'] = {'aggiornati': aggiornati, 'annoRecenti': anno_rif - 4}

    testo = testo[:m_ex.start(1)] + json.dumps(extra, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + testo[m_ex.end(1):]
    m_man, _ = riga_js(testo, 'MAN')
    testo = testo[:m_man.start(1)] + json.dumps(man, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + testo[m_man.end(1):]
    PAGINA.write_text(testo, encoding='utf-8')
    attivi_tot = sum(1 for p in progetti.values() if p['stato'] == 'ATTIVO' and p['com'] in indice)
    print(f'Opere pubbliche: {n_cup} progetti, {len(righe)} righe per comune, {attivi_tot} attivi; dati OpenCUP aggiornati al {aggiornati}.')


if __name__ == '__main__':
    main()
