#!/usr/bin/env python3
"""Legge l'elenco ufficiale «Bandi e avvisi» della Regione Autonoma Friuli Venezia Giulia e scrive dati/bandi.json.

Fonte: https://www.regione.fvg.it/rafvg/cms/RAFVG/MODULI/bandi_avvisi/ (tutti i bandi e gli avvisi in corso, a cura delle
strutture regionali competenti). Per ogni voce si prendono solo i campi che la pagina riporta: titolo, direzione o struttura,
data di pubblicazione, scadenza (se indicata) e indirizzo della pagina ufficiale. Il filtro «Bandi contenenti misure
contributive», offerto dalla stessa pagina, si legge a parte e diventa il campo `contributi`: è un'indicazione della Regione,
non una classificazione dell'Atlante. Nessun altro dato è dedotto: non si indovinano destinatari, importi o requisiti. Una scadenza del 1° gennaio 1970, che la
Regione usa come segnaposto, vale «scadenza non indicata».

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
    if vecchio and vecchio['voci'] == nuove:
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
