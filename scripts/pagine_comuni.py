#!/usr/bin/env python3
"""Crea le pagine statiche dell'Atlante, leggibili anche senza eseguire il programma della pagina.

- c/<comune>/index.html: una pagina per ognuno dei 215 comuni, con i dati principali, le fonti,
  il percorso (Atlante FVG > provincia > comune) e i collegamenti alle altre pagine.
- provincia/<nome>/index.html: l'elenco dei comuni di ogni provincia.
- mappe/, confronto/, autobus/, ambiente/, comuni/, archivio/, metodo/: una pagina per argomento,
  con il pulsante che apre la pagina interattiva (atlantefvg.it/?pagina=...).
- sitemap.xml e robots.txt.

Ogni pagina ha titolo e descrizione propri, un solo titolo H1, indirizzo canonico, intestazioni per
l'anteprima nelle condivisioni (WhatsApp, Facebook e simili) e dati strutturati schema.org
(BreadcrumbList; Dataset sulla pagina dell'archivio).

I dati vengono dalle righe `const DB = ...;` e `const MAN = ...;` di index.html.
Usa solo la libreria standard di Python.
"""
import datetime, html, json, re, shutil, unicodedata, urllib.parse
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
SITO = 'https://atlantefvg.it'
PROVINCE = {'UD': 'Udine', 'PN': 'Pordenone', 'GO': 'Gorizia', 'TS': 'Trieste'}
MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']
ANNUARIO = ('Annuario statistico regionale 2026, tavola 19.2',)
# pagine per argomento: indirizzo breve, titolo, descrizione, testo della pagina; devono coincidere con PAGINE in index.html
PAGINE = [
    ('mappe', 'Mappe dei comuni', 'Mappe dei 215 comuni del Friuli Venezia Giulia: popolazione, redditi, servizi, Terzo settore, rischio idrogeologico, bilanci, elezioni e opere pubbliche, comune per comune.',
     ['Oltre trenta indicatori, ognuno con fonte, periodo e copertura: popolazione ed età, redditi, turismo, farmacie, Terzo settore, rischio di frana e di alluvione, bilanci comunali, opere pubbliche, affluenza e liste più votate.',
      'Accanto a ogni mappa c\'è la tabella con gli stessi valori, scaricabile in CSV ed Excel. Ci sono anche le cartine dell\'Annuario statistico regionale e i servizi sul territorio: farmacie, guardie mediche, residenze per anziani.']),
    ('confronto', 'Confronto fra comuni', 'Confronta fino a quattro comuni del Friuli Venezia Giulia, indicatore per indicatore, con i valori assoluti separati da quelli per abitante.',
     ['Si scelgono fino a quattro comuni e si leggono fianco a fianco: popolazione, redditi, servizi, Terzo settore, bilanci, rischio idrogeologico ed elezioni.',
      'I valori assoluti sono separati da quelli per abitante, che permettono di confrontare comuni di taglia diversa. Ogni riga indica il periodo dei dati e segnala quelli meno recenti.']),
    ('autobus', 'Autobus', 'Linee, fermate e arrivi in tempo reale degli autobus del Friuli Venezia Giulia, con la mappa delle vie.',
     ['Le linee del trasporto pubblico locale, le fermate di ogni comune e gli arrivi in tempo reale, con i mezzi in viaggio sulla mappa delle vie.',
      'Fonte: TPL FVG tramite BusOne, rete aggiornata ogni lunedì e arrivi letti al momento.']),
    ('ambiente', 'Allerte meteo e qualità dell\'aria', 'Allerta meteo di oggi e di domani e qualità dell\'aria delle centraline del Friuli Venezia Giulia.',
     ['L\'allerta idrogeologica, idraulica e per temporali di oggi e di domani nelle quattro zone d\'allerta, dal bollettino del Dipartimento della Protezione civile.',
      'Gli ultimi valori validati di PM10, PM2,5, biossido di azoto e ozono delle centraline dell\'ARPA FVG (Agenzia regionale per la protezione dell\'ambiente), ognuno con la sua data.']),
    ('comuni', 'I 215 comuni del Friuli Venezia Giulia', 'Elenco dei 215 comuni del Friuli Venezia Giulia per provincia, con residenti, sindaci, servizi e prossime elezioni.',
     ['Il registro dei 215 comuni: residenti, sindaco in anagrafe con la data di aggiornamento, enti del Terzo settore, presenze turistiche e anno delle prossime elezioni comunali.']),
    ('archivio', 'Archivio dei dati dei comuni', 'Tutti i fogli del database dei comuni del Friuli Venezia Giulia, consultabili riga per riga e scaricabili in CSV ed Excel con fonte e data.',
     ['Ogni foglio del database è consultabile per intero, con tutte le righe e tutte le colonne, filtrabile per comune, per testo e colonna per colonna.',
      'I risultati filtrati si scaricano in CSV ed Excel con fonte, data dei dati e condizioni di riutilizzo. Qui sotto l\'elenco dei fogli con la loro fonte.']),
    ('metodo', 'Metodo e fonti', 'Versioni, date di aggiornamento, fonti, copertura e avvertenze sui dati dell\'Atlante dei comuni del Friuli Venezia Giulia.',
     ['Come sono fatti i dati dell\'Atlante: versioni e date di aggiornamento, fonti con i collegamenti alla documentazione originale, copertura di ogni gruppo di dati, differenza fra zero e dato non disponibile, avvertenze.']),
]
ICONA_PAG = {'mappe': 'Esplora le mappe', 'confronto': 'Apri il confronto', 'autobus': 'Apri gli autobus', 'ambiente': 'Apri allerte e aria', 'comuni': 'Apri il registro dei comuni', 'archivio': 'Apri l\'archivio', 'metodo': 'Apri Metodo e fonti'}

