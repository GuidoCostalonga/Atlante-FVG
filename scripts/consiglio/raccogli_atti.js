// Raccoglie gli indirizzi di dettaglio degli atti di indirizzo della XIII legislatura (tipo passato come argomento)
const pw = require(process.env.PWPATH || 'playwright-core'); const fs = require('fs');
const TIPO = process.argv[2] || 'Mozione', OUT = process.argv[3] || 'id_mozioni.json', LOG = OUT + '.log';
const log = s => fs.appendFileSync(LOG, new Date().toISOString().slice(11, 19) + ' ' + s + '\n');
(async () => {
  const b = await pw.chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined, args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] });
  const p = await (await b.newContext({ locale: 'it-IT' })).newPage(); p.setDefaultTimeout(60000);
  await p.goto('https://www.consiglio.regione.fvg.it/pagineinterne/Portale/Attivita/AttiIndirizzoRicerca.aspx', { waitUntil: 'networkidle', timeout: 90000 });
  await p.selectOption('#ContentPlaceHolder1_DD_legislatura', { label: 'Legislatura XIII' }); await p.selectOption('#ContentPlaceHolder1_DD_tipoatto', { label: TIPO });
  await Promise.all([p.waitForNavigation({ waitUntil: 'networkidle', timeout: 120000 }).catch(() => {}), p.click('#ContentPlaceHolder1_btnAtti')]); await p.waitForTimeout(1200);
  log('lista aperta ' + p.url());
  const trovati = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT)) : {}; let pagina = 1;
  while (true) {
    const righe = await p.evaluate(() => [...document.querySelectorAll('#elencoSchede tbody tr')].map(tr => ({ data: tr.children[0]?.innerText.trim(), testo: tr.children[1]?.innerText.trim(), target: (tr.querySelector('a[id*=attiIndirizzoDettaglio]')?.getAttribute('href') || '').match(/__doPostBack\('([^']+)'/)?.[1] })));
    log(`pagina ${pagina}: ${righe.length} righe`);
    for (const r of righe) {
      if (!r.target) continue;
      if (Object.values(trovati).some(v => v.testo === r.testo && v.data === r.data)) continue;
      try {
        const url = await p.evaluate(async t => { const f = document.getElementById('form1'); const fd = new FormData(f); fd.set('__EVENTTARGET', t); fd.set('__EVENTARGUMENT', ''); const ac = new AbortController(); setTimeout(() => ac.abort(), 45000); const r = await fetch(f.action || location.href, { method: 'POST', body: new URLSearchParams(fd), redirect: 'follow', signal: ac.signal }); await r.text(); return r.url; }, r.target);
        if (/Dettaglio\.aspx\?ID=/.test(url)) trovati[url] = { data: r.data, testo: r.testo }; else log('senza dettaglio: ' + (r.testo || '').slice(0, 50) + ' -> ' + url.slice(0, 90));
      } catch (e) { log('errore ' + (r.testo || '').slice(0, 40) + ': ' + String(e).slice(0, 80)); }
      fs.writeFileSync(OUT, JSON.stringify(trovati, null, 1));
    }
    log(`raccolti ${Object.keys(trovati).length}`);
    const next = p.locator('#elencoSchede_next'); if (await next.count() === 0 || /disabled/.test(await next.getAttribute('class') || '')) break;
    await next.locator('a').click(); await p.waitForTimeout(1500); pagina++;
    if (pagina > 200) break;
  }
  log('fine, totale ' + Object.keys(trovati).length); await b.close();
})().catch(e => { log('FATALE ' + e); process.exit(1); });
