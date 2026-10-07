#!/usr/bin/env python3
"""Legge l'elenco ufficiale «Bandi e avvisi» della Regione Autonoma Friuli Venezia Giulia e scrive dati/bandi.json.

Fonte: https://www.regione.fvg.it/rafvg/cms/RAFVG/MODULI/bandi_avvisi/ (tutti i bandi e gli avvisi in corso, a cura delle
strutture regionali competenti). Per ogni voce si prendono solo i campi che la pagina riporta: titolo, direzione o struttura,
data di pubblicazione, scadenza (se indicata) e indirizzo della pagina ufficiale. Il filtro «Bandi contenenti misure
contributive», offerto dalla stessa pagina, si legge a parte e diventa il campo `contributi`: è un'indicazione della Regione,
non una classificazione dell'Atlante. Nessun altro dato è dedotto: non si indovinano destinatari, importi o requisiti. Una scadenza del 1° gennaio 1970, che la
Regione usa come segnaposto, vale «scadenza non indicata».

Per ogni voce con pagina sul sito della Regione si legge anche la pagina stessa (`dettaglio`): il testo, i campi con
etichetta che la struttura ha scritto («Destinatari», «Attività finanziabile», «Modalità e termini di presentazione
della domanda», «Requisiti», «Spese ammissibili», «Dotazione», «Contributo», «Riferimenti normativi»), gli allegati con
il formato e la data in cui la pagina è stata letta (`verificato`). Le etichette variano da bando a bando e molti non ne
hanno: in quel caso i campi restano vuoti e la pagina dell'Atlante lo dice. Da titolo e campi si ricavano, con regole
di parole chiave dichiarate nella pagina, i destinatari indicativi, il settore (dalla struttura regionale) e il tipo
(bando con domanda, atto o esito, avviso): sono classificazioni dell'Atlante, segnate come tali.

Il file si riscrive solo se l'elenco cambia (la data `ultima_variazione` è quella del cambiamento). Se la lettura fallisce o
sembra incompleta, i dati di prima restano. Usa solo la libreria standard di Python; fra una richiesta e l'altra aspetta.
Uso: python scripts/aggiorna_bandi.py [cartella con le pagine già scaricate: elenco_N.html, contributi_N.html]
"""
import datetime, hashlib, html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FILE = RADICE / 'dati' / 'bandi.json'
SITO = 'https://www.regione.fvg.it'
ELENCO = SITO + '/rafvg/cms/RAFVG/MODULI/bandi_avvisi/'
RICERCA = ELENCO + 'ricerca.jsp'
UA = {'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/; info@atlantefvg.it)'}
MAX_PAGINE = 40
PAUSA = 0.8
# etichette dei campi che le strutture scrivono nel testo del bando, ricondotte a chiavi comuni
CAMPI = [('destinatari', r'^(destinatari|destinatari del contributo|beneficiari|beneficiari del contributo|soggetti beneficiari|soggetti ammessi|a chi (è|e) rivolto|chi può (partecipare|presentare))'),
         ('attivita', r'^(attivit[àa] finanziabil[ei]|oggetto|finalit[àa]|interventi (finanziabili|ammissibili)|iniziative (finanziabili|ammissibili)|cosa finanzia)'),
         ('requisiti', r'^(requisiti|requisiti di (ammissibilit[àa]|partecipazione|accesso)|condizioni)'),
         ('spese', r'^(spese ammissibili|spese finanziabili|costi ammissibili)'),
         ('dotazione', r'^(dotazione|dotazione finanziaria|risorse( disponibili| finanziarie)?|stanziamento|fondi disponibili)'),
         ('contributo', r'^(contributo|importo del contributo|misura del contributo|intensit[àa] (del contributo|di aiuto)|importo massimo|entit[àa] del contributo)'),
         ('modalita', r'^(modalit[àa] e termini.*|modalit[àa] di presentazione.*|termin[ei] (di |per la )?presentazione.*|presentazione delle domande|scadenza|come (presentare|partecipare).*)'),
         ('norme', r'^(riferimenti normativi|normativa( di riferimento)?|base giuridica)')]
