"""Demos & Pi (demos.it): Atlante Politico (la Repubblica), Osservatorio sul Nord Est (Il Gazzettino),
Osservatorio Capitale Sociale, indagini europee e altre ricerche.

Fonte primaria: le pagine dell'istituto riportano la nota informativa in testo (committente, giorni delle
interviste, campione, metodo, margine d'errore) e i grafici come immagini. I grafici vengono letti con
l'OCR: le tabelle delle intenzioni di voto che superano i controlli entrano come «automatica», tutto il
resto resta allegato come documento con il testo letto e, se contiene numeri, va in coda «da verificare».
L'Osservatorio sul Nord Est riguarda Veneto, Friuli Venezia Giulia e provincia di Trento insieme: il
territorio è registrato come «Nord Est» e non come Friuli Venezia Giulia, salvo che il titolo lo dica.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from archivio import inserisci  # noqa: E402
from comune import data_italiana, pulisci, scaduto  # noqa: E402
from estrai import controlli_voto, nota_informativa, ocr_righe, righe_ocr_in_valori  # noqa: E402

BASE = 'https://www.demos.it/'
SEZIONI = {
    'monitor_italia.php': {'nome': 'Atlante Politico e Società e politica in Italia', 'territorio': {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}},
    'mondo_nordest.php': {'nome': 'Osservatorio sul Nord Est', 'territorio': {'tipo': 'altro', 'nome': 'Nord Est', 'codice': None}},
    'osservatorio.php': {'nome': 'Osservatorio Capitale Sociale', 'territorio': {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}},
    'indagini_europee.php': {'nome': 'Indagini europee', 'territorio': {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}},
    'rapporto.php': {'nome': 'Rapporto Gli italiani e lo Stato', 'territorio': {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}},
    'mappe.php': {'nome': 'Le mappe di Ilvo Diamanti', 'territorio': {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}},
}
RE_VOCE = re.compile(r'<a[^>]+href="(a0\d+\.php)"[^>]*>(.*?)</a>', re.S)


def _testo(h: str) -> str:
    h = re.sub(r'<(script|style).*?</\1>', ' ', h or '', flags=re.S)
    return pulisci(html.unescape(re.sub(r'<[^>]+>', ' ', h)))


def elenco(rete, pagina: str) -> list[dict]:
    """Voci di una pagina di sezione: {url, titolo, data}."""
    h = rete.scarica(BASE + pagina)
    h = re.sub(r'<script.*?</script>', '', h, flags=re.S)
    voci = []
    viste = set()
    for m in re.finditer(r'<strong>(.*?)</strong>.{0,120}?\((\d{1,2} [a-zà]+ \d{4})[^)]*\).{0,200}?href="(a0\d+\.php)"', h, re.S | re.I):
        titolo, data, link = pulisci(html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1)))), data_italiana(m.group(2)), m.group(3)
        if link in viste or not titolo:
            continue
        viste.add(link)
        voci.append({'url': BASE + link, 'titolo': titolo, 'data': data.isoformat() if data else None})
    for m in RE_VOCE.finditer(h):
        link = m.group(1)
        if link not in viste:
            viste.add(link)
            voci.append({'url': BASE + link, 'titolo': pulisci(_testo(m.group(2))), 'data': None})
    return voci


def articolo(rete, voce: dict, sezione: dict, ocr: bool) -> dict:
    h = rete.scarica(voce['url'])
    titolo_pagina = pulisci(html.unescape((re.search(r'<title>(.*?)</title>', h, re.S) or [None, ''])[1]))
    titolo = voce['titolo'] or titolo_pagina.split(' - ')[0]
    testo = _testo(h)
    nota = nota_informativa(testo)
    m = re.search(r'NOTA INFORMATIVA(.{20,900}?)(?:Documentazione completa|home \|)', testo, re.S)
    nota_testo = pulisci(m.group(1)) if m else None
    committente = None
    m = re.search(r'realizzat[oa] da Demos\s*&\s*Pi per ([^.]{3,60}?)(?:\.|,| La rilevazione| Le interviste)', testo)
    if m:
        committente = pulisci(m.group(1))
    elif sezione['nome'].startswith('Osservatorio sul Nord Est'):
        committente = 'Il Gazzettino'
    elif 'Atlante Politico' in titolo or 'Atlante Politico' in sezione['nome']:
        committente = 'la Repubblica'
    territorio = dict(sezione['territorio'])
    if re.search(r'friuli', titolo, re.I) and not re.search(r'veneto|nord ?est', titolo, re.I):
        territorio = {'tipo': 'regione', 'nome': 'Friuli Venezia Giulia', 'codice': 'FVG'}
    elif re.search(r'\bveneto\b', titolo, re.I) and not re.search(r'friuli|nord ?est', titolo, re.I):
        territorio = {'tipo': 'regione', 'nome': 'Veneto', 'codice': None}
    ril = {
        'fonte': 'demos', 'riferimento': voce['url'].rsplit('/', 1)[-1], 'titolo': titolo, 'istituto': 'Demos & Pi',
        'committente': committente, 'editore': committente if committente in ('Il Gazzettino', 'la Repubblica') else None,
        'pubblicato': voce.get('data'), 'inizio': nota['inizio'], 'fine': nota['fine'], 'campione': nota['campione'],
        'metodo': nota['metodo'], 'erroreDichiarato': nota['erroreDichiarato'], 'nota': nota_testo,
        'criterioData': 'interviste' if nota['fine'] else 'pubblicazione', 'territorio': territorio, 'livello': 'primaria',
        'urls': [voce['url']], 'documenti': [], 'domande': [], 'sintesi': testo[testo.find(titolo.upper()) if titolo.upper() in testo else 0:][:400],
        'serieEditoriale': sezione['nome'],
    }
    if 'Atlante Politico' in titolo or 'intenzioni di voto' in testo.lower():
        ril['elezione'] = 'politiche'
    immagini = re.findall(r'<img[^>]+src="(\d{4}/img/[^"]+\.(?:jpe?g|png|gif))"', h, re.I)
    immagini = [BASE + u for u in dict.fromkeys(immagini)]
    trovata = False
    for u in immagini[:8]:
        doc = {'url': u, 'tipo': 'immagine', 'titolo': titolo, 'rif': 'grafico nella pagina'}
        if ocr:
            try:
                righe = ocr_righe(rete.scarica(u, binario=True))
            except ConnectionError:
                righe = []
            if righe:
                doc['testo'] = '\n'.join(r['testo'] for r in righe)[:4000]
                risposte, _ = righe_ocr_in_valori(righe, None)
                voto = [r for r in risposte if r['valore'] is not None and r['soggetto']]
                if not trovata and len(voto) >= 4 and 'voto' in (titolo + ' ' + doc['testo'][:200]).lower():
                    c = controlli_voto([r for r in risposte if r['valore'] is not None])
                    ril['domande'].append({'tipo': 'voto', 'elezione': 'politiche', 'turno': None, 'testo': 'Intenzioni di voto (lettura automatica del grafico)',
                                           'unita': '%', 'denominatore': 'validi', 'risposte': [r for r in risposte if r['valore'] is not None],
                                           'origine': 'ocr', 'controlli': c, 'documento': u})
                    trovata = True
                elif risposte and not trovata:
                    ril['domande'].append({'tipo': 'tema', 'testo': titolo, 'unita': '%', 'denominatore': 'totale',
                                           'risposte': [r for r in risposte if r['valore'] is not None or r['min'] is not None],
                                           'origine': 'ocr', 'controlli': {}, 'documento': u})
        ril['documenti'].append(doc)
    return ril


def aggiorna(fonte: dict, stato: dict, archivio: dict, rete, opzioni: dict) -> dict:
    esecuzione = opzioni['esecuzione']
    modalita = opzioni.get('modalita', 'incrementale')
    limite = int(opzioni.get('limite') or fonte.get('parametri', {}).get('lotto') or 40)
    if modalita != 'storico':
        limite = min(limite, 10)
    ocr = bool(opzioni.get('ocr', True))
    esito = {'letti': 0, 'nuovi': 0, 'aggiornati': 0, 'invariati': 0, 'coda': 0, 'protetti': 0, 'errori': [], 'finito': False}
    conteggio = {'nuova': 'nuovi', 'aggiornata': 'aggiornati', 'invariata': 'invariati', 'coda': 'coda', 'protetta': 'protetti'}
    fatti = set(stato.setdefault('avanzamento', {}).setdefault('letti', []))
    da_fare = []
    for pagina, sezione in SEZIONI.items():
        try:
            for v in elenco(rete, pagina):
                rif = v['url'].rsplit('/', 1)[-1]
                if modalita == 'storico' and rif in fatti:
                    continue
                if modalita != 'storico' and rif in fatti and v['data'] and v['data'] < (stato.get('ultimoRiuscito') or '0')[:10]:
                    continue
                da_fare.append((v, sezione))
        except ConnectionError as e:
            esito['errori'].append(str(e))
    da_fare.sort(key=lambda x: x[0]['data'] or '', reverse=True)
    for v, sezione in da_fare[:limite]:
        if scaduto(opzioni):
            break
        esito['letti'] += 1
        try:
            r = articolo(rete, v, sezione, ocr)
            esito[conteggio[inserisci(archivio, r, esecuzione)]] += 1
            fatti.add(r['riferimento'])
        except Exception as e:  # noqa: BLE001
            esito['errori'].append(f'{v["url"]}: {type(e).__name__}: {e}')
    stato['avanzamento']['letti'] = sorted(fatti)
    esito['finito'] = len(da_fare) <= esito['letti']
    if esito['finito'] and modalita == 'storico':
        stato['avanzamento']['storicoCompletato'] = esecuzione.get('inizio')
    return esito
