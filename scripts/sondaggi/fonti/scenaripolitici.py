"""Scenari Politici (scenaripolitici.com): ripubblica dal 2009 i sondaggi degli istituti italiani.

È una fonte secondaria: i valori stanno quasi sempre in immagini (schermate delle tabelle degli istituti
o delle trasmissioni televisive). Il connettore legge l'elenco degli articoli con l'interfaccia WordPress
(wp-json), ne ricava i metadati (istituto, data di pubblicazione, emittente o giornale, territorio, tipo di
elezione), conserva i collegamenti alle immagini come documenti e, se l'OCR è attivo, prova a leggere le
tabelle delle intenzioni di voto. Le letture che superano i controlli di coerenza entrano come «automatica»;
le altre vanno in coda «da verificare» con il testo letto come prova.

Modalità:
  storico       scorre l'archivio dal più recente al più antico, a lotti; riprende dall'ultimo offset
  incrementale  legge gli articoli pubblicati o modificati dopo l'ultimo giro riuscito
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from archivio import inserisci  # noqa: E402
from comune import adesso, data_italiana, pulisci, registro, scaduto  # noqa: E402
from estrai import controlli_voto, leggi_righe, nota_informativa, ocr_righe, righe_ocr_in_valori  # noqa: E402

BASE = 'https://www.scenaripolitici.com/wp-json/wp/v2/'
CAMPI = 'id,date,modified,link,title,content,excerpt,categories,tags'

# categorie e tag che indicano un territorio o un tipo di elezione (id → significato)
REGIONI = {
    44: 'Friuli Venezia Giulia', 34: 'Abruzzo', 22: 'Basilicata', 67: 'Calabria', 27: 'Campania', 1528: 'Emilia-Romagna',
    1713: 'Lazio', 1766: 'Liguria', 1714: 'Lombardia', 1764: 'Marche', 17: 'Molise', 1762: 'Veneto', 1699: 'Sicilia',
    1753: 'Toscana', 1765: 'Puglia', 49: 'Trentino-Alto Adige', 1752: 'Calabria', 1747: 'Campania',
}
CITTA = {323: 'Trieste', 377: 'Udine', 344: 'Pordenone', 215: 'Gorizia', 1642: 'Roma', 1563: 'Milano', 1546: 'Napoli',
         1649: 'Torino', 1648: 'Bologna', 229: 'Bologna', 1357: 'Bari', 787: 'Cagliari', 1402: 'Barletta-Andria-Trani'}
MEDIA_TAG = {
    1612: 'La7', 1615: 'TG La7', 1634: 'Rai 3', 1639: 'Rai 1', 1616: 'Porta a Porta', 1623: 'Agorà', 1614: 'Piazzapulita',
    1743: 'Agenzia Dire', 1789: 'Rai', 1646: 'Corriere della Sera', 1687: 'Cartabianca', 1663: 'Otto e mezzo',
    1685: 'Sky TG24', 1686: 'Sky', 1720: 'Rete 4', 1622: 'la Repubblica', 1725: 'Quarta Repubblica', 1640: 'Huffington Post',
    1678: 'La Stampa', 1712: 'Rai News 24', 1668: 'Il Sole 24 Ore', 1644: 'TGcom24', 1618: 'Ballarò', 1821: 'Mediaset',
    1683: 'Canale 5', 1684: 'Matrix', 1617: 'TG3', 1619: 'DiMartedì', 1790: 'Studio 24', 1818: 'Omnibus', 1745: 'Rai 2',
    1744: 'Povera Patria', 1777: 'Mezz\'ora in più', 1726: 'Il Giornale',
}
ELEZIONE_TAG = {1552: 'europee', 1836: 'europee', 1729: 'europee', 1698: 'regionali', 1748: 'regionali', 1820: 'regionali',
                1732: 'regionali', 1722: 'comunali', 1782: 'comunali', 1803: 'comunali', 1626: 'referendum', 1691: 'primarie',
                1692: 'primarie', 1728: 'primarie', 86: 'comunali', 706: 'comunali'}
CAT_ELEZIONE = {86: 'comunali', 706: 'comunali', 1552: 'europee'}

RE_TITOLO = re.compile(r'^\s*Sondaggi?o\s+(?P<ist>[^(:–\-]+?)\s*(?:\((?P<data>[^)]*)\))?\s*(?::|–|-|$)', re.I)
RE_COAL = re.compile(r'\b(?P<nome>CDX|CSX|M5S|MS|IBC|CX|PD|PDL|FI|LN|LEGA|FDI|MONTI|SC|NCD|IdV|SEL|UDC|FLI|AN|RC|Centrodestra|Centrosinistra|Centro)\s+(?P<v>\d{1,2}[,.]\d)\s*%?(?:\s*\((?P<var>[-+]\d{1,2}[,.]\d)\s*%?\))?', re.I)
RE_MEDIA = re.compile(r'(?:durante (?:la puntata|l.edizione(?: serale)?|la trasmissione)(?: di| del)?|puntata di|pubblicat[oa] (?:da|su|durante|a|per|nell.edizione di)|per (?:il|la|l.)?|ospite di|a|su|nel corso di)\s+(?P<m>(?:TG\s?La7|TG\s?\d|Tg\s?\w+|Agorà|Porta a Porta|Piazzapulita|Cartabianca|Otto e mezzo|Quarta Repubblica|DiMartedì|Ballarò|Matrix|Omnibus|Coffee Break|Tagadà|L.aria che tira|In Onda|Sky TG24|Sky Tg24|TGcom24|Rai\s?\d|La7|Mediaset|Il Giornale|Il Tempo|Il Messaggero|La Stampa|la Repubblica|Repubblica|Corriere della Sera|Il Fatto Quotidiano|Huffington Post|Affaritaliani|Agenzia Dire|Dire|Il Sole 24 Ore|Libero|QN|Il Mattino|La Nazione|Il Resto del Carlino|Avvenire|Fanpage|Today|Termometro Politico|Europa|Formiche|AGI)[^.,;:(]{0,30})')
NON_DOCUMENTO = ('themes/', 'share-', 'gravatar', '/avatar', 'emoji', 'logo', 'cropped-')


def _testo(h: str) -> str:
    h = re.sub(r'<(script|style).*?</\1>', ' ', h or '', flags=re.S)
    return pulisci(html.unescape(re.sub(r'<[^>]+>', ' ', h)))


def _immagini(contenuto: str) -> list[str]:
    urls = []
    for m in re.finditer(r'<img[^>]+src="([^"]+)"', contenuto or ''):
        u = html.unescape(m.group(1))
        if any(p in u for p in NON_DOCUMENTO) or 'wp-post-image' in m.group(0):
            continue
        # preferisce il collegamento all'originale quando l'immagine è dentro <a href="…png">
        u = re.sub(r'-\d{2,4}x\d{2,4}(\.\w{3,4})$', r'\1', u)
        if u not in urls:
            urls.append(u)
    for m in re.finditer(r'<a[^>]+href="([^"]+\.(?:png|jpe?g|webp|gif|pdf))"', contenuto or '', re.I):
        u = html.unescape(m.group(1))
        if u not in urls and not any(p in u for p in NON_DOCUMENTO):
            urls.append(u)
    return urls[:8]


def _istituto_da_titolo(titolo: str) -> tuple[str | None, str | None]:
    m = RE_TITOLO.match(titolo)
    if not m:
        return None, None
    ist = pulisci(m.group('ist'))
    ist = re.sub(r'^(?:di|per)\s+', '', ist, flags=re.I)
    ist = re.sub(r'\s+(?:per|–|-)\s+.*$', '', ist)
    if re.search(r'\b(regionali|comunali|politiche|europee|elezioni|senato|camera|primarie|nord|sud|centro)\b', ist, re.I):
        # titoli come «Sondaggio SCENARIPOLITICI: FRIULI VENEZIA GIULIA …» hanno il territorio dopo i due punti; qui l'istituto è la prima parola
        ist = ist.split()[0] if ist.split() else ist
    return (ist or None), (m.group('data') or None)


def _territorio(titolo: str, categorie: list[int], tag: list[int], testo: str) -> dict:
    t = titolo.upper()
    for cid, nome in CITTA.items():
        if cid in categorie or cid in tag:
            if nome.upper() in t or 'COMUNAL' in t or 'SINDAC' in t or 'AMMINISTRATIV' in t:
                return {'tipo': 'comune', 'nome': nome, 'codice': None}
    for cid, nome in REGIONI.items():
        if cid in categorie and (nome.upper() in t or 'REGIONAL' in t):
            return {'tipo': 'regione', 'nome': nome, 'codice': 'FVG' if nome.startswith('Friuli') else None}
    if 'FRIULI' in t:
        return {'tipo': 'regione', 'nome': 'Friuli Venezia Giulia', 'codice': 'FVG'}
    m = re.search(r'\b(TRIESTE|UDINE|PORDENONE|GORIZIA|ROMA|MILANO|NAPOLI|TORINO|BOLOGNA|GENOVA|FIRENZE|BARI|PALERMO|VENEZIA|CAGLIARI|CATANIA|MESSINA|VERONA|PADOVA|BRESCIA|PARMA|MODENA|REGGIO|RAVENNA|RIMINI|LATINA|SALERNO|TARANTO|PERUGIA|ANCONA|L.AQUILA|POTENZA|CAMPOBASSO|TRENTO|BOLZANO|AOSTA|SASSARI|LIVORNO|PRATO|PISA|LUCCA|SIENA|AREZZO|MONZA|BERGAMO|COMO|VARESE|NOVARA|ALESSANDRIA|ASTI|CUNEO|SAVONA|LA SPEZIA|TREVISO|VICENZA|BELLUNO|ROVIGO|FERRARA|PIACENZA|FORLI|CESENA|PESARO|MACERATA|ASCOLI|TERNI|VITERBO|RIETI|FROSINONE|PESCARA|CHIETI|TERAMO|FOGGIA|LECCE|BRINDISI|ANDRIA|MATERA|COSENZA|CATANZARO|REGGIO CALABRIA|CROTONE|VIBO|AGRIGENTO|CALTANISSETTA|ENNA|RAGUSA|SIRACUSA|TRAPANI|NUORO|ORISTANO|CARBONIA)\b', t)
    if m and re.search(r'COMUNAL|SINDAC|AMMINISTRATIV|BALLOTTAGG|ELEZIONI (?:A|DI) ', t):
        nome = m.group(1).title()
        return {'tipo': 'comune', 'nome': nome, 'codice': None}
    m = re.search(r'\b(ABRUZZO|BASILICATA|CALABRIA|CAMPANIA|EMILIA[- ]ROMAGNA|LAZIO|LIGURIA|LOMBARDIA|MARCHE|MOLISE|PIEMONTE|PUGLIA|SARDEGNA|SICILIA|TOSCANA|TRENTINO|UMBRIA|VALLE D.AOSTA|VENETO)\b', t)
    if m:
        return {'tipo': 'regione', 'nome': m.group(1).title().replace('Emilia Romagna', 'Emilia-Romagna'), 'codice': None}
    if re.search(r'\bNORD\b|\bSUD\b|\bNORD[- ]EST\b|\bCENTRO[- ]SUD\b|\bISOLE\b', t) and 'SONDAGGIO' in t:
        return {'tipo': 'altro', 'nome': re.search(r'\b(NORD[- ]EST|CENTRO[- ]SUD|NORD|SUD|ISOLE)\b', t).group(1).title(), 'codice': None}
    return {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}


def _elezione(titolo: str, categorie: list[int], tag: list[int], territorio: dict) -> tuple[str | None, str | None]:
    t = titolo.lower()
    turno = 'ballottaggio' if 'ballottagg' in t else None
    if 'europe' in t or any(ELEZIONE_TAG.get(x) == 'europee' for x in tag + categorie):
        return 'europee', turno
    if 'referendum' in t or any(ELEZIONE_TAG.get(x) == 'referendum' for x in tag):
        return 'referendum', turno
    if 'primarie' in t or any(ELEZIONE_TAG.get(x) == 'primarie' for x in tag):
        return 'primarie', turno
    if territorio['tipo'] == 'comune' or 'comunal' in t or 'sindac' in t or 'amministrativ' in t or any(ELEZIONE_TAG.get(x) == 'comunali' for x in tag + categorie):
        return 'comunali', turno
    if 'regional' in t or any(ELEZIONE_TAG.get(x) == 'regionali' for x in tag) or (territorio['tipo'] == 'regione' and 'politich' not in t):
        return 'regionali' if territorio['tipo'] == 'regione' or 'regional' in t else None, turno
    if 'senato' in t or 'camera' in t or 'politich' in t or territorio['tipo'] in ('Italia', 'altro'):
        return 'politiche', turno
    return None, turno


def _editore(testo: str, tag: list[int]) -> str | None:
    for tid, nome in MEDIA_TAG.items():
        if tid in tag:
            return nome
    m = RE_MEDIA.search(testo[:600])
    return pulisci(m.group('m')) if m else None


def _valori_dal_titolo(titolo: str, quando: dt.date | None) -> dict | None:
    """Coalizioni e partiti citati nel titolo dell'articolo (per esempio «CDX 35,4% (+1,0%), CSX 34,4%, M5S 21,2%»)."""
    righe = [f"{m.group('nome')} {m.group('v')}%" + (f" ({m.group('var')})" if m.group('var') else '') for m in RE_COAL.finditer(titolo)]
    if len(righe) < 2:
        return None
    risposte = leggi_righe(righe, quando)
    if not risposte:
        return None
    return {'tipo': 'voto', 'livello': 'coalizioni' if any(r['soggetto'] in ('cdx', 'csx') for r in risposte) else 'partiti',
            'testo': 'Intenzioni di voto (valori riportati nel titolo dell\'articolo)', 'unita': '%', 'denominatore': 'validi',
            'risposte': risposte, 'origine': 'titolo', 'controlli': {'ok': True, 'motivi': [], 'nota': 'estratto parziale dal titolo, non è l\'intera tabella'}}


