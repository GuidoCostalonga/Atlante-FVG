"""Scrive dati/partner.json, il catalogo della vista Partner, dai cataloghi parziali di estrai_partner.py.

Riconta le osservazioni direttamente dai file dati/partner/<insieme>/<chiave>.json.gz (non si fida dei contatori
accumulati fra i blocchi), raccoglie unita' e anni effettivi e controlla che ogni territorio del catalogo abbia il suo
file. I nomi dei paesi sono quelli italiani dell'Atlante (dati/meta.json) quando il codice FAOSTAT ha un ISO3;
altrimenti resta il nome originale della fonte. Prodotti, elementi e scopi conservano il nome originale ("en") e hanno
un'etichetta italiana solo per gli elementi e le unita', che sono pochi e fissi.

Uso: python3 genera_partner.py <cartella atlante> <catalogo RFM> <catalogo EA> <catalogo TM>
"""
import glob, gzip, json, os, sys

radice, f_rfm, f_ea, f_tm = sys.argv[1:5]
meta = json.load(open(os.path.join(radice, 'dati/meta.json')))
aree = json.load(open(os.path.join(radice, 'strumenti/aree_faostat.json')))
NOME = {t['id']: t['n'] for t in meta['territori']}
CORREGGI_ISO = {'ADO': 'AND'}  # codice storico di Andorra nella tabella FAOSTAT; la mappa e l'Atlante usano AND

INSIEMI = [
    ('TM', f_tm, 31, 'Commercio di prodotti agricoli per paese partner', 'dichiarante', 'partner', 'prodotto'),
    ('RFM', f_rfm, 19, 'Commercio di fertilizzanti per paese partner', 'dichiarante', 'partner', 'prodotto'),
    ('EA', f_ea, 26, 'Flussi di sviluppo verso l’agricoltura per donatore', 'destinatario', 'donatore', 'scopo'),
]
# etichette italiane degli elementi: traduzione letterale del nome originale, che resta in "en"
EL_IT = {'Import quantity': 'Importazioni, quantità', 'Import value': 'Importazioni, valore',
         'Export quantity': 'Esportazioni, quantità', 'Export value': 'Esportazioni, valore',
         'Import quantity (tonnes N)': 'Importazioni, quantità in tonnellate di azoto (N)',
         'Import quantity (tonnes P)': 'Importazioni, quantità in tonnellate di fosforo (P)',
         'Import quantity (tonnes K)': 'Importazioni, quantità in tonnellate di potassio (K)',
         'Export quantity (tonnes N)': 'Esportazioni, quantità in tonnellate di azoto (N)',
         'Export quantity (tonnes P)': 'Esportazioni, quantità in tonnellate di fosforo (P)',
         'Export quantity (tonnes K)': 'Esportazioni, quantità in tonnellate di potassio (K)'}
FLUSSO_IT = {'Commitment': 'Impegni', 'Disbursement': 'Erogazioni', 'ODA': 'aiuto pubblico allo sviluppo (APS)',
             'OOF': 'altri flussi pubblici', 'Private Grant': 'doni privati', 'Private Sector Instrument': 'strumenti per il settore privato'}
VAL_IT = {'Value US$': 'valore in dollari USA correnti', 'Value US$, 2023 prices': 'valore in dollari USA a prezzi 2023',
          'Share of Total US$': 'quota sul totale', 'Agriculture orientation index US$': 'indice di orientamento all’agricoltura'}
UNITA_IT = {'t': 'tonnellate', '1000 USD': 'migliaia di dollari USA', 'million USD': 'milioni di dollari USA', '%': '%',
            'Head': 'capi', '1000 Head': 'migliaia di capi', 'No': 'numero', 'An': 'animali', '1000 An': 'migliaia di animali', '': 'unità non indicata'}
# descrizioni ufficiali dei contrassegni (file *_Flags.csv di FAOSTAT nei dizionari dei lotti), tradotte
FLAG = {'A': ['valore ufficiale', 'Official value'], 'E': ['valore stimato', 'Estimated value'],
        'I': ['valore imputato da un’agenzia ricevente', 'Value imputed by a receiving agency'],
        'L': ['valore mancante: il dato esiste ma non è stato raccolto', 'Missing value; data exist but were not collected'],
        'X': ['valore di un’organizzazione esterna', 'Value from external organization'],
        '_': ['riga senza contrassegno', '']}


