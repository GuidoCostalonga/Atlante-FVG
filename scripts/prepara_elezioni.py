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
corpo = corpo.replace('<div class="strumenti">\n        <div class="campo-el"><label for="cLista">Lista</label><select id="cLista"></select></div>',
    '<div class="strumenti">\n        <div class="campo-el"><label for="cCirc">Circoscrizione</label><select id="cCirc"></select></div>\n        <div class="campo-el"><label for="cLista">Lista</label><select id="cLista"></select></div>')
assert 'id="cCirc"' in corpo
corpo = corpo.replace('<a class="solo-reg" href="#sez-comuni">Comuni</a>', '<a class="solo-reg" href="#sez-comuni">Comuni</a><a class="solo-reg" href="#sez-prefliste">Preferenze per comune</a>')
assert 'id="sez-prefliste"' in corpo and '#sez-prefliste' in corpo
# ---------------------------------------------------------------- comunali: un solo pannello di filtri
PANNELLO = '''    <section class="card s12 solo-com ancora" id="filtriCom" aria-labelledby="fcTitolo">
      <div class="card-testa"><div><h2 id="fcTitolo">Filtri delle comunali</h2>
        <p class="sotto">Valgono insieme per la mappa, gli indicatori e tutte le tabelle della vista. Il territorio si sceglie nella barra in alto.</p></div></div>
      <div class="strumenti">
        <div class="campo-el"><label for="fcEl">Elezione</label><select id="fcEl"></select></div>
        <div class="campo-el"><label for="fcPart">Partito nel nome di una lista</label><select id="fcPart"></select></div>
        <div class="campo-el"><label for="fcDim">Dimensione del comune</label><select id="fcDim"></select></div>
        <div class="campo-el"><label for="fcEsito">Esito</label><select id="fcEsito"></select></div>
        <div class="campo-el"><label for="fcCerca">Cerca nelle tabelle</label><input id="fcCerca" placeholder="Comune, sindaco o consigliere" autocomplete="off"></div>
        <button class="bot" type="button" id="fcAzzera">Azzera i filtri</button>
      </div>
      <p class="conteggio" id="fcRiepilogo" aria-live="polite"></p>
    </section>

    <section class="card s12 solo-com" id="sintesiCom"></section>'''
corpo = corpo.replace('    <section class="card s12 solo-com" id="sintesiCom"></section>', PANNELLO)
assert 'id="filtriCom"' in corpo
corpo = corpo.replace('''      <p class="sotto">Preferenze all'ultima elezione di ogni comune del territorio scelto. Tocca una riga per aprire il comune. Attenzione: i comuni hanno dimensioni molto diverse.</p>
      <div class="strumenti">
        <div class="campo-el"><label for="cpPart">Partito nel nome della lista</label><select id="cpPart"></select></div>
        <div class="campo-el"><label for="cpCerca">Cerca nome o comune</label><input id="cpCerca" placeholder="Nome, cognome o comune" autocomplete="off"></div>
        <button class="bot" type="button" id="cpCsv">Scarica in CSV</button>''', '''      <p class="sotto" id="cpSotto"></p>
      <div class="strumenti">
        <button class="bot" type="button" id="cpCsv">Scarica in CSV</button>''')
assert 'id="cpPart"' not in corpo and 'id="cpSotto"' in corpo
corpo = corpo.replace('''      <h2>Tutti i comuni, ultima elezione</h2>
      <p class="sotto">Tocca una riga per aprire il comune. Tocca le intestazioni per ordinare.</p>
      <div class="strumenti">
        <div class="campo-el"><label for="tcAnno">Anno</label><select id="tcAnno"></select></div>
        <div class="campo-el"><label for="tcPart">Partito nel nome di una lista</label><select id="tcPart"></select></div>
        <div class="campo-el"><label for="tcCerca">Cerca</label><input id="tcCerca" placeholder="Nome del comune" autocomplete="off"></div>
        <button class="bot" type="button" id="tcCsv">Scarica in CSV</button>''', '''      <h2 id="tcTitolo">Tutti i comuni</h2>
      <p class="sotto">Una riga per comune, con l'elezione scelta nei filtri. Tocca una riga per aprire il comune. Tocca le intestazioni per ordinare.</p>
      <div class="strumenti">
        <button class="bot" type="button" id="tcCsv">Scarica in CSV</button>''')
