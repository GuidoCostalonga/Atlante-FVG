"""Wikipedia (edizione inglese e italiana): tabelle dei sondaggi per elezione.

Fonte secondaria strutturata: ogni riga riporta istituto, periodo delle interviste, campione, valori per
partito o coalizione e un riferimento alla pubblicazione originale (quasi sempre un sito di notizie,
l'istituto o Scenari Politici). Le pagine da leggere stanno nei parametri della fonte (fonti.json):
  pagine: [{lingua, titolo, elezione, territorio: {tipo, nome, codice}}]
Le tabelle degli «aggregatori» (medie fra istituti) e i sottocampioni per età o squadra del cuore
vengono saltati: l'Osservatorio non pubblica medie fra istituti né sottocampioni non dichiarati.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from archivio import inserisci  # noqa: E402
from comune import MESI, MESI_EN, impronta, numero, pulisci, scaduto  # noqa: E402
from estrai import controlli_voto  # noqa: E402
from soggetti import riconosci  # noqa: E402

MESI_EN_ABBR = {m[:3]: n for m, n in MESI_EN.items()}
MESI_IT_ABBR = {m[:3]: n for m, n in MESI.items()}
RE_NOTA = re.compile(r'\[[^\]]*\]')
SALTA_SEZIONE = re.compile(r'aggregat|by age|by football|football team|electoral law|different years|by region|by gender|by education|by profession|graphical|seat projection|hypothetical.*seat', re.I)
TRADUZIONI = {'approve': 'Giudizio positivo', 'disapprove': 'Giudizio negativo', 'favourable': 'Favorevole', 'favorable': 'Favorevole', 'unfavourable': 'Sfavorevole',
              'unfavorable': 'Sfavorevole', 'yes': 'Sì', 'no': 'No', 'positive': 'Positivo', 'negative': 'Negativo', 'primaries': 'Primarie',
              "most-voted party's leader": 'Leader del partito più votato', 'agreement between leaders': 'Accordo fra i leader'}
SALTA_RIGA = re.compile(r'\b(election|elezioni|referendum result|results?)\b', re.I)


def _mese(nome: str) -> int | None:
    k = nome.lower().strip('.')
    return MESI_EN.get(k) or MESI_EN_ABBR.get(k[:3]) or MESI.get(k) or MESI_IT_ABBR.get(k[:3])


def date_riga(testo: str, anno: int | None) -> tuple[str | None, str | None]:
    """«7–12 Oct», «28 Dec–3 Jan», «5 Oct 2026», «17–22 Dec 2025», «1–3 ott 2026» → (inizio, fine) ISO."""
    t = pulisci(RE_NOTA.sub('', testo)).replace('—', '–').replace('-', '–')
    if not t:
        return None, None
    m = re.match(r'^(\d{1,2})(?:\s+([A-Za-zÀ-ü]+))?\s*–\s*(\d{1,2})\s+([A-Za-zÀ-ü]+)(?:\s+(\d{4}))?$', t)
    if m:
        anno_f = int(m.group(5)) if m.group(5) else anno
        mf = _mese(m.group(4))
        mi = _mese(m.group(2)) if m.group(2) else mf
        if not (mf and mi and anno_f):
            return None, None
        anno_i = anno_f - 1 if mi > mf else anno_f
        try:
            return dt.date(anno_i, mi, int(m.group(1))).isoformat(), dt.date(anno_f, mf, int(m.group(3))).isoformat()
        except ValueError:
            return None, None
    m = re.match(r'^(\d{1,2})\s+([A-Za-zÀ-ü]+)(?:\s+(\d{4}))?$', t)
    if m:
        a = int(m.group(3)) if m.group(3) else anno
        mm = _mese(m.group(2))
        if a and mm:
            try:
                d = dt.date(a, mm, int(m.group(1))).isoformat()
                return d, d
            except ValueError:
                return None, None
    m = re.match(r'^([A-Za-zÀ-ü]+)\s+(\d{4})$', t)  # «Oct 2026»: solo il mese
    if m and _mese(m.group(1)):
        return None, None
    return None, None


def _valore(testo: str) -> float | None:
    t = RE_NOTA.sub('', testo or '').strip()
    t = re.split(r'\n|\s{2,}|–\s', t)[0].strip()
    if not t or t in ('–', '—', '-', '?', 'N/a', '—N/a', 'n/a', 'TBA'):
        return None
    m = re.match(r'^[-+]?\d{1,3}(?:[.,]\d{1,2})?', t.replace('%', ''))
    if not m:
        return None
    return numero(m.group(0).replace(',', '.'))


def griglia(tabella_html: str) -> list[list[dict]]:
    """Tabella HTML → matrice di celle {testo, th, links} con rowspan e colspan risolti."""
    from bs4 import BeautifulSoup
    zuppa = BeautifulSoup(tabella_html, 'lxml')
    righe = []
    occupate: dict[tuple[int, int], dict] = {}
    for ri, tr in enumerate(zuppa.find_all('tr')):
        riga = []
        ci = 0
        for td in tr.find_all(['td', 'th']):
            while (ri, ci) in occupate:
                riga.append(occupate[(ri, ci)])
                ci += 1
            for s in td.find_all(['style']):
                s.decompose()
            testo = pulisci(td.get_text('\n'))
            cella = {'testo': testo, 'th': td.name == 'th', 'links': [a.get('href') for a in td.find_all('a', href=True)]}
            rs, cs = int(td.get('rowspan') or 1), int(td.get('colspan') or 1)
            for dr in range(rs):
                for dc in range(cs):
                    if dr == 0 and dc == 0:
                        continue
                    occupate[(ri + dr, ci + dc)] = cella
            riga.append(cella)
            ci += cs
        while (ri, ci) in occupate:
            riga.append(occupate[(ri, ci)])
            ci += 1
        righe.append(riga)
    return righe


def tabella_in_righe(tab: list[list[dict]], contesto: dict) -> list[dict]:
    """Legge una tabella di sondaggi: restituisce proposte di rilevazione (una per riga, con una domanda)."""
    intestazioni = []
    dati = []
    for r in tab:
        if r and all(c['th'] for c in r) and not dati:
            intestazioni.append(r)
        else:
            dati.append(r)
    if not intestazioni or not dati:
        return []
    ncol = max(len(r) for r in intestazioni + dati)
    etichette = []
    for ci in range(ncol):
        et = ''
        for r in intestazioni:
            if ci < len(r) and r[ci]['testo']:
                et = r[ci]['testo']
        etichette.append(RE_NOTA.sub('', et).strip())
    ruoli = []
    for et in etichette:
        e = et.lower()
        if re.search(r'fieldwork|^date|data|periodo', e):
            ruoli.append('data')
        elif re.search(r'polling ?firm|pollster|istituto|società', e):
            ruoli.append('istituto')
        elif re.search(r'sample|campione', e):
            ruoli.append('campione')
        elif re.search(r'^lead$|^vantaggio|^ref\.?$|^notes?$|^majority|^house$|^tifosi|^commissioner|^client|^committente', e):
            ruoli.append('salta')
        elif re.search(r'^others?$|^altri', e):
            ruoli.append('altri')
        elif re.search(r"don.?t know|undecided|non sa|no answer|indecisi|dk", e):
            ruoli.append('indecisi')
        elif re.search(r'abstention|astensione|astenuti|non vot', e):
            ruoli.append('astenuti')
        elif re.search(r'^approve|favou?rable|positive|^sì$|^si$|^yes$|fiducia$', e):
            ruoli.append('risposta')
        elif re.search(r'^disapprove|unfavou?rable|negative|^no$|sfiducia', e):
            ruoli.append('risposta')
        else:
            ruoli.append('soggetto' if et else 'salta')
    if 'istituto' not in ruoli:
        return []
    esito = []
    tipo = contesto['tipo']
    for r in dati:
        if len(r) < 3:
            continue
        valori = {k: None for k in ('data', 'istituto', 'campione')}
        risposte, coalizioni, indecisi, astenuti = [], [], None, None
        link_riga = []
        for ci, c in enumerate(r):
            if ci >= len(ruoli):
                break
            ruolo = ruoli[ci]
            link_riga += [l for l in c['links'] if l.startswith('http')]
            if ruolo in ('data', 'istituto', 'campione'):
                valori[ruolo] = c['testo']
            elif ruolo == 'indecisi':
                indecisi = _valore(c['testo'])
            elif ruolo == 'astenuti':
                astenuti = _valore(c['testo'])
            elif ruolo in ('soggetto', 'altri', 'risposta'):
                v = _valore(c['testo'])
                et = etichette[ci]
                if et.upper() in ('CSX', 'CDX', 'CX', 'CENTRE', 'CENTRE-LEFT', 'CENTRE-RIGHT', 'CENTRO', 'CENTRODESTRA', 'CENTROSINISTRA') or (et.upper() == 'FN' and tipo == 'voto' and 'coal' in contesto.get('gruppo_colonna', {}).get(ci, '')):
                    coalizioni.append({'testo': et, 'valore': v})
                else:
                    risposte.append({'testo': et, 'valore': v, 'ruolo': ruolo})
        ist = pulisci(RE_NOTA.sub('', valori['istituto'] or ''))
        if not ist or SALTA_RIGA.search(ist) or re.fullmatch(r'[\d\s.,%–-]+', ist):
            continue
        inizio, fine = date_riga(valori['data'] or '', contesto.get('anno'))
        campione = None
        if valori['campione']:
            cifre = re.sub(r'[^\d]', '', RE_NOTA.sub('', valori['campione']).split('\n')[0])
            campione = int(cifre) if cifre and 50 <= int(cifre) <= 200000 else None
        quando = dt.date.fromisoformat(fine) if fine else (dt.date(contesto['anno'], 12, 31) if contesto.get('anno') else None)
        voci = []
        for x in risposte:
            if x['valore'] is None and x['ruolo'] != 'risposta':
                continue
            if x['ruolo'] == 'altri':
                voci.append({'testo': x['testo'], 'soggetto': 'altri', 'valore': x['valore'], 'min': None, 'max': None, 'variazione': None})
            elif tipo == 'voto':
                sid, motivo = riconosci(x['testo'], quando)
                voci.append({'testo': x['testo'], 'soggetto': sid, 'motivo': motivo, 'valore': x['valore'], 'min': None, 'max': None, 'variazione': None})
            else:
                voci.append({'testo': TRADUZIONI.get(x['testo'].lower(), x['testo']), 'soggetto': None, 'valore': x['valore'], 'min': None, 'max': None, 'variazione': None})
        if not voci and not coalizioni:
            continue
        domanda = {'tipo': tipo, 'elezione': contesto.get('elezione'), 'turno': None, 'scenario': contesto.get('scenario'),
                   'testo': contesto['testo'], 'unita': '%', 'denominatore': 'validi' if tipo == 'voto' else 'totale',
                   'indecisi': indecisi, 'astenuti': astenuti, 'risposte': voci, 'origine': 'tabella',
                   'controlli': controlli_voto(voci) if tipo == 'voto' else {'ok': True, 'motivi': []}}
        if tipo == 'voto' and domanda['controlli'] and not domanda['controlli']['ok']:
            # le tabelle di Wikipedia omettono spesso partiti minori: la somma può non chiudere a 100 senza che il dato sia sbagliato
            motivi = [m for m in domanda['controlli']['motivi'] if not m.startswith('somma')]
            domanda['controlli']['motivi'] = motivi
            domanda['controlli']['ok'] = not motivi
            if domanda['controlli']['somma'] < 85:
                domanda['controlli']['motivi'].append(f"somma {domanda['controlli']['somma']} troppo bassa")
                domanda['controlli']['ok'] = False
        domande = [domanda]
        if coalizioni:
            voci_c = []
            for x in coalizioni:
                sid, motivo = riconosci(x['testo'], quando)
                voci_c.append({'testo': x['testo'], 'soggetto': sid, 'motivo': motivo, 'valore': x['valore'], 'min': None, 'max': None, 'variazione': None})
            domande.append({'tipo': 'voto', 'livello': 'coalizioni', 'elezione': contesto.get('elezione'), 'turno': None, 'testo': contesto['testo'] + ' (coalizioni)',
                            'unita': '%', 'denominatore': 'validi', 'risposte': voci_c, 'origine': 'tabella', 'controlli': {'ok': True, 'motivi': []}})
        esito.append({'istituto': ist, 'inizio': inizio, 'fine': fine, 'campione': campione, 'domande': domande,
                      'urls': link_riga[:3], 'dataTesto': valori['data']})
    return esito


def leggi_pagina(testo_html: str, pagina: dict, permalink: str) -> list[dict]:
    """Da una pagina (HTML del parse) a proposte di rilevazione, unendo le righe della stessa rilevazione."""
    from bs4 import BeautifulSoup
    zuppa = BeautifulSoup(testo_html, 'lxml')
    corpo = zuppa.find(class_='mw-parser-output') or zuppa
    titoli = {'h2': '', 'h3': '', 'h4': ''}
    per_chiave: dict[str, dict] = {}
    for el in corpo.find_all(['h2', 'h3', 'h4', 'table']):
        if el.name in titoli:
            titoli[el.name] = pulisci(el.get_text(' ').replace('[edit]', '').replace('[modifica | modifica wikitesto]', ''))
            for sotto in ('h3', 'h4') if el.name == 'h2' else (('h4',) if el.name == 'h3' else ()):
                titoli[sotto] = ''
            continue
        if 'wikitable' not in (el.get('class') or []):
            continue
        catena = ' > '.join(t for t in (titoli['h2'], titoli['h3'], titoli['h4']) if t)
        if SALTA_SEZIONE.search(catena):
            continue
        anno = None
        for t in (titoli['h4'], titoli['h3'], titoli['h2']):
            m = re.fullmatch(r'(\d{4})(?:\s*[–-]\s*\d{2,4})?', t or '')
            if m:
                anno = int(m.group(1))
                break
        c = catena.lower()
        if re.search(r'government|governo|cabinet|esecutivo', c) and 'approval' in c or 'fiducia nel governo' in c:
            tipo, testo = 'fiducia', 'Giudizio sul Governo (' + catena.split(' > ')[0] + ')'
        elif 'approval' in c or 'fiducia' in c or 'gradimento' in c:
            tipo, testo = 'fiducia', catena.split(' > ')[0]
        elif ' vs' in c or 'preferred' in c or 'preferito' in c or 'most likely' in c or 'how to choose' in c or 'candidate' in c:
            tipo, testo = 'scenario', catena
        elif 'leadership' in c or 'primar' in c:
            tipo, testo = 'scenario', catena
        elif 'coalition' in c or 'coalizion' in c or 'party vote' in c or 'vote' in c or 'voto' in c or 'intenzioni' in c or re.search(r'\b(19|20)\d{2}\b', c) or not catena or 'opinion poll' in c or 'sondagg' in c:
            tipo, testo = 'voto', 'Intenzioni di voto'
        else:
            tipo, testo = 'tema', catena
        contesto = {'tipo': tipo, 'testo': testo, 'anno': anno, 'elezione': pagina.get('elezione') if tipo == 'voto' else None,
                    'scenario': catena if tipo == 'scenario' else None}
        try:
            righe = tabella_in_righe(griglia(str(el)), contesto)
        except Exception:  # noqa: BLE001
            continue
        for r in righe:
            chiave = impronta(pagina['titolo'], r['istituto'], r['fine'] or r['dataTesto'] or '', str(r['campione'] or ''))
            voce = per_chiave.get(chiave)
            if not voce:
                voce = {
                    'fonte': 'wikipedia', 'riferimento': chiave, 'titolo': f"{r['istituto']}: {pagina.get('descrizione') or pagina['titolo'].replace('_', ' ')}",
                    'istituto': r['istituto'], 'committente': None, 'editore': None, 'inizio': r['inizio'], 'fine': r['fine'],
                    'pubblicato': None, 'criterioData': 'interviste' if r['fine'] else 'pubblicazione', 'territorio': pagina.get('territorio') or {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'},
                    'campione': r['campione'], 'livello': 'secondaria', 'urls': [permalink], 'documenti': [], 'domande': [],
                    'limiti': 'Valori ripresi dalla tabella di Wikipedia, che cita la pubblicazione originale; le tabelle omettono i partiti minori e arrotondano a un decimale.',
                }
                if pagina.get('elezione'):
                    voce['elezione'] = pagina['elezione']
                per_chiave[chiave] = voce
            voce['domande'].extend(r['domande'])
            for u in r['urls']:
                if u not in voce['urls']:
                    voce['urls'].append(u)
                    voce['documenti'].append({'url': u, 'tipo': 'html', 'titolo': 'Pubblicazione citata da Wikipedia', 'rif': 'riferimento nella riga della tabella'})
    return list(per_chiave.values())


def aggiorna(fonte: dict, stato: dict, archivio: dict, rete, opzioni: dict) -> dict:
    esecuzione = opzioni['esecuzione']
    esito = {'letti': 0, 'nuovi': 0, 'aggiornati': 0, 'invariati': 0, 'coda': 0, 'protetti': 0, 'errori': [], 'finito': True, 'pagine': 0}
    conteggio = {'nuova': 'nuovi', 'aggiornata': 'aggiornati', 'invariata': 'invariati', 'coda': 'coda', 'protetta': 'protetti'}
    for pagina in fonte.get('parametri', {}).get('pagine', []):
        if scaduto(opzioni):
            esito['finito'] = False
            esito['errori'].append('tempo esaurito: pagine restanti rinviate al giro successivo')
            break
        lingua = pagina.get('lingua', 'en')
        titolo = pagina['titolo']
        url = f'https://{lingua}.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(titolo)}&prop=text|revid&format=json&formatversion=2&redirects=1'
        try:
            d = rete.json(url)
        except ConnectionError as e:
            esito['errori'].append(str(e))
            continue
        if 'error' in d:
            esito['errori'].append(f'{titolo}: {d["error"].get("info")}')
            continue
        testo_html = d['parse']['text']
        permalink = f'https://{lingua}.wikipedia.org/w/index.php?title={urllib.parse.quote(titolo)}&oldid={d["parse"].get("revid")}'
        esito['pagine'] += 1
        for r in leggi_pagina(testo_html, pagina, permalink):
            esito['letti'] += 1
            try:
                esito[conteggio[inserisci(archivio, r, esecuzione)]] += 1
            except Exception as e:  # noqa: BLE001
                esito['errori'].append(f'{titolo}: {type(e).__name__}: {e}')
    return esito