def it_elem(ds, nome):
    if ds != 'EA':
        return EL_IT.get(nome, nome)
    flusso, val = nome.split(' · ', 1)
    base = flusso.split(' ')[0]
    resto = flusso[len(base):].strip()
    testo = FLUSSO_IT.get(base, base) + (', ' + FLUSSO_IT.get(resto, resto) if resto else '')
    return testo + ': ' + VAL_IT.get(val, val)


def iso_di(cod):
    iso = aree.get(cod)
    return CORREGGI_ISO.get(iso, iso) if iso else None


out = {'fonte': 'FAOSTAT (FAO, Organizzazione delle Nazioni Unite per l’alimentazione e l’agricoltura)', 'flag': FLAG,
       'unita': {}, 'insiemi': []}
for ds, f_cat, lotto, nome_it, ruolo, ruolo_p, voce_p in INSIEMI:
    cat = json.load(open(f_cat))
    terr, unita, anni, oss_tot, flag = [], set(), [9999, 0], 0, set()
    for tk, t in sorted(cat['terr'].items(), key=lambda x: x[0]):
        percorso = os.path.join(radice, 'dati/partner', ds, tk + '.json.gz')
        if not os.path.exists(percorso):
            raise SystemExit(f'ERRORE manca {percorso}')
        d = json.loads(gzip.open(percorso).read())
        oss = 0
        for k, per in d['s'].items():
            for p, (a0, vals, fl) in per.items():
                n = sum(1 for c in fl if c != '-')
                oss += n
                flag.update(c for c in fl if c != '-')
                anni[0] = min(anni[0], a0)
                anni[1] = max(anni[1], a0 + len(vals) - 1)
        unita.update(d['u'].values())
        iso = iso_di(t['cod'])
        terr.append([tk, NOME.get(iso, t['n']) if iso else t['n'], t['cod'], oss, 1 if t['agg'] else 0, iso or ''])
        oss_tot += oss
    file_presenti = {os.path.basename(f)[:-8] for f in glob.glob(os.path.join(radice, 'dati/partner', ds, '*.json.gz'))}
    if file_presenti != {t[0] for t in terr}:
        raise SystemExit(f'ERRORE {ds}: file in piu\' o in meno rispetto al catalogo: {sorted(file_presenti ^ {t[0] for t in terr})}')
    partner = {}
    for cod, n in sorted(cat['partner'].items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        iso = iso_di(cod)
        partner[cod] = [NOME.get(iso, n) if iso else n, iso or '', n]
    for u in unita:
        out['unita'][u] = UNITA_IT.get(u, u)
    if flag - set(FLAG):
        raise SystemExit(f'ERRORE {ds}: contrassegni senza descrizione {flag - set(FLAG)}')
    out['insiemi'].append({
        'k': ds, 'lotto': lotto, 'n': nome_it, 'en': cat['nome'], 'url': cat['url'], 'agg': cat['agg'],
        'ruolo': ruolo, 'ruoloPartner': ruolo_p, 'voceProdotto': voce_p,
        'anni': anni, 'oss': oss_tot, 'flag': sorted(flag),
        'prod': {k: v for k, v in sorted(cat['prod'].items(), key=lambda x: x[1].lower())},
        'elem': {k: [it_elem(ds, v), v] for k, v in sorted(cat['elem'].items())},
        'terr': terr, 'partner': partner})
    print(f'{ds}: {len(terr)} territori, {len(partner)} {ruolo_p}, {len(cat["prod"])} {voce_p}, {len(cat["elem"])} elementi, '
          f'anni {anni[0]}–{anni[1]}, {oss_tot} osservazioni, contrassegni {sorted(flag)}', flush=True)

with open(os.path.join(radice, 'dati/partner.json'), 'w') as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
print('unità', out['unita'])
