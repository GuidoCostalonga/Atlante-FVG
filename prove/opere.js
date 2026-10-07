// Prova dell'osservatorio delle opere pubbliche. Uso: node prove/opere.js
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
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, locale: 'it-IT', acceptDownloads: true }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e + ''));
    await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
    await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
    await p.goto('https://atlante.prova/opere/?comune=roveredo-in-piano', { waitUntil: 'networkidle', timeout: 120000 }); await p.waitForFunction(() => document.querySelectorAll('#elenco li').length > 0, null, { timeout: 60000 });
    const n = () => p.locator('#elenco li').count();
    const nOp = await p.evaluate(() => filtra().length).catch(() => null);
    ok(await n() > 0 && /opere/.test(await p.locator('#esito').innerText()), 'opere del comune elencate: ' + await p.locator('#esito').innerText());
    ok(/una per CUP/.test(await p.locator('#totali').innerText()) && /non sommate/.test(await p.locator('#totali').innerText()), 'totali con il criterio di conteggio');
    const cup = await p.locator('#elenco li h2 a').first().getAttribute('href');
    await p.locator('#elenco li h2 a').first().click(); await p.waitForTimeout(500);
    const t = await p.locator('#dettaglio').innerText();
    ok(/CUP [A-Z0-9]{15}/.test(t) && /Ente responsabile/i.test(t) && /Costo previsto/i.test(t) && /Fonti di copertura/i.test(t) && /Stato documentato/i.test(t) && /Date documentate/i.test(t) && /Ultimo aggiornamento/i.test(t), 'scheda con tutti i campi previsti');
    ok(/non dice se i lavori|non che i lavori siano in corso/.test(t) && /non sono nella fonte/.test(t), 'avvertenze su stato e date');
    ok(/cup=/.test(p.url()), 'indirizzo della scheda: ' + p.url().split('?')[1]);
    await p.goto(p.url(), { waitUntil: 'networkidle', timeout: 120000 }); await p.waitForFunction(() => !document.getElementById('dettaglio').hidden, null, { timeout: 60000 });
    ok(/CUP/.test(await p.locator('#dettaglio').innerText()), 'scheda riaperta dall\'indirizzo');
    await p.locator('#dettaglio a[href="./"]').click(); await p.waitForTimeout(400); ok(!(await p.locator('#ricerca').isHidden()), 'ritorno alla ricerca');
    await p.locator('#comune').selectOption(''); await p.locator('#q').fill('ciclabile'); await p.waitForTimeout(400);
    ok(await n() > 0 && /q=ciclabile/.test(p.url()), 'ricerca per descrizione');
    await p.locator('#solo').check(); await p.waitForTimeout(300); ok(/solo=1/.test(p.url()), 'solo opere in un comune');
    const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 20000 }), p.locator('#scaricaCsv').click()]); ok(dl.suggestedFilename() === 'opere-pubbliche-fvg.csv', 'CSV scaricato');
    await p.goto('https://atlante.prova/opere/?cup=XXXXXXXXXXXXXXX', { waitUntil: 'networkidle', timeout: 120000 }); await p.waitForFunction(() => !document.getElementById('dettaglio').hidden, null, { timeout: 60000 });
    ok(/non trovato/.test(await p.locator('#dettaglio').innerText()), 'CUP inesistente gestito');
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'nessuno scorrimento orizzontale');
    ok(errs.length === 0, 'nessun errore JS ' + errs.join(' | '));
    if (!mob) { await p.goto('https://atlante.prova/opere/?comune=roveredo-in-piano', { waitUntil: 'networkidle', timeout: 120000 }); await p.waitForFunction(() => document.querySelectorAll('#elenco li').length > 0, null, { timeout: 60000 }); await p.screenshot({ path: (process.env.S || '/tmp') + `/shotO/opere-${w}.png` }); }
    await ctx.close();
  }
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
