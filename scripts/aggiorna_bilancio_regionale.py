#!/usr/bin/env python3
"""Bilancio della Regione: spese per missione e programma, entrate per titolo, dai rendiconti ufficiali.

Legge i PDF dei rendiconti generali pubblicati dalla Regione (pagina «Bilancio», conto del bilancio: gestione delle
spese e gestione delle entrate), li converte in testo con pdftotext (poppler) e ne estrae le righe «TOTALE MISSIONE»,
«TOTALE PROGRAMMA» e «TOTALE TITOLO» con le colonne stampate nel documento: per le spese previsioni definitive di
competenza (CP), impegni (I), pagamenti in conto competenza (PC) e pagamenti totali (TP); per le entrate previsioni (CP),
accertamenti (A) e riscossioni in conto competenza (RC). Ogni anno viene controllato contro il totale generale stampato
nel documento: se non torna, l'anno non viene scritto.

Scrive dati/bilancio_regionale.json. Uso:
  python3 scripts/aggiorna_bilancio_regionale.py [--cartella <cartella con i PDF o i testi già estratti>]
Senza --cartella scarica i PDF (circa 150 MB in tutto) in una cartella temporanea. Usa solo la libreria standard di Python.
"""
import json, re, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / 'dati' / 'bilancio_regionale.json'
PAGINA = 'https://www.regione.fvg.it/rafvg/cms/RAFVG/GEN/bilancio/'
B = 'https://www.regione.fvg.it/rafvg/export/sites/default/RAFVG/GEN/bilancio/allegati/'
ANNI = {
    2019: {'spese': B + '20201014_Rendiconto_2019_-_Spese_.pdf', 'entrate': B + '20201014_Rendiconto_2019_-_Entrata.pdf', 'approvazione': 'legge regionale 6 ottobre 2020, n. 16'},
    2020: {'spese': B + 'Rendiconto2020spesa.pdf', 'entrate': B + 'Rendiconto2020entrata.pdf', 'approvazione': 'legge regionale 6 agosto 2021, n. 11'},
    2021: {'spese': B + '20220810_CC118_Rendiconto_spese.pdf', 'entrate': B + '20220810_CC118_Rendiconto_entrate.pdf', 'approvazione': 'legge regionale 2 agosto 2022, n. 12'},
    2022: {'spese': B + '20230807_Rendiconto_2022_Spese.pdf', 'entrate': B + '20230807_Rendiconto_2022_Entrate.pdf', 'approvazione': 'legge regionale 1° agosto 2023, n. 12'},
    2023: {'spese': B + '05082024_Rendiconto_2023_Spese.pdf', 'entrate': B + '05082024_Rendiconto_2023_Entrate.pdf', 'approvazione': 'legge regionale 31 luglio 2024, n. 6'},
    2024: {'spese': 'https://www.regione.fvg.it/rafvg/cms/RAFVG/GEN/bilancio/allegati/20250804_Rendiconto_2024_Spese.zip', 'entrate': B + '20250804_Rendiconto_2024_Entrate.pdf', 'approvazione': 'legge regionale 1° agosto 2025, n. 11'},
    2025: {'spese': B + '20260803_Rendiconto_2025_-_Spese.zip', 'entrate': B + '20260803_Rendiconto_2025_-_Entrate.zip', 'approvazione': 'legge regionale 30 luglio 2026, n. 8'},
}
UA = {'User-Agent': 'AtlanteFVG/1.0 (+https://atlantefvg.it/)'}
NUM = r'-?\s?[\d\.]+,\d{1,2}'


def numero(s):
    return float(s.replace(' ', '').replace('.', '').replace(',', '.'))


def testo_di(anno, tipo, cartella):
    """Restituisce il testo del documento, scaricando e convertendo se serve."""
    txt = cartella / f'{anno}_{tipo}.txt'
    if txt.exists():
        return txt.read_text(encoding='utf-8')
    pdf = cartella / f'{anno}_{tipo}.pdf'
    if not pdf.exists():
        url = ANNI[anno][tipo]
        print(f'scarico {anno} {tipo}…')
        dati = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900).read()
        if url.lower().endswith('.zip'):
            import io, zipfile
            with zipfile.ZipFile(io.BytesIO(dati)) as z:
                nome = [n for n in z.namelist() if n.lower().endswith('.pdf')][0]
                pdf.write_bytes(z.read(nome))
        else:
            pdf.write_bytes(dati)
    subprocess.run(['pdftotext', '-layout', str(pdf), str(txt)], check=True)
    return txt.read_text(encoding='utf-8')


def valori(segmento):
    out = {}
    for k, v in re.findall(r'(?<![A-Za-z])([A-Z]{1,3})\s+(' + NUM + r')(?![\d,])', segmento):
        out.setdefault(k, numero(v))
    return out


def denominazione_seguente(righe, i):
    """La denominazione può continuare sulla riga sotto, da sola o davanti ai numeri."""
    if i + 1 >= len(righe):
        return ''
    l2 = righe[i + 1]
    m = re.match(r"\s*([A-Za-z][A-Za-z'’ ,\-]*?)\s{2,}[A-Z]{1,3}\s+" + NUM, l2) or re.match(r"\s*([A-Za-z][A-Za-z'’ ,\-]*)\s*$", l2)
    return m.group(1).strip() if m and len(m.group(1).strip()) > 2 else ''


