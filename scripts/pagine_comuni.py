#!/usr/bin/env python3
"""Crea le pagine statiche dell'Atlante, leggibili anche senza eseguire il programma della pagina.

- c/<comune>/index.html: una pagina per ognuno dei 215 comuni, con i dati principali, le fonti,
  il percorso (Atlante FVG > provincia > comune) e i collegamenti alle altre pagine.
- provincia/<nome>/index.html: l'elenco dei comuni di ogni provincia.
- mappe/, confronto/, autobus/, ambiente/, comuni/, archivio/, metodo/: una pagina per argomento,
  con il pulsante che apre la pagina interattiva (atlantefvg.it/?pagina=...).
- sitemap.xml (indice) con sitemap-servizi.xml, sitemap-province.xml e sitemap-comuni.xml, e robots.txt.
  La data <lastmod> di ogni indirizzo è quella dell'ultima modifica reale del file: la data dell'ultimo
  commit che lo ha cambiato oppure, se il file cambia in questa esecuzione, la data di oggi.

Ogni pagina ha titolo e descrizione propri, un solo titolo H1, indirizzo canonico, intestazioni per
l'anteprima nelle condivisioni (WhatsApp, Facebook e simili) e dati strutturati schema.org
(BreadcrumbList; City sui comuni; Dataset sulla pagina dell'archivio).
Le schede dei comuni riportano anche posizioni e confronti con la media provinciale e regionale,
calcolati dai dati già presenti, e i comuni confinanti, calcolati dai confini delle mappe dell'Atlante.

I dati vengono dalle righe `const DB = ...;` e `const MAN = ...;` di index.html.
Usa solo la libreria standard di Python.
"""
import base64, collections, datetime, gzip, html, json, math, re, shutil, subprocess, unicodedata, urllib.parse
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
SITO = 'https://atlantefvg.it'
PROVINCE = {'UD': 'Udine', 'PN': 'Pordenone', 'GO': 'Gorizia', 'TS': 'Trieste'}
MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']
ANNUARIO = ('Annuario statistico regionale 2026, tavola 19.2', 'Annuario statistico regionale 2026')
# pagine per argomento: indirizzo breve, titolo, descrizione, testo della pagina; devono coincidere con PAGINE in index.html
PAGINE = [
    ('mappe', 'Mappe dei comuni', 'Mappe dei 215 comuni del Friuli Venezia Giulia: popolazione, redditi, servizi, Terzo settore, rischio idrogeologico, bilanci, elezioni e opere pubbliche.',
     ['Oltre trenta indicatori, ognuno con fonte, periodo e copertura: popolazione ed età, redditi, turismo, farmacie, Terzo settore, rischio di frana e di alluvione, bilanci comunali, opere pubbliche, affluenza e liste più votate.',
      'Accanto a ogni mappa c\'è la tabella con gli stessi valori, scaricabile in CSV ed Excel. Ci sono anche le cartine dell\'Annuario statistico regionale e i servizi sul territorio: farmacie, guardie mediche, residenze per anziani.']),
    ('confronto', 'Confronto fra comuni', 'Confronta fino a sei comuni del Friuli Venezia Giulia, indicatore per indicatore, con i valori assoluti separati da quelli per abitante.',
     ['Si scelgono fino a sei comuni e si leggono fianco a fianco: popolazione, redditi, servizi, Terzo settore, bilanci, rischio idrogeologico ed elezioni.',
      'I valori assoluti sono separati da quelli per abitante, che permettono di confrontare comuni di taglia diversa. Ogni riga indica il periodo dei dati e segnala quelli meno recenti.']),
    ('autobus', 'Autobus del Friuli Venezia Giulia', 'Linee, fermate e arrivi in tempo reale degli autobus del Friuli Venezia Giulia, con la mappa delle vie.',
     ['Le linee del trasporto pubblico locale, le fermate di ogni comune e gli arrivi in tempo reale, con i mezzi in viaggio sulla mappa delle vie.',
      'Gli orari di ogni linea, fermata per fermata e giorno per giorno, sono nella pagina Orari degli autobus.',
      'Fonte: TPL FVG tramite BusOne, rete aggiornata ogni lunedì e arrivi letti al momento.']),
    ('ambiente', 'Allerte meteo e qualità dell\'aria', 'Allerta meteo di oggi e di domani, letta al momento, e ultimi dati validati della qualità dell\'aria delle centraline del Friuli Venezia Giulia.',
     ['Allerte attuali: l\'allerta idrogeologica, idraulica e per temporali di oggi e di domani nelle quattro zone d\'allerta, letta al momento dal bollettino del Dipartimento della Protezione civile.',
      'Qualità dell\'aria, ultimi dati disponibili: medie giornaliere validate di PM10, PM2,5, biossido di azoto e ozono delle centraline dell\'ARPA FVG (Agenzia regionale per la protezione dell\'ambiente). Arrivano con circa una settimana di ritardo: descrivono i giorni scorsi, non l\'aria di oggi, e ognuna ha la sua data.']),
    ('comuni', 'I 215 comuni del Friuli Venezia Giulia', 'Elenco dei 215 comuni del Friuli Venezia Giulia per provincia, con residenti, sindaci, servizi e prossime elezioni.',
     ['Il registro dei 215 comuni: residenti, sindaco in anagrafe con la data di aggiornamento, enti del Terzo settore, presenze turistiche e anno delle prossime elezioni comunali.']),
    ('archivio', 'Archivio dei dati dei comuni', 'Tutti i fogli del database dei comuni del Friuli Venezia Giulia, consultabili riga per riga e scaricabili in CSV ed Excel con fonte e data.',
     ['Ogni foglio del database è consultabile per intero, con tutte le righe e tutte le colonne, filtrabile per comune, per testo e colonna per colonna.',
      'I risultati filtrati si scaricano in CSV ed Excel con fonte, data dei dati e condizioni di riutilizzo. Qui sotto l\'elenco dei fogli con la loro fonte.']),
    ('metodo', 'Metodo e fonti', 'Versioni, date di aggiornamento, fonti, copertura e avvertenze sui dati dell\'Atlante dei comuni del Friuli Venezia Giulia.',
     ['Come sono fatti i dati dell\'Atlante: versioni e date di aggiornamento, fonti con i collegamenti alla documentazione originale, copertura di ogni gruppo di dati, differenza fra zero e dato non disponibile, avvertenze.']),
]
# pagine fatte a mano o da altri script, da tenere nella sitemap
PAGINE_FISSE = ('orari', 'bandi', 'opere', 'finanziamenti', 'pnrr', 'bilancio-regionale', 'consiglio', 'servizi', 'meteo', 'stradario', 'catasto', 'aggiornamenti')
ICONA_PAG = {'mappe': 'Esplora le mappe', 'confronto': 'Apri il confronto', 'autobus': 'Apri gli autobus', 'ambiente': 'Apri allerte e aria', 'comuni': 'Apri il registro dei comuni', 'archivio': 'Apri l\'archivio', 'metodo': 'Apri Metodo e fonti'}

