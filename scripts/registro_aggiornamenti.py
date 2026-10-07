#!/usr/bin/env python3
"""Costruisce dati/aggiornamenti.json, il registro di «Cosa è cambiato», dalla storia verificabile del repository.

Ogni voce nasce da un commit del ramo principale: data, titolo, descrizione, tipo (nuovi dati, correzione, metodo,
funzione), fogli o servizi interessati e, quando il messaggio del commit li riporta, i valori di prima e di dopo
(righe dei fogli, fermate e percorsi della rete, voci dei bandi). Non si ricostruisce nulla a mano: il registro parte
dalla prima versione pubblicata e cresce con i commit; i flussi automatici lo rigenerano dopo ogni aggiornamento.

Per ogni foglio dell'archivio il registro riporta anche l'ultima data di consultazione della fonte (`cons` nell'indice
della pagina) e il periodo dei dati, se l'indice lo dichiara («aggiornamento dati AAAA-MM-GG»).

Uso: python scripts/registro_aggiornamenti.py [--messaggio "titolo" --corpo "testo"]  (per includere un aggiornamento
     non ancora commesso, come fanno i flussi automatici prima di pubblicare)
"""
import datetime, json, re, subprocess, sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINA = RADICE / 'index.html'
FILE = RADICE / 'dati' / 'aggiornamenti.json'
BOT = 'github-actions'
# pagine o servizi riconosciuti nel testo dei commit: parola chiave -> (etichetta, collegamento)
SERVIZI = [(r'\bbandi\b', 'Bandi e avvisi della Regione', '../bandi/'), (r'finanziament|vantaggi economici|atti di concessione', 'Finanziamenti regionali', '../finanziamenti/'), (r'osservatorio|\bopere\b', 'Osservatorio delle opere pubbliche', '../opere/'), (r'servizi sul territorio|mappa dei servizi', 'Servizi sul territorio', '../servizi/'), (r'opere pubbliche|OpenCUP', 'Opere pubbliche (OpenCUP)', '../?pagina=archivio&foglio=Opere_pubbliche_OpenCUP'),
           (r'\borari\b', 'Orari degli autobus', '../orari/'), (r'autobus|rete|GTFS|fermat', 'Rete degli autobus', '../?pagina=autobus'), (r'meteo', 'Meteo', '../meteo/'),
           (r'catasto', 'Catasto', '../catasto/'), (r'stradario', 'Stradario', '../stradario/'), (r'allert|qualità dell.aria|\baria\b', 'Allerte e qualità dell\'aria', '../?pagina=ambiente'),
           (r'confronto', 'Confronto', '../?pagina=confronto'), (r'mapp', 'Mappe', '../?pagina=mappe'), (r'dossier|scheda', 'Scheda del comune', '../?pagina=comuni'), (r'metodo|fonti|versioni', 'Metodo e fonti', '../?pagina=metodo')]


def git(*args):
    return subprocess.run(['git', *args], cwd=RADICE, capture_output=True, text=True, check=True).stdout


def tipo_di(titolo, autore, corpo):
    t = titolo.lower()
    if autore.startswith(BOT) or re.match(r'^aggiorna (i dati|i bandi|le opere|la rete|gli orari)', t):
        return 'dati'
    if re.match(r'^(corregge|sistema|risolve|ripara|allinea|toglie|mantiene|separa|fa scendere|armonizza)', t) or 'correzion' in t:
        return 'correzione'
    if re.search(r'metodo|trasparent|avvertenz|versioni|licenz|fonti', t):
        return 'metodo'
    return 'funzione'


