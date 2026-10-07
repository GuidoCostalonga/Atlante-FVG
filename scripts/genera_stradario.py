#!/usr/bin/env python3
"""Genera stradario/index.html: lo Stradario del Friuli Venezia Giulia con la grafica dell'Atlante.

Mappa stradale (OpenStreetMap) e satellitare (Esri) di tutta la regione, ricerca di vie, piazze e luoghi
(geocodificatore Photon, su dati OpenStreetMap, limitato al Friuli Venezia Giulia), scelta rapida di uno dei
215 comuni, posizione del telefono, collegamento condivisibile. Aperta con ?comune=<nome> o #<nome> la pagina
parte già centrata sul comune, con il segnaposto e il cartellino, come la pagina «Mappa di Roveredo in Piano»
di costalonga.org da cui deriva.

I comuni, con le coordinate, vengono dall'elenco della pagina Meteo (meteo/index.html), che li prende dalla
stessa fonte dell'Atlante. Uso: python scripts/genera_stradario.py
"""
import json, re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def comuni():
    t = (RADICE / 'meteo' / 'index.html').read_text(encoding='utf-8')
    i = t.index('const COMUNI=['); j = t.index('];', i)
    lista = json.loads(t[i + len('const COMUNI='):j + 1])
    # nome, provincia, latitudine, longitudine (il codice ISTAT non serve qui)
    return [[n, pv, lat, lon] for n, pv, lat, lon, _ in lista]