e = html.escape
POSTA = 'info@atlantefvg.it'
WHATSAPP = '393283692227'


def segnala(url, titolo):
    corpo = f'Pagina: {url}\nDato segnalato: \n\nChe cosa non torna:\n\n\nValore corretto e fonte, se li conosci:\n\n'
    q = urllib.parse.urlencode({'subject': f'Segnalazione di errore: {titolo}', 'body': corpo}, quote_via=urllib.parse.quote)
    return e(f'mailto:{POSTA}?{q}')


def segnala_wa(url, titolo):
    testo = f"Segnalazione di errore sull'Atlante FVG\nPagina: {url}\nDato segnalato: {titolo}\n\nChe cosa non torna: "
    return e(f'https://wa.me/{WHATSAPP}?text={urllib.parse.quote(testo)}')


def slug(nome):
    s = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def migliaia(n):
    return f'{int(round(n)):,}'.replace(',', '.')


def decimale(n, cifre=1):
    return f'{n:,.{cifre}f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def data_estesa(iso_o_it):
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', iso_o_it or '') or None
    if m:
        a, me, g = m.groups()
    else:
        m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', iso_o_it or '')
        if not m:
            return iso_o_it or ''
        g, me, a = m.groups()
    g = int(g)
    return f"{'1°' if g == 1 else g} {MESI[int(me) - 1]} {a}"


def nome_proprio(s):
    return re.sub(r"(^|[\s'’-])(\w)", lambda m: m.group(1) + m.group(2).upper(), (s or '').lower())


def percento(x):
    """Variazione percentuale con segno; due decimali quando una sola cifra la mostrerebbe come zero."""
    cifre = 2 if 0 < abs(x) < 0.05 else 1
    return ('+' if x > 0 else '−' if x < 0 else '') + decimale(abs(x), cifre) + '%'


def leggi_dati(nome):
    return json.loads(gzip.decompress(base64.b64decode((RADICE / 'dati' / nome).read_text())))


# Due comuni confinano se condividono almeno CONFINE_MIN metri di confine in entrambe le direzioni:
# così si escludono i punti in cui si toccano tre comuni (pochi metri dovuti alla semplificazione del tracciato).
CONFINE_MIN, CONFINE_TOLL, CONFINE_PASSO, CELLA = 300, 60, 50, 400