# strutture regionali ricondotte a un settore (etichette dell'Atlante, mostrate come tali)
SETTORI = [('Salute e sociale', r'salute|sociali|disabilit'), ('Lavoro, formazione e istruzione', r'lavoro|formazione|istruzione|famiglia|impiego|collocamento'), ('Cultura e sport', r'cultura|sport'),
           ('Ambiente ed energia', r'ambiente|energia|sostenibil'), ('Agricoltura, foreste e pesca', r'agro|agricol|forest|ittic|rurale|ERSA'), ('Attività produttive e turismo', r'attivit.* produttive|turismo|commercio|cooperazione'),
           ('Infrastrutture, territorio e trasporti', r'infrastrutture|territorio|motorizzazione|trasport|lavori pubblici|edilizia'), ('Autonomie locali e sicurezza', r'autonomie locali|funzione pubblica|sicurezza|immigrazione|protezione civile'),
           ('Finanze, patrimonio e organizzazione', r'finanze|patrimonio|demanio|sistemi informativi|generale|gabinetto|segretariato')]
DESTINATARI = [('comuni', r'\bcomun[ei]\b|enti locali|amministrazioni comunali|unioni'), ('enti', r'enti pubblici|aziende sanitarie|asu|università|scuole|istituti|ater|consorzi|enti del servizio sanitario|pubbliche amministrazioni|camere di commercio'),
               ('associazioni', r'associazion|terzo settore|\bets\b|\bodv\b|\baps\b|volontariato|organizzazioni|fondazion|pro loco|cooperative sociali|parrocchi|enti religiosi|comitati'),
               ('imprese', r'impres|\bpmi\b|aziend|operatori economici|liberi professionisti|società|ditte|esercizi|attività economiche|agricoltori|imprenditori|start'),
               ('cittadini', r'cittadin|persone fisiche|famigli|privati|residenti|nuclei|studenti|lavoratori|disoccupati|giovani|anziani|donne|genitori|persone con disabilit|candidati|laureati|medici')]


def scarica(url, dati=None):
    errore = None
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=dati, headers=UA), timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # rete instabile: riprova
            errore = e; time.sleep(5 * (tentativo + 1))
    raise errore


def pulisci(s):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def data_iso(s):
    m = re.fullmatch(r'(\d{2})\.(\d{2})\.(\d{4})', (s or '').strip())
    if not m:
        return None
    try:
        return datetime.date(int(m[3]), int(m[2]), int(m[1])).isoformat()
    except ValueError:
        return None


def direzione(s):
    # la fonte scrive una volta «disabilita'» senza accento: stessa struttura, stessa voce
    return re.sub(r"disabilita'", 'disabilità', s)


def testo_pulito(frag):
    s = re.sub(r'<(br|/p|/li|/div|/h\d)[^>]*>', '\n', frag)
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s))
    return re.sub(r'\n\s*\n+', '\n', re.sub(r'[ \t\xa0]+', ' ', s)).strip()


def dettaglio(t, letto):
    """Dettaglio di una pagina di bando: testo, campi con etichetta, allegati, servizio, tag della Regione."""
    d = {'verificato': letto, 'campi': {}, 'allegati': [], 'testo': ''}
    m = re.search(r'<div class="box-descrizione">(.*?)<div class="box-documentazione"|<div class="box-descrizione">(.*?)</div>\s*</div>', t, re.S)
    frag = (m.group(1) or m.group(2)) if m else ''
    d['testo'] = testo_pulito(frag)[:4000]
    for p in re.findall(r'<p>(.*?)</p>', frag, re.S):
        tp = testo_pulito(p)
        mm = re.match(r'^([^:\n]{3,80}):\s*(.+)$', tp, re.S)
        if not mm:
            continue
        etichetta, valore = mm.group(1).strip(), mm.group(2).strip()
        for chiave, rx in CAMPI:
            if re.match(rx, etichetta, re.I) and chiave not in d['campi']:
                d['campi'][chiave] = valore[:1500]; break
    for a in re.finditer(r'<a class="file blank" href="([^"]+)"[^>]*>(.*?)</a>(?:&nbsp;|\s)*\[formato \.(\w+)\]', t, re.S):
        href = html.unescape(a.group(1)); d['allegati'].append({'titolo': testo_pulito(a.group(2))[:200], 'url': href if href.startswith('http') else SITO + href, 'formato': a.group(3).lower()})
    sv = re.search(r'<div class="box-campo">(.*?)</div>', t, re.S)
    if sv:
        righe = [r for r in testo_pulito(sv.group(1)).split('\n') if r.strip() and not r.startswith('<!--')]
        if len(righe) > 1:
            d['servizio'] = righe[1][:160]
    d['tag'] = sorted(set(re.findall(r'data-tag-servizio="([^"]+)"', t)))
    return d


