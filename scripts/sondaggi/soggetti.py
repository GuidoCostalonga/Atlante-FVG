"""Riconoscimento di partiti, coalizioni, liste e candidati nei testi estratti.

Il dizionario sta in dati/sondaggi/soggetti.json. Il riconoscimento è prudente: una denominazione è
accettata solo se corrisponde a un alias (confronto senza accenti, maiuscole, punteggiatura); nomi non
riconosciuti restano come testo originale con `soggetto: null`, e la rilevazione finisce in coda se il
numero di righe non riconosciute è alto. Non si fondono mai soggetti diversi.
"""
from __future__ import annotations

import datetime as dt
import re

from comune import chiave_testo, leggi_json_locale

_DIZ = None
GRUPPI_UE = {'id', 's', 'd', 's d', 'epp', 'ecr', 'ni', 'renew', 'left', 'g', 'efa', 'g efa', 'gue', 'ngl', 'alde', 'pes', 'efdd', 'enf', 'ppe', 'pse', 'ecr', 'eu', 'ue', 'left g efa'}


def dizionario() -> dict:
    global _DIZ
    if _DIZ is None:
        d = leggi_json_locale('soggetti.json', {'soggetti': []})
        alias = {}
        for s in d['soggetti']:
            for a in [s['nome']] + s.get('alias', []):
                lista = alias.setdefault(chiave_testo(a), [])
                if s['id'] not in lista:
                    lista.append(s['id'])
        _DIZ = {'per_id': {s['id']: s for s in d['soggetti']}, 'alias': alias}
    return _DIZ


def _in_periodo(s: dict, quando: dt.date | None) -> bool:
    if not quando:
        return True
    if s.get('dal') and quando < dt.date.fromisoformat(s['dal']):
        return False
    if s.get('al') and quando > dt.date.fromisoformat(s['al']):
        return False
    return True


def pulisci_nome(testo: str) -> str:
    """Toglie code tipiche delle tabelle: «Fratelli d'Italia (Meloni)» → «Fratelli d'Italia»; «PD*» → «PD»."""
    t = re.sub(r'\s*\((?!Meloni|Schlein|Conte|Salvini|Tajani|Calenda|Renzi|Bonino|Lupi|Magi|Fratoianni|Bonelli|Vannacci|de Magistris|Paragone|Rizzo|Bandecchi)[^)]*\)\s*$', '', testo.strip())
    t = re.sub(r'\s*\([^)]*\)\s*$', '', t)
    t = re.sub(r'[*°^]+$', '', t).strip(' .:;-–')
    return t


def riconosci(testo: str, quando: dt.date | None = None) -> tuple[str | None, str]:
    """Restituisce (id soggetto o None, motivo). Il motivo spiega perché non è stato riconosciuto."""
    if not testo:
        return None, 'vuoto'
    d = dizionario()
    nome = pulisci_nome(testo)
    chiave = chiave_testo(nome)
    if not chiave:
        return None, 'vuoto'
    candidati = d['alias'].get(chiave)
    if not candidati:
        # tollera «Movimento5Stelle», «Fratelli d'ltalia» (l al posto di I nell'OCR)
        chiave2 = chiave.replace(' ', '')
        for k, ids in d['alias'].items():
            if k.replace(' ', '') == chiave2 or k.replace(' ', '').replace('i', 'l') == chiave2.replace('i', 'l'):
                candidati = ids
                break
    if not candidati:
        # «PD Partito Democratico», «M5S Movimento 5 Stelle»: sigla seguita dal nome dello stesso soggetto
        parole = chiave.split()
        for taglio in range(1, len(parole)):
            a, b = d['alias'].get(' '.join(parole[:taglio])), d['alias'].get(' '.join(parole[taglio:]))
            if a and b and set(a) & set(b):
                candidati = list(set(a) & set(b))
                break
    if not candidati:
        # «Lega ID», «PD S&D», «AVS Left – G/EFA»: nome seguito dal gruppo del Parlamento europeo
        parole = chiave.split()
        for taglio in range(len(parole) - 1, 0, -1):
            resto = set(parole[taglio:])
            if resto <= GRUPPI_UE and d['alias'].get(' '.join(parole[:taglio])):
                candidati = d['alias'][' '.join(parole[:taglio])]
                break
    if not candidati:
        senza_articolo = re.sub(r"^(?:l'|il |la |lo |i |gli |le |the )", '', chiave + ' ').strip()
        if senza_articolo != chiave and senza_articolo in d['alias']:
            candidati = d['alias'][senza_articolo]
        else:
            con_articolo = [k for k in d['alias'] if re.sub(r"^(?:l |il |la |lo |i |gli |le )", '', k) == chiave and k != chiave]
            if len(con_articolo) == 1:
                candidati = d['alias'][con_articolo[0]]
    if not candidati:
        return None, 'sconosciuto'
    validi = [c for c in dict.fromkeys(candidati) if _in_periodo(d['per_id'][c], quando)]
    if len(validi) == 1:
        return validi[0], 'ok'
    if not validi:
        return None, 'fuori periodo: ' + ', '.join(candidati)
    return None, 'ambiguo: ' + ', '.join(validi)


def scheda(id_soggetto: str) -> dict | None:
    return dizionario()['per_id'].get(id_soggetto)


def tutti() -> list[dict]:
    return list(dizionario()['per_id'].values())
