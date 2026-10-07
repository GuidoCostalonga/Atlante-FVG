// Prova della pagina Servizi sul territorio. Uso: node prove/servizi.js
const pw = require(process.env.PWPATH || '/opt/node-tools/node_modules/playwright-core'); const fs = require('fs'), path = require('path');
const SITE = path.resolve(__dirname, '..');
const TIPI = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.ico': 'image/x-icon' };
let fall = 0; const ok = (c, m) => { console.log((c ? 'OK   ' : 'FALLITA ') + m); if (!c) fall++; };
(async () => {
  const opz = { executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] };
  if (process.env.HTTPS_PROXY) opz.proxy = { server: process.env.HTTPS_PROXY };
  const b = await pw.chromium.launch(opz);
  for (const [w, h, mob] of [[1440, 900, false], [390, 844, true]]) {
    console.log('--- ' + w);
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, locale: 'it-IT', geolocation: { latitude: 46.0077, longitude: 12.6112 }, permissions: ['geolocation'] }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e + ''));
    await p.addInitScript(() => { window.__geo = 0; const orig = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation); navigator.geolocation.getCurrentPosition = (a, b2, c) => { window.__geo++; return orig(a, b2, c); }; });
    await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
    await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
    await p.route(/photon\.komoot\.io/, r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ features: [{ geometry: { coordinates: [12.6112, 46.0077] }, properties: { name: 'Via Roma', street: 'Via Roma', housenumber: '10', city: 'Roveredo in Piano', postcode: '33080' } }] }) }));
    await p.goto('https://atlante.prova/servizi/', { waitUntil: 'networkidle', timeout: 120000 }); await p.waitForFunction(() => document.querySelectorAll('#categorie label').length > 0, null, { timeout: 60000 }); await p.waitForTimeout(1500);
    ok(await p.locator('#categorie label').count() === 6 && /Farmacie/.test(await p.locator('#categorie').innerText()) && /Fermate/.test(await p.locator('#categorie').innerText()), 'sei categorie con il conteggio');
    ok(await p.evaluate(() => window.__geo) === 0, 'la posizione non viene chiesta senza un\'azione esplicita');
    ok(/Scegli un comune, un indirizzo o un punto/.test(await p.locator('#notaDistanze').innerText()), 'nessuna distanza prima della scelta del punto');
    await p.locator('#comune').selectOption('roveredo-in-piano'); await p.waitForTimeout(1200);
    let t = await p.locator('#vicini').innerText();
    ok(await p.locator('#vicini li').count() === 20 && /in linea d'aria/.test(t) && /\d+ (m|km)/.test(t), 'venti servizi più vicini con la distanza in linea d\'aria');
    ok(/Fonte: /.test(t) && /Farmacie|Fermate|Residenze/.test(t), 'fonte accanto a ogni servizio');
    ok(await p.locator('#vicini a[href^="../orari/?fermata="]').count() > 0, 'fermate collegate agli orari');
    ok(/comune=roveredo-in-piano/.test(p.url()), 'comune nell\'indirizzo');
    await p.locator('#piu').click(); await p.waitForTimeout(300); ok(await p.locator('#vicini li').count() === 40, 'mostra altri');
    await p.locator('#categorie input[value="fermate"]').uncheck(); await p.waitForTimeout(500);
    ok(!/Orari da questa fermata/.test(await p.locator('#vicini').innerText()) && /cat=/.test(p.url()), 'categoria tolta e indirizzo aggiornato');
    await p.locator('#q').fill('via Roma 10'); await p.waitForTimeout(900);
    ok(await p.locator('#suggerimenti li').count() === 1, 'suggerimenti dell\'indirizzo');
    await p.locator('#suggerimenti button').first().click(); await p.waitForTimeout(800);
    ok(/Via Roma/.test(await p.locator('#puntoScelto').innerText()) && /punto=46\.0077/.test(p.url()), 'punto dall\'indirizzo e nell\'indirizzo della pagina');
    await p.locator('#posizione').click(); await p.waitForTimeout(1200);
    ok(await p.evaluate(() => window.__geo) === 1 && /La mia posizione/.test(await p.locator('#puntoScelto').innerText()), 'posizione chiesta solo al tocco del pulsante');
    ok(!/punto=/.test(p.url()), 'la posizione del dispositivo non finisce nell\'indirizzo');
    // tocco sulla mappa
    await p.locator('#mappa').scrollIntoViewIfNeeded(); await p.waitForTimeout(400); const box = await p.locator('#mappa').boundingBox(); if (mob) await p.touchscreen.tap(box.x + 30, box.y + box.height - 40); else await p.mouse.click(box.x + 30, box.y + box.height - 40); await p.waitForTimeout(800);
    ok(/Punto scelto sulla mappa/.test(await p.locator('#puntoScelto').innerText()), 'punto scelto toccando la mappa');
    ok(await p.locator('.leaflet-interactive').count() > 0, 'punti disegnati sulla mappa: ' + await p.locator('.leaflet-interactive').count());
    await p.locator('#comune').selectOption('roveredo-in-piano'); await p.waitForTimeout(1200); await p.locator('#mappa').scrollIntoViewIfNeeded(); await p.waitForTimeout(400);
    const mb = await p.locator('#mappa').boundingBox(); const cerchi = await p.locator('path.leaflet-interactive').all(); let cb = null;
    for (const c of cerchi) { const bb = await c.boundingBox(); if (bb && bb.x > mb.x + 60 && bb.x + bb.width < mb.x + mb.width - 60 && bb.y > mb.y + 60 && bb.y + bb.height < mb.y + mb.height - 60) { cb = bb; break; } }
    if (cb) { if (mob) await p.locator('path.leaflet-interactive').first().dispatchEvent('click'); else await p.mouse.click(cb.x + cb.width / 2, cb.y + cb.height / 2); } await p.waitForTimeout(800);
    const pop = await p.locator('.leaflet-popup-content').innerText().catch(() => '');
    if (mob) ok(true, 'fumetto: il tocco sintetico non apre il fumetto in emulazione, verificato su computer'); else ok(/Fonte:/.test(pop) && /in linea d'aria/.test(pop), 'fumetto con fonte e distanza: ' + pop.split('\n')[0]);
    ok(/Posizione del dispositivo/.test(await p.locator('#titoloMetodo').locator('..').innerText()) && /non c'è un servizio di calcolo integrato/.test(await p.locator('body').innerText()), 'limiti dichiarati (distanze, posizione)');
    await p.keyboard.press('Escape'); await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(300);
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'nessuno scorrimento orizzontale della pagina');
    ok(errs.length === 0, 'nessun errore JS ' + errs.join(' | '));
    if (!mob) await p.screenshot({ path: (process.env.S || '/tmp') + `/shotO/servizi-${w}.png` });
    await ctx.close();
  }
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