def confinanti(istat):
    """Comuni confinanti, calcolati dai confini comunali delle mappe dell'Atlante (dati/_mappe_0.txt, coordinate in metri)."""
    geo = leggi_dati('_mappe_0.txt')
    seg = {}
    for c in geo['comuni']:
        s = []
        for r in c['r']:
            pt = list(zip(r[0::2], r[1::2]))
            s += [(pt[i], pt[i + 1]) for i in range(len(pt) - 1)]
        seg[istat[c['c']]] = s
    celle = collections.defaultdict(list)
    for k, ss in seg.items():
        for a, b in ss:
            for gx in range(int(min(a[0], b[0]) - CONFINE_TOLL) // CELLA, int(max(a[0], b[0]) + CONFINE_TOLL) // CELLA + 1):
                for gy in range(int(min(a[1], b[1]) - CONFINE_TOLL) // CELLA, int(max(a[1], b[1]) + CONFINE_TOLL) // CELLA + 1):
                    celle[(gx, gy)].append((k, a, b))

    def dist(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; q = dx * dx + dy * dy
        t = 0 if q == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / q))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
    comune = collections.Counter()
    for k, ss in seg.items():
        for a, b in ss:
            lung = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(lung // CONFINE_PASSO))
            for i in range(n):
                p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                vicini = {o for o, sa, sb in celle[(int(p[0]) // CELLA, int(p[1]) // CELLA)] if o != k and dist(p, sa, sb) <= CONFINE_TOLL}
                for o in vicini:
                    comune[(k, o)] += lung / n
    out = collections.defaultdict(list)
    for (k, o), lung in comune.items():
        if lung >= CONFINE_MIN and comune.get((o, k), 0) >= CONFINE_MIN:
            out[k].append(o)
    return out


def posizione(c, gruppo, campo):
    """Posizione di c nel gruppo per campo, dal valore più alto (1 = il più alto); None se manca il valore."""
    v = campo(c)
    if v is None:
        return None
    return 1 + sum(1 for x in gruppo if campo(x) is not None and campo(x) > v)


def densita(c):
    return c['p25'] / c['km'] if c.get('km') else None


def variazione(c):
    return (c['p25'] - c['p24']) / c['p24'] * 100 if c.get('p24') else None


def aggregato(gruppo):
    """Densità e variazione dei residenti dell'insieme dei comuni (totali, non media dei singoli comuni)."""
    p25 = sum(c['p25'] for c in gruppo); km = sum(c['km'] for c in gruppo if c.get('km'))
    con24 = [c for c in gruppo if c.get('p24')]
    p24 = sum(c['p24'] for c in con24); p25b = sum(c['p25'] for c in con24)
    return {'dens': p25 / km if km else None, 'var': (p25b - p24) / p24 * 100 if p24 else None, 'p25': p25}


def ultima_modifica(percorso_file):
    """Data dell'ultima modifica reale del file: oggi se è cambiato rispetto all'ultimo commit, altrimenti la data di quel commit."""
    oggi = datetime.date.today().isoformat()
    rel = str(percorso_file.relative_to(RADICE))
    try:
        cambiato = subprocess.run(['git', 'status', '--porcelain', '--', rel], cwd=RADICE, capture_output=True, text=True, check=True).stdout.strip()
        if cambiato:
            return oggi
        data = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', rel], cwd=RADICE, capture_output=True, text=True, check=True).stdout.strip()
        return data or oggi
    except (OSError, subprocess.CalledProcessError):
        return oggi


STILE = """<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;font-family:system-ui,"Segoe UI",sans-serif;background:#F8F7F4;color:#202226;line-height:1.55}
a{color:#0E4273}a:focus-visible,.bott:focus-visible{outline:3px solid #0B3359;outline-offset:2px;box-shadow:0 0 0 5px #F7D678}
header{background:#07213A;color:#fff;padding:12px 16px}header a{color:#fff;font-weight:700;text-decoration:none;letter-spacing:.04em}
nav.menu{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:6px;font-size:14px}nav.menu a{font-weight:600;letter-spacing:0;color:#F7D678}nav.menu a:hover{text-decoration:underline}
main{max-width:56rem;margin:0 auto;padding:16px}nav.percorso{font-size:14px;color:#52565E;margin:4px 0 12px}nav.percorso ol{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px}nav.percorso li+li:before{content:"›";margin-right:6px;color:#8A5313}
h1{font-family:Georgia,serif;color:#0B3359;font-size:clamp(1.6rem,5vw,2.3rem);line-height:1.2;margin:0 0 8px}h2{font-family:Georgia,serif;color:#0B3359;font-size:1.25rem;margin:28px 0 8px}
.bott{display:inline-block;background:#D8973C;color:#07213A;font-weight:700;text-decoration:none;border-radius:10px;padding:12px 18px;margin:8px 8px 8px 0}.bott.sec{background:#fff;border:1px solid #B6D4EE;color:#0E4273}
.riquadro{background:#fff;border:1px solid rgba(216,151,60,.35);border-radius:12px;padding:4px 12px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:8px 6px;border-bottom:1px solid #F4F1EA;vertical-align:top}thead th{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#32353B}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.fonte{font-size:12px;color:#52565E}.dv{color:#C1292E;font-style:italic}
ul.elenco{columns:2 14rem;padding-left:18px}footer{max-width:56rem;margin:24px auto;padding:0 16px 32px;font-size:13px;color:#52565E}
</style>"""


def pagina_html(percorso, titolo, descr, briciole, corpo, extra_ld=None):
    """briciole: elenco di (nome, percorso relativo al sito o None per la pagina corrente)."""
    url = f'{SITO}/{percorso}' if percorso else f'{SITO}/'
    su = '../' * percorso.count('/')
    ld = [{'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': k + 1, 'name': n, 'item': f'{SITO}/{p}' if p is not None else url} for k, (n, p) in enumerate(briciole)]}]
    if extra_ld:
        ld.append(extra_ld)
    bric = ''.join(f'<li><a href="{su}{p}">{e(n)}</a></li>' if p is not None else f'<li aria-current="page">{e(n)}</li>' for n, p in briciole)
    ld_txt = ''.join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False).replace('</', '<\\/') + '</script>\n' for x in ld)
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titolo)}</title>
<meta name="description" content="{e(descr)}">
<link rel="canonical" href="{url}">
<link rel="icon" href="{su}favicon.ico" sizes="any">
<meta name="theme-color" content="#0B3359">
<meta property="og:type" content="website">
<meta property="og:locale" content="it_IT">
<meta property="og:site_name" content="Atlante FVG">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(titolo)}">
<meta property="og:description" content="{e(descr)}">
<meta property="og:image" content="{SITO}/anteprima.jpg">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Logo Atlante FVG con la scritta: i 215 comuni del Friuli Venezia Giulia">
<meta name="twitter:card" content="summary_large_image">
<script data-goatcounter="https://guidocostalonga.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
{ld_txt}{STILE}
</head>
<body>
<header><a href="{su}">ATLANTE FVG</a> · i comuni del Friuli Venezia Giulia<nav class="menu" aria-label="Menu principale"><a href="{su}comuni/">Comuni</a><a href="{su}provincia/gorizia/">Gorizia</a><a href="{su}provincia/pordenone/">Pordenone</a><a href="{su}provincia/trieste/">Trieste</a><a href="{su}provincia/udine/">Udine</a><a href="{su}mappe/">Mappe</a><a href="{su}metodo/">Metodo e fonti</a></nav></header>
<main>
<nav class="percorso" aria-label="Percorso"><ol>{bric}</ol></nav>
{corpo}
</main>
<footer><p>Hai trovato un errore? Segnalalo <a href="{segnala(url, titolo)}">per posta a {POSTA}</a> oppure <a href="{segnala_wa(url, titolo)}" target="_blank" rel="noopener">via WhatsApp</a>: il messaggio contiene già l'indirizzo della pagina.</p>Atlante FVG raccoglie dati pubblici con la loro fonte e la loro data. Per come sono trattati i dati vedi <a href="{su}metodo/">Metodo e fonti</a>. Province: <a href="{su}provincia/gorizia/">Gorizia</a> · <a href="{su}provincia/pordenone/">Pordenone</a> · <a href="{su}provincia/trieste/">Trieste</a> · <a href="{su}provincia/udine/">Udine</a>. Pagine: <a href="{su}">Inizio</a> · <a href="{su}mappe/">Mappe</a> · <a href="{su}confronto/">Confronto</a> · <a href="{su}comuni/">Comuni</a> · <a href="{su}archivio/">Archivio</a> · <a href="{su}autobus/">Autobus</a> · <a href="{su}orari/">Orari degli autobus</a> · <a href="{su}bandi/">Bandi</a> · <a href="{su}opere/">Opere pubbliche</a> · <a href="{su}finanziamenti/">Finanziamenti</a> · <a href="{su}pnrr/">PNRR</a> · <a href="{su}bilancio-regionale/">Bilancio della Regione</a> · <a href="{su}consiglio/">Consiglio regionale</a> · <a href="{su}servizi/">Servizi sul territorio</a> · <a href="{su}strutture/">Strutture ricettive</a> · <a href="{su}aggiornamenti/">Cosa è cambiato</a> · <a href="{su}meteo/">Meteo</a> · <a href="{su}stradario/">Stradario</a> · <a href="{su}catasto/">Catasto</a> · <a href="{su}ambiente/">Allerte e aria</a>.</footer>
</body>
</html>
"""


def fonti_manifest(man):
    return {f['id']: f for f in man['manifest']}


def link_fonte(f, testo):
    u = (f or {}).get('fonte', '')
    return f'<a href="{e(u)}">{e(testo)}</a>' if u.startswith('http') else e(testo)


def pagina_comune(c, db, fm, simili, prec, succ, vicini):
    s = slug(c['n'])
    pv = PROVINCE.get(c['pv'], c['pv'])
    prov = [x for x in db['c'] if x['pv'] == c['pv']]
    tutti = db['c']
    var = variazione(c)
    dens = densita(c)
    ag_p, ag_r = aggregato(prov), aggregato(tutti)
    titolo = f"{c['n']} ({c['pv']}): residenti, sindaco e servizi · Atlante FVG"
    if len(titolo) > 65:  # i nomi lunghi restano leggibili nei risultati di ricerca
        titolo = f"{c['n']} ({c['pv']}): residenti, sindaco e servizi"
    descr = (f"{c['n']}, provincia di {pv}: {migliaia(c['p25'])} residenti al 31 dicembre 2025. "
             'Sindaco, servizi, Terzo settore, turismo, elezioni e fonti ufficiali del comune.')
    if len(descr) > 160:  # i motori di ricerca tagliano le descrizioni più lunghe
        descr = (f"{c['n']} ({c['pv']}): {migliaia(c['p25'])} residenti al 31 dicembre 2025. "
                 'Sindaco, servizi, Terzo settore, turismo, elezioni e fonti ufficiali.')
    agg = c.get('agg') or ''
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', agg)
    vecchia = bool(m) and datetime.date(int(m[3]), int(m[2]), int(m[1])) < datetime.date(2024, 10, 5)
    sindaco = e(nome_proprio(c.get('sin'))) if c.get('sin') else 'non indicato'
    nota_sin = (f'<span class="dv">anagrafe ferma al {e(data_estesa(agg))}: DA VERIFICARE</span>' if vecchia
                else f'anagrafe aggiornata dal comune il {e(data_estesa(agg))}' if agg else '')
    f_runts = link_fonte(fm.get('RUNTS_FVG'), 'RUNTS (Registro unico nazionale del Terzo settore), elenco del 5 ottobre 2026')
    f_tur = link_fonte(fm.get('Turismo_comunale'), 'portale dei dati aperti della Regione FVG')
    rsa = c.get('rsa') or 0
    righe = [
        ('Residenti al 31 dicembre 2025', migliaia(c['p25']), e(ANNUARIO[0])),
        ('Residenti al 31 dicembre 2024', migliaia(c['p24']) if c.get('p24') else 'dato non disponibile', e(ANNUARIO[0])),
        ('Variazione in un anno', percento(var) if var is not None else 'dato non disponibile', e(ANNUARIO[0])),
        ('Maschi e femmine al 31 dicembre 2025', f"{migliaia(c['m'])} maschi, {migliaia(c['f'])} femmine" if c.get('m') is not None and c.get('f') is not None else 'dato non disponibile', e(ANNUARIO[1])),
        ('Superficie', decimale(c['km'], 2) + ' km²' if c.get('km') else 'dato non disponibile', e(ANNUARIO[0])),
        ('Densità (abitanti per km²)', decimale(dens) if dens is not None else 'dato non disponibile', 'calcolata da residenti e superficie'),
        ('Sindaco in anagrafe', sindaco, link_fonte(fm.get('Amministratori_locali'), 'anagrafe regionale degli amministratori locali') + (', ' + nota_sin if nota_sin else '')),
        ('Prossime elezioni comunali', str(c['el']) if c.get('el') else 'dato non disponibile', link_fonte(fm.get('Amministratori_locali'), 'anagrafe regionale degli amministratori locali')),
        ('Enti del Terzo settore iscritti al RUNTS', migliaia(c.get('ru') or 0), f_runts),
        ('di cui associazioni di promozione sociale', migliaia(c.get('aps') or 0), f_runts + ', sezione del registro'),
        ('di cui organizzazioni di volontariato', migliaia(c.get('odv') or 0), f_runts + ', sezione del registro'),
        ('Farmacie', migliaia(c.get('fa') or 0), link_fonte(fm.get('Farmacie'), 'portale dei dati aperti della Regione FVG')),
        ('Istituti scolastici statali con sede nel comune', migliaia(c.get('sc') or 0), link_fonte(fm.get('Scuole_2026_27'), 'Ufficio scolastico regionale, anno scolastico 2026/2027')),
        ('Residenze per anziani', migliaia(rsa) + (f" ({migliaia(c.get('rpl') or 0)} posti letto)" if rsa else ''), link_fonte(fm.get('Residenze_anziani'), 'portale dei dati aperti della Regione FVG')),
        ('Arrivi turistici nel 2025', migliaia(c.get('ar') or 0), f_tur),
        ('Presenze turistiche nel 2025', migliaia(c.get('pr') or 0), link_fonte(fm.get('Turismo_comunale'), 'notti nelle strutture ricettive, portale dei dati aperti della Regione FVG')),
        ('Quota di presenze straniere nel 2025', decimale(c['prs'] / c['pr'] * 100) + '%' if c.get('pr') else 'nessuna presenza registrata', f_tur + ', calcolata su presenze straniere e totali'),
    ]
    tab = ''.join(f'<tr><th scope="row">{e(a)}<div class="fonte" style="font-weight:400">Fonte: {f}</div></th><td class="n">{b}</td></tr>' for a, b, f in righe)
    # posizioni e confronti, calcolati dai residenti e dalle superfici dell'Annuario
    pos_p, pos_r = posizione(c, prov, lambda x: x['p25']), posizione(c, tutti, lambda x: x['p25'])
    den_p, den_r = posizione(c, prov, densita), posizione(c, tutti, densita)
    def cella(v, fmt):
        return fmt(v) if v is not None else 'dato non disponibile'
    confronto = [
        ('Densità (abitanti per km²)', cella(dens, decimale), cella(ag_p['dens'], decimale), cella(ag_r['dens'], decimale)),
        ('Variazione dei residenti 2024-2025', cella(var, percento), cella(ag_p['var'], percento), cella(ag_r['var'], percento)),
        ('Posizione per numero di residenti', '', f'{pos_p}° su {len(prov)}', f'{pos_r}° su {len(tutti)}'),
        ('Posizione per densità', '', f'{den_p}° su {len(prov)}' if den_p else 'dato non disponibile', f'{den_r}° su {len(tutti)}' if den_r else 'dato non disponibile'),
    ]
    tab_conf = ''.join(f'<tr><th scope="row">{e(a)}</th><td class="n">{b}</td><td class="n">{x}</td><td class="n">{y}</td></tr>' for a, b, x, y in confronto)
    vs = '&amp;confronta=' + ','.join([s] + [slug(x['n']) for x in simili])
    vic = sorted(vicini, key=lambda x: x['n'])
    corpo = f"""<h1>{e(c['n'])}</h1>