def _ocr_immagine(rete, url: str, quando: dt.date | None) -> tuple[dict | None, dict, str]:
    """Scarica un'immagine, la legge e prova a ricostruire la tabella delle intenzioni di voto."""
    try:
        dati = rete.scarica(url, binario=True)
    except ConnectionError as e:
        return None, {}, f'immagine non scaricata: {e}'
    righe = ocr_righe(dati)
    if not righe:
        return None, {}, ''
    testo = '\n'.join(r['testo'] for r in righe)
    risposte, nota = righe_ocr_in_valori(righe, quando)
    if not risposte:
        return None, nota, testo
    # tiene solo le voci partito/coalizione, lascia fuori indecisi e simili (già scartati) e gli intervalli
    voto = [r for r in risposte if r['valore'] is not None]
    if len(voto) < 3:
        return None, nota, testo
    c = controlli_voto(voto)
    domanda = {'tipo': 'voto', 'livello': 'partiti', 'testo': 'Intenzioni di voto (lettura automatica dell\'immagine)', 'unita': '%',
               'denominatore': 'validi', 'risposte': voto, 'origine': 'ocr', 'controlli': c, 'documento': url}
    intervalli = [r for r in risposte if r['min'] is not None]
    if intervalli:
        domanda['intervalli'] = intervalli
    return domanda, nota, testo


