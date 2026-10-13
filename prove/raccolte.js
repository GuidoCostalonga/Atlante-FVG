// Prova dei fogli delle raccolte di ottobre 2026 (scripts/importa_raccolte.py). Uso: node prove/raccolte.js
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
  for (const [foglio, comune, atteso, nome] of [
    ['NIDI_STRUTTURE', 'aquileia', /OLIVIA PAPERINA/i, /Nidi e servizi per la prima infanzia/],
    ['ETA_2025', 'aiello-del-friuli', /Aiello del Friuli/, /Popolazione per età al 1° gennaio 2025/],
    ['OMI_QUOTAZIONI', 'andreis', /Abitazioni civili/, /Valori immobiliari: quotazioni/],
    ['APP_PROCEDURE', 'san-giovanni-al-natisone', /COMUNE DI SAN GIOVANNI AL NATISONE/, /Appalti: procedure/],
    ['SIOPE_BI_SPESE_2025', 'grado', /COMUNE DI GRADO/, /pagamenti mensili dei comuni 2025/],
    ['BD24_S01', 'dignano', /COMUNE DI DIGNANO/, /Rendiconto 2024/],
    ['AMBULATORI', 'zoppola', /ZOPPOLA/, /Ambulatori dei medici/]]) {
    await p.goto(`https://atlante.prova/?pagina=archivio&foglio=${foglio}&comune=${comune}`, { waitUntil: 'networkidle', timeout: 120000 }); await p.waitForTimeout(3000);
    const t = await p.locator('body').innerText();
    ok(atteso.test(t), `${foglio} per ${comune}: righe del comune visibili`);
    ok(nome.test(t), `${foglio}: nome leggibile mostrato`);
    ok(!/NaN|undefined/.test(t), `${foglio}: nessun NaN o undefined`);
    ok(!/\btelefono\b|E-mail/i.test(await p.locator('#aTesta').innerText()), `${foglio}: nessuna colonna di contatti`);
  }
  const elenco = await p.locator('#elencoFogli').innerText();
  ok(/Rendiconti dei comuni 2018 \(OpenBDAP\)/i.test(elenco) && /Incassi e pagamenti dei comuni \(SIOPE\)/i.test(elenco), 'nuovi ambiti nell\'elenco dei fogli');
  ok(errs.length === 0, 'nessun errore JS ' + errs.join(' '));
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