<p>Comune della <a href="../../provincia/{slug(pv)}/">provincia di {e(pv)}</a>{' (nome ufficiale: ' + e(c['ml']) + ')' if c.get('ml') and c['ml'] != c['n'] else ''}, con <b>{migliaia(c['p25'])} residenti</b> al 31 dicembre 2025. Codice ISTAT {e(c['id'])}.</p>
<p>Per numero di residenti è al {pos_p}° posto fra i {len(prov)} comuni della provincia di {e(pv)} e al {pos_r}° posto fra i {len(tutti)} comuni del Friuli Venezia Giulia.</p>
<p><a class="bott" href="../../?comune={s}">Apri la scheda completa nell'Atlante</a></p>
<h2>I dati principali</h2>
<div class="riquadro"><table><caption class="fonte" style="text-align:left;padding:8px 0">Dati di {e(c['n'])} con la loro fonte</caption><thead><tr><th scope="col">Dato e fonte</th><th scope="col" style="text-align:right">Valore</th></tr></thead><tbody>{tab}</tbody></table></div>
<p class="fonte">Lo zero indica che la fonte non riporta voci per il comune. Altri dati (età, redditi, bilanci, opere pubbliche, rischio idrogeologico, elezioni) sono nella scheda completa.</p>
<h2>{e(c['n'])} a confronto con la provincia e la regione</h2>
<div class="riquadro"><table><caption class="fonte" style="text-align:left;padding:8px 0">Fonte: {e(ANNUARIO[0])}. I valori della provincia e della regione sono calcolati sull'insieme dei loro comuni; la posizione 1 è quella con il valore più alto.</caption><thead><tr><th scope="col">Indicatore</th><th scope="col" style="text-align:right">{e(c['n'])}</th><th scope="col" style="text-align:right">Provincia di {e(pv)}</th><th scope="col" style="text-align:right">Friuli Venezia Giulia</th></tr></thead><tbody>{tab_conf}</tbody></table></div>
<h2>Comuni confinanti</h2>
<ul class="elenco">{''.join(f'<li><a href="../{slug(x["n"])}/">{e(x["n"])}</a> ({x["pv"]}), {migliaia(x["p25"])} residenti</li>' for x in vic)}</ul>
<p class="fonte">Comuni del Friuli Venezia Giulia che condividono almeno {CONFINE_MIN} metri di confine con {e(c['n'])}, calcolati dai confini comunali delle mappe dell'Atlante. Non sono elencati i comuni di altre regioni o di altri Stati.</p>
<h2>Approfondisci</h2>
<p><a class="bott sec" href="../../?pagina=mappe&amp;comune={s}">{e(c['n'])} sulle mappe</a><a class="bott sec" href="../../?pagina=confronto{vs}">Confronta con comuni di taglia simile</a><a class="bott sec" href="../../?pagina=archivio&amp;comune={s}">Tutte le righe dell'archivio</a><a class="bott sec" href="../../?pagina=autobus&amp;comune={s}">Autobus e fermate</a><a class="bott sec" href="../../?pagina=ambiente&amp;comune={s}">Allerte e aria</a><a class="bott sec" href="../../meteo/#{s}">Meteo di {e(c['n'])}</a><a class="bott sec" href="../../stradario/?comune={s}">{e(c['n'])} sullo stradario</a><a class="bott sec" href="../../catasto/">Catasto sulla mappa</a></p>
<h2>Comuni di taglia simile in provincia di {e(pv)}</h2>
<ul class="elenco">{''.join(f'<li><a href="../{slug(x["n"])}/">{e(x["n"])}</a>, {migliaia(x["p25"])} residenti</li>' for x in simili)}</ul>
<p class="fonte">In ordine alfabetico: {f'<a href="../{slug(prec["n"])}/">‹ {e(prec["n"])}</a>' if prec else ''}{' · ' if prec and succ else ''}{f'<a href="../{slug(succ["n"])}/">{e(succ["n"])} ›</a>' if succ else ''} · <a href="../../provincia/{slug(pv)}/">i comuni della provincia di {e(pv)}</a> · <a href="../../comuni/">tutti i 215 comuni</a></p>"""
    br = [('Atlante FVG', ''), (f'Provincia di {pv}', f'provincia/{slug(pv)}/'), (c['n'], None)]
    luogo = {'@context': 'https://schema.org', '@type': 'City', 'name': c['n'], 'url': f'{SITO}/c/{s}/',
             'identifier': {'@type': 'PropertyValue', 'propertyID': 'Codice ISTAT', 'value': str(c['id'])},
             'containedInPlace': {'@type': 'AdministrativeArea', 'name': f'Provincia di {pv}',
                                  'containedInPlace': {'@type': 'AdministrativeArea', 'name': 'Friuli Venezia Giulia'}}}
    if c.get('ml') and c['ml'] != c['n']:
        luogo['alternateName'] = c['ml']
    return s, pagina_html(f'c/{s}/', titolo, descr, br, corpo, luogo)


def pagina_provincia(pv, comuni):
    nome = PROVINCE[pv]
    tot = sum(c['p25'] for c in comuni)
    titolo = f'Provincia di {nome}: i {len(comuni)} comuni · Atlante FVG'
    descr = f'I {len(comuni)} comuni della provincia di {nome}, con {migliaia(tot)} residenti al 31 dicembre 2025: elenco con residenti e collegamenti ai dati di ogni comune.'
    righe = ''.join(f'<tr><th scope="row"><a href="../../c/{slug(c["n"])}/">{e(c["n"])}</a></th><td class="n">{migliaia(c["p25"])}</td><td class="n">{c.get("el") or ""}</td></tr>' for c in sorted(comuni, key=lambda c: c['n']))
    corpo = f"""<h1>Provincia di {e(nome)}</h1>
