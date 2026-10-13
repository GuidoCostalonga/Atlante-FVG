"""Serie storiche comparabili.

Una serie raccoglie le domande dello stesso istituto che sono confrontabili fra loro: stesso tipo, stesso
testo normalizzato (per le intenzioni di voto: stessa elezione, stesso territorio, stesso turno e stesso
scenario), stessa unità e stesso denominatore. Le serie si ricostruiscono a ogni esecuzione dalle
rilevazioni in archivio; le serie dichiarate a mano dal pannello (manuale: true) restano com'è e sono
unite alle automatiche. La pagina usa le serie per tracciare le linee e per calcolare le variazioni
rispetto alla rilevazione comparabile precedente dello stesso istituto, e interrompe la linea dove la
chiave cambia (discontinuità metodologica dichiarata nel campo `nota`).
"""
from __future__ import annotations

import re

from archivio import IN_GRAFICO
from comune import chiave_testo, impronta, slug


def chiave_domanda(ril: dict, d: dict) -> str | None:
    if not ril.get('istituto'):
        return None
    terr = ril.get('territorio') or {}
    pezzi = [ril['istituto'], d.get('tipo') or 'altro', terr.get('tipo') or 'Italia', slug(terr.get('nome') or 'Italia')]
    if d.get('tipo') == 'voto':
        pezzi += [d.get('elezione') or ril.get('elezione') or '', d.get('turno') or '', slug(d.get('scenario') or ''), d.get('livello') or 'partiti', d.get('denominatore') or 'validi']
    else:
        testo = chiave_testo(re.sub(r'\(.*?\)', '', d.get('testo') or ''))
        pezzi += [testo[:80], d.get('unita') or '%', d.get('denominatore') or '', slug(d.get('scala') or '')]
    return impronta(*pezzi)


def ricostruisci_serie(archivio: dict) -> None:
    manuali = {k: v for k, v in archivio.get('serie', {}).items() if v.get('manuale')}
    serie: dict[str, dict] = {}
    for rid, r in archivio['rilevazioni'].items():
        if r.get('stato') not in IN_GRAFICO or not r.get('principale', True):
            continue
        data = r.get('fine') or r.get('pubblicato')
        if not data:
            continue
        for i, d in enumerate(r.get('domande') or []):
            if not any(x.get('valore') is not None for x in d.get('risposte', [])):
                continue
            k = chiave_domanda(r, d)
            if not k:
                continue
            s = serie.setdefault(k, {'id': k, 'istituto': r['istituto'], 'tipo': d.get('tipo'), 'testo': d.get('testo'), 'elezione': d.get('elezione') or r.get('elezione'),
                                     'turno': d.get('turno'), 'scenario': d.get('scenario'), 'territorio': r.get('territorio'), 'unita': d.get('unita'),
                                     'denominatore': d.get('denominatore'), 'livello': d.get('livello'), 'punti': [], 'soggetti': []})
            s['punti'].append({'rilevazione': rid, 'domanda': i, 'data': data, 'criterioData': r.get('criterioData'), 'campione': r.get('campione'), 'stato': r.get('stato')})
            for x in d.get('risposte', []):
                et = x.get('soggetto') or ('t:' + chiave_testo(x.get('testo') or ''))
                if et not in s['soggetti']:
                    s['soggetti'].append(et)
    for s in serie.values():
        s['punti'].sort(key=lambda p: p['data'])
        s['prima'], s['ultima'], s['n'] = s['punti'][0]['data'], s['punti'][-1]['data'], len(s['punti'])
        # intervalli lunghi senza osservazioni (oltre 180 giorni) vengono annotati: la pagina li evidenzia
        import datetime as dt
        buchi = []
        for a, b in zip(s['punti'], s['punti'][1:]):
            da, db = dt.date.fromisoformat(a['data']), dt.date.fromisoformat(b['data'])
            if (db - da).days > 180:
                buchi.append([a['data'], b['data']])
        s['buchi'] = buchi
    serie.update(manuali)
    archivio['serie'] = serie