def valori_dal_corpo(corpo):
    """Legge dal messaggio del commit i confronti «prima / dopo» che i flussi automatici scrivono."""
    out = []
    for m in re.finditer(r'^\s*([A-Za-z0-9_]+): (\d[\d.]*) righe \(prima (\d[\d.]*)\)', corpo, re.M):
        n, p = int(m.group(2).replace('.', '')), int(m.group(3).replace('.', ''))
        out.append({'cosa': m.group(1), 'misura': 'righe', 'prima': p, 'dopo': n, 'differenza': n - p, 'collegamento': f'../?pagina=archivio&foglio={m.group(1)}'})
    m = re.search(r'Autobus: rete aggiornata alla versione (\S+): (\d+) fermate e (\d+) percorsi \(prima (\d+) fermate e (\d+) percorsi\)', corpo)
    if m:
        out.append({'cosa': 'Rete degli autobus (GTFS ' + m.group(1) + ')', 'misura': 'fermate', 'prima': int(m.group(4)), 'dopo': int(m.group(2)), 'differenza': int(m.group(2)) - int(m.group(4)), 'collegamento': '../?pagina=autobus'})
        out.append({'cosa': 'Rete degli autobus (GTFS ' + m.group(1) + ')', 'misura': 'percorsi', 'prima': int(m.group(5)), 'dopo': int(m.group(3)), 'differenza': int(m.group(3)) - int(m.group(5)), 'collegamento': '../?pagina=autobus'})
    m = re.search(r'Bandi: (\d+) voci \((\d+) con misure contributive\), (\d+) nuove e (\d+) tolte', corpo)
    if m:
        n, nuove, tolte = int(m.group(1)), int(m.group(3)), int(m.group(4))
        out.append({'cosa': 'Bandi e avvisi della Regione', 'misura': 'voci', 'prima': n - nuove + tolte, 'dopo': n, 'differenza': nuove - tolte, 'collegamento': '../bandi/'})
    m = re.search(r'Finanziamenti: (\d+) righe lette dal (\S+) al (\S+), (\d+) nuove; archivio di (\d+) righe', corpo)
    if m:
        out.append({'cosa': 'Finanziamenti regionali (Amministrazione trasparente)', 'misura': 'righe in archivio', 'prima': int(m.group(5)) - int(m.group(4)), 'dopo': int(m.group(5)), 'differenza': int(m.group(4)), 'collegamento': '../finanziamenti/'})
    m = re.search(r'Opere pubbliche: (\d+) progetti, (\d+) righe per comune', corpo)
    if m:
        out.append({'cosa': 'Opere pubbliche (OpenCUP)', 'misura': 'progetti', 'prima': None, 'dopo': int(m.group(1)), 'differenza': None, 'collegamento': '../?pagina=archivio&foglio=Opere_pubbliche_OpenCUP'})
    return out


def servizi_di(testo, file_toccati):
    """Fogli e servizi interessati: dai file dati/ toccati e dalle parole del messaggio."""
    s = []
    for f in file_toccati:
        m = re.match(r'dati/([A-Za-z0-9_]+?)_\d+\.txt$', f)
        if m and not m.group(1).startswith('_'):
            s.append({'nome': m.group(1).replace('_', ' '), 'collegamento': f'../?pagina=archivio&foglio={m.group(1)}'})
        elif f.startswith('dati/fin/') or f == 'dati/finanziamenti_indice.json':
            s.append({'nome': 'Finanziamenti regionali', 'collegamento': '../finanziamenti/'})
        elif f == 'dati/bandi.json':
            s.append({'nome': 'Bandi e avvisi della Regione', 'collegamento': '../bandi/'})
        elif f == 'dati/_tpl_0.txt':
            s.append({'nome': 'Rete degli autobus', 'collegamento': '../?pagina=autobus'})
        elif f == 'dati/_punti_0.txt':
            s.append({'nome': 'Servizi sulla mappa', 'collegamento': '../?pagina=mappe'})
        elif f.startswith('orari/'):
            s.append({'nome': 'Orari degli autobus', 'collegamento': '../orari/'})
    if not s:
        for ch, nome, link in SERVIZI:
            if re.search(ch, testo, re.I):
                s.append({'nome': nome, 'collegamento': link}); break
    visti, out = set(), []
    for x in s:
        if x['nome'] not in visti:
            visti.add(x['nome']); out.append(x)
    return out[:12]


