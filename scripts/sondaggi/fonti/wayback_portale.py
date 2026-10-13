"""Portale ufficiale sondaggipoliticoelettorali.it attraverso la Wayback Machine (web.archive.org).

Il portale della Presidenza del Consiglio non risponde né dal computer di GitHub né dall'ambiente di lavoro
(blocco geografico): si leggono le copie conservate dalla Wayback Machine. Sono archiviate soprattutto le
pagine del vecchio sito (2002–2013): elenchi («visualizza_sondaggi.asp», con data, autore, committente e
titolo) e circa 2.500 schede di dettaglio («visualizza_sondaggio.asp?idsondaggio=N») con la nota
informativa e le domande; i valori stanno in immagini e vengono letti con l'OCR quando possibile.

Fonte primaria (è il deposito di legge dei sondaggi pubblicati), copertura parziale: la rilevazione
registra sempre il collegamento alla copia archiviata.
"""
from __future__ import annotations

import html
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from archivio import inserisci  # noqa: E402
from comune import data_italiana, numero, pulisci, scaduto  # noqa: E402
from estrai import controlli_voto, leggi_righe, nota_informativa, ocr_righe, righe_ocr_in_valori, tabelle_html  # noqa: E402

CDX = 'https://web.archive.org/cdx/search/cdx?url=sondaggipoliticoelettorali.it/asp/visualizza_sondaggi*&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&collapse=digest&limit=20000'
WB = 'https://web.archive.org/web/{ts}id_/{url}'
RE_TITOLO = re.compile(r'<title>(.*?)</title>', re.S)


def _testo(h: str) -> str:
    h = re.sub(r'<(script|style).*?</\1>', ' ', h or '', flags=re.S)
    return pulisci(html.unescape(re.sub(r'<[^>]+>', ' ', h)))


def _decodifica(b: bytes) -> str:
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode('utf-8', 'replace')


def righe_elenco(h: str) -> list[dict]:
    """Da una pagina «visualizza_sondaggi.asp»: {data, autore, committente, titolo, id}."""
    voci = []
    for tab in tabelle_html(h):
        for r in tab:
            if len(r) >= 4 and re.match(r'\d{2}/\d{2}/\d{4}$', r[0]):
                voci.append({'data': data_italiana(r[0]), 'autore': r[1], 'committente': r[2], 'titolo': r[3]})
    # gli id stanno nei collegamenti, nello stesso ordine delle righe
    ids = re.findall(r'visualizza_sondaggio\.asp\?idsondaggio=(\d+)', h)
    for v, i in zip(voci, ids):
        v['id'] = i
    return [v for v in voci if v.get('id')]


ETICHETTE = ['Pubblicato il', 'Autore:', 'Committente/ Acquirente:', 'Committente:', 'Acquirente:', 'Criteri seguiti per la formazione del campione:',
             'Metodo di raccolta delle informazioni:', 'Numero delle persone interpellate e universo di riferimento:', 'Data in cui è stato realizzato il sondaggio:',
             'Rispondenti:', 'Margine di approssimazione:', 'Margine di errore:', 'QUESTIONARIO', 'INDIETRO']
RE_ETICHETTA = re.compile('(' + '|'.join(re.escape(e) for e in ETICHETTE) + ')')


def campi_scheda(testo: str) -> dict:
    """Spezza il testo della scheda del vecchio portale nei suoi campi."""
    pezzi = RE_ETICHETTA.split(testo)
    campi = {'_testa': pulisci(pezzi[0])}
    for et, val in zip(pezzi[1::2], pezzi[2::2]):
        campi[et.rstrip(':').strip()] = pulisci(val)
    return campi


