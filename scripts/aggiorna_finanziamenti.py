#!/usr/bin/env python3
"""Archivio dei vantaggi economici concessi dalla Regione e dagli enti del Friuli Venezia Giulia (Amministrazione trasparente).

Fonte: https://amministrazionetrasparente.regione.fvg.it/AmministrazioneTrasparente/ricerca.html, sezione «Concessione e
attribuzione di vantaggi economici» (articoli 26 e 27 del decreto legislativo 33/2013; legge regionale 7/2014, articolo 7).
Il portale raccoglie gli atti di concessione della Regione e di altri enti (Comuni, aziende sanitarie, ERSA, FVG Plus, Consiglio
regionale...) e offre l'esportazione in CSV per intervallo di date di pubblicazione: lo script la usa a finestre di dieci
giorni (il server rifiuta intervalli lunghi), con una pausa fra una richiesta e l'altra, e conserva in una cartella di lavoro
le esportazioni grezze.

Che cosa si tiene di ogni riga (una riga = un beneficiario in un atto): ente che ha adottato l'atto, tipo di beneficiario,
beneficiario, codice fiscale o partita IVA (solo per le persone giuridiche), oggetto, CIG, CUP, importo concesso («Importo
vantaggio»), importo erogato, tipo di atto, norma a base della concessione, collegamenti al bando e all'atto, struttura
competente, modalità di individuazione del beneficiario, date, estremi dell'atto. Per le persone fisiche il nome e il codice
fiscale non vengono ripubblicati: resta «persona fisica», con l'importo e l'ente.

Fasi: la fonte distingue l'importo concesso dall'importo erogato; non pubblica stanziamenti o impegni, e lo script non li
deduce. Territorio: si attribuisce un comune solo con un criterio documentato (ente concedente = Comune; CUP presente in
OpenCUP e localizzato in un solo comune; comune nominato nell'oggetto), mai dalla sede del beneficiario. Settore: dalla
struttura competente e dall'ente, con parole chiave dichiarate. Gli atti con più beneficiari restano collegati dalla chiave
dell'atto (ente, anno, numero), così i totali non li contano due volte.

Controlli: righe duplicate (stessa chiave), importi non numerici, date non valide, estremi mancanti; tutto è registrato
nell'indice (`controlli`) e nel registro degli errori. Se il portale non risponde, restano i dati di prima e l'indice lo dice.

Uscita: dati/fin/AAAA-MM.txt (un file per mese di pubblicazione, JSON compresso e codificato come gli altri fogli) e
dati/finanziamenti_indice.json (mesi, totali, enti, controlli, errori, data della lettura).
Uso: python scripts/aggiorna_finanziamenti.py [--da AAAA-MM-GG] [--a AAAA-MM-GG] [--cache cartella]
     Senza argomenti rilegge gli ultimi 40 giorni (gli atti possono essere pubblicati o aggiornati con ritardo) e aggiunge.
     --solo-cache: usa soltanto le esportazioni già nella cartella di lavoro, senza interrogare il portale.
"""
import base64, csv, datetime, gzip, hashlib, io, json, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CARTELLA = RADICE / 'dati' / 'fin'
INDICE = RADICE / 'dati' / 'finanziamenti_indice.json'
URL = 'https://amministrazionetrasparente.regione.fvg.it/AmministrazioneTrasparente/exportCsv.html'
RICERCA = 'https://amministrazionetrasparente.regione.fvg.it/AmministrazioneTrasparente/ricerca.html'
UA = 'Mozilla/5.0 (compatible; AtlanteFVG/1.0; +https://atlantefvg.it/; info@atlantefvg.it)'
PASSO = 10
PAUSA = 2
SOLO_CACHE = '--solo-cache' in sys.argv  # usa solo le esportazioni già scaricate, senza interrogare il portale
COLONNE = ['id', 'atto', 'ente', 'tipoBeneficiario', 'beneficiario', 'cf', 'oggetto', 'cig', 'cup', 'concesso', 'erogato', 'tipoAtto', 'norma', 'linkBando', 'linkAtto', 'struttura',
           'modalita', 'pubblicato', 'aggiornato', 'annoAtto', 'numeroAtto', 'progetto', 'settore', 'territorio', 'territorioCriterio', 'comuneIstat']