<p>{len(comuni)} comuni e <b>{migliaia(tot)} residenti</b> al 31 dicembre 2025 ({e(ANNUARIO[0])}).</p>
<p><a class="bott" href="../../?provincia={pv}&amp;pagina=comuni">Apri i comuni della provincia nell'Atlante</a><a class="bott sec" href="../../?provincia={pv}&amp;pagina=mappe">Sulle mappe</a></p>
<h2>I comuni</h2>
<div class="riquadro"><table><thead><tr><th scope="col">Comune</th><th scope="col" style="text-align:right">Residenti 2025</th><th scope="col" style="text-align:right">Prossime elezioni</th></tr></thead><tbody>{righe}</tbody></table></div>
<p class="fonte">Altre province: {' · '.join(f'<a href="../{slug(n)}/">{e(n)}</a>' for k, n in PROVINCE.items() if k != pv)}</p>"""
    return pagina_html(f'provincia/{slug(nome)}/', titolo, descr, [('Atlante FVG', ''), (f'Provincia di {nome}', None)], corpo)


# fonti degli indicatori: le stesse costanti usate da index.html (le parti calcolate al momento sono omesse)
FONTI_IND = {'F_ANN': 'Annuario statistico regionale 2026', 'F_RFVG': 'banca dati «Regione FVG Dati» del 16 settembre 2026',
             'F_REG': 'Portale dei dati aperti della Regione FVG e Annuario statistico regionale 2026',
             'F_OP': 'OpenCUP, Presidenza del Consiglio dei ministri (DIPE)', 'F_PNRR': 'Italia Domani e ReGiS, tramite OpenPNRR (Fondazione Openpolis)',
             'F_TPL': 'Orari TPL FVG (GTFS tramite BusOne)'}


def fonte_indicatore(espr):
    parti = []
    for tok in re.findall(r"'((?:[^'\\]|\\.)*)'|`([^`$]*)`|\b(F_[A-Z]+)\b", espr):
        if tok[2]:
            if tok[2] not in FONTI_IND:
                return None
            parti.append(FONTI_IND[tok[2]])
        else:
            parti.append((tok[0] or tok[1]).replace("\\'", "'"))
    return ''.join(parti).strip(' ,') or None


def indicatori_html():
    """Elenco degli indicatori delle mappe e del confronto, letto dalle definizioni di index.html."""
    testo = (RADICE / 'index.html').read_text(encoding='utf-8')
    gruppi = collections.OrderedDict()
    for g, t, resto in re.findall(r"\{ g: '([^']+)', id: '[^']*', t: '((?:[^'\\]|\\.)*)'(.*?)\}(?=,?\s*\n)", testo):
        m = re.search(r"fonte: (.*)$", resto)
        gruppi.setdefault(g, []).append((t.replace("\\'", "'"), fonte_indicatore(m.group(1)) if m else None))
    n = sum(len(v) for v in gruppi.values())
    h = f'<h2>Gli indicatori disponibili ({n})</h2>\n<p>Ogni indicatore è mostrato comune per comune, con fonte, periodo e copertura indicati accanto alla mappa e nella tabella.</p>\n'
    for g, voci in gruppi.items():
        h += f'<h3>{e(g)}</h3>\n<ul>' + ''.join(f'<li>{e(t)}' + (f' <span class="fonte">· {e(f)}</span>' if f else '') + '</li>' for t, f in voci) + '</ul>\n'
    return h


def rete_autobus_html(db, man):
    """Fermate per provincia, contate dagli orari GTFS già usati dalla pagina degli autobus."""
    tpl = leggi_dati('_tpl_0.txt')
    pv_di = {c['id']: c['pv'] for c in db['c']}
    per_pv, comuni_serviti, fuori = collections.Counter(), collections.defaultdict(set), 0
    for f in tpl['fermate']:
        if f[3] is None or f[3] < 0:
            fuori += 1; continue
        ist = man['istat'][f[3]]; per_pv[pv_di[ist]] += 1; comuni_serviti[pv_di[ist]].add(ist)
    v = tpl.get('versione', '')
    data = data_estesa(f'{v[0:4]}-{v[4:6]}-{v[6:8]}') if re.match(r'^\d{8}', v) else ''
    righe = ''.join(f'<tr><th scope="row"><a href="../provincia/{slug(n)}/">Provincia di {e(n)}</a></th><td class="n">{migliaia(per_pv[pv])}</td>'
                    f'<td class="n">{len(comuni_serviti[pv])} su {sum(1 for c in db["c"] if c["pv"] == pv)}</td></tr>' for pv, n in PROVINCE.items())
    h = (f'<h2>La rete in numeri</h2>\n<div class="riquadro"><table><caption class="fonte" style="text-align:left;padding:8px 0">Fonte: {e(tpl.get("fonte", ""))}'
         + (f', orari nella versione del {e(data)}' if data else '') + '.</caption><thead><tr><th scope="col">Provincia</th><th scope="col" style="text-align:right">Fermate</th>'
         '<th scope="col" style="text-align:right">Comuni con almeno una fermata</th></tr></thead><tbody>' + righe + '</tbody></table></div>\n')
    if fuori:
        h += f'<p class="fonte">Altre {migliaia(fuori)} fermate della rete sono fuori dai confini regionali.</p>\n'
    return h


def zone_allerta_html(db, man):
    """Comuni di ogni zona d'allerta, dagli elenchi già usati da index.html (costanti ZONA_COM e ZONE_AL)."""
    testo = (RADICE / 'index.html').read_text(encoding='utf-8')
    zc = re.search(r"^const ZONA_COM = '([A-D]+)';", testo, re.M)
    za = re.search(r"^const ZONE_AL = \{(.*)\};", testo, re.M)
    nota = re.search(r"^// zona d'allerta di ogni comune.*?, (dagli elenchi .*)$", testo, re.M)
    if not (zc and za) or len(zc.group(1)) != len(man['istat']):
        return ''
    nomi = dict(re.findall(r"""([A-D]): ['"]([^'"]+)['"]""", za.group(1)))
    per_id = {c['id']: c for c in db['c']}
    h = '<h2>Le zone d\'allerta e i loro comuni</h2>\n<p>Il bollettino di criticità divide il Friuli Venezia Giulia in quattro zone d\'allerta: l\'allerta del giorno vale per tutti i comuni della zona.</p>\n'
    for z in sorted(nomi):
        cc = sorted((per_id[man['istat'][i]] for i, x in enumerate(zc.group(1)) if x == z), key=lambda c: c['n'])
        h += (f'<h3>Zona {z}: {e(nomi[z])} ({len(cc)} comuni)</h3>\n<ul class="elenco">'
              + ''.join(f'<li><a href="../c/{slug(c["n"])}/">{e(c["n"])}</a></li>' for c in cc) + '</ul>\n')
    if nota:
        h += f'<p class="fonte">Fonte: Dipartimento della Protezione civile, {e(nota.group(1).rstrip(". "))}.</p>\n'
    return h