def quesiti(testo_questionario: str) -> list[dict]:
    """«QUESITO n.1 Domanda : … Risposta: • A: 1.6% • B: 3.4% …» → elenco di {testo, risposte_testo}."""
    esito = []
    for m in re.finditer(r'QUESITO\s*n\.?\s*(\d+)\s*Domanda\s*:?\s*(.*?)(?=QUESITO\s*n\.|$)', testo_questionario, re.S | re.I):
        blocco = m.group(2)
        dom, _, risp = blocco.partition('Risposta')
        risp = risp.lstrip(' :')
        voci = [pulisci(x) for x in re.split(r'[•·]|\s(?=\d+\.\s)', risp) if pulisci(x)]
        esito.append({'n': int(m.group(1)), 'testo': pulisci(dom).rstrip(' .'), 'risposte_testo': voci})
    return esito


def scheda_in_rilevazione(h: str, url_archivio: str, idsondaggio: str, elenco: dict | None, rete, ocr: bool, ts: str) -> dict:
    testo = _testo(h)
    campi = campi_scheda(testo)
    titolo = re.sub(r'^Sondaggio Politico-Elettorale\s*', '', campi['_testa']).strip() or (elenco or {}).get('titolo') or f'Sondaggio n. {idsondaggio}'
    autore = campi.get('Autore') or (elenco or {}).get('autore')
    committente = campi.get('Committente/ Acquirente') or campi.get('Committente') or (elenco or {}).get('committente')
    acquirente = campi.get('Acquirente')
    acquirente = None if not acquirente or acquirente.startswith('---') else acquirente
    pubblicato = data_italiana(campi.get('Pubblicato il') or '') or (elenco or {}).get('data')
    from comune import intervallo_date
    inizio, fine = intervallo_date(campi.get('Data in cui è stato realizzato il sondaggio') or '')
    nota = nota_informativa(' '.join(campi.get(k, '') for k in ('Numero delle persone interpellate e universo di riferimento', 'Metodo di raccolta delle informazioni', 'Criteri seguiti per la formazione del campione', 'Margine di errore', 'Margine di approssimazione')))
    campione = nota['campione']
    if not campione:
        m = re.search(r'(?:casi|interviste|campione|interpellat\w+)\s*:?\s*(\d{1,2}[.\s]?\d{3}|\d{3,4})', campi.get('Numero delle persone interpellate e universo di riferimento', ''), re.I)
        if m:
            campione = int(m.group(1).replace('.', '').replace(' ', ''))
    universo = None
    m = re.search(r'universo(?: di riferimento)?\s*:?\s*([^.;]{5,120})', campi.get('Numero delle persone interpellate e universo di riferimento', ''), re.I)
    if m:
        universo = pulisci(m.group(1))
    errore = nota['erroreDichiarato'] or numero((re.search(r'(\d{1,2}(?:[,.]\d)?)\s*%', campi.get('Margine di approssimazione', '') + ' ' + campi.get('Margine di errore', '')) or [None, None])[1])
    est = ' '.join([titolo, universo or '', campi.get('Criteri seguiti per la formazione del campione', '')]).lower()
    territorio = {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}
    if 'friuli' in est:
        territorio = {'tipo': 'regione', 'nome': 'Friuli Venezia Giulia', 'codice': 'FVG'}
    elif re.search(r'\b(trieste|udine|pordenone|gorizia)\b', est):
        territorio = {'tipo': 'comune', 'nome': re.search(r'\b(trieste|udine|pordenone|gorizia)\b', est).group(1).title(), 'codice': None}
    else:
        m = re.search(r'\b(abruzzo|basilicata|calabria|campania|emilia[- ]romagna|lazio|liguria|lombardia|marche|molise|piemonte|puglia|sardegna|sicilia|toscana|trentino|umbria|veneto|valle d.aosta)\b', est)
        if m and not re.search(r'popolazione italiana|nazionale|italia\b', est):
            territorio = {'tipo': 'regione', 'nome': m.group(1).title(), 'codice': None}
        elif re.search(r'elettori del comune di|cittadini di|residenti nel comune di|elezioni (?:comunali|amministrative)|elezione del sindaco', est):
            m2 = re.search(r'(?:elettori del comune di|cittadini di|residenti nel comune di|comunali (?:di|a)|sindaco di)\s+([a-zà\' ]{3,30}?)(?=[ ,.;)]|$)', est)
            nome = m2.group(1).strip().title() if m2 and m2.group(1).strip() not in ('residenza',) else 'comune non indicato'
            territorio = {'tipo': 'comune', 'nome': nome, 'codice': None}
    quando = fine or pubblicato
    import datetime as dt
    quando_d = dt.date.fromisoformat(quando.isoformat() if hasattr(quando, 'isoformat') else quando) if quando else None
    domande = []
    testo_q = campi.get('QUESTIONARIO', '')
    elezione = None
    if re.search(r'intenzioni di voto|se oggi si votasse|cabina elettorale|per quale (?:partito|lista|coalizione)|votare per', titolo + ' ' + testo_q, re.I):
        elezione = 'europee' if re.search(r'europe', titolo + ' ' + testo_q, re.I) else ('regionali' if territorio['tipo'] == 'regione' else ('comunali' if territorio['tipo'] == 'comune' else 'politiche'))
    for q in quesiti(testo_q):
        risposte = leggi_righe([re.sub(r'^(?:L.|Il |La |I |Gli |Le )', '', v) for v in q['risposte_testo']], quando_d)
        valide = [r for r in risposte if r['valore'] is not None]
        e_voto = elezione and re.search(r'voto|votare|cabina|partit|lista|coalizion|camera|senato', q['testo'], re.I) and sum(1 for r in valide if r['soggetto']) >= 3
        if e_voto:
            partiti = [r for r in valide if not re.search(r'indecis|scheda bianca|affluenza|non vot|astenut|non risponde|non sa', r['testo'], re.I)]
            d = {'tipo': 'voto', 'elezione': elezione, 'turno': None, 'testo': q['testo'], 'unita': '%', 'denominatore': 'validi', 'risposte': partiti,
                 'origine': 'testo', 'controlli': controlli_voto(partiti), 'rif': f'quesito n. {q["n"]}'}
            extra = 0.0
            for r in valide:
                if re.search(r'indecis', r['testo'], re.I):
                    d['indecisi'] = r['valore']
                    extra += r['valore']
                elif re.search(r'affluenza', r['testo'], re.I):
                    d['affluenzaStimata'] = r['valore']
                elif re.search(r'scheda bianca|astenut|non vot|nulla', r['testo'], re.I):
                    d['astenuti'] = (d.get('astenuti') or 0) + r['valore']
                    extra += r['valore']
            c = d['controlli']
            if not c['ok'] and extra and 97.0 <= round(c['somma'] + extra, 1) <= 101.5:
                # i valori includono indecisi e schede bianche: il denominatore è il totale degli intervistati, non i voti validi
                c['motivi'] = [m for m in c['motivi'] if not m.startswith('somma')]
                c['ok'] = not c['motivi']
                c['nota'] = f'somma con indecisi e schede bianche: {round(c["somma"] + extra, 1)}'
                d['denominatore'] = 'totale'
            domande.append(d)
        elif valide:
            domande.append({'tipo': 'altro', 'testo': q['testo'], 'unita': '%', 'risposte': valide, 'origine': 'testo', 'controlli': {'ok': True, 'motivi': []}, 'rif': f'quesito n. {q["n"]}'})
        elif q['testo'] and not re.search(r'nota metodologica', q['testo'], re.I):
            domande.append({'tipo': 'altro', 'testo': q['testo'], 'unita': '%', 'risposte': [{'testo': v, 'soggetto': None, 'valore': None, 'min': None, 'max': None, 'variazione': None} for v in q['risposte_testo'][:12]],
                            'origine': 'testo', 'controlli': {}, 'rif': f'quesito n. {q["n"]}'})
    ril = {
        'fonte': 'wayback_portale', 'riferimento': idsondaggio, 'titolo': titolo, 'istituto': autore, 'committente': committente, 'editore': acquirente,
        'inizio': inizio.isoformat() if inizio else None, 'fine': fine.isoformat() if fine else None,
        'pubblicato': pubblicato.isoformat() if hasattr(pubblicato, 'isoformat') else pubblicato,
        'criterioData': 'interviste' if fine else 'pubblicazione', 'territorio': territorio, 'popolazione': universo, 'campione': campione,
        'metodo': nota['metodo'] or campi.get('Metodo di raccolta delle informazioni'), 'ponderazione': campi.get('Criteri seguiti per la formazione del campione'),
        'erroreDichiarato': errore, 'nota': ' · '.join(f'{k}: {v}' for k, v in campi.items() if k not in ('_testa', 'QUESTIONARIO', 'INDIETRO') and v)[:1500] or None,
        'livello': 'primaria', 'urls': [url_archivio, f'https://www.sondaggipoliticoelettorali.it/asp/visualizza_sondaggio.asp?idsondaggio={idsondaggio}'],
        'documenti': [{'url': url_archivio, 'tipo': 'html', 'titolo': 'Scheda sul portale (copia Wayback Machine)', 'rif': f'copia del {ts[:4]}-{ts[4:6]}-{ts[6:8]}'}],
        'domande': domande, 'limiti': 'Copia d\'archivio del vecchio portale ufficiale: le tabelle delle risposte sono spesso immagini, non sempre archiviate.',
    }
    if elezione:
        ril['elezione'] = elezione
    immagini = re.findall(r'<img[^>]+src="([^"]+immagini(?:domande|finali)/[^"]+)"', h, re.I)
    for u in immagini[:3]:
        u_ass = urllib.parse.urljoin(url_archivio, html.unescape(u))
        doc = {'url': u_ass, 'tipo': 'immagine', 'titolo': titolo, 'rif': 'immagine delle risposte'}
        if ocr and not any(d['tipo'] == 'voto' for d in domande):
            try:
                dati_img = rete.scarica(u_ass, binario=True)
                # la Wayback Machine risponde con una pagina HTML quando l'immagine non è archiviata
                righe = ocr_righe(dati_img) if dati_img[:4] in (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\x89PNG', b'GIF8') or dati_img[:3] == b'\xff\xd8\xff' else []
                if not righe and dati_img[:3] != b'\xff\xd8\xff' and dati_img[:4] not in (b'\x89PNG', b'GIF8'):
                    doc['rif'] = 'immagine non archiviata dalla Wayback Machine'
            except ConnectionError:
                righe = []
            if righe:
                doc['testo'] = '\n'.join(r['testo'] for r in righe)[:4000]
                risposte, _ = righe_ocr_in_valori(righe, quando_d)
                valide = [r for r in risposte if r['valore'] is not None]
                if elezione and sum(1 for r in valide if r['soggetto']) >= 4:
                    domande.append({'tipo': 'voto', 'elezione': elezione, 'turno': None, 'testo': 'Intenzioni di voto (lettura automatica dell\'immagine)',
                                    'unita': '%', 'denominatore': 'validi', 'risposte': valide, 'origine': 'ocr', 'controlli': controlli_voto(valide), 'documento': u_ass})
                elif valide:
                    domande.append({'tipo': 'altro', 'testo': titolo, 'unita': '%', 'risposte': valide, 'origine': 'ocr', 'controlli': {}, 'documento': u_ass})
        ril['documenti'].append(doc)
    return ril


def aggiorna(fonte: dict, stato: dict, archivio: dict, rete, opzioni: dict) -> dict:
    esecuzione = opzioni['esecuzione']
    limite = int(opzioni.get('limite') or fonte.get('parametri', {}).get('lotto') or 60)
    if opzioni.get('modalita') != 'storico':
        limite = min(limite, 15)  # fonte statica: nei giri quotidiani avanza di poco, il recupero vero è in modalità storico
    ocr = bool(opzioni.get('ocr', True))
    esito = {'letti': 0, 'nuovi': 0, 'aggiornati': 0, 'invariati': 0, 'coda': 0, 'protetti': 0, 'errori': [], 'finito': False}
    conteggio = {'nuova': 'nuovi', 'aggiornata': 'aggiornati', 'invariata': 'invariati', 'coda': 'coda', 'protetta': 'protetti'}
    av = stato.setdefault('avanzamento', {})
    if not av.get('catture'):
        try:
            d = rete.json(CDX)
        except ConnectionError as e:
            esito['errori'].append(str(e))
            return esito
        catture = {}
        for ts, u, s in d[1:]:
            m = re.search(r'idsondaggio=(\d+)', u)
            chiave = ('d', m.group(1)) if m else ('l', u.split('?')[-1])
            if chiave not in catture or ts > catture[chiave][0]:
                catture[chiave] = (ts, u)
        av['catture'] = [[k[0], k[1], ts, u] for k, (ts, u) in sorted(catture.items(), key=lambda x: x[1][0], reverse=True)]
        av['fatte'] = []
        av['elenco'] = {}
    fatte = set(av['fatte'])
    # prima gli elenchi (metadati rapidi), poi i dettagli
    liste = [c for c in av['catture'] if c[0] == 'l' and c[3] not in fatte]
    for tipo, chiave, ts, u in liste[:max(5, limite // 4)]:
        if scaduto(opzioni):
            break
        esito['letti'] += 1
        try:
            h = _decodifica(rete.scarica(WB.format(ts=ts, url=u), binario=True))
            for v in righe_elenco(h):
                av['elenco'][v['id']] = {'data': v['data'].isoformat() if v['data'] else None, 'autore': v['autore'], 'committente': v['committente'], 'titolo': v['titolo'], 'ts': ts}
            fatte.add(u)
        except Exception as e:  # noqa: BLE001
            esito['errori'].append(f'{u}: {type(e).__name__}: {e}')
    dettagli = [c for c in av['catture'] if c[0] == 'd' and c[1] not in fatte]
    for tipo, idsondaggio, ts, u in dettagli[:limite]:
        if scaduto(opzioni):
            break
        esito['letti'] += 1
        url_arch = WB.format(ts=ts, url=u)
        try:
            h = _decodifica(rete.scarica(url_arch, binario=True))
            el = av['elenco'].get(idsondaggio)
            if el and el.get('data'):
                import datetime as dt
                el = dict(el, data=dt.date.fromisoformat(el['data']))
            r = scheda_in_rilevazione(h, url_arch.replace('id_/', '/'), idsondaggio, el, rete, ocr, ts)
            esito[conteggio[inserisci(archivio, r, esecuzione)]] += 1
            fatte.add(idsondaggio)
        except Exception as e:  # noqa: BLE001
            esito['errori'].append(f'{u}: {type(e).__name__}: {e}')
    # schede note solo dall'elenco (dettaglio non archiviato): metadati senza valori
    if not dettagli[limite:] and not liste[max(5, limite // 4):] and not scaduto(opzioni):
        for idsondaggio, el in av['elenco'].items():
            if idsondaggio in fatte:
                continue
            r = {'fonte': 'wayback_portale', 'riferimento': idsondaggio, 'titolo': el['titolo'], 'istituto': el['autore'], 'committente': el['committente'],
                 'pubblicato': el['data'], 'criterioData': 'pubblicazione', 'livello': 'primaria',
                 'urls': [WB.format(ts=el['ts'], url='http://www.sondaggipoliticoelettorali.it/asp/visualizza_sondaggi.asp').replace('id_/', '/')],
                 'documenti': [], 'domande': [], 'limiti': 'Solo riga dell\'elenco del portale (copia Wayback Machine): la scheda di dettaglio non è archiviata.'}
            try:
                esito[conteggio[inserisci(archivio, r, esecuzione)]] += 1
            except Exception as e:  # noqa: BLE001
                esito['errori'].append(f'elenco {idsondaggio}: {e}')
            fatte.add(idsondaggio)
        esito['finito'] = True
        av['storicoCompletato'] = esecuzione.get('inizio')
    av['fatte'] = sorted(fatte)
    return esito
