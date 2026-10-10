// Per ogni stato dell'atto, raccoglie le righe (data e titolo) della ricerca: serve a conoscere lo stato di ogni mozione
const pw = require(process.env.PWPATH || 'playwright-core'); const fs = require('fs');
const TIPO = process.argv[2] || 'Mozione', OUT = process.argv[3] || 'stati_mozioni.json', LOG = OUT + '.log';
const log = s => fs.appendFileSync(LOG, new Date().toISOString().slice(11, 19) + ' ' + s + '\n');
(async () => {
  const b = await pw.chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined, args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] });
  const p = await (await b.newContext({ locale: 'it-IT' })).newPage(); p.setDefaultTimeout(60000);
  const out = {};
  for (const stato of ['Presentato in attesa di esame', 'Esaminato e approvato', 'Esaminato e non approvato', 'Ritirato']) {
    await p.goto('https://www.consiglio.regione.fvg.it/pagineinterne/Portale/Attivita/AttiIndirizzoRicerca.aspx', { waitUntil: 'networkidle', timeout: 90000 });
    await p.selectOption('#ContentPlaceHolder1_DD_legislatura', { label: 'Legislatura XIII' }); await p.selectOption('#ContentPlaceHolder1_DD_tipoatto', { label: TIPO });
    const ok = await p.selectOption('#ContentPlaceHolder1_DD_stato_atto', { label: stato }).catch(e => { log('stato non selezionabile ' + stato + ' ' + e.message); return null; }); if (!ok) continue;
    await Promise.all([p.waitForNavigation({ waitUntil: 'networkidle', timeout: 120000 }).catch(() => {}), p.click('#ContentPlaceHolder1_btnAtti')]); await p.waitForTimeout(1200);
    const info = await p.locator('#elencoSchede_info').innerText().catch(() => ''); log(stato + ': ' + info);
    out[stato] = []; let pagina = 1;
    while (true) {
      const righe = await p.evaluate(() => [...document.querySelectorAll('#elencoSchede tbody tr')].map(tr => ({ data: tr.children[0]?.innerText.trim(), testo: tr.children[1]?.innerText.trim() })));
      out[stato].push(...righe.filter(r => r.testo));
      const next = p.locator('#elencoSchede_next'); if (await next.count() === 0 || /disabled/.test(await next.getAttribute('class') || '')) break;
      await next.locator('a').click(); await p.waitForTimeout(1200); pagina++; if (pagina > 300) break;
    }
    log(stato + ': raccolte ' + out[stato].length); fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  }
  log('fine'); await b.close();
})().catch(e => { log('FATALE ' + e); process.exit(1); });