def classifica(v):
    """Classificazioni dell'Atlante, da parole chiave dichiarate: destinatari indicativi, settore dalla struttura, tipo dal titolo."""
    c = v.get('dettaglio', {}).get('campi', {})
    base = c.get('destinatari') or ''
    fonte_dest = 'campo' if base else 'titolo'
    testo = (base or (v['titolo'] + ' ' + c.get('attivita', '') + ' ' + c.get('requisiti', ''))).lower()
    dest = [k for k, rx in DESTINATARI if re.search(rx, testo)]
    if v['sezione'] in ('cpi', 'cm'):
        dest = ['cittadini'] if 'cittadini' in dest or not dest else dest; fonte_dest = 'sezione'
    settore = next((s for s, rx in SETTORI if re.search(rx, (v['direzione'] or '').lower())), 'Altro')
    if v['sezione'] in ('cpi', 'cm'):
        settore = 'Lavoro, formazione e istruzione'
    tl = v['titolo'].lower()
    if v['sezione'] in ('cpi', 'cm') and not re.search(r'graduatori|esit[oi]\b|elenco', tl):
        tipo = 'bando'  # offerte e selezioni dei Centri per l'impiego: si presenta candidatura
    elif re.search(r'graduatori|esit[oi]\b|elenco (dei |degli |delle )?(beneficiar|ammess|idone|esclus|domande)|decreto di approvazione|approvazione (della graduatoria|degli elenchi|dell.elenco)|riparto|liquidazion|\bnomin[ae]\b|designazion|rendicontazion|proroga dei termini di rendicont', tl):
        tipo = 'atto'
    elif re.search(r'\bbando\b|avviso pubblico|manifestazione d.interesse|concessione di contribut|contributi (per|a sostegno|a favore|alle|ai|agli)|finanziament|domand[ae]\b|candidatur|selezione|iscrizion|invito|sportello|procedura|concorso', tl) or 'contributi' in (v.get('dettaglio', {}).get('tag') or []):
        tipo = 'bando'
    else:
        tipo = 'avviso'
    comuni = []
    return {'destinatari': dest, 'destinatariDa': fonte_dest, 'settore': settore, 'tipo': tipo}


def voci(t):
    out = []
    for m in re.finditer(r'<div class="box-link box box-bando">(.*?)</a>\s*</div', t, re.S):
        b = m.group(1)
        h = re.search(r'href="([^"#]+)', b)
        ti = re.search(r'<h3>(.*?)</h3>', b, re.S)
        dz = re.search(r'box-campo">\s*(.*?)\s*</div', b, re.S)
        pub = re.search(r'box-header-normal">\s*([\d.]+)', b)
        sc = re.search(r'scadenza</span>\s*<span class="box-header-important">\s*([\d.]+)', b)
        if not (h and ti and pub and data_iso(pub.group(1))):
            raise ValueError("voce dell'elenco con una struttura inattesa: " + pulisci(b)[:120])
        href = html.unescape(h.group(1))
        if href.startswith('/') and '/BANDI/' in href:  # pagina del sito della Regione
            percorso = href.split('?')[0].split(';')[0]
            idv, url = re.sub(r'\.html$', '', percorso.split('/BANDI/', 1)[1]), SITO + percorso
        elif re.match(r'https?://', href):  # sito esterno indicato dalla Regione (per esempio il portale dei bandi di formazione)
            idv, url = 'x-' + hashlib.sha1(href.encode()).hexdigest()[:10], href
        else:
            raise ValueError("indirizzo della voce non riconosciuto: " + href[:100])
        scadenza = data_iso(sc.group(1)) if sc else None
        if scadenza and scadenza < '2000-01-01':  # la Regione usa il 1° gennaio 1970 come segnaposto: equivale a «scadenza non indicata»
            scadenza = None
        v = {'id': idv, 'titolo': pulisci(ti.group(1)), 'direzione': direzione(pulisci(dz.group(1))) if dz else '',
             'pubblicato': data_iso(pub.group(1)), 'scadenza': scadenza, 'url': url}
        sito = urllib.parse.urlparse(url).hostname
        if sito != 'www.regione.fvg.it':
            v['sito'] = sito
        out.append(v)
    return out


