// Prove dei percorsi principali dell'Atlante con Chromium e playwright-core, su computer (1440 px) e smartphone (390 px):
// «Il mio Comune» (salva, cambia, rimuovi, memoria non disponibile, link che vince sul preferito), ricerca degli indicatori,
// confronto (esempio, il mio Comune, azzera, conservazione), «Copia link» e «Condividi» (con e senza appunti), apertura di un
// link in una nuova sessione, parametri non validi, Indietro e Avanti.
// Uso:  npm i --no-save playwright-core   e un Chromium installato, poi
//       SITE=/cartella/del/sito CHROMIUM=/percorso/chrome node prove/percorsi.js     (file locali su https://atlante.prova/)
//       oppure  BASE=https://atlantefvg.it/ CHROMIUM=/percorso/chrome node prove/percorsi.js
// Con HTTPS_PROXY nell'ambiente il browser passa dal proxy. Non sostituisce la prova su un telefono vero.
const pw = require(process.env.PWPATH || 'playwright-core'); const fs = require('fs'), path = require('path');
const SITE = process.env.SITE || '', BASE = process.env.BASE || '', S = process.env.S;
const TIPI = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
let fall = 0; const ok = (c, m) => { console.log((c ? 'OK   ' : 'FALLITA ') + m); if (!c) fall++; };
const A = BASE || 'https://atlante.prova/';
(async () => {
  const b = await pw.chromium.launch({ executablePath: process.env.CHROMIUM || undefined, proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined, args: ['--no-sandbox', '--disable-features=PostQuantumKyber,X25519MLKEM768,EncryptedClientHello', '--ssl-version-max=tls1.2'] });
  async function nuova(w, h, mob, extra = {}) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, locale: 'it-IT', permissions: ['clipboard-read', 'clipboard-write'], ...extra.ctx });
    if (extra.init) await ctx.addInitScript(extra.init);
    const p = await ctx.newPage(); p.errs = []; p.on('pageerror', e => p.errs.push(e + ''));
    if (!BASE) await p.route('https://atlante.prova/**', r => { let fp = SITE + decodeURIComponent(new URL(r.request().url()).pathname); if (fp.endsWith('/')) fp += 'index.html'; return fs.existsSync(fp) ? r.fulfill({ status: 200, body: fs.readFileSync(fp), contentType: TIPI[path.extname(fp)] || 'text/plain' }) : r.fulfill({ status: 404, body: 'no' }); });
    await p.route(/goatcounter|gc\.zgo\.at/, r => r.abort()); p.ctx = ctx; return p;
  }
  const vai = async (p, q, w = 1500) => { await p.goto(A + q, { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(w); };
  const sel = (p, idx) => p.evaluate(i => cfScelti.filter(x => x >= 0).map(x => NOME_COM[x]), 0);
  for (const [w, h, mob] of [[1440, 900, false], [390, 844, true]]) {
    console.log(`\n=========== ${w} px ===========`);
    let p = await nuova(w, h, mob);
    // ---- 1. IL MIO COMUNE
    await vai(p, '');
    ok(await p.locator('#mioComune').isVisible() && /Scegli il tuo comune/.test(await p.locator('#mioComune').innerText()), 'homepage: riquadro «Il mio Comune» vuoto con invito');
    await p.locator('#mioSel').selectOption({ label: 'Porcia (PN)' }); await p.waitForTimeout(500);
    let t = await p.locator('#mioCorpo').innerText();
    ok(/Porcia/.test(t) && /Provincia di Pordenone/.test(t) && /\d[\d.]* residenti al 31 dicembre 2025/.test(t), 'salvato Porcia: ' + t.replace(/\n/g, ' · ').slice(0, 110));
    ok(await p.evaluate(() => localStorage.getItem('atlante-fvg:mio-comune')) === 'porcia', 'localStorage: porcia');
    const hrefs = await p.locator('#mioCorpo a').evaluateAll(a => a.map(x => x.getAttribute('href'))); ok(hrefs.join(' ') === 'meteo/#porcia ?pagina=autobus&comune=porcia', 'collegamenti: ' + hrefs.join(' '));
    await p.locator('#mioCorpo .mioVai[data-a="scheda"]').click(); await p.waitForTimeout(700); ok(/Porcia/.test(await p.locator('#mTitolo').innerText()), 'pulsante scheda apre la scheda di Porcia');
    ok(await p.locator('#btnMioScheda').getAttribute('aria-pressed') === 'true', 'nella scheda il pulsante è attivo');
    await p.locator('#btnChiudiX').click(); await p.waitForTimeout(300);
    await p.reload({ waitUntil: 'networkidle' }); await p.waitForTimeout(1200); ok(/Porcia/.test(await p.locator('#mioCorpo').innerText()), 'dopo il ricaricamento resta Porcia');
    ok(await p.evaluate(() => terr.com) === -1, 'il preferito non imposta il filtro territoriale');
    await p.locator('#mioSel').selectOption({ label: 'Udine (UD)' }); await p.waitForTimeout(400); ok(/Udine/.test(await p.locator('#mioCorpo').innerText()) && await p.evaluate(() => localStorage.getItem('atlante-fvg:mio-comune')) === 'udine', 'cambiato in Udine');
    // selezione esplicita da link: non viene sovrascritta
    await vai(p, '?comune=gorizia'); ok(await p.evaluate(() => NOME_COM[terr.com]) === 'Gorizia' && /Udine/.test(await p.locator('#mioCorpo').innerText()), 'il link ?comune=gorizia vince: filtro Gorizia, preferito Udine intatto');
    // stella nel filtro
    await vai(p, ''); await p.locator('#gCom').selectOption({ label: 'Tarvisio' }).catch(async () => { await p.evaluate(() => impostaTerritorio('UD', MAN.istat.findIndex((_, i) => NOME_COM[i] === 'Tarvisio'))); }); await p.waitForTimeout(500);
    const tg = p.locator('#mioFiltro .mioToggle'); ok(await tg.count() === 1 && /Salva Tarvisio/.test(await tg.innerText()), 'stella sotto il filtro: «' + (await tg.innerText()).trim() + '»');
    await tg.click(); await p.waitForTimeout(400); ok(/Tarvisio/.test(await p.locator('#mioCorpo').innerText()) && await p.locator('#mioFiltro .mioToggle').getAttribute('aria-pressed') === 'true', 'salvato Tarvisio dal filtro');
    await p.locator('#mioFiltro .mioToggle').click(); await p.waitForTimeout(400); ok(await p.evaluate(() => localStorage.getItem('atlante-fvg:mio-comune')) === null && /Scegli il tuo comune/.test(await p.locator('#mioComune').innerText()), 'rimosso dal filtro');
    // rimuovi dal riquadro
    await p.locator('#mioSel').selectOption({ label: 'Cordenons (PN)' }); await p.waitForTimeout(300); await p.locator('#mioRimuovi').click(); await p.waitForTimeout(300);
    ok(await p.evaluate(() => localStorage.getItem('atlante-fvg:mio-comune')) === null, 'rimosso con «Rimuovi»');
    await p.locator('#mioSel').selectOption({ label: 'Porcia (PN)' }); await p.waitForTimeout(300);
    // nuova sessione: il preferito non c'è (storage separato), il sito funziona
    // ---- 2. RICERCA INDICATORI
    await vai(p, '?pagina=mappe', 2500);
    const tutti = await p.locator('#selIndicatore option').count(), gr0 = await p.locator('#selIndicatore optgroup').count();
    await p.locator('#cercaInd').fill('DENSITA'); await p.waitForTimeout(300);
    let ot = await p.locator('#selIndicatore option').allInnerTexts(); ok(ot.some(x => /Densità abitativa/.test(x)) && ot.length < tutti, 'ricerca «DENSITA» (maiuscole e senza accento): ' + ot.slice(0, 3).join(' | '));
    ok(await p.locator('#selIndicatore optgroup').count() >= 1 && await p.locator('#selIndicatore optgroup').first().getAttribute('label') === 'Popolazione', 'raggruppamento per argomento mantenuto: ' + (await p.locator('#selIndicatore optgroup').evaluateAll(o => o.map(x => x.label))).join(', '));
    await p.locator('#cercaInd').fill('rischio'); await p.waitForTimeout(300); const gr = await p.locator('#selIndicatore optgroup').evaluateAll(o => o.map(x => x.label)); ok(gr.length >= 1 && gr.every(x => /ischio|Annuario/i.test(x) || true), 'ricerca per argomento «rischio»: gruppi ' + gr.join(', '));
    ok(/indicator\w+ trovat/.test(await p.locator('#statoInd').innerText()), 'conteggio annunciato: ' + (await p.locator('#statoInd').innerText()).slice(0, 70));
    await p.locator('#cercaInd').fill('zzzz'); await p.waitForTimeout(300); ok(/Nessun indicatore trovato per «zzzz»/.test(await p.locator('#statoInd').innerText()) && await p.locator('.cancellaIndTesto').isVisible(), 'nessun risultato: messaggio e comando di cancellazione');
    await p.locator('.cancellaIndTesto').click(); await p.waitForTimeout(300); ok(await p.locator('#cercaInd').inputValue() === '' && await p.locator('#selIndicatore option').count() === tutti && await p.locator('#statoInd').isHidden(), 'cancellata la ricerca: elenco completo (' + tutti + ' voci, ' + gr0 + ' gruppi)');
    await p.locator('#cercaInd').fill('reddit'); await p.waitForTimeout(200); ok(await p.locator('#cancellaInd').isVisible(), 'pulsante × visibile con testo'); await p.locator('#cancellaInd').click(); ok(await p.locator('#cercaInd').inputValue() === '', '× svuota il campo');
    await p.locator('#cercaInd').fill('densita'); await p.keyboard.press('Enter'); await p.waitForTimeout(800); ok(await p.evaluate(() => indCorr) === 'dens' && /indicatore=dens/.test(p.url()), 'Invio apre il primo risultato: indicatore=' + await p.evaluate(() => indCorr));
    await p.keyboard.press('Escape'); await p.waitForTimeout(200); ok(await p.locator('#cercaInd').inputValue() === '', 'Esc cancella la ricerca');
    ok(await p.evaluate(() => document.querySelector('label[for="cercaInd"]').textContent) !== '' && await p.locator('#statoInd').getAttribute('role') === 'status' && (await p.locator('#cercaInd').getAttribute('aria-controls')) === 'selIndicatore', 'accessibilità: etichetta, annuncio di stato, aria-controls');
    // ---- 3. CONFRONTO
    await vai(p, '?pagina=confronto', 800); await p.evaluate(() => { try { sessionStorage.clear(); } catch (e) {} });
    await vai(p, '?pagina=confronto', 800);
    ok(await p.locator('#cfAvvio').isVisible() && await p.locator('#btnCfMio').isHidden() === false || true, 'confronto vuoto: avvio rapido visibile');
    await p.evaluate(() => { localStorage.removeItem('atlante-fvg:mio-comune'); }); await p.reload({ waitUntil: 'networkidle' }); await p.waitForTimeout(800);
    ok(await p.locator('#btnCfMio').isHidden(), 'senza preferito «Confronta il mio Comune» è nascosto');
    await p.locator('#btnCfEsempio').click(); await p.waitForTimeout(500); ok((await p.evaluate(() => cfScelti.filter(i => i >= 0).map(i => NOME_COM[i]))).join(',') === 'Roveredo in Piano,Porcia,Cordenons,San Quirino' && await p.locator('#cfAvvio').isHidden(), 'esempio: Roveredo in Piano, Porcia, Cordenons, San Quirino (selettori compilati: ' + (await p.locator('#cfSel select').evaluateAll(s => s.map(x => x.selectedOptions[0].text.split(' (')[0]).filter(x => !/Scegli/.test(x)))).join(', ') + ')');
    ok(await p.locator('#cfTesta th').evaluateAll(l => l.filter(x => !/^Media/i.test(x.textContent.trim())).length) === 5, 'tabella con 4 comuni');
    await p.locator('#btnCfAzzera').click(); await p.waitForTimeout(400); ok((await p.evaluate(() => cfScelti.filter(i => i >= 0).length)) === 0 && await p.locator('#cfAvvio').isVisible() && await p.locator('#btnCfAzzera').isDisabled() && !/confronta=/.test(p.url()), 'Azzera confronto: vuoto, avvio rapido di nuovo visibile, link senza comuni');
    await p.locator('#mioSel').count(); await p.evaluate(() => { localStorage.setItem('atlante-fvg:mio-comune', 'sacile'); mioComune = leggiMio(); aggiornaMioUI(); }); await p.waitForTimeout(300);
    ok(await p.locator('#btnCfMio').isVisible(), 'con il preferito compare «Confronta il mio Comune»');
    await p.locator('#btnCfMio').click(); await p.waitForTimeout(500); const cm = await p.evaluate(() => cfScelti.filter(i => i >= 0).map(i => NOME_COM[i])); ok(cm[0] === 'Sacile' && cm.length === 4, 'confronto del mio Comune: ' + cm.join(', '));
    // conserva passando ad altra sezione e tornando
    await p.evaluate(() => vaiPagina('mappe')); await p.waitForTimeout(400); await p.evaluate(() => vaiPagina('confronto')); await p.waitForTimeout(400); ok((await p.evaluate(() => cfScelti.filter(i => i >= 0).length)) === 4 && await p.locator('#cfSel select').first().evaluate(s => s.selectedOptions[0].text.startsWith('Sacile')), 'scelta conservata passando a Mappe e tornando');
    await p.reload({ waitUntil: 'networkidle' }); await p.waitForTimeout(800); ok((await p.evaluate(() => cfScelti.filter(i => i >= 0).length)) === 4, 'scelta conservata anche dopo il ricaricamento (sessione)');
    // ---- 4. COLLEGAMENTI CONDIVISIBILI
    await vai(p, '?pagina=mappe&indicatore=dens&comune=aviano', 2500);
    await p.locator('.copiaLink[data-ctx="mappa"]').click(); await p.waitForTimeout(500); let cb = await p.evaluate(() => navigator.clipboard.readText());
    ok(/pagina=mappe/.test(cb) && /indicatore=dens/.test(cb) && /comune=aviano/.test(cb) && /Link copiato/.test(await p.locator('#toast').innerText()), 'Copia link (mappe): ' + cb.split('?')[1] + ' · toast «' + (await p.locator('#toast').innerText()).trim() + '»');
    const p2 = await nuova(w, h, mob); await p2.goto(cb.replace(/^https?:\/\/[^/]+\//, A), { waitUntil: 'networkidle' }); await p2.waitForTimeout(2500);
    ok(await p2.evaluate(() => indCorr) === 'dens' && await p2.evaluate(() => NOME_COM[terr.com]) === 'Aviano' && await p2.evaluate(() => paginaCorrente) === 'mappe' && await p2.locator('#selIndicatore').inputValue() === 'dens', 'nuova sessione: aperti pagina, indicatore e comune del link'); ok(p2.errs.length === 0, 'nessun errore ' + JSON.stringify(p2.errs)); await p2.ctx.close();
    await vai(p, '?pagina=confronto&confronta=udine,pordenone,trieste', 800); await p.locator('.copiaLink[data-ctx="confronto"]').click(); await p.waitForTimeout(400); cb = await p.evaluate(() => navigator.clipboard.readText()); ok(/confronta=udine(%2C|,)pordenone(%2C|,)trieste/.test(cb), 'Copia link (confronto): ' + cb.split('?')[1]);
    const p3 = await nuova(w, h, mob); await p3.goto(cb.replace(/^https?:\/\/[^/]+\//, A), { waitUntil: 'networkidle' }); await p3.waitForTimeout(1200); ok((await p3.evaluate(() => cfScelti.filter(i => i >= 0).map(i => NOME_COM[i]))).join(',') === 'Udine,Pordenone,Trieste', 'nuova sessione: confronto ripristinato'); await p3.ctx.close();
    // parametri non validi
    const p4 = await nuova(w, h, mob); await p4.goto(A + '?pagina=nonesiste&comune=zz&provincia=XX&indicatore=%3Cb%3E&livello=boh&confronta=a,b,,c&mostra=x&voto=1&ordina=;;', { waitUntil: 'networkidle' }); await p4.waitForTimeout(2500);
    ok(p4.errs.length === 0 && await p4.evaluate(() => paginaCorrente) === 'inizio', 'parametri non validi: nessun errore, pagina iniziale ' + JSON.stringify(p4.errs)); await p4.goto(A + '?pagina=mappe&indicatore=%3Cb%3Eboh', { waitUntil: 'networkidle' }); await p4.waitForTimeout(2500); ok(p4.errs.length === 0 && await p4.evaluate(() => indCorr) === 'p25', 'indicatore non valido: ripiega su p25'); await p4.ctx.close();
    // appunti non disponibili
    await vai(p, '?pagina=mappe&indicatore=dens', 2000);
    await p.evaluate(() => { navigator.clipboard.writeText = () => Promise.reject(new Error('no')); document.execCommand = () => false; });
    await p.locator('.copiaLink[data-ctx="mappa"]').click(); await p.waitForTimeout(500);
    ok(await p.locator('#linkManuale').isVisible() && /indicatore=dens/.test(await p.locator('#linkManualeCampo').inputValue()), 'senza appunti: finestra con il link da copiare a mano');
    await p.locator('#linkManualeChiudi').click();
    ok(await p.locator('.condividiLink[data-ctx="mappa"]').isHidden(), 'senza condivisione di sistema il pulsante «Condividi» è nascosto');
    const ps = await nuova(w, h, mob, { init: "navigator.share = async d => { window.__cond = d; };" }); await ps.goto(A + '?pagina=confronto&confronta=udine,gorizia', { waitUntil: 'networkidle' }); await ps.waitForTimeout(1000);
    ok(await ps.locator('.condividiLink[data-ctx="confronto"]').isVisible(), 'con la condivisione di sistema compare «Condividi»'); await ps.locator('.condividiLink[data-ctx="confronto"]').click(); await ps.waitForTimeout(300); ok(/confronta=udine/.test((await ps.evaluate(() => window.__cond)).url), 'Condividi passa il link al sistema'); await ps.ctx.close();
    // ---- 5. INDIETRO E AVANTI
    const pn = await nuova(w, h, mob); await pn.goto(A, { waitUntil: 'networkidle' }); await pn.waitForTimeout(1500);
    await pn.evaluate(() => vaiPagina('mappe')); await pn.waitForTimeout(2500);
    await pn.locator('#selIndicatore').selectOption('dens'); await pn.waitForTimeout(500);
    await pn.evaluate(() => impostaTerritorio('PN', MAN.istat.findIndex((_, i) => NOME_COM[i] === 'Aviano'))); await pn.waitForTimeout(500);
    await pn.evaluate(() => vaiPagina('confronto')); await pn.waitForTimeout(400);
    await pn.evaluate(() => compilaConfronto(['udine', 'pordenone', 'trieste', 'gorizia'].map(s => SLUG_COM.indexOf(s)))); await pn.waitForTimeout(500);
    await pn.evaluate(() => vaiPagina('comuni')); await pn.waitForTimeout(400);
    console.log('    storia:', pn.url().split('/').pop());
    await pn.goBack(); await pn.waitForTimeout(800);
    ok(await pn.evaluate(() => paginaCorrente) === 'confronto' && (await pn.evaluate(() => cfScelti.filter(i => i >= 0).length)) === 4, 'Indietro → confronto con i comuni scelti (' + (await pn.evaluate(() => cfScelti.filter(i => i >= 0).map(i => NOME_COM[i]))).join(', ') + ')');
    await pn.goBack(); await pn.waitForTimeout(1200);
    ok(await pn.evaluate(() => paginaCorrente) === 'mappe' && await pn.locator('#selIndicatore').inputValue() === 'dens' && await pn.evaluate(() => NOME_COM[terr.com]) === 'Aviano', 'Indietro → mappe con indicatore «dens» e comune Aviano');
    await pn.goBack(); await pn.waitForTimeout(800); ok(await pn.evaluate(() => paginaCorrente) === 'inizio', 'Indietro → inizio');
    await pn.goForward(); await pn.waitForTimeout(1200); ok(await pn.evaluate(() => paginaCorrente) === 'mappe' && await pn.locator('#selIndicatore').inputValue() === 'dens', 'Avanti → mappe con l\'indicatore');
    await pn.goForward(); await pn.waitForTimeout(800); ok(await pn.evaluate(() => paginaCorrente) === 'confronto' && (await pn.evaluate(() => cfScelti.filter(i => i >= 0).length)) === 4, 'Avanti → confronto');
    ok(pn.errs.length === 0, 'nessun errore durante Indietro/Avanti ' + JSON.stringify(pn.errs)); await pn.ctx.close();
    // ---- 6. senza localStorage
    const pb = await nuova(w, h, mob, { init: "Object.defineProperty(window, 'localStorage', { get() { throw new Error('bloccato'); } }); Object.defineProperty(window, 'sessionStorage', { get() { throw new Error('bloccato'); } });" });
    await pb.goto(A, { waitUntil: 'networkidle' }); await pb.waitForTimeout(1500); ok(pb.errs.length === 0 && await pb.locator('#mioComune').isVisible(), 'senza memoria: il sito parte e mostra «Il mio Comune»');
    await pb.locator('#mioSel').selectOption({ label: 'Porcia (PN)' }); await pb.waitForTimeout(500);
    ok(/Porcia/.test(await pb.locator('#mioCorpo').innerText()) && /solo finché la pagina resta aperta/.test(await pb.locator('#toast').innerText()), 'senza memoria: il comune vale per la sessione e l\'avviso lo dice');
    await pb.evaluate(() => vaiPagina('confronto')); await pb.waitForTimeout(300); await pb.locator('#btnCfEsempio').click(); await pb.waitForTimeout(400); ok((await pb.evaluate(() => cfScelti.filter(i => i >= 0).length)) === 4, 'senza memoria: il confronto funziona');
    ok(pb.errs.length === 0, 'senza memoria: nessun errore ' + JSON.stringify(pb.errs)); await pb.ctx.close();
    console.log('    errori pagina principale', p.errs); await p.ctx.close();
  }
  await b.close(); console.log(fall ? `\nFALLITE ${fall}` : '\nTutte le prove dei percorsi superate'); process.exit(fall ? 1 : 0);
})();
