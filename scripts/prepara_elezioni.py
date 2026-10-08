#!/usr/bin/env python3
"""Prepara la sezione riservata «Elezioni regionali e comunali».

Prende il cruscotto autonomo (un solo file HTML con stile, dati e codice) e lo trasforma in un frammento
che vive dentro la pagina elezioni/index.html dell'Atlante: lo stile viene confinato sotto #elezioni e
riportato ai colori e ai caratteri dell'Atlante, le classi che si scontrano con pagine.css sono rinominate,
i riferimenti al documento (body, intestazione, tema scuro) sono tolti. Il frammento va poi cifrato con
scripts/cifra_pagina.js: il file sorgente non va mai pubblicato.

Uso:  python3 -I scripts/prepara_elezioni.py <sorgente.html> <frammento.html>
"""
import re, sys

sorgente, uscita = sys.argv[1], sys.argv[2]
s = open(sorgente, encoding='utf-8').read()
stile = re.search(r'<style>(.*?)</style>', s, re.S).group(1)
corpo = re.search(r'<body[^>]*>(.*)</body>', s, re.S).group(1)
script = re.findall(r'<script[^>]*>(.*?)</script>', corpo, re.S)
corpo = re.sub(r'<script.*?</script>', '', corpo, flags=re.S)

# ---------------------------------------------------------------- HTML
# via l'intestazione propria, il collegamento «salta», il tema scuro e lo scarico della pagina
corpo = re.sub(r'<a class="salta".*?</a>', '', corpo, flags=re.S)
corpo = re.sub(r'<header class="testata">.*?</header>', '<div class="intro-el"><h1>Elezioni regionali <span>Friuli Venezia Giulia 2023</span></h1>\n<p>Il voto del 2 e 3 aprile 2023 in tutti i 215 comuni: presidenti, liste, preferenze ai 560 candidati e affluenza. Scegli una circoscrizione o un comune, oppure tocca la mappa: tutti i grafici e le tabelle si aggiornano.</p></div>', corpo, flags=re.S)
corpo = corpo.replace('<main id="contenuto" tabindex="-1">', '<div class="corpo-el">').replace('</main>', '</div>')
corpo = corpo.replace('<footer>', '<section class="fonti-el riquadro" aria-label="Fonti e note"><h2>Fonti e note</h2>').replace('</footer>', '</section>')
corpo = corpo.replace('class="campo campo-vista"', 'class="campo-el campo-vista"').replace('class="campo campo-cerca"', 'class="campo-el campo-cerca"').replace('class="campo"', 'class="campo-el"')
corpo = corpo.replace('class="nota"', 'class="nota-el"')
corpo = corpo.replace(' autocomplete="off"', ' autocomplete="off"')
assert 'class="campo"' not in corpo and '<footer' not in corpo

