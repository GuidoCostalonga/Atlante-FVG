"""Orchestratore dell'Osservatorio sondaggi.

Uso:
  python3 scripts/sondaggi/aggiorna.py --cartella <ramo sondaggi-dati> [--modalita incrementale|storico|ricontrollo]
                                       [--fonti a,b,c] [--limite N] [--senza-ocr] [--minuti 25]

La cartella è una copia di lavoro del ramo `sondaggi-dati`: contiene `archivio.json` (cifrato), `stato.json`
(cifrato), `revisioni/*.json` e `caricati/*.json` scritti dal pannello (cifrati con la stessa chiave).
Lo script:
  1. legge archivio e stato (se mancano, parte da vuoto);
  2. applica le revisioni non ancora applicate (correzioni, approvazioni, scarti, fonti, istituti, serie);
  3. per ogni fonte attiva esegue il connettore nella modalità richiesta, con un tempo massimo complessivo:
     un errore di una fonte non tocca le altre né i dati esistenti;
  4. ricalcola riepiloghi, serie comparabili e il registro delle esecuzioni;
  5. riscrive archivio e stato. Il codice di uscita è 0 anche con errori parziali (sono nel registro);
     è 2 solo se non è stato possibile scrivere l'archivio.

Modalità:
  incrementale  novità dall'ultimo giro riuscito (quotidiana);
  storico       recupero a lotti dell'archivio delle fonti, riprendibile (ogni esecuzione avanza di un lotto);
  ricontrollo   rilegge le rilevazioni acquisite negli ultimi 60 giorni per cogliere documenti corretti.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'fonti'))
from archivio import applica_revisione, ricalcola_riepiloghi  # noqa: E402
from comune import ROMA, Rete, adesso, decifra_json, impronta, leggi_archivio, leggi_json_locale, registro, scrivi_archivio  # noqa: E402
from serie import ricostruisci_serie  # noqa: E402

CONNETTORI = {'wordpress': 'scenaripolitici', 'wikipedia': 'wikipedia', 'demos': 'demos', 'swg': 'swg', 'wayback_portale': 'wayback_portale', 'caricamenti': 'caricamenti'}


def leggi_cifrato(p: Path):
    try:
        return decifra_json(p.read_bytes())
    except Exception as e:  # noqa: BLE001
        registro(f'file non leggibile {p.name}: {e}')
        return None


def fonti_configurate(archivio: dict) -> list[dict]:
    """Registro delle fonti: file dati/sondaggi/fonti.json più le modifiche fatte dal pannello (revisioni «fonte»)."""
    base = {f['id']: dict(f) for f in leggi_json_locale('fonti.json', {'fonti': []})['fonti']}
    for rev in archivio.get('revisioniFonti', []):
        f = base.setdefault(rev['id'], {'id': rev['id'], 'nome': rev['id'], 'tipo': rev.get('tipo', 'wordpress'), 'attiva': True, 'parametri': {}})
        for k in ('attiva', 'nome', 'url', 'tipo', 'parametri', 'copertura', 'accesso', 'livello'):
            if rev.get(k) is not None:
                f[k] = rev[k]
    return list(base.values())


def applica_revisioni(cartella: Path, archivio: dict) -> list[str]:
    applicate = {r['file'] for r in archivio.get('revisioni', []) if r.get('file')}
    esiti = []
    for p in sorted((cartella / 'revisioni').glob('*.json')) if (cartella / 'revisioni').exists() else []:
        if p.name in applicate:
            continue
        rev = leggi_cifrato(p)
        if not isinstance(rev, dict):
            esiti.append(f'{p.name}: non leggibile')
            continue
        rev.setdefault('quando', adesso())
        try:
            if rev.get('tipo') == 'fonte':
                archivio.setdefault('revisioniFonti', []).append(rev)
                esito = f'fonte: {rev.get("id")} attiva={rev.get("attiva")}'
            elif rev.get('tipo') == 'restrizione':
                archivio.setdefault('restrizioniExtra', []).append(rev)
                esito = f'restrizione: {rev.get("nome")}'
            elif rev.get('tipo') == 'soggetto':
                archivio.setdefault('soggettiExtra', {})[rev['id']] = {k: v for k, v in rev.items() if k not in ('tipo', 'file')}
                esito = f'soggetto: {rev["id"]}'
            else:
                esito = applica_revisione(archivio, rev)
        except Exception as e:  # noqa: BLE001
            esito = f'errore: {type(e).__name__}: {e}'
        archivio.setdefault('revisioni', []).append({'file': p.name, 'tipo': rev.get('tipo'), 'quando': rev.get('quando'), 'autore': rev.get('autore'),
                                                     'rilevazione': rev.get('rilevazione'), 'nota': rev.get('nota'), 'esito': esito, 'applicata': adesso()})
        esiti.append(f'{p.name}: {esito}')
    return esiti


def leggi_caricamenti(cartella: Path) -> list[dict]:
    esito = []
    for p in sorted((cartella / 'caricati').glob('*.json')) if (cartella / 'caricati').exists() else []:
        c = leggi_cifrato(p)
        if isinstance(c, dict):
            c.setdefault('id', p.stem)
            esito.append(c)
    return esito


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cartella', required=True)
    ap.add_argument('--modalita', default='incrementale', choices=['incrementale', 'storico', 'ricontrollo'])
    ap.add_argument('--fonti', default='')
    ap.add_argument('--limite', type=int, default=0)
    ap.add_argument('--senza-ocr', action='store_true')
    ap.add_argument('--minuti', type=float, default=25.0, help='tempo massimo complessivo per i connettori')
    ap.add_argument('--esecutore', default='locale')
    a = ap.parse_args()
    cartella = Path(a.cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    inizio = time.monotonic()
    archivio = leggi_archivio(cartella / 'archivio.json')
    stato_p = cartella / 'stato.json'
    stato = leggi_cifrato(stato_p) if stato_p.exists() else None
    stato = stato if isinstance(stato, dict) else {'fonti': {}}
    stato.setdefault('fonti', {})
    esecuzione = {'id': impronta(adesso(), a.modalita, str(time.time())), 'inizio': adesso(), 'modalita': a.modalita, 'esecutore': a.esecutore,
                  'fonti': {}, 'revisioni': [], 'errori': [], 'fine': None, 'esito': None}
    archivio['ultimoTentativo'] = esecuzione['inizio']
    registro(f'esecuzione {esecuzione["id"]} ({a.modalita}); archivio con {len(archivio["rilevazioni"])} rilevazioni')

    esecuzione['revisioni'] = applica_revisioni(cartella, archivio)
    for e in esecuzione['revisioni']:
        registro('revisione ' + e)

    rete = Rete(pausa=1.0)
    scelte = {x.strip() for x in a.fonti.split(',') if x.strip()}
    caricamenti = leggi_caricamenti(cartella)
    fonti = fonti_configurate(archivio)
    archivio['fonti'] = {f['id']: {k: f.get(k) for k in ('id', 'nome', 'tipo', 'livello', 'attiva', 'url', 'copertura', 'accesso')} for f in fonti}
    riuscite = 0
    for f in fonti:
        fid = f['id']
        st = stato['fonti'].setdefault(fid, {'ultimoTentativo': None, 'ultimoRiuscito': None, 'errore': None, 'avanzamento': {}})
        if scelte and fid not in scelte:
            continue
        if not f.get('attiva') or f.get('tipo') not in CONNETTORI:
            continue
        if a.modalita == 'storico' and st.get('avanzamento', {}).get('storicoCompletato') and f['tipo'] in ('wordpress', 'wayback_portale', 'demos'):
            registro(f'{fid}: storico già completato il {st["avanzamento"]["storicoCompletato"]}')
            continue
        rimasti = a.minuti * 60 - (time.monotonic() - inizio)
        if rimasti < 60:
            esecuzione['errori'].append(f'{fid}: tempo esaurito, fonte rinviata al giro successivo')
            continue
        st['ultimoTentativo'] = adesso()
        opzioni = {'modalita': 'incrementale' if a.modalita == 'ricontrollo' else a.modalita, 'esecuzione': esecuzione,
                   'ocr': (not a.senza_ocr) and f.get('parametri', {}).get('ocr', True), 'limite': a.limite or None,
                   'caricamenti': caricamenti, 'secondi': rimasti - 30, 'scadenza': inizio + a.minuti * 60 - 45}
        if a.modalita == 'ricontrollo':
            st_rc = dict(st)
            st_rc['ultimoRiuscito'] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=60)).isoformat()
            st_in = st_rc
        else:
            st_in = st
        try:
            modulo = importlib.import_module(CONNETTORI[f['tipo']])
            registro(f'{fid}: avvio ({opzioni["modalita"]}, OCR {"sì" if opzioni["ocr"] else "no"})')
            esito = modulo.aggiorna(f, st_in, archivio, rete, opzioni)
            if a.modalita == 'ricontrollo':
                st['avanzamento'] = st_in.get('avanzamento', st.get('avanzamento'))
            esito['durata'] = round(time.monotonic() - inizio)
            st['errore'] = '; '.join(esito.get('errori') or [])[:1000] or None
            st['ultimoEsito'] = {k: v for k, v in esito.items() if k != 'errori'}
            if not esito.get('errori') or esito.get('letti', 0) > 0:
                st['ultimoRiuscito'] = adesso()
                riuscite += 1
            esecuzione['fonti'][fid] = esito
            registro(f'{fid}: ' + ', '.join(f'{k} {v}' for k, v in esito.items() if k not in ('errori',)) + (f'; errori {len(esito["errori"])}' if esito.get('errori') else ''))
            for e in esito.get('errori', [])[:5]:
                registro(f'   {e}')
        except Exception as e:  # noqa: BLE001
            st['errore'] = f'{type(e).__name__}: {e}'
            esecuzione['errori'].append(f'{fid}: {type(e).__name__}: {e}')
            registro(f'{fid}: ERRORE {type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}')
    esecuzione['fallimentiRete'] = rete.fallimenti[:50]
    esecuzione['richieste'] = rete.richieste

    try:
        ricalcola_riepiloghi(archivio)
        ricostruisci_serie(archivio)
    except Exception as e:  # noqa: BLE001
        esecuzione['errori'].append(f'riepiloghi: {type(e).__name__}: {e}')
        registro(f'riepiloghi: ERRORE {e}\n{traceback.format_exc()[-1500:]}')

    esecuzione['fine'] = adesso()
    esecuzione['durata'] = round(time.monotonic() - inizio)
    esecuzione['esito'] = 'riuscita' if riuscite and not esecuzione['errori'] else ('parziale' if riuscite else 'fallita')
    esecuzione['totali'] = {'rilevazioni': len(archivio['rilevazioni']), 'coda': len(archivio['coda']), 'istituti': len(archivio['istituti'])}
    archivio['esecuzioni'] = ([esecuzione] + archivio.get('esecuzioni', []))[:200]
    if riuscite:
        archivio['ultimoRiuscito'] = esecuzione['fine']
    archivio['statoFonti'] = {fid: {k: v for k, v in st.items() if k != 'avanzamento'} | {'avanzamento': {k: v for k, v in st.get('avanzamento', {}).items() if k not in ('letti', 'fatte', 'catture', 'elenco', 'fatti', 'pdf')}}
                              for fid, st in stato['fonti'].items()}
    try:
        scrivi_archivio(archivio, cartella / 'archivio.json')
        stato['ultimaEsecuzione'] = esecuzione['id']
        from comune import cifra_json
        stato_p.write_bytes(cifra_json(stato))
    except Exception as e:  # noqa: BLE001
        registro(f'SCRITTURA FALLITA: {e}')
        return 2
    registro(f'fine: {esecuzione["esito"]}, {len(archivio["rilevazioni"])} rilevazioni, {len(archivio["coda"])} in coda, {esecuzione["durata"]} s')
    riepilogo = {k: esecuzione[k] for k in ('id', 'modalita', 'esito', 'durata', 'totali', 'errori')}
    riepilogo['storicoFinito'] = all(f.get('finito', True) for f in esecuzione['fonti'].values())
    (cartella / 'esito.txt').write_text(json.dumps(riepilogo, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
