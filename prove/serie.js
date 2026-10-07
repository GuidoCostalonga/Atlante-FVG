// Prova delle serie storiche: intervallo e variazione nella scheda, anno e confronto fra due anni nelle mappe. Uso: node prove/serie.js
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
    // scheda: intervallo e variazione
    await p.goto('https://atlante.prova/?comune=rivignano-teor', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(3000);
    let v = await p.locator('#serieVar').innerText();
    ok(/Dal 2002 al 2026: [+−] [\d.]+ residenti \([+−][\d,]+%\)/.test(v), 'variazione sull\'intero periodo: ' + v);
    ok(/fusione di Rivignano e Teor/.test(await p.locator('#mCorpo').innerText()), 'nota sulla fusione e sulla serie ricostruita');
    await p.locator('#serieDa').selectOption('2015'); await p.waitForTimeout(600);
    v = await p.locator('#serieVar').innerText(); ok(/^Dal 2015 al 2026/.test(v), 'intervallo cambiato: ' + v);
    const att = await p.evaluate(() => { const i = SLUG_COM.indexOf('rivignano-teor'), s = X(i).serie, k = ANNI_SERIE.indexOf('2015'); return s[s.length - 1] - s[k]; });
    ok(v.replace(/\./g, '').includes(String(Math.abs(att))), 'variazione assoluta coerente con i dati (' + att + ')');
    ok((await p.locator('#gSerieCom').getAttribute('aria-label')).startsWith('Residenti di Rivignano Teor: 2015'), 'testo alternativo sull\'intervallo');
    ok(/Spesa corrente per abitante dal 2018 al 2023/.test(await p.locator('#bilVar').innerText().catch(() => '')), 'variazione dei conti negli anni');
    await p.locator('#btnChiudiX').click();
    // mappe: anno scelto e soglie fisse
    await p.goto('https://atlante.prova/?pagina=mappe&indicatore=popAnno&anno=2010&anno2=2026', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(2500);
    ok(!(await p.locator('#mappaTempo').isHidden()), 'comandi del tempo visibili');
    ok(await p.locator('#selAnnoA').inputValue() === '2010' && await p.locator('#selAnnoB').inputValue() === '2026', 'anni dall\'indirizzo');
    ok(/Residenti al 1° gennaio 2010/.test(await p.locator('#legTitolo').innerText()), 'titolo della legenda con l\'anno');
    const leg1 = await p.locator('#legenda').innerText(); ok(/soglie|legenda resta uguale/.test(await p.locator('#notaMappa').innerText()) || /2010 e del 2026/.test(await p.locator('#notaMappa').innerText()), 'nota sulle soglie fisse');
    await p.locator('#scambiaAnni').click(); await p.waitForTimeout(800);
    ok(/Residenti al 1° gennaio 2026/.test(await p.locator('#legTitolo').innerText()), 'scambio degli anni');
    ok((await p.locator('#legenda').innerText()) === leg1, 'legenda identica fra i due anni (stesse soglie)');
    ok(/anno=2026/.test(p.url()) && /anno2=2010/.test(p.url()), 'anni nell\'indirizzo');
    await p.locator('#soglieFisse').uncheck(); await p.waitForTimeout(600);
    ok((await p.locator('#legenda').innerText()) !== leg1 && /soglie=libere/.test(p.url()), 'soglie libere cambiano la legenda');
    await p.locator('#vaiVariazione').click(); await p.waitForTimeout(800);
    ok(/Variazione dei residenti dal 2010 al 2026/.test(await p.locator('#legTitolo').innerText()), 'mappa della variazione fra i due anni');
    const cl = await p.locator('#classifica').innerText(); ok(/[+−]?\d+,\d%/.test(cl) || /%/.test(cl), 'classifica della variazione in percentuale');
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'nessuno scorrimento orizzontale');
    ok(errs.length === 0, 'nessun errore JS ' + errs.join(' | '));
    if (!mob) await p.screenshot({ path: (process.env.S || '/tmp') + `/shotO/serie-mappa-${w}.png` });
    await ctx.close();
  }
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