def periodo_fogli():
    """Per ogni foglio: data di consultazione della fonte e periodo dei dati dichiarato nell'indice."""
    testo = PAGINA.read_text(encoding='utf-8')
    m = re.search(r'^const MAN = (.*);$', testo, re.M)
    if not m:
        return []
    man = json.loads(m.group(1))
    out = []
    for f in man['manifest']:
        d = f.get('descr') or ''
        per = re.search(r'aggiornamento dati (\d{4}-\d{2}-\d{2})', d)
        anni = re.findall(r'(?<!\d)(19\d\d|20\d\d)(?!\d)', f['id'].replace('_', ' '))
        out.append({'id': f['id'], 'nome': f['id'].replace('_', ' '), 'ambito': f.get('ambito', ''), 'righe': f.get('righe'), 'consultazione': f.get('cons') or None,
                    'periodo': ('dati aggiornati dalla fonte al ' + per.group(1)) if per else (f'anni {min(anni)}-{max(anni)}' if len(set(anni)) > 1 else f'anno {anni[0]}' if anni else None),
                    'fonte': (f.get('fonte') or '')[:160]})
    return out


def main():
    arg = sys.argv[1:]
    log = git('log', '--first-parent', '--reverse', '--date=short', '--format=%H%x1f%ad%x1f%an%x1f%s%x1f%b%x1e', 'HEAD')
    voci = []
    for blocco in log.split('\x1e'):
        if not blocco.strip():
            continue
        h, data, autore, titolo, corpo = (blocco.strip('\n').split('\x1f') + [''] * 5)[:5]
        titolo = re.sub(r'\s*\(#\d+\)$', '', titolo.strip())
        # restano fuori le firme tecniche dei commit (coautore, sessione, generatore)
        corpo = '\n'.join(l for l in corpo.strip().splitlines() if not re.match(r'^(co-authored-by|claude-session|🤖|https://claude\.ai|generated with)', l.strip(), re.I)).strip()
        file_toccati = git('show', '--pretty=format:', '--name-only', h).split()
        tipo = tipo_di(titolo, autore, corpo)
        # un commit che porta file di dati nuovi o cambiati è «nuovi dati», anche se è stato fatto a mano
        if tipo == 'funzione' and any(re.match(r'dati/(?!_|aggiornamenti\.json)', x) for x in file_toccati):
            tipo = 'dati'
        voci.append({'data': data, 'tipo': tipo, 'automatico': autore.startswith(BOT), 'titolo': titolo, 'descrizione': corpo,
                     'interessa': servizi_di(titolo + ' ' + corpo, file_toccati), 'valori': valori_dal_corpo(corpo), 'commit': h[:10]})
    if '--messaggio' in arg:
        titolo = arg[arg.index('--messaggio') + 1]; corpo = arg[arg.index('--corpo') + 1] if '--corpo' in arg else ''
        file_toccati = git('diff', '--cached', '--name-only').split() + git('diff', '--name-only').split()
        voci.append({'data': datetime.date.today().isoformat(), 'tipo': 'dati', 'automatico': True, 'titolo': titolo, 'descrizione': corpo,
                     'interessa': servizi_di(titolo + ' ' + corpo, file_toccati), 'valori': valori_dal_corpo(corpo), 'commit': None})
    voci.reverse()
    out = {'generato': datetime.date.today().isoformat(), 'prima_versione': min(v['data'] for v in voci), 'nota': 'Registro ricavato dalla storia del repository GuidoCostalonga/Atlante-FVG: ogni voce corrisponde a una modifica pubblicata e verificabile. Prima della prima versione non esiste cronologia.',
           'voci': voci, 'fogli': periodo_fogli()}
    FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Registro: {len(voci)} voci dal {out["prima_versione"]}, {len(out["fogli"])} fogli con data di consultazione.')


if __name__ == '__main__':
    main()
