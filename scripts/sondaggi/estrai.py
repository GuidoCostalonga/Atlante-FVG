"""Estrazione dei valori da testi, tabelle HTML, PDF e immagini (OCR).

Tutto ciò che esce di qui è una proposta: `righe` di {testo, soggetto, valore, min, max, variazione}
più un elenco di `controlli` con l'esito. La decisione (importazione automatica o coda «da verificare»)
spetta a `aggiorna.py`, con regole esplicite. Nessuna funzione inventa valori: le righe senza numero
restano con `valore: null`.
"""
from __future__ import annotations

import datetime as dt
import io
import re

from comune import intervallo_date, numero, pulisci, registro
from soggetti import riconosci

RE_VALORE = re.compile(r'^(?P<nome>.+?)\s*[:\-–]?\s*(?P<v>\d{1,3}(?:[,.]\d{1,2})?)\s*%?(?:\s*\(?\s*(?P<var>[-+±]?\s?\d{1,2}(?:[,.]\d)?)\s*%?\)?)?\s*$')
RE_INTERVALLO = re.compile(r'^(?P<nome>.+?)\s*[:\-–]?\s*(?P<a>\d{1,2}(?:[,.]\d)?)\s*%?\s*[-–/]\s*(?P<b>\d{1,2}(?:[,.]\d)?)\s*%?\s*$')
RE_CAMPIONE = re.compile(r'(?:campione|interviste|casi|intervistati|N\s*=|n\.\s*interviste|totale interviste)[^0-9]{0,40}?(\d{1,2}[.\s]?\d{3}|\d{3,5})', re.I)
RE_METODO = re.compile(r'\b(CATI|CAWI|CAMI|CAPI|mixed mode|mix(?:ed)?\s*mode|telefonic\w+|online|web|panel|interviste personali|face to face)\b', re.I)
RE_ERRORE = re.compile(r'margine d.errore[^0-9]{0,40}(\d{1,2}(?:[,.]\d{1,2})?)\s*%', re.I)
RE_PERIODO = re.compile(r'(?:date di esecuzione|periodo di rilevazione|rilevazione(?: è stata)? (?:condotta|effettuata|realizzata)|interviste(?: sono state)? (?:effettuate|realizzate|condotte|raccolte)|effettuat[ea] (?:tra|fra|il|dal|nei giorni)|realizzat[oa] (?:tra|fra|il|dal|nei giorni)|condott[oa] (?:tra|fra|il|dal|nei giorni)|nei giorni|svolt[oa] (?:tra|fra|dal|il))[^0-9]{0,25}((?:\d{1,2}(?:\s+[a-zà]+)?\s*[-–—/]\s*)?\d{1,2}\s+[a-zà]+\.?\s+\d{4}|\d{1,2}[/.]\d{1,2}(?:[/.]\d{4})?\s*[-–—]\s*\d{1,2}[/.]\d{1,2}[/.]\d{4}|\d{1,2}[/.]\d{1,2}[/.]\d{4})', re.I)
PAROLE_SCARTO = re.compile(r'\b(totale|differenza|variazione|rispetto|settimana|precedente|indecisi|astenuti|astensione|non si esprim|non sa|non risponde|non vot|affluenza|campione|margine|nota|fonte|sondaggio|rilevazione|intenzioni|orientamenti|data|date|tg|la7|rai|sky|mediaset|%|valori|elettori)\b', re.I)


def leggi_righe(righe_testo: list[str], quando: dt.date | None = None) -> list[dict]:
    """Da righe di testo «Nome 27,7% +0,3» a voci strutturate. Riconosce anche intervalli «47%-51%»."""
    esito = []
    for r in righe_testo:
        t = pulisci(r).replace('%%', '%')
        if not t or len(t) > 120:
            continue
        m = RE_INTERVALLO.match(t)
        if m:
            nome = m.group('nome')
            if PAROLE_SCARTO.search(nome):
                continue
            a, b = numero(m.group('a')), numero(m.group('b'))
            sid, motivo = riconosci(nome, quando)
            esito.append({'testo': nome, 'soggetto': sid, 'motivo': motivo, 'valore': None, 'min': min(a, b), 'max': max(a, b), 'variazione': None})
            continue
        m = RE_VALORE.match(t)
        if not m:
            continue
        nome = m.group('nome').strip(' |:')
        if len(nome) < 2 or PAROLE_SCARTO.search(nome) or re.fullmatch(r'[\d\s,.%+-]+', nome) or len(re.findall(r'[A-Za-zÀ-ü]', nome)) < 3:
            continue
        v = numero(m.group('v'))
        if v is None or v < 0 or v > 100:
            continue
        var = numero(m.group('var').replace(' ', '')) if m.group('var') else None
        sid, motivo = riconosci(nome, quando)
        esito.append({'testo': nome, 'soggetto': sid, 'motivo': motivo, 'valore': v, 'min': None, 'max': None, 'variazione': var})
    return esito


