#!/usr/bin/env python3
"""Porta nell'Atlante l'applicazione Catasto Map (repository GuidoCostalonga/catasto-map, su costalonga.org/catasto-map/).

Copia in catasto/ la parte che gira nel browser (pagina, stile, programmi, OpenLayers, elenco dei comuni, icone,
manifest e service worker; non il server Node) e la adatta all'Atlante: marchio e collegamento di ritorno
all'Atlante, colori blu, oro e avorio, caratteri dell'Atlante, titolo e anteprime di atlantefvg.it.
Le funzioni restano quelle dell'originale. La cartografia passa dallo stesso proxy (Cloudflare Worker
catasto-map-proxy), che deve accettare l'origine https://atlantefvg.it.

Uso: python scripts/porta_catasto.py <cartella del repository catasto-map>
"""
import json, re, shutil, sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
DEST = RADICE / 'catasto'
COPIA = ['index.html', 'manifest.json', 'service-worker.js', 'LICENSE', 'css', 'js', 'vendor', 'data', 'icons']


def sostituisci(t, vecchio, nuovo, regex=False):
    n = len(re.findall(vecchio, t, re.S)) if regex else t.count(vecchio)
    if n != 1:
        raise SystemExit(f'Atteso un solo punto da cambiare, trovati {n}: {vecchio[:70]!r}')
    return re.sub(vecchio, lambda m: nuovo, t, count=1, flags=re.S) if regex else t.replace(vecchio, nuovo)


STILE = """

/* ===== Grafica dell'Atlante FVG ===== */
:root {
  --blu: #0B3359; --blu-scuro: #07213A; --blu-chiaro: #F0F6FB;
  --arancio: #D8973C; --arancio-chiaro: #FEF8E3;
  --grigio-100: #F7F4EC; --grigio-200: #E4DDCD; --grigio-300: #CFC7B5;
  --font: "Plus Jakarta Sans", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
}
body { background: #F7F4EC; }
.topbar { background: rgba(247,244,236,.97); border-bottom: 1px solid #E4DDCD; }
.btn-accent { background: #D8973C; border-color: #D8973C; color: #07213A; }
.btn-accent:hover { background: #B67524; border-color: #B67524; color: #fff; }
.btn-accent[aria-pressed="true"] { background: #0B3359; border-color: #0B3359; color: #fff; box-shadow: 0 0 0 4px rgba(216,151,60,.35); }
.atl-marchio { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; min-height: 44px; }
.atl-marchio img { height: 34px; width: auto; display: block; }
.atl-marchio .atl-nome { font-family: "Source Serif 4", Georgia, serif; font-weight: 700; font-size: 18px; color: #0B3359; white-space: nowrap; }
.panel-header h2, .modal-header h2 { font-family: "Source Serif 4", Georgia, serif; letter-spacing: 0; text-transform: none; font-size: 17px; }
.section-title { color: #52565E; }
:focus-visible { outline: 3px solid #0B3359 !important; outline-offset: 2px; box-shadow: 0 0 0 5px #F7D678 !important; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@media (max-width: 760px) { .atl-marchio .atl-nome { display: none; } .atl-marchio img { height: 30px; } }
"""


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = Path(sys.argv[1])
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir()
    for n in COPIA:
        (shutil.copytree if (src / n).is_dir() else shutil.copy2)(src / n, DEST / n)
    # pagina
    p = DEST / 'index.html'; t = p.read_text(encoding='utf-8')
    t = sostituisci(t, '<title>CATASTO MAP</title>', """<title>Catasto: foglio e particella sulla mappa · Atlante FVG</title>
  <link rel="canonical" href="https://atlantefvg.it/catasto/">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="it_IT">
  <meta property="og:site_name" content="Atlante FVG">
  <meta property="og:url" content="https://atlantefvg.it/catasto/">
  <meta property="og:title" content="Catasto: foglio e particella sulla mappa · Atlante FVG">
  <meta property="og:description" content="Trova su mappa un terreno o un fabbricato e leggi foglio e particella catastale, con la cartografia ufficiale dell'Agenzia delle Entrate.">
  <meta property="og:image" content="https://atlantefvg.it/anteprima.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <script data-goatcounter="https://guidocostalonga.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap">""")
    t = sostituisci(t, r'<meta name="description" content="[^"]*">', '<meta name="description" content="Catasto dell\'Atlante FVG: trova su mappa un terreno o un fabbricato e leggi foglio e particella catastale, con la cartografia ufficiale dell\'Agenzia delle Entrate (CC BY 4.0).">', regex=True)
    t = t.replace('<meta name="theme-color" content="#0f4c81">', '<meta name="theme-color" content="#0B3359">').replace('content="Catasto Map"', 'content="Catasto FVG"')
    t = sostituisci(t, r'<div class="brand" title="CATASTO MAP">.*?</div>', """<div class="brand" title="Catasto · Atlante FVG">
      <a class="atl-marchio" href="../" aria-label="Atlante FVG, pagina iniziale"><img src="../logo.webp" alt="Atlante FVG" width="96" height="34"><span class="atl-nome">Catasto</span></a>
      <span class="brand-badge" id="mode-badge" title="Profilo corrente">PUBBLICO</span>
    </div>""", regex=True)
    t = sostituisci(t, '<a id="tasto-home" class="icon-btn" href="/" title="Torna alla home di costalonga.org" aria-label="Home" hidden>⌂</a>',
                    '<a id="tasto-home" class="icon-btn" href="../" title="Torna all\'Atlante FVG" aria-label="Torna all\'Atlante FVG" hidden>⌂</a>')
    t = sostituisci(t, '<div id="app" class="app right-closed" data-mode="navigate">', '<h1 class="sr-only">Catasto: foglio e particella sulla mappa</h1>\n<div id="app" class="app right-closed" data-mode="navigate">')
    p.write_text(t, encoding='utf-8')
    # vista iniziale sul Friuli Venezia Giulia invece che sull'Italia intera
    cf = DEST / 'js' / 'config.js'
    cf.write_text(sostituisci(cf.read_text(encoding='utf-8'), 'DEFAULT_VIEW: { lon: 12.55, lat: 42.6, zoom: 6 },', 'DEFAULT_VIEW: { lon: 13.05, lat: 46.12, zoom: 8.6 },'), encoding='utf-8')
    # stile
    c = DEST / 'css' / 'style.css'; c.write_text(c.read_text(encoding='utf-8') + STILE, encoding='utf-8')
    # nome dell'applicazione installabile e cache separata da quella di costalonga.org
    m = DEST / 'manifest.json'; man = json.loads(m.read_text(encoding='utf-8'))
    man.update({'name': 'Catasto · Atlante FVG', 'short_name': 'Catasto FVG', 'theme_color': '#0B3359', 'background_color': '#F7F4EC'})
    m.write_text(json.dumps(man, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sw = DEST / 'service-worker.js'; s = sw.read_text(encoding='utf-8')
    s, n = re.subn(r"const CACHE_VERSION = 'catasto-map-v([^']+)';", r"const CACHE_VERSION = 'catasto-atlante-v\1';", s, count=1)
    if n != 1:
        raise SystemExit('Versione della cache non trovata nel service worker')
    sw.write_text(s, encoding='utf-8')
    print(f'Catasto: copiato in {DEST} ({sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file()) // 1024} KB)')


if __name__ == '__main__':
    main()
