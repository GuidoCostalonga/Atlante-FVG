// Prova della pagina «Cosa è cambiato». Uso: node prove/aggiornamenti.js
const pw = require(process.env.PWPATH || '/opt/node-tools/node_modules/playwright-core'); const fs = require('fs'), path = require('path');
const SITE = path.resolve(__dirname, '..');
const TIPI = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.ico': 'image/x-icon' };
let fall = 0; const ok = (c, m) => { console.log((c ? 'OK   ' : 'FALLITA ') + m); if (!c) fall++; };
(async () => {
  const opz = { executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] };
  if (process.env.HTTPS_PROXY) opz.proxy = { server: process.env.HTTPS_PROXY };
  const b = await pw.chromium.launch(opz);
  const D = JSON.parse(fs.readFileSync(SITE + '/dati/aggiornamenti.json', 'utf8'));
  for (const [w, h, mob] of [[1440, 900, false], [390, 844, true]]) {
    console.log('--- ' + w);
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, locale: 'it-IT' }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e + ''));
    await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
    await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
    await p.goto('https://atlante.prova/aggiornamenti/', { waitUntil: 'networkidle' }); await p.waitForTimeout(600);
    const n = () => p.locator('#elenco > li').count();
    ok(await n() === D.voci.length, `tutte le voci: ${await n()} (attese ${D.voci.length})`);
    ok(/prima versione pubblicata, il 6 ottobre 2026/.test(await p.locator('#fonte').innerText()), 'data della prima versione dichiarata');
    const t = await p.locator('#elenco').innerText();
    ok(/7\.855/.test(t) && /7\.966/.test(t) && /\+111/.test(t) && /−31/.test(t), 'valori prima, dopo e differenza della rete degli autobus');
    ok(/Nuovi dati/.test(t) && /Correzione/.test(t) && /Funzione nuova/.test(t), 'tipi distinti');
    await p.locator('.tipi button[data-t="funzione"]').click(); await p.waitForTimeout(200);
    const nFun = D.voci.filter(v => v.tipo !== 'funzione').length; ok(await n() === nFun && /tipo=dati%2Ccorrezione%2Cmetodo|tipo=dati,correzione,metodo/.test(p.url()), `senza le funzioni: ${await n()} (attese ${nFun}), tipi nell'indirizzo`);
    await p.locator('#origine').selectOption('auto'); await p.waitForTimeout(200);
    const nAuto = D.voci.filter(v => v.tipo !== 'funzione' && v.automatico).length; ok(await n() === nAuto, `solo automatici: ${await n()} (attese ${nAuto})`);
    await p.locator('#azzeraTutto').click(); await p.waitForTimeout(200); ok(await n() === D.voci.length, 'filtri azzerati');
    await p.locator('#q').fill('bandi'); await p.waitForTimeout(200); ok(await n() > 0 && await n() < D.voci.length && /q=bandi/.test(p.url()), 'ricerca nel testo');
    await p.locator('#cancella').click();
    const opts = await p.locator('#dataset option').count(); ok(opts > 5, `dati o servizi nel filtro: ${opts}`);
    ok(await p.locator('#fogli tr').count() === D.fogli.length && /non è la data dei dati/.test(await p.locator('body').innerText()), `tabella delle consultazioni: ${await p.locator('#fogli tr').count()} fogli`);
    ok(await p.locator('#elenco a[href^="../?pagina="], #elenco a[href^="../bandi/"], #elenco a[href^="../orari/"]').count() > 10, 'collegamenti alle sezioni');
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'nessuno scorrimento orizzontale');
    ok(errs.length === 0, 'nessun errore JS ' + errs.join(' | '));
    if (!mob) await p.screenshot({ path: (process.env.S || '/tmp') + `/shotO/aggiornamenti-${w}.png` });
    await ctx.close();
  }
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
