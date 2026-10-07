// Prova dei finanziamenti delle opere: scheda del comune, indicatori, confronto. Uso: node prove/finanziamenti.js
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
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, locale: 'it-IT' }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e + ''));
    await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
    await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
    await p.goto('https://atlante.prova/?comune=roveredo-in-piano', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(1500);
    const t = await p.locator('body').innerText();
    ok(/Chi compare fra le fonti di copertura/.test(t), 'blocco nella scheda del comune');
    const m = /([\d,]+)%\s*del costo: con la Regione/.exec(t.replace(/\n/g, ' ')); ok(!!m, 'quota regionale visibile: ' + (m && m[1]));
    ok(/non si sommano a cento/.test(t), 'avvertenza sulle quote');
    ok(!/NaN|undefined/.test(t), 'nessun NaN o undefined');
    await p.goto('https://atlante.prova/?pagina=confronto&confronta=roveredo-in-piano,pordenone,udine', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(1500);
    const c = (await p.locator('body').innerText());
    ok(/con la Regione fra le fonti/.test(c), 'riga nel confronto');
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'nessuno scorrimento orizzontale');
    await p.goto('https://atlante.prova/?pagina=mappe&indicatore=finReg', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(2000);
    ok(/Regione fra le fonti/.test(await p.locator('body').innerText()), 'indicatore sulle mappe');
    ok(errs.length === 0, 'nessun errore JS ' + errs.join(' '));
  }
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
