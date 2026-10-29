/* Atlante dei dati: vista Partner. Matrici bilaterali FAOSTAT (commercio per paese partner, fertilizzanti per paese
   partner, aiuti per donatore): per un paese, un prodotto (o scopo), un elemento e un anno mostra i valori di ciascun
   partner sulla mappa e in tabella, con il contrassegno della fonte. Nessuna somma, saldo o stima: ogni numero è
   quello della riga originale; importazioni ed esportazioni restano elementi separati. */
(function (A) {
  'use strict';
  const $ = A.$, esc = A.esc, fmt = A.fmt;
  const briciole = (voci) => `<nav class="briciole" aria-label="Percorso">${voci.map((v, i) => (i ? '<svg viewBox="0 0 20 20"><path d="M7 4l6 6-6 6"/></svg>' : '') + (v.href ? `<a href="${v.href}">${esc(v.n)}</a>` : `<span>${esc(v.n)}</span>`)).join('')}</nav>`;
  let catalogo = null;
  const fileCache = {};
  A.caricaPartner = () => { if (!catalogo) catalogo = A.caricaJson('dati/partner.json'); return catalogo; };
  const caricaPaese = (ins, t) => { const k = ins + '/' + t; if (!fileCache[k]) fileCache[k] = A.caricaGz(`dati/partner/${ins}/${t}.json.gz`); return fileCache[k]; };

  // valore e contrassegno di un partner in un anno: null se la fonte non ha la riga
  const valoreAnno = (x, anno) => { if (!x) return null; const i = anno - x[0]; if (i < 0 || i >= x[1].length || x[2][i] === '-') return null; return { v: x[1][i], f: x[2][i] }; };

  A.pagine.partner = async (main, parti, q) => {
    main.innerHTML = '<div class="caricamento">Carico il catalogo delle matrici bilaterali…</div>';
    const C = await A.caricaPartner();
    const ins = C.insiemi.find((x) => x.k === parti[1]) || C.insiemi[0];
    if (parti[1] !== ins.k) A.sostituisci(`#/partner/${ins.k}`);
    const terr = new Map(ins.terr.map((t) => [t[0], { k: t[0], n: t[1], cod: t[2], oss: t[3], agg: !!t[4], iso: t[5] }]));
    const isoTerr = new Map(); ins.terr.forEach((t) => { if (t[5] && !t[4]) isoTerr.set(t[5], t[0]); });
    const voceP = ins.voceProdotto, ruoloP = ins.ruoloPartner;
    const st = { t: q.get('t'), p: q.get('p'), e: q.get('e'), a: +q.get('a') || null, ord: { col: 'v', dir: 'desc' } };
    const chiesto = st.t;
    if (!terr.has(st.t)) st.t = terr.has('ITA') ? 'ITA' : ins.terr.filter((t) => !t[4]).sort((x, y) => y[3] - x[3])[0][0];
    // territorio richiesto ma assente come dichiarante o destinatario: lo si dice, invece di cambiare paese in silenzio
    const nomeChiesto = chiesto && chiesto !== st.t ? (A.T[chiesto] ? A.T[chiesto].n : chiesto) : null;
    const comeDonatore = nomeChiesto && Object.values(ins.partner).some((x) => x[1] === chiesto);
    const avviso = nomeChiesto ? `<p class="avviso" style="margin-top:14px">${esc(nomeChiesto)} non è fra i ${ins.ruolo === 'destinatario' ? 'destinatari' : 'dichiaranti'} di questo insieme${comeDonatore ? `: compare come ${ruoloP}, quindi nelle tabelle degli altri paesi` : ''}. È mostrato ${esc(terr.get(st.t).n)}.</p>` : '';
    document.title = `${ins.n} · Partner · Atlante dei dati`;

    const nomePartner = (c) => (ins.partner[c] ? ins.partner[c][0] : `codice ${c}`);
    const unitaIt = (u) => (C.unita[u] != null ? C.unita[u] : u);
    const descrFlag = (f) => (C.flag[f] ? C.flag[f][0] : 'contrassegno della fonte');
    const sigla = (f) => (f === '_' ? '' : f);

    main.innerHTML = `<div class="entra" data-tema="arc">${briciole([{ n: 'Atlante', href: '#/' }, { n: 'Insiemi di dati', href: '#/archivi' }, { n: 'Partner' }])}
      <header class="tema-testa"><div class="tema-testa__riga">${A.icona('mappa')}<h1>${esc(ins.n)}</h1></div>
        <p>${esc(C.fonte)}, insieme di dati ${esc(ins.k)} (“${esc(ins.en)}”), lotto ${ins.lotto}, aggiornamento della fonte del ${A.data(ins.agg)}. Insieme completo: ${A.F.int.format(ins.oss)} osservazioni dal ${ins.anni[0]} al ${ins.anni[1]}, ${ins.terr.length} ${ins.ruolo === 'destinatario' ? 'destinatari' : 'dichiaranti'} e ${Object.keys(ins.partner).length} ${ruoloP === 'donatore' ? 'donatori' : 'partner'}. Scegli un ${ins.ruolo}, un ${voceP}, un elemento e un anno: la mappa colora ogni ${ruoloP} secondo il valore, la tabella riporta lo stesso valore con il contrassegno della fonte.</p>
        <p class="nota">L’Atlante non somma, non calcola saldi e non stima: ogni numero è quello pubblicato da FAOSTAT per la coppia ${ins.ruolo}–${ruoloP}. Importazioni ed esportazioni sono elementi distinti e restano separati; i dati dichiarati da un paese possono non coincidere con quelli dichiarati dal suo partner. Prodotti e scopi hanno il nome originale inglese della fonte.</p>
        <div class="segmenti" role="tablist" aria-label="Matrici bilaterali">${C.insiemi.map((x) => `<button role="tab" type="button" data-ins="${x.k}" aria-selected="${x.k === ins.k}">${esc(x.k)} · lotto ${x.lotto}</button>`).join('')}</div>
      </header>
      ${avviso}
      <div class="comandi" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-top:18px">
        <div class="campo"><label for="p-terr">${ins.ruolo === 'destinatario' ? 'Destinatario' : 'Paese dichiarante'}</label><div class="combo"><input id="p-terr" type="text" autocomplete="off"><span class="combo__freccia"></span><ul class="combo__lista" id="p-terr-lista" hidden></ul></div></div>
        <div class="campo"><label for="p-prod">${voceP === 'scopo' ? 'Scopo' : 'Prodotto'}</label><div class="combo"><input id="p-prod" type="text" autocomplete="off"><span class="combo__freccia"></span><ul class="combo__lista" id="p-prod-lista" hidden></ul></div></div>
        <div class="campo"><label for="p-elem">Elemento</label><div class="seleziona"><select id="p-elem"></select></div></div>
        <div class="campo"><label for="p-anno">Anno</label><div class="seleziona"><select id="p-anno"></select></div></div>
      </div>
      <div class="esplora__titolo"><h2 id="p-titolo" style="margin:18px 0 4px"></h2><p class="evidenza" id="p-evidenza" aria-live="polite"></p></div>
      <div class="grafico-card"><div class="scena"><div class="scena__corpo" id="p-mappa"></div><div class="legenda-mappa" id="p-legenda"></div><div class="scena__carico" id="p-carico">Carico i dati…</div></div></div>
      <div class="grafico-card" style="margin-top:14px"><div class="tabella" id="p-tabella" style="position:relative;max-height:620px" tabindex="0" role="region" aria-label="Tabella dei valori per ${esc(ruoloP)}"></div></div>
      <p class="nota" id="p-nota" style="margin-top:10px"></p>
    </div>`;

    main.querySelectorAll('[data-ins]').forEach((b) => b.addEventListener('click', () => A.vai(`#/partner/${b.dataset.ins}?t=${encodeURIComponent(st.t)}`)));

    let D = null; // file del paese scelto
    const serie = () => (D ? Object.keys(D.s) : []);
    const prodottiDi = () => [...new Set(serie().map((k) => k.split('|')[0]))].sort((a, b) => (ins.prod[a] || a).localeCompare(ins.prod[b] || b));
    const chiaviDi = (p) => serie().filter((k) => k.split('|')[0] === p).sort();
    const etichettaChiave = (k) => { const [, e] = k.split('|'); const el = ins.elem[e]; return `${el ? el[0] : e} (${unitaIt(D.u[k])})`; };
    const anniDi = (k) => { const s = new Set(); Object.values(D.s[k] || {}).forEach((x) => x[2].split('').forEach((f, i) => { if (f !== '-') s.add(x[0] + i); })); return [...s].sort((a, b) => a - b); };
    const chiave = () => (st.p != null && st.e != null ? serie().find((k) => k === `${st.p}|${st.e}` || k.startsWith(`${st.p}|${st.e}|`)) || null : null);
    const chiaveScelta = () => { const p = serie().find((k) => k === st.k); return p || chiave(); };

    /* ---- mappa ---- */
    const corpo = $('#p-mappa');
    const w = corpo.clientWidth || 800, hh = corpo.clientHeight || 480;
    const mondo = topojson.feature(A.GEO, A.GEO.objects[Object.keys(A.GEO.objects)[0]]);
    mondo.features = mondo.features.filter((f) => f.properties.id !== 'NE_ATA');
    const idMappa = (f) => { const k = f.properties.id; return !A.T[k] && k.startsWith('NE_') ? k.slice(3) : k; };
    const proj = d3.geoEqualEarth().fitExtent([[6, 6], [w - 6, hh - 6]], mondo);
    const path = d3.geoPath(proj);
    const svg = d3.select(corpo).append('svg').attr('class', 'mappa').attr('viewBox', `0 0 ${w} ${hh}`).attr('role', 'img');
    A.trama(svg.append('defs'), 'trama-p');
    const g = svg.append('g');
    const aree = g.append('g').selectAll('path').data(mondo.features).join('path').attr('d', path).attr('class', 'paese').style('vector-effect', 'non-scaling-stroke');
    const zoom = d3.zoom().scaleExtent([1, 28]).translateExtent([[-w * 0.5, -hh * 0.5], [w * 1.5, hh * 1.5]]).on('zoom', (e) => g.attr('transform', e.transform));
    svg.call(zoom);
    d3.select(corpo.parentNode).append('div').attr('class', 'zoom-nota').text('Rotellina, pizzico o doppio clic per ingrandire · trascina per spostare');
    const com = d3.select(corpo.parentNode).append('div').attr('class', 'comandi-mappa');
    const bottone = (et, ico, f) => com.append('button').attr('class', 'pulsante').attr('type', 'button').attr('aria-label', et).attr('title', et).html(A.icona(ico, '')).on('click', f);
    bottone('Ingrandisci', 'piu', () => svg.transition().duration(300).call(zoom.scaleBy, 1.6));
    bottone('Riduci', 'meno', () => svg.transition().duration(300).call(zoom.scaleBy, 1 / 1.6));
    bottone('Torna all’inquadratura iniziale', 'reset', () => svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity));

    let perIso = new Map(); // ISO3 del partner -> riga della tabella
    const righeAnno = () => {
      const k = chiaveScelta(); if (!k) return [];
      const nt = D.nt || {};
      return Object.entries(D.s[k]).map(([c, x]) => {
        const r = valoreAnno(x, st.a);
        const anni = x[2].split('').filter((f) => f !== '-').length;
        return { c, n: nomePartner(c), iso: ins.partner[c] ? ins.partner[c][1] : '', v: r ? r.v : null, f: r ? r.f : null, presente: !!r, anni, nota: (nt[`${k}|${c}`] || {})[st.a] || '' };
      });
    };

    const disegna = () => {
      const k = chiaveScelta();
      const t = terr.get(st.t);
      const righe = righeAnno().filter((r) => r.presente);
      const unita = k ? unitaIt(D.u[k]) : '';
      const el = k ? ins.elem[k.split('|')[1]] : null;
      $('#p-titolo').textContent = k ? `${t.n} · ${ins.prod[st.p] || st.p} · ${el ? el[0] : st.e}, ${st.a}` : t.n;
      svg.attr('aria-label', `Mappa dei ${ruoloP === 'donatore' ? 'donatori' : 'partner'} di ${t.n}${k ? `: ${ins.prod[st.p] || st.p}, ${el ? el[0] : ''}, ${st.a}, in ${unita}` : ''}. La tabella sotto la mappa riporta gli stessi valori.`);
      const conIso = righe.filter((r) => r.iso);
      perIso = new Map(); conIso.forEach((r) => { if (!perIso.has(r.iso)) perIso.set(r.iso, r); });
      const valori = conIso.map((r) => r.v).filter((v) => v != null).sort((a, b) => a - b);
      const positivi = valori.filter((v) => v > 0);
      const qn = (arr, p) => arr[Math.min(arr.length - 1, Math.max(0, Math.round(p * (arr.length - 1))))];
      const lg = positivi.length === valori.length && positivi.length > 2 && qn(positivi, 0.98) / qn(positivi, 0.02) > 100;
      const interp = d3.interpolateLab(A.colori.seq0, A.colori.seq1);
      const dom = valori.length ? (lg ? [qn(positivi, 0.02), qn(positivi, 0.98)] : [qn(valori, 0.02), qn(valori, 0.98)]) : [0, 1];
      if (dom[0] === dom[1]) { dom[0] = valori.length ? valori[0] : 0; dom[1] = valori.length ? valori[valori.length - 1] : 1; }
      const scala = (lg ? d3.scaleSequentialLog(interp) : d3.scaleSequential(interp)).domain(dom[0] < dom[1] ? dom : [dom[0], dom[0] + 1]).clamp(true);
      aree.each(function (f) {
        const id = idMappa(f), r = perIso.get(id), s = d3.select(this);
        const proprio = t.iso && id === t.iso;
        s.classed('paese--sel', proprio).style('fill', proprio ? A.colori.grafite : r ? (r.v == null ? 'url(#trama-p)' : (lg && r.v <= 0 ? A.colori.seq0 : scala(r.v))) : A.colori.altro);
      });
      aree.filter((f) => t.iso && idMappa(f) === t.iso).raise();
      const stops = d3.range(0, 1.01, 0.1).map((x) => `${interp(x)} ${x * 100}%`).join(',');
      $('#p-legenda').innerHTML = k ? `<div><strong>${esc(unita)}</strong></div><div class="legenda-mappa__barra" style="background:linear-gradient(90deg,${stops})"></div><div class="legenda-mappa__estremi"><span>${A.fmtAsse(scala.domain()[0])}${lg ? ' (log)' : ''}</span><span>${A.fmtAsse(scala.domain()[1])}</span></div><div class="legenda-mappa__riga"><span style="background:${A.colori.grafite}"></span>${esc(t.n)}</div><div class="legenda-mappa__riga"><span class="campione-vuoto"></span>riga senza valore numerico</div><div class="legenda-mappa__riga"><span style="background:${A.colori.altro}"></span>nessuna riga della fonte</div>` : '';
      const senzaIso = righe.filter((r) => !r.iso).length;
      $('#p-evidenza').innerHTML = k ? `${A.F.int.format(righe.length)} ${ruoloP === 'donatore' ? 'donatori' : 'partner'} con una riga della fonte nel ${st.a}${senzaIso ? `, di cui ${senzaIso} ${senzaIso === 1 ? 'non rappresentabile' : 'non rappresentabili'} sulla mappa (${ruoloP === 'donatore' ? 'organizzazioni, fondazioni, gruppi di paesi' : 'territori storici o senza codice ISO3'}): ${senzaIso === 1 ? 'compare' : 'compaiono'} solo in tabella` : ''}.` : 'Questo territorio non ha righe per la scelta fatta.';
      tabella();
      const fl = [...new Set(righe.map((r) => r.f).filter(Boolean))].sort();
      $('#p-nota').innerHTML = fl.length ? 'Contrassegni della fonte in questa tabella: ' + fl.map((f) => `<strong>${esc(f === '_' ? 'nessuno' : f)}</strong> ${esc(descrFlag(f))}`).join(' · ') + '. Fonte: <a href="' + esc(ins.url) + '" target="_blank" rel="noopener">file normalizzato FAOSTAT</a>.' : '';
    };

    const tabella = () => {
      const box = $('#p-tabella');
      const k = chiaveScelta();
      if (!k) { box.innerHTML = '<p class="nota" style="padding:12px">Nessuna riga per questa scelta.</p>'; return; }
      const unita = unitaIt(D.u[k]);
      const righe = righeAnno().filter((r) => r.presente);
      const conNote = righe.some((r) => r.nota);
      const { col, dir } = st.ord, s = dir === 'asc' ? 1 : -1;
      righe.sort((a, b) => { const x = a[col], y = b[col]; if (x == null && y == null) return a.n.localeCompare(b.n, 'it'); if (x == null) return 1; if (y == null) return -1; return typeof x === 'string' ? s * x.localeCompare(y, 'it') : s * (x - y); });
      const cols = [['n', ruoloP === 'donatore' ? 'Donatore' : 'Partner'], ['c', 'Codice FAOSTAT'], ['v', `Valore ${st.a} (${unita})`, true], ['f', 'Contrassegno della fonte'], ['anni', 'Anni con dato', true]].concat(conNote ? [['nota', 'Nota della fonte']] : []);
      const nd = '<span class="nd">n.d.</span>';
      box.innerHTML = `<table><caption class="visivo-nascosto">${esc(terr.get(st.t).n)}, ${esc(ins.prod[st.p] || st.p)}, ${esc(etichettaChiave(k))}, anno ${st.a}</caption><thead><tr>${cols.map(([c, n, num]) => `<th scope="col" class="${num ? 'num' : ''}" ${col === c ? `aria-sort="${dir === 'asc' ? 'ascending' : 'descending'}"` : ''}><button type="button" data-k="${c}">${esc(n)}</button></th>`).join('')}</tr></thead><tbody>${righe.map((r) => `<tr><td>${r.iso && isoTerr.has(r.iso) ? `<a href="#/partner/${ins.k}?t=${encodeURIComponent(isoTerr.get(r.iso))}&p=${encodeURIComponent(st.p)}&e=${encodeURIComponent(st.e)}&a=${st.a}" title="Vedi i partner di ${esc(r.n)}">${esc(r.n)}</a>` : esc(r.n)}</td><td class="anno-dato">${esc(r.c)}</td><td class="num"><strong>${r.v == null ? nd : fmt(r.v)}</strong></td><td>${r.f && r.f !== '_' ? `<abbr class="nota-flag" title="${esc(descrFlag(r.f))}">${esc(r.f)}</abbr> ${esc(descrFlag(r.f))}` : '<span class="nd">nessuno</span>'}</td><td class="num anno-dato">${r.anni}</td>${conNote ? `<td>${esc(r.nota)}</td>` : ''}</tr>`).join('')}</tbody></table>`;
      box.querySelectorAll('th button').forEach((b) => b.addEventListener('click', () => { const c = b.dataset.k; st.ord = { col: c, dir: st.ord.col === c ? (st.ord.dir === 'desc' ? 'asc' : 'desc') : (c === 'n' || c === 'c' || c === 'f' ? 'asc' : 'desc') }; tabella(); box.querySelector(`[data-k="${c}"]`).focus(); }));
    };

    aree.on('pointermove', (ev, f) => {
      const id = idMappa(f), r = perIso.get(id), t = terr.get(st.t), k = chiaveScelta();
      const nome = A.T[id] ? A.T[id].n : f.properties.n;
      let riga;
      if (t.iso && id === t.iso) riga = `<div class="suggerimento__vuoto">${ins.ruolo === 'destinatario' ? 'Destinatario scelto' : 'Paese dichiarante scelto'}</div>`;
      else if (r) riga = `<div class="suggerimento__riga"><span>${st.a}</span><strong>${r.v == null ? 'n.d.' : fmt(r.v)} ${esc(k ? unitaIt(D.u[k]) : '')}</strong></div>${r.f && r.f !== '_' ? `<div class="suggerimento__nota">${esc(r.f)}: ${esc(descrFlag(r.f))}</div>` : ''}${r.nota ? `<div class="suggerimento__nota">${esc(r.nota)}</div>` : ''}`;
      else riga = '<div class="suggerimento__vuoto">Nessuna riga della fonte per questa scelta</div>';
      const altro = isoTerr.has(id) && id !== t.iso ? `<div class="suggerimento__nota">Tocca per vedere i suoi ${ruoloP === 'donatore' ? 'donatori' : 'partner'}</div>` : '';
      A.mostraSuggerimento(ev, `<div class="suggerimento__nome">${esc(nome)}</div>${riga}${altro}`);
    }).on('pointerleave', (ev) => { if (ev.pointerType !== 'touch') A.nascondiSuggerimento(); })
      .on('click', (ev, f) => { const id = idMappa(f); if (isoTerr.has(id) && id !== terr.get(st.t).iso) { st.t = isoTerr.get(id); caricaTerritorio(); } });

    /* ---- comandi ---- */
    const inTerr = $('#p-terr'), inProd = $('#p-prod'), selEl = $('#p-elem'), selAnno = $('#p-anno');
    const voceTerr = (t) => ({ id: t.k, t, html: `<span>${esc(t.n)}</span><span class="tipo">${t.agg ? 'aggregato o non classificato' : esc(t.iso || t.k)}</span>` });
    A.combobox({ input: inTerr, lista: $('#p-terr-lista'), vuoto: 'Nessun territorio con questo nome',
      cerca: (qq) => { const nq = A.norm(qq); const tutti = [...terr.values()].filter((t) => !nq || A.norm(`${t.n} ${t.iso} ${t.k}`).includes(nq)).sort((a, b) => a.n.localeCompare(b.n, 'it')); return [{ titolo: 'Paesi e territori', voci: tutti.filter((t) => !t.agg).map(voceTerr) }, { titolo: 'Aggregati e non classificati della fonte', voci: tutti.filter((t) => t.agg).map(voceTerr) }]; },
      scegli: (v) => { st.t = v.t.k; caricaTerritorio(); } });
    inTerr.addEventListener('focus', () => inTerr.select());
    A.combobox({ input: inProd, lista: $('#p-prod-lista'), vuoto: 'Nessun elemento corrisponde',
      cerca: (qq) => { const parole = A.norm(qq).split(/\s+/).filter(Boolean); const voci = prodottiDi().filter((p) => parole.every((w) => A.norm(`${ins.prod[p] || ''} ${p}`).includes(w))).slice(0, 200).map((p) => ({ id: p, p, html: `<span>${esc(ins.prod[p] || p)}</span><span class="tipo">${esc(p)}</span>` })); return [{ titolo: '', voci }]; },
      scegli: (v) => { st.p = v.p; st.e = null; st.k = null; scegliSerie(); } });
    inProd.addEventListener('focus', () => inProd.select());
    selEl.addEventListener('change', () => { st.k = selEl.value; st.e = st.k.split('|')[1]; scegliSerie(); });
    selAnno.addEventListener('change', () => { st.a = +selAnno.value; aggiornaUrl(); disegna(); });

    const aggiornaUrl = () => A.sostituisci(`#/partner/${ins.k}?t=${encodeURIComponent(st.t)}&p=${encodeURIComponent(st.p ?? '')}&e=${encodeURIComponent(st.e ?? '')}&a=${st.a ?? ''}`);

    // sceglie prodotto, elemento e anno validi per il territorio: tiene i precedenti se esistono, altrimenti il prodotto
    // con più partner, il primo elemento e l'ultimo anno con dati
    const scegliSerie = () => {
      const prods = prodottiDi();
      if (!prods.length) { st.p = st.e = st.k = null; inProd.value = ''; selEl.innerHTML = ''; selAnno.innerHTML = ''; aggiornaUrl(); disegna(); return; }
      if (!prods.includes(st.p)) {
        const conta = {}; serie().forEach((k) => { const p = k.split('|')[0]; conta[p] = Math.max(conta[p] || 0, Object.keys(D.s[k]).length); });
        st.p = prods.slice().sort((a, b) => conta[b] - conta[a])[0];
      }
      inProd.value = ins.prod[st.p] || st.p;
      const chiavi = chiaviDi(st.p);
      let k = chiavi.find((x) => x === st.k) || chiavi.find((x) => x.split('|')[1] === st.e) || chiavi[0];
      st.k = k; st.e = k.split('|')[1];
      selEl.innerHTML = chiavi.map((x) => `<option value="${esc(x)}" ${x === k ? 'selected' : ''}>${esc(etichettaChiave(x))}</option>`).join('');
      const anni = anniDi(k);
      if (!anni.includes(st.a)) st.a = anni[anni.length - 1];
      selAnno.innerHTML = anni.slice().reverse().map((a) => `<option value="${a}" ${a === st.a ? 'selected' : ''}>${a}</option>`).join('');
      aggiornaUrl(); disegna();
    };

    const caricaTerritorio = async () => {
      const t = terr.get(st.t);
      inTerr.value = t.n;
      $('#p-carico').hidden = false;
      try { D = await caricaPaese(ins.k, st.t); } catch (e) { D = { s: {}, u: {} }; $('#p-evidenza').textContent = 'Non riesco a leggere il file di questo territorio.'; }
      $('#p-carico').hidden = true;
      scegliSerie();
    };
    st.k = null;
    await caricaTerritorio();
    return { distruggi: () => A.nascondiSuggerimento() };
  };
})(window.Atlante);