def pagina_argomento(nome, titolo, descr, testi, db, man):
    corpo = f'<h1>{e(titolo)}</h1>\n' + ''.join(f'<p>{e(t)}</p>\n' for t in testi) + f'<p><a class="bott" href="../?pagina={nome}">{e(ICONA_PAG[nome])}</a></p>\n'
    if nome == 'autobus':
        corpo += '<p><a class="bott sec" href="../orari/">Orari degli autobus</a></p>\n'
    ld = None
    if nome in ('mappe', 'confronto'):
        corpo += indicatori_html()
    if nome == 'autobus':
        corpo += rete_autobus_html(db, man)
    if nome == 'ambiente':
        corpo += zone_allerta_html(db, man)
    if nome == 'comuni':
        for pv, n in PROVINCE.items():
            cc = sorted((c for c in db['c'] if c['pv'] == pv), key=lambda c: c['n'])
            corpo += f'<h2><a href="../provincia/{slug(n)}/">Provincia di {e(n)}</a>: {len(cc)} comuni</h2>\n<ul class="elenco">' + ''.join(f'<li><a href="../c/{slug(c["n"])}/">{e(c["n"])}</a></li>' for c in cc) + '</ul>\n'
    if nome == 'metodo':
        reg = json.loads((RADICE / 'dati' / 'correzioni.json').read_text(encoding='utf-8'))
        corpo += (f'<h2>Segnalazioni e registro delle correzioni</h2>\n<p>Un dato sbagliato si segnala con «Segnala un errore» (nella scheda di ogni comune, sotto le mappe, nel confronto, nelle righe dell\'archivio) oppure scrivendo a <a href="mailto:{POSTA}">{POSTA}</a> o via WhatsApp al numero <a href="https://wa.me/{WHATSAPP}">+39 328 369 2227</a>. Ogni segnalazione si controlla sulla fonte ufficiale; un dato si corregge solo se la fonte lo conferma.</p>\n')
        if reg['voci']:
            corpo += '<div class="riquadro"><table><thead><tr><th scope="col">Data</th><th scope="col">Dato</th><th scope="col">Prima</th><th scope="col">Dopo</th><th scope="col">Fonte</th></tr></thead><tbody>' + ''.join(
                f'<tr><td>{e(data_estesa(v["data"]))}</td><td>{e(v["dato"])}</td><td>{e(v["prima"])}</td><td>{e(v["dopo"])}</td><td class="fonte">{e(v["fonte"])}</td></tr>' for v in reg['voci']) + '</tbody></table></div>\n'
        else:
            corpo += f'<p>Nessuna correzione registrata finora. Il registro è attivo dal {e(data_estesa(reg["inizio"]))}.</p>\n'
        corpo += ('<h2>Statistiche di visita e privacy</h2>\n<p>L\'Atlante conta le visite con <a href="https://www.goatcounter.com/help/privacy">GoatCounter</a>, che non usa cookie né altri sistemi di memoria nel browser e non conserva l\'indirizzo IP né identificativi di chi visita. Si contano in forma aggregata le pagine viste e l\'uso di ricerca, filtri, confronto e download, oltre agli errori di caricamento; per la ricerca solo il fatto che un comune è stato scelto, non il testo scritto. I dati stanno su server di Hetzner Online in Finlandia e in Germania e non sono ceduti a terzi. Non essendoci cookie né tracciamento delle persone, non viene chiesto il consenso.</p>\n'
                  f'<p>Chi scrive a {POSTA} comunica il proprio indirizzo di posta; chi usa WhatsApp comunica il proprio numero di telefono, e il messaggio passa dal servizio WhatsApp di Meta. Indirizzo e numero servono solo a rispondere alla segnalazione.</p>\n'
                  f'<p>Titolare del trattamento: Guido Costalonga. Per qualsiasi richiesta sui dati: <a href="mailto:{POSTA}">{POSTA}</a>.</p>\n')
        m = re.search(r'<script type="text/html" id="testoAvvertenze">\s*(.*?)\s*</script>', (RADICE / 'index.html').read_text(encoding='utf-8'), re.S)
        if m:
            corpo += '<h2>Avvertenze</h2>\n' + re.sub(r' class="[^"]*"', '', m.group(1)).replace(' target="_blank" rel="noopener"', '') + '\n'
    if nome == 'archivio':
        fogli = man['manifest']
        corpo += f'<h2>I {len(fogli)} fogli dell\'archivio</h2>\n<div class="riquadro"><table><thead><tr><th scope="col">Foglio</th><th scope="col">Ambito</th><th scope="col" style="text-align:right">Righe</th><th scope="col">Fonte</th></tr></thead><tbody>'
        for f in fogli:
            fonte = f['fonte'] or ''
            breve = e(fonte[:70]) + ('…' if len(fonte) > 70 else '')
            cella = f'<a href="{e(fonte)}">{breve}</a>' if fonte.startswith('http') else e(fonte[:160])
            corpo += (f'<tr><th scope="row">{e(f.get("nome") or f["id"].replace("_", " "))}</th><td>{e(f["ambito"])}</td><td class="n">{migliaia(f["righe"])}</td>'
                      f'<td class="fonte">{cella}</td></tr>')
        corpo += '</tbody></table></div>\n'
        date = sorted(f['cons'] for f in fogli if re.match(r'^\d{4}-\d{2}-\d{2}$', f.get('cons') or ''))
        fonti = sorted({f['fonte'] for f in fogli if (f.get('fonte') or '').startswith('http')})
        ld = {'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Database dei comuni del Friuli Venezia Giulia',
              'description': f'Raccolta di {len(fogli)} fogli di dati pubblici sui 215 comuni del Friuli Venezia Giulia: popolazione, amministratori, Terzo settore, servizi, scuole, turismo, bilanci, elezioni, ambiente e trasporti, con la fonte di ogni foglio. Consultabile riga per riga e scaricabile in CSV ed Excel.',
              'url': f'{SITO}/archivio/', 'inLanguage': 'it', 'isAccessibleForFree': True,
              'keywords': ['Friuli Venezia Giulia', 'comuni', 'dati aperti', 'statistiche comunali'],
              'spatialCoverage': {'@type': 'Place', 'name': 'Friuli Venezia Giulia'},
              'creator': {'@type': 'Organization', 'name': 'Atlante FVG', 'url': f'{SITO}/'},
              'isBasedOn': fonti[:100]}
        if date:
            ld['dateModified'] = date[-1]
    return pagina_html(f'{nome}/', f'{titolo} · Atlante FVG', descr, [('Atlante FVG', ''), (titolo, None)], corpo, ld)