def pagine(cartella, prefisso, primo, altri):
    """Tutte le pagine di un elenco: da internet (primo, altri(n)) oppure da una cartella di file già scaricati."""
    tutte, n = [], 1
    while n <= MAX_PAGINE:
        if cartella:
            f = Path(cartella) / f'{prefisso}_{n}.html'
            if not f.exists():
                break
            t = f.read_text(encoding='utf-8')
        else:
            t = primo() if n == 1 else altri(n)
            time.sleep(PAUSA)
        v = voci(t); tutte += v
        if not v or not re.search(r'[?&]pag=%d\b' % (n + 1), t):
            break
        n += 1
    return tutte


def leggi(cartella=None):
    elenco = pagine(cartella, 'elenco', lambda: scarica(ELENCO), lambda n: scarica(f'{ELENCO}?pag={n}'))
    contrib = pagine(cartella, 'contributi',
                     lambda: scarica(RICERCA, urllib.parse.urlencode({'txtChiave': '', 'onlyTagServizio': '1', 'startsearch': 'vai'}).encode()),
                     lambda n: scarica(f'{RICERCA}?txtChiave=&pag={n}&onlyTagServizio=1'))
    ids_contrib = {v['id'] for v in contrib}
    visti, risultato = set(), []
    for v in elenco:
        if v['id'] in visti:
            continue
        visti.add(v['id'])
        v['contributi'] = v['id'] in ids_contrib
        v['sezione'] = 'cpi' if v['direzione'] == "Centri per l'impiego" else 'cm' if v['direzione'] == 'Collocamento mirato' else 'regione'
        risultato.append(v)
    mancano = ids_contrib - visti
    if mancano:  # un bando con misure contributive che non sta nell'elenco generale: si tiene, con i suoi dati
        for v in contrib:
            if v['id'] in mancano:
                visti.add(v['id']); v['contributi'] = True; v['sezione'] = 'regione'; risultato.append(v)
    oggi = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2))).date().isoformat()
    for v in risultato:
        if v.get('sito'):  # pagina su un altro sito della Regione: non si legge, ma la voce si classifica lo stesso
            v['dettaglio'] = {'verificato': oggi, 'campi': {}, 'allegati': [], 'testo': '', 'esterno': True}
            v.update(classifica(v)); continue
        if cartella:
            f = Path(cartella) / ('bando_' + hashlib.sha1(v['id'].encode()).hexdigest()[:12] + '.html')
            pagina = f.read_text(encoding='utf-8') if f.exists() else ''
        else:
            try:
                pagina = scarica(v['url']); time.sleep(PAUSA)
            except Exception as e:
                pagina = ''
        v['dettaglio'] = dettaglio(pagina, oggi) if pagina else {'verificato': None, 'campi': {}, 'allegati': [], 'testo': '', 'nonLetta': True}
        v.update(classifica(v))
    risultato.sort(key=lambda v: (v['pubblicato'], v['id']), reverse=True)
    return risultato


def main():
    try:
        nuove = leggi(sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception as e:
        print(f'Bandi: non aggiornati ({e}). Restano quelli di prima.')
        return 0
    vecchio = json.loads(FILE.read_text(encoding='utf-8')) if FILE.exists() else None
    prima = len(vecchio['voci']) if vecchio else 0
    if len(nuove) < 20 or (prima and len(nuove) < prima * 0.4):
        print(f'Bandi: elenco sospetto ({len(nuove)} voci, prima {prima}). Restano quelli di prima.')
        return 0
    def senza_data(voci):
        return [{k: ({kk: vv for kk, vv in v['dettaglio'].items() if kk != 'verificato'} if k == 'dettaglio' else val) for k, val in v.items()} for v in voci]
    if vecchio and senza_data(vecchio['voci']) == senza_data(nuove):
        print(f'Bandi: nessuna variazione ({len(nuove)} voci, {sum(v["contributi"] for v in nuove)} con misure contributive).')
        return 0
    oggi = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2))).date().isoformat()
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_text(json.dumps({'fonte': ELENCO, 'ultima_variazione': oggi, 'voci': nuove}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    vecchi_id = {v['id'] for v in vecchio['voci']} if vecchio else set(); nuovi_id = {v['id'] for v in nuove}
    print(f'Bandi: {len(nuove)} voci ({sum(v["contributi"] for v in nuove)} con misure contributive), '
          f'{len(nuovi_id - vecchi_id)} nuove e {len(vecchi_id - nuovi_id)} tolte rispetto a prima.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
