"""SWG (swg.it): il «Radar» settimanale in PDF, con la nota informativa in testo e i grafici come immagini.

La pagina /osservatorio collega soltanto l'ultimo Radar: la storia si costruisce giro dopo giro (e con le
copie della Wayback Machine, lette dalla fonte `wayback_swg` quando attiva). Le pagine del PDF con gli
orientamenti di voto vengono rese come immagine e lette con l'OCR; le pagine con le tabelle testuali
(fiducia nelle istituzioni) restano come documento con il testo, in coda se contengono numeri.
"""
from __future__ import annotations

import hashlib
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from archivio import inserisci  # noqa: E402
from comune import impronta, intervallo_date, pulisci, scaduto  # noqa: E402
from estrai import controlli_voto, nota_informativa, ocr_righe, righe_ocr_in_valori, righe_pdf_parole, testo_pdf  # noqa: E402

BASE = 'https://www.swg.it/osservatorio'


def pagina_in_immagine(dati: bytes, numero_pagina: int, scala: float = 2.0) -> bytes | None:
    """Rende una pagina del PDF in PNG (pypdfium2) per leggerla con l'OCR."""
    try:
        import io
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(dati)
        pagina = doc[numero_pagina - 1]
        img = pagina.render(scale=scala).to_pil()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return None


def radar_in_rilevazione(url: str, dati: bytes, ocr: bool, titolo: str | None = None) -> dict:
    pagine = testo_pdf(dati)
    tutto = '\n'.join(pagine)
    m = re.search(r'Radar SWG,?\s*(\d{1,2}(?:\s+[a-zà]+)?\s*[-–]\s*\d{1,2}\s+[a-zà]+\s+\d{4})', html.unescape(url) + ' ' + tutto[:400])
    periodo = m.group(1) if m else None
    inizio, fine = intervallo_date(periodo) if periodo else (None, None)
    ril = {
        'fonte': 'swg', 'riferimento': hashlib.sha256(dati).hexdigest()[:16], 'titolo': titolo or ('Radar SWG ' + (periodo or '')).strip(),
        'istituto': 'SWG', 'committente': 'SWG (in proprio); intenzioni di voto per La7', 'editore': 'TG La7',
        'inizio': None, 'fine': None, 'campione': None, 'metodo': None, 'erroreDichiarato': None, 'pubblicato': fine.isoformat() if fine else None, 'criterioData': 'pubblicazione',
        'territorio': {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'}, 'livello': 'primaria', 'urls': [url],
        'documenti': [{'url': url, 'tipo': 'pdf', 'titolo': 'Radar SWG', 'rif': 'documento completo'}], 'domande': [],
        'elezione': 'politiche', 'serieEditoriale': 'Radar SWG',
    }
    for n, t in enumerate(pagine, 1):
        corto = len(pulisci(t)) < 600
        if not (re.search(r'(orientamenti|intenzioni) di voto', pulisci(t), re.I) or corto) or n == 1:
            continue
        if not ocr or any(d.get('tipo') == 'voto' for d in ril['domande']):
            continue
        # prima le parole del PDF (testo vero), poi l'OCR della pagina resa come immagine
        righe = righe_pdf_parole(dati, n) if not corto else []
        testo_ocr = '\n'.join(r['testo'] for r in righe)
        def e_voto(s):
            return re.search(r'(orientamenti|intenzioni) di voto', re.sub(r'[\s|]+', ' ', s), re.I)
        if not e_voto(testo_ocr) or sum(1 for r in righe_ocr_in_valori(righe, None)[0] if r['soggetto']) < 4:
            png = pagina_in_immagine(dati, n)
            righe = ocr_righe(png) if png else []
            if not righe:
                continue
            testo_ocr = '\n'.join(r['testo'] for r in righe)
        if not e_voto(testo_ocr):
            continue
        risposte, nota_ocr = righe_ocr_in_valori(righe, None)
        voto = [r for r in risposte if r['valore'] is not None]
        if sum(1 for r in voto if r['soggetto']) >= 4:
            ril['domande'].append({'tipo': 'voto', 'elezione': 'politiche', 'turno': None, 'testo': 'Orientamenti di voto (lettura automatica della pagina del Radar)',
                                   'unita': '%', 'denominatore': 'validi', 'risposte': voto, 'origine': 'ocr', 'controlli': controlli_voto(voto),
                                   'documento': url, 'rif': f'pagina {n}'})
            ril['documenti'][0]['testo'] = testo_ocr[:4000]
            ril['documenti'][0]['rif'] = f'pagina {n}'
            nota = nota_informativa(t + ' ' + testo_ocr)
            for k in ('inizio', 'fine', 'campione', 'metodo', 'erroreDichiarato'):
                if nota.get(k) or nota_ocr.get(k):
                    ril[k] = nota.get(k) or nota_ocr.get(k)
            m = re.search(r'non si esprim\w*\s*:?\s*(\d{1,2}(?:[,.]\d)?)\s*%', testo_ocr, re.I)
            if m:
                ril['domande'][-1]['indecisi'] = float(m.group(1).replace(',', '.'))
    if ril.get('fine'):
        ril['criterioData'] = 'interviste'
    titoli = [pulisci(r) for r in pagine[0].split('\n') if pulisci(r)][:8] if pagine else []
    ril['sintesi'] = ' · '.join(titoli)[:400]
    return ril


def aggiorna(fonte: dict, stato: dict, archivio: dict, rete, opzioni: dict) -> dict:
    esecuzione = opzioni['esecuzione']
    ocr = bool(opzioni.get('ocr', True))
    esito = {'letti': 0, 'nuovi': 0, 'aggiornati': 0, 'invariati': 0, 'coda': 0, 'protetti': 0, 'errori': [], 'finito': True}
    conteggio = {'nuova': 'nuovi', 'aggiornata': 'aggiornati', 'invariata': 'invariati', 'coda': 'coda', 'protetta': 'protetti'}
    try:
        h = rete.scarica(BASE)
    except ConnectionError as e:
        esito['errori'].append(str(e))
        return esito
    links = [html.unescape(u) for u in re.findall(r'href="([^"]+/pa/attachment/[^"]+\.pdf)"', h, re.I)]
    visti = set(stato.setdefault('avanzamento', {}).setdefault('pdf', []))
    for u in dict.fromkeys(links):
        if u in visti:
            esito['invariati'] += 1
            continue
        if scaduto(opzioni):
            esito['finito'] = False
            break
        esito['letti'] += 1
        try:
            dati = rete.scarica(u, binario=True)
            r = radar_in_rilevazione(u, dati, ocr)
            esito[conteggio[inserisci(archivio, r, esecuzione)]] += 1
            visti.add(u)
        except Exception as e:  # noqa: BLE001
            esito['errori'].append(f'{u}: {type(e).__name__}: {e}')
    stato['avanzamento']['pdf'] = sorted(visti)[-400:]
    return esito