e = html.escape
POSTA = 'info@atlantefvg.it'


def segnala(url, titolo):
    corpo = f'Pagina: {url}\nDato segnalato: \n\nChe cosa non torna:\n\n\nValore corretto e fonte, se li conosci:\n\n'
    q = urllib.parse.urlencode({'subject': f'Segnalazione di errore: {titolo}', 'body': corpo}, quote_via=urllib.parse.quote)
    return e(f'mailto:{POSTA}?{q}')


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


STILE = """<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;font-family:system-ui,"Segoe UI",sans-serif;background:#F8F7F4;color:#202226;line-height:1.55}
a{color:#0E4273}a:focus-visible,.bott:focus-visible{outline:3px solid #0B3359;outline-offset:2px;box-shadow:0 0 0 5px #F7D678}
header{background:#07213A;color:#fff;padding:12px 16px}header a{color:#fff;font-weight:700;text-decoration:none;letter-spacing:.04em}
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
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script data-goatcounter="https://guidocostalonga.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
{ld_txt}{STILE}
</head>
<body>
<header><a href="{su}">ATLANTE FVG</a> · i comuni del Friuli Venezia Giulia</header>
<main>
<nav class="percorso" aria-label="Percorso"><ol>{bric}</ol></nav>
{corpo}
</main>
<footer><p><a href="{segnala(url, titolo)}">Segnala un errore in questa pagina</a> (si apre un messaggio per {POSTA} con l'indirizzo della pagina già scritto).</p>Atlante FVG raccoglie dati pubblici con la loro fonte e la loro data. Per come sono trattati i dati vedi <a href="{su}metodo/">Metodo e fonti</a>. Pagine: <a href="{su}mappe/">Mappe</a> · <a href="{su}confronto/">Confronto</a> · <a href="{su}comuni/">Comuni</a> · <a href="{su}archivio/">Archivio</a> · <a href="{su}autobus/">Autobus</a> · <a href="{su}ambiente/">Allerte e aria</a>.</footer>
</body>
</html>
"""


def fonti_manifest(man):
    return {f['id']: f for f in man['manifest']}


def link_fonte(f, testo):
    u = (f or {}).get('fonte', '')
    return f'<a href="{e(u)}">{e(testo)}</a>' if u.startswith('http') else e(testo)