PAGINA = r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stradario del Friuli Venezia Giulia · Atlante FVG</title>
<meta name="description" content="Stradario del Friuli Venezia Giulia: cerca una via, una piazza o un luogo in uno dei 215 comuni sulla mappa stradale e satellitare, con la tua posizione e il collegamento da condividere.">
<link rel="canonical" href="https://atlantefvg.it/stradario/">
<link rel="icon" href="../favicon.ico" sizes="any">
<meta name="theme-color" content="#0B3359">
<meta property="og:type" content="website">
<meta property="og:locale" content="it_IT">
<meta property="og:site_name" content="Atlante FVG">
<meta property="og:url" content="https://atlantefvg.it/stradario/">
<meta property="og:title" content="Stradario del Friuli Venezia Giulia · Atlante FVG">
<meta property="og:description" content="Cerca una via, una piazza o un luogo nei 215 comuni del Friuli Venezia Giulia, sulla mappa stradale e satellitare.">
<meta property="og:image" content="https://atlantefvg.it/anteprima.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Atlante FVG","item":"https://atlantefvg.it/"},{"@type":"ListItem","position":2,"name":"Stradario","item":"https://atlantefvg.it/stradario/"}]}</script>
<script data-goatcounter="https://guidocostalonga.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="../pagine.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
  .contenuto { padding-bottom: 16px; gap: 12px; }
  .comandi { display: grid; grid-template-columns: 1fr; gap: 10px; }
  @media (min-width: 900px) { .comandi { grid-template-columns: minmax(0, 1fr) auto; align-items: end; } }
  .cerca { position: relative; }
  .cerca .campo { padding-left: 40px; }
  .cerca .lente { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); margin-top: 11px; color: var(--testo-3); pointer-events: none; }
  .risultati { position: absolute; z-index: 1100; left: 0; right: 0; top: 100%; margin-top: 4px; background: #fff; border: 1px solid var(--linea); border-radius: 12px; box-shadow: 0 8px 24px rgba(11,51,89,.14); max-height: 20rem; overflow-y: auto; padding: 4px; }
  .risultati button { width: 100%; display: flex; align-items: flex-start; gap: 10px; text-align: left; min-height: 48px; padding: 8px; border: 0; background: none; border-radius: 8px; font: inherit; color: var(--testo); cursor: pointer; }
  .risultati button:hover, .risultati button[aria-selected="true"] { background: var(--blu-tenue); }
  .risultati .tipo { flex: 0 0 auto; margin-top: 2px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--blu-medio); background: var(--blu-tenue); border-radius: 6px; padding: 2px 6px; }
  .risultati .dove { display: block; font-size: 13px; color: var(--testo-3); }
  .pulsanti { display: flex; flex-wrap: wrap; gap: 8px; }
  .riquadro-mappa { position: relative; border-radius: 14px; overflow: hidden; border: 1px solid var(--linea); background: #EDE9DF; }
  #mappa { height: calc(100dvh - 56px - 120px); min-height: 420px; }
  @media (min-width: 1024px) { #mappa { height: calc(100dvh - 64px - 200px); min-height: 480px; } }
  .cartellino { position: absolute; z-index: 1000; left: 50%; top: 12px; transform: translateX(-50%); max-width: calc(100% - 24px); background: #fff; border: 1px solid var(--linea); border-radius: 12px; box-shadow: 0 8px 24px rgba(11,51,89,.14); padding: 8px 14px; text-align: center; pointer-events: none; }
  .cartellino b { font-family: var(--serif); font-size: 16px; color: var(--blu); display: block; line-height: 1.25; }
  .cartellino small { display: block; font-size: 12px; color: var(--testo-3); font-variant-numeric: tabular-nums; margin-top: 2px; }
  .cartellino a { pointer-events: auto; }
  .leaflet-container { font-family: var(--sans); font-size: 13px; }
  .leaflet-control-layers, .leaflet-bar { border: 1px solid var(--linea) !important; border-radius: 10px !important; box-shadow: 0 2px 8px rgba(11,51,89,.12) !important; overflow: hidden; }
  .leaflet-control-layers-expanded { padding: 8px 12px; font-size: 14px; color: var(--testo); }
  .leaflet-control-layers label { display: flex; align-items: center; gap: 10px; min-height: 40px; margin: 0; cursor: pointer; }
  .leaflet-control-layers input { accent-color: var(--blu-chiaro); width: 18px; height: 18px; }
  .leaflet-bar a { width: 40px !important; height: 40px !important; line-height: 40px !important; color: var(--blu) !important; font-weight: 700; font-size: 18px; }
  .leaflet-bar a:hover { background: var(--blu-tenue) !important; }
  .leaflet-popup-content-wrapper { border-radius: 12px !important; box-shadow: 0 8px 24px rgba(11,51,89,.16) !important; }
  .leaflet-popup-content { font-size: 14px; line-height: 1.5; margin: 12px 16px; }
  .leaflet-popup-content b { color: var(--blu); font-family: var(--serif); font-size: 15px; }
  .leaflet-container a { color: var(--blu-medio); }
  .leaflet-control-attribution { font-size: 11px; color: #4a463e; background: rgba(255,255,255,.85) !important; }
  .leaflet-control-attribution a { color: var(--blu-medio); }
  .scelto { display: none; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
  .scelto.visibile { display: flex; }
  .scelto .dati { flex: 1 1 16rem; min-width: 0; }
  .scelto h2 { font-size: 1.15rem; }
  .scelto .nota { margin-top: 2px; }
  .scelto .pulsanti { flex: 0 0 auto; }
  .fonte { font-size: 12px; color: var(--testo-3); line-height: 1.5; }
  /* sul telefono la mappa viene subito dopo la ricerca; il riquadro del luogo scelto sta sotto la mappa */
  @media (max-width: 899px) { .riquadro-mappa { order: 4; } .scelto { order: 5; } .fonte { order: 6; } .intro p { font-size: 15px; } }
</style>
</head>
<body>
<header class="testata"><div class="testata-dentro">
  <a class="marchio" href="../" aria-label="Atlante FVG, pagina iniziale"><img src="../logo.webp" alt="Atlante FVG" width="113" height="40"></a>
  <nav class="voci" aria-label="Pagine dell'Atlante">
    <a href="../">Inizio</a><a href="../?pagina=mappe">Mappe</a><a href="../?pagina=comuni">Comuni</a><a href="../?pagina=autobus">Autobus</a><a href="../orari/">Orari</a><a href="../meteo/">Meteo</a><a href="../stradario/" aria-current="page">Stradario</a><a href="../catasto/">Catasto</a><a href="../?pagina=metodo">Metodo</a>
  </nav>
  <details class="menu-mob"><summary>Menu</summary><nav aria-label="Pagine dell'Atlante">
    <a href="../">Inizio</a><a href="../?pagina=mappe">Mappe</a><a href="../?pagina=comuni">Comuni</a><a href="../?pagina=autobus">Autobus in tempo reale</a><a href="../orari/">Orari degli autobus</a><a href="../meteo/">Meteo</a><a href="../stradario/" aria-current="page">Stradario</a><a href="../catasto/">Catasto</a><a href="../?pagina=metodo">Metodo e fonti</a>
  </nav></details>
</div></header>

<main class="contenuto">
  <nav class="percorso" aria-label="Percorso"><a href="../">Atlante FVG</a> › Stradario</nav>
  <section class="intro">
    <h1>Stradario del Friuli Venezia Giulia</h1>
    <p>Cerca una via, una piazza o un luogo in uno dei 215 comuni, oppure scegli il comune: la mappa stradale si può cambiare in satellitare. Il collegamento ricorda il punto scelto, comodo da mandare per messaggio.</p>
  </section>

  <section class="riquadro" aria-labelledby="titoloCerca">
    <h2 id="titoloCerca" class="sr-only">Cerca sulla mappa</h2>
    <div class="comandi">
      <div class="cerca">
        <label class="etichetta" for="cerca">Via, piazza, luogo o comune</label>
        <svg class="lente" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input id="cerca" class="campo" type="search" autocomplete="off" placeholder="Per esempio: via Roma, Roveredo in Piano" role="combobox" aria-autocomplete="list" aria-controls="risultati" aria-expanded="false">
        <div id="risultati" class="risultati" role="listbox" aria-label="Luoghi trovati" hidden></div>
      </div>
      <div class="pulsanti">
        <button type="button" class="btn btn-secondario" id="btnPosizione"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="8"/></svg>La mia posizione</button>
        <button type="button" class="btn btn-secondario" id="btnCondividi">Copia il collegamento</button>
      </div>
    </div>
    <p class="nota" id="statoCerca" role="status"></p>
  </section>

  <section class="riquadro scelto" id="scelto" aria-live="polite">
    <div class="dati"><h2 id="sceltoNome"></h2><p class="nota" id="sceltoDove"></p></div>
    <div class="pulsanti" id="sceltoAzioni"></div>
  </section>

  <div class="riquadro-mappa">
    <div id="mappa" role="region" aria-label="Mappa stradale del Friuli Venezia Giulia"></div>
    <div class="cartellino" id="cartellino" hidden><b id="cartNome"></b><small id="cartDati"></small></div>
  </div>
  <p class="fonte">Mappa stradale: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© contributori di OpenStreetMap</a>. Immagini satellitari: Esri, Maxar, Earthstar Geographics. Ricerca dei luoghi: <a href="https://photon.komoot.io/" target="_blank" rel="noopener">Photon</a>, su dati OpenStreetMap. Mappa e risultati sono scaricati dal tuo browser al momento; la posizione, se la chiedi, resta sul tuo telefono. Le coordinate dei comuni sono quelle dell'Atlante. Hai trovato un errore? <a href="mailto:info@atlantefvg.it?subject=Segnalazione%20di%20errore%3A%20stradario">Segnalalo per posta</a> oppure <a href="https://wa.me/393283692227?text=Segnalazione%20di%20errore%20sull%27Atlante%20FVG%3A%20pagina%20Stradario" target="_blank" rel="noopener">via WhatsApp</a>.</p>
</main>

<footer class="piede"><div class="piede-dentro">
  <div><strong>Atlante FVG</strong><br>I comuni del Friuli Venezia Giulia, con fonte e data di ogni dato.</div>
  <div><a href="../">Pagina iniziale</a> · <a href="../?pagina=mappe">Mappe</a> · <a href="../catasto/">Catasto</a> · <a href="../?pagina=metodo">Metodo e fonti</a></div>
</div></footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
(() => {
  const COMUNI = __COMUNI__;
  const PROV = { UD: 'Udine', PN: 'Pordenone', GO: 'Gorizia', TS: 'Trieste' };
  // confini della regione per la ricerca (ovest, sud, est, nord)
  const BOX = [12.32, 45.58, 13.92, 46.65];
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const slug = n => String(n || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const coord = (lat, lon) => `${lat.toFixed(4).replace('.', ',')} N · ${lon.toFixed(4).replace('.', ',')} E`;
  COMUNI.forEach(c => c.push(slug(c[0])));

  /* ---------- mappa ---------- */
  const mappa = L.map('mappa', { zoomSnap: .5, attributionControl: true });
  mappa.attributionControl.setPrefix('');
  const stradale = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(mappa);
  const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: 'Immagini © Esri, Maxar, Earthstar Geographics' });
  L.control.layers({ 'Stradale': stradale, 'Satellite': satellite }, null, { collapsed: matchMedia('(max-width: 899px)').matches, position: 'topright' }).addTo(mappa);
  L.control.scale({ imperial: false }).addTo(mappa);
  const VISTA_FVG = [[45.58, 12.32], [46.65, 13.92]];
  mappa.fitBounds(VISTA_FVG, { padding: [10, 10] });
  let segnaposto = null, cerchio = null, scelta = null;

  function mostra(p, { zoom = 16, apri = true } = {}) {
    // p: { nome, dove, lat, lon, tipo, comune }
    scelta = p;
    if (segnaposto) segnaposto.remove();
    segnaposto = L.marker([p.lat, p.lon]).addTo(mappa);
    const link = p.comune ? `<br><a href="../c/${p.comune[4]}/">Dati del comune nell'Atlante</a>` : '';
    segnaposto.bindPopup(`<b>${esc(p.nome)}</b><br>${esc(p.dove)}${link}`);
    mappa.setView([p.lat, p.lon], zoom);
    if (apri) segnaposto.openPopup();
    $('cartellino').hidden = false; $('cartNome').textContent = p.nome; $('cartDati').textContent = `${coord(p.lat, p.lon)}${p.dove ? ' · ' + p.dove : ''}`;
    $('scelto').classList.add('visibile'); $('sceltoNome').textContent = p.nome; $('sceltoDove').textContent = `${p.dove ? p.dove + ' · ' : ''}${coord(p.lat, p.lon)}`;
    $('sceltoAzioni').innerHTML = (p.comune ? `<a class="btn btn-secondario" href="../c/${p.comune[4]}/">Dati del comune</a><a class="btn btn-secondario" href="../meteo/#${p.comune[4]}">Meteo</a>` : '')
      + `<a class="btn btn-secondario" href="https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lon}#map=${zoom}/${p.lat}/${p.lon}" target="_blank" rel="noopener">Apri in OpenStreetMap</a>`;
    ricorda();
  }

  function mostraComune(c, { apri = true } = {}) {
    mostra({ nome: `${c[0]} (${c[1]})`, dove: `Provincia di ${PROV[c[1]]}`, lat: c[2], lon: c[3], tipo: 'comune', comune: c }, { zoom: 14, apri });
  }

  /* ---------- indirizzo condivisibile: ?comune=<nome> oppure #<lat>,<lon>,<zoom> ---------- */
  function ricorda() {
    if (!scelta) return;
    const u = new URL(location.href); u.search = ''; u.hash = '';
    if (scelta.comune) u.searchParams.set('comune', scelta.comune[4]);
    else u.hash = `${scelta.lat.toFixed(5)},${scelta.lon.toFixed(5)},${mappa.getZoom()}`;
    try { history.replaceState(null, '', u.pathname + u.search + u.hash); } catch (e) { /* indirizzo non modificabile */ }
  }
  $('btnCondividi').addEventListener('click', async () => {
    let fatto = false;
    try { await navigator.clipboard.writeText(location.href); fatto = true; } catch (e) { /* appunti non disponibili */ }
    const b = $('btnCondividi'); b.textContent = fatto ? 'Collegamento copiato' : 'Copia non riuscita: usa la barra degli indirizzi';
    clearTimeout(b.attesa); b.attesa = setTimeout(() => { b.textContent = 'Copia il collegamento'; }, 2600);
  });

  /* ---------- posizione del telefono ---------- */
  $('btnPosizione').addEventListener('click', () => {
    if (!navigator.geolocation) { $('statoCerca').textContent = 'Il tuo browser non sa dare la posizione.'; return; }
    $('statoCerca').textContent = 'Cerco la tua posizione…';
    navigator.geolocation.getCurrentPosition(pos => {
      const { latitude: lat, longitude: lon, accuracy } = pos.coords;
      if (cerchio) cerchio.remove();
      cerchio = L.circle([lat, lon], { radius: accuracy || 30, color: '#155E9E', fillColor: '#155E9E', fillOpacity: .15, weight: 1.5 }).addTo(mappa);
      $('statoCerca').textContent = `Posizione trovata, precisione di circa ${Math.round(accuracy || 0)} metri. Non viene inviata a nessuno.`;
      mostra({ nome: 'La tua posizione', dove: '', lat, lon, tipo: 'posizione' }, { zoom: 16 });
    }, err => { $('statoCerca').textContent = err.code === 1 ? 'Posizione non consentita: puoi cercare una via o un comune.' : 'Posizione non disponibile in questo momento.'; }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
  });

  /* ---------- ricerca: comuni dall'elenco dell'Atlante, vie e luoghi da Photon ---------- */
  const inp = $('cerca'), box = $('risultati'); let ris = [], sel = -1, attesa, ultimaRichiesta = 0;
  const TIPI = { street: 'via', house: 'civico', city: 'comune', town: 'comune', village: 'località', locality: 'località', district: 'quartiere', county: 'provincia', state: 'regione' };
  function etichettaTipo(f) {
    const p = f.properties; if (p.osm_key === 'highway') return p.osm_value === 'bus_stop' ? 'fermata' : 'via';
    if (p.osm_key === 'place') return TIPI[p.osm_value] || 'luogo';
    if (p.osm_key === 'amenity' || p.osm_key === 'shop' || p.osm_key === 'tourism' || p.osm_key === 'leisure') return 'luogo';
    if (p.osm_key === 'building') return 'edificio';
    return TIPI[p.type] || 'luogo';
  }
  const nomeRis = f => { const p = f.properties; return p.name || [p.street, p.housenumber].filter(Boolean).join(' ') || 'Luogo senza nome'; };
  const doveRis = f => { const p = f.properties; return [p.name && p.street ? [p.street, p.housenumber].filter(Boolean).join(' ') : '', p.postcode, p.city || p.town || p.village || p.locality, p.county && p.county !== p.city ? `provincia di ${p.county}` : ''].filter(Boolean).join(', '); };
  function disegna() {
    sel = ris.length ? 0 : -1;
    box.hidden = !ris.length; inp.setAttribute('aria-expanded', String(!box.hidden));
    box.innerHTML = ris.map((r, k) => `<button type="button" role="option" id="ris${k}" aria-selected="${k === sel}" data-k="${k}"><span class="tipo">${esc(r.tipo)}</span><span class="min-w-0"><span>${esc(r.nome)}</span><span class="dove">${esc(r.dove)}</span></span></button>`).join('');
  }
  function cercaComuni(q) {
    const parole = norm(q).split(/\s+/).filter(Boolean); if (!parole.length) return [];
    return COMUNI.filter(c => parole.every(w => norm(c[0]).includes(w))).slice(0, 5).map(c => ({ tipo: 'comune', nome: `${c[0]} (${c[1]})`, dove: `Provincia di ${PROV[c[1]]}`, lat: c[2], lon: c[3], comune: c }));
  }
  async function cerca() {
    const q = inp.value.trim();
    if (q.length < 2) { ris = []; disegna(); $('statoCerca').textContent = ''; return; }
    const locali = cercaComuni(q); ris = locali; disegna();
    const n = ++ultimaRichiesta;
    $('statoCerca').textContent = 'Cerco vie e luoghi…';
    try {
      // senza le fermate dell'autobus (stanno nella pagina Orari), altrimenti coprono le vie
      const u = `https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=10&lang=default&bbox=${BOX.join(',')}&osm_tag=!highway:bus_stop`;
      const r = await fetch(u); if (!r.ok) throw new Error('risposta ' + r.status);
      const j = await r.json(); if (n !== ultimaRichiesta) return;
      const visti = new Set(locali.map(x => x.nome));
      const esterni = (j.features || []).filter(f => f.geometry && f.properties && (f.properties.state || '').toLowerCase().includes('friuli')).map(f => ({ tipo: etichettaTipo(f), nome: nomeRis(f), dove: doveRis(f), lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] }))
        .filter(x => { const k = x.nome + '|' + x.dove; if (visti.has(k)) return false; visti.add(k); return true; });
      // prima le vie e i luoghi, poi le fermate
      esterni.sort((a, b) => (a.tipo === 'fermata') - (b.tipo === 'fermata'));
      ris = [...locali, ...esterni].slice(0, 10); disegna();
      $('statoCerca').textContent = ris.length ? `${ris.length} ${ris.length === 1 ? 'risultato' : 'risultati'} in Friuli Venezia Giulia.` : 'Nessun risultato: prova con il nome della via e del comune, per esempio «via Roma, Roveredo in Piano».';
    } catch (e) {
      if (n !== ultimaRichiesta) return;
      $('statoCerca').textContent = locali.length ? 'La ricerca delle vie non risponde in questo momento; i comuni sono comunque disponibili.' : 'La ricerca delle vie non risponde in questo momento: riprova tra poco.';
    }
  }
  function scegli(k) {
    const r = ris[k]; if (!r) return;
    box.hidden = true; inp.setAttribute('aria-expanded', 'false'); inp.value = r.nome;
    if (r.comune) mostraComune(r.comune); else mostra(r, { zoom: r.tipo === 'via' ? 17 : r.tipo === 'luogo' || r.tipo === 'civico' || r.tipo === 'edificio' || r.tipo === 'fermata' ? 18 : 15 });
    $('statoCerca').textContent = '';
  }
  inp.addEventListener('input', () => { clearTimeout(attesa); attesa = setTimeout(cerca, 300); });
  inp.addEventListener('focus', () => { if (ris.length && inp.value.trim()) { box.hidden = false; inp.setAttribute('aria-expanded', 'true'); } });
  inp.addEventListener('keydown', e => {
    if (e.key === 'Enter' && box.hidden) { e.preventDefault(); clearTimeout(attesa); cerca().then(() => { if (ris.length === 1) scegli(0); }); return; }
    if (box.hidden || !ris.length) { if (e.key === 'Escape') { box.hidden = true; inp.setAttribute('aria-expanded', 'false'); } return; }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); sel = (sel + (e.key === 'ArrowDown' ? 1 : ris.length - 1)) % ris.length; box.querySelectorAll('button').forEach((b, k) => b.setAttribute('aria-selected', String(k === sel))); inp.setAttribute('aria-activedescendant', 'ris' + sel); box.querySelector('#ris' + sel).scrollIntoView({ block: 'nearest' }); }
    else if (e.key === 'Enter') { e.preventDefault(); scegli(Math.max(0, sel)); }
    else if (e.key === 'Escape') { box.hidden = true; inp.setAttribute('aria-expanded', 'false'); }
  });
  box.addEventListener('mousedown', e => e.preventDefault());
  box.addEventListener('click', e => { const b = e.target.closest('button[data-k]'); if (b) scegli(+b.dataset.k); });
  document.addEventListener('click', e => { if (!box.hidden && !box.contains(e.target) && e.target !== inp) { box.hidden = true; inp.setAttribute('aria-expanded', 'false'); } });

  /* ---------- avvio: comune dall'indirizzo, oppure punto e zoom dal cancelletto ---------- */
  const q = new URLSearchParams(location.search), sc = slug(q.get('comune') || decodeURIComponent(location.hash.replace(/^#/, '')));
  const c0 = sc && COMUNI.find(c => c[4] === sc);
  const m = /^#(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?:,(\d+(?:\.\d+)?))?$/.exec(location.hash);
  if (c0) { inp.value = `${c0[0]} (${c0[1]})`; mostraComune(c0); }
  else if (m) mostra({ nome: 'Punto scelto', dove: '', lat: +m[1], lon: +m[2], tipo: 'punto' }, { zoom: m[3] ? +m[3] : 16 });
  mappa.on('zoomend moveend', () => { if (scelta && !scelta.comune) ricorda(); });
})();
</script>
</body>
</html>
"""


def main():
    lista = comuni()
    out = RADICE / 'stradario' / 'index.html'
    out.parent.mkdir(exist_ok=True)
    html = PAGINA.replace('__COMUNI__', json.dumps(lista, ensure_ascii=False, separators=(',', ':')))
    out.write_text(html, encoding='utf-8')
    print(f'Stradario: {out} scritta ({len(html) // 1024} KB, {len(lista)} comuni)')


if __name__ == '__main__':
    main()