assert 'id="tcAnno"' not in corpo and 'id="tcTitolo"' in corpo
corpo = corpo.replace('<a class="solo-com" href="#sez-com-scheda">Il comune</a>', '<a class="solo-com" href="#filtriCom">Filtri</a><a class="solo-com" href="#sez-com-scheda">Il comune</a>')
assert '#filtriCom' in corpo
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
    sel = re.sub(r'/\*.*?\*/', '', sel, flags=re.S).strip()  # un commento prima del selettore ne impediva la riscrittura
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
assert '#elezioni[data-vista="com"] .solo-reg{display:none!important}' in css and '\nbody' not in css, 'regola delle viste non confinata'
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

css += '''
#elezioni #filtriCom .strumenti{margin-bottom:4px}
#elezioni #filtriCom .campo-el select,#elezioni #filtriCom .campo-el input{min-width:200px}
#elezioni #fcEl{min-width:250px}
#elezioni #fcCerca{min-width:230px}
#elezioni #fcRiepilogo{margin-top:6px}
@media (max-width:640px){#elezioni #filtriCom .campo-el{flex:1 1 100%}#elezioni #filtriCom .campo-el select,#elezioni #filtriCom .campo-el input{min-width:0;width:100%}}
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
sost('comPrec:null };', 'comPrec:null, plCirc:null, plLista:null, candCerca:"", candLista:"", cCirc:"" };')
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
sost('''d3.select("#cGen").on("change",function(){S.cGen=this.value;S.cMostra=50;disegnaCandidati();});''',
     '''d3.select("#cGen").on("change",function(){S.cGen=this.value;S.cMostra=50;disegnaCandidati();});
d3.select("#cCirc").selectAll("option").data([""].concat(CIRC)).join("option").attr("value",d=>d).text(d=>d===""?"Tutte le circoscrizioni":"Circoscrizione di "+d);
d3.select("#cCirc").on("change",function(){S.cCirc=this.value;S.cMostra=50;disegnaCandidati();});''')
sost('''  const idx=insieme();
  const totLista={};
  let righe=K.map(k=>({k,v:prefIn(k,idx)})).filter(r=>r.v!=null);''',
     '''  // filtro per circoscrizione della classifica: se il territorio scelto in alto è già una circoscrizione (o un comune), vale quello
  const circTerr = S.com!=null ? C[S.com].ci : S.circ;
  const sc=d3.select("#cCirc"); sc.property("value",circTerr||S.cCirc).property("disabled",!!circTerr);
  const circClass = circTerr || S.cCirc;
  const idx = circClass && !circTerr ? TUTTI.filter(i=>C[i].ci===circClass && !assente(i)) : insieme();
  const totLista={};
  let righe=K.map(k=>({k,v:prefIn(k,idx)})).filter(r=>r.v!=null && (!circClass || r.k.ci===circClass));''')
sost('''d3.select("#candSotto").text((D.prefNota?D.prefNota+" ":"")+"Preferenze in "+terrPref()+".''',
     '''d3.select("#candSotto").text((D.prefNota?D.prefNota+" ":"")+"Preferenze in "+(circClass && !circTerr ? "circoscrizione di "+circClass : terrPref())+".''')
sost('''  S.lista=fdi; S.tLista=fdi; S.pres=0; S.cand=null;''', '''  S.lista=fdi; S.tLista=fdi; S.pres=0; S.cand=null; S.plLista=null; S.candCerca=""; S.candLista=""; d3.select("#cercaCand").property("value","");''')
sost('''disegnaMatrice(); disegnaComuni(); disegnaStoria();
}''', '''disegnaMatrice(); disegnaComuni(); disegnaPrefListe(); disegnaStoria();
}''')
sost('''// ---------- aggiornamento generale
function aggiorna(spostaMappa){''', open(__file__.replace('prepara_elezioni.py', 'prefliste.js'), encoding='utf-8').read() + '''
// ---------- aggiornamento generale
function aggiorna(spostaMappa){''')
# ---------------------------------------------------------------- comunali: filtri unici (scripts/filtricom.js)
sost('cCirc:"" };', 'cCirc:"", fcEl:"1", fcPart:"", fcDim:"", fcEsito:"", fcCerca:"" };')
sost('function ambitoCom(){ return S.circ ? TUTTI.filter(i=>C[i].ci===S.circ) : TUTTI; }',
     open(__file__.replace('prepara_elezioni.py', 'filtricom.js'), encoding='utf-8').read())