def pagina_comune(c, db, fm, simili, prec, succ):
    s = slug(c['n'])
    pv = PROVINCE.get(c['pv'], c['pv'])
    var = (c['p25'] - c['p24']) / c['p24'] * 100 if c.get('p24') else None
    titolo = f"{c['n']} ({c['pv']}): dati del comune · Atlante FVG"
    descr = (f"{c['n']}, provincia di {pv}: {migliaia(c['p25'])} residenti al 31 dicembre 2025. "
             'Sindaco, servizi, Terzo settore, turismo, elezioni e fonti ufficiali del comune.')
    agg = c.get('agg') or ''
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', agg)
    vecchia = bool(m) and datetime.date(int(m[3]), int(m[2]), int(m[1])) < datetime.date(2024, 10, 5)
    sindaco = e(nome_proprio(c.get('sin'))) if c.get('sin') else 'non indicato'
    nota_sin = (f'<span class="dv">anagrafe ferma al {e(data_estesa(agg))}: DA VERIFICARE</span>' if vecchia
                else f'anagrafe aggiornata dal comune il {e(data_estesa(agg))}' if agg else '')
    righe = [
        ('Residenti al 31 dicembre 2025', migliaia(c['p25']), e(ANNUARIO[0])),
        ('Residenti al 31 dicembre 2024', migliaia(c['p24']) if c.get('p24') else 'dato non disponibile', e(ANNUARIO[0])),
        ('Variazione in un anno', (('+' if var > 0 else '−' if var < 0 else '') + decimale(abs(var)) + '%') if var is not None else 'dato non disponibile', e(ANNUARIO[0])),
        ('Superficie', decimale(c['km'], 2) + ' km²' if c.get('km') else 'dato non disponibile', e(ANNUARIO[0])),
        ('Densità (abitanti per km²)', decimale(c['p25'] / c['km']) if c.get('km') else 'dato non disponibile', 'calcolata da residenti e superficie'),
        ('Sindaco in anagrafe', sindaco, link_fonte(fm.get('Amministratori_locali'), 'anagrafe regionale degli amministratori locali') + (', ' + nota_sin if nota_sin else '')),
        ('Prossime elezioni comunali', str(c['el']) if c.get('el') else 'dato non disponibile', link_fonte(fm.get('Amministratori_locali'), 'anagrafe regionale degli amministratori locali')),
        ('Enti del Terzo settore iscritti al RUNTS', migliaia(c.get('ru') or 0), link_fonte(fm.get('RUNTS_FVG'), 'RUNTS (Registro unico nazionale del Terzo settore), elenco del 5 ottobre 2026')),
        ('Farmacie', migliaia(c.get('fa') or 0), link_fonte(fm.get('Farmacie'), 'portale dei dati aperti della Regione FVG')),
        ('Istituti scolastici statali con sede nel comune', migliaia(c.get('sc') or 0), link_fonte(fm.get('Scuole_2026_27'), 'Ufficio scolastico regionale, anno scolastico 2026/2027')),
        ('Residenze per anziani', migliaia(c.get('rsa') or 0), link_fonte(fm.get('Residenze_anziani'), 'portale dei dati aperti della Regione FVG')),
        ('Arrivi turistici nel 2025', migliaia(c.get('ar') or 0), link_fonte(fm.get('Turismo_comunale'), 'portale dei dati aperti della Regione FVG')),
        ('Presenze turistiche nel 2025', migliaia(c.get('pr') or 0), link_fonte(fm.get('Turismo_comunale'), 'notti nelle strutture ricettive, portale dei dati aperti della Regione FVG')),
    ]
    tab = ''.join(f'<tr><th scope="row">{e(a)}<div class="fonte" style="font-weight:400">Fonte: {f}</div></th><td class="n">{b}</td></tr>' for a, b, f in righe)
    vs = '&amp;confronta=' + ','.join([s] + [slug(x['n']) for x in simili])
    corpo = f"""<h1>{e(c['n'])}</h1>
<p>Comune della <a href="../../provincia/{slug(pv)}/">provincia di {e(pv)}</a>{' (nome ufficiale: ' + e(c['ml']) + ')' if c.get('ml') and c['ml'] != c['n'] else ''}, con <b>{migliaia(c['p25'])} residenti</b> al 31 dicembre 2025. Codice ISTAT {e(c['id'])}.</p>
<p><a class="bott" href="../../?comune={s}">Apri la scheda completa nell'Atlante</a></p>
<h2>I dati principali</h2>
<div class="riquadro"><table><caption class="fonte" style="text-align:left;padding:8px 0">Dati di {e(c['n'])} con la loro fonte</caption><thead><tr><th scope="col">Dato e fonte</th><th scope="col" style="text-align:right">Valore</th></tr></thead><tbody>{tab}</tbody></table></div>
<p class="fonte">Lo zero indica che la fonte non riporta voci per il comune. Altri dati (età, redditi, bilanci, opere pubbliche, rischio idrogeologico, elezioni) sono nella scheda completa.</p>
<h2>Approfondisci</h2>
<p><a class="bott sec" href="../../?pagina=mappe&amp;comune={s}">{e(c['n'])} sulle mappe</a><a class="bott sec" href="../../?pagina=confronto{vs}">Confronta con comuni di taglia simile</a><a class="bott sec" href="../../?pagina=archivio&amp;comune={s}">Tutte le righe dell'archivio</a><a class="bott sec" href="../../?pagina=autobus&amp;comune={s}">Autobus e fermate</a><a class="bott sec" href="../../?pagina=ambiente&amp;comune={s}">Allerte e aria</a></p>
<h2>Comuni di taglia simile in provincia di {e(pv)}</h2>
<ul class="elenco">{''.join(f'<li><a href="../{slug(x["n"])}/">{e(x["n"])}</a>, {migliaia(x["p25"])} residenti</li>' for x in simili)}</ul>
<p class="fonte">In ordine alfabetico: {f'<a href="../{slug(prec["n"])}/">‹ {e(prec["n"])}</a>' if prec else ''}{' · ' if prec and succ else ''}{f'<a href="../{slug(succ["n"])}/">{e(succ["n"])} ›</a>' if succ else ''} · <a href="../../comuni/">tutti i 215 comuni</a></p>"""
    br = [('Atlante FVG', ''), (f'Provincia di {pv}', f'provincia/{slug(pv)}/'), (c['n'], None)]
    return s, pagina_html(f'c/{s}/', titolo, descr, br, corpo)


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