def nota_informativa(testo: str) -> dict:
    """Legge dalla nota metodologica: periodo delle interviste, campione, metodo, margine d'errore."""
    t = pulisci(testo)
    esito = {'inizio': None, 'fine': None, 'campione': None, 'metodo': None, 'erroreDichiarato': None}
    m = RE_PERIODO.search(t)
    if m:
        a, b = intervallo_date(m.group(1))
        esito['inizio'], esito['fine'] = a.isoformat() if a else None, b.isoformat() if b else None
    m = RE_CAMPIONE.search(t)
    if m:
        n = numero(m.group(1).replace(' ', ''))
        if n and 100 <= n <= 100000:
            esito['campione'] = int(n)
    metodi = sorted({x.upper() if len(x) <= 4 else x.lower() for x in RE_METODO.findall(t)})
    if metodi:
        esito['metodo'] = ', '.join(metodi)
    m = RE_ERRORE.search(t)
    if m:
        esito['erroreDichiarato'] = numero(m.group(1))
    return esito


def controlli_voto(righe: list[dict]) -> dict:
    """Controlli di coerenza su un elenco di intenzioni di voto per partito."""
    valori = [r for r in righe if r['valore'] is not None]
    somma = round(sum(r['valore'] for r in valori), 1)
    riconosciute = [r for r in valori if r['soggetto']]
    sconosciute = [r for r in valori if not r['soggetto']]
    esito = {
        'righe': len(valori), 'riconosciute': len(riconosciute), 'sconosciute': [r['testo'] for r in sconosciute],
        'somma': somma, 'duplicati': [], 'ok': False, 'motivi': [],
    }
    visti = set()
    for r in riconosciute:
        if r['soggetto'] in visti:
            esito['duplicati'].append(r['soggetto'])
        visti.add(r['soggetto'])
    if len(valori) < 4:
        esito['motivi'].append('meno di quattro valori')
    if len(riconosciute) < 4:
        esito['motivi'].append('meno di quattro soggetti riconosciuti')
    if esito['duplicati']:
        esito['motivi'].append('soggetto ripetuto: ' + ', '.join(esito['duplicati']))
    if not (97.0 <= somma <= 101.5):
        esito['motivi'].append(f'somma {somma} fuori dall\'intervallo 97–101,5')
    if len(sconosciute) > max(1, len(valori) // 4):
        esito['motivi'].append('troppe righe non riconosciute')
    esito['ok'] = not esito['motivi']
    return esito


# ------------------------------------------------------------------------------------------------- tabelle HTML

def tabelle_html(html: str) -> list[list[list[str]]]:
    """Tutte le tabelle della pagina come matrici di celle di testo (senza etichette HTML)."""
    from bs4 import BeautifulSoup
    zuppa = BeautifulSoup(html, 'lxml')
    tabelle = []
    for tab in zuppa.find_all('table'):
        righe = []
        for tr in tab.find_all('tr'):
            celle = [pulisci(td.get_text(' ')) for td in tr.find_all(['td', 'th'])]
            if celle:
                righe.append(celle)
        if righe:
            tabelle.append(righe)
    return tabelle


def testo_html(html: str) -> str:
    from bs4 import BeautifulSoup
    zuppa = BeautifulSoup(html, 'lxml')
    for s in zuppa(['script', 'style', 'noscript']):
        s.decompose()
    return pulisci(zuppa.get_text(' '))


# -------------------------------------------------------------------------------------------------------- PDF

def testo_pdf(dati: bytes, massimo_pagine: int = 60) -> list[str]:
    """Testo pagina per pagina (pdfplumber, con disposizione conservata)."""
    import pdfplumber
    pagine = []
    with pdfplumber.open(io.BytesIO(dati)) as pdf:
        for p in pdf.pages[:massimo_pagine]:
            try:
                pagine.append(p.extract_text(layout=True) or '')
            except Exception as e:  # noqa: BLE001
                registro(f'pdf: pagina non leggibile ({e})')
                pagine.append('')
    return pagine


def tabelle_pdf(dati: bytes, massimo_pagine: int = 60) -> list[dict]:
    """Tabelle trovate da pdfplumber, con il numero di pagina."""
    import pdfplumber
    esito = []
    with pdfplumber.open(io.BytesIO(dati)) as pdf:
        for n, p in enumerate(pdf.pages[:massimo_pagine], 1):
            try:
                for t in p.extract_tables():
                    righe = [[pulisci(c or '') for c in r] for r in t if any(c for c in r)]
                    if righe:
                        esito.append({'pagina': n, 'righe': righe})
            except Exception:  # noqa: BLE001
                continue
    return esito


def righe_pdf_parole(dati: bytes, numero_pagina: int, tolleranza: float = 3.5) -> list[dict]:
    """Righe di una pagina PDF ricostruite dalle coordinate delle parole (per le impaginazioni a colonne,
    dove il testo «con disposizione» mescola le colonne). Stesso formato delle righe OCR: {y, testo}."""
    import pdfplumber
    with pdfplumber.open(io.BytesIO(dati)) as pdf:
        if numero_pagina > len(pdf.pages):
            return []
        parole = pdf.pages[numero_pagina - 1].extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1.5)
    righe: dict[float, list] = {}
    for w in sorted(parole, key=lambda w: (w['top'], w['x0'])):
        y = round(w['top'], 1)
        vicina = min(righe, key=lambda k: abs(k - y)) if righe else None
        k = vicina if vicina is not None and abs(vicina - y) < tolleranza else y
        righe.setdefault(k, []).append((w['x0'], w['x1'], w['text']))
    esito = []
    for y in sorted(righe):
        pezzi = sorted(righe[y])
        # parole vicine (meno di 8 punti) stanno nella stessa cella; spazi più larghi separano le celle
        celle, corrente, fine = [], [], None
        for x0, x1, testo in pezzi:
            if corrente and fine is not None and x0 - fine > 8:
                celle.append(' '.join(corrente))
                corrente = []
            corrente.append(testo)
            fine = x1
        if corrente:
            celle.append(' '.join(corrente))
        esito.append({'y': y, 'testo': ' | '.join(celle), 'fiducia': 1.0})
    return esito