SETTORI = [('Salute e sociale', r'salute|sociali|disabilit|sanitari|asu ?gi|asufc|asfo|welfare|assistenza|famigli|dote|carta famiglia|minori|anziani|caregiver|bonus'), ('Lavoro, formazione e istruzione', r'lavoro|formazione|istruzione|famiglia|impiego|scuol|universit|borse'),
           ('Cultura e sport', r'cultura|sport|spettacolo|biblioteca|museo|turismo culturale'), ('Ambiente ed energia', r'ambiente|energia|sostenibil|rifiuti|bonific'),
           ('Agricoltura, foreste e pesca', r'agro|agricol|forest|ittic|rurale|ersa|feasr|pesca|montagna'), ('Attività produttive e turismo', r'attivit.* produttive|turismo|commercio|cooperazione|imprese|artigian|industria|promoturismo'),
           ('Infrastrutture, territorio e trasporti', r'infrastrutture|territorio|motorizzazione|trasport|lavori pubblici|edilizia|viabilit|urbanistic'), ('Casa', r'casa|abitativ|alloggi|ater\b|edilizia residenziale|fvg plus|affitt|locazion'),
           ('Autonomie locali e sicurezza', r'autonomie locali|funzione pubblica|sicurezza|immigrazione|protezione civile|polizia locale'), ('Istituzioni e organizzazione', r'consiglio regionale|gabinetto|segretariato|finanze|patrimonio|demanio|sistemi informativi|affari generali|direzione generale')]


def scarica(a, b, cache):
    """CSV grezzo per l'intervallo di date di pubblicazione [a, b]; dalla cache se già scaricato."""
    f = cache / f'{a:%Y%m%d}_{b:%Y%m%d}.csv'
    if f.exists() and f.stat().st_size > 400:
        return f.read_bytes()
    if SOLO_CACHE:
        raise RuntimeError(f'finestra {a}-{b} non in cache')
    dati = urllib.parse.urlencode({'numeroAtto': '', 'annoAtto': '', 'pStr': '0', 'beneficiario': '', 'dataDa': a.strftime('%d/%m/%Y'), 'dataA': b.strftime('%d/%m/%Y'), 'stins': 'P', 'codiceGruppo': 'VANTAGGIO',
                                   'frontEnd': 'ente', 'ordinamentoSel': '1', 'tipoSoggetto': '', 'incarichiCessati': '', 'codiceTipoAtto': '', 'operazione': 'esporta'}).encode()
    for tentativo in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, data=dati, headers={'User-Agent': UA}), timeout=400) as r:
                b2 = r.read()
            if b2[:4].lower() == b'ente':
                f.write_bytes(b2); return b2
        except Exception as e:  # il server rifiuta gli intervalli pesanti con un errore 502: si riprova e poi si spezza
            errore = e
        time.sleep(PAUSA * 2)
    raise RuntimeError(f'esportazione non riuscita per {a}-{b}')


def finestre(da, a, cache):
    """Tutte le righe grezze fra due date, a finestre di dieci giorni, spezzate a cinque se il server rifiuta."""
    righe, problemi, d = [], [], da
    while d <= a:
        e = min(d + datetime.timedelta(days=PASSO - 1), a)
        try:
            righe.append(scarica(d, e, cache))
        except RuntimeError:
            for k in range(0, PASSO, 5):
                d2 = d + datetime.timedelta(days=k)
                if d2 > e:
                    break
                e2 = min(d2 + datetime.timedelta(days=4), e)
                try:
                    righe.append(scarica(d2, e2, cache))
                except RuntimeError as err:
                    problemi.append(str(err))
                time.sleep(PAUSA)
        d = e + datetime.timedelta(days=1); time.sleep(PAUSA)
    return righe, problemi


def numero(s):
    s = (s or '').strip().replace('€', '').replace('.', '').replace(' ', '')
    if not s:
        return None
    try:
        return round(float(s.replace(',', '.')), 2)
    except ValueError:
        return 'errore'


def data_iso(s):
    m = re.fullmatch(r'(\d{2})/(\d{2})/(\d{4})', (s or '').strip())
    if not m:
        return None
    try:
        return datetime.date(int(m[3]), int(m[2]), int(m[1])).isoformat()
    except ValueError:
        return None


def pulisci(s):
    return re.sub(r'\s+', ' ', (s or '').replace('¿', "'")).strip()


def settore_di(ente, struttura, oggetto):
    t = (ente + ' ' + struttura).lower()
    for nome, rx in SETTORI:
        if re.search(rx, t):
            return nome
    for nome, rx in SETTORI:
        if re.search(rx, oggetto.lower()):
            return nome
    return 'Altro'


