/* Atlante dei dati: grafici. Andamento (linee con ingrandimento del periodo), Mappa (paesi, continenti,
   regioni europee), Classifica (barre animate) e Tabella. Ogni grafico riceve il contenitore e il contesto
   e restituisce { aggiorna(anima), selezione(), distruggi() }. */
(function (A) {
  'use strict';
  const G = A.grafici = {};
  const S = A.S;
  S.velocita = 800;
  const durata = () => (A.ridotto.matches ? 0 : S.inRiproduzione ? S.velocita * 0.92 : 550);
  A.durata = durata;
  const fmt = A.fmt, fmtAsse = A.fmtAsse, esc = A.esc;
  const spento = (id) => S.regione && A.T[id] && A.T[id].r !== S.regione;
  const tickLog = (scala, n) => scala.ticks(n).filter((v) => /^[125]/.test(String(v).replace(/^0\.0*/, '')));

  A.trama = (defs, id) => {
    const p = defs.append('pattern').attr('id', id).attr('patternUnits', 'userSpaceOnUse').attr('width', 5).attr('height', 5).attr('patternTransform', 'rotate(45)');
    p.append('rect').attr('width', 5).attr('height', 5).style('fill', A.colori.vuoto);
    p.append('line').attr('x1', 0).attr('x2', 0).attr('y1', 0).attr('y2', 5).style('stroke', A.colori.trama).style('stroke-width', 1.6);
  };

  /* ---------- ANDAMENTO ---------- */
  G.andamento = function (el, nav, ctx) {
    const cod = ctx.cod, d = A.dati(cod), univ = A.universo(cod);
    const W = el.clientWidth, H = el.clientHeight, stretto = W < 560;
    const m = { t: 22, r: stretto ? 92 : 160, b: 34, l: stretto ? 46 : 64 };
    const w = Math.max(60, W - m.l - m.r), h = Math.max(60, H - m.t - m.b);
    const lg = A.usaLog(cod);
    const rif = A.fam(cod) === 'wb' ? 'WLD' : A.fam(cod) === 'eu' ? 'EU:EU27_2020' : null;
    const scelti = [...new Set(S.sel.map((s) => A.idPer(cod, s)).filter((id) => id && d.d[id]))];
    const ids = scelti.concat(rif && !scelti.includes(rif) && d.d[rif] ? [rif] : []);
    const colore = (id) => (A.eAggregato(id) ? A.colori.grafite : A.coloreRegione(id));
    const pieno = [d.y0, Math.max(d.y1, d.y0 + 1)];
    const xBase = d3.scaleLinear().domain(pieno).range([0, w]);
    const dominio = () => (S.zoom && S.zoom[1] > S.zoom[0] ? [Math.max(pieno[0], S.zoom[0]), Math.min(pieno[1], S.zoom[1])] : pieno);
    const x = d3.scaleLinear().domain(dominio()).range([0, w]);
    const sfondo = S.sfondo ? univ.filter((p) => d.d[p.id] && !scelti.includes(p.id)) : [];

    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', `Andamento nel tempo: ${A.IND[cod].n}, dal ${d.y0} al ${d.y1}. La tabella offre gli stessi valori in forma testuale.`);
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);
    const clipId = 'clip-' + Math.random().toString(36).slice(2, 7);
    svg.append('defs').append('clipPath').attr('id', clipId).append('rect').attr('x', -2).attr('y', -6).attr('width', w + 4).attr('height', h + 8);
    const gx = g.append('g').attr('class', 'asse asse--base').attr('transform', `translate(0,${h})`);
    const gy = g.append('g').attr('class', 'asse');
    const area = g.append('rect').attr('width', w).attr('height', h).style('fill', 'transparent');
    const strati = g.append('g').attr('clip-path', `url(#${clipId})`);
    const fondo = strati.append('g'), primo = strati.append('g'), punti = strati.append('g');
    const cursore = g.append('line').attr('class', 'cursore-anno').attr('y1', 0).attr('y2', h).style('pointer-events', 'none');
    const mirino = g.append('line').attr('class', 'mirino').attr('y1', 0).attr('y2', h).style('opacity', 0).style('pointer-events', 'none');
    const etich = g.append('g');
    const linea = d3.line().defined((v) => v != null).x((v, i) => x(d.y0 + i)).y((v) => y(v));
    let y;
    const nota = d3.select(el).append('div').attr('class', 'zoom-nota');
    let sincronizza = null;

    const dominioY = () => {
      const [a, b] = x.domain();
      let lo = Infinity, hi = -Infinity;
      const scorri = (id) => { const arr = d.d[id]; if (!arr) return; for (let i = Math.max(0, Math.floor(a - d.y0)); i <= Math.min(arr.length - 1, Math.ceil(b - d.y0)); i++) { const v = arr[i]; if (v != null && (!lg || v > 0)) { if (v < lo) lo = v; if (v > hi) hi = v; } } };
      sfondo.forEach((p) => scorri(p.id)); ids.forEach(scorri);
      if (!isFinite(lo)) { lo = 0; hi = 1; }
      if (lo === hi) { lo -= 1; hi += 1; }
      return [lo, hi];
    };
    let prima = true;
    const disegna = (anima) => {
      x.domain(dominio());
      const [lo, hi] = dominioY();
      y = (lg ? d3.scaleLog().domain([lo / 1.1, hi * 1.1]) : d3.scaleLinear().domain([lo, hi]).nice()).range([h, 0]);
      const [a, b] = x.domain();
      gx.call(d3.axisBottom(x).ticks(Math.min(stretto ? 4 : 9, Math.max(1, Math.round(b - a)))).tickFormat(d3.format('d')).tickSizeOuter(0));
      gy.call(d3.axisLeft(y).tickValues(lg ? tickLog(y, 6) : y.ticks(stretto ? 5 : 7)).tickFormat(fmtAsse).tickSize(-w).tickPadding(8));
      const t = anima && durata() ? d3.transition().duration(360).ease(d3.easeCubicOut) : null;
      const f = fondo.selectAll('path').data(sfondo, (p) => p.id).join('path').attr('class', 'linea linea--fondo');
      (t ? f.transition(t) : f).attr('d', (p) => linea(d.d[p.id]));
      f.on('pointermove', (ev, p) => A.mostraSuggerimento(ev, A.intestazioneSug(p.id) + `<div class="suggerimento__nota">Tocca per aggiungere ai territori selezionati</div>`)).on('pointerleave', A.nascondiSuggerimento).on('click', (ev, p) => ctx.onSeleziona(p.id));
      const pr = primo.selectAll('path').data(ids, (id) => id).join('path').attr('class', (id) => 'linea' + (A.eAggregato(id) ? ' linea--rif' : '')).style('stroke', colore).style('opacity', (id) => (spento(id) && !A.eAggregato(id) ? 0.2 : 1));
      (t ? pr.transition(t) : pr).attr('d', (id) => linea(d.d[id]));
      if (prima && !A.ridotto.matches) {
        pr.each(function () { const L = this.getTotalLength(); d3.select(this).attr('stroke-dasharray', `${L} ${L}`).attr('stroke-dashoffset', L).transition().duration(900).ease(d3.easeCubicOut).attr('stroke-dashoffset', 0).on('end', function () { d3.select(this).attr('stroke-dasharray', null).attr('stroke-dashoffset', null); }); });
      }
      prima = false;
      // etichette alla fine della parte visibile di ogni linea
      const fine = ids.map((id) => { const arr = d.d[id]; let k = Math.min(arr.length - 1, Math.floor(b - d.y0)); while (k >= 0 && (arr[k] == null || d.y0 + k < a)) k--; return k < 0 ? null : { id, x: x(d.y0 + k), y: y(arr[k]), ty: y(arr[k]), v: arr[k] }; }).filter(Boolean).sort((p, q) => p.y - q.y);
      for (let k = 1; k < fine.length; k++) if (fine[k].ty - fine[k - 1].ty < 14) fine[k].ty = fine[k - 1].ty + 14;
      etich.selectAll('text').data(fine, (f2) => f2.id).join('text').attr('class', (f2) => 'etichetta-dato' + (A.eAggregato(f2.id) ? ' etichetta-dato--tenue' : ''))
        .attr('x', (f2) => Math.min(f2.x, w) + 6).attr('y', (f2) => f2.ty + 4).text((f2) => `${A.nomeRif(f2.id)} ${fmt(f2.v)}`).style('opacity', (f2) => (spento(f2.id) && !A.eAggregato(f2.id) ? 0.3 : 1));
      aggiornaAnno(false);
      nota.text(S.zoom ? `Periodo ${a}–${b} · doppio clic o pulsante per tornare all’intero periodo` : (stretto ? 'Pizzica, usa i pulsanti o il cursore sotto il grafico per ingrandire un periodo' : 'Rotellina, trascinamento o pulsanti per ingrandire un periodo'));
      if (sincronizza) sincronizza();
    };
    const aggiornaAnno = (anima) => {
      const [a, b] = x.domain();
      const dentro = S.anno >= a && S.anno <= b;
      cursore.style('opacity', dentro ? 1 : 0);
      const cx = x(Math.max(a, Math.min(b, S.anno)));
      (anima && durata() ? cursore.transition().duration(durata()).ease(d3.easeLinear) : cursore).attr('x1', cx).attr('x2', cx);
      const p = dentro ? ids.map((id) => ({ id, r: A.valore(d, id, S.anno) })).filter((o) => o.r && o.r.y === S.anno) : [];
      punti.selectAll('circle').data(p, (o) => o.id).join('circle').attr('r', 4.5).style('stroke', A.colori.carta).style('stroke-width', 2).style('fill', (o) => colore(o.id)).attr('cx', cx).attr('cy', (o) => y(o.r.v));
    };
    // passaggio del puntatore: mirino e valori di tutte le linee in evidenza
    area.on('pointermove', (ev) => {
      const [px] = d3.pointer(ev, g.node());
      const anno = Math.round(x.invert(px)); if (anno < d.y0 || anno > d.y1) return;
      mirino.attr('x1', x(anno)).attr('x2', x(anno)).style('opacity', 1);
      const righe = ids.map((id) => ({ id, v: d.d[id][anno - d.y0] })).sort((p, q) => (q.v ?? -Infinity) - (p.v ?? -Infinity));
      A.mostraSuggerimento(ev, `<div class="suggerimento__nome">${anno}</div>` + righe.map((o) => `<div class="suggerimento__riga"><span><span class="pallino" style="background:${colore(o.id)}"></span> ${esc(A.nomeRif(o.id))}</span><strong>${o.v == null ? 'n.d.' : fmt(o.v)}</strong></div>`).join('') + `<div class="suggerimento__nota">${esc(A.IND[cod].u)}</div>`);
    }).on('pointerleave', () => { mirino.style('opacity', 0); A.nascondiSuggerimento(); });
    // trascinamento con il mouse: ingrandisce il periodo scelto
    const pennello = d3.brushX().extent([[0, 0], [w, h]]).filter((ev) => ev.type === 'mousedown' && !ev.button).on('end', (ev) => {
      if (!ev.selection || !ev.sourceEvent) return;
      const [a, b] = ev.selection.map(x.invert).map(Math.round);
      g.select('.pennello').call(pennello.move, null);
      if (b - a >= 1) ctx.onZoom([a, b]);
    });
    const gp = g.append('g').attr('class', 'pennello').call(pennello);
    gp.select('.overlay').style('cursor', 'crosshair').style('pointer-events', 'none');
    gp.selectAll('.selection').style('fill', A.colori.grafite).style('fill-opacity', 0.08).style('stroke', 'none');
    // il rettangolo trasparente passa gli eventi del mouse al pennello
    const avviaPennello = (ev) => { const o = gp.select('.overlay').node(); if (o && !ev.button) { ev.preventDefault(); o.dispatchEvent(new MouseEvent('mousedown', ev)); } };
    area.on('mousedown', avviaPennello); strati.on('mousedown', avviaPennello);
    gp.on('mousemove', (ev) => area.dispatch('pointermove', { detail: ev }));
    svg.on('dblclick', () => ctx.onZoom(null));
    // rotellina, pizzico e trascinamento con due dita: ingrandiscono o spostano il periodo (il mouse trascina il pennello)
    let programmaticoZoom = false;
    const periodoDa = (tr) => {
      let [a, b] = tr.rescaleX(xBase).domain().map(Math.round);
      a = Math.max(pieno[0], a); b = Math.min(pieno[1], b);
      if (b - a < 2) { const c = Math.round((a + b) / 2); a = Math.max(pieno[0], c - 1); b = Math.min(pieno[1], a + 2); }
      return a <= pieno[0] && b >= pieno[1] ? null : [a, b];
    };
    const zx = d3.zoom().scaleExtent([1, Math.max(1, (pieno[1] - pieno[0]) / 2)]).extent([[0, 0], [w, h]]).translateExtent([[0, 0], [w, h]])
      .filter((ev) => ev.type === 'wheel' || ev.type.startsWith('touch'))
      .on('zoom', (ev) => { if (programmaticoZoom || !ev.sourceEvent) return; const z = periodoDa(ev.transform); const cur = S.zoom; if ((z && cur && z[0] === cur[0] && z[1] === cur[1]) || (!z && !cur)) return; ctx.onZoom(z); });
    g.call(zx);
    const sincronizzaZoom = () => {
      const [a, b] = dominio(); const k = (pieno[1] - pieno[0]) / Math.max(1, b - a);
      programmaticoZoom = true; g.call(zx.transform, d3.zoomIdentity.translate(-xBase(a) * k, 0).scale(k)); programmaticoZoom = false;
    };
    sincronizza = sincronizzaZoom;
    // pulsanti sul grafico: ingrandisce o riduce il periodo attorno al centro, torna all'intero periodo
    const com = d3.select(el).append('div').attr('class', 'comandi-mappa comandi-mappa--grafico');
    const zoomDi = (k) => { const [a0, a1] = dominio(); const c = (a0 + a1) / 2, half = Math.max(1, ((a1 - a0) / 2) * k); let na = Math.round(c - half), nb = Math.round(c + half); na = Math.max(pieno[0], na); nb = Math.min(pieno[1], nb); if (nb - na < 2) return; ctx.onZoom(na <= pieno[0] && nb >= pieno[1] ? null : [na, nb]); };
    const bottone = (et, ico, f) => com.append('button').attr('class', 'pulsante').attr('type', 'button').attr('aria-label', et).attr('title', et).html(A.icona(ico, '')).on('click', f);
    bottone('Ingrandisci il periodo', 'piu', () => zoomDi(0.6));
    bottone('Riduci', 'meno', () => zoomDi(1 / 0.6));
    bottone('Tutto il periodo', 'reset', () => ctx.onZoom(null));

    // navigatore sotto il grafico: miniserie di riferimento e cursore del periodo
    let brushNav = null, gNav = null, xNav = null, programmatico = false;
    if (nav) {
      nav.innerHTML = '';
      const Wn = nav.clientWidth || W, Hn = 52, mn = { l: m.l, r: m.r, t: 6, b: 16 };
      const wn = Math.max(60, Wn - mn.l - mn.r), hn = Hn - mn.t - mn.b;
      xNav = d3.scaleLinear().domain(pieno).range([0, wn]);
      const serieRif = d.d[rif] || d.d[scelti[0]] || Object.values(d.d)[0] || [];
      const vals = serieRif.filter((v) => v != null);
      const yn = d3.scaleLinear().domain(vals.length ? d3.extent(vals) : [0, 1]).range([hn, 0]);
      const sn = d3.select(nav).append('svg').attr('viewBox', `0 0 ${Wn} ${Hn}`).attr('aria-hidden', 'true');
      const gn = sn.append('g').attr('transform', `translate(${mn.l},${mn.t})`);
      gn.append('path').attr('d', d3.area().defined((v) => v != null).x((v, i) => xNav(d.y0 + i)).y0(hn).y1((v) => yn(v))(serieRif) || '').style('fill', A.colori.grafite).style('fill-opacity', 0.12);
      gn.append('g').attr('class', 'asse asse--base').attr('transform', `translate(0,${hn})`).call(d3.axisBottom(xNav).ticks(stretto ? 4 : 8).tickFormat(d3.format('d')).tickSizeOuter(0));
      brushNav = d3.brushX().extent([[0, 0], [wn, hn]]).on('brush end', (ev) => {
        if (programmatico || !ev.sourceEvent) return;
        if (!ev.selection) { if (ev.type === 'end') ctx.onZoom(null); return; }
        const [a, b] = ev.selection.map(xNav.invert).map(Math.round);
        if (b - a >= 1) { S.zoom = (a <= pieno[0] && b >= pieno[1]) ? null : [a, b]; disegna(false); if (ev.type === 'end') ctx.onZoom(S.zoom, true); }
      });
      gNav = gn.append('g').attr('class', 'pennello-nav').call(brushNav);
      gNav.selectAll('.handle').attr('rx', 3);
    }
    const sincronizzaNav = () => {
      if (!gNav) return;
      programmatico = true;
      const z = dominio();
      gNav.call(brushNav.move, S.zoom ? [xNav(z[0]), xNav(z[1])] : [xNav(pieno[0]), xNav(pieno[1])]);
      programmatico = false;
    };
    disegna(false); sincronizzaNav();
    return {
      aggiorna: (anima) => aggiornaAnno(anima),
      zoom: () => { disegna(true); sincronizzaNav(); },
      selezione: () => { ctx.ridisegna(); },
      distruggi: () => { A.nascondiSuggerimento(); },
    };
  };

  /* ---------- MAPPA ---------- */
  function puntiRiquadro(b) {
    const [x0, y0, x1, y1] = b, pts = [];
    for (let k = 0; k <= 10; k++) { const x = x0 + (x1 - x0) * k / 10, y = y0 + (y1 - y0) * k / 10; pts.push([x, y0], [x, y1], [x0, y], [x1, y]); }
    return { type: 'MultiPoint', coordinates: pts };
  }
  G.mappa = function (el, legendaEl, ctx) {
    const cod = ctx.cod, d = A.dati(cod), st = A.stat(cod), eu = A.fam(cod) === 'eu';
    const w = el.clientWidth, h = el.clientHeight;
    const lg = A.usaLog(cod);
    const interp = d3.interpolateLab(A.colori.seq0, A.colori.seq1);
    const scala = (lg ? d3.scaleSequentialLog(interp) : d3.scaleSequential(interp)).domain(st.p02 < st.p98 ? [st.p02, st.p98] : [st.min, st.max]).clamp(true);
    const mondo = topojson.feature(A.GEO, A.GEO.objects[Object.keys(A.GEO.objects)[0]]);
    mondo.features = mondo.features.filter((f) => f.properties.id !== 'NE_ATA');
    const inUniverso = new Set(A.universo(cod).map((t) => t.id));
    let regioni = null, proj;
    const chiave = (f) => { if (eu) return f.properties.key; const k = f.properties.id; return !A.T[k] && k.startsWith('NE_') && A.T[k.slice(3)] ? k.slice(3) : k; };
    if (eu) {
      const tutte = topojson.feature(A.GEO_NUTS, A.GEO_NUTS.objects[Object.keys(A.GEO_NUTS.objects)[0]]).features;
      regioni = tutte.filter((f) => f.properties.l === S.livello && (!S.paeseEU || f.properties.c === S.paeseEU));
      regioni.forEach((f) => { f.properties.key = 'EU:' + f.properties.id; });
      proj = d3.geoAzimuthalEqualArea().rotate([-10, -52]);
      if (S.paeseEU) {
        const vicine = regioni.filter((f) => { const c = d3.geoCentroid(f); return c[0] > -25 && c[1] > 27; });
        proj.fitExtent([[10, 10], [w - 10, h - 10]], { type: 'FeatureCollection', features: vicine.length ? vicine : regioni });
      } else proj.fitExtent([[6, 6], [w - 6, h - 6]], puntiRiquadro([-24, 34.5, 42, 70.5]));
    } else {
      proj = d3.geoEqualEarth();
      const a = A.AREE[S.area] || A.AREE.mondo;
      if (a.b) { if (S.area === 'oceania') proj.rotate([-150, 0]); proj.fitExtent([[6, 6], [w - 6, h - 6]], puntiRiquadro(a.b)); }
      else proj.fitExtent([[6, 6], [w - 6, h - 6]], mondo);
    }
    const path = d3.geoPath(proj);
    const svg = d3.select(el).append('svg').attr('class', 'mappa').attr('viewBox', `0 0 ${w} ${h}`).attr('role', 'img')
      .attr('aria-label', `Mappa${eu ? ' delle regioni europee' : ''}: ${A.IND[cod].n}. La tabella offre gli stessi valori in forma testuale.`);
    A.trama(svg.append('defs'), 'trama');
    const g = svg.append('g');
    const sfondo = g.append('g').selectAll('path').data(mondo.features).join('path').attr('d', path)
      .attr('class', (f) => 'paese' + (!eu && inUniverso.has(chiave(f)) ? '' : ' paese--altro')).style('vector-effect', 'non-scaling-stroke');
    const aree = eu ? g.append('g').selectAll('path').data(regioni).join('path').attr('d', path).attr('class', 'paese').style('vector-effect', 'non-scaling-stroke') : sfondo.filter((f) => inUniverso.has(chiave(f)));
    if (eu) sfondo.style('pointer-events', 'none');
    const colora = (anima) => {
      aree.each(function (f) {
        const r = A.valore(d, chiave(f), S.anno), s = d3.select(this), c = r ? scala(r.v) : 'url(#trama)';
        if (anima && r && durata()) s.transition().duration(durata()).ease(S.inRiproduzione ? d3.easeLinear : d3.easeCubicOut).style('fill', c);
        else s.interrupt().style('fill', c);
      });
    };
    const selezione = () => {
      aree.classed('paese--sel', (f) => A.selezionato(cod, chiave(f))).style('opacity', (f) => (spento(chiave(f)) ? 0.22 : 1));
      aree.filter((f) => A.selezionato(cod, chiave(f))).raise();
    };
    aree.on('pointermove', (ev, f) => {
      const id = chiave(f);
      if (!A.T[id]) { A.mostraSuggerimento(ev, `<div class="suggerimento__nome">${esc(f.properties.n)}</div><div class="suggerimento__vuoto">Codice non presente nei dati</div>`); return; }
      A.mostraSuggerimento(ev, A.intestazioneSug(id) + A.rigaValore(cod, id) + `<div class="suggerimento__nota">${A.selezionato(cod, id) ? 'Selezionato: tocca per togliere' : 'Tocca per selezionare'}</div>`);
    }).on('pointerleave', (ev) => { if (ev.pointerType !== 'touch') A.nascondiSuggerimento(); })
      .on('click', (ev, f) => { if (A.T[chiave(f)]) ctx.onSeleziona(chiave(f)); });
    if (!eu) sfondo.filter((f) => !inUniverso.has(chiave(f))).on('pointermove', (ev, f) => A.mostraSuggerimento(ev, `<div class="suggerimento__nome">${esc(f.properties.n)}</div><div class="suggerimento__vuoto">${A.fam(cod) === 'arc' ? 'Non presente nell’archivio parziale del repository' : 'Territorio non presente nei dati della Banca Mondiale'}</div>`)).on('pointerleave', A.nascondiSuggerimento);
    const zoom = d3.zoom().scaleExtent([1, 28]).translateExtent([[-w * 0.5, -h * 0.5], [w * 1.5, h * 1.5]]).on('zoom', (e) => g.attr('transform', e.transform));
    svg.call(zoom);
    d3.select(el).append('div').attr('class', 'zoom-nota').text('Rotellina, pizzico o doppio clic per ingrandire · trascina per spostare');
    const com = d3.select(el).append('div').attr('class', 'comandi-mappa');
    const bottone = (et, ico, f) => com.append('button').attr('class', 'pulsante').attr('type', 'button').attr('aria-label', et).attr('title', et).html(A.icona(ico, '')).on('click', f);
    bottone('Ingrandisci', 'piu', () => svg.transition().duration(300).call(zoom.scaleBy, 1.6));
    bottone('Riduci', 'meno', () => svg.transition().duration(300).call(zoom.scaleBy, 1 / 1.6));
    bottone('Torna all’inquadratura iniziale', 'reset', () => svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity));
    // legenda dentro la mappa
    if (legendaEl) {
      const stops = d3.range(0, 1.01, 0.1).map((t) => `${scala.interpolator()(t)} ${t * 100}%`).join(',');
      legendaEl.innerHTML = `<div><strong>${esc(A.IND[cod].u)}</strong></div><div class="legenda-mappa__barra" style="background:linear-gradient(90deg,${stops})"></div><div class="legenda-mappa__estremi"><span>${fmtAsse(scala.domain()[0])}${lg ? ' (log)' : ''}</span><span>${fmtAsse(scala.domain()[1])}</span></div><div class="legenda-mappa__riga"><span class="campione-vuoto"></span>dato mancante</div><div class="legenda-mappa__riga"><span style="background:${A.colori.altro}"></span>${A.fam(cod) === 'arc' ? 'non nel repository' : 'fuori dai dati'}</div>`;
    }
    colora(false); selezione();
    return { aggiorna: colora, selezione, scala, distruggi: () => A.nascondiSuggerimento() };
  };

  /* ---------- CLASSIFICA ---------- */
  G.classifica = function (el, ctx) {
    const cod = ctx.cod, d = A.dati(cod), st = A.stat(cod), univ = A.universo(cod);
    const box = document.createElement('div'); box.className = 'barre'; el.appendChild(box);
    const ol = document.createElement('ol'); ol.className = 'barre__lista'; ol.setAttribute('aria-label', `${A.IND[cod].n}, classifica`); box.appendChild(ol);
    const lo = Math.min(0, st.min), hi = Math.max(0, st.max);
    const pct = (v) => ((v - lo) / (hi - lo || 1)) * 100;
    const righe = new Map(), PASSO = 32;
    const sep = document.createElement('li'); sep.className = 'barre__separatore'; sep.setAttribute('aria-hidden', 'true'); sep.innerHTML = '<span>Selezionati fuori classifica</span>';
    const aggiorna = () => {
      const tutti = univ.map((p) => ({ id: p.id, r: A.valore(d, p.id, S.anno) })).filter((o) => o.r).sort((a, b) => (S.ordine === 'desc' ? b.r.v - a.r.v : a.r.v - b.r.v));
      const N = S.nBarre === 'tutti' ? tutti.length : Math.min(+S.nBarre || 25, tutti.length);
      const vis = tutti.slice(0, N);
      const extra = tutti.slice(N).filter((o) => A.selezionato(cod, o.id));
      const elenco = vis.map((o, k) => ({ ...o, pos: k, rank: k + 1 })).concat(extra.map((o, k) => ({ ...o, pos: N + 1 + k, rank: tutti.indexOf(o) + 1 })));
      const vivi = new Set(elenco.map((o) => o.id));
      for (const [id, li] of righe) if (!vivi.has(id)) { li.remove(); righe.delete(id); }
      elenco.forEach((o) => {
        let li = righe.get(o.id);
        if (!li) {
          li = document.createElement('li'); li.className = 'barra';
          li.innerHTML = `<button type="button"><span class="barra__nome"></span><span class="barra__traccia"><span class="barra__riempimento"></span><span class="barra__valore"></span></span></button>`;
          li.style.transform = `translateY(${o.pos * PASSO}px)`;
          li.querySelector('button').addEventListener('click', () => ctx.onSeleziona(o.id));
          li.querySelector('button').addEventListener('pointermove', (ev) => A.mostraSuggerimento(ev, A.intestazioneSug(o.id) + A.rigaValore(cod, o.id)));
          li.querySelector('button').addEventListener('pointerleave', A.nascondiSuggerimento);
          ol.appendChild(li); righe.set(o.id, li);
        }
        const sel = A.selezionato(cod, o.id);
        li.classList.toggle('barra--sel', sel); li.classList.toggle('barra--spenta', !!spento(o.id));
        li.querySelector('button').setAttribute('aria-pressed', sel ? 'true' : 'false');
        li.querySelector('button').setAttribute('aria-label', `${o.rank}° ${A.T[o.id].n}: ${fmt(o.r.v)} ${A.IND[cod].u}${o.r.y !== S.anno ? `, dato del ${o.r.y}` : ''}. ${sel ? 'Selezionato' : 'Seleziona'}`);
        li.querySelector('.barra__nome').textContent = `${o.rank}. ${A.T[o.id].n}`;
        const f = li.querySelector('.barra__riempimento'), z = pct(0), p = pct(o.r.v);
        f.style.marginLeft = `calc((100% - 76px) * ${Math.min(z, p) / 100})`; f.style.width = `calc((100% - 76px) * ${Math.abs(p - z) / 100})`;
        f.style.backgroundColor = A.coloreRegione(o.id);
        li.querySelector('.barra__valore').textContent = fmt(o.r.v) + (o.r.y !== S.anno ? ` (${o.r.y})` : '');
        li.style.transform = `translateY(${o.pos * PASSO}px)`;
        li.style.transitionDuration = durata() + 'ms'; f.style.transitionDuration = durata() + 'ms';
      });
      if (extra.length) { sep.style.top = (N * PASSO + PASSO / 2 - 2) + 'px'; ol.appendChild(sep); } else sep.remove();
      ol.style.height = (elenco.length + (extra.length ? 1 : 0)) * PASSO + 'px';
      if (!elenco.length) ol.innerHTML = `<li class="nota" style="padding:24px">Nessun territorio ha un valore nel ${S.anno}.</li>`;
    };
    aggiorna();
    return { aggiorna, selezione: aggiorna, distruggi: () => A.nascondiSuggerimento() };
  };

  /* ---------- TABELLA ---------- */
  G.tabella = function (el, ctx) {
    const cod = ctx.cod, d = A.dati(cod), eu = A.fam(cod) === 'eu';
    const box = document.createElement('div'); box.className = 'tabella'; box.tabIndex = 0; box.setAttribute('role', 'region'); box.setAttribute('aria-label', 'Tabella dei valori'); el.appendChild(box);
    const conf = () => (S.anno - 10 >= d.y0 ? S.anno - 10 : d.y0);
    const cols = [
      { k: 'sel', t: '<span class="visivo-nascosto">Selezione</span>' }, { k: 'n', t: 'Territorio' }, { k: 'r', t: eu ? 'Paese' : 'Regione' },
      { k: 'v', t: () => `Valore ${S.anno}`, num: true }, { k: 'y', t: 'Anno del dato', num: true },
      { k: 'c', t: () => `Valore ${conf()}`, num: true }, { k: 'dv', t: 'Variazione', num: true }, { k: 'pos', t: 'Posizione', num: true },
    ];
    const tab = document.createElement('table');
    const cap = document.createElement('caption'); cap.className = 'visivo-nascosto'; tab.appendChild(cap);
    const thead = tab.createTHead(), tbody = tab.createTBody(); box.appendChild(tab);
    const gruppo = (t) => (eu ? (t.p && A.T[t.p] ? A.T[t.p].n : 'aggregato') : A.eAggregato(t.id) ? 'aggregato' : t.r ? A.REG[t.r].n : 'non classificata');
    const aggiorna = () => {
      cap.textContent = `${A.IND[cod].n}, ${A.IND[cod].u}, anno ${S.anno}`;
      let insieme = A.universo(cod);
      // se nessun paese ha dati (serie di soli aggregati, tipica dei lotti parziali) gli aggregati compaiono comunque
      if (S.aggregati || !insieme.some((t) => d.d[t.id])) insieme = insieme.concat(A.aggregatiDi(cod));
      const righe = insieme.map((t) => { const r = A.valore(d, t.id, S.anno), c = d.d[t.id] ? d.d[t.id][conf() - d.y0] : null; return { t, v: r ? r.v : null, y: r ? r.y : null, c: c ?? null, dv: r && c != null ? r.v - c : null }; });
      righe.filter((o) => o.v != null && !A.eAggregato(o.t.id)).sort((a, b) => b.v - a.v).forEach((o, k) => { o.pos = k + 1; });
      const { col, dir } = S.ordTab, s = dir === 'asc' ? 1 : -1;
      const chiave = (o) => (col === 'n' ? o.t.n : col === 'r' ? gruppo(o.t) : col === 'sel' ? (A.selezionato(cod, o.t.id) ? 0 : 1) : o[col]);
      righe.sort((a, b) => { const x = chiave(a), y = chiave(b); if (x == null && y == null) return a.t.n.localeCompare(b.t.n, 'it'); if (x == null) return 1; if (y == null) return -1; return typeof x === 'string' ? s * x.localeCompare(y, 'it') : s * (x - y); });
      thead.innerHTML = '<tr>' + cols.map((c) => `<th scope="col" class="${c.num ? 'num' : ''}" ${S.ordTab.col === c.k ? `aria-sort="${dir === 'asc' ? 'ascending' : 'descending'}"` : ''}><button type="button" data-k="${c.k}">${typeof c.t === 'function' ? c.t() : c.t}</button></th>`).join('') + '</tr>';
      thead.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => { const k = b.dataset.k; S.ordTab = { col: k, dir: S.ordTab.col === k ? (S.ordTab.dir === 'desc' ? 'asc' : 'desc') : (k === 'n' || k === 'r' || k === 'pos' ? 'asc' : 'desc') }; aggiorna(); thead.querySelector(`[data-k="${k}"]`).focus(); }));
      const nd = '<span class="nd">n.d.</span>';
      tbody.innerHTML = righe.map((o) => {
        const sel = A.selezionato(cod, o.t.id), dv = o.dv == null ? nd : (o.dv > 0 ? '+' : o.dv < 0 ? '−' : '') + fmt(Math.abs(o.dv));
        const nota = o.v == null ? null : A.notaDi(cod, o.t.id, o.y), flag = nota ? ` <abbr class="nota-flag" title="${esc(nota)}">${esc(nota.split(':')[0].slice(0, 4))}</abbr>` : '';
        return `<tr class="${sel ? 'riga--sel' : ''} ${A.eAggregato(o.t.id) ? 'agg' : ''}" style="${spento(o.t.id) ? 'opacity:.4' : ''}">
          <td><input type="checkbox" data-id="${esc(o.t.id)}" ${sel ? 'checked' : ''} aria-label="Seleziona ${esc(o.t.n)}"></td>
          <td><span class="pallino" style="background:${A.coloreRegione(o.t.id)}"></span> <a href="#/t/${esc(o.t.id)}">${esc(o.t.n)}</a>${eu && o.t.cod ? ` <span class="anno-dato">${esc(o.t.cod)}</span>` : ''}</td>
          <td>${esc(gruppo(o.t))}</td><td class="num"><strong>${o.v == null ? nd : fmt(o.v)}</strong>${flag}</td><td class="num anno-dato">${o.y ?? nd}</td>
          <td class="num">${o.c == null ? nd : fmt(o.c)}</td><td class="num">${dv}</td><td class="num">${o.pos ?? '<span class="nd">·</span>'}</td></tr>`;
      }).join('');
      tbody.querySelectorAll('input[type="checkbox"]').forEach((c) => c.addEventListener('change', () => ctx.onSeleziona(c.dataset.id)));
    };
    aggiorna();
    return { aggiorna, selezione: aggiorna, distruggi: () => {} };
  };

  /* ---------- CSV ---------- */
  A.scaricaCsv = (cod) => {
    const d = A.dati(cod), i = A.IND[cod];
    const righe = [['territorio', 'codice', 'indicatore', 'unita', 'anno', 'valore']];
    const insieme = A.universo(cod).concat(A.aggregatiDi(cod));
    insieme.forEach((t) => { const a = d.d[t.id]; if (!a) return; a.forEach((v, k) => { if (v != null) righe.push([t.n, t.id, i.n, i.u, d.y0 + k, String(v).replace('.', ',')]); }); });
    const testo = '﻿' + righe.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\r\n');
    const blob = new Blob([testo], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `atlante_${cod.replace(/[^A-Za-z0-9_.-]+/g, '_')}.csv`; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  };
})(window.Atlante);