# nelle funzioni delle comunali l'elezione di ogni comune è quella scelta nei filtri (EL), non più sempre l'ultima (ULT)
a = app.index('// ---------- indicatori\nfunction disegnaKpiCom'); b = app.index('// ---------- scelta della vista')
blocco = re.sub(r'ULT\[([^\]]+)\]', r'EL(\1)', app[a:b]).replace('EL(S.com)', 'ELC(S.com)')
assert 'ULT[' not in blocco
app = app[:a] + blocco + app[b:]
# filtri delle singole sezioni: restano solo i pulsanti di scarico e «Mostra altri»
sost('''  const anni=[...new Set(ULT.filter(Boolean).map(anno))].sort((a,b)=>b-a);
  d3.select("#tcAnno").selectAll("option").data([""].concat(anni)).join("option").attr("value",d=>d).text(d=>d===""?"Tutti gli anni":d);
  d3.select("#tcAnno").on("change",function(){S.tcAnno=this.value;disegnaTabComuniCom();});
  const op=[""].concat(PART.map((p,k)=>k));
  ["#tcPart","#cpPart"].forEach(id=>d3.select(id).selectAll("option").data(op).join("option").attr("value",d=>d).text(d=>d===""?"Tutte":PART[d].n));
  d3.select("#tcPart").on("change",function(){S.tcPart=this.value;disegnaTabComuniCom();});
  d3.select("#cpPart").on("change",function(){S.cpPart=this.value;S.cpMostra=50;disegnaClassificaCom();});
  d3.select("#tcCerca").on("input",function(){S.tcCerca=this.value.trim().toLowerCase();disegnaTabComuniCom();});
  d3.select("#cpCerca").on("input",function(){S.cpCerca=this.value.trim().toLowerCase();S.cpMostra=50;disegnaClassificaCom();});
''', '')
sost('''  if (S.cpPart!=="") righe=righe.filter(r=>r.l.pa.includes(+S.cpPart));
  if (S.cpCerca) righe=righe.filter(r=>r.p[1].toLowerCase().includes(S.cpCerca)||C[r.c.c].n.toLowerCase().includes(S.cpCerca));''',
     '''  if (S.fcPart!=="") righe=righe.filter(r=>r.l.pa.includes(+S.fcPart));
  if (S.fcCerca) righe=righe.filter(r=>normTesto(r.p[1]).includes(S.fcCerca)||normTesto(C[r.c.c].n).includes(S.fcCerca));
  d3.select("#cpSotto").text(`Preferenze ${etEl()} nei comuni del territorio scelto${S.fcPart!==""?", solo nelle liste con il nome "+PART[+S.fcPart].n:""}. Tocca una riga per aprire il comune. Attenzione: i comuni hanno dimensioni molto diverse.`);''')
sost('''  if (S.tcAnno) righe=righe.filter(r=>anno(r.c)===+S.tcAnno);
  if (S.tcPart!=="") righe=righe.filter(r=>partitiUlt(r.i).includes(+S.tcPart));
  if (S.tcCerca) righe=righe.filter(r=>C[r.i].n.toLowerCase().includes(S.tcCerca));''',
     '''  if (S.fcCerca) righe=righe.filter(r=>normTesto(C[r.i].n).includes(S.fcCerca)||(r.w&&normTesto(r.w.s.n).includes(S.fcCerca)));
  d3.select("#tcTitolo").text("Tutti i comuni, "+etElBreve());''')
sost('{m:0,k:"d",t:"Ultima elezione",f:r=>dataIt(r.c.d),csv:r=>r.c.d},', '{m:0,k:"d",t:"Elezione",f:r=>dataIt(r.c.d),csv:r=>r.c.d},')
sost('scaricaCsv("comunali-fvg-ultima-elezione.csv",COL_TC,TC_RIGHE)', 'scaricaCsv("comunali-fvg-"+etElBreve().replace(/ /g,"-")+".csv",COL_TC,TC_RIGHE)')
sost('''function disegnaComunali(){
  disegnaKpiCom();''', '''function disegnaComunali(){
  riepilogoFiltri(); disegnaKpiCom();''')
