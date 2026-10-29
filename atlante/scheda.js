/* Scheda "Italia e Friuli Venezia Giulia a confronto con l'Europa".
   Ogni numero del testo è letto dai file di dati dell'Atlante al caricamento della pagina. */
(function () {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const FVG = 'EU:ITH4', IT = 'EU:IT', UE = 'EU:EU27_2020';
  const VICINI = ['EU:ITH3', 'EU:AT21', 'EU:SI04'];
  const PROVINCE = ['EU:ITH41', 'EU:ITH42', 'EU:ITH43', 'EU:ITH44'];
  const NOMI = { 'EU:ITH4': 'Friuli Venezia Giulia', 'EU:IT': 'Italia', 'EU:EU27_2020': 'Unione europea a 27', 'EU:ITH3': 'Veneto', 'EU:AT21': 'Carinzia', 'EU:SI04': 'Slovenia occidentale', ITA: 'Italia', EUU: 'Unione europea', WLD: 'Mondo' };
  // nomi brevi per i grafici su schermi stretti; la sigla FVG è sciolta nel titolo della pagina
  const CORTI = { 'EU:ITH4': 'FVG', 'EU:EU27_2020': 'UE a 27', 'EU:SI04': 'Slovenia occ.' };
  const nf = (o) => new Intl.NumberFormat('it-IT', o);
  const F = { int: nf({ maximumFractionDigits: 0, useGrouping: 'always' }), d1: nf({ minimumFractionDigits: 1, maximumFractionDigits: 1 }), d2: nf({ minimumFractionDigits: 2, maximumFractionDigits: 2 }), s3: nf({ maximumSignificantDigits: 3 }) };
  function fmt(v, dec) {
    if (v == null) return 'n.d.';
    if (v < 0) return '−' + fmt(-v, dec);
    if (dec === 1) return F.d1.format(v);
    if (dec === 2) return F.d2.format(v);
    const a = Math.abs(v);
    if (a >= 1e6) { const t = F.s3.format(v / 1e6); return t + (t === '1' ? ' milione' : ' milioni'); }
    if (a >= 1000) return F.int.format(v);
    return F.s3.format(v);
  }
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let T = {}, colori = {};

  const carica = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); });
  // ultimo anno con dato per un territorio, oppure il valore di un anno preciso
  function ultimo(d, id) { const a = d.d[id]; if (!a) return null; for (let i = a.length - 1; i >= 0; i--) if (a[i] != null) return { y: d.y0 + i, v: a[i] }; return null; }
  function in_(d, id, y) { const a = d.d[id]; const i = y - d.y0; return a && i >= 0 && i < a.length && a[i] != null ? a[i] : null; }
  const nome = (id) => NOMI[id] || (T[id] ? T[id].n : id);
  function leggiColori() {
    const cs = getComputedStyle(document.documentElement), g = (n) => cs.getPropertyValue(n).trim();
    colori = { grafite: g('--grafite'), carta: g('--carta'), seq0: g('--seq-0'), seq1: g('--seq-1'), altro: g('--carta-3'), griglia: g('--griglia'),
      serie: [g('--c1'), g('--c2'), g('--c3'), g('--c4'), g('--c5'), g('--c6')] };
  }
  // colori fissi per territorio in tutta la scheda
  const COL = { 'EU:ITH4': 0, 'EU:IT': 1, 'EU:EU27_2020': -1, 'EU:ITH3': 2, 'EU:AT21': 3, 'EU:SI04': 4 };
  const colore = (id) => (COL[id] === -1 ? colori.grafite : colori.serie[COL[id] ?? 5]);

  // classifica fra le regioni NUTS 2 con il dato nell'anno y (1 = valore più alto)
  function posizione(d, id, y, regioni) {
    const v = regioni.map((t) => ({ id: t.id, v: in_(d, t.id, y) })).filter((o) => o.v != null).sort((a, b) => b.v - a.v);
    return { k: v.findIndex((o) => o.id === id) + 1, n: v.length, valori: v };
  }

  /* ---------- grafici ---------- */
  function linee(el, d, ids, opz = {}) {
    el.innerHTML = '';
    const W = el.clientWidth, H = el.clientHeight, stretto = W < 520;
    const m = { t: 14, r: Math.min(200, Math.max(110, W * 0.34)), b: 28, l: 44 };
    const w = W - m.l - m.r, h = H - m.t - m.b;
    const serie = ids.filter((id) => d.d[id]).map((id) => ({ id, p: d.d[id].map((v, i) => ({ y: d.y0 + i, v })).filter((o) => o.v != null) }));
    const anni = d3.extent(serie.flatMap((s) => s.p.map((o) => o.y)));
    const vals = serie.flatMap((s) => s.p.map((o) => o.v));
    const x0 = d3.scaleLinear().domain(anni).range([0, w]);
    const y = d3.scaleLinear().domain(opz.zero ? [0, d3.max(vals)] : d3.extent(vals)).nice().range([h, 0]);
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', opz.etichetta || 'Grafico a linee');
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);
    const clipId = 'clip-' + Math.random().toString(36).slice(2, 7);
    svg.append('defs').append('clipPath').attr('id', clipId).append('rect').attr('x', -2).attr('y', -6).attr('width', w + 4).attr('height', h + 8);
    const gx = g.append('g').attr('class', 'asse asse--base').attr('transform', `translate(0,${h})`);
    g.append('g').attr('class', 'asse').call(d3.axisLeft(y).ticks(5).tickSize(-w).tickPadding(6).tickFormat((v) => (Math.abs(v) >= 1000 ? F.int.format(v) : F.s3.format(v))));
    g.append('rect').attr('width', w).attr('height', h).style('fill', 'transparent');
    const strati = g.append('g').attr('clip-path', `url(#${clipId})`);
    const col = opz.colore || ((s) => colore(s.id));
    const disegna = (x) => {
      const [a, b] = x.domain();
      gx.call(d3.axisBottom(x).ticks(Math.min(stretto ? 4 : 8, Math.max(1, Math.round(b - a)))).tickFormat(d3.format('d')).tickSizeOuter(0));
      const linea = d3.line().x((o) => x(o.y)).y((o) => y(o.v));
      strati.selectAll('path.l').data(serie).join('path').attr('class', (s) => 'l linea' + (s.id === UE ? ' linea--mondo' : '')).attr('d', (s) => linea(s.p))
        .style('stroke', col).style('stroke-width', (s) => (s.id === FVG || opz.spesse ? 3 : 2));
      const fine = serie.map((s) => { const vis = s.p.filter((o) => o.y >= a && o.y <= b); const o = vis[vis.length - 1]; return o ? { s, x: x(o.y), y: y(o.v), ty: y(o.v), v: o.v } : null; }).filter(Boolean).sort((p, q) => p.y - q.y);
      for (let k = 1; k < fine.length; k++) if (fine[k].ty - fine[k - 1].ty < 15) fine[k].ty = fine[k - 1].ty + 15;
      g.selectAll('circle').data(fine, (f) => f.s.id).join('circle').attr('cx', (f) => f.x).attr('cy', (f) => f.y).attr('r', 4).style('fill', (f) => col(f.s)).style('stroke', colori.carta).style('stroke-width', 2);
      g.selectAll('text.e').data(fine, (f) => f.s.id).join('text').attr('class', (f) => 'e etichetta-dato' + (f.s.id === FVG ? '' : ' etichetta-dato--tenue'))
        .attr('x', (f) => f.x + 8).attr('y', (f) => f.ty + 4).text((f) => `${opz.nome ? opz.nome(f.s) : (stretto && CORTI[f.s.id]) || nome(f.s.id)} ${fmt(f.v, opz.dec)}`);
    };
    // ingrandimento del periodo: rotellina, pizzico, trascinamento, pulsanti; doppio clic per tornare all'intero periodo
    const zx = d3.zoom().scaleExtent([1, Math.max(1, (anni[1] - anni[0]) / 2)]).extent([[0, 0], [w, h]]).translateExtent([[0, 0], [w, h]])
      .on('zoom', (ev) => { const x = ev.transform.rescaleX(x0); disegna(x); });
    g.call(zx).on('dblclick.zoom', null);
    svg.on('dblclick', () => g.transition().duration(300).call(zx.transform, d3.zoomIdentity));
    const com = d3.select(el).append('div').attr('class', 'comandi-mappa comandi-mappa--grafico');
    const bottone = (et, ico, f) => com.append('button').attr('class', 'pulsante').attr('type', 'button').attr('aria-label', et).attr('title', et).html(window.Atlante.icona(ico, '')).on('click', f);
    bottone('Ingrandisci il periodo', 'piu', () => g.transition().duration(300).call(zx.scaleBy, 1.6));
    bottone('Riduci', 'meno', () => g.transition().duration(300).call(zx.scaleBy, 1 / 1.6));
    bottone('Tutto il periodo', 'reset', () => g.transition().duration(300).call(zx.transform, d3.zoomIdentity));
    disegna(x0);
  }

  function sciame(el, d, y, regioni, evid) {
    el.innerHTML = '';
    const W = el.clientWidth, H = el.clientHeight;
    const m = { t: 30, r: 20, b: 34, l: 20 }, w = W - m.l - m.r, h = H - m.t - m.b;
    const punti = regioni.map((t) => ({ id: t.id, v: in_(d, t.id, y) })).filter((o) => o.v != null);
    const x = d3.scaleLinear().domain(d3.extent(punti, (o) => o.v)).nice().range([0, w]);
    const r = 3.4, cy = h / 2;
    punti.sort((a, b) => a.v - b.v).forEach((p) => { p.px = x(p.v); });
    const messi = [];
    for (const p of punti) {
      for (let k = 0; k < 300; k++) {
        const c = k === 0 ? 0 : Math.ceil(k / 2) * r * 0.9 * (k % 2 ? -1 : 1);
        if (!messi.some((q) => Math.abs(q.px - p.px) < 2 * r + 1 && (q.px - p.px) ** 2 + (q.py - (cy + c)) ** 2 < (2 * r + 0.6) ** 2)) { p.py = Math.max(r, Math.min(h - r, cy + c)); break; }
      }
      if (p.py == null) p.py = cy;
      messi.push(p);
    }
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', 'Distribuzione delle regioni europee');
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);
    g.append('g').attr('class', 'asse').attr('transform', `translate(0,${h})`).call(d3.axisBottom(x).ticks(8).tickSize(-h).tickPadding(6).tickFormat((v) => F.s3.format(v)));
    const med = d3.median(punti, (o) => o.v);
    g.append('line').attr('class', 'mediana-linea').attr('x1', x(med)).attr('x2', x(med)).attr('y1', -10).attr('y2', h);
    g.append('text').attr('class', 'etichetta-dato etichetta-dato--tenue').attr('x', x(med)).attr('y', -14).attr('text-anchor', 'middle').text(`mediana ${fmt(med, 1)}`);
    g.selectAll('circle').data(punti).join('circle').attr('cx', (p) => p.px).attr('cy', (p) => p.py).attr('r', (p) => (evid.includes(p.id) ? r + 2.6 : r))
      .style('fill', (p) => (evid.includes(p.id) ? colore(p.id) : colori.grafite)).style('fill-opacity', (p) => (evid.includes(p.id) ? 1 : 0.22))
      .style('stroke', (p) => (evid.includes(p.id) ? colori.carta : 'none')).style('stroke-width', 1.5)
      .append('title').text((p) => `${T[p.id] ? T[p.id].n : p.id}: ${fmt(p.v, 1)}%`);
    const lab = punti.filter((p) => evid.includes(p.id)).sort((a, b) => a.px - b.px);
    lab.forEach((p, k) => { p.ly = k % 2 ? p.py + r + 16 : p.py - r - 8; });
    g.selectAll('text.l').data(lab).join('text').attr('class', 'etichetta-dato').attr('text-anchor', 'middle')
      .attr('x', (p) => Math.max(40, Math.min(w - 40, p.px))).attr('y', (p) => p.ly).text((p) => nome(p.id));
  }

  function mappa(el, geoNuts, mondo, d, y) {
    el.innerHTML = '';
    const W = el.clientWidth, H = el.clientHeight;
    const regioni = topojson.feature(geoNuts, geoNuts.objects[Object.keys(geoNuts.objects)[0]]).features.filter((f) => f.properties.l === 2);
    const paesi = topojson.feature(mondo, mondo.objects[Object.keys(mondo.objects)[0]]).features;
    const proj = d3.geoAzimuthalEqualArea().rotate([-10, -52]).fitExtent([[4, 4], [W - 4, H - 4]], { type: 'MultiPoint', coordinates: [[-11, 35], [32, 35], [-11, 70], [32, 70], [10, 34.5], [10, 70.5]] });
    const path = d3.geoPath(proj);
    const vals = regioni.map((f) => in_(d, 'EU:' + f.properties.id, y)).filter((v) => v != null).sort((a, b) => a - b);
    const sc = d3.scaleSequential(d3.interpolateLab(colori.seq0, colori.seq1)).domain([d3.quantile(vals, 0.02), d3.quantile(vals, 0.98)]).clamp(true);
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', `Mappa delle regioni europee, quota di 65 anni e oltre nel ${y}`);
    svg.attr('class', 'mappa');
    const g = svg.append('g');
    g.append('g').selectAll('path').data(paesi).join('path').attr('d', path).style('fill', colori.altro).style('stroke', colori.carta).style('stroke-width', 0.4);
    g.append('g').selectAll('path').data(regioni).join('path').attr('d', path)
      .style('fill', (f) => { const v = in_(d, 'EU:' + f.properties.id, y); return v == null ? colori.altro : sc(v); })
      .style('stroke', colori.carta).style('stroke-width', 0.4)
      .append('title').text((f) => { const v = in_(d, 'EU:' + f.properties.id, y); return `${f.properties.n}: ${v == null ? 'n.d.' : fmt(v, 1) + '%'}`; });
    const f = regioni.find((q) => 'EU:' + q.properties.id === FVG);
    if (f) g.append('path').attr('d', path(f)).style('fill', 'none').style('stroke', colori.grafite).style('stroke-width', 2.2);
    const zoom = d3.zoom().scaleExtent([1, 20]).translateExtent([[-W * 0.5, -H * 0.5], [W * 1.5, H * 1.5]]).on('zoom', (e) => g.attr('transform', e.transform));
    svg.call(zoom);
    const com = d3.select(el).append('div').attr('class', 'comandi-mappa');
    const bottone = (et, ico, fn) => com.append('button').attr('class', 'pulsante').attr('type', 'button').attr('aria-label', et).attr('title', et).html(window.Atlante.icona(ico, '')).on('click', fn);
    bottone('Ingrandisci', 'piu', () => svg.transition().duration(300).call(zoom.scaleBy, 1.6));
    bottone('Riduci', 'meno', () => svg.transition().duration(300).call(zoom.scaleBy, 1 / 1.6));
    bottone('Torna all’inquadratura iniziale', 'reset', () => svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity));
    const lg = $('#legenda-mappa');
    const stops = d3.range(0, 1.01, 0.1).map((t) => `${sc.interpolator()(t)} ${t * 100}%`).join(',');
    lg.innerHTML = `<span>${fmt(sc.domain()[0], 1)}% o meno</span><span class="sch__barra" style="background:linear-gradient(90deg,${stops})"></span><span>${fmt(sc.domain()[1], 1)}% o più</span>`;
  }

  /* ---------- pagina ---------- */
  async function avvia() {
    leggiColori();
    const E = (c) => carica(`dati/eurostat/${c}.json`), W = (c) => carica(`dati/indicatori/${c}.json`);
    let meta, nuts, mondo, q65, q15, pop, dens, nati, morti, figli, etaMadri;
    try {
      [meta, nuts, mondo, q65, q15, pop, dens, nati, morti, figli, etaMadri] = await Promise.all([
        carica('dati/meta.json'), carica('dati/nuts.topo.json'), carica('dati/mondo.topo.json'),
        E('EU_QUOTA_Y_GE65'), E('EU_QUOTA_Y_LT15'), E('EU_POP_T_TOTAL'), E('EU_DENS'), E('EU_NATI'), E('EU_MORTI'), E('EU_TOTFERRT'), E('EU_AGEMOTH')]);
    } catch (e) { $('#lede').textContent = 'Impossibile leggere i file di dati. Apri la pagina da un server web.'; return; }
    meta.territori.forEach((t) => { T[t.id] = t; });
    const regioniNuts2 = meta.territori.filter((t) => t.k === 'nuts' && t.l === 2 && t.g);
    const yPop = ultimo(pop, FVG).y, y65 = ultimo(q65, FVG).y;

    $('#lede').innerHTML = `Il Friuli Venezia Giulia (FVG) conta <strong>${fmt(ultimo(pop, FVG).v)}</strong> di residenti al 1° gennaio ${yPop}. Questa scheda lo mette accanto all’Italia, all’Unione europea e alle regioni vicine con i dati Eurostat e Banca Mondiale del repository: ogni numero è letto dai file al caricamento della pagina.`;

    // tessere di sintesi
    const p65 = posizione(q65, FVG, y65, regioniNuts2), p15 = posizione(q15, FVG, y65, regioniNuts2);
    const yF = ultimo(figli, FVG).y, pF = posizione(figli, FVG, yF, regioniNuts2);
    const yD = ultimo(dens, FVG).y, yM = ultimo(etaMadri, FVG).y;
    const tessere = [
      { t: 'Residenti', u: `al 1° gennaio ${yPop}`, d: pop, y: yPop, dec: 0 },
      { t: '65 anni e oltre', u: `% dei residenti, ${y65}`, d: q65, y: y65, dec: 1, pos: p65, cosa: 'quota più alta' },
      { t: 'Sotto i 15 anni', u: `% dei residenti, ${y65}`, d: q15, y: y65, dec: 1, pos: { k: p15.n - p15.k + 1, n: p15.n }, cosa: 'quota più bassa' },
      { t: 'Figli per donna', u: `${yF}`, d: figli, y: yF, dec: 2, pos: { k: pF.n - pF.k + 1, n: pF.n }, cosa: 'valore più basso' },
      { t: 'Età media delle madri al parto', u: `anni, ${yM}`, d: etaMadri, y: yM, dec: 1 },
      { t: 'Densità', u: `abitanti per km², ${yD}`, d: dens, y: yD, dec: 1 },
    ];
    $('#tessere').innerHTML = tessere.map((x) => {
      const v = in_(x.d, FVG, x.y), vi = in_(x.d, IT, x.y), vu = in_(x.d, UE, x.y);
      return `<article class="sch__tessera"><h3>${x.t}</h3><p class="sch__valore">${fmt(v, x.dec)}</p><p class="sch__unita">${x.u}</p>
        <dl><div><dt>Italia</dt><dd>${fmt(vi, x.dec)}</dd></div><div><dt>Unione europea</dt><dd>${vu == null ? '<span class="nd">non pubblicato</span>' : fmt(vu, x.dec)}</dd></div></dl>
        ${x.pos && x.pos.k > 0 ? `<p class="sch__pos">${x.pos.k}° su ${x.pos.n} regioni europee per ${x.cosa}</p>` : ''}</article>`;
    }).join('');
    $('#nota-tessere').textContent = 'Valori Eurostat. “Non pubblicato”: il dataset non contiene il totale dell’Unione europea per questo indicatore. Le posizioni sono calcolate fra le regioni NUTS 2 con il dato nello stesso anno.';

    // invecchiamento
    const primo = q65.d[FVG].findIndex((v) => v != null), y0 = q65.y0 + primo;
    $('#testo-eta').innerHTML = `Nel ${y0} le persone con 65 anni e oltre erano il <strong>${fmt(in_(q65, FVG, y0), 1)}%</strong> dei residenti del Friuli Venezia Giulia; nel ${y65} sono il <strong>${fmt(in_(q65, FVG, y65), 1)}%</strong>, contro il ${fmt(in_(q65, IT, y65), 1)}% dell’Italia e il ${fmt(in_(q65, UE, y65), 1)}% dell’Unione europea a 27. Fra le ${p65.n} regioni europee con il dato, il Friuli Venezia Giulia è al <strong>${p65.k}° posto</strong> per quota di anziani.`;
    const disegna = () => {
      linee($('#g-eta'), q65, [FVG, IT, UE, ...VICINI], { dec: 1, etichetta: 'Quota di 65 anni e oltre nel tempo' });
      linee($('#g-saldo'), { y0: nati.y0, d: { N: nati.d[FVG], M: morti.d[FVG] } }, ['N', 'M'], { zero: true, spesse: true, colore: (s) => colori.serie[s.id === 'N' ? 2 : 1], nome: (s) => (s.id === 'N' ? 'Nati' : 'Decessi'), etichetta: 'Nati e decessi in Friuli Venezia Giulia' });
      linee($('#g-figli'), figli, [FVG, IT, ...VICINI], { dec: 2, etichetta: 'Figli per donna' });
      mappa($('#g-mappa'), nuts, mondo, q65, y65);
      sciame($('#g-sciame'), q65, y65, regioniNuts2, [FVG, ...VICINI]);
    };

    // nascite e decessi
    const yN = Math.min(ultimo(nati, FVG).y, ultimo(morti, FVG).y);
    const n = in_(nati, FVG, yN), mo = in_(morti, FVG, yN);
    const yN0 = nati.y0 + nati.d[FVG].findIndex((v) => v != null);
    $('#testo-nascite').innerHTML = `Nel ${yN} in Friuli Venezia Giulia sono nati <strong>${fmt(n)}</strong> bambini e sono morte <strong>${fmt(mo)}</strong> persone: il saldo naturale, calcolato come nati meno decessi, è di <strong>${fmt(n - mo)}</strong>. Nel ${yN0} i nati erano ${fmt(in_(nati, FVG, yN0))}. Nel ${yF} i figli per donna sono ${fmt(in_(figli, FVG, yF), 2)}, contro ${fmt(in_(figli, IT, yF), 2)} in Italia.`;

    // regioni europee
    $('#testo-europa').innerHTML = `La mappa mostra la quota di anziani in ogni regione europea nel ${y65}. La mediana delle ${p65.n} regioni è ${fmt(d3.median(p65.valori, (o) => o.v), 1)}%: il Friuli Venezia Giulia, con il ${fmt(in_(q65, FVG, y65), 1)}%, supera ${p65.valori.filter((o) => o.v < in_(q65, FVG, y65)).length} regioni su ${p65.n}. Le cinque regioni con la quota più alta sono ${p65.valori.slice(0, 5).map((o) => `${esc(T[o.id].n)} (${fmt(o.v, 1)}%)`).join(', ')}. Sotto la mappa la stessa informazione come distribuzione, con le regioni vicine in evidenza.`;

    // province
    const righe = [
      { t: 'Residenti al 1° gennaio', d: pop, dec: 0 },
      { t: '65 anni e oltre (%)', d: q65, dec: 1 },
      { t: 'Sotto i 15 anni (%)', d: q15, dec: 1 },
      { t: 'Figli per donna', d: figli, dec: 2 },
      { t: 'Età media delle madri (anni)', d: etaMadri, dec: 1 },
      { t: 'Densità (abitanti per km²)', d: dens, dec: 1 },
      { t: 'Nati vivi', d: nati, dec: 0 },
      { t: 'Decessi', d: morti, dec: 0 },
    ];
    const colonne = [...PROVINCE, FVG, IT];
    $('#tab-province').innerHTML = `<table><thead><tr><th scope="col">Indicatore</th><th scope="col" class="num">Anno</th>${colonne.map((id) => `<th scope="col" class="num">${esc(nome(id))}</th>`).join('')}</tr></thead><tbody>${righe.map((r) => {
      const y = Math.min(...PROVINCE.map((id) => (ultimo(r.d, id) || { y: 0 }).y));
      const vp = PROVINCE.map((id) => in_(r.d, id, y)); const mx = d3.max(vp);
      return `<tr><th scope="row">${r.t}</th><td class="num">${y}</td>${colonne.map((id, k) => { const v = in_(r.d, id, y); return `<td class="num${k < 4 && v === mx ? ' sch__max' : ''}">${fmt(v, r.dec)}</td>`; }).join('')}</tr>`;
    }).join('')}</tbody></table>`;
    const q = PROVINCE.map((id) => ({ id, v: in_(q65, id, y65) })).sort((a, b) => b.v - a.v);
    $('#testo-province').innerHTML = `Dentro la regione i valori cambiano da provincia a provincia. Nel ${y65} la provincia con più anziani è <strong>${esc(nome(q[0].id))}</strong> (${fmt(q[0].v, 1)}%), quella con meno è <strong>${esc(nome(q[3].id))}</strong> (${fmt(q[3].v, 1)}%). In grassetto, per ogni riga, il valore più alto fra le quattro province.`;

    // Italia, UE e mondo dalla Banca Mondiale
    const wb = [['SP.DYN.LE00.IN', 'Speranza di vita alla nascita', 'anni', 1], ['SP.DYN.LE00.FE.IN', 'Speranza di vita, donne', 'anni', 1], ['SP.DYN.LE00.MA.IN', 'Speranza di vita, uomini', 'anni', 1],
      ['SP.DYN.TFRT.IN', 'Figli per donna', 'nati per donna', 2], ['SP.POP.65UP.TO.ZS', 'Popolazione di 65 anni e oltre', '% del totale', 1], ['SP.DYN.IMRT.IN', 'Mortalità infantile', 'per 1.000 nati vivi', 1],
      ['SH.MED.PHYS.ZS', 'Medici', 'per 1.000 abitanti', 1], ['SH.MED.BEDS.ZS', 'Posti letto ospedalieri', 'per 1.000 abitanti', 1], ['SE.TER.ENRR', 'Iscrizioni all’istruzione terziaria', '% lorda', 1],
      ['IT.NET.BBND.P2', 'Banda larga fissa', 'abbonamenti per 100 abitanti', 1], ['EG.FEC.RNEW.ZS', 'Energia rinnovabile sui consumi finali', '%', 1], ['EN.GHG.ALL.PC.CE.AR5', 'Gas serra per abitante', 't di CO₂ equivalente', 1],
      ['EN.ATM.PM25.MC.M3', 'Esposizione media al PM2,5', 'microgrammi per m³', 1], ['AG.LND.FRST.ZS', 'Superficie forestale', '% del territorio', 1]];
    const dati = await Promise.all(wb.map(([c]) => W(c)));
    $('#tab-italia').innerHTML = `<table><thead><tr><th scope="col">Indicatore</th><th scope="col">Unità</th>${['ITA', 'EUU', 'WLD'].map((id) => `<th scope="col" class="num">${nome(id)}</th>`).join('')}</tr></thead><tbody>${wb.map(([c, t, u, dec], k) => {
      const d = dati[k];
      const cel = ['ITA', 'EUU', 'WLD'].map((id) => { const o = ultimo(d, id); return o ? `${fmt(o.v, dec)}<span class="sch__anno">${o.y}</span>` : '<span class="nd">n.d.</span>'; });
      return `<tr><th scope="row">${t}</th><td>${u}</td>${cel.map((x) => `<td class="num">${x}</td>`).join('')}</tr>`;
    }).join('')}</tbody></table>`;
    const le = dati[0], fe = dati[3];
    const paesi = meta.territori.filter((t) => t.k === 'paese');
    const yfe = ultimo(fe, 'ITA').y;
    const ord = paesi.map((t) => ({ id: t.id, v: in_(fe, t.id, yfe) })).filter((o) => o.v != null).sort((a, b) => a.v - b.v);
    const rf = { k: ord.findIndex((o) => o.id === 'ITA') + 1, n: ord.length };
    $('#testo-italia').innerHTML = `Su scala nazionale l’Italia ha una speranza di vita di <strong>${fmt(ultimo(le, 'ITA').v, 1)} anni</strong> (${ultimo(le, 'ITA').y}), contro ${fmt(ultimo(le, 'EUU').v, 1)} nell’Unione europea e ${fmt(ultimo(le, 'WLD').v, 1)} nel mondo, mentre i figli per donna sono ${fmt(ultimo(fe, 'ITA').v, 2)} contro ${fmt(ultimo(fe, 'EUU').v, 2)} nell’Unione europea: fra i ${rf.n} paesi con il dato nel ${ultimo(fe, 'ITA').y}, l’Italia è al ${rf.k}° posto per fecondità più bassa. Sotto ogni valore l’anno del dato più recente.`;

    disegna();
    let t; new ResizeObserver(() => { clearTimeout(t); t = setTimeout(disegna, 150); }).observe($('.sch__pagina'));
    const ricolora = () => { leggiColori(); disegna(); };
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', ricolora);
    new MutationObserver(ricolora).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  }
  avvia();
})();