def pagina_argomento(nome, titolo, descr, testi, db, man):
    corpo = f'<h1>{e(titolo)}</h1>\n' + ''.join(f'<p>{e(t)}</p>\n' for t in testi) + f'<p><a class="bott" href="../?pagina={nome}">{e(ICONA_PAG[nome])}</a></p>\n'
    ld = None
    if nome == 'comuni':
        for pv, n in PROVINCE.items():
            cc = sorted((c for c in db['c'] if c['pv'] == pv), key=lambda c: c['n'])
            corpo += f'<h2><a href="../provincia/{slug(n)}/">Provincia di {e(n)}</a>: {len(cc)} comuni</h2>\n<ul class="elenco">' + ''.join(f'<li><a href="../c/{slug(c["n"])}/">{e(c["n"])}</a></li>' for c in cc) + '</ul>\n'
    if nome == 'metodo':
        reg = json.loads((RADICE / 'dati' / 'correzioni.json').read_text(encoding='utf-8'))
        corpo += (f'<h2>Segnalazioni e registro delle correzioni</h2>\n<p>Un dato sbagliato si segnala con «Segnala un errore» (nella scheda di ogni comune, sotto le mappe, nel confronto, nelle righe dell\'archivio) oppure scrivendo a <a href="mailto:{POSTA}">{POSTA}</a>. Ogni segnalazione si controlla sulla fonte ufficiale; un dato si corregge solo se la fonte lo conferma.</p>\n')
        if reg['voci']:
            corpo += '<div class="riquadro"><table><thead><tr><th scope="col">Data</th><th scope="col">Dato</th><th scope="col">Prima</th><th scope="col">Dopo</th><th scope="col">Fonte</th></tr></thead><tbody>' + ''.join(
                f'<tr><td>{e(data_estesa(v["data"]))}</td><td>{e(v["dato"])}</td><td>{e(v["prima"])}</td><td>{e(v["dopo"])}</td><td class="fonte">{e(v["fonte"])}</td></tr>' for v in reg['voci']) + '</tbody></table></div>\n'
        else:
            corpo += f'<p>Nessuna correzione registrata finora. Il registro è attivo dal {e(data_estesa(reg["inizio"]))}.</p>\n'
        corpo += ('<h2>Statistiche di visita e privacy</h2>\n<p>L\'Atlante conta le visite con <a href="https://www.goatcounter.com/help/privacy">GoatCounter</a>, che non usa cookie né altri sistemi di memoria nel browser e non conserva l\'indirizzo IP né identificativi di chi visita. Si contano in forma aggregata le pagine viste e l\'uso di ricerca, filtri, confronto e download, oltre agli errori di caricamento; per la ricerca solo il fatto che un comune è stato scelto, non il testo scritto. I dati stanno su server di Hetzner Online in Finlandia e in Germania e non sono ceduti a terzi. Non essendoci cookie né tracciamento delle persone, non viene chiesto il consenso.</p>\n'
                  f'<p>Chi scrive a {POSTA} comunica il proprio indirizzo di posta: serve solo a rispondere alla segnalazione.</p>\n')
    if nome == 'archivio':
        fogli = man['manifest']
        corpo += f'<h2>I {len(fogli)} fogli dell\'archivio</h2>\n<div class="riquadro"><table><thead><tr><th scope="col">Foglio</th><th scope="col">Ambito</th><th scope="col" style="text-align:right">Righe</th><th scope="col">Fonte</th></tr></thead><tbody>'
        for f in fogli:
            fonte = f['fonte'] or ''
            breve = e(fonte[:70]) + ('…' if len(fonte) > 70 else '')
            cella = f'<a href="{e(fonte)}">{breve}</a>' if fonte.startswith('http') else e(fonte[:160])
            corpo += (f'<tr><th scope="row">{e(f["id"].replace("_", " "))}</th><td>{e(f["ambito"])}</td><td class="n">{migliaia(f["righe"])}</td>'
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
    for k, c in enumerate(comuni):
        stessi = [x for x in db['c'] if x['pv'] == c['pv'] and x['id'] != c['id']]
        simili = sorted(stessi, key=lambda x: abs(x['p25'] - c['p25']))[:3]
        s, h = pagina_comune(c, db, fm, simili, comuni[k - 1] if k else None, comuni[k + 1] if k + 1 < len(comuni) else None)
        (RADICE / 'c' / s).mkdir(parents=True)
        (RADICE / 'c' / s / 'index.html').write_text(h, encoding='utf-8')
    for pv, n in PROVINCE.items():
        d = RADICE / 'provincia' / slug(n); d.mkdir(parents=True)
        (d / 'index.html').write_text(pagina_provincia(pv, [c for c in db['c'] if c['pv'] == pv]), encoding='utf-8')
    for nome, titolo, descr, testi in PAGINE:
        (RADICE / nome).mkdir(exist_ok=True)
        (RADICE / nome / 'index.html').write_text(pagina_argomento(nome, titolo, descr, testi, db, man), encoding='utf-8')
    # data dell'ultimo aggiornamento dei dati, non del giorno in cui gira lo script: così la sitemap cambia solo con i dati
    oggi = max((f['cons'] for f in man['manifest'] if re.match(r'^\d{4}-\d{2}-\d{2}$', f.get('cons') or '')), default=datetime.date.today().isoformat())
    voci = [f'  <url><loc>{SITO}/</loc><lastmod>{oggi}</lastmod></url>']
    voci += [f'  <url><loc>{SITO}/{nome}/</loc><lastmod>{oggi}</lastmod></url>' for nome, *_ in PAGINE]
    voci += [f'  <url><loc>{SITO}/provincia/{slug(n)}/</loc><lastmod>{oggi}</lastmod></url>' for n in PROVINCE.values()]
    voci += [f'  <url><loc>{SITO}/c/{slug(c["n"])}/</loc><lastmod>{oggi}</lastmod></url>' for c in comuni]
    (RADICE / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                         + '\n'.join(voci) + '\n</urlset>\n', encoding='utf-8')
    (RADICE / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITO}/sitemap.xml\n', encoding='utf-8')
    print(f'Pagine: {len(comuni)} comuni, {len(PROVINCE)} province, {len(PAGINE)} argomenti; sitemap con {len(voci)} indirizzi')


if __name__ == '__main__':
    main()
