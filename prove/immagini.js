// Prova delle esportazioni di immagini: mappa in PNG e SVG, grafici della scheda in PNG. Uso: node prove/immagini.js
const pw = require(process.env.PWPATH || '/opt/node-tools/node_modules/playwright-core'); const fs = require('fs'), path = require('path');
const SITE = path.resolve(__dirname, '..');
const TIPI = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.ico': 'image/x-icon' };
let fall = 0; const ok = (c, m) => { console.log((c ? 'OK   ' : 'FALLITA ') + m); if (!c) fall++; };
(async () => {
  const opz = { executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] };
  if (process.env.HTTPS_PROXY) opz.proxy = { server: process.env.HTTPS_PROXY };
  const b = await pw.chromium.launch(opz); const out = (process.env.S || '/tmp') + '/shotO';
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: 'it-IT', acceptDownloads: true }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e + ''));
  await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
  await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
  await p.goto('https://atlante.prova/?pagina=mappe&indicatore=red24&comune=roveredo-in-piano', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(2500);
  const scarica = async (sel) => { const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 30000 }), p.locator(sel).click()]); return [dl.suggestedFilename(), await dl.path()]; };
  let [nome, fp] = await scarica('#btnMappaSvg');
  const svg = fs.readFileSync(fp, 'utf8');
  ok(/^mappa-.*\.svg$/.test(nome) && svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg"'), 'SVG della mappa: ' + nome);
  ok(/<title>Reddito imponibile medio 2024<\/title>/.test(svg) && /LEGENDA/.test(svg) && /Fonte:/.test(svg) && /Atlante FVG · atlantefvg.it/.test(svg) && /anno d&#39;imposta 2024|anno d'imposta 2024/.test(svg), 'SVG con titolo, legenda, fonte, periodo e marchio');
  ok((svg.match(/<path class="unita"/g) || []).length === 215 && !/zoomMappa|<button/.test(svg), 'SVG con i 215 comuni e senza comandi dell\'interfaccia');
  ok(/<image href="data:image\/webp/.test(svg), 'logo incorporato nello SVG');
  fs.writeFileSync(out + '/mappa-export.svg', svg);
  for (const f of ['documento', 'presentazione', 'social']) {
    await p.locator('#mappaPngFormato').selectOption(f); [nome, fp] = await scarica('#btnMappaPng');
    const dim = fs.statSync(fp).size; ok(nome.endsWith(`-${f}.png`) && dim > 80000, `PNG della mappa ${f}: ${nome} ${dim} byte`);
    fs.copyFileSync(fp, `${out}/mappa-export-${f}.png`);
  }
  // confronto fra due anni: nome con gli anni
  await p.goto('https://atlante.prova/?pagina=mappe&indicatore=popVar&anno=2026&anno2=2010', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(2000);
  [nome] = await scarica('#btnMappaSvg'); ok(/-2010-2026\.svg$/.test(nome), 'nome con i due anni: ' + nome);
  // grafici della scheda
  await p.goto('https://atlante.prova/?comune=roveredo-in-piano', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(3000);
  ok(await p.locator('.scaricaGrafico').count() >= 4, 'pulsanti di scarico sui grafici: ' + await p.locator('.scaricaGrafico').count());
  [nome, fp] = await scarica('.scaricaGrafico[data-c="gSerieCom"]');
  ok(/^grafico-residenti-dal-2002-al-2026-roveredo-in-piano-documento\.png$/.test(nome) && fs.statSync(fp).size > 40000, 'PNG del grafico dei residenti: ' + nome);
  fs.copyFileSync(fp, out + '/grafico-export.png');
  ok(errs.length === 0, 'nessun errore JS ' + errs.join(' | '));
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