def territorio_di(ente, oggetto, cup, cup_comuni, nomi):
    """Comune collegato solo con un criterio documentato; altrimenti l'ambito resta dichiarato come non indicato."""
    m = re.match(r"^\s*COMUNE DI ([A-Z' .-]+)$", ente.upper())
    if m:
        nome = m.group(1).strip().title().replace("'", "'")
        k = nomi.get(norm(nome))
        if k:
            return k[0], 'ente concedente: il Comune stesso', k[1]
    if cup and cup in cup_comuni:
        c = cup_comuni[cup]
        if c['n'] == 1:
            return c['comune'], 'CUP localizzato in questo comune in OpenCUP', c['istat']
        return f"{c['n']} comuni (CUP sovracomunale)", 'CUP localizzato in più comuni in OpenCUP: importo non ripartito', None
    m = re.search(r"\b(?:nel |del |di |a )?comune di ([A-ZÀ-Ü][a-zà-ü']+(?: [A-ZÀ-Ü][a-zà-ü']+){0,3})", oggetto)
    if m:
        k = nomi.get(norm(m.group(1)))
        if k:
            return k[0], "comune nominato nell'oggetto dell'atto", k[1]
    if re.search(r'\bregional|regione|fvg|friuli venezia giulia\b', ente.lower()):
        return 'Ambito regionale o non indicato', 'l\'atto non indica un comune: ente regionale', None
    return 'Ambito non indicato', 'l\'atto non indica un comune', None


def norm(s):
    import unicodedata
    return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower())


def comuni_e_cup():
    """Nomi dei comuni (per il riconoscimento) e comuni dei CUP già noti dal foglio delle opere pubbliche."""
    testo = (RADICE / 'index.html').read_text(encoding='utf-8')
    db = json.loads(re.search(r'^const DB = (.*);$', testo, re.M).group(1))
    nomi = {norm(c['n']): (c['n'], c['id']) for c in db['c']}
    for c in db['c']:
        for alt in str(c.get('ml', '')).split('/'):
            nomi.setdefault(norm(alt), (c['n'], c['id']))
    cup = {}
    for f in sorted((RADICE / 'dati').glob('Opere_pubbliche_OpenCUP_*.txt')):
        d = json.loads(gzip.decompress(base64.b64decode(f.read_text())))
        for r in d['rows']:
            if r[1] not in cup:
                cup[r[1]] = {'comune': r[0], 'n': r[11] or 1, 'istat': None}
    istat = {c['n']: c['id'] for c in db['c']}
    for v in cup.values():
        v['istat'] = istat.get(v['comune'])
    return nomi, cup