# testi che davano per scontata l'ultima elezione
sost('{et:"Ultima elezione",t:dataIt(c.d),n:c.ba?"con ballottaggio":"turno unico"},', '{et:cap(etElBreve()),t:dataIt(c.d),n:c.ba?"con ballottaggio":"turno unico"},')
sost('{et:"Comuni",v:idx.length,f:x=>N(Math.round(x)),n:S.circ?"circoscrizione di "+S.circ:"tutta la regione"},', '{et:"Comuni",v:idx.length,f:x=>N(Math.round(x)),n:(S.circ?"circoscrizione di "+S.circ:"tutta la regione")+(filtriAttivi()?", con i filtri":"")},')
sost('''{et:"Affluenza all'ultima",v:el?vv/el:null,f:x=>pf(x),n:"regionali 2023: "+pf(r.aff[FIN]/r.el,1)},''', '''{et:"Affluenza",v:el?vv/el:null,f:x=>pf(x),n:"regionali 2023: "+pf(r.aff[FIN]/r.el,1)},''')
sost('''{et:"Candidati sindaco",v:d3.sum(ult,c=>c.S.length),f:x=>N(Math.round(x)),n:"all'ultima elezione"},''', '''{et:"Candidati sindaco",v:d3.sum(ult,c=>c.S.length),f:x=>N(Math.round(x)),n:etEl()},''')
sost('''{et:"Candidato unico",v:ult.filter(c=>c.S.length===1).length,f:x=>N(Math.round(x)),n:"comuni, all'ultima elezione"},''', '''{et:"Candidato unico",v:ult.filter(c=>c.S.length===1).length,f:x=>N(Math.round(x)),n:"comuni, "+etEl()},''')
sost('''  const idx=ambitoCom(), ult=idx.map(i=>EL(i)).filter(Boolean);
  const anni=d3.rollups(ult,v=>v.length,anno).sort((a,b)=>b[1]-a[1]);''', '''  const idx=ambitoCom(), ult=idx.map(i=>EL(i)).filter(Boolean);
  if (!ult.length){ box.html(`<h2 class="sintesi-tit">${S.circ?"Circoscrizione di "+esc(S.circ):"Friuli Venezia Giulia"}: le elezioni comunali</h2><div class="sintesi"><p>Nessun comune del territorio corrisponde ai filtri scelti: cambia elezione, partito, dimensione o esito, oppure azzera i filtri.</p></div>`); return; }
  const anni=d3.rollups(ult,v=>v.length,anno).sort((a,b)=>b[1]-a[1]);''')
sost("<p>Ogni comune vota con un suo calendario: l'ultima elezione va dal ${dataIt(dmin)} al ${dataIt(dmax)}.", "<p>Ogni comune vota con un suo calendario: l'elezione scelta (${etElBreve()}) va dal ${dataIt(dmin)} al ${dataIt(dmax)}.")
sost("<p>All'ultima tornata, in <b>${unico}</b> comuni su ${ult.length}", "<p>${cap(etEl())}, in <b>${unico}</b> comuni su ${ult.length}")
sost('''  const idx=ambitoCom(), tutte=idx.flatMap(i=>PER_COM[i].filter(c=>c.o>0));
  const anni=d3.range(''', '''  const idx=ambitoCom(), tutte=idx.flatMap(i=>PER_COM[i].filter(c=>c.o>0));
  if (!tutte.length){ d3.select("#calCom").html('<p class="nota-el">Nessun comune corrisponde ai filtri scelti.</p>'); return; }
  const anni=d3.range(''')
sost('''d3.select("#partSotto").text(`All'ultima elezione, ${S.circ?"circoscrizione di "+S.circ:"tutta la regione"}. Tocca una riga per vederla sulla mappa.`);''', '''d3.select("#partSotto").text(`${cap(etEl())}, ${S.circ?"circoscrizione di "+S.circ:"tutta la regione"}${filtriAttivi()?", con i filtri scelti":""}. Tocca una riga per vederla sulla mappa.`);''')
# mappa: lenti e legende seguono i filtri; i comuni esclusi restano in grigio
sost('''{k:"cAnno",t:"Anno dell'ultima elezione"}''', '''{k:"cAnno",t:"Anno dell'elezione"}''')
sost('''  let colore, leg="";
  const ult=i=>EL(i);
  if (S.lenteC==="cAnno"){''', '''  let colore, leg="";
  const ult=i=>EL(i);
  const esclusi=(S.circ?TUTTI.filter(i=>C[i].ci===S.circ):TUTTI).length-ambito.length;
  const notaEsclusi = esclusi ? `<p class="nota-el">In grigio ${esclusi} ${esclusi===1?"comune escluso":"comuni esclusi"} dai filtri delle comunali.</p>` : "";
  if (!ambito.length) return {colore:()=>ass, leg:`<h3>Nessun comune</h3><p class="nota-el">Nessun comune del territorio corrisponde ai filtri scelti.</p>`};
  if (S.lenteC==="cAnno"){''')
