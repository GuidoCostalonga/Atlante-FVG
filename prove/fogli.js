// Prova dei fogli aggiunti l'8 ottobre 2026 (radon, parchi e giardini, rifugi alpini). Uso: node prove/fogli.js
const pw = require(process.env.PWPATH || '/opt/node-tools/node_modules/playwright-core'); const fs = require('fs'), path = require('path');
const SITE = path.resolve(__dirname, '..');
const TIPI = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.ico': 'image/x-icon' };
let fall = 0; const ok = (c, m) => { console.log((c ? 'OK   ' : 'FALLITA ') + m); if (!c) fall++; };
(async () => {
  const opz = { executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] };
  if (process.env.HTTPS_PROXY) opz.proxy = { server: process.env.HTTPS_PROXY };
  const b = await pw.chromium.launch(opz);
  const p = await (await b.newContext({ viewport: { width: 1300, height: 900 }, locale: 'it-IT' })).newPage(); const errs = []; p.on('pageerror', e => errs.push(e + ''));
  await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
  await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
  for (const [foglio, comune, atteso] of [['Radon_scuole_ARPA', 'cordenons', /Valori nella norma|superamenti/], ['Parchi_e_giardini', 'codroipo', /Villa Kechler/], ['Rifugi_alpini', 'staranzano', /ISOLA DELLA CONA/i]]) {
    await p.goto(`https://atlante.prova/?pagina=archivio&foglio=${foglio}&comune=${comune}`, { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(2500);
    const t = await p.locator('body').innerText();
    ok(atteso.test(t), `${foglio} per ${comune}: righe del comune visibili`);
    ok(!/NaN|undefined/.test(t), `${foglio}: nessun NaN o undefined`);
  }
  ok(errs.length === 0, 'nessun errore JS ' + errs.join(' '));
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