RE_NON_SONDAGGIO = re.compile(r'^(LIVE|Liveblogging|Risultati|Elezioni .*: |Elezioni (?:Politiche|Regionali|Europee|Amministrative|Comunali) \d{4}(?::| –|$)|Esclusivo|Analisi del voto|Mappa|Speciale|Editoriale|Intervista|Diretta|Exit poll|Proiezioni)', re.I)
RE_SONDAGGIO = re.compile(r'sondagg|governance poll|gradimento|intenzioni di voto|fiducia|rilevazione|supermedia|indagine', re.I)
CAT_SONDAGGI = {1441, 145, 99, 417, 1609}
CAT_NON_SONDAGGI = {529, 392, 438, 172, 1451, 986, 137}  # analisi elettorali, risultati, spogli, ciclismo


def e_sondaggio(p: dict) -> bool:
    titolo = html.unescape(p['title']['rendered'])
    cat = set(p.get('categories') or [])
    if RE_NON_SONDAGGIO.search(titolo) or (cat & CAT_NON_SONDAGGI and not cat & CAT_SONDAGGI):
        return False
    return bool(RE_SONDAGGIO.search(titolo) or cat & CAT_SONDAGGI)


def articolo_in_rilevazione(p: dict, rete, ocr: bool) -> dict:
    titolo = pulisci(html.unescape(p['title']['rendered']))
    contenuto = p['content']['rendered']
    testo = _testo(contenuto)
    categorie, tag = p.get('categories') or [], p.get('tags') or []
    istituto, data_titolo = _istituto_da_titolo(titolo)
    if istituto and istituto.upper() in ('SCENARIPOLITICI', 'SCENARIPOLITICI.COM', 'SCENARI POLITICI', 'SP'):
        istituto = 'Scenari Politici'
    if istituto and istituto.upper() in ('GPG', 'GPG-SP'):
        istituto = 'GPG (Scenari Politici)'
    if istituto and re.search(r'\b(friuli|veneto|lombardia|piemonte|liguria|emilia|toscana|umbria|marche|lazio|abruzzo|molise|campania|puglia|basilicata|calabria|sicilia|sardegna|trentino|valle|nord|sud|centro|italia|senato|camera|politiche|europee|regionali|comunali|roma|milano|napoli|torino|trieste|udine|pordenone|genova|bologna|firenze|palermo|bari|venezia)\b', istituto, re.I):
        istituto = None  # il titolo porta il territorio, non l'istituto: resterà «istituto non riconosciuto» finché una persona non lo indica
    pubblicato = data_italiana(data_titolo) if data_titolo else None
    data_post = dt.date.fromisoformat(p['date'][:10])
    if not pubblicato or abs((data_post - pubblicato).days) > 400:
        pubblicato = pubblicato or data_post
    territorio = _territorio(titolo, categorie, tag, testo)
    elezione, turno = _elezione(titolo, categorie, tag, territorio)
    ril = {
        'fonte': 'scenaripolitici', 'riferimento': str(p['id']), 'titolo': titolo, 'istituto': istituto,
        'committente': None, 'editore': _editore(testo, tag), 'pubblicato': pubblicato.isoformat(),
        'inizio': None, 'fine': None, 'criterioData': 'pubblicazione', 'territorio': territorio,
        'popolazione': None, 'campione': None, 'metodo': None, 'livello': 'secondaria',
        'urls': [p['link']], 'documenti': [], 'domande': [], 'limiti': None,
        'modificato': p.get('modified'), 'sintesi': testo[:400],
    }
    if elezione or turno:
        ril['elezione'], ril['turno'] = elezione, turno
    quando = pubblicato
    dal_titolo = _valori_dal_titolo(titolo, quando)
    if dal_titolo:
        dal_titolo['elezione'], dal_titolo['turno'] = elezione, turno
        ril['domande'].append(dal_titolo)
    immagini = _immagini(contenuto)
    trovata_tabella = False
    for u in immagini:
        doc = {'url': u, 'tipo': 'pdf' if u.lower().endswith('.pdf') else 'immagine', 'titolo': titolo, 'rif': 'immagine nell\'articolo'}
        if ocr and doc['tipo'] == 'immagine' and not trovata_tabella and len(ril['documenti']) < 4:
            domanda, nota, letto = _ocr_immagine(rete, u, quando)
            if letto:
                doc['testo'] = letto[:4000]
            for k in ('inizio', 'fine', 'campione', 'metodo', 'erroreDichiarato'):
                if nota.get(k) and not ril.get(k):
                    ril[k] = nota[k]
            if domanda:
                domanda['elezione'], domanda['turno'] = elezione, turno
                ril['domande'].append(domanda)
                trovata_tabella = True
        ril['documenti'].append(doc)
    if ril.get('fine'):
        ril['criterioData'] = 'interviste'
    nota_testo = nota_informativa(testo)
    for k in ('inizio', 'fine', 'campione', 'metodo', 'erroreDichiarato'):
        if nota_testo.get(k) and not ril.get(k):
            ril[k] = nota_testo[k]
    m = re.search(r'(?:per conto di|commissionat[oa] da|committente:?)\s+([A-Z][^.,;:()]{2,60})', testo)
    if m:
        ril['committente'] = pulisci(m.group(1))
    if 'secondaria' == ril['livello'] and not ril['domande']:
        ril['limiti'] = 'Ripubblicazione: i valori sono nelle immagini allegate e non sono stati letti automaticamente.'
    elif ril['domande'] and all(d.get('origine') in ('titolo', 'ocr') for d in ril['domande']):
        ril['limiti'] = 'Ripubblicazione di Scenari Politici: i valori derivano dal titolo dell\'articolo o dalla lettura automatica delle immagini; il documento originale è presso l\'istituto o sul portale ufficiale.'
    return ril


