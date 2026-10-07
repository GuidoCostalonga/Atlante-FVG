#!/usr/bin/env python3
"""Porta nell'Atlante la pagina Meteo FVG (repository GuidoCostalonga/meteo, pubblicata su costalonga.org/meteo/).

Prende index.html della pagina originale e scrive meteo/index.html con la grafica dell'Atlante:
intestazione e piè di pagina dell'Atlante al posto di quelli di costalonga.org, colori blu, oro e avorio,
titoli in Source Serif 4 e testi in Plus Jakarta Sans, indirizzi e anteprime di atlantefvg.it,
collegamenti per segnalare un errore. Contenuto, dati e funzioni restano quelli dell'originale.

Uso: python scripts/porta_meteo.py <percorso di index.html della pagina Meteo FVG>
"""
import re, sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def sostituisci(t, vecchio, nuovo, regex=False):
    n = len(re.findall(vecchio, t, re.S)) if regex else t.count(vecchio)
    if n != 1:
        raise SystemExit(f'Atteso un solo punto da cambiare, trovati {n}: {vecchio[:70]!r}')
    return re.sub(vecchio, lambda m: nuovo, t, count=1, flags=re.S) if regex else t.replace(vecchio, nuovo)


TESTATA = """<header class="atl-testata"><div class="atl-dentro">
  <a class="atl-marchio" href="../" aria-label="Atlante FVG, pagina iniziale"><img src="../logo.webp" alt="Atlante FVG" width="113" height="40"></a>
  <nav class="atl-voci" aria-label="Pagine dell'Atlante">
    <a href="../">Inizio</a><a href="../?pagina=mappe">Mappe</a><a href="../?pagina=comuni">Comuni</a><a href="../?pagina=autobus">Autobus</a><a href="../orari/">Orari</a><a href="../meteo/" aria-current="page">Meteo</a><a href="../stradario/">Stradario</a><a href="../catasto/">Catasto</a><a href="../?pagina=metodo">Metodo</a>
  </nav>
  <details class="atl-menu"><summary>Menu</summary><nav aria-label="Pagine dell'Atlante">
    <a href="../">Inizio</a><a href="../?pagina=mappe">Mappe</a><a href="../?pagina=comuni">Comuni</a><a href="../?pagina=ambiente">Allerte e qualità dell'aria</a><a href="../?pagina=autobus">Autobus in tempo reale</a><a href="../orari/">Orari degli autobus</a><a href="../meteo/" aria-current="page">Meteo</a><a href="../stradario/">Stradario</a><a href="../catasto/">Catasto</a><a href="../?pagina=metodo">Metodo e fonti</a>
  </nav></details>
</div></header>"""

PIEDE = """<footer class="atl-piede"><div class="atl-piede-dentro">
  <div><strong>Atlante FVG</strong><br>I comuni del Friuli Venezia Giulia, con fonte e data di ogni dato.</div>
  <div><a href="../">Pagina iniziale</a> · <a href="../?pagina=ambiente">Allerte e qualità dell'aria</a> · <a href="../orari/">Orari degli autobus</a> · <a href="../?pagina=metodo">Metodo e fonti</a></div>
  <p class="atl-fonti">FONTI</p>
  <p class="atl-fonti">Hai trovato un errore? <a href="mailto:info@atlantefvg.it?subject=Segnalazione%20di%20errore%3A%20meteo">Segnalalo per posta</a> oppure <a href="https://wa.me/393283692227?text=Segnalazione%20di%20errore%20sull%27Atlante%20FVG%3A%20pagina%20Meteo" target="_blank" rel="noopener">via WhatsApp</a>.</p>
</div></footer>"""

