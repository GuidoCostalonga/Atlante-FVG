// Prova del confronto avanzato: riferimento, scostamenti, medie, scelta degli indicatori, grafici, esportazioni. Uso: node prove/confronto.js
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
    await p.goto('https://atlante.prova/?pagina=confronto&confronta=roveredo-in-piano,porcia,cordenons', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(2500);
    const testa = await p.locator('#cfTesta').innerText();
    ok(/riferimento/i.test(testa) && /Media prov\. di Pordenone/i.test(testa) && /Media FVG/i.test(testa), 'intestazione: riferimento e colonne delle medie');
    const corpo = () => p.locator('#cfCorpo').innerText();
    let t = await corpo();
    ok(/[+−] [\d.,]+ \([+−][\d,]+%\)/.test(t), 'scostamenti assoluti e percentuali');
    ok(/[+−] [\d,]+ punti/.test(t), 'scostamenti in punti per le percentuali');
    ok(/non calc\./.test(t), 'medie non calcolabili segnalate');
    const medFvg = await p.evaluate(() => { const ind = IND_COM.find(x => x.id === 'p25'); return aggregaInd(ind, TUTTI_COM()).v; });
    ok(medFvg === 1193496, 'media FVG dei residenti = somma dei residenti (' + medFvg + ')');
    const dens = await p.evaluate(() => { const ind = IND_COM.find(x => x.id === 'dens'); const a = aggregaInd(ind, TUTTI_COM()); const semplice = TUTTI_COM().map(i => ind.f(i)).filter(v => v).reduce((s, v, _, arr) => s + v / arr.length, 0); return [a.v, semplice]; });
    ok(Math.abs(dens[0] - dens[1]) > 1, `densità regionale dai totali (${dens[0].toFixed(1)}) diversa dalla media semplice (${dens[1].toFixed(1)})`);
    ok(await p.locator('#cfGraficiBox canvas').count() === 12, 'dodici grafici a barre');
    // riferimento diverso
    await p.locator('#cfRif').selectOption({ label: 'Porcia' }); await p.waitForTimeout(500);
    ok(/rif=porcia/.test(p.url()), 'riferimento nell\'indirizzo'); ok(/Media prov\. di Pordenone/i.test(await p.locator('#cfTesta').innerText()), 'media della provincia del riferimento');
    // scelta degli indicatori
    await p.locator('#cfIndSel summary').click(); await p.locator('#cfIndNessuno').click(); await p.waitForTimeout(300);
    ok(await p.locator('#cfCorpo tr').count() === 0 || (await corpo()).trim() === '', 'nessun indicatore: tabella vuota');
    await p.locator('.cfIndChk[value="p25"]').check(); await p.locator('.cfIndChk[value="red24"]').check(); await p.waitForTimeout(400);
    t = await corpo(); ok(/Residenti al 31 dicembre 2025/.test(t) && /Reddito imponibile medio 2024/.test(t) && !/Densità abitativa/.test(t), 'solo gli indicatori scelti');
    ok(/ind=p25%2Cred24|ind=p25,red24/.test(p.url()), 'indicatori nell\'indirizzo'); ok(await p.locator('#cfGraficiBox canvas').count() === 2, 'due grafici');
    // spegnere scostamenti e medie
    await p.locator('#cfScost').uncheck(); await p.locator('#cfMedie').uncheck(); await p.waitForTimeout(300);
    t = await corpo(); ok(!/\([+−][\d,]+%\)/.test(t) && !/Media FVG/i.test(await p.locator('#cfTesta').innerText()), 'senza scostamenti e medie'); ok(/scost=0/.test(p.url()) && /medie=0/.test(p.url()), 'opzioni nell\'indirizzo');
    // ripristino dall'indirizzo
    const u = p.url(); await p.goto(u, { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
    ok(await p.locator('#cfRif').inputValue() === String(await p.evaluate(() => SLUG_COM.indexOf('porcia'))) && !(await p.locator('#cfScost').isChecked()) && (await corpo()).includes('Reddito imponibile medio 2024') && !(await corpo()).includes('Densità'), 'stato ripristinato dall\'indirizzo');
    await p.locator('#cfScost').check(); await p.locator('#cfMedie').check(); await p.waitForTimeout(300);
    // esportazione PNG e Excel (CSV)
    const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 20000 }), p.locator('#btnCfPng').click()]);
    const fp = await dl.path(); ok(/confronto-.*-documento\.png$/.test(dl.suggestedFilename()) && fs.statSync(fp).size > 50000, 'PNG dei grafici scaricato: ' + dl.suggestedFilename() + ' ' + fs.statSync(fp).size + ' byte');
    if (!mob) fs.copyFileSync(fp, (process.env.S || '/tmp') + '/shotO/confronto-export.png');
    const [dl2] = await Promise.all([p.waitForEvent('download', { timeout: 20000 }), p.locator('.scarica[data-t="confronto"][data-f="csv"]').first().click()]);
    const csv = fs.readFileSync(await dl2.path(), 'utf8'); ok(/Media FVG/.test(csv) && /Metodo media fvg/.test(csv) && /Scostamento Roveredo in Piano dal riferimento/.test(csv), 'CSV con medie, metodo e scostamenti');
    // comuni simili con criteri
    await p.locator('#cfCrit summary').click(); ok(await p.locator('.cfCritChk').count() === 4, 'criteri dei comuni simili');
    await p.locator('.cfCritChk[data-k="urb"]').check(); await p.locator('#btnCfVicini').click(); await p.waitForTimeout(600);
    const nota = await p.locator('#cfCritNota').innerText(); ok(/popolazione più vicina/.test(nota) && /stessa provincia/.test(nota) && /urbanizzazione/.test(nota), 'criteri dichiarati: ' + nota.slice(0, 120));
    const scelti = await p.evaluate(() => cfScelti.filter(i => i >= 0).map(i => [NOME_COM[i], PV_COM[i], (X(i).cart || {})['Cart. 1.4']]));
    ok(scelti.length === 6 && scelti.every(s => s[1] === 'PN') && new Set(scelti.map(s => s[2])).size === 1, 'simili: stessa provincia e stesso grado di urbanizzazione: ' + scelti.map(s => s[0]).join(', '));
    await p.locator('.cfCritChk[data-k="urb"]').uncheck();
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'nessuno scorrimento orizzontale della pagina');
    ok(errs.length === 0, 'nessun errore JS ' + errs.join(' | '));
    if (!mob) await p.screenshot({ path: (process.env.S || '/tmp') + `/shotO/confronto-${w}.png`, fullPage: false });
    await ctx.close();
  }
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
