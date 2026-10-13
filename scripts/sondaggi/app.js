/* Osservatorio sondaggi: programma della sezione riservata.
   Legge l'archivio cifrato (ramo sondaggi-dati), lo apre con la chiave della sezione e costruisce le viste:
   Panoramica, Italia, Friuli Venezia Giulia, Istituti, Percezioni, Archivio, Gestione.
   Nessuna libreria esterna: grafici in SVG, esportazioni CSV e XLSX scritte qui. */
(() => {
  'use strict';
  const RAD = document.getElementById('oss');
  if (!RAD) return;
  const $ = (sel, el) => (el || RAD).querySelector(sel);
  const $$ = (sel, el) => [...(el || RAD).querySelectorAll(sel)];
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtN = (v, d) => v == null || isNaN(v) ? '–' : Number(v).toLocaleString('it-IT', { minimumFractionDigits: d == null ? (Number.isInteger(v) ? 0 : 1) : d, maximumFractionDigits: d == null ? 1 : d });
  const fmtPP = v => v == null || isNaN(v) ? '' : (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'];
  const fmtD = iso => { if (!iso) return '–'; const [a, m, g] = iso.slice(0, 10).split('-').map(Number); return isNaN(g) ? iso : `${g} ${MESI[m - 1]} ${a}`; };
  const fmtDbreve = iso => { if (!iso) return '–'; const [a, m, g] = iso.slice(0, 10).split('-').map(Number); return `${g} ${MESI[m - 1].slice(0, 3)} ${a}`; };
  const fmtDT = iso => { if (!iso) return '–'; const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString('it-IT', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Rome' }); };
  const periodo = r => r.inizio && r.fine && r.inizio !== r.fine ? `${fmtD(r.inizio)} – ${fmtD(r.fine)}` : (r.fine ? fmtD(r.fine) : (r.pubblicato ? fmtD(r.pubblicato) + ' (pubblicazione)' : '–'));
  const dataRif = r => r.fine || r.pubblicato || null;
  const oggi = () => new Date().toISOString().slice(0, 10);
  const giorni = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);
  const TIPI = { voto: 'Intenzioni di voto', fiducia: 'Fiducia e giudizi', priorita: 'Problemi prioritari', economia: 'Situazione economica', servizi: 'Amministrazione e servizi', tema: 'Temi e provvedimenti', scenario: 'Scenari e candidati', altro: 'Altre domande' };
  const ELEZ = { politiche: 'Politiche', europee: 'Europee', regionali: 'Regionali', comunali: 'Comunali', referendum: 'Referendum', primarie: 'Primarie' };
  const STATI = { verificata: ['Verificata', 'b-ok'], automatica: ['Automatica', 'b-auto'], secondaria: ['Fonte secondaria', 'b-sec'], senza_valori: ['Senza valori', 'b-grigio'], da_verificare: ['Da verificare', 'b-coda'], scartata: ['Scartata', 'b-no'] };
  const IN_GRAFICO = new Set(['verificata', 'automatica', 'secondaria']);
  const COMUNI_FVG = new Set(['trieste', 'udine', 'pordenone', 'gorizia', 'monfalcone', 'sacile', 'codroipo', 'cervignano del friuli', 'tolmezzo', 'latisana', 'lignano sabbiadoro', 'cividale del friuli', 'gemona del friuli', 'tavagnacco', 'azzano decimo', 'san vito al tagliamento', 'spilimbergo', 'maniago', 'grado', 'ronchi dei legionari', 'muggia', 'palmanova', 'fontanafredda', 'porcia', 'cordenons', 'casarsa della delizia', 'san daniele del friuli', 'aviano', 'roveredo in piano', 'manzano', 'san giorgio di nogaro', 'staranzano', 'brugnera', 'prata di pordenone', 'pasiano di pordenone', 'fiume veneto', 'zoppola', 'cormons', 'gradisca d\'isonzo', 'duino aurisina', 'martignacco', 'pavia di udine', 'pozzuolo del friuli', 'remanzacco', 'tricesimo', 'fagagna', 'majano', 'buja', 'aquileia', 'tarvisio']);
  const S = { a: null, restr: null, sogg: {}, vista: 'panoramica', p: {}, token: null, ordAr: ['data', -1], pagAr: 0, tipo: 'voto' };

  // ------------------------------------------------------------------------------------------ caricamento
  const daB64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const aB64 = u8 => { let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  async function decifra(p) {
    const k = window.ATLANTE_SONDAGGI_CHIAVE;
    if (!k) throw new Error('chiave non disponibile');
    const chiaro = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: daB64(p.i) }, k, daB64(p.d));
    const testo = await new Response(new Blob([chiaro]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    return JSON.parse(testo);
  }
  async function cifraJSON(oggetto) {
    const k = window.ATLANTE_SONDAGGI_CHIAVE;
    const gz = new Uint8Array(await new Response(new Blob([JSON.stringify(oggetto)]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer());
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const c = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, k, gz));
    return JSON.stringify({ v: 1, i: aB64(iv), d: aB64(c) });
  }
  async function carica() {
    const st = $('#stato-dati');
    try {
      const [rRestr, rSogg] = await Promise.all([fetch(RAD.dataset.restrizioni, { cache: 'no-cache' }).catch(() => null), fetch(RAD.dataset.soggetti, { cache: 'no-cache' }).catch(() => null)]);
      S.restr = rRestr && rRestr.ok ? await rRestr.json() : { regola: null, elezioni: [], periodi: [] };
      const sj = rSogg && rSogg.ok ? await rSogg.json() : { soggetti: [] };
      for (const s of sj.soggetti) S.sogg[s.id] = s;
      const r = await fetch(RAD.dataset.dati, { cache: 'no-cache' });
      if (r.status === 404) { S.a = vuoto(); st.innerHTML = '<b>Archivio non ancora pubblicato.</b> Il flusso automatico non ha ancora scritto il ramo dei dati: avvialo dalla scheda Gestione («Aggiorna adesso») o attendi il giro delle 6 di mattina.'; }
      else if (!r.ok) throw new Error('HTTP ' + r.status);
      else {
        const p = await r.json();
        S.a = p.d ? await decifra(p) : p;
        for (const s of Object.values(S.a.soggettiExtra || {})) S.sogg[s.id] = s;
        indicizza();
        st.innerHTML = `<span><b>${fmtN(S.R.length)}</b> rilevazioni</span><span>ultimo tentativo <b>${fmtDT(S.a.ultimoTentativo)}</b></span><span>ultimo aggiornamento riuscito <b>${fmtDT(S.a.ultimoRiuscito)}</b></span><span>ultima rilevazione disponibile <b>${fmtD(S.a.ultimaRilevazione)}</b></span>`;
      }
    } catch (e) {
      S.a = S.a || vuoto();
      st.innerHTML = `<span class="errore">Archivio non leggibile: ${esc(e.message)}. ${/chiave|decrypt|operation/i.test(e.message) ? 'La parola d\'ordine apre la pagina ma non l\'archivio: il flusso automatico usa un segreto diverso (vedi Gestione).' : ''}</span>`;
    }
    if (!S.R) indicizza();
    daHash();
    mostra();
  }
  const vuoto = () => ({ istituti: {}, fonti: {}, rilevazioni: {}, serie: {}, coda: {}, revisioni: [], esecuzioni: [], statoFonti: {} });
  function indicizza() {
    S.R = Object.values(S.a.rilevazioni || {}).map(r => { r._data = dataRif(r); r._area = area(r); r._ist = S.a.istituti[r.istituto] ? S.a.istituti[r.istituto].nome : (r.istituto || 'Istituto non indicato'); return r; }).sort((x, y) => (y._data || '').localeCompare(x._data || ''));
    S.perIst = {};
    for (const r of S.R) (S.perIst[r.istituto || '_'] = S.perIst[r.istituto || '_'] || []).push(r);
    S.SER = Object.values(S.a.serie || {});
  }
  function area(r) {
    const t = r.territorio || {};
    if (t.codice === 'FVG' || /friuli/i.test(t.nome || '')) return 'fvg';
    if (t.tipo === 'comune' && COMUNI_FVG.has((t.nome || '').toLowerCase())) return 'fvg';
    if (t.tipo === 'Italia' || !t.tipo) return 'italia';
    return 'altro';
  }
  const nomeSogg = id => id && id.startsWith('t:') ? id.slice(2).replace(/\b\w/g, c => c.toUpperCase()) : (S.sogg[id] ? S.sogg[id].nome : id);
  const colSogg = (id, i) => (S.sogg[id] && S.sogg[id].colore) || ['#0B3359', '#A41D22', '#D8973C', '#2F7D4F', '#155E9E', '#7A4E9E', '#8B5A2B', '#2B7A78', '#C0392B', '#5D6D7E', '#AF7AC5', '#17A589'][i % 12];

  // -------------------------------------------------------------------------------------------- restrizioni
  function blocchi() {
    const r = S.restr || {}; const regola = r.regola || { giorniPrima: 15, blocca: ['grafici', 'tabelle', 'esportazione'], tipi: ['voto', 'scenario'] };
    const oggiD = oggi(); const attivi = [];
    for (const e of [...(r.elezioni || []), ...((S.a && S.a.restrizioniExtra) || [])]) {
      if (e.attiva === false || !e.voto) continue;
      const inizio = new Date(e.voto); inizio.setDate(inizio.getDate() - (regola.giorniPrima || 15));
      const fine = e.chiusura || e.voto;
      if (oggiD >= inizio.toISOString().slice(0, 10) && oggiD <= fine) attivi.push({ ...e, blocca: regola.blocca, tipi: regola.tipi, avviso: regola.avviso });
    }
    for (const p of r.periodi || []) if (oggiD >= p.dal && oggiD <= p.al) attivi.push({ ...p, blocca: p.blocca || regola.blocca, tipi: p.tipi || regola.tipi });
    return attivi;
  }
  function bloccata(r, d) {
    for (const b of blocchi()) {
      if (!(b.tipi || []).includes(d ? d.tipo : 'voto')) continue;
      const bt = b.territorio || {}; const rt = r.territorio || {};
      const stesso = !bt.tipo || (bt.tipo === 'Italia' && rt.tipo === 'Italia') || (bt.codice === 'FVG' && r._area === 'fvg') || (bt.tipo === 'comune' && rt.tipo === 'comune' && (bt.nome || '').toLowerCase() === (rt.nome || '').toLowerCase());
      const stessaEl = !b.elezione || !d || !d.elezione || b.elezione === d.elezione;
      if (stesso && stessaEl) return b;
    }
    return null;
  }

  // ----------------------------------------------------------------------------------------------- viste
  function daHash() {
    const h = new URLSearchParams(location.hash.replace(/^#/, ''));
    S.vista = h.get('v') || 'panoramica'; S.p = {}; for (const [k, v] of h) if (k !== 'v') S.p[k] = v;
  }
  function vai(vista, p) {
    S.vista = vista; S.p = p || {};
    const h = new URLSearchParams({ v: vista, ...S.p });
    history.replaceState(null, '', '#' + h.toString());
    mostra();
  }
  function mostra() {
    $$('#schede button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.vista === (S.vista === 'istituto' ? 'istituti' : S.vista))));
    const v = $('#vista');
    const f = { panoramica: vPanoramica, italia: () => vTerritorio('italia'), fvg: () => vTerritorio('fvg'), istituti: vIstituti, istituto: vIstituto, percezioni: vPercezioni, archivio: vArchivio, gestione: vGestione }[S.vista] || vPanoramica;
    v.innerHTML = '';
    try { f(v); } catch (e) { v.innerHTML = `<p class="errore">Errore nella vista: ${esc(e.message)}</p>`; console.error(e); }
    v.querySelectorAll('[data-scheda]').forEach(el => el.addEventListener('click', ev => { ev.preventDefault(); apriScheda(el.dataset.scheda); }));
    v.querySelectorAll('[data-vai]').forEach(el => el.addEventListener('click', ev => { ev.preventDefault(); const [vista, q] = el.dataset.vai.split('?'); vai(vista, Object.fromEntries(new URLSearchParams(q || ''))); }));
  }
  $$('#schede button').forEach(b => b.addEventListener('click', () => vai(b.dataset.vista)));
  window.addEventListener('hashchange', () => { daHash(); mostra(); });

  const badgeStato = s => { const [t, c] = STATI[s] || [s, 'b-grigio']; return `<span class="badge ${c}">${esc(t)}</span>`; };
  const badgeTerr = r => { const t = r.territorio || {}; return t.tipo === 'Italia' ? '' : `<span class="badge ${r._area === 'fvg' ? 'b-fvg' : 'b-grigio'}">${esc(t.nome || t.tipo)}</span>`; };
  function voceRil(r) {
    const d0 = (r.domande || []).find(d => d.tipo === 'voto' && d.risposte && d.risposte.some(x => x.valore != null));
    const sintesi = d0 ? d0.risposte.filter(x => x.valore != null).slice(0, 6).map(x => `${esc(nomeSogg(x.soggetto) || x.testo)} ${fmtN(x.valore)}`).join(' · ') : (r.domande && r.domande.length ? `${r.domande.length} ${r.domande.length === 1 ? 'domanda' : 'domande'}` : 'solo scheda e documenti');
    return `<li class="voce"><div><h3><button type="button" data-scheda="${esc(r.id)}">${esc(r.titolo || 'Rilevazione')}</button></h3>
      <div class="meta">${esc(r._ist)}${r.committente ? ' per ' + esc(r.committente) : ''}${r.editore && r.editore !== r.committente ? ' · ' + esc(r.editore) : ''} · interviste ${esc(periodo(r))}${r.campione ? ' · campione ' + fmtN(r.campione, 0) : ''}</div>
      <div class="meta">${sintesi}</div>
      <div class="riga-badge">${badgeStato(r.stato)}${badgeTerr(r)}${r.elezione ? `<span class="badge b-grigio">${esc(ELEZ[r.elezione] || r.elezione)}</span>` : ''}${r.livello === 'secondaria' ? '' : '<span class="badge b-grigio">fonte primaria</span>'}</div></div>
      <div class="lato"><b>${fmtDbreve(r._data)}</b><span>${esc((S.a.fonti[r.fonte] || {}).nome || r.fonte)}</span></div></li>`;
  }

  // Panoramica
  function vPanoramica(v) {
    const R = S.R, inG = R.filter(r => IN_GRAFICO.has(r.stato)), coda = Object.values(S.a.coda || {}).filter(c => c.stato !== 'chiusa');
    const date = R.map(r => r._data).filter(Boolean).sort();
    const perAnno = {}; for (const r of R) if (r._data) { const a = r._data.slice(0, 4); perAnno[a] = perAnno[a] || { tot: 0, g: 0 }; perAnno[a].tot++; if (IN_GRAFICO.has(r.stato)) perAnno[a].g++; }
    const anni = Object.keys(perAnno).sort();
    const fonti = Object.values(S.a.fonti || {});
    const b = blocchi();
    v.innerHTML = `
      ${S.restr && S.restr.mostraAvvisoGenerale ? `<p class="nota" style="margin:0 0 10px">${esc(S.restr.avvisoGenerale)}</p>` : ''}
      ${b.length ? `<div class="avviso-blocco"><strong>Periodo di silenzio attivo.</strong> ${b.map(x => esc(x.nome)).join('; ')}. ${esc(b[0].avviso || '')}</div>` : ''}
      <section class="riquadro"><h2>Copertura dell'archivio</h2>
        <div class="tot sei">
          <div><b>${fmtN(R.length)}</b><span>rilevazioni registrate</span></div>
          <div><b>${fmtN(inG.length)}</b><span>con valori nei grafici</span></div>
          <div><b>${fmtN(coda.length)}</b><span>in coda «da verificare»</span></div>
          <div><b>${fmtN(Object.keys(S.a.istituti || {}).length)}</b><span>istituti</span></div>
          <div><b>${date.length ? date[0].slice(0, 4) + '–' + date[date.length - 1].slice(0, 4) : '–'}</b><span>periodo coperto</span></div>
          <div><b>${fmtN(R.filter(r => r._area === 'fvg').length)}</b><span>sul Friuli Venezia Giulia</span></div>
        </div>
        <div class="grafico-box">${barreAnni(anni, perAnno)}</div>
        <p class="spiega">La copertura dipende dalle fonti raggiungibili: il portale ufficiale dei sondaggi non risponde dal computer che esegue gli aggiornamenti (vedi Gestione › Fonti), quindi i documenti originali recenti arrivano dagli istituti, dalle ripubblicazioni e dai caricamenti manuali. L'archivio non contiene «tutti» i sondaggi: contiene quelli documentati qui sotto.</p>
      </section>
      <section class="riquadro"><h2>Stato degli aggiornamenti</h2>
        <dl class="dati">
          <dt>Ultimo tentativo</dt><dd>${fmtDT(S.a.ultimoTentativo)}</dd>
          <dt>Ultimo aggiornamento riuscito</dt><dd>${fmtDT(S.a.ultimoRiuscito)}</dd>
          <dt>Ultima rilevazione disponibile</dt><dd>${fmtD(S.a.ultimaRilevazione)}</dd>
          <dt>Prossimo aggiornamento</dt><dd>ogni giorno alle 6 (ora di Roma), dal flusso GitHub Actions «Osservatorio sondaggi»; avvio manuale da Gestione</dd>
        </dl>
        <h3>Fonti</h3>
        <div class="scorri"><table class="tab"><thead><tr><th>Fonte</th><th>Livello</th><th>Stato</th><th class="n">Rilevazioni</th><th>Ultimo giro riuscito</th><th>Copertura</th></tr></thead><tbody>
          ${fonti.map(f => { const st = (S.a.statoFonti || {})[f.id] || {}; const n = R.filter(r => r.fonte === f.id).length; return `<tr><td><b>${esc(f.nome)}</b>${f.url ? `<br><a href="${esc(f.url)}" target="_blank" rel="noopener" class="nota-l">${esc(f.url.replace(/^https?:\/\//, '').slice(0, 50))}</a>` : ''}</td><td>${esc(f.livello || '')}</td><td>${f.attiva ? (st.errore ? '<span class="badge b-coda">attiva, con errori</span>' : '<span class="badge b-ok">attiva</span>') : '<span class="badge b-no">non attiva</span>'}${f.tipo === 'non_raggiungibile' ? '<br><span class="nota-l">non raggiungibile</span>' : ''}</td><td class="n">${fmtN(n)}</td><td>${fmtDT(st.ultimoRiuscito)}</td><td class="nota-l">${esc(f.copertura || '')}${f.accesso ? '<br>' + esc(f.accesso) : ''}</td></tr>`; }).join('')}
        </tbody></table></div>
      </section>
      <section class="riquadro"><h2>Ultimi sondaggi registrati</h2>
        <ul class="elenco">${R.slice(0, 15).map(voceRil).join('') || '<li class="vuoto">Nessuna rilevazione in archivio.</li>'}</ul>
        <p class="azioni"><button type="button" class="btn btn-secondario" data-vai="archivio">Vai all'archivio completo</button></p>
      </section>`;
  }
  function barreAnni(anni, perAnno) {
    if (!anni.length) return '<p class="vuoto">Nessun dato per anno.</p>';
    const W = 860, H = 170, m = { t: 14, r: 10, b: 28, l: 36 }; const max = Math.max(...anni.map(a => perAnno[a].tot)); const bw = (W - m.l - m.r) / anni.length;
    const y = v => m.t + (H - m.t - m.b) * (1 - v / max);
    return `<p class="titolo-g">Rilevazioni per anno</p><p class="sotto-g">Barre piene: con valori nei grafici; barre chiare: tutte le registrate (anche solo scheda o in coda).</p><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Rilevazioni per anno">
      ${[0, 0.5, 1].map(f => `<line x1="${m.l}" x2="${W - m.r}" y1="${y(max * f)}" y2="${y(max * f)}" stroke="#E4DDCD"/><text x="${m.l - 6}" y="${y(max * f) + 4}" font-size="10" text-anchor="end" fill="#52565E">${Math.round(max * f)}</text>`).join('')}
      ${anni.map((a, i) => `<g><rect x="${m.l + i * bw + 2}" y="${y(perAnno[a].tot)}" width="${Math.max(2, bw - 4)}" height="${y(0) - y(perAnno[a].tot)}" fill="#CFE0F0" rx="2"/><rect x="${m.l + i * bw + 2}" y="${y(perAnno[a].g)}" width="${Math.max(2, bw - 4)}" height="${y(0) - y(perAnno[a].g)}" fill="#0E4273" rx="2"/><title>${a}: ${perAnno[a].tot} registrate, ${perAnno[a].g} nei grafici</title>${anni.length <= 30 || i % 2 === 0 ? `<text x="${m.l + i * bw + bw / 2}" y="${H - 10}" font-size="10" text-anchor="middle" fill="#52565E">${a}</text>` : ''}</g>`).join('')}
    </svg>`;
  }

  // Territorio (Italia, FVG) e istituto: intenzioni di voto + percezioni
  function filtroBase(ar, ist) {
    return S.R.filter(r => (ar ? r._area === ar : true) && (!ist || r.istituto === ist));
  }
  function vTerritorio(ar) {
    const v = $('#vista'); const R = filtroBase(ar);
    const ist = S.p.ist || ''; const inG = R.filter(r => IN_GRAFICO.has(r.stato) && r.principale !== false);
    const istituti = {}; for (const r of inG) if (r.istituto) istituti[r.istituto] = (istituti[r.istituto] || 0) + 1;
    const titolo = ar === 'fvg' ? 'Friuli Venezia Giulia' : 'Italia';
    v.innerHTML = `<section class="riquadro"><h2>${titolo}: intenzioni di voto per istituto</h2>
      <p class="nota">${ar === 'fvg' ? 'Solo rilevazioni sull\'elettorato o sulla popolazione regionale e locale (comuni del Friuli Venezia Giulia) dichiarate dalla fonte. I dati nazionali e del Nord Est non sono attribuiti alla regione.' : 'Rilevazioni su popolazione o elettorato nazionale.'} Ogni grafico mostra un solo istituto: nessuna media fra istituti. Le variazioni sono in punti percentuali rispetto alla rilevazione comparabile precedente dello stesso istituto.</p>
      <div class="filtri tre" style="margin-top:10px">
        <div><label class="etichetta" for="f-ist">Istituto</label><select class="campo" id="f-ist">${Object.keys(istituti).length ? '' : '<option value="">Nessun istituto con valori</option>'}${Object.entries(istituti).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<option value="${esc(k)}" ${k === ist ? 'selected' : ''}>${esc(S.a.istituti[k] ? S.a.istituti[k].nome : k)} (${n})</option>`).join('')}</select></div>
        <div><label class="etichetta" for="f-el">Tipo di elezione</label><select class="campo" id="f-el"></select></div>
        <div><label class="etichetta" for="f-liv">Livello</label><select class="campo" id="f-liv"><option value="partiti">Partiti e liste</option><option value="coalizioni">Coalizioni</option></select></div>
      </div>
      <div id="blocco-voto"></div>
    </section>
    <section class="riquadro"><h2>Percezioni e opinioni (${titolo})</h2><div id="blocco-perc"></div></section>
    <section class="riquadro"><h2>Tutte le rilevazioni (${titolo})</h2><p class="nota">${fmtN(R.length)} registrate, ${fmtN(inG.length)} con valori nei grafici.</p><ul class="elenco">${R.slice(0, 12).map(voceRil).join('') || '<li class="vuoto">Nessuna rilevazione per questo territorio.</li>'}</ul><p class="azioni"><button type="button" class="btn btn-secondario" data-vai="archivio?area=${ar}">Apri l'archivio filtrato</button></p></section>`;
    const sel = $('#f-ist'); if (!ist && sel.value) S.p.ist = sel.value;
    const agg = () => { S.p.ist = sel.value; S.p.el = $('#f-el').value; S.p.liv = $('#f-liv').value; history.replaceState(null, '', '#' + new URLSearchParams({ v: S.vista, ...S.p })); disegnaVoto($('#blocco-voto'), filtroBase(ar, S.p.ist), S.p); };
    const popolaEl = () => { const el = $('#f-el'); const ril = filtroBase(ar, sel.value); const tipi = {}; for (const r of ril) for (const d of r.domande || []) if (d.tipo === 'voto' && IN_GRAFICO.has(r.stato)) tipi[d.elezione || r.elezione || 'politiche'] = (tipi[d.elezione || r.elezione || 'politiche'] || 0) + 1; el.innerHTML = Object.entries(tipi).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<option value="${k}" ${k === S.p.el ? 'selected' : ''}>${esc(ELEZ[k] || k)} (${n})</option>`).join('') || '<option value="">–</option>'; };
    popolaEl(); if (S.p.liv) $('#f-liv').value = S.p.liv;
    sel.addEventListener('change', () => { popolaEl(); agg(); }); $('#f-el').addEventListener('change', agg); $('#f-liv').addEventListener('change', agg);
    agg();
    disegnaPercezioni($('#blocco-perc'), R.filter(r => IN_GRAFICO.has(r.stato)), S.p.ist);
  }

  // serie di voto: punti per soggetto da una lista di rilevazioni di UN istituto
  function serieVoto(ril, el, liv) {
    const punti = [];
    for (const r of ril) {
      if (!IN_GRAFICO.has(r.stato) || r.principale === false || !r._data) continue;
      for (let i = 0; i < (r.domande || []).length; i++) {
        const d = r.domande[i];
        if (d.tipo !== 'voto' || (d.elezione || r.elezione || 'politiche') !== el || (d.livello || 'partiti') !== liv || d.turno) continue;
        if (!d.risposte || !d.risposte.some(x => x.valore != null)) continue;
        punti.push({ r, d, i, data: r._data });
      }
    }
    punti.sort((a, b) => a.data.localeCompare(b.data) || (a.r.pubblicato || '').localeCompare(b.r.pubblicato || ''));
    const perS = {};
    for (const p of punti) for (const x of p.d.risposte) {
      if (x.valore == null) continue;
      const id = x.soggetto || ('t:' + (x.testo || '').toLowerCase());
      (perS[id] = perS[id] || []).push({ data: p.data, v: x.valore, r: p.r, d: p.d, criterio: p.r.criterioData });
    }
    return { punti, perS };
  }
  function disegnaVoto(box, ril, p) {
    const el = p.el || 'politiche', liv = p.liv || 'partiti';
    if (!p.ist) { box.innerHTML = '<p class="vuoto">Nessun istituto con intenzioni di voto per questo territorio. Le rilevazioni senza valori o in coda non entrano nei grafici.</p>'; return; }
    const { punti, perS } = serieVoto(ril, el, liv);
    const istN = S.a.istituti[p.ist] ? S.a.istituti[p.ist].nome : p.ist;
    if (!punti.length) { box.innerHTML = `<p class="vuoto">Nessuna rilevazione di ${esc(istN)} con valori per «${esc(ELEZ[el] || el)}» a livello ${liv}.</p>`; return; }
    const bl = bloccata(punti[0].r, punti[0].d);
    if (bl && (bl.blocca || []).includes('grafici')) { box.innerHTML = `<div class="avviso-blocco"><strong>Grafico non disponibile.</strong> ${esc(bl.avviso || 'Periodo di silenzio dei sondaggi per questa consultazione.')} (${esc(bl.nome || '')}) I dati restano conservati nell'archivio.</div>`; return; }
    const ultimo = punti[punti.length - 1];
    const sub = `${istN} · ${ELEZ[el] || el} · ${punti.length} rilevazioni dal ${fmtD(punti[0].data)} al ${fmtD(ultimo.data)} · data di riferimento: fine interviste${punti.some(x => x.r.criterioData === 'pubblicazione') ? ' (per alcune rilevazioni la pubblicazione, segnalato nei punti)' : ''}`;
    grafico(box, { titolo: `Intenzioni di voto: ${istN}`, sotto: sub, perS, fonte: `Fonte: ${istN}; archivio Osservatorio sondaggi, Atlante FVG`, unita: '%', id: 'voto' });
    // tabella dell'ultima rilevazione con variazioni rispetto alla precedente comparabile
    const prec = punti.length > 1 ? punti[punti.length - 2] : null;
    const righe = ultimo.d.risposte.filter(x => x.valore != null).map(x => { const id = x.soggetto || ('t:' + (x.testo || '').toLowerCase()); const pv = prec ? (prec.d.risposte.find(y => (y.soggetto || ('t:' + (y.testo || '').toLowerCase())) === id) || {}).valore : null; return { nome: nomeSogg(id) || x.testo, v: x.valore, var: pv != null ? Math.round((x.valore - pv) * 10) / 10 : (x.variazione != null ? x.variazione : null), dich: pv == null && x.variazione != null }; });
    box.insertAdjacentHTML('beforeend', `<h3>Ultima rilevazione: ${esc(periodo(ultimo.r))}${ultimo.r.campione ? ', campione ' + fmtN(ultimo.r.campione, 0) : ''} <button type="button" class="btn btn-secondario mini" data-scheda="${esc(ultimo.r.id)}">Scheda</button></h3>
      <div class="scorri" style="max-height:none"><table class="tab"><thead><tr><th>Soggetto</th><th class="n">Valore %</th><th class="n">Variazione (p.p.)</th><th>Rispetto a</th></tr></thead><tbody>
      ${righe.map(x => `<tr><td>${esc(x.nome)}</td><td class="n">${fmtN(x.v)}</td><td class="n">${x.var == null ? '–' : fmtPP(x.var)}</td><td class="nota-l">${x.var == null ? 'nessuna rilevazione comparabile precedente' : x.dich ? 'variazione dichiarata dalla fonte' : esc(prec ? periodo(prec.r) : '')}</td></tr>`).join('')}
      </tbody></table></div>
      ${ultimo.d.indecisi != null ? `<p class="nota">Indecisi o non rispondenti dichiarati: ${fmtN(ultimo.d.indecisi)}%${ultimo.d.astenuti != null ? '; astenuti: ' + fmtN(ultimo.d.astenuti) + '%' : ''}. Denominatore dei valori: ${esc(ultimo.d.denominatore || 'voti validi')}.</p>` : `<p class="nota">Denominatore dei valori: ${esc(ultimo.d.denominatore === 'totale' ? 'totale degli intervistati' : 'voti validi (indecisi e astenuti esclusi), come pubblicato dalla fonte')}.</p>`}`);
    box.querySelectorAll('[data-scheda]').forEach(e => e.addEventListener('click', () => apriScheda(e.dataset.scheda)));
  }

  // grafico temporale generico: perS = {id: [{data, v, r, d}]}
  function grafico(box, o) {
    const ids = Object.keys(o.perS).sort((a, b) => (o.perS[b][o.perS[b].length - 1].v) - (o.perS[a][o.perS[a].length - 1].v));
    const stato = { on: new Set(ids.slice(0, 14)), da: null, a: null, sel: 'tutto' };
    const tutte = ids.flatMap(i => o.perS[i].map(p => p.data)).sort();
    const fine = tutte[tutte.length - 1], inizio = tutte[0];
    const W = 860, H = 380, m = { t: 44, r: 16, b: 46, l: 40 };
    const wrap = document.createElement('div'); wrap.className = 'grafico-box'; box.innerHTML = ''; box.appendChild(wrap);
    const intervalli = [['6m', '6 mesi', 183], ['1a', '1 anno', 366], ['3a', '3 anni', 1096], ['tutto', 'Tutto', 0]];
    function render() {
      let da = stato.da, a = stato.a;
      if (!da) { const g = intervalli.find(x => x[0] === stato.sel); da = g && g[2] ? new Date(new Date(fine) - g[2] * 86400000).toISOString().slice(0, 10) : inizio; }
      if (!a) a = fine;
      if (da > a) [da, a] = [a, da];
      const t0 = new Date(da).getTime(), t1 = Math.max(new Date(a).getTime(), t0 + 86400000 * 7);
      const vis = {}; let maxV = 0, minV = Infinity;
      for (const id of ids) if (stato.on.has(id)) { vis[id] = o.perS[id].filter(p => p.data >= da && p.data <= a); for (const p of vis[id]) { maxV = Math.max(maxV, p.v); minV = Math.min(minV, p.v); } }
      const unoSolo = Object.values(vis).every(l => l.length <= 1);
      if (!isFinite(minV)) { minV = 0; maxV = 10; }
      const barre = o.unita === '%' && !o.saldo; const yMin = barre ? 0 : Math.floor(Math.min(minV, 0) / 5) * 5, yMax = Math.ceil((maxV + 1) / 5) * 5 || 5;
      const x = t => m.l + (W - m.l - m.r) * (new Date(t).getTime() - t0) / (t1 - t0), y = v => m.t + (H - m.t - m.b) * (1 - (v - yMin) / (yMax - yMin));
      const tick = []; const passo = (yMax - yMin) <= 20 ? 5 : (yMax - yMin) <= 50 ? 10 : 20; for (let v = yMin; v <= yMax; v += passo) tick.push(v);
      const mesi = []; const d0 = new Date(t0); d0.setDate(1); const span = (t1 - t0) / 86400000; const ogni = span > 365 * 6 ? 24 : span > 365 * 2.5 ? 12 : span > 400 ? 6 : span > 150 ? 2 : 1;
      for (let d = new Date(d0); d.getTime() <= t1; d.setMonth(d.getMonth() + 1)) if (d.getMonth() % ogni === 0 && d.getTime() >= t0) mesi.push(new Date(d));
      let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.titolo)}" id="g-${o.id}"><rect width="${W}" height="${H}" fill="#fff"/>
        <text x="${m.l}" y="20" font-size="15" font-weight="600" fill="#0B3359" font-family="Source Serif 4, Georgia, serif">${esc(o.titolo)}</text>
        <text x="${m.l}" y="36" font-size="10.5" fill="#52565E">${esc(o.sotto.length > 150 ? o.sotto.slice(0, 147) + '…' : o.sotto)}</text>
        ${tick.map(v => `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${v === 0 ? '#B9B2A2' : '#EDE8DC'}"/><text x="${m.l - 6}" y="${y(v) + 3.5}" font-size="10" text-anchor="end" fill="#52565E">${v}${o.unita === '%' ? '%' : ''}</text>`).join('')}
        ${mesi.map(d => `<line x1="${x(d)}" x2="${x(d)}" y1="${m.t}" y2="${H - m.b}" stroke="#F3EFE6"/><text x="${x(d)}" y="${H - m.b + 14}" font-size="10" text-anchor="middle" fill="#52565E">${d.toLocaleDateString('it-IT', { month: 'short', year: ogni >= 12 || d.getMonth() === 0 ? 'numeric' : undefined })}</text>`).join('')}
        <text x="${W - m.r}" y="${H - 6}" font-size="9.5" text-anchor="end" fill="#52565E">${esc(o.fonte)}</text>`;
      const buchi = [];
      ids.forEach((id, k) => {
        if (!vis[id]) return;
        const pts = vis[id]; const col = colSogg(id, ids.indexOf(id));
        let path = '';
        for (let i = 0; i < pts.length; i++) {
          const p = pts[i]; const salto = i > 0 && giorni(pts[i - 1].data, p.data) > 180;
          if (salto) buchi.push([pts[i - 1].data, p.data]);
          path += (i === 0 || salto ? 'M' : 'L') + x(p.data).toFixed(1) + ' ' + y(p.v).toFixed(1) + ' ';
        }
        svg += `<path d="${path}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" opacity=".9"/>`;
        svg += pts.map((p, i) => `<circle class="punto-g" data-id="${esc(id)}" data-i="${i}" cx="${x(p.data).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="${pts.length > 80 ? 2.2 : 3.4}" fill="${p.criterio === 'pubblicazione' ? '#fff' : col}" stroke="${col}" stroke-width="1.6"/>`).join('');
        if (pts.length) { const u = pts[pts.length - 1]; svg += `<text x="${Math.min(x(u.data) + 5, W - m.r - 30)}" y="${y(u.v) + 3.5}" font-size="10" fill="${col}" font-weight="600">${esc((nomeSogg(id) || '').slice(0, 22))} ${fmtN(u.v)}</text>`; }
      });
      const uniq = buchi.filter((b, i) => buchi.findIndex(c => c[0] === b[0] && c[1] === b[1]) === i).slice(0, 6);
      for (const [a1, b1] of uniq) svg += `<rect x="${x(a1)}" y="${m.t}" width="${Math.max(0, x(b1) - x(a1))}" height="${H - m.t - m.b}" fill="#F7D678" opacity=".16"/><title>Nessuna rilevazione fra ${fmtD(a1)} e ${fmtD(b1)}</title>`;
      svg += `<rect id="zona-${o.id}" x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b}" fill="transparent"/></svg>`;
      wrap.innerHTML = `${svg}
        <div class="legenda" role="group" aria-label="Soggetti in grafico">${ids.map((id, k) => `<button type="button" data-id="${esc(id)}" aria-pressed="${stato.on.has(id)}"><i style="background:${colSogg(id, k)}"></i>${esc(nomeSogg(id))}</button>`).join('')}</div>
        <div class="intervalli" role="group" aria-label="Intervallo"><span class="nota-l">Intervallo:</span>${intervalli.map(([k, et]) => `<button type="button" data-int="${k}" aria-pressed="${stato.sel === k && !stato.da}">${et}</button>`).join('')}
          <label class="nota-l">dal <input type="date" id="int-da-${o.id}" value="${da}"></label><label class="nota-l">al <input type="date" id="int-a-${o.id}" value="${a}"></label>
          <span class="nota-l">Trascina sul grafico per ingrandire; doppio tocco per ripristinare.</span></div>
        ${unoSolo ? '<p class="nota">Una sola osservazione nell\'intervallo: il punto non descrive un andamento.</p>' : ''}
        ${uniq.length ? `<p class="nota">Fasce gialle: oltre sei mesi senza rilevazioni (${uniq.map(([a1, b1]) => fmtDbreve(a1) + ' → ' + fmtDbreve(b1)).join('; ')}). Punti vuoti: data di pubblicazione usata al posto della fine delle interviste.</p>` : '<p class="nota">Punti vuoti: data di pubblicazione usata al posto della fine delle interviste. Nessuna interpolazione: le linee uniscono solo rilevazioni consecutive dello stesso istituto.</p>'}
        <div class="azioni"><button type="button" class="btn btn-secondario mini" data-exp="svg">Scarica grafico SVG</button><button type="button" class="btn btn-secondario mini" data-exp="png">Scarica grafico PNG</button><button type="button" class="btn btn-secondario mini" data-exp="csv">Dati CSV</button><button type="button" class="btn btn-secondario mini" data-exp="xlsx">Dati Excel</button></div>
        <details style="margin-top:8px"><summary class="nota-l" style="cursor:pointer;min-height:36px;display:flex;align-items:center">Tabella dei valori (accessibile)</summary><div class="scorri"><table class="tab"><thead><tr><th>Data</th><th>Soggetto</th><th class="n">Valore</th><th>Interviste</th><th class="n">Campione</th><th>Rilevazione</th></tr></thead><tbody>
        ${ids.filter(i => vis[i]).flatMap(id => vis[id].map(p => `<tr><td>${fmtDbreve(p.data)}</td><td>${esc(nomeSogg(id))}</td><td class="n">${fmtN(p.v)}</td><td class="nota-l">${esc(periodo(p.r))}</td><td class="n">${p.r.campione ? fmtN(p.r.campione, 0) : '–'}</td><td><button type="button" class="btn btn-secondario mini" data-scheda="${esc(p.r.id)}">Scheda</button></td></tr>`)).join('')}
        </tbody></table></div></details>`;
      // interazioni
      wrap.querySelectorAll('.legenda button').forEach(b => b.addEventListener('click', () => { const id = b.dataset.id; if (stato.on.has(id)) stato.on.delete(id); else stato.on.add(id); render(); }));
      wrap.querySelectorAll('[data-int]').forEach(b => b.addEventListener('click', () => { stato.sel = b.dataset.int; stato.da = stato.a = null; render(); }));
      $(`#int-da-${o.id}`, wrap).addEventListener('change', e => { stato.da = e.target.value; stato.a = stato.a || a; render(); });
      $(`#int-a-${o.id}`, wrap).addEventListener('change', e => { stato.a = e.target.value; stato.da = stato.da || da; render(); });
      wrap.querySelectorAll('[data-scheda]').forEach(e => e.addEventListener('click', () => apriScheda(e.dataset.scheda)));
      wrap.querySelectorAll('[data-exp]').forEach(b => b.addEventListener('click', () => esporta(b.dataset.exp, wrap.querySelector('svg'), o, vis, ids)));
      const svgEl = wrap.querySelector('svg'); const tip = document.createElement('div'); tip.className = 'suggerimento'; tip.hidden = true; wrap.appendChild(tip);
      const posiziona = (ev, html) => { const r = wrap.getBoundingClientRect(); tip.innerHTML = html; tip.hidden = false; const tx = Math.min(ev.clientX - r.left + 12, r.width - 300), ty = ev.clientY - r.top + 12; tip.style.left = Math.max(0, tx) + 'px'; tip.style.top = ty + 'px'; };
      svgEl.querySelectorAll('.punto-g').forEach(c => {
        const mostraTip = ev => { const p = vis[c.dataset.id][+c.dataset.i]; const prev = vis[c.dataset.id][+c.dataset.i - 1]; posiziona(ev, `<b>${esc(nomeSogg(c.dataset.id))}: ${fmtN(p.v)}${o.unita === '%' ? '%' : ''}</b>${prev ? ` (${fmtPP(Math.round((p.v - prev.v) * 10) / 10)} p.p. sulla precedente)` : ''}<br>${esc(p.r._ist)} · interviste ${esc(periodo(p.r))}${p.r.campione ? `<br>campione ${fmtN(p.r.campione, 0)}` : ''}${p.criterio === 'pubblicazione' ? '<br><i>data di pubblicazione (fine interviste non nota)</i>' : ''}<br><u>apri la scheda</u>`); };
        c.addEventListener('pointerenter', mostraTip); c.addEventListener('pointermove', mostraTip); c.addEventListener('pointerleave', () => { tip.hidden = true; });
        c.addEventListener('click', () => apriScheda(vis[c.dataset.id][+c.dataset.i].r.id));
      });
      // zoom per trascinamento
      const zona = svgEl.querySelector(`#zona-${o.id}`); let drag = null; const scalaX = () => svgEl.getBoundingClientRect().width / W;
      const tDa = px => { const r = svgEl.getBoundingClientRect(); const xs = (px - r.left) / scalaX(); return new Date(t0 + (t1 - t0) * (xs - m.l) / (W - m.l - m.r)); };
      zona.addEventListener('pointerdown', ev => { drag = { x0: ev.clientX, rect: null }; zona.setPointerCapture(ev.pointerId); const rr = document.createElementNS('http://www.w3.org/2000/svg', 'rect'); rr.setAttribute('y', m.t); rr.setAttribute('height', H - m.t - m.b); rr.setAttribute('fill', '#155E9E'); rr.setAttribute('opacity', '.15'); svgEl.appendChild(rr); drag.rect = rr; });
      zona.addEventListener('pointermove', ev => { if (!drag) return; const r = svgEl.getBoundingClientRect(); const a0 = (Math.min(drag.x0, ev.clientX) - r.left) / scalaX(), a1 = (Math.max(drag.x0, ev.clientX) - r.left) / scalaX(); drag.rect.setAttribute('x', a0); drag.rect.setAttribute('width', Math.max(0, a1 - a0)); });
      zona.addEventListener('pointerup', ev => { if (!drag) return; const dx = Math.abs(ev.clientX - drag.x0); drag.rect.remove(); if (dx > 12) { const d1 = tDa(Math.min(drag.x0, ev.clientX)), d2 = tDa(Math.max(drag.x0, ev.clientX)); stato.da = d1.toISOString().slice(0, 10); stato.a = d2.toISOString().slice(0, 10); render(); } drag = null; });
      zona.addEventListener('dblclick', () => { stato.da = stato.a = null; stato.sel = 'tutto'; render(); });
    }
    render();
  }

  // Percezioni: serie non di voto per territorio/istituto
  function disegnaPercezioni(box, ril, ist) {
    const serie = {};
    for (const r of ril) {
      if (r.principale === false || !r._data || (ist && r.istituto !== ist)) continue;
      (r.domande || []).forEach((d, i) => {
        if (d.tipo === 'voto' || !d.risposte || !d.risposte.some(x => x.valore != null)) return;
        const k = [r.istituto, d.tipo, (d.testo || '').toLowerCase().replace(/\(.*?\)/g, '').replace(/[^a-zà-ü0-9]+/g, ' ').trim().slice(0, 80), d.unita || '%', d.denominatore || ''].join('|');
        const s = serie[k] = serie[k] || { k, ist: r.istituto, tipo: d.tipo, testo: d.testo, unita: d.unita || '%', punti: [] };
        s.punti.push({ r, d, i, data: r._data });
      });
    }
    const lista = Object.values(serie).sort((a, b) => b.punti.length - a.punti.length);
    if (!lista.length) { box.innerHTML = '<p class="vuoto">Nessuna domanda di opinione con valori per questa selezione.</p>'; return; }
    const perTipo = {}; for (const s of lista) (perTipo[s.tipo] = perTipo[s.tipo] || []).push(s);
    box.innerHTML = `<p class="nota">Le serie uniscono solo domande dello stesso istituto con testo, unità e denominatore uguali; due domande sullo stesso argomento ma formulate in modo diverso restano separate. Con una sola osservazione si mostra un grafico a barre.</p>
      <div class="filtri tre" style="margin-top:8px"><div><label class="etichetta" for="p-tipo">Argomento</label><select class="campo" id="p-tipo">${Object.keys(perTipo).map(t => `<option value="${t}" ${t === S.tipo ? 'selected' : ''}>${esc(TIPI[t] || t)} (${perTipo[t].length})</option>`).join('')}</select></div></div><div id="p-serie"></div>`;
    const sel = $('#p-tipo', box);
    const disegna = () => { const t = sel.value; S.tipo = t; const cont = $('#p-serie', box); cont.innerHTML = ''; for (const s of (perTipo[t] || []).slice(0, 12)) cont.appendChild(cartaSerie(s)); };
    sel.addEventListener('change', disegna); disegna();
  }
  function cartaSerie(s) {
    const div = document.createElement('div');
    const istN = S.a.istituti[s.ist] ? S.a.istituti[s.ist].nome : s.ist;
    const bl = bloccata(s.punti[0].r, s.punti[0].d);
    if (bl && (bl.blocca || []).includes('grafici')) { div.innerHTML = `<div class="avviso-blocco"><strong>${esc(s.testo)}</strong>: non mostrato. ${esc(bl.avviso || '')}</div>`; return div; }
    if (s.punti.length >= 2) {
      const perS = {}; for (const p of s.punti.sort((a, b) => a.data.localeCompare(b.data))) for (const x of p.d.risposte) if (x.valore != null) { const id = x.soggetto || ('t:' + (x.testo || '').toLowerCase()); (perS[id] = perS[id] || []).push({ data: p.data, v: x.valore, r: p.r, d: p.d, criterio: p.r.criterioData }); }
      grafico(div, { titolo: `${TIPI[s.tipo] || s.tipo}: ${s.testo}`.slice(0, 90), sotto: `${istN} · ${s.punti.length} rilevazioni · unità: ${s.unita === '%' ? 'percentuale' : s.unita}`, perS, fonte: `Fonte: ${istN}; Osservatorio sondaggi, Atlante FVG`, unita: s.unita, saldo: s.unita === 'saldo', id: 'p' + Math.random().toString(36).slice(2, 7) });
      div.insertAdjacentHTML('afterbegin', `<p class="nota" style="margin-top:12px"><b>Domanda originale:</b> ${esc(s.punti[0].d.testo)}</p>`);
    } else {
      const p = s.punti[0]; const risp = p.d.risposte.filter(x => x.valore != null); const max = Math.max(100, ...risp.map(x => x.valore));
      div.innerHTML = `<div class="grafico-box"><p class="titolo-g">${esc(TIPI[s.tipo] || s.tipo)}: ${esc(s.testo)}</p><p class="sotto-g">${esc(istN)} · ${esc(periodo(p.r))}${p.r.campione ? ' · campione ' + fmtN(p.r.campione, 0) : ''} · una sola osservazione · unità: ${s.unita === '%' ? 'percentuale' : esc(s.unita)}</p>
        <div class="barre">${risp.map(x => `<div class="barra"><span>${esc(nomeSogg(x.soggetto) || x.testo)}</span><div class="asta"><i style="width:${Math.max(0, Math.min(100, x.valore / max * 100))}%"></i></div><span class="v">${fmtN(x.valore)}${s.unita === '%' ? '%' : ''}</span></div>`).join('')}</div>
        <p class="nota" style="margin-top:8px"><b>Domanda originale:</b> ${esc(p.d.testo)} <button type="button" class="btn btn-secondario mini" data-scheda="${esc(p.r.id)}">Scheda</button></p></div>`;
      div.querySelector('[data-scheda]').addEventListener('click', e => apriScheda(e.target.dataset.scheda));
    }
    return div;
  }
  function vPercezioni(v) {
    const inG = S.R.filter(r => IN_GRAFICO.has(r.stato));
    v.innerHTML = `<section class="riquadro"><h2>Percezioni e opinioni</h2><p class="nota">Fiducia nei leader, nel Governo e nelle istituzioni; problemi prioritari; giudizi sull'economia; valutazioni sull'amministrazione e sui servizi; opinioni su temi e provvedimenti. Navigazione per argomento; filtro per territorio e istituto.</p>
      <div class="filtri tre" style="margin-top:8px"><div><label class="etichetta" for="pz-area">Territorio</label><select class="campo" id="pz-area"><option value="">Tutti</option><option value="italia">Italia</option><option value="fvg">Friuli Venezia Giulia</option><option value="altro">Altre aree (Nord Est, altre regioni)</option></select></div>
      <div><label class="etichetta" for="pz-ist">Istituto</label><select class="campo" id="pz-ist"><option value="">Tutti</option>${Object.entries(S.a.istituti).sort((a, b) => a[1].nome.localeCompare(b[1].nome)).map(([k, s]) => `<option value="${esc(k)}">${esc(s.nome)}</option>`).join('')}</select></div></div>
      <div id="pz-box"></div></section>`;
    const agg = () => { const ar = $('#pz-area').value, ist = $('#pz-ist').value; disegnaPercezioni($('#pz-box'), inG.filter(r => !ar || r._area === ar), ist); };
    $('#pz-area').addEventListener('change', agg); $('#pz-ist').addEventListener('change', agg); agg();
  }

  // Istituti
  function vIstituti(v) {
    const q = (S.p.q || '').toLowerCase();
    const lista = Object.entries(S.a.istituti || {}).map(([id, s]) => ({ id, ...s, n: (S.perIst[id] || []).length, g: (S.perIst[id] || []).filter(r => IN_GRAFICO.has(r.stato)).length, fvg: (S.perIst[id] || []).filter(r => r._area === 'fvg').length })).filter(s => !q || (s.nome + ' ' + (s.alias || []).join(' ')).toLowerCase().includes(q)).sort((a, b) => b.g - a.g || b.n - a.n);
    v.innerHTML = `<section class="riquadro"><h2>Istituti</h2><p class="nota">Il registro nasce dalle fonti lette: ogni istituto ha la sua pagina con i grafici delle intenzioni di voto e delle percezioni. Istituto realizzatore, committente ed editore sono distinti in ogni scheda.</p>
      <div class="cerca" style="margin-top:8px;max-width:28rem"><label class="etichetta" for="ist-q">Cerca un istituto</label><input class="campo" id="ist-q" type="search" value="${esc(S.p.q || '')}" placeholder="Nome o sigla"></div>
      <div class="griglia-istituti">${lista.map(s => `<button type="button" class="ist" data-vai="istituto?ist=${esc(s.id)}"><b>${esc(s.nome)}</b><span>${fmtN(s.n)} rilevazioni, ${fmtN(s.g)} nei grafici${s.fvg ? `, ${fmtN(s.fvg)} sul Friuli Venezia Giulia` : ''}${s.prima ? ` · ${s.prima.slice(0, 4)}–${(s.ultima || '').slice(0, 4)}` : ''}</span>${sparkline(s.id)}</button>`).join('') || '<p class="vuoto">Nessun istituto.</p>'}</div></section>`;
    $('#ist-q').addEventListener('input', e => { S.p.q = e.target.value; const g = $('.griglia-istituti'); const q2 = e.target.value.toLowerCase(); g.querySelectorAll('.ist').forEach(b => { b.hidden = q2 && !b.textContent.toLowerCase().includes(q2); }); });
  }
  function sparkline(ist) {
    const pts = (S.perIst[ist] || []).filter(r => IN_GRAFICO.has(r.stato) && r._data).map(r => r._data).sort();
    if (pts.length < 2) return '';
    const W = 220, H = 22; const t0 = new Date(pts[0]).getTime(), t1 = new Date(pts[pts.length - 1]).getTime() || t0 + 1;
    return `<svg class="sparkline" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true">${pts.map(p => `<line x1="${((new Date(p).getTime() - t0) / (t1 - t0) * (W - 2) + 1).toFixed(1)}" x2="${((new Date(p).getTime() - t0) / (t1 - t0) * (W - 2) + 1).toFixed(1)}" y1="4" y2="${H - 4}" stroke="#155E9E" stroke-width="1.2" opacity=".6"/>`).join('')}</svg>`;
  }
  function vIstituto(v) {
    const id = S.p.ist; const s = S.a.istituti[id]; if (!s) { v.innerHTML = '<p class="vuoto">Istituto non trovato.</p>'; return; }
    const R = S.perIst[id] || []; const inG = R.filter(r => IN_GRAFICO.has(r.stato));
    const aree = {}; for (const r of inG) aree[r._area] = (aree[r._area] || 0) + 1;
    v.innerHTML = `<section class="riquadro"><p class="nota"><button type="button" class="btn btn-secondario mini" data-vai="istituti">← Tutti gli istituti</button></p><h2>${esc(s.nome)}</h2>
      <p class="nota">${fmtN(R.length)} rilevazioni registrate (${fmtN(inG.length)} con valori) dal ${fmtD(s.prima)} al ${fmtD(s.ultima)}.${s.sito ? ` Sito: <a href="${esc(s.sito)}" target="_blank" rel="noopener">${esc(s.sito)}</a>.` : ''}${(s.alias || []).length ? ' Denominazioni incontrate: ' + s.alias.map(esc).join(', ') + '.' : ''} Fonti: ${(s.fonti || []).map(f => esc((S.a.fonti[f] || {}).nome || f)).join(', ')}.</p>
      <h3>Intenzioni di voto</h3>
      <div class="filtri tre"><div><label class="etichetta" for="i-area">Territorio</label><select class="campo" id="i-area">${Object.entries(aree).map(([a, n]) => `<option value="${a}">${a === 'italia' ? 'Italia' : a === 'fvg' ? 'Friuli Venezia Giulia' : 'Altre aree'} (${n})</option>`).join('') || '<option value="">–</option>'}</select></div>
        <div><label class="etichetta" for="i-el">Tipo di elezione</label><select class="campo" id="i-el"></select></div>
        <div><label class="etichetta" for="i-liv">Livello</label><select class="campo" id="i-liv"><option value="partiti">Partiti e liste</option><option value="coalizioni">Coalizioni</option></select></div></div>
      <div id="i-voto"></div>
      <h3>Percezioni e opinioni</h3><div id="i-perc"></div>
      <h3>Rilevazioni dell'istituto</h3><ul class="elenco">${R.slice(0, 20).map(voceRil).join('')}</ul><p class="azioni"><button type="button" class="btn btn-secondario" data-vai="archivio?ist=${esc(id)}">Tutte nell'archivio</button></p></section>`;
    const popolaEl = () => { const ar = $('#i-area').value; const tipi = {}; for (const r of inG) if (r._area === ar) for (const d of r.domande || []) if (d.tipo === 'voto') tipi[d.elezione || r.elezione || 'politiche'] = (tipi[d.elezione || r.elezione || 'politiche'] || 0) + 1; $('#i-el').innerHTML = Object.entries(tipi).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<option value="${k}">${esc(ELEZ[k] || k)} (${n})</option>`).join('') || '<option value="">–</option>'; };
    const agg = () => { const ar = $('#i-area').value; disegnaVoto($('#i-voto'), R.filter(r => r._area === ar), { ist: id, el: $('#i-el').value, liv: $('#i-liv').value }); };
    popolaEl(); $('#i-area').addEventListener('change', () => { popolaEl(); agg(); }); $('#i-el').addEventListener('change', agg); $('#i-liv').addEventListener('change', agg); agg();
    disegnaPercezioni($('#i-perc'), inG, id);
  }

  // Archivio
  function vArchivio(v) {
    const p = S.p;
    const fonti = Object.values(S.a.fonti || {});
    v.innerHTML = `<section class="riquadro"><h2>Archivio delle rilevazioni</h2>
      <div class="filtri sei">
        <div class="cerca"><label class="etichetta" for="a-q">Cerca</label><input class="campo" id="a-q" type="search" value="${esc(p.q || '')}" placeholder="Titolo, istituto, committente, domanda"></div>
        <div><label class="etichetta" for="a-ist">Istituto</label><select class="campo" id="a-ist"><option value="">Tutti</option>${Object.entries(S.a.istituti).sort((a, b) => a[1].nome.localeCompare(b[1].nome)).map(([k, s]) => `<option value="${esc(k)}" ${p.ist === k ? 'selected' : ''}>${esc(s.nome)}</option>`).join('')}</select></div>
        <div><label class="etichetta" for="a-area">Territorio</label><select class="campo" id="a-area"><option value="">Tutti</option><option value="italia" ${p.area === 'italia' ? 'selected' : ''}>Italia</option><option value="fvg" ${p.area === 'fvg' ? 'selected' : ''}>Friuli Venezia Giulia</option><option value="altro" ${p.area === 'altro' ? 'selected' : ''}>Altre aree</option></select></div>
        <div><label class="etichetta" for="a-el">Consultazione</label><select class="campo" id="a-el"><option value="">Tutte</option>${Object.entries(ELEZ).map(([k, n]) => `<option value="${k}" ${p.el === k ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
        <div><label class="etichetta" for="a-stato">Stato</label><select class="campo" id="a-stato"><option value="">Tutti</option>${Object.entries(STATI).map(([k, [n]]) => `<option value="${k}" ${p.stato === k ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
        <div><label class="etichetta" for="a-fonte">Fonte</label><select class="campo" id="a-fonte"><option value="">Tutte</option>${fonti.map(f => `<option value="${esc(f.id)}" ${p.fonte === f.id ? 'selected' : ''}>${esc(f.nome)}</option>`).join('')}</select></div>
      </div>
      <div class="filtri tre" style="margin-top:8px"><div><label class="etichetta" for="a-da">Dal</label><input class="campo" id="a-da" type="date" value="${esc(p.da || '')}"></div><div><label class="etichetta" for="a-a">Al</label><input class="campo" id="a-a" type="date" value="${esc(p.a || '')}"></div>
        <div><label class="etichetta" for="a-tipo">Tipo di domanda</label><select class="campo" id="a-tipo"><option value="">Tutte</option>${Object.entries(TIPI).map(([k, n]) => `<option value="${k}" ${p.tipo === k ? 'selected' : ''}>${n}</option>`).join('')}</select></div></div>
      <div class="azioni" id="a-azioni"></div><div id="a-tab"></div></section>`;
    const agg = () => { for (const [k, id] of [['q', 'a-q'], ['ist', 'a-ist'], ['area', 'a-area'], ['el', 'a-el'], ['stato', 'a-stato'], ['fonte', 'a-fonte'], ['da', 'a-da'], ['a', 'a-a'], ['tipo', 'a-tipo']]) { const val = $('#' + id).value; if (val) S.p[k] = val; else delete S.p[k]; } S.pagAr = 0; history.replaceState(null, '', '#' + new URLSearchParams({ v: 'archivio', ...S.p })); tabellaArchivio(); };
    ['a-q', 'a-ist', 'a-area', 'a-el', 'a-stato', 'a-fonte', 'a-da', 'a-a', 'a-tipo'].forEach(id => $('#' + id).addEventListener(id === 'a-q' ? 'input' : 'change', agg));
    tabellaArchivio();
  }
  function filtraArchivio() {
    const p = S.p; const q = (p.q || '').toLowerCase();
    return S.R.filter(r => (!p.ist || r.istituto === p.ist) && (!p.area || r._area === p.area) && (!p.el || r.elezione === p.el || (r.domande || []).some(d => d.elezione === p.el)) && (!p.stato || r.stato === p.stato) && (!p.fonte || r.fonte === p.fonte) && (!p.da || (r._data || '') >= p.da) && (!p.a || (r._data || '9') <= p.a) && (!p.tipo || (r.domande || []).some(d => d.tipo === p.tipo)) && (!q || [r.titolo, r._ist, r.committente, r.editore, (r.territorio || {}).nome, ...(r.domande || []).map(d => d.testo)].join(' ').toLowerCase().includes(q)));
  }
  function tabellaArchivio() {
    const lista = filtraArchivio(); const [col, dir] = S.ordAr;
    const chiave = r => ({ data: r._data || '', ist: r._ist, titolo: r.titolo || '', terr: (r.territorio || {}).nome || '', camp: r.campione || 0, stato: r.stato || '', fonte: r.fonte || '' })[col];
    lista.sort((a, b) => { const x = chiave(a), y = chiave(b); return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * dir; });
    const per = 50, pag = Math.min(S.pagAr, Math.max(0, Math.ceil(lista.length / per) - 1)), vis = lista.slice(pag * per, pag * per + per);
    const th = (k, n, cls) => `<th class="${cls || ''}"><button type="button" data-ord="${k}">${n}${col === k ? (dir > 0 ? ' ▲' : ' ▼') : ''}</button></th>`;
    $('#a-azioni').innerHTML = `<span class="nota-l">${fmtN(lista.length)} rilevazioni</span><button type="button" class="btn btn-secondario mini" id="a-csv">Esporta CSV</button><button type="button" class="btn btn-secondario mini" id="a-xlsx">Esporta Excel</button>`;
    $('#a-tab').innerHTML = lista.length ? `<div class="scorri"><table class="tab"><thead><tr>${th('data', 'Data')}${th('ist', 'Istituto')}${th('titolo', 'Titolo')}<th>Committente / editore</th>${th('terr', 'Territorio')}<th>Consultazione</th>${th('camp', 'Campione', 'n')}${th('stato', 'Stato')}${th('fonte', 'Fonte')}</tr></thead><tbody>
      ${vis.map(r => `<tr class="cliccabile" data-scheda="${esc(r.id)}" tabindex="0"><td>${fmtDbreve(r._data)}${r.criterioData === 'pubblicazione' ? '<br><span class="nota-l">pubbl.</span>' : ''}</td><td>${esc(r._ist)}</td><td>${esc((r.titolo || '').slice(0, 90))}</td><td class="nota-l">${esc(r.committente || '')}${r.editore && r.editore !== r.committente ? (r.committente ? ' / ' : '') + esc(r.editore) : ''}</td><td>${esc((r.territorio || {}).nome || '')}</td><td>${esc(ELEZ[r.elezione] || r.elezione || '')}</td><td class="n">${r.campione ? fmtN(r.campione, 0) : '–'}</td><td>${badgeStato(r.stato)}</td><td class="nota-l">${esc((S.a.fonti[r.fonte] || {}).nome || r.fonte)}</td></tr>`).join('')}
      </tbody></table></div><div class="pagine">${pag > 0 ? '<button type="button" class="btn btn-secondario mini" data-pag="-1">← Precedenti</button>' : ''}<span class="nota-l">pagina ${pag + 1} di ${Math.max(1, Math.ceil(lista.length / per))}</span>${(pag + 1) * per < lista.length ? '<button type="button" class="btn btn-secondario mini" data-pag="1">Successive →</button>' : ''}</div>` : '<p class="vuoto">Nessuna rilevazione con questi filtri.</p>';
    $$('#a-tab [data-ord]').forEach(b => b.addEventListener('click', () => { S.ordAr = S.ordAr[0] === b.dataset.ord ? [b.dataset.ord, -S.ordAr[1]] : [b.dataset.ord, 1]; tabellaArchivio(); }));
    $$('#a-tab [data-pag]').forEach(b => b.addEventListener('click', () => { S.pagAr = pag + Number(b.dataset.pag); tabellaArchivio(); }));
    $$('#a-tab tr[data-scheda]').forEach(tr => { tr.addEventListener('click', () => apriScheda(tr.dataset.scheda)); tr.addEventListener('keydown', e => { if (e.key === 'Enter') apriScheda(tr.dataset.scheda); }); });
    $('#a-csv').addEventListener('click', () => scaricaFile('osservatorio-sondaggi.csv', csvDa(righeEsport(lista)), 'text/csv;charset=utf-8'));
    $('#a-xlsx').addEventListener('click', async () => scaricaFile('osservatorio-sondaggi.xlsx', await xlsxDa(righeEsport(lista)), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
  }
  function righeEsport(lista) {
    const righe = [['Data riferimento', 'Criterio data', 'Inizio interviste', 'Fine interviste', 'Pubblicazione', 'Istituto', 'Committente', 'Editore', 'Titolo', 'Territorio', 'Tipo territorio', 'Consultazione', 'Campione', 'Metodo', 'Domanda', 'Tipo domanda', 'Soggetto', 'Testo risposta', 'Valore', 'Minimo', 'Maximo', 'Variazione dichiarata', 'Unità', 'Denominatore', 'Indecisi', 'Stato', 'Livello fonte', 'Fonte', 'Indirizzo', 'Riferimento nel documento', 'Nota metodologica', 'Limiti']];
    for (const r of lista) {
      const bl = bloccata(r, (r.domande || [])[0]); if (bl && (bl.blocca || []).includes('esportazione')) { righe.push([r._data, r.criterioData, r.inizio, r.fine, r.pubblicato, r._ist, r.committente, r.editore, r.titolo, (r.territorio || {}).nome, (r.territorio || {}).tipo, r.elezione, r.campione, r.metodo, 'VALORI NON ESPORTABILI: periodo di silenzio (' + (bl.nome || '') + ')']); continue; }
      const base = [r._data, r.criterioData, r.inizio, r.fine, r.pubblicato, r._ist, r.committente, r.editore, r.titolo, (r.territorio || {}).nome, (r.territorio || {}).tipo, r.elezione, r.campione, r.metodo];
      const coda = [r.stato, r.livello, (S.a.fonti[r.fonte] || {}).nome || r.fonte, (r.urls || [])[0], '', r.nota, r.limiti];
      if (!(r.domande || []).length) righe.push([...base, '', '', '', '', '', '', '', '', '', '', '', ...coda]);
      for (const d of r.domande || []) for (const x of d.risposte || []) righe.push([...base, d.testo, d.tipo, nomeSogg(x.soggetto) || '', x.testo, x.valore, x.min, x.max, x.variazione, d.unita, d.denominatore, d.indecisi, ...coda.slice(0, 4), d.rif || d.documento || '', r.nota, r.limiti]);
    }
    return righe;
  }

  // Scheda della rilevazione
  function apriScheda(id) {
    const r = S.a.rilevazioni[id]; if (!r) return;
    const dlg = $('#scheda'); const gem = Object.values(S.a.rilevazioni).filter(x => x.gemelli && x.gemelli === r.gemelli && x.id !== r.id);
    const coda = (S.a.coda || {})[id];
    const bl = bloccata(r, (r.domande || [])[0]); const nascondi = bl && (bl.blocca || []).includes('tabelle');
    $('#scheda-dentro').innerHTML = `<div class="testa"><h2 id="scheda-titolo">${esc(r.titolo || 'Rilevazione')}</h2><button type="button" class="chiudi-s" aria-label="Chiudi">×</button></div>
      <div class="riga-badge">${badgeStato(r.stato)}${badgeTerr(r)}${r.elezione ? `<span class="badge b-grigio">${esc(ELEZ[r.elezione] || r.elezione)}</span>` : ''}<span class="badge b-grigio">fonte ${esc(r.livello || 'primaria')}</span>${r.principale === false ? '<span class="badge b-grigio">doppione di un\'altra pubblicazione</span>' : ''}</div>
      <div class="colonne" style="margin-top:10px"><div><dl class="dati">
        <dt>Istituto realizzatore</dt><dd>${esc(r._ist)}</dd><dt>Committente</dt><dd>${esc(r.committente || 'non indicato')}</dd><dt>Editore / diffusione</dt><dd>${esc(r.editore || 'non indicato')}</dd>
        <dt>Interviste</dt><dd>${r.inizio || r.fine ? esc(periodo(r)) : 'date non dichiarate'}</dd><dt>Pubblicazione</dt><dd>${fmtD(r.pubblicato)}</dd><dt>Acquisizione</dt><dd>${fmtDT(r.primaAcquisizione || r.acquisito)}${r.ultimaAcquisizione ? ' (ricontrollo ' + fmtDT(r.ultimaAcquisizione) + ')' : ''}</dd>
        <dt>Data di riferimento</dt><dd>${fmtD(r._data)} (${r.criterioData === 'pubblicazione' ? 'pubblicazione: fine interviste non nota' : 'fine delle interviste'})</dd></dl></div>
        <div><dl class="dati"><dt>Territorio e popolazione</dt><dd>${esc((r.territorio || {}).nome || '')} (${esc((r.territorio || {}).tipo || '')})${r.popolazione ? '; ' + esc(r.popolazione) : ''}</dd><dt>Campione</dt><dd>${r.campione ? fmtN(r.campione, 0) + ' intervistati' : 'non dichiarato'}${r.sottocampione ? '; sottocampione ' + fmtN(r.sottocampione, 0) : ''}</dd>
        <dt>Metodo</dt><dd>${esc(r.metodo || 'non dichiarato')}</dd><dt>Ponderazione</dt><dd>${esc(r.ponderazione || 'non dichiarata')}</dd><dt>Margine d'errore dichiarato</dt><dd>${r.erroreDichiarato != null ? '±' + fmtN(r.erroreDichiarato) + '%' : 'non dichiarato'}</dd></dl></div></div>
      ${r.nota ? `<p class="nota" style="margin-top:8px"><b>Nota metodologica:</b> ${esc(r.nota)}</p>` : ''}${r.limiti ? `<p class="nota"><b>Limiti:</b> ${esc(r.limiti)}</p>` : ''}
      ${coda ? `<div class="avviso-blocco"><strong>In coda «da verificare».</strong> Motivi: ${coda.motivi.map(esc).join('; ')}. I valori qui sotto sono una proposta di estrazione e non entrano nei grafici finché non vengono approvati o corretti in Gestione.</div>` : ''}
      ${nascondi ? `<div class="avviso-blocco"><strong>Valori non mostrati.</strong> ${esc(bl.avviso || '')}</div>` : (r.domande || []).map((d, i) => `<h3>${esc(TIPI[d.tipo] || d.tipo)}${d.elezione ? ' · ' + esc(ELEZ[d.elezione] || d.elezione) : ''}${d.turno ? ' · ' + esc(d.turno) : ''}${d.scenario ? ' · ' + esc(d.scenario) : ''}</h3>
        <p class="nota"><b>Domanda:</b> ${esc(d.testo || '')}${d.scala ? ' · scala: ' + esc(d.scala) : ''} · unità: ${esc(d.unita || '%')}${d.denominatore ? ' · denominatore: ' + esc(d.denominatore) : ''}${d.indecisi != null ? ' · indecisi: ' + fmtN(d.indecisi) + '%' : ''}${d.astenuti != null ? ' · astenuti: ' + fmtN(d.astenuti) + '%' : ''} · origine: ${esc({ tabella: 'tabella del documento', testo: 'testo del documento', ocr: 'lettura automatica di un\'immagine', titolo: 'titolo della ripubblicazione', manuale: 'inserimento manuale' }[d.origine] || d.origine || '')}${d.rif ? ' · ' + esc(d.rif) : ''}${d.controlli && d.controlli.somma != null ? ' · somma ' + fmtN(d.controlli.somma) : ''}</p>
        ${(d.risposte || []).length ? `<div class="scorri" style="max-height:none"><table class="tab"><thead><tr><th>Soggetto / risposta</th><th>Testo originale</th><th class="n">Valore</th><th class="n">Variazione dichiarata</th></tr></thead><tbody>${d.risposte.map(x => `<tr><td>${esc(nomeSogg(x.soggetto) || (x.soggetto ? x.soggetto : 'non riconosciuto'))}</td><td class="nota-l">${esc(x.testo || '')}${x.motivo && x.motivo !== 'ok' && !x.soggetto ? ` <span class="badge b-coda">${esc(x.motivo)}</span>` : ''}</td><td class="n">${x.valore != null ? fmtN(x.valore) : (x.min != null ? fmtN(x.min) + '–' + fmtN(x.max) : '<span class="nota-l">non disponibile</span>')}</td><td class="n">${x.variazione != null ? fmtPP(x.variazione) : ''}</td></tr>`).join('')}</tbody></table></div>` : '<p class="nota">Nessun valore disponibile per questa domanda.</p>'}
        ${d.controlli && d.controlli.motivi && d.controlli.motivi.length ? `<p class="nota"><b>Controlli:</b> ${d.controlli.motivi.map(esc).join('; ')}</p>` : ''}`).join('')}
      <h3>Fonti e documenti</h3><ul class="nota" style="padding-left:18px">${(r.urls || []).map(u => `<li><a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a></li>`).join('')}${(r.documenti || []).map(d => `<li>${esc(d.tipo)}: <a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.titolo || d.url)}</a>${d.rif ? ' · ' + esc(d.rif) : ''}${d.testo ? `<details><summary style="cursor:pointer">testo letto automaticamente (prova documentale)</summary><pre style="white-space:pre-wrap;font-size:12px">${esc(d.testo)}</pre></details>` : ''}</li>`).join('')}</ul>
      <p class="nota">Fonte dell'acquisizione: ${esc((S.a.fonti[r.fonte] || {}).nome || r.fonte)} · identificativo ${esc(r.id)} · riferimento presso la fonte ${esc(r.riferimento || '')}</p>
      ${gem.length ? `<h3>Stessa rilevazione in altre fonti</h3><ul class="elenco">${gem.map(voceRil).join('')}</ul>` : ''}
      ${(r.revisioni || []).length ? `<h3>Cronologia delle revisioni</h3><ul class="nota" style="padding-left:18px">${r.revisioni.map(x => `<li>${fmtDT(x.quando)}${x.autore ? ' · ' + esc(x.autore) : ''}: ${esc(x.nota || '')}${x.prima ? ` <details><summary style="cursor:pointer">valori precedenti</summary><pre style="white-space:pre-wrap;font-size:12px">${esc(JSON.stringify(x.prima, null, 1))}</pre></details>` : ''}</li>`).join('')}</ul>` : ''}
      <div class="azioni"><button type="button" class="btn btn-secondario mini" data-az="approva">Approva come verificata</button><button type="button" class="btn btn-secondario mini" data-az="correggi">Correggi</button><button type="button" class="btn btn-secondario mini" data-az="scarta">Scarta</button><button type="button" class="btn btn-secondario mini" data-az="csv">Scarica CSV</button></div><div id="scheda-azione"></div>`;
    dlg.querySelector('.chiudi-s').onclick = () => dlg.close();
    dlg.querySelectorAll('[data-scheda]').forEach(e => e.addEventListener('click', () => apriScheda(e.dataset.scheda)));
    dlg.querySelectorAll('[data-az]').forEach(b => b.addEventListener('click', () => azioneScheda(r, b.dataset.az)));
    if (!dlg.open) dlg.showModal();
    dlg.scrollTop = 0;
  }
  function azioneScheda(r, az) {
    const box = $('#scheda-azione');
    if (az === 'csv') { scaricaFile(`sondaggio-${r.id}.csv`, csvDa(righeEsport([r])), 'text/csv;charset=utf-8'); return; }
    if (az === 'approva' || az === 'scarta') { box.innerHTML = `<div class="riquadro" style="margin-top:10px"><label class="etichetta" for="az-nota">Nota (facoltativa)</label><input class="campo" id="az-nota" placeholder="${az === 'approva' ? 'per esempio: valori confrontati con il documento originale' : 'motivo dello scarto'}"><div class="azioni"><button type="button" class="btn btn-primario mini" id="az-ok">${az === 'approva' ? 'Conferma approvazione' : 'Conferma scarto'}</button></div><div id="az-esito"></div></div>`; $('#az-ok').addEventListener('click', () => inviaRevisione({ tipo: az, rilevazione: r.id, nota: $('#az-nota').value }, $('#az-esito'))); return; }
    // correzione: campi principali e tabella delle risposte della prima domanda con valori (o nuova)
    const d = (r.domande || [])[0] || { tipo: 'voto', testo: 'Intenzioni di voto', unita: '%', denominatore: 'validi', risposte: [] };
    const opzSogg = sel => `<option value="">(testo libero)</option>` + Object.values(S.sogg).sort((a, b) => a.nome.localeCompare(b.nome)).map(s => `<option value="${esc(s.id)}" ${sel === s.id ? 'selected' : ''}>${esc(s.nome)}</option>`).join('');
    box.innerHTML = `<div class="riquadro" style="margin-top:10px"><h3 style="margin-top:0">Correzione manuale</h3><p class="nota">I campi vuoti restano com'erano. La rilevazione corretta diventa «verificata» e protetta: gli aggiornamenti automatici non la sovrascrivono più.</p>
      <div class="filtri"><div><label class="etichetta">Istituto</label><input class="campo" id="c-ist" value="${esc(r._ist)}"></div><div><label class="etichetta">Committente</label><input class="campo" id="c-com" value="${esc(r.committente || '')}"></div><div><label class="etichetta">Inizio interviste</label><input class="campo" id="c-ini" type="date" value="${esc(r.inizio || '')}"></div><div><label class="etichetta">Fine interviste</label><input class="campo" id="c-fin" type="date" value="${esc(r.fine || '')}"></div>
      <div><label class="etichetta">Campione</label><input class="campo" id="c-camp" type="number" value="${esc(r.campione || '')}"></div><div><label class="etichetta">Territorio</label><select class="campo" id="c-terr"><option value="Italia" ${(r.territorio || {}).tipo === 'Italia' ? 'selected' : ''}>Italia</option><option value="FVG" ${r._area === 'fvg' && (r.territorio || {}).tipo === 'regione' ? 'selected' : ''}>Friuli Venezia Giulia</option><option value="comune" ${(r.territorio || {}).tipo === 'comune' ? 'selected' : ''}>Comune (nome nel campo accanto)</option><option value="altro" ${(r.territorio || {}).tipo === 'altro' || (r.territorio || {}).tipo === 'regione' && r._area !== 'fvg' ? 'selected' : ''}>Altra area</option></select></div><div><label class="etichetta">Nome territorio</label><input class="campo" id="c-tnome" value="${esc((r.territorio || {}).nome || '')}"></div>
      <div><label class="etichetta">Consultazione</label><select class="campo" id="c-el"><option value="">–</option>${Object.entries(ELEZ).map(([k, n]) => `<option value="${k}" ${(d.elezione || r.elezione) === k ? 'selected' : ''}>${n}</option>`).join('')}</select></div></div>
      <h3>Valori della domanda «${esc(d.testo || '')}»</h3><div class="scorri" style="max-height:none"><table class="tab" id="c-tab"><thead><tr><th>Soggetto</th><th>Testo originale</th><th class="n">Valore</th><th></th></tr></thead><tbody>
      ${(d.risposte || []).map(x => `<tr><td><select class="campo">${opzSogg(x.soggetto)}</select></td><td><input class="campo" value="${esc(x.testo || '')}"></td><td><input class="campo" type="number" step="0.1" value="${x.valore == null ? '' : x.valore}"></td><td><button type="button" class="btn btn-secondario mini" data-del>✕</button></td></tr>`).join('')}
      </tbody></table></div><div class="azioni"><button type="button" class="btn btn-secondario mini" id="c-add">+ Riga</button></div>
      <label class="etichetta" for="c-nota" style="margin-top:8px">Nota della correzione (obbligatoria)</label><input class="campo" id="c-nota" placeholder="Che cosa è stato corretto e sulla base di quale documento">
      <div class="azioni"><button type="button" class="btn btn-primario mini" id="c-ok">Salva la correzione</button></div><div id="az-esito"></div></div>`;
    const aggDel = () => box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => b.closest('tr').remove());
    aggDel();
    $('#c-add').addEventListener('click', () => { $('#c-tab tbody').insertAdjacentHTML('beforeend', `<tr><td><select class="campo">${opzSogg('')}</select></td><td><input class="campo"></td><td><input class="campo" type="number" step="0.1"></td><td><button type="button" class="btn btn-secondario mini" data-del>✕</button></td></tr>`); aggDel(); });
    $('#c-ok').addEventListener('click', () => {
      if (!$('#c-nota').value.trim()) { $('#az-esito').innerHTML = '<p class="errore">Serve una nota che spieghi la correzione.</p>'; return; }
      const terr = $('#c-terr').value; const territorio = terr === 'Italia' ? { tipo: 'Italia', nome: 'Italia', codice: 'IT' } : terr === 'FVG' ? { tipo: 'regione', nome: 'Friuli Venezia Giulia', codice: 'FVG' } : terr === 'comune' ? { tipo: 'comune', nome: $('#c-tnome').value, codice: null } : { tipo: 'altro', nome: $('#c-tnome').value, codice: null };
      const risposte = [...$('#c-tab tbody').querySelectorAll('tr')].map(tr => { const [sel, inp, num] = tr.querySelectorAll('select,input'); return { soggetto: sel.value || null, testo: inp.value, valore: num.value === '' ? null : Number(num.value), min: null, max: null, variazione: null }; }).filter(x => x.soggetto || x.testo);
      const campi = { committente: $('#c-com').value || null, inizio: $('#c-ini').value || null, fine: $('#c-fin').value || null, campione: $('#c-camp').value ? Number($('#c-camp').value) : null, territorio };
      if ($('#c-fin').value) campi.criterioData = 'interviste';
      const istN = $('#c-ist').value.trim(); const istId = Object.entries(S.a.istituti).find(([k, s]) => s.nome.toLowerCase() === istN.toLowerCase()); if (istId) campi.istituto = istId[0]; else if (istN) campi.istituto = istN.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      if ($('#c-el').value) campi.elezione = $('#c-el').value;
      const domande = [{ ...d, elezione: $('#c-el').value || d.elezione || null, risposte, origine: 'manuale', controlli: { ok: true, motivi: [], nota: 'corretta a mano' } }, ...(r.domande || []).slice(1)];
      inviaRevisione({ tipo: 'correzione', rilevazione: r.id, campi, domande, nota: $('#c-nota').value }, $('#az-esito'));
    });
  }

  // ------------------------------------------------------------------------------------------- Gestione
  const tokenMem = () => { try { return sessionStorage.getItem('atlante-fvg:sondaggi-token') || ''; } catch (e) { return ''; } };
  async function gh(percorso, opz) {
    const t = tokenMem(); if (!t) throw new Error('nessun token GitHub salvato in questa sessione');
    const r = await fetch('https://api.github.com' + percorso, { ...opz, headers: { Authorization: 'Bearer ' + t, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', ...((opz || {}).headers || {}) } });
    if (!r.ok) { let m = ''; try { m = (await r.json()).message; } catch (e) {} throw new Error(`GitHub ${r.status}${m ? ': ' + m : ''}`); }
    return r.status === 204 ? null : r.json();
  }
  async function scriviNelRamo(percorso, contenutoTesto, messaggio) {
    const repo = RAD.dataset.repo, ramo = RAD.dataset.ramo;
    const b64 = aB64(new TextEncoder().encode(contenutoTesto));
    return gh(`/repos/${repo}/contents/${percorso}`, { method: 'PUT', body: JSON.stringify({ message: messaggio, content: b64, branch: ramo }) });
  }
  async function inviaRevisione(rev, esitoBox) {
    rev.quando = new Date().toISOString(); rev.autore = (tokenMem() ? 'pannello (GitHub)' : 'pannello');
    esitoBox.innerHTML = '<p class="nota"><span class="rotella"></span> Cifro e invio…</p>';
    try {
      const cifrato = await cifraJSON(rev);
      const nome = `revisioni/${rev.quando.replace(/[:.]/g, '-')}-${rev.tipo}.json`;
      if (tokenMem()) {
        await scriviNelRamo(nome, cifrato, `Osservatorio sondaggi: revisione ${rev.tipo}${rev.rilevazione ? ' ' + rev.rilevazione : ''}`);
        esitoBox.innerHTML = `<div class="ok-msg">Revisione registrata nel ramo dei dati (<span class="k">${esc(nome)}</span>). Sarà applicata al prossimo aggiornamento: puoi avviarlo subito da Gestione › «Aggiorna adesso».</div>`;
      } else {
        scaricaFile(nome.split('/')[1], cifrato, 'application/json');
        esitoBox.innerHTML = `<div class="ok-msg">Nessun token GitHub in sessione: la revisione cifrata è stata scaricata. Caricala nel ramo <span class="k">${esc(RAD.dataset.ramo)}</span>, cartella <span class="k">revisioni/</span>, dal sito GitHub, oppure salva un token in Gestione e ripeti.</div>`;
      }
    } catch (e) { esitoBox.innerHTML = `<p class="errore">Invio non riuscito: ${esc(e.message)}</p>`; }
  }
  function vGestione(v) {
    const a = S.a; const coda = Object.values(a.coda || {}).filter(c => c.stato !== 'chiusa').sort((x, y) => (y.aggiornata || '').localeCompare(x.aggiornata || ''));
    const esec = (a.esecuzioni || []).slice(0, 30); const fonti = Object.values(a.fonti || {});
    const repo = RAD.dataset.repo;
    v.innerHTML = `<section class="riquadro"><h2>Gestione</h2>
      <p class="nota">Le modifiche non toccano direttamente l'archivio: diventano «revisioni» cifrate con la chiave della sezione e scritte nel ramo <span class="k">${esc(RAD.dataset.ramo)}</span> del repository GitHub; il flusso automatico le applica al giro successivo e non le sovrascrive più. Per scrivere su GitHub dal browser serve un token personale (fine-grained) con permessi <b>Contents: lettura e scrittura</b> e <b>Actions: lettura e scrittura</b> sul repository <span class="k">${esc(repo)}</span>; il token resta solo in questa sessione del browser e non viene salvato altrove.</p>
      <div class="filtri tre"><div><label class="etichetta" for="g-token">Token GitHub (sessione)</label><input class="campo" id="g-token" type="password" value="${esc(tokenMem())}" placeholder="github_pat_…"></div><div class="azioni" style="margin:0"><button type="button" class="btn btn-secondario" id="g-salva">Salva nella sessione</button><button type="button" class="btn btn-secondario" id="g-verifica">Verifica</button></div></div><div id="g-esito-token"></div>
      <h3>Aggiornamento</h3>
      <dl class="dati"><dt>Ultimo tentativo</dt><dd>${fmtDT(a.ultimoTentativo)}</dd><dt>Ultimo riuscito</dt><dd>${fmtDT(a.ultimoRiuscito)}</dd><dt>Ultima rilevazione disponibile</dt><dd>${fmtD(a.ultimaRilevazione)}</dd><dt>Pianificazione</dt><dd>ogni giorno alle 6 (Europe/Rome), GitHub Actions «Osservatorio sondaggi» (<a href="https://github.com/${esc(repo)}/actions/workflows/${esc(RAD.dataset.flusso)}" target="_blank" rel="noopener">registro delle esecuzioni</a>)</dd></dl>
      <div class="azioni"><button type="button" class="btn btn-primario" data-avvia="incrementale">Aggiorna adesso</button><button type="button" class="btn btn-secondario" data-avvia="storico">Riprendi il recupero storico</button><button type="button" class="btn btn-secondario" data-avvia="ricontrollo">Ricontrolla i documenti recenti</button></div><div id="g-esito-avvio"></div>
      </section>
      <section class="riquadro"><h2>Coda «da verificare» (${fmtN(coda.length)})</h2><p class="nota">Estrazioni ambigue o contraddittorie, escluse dai grafici. Apri la scheda per approvare, correggere o scartare.</p>
        <div class="filtri tre"><div><label class="etichetta" for="g-coda-f">Fonte</label><select class="campo" id="g-coda-f"><option value="">Tutte</option>${fonti.map(f => `<option value="${esc(f.id)}">${esc(f.nome)}</option>`).join('')}</select></div><div><label class="etichetta" for="g-coda-m">Motivo</label><select class="campo" id="g-coda-m"><option value="">Tutti</option>${[...new Set(coda.flatMap(c => c.motivi.map(m => m.replace(/[\d.,]+/g, 'N'))))].map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('')}</select></div></div>
        <ul class="elenco" id="g-coda"></ul><div class="pagine" id="g-coda-pag"></div></section>
      <section class="riquadro"><h2>Fonti</h2><div class="scorri"><table class="tab"><thead><tr><th>Fonte</th><th>Tipo</th><th>Attiva</th><th>Avanzamento storico</th><th>Ultimo esito</th><th>Errore</th><th></th></tr></thead><tbody>
        ${fonti.map(f => { const st = (a.statoFonti || {})[f.id] || {}; const av = st.avanzamento || {}; const ue = st.ultimoEsito || {}; return `<tr><td><b>${esc(f.nome)}</b><br><span class="nota-l">${esc(f.accesso || '')}</span></td><td>${esc(f.tipo)}</td><td>${f.attiva ? '<span class="badge b-ok">sì</span>' : '<span class="badge b-no">no</span>'}</td><td class="nota-l">${av.storicoCompletato ? 'completato ' + fmtDT(av.storicoCompletato) : (av.offset != null ? `voce ${fmtN(av.offset)}, fino al ${esc(av.ultimaData || '')}` : (av.storicoCompletato === undefined && f.attiva ? 'in corso o non avviato' : ''))}</td><td class="nota-l">${Object.keys(ue).length ? `letti ${ue.letti || 0}, nuovi ${ue.nuovi || 0}, aggiornati ${ue.aggiornati || 0}, in coda ${ue.coda || 0}${ue.saltati ? ', saltati ' + ue.saltati : ''}` : ''}<br>${fmtDT(st.ultimoTentativo)}</td><td class="nota-l">${esc(st.errore || '')}</td><td>${f.tipo !== 'non_raggiungibile' ? `<button type="button" class="btn btn-secondario mini" data-fonte="${esc(f.id)}" data-attiva="${f.attiva ? '0' : '1'}">${f.attiva ? 'Disattiva' : 'Attiva'}</button>` : ''}</td></tr>`; }).join('')}
        </tbody></table></div><div id="g-esito-fonte"></div>
        <h3>Aggiungi una fonte o un collegamento</h3><p class="nota">Un collegamento singolo crea una rilevazione manuale (titolo, istituto, date, territorio e indirizzo) da completare con i valori tramite «Correggi» nella scheda. Una nuova fonte periodica richiede un connettore nel codice: qui viene registrata la richiesta.</p>
        <div class="filtri"><div><label class="etichetta" for="g-l-url">Indirizzo</label><input class="campo" id="g-l-url" placeholder="https://…"></div><div><label class="etichetta" for="g-l-tit">Titolo</label><input class="campo" id="g-l-tit"></div><div><label class="etichetta" for="g-l-ist">Istituto</label><input class="campo" id="g-l-ist"></div><div><label class="etichetta" for="g-l-com">Committente</label><input class="campo" id="g-l-com"></div><div><label class="etichetta" for="g-l-ini">Inizio interviste</label><input class="campo" id="g-l-ini" type="date"></div><div><label class="etichetta" for="g-l-fin">Fine interviste</label><input class="campo" id="g-l-fin" type="date"></div><div><label class="etichetta" for="g-l-terr">Territorio</label><select class="campo" id="g-l-terr"><option value="Italia">Italia</option><option value="FVG">Friuli Venezia Giulia</option><option value="comune">Comune del Friuli Venezia Giulia</option><option value="altro">Altra area</option></select></div><div><label class="etichetta" for="g-l-tnome">Nome territorio (se comune o altra area)</label><input class="campo" id="g-l-tnome"></div><div><label class="etichetta" for="g-l-el">Consultazione</label><select class="campo" id="g-l-el"><option value="">–</option>${Object.entries(ELEZ).map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select></div><div><label class="etichetta" for="g-l-tipo">Che cosa registrare</label><select class="campo" id="g-l-tipo"><option value="manuale">Collegamento singolo (rilevazione manuale)</option><option value="fonte">Richiesta di nuova fonte periodica</option></select></div></div>
        <div class="azioni"><button type="button" class="btn btn-primario mini" id="g-l-ok">Registra</button></div><div id="g-esito-link"></div>
        <h3>Carica un documento (PDF, CSV, XLSX, immagine)</h3><p class="nota">Il file viene cifrato nel browser e scritto nel ramo dei dati; al giro successivo il flusso ne estrae tabelle e nota informativa. Per i CSV/XLSX compilati a mano usa le colonne <span class="k">soggetto; valore</span> (facoltative: <span class="k">domanda; variazione; min; max</span>): entrano come trascrizione verificata. Dimensione massima consigliata 15 MB.</p>
        <div class="filtri"><div><label class="etichetta" for="g-f-file">File</label><input class="campo-file" id="g-f-file" type="file" accept=".pdf,.csv,.xlsx,.png,.jpg,.jpeg,.webp"></div><div><label class="etichetta" for="g-f-ist">Istituto</label><input class="campo" id="g-f-ist"></div><div><label class="etichetta" for="g-f-tit">Titolo</label><input class="campo" id="g-f-tit"></div><div><label class="etichetta" for="g-f-url">Indirizzo originale (se noto)</label><input class="campo" id="g-f-url"></div><div><label class="etichetta" for="g-f-ini">Inizio interviste</label><input class="campo" id="g-f-ini" type="date"></div><div><label class="etichetta" for="g-f-fin">Fine interviste</label><input class="campo" id="g-f-fin" type="date"></div><div><label class="etichetta" for="g-f-terr">Territorio</label><select class="campo" id="g-f-terr"><option value="Italia">Italia</option><option value="FVG">Friuli Venezia Giulia</option><option value="comune">Comune del Friuli Venezia Giulia</option><option value="altro">Altra area</option></select></div><div><label class="etichetta" for="g-f-tnome">Nome territorio</label><input class="campo" id="g-f-tnome"></div><div><label class="etichetta" for="g-f-el">Consultazione</label><select class="campo" id="g-f-el"><option value="">–</option>${Object.entries(ELEZ).map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select></div></div>
        <div class="azioni"><button type="button" class="btn btn-primario mini" id="g-f-ok">Carica</button></div><div id="g-esito-file"></div></section>
      <section class="riquadro"><h2>Istituti, alias e serie</h2><p class="nota">Unisci le grafie di uno stesso istituto indicando gli alias; dichiara una serie comparabile a mano quando il confronto automatico non la riconosce.</p>
        <div class="filtri tre"><div><label class="etichetta" for="g-i-id">Istituto</label><select class="campo" id="g-i-id">${Object.entries(a.istituti).sort((x, y) => x[1].nome.localeCompare(y[1].nome)).map(([k, s]) => `<option value="${esc(k)}">${esc(s.nome)} (${esc(k)})</option>`).join('')}</select></div><div><label class="etichetta" for="g-i-nome">Nome da mostrare</label><input class="campo" id="g-i-nome"></div><div><label class="etichetta" for="g-i-alias">Alias (separati da ;)</label><input class="campo" id="g-i-alias"></div></div>
        <div class="azioni"><button type="button" class="btn btn-secondario mini" id="g-i-ok">Salva istituto</button></div><div id="g-esito-ist"></div>
        <div class="filtri tre" style="margin-top:10px"><div><label class="etichetta" for="g-s-nome">Nome della serie</label><input class="campo" id="g-s-nome"></div><div><label class="etichetta" for="g-s-ids">Identificativi delle rilevazioni (separati da ;)</label><input class="campo" id="g-s-ids" placeholder="id;id;id (dalla scheda)"></div><div><label class="etichetta" for="g-s-nota">Nota sulla comparabilità</label><input class="campo" id="g-s-nota"></div></div>
        <div class="azioni"><button type="button" class="btn btn-secondario mini" id="g-s-ok">Salva serie</button></div><div id="g-esito-serie"></div></section>
      <section class="riquadro"><h2>Esecuzioni ed errori</h2><div class="scorri"><table class="tab"><thead><tr><th>Inizio</th><th>Modalità</th><th>Esito</th><th class="n">Durata</th><th>Per fonte</th><th>Errori</th></tr></thead><tbody>
        ${esec.map(e => `<tr><td>${fmtDT(e.inizio)}</td><td>${esc(e.modalita)}<br><span class="nota-l">${esc(e.esecutore || '')}</span></td><td>${e.esito === 'riuscita' ? '<span class="badge b-ok">riuscita</span>' : e.esito === 'parziale' ? '<span class="badge b-coda">parziale</span>' : '<span class="badge b-no">' + esc(e.esito || '') + '</span>'}</td><td class="n">${e.durata != null ? Math.round(e.durata / 60) + ' min' : ''}</td><td class="nota-l">${Object.entries(e.fonti || {}).map(([f, x]) => `${esc(f)}: letti ${x.letti || 0}, nuovi ${x.nuovi || 0}, coda ${x.coda || 0}${(x.errori || []).length ? ', errori ' + x.errori.length : ''}`).join('<br>')}</td><td class="nota-l">${[...(e.errori || []), ...Object.values(e.fonti || {}).flatMap(x => x.errori || [])].slice(0, 6).map(esc).join('<br>')}${(e.fallimentiRete || []).length ? `<br>indirizzi senza risposta: ${e.fallimentiRete.slice(0, 4).map(x => esc(x.url.slice(0, 70))).join(', ')}` : ''}</td></tr>`).join('') || '<tr><td colspan="6" class="vuoto">Nessuna esecuzione registrata.</td></tr>'}
        </tbody></table></div>
        <h3>Revisioni applicate</h3><div class="scorri"><table class="tab"><thead><tr><th>Quando</th><th>Tipo</th><th>Rilevazione</th><th>Esito</th></tr></thead><tbody>${(a.revisioni || []).slice(-30).reverse().map(r => `<tr><td>${fmtDT(r.quando)}</td><td>${esc(r.tipo)}</td><td class="nota-l">${r.rilevazione ? `<a href="#" class="scheda-link" data-scheda="${esc(r.rilevazione)}">${esc(r.rilevazione)}</a>` : ''}</td><td class="nota-l">${esc(r.esito || '')} ${r.nota ? '· ' + esc(r.nota) : ''}</td></tr>`).join('') || '<tr><td colspan="4" class="vuoto">Nessuna revisione.</td></tr>'}</tbody></table></div>
      </section>`;
    $('#g-salva').addEventListener('click', () => { try { sessionStorage.setItem('atlante-fvg:sondaggi-token', $('#g-token').value.trim()); $('#g-esito-token').innerHTML = '<div class="ok-msg">Token salvato nella sessione del browser (si cancella chiudendo la sezione).</div>'; } catch (e) { $('#g-esito-token').innerHTML = `<p class="errore">${esc(e.message)}</p>`; } });
    $('#g-verifica').addEventListener('click', async () => { const b = $('#g-esito-token'); b.innerHTML = '<p class="nota"><span class="rotella"></span> Verifico…</p>'; try { const r = await gh(`/repos/${repo}`); const w = await gh(`/repos/${repo}/actions/workflows/${RAD.dataset.flusso}`); let ramo = 'assente (lo crea il primo giro del flusso)'; try { await gh(`/repos/${repo}/branches/${RAD.dataset.ramo}`); ramo = 'presente'; } catch (e) {} b.innerHTML = `<div class="ok-msg">Accesso a <b>${esc(r.full_name)}</b> (permessi: ${r.permissions && r.permissions.push ? 'scrittura' : 'sola lettura'}); flusso «${esc(w.name)}» ${esc(w.state)}; ramo dei dati ${ramo}.</div>`; } catch (e) { b.innerHTML = `<p class="errore">${esc(e.message)}</p>`; } });
    $$('[data-avvia]').forEach(b => b.addEventListener('click', async () => { const box = $('#g-esito-avvio'); box.innerHTML = '<p class="nota"><span class="rotella"></span> Avvio…</p>'; try { await gh(`/repos/${repo}/actions/workflows/${RAD.dataset.flusso}/dispatches`, { method: 'POST', body: JSON.stringify({ ref: 'main', inputs: { modalita: b.dataset.avvia } }) }); box.innerHTML = `<div class="ok-msg">Flusso avviato in modalità «${esc(b.dataset.avvia)}». Il risultato comparirà qui dopo qualche minuto (ricarica la pagina): <a href="https://github.com/${esc(repo)}/actions/workflows/${esc(RAD.dataset.flusso)}" target="_blank" rel="noopener">segui l'esecuzione su GitHub</a>.</div>`; } catch (e) { box.innerHTML = `<p class="errore">Avvio non riuscito: ${esc(e.message)}. Senza token puoi avviarlo dal sito GitHub: Actions › Osservatorio sondaggi › «Run workflow».</p>`; } }));
    $$('[data-fonte]').forEach(b => b.addEventListener('click', () => inviaRevisione({ tipo: 'fonte', id: b.dataset.fonte, attiva: b.dataset.attiva === '1', nota: (b.dataset.attiva === '1' ? 'riattivata' : 'disattivata') + ' dal pannello' }, $('#g-esito-fonte'))));
    const terrDa = (sel, nome) => sel === 'Italia' ? { tipo: 'Italia', nome: 'Italia', codice: 'IT' } : sel === 'FVG' ? { tipo: 'regione', nome: 'Friuli Venezia Giulia', codice: 'FVG' } : sel === 'comune' ? { tipo: 'comune', nome: nome || 'comune non indicato', codice: null } : { tipo: 'altro', nome: nome || 'altra area', codice: null };
    $('#g-l-ok').addEventListener('click', () => {
      const url = $('#g-l-url').value.trim(); if (!url) { $('#g-esito-link').innerHTML = '<p class="errore">Serve un indirizzo.</p>'; return; }
      if ($('#g-l-tipo').value === 'fonte') { inviaRevisione({ tipo: 'fonte', id: 'richiesta-' + Date.now().toString(36), nome: $('#g-l-tit').value || url, url, tipo_fonte: 'richiesta', attiva: false, nota: 'richiesta di nuova fonte dal pannello: serve un connettore' }, $('#g-esito-link')); return; }
      inviaRevisione({ tipo: 'manuale', nota: 'collegamento aggiunto dal pannello', rilevazione: { fonte: 'manuale', riferimento: url, titolo: $('#g-l-tit').value || url, istituto: $('#g-l-ist').value || null, committente: $('#g-l-com').value || null, inizio: $('#g-l-ini').value || null, fine: $('#g-l-fin').value || null, criterioData: $('#g-l-fin').value ? 'interviste' : 'pubblicazione', territorio: terrDa($('#g-l-terr').value, $('#g-l-tnome').value), elezione: $('#g-l-el').value || null, livello: 'primaria', urls: [url], documenti: [{ url, tipo: /\.pdf($|\?)/i.test(url) ? 'pdf' : 'html', titolo: $('#g-l-tit').value || url, rif: 'collegamento aggiunto a mano' }], domande: [] } }, $('#g-esito-link'));
    });
    $('#g-f-ok').addEventListener('click', async () => {
      const f = $('#g-f-file').files[0]; const box = $('#g-esito-file'); if (!f) { box.innerHTML = '<p class="errore">Scegli un file.</p>'; return; }
      if (f.size > 20 * 1024 * 1024) { box.innerHTML = '<p class="errore">File troppo grande (massimo 20 MB).</p>'; return; }
      box.innerHTML = '<p class="nota"><span class="rotella"></span> Leggo, cifro e carico…</p>';
      try {
        const buf = new Uint8Array(await f.arrayBuffer()); const id = Date.now().toString(36) + '-' + f.name.toLowerCase().replace(/[^a-z0-9.]+/g, '-').slice(0, 40);
        const c = { id, nome: f.name, tipo: f.type, quando: new Date().toISOString(), autore: 'pannello', istituto: $('#g-f-ist').value || null, titolo: $('#g-f-tit').value || f.name, url: $('#g-f-url').value || null, inizio: $('#g-f-ini').value || null, fine: $('#g-f-fin').value || null, territorio: terrDa($('#g-f-terr').value, $('#g-f-tnome').value), elezione: $('#g-f-el').value || null, contenuto: aB64(buf) };
        const cifrato = await cifraJSON(c);
        if (tokenMem()) { await scriviNelRamo(`caricati/${id}.json`, cifrato, `Osservatorio sondaggi: documento caricato ${f.name}`); box.innerHTML = `<div class="ok-msg">Documento caricato (<span class="k">caricati/${esc(id)}.json</span>). Verrà letto al prossimo aggiornamento: avvialo con «Aggiorna adesso».</div>`; }
        else { scaricaFile(id + '.json', cifrato, 'application/json'); box.innerHTML = `<div class="ok-msg">Senza token il file cifrato è stato scaricato: caricalo nel ramo <span class="k">${esc(RAD.dataset.ramo)}</span>, cartella <span class="k">caricati/</span>.</div>`; }
      } catch (e) { box.innerHTML = `<p class="errore">${esc(e.message)}</p>`; }
    });
    const selI = $('#g-i-id'); const riempi = () => { const s = a.istituti[selI.value]; if (s) { $('#g-i-nome').value = s.nome; $('#g-i-alias').value = (s.alias || []).join('; '); } }; selI.addEventListener('change', riempi); riempi();
    $('#g-i-ok').addEventListener('click', () => inviaRevisione({ tipo: 'istituto', id: selI.value, nome: $('#g-i-nome').value, alias: $('#g-i-alias').value.split(';').map(x => x.trim()).filter(Boolean), nota: 'istituto aggiornato dal pannello' }, $('#g-esito-ist')));
    $('#g-s-ok').addEventListener('click', () => { const ids = $('#g-s-ids').value.split(';').map(x => x.trim()).filter(Boolean); if (!ids.length || !$('#g-s-nome').value) { $('#g-esito-serie').innerHTML = '<p class="errore">Servono nome e almeno un identificativo.</p>'; return; } inviaRevisione({ tipo: 'serie', id: 'manuale-' + Date.now().toString(36), nome: $('#g-s-nome').value, rilevazioni: ids, nota: $('#g-s-nota').value }, $('#g-esito-serie')); });
    // coda
    let pagC = 0; const perC = 25;
    const disegnaCoda = () => { const f = $('#g-coda-f').value, m = $('#g-coda-m').value; const l = coda.filter(c => (!f || c.fonte === f) && (!m || c.motivi.some(x => x.replace(/[\d.,]+/g, 'N') === m))); const vis = l.slice(pagC * perC, pagC * perC + perC); $('#g-coda').innerHTML = vis.map(c => { const r = a.rilevazioni[c.rilevazione]; return `<li class="voce"><div><h3><button type="button" data-scheda="${esc(c.rilevazione)}">${esc(c.titolo || c.rilevazione)}</button></h3><div class="meta">${r ? esc(r._ist) + ' · ' + esc(periodo(r)) + ' · ' : ''}${esc((a.fonti[c.fonte] || {}).nome || c.fonte)}</div><div class="meta">${c.motivi.map(esc).join('; ')}</div></div><div class="lato"><b>${fmtDbreve(c.aggiornata)}</b><span>in coda</span></div></li>`; }).join('') || '<li class="vuoto">Nessuna voce in coda con questi filtri.</li>'; $('#g-coda-pag').innerHTML = `${pagC > 0 ? '<button type="button" class="btn btn-secondario mini" id="c-prev">←</button>' : ''}<span class="nota-l">${fmtN(l.length)} voci · pagina ${pagC + 1}</span>${(pagC + 1) * perC < l.length ? '<button type="button" class="btn btn-secondario mini" id="c-next">→</button>' : ''}`; $$('#g-coda [data-scheda]').forEach(b => b.addEventListener('click', () => apriScheda(b.dataset.scheda))); const pv = $('#c-prev'), nx = $('#c-next'); if (pv) pv.onclick = () => { pagC--; disegnaCoda(); }; if (nx) nx.onclick = () => { pagC++; disegnaCoda(); }; };
    $('#g-coda-f').addEventListener('change', () => { pagC = 0; disegnaCoda(); }); $('#g-coda-m').addEventListener('change', () => { pagC = 0; disegnaCoda(); }); disegnaCoda();
  }

  // ---------------------------------------------------------------------------------------- esportazioni
  function scaricaFile(nome, contenuto, tipo) { const b = contenuto instanceof Blob ? contenuto : new Blob([contenuto], { type: tipo }); const u = URL.createObjectURL(b); const a = document.createElement('a'); a.href = u; a.download = nome; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 2000); }
  const csvDa = righe => '﻿' + righe.map(r => r.map(c => { const s = c == null ? '' : typeof c === 'number' ? String(c).replace('.', ',') : String(c); return /[;"\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }).join(';')).join('\r\n');
  // XLSX minimo: archivio ZIP «stored» con CRC32 e un foglio con stringhe in linea
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return b => { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = t[(c ^ b[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }; })();
  async function xlsxDa(righe) {
    const xmlEsc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const col = n => { let s = ''; n++; while (n) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); } return s; };
    const foglio = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${righe.map((r, i) => `<row r="${i + 1}">${r.map((c, j) => c == null || c === '' ? '' : typeof c === 'number' ? `<c r="${col(j)}${i + 1}"><v>${c}</v></c>` : `<c r="${col(j)}${i + 1}" t="inlineStr"><is><t>${xmlEsc(c)}</t></is></c>`).join('')}</row>`).join('')}</sheetData></worksheet>`;
    const file = {
      '[Content_Types].xml': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`,
      '_rels/.rels': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
      'xl/workbook.xml': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sondaggi" sheetId="1" r:id="rId1"/></sheets></workbook>`,
      'xl/_rels/workbook.xml.rels': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>`,
      'xl/worksheets/sheet1.xml': foglio,
    };
    const enc = new TextEncoder(); const parti = []; const centrale = []; let offset = 0;
    const le16 = n => [n & 255, (n >> 8) & 255], le32 = n => [n & 255, (n >> 8) & 255, (n >> 16) & 255, (n >>> 24) & 255];
    for (const [nome, testo] of Object.entries(file)) {
      const nomeB = enc.encode(nome), dati = enc.encode(testo), crc = CRC(dati);
      const loc = new Uint8Array([...le32(0x04034b50), ...le16(20), ...le16(0x0800), ...le16(0), ...le16(0), ...le16(0), ...le32(crc), ...le32(dati.length), ...le32(dati.length), ...le16(nomeB.length), ...le16(0), ...nomeB]);
      parti.push(loc, dati);
      centrale.push(new Uint8Array([...le32(0x02014b50), ...le16(20), ...le16(20), ...le16(0x0800), ...le16(0), ...le16(0), ...le16(0), ...le32(crc), ...le32(dati.length), ...le32(dati.length), ...le16(nomeB.length), ...le16(0), ...le16(0), ...le16(0), ...le16(0), ...le32(0), ...le32(offset), ...nomeB]));
      offset += loc.length + dati.length;
    }
    const dimC = centrale.reduce((s, c) => s + c.length, 0);
    const fine = new Uint8Array([...le32(0x06054b50), ...le16(0), ...le16(0), ...le16(centrale.length), ...le16(centrale.length), ...le32(dimC), ...le32(offset), ...le16(0)]);
    return new Blob([...parti, ...centrale, fine], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  }
  async function esporta(tipo, svgEl, o, vis, ids) {
    const nome = (o.titolo || 'grafico').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60);
    if (tipo === 'csv' || tipo === 'xlsx') {
      const righe = [['Data', 'Soggetto', 'Valore', 'Unità', 'Istituto', 'Interviste inizio', 'Interviste fine', 'Pubblicazione', 'Campione', 'Metodo', 'Stato', 'Fonte', 'Indirizzo', 'Nota metodologica']];
      for (const id of ids) for (const p of vis[id] || []) righe.push([p.data, nomeSogg(id), p.v, o.unita, p.r._ist, p.r.inizio, p.r.fine, p.r.pubblicato, p.r.campione, p.r.metodo, p.r.stato, (S.a.fonti[p.r.fonte] || {}).nome || p.r.fonte, (p.r.urls || [])[0], p.r.nota]);
      if (tipo === 'csv') scaricaFile(nome + '.csv', csvDa(righe), 'text/csv;charset=utf-8'); else scaricaFile(nome + '.xlsx', await xlsxDa(righe), '');
      return;
    }
    const clone = svgEl.cloneNode(true); clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg'); clone.querySelectorAll('[id^=zona]').forEach(z => z.remove());
    clone.querySelectorAll('text').forEach(t => { if (!t.getAttribute('font-family')) t.setAttribute('font-family', 'Plus Jakarta Sans, Arial, sans-serif'); });
    const src = new XMLSerializer().serializeToString(clone);
    if (tipo === 'svg') { scaricaFile(nome + '.svg', src, 'image/svg+xml'); return; }
    const img = new Image(); const url = URL.createObjectURL(new Blob([src], { type: 'image/svg+xml' }));
    img.onload = () => { const c = document.createElement('canvas'); c.width = 1720; c.height = 760; const ctx = c.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height); ctx.drawImage(img, 0, 0, c.width, c.height); c.toBlob(b => { scaricaFile(nome + '.png', b, 'image/png'); URL.revokeObjectURL(url); }, 'image/png'); };
    img.src = url;
  }

  carica();
})();
