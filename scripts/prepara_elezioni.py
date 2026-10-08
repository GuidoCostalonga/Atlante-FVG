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
# lente «Preferenze di un candidato»: campo di ricerca per nome accanto al selettore
corpo = corpo.replace('<div class="campo-el" id="lenteCand" hidden><label for="selCand">Candidato consigliere</label><select id="selCand"></select></div>',
    '<div class="campo-el" id="lenteCand" hidden><label for="listaCand">Candidato consigliere: scegli la lista, cerca per nome o scegli dall\'elenco</label><div class="conf-sel"><select id="listaCand" aria-label="Lista del candidato"></select><input id="cercaCand" placeholder="Cognome o nome" autocomplete="off" aria-label="Cerca un candidato per nome"><select id="selCand" aria-label="Candidato consigliere"></select></div></div>')
assert 'id="cercaCand"' in corpo
# nuova sezione: le preferenze dei candidati di una lista, comune per comune, con i totali
SEZ_PREF = '''    <!-- PREFERENZE DI UNA LISTA PER COMUNE -->
    <section class="card solo-reg s12 ancora" id="sez-prefliste">
      <h2>Le preferenze di una lista, comune per comune</h2>
      <p class="sotto" id="plSotto">Scegli la circoscrizione e la lista: per ogni comune i voti alla lista e le preferenze a ciascun candidato, con i totali di riga e di colonna.</p>
      <div class="strumenti">
        <div class="campo-el"><label for="plCirc">Circoscrizione</label><select id="plCirc"></select></div>
        <div class="campo-el"><label for="plLista">Lista</label><select id="plLista"></select></div>
        <button class="bot" type="button" id="plCsv">Scarica in CSV</button>
      </div>
      <div class="tab-box" style="max-height:640px"><table class="matrice" id="tabPrefListe"></table></div>
      <p class="nota-el" id="plNota"></p>
    </section>

'''
corpo = corpo.replace('    <!-- COMUNALI -->', SEZ_PREF + '    <!-- COMUNALI -->')
corpo = corpo.replace('<a class="solo-reg" href="#sez-comuni">Comuni</a>', '<a class="solo-reg" href="#sez-comuni">Comuni</a><a class="solo-reg" href="#sez-prefliste">Preferenze per comune</a>')
assert 'id="sez-prefliste"' in corpo and '#sez-prefliste' in corpo
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
#elezioni #cercaCand{min-width:180px}
#elezioni #listaCand{min-width:150px}
#elezioni #tabPrefListe th{white-space:normal;min-width:118px;vertical-align:bottom;line-height:1.25}
#elezioni #tabPrefListe th:first-child,#elezioni #tabPrefListe td.nome{min-width:160px}
#elezioni #tabPrefListe td.cel{text-align:right;font-variant-numeric:tabular-nums}
#elezioni #tabPrefListe tr.totale td{font-weight:800;background:var(--superficie-2);position:sticky;bottom:0;z-index:1}
#elezioni #tabPrefListe tr.totale td:first-child{z-index:2}
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
# stato aggiuntivo: circoscrizione e lista della tabella delle preferenze, ricerca del candidato
sost('comPrec:null };', 'comPrec:null, plCirc:null, plLista:null, candCerca:"", candLista:"" };')
# ricerca del candidato nella lente della mappa
sost('''  const ks=K.filter(k=>!S.circ||k.ci===S.circ);
  const gruppi=d3.groups(ks,k=>k.l)''', '''  // filtro per lista: le liste presenti nel territorio scelto, in ordine di voti
  const listeQui=L.map((l,i)=>i).filter(i=>K.some(k=>k.l===i && (!S.circ||k.ci===S.circ))).sort((a,b)=>L[b].v-L[a].v);
  if (S.candLista!=="" && !listeQui.includes(+S.candLista)) S.candLista="";
  const sl=d3.select("#listaCand"); sl.selectAll("option").data([["","Tutte le liste"],...listeQui.map(i=>[String(i),L[i].s])],d=>d[0]).join("option").attr("value",d=>d[0]).text(d=>d[1]); sl.property("value",S.candLista);
  const ks=candFiltrati();
  s.selectAll(":scope > option").remove();
  if (!ks.length){ s.selectAll("optgroup").remove(); s.append("option").attr("value","").text("Nessun candidato con questi filtri: cambia lista o ricerca"); return; }
  const gruppi=d3.groups(ks,k=>k.l)''')
sost('''d3.select("#selCand").on("change",function(){S.cand=+this.value;disegnaMappa();});''',
     '''d3.select("#selCand").on("change",function(){S.cand=+this.value;disegnaMappa();});
const normCand = s => String(s).toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"");
const candFiltrati = () => K.filter(k=>(!S.circ||k.ci===S.circ) && (S.candLista==="" || k.l===+S.candLista) && (!S.candCerca || normCand(k.n).includes(S.candCerca)));
const scegliPrimoCand = () => { const ks=candFiltrati(); if (ks.length && !ks.find(k=>k.id===S.cand)) S.cand=ks.slice().sort((a,b)=>b.v-a.v)[0].id; };
d3.select("#cercaCand").on("input",function(){ S.candCerca=normCand(this.value.trim()); scegliPrimoCand(); disegnaMappa(); });
d3.select("#listaCand").on("change",function(){ S.candLista=this.value; scegliPrimoCand(); disegnaMappa(); });''')
sost('''  S.lista=fdi; S.tLista=fdi; S.pres=0; S.cand=null;''', '''  S.lista=fdi; S.tLista=fdi; S.pres=0; S.cand=null; S.plLista=null; S.candCerca=""; S.candLista=""; d3.select("#cercaCand").property("value","");''')
sost('''disegnaMatrice(); disegnaComuni(); disegnaStoria();
}''', '''disegnaMatrice(); disegnaComuni(); disegnaPrefListe(); disegnaStoria();
}''')
sost('''// ---------- aggiornamento generale
function aggiorna(spostaMappa){''', open(__file__.replace('prepara_elezioni.py', 'prefliste.js'), encoding='utf-8').read() + '''
// ---------- aggiornamento generale
function aggiorna(spostaMappa){''')
script[-1] = app

frammento = '<style>\n' + css + '\n</style>\n' + corpo.strip() + '\n' + ''.join(f'<script>{x}</script>\n' for x in script)
open(uscita, 'w', encoding='utf-8').write(frammento)
print(f'frammento: {len(frammento):,} caratteri · stile {len(css):,} · corpo {len(corpo):,} · script {[len(x) for x in script]}')
