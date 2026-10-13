"""Inserimento delle rilevazioni nell'archivio: controlli, coda «da verificare», doppioni, revisioni.

Una rilevazione proposta da un connettore è un dizionario con questi campi (tutti facoltativi salvo
`fonte`, `riferimento`, `titolo`):

  fonte           id della fonte (chiave di dati/sondaggi/fonti.json)
  riferimento     identificativo stabile presso la fonte (per esempio l'id dell'articolo): serve a
                  riconoscere la stessa pubblicazione negli aggiornamenti successivi
  titolo, istituto, committente, editore
  inizio, fine    date delle interviste (ISO) · pubblicato · criterioData ('interviste'|'pubblicazione')
  territorio      {tipo: 'Italia'|'regione'|'comune'|'sottocampione'|'altro', nome, codice}
  popolazione, campione, sottocampione, metodo, ponderazione, nota, erroreDichiarato
  livello         'primaria' (documento dell'istituto o del committente) | 'secondaria' (ripubblicazione)
  domande         elenco di domande (vedi sotto)
  documenti       elenco di {url, tipo ('html'|'pdf'|'immagine'|'csv'), titolo, rif (pagina/tabella), testo}
  urls            indirizzi consultabili (il primo è quello principale)
  limiti          note sui limiti del dato (testo)

Una domanda: {tipo: 'voto'|'fiducia'|'priorita'|'economia'|'servizi'|'tema'|'scenario'|'altro',
  elezione: 'politiche'|'europee'|'regionali'|'comunali'|'referendum'|null, turno: 'primo'|'ballottaggio'|null,
  scenario (testo), testo (domanda originale), scala, unita ('%'|'punteggio'|'saldo'|'seggi'),
  denominatore ('validi'|'totale'|null), indecisi, astenuti (valori % se noti),
  risposte: [{soggetto (id o null), testo, valore, min, max, variazione}],
  origine: 'tabella'|'testo'|'ocr'|'titolo'|'manuale', controlli: {...}}

Stati di una rilevazione: 'verificata' (controllata da una persona), 'automatica' (importata con i controlli
superati), 'secondaria' (fonte secondaria con valori), 'senza_valori' (solo metadati e documenti),
'da_verificare' (in coda), 'scartata'. Nei grafici entrano verificata, automatica e secondaria.
"""
from __future__ import annotations

import datetime as dt
import re

from comune import adesso, chiave_testo, impronta, leggi_json_locale, pulisci, slug

IN_GRAFICO = ('verificata', 'automatica', 'secondaria')
_REGISTRO = None


def registro_istituti() -> dict:
    """Alias → id canonico, dal registro dati/sondaggi/istituti.json."""
    global _REGISTRO
    if _REGISTRO is None:
        d = leggi_json_locale('istituti.json', {'istituti': []})
        _REGISTRO = {'alias': {}, 'schede': {}}
        for s in d['istituti']:
            _REGISTRO['schede'][s['id']] = s
            for a in [s['nome']] + s.get('alias', []):
                _REGISTRO['alias'].setdefault(chiave_testo(a), s['id'])
    return _REGISTRO


def id_rilevazione(fonte: str, riferimento: str) -> str:
    return impronta(fonte, str(riferimento))


def id_istituto(nome: str) -> str:
    return slug(nome)[:40] or 'istituto-sconosciuto'


