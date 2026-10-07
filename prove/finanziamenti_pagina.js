// Prova dell'archivio dei finanziamenti regionali. Uso: node prove/finanziamenti_pagina.js
const pw = require(process.env.PWPATH || '/opt/node-tools/node_modules/playwright-core'); const fs = require('fs'), path = require('path');
const SITE = path.resolve(__dirname, '..');
const TIPI = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.ico': 'image/x-icon' };
let fall = 0; const ok = (c, m) => { console.log((c ? 'OK   ' : 'FALLITA ') + m); if (!c) fall++; };
(async () => {
  const opz = { executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] };
  if (process.env.HTTPS_PROXY) opz.proxy = { server: process.env.HTTPS_PROXY };
  const b = await pw.chromium.launch(opz); const IDX = JSON.parse(fs.readFileSync(SITE + '/dati/finanziamenti_indice.json', 'utf8'));
  for (const [w, h, mob] of [[1440, 900, false], [390, 844, true]]) {
    console.log('--- ' + w);
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, locale: 'it-IT', acceptDownloads: true }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e + ''));
    await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
    await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
    await p.goto('https://atlante.prova/finanziamenti/', { waitUntil: 'networkidle', timeout: 120000 }); await p.waitForFunction(() => document.querySelectorAll('#risultati li').length > 0, null, { timeout: 90000 });
    const n = () => p.locator('#risultati li').count();
    ok(await n() === 50 && /righe/.test(await p.locator('#esito').innerText()), 'prima pagina di 50 righe: ' + await p.locator('#esito').innerText());
    const tot = await p.locator('#totali').innerText(); ok(/atti distinti/.test(tot) && /importi concessi/.test(tot) && /importi erogati/.test(tot), 'totali separati per tipo di importo');
    ok(/sommano solo importi dello stesso tipo/.test(await p.locator('#criterio').innerText()), 'criterio di conteggio dichiarato');
    const t = await p.locator('#risultati').innerText();
    ok(/Territorio:/.test(t) && /\((ente concedente|CUP localizzato|comune nominato|l'atto non indica)/.test(t), 'territorio con criterio accanto');
    ok(/persona fisica \(nome non ripubblicato\)|Persone fisiche/.test(t) || !/persona fisica/.test(t), 'persone fisiche senza nome');
    ok(await p.locator('#risultati a[href*="ricerca.html?numeroAtto="]').count() > 0, 'collegamenti al portale per numero e anno dell\'atto');
    await p.locator('#benef').selectOption('persona fisica'); await p.waitForTimeout(400);
    const tf = await p.locator('#risultati').innerText(); ok(!/[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]/.test(tf) && (await n() === 0 || /nome non ripubblicato/.test(tf)), 'nessun codice fiscale di persone fisiche');
    await p.locator('#benef').selectOption('');
    await p.locator('#vista').selectOption('ente'); await p.waitForTimeout(400); ok(await p.locator('#risultati table tr').count() > 3 && /vista=ente/.test(p.url()), 'raggruppamento per ente');
    await p.locator('#vista').selectOption('comune'); await p.waitForTimeout(400); ok(/Ambito regionale o non indicato/.test(await p.locator('#risultati').innerText()), 'ambito non indicato distinto dai comuni');
    await p.locator('#vista').selectOption('atti');
    const primoEnte = await p.locator('#ente option').nth(1).getAttribute('value'); await p.locator('#ente').selectOption(primoEnte); await p.waitForTimeout(400);
    ok((await p.locator('#risultati').innerText()).toLowerCase().includes(primoEnte.toLowerCase().slice(0, 12)) && /ente=/.test(p.url()), 'filtro per ente: ' + primoEnte.slice(0, 40));
    await p.locator('#ente').selectOption('');
    await p.locator('#q').fill('pro loco'); await p.waitForTimeout(400); ok(await n() > 0 && /pro loco/i.test(await p.locator('#risultati').innerText()), 'ricerca per beneficiario');
    const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 20000 }), p.locator('#scaricaCsv').click()]); ok(dl.suggestedFilename() === 'finanziamenti-fvg.csv', 'CSV scaricato');
    ok(/Controlli dell'ultima lettura/.test(await p.locator('#controlli').innerText()), 'controlli e registro degli errori mostrati');
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'nessuno scorrimento orizzontale');
    ok(errs.length === 0, 'nessun errore JS ' + errs.join(' | '));
    if (!mob) await p.screenshot({ path: (process.env.S || '/tmp') + `/shotO/finanziamenti-${w}.png` });
    await ctx.close();
  }
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