def pagina_404(comuni):
    """Pagina per gli indirizzi inesistenti (GitHub Pages la serve con lo stato 404): percorsi assoluti, nessun canonico."""
    elenco = ''.join(f'<h2><a href="/provincia/{slug(n)}/">Provincia di {e(n)}</a></h2>\n<ul class="elenco">'
                     + ''.join(f'<li><a href="/c/{slug(c["n"])}/">{e(c["n"])}</a></li>' for c in sorted((c for c in comuni if c['pv'] == pv), key=lambda c: c['n']))
                     + '</ul>\n' for pv, n in PROVINCE.items())
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pagina non trovata · Atlante FVG</title>
<meta name="robots" content="noindex">
<link rel="icon" href="/favicon.ico" sizes="any">
<meta name="theme-color" content="#0B3359">
{STILE}
</head>
<body>
<header><a href="/">ATLANTE FVG</a> · i comuni del Friuli Venezia Giulia</header>
<main>
<h1>Pagina non trovata</h1>
<p>L'indirizzo che hai aperto non esiste o è cambiato. Da qui puoi raggiungere ogni comune del Friuli Venezia Giulia.</p>
<p><a class="bott" href="/">Vai all'Atlante FVG</a><a class="bott sec" href="/comuni/">I 215 comuni</a><a class="bott sec" href="/metodo/">Metodo e fonti</a></p>
{elenco}</main>
<footer>Se pensi che il collegamento dovrebbe funzionare, scrivi a <a href="mailto:{POSTA}">{POSTA}</a> indicando l'indirizzo.</footer>
</body>
</html>
"""


def main():
    testo = (RADICE / 'index.html').read_text(encoding='utf-8')
    db = json.loads(re.search(r'^const DB = (.*);$', testo, re.M).group(1))
    man = json.loads(re.search(r'^const MAN = (.*);$', testo, re.M).group(1))
    fm = fonti_manifest(man)
    comuni = sorted(db['c'], key=lambda c: c['n'])
    if len({slug(c['n']) for c in comuni}) != len(comuni):
        raise SystemExit('Due comuni hanno lo stesso indirizzo: controllare la funzione slug')
    for cartella in ('c', 'provincia'):
        if (RADICE / cartella).exists():
            shutil.rmtree(RADICE / cartella)
    per_id = {c['id']: c for c in db['c']}
    conf = confinanti(man['istat'])
    senza = [c['n'] for c in comuni if not conf.get(c['id'])]
    if senza or any(c['id'] not in conf.get(o, []) for c in comuni for o in conf.get(c['id'], [])):
        raise SystemExit(f'Calcolo dei confinanti non affidabile (comuni senza confinanti: {senza}): controllare dati/_mappe_0.txt')
    for k, c in enumerate(comuni):
        stessi = [x for x in db['c'] if x['pv'] == c['pv'] and x['id'] != c['id']]
        simili = sorted(stessi, key=lambda x: abs(x['p25'] - c['p25']))[:3]
        s, h = pagina_comune(c, db, fm, simili, comuni[k - 1] if k else None, comuni[k + 1] if k + 1 < len(comuni) else None,
                            [per_id[o] for o in conf[c['id']]])
        (RADICE / 'c' / s).mkdir(parents=True)
        (RADICE / 'c' / s / 'index.html').write_text(h, encoding='utf-8')
    for pv, n in PROVINCE.items():
        d = RADICE / 'provincia' / slug(n); d.mkdir(parents=True)
        (d / 'index.html').write_text(pagina_provincia(pv, [c for c in db['c'] if c['pv'] == pv]), encoding='utf-8')
    for nome, titolo, descr, testi in PAGINE:
        (RADICE / nome).mkdir(exist_ok=True)
        (RADICE / nome / 'index.html').write_text(pagina_argomento(nome, titolo, descr, testi, db, man), encoding='utf-8')
    # una sitemap per tipo di pagina, raccolte in un indice; <lastmod> è la data dell'ultima modifica reale di ogni file
    gruppi = {
        'servizi': [''] + [f'{nome}/' for nome, *_ in PAGINE] + [f'{nome}/' for nome in PAGINE_FISSE],
        'province': [f'provincia/{slug(n)}/' for n in PROVINCE.values()],
        'comuni': [f'c/{slug(c["n"])}/' for c in comuni],
    }
    indice, voci = [], 0
    for gruppo, percorsi in gruppi.items():
        date = [ultima_modifica(RADICE / pth / 'index.html') for pth in percorsi]
        righe = [f'  <url><loc>{SITO}/{pth}</loc><lastmod>{d}</lastmod></url>' for pth, d in zip(percorsi, date)]
        nome_file = f'sitemap-{gruppo}.xml'
        nuovo = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                 + '\n'.join(righe) + '\n</urlset>\n')
        f = RADICE / nome_file
        if not f.exists() or f.read_text(encoding='utf-8') != nuovo:
            f.write_text(nuovo, encoding='utf-8')
        indice.append(f'  <sitemap><loc>{SITO}/{nome_file}</loc><lastmod>{max(date)}</lastmod></sitemap>')
        voci += len(righe)
    (RADICE / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                         + '\n'.join(indice) + '\n</sitemapindex>\n', encoding='utf-8')
    (RADICE / '404.html').write_text(pagina_404(comuni), encoding='utf-8')
    (RADICE / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITO}/sitemap.xml\n', encoding='utf-8')
    print(f'Pagine: {len(comuni)} comuni, {len(PROVINCE)} province, {len(PAGINE)} argomenti; indice delle sitemap con {voci} indirizzi in {len(gruppi)} file')


if __name__ == '__main__':
    main()
