// Prove dei gesti sulle mappe dell'Atlante con veri eventi multitocco di Chromium (CDP Input.dispatchTouchEvent).
// Controlla: pizzico per ingrandire e ridurre centrato fra le dita, limiti di zoom, ripristino, scorrimento della pagina con un dito,
// tocco che seleziona un comune, nessuna selezione dopo trascinamenti o pizzichi, schermo intero, rotazione, interruzioni,
// mappe di autobus, aria e allerte, rotella e trascinamento del mouse, tastiera.
// Uso:  npm i --no-save playwright-core   e un Chromium installato, poi
//       BASE=https://atlantefvg.it/ CHROMIUM=/percorso/chrome node prove/gesti.js
//       (oppure SITE=/cartella/del/sito per provare i file locali su https://atlante.prova/)
// Non sostituisce la prova su un telefono vero: Safari su iPhone non si può pilotare da qui.
const pw = require(process.env.PWPATH || 'playwright-core'); const fs = require('fs');
const BASE = process.env.BASE || (process.env.SITE ? 'https://atlante.prova/' : 'https://atlantefvg.it/');
let fallite = 0;
const ok = (cond, msg) => { console.log((cond ? 'OK   ' : 'FALLITA ') + msg); if (!cond) fallite++; };
(async () => {
  const b = await pw.chromium.launch({ executablePath: process.env.CHROMIUM || undefined, proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined, args: ['--no-sandbox'] });
  const errs = [];
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  if (BASE.includes('atlante.prova')) await p.route('https://atlante.prova/**', r => { let fp = process.env.SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: fp.endsWith('.html') ? 'text/html; charset=utf-8' : 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
  await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
  p.on('pageerror', e => errs.push(e + ''));
  const cdp = await ctx.newCDPSession(p);
  const tocco = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map((q, i) => ({ x: q[0], y: q[1], id: i + 1, radiusX: 4, radiusY: 4, force: 1 })) });
  async function pizzico(cx, cy, d0, d1, passi = 12) {
    await tocco('touchStart', [[cx - d0 / 2, cy]]); await tocco('touchStart', [[cx - d0 / 2, cy], [cx + d0 / 2, cy]]);
    for (let k = 1; k <= passi; k++) { const d = d0 + (d1 - d0) * k / passi; await tocco('touchMove', [[cx - d / 2, cy], [cx + d / 2, cy]]); await p.waitForTimeout(16); }
    await tocco('touchEnd', [[cx + d1 / 2, cy]]); await tocco('touchEnd', []); await p.waitForTimeout(120);
  }
  async function trascina(x0, y0, x1, y1, passi = 12) {
    await tocco('touchStart', [[x0, y0]]);
    for (let k = 1; k <= passi; k++) { await tocco('touchMove', [[x0 + (x1 - x0) * k / passi, y0 + (y1 - y0) * k / passi]]); await p.waitForTimeout(16); }
    await tocco('touchEnd', []); await p.waitForTimeout(200);
  }
  const stato = sel => p.evaluate(s => { const svg = document.querySelector(s), vb = svg.viewBox.baseVal; return { x: vb.x, y: vb.y, w: vb.width, h: vb.height, scroll: scrollY, scala: visualViewport.scale, com: terr.com }; }, sel);
  // punto della mappa sotto un punto dello schermo
  const puntoMappa = (sel, cx, cy) => p.evaluate(([s, cx, cy]) => { const svg = document.querySelector(s), q = svg.createSVGPoint(); q.x = cx; q.y = cy; const r = q.matrixTransform(svg.getScreenCTM().inverse()); return [r.x, r.y]; }, [sel, cx, cy]);

  await p.goto(BASE + 'index.html?pagina=mappe', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(1500);
  const box = await p.locator('#svgMappa').boundingBox();
  // la mappa in vista
  await p.evaluate(() => document.getElementById('svgMappa').scrollIntoView({ block: 'center' })); await p.waitForTimeout(300);
  const bb = await p.locator('#svgMappa').boundingBox();
  // il punto medio sta un po' a sinistra del centro, così con le dita larghe non si tocca la colonna dei pulsanti di ingrandimento
  const cx = bb.x + bb.width * 0.45, cy = bb.y + bb.height * 0.5;
  // 1. pizzico per ingrandire, centrato sul punto medio
  let s0 = await stato('#svgMappa'); const sotto0 = await puntoMappa('#svgMappa', cx, cy);
  await pizzico(cx, cy, 60, 220);
  let s1 = await stato('#svgMappa'); const sotto1 = await puntoMappa('#svgMappa', cx, cy);
  ok(s1.w < s0.w * 0.45, `pizzico allargando: la mappa si ingrandisce (larghezza vista ${Math.round(s0.w)} → ${Math.round(s1.w)})`);
  ok(Math.hypot(sotto1[0] - sotto0[0], sotto1[1] - sotto0[1]) < s0.w * 0.02, `lo zoom resta centrato sul punto medio fra le dita (scarto ${Math.round(Math.hypot(sotto1[0] - sotto0[0], sotto1[1] - sotto0[1]))} unità)`);
  ok(s1.scroll === s0.scroll && s1.scala === 1, `la pagina non scorre e non si ingrandisce (scorrimento ${s0.scroll} → ${s1.scroll}, scala ${s1.scala})`);
  ok(s1.com === s0.com, 'il pizzico non seleziona un comune');
  // 2. pizzico per ridurre
  await pizzico(cx, cy, 240, 80);
  let s2 = await stato('#svgMappa'); ok(s2.w > s1.w * 2, `pizzico stringendo: la mappa si riduce (${Math.round(s1.w)} → ${Math.round(s2.w)})`);
  // 3. limite di zoom
  for (let k = 0; k < 6; k++) await pizzico(cx, cy, 40, 300, 8);
  const lim = await p.evaluate(() => vb.w / vb0.w); ok(lim >= 1 / 25 - 1e-6, `limite di ingrandimento rispettato (vista ${lim.toFixed(3)} della larghezza iniziale, minimo 0,040)`);
  await p.click('#riquadroMappa [data-z="reset"]'); await p.waitForTimeout(200);
  const r0 = await p.evaluate(() => Math.abs(vb.w - vb0.w) < 1 && Math.abs(vb.x - vb0.x) < 1); ok(r0, 'il pulsante «Ripristina» torna alla vista iniziale');
  // 4. un dito in verticale fa scorrere la pagina, non sposta la mappa e non seleziona
  s0 = await stato('#svgMappa');
  await trascina(cx, cy + 120, cx, cy - 120);
  s1 = await stato('#svgMappa');
  ok(s1.scroll > s0.scroll + 50, `un dito fa scorrere la pagina (scorrimento ${s0.scroll} → ${s1.scroll})`);
  ok(Math.abs(s1.x - s0.x) < 1 && Math.abs(s1.w - s0.w) < 1, 'un dito nella pagina normale non sposta la mappa');
  ok(s1.com === s0.com, 'lo scorrimento non seleziona un comune');
  // 5. tocco breve su un comune: selezione e pannello dal basso
  await p.evaluate(() => document.getElementById('svgMappa').scrollIntoView({ block: 'center' })); await p.waitForTimeout(300);
  const centro = await p.evaluate(() => { const el = document.querySelector('#svgMappa .unita[data-i="' + NOME_COM.indexOf('Udine') + '"]'), r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
  await tocco('touchStart', [centro]); await p.waitForTimeout(60); await tocco('touchEnd', []); await p.waitForTimeout(500);
  const sel = await p.evaluate(() => [NOME_COM[terr.com], !document.getElementById('fogliettoMappa').hidden, document.getElementById('fogliettoMappa').innerText.replace(/\s+/g, ' ').slice(0, 90)]);
  ok(sel[0] === 'Udine' && sel[1], `il tocco su un comune lo seleziona e apre il pannello: ${sel[0]} | ${sel[2]}`);
  // 6. pizzico dopo la selezione: il comune resta, nessuna nuova selezione
  await pizzico(cx, cy, 80, 200); const dopo = await p.evaluate(() => NOME_COM[terr.com]); ok(dopo === 'Udine', 'un pizzico sopra un altro comune non cambia la selezione');
  await p.click('.chiudiFoglietto'); await p.waitForTimeout(150);
  // 7. schermo intero: un dito sposta la mappa
  await p.click('#riquadroMappa .schermoIntero'); await p.waitForTimeout(300);
  const fs1 = await p.evaluate(() => { const r = document.getElementById('riquadroMappa').getBoundingClientRect(); return [document.getElementById('riquadroMappa').classList.contains('intera'), Math.round(r.width), Math.round(r.height)]; });
  ok(fs1[0] && fs1[1] === 390, `schermo intero aperto (${fs1[1]}×${fs1[2]})`);
  s0 = await stato('#svgMappa'); await trascina(200, 420, 80, 300); s1 = await stato('#svgMappa');
  ok(Math.abs(s1.x - s0.x) > s0.w * 0.05 && s1.scroll === s0.scroll, `a schermo intero un dito sposta la mappa (x ${Math.round(s0.x)} → ${Math.round(s1.x)}) senza far scorrere la pagina`);
  ok(s1.com === s0.com, 'lo spostamento a schermo intero non seleziona un comune');
  await pizzico(195, 420, 60, 200); s2 = await stato('#svgMappa'); ok(s2.w < s1.w * 0.6, 'a schermo intero il pizzico ingrandisce');
  // 8. cambio di orientamento a schermo intero, poi di nuovo un pizzico
  await p.setViewportSize({ width: 844, height: 390 }); await p.evaluate(() => dispatchEvent(new Event('orientationchange'))); await p.waitForTimeout(400);
  const or = await p.evaluate(() => { const r = document.getElementById('riquadroMappa').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
  s0 = await stato('#svgMappa'); await pizzico(420, 200, 200, 70); s1 = await stato('#svgMappa');
  ok(or[0] === 844 && s1.w > s0.w * 1.8, `dopo la rotazione (${or[0]}×${or[1]}) il pizzico funziona ancora (${Math.round(s0.w)} → ${Math.round(s1.w)})`);
  await p.click('#riquadroMappa .schermoIntero'); await p.waitForTimeout(200);
  ok(await p.evaluate(() => !document.getElementById('riquadroMappa').classList.contains('intera') && !document.body.classList.contains('mappa-intera')), 'schermo intero chiuso con lo stesso pulsante');
  await p.setViewportSize({ width: 390, height: 844 }); await p.waitForTimeout(300);
  // 9. interruzione: un dito resta giù dopo il pizzico, poi si alza; nessuna selezione, nessun blocco
  const prima = await p.evaluate(() => terr.com);
  await p.evaluate(() => document.getElementById('svgMappa').scrollIntoView({ block: 'center' })); await p.waitForTimeout(200);
  const b2 = await p.locator('#svgMappa').boundingBox(), mx = b2.x + b2.width / 2, my = b2.y + b2.height / 2;
  await tocco('touchStart', [[mx - 40, my]]); await tocco('touchStart', [[mx - 40, my], [mx + 40, my]]); await tocco('touchMove', [[mx - 80, my], [mx + 80, my]]);
  await tocco('touchEnd', [[mx - 80, my]]); await p.waitForTimeout(100); await tocco('touchEnd', []); await p.waitForTimeout(300);
  ok(await p.evaluate(() => terr.com) === prima, 'un dito che si alza dopo il pizzico non seleziona nulla');
  await tocco('touchStart', [[mx, my]]); await tocco('touchCancel', []); await p.waitForTimeout(100);
  ok(await p.evaluate(() => gestiMappe[0].stato().punti === 0), 'un tocco annullato dal sistema non lascia gesti aperti');
  // 10. le altre mappe: autobus, aria e allerte rispondono al pizzico
  for (const [pag, sel, attesa] of [['autobus', '#svgTpl', () => TPL], ['ambiente', '#svgAria', () => vistaFissa.aria.vb], ['ambiente', '#svgAllerte', () => vistaFissa.allerte.vb]]) {
    await p.evaluate(x => vaiPagina(x), pag); await p.waitForTimeout(500);
    await p.waitForFunction(attesa, null, { timeout: 30000 }).catch(() => {});
    await p.evaluate(s => document.querySelector(s).scrollIntoView({ block: 'center' }), sel); await p.waitForTimeout(300);
    const bx = await p.locator(sel).boundingBox(); const a = await stato(sel);
    await pizzico(bx.x + bx.width / 2, bx.y + bx.height / 2, 60, 200); const c = await stato(sel);
    ok(c.w < a.w * 0.6 && c.scroll === a.scroll, `${sel}: il pizzico ingrandisce (${Math.round(a.w)} → ${Math.round(c.w)}) senza far scorrere la pagina`);
  }
  // 11. lo zoom del browser resta disponibile fuori dalle mappe
  const vp = await p.evaluate(() => document.querySelector('meta[name=viewport]').content); ok(!/user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b/.test(vp), `il viewport non blocca lo zoom della pagina («${vp}»)`);
  await ctx.close();
  // 12. desktop: rotella e trascinamento con il mouse; un trascinamento non seleziona
  const d = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  if (BASE.includes('atlante.prova')) await d.route('https://atlante.prova/**', r => { let fp = process.env.SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: fp.endsWith('.html') ? 'text/html; charset=utf-8' : 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
  await d.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
  d.on('pageerror', e => errs.push(e + ''));
  await d.goto(BASE + 'index.html?pagina=mappe', { waitUntil: 'networkidle' }); await d.waitForTimeout(1200);
  const db = await d.locator('#svgMappa').boundingBox(); const ex = db.x + db.width / 2, ey = db.y + db.height / 2;
  const w0 = await d.evaluate(() => vb.w); await d.mouse.move(ex, ey); await d.mouse.wheel(0, -300); await d.waitForTimeout(200);
  const w1 = await d.evaluate(() => vb.w); ok(w1 < w0, `rotella del mouse: ingrandisce (${Math.round(w0)} → ${Math.round(w1)})`);
  const x0 = await d.evaluate(() => vb.x); await d.mouse.down(); await d.mouse.move(ex - 150, ey - 40, { steps: 8 }); await d.mouse.up(); await d.waitForTimeout(200);
  const x1 = await d.evaluate(() => vb.x); ok(Math.abs(x1 - x0) > 1 && await d.evaluate(() => terr.com) === -1, 'trascinamento con il mouse: sposta la mappa e non seleziona');
  await d.mouse.click(ex, ey); await d.waitForTimeout(300); ok(await d.evaluate(() => terr.com) >= 0, 'clic semplice: seleziona il comune sotto il puntatore');
  // tastiera: i comandi della mappa si raggiungono e funzionano
  await d.focus('#riquadroMappa [data-z="in"]'); const wk = await d.evaluate(() => vb.w); await d.keyboard.press('Enter'); await d.waitForTimeout(200);
  ok(await d.evaluate(() => vb.w) < wk, 'da tastiera: Invio sul pulsante «+» ingrandisce');
  console.log('ERRORI DELLA PAGINA', errs);
  console.log(fallite ? `${fallite} prove fallite` : 'Tutte le prove dei gesti superate');
  await b.close();
  process.exit(fallite ? 1 : 0);
})();