def registra_istituto(archivio: dict, nome: str | None, fonte: str) -> str | None:
    if not nome:
        return None
    nome = pulisci(nome)
    reg = registro_istituti()
    iid = reg['alias'].get(chiave_testo(nome))
    if not iid:
        # tollera suffissi come «S.p.A.», «srl», «Ricerche» e il nome di una persona tra parentesi
        base = chiave_testo(re.sub(r'\s*\(.*?\)|\b(s\.?p\.?a\.?|s\.?r\.?l\.?|srl|spa|ricerche|research|italia|group)\b', '', nome, flags=re.I))
        iid = reg['alias'].get(base)
    if not iid:
        iid = id_istituto(nome)
        for i, s in archivio['istituti'].items():
            if iid == i or chiave_testo(nome) in [chiave_testo(a) for a in s.get('alias', [])]:
                iid = i
                break
    scheda_reg = reg['schede'].get(iid, {})
    s = archivio['istituti'].setdefault(iid, {'nome': scheda_reg.get('nome') or nome, 'alias': list(scheda_reg.get('alias', [])), 'sito': scheda_reg.get('sito'),
                                              'fonti': [], 'rilevazioni': 0, 'prima': None, 'ultima': None})
    if nome not in s['alias'] and nome != s['nome']:
        s['alias'].append(nome)
    if fonte not in s['fonti']:
        s['fonti'].append(fonte)
    return iid


def _decidi_stato(ril: dict) -> tuple[str, list[str]]:
    """Stato iniziale della rilevazione e motivi di un'eventuale messa in coda."""
    motivi = []
    domande = ril.get('domande') or []
    con_valori = [d for d in domande if any(r.get('valore') is not None or r.get('min') is not None for r in d.get('risposte', []))]
    if not con_valori:
        return 'senza_valori', []
    for d in con_valori:
        c = d.get('controlli') or {}
        if d.get('tipo') == 'voto' and c and not c.get('ok'):
            motivi.extend(c.get('motivi') or ['controlli non superati'])
        if d.get('origine') == 'ocr' and not c:
            motivi.append('estrazione OCR senza controlli')
        if d.get('origine') == 'ocr' and d.get('tipo') != 'voto':
            motivi.append('lettura automatica di un grafico non elettorale: va confrontata con l\'immagine')
    if not ril.get('istituto'):
        motivi.append('istituto non riconosciuto')
    if not (ril.get('fine') or ril.get('pubblicato')):
        motivi.append('nessuna data')
    if motivi:
        return 'da_verificare', sorted(set(motivi))
    return ('secondaria' if ril.get('livello') == 'secondaria' else 'automatica'), []


def _chiave_gemelli(ril: dict) -> str | None:
    """Stessa rilevazione pubblicata da fonti diverse: stesso istituto, stesso territorio, stessa data
    (fine interviste o pubblicazione) e stesso tipo di elezione della prima domanda di voto."""
    if not ril.get('istituto'):
        return None
    data = ril.get('fine') or ril.get('pubblicato')
    if not data:
        return None
    voto = next((d for d in ril.get('domande') or [] if d.get('tipo') == 'voto'), None)
    terr = (ril.get('territorio') or {}).get('nome') or 'Italia'
    return impronta(ril['istituto'], data, slug(terr), (voto or {}).get('elezione') or '', (voto or {}).get('turno') or '')


