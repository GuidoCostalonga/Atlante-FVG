// Prove della sezione riservata «Osservatorio sondaggi» con Chromium (playwright-core).
// Uso: SITE=/percorso/Atlante-FVG ARCHIVIO=/percorso/archivio.cifrato.json PAROLA=… node prove/sondaggi.js
// Controlla: cancello (accesso anonimo negato, parola errata rifiutata), apertura con la parola giusta,
// lettura dell'archivio cifrato, tutte le viste senza errori di pagina, coda esclusa dai grafici,
// separazione Italia / Friuli Venezia Giulia, esportazione CSV, pannello di gestione, resa su telefono.
const fs = require('fs'), path = require('path');
const { chromium } = require(process.env.PWPATH || '/opt/node-tools/node_modules/playwright-core');
const SITE = process.env.SITE || path.resolve(__dirname, '..');
const ARCHIVIO = process.env.ARCHIVIO; const PAROLA = process.env.PAROLA || '';
const CHROMIUM = process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
let falliti = 0, passati = 0;
const ok = (c, m) => { if (c) { passati++; console.log('OK  ', m); } else { falliti++; console.log('FAIL', m); } };
const TIPI = { '.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript', '.json': 'application/json', '.png': 'image/png', '.webp': 'image/webp', '.ico': 'image/x-icon', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.txt': 'text/plain' };
(async () => {
  const b = await chromium.launch({ executablePath: CHROMIUM, args: ['--no-sandbox'] });
  async function pagina(mobile) {
    const ctx = await b.newContext(mobile ? { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 } : { viewport: { width: 1280, height: 900 } });
    const p = await ctx.newPage(); const errori = [];
    p.on('pageerror', e => errori.push(String(e.message))); p.on('console', m => { if (m.type() === 'error' && !/favicon|goatcounter|fonts|net::ERR/.test(m.text())) errori.push(m.text()); });
    await p.route('**/*', async route => {
      const u = new URL(route.request().url());
      if (u.hostname === 'atlante.prova') {
        let f = path.join(SITE, decodeURIComponent(u.pathname)); if (f.endsWith('/')) f += 'index.html';
        if (!fs.existsSync(f)) return route.fulfill({ status: 404, body: 'non trovato' });
        return route.fulfill({ status: 200, contentType: TIPI[path.extname(f)] || 'application/octet-stream', body: fs.readFileSync(f) });
      }
      if (u.hostname === 'raw.githubusercontent.com' && /archivio\.json$/.test(u.pathname)) {
        if (ARCHIVIO && fs.existsSync(ARCHIVIO)) return route.fulfill({ status: 200, contentType: 'application/json', body: fs.readFileSync(ARCHIVIO) });
        return route.fulfill({ status: 404, body: '' });
      }
      if (/gc\.zgo\.at|googleapis|gstatic|github\.com/.test(u.hostname)) return route.fulfill({ status: 200, body: '' });
      return route.fulfill({ status: 404, body: '' });
    });
    return { p, errori, ctx };
  }
  // 1. accesso anonimo: la pagina mostra solo il cancello e il contenuto cifrato non è leggibile
  const { p, errori, ctx } = await pagina(false);
  await p.goto('https://atlante.prova/sondaggi/', { waitUntil: 'load' });
  ok(await p.isVisible('#cancello'), 'cancello visibile senza parola');
  ok(await p.isHidden('#sondaggi'), 'contenuto nascosto senza parola');
  const cont = JSON.parse(fs.readFileSync(path.join(SITE, 'sondaggi/contenuto.json'), 'utf8'));
  ok(cont.v === 1 && cont.d && cont.s && cont.i && !/Osservatorio|rilevazion/i.test(Buffer.from(cont.d, 'base64').toString('latin1')), 'contenuto.json cifrato: nessun testo in chiaro');
  if (ARCHIVIO) { const a = fs.readFileSync(ARCHIVIO, 'utf8'); ok(/"d":/.test(a) && !/rilevazioni|istituto/.test(a), 'archivio cifrato: nessun testo in chiaro'); }
  // 2. parola errata
  await p.fill('#parola', 'sbagliata'); await p.click('#btnApri'); await p.waitForTimeout(1500);
  ok(/non corretta/i.test(await p.textContent('#statoCancello')), 'parola errata rifiutata');
  ok(await p.isHidden('#sondaggi'), 'contenuto ancora nascosto dopo parola errata');
  if (!PAROLA) { console.log('PAROLA assente: salto le prove con la sezione aperta.'); await b.close(); process.exit(falliti ? 1 : 0); }
  // 3. apertura
  await p.fill('#parola', PAROLA); await p.click('#btnApri');
  await p.waitForSelector('#oss', { timeout: 20000 });
  ok(await p.isVisible('#oss'), 'sezione aperta con la parola giusta');
  await p.waitForFunction(() => !document.querySelector('#stato-dati .rotella'), null, { timeout: 20000 });
  const statoDati = await p.textContent('#stato-dati');
  ok(ARCHIVIO ? /rilevazioni/.test(statoDati) : /non ancora pubblicato|non leggibile/.test(statoDati), 'stato dei dati: ' + statoDati.trim().slice(0, 90));
  // 4. viste
  for (const v of ['panoramica', 'italia', 'fvg', 'istituti', 'percezioni', 'archivio', 'gestione']) {
    await p.click(`#schede button[data-vista="${v}"]`); await p.waitForTimeout(400);
    const h = await p.$eval('#vista', e => e.innerText.length);
    ok(h > 50, `vista ${v} resa (${h} caratteri)`);
  }
  if (ARCHIVIO) {
    // 5. coda esclusa dai grafici e separazione dei territori
    const dati = await p.evaluate(async () => {
      const r = await fetch(document.getElementById('oss').dataset.dati); const pk = await r.json();
      const k = window.ATLANTE_SONDAGGI_CHIAVE; const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
      const chiaro = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(pk.i) }, k, b64(pk.d));
      const a = JSON.parse(await new Response(new Blob([chiaro]).stream().pipeThrough(new DecompressionStream('gzip'))).text());
      const R = Object.values(a.rilevazioni);
      return { n: R.length, coda: Object.keys(a.coda).length, daVer: R.filter(x => x.stato === 'da_verificare').map(x => x.id), fvg: R.filter(x => (x.territorio || {}).codice === 'FVG').length, italia: R.filter(x => (x.territorio || {}).tipo === 'Italia').length };
    });
    ok(dati.n > 0, `archivio letto nella pagina: ${dati.n} rilevazioni, ${dati.coda} in coda`);
    await p.click('#schede button[data-vista="archivio"]'); await p.waitForTimeout(300);
    await p.selectOption('#a-stato', 'da_verificare'); await p.waitForTimeout(300);
    const righeCoda = await p.$$eval('#a-tab tbody tr', r => r.length);
    ok(righeCoda === Math.min(50, dati.daVer.length), `archivio filtrato «da verificare»: ${righeCoda} righe`);
    await p.selectOption('#a-stato', ''); await p.selectOption('#a-area', 'fvg'); await p.waitForTimeout(300);
    const righeFvg = await p.$$eval('#a-tab tbody tr', r => r.map(x => x.children[4].textContent));
    ok(righeFvg.every(t => /Friuli|Trieste|Udine|Pordenone|Gorizia/i.test(t)), `filtro Friuli Venezia Giulia: ${righeFvg.length} righe, tutte regionali o locali`);
    await p.selectOption('#a-area', 'italia'); await p.waitForTimeout(300);
    const righeIt = await p.$$eval('#a-tab tbody tr', r => r.map(x => x.children[4].textContent));
    ok(righeIt.every(t => t.trim() === 'Italia'), `filtro Italia: ${righeIt.length} righe, nessuna regionale`);
    // i punti nei grafici non appartengono a rilevazioni in coda
    await p.click('#schede button[data-vista="italia"]'); await p.waitForTimeout(600);
    const puntiCoda = await p.evaluate(ids => { const s = new Set(ids); return [...document.querySelectorAll('#blocco-voto [data-scheda]')].filter(e => s.has(e.dataset.scheda)).length; }, dati.daVer);
    ok(puntiCoda === 0, 'nessuna rilevazione «da verificare» fra quelle collegate dal grafico');
    const haGrafico = await p.$('#blocco-voto svg');
    ok(!!haGrafico || /Nessun/.test(await p.textContent('#blocco-voto')), 'grafico Italia disegnato o stato vuoto informativo');
    // scheda
    const primo = p.locator('#vista .voce [data-scheda]:visible').first();
    if (await primo.count()) { await primo.click(); await p.waitForTimeout(300); ok(await p.isVisible('#scheda'), 'scheda della rilevazione aperta'); ok(/Istituto realizzatore/.test(await p.textContent('#scheda-dentro')), 'scheda con istituto, committente e metodologia'); await p.click('#scheda .chiudi-s'); }
    // esportazione CSV dall'archivio
    await p.click('#schede button[data-vista="archivio"]'); await p.waitForTimeout(300);
    const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 10000 }).catch(() => null), p.click('#a-csv')]);
    ok(dl && /\.csv$/.test(dl.suggestedFilename()), 'esportazione CSV avviata');
    const [dlx] = await Promise.all([p.waitForEvent('download', { timeout: 10000 }).catch(() => null), p.click('#a-xlsx')]);
    ok(dlx && /\.xlsx$/.test(dlx.suggestedFilename()), 'esportazione Excel avviata');
    if (dlx) { const tmp = path.join(require('os').tmpdir(), 'prova.xlsx'); await dlx.saveAs(tmp); const buf = fs.readFileSync(tmp); ok(buf[0] === 0x50 && buf[1] === 0x4b, 'file Excel: archivio ZIP valido'); }
  }
  // 6. gestione senza token: la revisione viene scaricata, non inviata
  await p.click('#schede button[data-vista="gestione"]'); await p.waitForTimeout(300);
  ok(await p.isVisible('#g-token'), 'pannello di gestione con campo del token');
  ok(errori.length === 0, 'nessun errore di pagina (desktop): ' + JSON.stringify(errori.slice(0, 3)));
  await ctx.close();
  // 7. telefono
  const m = await pagina(true);
  await m.p.goto('https://atlante.prova/sondaggi/', { waitUntil: 'load' });
  await m.p.fill('#parola', PAROLA); await m.p.click('#btnApri'); await m.p.waitForSelector('#oss', { timeout: 20000 });
  await m.p.waitForFunction(() => !document.querySelector('#stato-dati .rotella'), null, { timeout: 20000 });
  for (const v of ['italia', 'archivio', 'gestione']) { await m.p.click(`#schede button[data-vista="${v}"]`); await m.p.waitForTimeout(400); }
  const largo = await m.p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  ok(largo, 'telefono: nessuno scorrimento orizzontale della pagina');
  const tocchi = await m.p.$$eval('#oss button, #oss select, #oss input', els => els.filter(e => e.offsetParent && !e.classList.contains('mini')).map(e => e.getBoundingClientRect().height).filter(h => h < 36).length);
  ok(tocchi === 0, `telefono: comandi principali alti almeno 36 px (${tocchi} sotto soglia)`);
  ok(m.errori.length === 0, 'nessun errore di pagina (telefono): ' + JSON.stringify(m.errori.slice(0, 3)));
  await b.close();
  console.log(`\n${passati} prove superate, ${falliti} fallite`);
  process.exit(falliti ? 1 : 0);
})().catch(e => { console.error('ERRORE', e); process.exit(2); });
