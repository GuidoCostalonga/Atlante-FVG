"""Estrae tutte le serie dai file Excel dei lotti (qualunque fonte: OMS, OCSE, ONU, FMI, FAOSTAT, data.europa.eu).

Ogni foglio DATI_* ha le 16 colonne comuni (B:Q) e, da R, i campi originali della fonte. Una serie è
identificata da dataset + dimensioni originali (JSON) senza la dimensione territoriale; il territorio è il
codice geografico originale. Per ogni dataset viene scritto un file JSON:

  <uscita>/<lotto>_<dataset>.json  = {"fonte","ds","n","url","agg","lotto","parziale","terr":{cod:{"n","agg"}},
                                      "ind":{chiave:{"n","u","dims","s":{terr:{anno:[val,flag]}}}}}

Uso: python3 estrai_lotti.py <cartella con L03/ L04/ ...> <cartella uscita> [aree_faostat.json] [--lotti=3,4]
Richiede python-calamine (lettura veloce dei file Excel). I fogli DATI_EUROSTAT sono saltati: i dati regionali
Eurostat arrivano dall'API (estrai_eurostat_api.py), più aggiornati.
"""
import glob, json, os, re, sys
from python_calamine import CalamineWorkbook

arg = [a for a in sys.argv[1:] if not a.startswith('--')]
radice, uscita = arg[0], arg[1]
mappa = json.load(open(arg[2])) if len(arg) > 2 else {}
# ISO3 validi per riconoscere il paese nel nome del file: quelli della tabella aree piu' quelli delle cartelle PAESI
iso_validi = set(mappa.values()) | {d for r in [radice] for root, dirs, _ in os.walk(r) if os.path.basename(root) == 'PAESI' for d in dirs if re.match(r'^[A-Z]{3}$', d)}
solo = None
for a in sys.argv[1:]:
    if a.startswith('--lotti='):
        solo = {int(x) for x in a[8:].split(',')}
os.makedirs(uscita, exist_ok=True)

# chiavi del JSON delle dimensioni che indicano il territorio o il tempo, non la serie
GEO = {'Area Code', 'Area Code (M49)', 'REF_AREA', 'SpatialDim', 'SpatialDimType', 'TimeDimType', 'geo',
       'Country Code', 'Country or Area Code', 'ISO3', 'ISO2', 'Area', 'Reporter Country Code', 'Reporter Country Code (M49)',
       'Reporter Countries', 'Recipient Country Code', 'Recipient Country Code (M49)', 'Recipient Country', 'Region/Country/Area'}
# intestazioni dei campi originali da non usare come etichetta
NON_ETICHETTA = re.compile(r'(code|_ID$|^STRUCTURE|^ACTION$|^Year|^Note$|^Unit$|^Area$|^Flag|^Value$|^Observation value|^Time period|'
                           r'^Observation status|^Decimals|^Unit multiplier|^Confidentiality|^Frequency|^Observation comment|'
                           r'^Low$|^High$|^Comments$|^Date$|^Id$|^TimeDim|^ParentLocation|^DataSource|Dim\dType|^Reporter Countries$|'
                           r'^Recipient Country$|^Country$|^Country or Area$|^Region/Country/Area$|^Source$|^Footnotes$|^Reference|'
                           r'^REPYEAR|^Questionnaire|^Statistical operation|^Time period collection|CONF_STATUS|UNIT_MULT|^Donor$|^ISO\d|source|^CTS_|^ObjectId$|footnote|Date|JSON)', re.I)
FONTE_LOTTO = {6: 'UNSD', 7: 'DATA_EUROPA', 8: 'IMF'}  # lotti senza indizi nel JSON delle dimensioni
RUBRICA_DIM = {'DIZ_DIMENSIONI_OMS': ('WHO', 1, 2)}  # foglio: (fonte, colonna codice, colonna descrizione)


def norm(x):
    """Cella letta da calamine: '' -> None, numeri interi -> testo senza decimali."""
    if x is None or x == '':
        return None
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return x


def testo(x):
    return '' if x is None else (str(int(x)) if isinstance(x, float) and x.is_integer() else str(x))


def lotti_presenti():
    out = {}
    for d in sorted(glob.glob(radice + '/L*/')):
        n = int(os.path.basename(d.rstrip('/'))[1:])
        if solo is None or n in solo:
            out[n] = sorted(glob.glob(d + '**/*.xlsx', recursive=True))
    return out


def chiave_file(f, validi=frozenset()):
    """Territorio e tipo dal nome del file o dalla cartella: (chiave ISO3 o None, aggregato?).
    Un token e' preso come ISO3 solo se e' un codice noto (evita di leggere il codice del dataset, es. TCL, come paese)."""
    base = os.path.basename(f)[:-5]
    parti = f.split('/')
    if 'AGGREGATI' in parti:
        return None, True
    if 'PAESI' in parti:
        i = parti.index('PAESI')
        return (parti[i + 1] if re.match(r'^[A-Z]{3}$', parti[i + 1]) else None), False
    tok = base.split('_')
    agg = any(t in ('AGG', 'DEST') for t in tok[1:3]) or 'excluding' in base or 'unspecified' in base
    for t in tok[1:3]:
        if re.match(r'^[A-Z]{3}$', t) and t in validi:
            return t, False
    return None, agg


