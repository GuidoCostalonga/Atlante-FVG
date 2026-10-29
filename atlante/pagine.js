/* Atlante dei dati: pagine. Prima pagina, temi, esploratore di un indicatore, profili dei territori,
   confronto, archivi, fonti e metodo. Avvio dell'applicazione. */
(function (A) {
  'use strict';
  const $ = A.$, esc = A.esc, fmt = A.fmt, S = A.S;
  const h = (html) => { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; };
  const briciole = (voci) => `<nav class="briciole" aria-label="Percorso">${voci.map((v, i) => (i ? `<svg viewBox="0 0 20 20"><path d="M7 4l6 6-6 6"/></svg>` : '') + (v.href ? `<a href="${v.href}">${esc(v.n)}</a>` : `<span>${esc(v.n)}</span>`)).join('')}</nav>`;
  const pano = (c) => (A.PANO[c] || null);
  const temiConIndicatori = () => A.ORDINE_TEMI.filter((k) => k !== 'arc');
  const indicatoriDi = (k) => Object.values(A.IND).filter((i) => i.fam !== 'arc' && i.t === k).sort((a, b) => a.n.localeCompare(b.n, 'it'));
  const primoDi = (k) => { const f = A.TEMI[k].flag.find((c) => A.IND[c]); return f || (indicatoriDi(k)[0] || {}).c; };
  const posTesto = (p, basso) => { if (!p) return ''; const k = basso ? p[1] - p[0] + 1 : p[0]; return `${k}° su ${p[1]}${basso ? ' partendo dal più basso' : ''}`; };

  // scheda di un indicatore (nelle pagine dei temi, nei correlati)
  const cardIndicatore = (i, idx) => {
    const p = pano(i.c), eu = i.fam === 'eu';
    const chi = eu ? 'Friuli Venezia Giulia' : 'Italia';
    const v = p && (eu ? p.fvg : p.it);
    const mini = `<div class="mini" data-c="${esc(i.c)}"></div>`;
    return `<a class="ind-card" data-tema="${i.t}" href="#/i/${esc(i.c)}" style="--i:${idx || 0}">
      <h3>${esc(i.n)}</h3><span class="unita">${esc(i.u)}</span>
      <div class="ind-card__dato">${v ? `<div class="ind-card__valore">${fmt(v[1])}<small>${chi}, ${v[0]}${p.pos ? ` · ${p.pos[0]}° su ${p.pos[1]}` : ''}</small></div>` : `<span class="nd">senza dato recente per ${chi}</span>`}${mini}</div></a>`;
  };
  const disegnaMini = (root) => {
    root.querySelectorAll('.mini[data-c]').forEach((el) => {
      const p = pano(el.dataset.c); if (!p || !p.sp) return;
      const i = A.IND[el.dataset.c];
      A.sparkline(el, { y0: p.sp[0], valori: p.sp[1], rif: p.spw ? { y0: p.spw[0], valori: p.spw[1] } : null, colore: A.colori['t_' + (i.fam === 'eu' ? 'eur' : i.t)] });
    });
  };

  /* ---------- prima pagina ---------- */
  A.pagine.home = async (main) => {
    document.title = 'Atlante dei dati';
    const nInd = Object.values(A.IND).filter((i) => i.fam !== 'arc').length;
    const nReg = A.META.territori.filter((t) => t.k === 'nuts' && t.l > 0).length;
    const nArc = (A.META.archivi || []).length;
    const storie = A.STORIE.map((s) => ({ s, i: A.IND[s.c], p: pano(s.c) })).filter((x) => x.i && x.p && x.p[x.s.k]).slice(0, 6);
    main.innerHTML = `<div class="entra">
      <section class="eroe">
        <p class="occhiello" data-tema="pop">Banca Mondiale · Eurostat · Commissione europea · FAOSTAT · OMS · OCSE · ONU · FMI</p>
        <h1>I numeri del <em>mondo</em>, delle regioni europee e del Friuli Venezia Giulia</h1>
        <p>Cerca un dato, aprilo su mappa, andamento e classifica, confronta paesi e regioni. Ogni valore viene dalla fonte: niente stime, niente interpolazioni.</p>
        <div class="eroe__numeri"><span><b data-n="${nInd}">0</b>indicatori</span><span><b data-n="${A.PAESI.length}">0</b>paesi</span><span><b data-n="${nReg}">0</b>regioni e province europee</span><span><b data-n="${nArc}">0</b>insiemi di dati FAOSTAT, OMS, OCSE, ONU, FMI</span></div>
        <div class="scorciatoie">
          <a class="chip chip--accento" data-tema="sal" href="#/i/SP.DYN.LE00.IN">Speranza di vita</a>
          <a class="chip chip--accento" data-tema="eur" href="#/i/EU_QUOTA_Y_GE65?t=EU:ITH4,EU:ITH3,EU:AT21,EU:SI04,EU:IT&v=mappa&liv=2">Over 65 nelle regioni europee</a>
          <a class="chip chip--accento" data-tema="pop" href="#/i/SP.DYN.TFRT.IN">Figli per donna</a>
          <a class="chip chip--accento" data-tema="dig" href="#/i/IT.NET.USER.ZS?v=mappa">Chi usa Internet</a>
          <a class="chip chip--accento" data-tema="ene" href="#/i/EG.FEC.RNEW.ZS?v=classifica">Rinnovabili</a>
          <a class="chip chip--accento" data-tema="amb" href="#/i/EN.GHG.ALL.PC.CE.AR5?v=mappa">Gas serra per abitante</a>
        </div>
      </section>
      <section class="sezione"><div class="sezione__testa"><h2>Scegli un tema</h2><p>Dieci aree, ogni indicatore con il valore più recente per l’Italia o il Friuli Venezia Giulia.</p></div>
        <div class="temi-griglia sfalsa">${A.ORDINE_TEMI.map((k, idx) => { const t = A.TEMI[k]; const n = k === 'arc' ? nArc : indicatoriDi(k).length; return `<a class="tema-tessera" data-tema="${k}" href="${k === 'arc' ? '#/archivi' : '#/tema/' + k}" style="--i:${idx}">${A.icona(k)}<h3>${esc(t.n)}</h3><span class="conta">${n} ${k === 'arc' ? 'insiemi di dati' : 'indicatori'}</span><div class="mini" data-c="${esc(t.flag[0] || '')}"></div></a>`; }).join('')}</div></section>
      <section class="sezione"><div class="sezione__testa"><h2>In evidenza</h2><p>Valori più recenti per l’Italia e il Friuli Venezia Giulia, con la posizione in classifica.</p></div>
        <div class="storie sfalsa">${storie.map((x, idx) => { const v = x.p[x.s.k]; const alt = x.s.k === 'fvg' ? `Italia ${x.p.it ? fmt(x.p.it[1]) : 'n.d.'} · Unione europea ${x.p.eu ? fmt(x.p.eu[1]) : 'n.d.'}` : `Unione europea ${x.p.eu ? fmt(x.p.eu[1]) : 'n.d.'} · mondo ${x.p.wld ? fmt(x.p.wld[1]) : 'n.d.'}`; return `<a class="storia" data-tema="${x.i.fam === 'eu' ? 'eur' : x.i.t}" href="#/i/${esc(x.s.c)}${x.s.k === 'fvg' ? '?t=EU:ITH4,EU:ITH3,EU:AT21,EU:SI04,EU:IT' : ''}" style="--i:${idx}"><div class="numero" data-v="${v[1]}"><span>0</span><small>${esc(x.i.u)}</small></div><h3>${esc(x.s.t)}</h3><p>${v[0]}${x.p.pos ? ` · ${posTesto(x.p.pos, x.s.basso)} ${x.i.fam === 'eu' ? 'regioni europee' : 'paesi'}` : ''}<br>${alt}</p><div class="mini" data-c="${esc(x.s.c)}"></div></a>`; }).join('')}</div></section>
      <section class="sezione"><div class="sezione__testa"><h2>Confronti pronti</h2><p>Una selezione di territori già impostata: apri il confronto o la mappa.</p></div>
        <div class="chips">${A.PRESET.map((p) => `<a class="chip" href="#/confronta?t=${p.ids.join(',')}">${esc(p.n)}</a>`).join('')}</div></section>
      <section class="sezione"><div class="sezione__testa"><h2>Schede e profili</h2></div>
        <div class="schede-griglia">
          <a class="scheda-card" data-tema="eur" href="scheda-fvg.html"><span class="occhiello">Scheda</span><h3>Italia e Friuli Venezia Giulia a confronto con l’Europa</h3><p>Invecchiamento, nascite e decessi, le quattro province, la posizione fra le regioni europee e l’Italia nel mondo. Testi e grafici calcolati dai dati.</p><span class="pulsante pulsante--accento">Apri la scheda</span></a>
          <a class="scheda-card" data-tema="pop" href="#/t/ITA"><span class="occhiello">Profilo</span><h3>Italia</h3><p>Diciotto indicatori in evidenza con posizione fra i paesi e andamento degli ultimi trent’anni. Cerca qualsiasi altro paese o regione nella barra in alto.</p><span class="pulsante pulsante--accento">Apri il profilo</span></a>
          <a class="scheda-card" data-tema="arc" href="#/archivi"><span class="occhiello">Insiemi di dati</span><h3>FAOSTAT, OMS, OCSE, ONU e FMI</h3><p>Tutte le serie dei lotti: produzione agricola, bilanci alimentari, emissioni, commercio, salute, istruzione e clima, serie per serie.</p><span class="pulsante pulsante--accento">Sfoglia gli insiemi di dati</span></a>
        </div></section>
    </div>`;
    main.querySelectorAll('.eroe__numeri b').forEach((b) => A.animaNumero(b, +b.dataset.n, (v) => A.F.int.format(Math.round(v))));
    main.querySelectorAll('.storia .numero').forEach((n) => A.animaNumero(n.querySelector('span'), +n.dataset.v, (v) => fmt(v)));
    disegnaMini(main);
  };

  /* ---------- pagina di un tema ---------- */
  A.pagine.tema = async (main, parti) => {
    const k = parti[1];
    if (k === 'arc') return A.pagine.archivi(main, ['archivi']);
    const t = A.TEMI[k]; if (!t) return A.pagine.home(main);
    document.title = `${t.n} · Atlante dei dati`;
    const inds = indicatoriDi(k);
    const gruppi = new Map();
    (A.SOTTOGRUPPI[k] || []).forEach(([n]) => gruppi.set(n, []));
    inds.forEach((i) => { const g = A.sottogruppo(i); if (!gruppi.has(g)) gruppi.set(g, []); gruppi.get(g).push(i); });
    const eu = k === 'eur';
    const num = t.flag.map((c) => A.IND[c]).filter(Boolean).map((i) => { const p = pano(i.c); const v = p && (eu ? p.fvg : p.it); return v ? `<div><b>${fmt(v[1])}</b><span>${esc(i.n)}, ${eu ? 'Friuli Venezia Giulia' : 'Italia'} ${v[0]}</span></div>` : ''; }).join('');
    main.innerHTML = `<div class="entra" data-tema="${k}">
      ${briciole([{ n: 'Atlante', href: '#/' }, { n: t.n }])}
      <header class="tema-testa"><div class="tema-testa__riga">${A.icona(k)}<h1>${esc(t.n)}</h1></div><p>${esc(t.breve)} ${inds.length} indicatori${eu ? ' per regioni e province europee (Eurostat e Commissione europea)' : ' della Banca Mondiale per 217 paesi'}.</p><div class="tema-testa__numeri">${num}</div></header>
      <div class="sottogruppi chips">${[...gruppi.keys()].filter((g) => gruppi.get(g).length).map((g) => `<a class="chip" href="#sg-${esc(g.replace(/\W+/g, '-'))}">${esc(g)} <span class="nd">${gruppi.get(g).length}</span></a>`).join('')}</div>
      ${[...gruppi.entries()].filter(([, v]) => v.length).map(([g, v]) => `<section class="sezione" id="sg-${esc(g.replace(/\W+/g, '-'))}"><div class="sezione__testa"><h2>${esc(g)}</h2></div><div class="indicatori-griglia sfalsa">${v.map((i, idx) => cardIndicatore(i, idx)).join('')}</div></section>`).join('')}
    </div>`;
    main.querySelectorAll('.sottogruppi a').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); const el = $(a.getAttribute('href')); if (el) el.scrollIntoView({ behavior: A.ridotto.matches ? 'auto' : 'smooth', block: 'start' }); }));
    disegnaMini(main);
  };

  /* ---------- selezione dei territori (esploratore e confronto) ---------- */
  A.selettoreTerritori = (box, o) => {
    const disegna = () => {
      box.innerHTML = `<div class="territori">
        ${S.sel.map((id) => { const t = A.T[id]; if (!t) return ''; const fuori = o.cod && A.idPer(o.cod, id) == null; return `<span class="chip${fuori ? ' chip--fuori' : ''}" ${fuori ? 'title="Non previsto per questo indicatore"' : ''}><span class="pallino${A.eAggregato(id) ? ' pallino--agg' : ''}" style="${A.eAggregato(id) ? '' : `background:${A.coloreRegione(id)}`}"></span>${esc(t.n)}${t.k === 'nuts' && t.l ? ` <span class="nd">NUTS ${t.l}</span>` : ''}<button class="chip__togli" type="button" aria-label="Togli ${esc(t.n)}"><svg viewBox="0 0 12 12"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7"/></svg></button></span>`; }).join('')}
        <div class="combo"><label class="visivo-nascosto" for="agg-terr">Aggiungi un territorio</label><input id="agg-terr" type="search" placeholder="+ Aggiungi un paese o una regione" autocomplete="off"><ul class="combo__lista" id="agg-terr-lista" hidden></ul></div>
        <div class="seleziona"><label class="visivo-nascosto" for="preset">Confronti pronti</label><select id="preset"><option value="">Confronti pronti…</option>${A.PRESET.map((p, i) => `<option value="${i}">${esc(p.n)}</option>`).join('')}</select></div>
        ${S.sel.length ? '<button class="pulsante pulsante--testo pulsante--piccolo" type="button" id="svuota">Svuota</button>' : ''}
      </div>`;
      box.querySelectorAll('.chip__togli').forEach((b, i) => b.addEventListener('click', () => { S.sel.splice(i, 1); A.salvaStato(); disegna(); o.onChange(); }));
      const sv = $('#svuota', box); if (sv) sv.addEventListener('click', () => { S.sel = []; A.salvaStato(); disegna(); o.onChange(); });
      $('#preset', box).addEventListener('change', (e) => { const p = A.PRESET[+e.target.value]; if (!p) return; S.sel = p.ids.filter((id) => A.T[id]); A.salvaStato(); disegna(); o.onPreset ? o.onPreset(p) : o.onChange(); });
      const input = $('#agg-terr', box), lista = $('#agg-terr-lista', box);
      A.combobox({ input, lista, apriSubito: true, vuoto: 'Nessun territorio trovato', cerca: (q) => {
        if (!q) {
          const sugg = (o.cod && A.fam(o.cod) === 'eu' ? ['EU:ITH4', 'EU:IT', 'EU:ITH3', 'EU:ITC4', 'EU:DE', 'EU:FR', 'EU:EU27_2020'] : ['ITA', 'DEU', 'FRA', 'ESP', 'USA', 'CHN', 'IND', 'EUU', 'WLD']).filter((id) => A.T[id] && !S.sel.includes(id));
          return [{ titolo: 'Suggeriti', voci: sugg.map((id) => ({ id, html: `<span class="pallino" style="background:${A.coloreRegione(id)}"></span><span>${esc(A.T[id].n)}</span><span class="tipo">${esc(A.descriviTerritorio(A.T[id]))}</span>` })) }];
        }
        const g = A.cercaIndice(q, { terr: 12 })[2];
        return [{ titolo: '', voci: g.voci.filter((v) => !S.sel.includes(v.id)).map((v) => ({ id: v.id, html: `<span class="pallino" style="background:${A.coloreRegione(v.id)}"></span><span>${esc(v.n)}</span><span class="tipo">${esc(v.sotto)}</span>` })) }];
      }, scegli: (v) => { if (!S.sel.includes(v.id)) S.sel.push(v.id); A.salvaStato(); input.value = ''; disegna(); o.onChange(); if (o.cod && A.idPer(o.cod, v.id) == null) A.toast(`${A.T[v.id].n}: non previsto per questo indicatore, resta nella selezione`); } });
    };
    disegna();
    return { disegna };
  };

  /* ---------- esploratore di un indicatore ---------- */
  let timerPlay = null, ro = null;
  const ferma = () => { if (!S.inRiproduzione) return; S.inRiproduzione = false; clearTimeout(timerPlay); const b = $('#t-play'); if (b) { b.setAttribute('aria-pressed', 'false'); b.setAttribute('aria-label', 'Riproduci'); } };
  A.pagine.i = async (main, parti, q) => {
    const cod = decodeURIComponent(parti.slice(1).join('/'));
    if (cod.startsWith('A:')) { try { await A.registraSerie(cod); } catch (e) { /* segue il rimando */ } }
    if (!A.IND[cod]) { A.vai(`#/i/${A.PREDEF.ind}`); return; }
    ferma(); if (ro) { ro.disconnect(); ro = null; }
    const i = A.IND[cod], fam = i.fam, tema = fam === 'arc' ? 'arc' : i.t;
    document.title = `${i.n} · Atlante dei dati`;
    // stato dalla query
    S.ind = cod;
    const v = q.get('v'); if (v && A.VISTE.some((x) => x[0] === v)) S.vista = v; else if (!A.VISTE.some((x) => x[0] === S.vista)) S.vista = 'andamento';
    if (q.get('t') != null) S.sel = q.get('t').split(',').filter((id) => A.T[id]);
    if (q.get('area') && A.AREE[q.get('area')]) S.area = q.get('area');
    if (q.get('liv')) S.livello = Math.max(0, Math.min(3, +q.get('liv')));
    if (q.get('pae') != null) S.paeseEU = A.T[q.get('pae')] ? q.get('pae') : '';
    if (q.get('log')) S.log[cod] = q.get('log') === '1';
    if (q.get('ult')) S.ultimo = q.get('ult') === '1';
    if (q.get('n')) S.nBarre = q.get('n') === 'tutti' ? 'tutti' : +q.get('n') || 25;
    if (q.get('o')) S.ordine = q.get('o') === 'asc' ? 'asc' : 'desc';
    const z = q.get('z'); S.zoom = z && /^\d{4}-\d{4}$/.test(z) ? z.split('-').map(Number) : null;
    // la selezione deve contenere almeno un territorio adatto alla famiglia dell'indicatore
    if (!S.sel.some((id) => A.idPer(cod, id) != null)) {
      if (fam === 'eu') S.sel = A.PREDEF.eu.sel.filter((id) => A.T[id]);
      else if (fam === 'arc') S.sel = i.arch.terr.filter((id) => !(i.arch.aggr || []).includes(id)).slice(0, 4);
      else S.sel = A.PREDEF.sel.slice();
    }
    main.innerHTML = '<div class="caricamento">Carico i dati…</div>';
    const d = await A.carica(cod); A.caricaNote(cod).then(() => { if (vista && vista.aggiorna && S.vista === 'tabella') vista.aggiorna(); });
    const st = A.stat(cod);
    // anno iniziale: il più recente con dati per almeno metà dei territori
    const annoBuono = () => { const mx = Math.max(...st.perAnno, 1); for (let k = st.perAnno.length - 1; k >= 0; k--) if (st.perAnno[k] >= mx * 0.5) return d.y0 + k; return d.y1; };
    const yq = +q.get('y'); S.anno = yq && yq >= d.y0 && yq <= d.y1 ? yq : (S.anno && S.anno >= d.y0 && S.anno <= d.y1 && q.get('y') !== null ? S.anno : annoBuono());
    if (!q.get('y') && (S.anno == null || S.anno > d.y1 || S.anno < d.y0)) S.anno = annoBuono();

    const sotto = fam === 'arc' ? null : A.sottogruppo(i);
    const correlati = fam === 'arc' ? [] : indicatoriDi(i.t).filter((x) => x.c !== cod && A.sottogruppo(x) === sotto).slice(0, 6);
    main.innerHTML = `<div class="entra esplora" data-tema="${tema}">
      ${briciole([{ n: 'Atlante', href: '#/' }, fam === 'arc' ? { n: 'Archivi', href: '#/archivi' } : { n: A.TEMI[i.t].n, href: '#/tema/' + i.t }, { n: i.n }])}
      <div class="comandi">
        <div class="campo"><label for="sel-tema">Tema</label><div class="seleziona"><select id="sel-tema">${A.ORDINE_TEMI.map((k) => `<option value="${k}" ${k === tema ? 'selected' : ''}>${esc(A.TEMI[k].n)}</option>`).join('')}</select></div></div>
        <div class="campo"><label for="sel-ind">Indicatore</label><div class="combo"><input id="sel-ind" type="text" autocomplete="off" value="${esc(i.n)}"><span class="combo__freccia"></span><ul class="combo__lista" id="sel-ind-lista" hidden></ul></div></div>
        <div class="campo"><label>&nbsp;</label><a class="pulsante" id="vai-confronto" href="#/confronta">${A.icona('classifica', '')} Confronta i territori</a></div>
      </div>
      <div class="comandi comandi--territori" id="box-territori"></div>
      <div class="esplora__titolo"><h1>${esc(i.n)}<span class="unita">${esc(i.u)}</span></h1><p class="evidenza" id="evidenza" aria-live="polite"></p><div id="avviso"></div></div>
      <div class="grafico-card" id="grafico-card">
        <div class="grafico-card__barra">
          <div class="segmenti" role="tablist" aria-label="Viste">${A.VISTE.map(([k, n]) => `<button role="tab" type="button" data-vista="${k}" aria-selected="${S.vista === k}">${A.icona(k, '')}${n}</button>`).join('')}</div>
          <div class="grafico-card__strumenti">
            <button class="pulsante pulsante--icona" type="button" id="b-pieno" aria-label="Schermo intero" title="Schermo intero">${A.icona('pieno', '')}</button>
            <button class="pulsante pulsante--icona" type="button" id="b-csv" aria-label="Scarica i dati in CSV" title="Scarica i dati (CSV)">${A.icona('scarica', '')}</button>
            <button class="pulsante pulsante--icona" type="button" id="b-link" aria-label="Copia il collegamento a questa vista" title="Copia il collegamento">${A.icona('collega', '')}</button>
          </div>
        </div>
        <div class="scena" id="scena"><div class="scena__anno" id="anno-filigrana" aria-hidden="true"></div><div class="scena__corpo" id="corpo"></div><div class="legenda-mappa" id="legenda-mappa" hidden></div><div class="scena__carico" id="carico" hidden>Carico…</div></div>
        <div class="navigatore" id="navigatore" hidden></div>
        <div class="controlli" id="controlli"></div>
      </div>
      <dl class="scheda-dato"><div><dt>Unità di misura</dt><dd>${esc(i.u)}</dd></div><div><dt>Periodo</dt><dd>dal ${i.y0} al ${i.y1}</dd></div><div><dt>Fonte</dt><dd id="sd-fonte"></dd></div><div><dt>Aggiornamento</dt><dd id="sd-agg"></dd></div><div><dt>Dati mancanti</dt><dd id="sd-mancanti"></dd></div></dl>
      <details class="definizione"><summary>Definizione, provenienza e territori senza dato</summary><div class="definizione__corpo"><p id="def-testo"></p><p id="def-fonte"></p><h3>Senza dato nell’anno mostrato</h3><p id="def-mancanti"></p></div></details>
      ${correlati.length ? `<section class="correlati"><div class="sezione__testa"><h2>Altri indicatori: ${esc(sotto)}</h2></div><div class="indicatori-griglia">${correlati.map((x, idx) => cardIndicatore(x, idx)).join('')}</div></section>` : ''}
    </div>`;
    disegnaMini(main);
    const fonte = fam === 'eu' ? `${esc(i.org || 'Eurostat')}, <a href="${i.url}" target="_blank" rel="noopener">${esc(i.ds)}</a>` : fam === 'arc' ? `${esc(i.arch.fonte.replace(/ \(.*/, ''))}, insieme di dati ${esc(i.arch.cod)}${i.url ? ` · <a href="${i.url}" target="_blank" rel="noopener">fonte</a>` : ''}` : `Banca Mondiale, WDI · <a href="${i.url}" target="_blank" rel="noopener">${esc(i.c)}</a>`;
    $('#sd-fonte').innerHTML = fonte;
    $('#sd-agg').innerHTML = `fonte: ${A.data(i.agg)}<br>repository: ${fam === 'arc' ? 'ottobre 2026' : A.data(A.META.acquisizione[String(i.lotto)] || '')}`;
    if (fam === 'arc') {
      const dims = i.dims ? Object.entries(i.dims).map(([k, v]) => `${k} = ${v}`).join('; ') : '';
      $('#def-testo').textContent = `Serie originale: ${i.en}.${dims ? ` Dimensioni originali: ${dims}.` : ''}${i.cods && i.cods !== i.arch.cod ? ` Codice indicatore: ${i.cods}.` : ''}`;
      if (i.arch.archivio) {
        $('#def-fonte').innerHTML = `<strong>Archivio parziale.</strong> La fonte distribuisce questo insieme di dati in più archivi; il repository ne contiene solo una parte (${esc(i.arch.archivio)}), cioè ${i.arch.terr.length} territori. Gli altri paesi non mancano nella fonte, mancano nel repository.`;
        $('#avviso').innerHTML = `<div class="avviso">Archivio parziale: ${i.arch.terr.length} territori presenti nel repository (${esc(i.arch.archivio)}). Gli altri paesi non sono mancanti nella fonte: non sono nel repository.</div>`;
      } else {
        $('#def-fonte').innerHTML = `Insieme di dati completo (lotto ${i.arch.lotto}): ${i.arch.terr.length} territori e ${A.F.int.format(i.arch.serie)} serie nell’insieme, ${i.nterr} territori in questa serie. I contrassegni della fonte (dato ufficiale, stima, valore imputato) compaiono nelle note della tabella.`;
      }
    } else {
      $('#def-testo').textContent = i.def ? `“${i.def}”` : 'Definizione non presente nella fonte.';
      $('#def-fonte').innerHTML = fam === 'eu' ? `Fonte: ${esc(i.org || 'Eurostat')}, dataset ${esc(i.ds)} (${esc(i.en)}). ${i.stima ? `<strong>${esc(i.stima)}</strong> ` : ''}${i.calc ? `<strong>${esc(i.calc)}</strong> ` : ''}I codici NUTS storici compaiono in tabella ma non sulla mappa, disegnata con i confini NUTS 2024.` : `Testo originale in inglese della Banca Mondiale per <strong>${esc(i.en)}</strong>. Fonte originaria dichiarata: ${esc((i.org || 'n.d.').replace(/, uri: \S+/g, '').replace(/\n/g, '; '))}. Osservazioni: ${A.F.int.format(i.righe)} righe, ${A.F.int.format(i.valori)} con valore numerico.`;
    }

    // tema e indicatore
    $('#sel-tema').addEventListener('change', (e) => { const k = e.target.value; if (k === 'arc') { A.vai('#/archivi'); return; } const c = primoDi(k); if (c) A.vai(`#/i/${c}`); });
    const inpInd = $('#sel-ind');
    A.combobox({ input: inpInd, lista: $('#sel-ind-lista'), apriSubito: true, vuoto: 'Nessun indicatore trovato', cerca: (qq) => {
      if (fam === 'arc') {
        const serie = (A.cache[i.arch.f + '_serie'] || []);
        const nq = A.norm(qq);
        const trov = serie.map((s, k) => ({ s, k })).filter((o) => !nq || A.norm(o.s.l).includes(nq)).slice(0, 40);
        return [{ titolo: `Serie di ${A.ARC[i.arch.f].n}`, voci: trov.map((o) => ({ id: `A:${i.arch.f}:${o.k}`, html: `<span>${esc(o.s.l)}</span><span class="tipo">${esc(o.s.u)}</span>` })) }];
      }
      if (!qq) { const gr = new Map(); indicatoriDi(i.t).forEach((x) => { const g = A.sottogruppo(x); if (!gr.has(g)) gr.set(g, []); gr.get(g).push(x); }); return [...gr.entries()].map(([g, v]) => ({ titolo: g, voci: v.map((x) => ({ id: x.c, html: `<span>${esc(x.n)}</span><span class="tipo">${esc(x.u)}</span>` })) })); }
      const g = A.cercaIndice(qq, { ind: 14 })[1];
      return [{ titolo: 'Indicatori', voci: g.voci.map((v2) => ({ id: v2.id, html: `${A.icona(v2.tema, 'icona')}<span>${esc(v2.n)}<span class="sotto">${esc(v2.sotto)}</span></span>` })) }];
    }, scegli: (v2) => { if (v2.id !== cod) A.vai(`#/i/${v2.id}${urlStato(true)}`); else inpInd.value = i.n; } });
    inpInd.addEventListener('focus', () => { inpInd.select(); });
    inpInd.addEventListener('blur', () => { setTimeout(() => { if (!inpInd.value.trim()) inpInd.value = i.n; }, 200); });
    if (fam === 'arc') A.caricaArchivio(i.arch.f).then((a) => { A.cache[i.arch.f + '_serie'] = a.s; });

    // territori
    let vista = null;
    const ridisegna = () => disegna();
    const selettore = A.selettoreTerritori($('#box-territori'), { cod, onChange: () => { if (vista && vista.selezione) vista.selezione(); aggiornaTesto(); aggiornaUrl(); }, onPreset: (p) => { const regioni = p.ids.some((id) => A.T[id] && A.T[id].k === 'nuts' && A.T[id].l > 0); if (regioni && fam !== 'eu') { S.livello = Math.max(...p.ids.filter((id) => A.T[id].k === 'nuts').map((id) => A.T[id].l)); S.paeseEU = ''; A.vai(`#/i/${A.PREDEF.eu.ind}?t=${S.sel.join(',')}&liv=${S.livello}`); } else if (!regioni && fam === 'eu') A.vai(`#/i/${A.PREDEF.ind}?t=${S.sel.join(',')}`); else { if (vista && vista.selezione) vista.selezione(); aggiornaTesto(); aggiornaUrl(); } } });
    const onSeleziona = (id) => { const gia = S.sel.find((s) => A.idPer(cod, s) === id); if (gia) S.sel.splice(S.sel.indexOf(gia), 1); else S.sel.push(id); A.salvaStato(); selettore.disegna(); if (vista && vista.selezione) vista.selezione(); aggiornaTesto(); aggiornaUrl(); };

    // indirizzo della vista
    function urlStato(soloComuni) {
      const p = new URLSearchParams();
      if (S.sel.length) p.set('t', S.sel.join(','));
      if (S.ultimo) p.set('ult', '1');
      if (!soloComuni) {
        if (S.vista !== 'andamento') p.set('v', S.vista);
        if (S.anno != null && S.vista !== 'andamento') p.set('y', S.anno);
        if (fam === 'eu') { p.set('liv', S.livello); if (S.paeseEU) p.set('pae', S.paeseEU); } else if (S.area !== 'mondo' && S.vista === 'mappa') p.set('area', S.area);
        if (S.log[cod] != null) p.set('log', S.log[cod] ? '1' : '0');
        if (S.zoom && S.vista === 'andamento') p.set('z', `${S.zoom[0]}-${S.zoom[1]}`);
        if (S.vista === 'classifica') { if (S.nBarre !== 25) p.set('n', S.nBarre); if (S.ordine !== 'desc') p.set('o', S.ordine); }
      }
      const s = p.toString(); return s ? '?' + s : '';
    }
    const aggiornaUrl = () => { A.sostituisci(`#/i/${cod}${urlStato()}`); $('#vai-confronto').href = `#/confronta?t=${S.sel.join(',')}&g=${fam === 'eu' ? 'eur' : fam === 'arc' ? 'sal' : i.t}`; };

    // comandi
    const scena = $('#scena'), corpo = $('#corpo'), legenda = $('#legenda-mappa'), nav = $('#navigatore'), controlli = $('#controlli'), card = $('#grafico-card');
    main.querySelectorAll('.segmenti [role="tab"]').forEach((b) => b.addEventListener('click', () => { S.vista = b.dataset.vista; main.querySelectorAll('.segmenti [role="tab"]').forEach((x) => x.setAttribute('aria-selected', x === b ? 'true' : 'false')); disegna(); aggiornaUrl(); }));
    $('#b-pieno').addEventListener('click', () => {
      if (document.fullscreenElement === card) { document.exitFullscreen(); return; }
      if (card.classList.contains('pieno')) { card.classList.remove('pieno'); return; }
      if (card.requestFullscreen) card.requestFullscreen().catch(() => card.classList.add('pieno')); else card.classList.add('pieno');
    });
    document.addEventListener('fullscreenchange', () => { card.classList.toggle('pieno-nativo', document.fullscreenElement === card); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && card.classList.contains('pieno')) card.classList.remove('pieno'); });
    $('#b-csv').addEventListener('click', () => { A.scaricaCsv(cod); A.toast('File CSV in scaricamento'); });
    $('#b-link').addEventListener('click', async () => { aggiornaUrl(); const u = location.href; try { await navigator.clipboard.writeText(u); A.toast('Collegamento copiato'); } catch (e) { prompt('Copia il collegamento:', u); } });
    document.addEventListener('keydown', (e) => { if (e.target.closest('input, select, textarea, button, [role="tab"]')) return; if (e.key === 'ArrowLeft') { ferma(); impostaAnno(S.anno - 1, true); } if (e.key === 'ArrowRight') { ferma(); impostaAnno(S.anno + 1, true); } });

    // tempo
    function impostaAnno(y, anima) {
      y = Math.max(d.y0, Math.min(d.y1, y)); if (y === S.anno && !anima) return;
      S.anno = y; aggiornaTempo();
      if (vista && vista.aggiorna) vista.aggiorna(anima);
      aggiornaTesto(); aggiornaUrl();
    }
    const aggiornaTempo = () => {
      const r = $('#t-range'), sl = $('#t-sel'); if (!r) return;
      r.value = S.anno; r.setAttribute('aria-valuetext', String(S.anno)); sl.value = S.anno; $('#t-anno').textContent = S.anno; $('#anno-filigrana').textContent = S.anno;
      $('#t-prev').disabled = S.anno <= d.y0; $('#t-next').disabled = S.anno >= d.y1;
    };
    const riproduci = () => {
      if (S.anno >= d.y1) impostaAnno(d.y0, false);
      S.inRiproduzione = true; const b = $('#t-play'); b.setAttribute('aria-pressed', 'true'); b.setAttribute('aria-label', 'Pausa');
      const passo = () => { if (!S.inRiproduzione) return; if (S.anno >= d.y1) { ferma(); return; } impostaAnno(S.anno + 1, true); timerPlay = setTimeout(passo, S.velocita); };
      timerPlay = setTimeout(passo, 120);
    };
    const tempoHtml = () => `<div class="tempo"><button class="pulsante pulsante--icona" type="button" id="t-prev" aria-label="Anno precedente">${A.icona('sinistra', '')}</button><button class="pulsante pulsante--play" type="button" id="t-play" aria-label="Riproduci" aria-pressed="false"><svg class="ico-play" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4l10 6-10 6z"/></svg><svg class="ico-pausa" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4h3v12H6zM11 4h3v12h-3z"/></svg></button><button class="pulsante pulsante--icona" type="button" id="t-next" aria-label="Anno successivo">${A.icona('destra', '')}</button><output class="tempo__anno" id="t-anno" for="t-range">${S.anno}</output><label class="visivo-nascosto" for="t-range">Anno</label><input type="range" id="t-range" min="${d.y0}" max="${d.y1}" step="1" value="${S.anno}"><div class="seleziona"><label class="visivo-nascosto" for="t-sel">Scegli l’anno</label><select id="t-sel">${d3.range(d.y1, d.y0 - 1, -1).map((y) => `<option value="${y}">${y}</option>`).join('')}</select></div><div class="seleziona"><label class="visivo-nascosto" for="t-vel">Velocità</label><select id="t-vel"><option value="1400">Lenta</option><option value="800" ${S.velocita === 800 ? 'selected' : ''}>Media</option><option value="350" ${S.velocita === 350 ? 'selected' : ''}>Veloce</option></select></div></div>`;
    const toggle = (id, testo, on, disab) => `<label class="interruttore" ${disab ? 'title="Non disponibile: l’indicatore contiene valori nulli o negativi"' : ''}><input type="checkbox" id="${id}" ${on ? 'checked' : ''} ${disab ? 'disabled' : ''}><span>${testo}</span></label>`;
    const selettoreHtml = (id, etichetta, opzioni, val) => `<div class="campo"><label for="${id}">${etichetta}</label><div class="seleziona"><select id="${id}">${opzioni.map(([v2, n]) => `<option value="${v2}" ${String(v2) === String(val) ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></div></div>`;
    const renderControlli = () => {
      const log = A.usaLog(cod), nolog = !st.positivi;
      let extra = '';
      if (S.vista === 'andamento') extra = `<button class="pulsante pulsante--piccolo" type="button" id="z-meno" title="Ingrandisci il periodo">${A.icona('piu', '')} Ingrandisci</button><button class="pulsante pulsante--piccolo" type="button" id="z-piu" title="Riduci">${A.icona('meno', '')} Riduci</button><button class="pulsante pulsante--piccolo" type="button" id="z-tutto" ${S.zoom ? '' : 'disabled'}>Tutto il periodo</button>${toggle('o-sfondo', 'Altri territori in grigio', S.sfondo)}${toggle('o-log', 'Scala logaritmica', log, nolog)}`;
      else if (S.vista === 'mappa') extra = (fam === 'eu' ? selettoreHtml('o-liv', 'Livello', A.LIVELLI.map((n, k) => [k, n]), S.livello) + selettoreHtml('o-pae', 'Paese', [['', 'Tutta l’Europa']].concat([...new Set(A.META.territori.filter((t) => t.k === 'nuts').map((t) => t.p))].filter((p) => A.T[p]).sort((a, b) => A.T[a].n.localeCompare(A.T[b].n, 'it')).map((p) => [p, A.T[p].n])), S.paeseEU) : selettoreHtml('o-area', 'Area', Object.entries(A.AREE).map(([k, a]) => [k, a.n]), S.area)) + toggle('o-log', 'Scala logaritmica', log, nolog) + toggle('o-ult', 'Ultimo dato disponibile (fino a 10 anni prima)', S.ultimo);
      else if (S.vista === 'classifica') extra = selettoreHtml('o-n', 'Mostra', [[10, 'Primi 10'], [25, 'Primi 25'], [50, 'Primi 50'], ['tutti', 'Tutti']], S.nBarre) + selettoreHtml('o-ord', 'Ordine', [['desc', 'Valori più alti'], ['asc', 'Valori più bassi']], S.ordine) + toggle('o-ult', 'Ultimo dato disponibile', S.ultimo);
      else extra = toggle('o-agg', 'Mostra gli aggregati', S.aggregati) + toggle('o-ult', 'Ultimo dato disponibile', S.ultimo);
      controlli.innerHTML = tempoHtml() + '<span class="spazio"></span>' + extra;
      $('#t-range').addEventListener('input', (e) => { ferma(); impostaAnno(+e.target.value, false); });
      $('#t-sel').addEventListener('change', (e) => { ferma(); impostaAnno(+e.target.value, true); });
      $('#t-vel').addEventListener('change', (e) => { S.velocita = +e.target.value; });
      $('#t-prev').addEventListener('click', () => { ferma(); impostaAnno(S.anno - 1, true); });
      $('#t-next').addEventListener('click', () => { ferma(); impostaAnno(S.anno + 1, true); });
      $('#t-play').addEventListener('click', () => (S.inRiproduzione ? ferma() : riproduci()));
      aggiornaTempo();
      const on = (id, f) => { const el = $(id); if (el) el.addEventListener('change', f); };
      on('#o-log', (e) => { S.log[cod] = e.target.checked; disegna(); aggiornaUrl(); });
      on('#o-ult', (e) => { S.ultimo = e.target.checked; A.salvaStato(); disegna(); aggiornaUrl(); });
      on('#o-agg', (e) => { S.aggregati = e.target.checked; A.salvaStato(); disegna(); });
      on('#o-sfondo', (e) => { S.sfondo = e.target.checked; A.salvaStato(); disegna(); });
      on('#o-area', (e) => { S.area = e.target.value; A.salvaStato(); disegna(); aggiornaUrl(); });
      on('#o-liv', (e) => { S.livello = +e.target.value; A.salvaStato(); disegna(); aggiornaUrl(); });
      on('#o-pae', (e) => { S.paeseEU = e.target.value; A.salvaStato(); disegna(); aggiornaUrl(); });
      on('#o-n', (e) => { S.nBarre = e.target.value === 'tutti' ? 'tutti' : +e.target.value; disegna(); aggiornaUrl(); });
      on('#o-ord', (e) => { S.ordine = e.target.value; disegna(); aggiornaUrl(); });
      const zoomDi = (k) => { const a0 = S.zoom ? S.zoom[0] : d.y0, a1 = S.zoom ? S.zoom[1] : d.y1, c = (a0 + a1) / 2, half = Math.max(1, (a1 - a0) / 2 * k); let na = Math.round(c - half), nb = Math.round(c + half); na = Math.max(d.y0, na); nb = Math.min(d.y1, nb); if (nb - na < 2) return; S.zoom = na <= d.y0 && nb >= d.y1 ? null : [na, nb]; if (vista && vista.zoom) vista.zoom(); renderControlli(); aggiornaUrl(); };
      const z1 = $('#z-meno'), z2 = $('#z-piu'), z3 = $('#z-tutto');
      if (z1) z1.addEventListener('click', () => zoomDi(0.6));
      if (z2) z2.addEventListener('click', () => zoomDi(1.6));
      if (z3) z3.addEventListener('click', () => { S.zoom = null; if (vista && vista.zoom) vista.zoom(); renderControlli(); aggiornaUrl(); });
    };

    // testi: frase in evidenza e dati mancanti
    const aggiornaTesto = () => {
      const univ = A.universo(cod), cosa = fam === 'eu' ? 'territori' : 'paesi';
      const righe = univ.map((p) => ({ p, r: A.valore(d, p.id, S.anno) })).filter((x) => x.r).sort((a, b) => b.r.v - a.r.v);
      const el = $('#evidenza');
      if (!righe.length) el.textContent = `Nel ${S.anno} nessun territorio ha un valore. Prova un altro anno o attiva l’ultimo dato disponibile.`;
      else {
        const alto = righe[0], basso = righe[righe.length - 1];
        let t = `Nel <strong>${S.anno}</strong>: valore più alto <strong>${esc(alto.p.n)}</strong> (${fmt(alto.r.v)}), più basso <strong>${esc(basso.p.n)}</strong> (${fmt(basso.r.v)}), su ${righe.length} ${cosa} con dato.`;
        const primo = S.sel.map((s) => A.idPer(cod, s)).find((id) => id && univ.some((u) => u.id === id));
        if (primo) { const k = righe.findIndex((x) => x.p.id === primo); t += k >= 0 ? ` <strong>${esc(A.T[primo].n)}</strong>: ${fmt(righe[k].r.v)}, ${k + 1}° posto su ${righe.length}${righe[k].r.y !== S.anno ? ` (dato del ${righe[k].r.y})` : ''}.` : ` ${esc(A.T[primo].n)}: nessun dato nel ${S.anno}.`; }
        el.innerHTML = t;
      }
      const m = univ.filter((p) => !A.valore(d, p.id, S.anno));
      $('#sd-mancanti').innerHTML = `<span class="campione-vuoto" aria-hidden="true"></span>${m.length} ${cosa} su ${univ.length} senza dato nel ${S.anno}${S.ultimo ? ' (anche cercando fino a 10 anni prima)' : ''}`;
      $('#def-mancanti').textContent = m.length ? m.map((p) => p.n).sort((a, b) => a.localeCompare(b, 'it')).join(', ') + '.' : 'Nessuno: tutti hanno un valore.';
    };

    // disegno della vista corrente
    function disegna() {
      ferma();
      if (vista && vista.distruggi) vista.distruggi();
      corpo.innerHTML = ''; legenda.hidden = true; nav.hidden = S.vista !== 'andamento';
      scena.dataset.vista = S.vista;
      $('#anno-filigrana').style.opacity = S.vista === 'mappa' || S.vista === 'classifica' ? '' : '0';
      const ctx = { cod, onSeleziona, onZoom: (z2, giaDisegnato) => { S.zoom = z2; if (!giaDisegnato && vista && vista.zoom) vista.zoom(); renderControlli(); aggiornaUrl(); }, ridisegna };
      if (S.vista === 'andamento') vista = A.grafici.andamento(corpo, nav, ctx);
      else if (S.vista === 'mappa') { legenda.hidden = false; vista = A.grafici.mappa(corpo, legenda, ctx); }
      else if (S.vista === 'classifica') vista = A.grafici.classifica(corpo, ctx);
      else vista = A.grafici.tabella(corpo, ctx);
      renderControlli(); aggiornaTesto();
    }
    disegna(); aggiornaUrl();
    ro = new ResizeObserver((() => { let t; return () => { clearTimeout(t); t = setTimeout(() => { if (document.contains(scena)) disegna(); }, 160); }; })());
    ro.observe(scena);
    return { distruggi: () => { ferma(); if (ro) ro.disconnect(); ro = null; if (vista && vista.distruggi) vista.distruggi(); } };
  };

  /* ---------- profilo di un territorio ---------- */
  A.pagine.t = async (main, parti) => {
    const id = decodeURIComponent(parti.slice(1).join('/'));
    const t = A.T[id];
    if (!t) { main.innerHTML = `<div class="entra prosa"><h1>Territorio non trovato</h1><p>Il codice “${esc(id)}” non è fra i territori dell’Atlante. <a href="#/">Torna alla prima pagina</a>.</p></div>`; return; }
    document.title = `${t.n} · Atlante dei dati`;
    main.innerHTML = '<div class="caricamento">Carico il profilo…</div>';
    const eu = t.k === 'nuts' || t.k === 'agg_eu';
    const tema = eu ? 'eur' : 'pop';
    const prof = await A.caricaProfilo(id);
    const profEu = !eu && A.NUTS0[id] ? await A.caricaProfilo(A.NUTS0[id]) : null;
    const tessera = (c, r, tid) => { const i = A.IND[c]; if (!i) return ''; const [y, v, k, n, y0, sp] = r; return `<a class="tessera" data-tema="${i.fam === 'eu' ? 'eur' : i.t}" href="#/i/${esc(c)}?t=${esc(tid)}"><h3>${esc(i.n)}</h3><div class="tessera__valore">${fmt(v)}<small>${esc(i.u)}</small></div><div class="tessera__pos">${y}${k ? ` · ${k}° su ${n} ${i.fam === 'eu' ? `territori NUTS ${A.T[tid].l}` : 'paesi'}` : ''}</div><div class="mini" data-sp="${esc(JSON.stringify([y0, sp]))}" data-tema="${i.fam === 'eu' ? 'eur' : i.t}"></div></a>`; };
    const sezioneProfilo = (p, tid, titolo) => (p && Object.keys(p.ind).length ? `<section class="sezione"><div class="sezione__testa"><h2>${titolo}</h2><p>Valore più recente, posizione in classifica e andamento degli ultimi trent’anni. Tocca una tessera per aprire l’indicatore con questo territorio selezionato.</p></div><div class="tessere sfalsa">${Object.entries(p.ind).map(([c, r]) => tessera(c, r, tid)).join('')}</div></section>` : '');
    const gia = S.sel.includes(id);
    const archiviCon = (A.META.archivi || []).filter((a) => a.terr.includes(id));
    main.innerHTML = `<div class="entra" data-tema="${tema}">
      ${briciole([{ n: 'Atlante', href: '#/' }, { n: 'Territori' }, { n: t.n }])}
      <header class="profilo-testa"><p class="occhiello">${esc(A.descriviTerritorio(t))}${t.cod ? ` · codice ${esc(t.cod)}` : ''}</p><h1>${esc(t.n)}</h1><p>${t.k === 'paese' ? `Paese o economia della Banca Mondiale${t.r ? `, regione ${esc(A.REG[t.r].n)}` : ''}.` : t.k === 'nuts' ? `Territorio Eurostat di livello NUTS ${t.l}${t.l ? ` in ${esc(A.T[t.p] ? A.T[t.p].n : t.p)}` : ''}.` : 'Aggregato statistico: non va sommato ai paesi.'}</p>
        <div class="chips"><button class="pulsante ${gia ? '' : 'pulsante--accento'}" type="button" id="p-sel">${gia ? 'Togli dai territori selezionati' : 'Aggiungi ai territori selezionati'}</button><a class="pulsante" href="#/confronta?t=${esc([...new Set([id, ...S.sel])].join(','))}&g=${eu ? 'eur' : 'sal'}">Confronta con gli altri selezionati</a>${t.k === 'nuts' && t.id === 'EU:ITH4' ? '<a class="pulsante" href="scheda-fvg.html">Scheda: Friuli Venezia Giulia in Europa</a>' : ''}${t.k === 'paese' && A.NUTS0[id] ? `<a class="pulsante" href="#/i/EU_QUOTA_Y_GE65?v=mappa&liv=2&pae=${id}&t=${A.NUTS0[id]}">Mappa delle regioni</a>` : ''}</div></header>
      ${sezioneProfilo(prof, id, eu ? 'Dati regionali in evidenza (Eurostat e Commissione europea)' : 'Indicatori in evidenza')}
      ${profEu ? sezioneProfilo(profEu, A.NUTS0[id], 'Dati regionali per il paese (Eurostat e Commissione europea)') : ''}
      ${!prof || !Object.keys(prof.ind).length ? `<p class="nota">${t.k === 'aggf' || t.k === 'storico' ? 'Territorio presente solo negli insiemi di dati FAOSTAT, OMS, OCSE, ONU o FMI: nessun indicatore della Banca Mondiale o di Eurostat.' : 'Nessun indicatore in evidenza disponibile per questo territorio.'}</p>` : ''}
      ${archiviCon.length ? `<section class="sezione"><div class="sezione__testa"><h2>Insiemi di dati con questo territorio</h2><p>Insiemi di dati dei lotti in cui compare ${esc(t.n)}: apri l’insieme e cerca una serie.</p></div><div class="archivi-griglia sfalsa">${archiviCon.map((a, idx) => `<a class="archivio-card" data-tema="arc" href="#/archivi/${esc(a.f)}" style="--i:${idx}"><h3>${esc(a.n)}</h3><p>${esc(a.fonte.replace(/ \(.*/, ''))} · ${esc(A.gruppoArchivio(a))}</p><span class="conta">${a.terr.length} territori · ${A.F.int.format(a.serie)} serie · ${a.y0}–${a.y1}</span></a>`).join('')}</div></section>` : ''}
    </div>`;
    $('#p-sel').addEventListener('click', () => { if (S.sel.includes(id)) S.sel.splice(S.sel.indexOf(id), 1); else S.sel.push(id); A.salvaStato(); A.toast(S.sel.includes(id) ? `${t.n} aggiunto ai territori selezionati` : `${t.n} tolto dai territori selezionati`); A.pagine.t(main, parti); });
    main.querySelectorAll('.mini[data-sp]').forEach((el) => { const [y0, sp] = JSON.parse(el.dataset.sp); A.sparkline(el, { y0, valori: sp, colore: A.colori['t_' + el.dataset.tema] }); });
  };

  /* ---------- confronto ---------- */
  A.pagine.confronta = async (main, parti, q) => {
    document.title = 'Confronta · Atlante dei dati';
    if (q.get('t') != null) S.sel = q.get('t').split(',').filter((id) => A.T[id]);
    // il gruppo è un tema oppure, per le Regioni europee (troppi indicatori per una tabella), un sottogruppo: "eur|Economia"
    const gruppoValido = (g) => { const [b, so] = (g || '').split('|'); return !!A.TEMI[b] && b !== 'arc' && (!so || (A.SOTTOGRUPPI[b] || []).some((x) => x[0] === so)); };
    if (q.get('g') && gruppoValido(q.get('g'))) S.temaConf = q.get('g');
    if (!gruppoValido(S.temaConf)) S.temaConf = 'sal';
    if (S.temaConf === 'eur') S.temaConf = 'eur|' + A.SOTTOGRUPPI.eur[0][0];
    const temaBase = () => S.temaConf.split('|')[0];
    const eRegione = (id) => !!A.T[id] && ((A.T[id].k === 'nuts' && A.T[id].l > 0) || A.T[id].k === 'agg_eu');
    // con regioni selezionate si offrono solo i gruppi regionali: gli indicatori nazionali non sono confrontabili fra regioni
    const opzioniGruppi = () => {
      const ordine = S.sel.some(eRegione) ? ['eur'] : temiConIndicatori();
      return ordine.map((k) => (k === 'eur' ? A.SOTTOGRUPPI.eur.map((g) => `<option value="eur|${esc(g[0])}" ${`eur|${g[0]}` === S.temaConf ? 'selected' : ''}>${esc(A.TEMI.eur.n)} · ${esc(g[0])}</option>`).join('') : `<option value="${k}" ${k === S.temaConf ? 'selected' : ''}>${esc(A.TEMI[k].n)}</option>`)).join('');
    };
    main.innerHTML = `<div class="entra" data-tema="${temaBase()}">
      ${briciole([{ n: 'Atlante', href: '#/' }, { n: 'Confronta' }])}
      <div class="esplora__titolo"><h1>Confronta paesi e regioni</h1><p class="evidenza">Scegli i territori e un gruppo di indicatori: ogni riga è un indicatore, ogni colonna un territorio, con il valore più recente disponibile o quello dell’anno scelto.</p></div>
      <div class="comandi comandi--territori" id="box-territori"></div>
      <div class="comandi"><div class="campo"><label for="c-tema">Gruppo di indicatori</label><div class="seleziona"><select id="c-tema">${opzioniGruppi()}</select></div></div><div class="campo"><label for="c-anno">Anno</label><div class="seleziona"><select id="c-anno"><option value="">Più recente disponibile</option></select></div></div><div class="campo"><label>&nbsp;</label><button class="pulsante" type="button" id="c-csv">${A.icona('scarica', '')} Scarica la tabella (CSV)</button></div></div>
      <div class="confronto" id="confronto"><div class="caricamento">Carico…</div></div>
      <p class="nota">▲ valore più alto fra i territori selezionati. “Non previsto”: l’indicatore non esiste per quel tipo di territorio. Un paese mostra anche i dati regionali nazionali (Eurostat e Commissione europea); una regione solo quelli.</p>
    </div>`;
    let righeCsv = [];
    const disegna = async () => {
      // gli indicatori della Banca Mondiale esistono solo per i paesi: con sole regioni selezionate si passa ai gruppi regionali
      let cambiato = false;
      const terrSel = S.sel.filter((id) => A.T[id]);
      if (terrSel.some(eRegione) && S.temaConf.split('|')[0] !== 'eur') { S.temaConf = 'eur|' + A.SOTTOGRUPPI.eur[0][0]; main.firstElementChild.dataset.tema = 'eur'; A.salvaStato(); cambiato = true; }
      $('#c-tema').innerHTML = opzioniGruppi();
      const [tb, ts] = S.temaConf.split('|');
      const inds = indicatoriDi(tb).filter((i) => !ts || A.sottogruppo(i) === ts);
      const box = $('#confronto'); box.innerHTML = '<div class="caricamento">Carico…</div>';
      await Promise.all(inds.map((i) => A.carica(i.c)));
      const sel = $('#c-anno'); const anni = d3.range(d3.max(inds, (i) => i.y1), d3.min(inds, (i) => i.y0) - 1, -1);
      const scelto = sel.value ? +sel.value : null;
      sel.innerHTML = '<option value="">Più recente disponibile</option>' + anni.map((y) => `<option value="${y}" ${y === scelto ? 'selected' : ''}>${y}</option>`).join('');
      const terr = S.sel.filter((id) => A.T[id]);
      if (terr.length < 2) { box.innerHTML = `<div class="confronto__vuoto"><p>Per confrontare servono almeno due territori: cercali qui sopra oppure scegli un confronto pronto.</p><div class="chips">${A.PRESET.map((p, k) => `<button class="chip" type="button" data-p="${k}">${esc(p.n)}</button>`).join('')}</div></div>`; box.querySelectorAll('[data-p]').forEach((b) => b.addEventListener('click', () => { S.sel = A.PRESET[+b.dataset.p].ids.filter((id) => A.T[id]); A.salvaStato(); selettore.disegna(); disegna(); })); return; }
      const val = (i, id) => { const k = A.idPer(i.c, id); if (!k) return { k: null }; const d = A.dati(i.c); const r = scelto ? (A.ultimo(d, k) && d.d[k] && d.d[k][scelto - d.y0] != null ? { v: d.d[k][scelto - d.y0], y: scelto } : null) : A.ultimo(d, k); return { k, r }; };
      const righe = inds.map((i) => { const celle = terr.map((id) => ({ id, ...val(i, id) })); const vals = celle.filter((c) => c.r).map((c) => c.r.v); return { i, celle, max: vals.length ? d3.max(vals, Math.abs) : 0, n: vals.length }; }).filter((r) => r.n >= Math.min(2, terr.length));
      righeCsv = [['indicatore', 'unita'].concat(terr.map((id) => A.T[id].n))].concat(righe.map((rg) => [rg.i.n, rg.i.u].concat(rg.celle.map((c) => (c.r ? `${String(c.r.v).replace('.', ',')} (${c.r.y})` : '')))));
      const chipsEur = A.SOTTOGRUPPI.eur.map((g) => `<button class="chip" type="button" data-g="eur|${esc(g[0])}">${esc(g[0])}</button>`).join('');
      const regioniSenza = tb !== 'eur' ? terr.filter(eRegione) : [];
      const avviso = terr.some(eRegione) ? `<div class="avviso confronto__avviso">Con regioni selezionate si confrontano solo i dati regionali di Eurostat e della Commissione europea (${cambiato ? `gruppo passato a “${esc(A.TEMI.eur.n)} · ${esc(ts)}”; ` : ''}gli indicatori nazionali della Banca Mondiale non esistono per le regioni). Altri gruppi:<div class="chips">${chipsEur}</div></div>`
        : regioniSenza.length ? `<div class="avviso confronto__avviso">Gli indicatori del gruppo “${esc(A.TEMI[tb].n)}” sono nazionali (Banca Mondiale) e non esistono per ${regioniSenza.map((id) => esc(A.T[id].n)).join(', ')}.</div>` : '';
      box.innerHTML = avviso + `<table class="confronto__tabella"><caption class="visivo-nascosto">Confronto fra territori</caption><thead><tr><th scope="col">Indicatore</th>${terr.map((id) => `<th scope="col"><a href="#/t/${esc(id)}"><span class="pallino${A.eAggregato(id) ? ' pallino--agg' : ''}" style="${A.eAggregato(id) ? '' : `background:${A.coloreRegione(id)}`}"></span> ${esc(A.T[id].n)}</a><span class="confronto__tipo">${esc(A.descriviTerritorio(A.T[id]))}</span></th>`).join('')}</tr></thead><tbody>${righe.map((rg) => `<tr><th scope="row"><a class="confronto__ind" href="#/i/${esc(rg.i.c)}?t=${esc(terr.join(','))}">${esc(rg.i.n)}</a><span class="confronto__unita">${esc(rg.i.u)}</span></th>${rg.celle.map((c) => { if (!c.k) return '<td class="nd" title="Indicatore non disponibile per questo tipo di territorio">non previsto</td>'; if (!c.r) return '<td class="nd">n.d.</td>'; const larg = rg.max ? Math.abs(c.r.v) / rg.max * 100 : 0; const top = rg.n > 1 && Math.abs(c.r.v) === rg.max; return `<td><span class="confronto__valore${top ? ' confronto__valore--max' : ''}">${fmt(c.r.v)}</span><span class="confronto__anno">${c.r.y}</span><span class="confronto__barra"><span style="width:${larg}%;background:${A.eAggregato(c.id) ? A.colori.grafite : A.coloreRegione(c.id)}"></span></span></td>`; }).join('')}</tr>`).join('')}</tbody></table>${inds.length - righe.length ? `<p class="nota confronto__nota">${inds.length - righe.length} indicatori del gruppo non hanno dati per almeno due dei territori selezionati e non sono mostrati.</p>` : ''}`;
      box.querySelectorAll('[data-g]').forEach((b) => b.addEventListener('click', () => { S.temaConf = b.dataset.g; main.firstElementChild.dataset.tema = 'eur'; A.salvaStato(); disegna(); }));
      A.sostituisci(`#/confronta?t=${S.sel.join(',')}&g=${S.temaConf}`);
    };
    const selettore = A.selettoreTerritori($('#box-territori'), { onChange: disegna });
    $('#c-tema').addEventListener('change', (e) => { S.temaConf = e.target.value; main.firstElementChild.dataset.tema = temaBase(); A.salvaStato(); disegna(); });
    $('#c-anno').addEventListener('change', disegna);
    $('#c-csv').addEventListener('click', () => { const testo = '﻿' + righeCsv.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\r\n'); const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([testo], { type: 'text/csv;charset=utf-8' })); a.download = 'atlante_confronto.csv'; document.body.appendChild(a); a.click(); a.remove(); A.toast('File CSV in scaricamento'); });
    await disegna();
  };

  /* ---------- insiemi di dati (archivi dei lotti) ---------- */
  A.pagine.archivi = async (main, parti) => {
    const elenco = A.META.archivi || [];
    const f = parti[1];
    if (f && A.ARC[f]) {
      const a = A.ARC[f];
      document.title = `${a.n} · Archivi · Atlante dei dati`;
      main.innerHTML = `<div class="entra" data-tema="arc">${briciole([{ n: 'Atlante', href: '#/' }, { n: 'Archivi', href: '#/archivi' }, { n: a.n }])}
        <header class="tema-testa"><div class="tema-testa__riga">${A.icona('arc')}<h1>${esc(a.n)}</h1></div><p>${esc(a.fonte)}, insieme di dati ${esc(a.cod)}, argomento “${esc(A.gruppoArchivio(a))}”, lotto ${a.lotto}. ${a.archivio ? `<strong>Archivio parziale:</strong> la fonte distribuisce questo insieme di dati in più archivi e il repository ne contiene solo una parte (${esc(a.archivio)}), cioè ${a.terr.length} territori` : `<strong>Insieme completo:</strong> ${a.terr.length} territori`}${a.aggr && a.aggr.length ? ` (di cui ${a.aggr.length} aggregati)` : ''}. ${A.F.int.format(a.serie)} serie dal ${a.y0} al ${a.y1}, ${A.F.int.format(a.righe || 0)} osservazioni; descrizioni in inglese, come nella fonte. Nome originale: ${esc(a.en)}.</p><div class="chips">${a.terr.slice(0, 40).map((id) => (A.T[id] ? `<a class="chip" href="#/t/${esc(id)}">${esc(A.T[id].n)}</a>` : '')).join('')}${a.terr.length > 40 ? `<span class="nd">e altri ${a.terr.length - 40}</span>` : ''}</div></header>
        <div class="comandi" style="grid-template-columns:1fr"><div class="campo"><label for="a-cerca">Cerca una serie</label><div class="combo"><input id="a-cerca" type="search" placeholder="es. wheat, nitrogen, import" autocomplete="off"></div></div></div>
        <ul class="serie-lista" id="a-serie"><li class="nota">Carico le serie…</li></ul></div>`;
      const ul = $('#a-serie'), inp = $('#a-cerca');
      let serie = [];
      const disegna = () => {
        const nq = A.norm(inp.value.trim());
        const parole = nq.split(/\s+/).filter(Boolean);
        const trov = serie.map((s, k) => ({ s, k, n: s.n })).filter((o) => { if (!parole.length) return true; const t = A.norm(`${o.s.l} ${o.s.u} ${o.s.cod || ''}`); return parole.every((w) => t.includes(w)); }).sort((x, y) => y.n - x.n || x.s.l.localeCompare(y.s.l));
        ul.innerHTML = trov.slice(0, 120).map((o) => `<li><button type="button" data-k="${o.k}"><span>${esc(o.s.l)}</span><span class="tipo">${esc(o.s.u || 'unità non indicata')} · dal ${o.s.y0} al ${o.s.y1} · ${o.n} territori</span></button></li>`).join('') + (trov.length > 120 ? `<li class="nota">Altre ${A.F.int.format(trov.length - 120)} serie: restringi la ricerca (più parole restringono).</li>` : '') + (!trov.length ? '<li class="nota">Nessuna serie corrisponde alla ricerca.</li>' : '');
        ul.querySelectorAll('button').forEach((b) => b.addEventListener('click', async () => { const id = `A:${f}:${b.dataset.k}`; await A.registraSerie(id); S.vista = 'mappa'; S.area = 'mondo'; A.vai(`#/i/${id}?v=mappa`); }));
      };
      try { serie = (await A.caricaArchivio(f)).s; A.cache[f + '_serie'] = serie; } catch (e) { ul.innerHTML = '<li class="nota">Non riesco a caricare questo archivio.</li>'; return; }
      let t; inp.addEventListener('input', () => { clearTimeout(t); t = setTimeout(disegna, 120); });
      disegna();
      return;
    }
    document.title = 'Insiemi di dati · Atlante dei dati';
    const PC = await A.caricaPartner().catch(() => null);
    const bilaterali = PC ? `<section class="sezione"><div class="sezione__testa"><h2>Matrici bilaterali: vista Partner</h2><p>FAOSTAT · per ogni paese i valori di ciascun partner o donatore, su mappa e in tabella</p></div><div class="archivi-griglia sfalsa">${PC.insiemi.map((x, idx) => `<a class="archivio-card" data-tema="arc" href="#/partner/${esc(x.k)}" style="--i:${idx}"><h3>${esc(x.n)}</h3><p>${esc(x.en)}</p><span class="conta">${x.terr.length} ${x.ruolo === 'destinatario' ? 'destinatari' : 'dichiaranti'} · ${Object.keys(x.partner).length} ${x.ruoloPartner === 'donatore' ? 'donatori' : 'partner'} · ${A.F.int.format(x.oss)} osservazioni · ${x.anni[0]}–${x.anni[1]}</span></a>`).join('')}</div></section>` : '';
    const ordineGruppi = A.GRUPPI_ARCHIVI.map((g) => g[0]).concat(Object.values(A.GRUPPI_FONTI), ['Altri insiemi di dati']);
    const perGruppo = new Map(); elenco.forEach((a) => { const g = A.gruppoArchivio(a); if (!perGruppo.has(g)) perGruppo.set(g, []); perGruppo.get(g).push(a); });
    main.innerHTML = `<div class="entra" data-tema="arc">${briciole([{ n: 'Atlante', href: '#/' }, { n: 'Archivi' }])}
      <header class="tema-testa"><div class="tema-testa__riga">${A.icona('arc')}<h1>Insiemi di dati</h1></div><p>${A.TEMI.arc.breve} ${elenco.filter((a) => !a.archivio).length} insiemi completi e ${elenco.filter((a) => a.archivio).length} ancora parziali (per questi il repository contiene solo una parte degli archivi della fonte, quindi solo alcuni paesi: la copertura è indicata in ogni scheda). Scegli un argomento e un insieme di dati, poi una serie: si apre su mappa, andamento, classifica e tabella. Le tre matrici bilaterali FAOSTAT (commercio e fertilizzanti per paese partner, aiuti per donatore) hanno una vista dedicata, la vista Partner.</p></header>
      ${bilaterali}
      ${ordineGruppi.filter((g) => perGruppo.has(g)).map((g) => { const arr = perGruppo.get(g).slice().sort((x, y) => x.n.localeCompare(y.n)); return `<section class="sezione"><div class="sezione__testa"><h2>${esc(g)}</h2><p>${arr.length === 1 ? 'un insieme di dati' : `${arr.length} insiemi di dati`} · ${esc([...new Set(arr.map((a) => a.fonte.replace(/ \(.*/, '')))].join(', '))}</p></div><div class="archivi-griglia sfalsa">${arr.map((a, idx) => `<a class="archivio-card" data-tema="arc" href="#/archivi/${esc(a.f)}" style="--i:${idx}"><h3>${esc(a.n)}</h3><p>${esc(a.en)}</p><span class="conta">${a.archivio ? 'parziale · ' : ''}${a.terr.length} territori · ${A.F.int.format(a.serie)} serie · ${a.y0}–${a.y1}</span></a>`).join('')}</div></section>`; }).join('')}
    </div>`;
  };

  /* ---------- fonti e metodo ---------- */
  A.pagine.fonti = async (main) => {
    document.title = 'Fonti e metodo · Atlante dei dati';
    const PC = await A.caricaPartner().catch(() => null);
    const archivi = (A.META.archivi || []).slice().sort((a, b) => A.gruppoArchivio(a).localeCompare(A.gruppoArchivio(b)) || a.n.localeCompare(b.n));
    const nPaesi = A.PAESI.length, nNuts = A.META.territori.filter((t) => t.k === 'nuts').length;
    const nWb = Object.values(A.IND).filter((i) => i.fam === 'wb').length, nEu = Object.values(A.IND).filter((i) => i.fam === 'eu' && i.lotto !== 'regio').length, nReg = Object.values(A.IND).filter((i) => i.lotto === 'regio').length;
    const righe = [
      ['Banca Mondiale, WDI (Indicatori di sviluppo mondiale)', `${nWb} indicatori su popolazione, salute, istruzione, ambiente, energia, acqua, agricoltura e digitale`, `completa: ${nPaesi} paesi e ${A.META.territori.filter((t) => t.k === 'agg').length} aggregati, dal 1960`],
      ['Eurostat, statistiche regionali', `${nEu} indicatori: popolazione, età, nascite, decessi e migrazioni; proiezioni di popolazione al 2100; economia, valore aggiunto, retribuzioni e produttività; lavoro; istruzione; ricerca; salute, cause di morte, ricoveri e personale sanitario; condizioni di vita e reati; digitale (famiglie e imprese); turismo; trasporti; agricoltura, aziende agricole e conti dell’agricoltura; impianti per i rifiuti ed erosione del suolo; imprese e innovazione. I file originali dell’API di Eurostat (scaricati il ${A.data(A.META.acquisizione.api || '')}) sono conservati nel repository`, `completa per i territori pubblicati da Eurostat: ${nNuts} codici NUTS (paesi, macroregioni, regioni, province; anche codici delle versioni precedenti della classificazione); a seconda dell’indicatore il dettaglio arriva alle regioni (NUTS 2) o alle province (NUTS 3)`],
      ['Commissione europea, DG REGIO (piattaforma cohesiondata, trovata su data.europa.eu)', `${nReg} indicatori: indice di competitività regionale RCI 2.0 (2016, 2019, 2022); indice di progresso sociale EU-SPI (edizioni 2020 e 2024); indice di qualità delle istituzioni EQI (2010, 2013, 2017, 2021, 2024); monitor regionale di genere 2021; emissioni di gas serra per abitante e intensità carbonica 1990-2021 (stime JRC); pagamenti dei fondi europei per regione 1989-2022; produzione e potenziale di energia rinnovabile da sole e vento per provincia (stima JRC). I file originali (scaricati il ${A.data(A.META.acquisizione.regio || '')}) sono conservati nel repository`, 'regioni NUTS 2 dei paesi dell’Unione europea (province NUTS 3 per le rinnovabili); gli indici hanno pochi anni di riferimento, le serie dei gas serra e dei fondi partono dal 1990 e dal 1989'],
    ];
    const perFonte = (src) => archivi.filter((a) => a.src === src);
    const descr = (src, testo) => { const arr = perFonte(src); if (!arr.length) return null; const comp = arr.filter((a) => !a.archivio).length, parz = arr.length - comp; return [arr[0].fonte, `${arr.length} insiemi di dati (${A.F.int.format(arr.reduce((t, a) => t + a.serie, 0))} serie): ${testo}`, `${comp ? `${comp} insiemi completi (tutti i territori pubblicati dalla fonte)` : ''}${comp && parz ? '; ' : ''}${parz ? `${parz} insiemi ancora parziali, con i soli paesi degli archivi presenti nel repository (elenco qui sotto)` : ''}`]; };
    [descr('FAOSTAT', 'produzione, prezzi, bilanci alimentari, commercio, fertilizzanti e terreni, emissioni, foreste, popolazione rurale, aiuti e investimenti'),
     descr('WHO', 'speranza di vita, mortalità, fattori di rischio (pressione, glicemia, colesterolo, peso, alcol, attività fisica), personale sanitario, suicidi; per sesso ed età'),
     descr('OECD', 'istruzione degli adulti e personale scolastico'), descr('UNSD', 'tavole dell’annuario statistico delle Nazioni Unite'),
     descr('IMF', 'cruscotto climatico del Fondo monetario internazionale'), descr('DATA_EUROPA', 'dataset comunale di Karlsruhe nel catalogo europeo')].filter(Boolean).forEach((r) => righe.push(r));
    if (PC) righe.push(['FAOSTAT, matrici bilaterali (vista Partner)', PC.insiemi.map((x) => `${x.n} (${x.k}, lotto ${x.lotto}): ${A.F.int.format(x.oss)} osservazioni dal ${x.anni[0]} al ${x.anni[1]}`).join('; '), `complete: ${PC.insiemi.map((x) => `${x.terr.length} ${x.ruolo === 'destinatario' ? 'destinatari' : 'dichiaranti'} e ${Object.keys(x.partner).length} ${x.ruoloPartner === 'donatore' ? 'donatori' : 'partner'} (${x.k})`).join('; ')}; un file per paese, letto solo quando lo si apre`]);
    const parziali = archivi.filter((a) => a.archivio);
    const soloIndici = [
      'Eurostat: i dati su lavoro e altri temi regionali citati negli indici dei lotti non sono nei lotti; l’Atlante li ha presi direttamente dall’API di Eurostat (tabella qui sopra).',
      'FAOSTAT: apporti alimentari da indagini individuali (FDIQ, lotto 25), organizzati per indagine e non per anno, quindi non rappresentabili nelle viste dell’Atlante.',
    ];
    main.innerHTML = `<div class="entra prosa">${briciole([{ n: 'Atlante', href: '#/' }, { n: 'Fonti e metodo' }])}
      <h1>Fonti e metodo</h1>
      <p>L’Atlante mostra tutti i <strong>valori</strong> contenuti nel repository <a href="https://github.com/GuidoCostalonga/open-data" target="_blank" rel="noopener">open data</a>. I file che contengono solo indici, registri o guide descrivono dati che nel repository non ci sono, e sono elencati qui come tali.</p>
      <h2>Che cosa contiene l’Atlante</h2>
      <div class="tabella-prosa"><table><thead><tr><th>Fonte</th><th>Contenuto</th><th>Copertura</th></tr></thead><tbody>${righe.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <h2>Insiemi di dati ancora parziali</h2>
      <p>Per questi insiemi il repository contiene solo una parte degli archivi della fonte, indicata qui. Un paese assente non è un dato mancante della fonte: è un archivio che non è nel repository. Gli altri ${archivi.length - parziali.length} insiemi sono completi.</p>
      <div class="tabella-prosa"><table><thead><tr><th>Insieme di dati</th><th>Argomento</th><th>Nel repository</th><th>Territori</th></tr></thead><tbody>${parziali.map((a) => `<tr><td><a href="#/archivi/${esc(a.f)}">${esc(a.n)}</a><br><span class="nd">${esc(a.fonte.replace(/ \(.*/, ''))}, ${esc(a.cod)}</span></td><td>${esc(A.gruppoArchivio(a))}</td><td>${esc(a.archivio)}</td><td>${a.terr.length}</td></tr>`).join('')}</tbody></table></div>
      ${(A.META.archivi_esclusi || []).length ? `<h2>Insiemi di dati presenti ma non rappresentabili</h2>
      <p>Questi insiemi sono nei lotti e sono stati letti integralmente, ma ogni loro serie ha una sola osservazione (indagini, censimenti, rilevazioni per sottogruppo): non sono serie annuali per territorio e le viste dell’Atlante non li possono mostrare.</p>
      <ul>${A.META.archivi_esclusi.map((a) => `<li>${esc(a.n)} (${esc(a.fonte.replace(/ \(.*/, ''))} ${esc(a.cod)}, lotto ${a.lotto}): ${A.F.int.format(a.serie)} serie e ${A.F.int.format(a.righe)} osservazioni; ${esc(a.motivo)}.</li>`).join('')}</ul>` : ''}
      <h2>Dati presenti solo come indici o guide</h2>
      <ul>${soloIndici.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>
      <h2>Come leggere i valori</h2>
      <ul>
        <li>Nessun valore è stimato o interpolato dall’Atlante. Gli anni senza dato restano vuoti: tratteggio sulla mappa, interruzioni nelle linee, “n.d.” (non disponibile) in tabella e nel confronto.</li>
        <li>Insiemi di dati parziali: un paese assente non è un dato mancante della fonte, è un file che non è nel repository. La mappa lo mostra in grigio come “non nel repository”.</li>
        <li>Negli insiemi di dati ogni osservazione conserva il contrassegno della fonte (dato ufficiale, stima, valore imputato, previsione): compare nelle note della tabella. Le stime e le previsioni restano tali e non vengono trasformate in dati osservati.</li>
        <li>Le tre quote di popolazione per età Eurostat sono calcolate dall’Atlante: popolazione della classe d’età divisa per la popolazione totale, stesso territorio e stesso anno, per 100. I due totali dei pagamenti dei fondi europei sono la somma, per regione e anno, dei sette fondi pubblicati dalla Commissione (sommando anche i periodi di programmazione che si sovrappongono nello stesso anno). Posizioni in classifica, mediane e variazioni sono calcolate dai valori della fonte. Tutti gli altri numeri sono quelli pubblicati.</li>
        <li>Alcuni indicatori sono stime o proiezioni della fonte stessa, non misurazioni: gas serra regionali e potenziale rinnovabile (modelli del Centro comune di ricerca), spesa modellata dei fondi europei, erosione del suolo, proiezioni di popolazione al 2100. La scheda dell’indicatore lo dichiara in evidenza.</li>
        <li>L’opzione “ultimo dato disponibile” riporta il valore più recente dei 10 anni precedenti e mostra sempre l’anno effettivo del dato.</li>
        <li>Per la visualizzazione i valori decimali sono arrotondati a 6 cifre significative; i conteggi interi restano esatti. Il valore originale è negli Excel del repository.</li>
        <li>Le percentuali sono nella scala della fonte: 35 significa 35%.</li>
        <li>Gli aggregati (Mondo, Unione europea, fasce di reddito, regioni FAOSTAT) sono calcolati dalle fonti e non vanno sommati ai paesi.</li>
        <li>Vista Partner (matrici bilaterali FAOSTAT dei lotti 19, 26 e 31): ogni valore è quello della riga originale per la coppia dichiarante e partner (o destinatario e donatore), con il suo contrassegno sempre visibile. L’Atlante non somma i partner, non calcola saldi fra importazioni ed esportazioni, che restano elementi separati, e non mette a confronto le dichiarazioni dei due paesi della coppia, che possono non coincidere. Donatori che sono organizzazioni o fondazioni e territori storici senza codice ISO3 compaiono solo in tabella.</li>
        <li>Negli insiemi di dati una serie è definita dalle dimensioni originali della fonte (prodotto, elemento, sesso, età, unità) senza il territorio, così da confrontare i paesi; le dimensioni originali sono riportate nella scheda della serie.</li>
      </ul>
      <h2>Mappe</h2>
      <p>Paesi e regioni del mondo: Natural Earth, scala 1:50 milioni, versione 5.1.2, campi <em>REGION_WB</em> e <em>CONTINENT</em>. Regioni europee: GISCO (Sistema d’informazione geografica della Commissione europea), NUTS (Nomenclatura delle unità territoriali statistiche) versione 2024, scala 1:10 milioni; © EuroGeographics per i confini amministrativi. I confini sono semplificati e non implicano alcuna posizione sullo status dei territori. I codici area FAOSTAT sono collegati ai codici ISO3 tramite il codice M49 dei dizionari originali.</p>
      <h2>Sigle</h2>
      <p>WDI: Indicatori di sviluppo mondiale della Banca Mondiale. OMS: Organizzazione mondiale della sanità. OCSE: Organizzazione per la cooperazione e lo sviluppo economico. FAOSTAT: banca dati statistica dell’Organizzazione delle Nazioni Unite per l’alimentazione e l’agricoltura. PAM: Programma alimentare mondiale. BIRS: Banca internazionale per la ricostruzione e lo sviluppo. AIS: Associazione internazionale per lo sviluppo. PM2,5: particolato fine con diametro fino a 2,5 micrometri.</p>
    </div>`;
  };

  /* ---------- avvio ---------- */
  A.avvia = async () => {
    const main = $('#contenuto');
    try {
      const [meta, geo, nuts, pano2] = await Promise.all(['dati/meta.json', 'dati/mondo.topo.json', 'dati/nuts.topo.json', 'dati/panoramica.json'].map(A.caricaJson));
      A.META = meta; A.GEO = geo; A.GEO_NUTS = nuts; A.PANO = pano2.ind || {};
    } catch (e) { main.innerHTML = '<div class="caricamento">Impossibile leggere i file di dati. Apri il sito da un server web, non direttamente dal disco.</div>'; return; }
    A.META.territori.forEach((t) => { A.T[t.id] = t; if (t.k === 'nuts' && t.l === 0) A.NUTS0[t.p] = t.id; });
    A.PAESI = A.META.territori.filter((t) => t.k === 'paese');
    A.META.indicatori.forEach((i) => { A.IND[i.c] = Object.assign({ fam: 'wb' }, i); });
    A.META.regioni.forEach((r, i) => { A.REG[r.k] = Object.assign({ i }, r); });
    (A.META.archivi || []).forEach((a) => { A.ARC[a.f] = a; });
    A.leggiStato();
    S.sel = S.sel.filter((id) => A.T[id]);
    A.leggiColori();
    A.costruisciIndice();
    A.preparaTestata();
    const ricolora = () => { A.leggiColori(); A.instrada(); };
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', ricolora);
    new MutationObserver(ricolora).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    addEventListener('hashchange', A.instrada);
    A.instrada();
  };
  A.avvia();
})(window.Atlante);