STILE = """
/* ===== Grafica dell'Atlante FVG ===== */
:root{--blu:#0B3359;--blu-fondo:#07213A;--blu-chiaro:#155E9E;--blu2:#155E9E;--blu-tenue:#F0F6FB;--giallo:#F7D678;--giallo-scuro:#D8973C;
  --fondo:#F7F4EC;--grigio:#F7F4EC;--superficie-2:#F4F1EA;--bordo:#E4DDCD;--bordo-forte:#CFC7B5;--anello:#0B3359}
body{font-family:"Plus Jakarta Sans",system-ui,"Segoe UI",sans-serif}
h1,h2,h3,h4,.titolo,.titolo-pagina{font-family:"Source Serif 4",Georgia,serif;letter-spacing:-.005em}
.atl-testata{position:sticky;top:0;z-index:70;background:rgba(247,244,236,.96);backdrop-filter:blur(6px);border-bottom:1px solid #E4DDCD}
.atl-dentro{max-width:1180px;margin:0 auto;padding:0 16px;min-height:56px;display:flex;align-items:center;gap:12px}
.atl-marchio img{height:36px;width:auto;display:block;border:0;border-radius:0}
.atl-voci{display:none;gap:2px;margin-left:8px}
.atl-voci a{min-height:40px;display:inline-flex;align-items:center;padding:0 10px;border-radius:8px;color:#22303F;font-weight:600;font-size:14px;text-decoration:none;white-space:nowrap}
.atl-voci a:hover{background:#ECE6D8}
.atl-voci a[aria-current="page"]{background:#0B3359;color:#fff}
.atl-menu{margin-left:auto;position:relative}
.atl-menu>summary{list-style:none;cursor:pointer;min-height:44px;display:inline-flex;align-items:center;padding:0 12px;border-radius:10px;font-weight:600;color:#0B3359;border:1px solid #CBD8E6;background:#fff}
.atl-menu>summary::-webkit-details-marker{display:none}
.atl-menu nav{position:absolute;right:0;top:calc(100% + 6px);width:min(18rem,calc(100vw - 32px));background:#fff;border:1px solid #E4DDCD;border-radius:12px;box-shadow:0 8px 24px rgba(11,51,89,.14);padding:6px;display:flex;flex-direction:column}
.atl-menu nav a{min-height:48px;display:flex;align-items:center;padding:0 12px;border-radius:8px;color:#1F2329;text-decoration:none;font-weight:600}
.atl-menu nav a[aria-current="page"]{background:#0B3359;color:#fff}
@media (min-width:1024px){.atl-voci{display:flex}.atl-menu{display:none}.atl-marchio img{height:40px}.atl-dentro{min-height:64px}}
.barra-pagina{top:56px}
@media (min-width:1024px){.barra-pagina{top:64px}}
.atl-piede{background:#202226;color:#D4CBBF;margin-top:32px}
.atl-piede-dentro{max-width:1180px;margin:0 auto;padding:24px 16px;display:flex;flex-wrap:wrap;gap:12px 24px;justify-content:space-between;font-size:14px}
.atl-piede a{color:#F7D678}
.atl-piede strong{color:#fff;font-family:"Source Serif 4",Georgia,serif;font-size:17px}
.atl-fonti{flex-basis:100%;margin:0;font-size:13px;color:#BFB8AA;line-height:1.6}
.titolo-pagina .k,.hero .k,.etichetta,.scheda .k{font-family:"Plus Jakarta Sans",system-ui,sans-serif}
"""


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    t = Path(sys.argv[1]).read_text(encoding='utf-8')
    # intestazioni della pagina: indirizzo, nome del sito, anteprima
    t = t.replace('https://costalonga.org/meteo/', 'https://atlantefvg.it/meteo/').replace('https://costalonga.org/anteprima.jpg', 'https://atlantefvg.it/anteprima.jpg')
    t = sostituisci(t, '<meta property="og:site_name" content="Guido Costalonga">', '<meta property="og:site_name" content="Atlante FVG">')
    t = sostituisci(t, r'<meta property="og:image:alt" content="[^"]*">', '<meta property="og:image:alt" content="Logo Atlante FVG con la scritta: i 215 comuni del Friuli Venezia Giulia">', regex=True)
    t = re.sub(r'\s*<meta name="twitter:site" content="[^"]*">', '', t)
    t = sostituisci(t, '<meta name="theme-color" content="#ffffff">', '<meta name="theme-color" content="#0B3359">')
    t = sostituisci(t, r'<title>[^<]*</title>', '<title>Meteo dei 215 comuni del Friuli Venezia Giulia · Atlante FVG</title>', regex=True)
    t = sostituisci(t, '<style>@font-face', """<link rel="icon" href="../favicon.ico" sizes="any">
<script data-goatcounter="https://guidocostalonga.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Atlante FVG","item":"https://atlantefvg.it/"},{"@type":"ListItem","position":2,"name":"Meteo","item":"https://atlantefvg.it/meteo/"}]}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap">
<style>@font-face""")
    # carattere incorporato dell'originale: sostituito dai caratteri dell'Atlante
    t = sostituisci(t, r"@font-face\{font-family:'Manrope';src:url\(data:font/woff2;base64,[^)]+\)[^}]*\}", '', regex=True)
    t = t.replace("font-family:'Manrope',", 'font-family:')
    i = t.index('</style>'); t = t[:i] + STILE + t[i:]
    # testata e piè di pagina dell'Atlante; le fonti dell'originale restano
    t = sostituisci(t, r'<header class="barra" id="barra">.*?</header>', TESTATA, regex=True)
    fonti = re.search(r'<div class="coda">\s*<div class="dentro">\s*<p>(.*?)</p>', t, re.S).group(1)
    t = sostituisci(t, r'<footer>.*?</footer>', PIEDE.replace('FONTI', fonti), regex=True)
    # comuni a portata di mano: i quattro capoluoghi, da ovest a est; all'apertura si parte da Udine
    t = sostituisci(t, r'<button class="city" data-c="Roveredo in Piano">Roveredo in Piano</button>\s*<button class="city" data-c="Pordenone">Pordenone</button>\s*<button class="city" data-c="Trieste">Trieste</button>',
                    '<button class="city" data-c="Pordenone">Pordenone</button>\n    <button class="city" data-c="Udine">Udine</button>\n    <button class="city" data-c="Gorizia">Gorizia</button>\n    <button class="city" data-c="Trieste">Trieste</button>', regex=True)
    t = sostituisci(t, "let active='Roveredo in Piano',", "let active='Udine',")
    # niente riferimenti rimasti alla testata originale (lo script dell'originale la cerca per l'ombra allo scorrimento)
    t = t.replace("document.getElementById('barra')", "document.querySelector('.atl-testata')")
    out = RADICE / 'meteo' / 'index.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(t, encoding='utf-8')
    print(f'Meteo: {out} scritta ({len(t) // 1024} KB)')


if __name__ == '__main__':
    main()
