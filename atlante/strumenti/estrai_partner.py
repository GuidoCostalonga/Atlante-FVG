"""Estrae le matrici bilaterali FAOSTAT (lotti 19 RFM, 26 EA, 31 TM) in un file compresso per paese.

Lavora a flusso: legge un file Excel alla volta e scrive un paese appena ne ha letto tutte le parti, quindi la memoria
resta quella di un solo paese. Se il file del paese esiste gia' (parti arrivate in un blocco precedente) lo rilegge e
lo completa, cosi' il lotto 31 si puo' trattare a blocchi di archivi.

  <uscita>/<insieme>/<chiave>.json.gz = {"c": chiave, "n": nome originale, "cod": codice FAOSTAT,
      "u": {serie: unita'}, "s": {serie: {partner: [primo anno, [valori], "contrassegni"]}}, "nt": {serie|partner: {anno: nota}}}

  serie     = "<prodotto>|<elemento>" (EA: scopo|flusso_elemento, cioe' Purpose Code | Item Code_Element Code)
  partner   = codice FAOSTAT del paese partner (RFM, TM) o del donatore (EA)
  valori    = uno per anno dal primo anno all'ultimo; null dove la fonte non da' l'anno o non da' un numero
  contrassegni = un carattere per anno: il contrassegno originale della fonte (A, E, I, X, ...), "_" se la riga non ne
              ha, "-" se l'anno manca. Nessuna somma, saldo o stima: ogni valore e' quello della riga originale.

La chiave del file e' l'ISO3 della tabella aree_faostat.json, altrimenti FAO_<codice> (aggregati statistici e
destinatari o dichiaranti non classificati). Gzip livello 9 con data azzerata: lo stesso ingresso da' gli stessi byte.

Il catalogo parziale (prodotti, elementi, partner, unita', anni, territori con numero di osservazioni) si accumula in
<catalogo.json> fra un blocco e l'altro; genera_partner.py lo trasforma in dati/partner.json.

Uso: python3 estrai_partner.py <insieme RFM|EA|TM> <cartella con gli Excel> <cartella uscita> <aree_faostat.json> <catalogo.json>
Richiede python-calamine.
"""
import glob, gzip, io, json, os, re, sys
from python_calamine import CalamineWorkbook

insieme, radice, uscita, f_aree, f_cat = sys.argv[1:6]
mappa = json.load(open(f_aree))
cart = os.path.join(uscita, insieme)
os.makedirs(cart, exist_ok=True)
cat = json.load(open(f_cat)) if os.path.exists(f_cat) else {
    'ds': insieme, 'nome': '', 'url': '', 'agg': '', 'prod': {}, 'elem': {}, 'partner': {}, 'anni': [9999, 0], 'terr': {}, 'oss': 0}


def testo(x):
    if x is None:
        return ''
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x).strip()


def chiave_terr(cod):
    return mappa.get(cod) or f'FAO_{cod}'


def gruppo(f):
    """Nome del file senza la parte: le parti dello stesso territorio vanno lette insieme."""
    return re.sub(r'_parte_\d+$', '', os.path.basename(f)[:-5])