def totali(testo, chiave, codice=True):
    righe = testo.split('\n'); out = []
    for i, l in enumerate(righe):
        m = re.match(r'\s*(?:(\d{5})\s+)?TOTALE ' + chiave + r'(?:\s+(\d+))?(?:\s+-)?\s+(.*?)\s+(RS|CP|CS)\s+(' + NUM + ')', l, re.I)
        if not m:
            continue
        cod, n, den = m.group(1) or '', m.group(2), m.group(3).strip()
        if not n:
            n = cod[0] if chiave == 'TITOLO' and cod else cod[:2]
        # nei rendiconti 2019 e 2020 la denominazione è in maiuscolo e su più righe: si prende quella degli anni successivi
        if den and (den.isupper() or re.fullmatch(r'[\d\s]*', den)):
            den = ''
        if den:
            den = (den + ' ' + denominazione_seguente(righe, i)).strip()
        if not n:
            continue
        out.append({'cod': cod, 'n': n.lstrip('0') or '0', 'den': re.sub(r'\s+', ' ', den), 'riga': i, **valori(' '.join(righe[i:i + 4]))})
    return out


def totale_generale(testo, etichette):
    righe = testo.split('\n')
    for i, l in enumerate(righe):
        if any(re.search(e, l, re.I) for e in etichette):
            return valori(' '.join(righe[i:i + 4]))
    return {}


def leggi_anno(anno, cartella, nomi_missioni, nomi_titoli):
    sp = testo_di(anno, 'spese', cartella); en = testo_di(anno, 'entrate', cartella)
    missioni = totali(sp, 'MISSIONE'); programmi = totali(sp, 'PROGRAMMA'); titoli = totali(en, 'TITOLO')
    # nei rendiconti 2019 e 2020 le righe dei totali non portano la denominazione: si usa quella degli anni successivi
    for m in missioni:
        if not m['den']: m['den'] = nomi_missioni.get(m['n'], f'Missione {m["n"]}')
    for t in titoli:
        if not t['den']: t['den'] = nomi_titoli.get(t['n'], f'Titolo {t["n"]}')
    # i programmi senza codice prendono la missione del primo «TOTALE MISSIONE» che li segue
    for p in programmi:
        if not p['cod']:
            seg = next((m for m in missioni if m['riga'] > p['riga']), None)
            p['cod'] = (seg['n'].zfill(2) if seg else '00') + p['n'].zfill(2) + '0'
    chiavi_sp = ['CP', 'I', 'PC', 'TP']; chiavi_en = ['CP', 'A', 'RC']
    pulisci = lambda x, chiavi: {'cod': x['cod'], 'n': x['n'], 'den': x['den'], **{k: round(x.get(k, 0.0), 2) for k in chiavi}}
    controlli = {}
    gen_sp = totale_generale(sp, [r'TOTALE GENERALE DELLE SPESE', r'TOTALE GENERALE SPESE', r'Totale Generale delle Spese'])
    gen_en = totale_generale(en, [r'TOTALE GENERALE DELLE ENTRATE', r'Totale Generale delle Entrate'])
    for k in ('I', 'TP'):
        somma = round(sum(m.get(k, 0) for m in missioni), 2); controlli[f'spese_{k}'] = [somma, gen_sp.get(k)]
    somma_a = round(sum(t.get('A', 0) for t in titoli), 2); controlli['entrate_A'] = [somma_a, gen_en.get('A')]
    ok = all(v[1] is not None and abs(v[0] - v[1]) < 1 for v in controlli.values())
    return {'anno': anno, 'fonte': ANNI[anno]['spese'], 'fonteEntrate': ANNI[anno]['entrate'], 'approvazione': ANNI[anno].get('approvazione', ''),
            'missioni': [pulisci(m, chiavi_sp) for m in missioni], 'programmi': [pulisci(p, chiavi_sp) for p in programmi], 'entrate': [pulisci(t, chiavi_en) for t in titoli], 'controlli': controlli}, ok


def main():
    args = sys.argv[1:]
    cartella = Path(args[args.index('--cartella') + 1]) if '--cartella' in args else Path(tempfile.gettempdir()) / 'rendiconti_fvg'
    cartella.mkdir(parents=True, exist_ok=True)
    nomi_m, nomi_t, anni = {}, {}, []
    # prima gli anni recenti, che portano le denominazioni
    for anno in sorted(ANNI, reverse=True):
        try:
            dati, ok = leggi_anno(anno, cartella, nomi_m, nomi_t)
        except Exception as e:
            print(f'{anno}: non letto ({e})'); continue
        for m in dati['missioni']: nomi_m.setdefault(m['n'], m['den'])
        for t in dati['entrate']: nomi_t.setdefault(t['n'], t['den'])
        c = dati['controlli']
        print(f"{anno}: missioni {len(dati['missioni'])}, programmi {len(dati['programmi'])}, titoli {len(dati['entrate'])}; impegni {c['spese_I'][0]:,.2f} contro {c['spese_I'][1]}; accertamenti {c['entrate_A'][0]:,.2f} contro {c['entrate_A'][1]} -> {'ok' if ok else 'NON TORNA, escluso'}")
        if ok:
            anni.append(dati)
    anni.sort(key=lambda a: a['anno'])
    if not anni:
        raise SystemExit('nessun anno valido: nulla è stato scritto')
    USCITA.write_text(json.dumps({'letti': time.strftime('%Y-%m-%d'), 'pagina': PAGINA, 'anni': anni}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'scritto {USCITA.name}: anni {[a["anno"] for a in anni]}')


if __name__ == '__main__':
    main()