def inserisci(archivio: dict, proposta: dict, esecuzione: dict) -> str:
    """Inserisce o aggiorna una rilevazione. Restituisce 'nuova', 'aggiornata', 'invariata', 'coda' o 'protetta'.
    Le rilevazioni con una revisione manuale (`protetta: true`) non vengono toccate dagli aggiornamenti
    automatici: si registra soltanto la nuova acquisizione nei documenti."""
    rid = id_rilevazione(proposta['fonte'], proposta['riferimento'])
    proposta['id'] = rid
    proposta['istituto'] = registra_istituto(archivio, proposta.get('istituto'), proposta['fonte']) if proposta.get('istituto') else None
    proposta.setdefault('livello', 'primaria')
    proposta.setdefault('territorio', {'tipo': 'Italia', 'nome': 'Italia', 'codice': 'IT'})
    proposta.setdefault('criterioData', 'interviste' if proposta.get('fine') else 'pubblicazione')
    proposta['acquisito'] = adesso()
    proposta['gemelli'] = _chiave_gemelli(proposta)
    esistente = archivio['rilevazioni'].get(rid)
    if esistente and esistente.get('protetta'):
        esistente['ultimaAcquisizione'] = proposta['acquisito']
        return 'protetta'
    stato, motivi = _decidi_stato(proposta)
    proposta['stato'] = stato
    proposta['motiviCoda'] = motivi
    if esistente:
        # confronto senza i campi che cambiano a ogni giro
        def nucleo(r):
            return {k: v for k, v in r.items() if k not in ('acquisito', 'ultimaAcquisizione', 'stato', 'motiviCoda')}
        if nucleo(esistente) == nucleo(proposta):
            esistente['ultimaAcquisizione'] = proposta['acquisito']
            return 'invariata'
        if esistente.get('stato') == 'verificata':
            # il dato verificato resta; la novità finisce in coda come «documento modificato»
            _in_coda(archivio, proposta, ['la fonte è cambiata dopo la verifica manuale'], esecuzione, rid_esistente=rid)
            esistente['ultimaAcquisizione'] = proposta['acquisito']
            return 'coda'
        proposta['storico'] = (esistente.get('storico') or []) + [{'quando': esistente.get('acquisito'), 'stato': esistente.get('stato')}]
        proposta['primaAcquisizione'] = esistente.get('primaAcquisizione') or esistente.get('acquisito')
    else:
        proposta['primaAcquisizione'] = proposta['acquisito']
    archivio['rilevazioni'][rid] = proposta
    if stato == 'da_verificare':
        _in_coda(archivio, proposta, motivi, esecuzione)
    elif rid in archivio['coda']:
        del archivio['coda'][rid]
    return 'aggiornata' if esistente else ('coda' if stato == 'da_verificare' else 'nuova')


def _in_coda(archivio: dict, ril: dict, motivi: list[str], esecuzione: dict, rid_esistente: str | None = None) -> None:
    cid = rid_esistente or ril['id']
    voce = archivio['coda'].get(cid) or {'id': cid, 'creata': adesso()}
    voce.update({'rilevazione': ril['id'], 'titolo': ril.get('titolo'), 'fonte': ril['fonte'], 'motivi': motivi,
                 'esecuzione': esecuzione.get('id'), 'aggiornata': adesso(), 'stato': 'aperta'})
    if rid_esistente and rid_esistente != ril['id']:
        voce['proposta'] = ril
    archivio['coda'][cid] = voce