# ---------------------------------------------------------------- CSS: confinato sotto #elezioni, colori e caratteri dell'Atlante
def regole(css):
    """Spezza un blocco CSS in (selettore, corpo) rispettando le graffe annidate."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find('{', i)
        if j < 0: break
        sel = css[i:j].strip(); k, liv = j, 0
        while k < n:
            if css[k] == '{': liv += 1
            elif css[k] == '}':
                liv -= 1
                if liv == 0: break
            k += 1
        out.append((sel, css[j + 1:k])); i = k + 1
    return out

SCARTA = ('*,*::before,*::after', 'html', 'body::after', '.salta', '.salta:focus', ':where(a,button,select,input,[tabindex]):focus-visible', '.tema', '.tema:hover', '.tema:active')
def prefissa(sel):
    sel = sel.strip()
    if sel.startswith('@keyframes') or sel == ':root': return sel
    parti = []
    for p in sel.split(','):
        p = p.strip()
        if not p: continue
        if p in SCARTA or p.startswith('header.testata') or p.startswith('.testata') or p.startswith(':root'): continue
        p = re.sub(r'^body(?=[\[\s:]|$)', '#elezioni', p)
        p = re.sub(r'^main(?=[\s{]|$)', '#elezioni .corpo-el', p)
        p = re.sub(r'^footer(?=[\s{]|$)', '#elezioni .fonti-el', p)
        if not p.startswith('#elezioni'): p = '#elezioni ' + p
        parti.append(p)
    return ', '.join(parti)

def trasforma(css, dentro_media=False):
    out = []
    for sel, corpo_r in regole(css):
        if sel.startswith('@media'):
            if 'prefers-color-scheme' in sel: continue  # niente tema scuro: l'Atlante è chiaro
            out.append(sel + '{' + trasforma(corpo_r, True) + '}')
            continue
        if sel.startswith('@keyframes'):
            out.append(sel + '{' + corpo_r + '}'); continue
        if sel.startswith(':root'):
            if '[data-theme' in sel or dentro_media: continue
            out.append(':root{' + corpo_r + '}'); continue
        ns = prefissa(sel)
        if ns: out.append(ns + '{' + corpo_r + '}')
    return '\n'.join(out)

stile = stile.replace('.campo', '.campo-el').replace('.nota{', '.nota-el{').replace('.nota ', '.nota-el ')
stile = stile.replace("'Geist',-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,Helvetica,Arial,sans-serif", 'var(--sans)')
stile = stile.replace("'Fraunces',Georgia,'Times New Roman',serif", 'var(--serif)').replace("'Fraunces',Georgia,serif", 'var(--serif)')
css = trasforma(stile)
# le variabili di base le dà pagine.css (--testo, --blu, --oro…); qui restano solo quelle proprie del cruscotto, con i toni dell'Atlante
css = re.sub(r':root\{[^}]*--z-barra:[^}]*\}', '', css)  # il secondo blocco di variabili è compreso in quello nuovo
css = re.sub(r':root\{[^}]*--sfondo:[^}]*\}', ':root{--sfondo:var(--avorio);--superficie:#ffffff;--superficie-2:#F4F1EA;--superficie-3:#ECE6D8;--bordo:var(--linea);--bordo-forte:#CFC7B5;--accento:var(--blu-chiaro);--griglia:#ECE9E2;--assente:#E6E0D4;--om-1:0 1px 2px rgba(11,51,89,.05),0 2px 6px -2px rgba(11,51,89,.06);--om-2:0 2px 4px rgba(11,51,89,.06),0 18px 36px -14px rgba(11,51,89,.22);--r:14px;--r-sm:10px;--r-xs:6px;--t:260ms cubic-bezier(.2,.6,.3,1);--molla:cubic-bezier(.34,1.3,.5,1);--z-barra:20;--z-barra-mob:25;--z-sugg:200}', css, count=1)
assert 'Geist' not in css and 'Fraunces' not in css, 'caratteri non sostituiti'
assert '--z-barra:' in css and css.count(':root{') == 1, 'variabili di base non in un solo blocco'
css += '''
/* ===== integrazione nell'Atlante ===== */
#elezioni .contenitore{max-width:none;padding:0}
#elezioni .intro-el h1{font-size:clamp(26px,4vw,38px);margin:0}
#elezioni .intro-el h1 span{display:block;font-style:italic;font-weight:600;color:var(--blu-medio)}
#elezioni .intro-el p{margin:8px 0 14px;color:var(--testo-2);max-width:62ch}
#elezioni .filtri{top:56px;border-radius:12px;padding:0 12px;margin:0 -4px}
#elezioni .barra-mob{top:56px}
@media (min-width:1024px){#elezioni .filtri{top:64px}}
#elezioni .corpo-el{padding:18px 0 10px}
#elezioni .card h2,#elezioni .fonti-el h2{color:var(--blu)}
#elezioni .fonti-el{margin-top:18px}
#elezioni .fonti-el h2{font-size:20px;margin-bottom:8px}
#elezioni .fonti-el p{font-size:13.5px;color:var(--testo-2)}
#elezioni .bot.pieno,#elezioni .lenti button[aria-pressed="true"],#elezioni .vista button[aria-pressed="true"],#elezioni .indice a.attivo{background:var(--blu);border-color:var(--blu);color:#fff}
#elezioni .kpi .k:nth-child(3)::before{background:var(--oro)}
#elezioni .ancora{scroll-margin-top:150px}
'''

# ---------------------------------------------------------------- JS: riferimenti al documento
app = script[-1]
def sost(a, b, n=1):
    global app
    assert app.count(a) == n, (app.count(a), a[:60]); app = app.replace(a, b)
sost('document.body.dataset.vista=v;', "document.getElementById('elezioni').dataset.vista=v;")
sost('d3.select(".testata h1").html(t.h); d3.select(".testata p").text(t.p);', 'd3.select("#elezioni .intro-el h1").html(t.h); d3.select("#elezioni .intro-el p").text(t.p);')
sost('try{ const t=localStorage.getItem("tema-reg23"); if(t) document.documentElement.dataset.theme=t; }catch(e){}', '')
sost('document.querySelector(".filtri").offsetTop-4', 'document.querySelector("#elezioni .filtri").offsetTop-70')
app = app.replace('class="campo"', 'class="campo-el"').replace('class="nota"', 'class="nota-el"')
assert 'class="campo"' not in app and 'class="nota"' not in app
script[-1] = app

frammento = '<style>\n' + css + '\n</style>\n' + corpo.strip() + '\n' + ''.join(f'<script>{x}</script>\n' for x in script)
open(uscita, 'w', encoding='utf-8').write(frammento)
print(f'frammento: {len(frammento):,} caratteri · stile {len(css):,} · corpo {len(corpo):,} · script {[len(x) for x in script]}')