def leggi_righe(grezzi, nomi, cup_comuni, errori):
    out = {}; lette = 0
    for b in grezzi:
        testo = b.decode('cp1252', 'replace')
        lettore = csv.reader(io.StringIO(testo), delimiter=';')
        try:
            h = next(lettore)
        except StopIteration:
            continue
        if 'ente' not in h or 'data pubblicazione' not in h:  # esportazione vuota o pagina di errore: non è un CSV della fonte
            errori.append({'tipo': 'esportazione senza intestazione valida', 'ente': '', 'valore': (h[0] if h else '')[:60]}); continue
        # l'intestazione ha 66 nomi ma le righe 69 campi: i primi 57 si allineano dall'inizio, gli ultimi 9 (date, note, estremi) dalla fine
        n_fine = 9
        for riga in lettore:
            if len(riga) < len(h):
                continue
            lette += 1
            r = {k: riga[i] for i, k in enumerate(h[:len(h) - n_fine])}
            r.update({k: riga[len(riga) - n_fine + i] for i, k in enumerate(h[len(h) - n_fine:])})
            g = lambda k: pulisci(r.get(k) or '')
            ente, benef, tipoB = g('ente'), g('beneficiario'), g('tipo beneficiario')
            anno, num = g('Estremi atto: anno'), g('Estremi atto: numero')
            cf = g('dati fiscali').strip('="')
            pubbl = data_iso(g('data pubblicazione'))
            if not ente or not pubbl:
                errori.append({'tipo': 'riga incompleta', 'ente': ente, 'beneficiario': benef[:60], 'pubblicato': g('data pubblicazione')}); continue
            concesso, erogato = numero(g('Importo vantaggio')), numero(g('importo erogato'))
            if concesso == 'errore' or erogato == 'errore':
                errori.append({'tipo': 'importo non numerico', 'ente': ente, 'atto': f'{num}/{anno}', 'valore': g('Importo vantaggio') or g('importo erogato')}); concesso = None if concesso == 'errore' else concesso; erogato = None if erogato == 'errore' else erogato
            if not anno or not num:
                errori.append({'tipo': 'estremi dell\'atto mancanti', 'ente': ente, 'beneficiario': benef[:60], 'pubblicato': pubbl})
            atto = hashlib.sha1(f'{ente}|{anno}|{num}'.encode()).hexdigest()[:10]
            chiave = hashlib.sha1(f'{ente}|{anno}|{num}|{cf}|{benef}|{g("oggetto")[:120]}|{concesso}|{erogato}'.encode()).hexdigest()[:12]
            if chiave in out:
                continue  # stessa riga esportata in due finestre o pubblicata due volte: si tiene una volta
            fisica = tipoB.lower() == 'persona fisica'
            terr, crit, istat = territorio_di(ente, g('oggetto'), g('cup'), cup_comuni, nomi)
            out[chiave] = [chiave, atto, ente, tipoB or None, 'persona fisica (nome non ripubblicato)' if fisica else benef, None if fisica else (cf or None), g('oggetto')[:600], g('cig') or None, g('cup') or None,
                           concesso, erogato, g('tipo atto') or None, g('norma/titolo a base della concessione')[:300] or None, (g('bando: link') or g('bando: file'))[:300] or None,
                           (g('atto di concessione: link') or g('atto di concessione: file') or g('provvedimento: link') or g('provvedimento: file'))[:300] or None, g('struttura competente')[:200] or None,
                           g('modalità di individuazione del soggetto')[:300] or None, pubbl, data_iso(g('data ultimo aggiornamento')), anno or None, num or None, g('progetto')[:400] or None,
                           settore_di(ente, g('struttura competente'), g('oggetto')), terr, crit, istat]
    return out, lette


def scrivi_mese(mese, righe):
    CARTELLA.mkdir(parents=True, exist_ok=True)
    payload = {'cols': COLONNE, 'rows': righe}
    (CARTELLA / f'{mese}.txt').write_text(base64.b64encode(gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode(), 9, mtime=0)).decode())


def leggi_mese(mese):
    f = CARTELLA / f'{mese}.txt'
    return json.loads(gzip.decompress(base64.b64decode(f.read_text())))['rows'] if f.exists() else []


