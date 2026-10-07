// Prova della pagina Bandi (bandi/index.html). Uso: node prove/bandi.js  (variabili: PWPATH, CHROMIUM, HTTPS_PROXY)
const pw = require(process.env.PWPATH || '/opt/node-tools/node_modules/playwright-core'); const fs = require('fs'), path = require('path');
const SITE = path.resolve(__dirname, '..');
const TIPI = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.ico': 'image/x-icon' };
let fall = 0; const ok = (c, m) => { console.log((c ? 'OK   ' : 'FALLITA ') + m); if (!c) fall++; };
(async () => {
  const opz = { executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] };
  if (process.env.HTTPS_PROXY) opz.proxy = { server: process.env.HTTPS_PROXY };
  const b = await pw.chromium.launch(opz);
  const D = JSON.parse(fs.readFileSync(SITE + '/dati/bandi.json', 'utf8')).voci;
  const oggi = new Date().toISOString().slice(0, 10);
  const scad = v => v.scadenza && v.scadenza < oggi;
  const nReg = D.filter(v => v.sezione === 'regione' && !scad(v)).length;
  async function pagina(w, h, mob, fallisci) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, locale: 'it-IT', acceptDownloads: true });
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
    const p = await ctx.newPage(); p.errs = [];
    await p.route('https://atlante.prova/**', r => { const u = new URL(r.request().url()); if (fallisci && /bandi\.json/.test(u.pathname)) return r.fulfill({ status: 503, body: 'no' }); let fp = SITE + decodeURIComponent(u.pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
    await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort());
    p.on('pageerror', e => p.errs.push(e + '')); return p;
  }
  const n = p => p.locator('#elenco > *').count();
  for (const [w, h, mob] of [[1440, 900, false], [390, 844, true], [360, 740, true]]) {
    console.log('--- ' + w);
    const p = await pagina(w, h, mob);
    await p.goto('https://atlante.prova/bandi/', { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
    ok(await n(p) === nReg, `predefinito: ${await n(p)} voci (attese ${nReg}, senza impiego né scaduti)`);
    ok(await p.locator('#elenco .campi').count() === nReg && /Destinatari/i.test(await p.locator('#elenco').innerText()) && /Requisiti principali/i.test(await p.locator('#elenco').innerText()), 'schede con i campi (destinatari, requisiti, termini)');
    ok(/pagina verificata il/.test(await p.locator('#elenco').innerText()), 'data di ultima verifica');
    ok(/non riportato in forma strutturata/.test(await p.locator('#elenco').innerText()), 'campi assenti dichiarati');
    ok(await p.locator('#elenco .allegati a').count() > 20, 'allegati collegati: ' + await p.locator('#elenco .allegati a').count());
    ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'nessuno scorrimento orizzontale');
    ok(await p.locator('#elenco h2 a[href^="https://www.regione.fvg.it"]').count() > 0, 'collegamenti alla pagina ufficiale');
    ok(await p.locator('#elenco a[target=_blank]').evaluateAll(a => a.every(x => /noopener/.test(x.rel))), 'rel noopener sui collegamenti esterni');
    await p.locator('#impiego').check(); const tutti = D.filter(v => !scad(v)).length;
    ok(await n(p) === tutti, `con impiego: ${await n(p)} (attese ${tutti})`);
    await p.locator('#stato').selectOption('tutti'); ok(await n(p) === D.length, `con scaduti: ${await n(p)} (attese ${D.length})`);
    ok(/scadut/i.test(await p.locator('#elenco').innerText()), 'compare almeno un bando scaduto');
    await p.locator('#stato').selectOption('scaduto'); ok(await n(p) === D.filter(v => scad(v)).length, 'solo scaduti');
    await p.locator('#stato').selectOption('');
    await p.goto('https://atlante.prova/bandi/?contributi=1', { waitUntil: 'networkidle' });
    const nc = D.filter(v => v.contributi && v.sezione === 'regione' && !scad(v)).length;
    ok(await n(p) === nc && await p.locator('#contributi').isChecked(), `solo contributi da indirizzo: ${await n(p)} (attese ${nc})`);
    await p.locator('#contributi').uncheck();
    ok(!/contributi/.test(p.url()), 'indirizzo aggiornato');
    await p.locator('#q').fill('Pordenone'); await p.waitForTimeout(300);
    const att = D.filter(v => v.sezione === 'regione' && !scad(v) && JSON.stringify([v.titolo, v.direzione, v.dettaglio]).toLowerCase().includes('pordenone')).length;
    ok(await n(p) === att, `ricerca nel testo e nei campi: ${await n(p)} (attese ${att})`); ok(/q=Pordenone/.test(p.url()), 'q nell\'indirizzo');
    await p.locator('#cancella').click(); ok(await p.locator('#q').inputValue() === '' && await n(p) === nReg, 'cancella la ricerca');
    await p.locator('.chips button[data-d="comuni"]').click(); await p.waitForTimeout(200);
    const nCom = D.filter(v => v.sezione === 'regione' && !scad(v) && (v.destinatari || []).includes('comuni')).length; ok(await n(p) === nCom && /dest=comuni/.test(p.url()), `destinatari Comuni: ${await n(p)} (attesi ${nCom})`);
    await p.locator('.chips button[data-d="comuni"]').click(); ok(await n(p) === nReg, 'chip si disattiva');
    await p.locator('#tipo').selectOption('atto'); const nAtti = D.filter(v => v.sezione === 'regione' && !scad(v) && v.tipo === 'atto').length; ok(await n(p) === nAtti && nAtti > 0, `atti ed esiti distinti dai bandi: ${nAtti}`); await p.locator('#tipo').selectOption('');
    await p.locator('#settore').selectOption({ index: 1 }); ok(await n(p) > 0 && await n(p) < nReg, 'filtro per settore'); await p.locator('#settore').selectOption('');
    await p.locator('#scad').selectOption('30'); ok(await n(p) === D.filter(v => v.sezione === 'regione' && v.scadenza && v.scadenza >= oggi && (new Date(v.scadenza) - new Date(oggi)) / 864e5 <= 30).length, 'scadenza entro 30 giorni'); await p.locator('#scad').selectOption('');
    // preferiti e calendario
    await p.locator('#elenco .stella:not(.ics)').first().click(); await p.waitForTimeout(200);
    ok(await p.evaluate(() => JSON.parse(localStorage.getItem('atlante-fvg:bandi-preferiti') || '[]').length) === 1 && /\(1\)/.test(await p.locator('#nPref').innerText()), 'preferito salvato sul dispositivo');
    await p.locator('#preferiti').check(); ok(await n(p) === 1 && /preferiti=1/.test(p.url()), 'filtro dei preferiti'); await p.locator('#preferiti').uncheck();
    { const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 15000 }), p.locator('#icsTutti').click()]); const txt = require('fs').readFileSync(await dl.path(), 'utf8'); const nEv = (txt.match(/BEGIN:VEVENT/g) || []).length; ok(dl.suggestedFilename() === 'scadenze-bandi-fvg.ics' && txt.startsWith('BEGIN:VCALENDAR') && nEv === D.filter(v => v.sezione === 'regione' && v.scadenza && !scad(v)).length && /DTSTART;VALUE=DATE:\d{8}/.test(txt), `calendario ICS con ${nEv} scadenze`); }
    { const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 15000 }), p.locator('#elenco .stella.ics').first().click()]); ok(/^scadenza-.*\.ics$/.test(dl.suggestedFilename()), 'ICS del singolo bando: ' + dl.suggestedFilename()); }
    await p.locator('#q').fill('zzzzzqq'); await p.waitForTimeout(300);
    ok(await p.locator('#vuoto').isVisible() && await n(p) === 0, 'stato vuoto'); await p.locator('#azzera').click(); ok(await n(p) === nReg, 'Cancella i filtri');
    await p.locator('#ordine').selectOption('recenti'); const prima = await p.locator('#elenco > *').first().innerText();
    ok(/ordine=recenti/.test(p.url()), 'ordine nell\'indirizzo');
    await p.goBack(); await p.waitForTimeout(300); ok(await p.locator('#ordine').inputValue() === 'scadenza', 'indietro ripristina l\'ordine');
    const sel = await p.locator('#direzione option').count(); ok(sel > 5, `struttura: ${sel} opzioni`);
    await p.locator('#direzione').selectOption({ index: 1 }); ok(await n(p) > 0 && await n(p) < nReg, 'filtro per struttura');
    await p.locator('#copiaLink').click(); await p.waitForTimeout(400);
    const cb = await p.evaluate(() => navigator.clipboard.readText()).catch(() => null); ok(cb ? /bandi\/\?.*direzione=/.test(cb) : true, 'Copia link: ' + (cb ? 'negli appunti' : 'appunti non leggibili in prova'));
    ok(await p.locator('#condividi').isVisible() === false || mob, 'Condividi solo se disponibile');
    const piccoli = await p.evaluate(() => [...document.querySelectorAll('a,button,select,input:not([type=checkbox])')].filter(e => e.offsetParent && matchMedia('(pointer:coarse)').matches).filter(e => { const r = e.getBoundingClientRect(); return r.height < 40 && !e.closest('p,li.n') && getComputedStyle(e).display !== 'inline'; }).map(e => (e.id || e.className || e.tagName) + ':' + Math.round(e.getBoundingClientRect().height) + ':' + e.textContent.trim().slice(0, 20)));
    ok(piccoli.length === 0, 'bersagli del tocco: ' + piccoli.join('|'));
    ok(p.errs.length === 0, 'nessun errore JS ' + p.errs.join(' '));
    if (w !== 360) await p.screenshot({ path: (process.env.S || '/tmp') + `/shotO/bandi-${w}.png`, fullPage: false });
  }
  const q = await pagina(1440, 900, false, true); await q.goto('https://atlante.prova/bandi/', { waitUntil: 'networkidle' }); await q.waitForTimeout(500);
  ok(/non|errore|riprova/i.test(await q.locator('#fonte').innerText() + await q.locator('#esito').innerText() + await q.locator('#vuotoTesto').innerText().catch(() => '') + await q.locator('#elenco').innerText()), 'errore di caricamento gestito');
  await b.close(); console.log(fall ? `\n${fall} FALLITE` : '\nTutte le prove superate'); process.exit(fall ? 1 : 0);
})();