def etichetta_dims(fonte, dims, extra_val, extra_testa, rubriche):
    """Testo che distingue la serie dentro il dataset: etichette originali dei campi non codice."""
    pezzi = []
    if fonte == 'WHO':
        for k in ('Dim1', 'Dim2', 'Dim3'):
            v = dims.get(k)
            if v:
                pezzi.append(rubriche.get(v, v))
        return pezzi
    for h, v in zip(extra_testa, extra_val):
        if v is None or v == '' or not h or NON_ETICHETTA.search(str(h)):
            continue
        if fonte == 'OECD' and str(h).isupper():  # colonne dei codici SDMX: resta la colonna con l'etichetta
            continue
        s = str(v).strip()
        if s and s not in ('_T', '_Z', 'Not applicable') and s not in pezzi:
            pezzi.append(s)
    return pezzi


for lotto, file in sorted(lotti_presenti().items()):
    out = {}
    rubriche = {}
    n_righe = 0
    for f in file:
        base = os.path.basename(f)[:-5]
        if not re.match(r'^L\d+_', base):
            continue
        iso, agg = chiave_file(f, iso_validi)
        wb = CalamineWorkbook.from_path(f)
        for s in wb.sheet_names:
            if s in RUBRICA_DIM:
                for r in wb.get_sheet_by_name(s).to_python(skip_empty_area=False)[3:]:
                    if len(r) > 3 and r[2] not in ('', None):
                        rubriche[testo(r[2])] = testo(r[3]) or testo(r[2])
        for s in wb.sheet_names:
            if not s.startswith('DATI_') or s == 'DATI_EUROSTAT':
                continue
            fonte = 'WHO' if s == 'DATI_OMS' else None
            foglio = wb.get_sheet_by_name(s).to_python(skip_empty_area=False)
            if len(foglio) < 4:
                continue
            testa = [testo(h) for h in foglio[2][1:]]
            extra_testa = testa[16:]
            for r in foglio[3:]:
                r = [norm(x) for x in r[1:]]
                if not r or r[0] is None:
                    continue
                r += [None] * (16 - len(r))
                codgeo, nomegeo, ds, ds_n, anno, val, _, unita, _, _, _, stato, agg_f, url, dims_j, ident = r[:16]
                if anno is None:
                    continue
                try:
                    anno = int(str(anno)[:4])
                except ValueError:
                    continue
                codgeo = str(codgeo)
                if fonte is None:
                    fonte = 'FAOSTAT' if ('Area Code' in (dims_j or '') or 'Element Code' in (dims_j or '')) else ('OECD' if 'REF_AREA' in (dims_j or '') else FONTE_LOTTO.get(lotto, 'ALTRO'))
                if fonte == 'WHO':  # tutti gli indicatori OMS formano un solo insieme; il codice indicatore entra nella serie
                    cod_ind, nome_ind = str(ds), ds_n
                    ds, ds_n = 'WHO_GHO', 'Global Health Observatory (GHO) data'
                    stato = None
                try:
                    dims = json.loads(dims_j) if dims_j else {}
                except ValueError:
                    dims = {}
                dims_serie = {k: v for k, v in dims.items() if k not in GEO and v not in (None, '')}
                if fonte == 'WHO':
                    dims_serie['Indicator'] = cod_ind
                if unita and 'Unit' not in dims_serie:
                    dims_serie['Unit'] = str(unita)
                chiave = json.dumps(dims_serie, sort_keys=True, ensure_ascii=False)
                d = out.setdefault(str(ds), {'fonte': fonte, 'ds': str(ds), 'n': ds_n, 'url': url, 'agg': str(agg_f or '')[:10], 'lotto': lotto,
                                             'terr': {}, 'ind': {}})
                # chiave del territorio: ISO3 dal nome del file, altrimenti dalla tabella FAOSTAT; gli aggregati e i codici
                # non ISO3 prendono il prefisso della fonte (WHO_AFR, FAOSTAT_5207, ...)
                k = iso or (mappa.get(codgeo) if fonte == 'FAOSTAT' else None) or (codgeo if (fonte != 'FAOSTAT' and not agg and re.match(r'^[A-Z]{3}$', codgeo)) else f'{fonte}_{codgeo}')
                if k not in d['terr']:
                    d['terr'][k] = {'n': nomegeo, 'agg': agg or (fonte == 'FAOSTAT' and not iso and codgeo not in mappa)}
                ind = d['ind'].get(chiave)
                if ind is None:
                    extra_val = r[16:16 + len(extra_testa)]
                    pezzi = etichetta_dims(fonte, dims, extra_val, extra_testa, rubriche)
                    if fonte == 'WHO':
                        pezzi = [nome_ind] + pezzi
                    ind = d['ind'][chiave] = {'n': ' · '.join(pezzi), 'u': str(unita) if unita else '', 'dims': dims_serie,
                                              'cod': cod_ind if fonte == 'WHO' else str(ds), 's': {}}
                v = None
                if val is not None:
                    try:
                        v = float(val)
                    except (TypeError, ValueError):
                        v = None
                ind['s'].setdefault(k, {})[anno] = [v, str(stato) if stato is not None else None]
                n_righe += 1
    for ds, d in out.items():
        with open(os.path.join(uscita, f'L{lotto:02d}_{re.sub(r"[^A-Za-z0-9_-]+", "_", ds)}.json'), 'w') as fh:
            json.dump(d, fh, ensure_ascii=False, separators=(',', ':'))
    print(f'lotto {lotto}: {len(file)} file, {n_righe} righe, dataset: ' + ', '.join(f"{ds} ({len(d['ind'])} serie, {len(d['terr'])} territori)" for ds, d in out.items()), flush=True)