def applica_revisione(archivio: dict, rev: dict) -> str:
    """Applica una revisione manuale (dal pannello di gestione). Tipi:
      correzione   {rilevazione, campi: {...}, domande: [...]?, nota}  → sostituisce i campi indicati, stato 'verificata', protetta
      approva      {rilevazione}                                       → stato 'verificata' con i valori proposti
      scarta       {rilevazione, nota}                                 → stato 'scartata', esclusa dai grafici
      istituto     {id, nome?, alias?, sito?, note?}                   → scheda istituto
      soggetto     {id, nome, alias, ...}                              → aggiunge/aggiorna un soggetto (gestito a parte)
      fonte        {id, attiva?, nome?, url?, tipo?, parametri?}        → registro fonti (gestito da aggiorna.py)
      serie        {id, domande: [...], nome, nota}                     → serie comparabile dichiarata a mano
      manuale      {rilevazione: {...}}                                 → rilevazione inserita a mano, verificata
    Restituisce una descrizione dell'esito."""
    tipo = rev.get('tipo')
    if tipo in ('correzione', 'approva', 'scarta'):
        rid = rev.get('rilevazione')
        ril = archivio['rilevazioni'].get(rid)
        if not ril:
            return f'rilevazione {rid} non trovata'
        if tipo == 'correzione':
            prima = {k: ril.get(k) for k in (rev.get('campi') or {})}
            ril.update(rev.get('campi') or {})
            if rev.get('domande') is not None:
                prima['domande'] = ril.get('domande')
                ril['domande'] = rev['domande']
            ril['stato'] = 'verificata'
            ril['protetta'] = True
            ril.setdefault('revisioni', []).append({'quando': rev.get('quando') or adesso(), 'autore': rev.get('autore'), 'nota': rev.get('nota'), 'prima': prima})
        elif tipo == 'approva':
            ril['stato'] = 'verificata'
            ril['protetta'] = True
            ril['motiviCoda'] = []
            ril.setdefault('revisioni', []).append({'quando': rev.get('quando') or adesso(), 'autore': rev.get('autore'), 'nota': rev.get('nota') or 'approvata dalla coda'})
        else:
            ril['stato'] = 'scartata'
            ril['protetta'] = True
            ril.setdefault('revisioni', []).append({'quando': rev.get('quando') or adesso(), 'autore': rev.get('autore'), 'nota': rev.get('nota') or 'scartata'})
        archivio['coda'].pop(rid, None)
        return f'{tipo}: {rid}'
    if tipo == 'istituto':
        s = archivio['istituti'].setdefault(rev['id'], {'nome': rev.get('nome') or rev['id'], 'alias': [], 'fonti': [], 'rilevazioni': 0})
        for k in ('nome', 'alias', 'sito', 'note', 'tipo'):
            if rev.get(k) is not None:
                s[k] = rev[k]
        return f'istituto: {rev["id"]}'
    if tipo == 'serie':
        archivio['serie'][rev['id']] = {k: rev[k] for k in rev if k not in ('tipo', 'quando', 'autore')}
        archivio['serie'][rev['id']]['manuale'] = True
        return f'serie: {rev["id"]}'
    if tipo == 'manuale':
        ril = dict(rev['rilevazione'])
        ril.setdefault('fonte', 'manuale')
        ril.setdefault('riferimento', rev.get('quando') or adesso())
        ril['id'] = id_rilevazione(ril['fonte'], ril['riferimento'])
        ril['istituto'] = registra_istituto(archivio, ril.get('istituto'), 'manuale')
        ril['stato'] = 'verificata'
        ril['protetta'] = True
        ril['acquisito'] = ril['primaAcquisizione'] = adesso()
        ril['gemelli'] = _chiave_gemelli(ril)
        ril.setdefault('revisioni', []).append({'quando': rev.get('quando') or adesso(), 'autore': rev.get('autore'), 'nota': rev.get('nota') or 'inserita a mano'})
        archivio['rilevazioni'][ril['id']] = ril
        return f'manuale: {ril["id"]}'
    return f'tipo di revisione sconosciuto: {tipo}'


def ricalcola_riepiloghi(archivio: dict) -> None:
    """Conteggi per istituto, ultima rilevazione disponibile, gruppi di gemelli."""
    for s in archivio['istituti'].values():
        s['rilevazioni'] = 0
        s['prima'] = s['ultima'] = None
    ultima = None
    gruppi: dict[str, list[str]] = {}
    for rid, r in archivio['rilevazioni'].items():
        if r.get('stato') == 'scartata':
            continue
        data = r.get('fine') or r.get('pubblicato')
        if r.get('istituto') in archivio['istituti']:
            s = archivio['istituti'][r['istituto']]
            s['rilevazioni'] += 1
            if data:
                s['prima'] = min(s['prima'] or data, data)
                s['ultima'] = max(s['ultima'] or data, data)
        if data and r.get('stato') in IN_GRAFICO:
            ultima = max(ultima or data, data)
        if r.get('gemelli'):
            gruppi.setdefault(r['gemelli'], []).append(rid)
    archivio['ultimaRilevazione'] = ultima
    # in ogni gruppo di gemelli una sola rilevazione è «principale» per i grafici: la più affidabile
    ordine = {'verificata': 0, 'automatica': 1, 'secondaria': 2, 'senza_valori': 3, 'da_verificare': 4, 'scartata': 5}
    for rid, r in archivio['rilevazioni'].items():
        r['principale'] = True
    for g, ids in gruppi.items():
        if len(ids) < 2:
            continue
        ids.sort(key=lambda i: (ordine.get(archivio['rilevazioni'][i].get('stato'), 9), 0 if archivio['rilevazioni'][i].get('livello') == 'primaria' else 1, i))
        for i in ids[1:]:
            archivio['rilevazioni'][i]['principale'] = False
            archivio['rilevazioni'][i]['principaleDi'] = ids[0]