def righe_da_tabella(tab: list[list[str]]) -> list[str]:
    """Trasforma una tabella (celle) in righe «Nome valore» leggibili da leggi_righe: prende la prima cella
    testuale come nome e la prima cella numerica come valore."""
    righe = []
    for r in tab:
        nome, val = None, None
        for c in r:
            if nome is None and c and numero(c) is None:
                nome = c
            elif nome is not None and val is None and numero(c) is not None:
                val = c
        if nome and val is not None:
            righe.append(f'{nome} {val}')
    return righe


# -------------------------------------------------------------------------------------------------------- OCR

_OCR = None


def ocr_righe(immagine: bytes) -> list[dict]:
    """Legge un'immagine (tabella o grafico) e restituisce le righe di testo raggruppate per altezza,
    come {y, testo}. Richiede rapidocr_onnxruntime; se manca restituisce una lista vuota."""
    global _OCR
    try:
        if _OCR is None:
            from rapidocr_onnxruntime import RapidOCR
            _OCR = RapidOCR()
    except ImportError:
        return []
    import numpy as np
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(immagine)).convert('RGB')
        if max(img.size) > 2200:
            img.thumbnail((2200, 2200))
        if max(img.size) < 700:
            img = img.resize((img.width * 2, img.height * 2))
        arr = np.array(img)
    except Exception as e:  # noqa: BLE001
        registro(f'ocr: immagine non leggibile ({e})')
        return []
    try:
        res, _ = _OCR(arr)
    except Exception as e:  # noqa: BLE001
        registro(f'ocr: errore ({e})')
        return []
    if not res:
        return []
    righe: dict[int, list] = {}
    altezze = [abs(b[2][1] - b[0][1]) for b, _, _ in res]
    tolleranza = max(8, sorted(altezze)[len(altezze) // 2] * 0.6)
    for box, txt, conf in res:
        y = sum(p[1] for p in box) / 4
        x = min(p[0] for p in box)
        vicina = min(righe, key=lambda k: abs(k - y)) if righe else None
        k = vicina if vicina is not None and abs(vicina - y) < tolleranza else int(y)
        righe.setdefault(k, []).append((x, txt, float(conf)))
    esito = []
    for y in sorted(righe):
        pezzi = sorted(righe[y])
        esito.append({'y': y, 'testo': ' | '.join(t for _, t, _ in pezzi), 'fiducia': round(min(c for _, _, c in pezzi), 2)})
    return esito


def righe_ocr_in_valori(righe: list[dict], quando: dt.date | None = None) -> tuple[list[dict], dict]:
    """Dalle righe OCR alle voci strutturate. Una riga OCR «Fratelli d'Italia | 27,7% | +0,3» diventa
    «Fratelli d'Italia 27,7% (+0,3)»; i pezzi numerici in più (per esempio confronti con rilevazioni
    precedenti) vengono ignorati. Restituisce anche la nota informativa trovata nel testo."""
    testi = []
    testo_tutto = ' '.join(r['testo'].replace(' | ', ' ') for r in righe)
    for r in righe:
        pezzi = [p.strip() for p in r['testo'].split('|')]
        nomi = [p for p in pezzi if numero(p.replace('%', '')) is None and not re.fullmatch(r'[-+]\s?\d+[,.]?\d*\s*%?', p)]
        numeri = [p for p in pezzi if numero(p.replace('%', '')) is not None]
        if not nomi or not numeri:
            # riga tipo «RobertoDiPiazza | 47%-51%» o «(Cdx)»: lasciata al riconoscimento degli intervalli
            if nomi and any(re.search(r'\d+\s*%?\s*[-–]\s*\d+\s*%', p) for p in pezzi):
                testi.append(nomi[0] + ' ' + next(p for p in pezzi if re.search(r'\d+\s*%?\s*[-–]\s*\d+\s*%', p)))
            continue
        riconosciuti = [p for p in nomi if riconosci(p, quando)[0]]
        nome = riconosciuti[0] if riconosciuti else max(nomi, key=len)
        # il valore è il primo numero con la % o il primo numero fra 0 e 100 che non sia una variazione
        valore = next((p for p in numeri if '%' in p and not re.match(r'[-+]', p)), None)
        if valore is None:
            cand = [p for p in numeri if not re.match(r'[-+]', p) and 0 <= (numero(p) or -1) <= 100]
            valore = cand[0] if cand else None
        if valore is None:
            continue
        var = next((p for p in numeri if re.match(r'[-+]\s?\d', p)), None)
        testi.append(f'{nome} {valore}' + (f' ({var})' if var else ''))
    righe_lette = leggi_righe(testi, quando)
    # nelle pagine con due pannelli (valori attuali e precedenti) lo stesso soggetto compare due volte:
    # resta la prima occorrenza dall'alto, le altre vengono annotate e scartate
    visti, esito, scartate = set(), [], []
    nomi_riconosciuti = ' '.join(r['testo'].lower() for r in righe_lette if r['soggetto'])
    for r in righe_lette:
        if r['soggetto'] and r['soggetto'] != 'altri' and r['soggetto'] in visti:
            scartate.append(r)
            continue
        if not r['soggetto'] and len(r['testo'].split()) == 1 and r['testo'].lower() in nomi_riconosciuti:
            # seconda riga di un nome che va a capo («Futuro / Nazionale»): il valore accanto appartiene a un altro pannello
            scartate.append(r)
            continue
        if r['soggetto']:
            visti.add(r['soggetto'])
        esito.append(r)
    nota = nota_informativa(testo_tutto)
    if scartate:
        nota['righeScartate'] = [{'testo': r['testo'], 'valore': r['valore']} for r in scartate]
    return esito, nota
