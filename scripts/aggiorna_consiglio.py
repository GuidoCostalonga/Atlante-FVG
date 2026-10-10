#!/usr/bin/env python3
"""Unisce gli atti di indirizzo del Consiglio regionale raccolti con gli strumenti in scripts/consiglio/ (vedi LEGGIMI.md)
e scrive dati/consiglio_atti.json: per ogni atto tipo, numero, titolo, data di presentazione, proponenti, primo firmatario,
assessore competente, stato, testo depositato e scheda; più la composizione dei gruppi consiliari.

Uso: python3 scripts/aggiorna_consiglio.py <cartella con mozioni_dett.json, stati_mozioni.json, odg_dett.json, stati_odg.json, gruppi.json> [--letti AAAA-MM-GG]
"""
import collections, json, re, sys, time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / 'dati' / 'consiglio_atti.json'
SIGLE = {'PARTITO DEMOCRATICO': 'PD', 'LEGA SALVINI FVG': 'Lega', 'FEDRIGA PRESIDENTE': 'Fedriga Presidente', "FRATELLI D'ITALIA": 'FdI',
         "PATTO PER L'AUTONOMIA - CIVICA FVG": "Patto per l'Autonomia - Civica FVG", 'FORZA ITALIA - PARTITO POPOLARE EUROPEO': 'Forza Italia', 'GRUPPO MISTO': 'Gruppo misto'}
MISTO = [('CAPOZZI', 'Movimento 5 Stelle'), ('PELLEGRINO', 'Alleanza Verdi Sinistra'), ('HONSELL', 'Open Sinistra FVG'), ('SPAGNOLO', 'Futuro Nazionale'), ('BULLIAN', '')]


def gruppi(cartella):
    """Dalla raccolta grezza (testo della pagina di ogni gruppo) alla mappa cognome -> gruppo."""
    grezzi = json.loads((cartella / 'gruppi_grezzi.json').read_text(encoding='utf-8'))
    membri = {}
    for g, t in grezzi.items():
        t = t.replace('\xa0', ' ')
        seg = t.split('Segreteria del Gruppo consiliare')[1].split('Recapiti e contatti')[0] if 'Segreteria del Gruppo consiliare' in t else ''
        for l in seg.split('\n'):
            m = re.match(r"\s*([A-ZÀ-Ü' ]{3,}?) ([A-ZÀ-Ü][a-zà-ü]+(?: [A-ZÀ-Ü][a-zà-ü]+)*)(?: - ([A-Za-z ]+))?\s*$", l)
            if m:
                membri[m.group(1).strip()] = {'nome': m.group(2), 'gruppo': SIGLE.get(g, g.title()), 'ruolo': (m.group(3) or '').strip()}
    testo_misto = grezzi.get('GRUPPO MISTO', '')
    for cogn, forza in MISTO:
        if cogn in testo_misto:
            membri[cogn] = {'nome': '', 'gruppo': 'Gruppo misto', 'forza': forza, 'ruolo': ''}
    return membri


def atti(cartella, tipo, dett, stati):
    d = json.loads((cartella / dett).read_text(encoding='utf-8'))
    st = json.loads((cartella / stati).read_text(encoding='utf-8')) if (cartella / stati).exists() else {}
    stato_di = {}
    for s, righe in st.items():
        for r in righe:
            m = re.match(r'(\d+)\s*-', r['testo'])
            if m:
                stato_di[(m.group(1), r['data'])] = s
    out = []
    for v in d.values():
        m = re.search(r'n\.\s*(\d+)', v['numero']); num = int(m.group(1)) if m else None
        dm = re.match(r'(\d\d)/(\d\d)/(\d{4})', v['data']); data = f'{dm.group(3)}-{dm.group(2)}-{dm.group(1)}' if dm else ''
        out.append({'tipo': tipo, 'numero': num, 'titolo': v['titolo'].rstrip('.'), 'data': data, 'proponenti': v['proponenti'], 'primo': v['proponenti'][0] if v['proponenti'] else '',
                    'assessore': v['assessore'].strip(), 'stato': stato_di.get((str(num), v['lista']['data']), ''), 'allegato': v['allegato'], 'url': v['url']})
    return out


def atti_odg(cartella, dett, stati):
    """Gli ordini del giorno hanno una scheda diversa: numero per disegno di legge, esito della votazione, legge approvata, firme aggiunte."""
    d = json.loads((cartella / dett).read_text(encoding='utf-8'))
    st = json.loads((cartella / stati).read_text(encoding='utf-8')) if (cartella / stati).exists() else {}
    stato_di = {}
    for s, righe in st.items():
        for r in righe:
            stato_di[(r['testo'].split('\n')[0].strip(), r['data'])] = s
    out = []
    for v in d.values():
        testa = re.sub(r'^Legislatura \S+\s*', '', v.get('titolo', '')).strip()
        m = re.match(r'Odg(?: su (.*?))? - (\d+)\s+(.*)$', testa)
        oggetto, num, titolo = (m.group(1) or '', int(m.group(2)), m.group(3)) if m else ('', None, testa)
        riga = v['lista']['testo'].split('\n')
        mn = re.match(r'(\d+)\s*-', riga[0])
        if mn: num = int(mn.group(1))
        dm = re.match(r'(\d\d)/(\d\d)/(\d{4})', v['data']); data = f'{dm.group(3)}-{dm.group(2)}-{dm.group(1)}' if dm else ''
        firme = re.findall(r'Firma aggiunta:\s*([A-ZÀ-Ü\' ,]+)', v.get('note', ''))
        aggiunte = [x.strip() for x in firme[0].split(',')] if firme else []
        out.append({'tipo': 'Ordine del giorno', 'numero': num, 'titolo': titolo.rstrip('.'), 'data': data, 'proponenti': v['proponenti'], 'primo': v['proponenti'][0] if v['proponenti'] else '',
                    'assessore': '', 'stato': stato_di.get((riga[0].strip(), v['lista']['data']), ''), 'esito': v.get('esito', ''), 'ddl': v.get('ddl', ''), 'legge': v.get('legge', ''),
                    'oggetto': oggetto or (riga[1].strip() if len(riga) > 1 else ''), 'firmeAggiunte': aggiunte, 'allegato': v.get('allegato', ''), 'url': v['url']})
    return out


def main():
    args = sys.argv[1:]
    cartella = Path(args[0])
    letti = args[args.index('--letti') + 1] if '--letti' in args else time.strftime('%Y-%m-%d')
    membri = gruppi(cartella)
    tutti = atti(cartella, 'Mozione', 'mozioni_dett.json', 'stati_mozioni.json')
    if (cartella / 'odg_dett.json').exists():
        tutti += atti_odg(cartella, 'odg_dett.json', 'stati_odg.json')
    senza = [a['primo'] for a in tutti if a['primo'] and a['primo'] not in membri]
    print(f"atti: {len(tutti)}; stati: {dict(collections.Counter(a['stato'] for a in tutti))}; gruppi: {len(membri)} consiglieri; primi firmatari non nei gruppi: {sorted(set(senza)) or 'nessuno'}")
    USCITA.write_text(json.dumps({'letti': letti, 'legislatura': 'XIII', 'fonte': 'https://www.consiglio.regione.fvg.it/pagineinterne/Portale/Attivita/AttiIndirizzoRicerca.aspx', 'gruppi': membri,
                                  'atti': sorted(tutti, key=lambda a: (a['data'], a['numero'] or 0), reverse=True)}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'scritto {USCITA.name}')


if __name__ == '__main__':
    main()
