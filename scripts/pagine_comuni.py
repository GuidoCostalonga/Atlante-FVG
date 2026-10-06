#!/usr/bin/env python3
"""Crea una piccola pagina per ogni comune in c/<nome>/index.html, più sitemap.xml e robots.txt.

Ogni pagina porta il titolo e la descrizione del comune per l'anteprima nelle condivisioni
(WhatsApp, Facebook e simili leggono queste intestazioni senza eseguire il programma della pagina)
e poi rimanda subito all'Atlante con il comune già scelto: https://atlantefvg.it/?comune=<nome>.

I dati vengono dalla riga `const DB = ...;` di index.html. Usa solo la libreria standard di Python.
"""
import html, json, re, shutil, unicodedata
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
SITO = 'https://atlantefvg.it'
PROVINCE = {'UD': 'Udine', 'PN': 'Pordenone', 'GO': 'Gorizia', 'TS': 'Trieste'}
# pagine dell'Atlante con un indirizzo breve (atlantefvg.it/mappe/ apre ?pagina=mappe); devono coincidere con PAGINE in index.html
PAGINE = [('mappe', 'Mappe', 'Oltre trenta indicatori comune per comune, le cartine dell\'Annuario e i servizi sul territorio.'),
          ('confronto', 'Confronto fra comuni', 'Quattro comuni fianco a fianco, indicatore per indicatore.'),
          ('autobus', 'Autobus', 'Linee, fermate e arrivi in tempo reale degli autobus del Friuli Venezia Giulia, con la mappa delle vie.'),
          ('ambiente', 'Allerte meteo e qualità dell\'aria', 'Allerta meteo di oggi e di domani e qualità dell\'aria delle centraline del Friuli Venezia Giulia.'),
          ('comuni', 'I 215 comuni', 'Il registro dei 215 comuni: residenti, sindaci, servizi, elezioni.'),
          ('archivio', 'Archivio dati', 'Tutti i fogli del database dei comuni del Friuli Venezia Giulia, filtrabili per comune.')]


def slug(nome):
    s = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def migliaia(n):
    return f'{int(n):,}'.replace(',', '.')


def rimando(percorso, titolo, descr, dest, testo):
    e = html.escape
    return f"""<!doctype html>
<html lang="it">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titolo)}</title>
<meta name="description" content="{e(descr)}">
<link rel="canonical" href="{SITO}/{percorso}/">
<link rel="icon" href="../favicon.ico" sizes="any">
<meta property="og:type" content="website">
<meta property="og:locale" content="it_IT">
<meta property="og:site_name" content="Atlante FVG">
<meta property="og:url" content="{SITO}/{percorso}/">
<meta property="og:title" content="{e(titolo)}">
<meta property="og:description" content="{e(descr)}">
<meta property="og:image" content="{SITO}/anteprima.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script>location.replace({json.dumps(dest)});</script>
<body style="font-family:system-ui,sans-serif;background:#FAF9F6;color:#0B3359;padding:24px">
<p>{e(testo)}… Se non succede nulla, <a href="{e(dest)}">continua qui</a>.</p>
</body>
</html>
"""


def pagina(c):
    s = slug(c['n'])
    titolo = f"{c['n']} · Atlante FVG"
    descr = (f"{c['n']}, provincia di {PROVINCE.get(c['pv'], c['pv'])}: {migliaia(c['p25'])} residenti al 31 dicembre 2025. "
             'Amministratori, servizi, bilanci, elezioni, mappe e autobus del comune.') if c.get('p25') else \
            f"{c['n']}: amministratori, servizi, bilanci, elezioni, mappe e autobus del comune."
    dest = f'../../?comune={s}'
    e = html.escape
    return s, f"""<!doctype html>
<html lang="it">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titolo)}</title>
<meta name="description" content="{e(descr)}">
<link rel="canonical" href="{SITO}/c/{s}/">
<link rel="icon" href="../../favicon.ico" sizes="any">
<meta property="og:type" content="website">
<meta property="og:locale" content="it_IT">
<meta property="og:site_name" content="Atlante FVG">
<meta property="og:url" content="{SITO}/c/{s}/">
<meta property="og:title" content="{e(titolo)}">
<meta property="og:description" content="{e(descr)}">
<meta property="og:image" content="{SITO}/anteprima.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script>location.replace({json.dumps(dest)});</script>
<body style="font-family:system-ui,sans-serif;background:#FAF9F6;color:#0B3359;padding:24px">
<p>Apertura della scheda di {e(c['n'])}… Se non succede nulla, <a href="{e(dest)}">continua qui</a>.</p>
</body>
</html>
"""


def main():
    testo = (RADICE / 'index.html').read_text(encoding='utf-8')
    db = json.loads(re.search(r'^const DB = (.*);$', testo, re.M).group(1))
    cartella = RADICE / 'c'
    if cartella.exists():
        shutil.rmtree(cartella)
    pagine = []
    for c in db['c']:
        s, h = pagina(c)
        (cartella / s).mkdir(parents=True)
        (cartella / s / 'index.html').write_text(h, encoding='utf-8')
        pagine.append(s)
    if len(set(pagine)) != len(pagine):
        raise SystemExit('Due comuni hanno lo stesso indirizzo: controllare la funzione slug')
    for nome, titolo, descr in PAGINE:
        (RADICE / nome).mkdir(exist_ok=True)
        (RADICE / nome / 'index.html').write_text(rimando(nome, f'{titolo} · Atlante FVG', descr, f'../?pagina={nome}', f'Apertura della pagina {titolo}'), encoding='utf-8')
    voci = [f'  <url><loc>{SITO}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>']
    voci += [f'  <url><loc>{SITO}/{nome}/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>' for nome, _, _ in PAGINE]
    voci += [f'  <url><loc>{SITO}/c/{s}/</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>' for s in sorted(pagine)]
    (RADICE / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                         + '\n'.join(voci) + '\n</urlset>\n', encoding='utf-8')
    (RADICE / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITO}/sitemap.xml\n', encoding='utf-8')
    print(f'Pagine dei comuni: {len(pagine)}')


if __name__ == '__main__':
    main()