def aggiorna(fonte: dict, stato: dict, archivio: dict, rete, opzioni: dict) -> dict:
    modalita = opzioni.get('modalita', 'incrementale')
    limite = int(opzioni.get('limite') or fonte.get('parametri', {}).get('lotto') or 100)
    ocr = bool(opzioni.get('ocr', True))
    esecuzione = opzioni['esecuzione']
    esito = {'letti': 0, 'nuovi': 0, 'aggiornati': 0, 'invariati': 0, 'coda': 0, 'protetti': 0, 'errori': [], 'finito': False}
    conteggio = {'nuova': 'nuovi', 'aggiornata': 'aggiornati', 'invariata': 'invariati', 'coda': 'coda', 'protetta': 'protetti'}
    per_pagina = 20
    if modalita == 'storico':
        offset = int(stato.get('avanzamento', {}).get('offset') or 0)
        totale = None
        while esito['letti'] < limite and not scaduto(opzioni):
            url = f'{BASE}posts?per_page={per_pagina}&offset={offset}&orderby=date&order=desc&_fields={CAMPI}'
            try:
                lista = rete.json(url)
            except ConnectionError as e:
                esito['errori'].append(str(e))
                break
            if not lista:
                esito['finito'] = True
                break
            interrotto = False
            for n_p, p in enumerate(lista):
                if scaduto(opzioni):
                    lista = lista[:n_p]
                    interrotto = True
                    break
                esito['letti'] += 1
                if not e_sondaggio(p):
                    esito['saltati'] = esito.get('saltati', 0) + 1
                    continue
                try:
                    r = articolo_in_rilevazione(p, rete, ocr)
                    esito[conteggio[inserisci(archivio, r, esecuzione)]] += 1
                except Exception as e:  # noqa: BLE001
                    esito['errori'].append(f'articolo {p.get("id")}: {type(e).__name__}: {e}')
            offset += len(lista)
            stato.setdefault('avanzamento', {})['offset'] = offset
            if lista:
                stato['avanzamento']['ultimaData'] = lista[-1]['date'][:10]
            if interrotto:
                break
            if len(lista) < per_pagina:
                esito['finito'] = True
                break
        if esito['finito']:
            stato['avanzamento']['storicoCompletato'] = adesso()
    else:
        da = stato.get('ultimoRiuscito') or stato.get('avanzamento', {}).get('incrementaleDa')
        if da:
            da_dt = (dt.datetime.fromisoformat(da.replace('Z', '+00:00')) - dt.timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S')
        else:
            da_dt = (dt.datetime.utcnow() - dt.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S')
        for chiave in ('after', 'modified_after'):
            pagina = 1
            while esito['letti'] < limite and not scaduto(opzioni):
                url = f'{BASE}posts?per_page={per_pagina}&page={pagina}&{chiave}={da_dt}&orderby=date&order=asc&_fields={CAMPI}'
                try:
                    lista = rete.json(url)
                except ConnectionError as e:
                    if 'HTTP 400' in str(e):  # pagina oltre l'ultima
                        break
                    esito['errori'].append(str(e))
                    break
                if not lista:
                    break
                for p in lista:
                    if scaduto(opzioni):
                        break
                    esito['letti'] += 1
                    if not e_sondaggio(p):
                        esito['saltati'] = esito.get('saltati', 0) + 1
                        continue
                    try:
                        r = articolo_in_rilevazione(p, rete, ocr)
                        esito[conteggio[inserisci(archivio, r, esecuzione)]] += 1
                    except Exception as e:  # noqa: BLE001
                        esito['errori'].append(f'articolo {p.get("id")}: {type(e).__name__}: {e}')
                if len(lista) < per_pagina:
                    break
                pagina += 1
        esito['finito'] = not scaduto(opzioni)
    return esito