def main():
    arg = sys.argv[1:]
    oggi = datetime.date.today()
    da = datetime.date.fromisoformat(arg[arg.index('--da') + 1]) if '--da' in arg else oggi - datetime.timedelta(days=40)
    a = datetime.date.fromisoformat(arg[arg.index('--a') + 1]) if '--a' in arg else oggi
    cache = Path(arg[arg.index('--cache') + 1]) if '--cache' in arg else Path('/tmp/atlante_finanziamenti'); cache.mkdir(parents=True, exist_ok=True)
    indice = json.loads(INDICE.read_text(encoding='utf-8')) if INDICE.exists() else {'mesi': {}, 'errori': []}
    nomi, cup_comuni = comuni_e_cup()
    grezzi, problemi = finestre(da, a, cache)
    # le finestre che il portale non ha servito in passato si ritentano poco alla volta a ogni giro
    arretrate = []
    for p in indice.get('finestreNonScaricate', [])[:12]:
        m = re.search(r'(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})', p)
        if not m:
            continue
        try:
            grezzi.append(scarica(datetime.date.fromisoformat(m.group(1)), datetime.date.fromisoformat(m.group(2)), cache)); arretrate.append(p)
        except RuntimeError:
            problemi.append(p)
        time.sleep(PAUSA)
    problemi += [p for p in indice.get('finestreNonScaricate', [])[12:]]
    if not grezzi:
        indice['ultimaLettura'] = {'data': oggi.isoformat(), 'esito': 'fonte non raggiungibile: dati non aggiornati', 'problemi': problemi[:20]}
        INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('Finanziamenti: il portale non ha risposto, restano i dati di prima.'); return 0
    errori = []
    nuove, lette = leggi_righe(grezzi, nomi, cup_comuni, errori)
    # unione con i mesi già salvati: le righe nuove sostituiscono quelle con la stessa chiave
    per_mese = {}
    for chiave, r in nuove.items():
        per_mese.setdefault(r[17][:7], {})[chiave] = r
    n_nuove = 0
    for mese, righe in per_mese.items():
        vecchie = {r[0]: r for r in leggi_mese(mese)}
        prima = len(vecchie); vecchie.update(righe); n_nuove += len(vecchie) - prima
        lista = sorted(vecchie.values(), key=lambda r: (r[17], r[2], r[1]), reverse=True)
        scrivi_mese(mese, lista)
    # indice: mesi, totali per ente e anno, enti, settori, controlli
    mesi, enti, settori, tot = {}, {}, {}, {'concesso': 0.0, 'erogato': 0.0, 'righe': 0, 'atti': set()}
    for f in sorted(CARTELLA.glob('*.txt')):
        righe = leggi_mese(f.stem)
        mesi[f.stem] = {'righe': len(righe), 'concesso': round(sum(r[9] or 0 for r in righe), 2), 'erogato': round(sum(r[10] or 0 for r in righe), 2), 'atti': len({r[1] for r in righe})}
        for r in righe:
            e = enti.setdefault(r[2], {'righe': 0, 'concesso': 0.0, 'erogato': 0.0, 'anni': {}}); e['righe'] += 1; e['concesso'] += r[9] or 0; e['erogato'] += r[10] or 0
            ea = e['anni'].setdefault(r[17][:4], {'righe': 0, 'concesso': 0.0, 'erogato': 0.0}); ea['righe'] += 1; ea['concesso'] += r[9] or 0; ea['erogato'] += r[10] or 0
            s = settori.setdefault(r[22], {'righe': 0, 'concesso': 0.0}); s['righe'] += 1; s['concesso'] += r[9] or 0
            tot['concesso'] += r[9] or 0; tot['erogato'] += r[10] or 0; tot['righe'] += 1; tot['atti'].add(r[1])
    for e in enti.values():
        e['concesso'] = round(e['concesso'], 2); e['erogato'] = round(e['erogato'], 2)
        for ea in e['anni'].values():
            ea['concesso'] = round(ea['concesso'], 2); ea['erogato'] = round(ea['erogato'], 2)
    for s in settori.values():
        s['concesso'] = round(s['concesso'], 2)
    tot['concesso'] = round(tot['concesso'], 2); tot['erogato'] = round(tot['erogato'], 2); tot['atti'] = len(tot['atti'])
    # mesi fra il primo e l'ultimo senza alcun file: il portale non ha risposto per quelle finestre
    chiavi = sorted(mesi); mancanti = []
    if chiavi:
        y, m = int(chiavi[0][:4]), int(chiavi[0][5:7])
        while f'{y:04d}-{m:02d}' <= chiavi[-1]:
            k = f'{y:04d}-{m:02d}'
            if k not in mesi:
                mancanti.append(k)
            m += 1
            if m > 12:
                m = 1; y += 1
    indice.update({'mesiMancanti': mancanti, 'finestreNonScaricate': sorted(set(problemi))[:400],
                   'fonte': RICERCA, 'generato': oggi.isoformat(), 'ultimaLettura': {'data': oggi.isoformat(), 'da': da.isoformat(), 'a': a.isoformat(), 'esito': 'letta', 'righeLette': len(nuove), 'righeNuove': n_nuove, 'problemi': problemi[:20]},
                   'mesi': mesi, 'enti': enti, 'settori': settori, 'totali': tot, 'colonne': COLONNE,
                   'controlli': {'righeLetteGrezze': lette, 'duplicatiScartati': max(0, lette - len(errori) - len(nuove)), 'erroriLettura': len(errori)},
                   'errori': (errori[:200] + indice.get('errori', []))[:500],
                   'nota': 'Una riga è un beneficiario in un atto. Importi concessi ed erogati sono quelli pubblicati dalla fonte e si sommano solo fra loro; stanziamenti e impegni non sono pubblicati. Le persone fisiche compaiono senza nome né codice fiscale. Il territorio è attribuito solo con un criterio documentato, mai dalla sede del beneficiario.'})
    INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Finanziamenti: {len(nuove)} righe lette dal {da} al {a}, {n_nuove} nuove; archivio di {tot["righe"]} righe in {len(mesi)} mesi, {len(errori)} righe con problemi, {len(set(problemi))} finestre non scaricate, {len(arretrate)} arretrate recuperate.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
