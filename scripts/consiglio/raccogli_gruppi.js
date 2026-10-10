const pw = require(process.env.PWPATH || 'playwright-core'); const fs = require('fs');
(async () => {
  const b = await pw.chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined, args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] });
  const p = await (await b.newContext({ locale: 'it-IT' })).newPage(); p.setDefaultTimeout(60000);
  const out = {};
  for (let k = 0; k < 7; k++) {
    await p.goto('https://www.consiglio.regione.fvg.it/cms/organi/gruppi.html', { waitUntil: 'networkidle', timeout: 90000 });
    const nome = await p.locator(`a[href*="LV_Gruppi$ctrl${k}$"]`).first().innerText();
    await Promise.all([p.waitForNavigation({ waitUntil: 'networkidle', timeout: 90000 }).catch(() => {}), p.locator(`a[href*="LV_Gruppi$ctrl${k}$"]`).first().click()]); await p.waitForTimeout(800);
    const t = await p.evaluate(() => document.body.innerText.replace(/[ \t]+/g, ' '));
    fs.writeFileSync(`gruppo_${k}.txt`, t);
    const i = t.indexOf(nome.trim()); out[nome.trim()] = t.slice(i, i + 1500);
    console.log(k, nome.trim(), p.url().slice(-60));
  }
  fs.writeFileSync('gruppi_grezzi.json', JSON.stringify(out, null, 1)); await b.close();
})();