sost("leg=`<h3>Anno dell'ultima elezione</h3>${cont.map(", "leg=`<h3>Anno dell'elezione (${etElBreve()})</h3>${cont.map(")
sost('''legendaScala("Affluenza all'ultima elezione comunale","#1a6098"''', '''legendaScala("Affluenza "+etEl(),"#1a6098"''')
sost("leg=`<h3>Candidati sindaco all'ultima elezione</h3>", "leg=`<h3>Candidati sindaco ${etEl()}</h3>")
sost("Presenti in <b>${pres.length}</b> comuni all'ultima elezione. Grigio: nessuna lista con questo nome.", "Presenti in <b>${pres.length}</b> comuni ${etEl()}. Grigio: nessuna lista con questo nome.")
sost('''<p class="nota-el">Nessuna lista con questo nome all'ultima elezione nel territorio scelto.</p>''', '''<p class="nota-el">Nessuna lista con questo nome ${etEl()} nel territorio scelto.</p>''')
sost('''  return {colore, leg};
}
function schedaComuneCom(i){
  const c=EL(i), w=vincitore(c), a=affFin(c), rr=aggrega([i]);
  return `<h4>${esc(C[i].n)}</h4><small>Ultima elezione: ${dataIt(c.d)}''', '''  return {colore, leg:leg+notaEsclusi};
}
function schedaComuneCom(i){
  const c=EL(i); if (!c || !passaFiltri(i)) return `<h4>${esc(C[i].n)}</h4><small>${c?"Escluso dai filtri delle comunali":"Nessuna elezione comunale "+etEl()}</small>`;
  const w=vincitore(c), a=affFin(c), rr=aggrega([i]);
  return `<h4>${esc(C[i].n)}</h4><small>${cap(etElBreve())}: ${dataIt(c.d)}''')
sost('const ambito = (S.circ ? TUTTI.filter(i=>C[i].ci===S.circ) : TUTTI).filter(i=>S.vista==="com"||!assente(i));', 'const ambito = (S.circ ? TUTTI.filter(i=>C[i].ci===S.circ) : TUTTI).filter(i=>S.vista==="com"?passaFiltri(i):!assente(i));')
sost('  if (S.vista!=="com"){ const c0=colore; colore=i=>assente(i)?ass:c0(i); }', '  if (S.vista!=="com"){ const c0=colore; colore=i=>assente(i)?ass:c0(i); } else { const c0=colore; colore=i=>passaFiltri(i)?c0(i):ass; }')
# scheda del comune: all'apertura di un comune si parte dall'elezione scelta nei filtri
sost('if (S.com!==S.comPrec){ S.comPrec=S.com; S.consO=1;', 'if (S.com!==S.comPrec){ S.comPrec=S.com; S.consO=S.com!=null&&EL(S.com)?EL(S.com).o:1;')
# indicatori del territorio: seguono i filtri, non il solo territorio
sost('''function disegnaKpiCom(){
  const idx=insieme(), box=d3.select("#kpiCom");''', '''function disegnaKpiCom(){
  let idx=insieme(); const box=d3.select("#kpiCom");''')
sost('''  } else {
    const ult=idx.map(i=>EL(i)).filter(Boolean);
    let el=0,vv=0;''', '''  } else {
    idx=ambitoCom();
    const ult=idx.map(i=>EL(i)).filter(Boolean);
    let el=0,vv=0;''')
sost('{et:"Elezioni comunali",v:nCons,f:x=>N(Math.round(x)),n:"le ultime tre di ogni comune"},', '{et:"Elezioni comunali",v:nCons,f:x=>N(Math.round(x)),n:"le ultime tre di ogni comune mostrato"},')
sost('{et:"Ballottaggi",v:ball,f:x=>N(Math.round(x)),n:"nelle tre tornate"}', '{et:"Ballottaggi",v:ball,f:x=>N(Math.round(x)),n:"nelle tre tornate dei comuni mostrati"}')
sost('d3.select("#tcConta").text(`${N(righe.length)} comuni.`);', 'd3.select("#tcConta").text(`${N(righe.length)} ${righe.length===1?"comune":"comuni"}.`);')
assert 'S.tcAnno' not in app and 'S.cpPart' not in app and 'S.tcCerca' not in app and 'S.cpCerca' not in app
script[-1] = app

frammento = '<style>\n' + css + '\n</style>\n' + corpo.strip() + '\n' + ''.join(f'<script>{x}</script>\n' for x in script)
open(uscita, 'w', encoding='utf-8').write(frammento)
print(f'frammento: {len(frammento):,} caratteri · stile {len(css):,} · corpo {len(corpo):,} · script {[len(x) for x in script]}')