def scrivi_gz(percorso, dati):
    buf = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, compresslevel=9, mtime=0) as g:
        g.write(json.dumps(dati, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8'))
    with open(percorso, 'wb') as fh:
        fh.write(buf.getvalue())


def leggi_gz(percorso):
    """Riporta un file gia' scritto alla forma di lavoro {serie: {partner: {anno: (valore, contrassegno)}}}."""
    d = json.loads(gzip.open(percorso).read())
    s = {}
    for k, per in d['s'].items():
        for p, (a0, vals, fl) in per.items():
            s.setdefault(k, {})[p] = {a0 + i: (v, fl[i]) for i, v in enumerate(vals) if fl[i] != '-'}
    nt = {k: {int(a): t for a, t in v.items()} for k, v in d.get('nt', {}).items()}
    return d, s, nt


def compatta(s):
    out = {}
    for k, per in s.items():
        out[k] = {}
        for p, anni in per.items():
            a0, a1 = min(anni), max(anni)
            vals, fl = [], []
            for a in range(a0, a1 + 1):
                if a in anni:
                    v, f = anni[a]
                    vals.append(int(v) if v is not None and float(v).is_integer() else v)
                    fl.append(f)
                else:
                    vals.append(None)
                    fl.append('-')
            out[k][p] = [a0, vals, ''.join(fl)]
    return out


def scrivi_terr(tk, info, s, unita, nt, n_oss):
    percorso = os.path.join(cart, tk + '.json.gz')
    if os.path.exists(percorso):  # parti gia' estratte in un blocco precedente
        vecchio, s0, nt0 = leggi_gz(percorso)
        for k, per in s0.items():
            for p, anni in per.items():
                dest = s.setdefault(k, {}).setdefault(p, {})
                for a, x in anni.items():
                    if a in dest and dest[a] != x:
                        raise SystemExit(f'ERRORE {tk} {k} {p} {a}: due valori diversi per lo stesso anno')
                    dest[a] = x
        for k, u in vecchio.get('u', {}).items():
            if unita.setdefault(k, u) != u:
                raise SystemExit(f'ERRORE {tk} {k}: unita\' diverse')
        for k, v in nt0.items():
            nt.setdefault(k, {}).update(v)
    dati = {'c': tk, 'n': info['n'], 'cod': info['cod'], 'u': unita, 's': compatta(s)}
    if nt:
        dati['nt'] = {k: {str(a): t for a, t in sorted(v.items())} for k, v in nt.items()}
    scrivi_gz(percorso, dati)
    t = cat['terr'].setdefault(tk, {'n': info['n'], 'cod': info['cod'], 'oss': 0, 'agg': info['agg']})
    t['oss'] += n_oss


file = sorted(glob.glob(os.path.join(radice, '**', 'L*_*.xlsx'), recursive=True))
file = [f for f in file if re.match(r'^L\d+_', os.path.basename(f)) and 'Registro' not in f and 'Indice' not in f and 'Dizionari' not in f]
gruppi = {}
for f in file:
    gruppi.setdefault(gruppo(f), []).append(f)

tot = 0
for g, fs in sorted(gruppi.items()):
    s, unita, nt = {}, {}, {}
    info = None
    n_oss = 0
    for f in sorted(fs):
        wb = CalamineWorkbook.from_path(f)
        for nome in wb.sheet_names:
            if not nome.startswith('DATI_'):
                continue
            fo = wb.get_sheet_by_name(nome).to_python(skip_empty_area=False)
            if len(fo) < 4:
                continue
            testa = [testo(h) for h in fo[2]]
            col = {h: i for i, h in enumerate(testa) if h}
            if insieme == 'EA':
                c_par, c_parn = col['Donor Code'], col['Donor']
                c_pro, c_pron = col['Purpose Code'], col['Purpose']
            else:
                c_par, c_parn = col['Partner Country Code'], col['Partner Countries']
                c_pro, c_pron = col['Item Code'], col['Item']
            c_it, c_itn, c_el, c_eln = col['Item Code'], col['Item'], col['Element Code'], col['Element']
            c_nota = col.get('Note')
            for r in fo[3:]:
                if len(r) < 17 or r[1] in ('', None):
                    continue
                cod = testo(r[1])
                anno = testo(r[5])
                if not anno:
                    continue
                anno = int(anno[:4])
                tk = chiave_terr(cod)
                if info is None:
                    info = {'n': testo(r[2]), 'cod': cod, 'agg': cod not in mappa, 'tk': tk}
                    cat['nome'], cat['url'], cat['agg'] = testo(r[4]), testo(r[14]), testo(r[13])[:10]
                elif tk != info['tk']:
                    raise SystemExit(f'ERRORE {f}: piu\' territori nello stesso gruppo ({info["tk"]}, {tk})')
                par, pro = testo(r[c_par]), testo(r[c_pro])
                if insieme == 'EA':
                    el = testo(r[c_it]) + '_' + testo(r[c_el])
                    cat['elem'].setdefault(el, testo(r[c_itn]) + ' · ' + testo(r[c_eln]))
                else:
                    el = testo(r[c_el])
                    cat['elem'].setdefault(el, testo(r[c_eln]))
                cat['prod'].setdefault(pro, testo(r[c_pron]))
                cat['partner'].setdefault(par, testo(r[c_parn]))
                u = testo(r[8])
                k = pro + '|' + el
                if unita.setdefault(k, u) != u:  # stessa serie con un'altra unita': la serie si distingue per unita'
                    k = k + '|' + u
                    unita.setdefault(k, u)
                v = r[6]
                v = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
                fl = testo(r[12])[:1] or '_'
                anni = s.setdefault(k, {}).setdefault(par, {})
                if anno in anni:
                    raise SystemExit(f'ERRORE {f}: {k} {par} {anno} ripetuto')
                anni[anno] = (v, fl)
                if c_nota is not None and len(r) > c_nota and testo(r[c_nota]):
                    nt.setdefault(k + '|' + par, {})[anno] = testo(r[c_nota])
                cat['anni'][0] = min(cat['anni'][0], anno)
                cat['anni'][1] = max(cat['anni'][1], anno)
                n_oss += 1
    if info is None:
        continue
    scrivi_terr(info['tk'], info, s, unita, nt, n_oss)
    tot += n_oss
    cat['oss'] += n_oss
    print(g, n_oss, flush=True)

json.dump(cat, open(f_cat, 'w'), ensure_ascii=False, sort_keys=True, indent=0)
print(f'{insieme}: {len(gruppi)} gruppi, {tot} osservazioni in questo passaggio, {cat["oss"]} in tutto, {len(cat["terr"])} territori', flush=True)
