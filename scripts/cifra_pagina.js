// Cifra un frammento HTML con una parola d'ordine, per le sezioni riservate dell'Atlante.
// Il frammento viene compresso (gzip) e cifrato con AES-GCM a 256 bit; la chiave deriva dalla parola
// d'ordine con PBKDF2 (SHA-256, 300.000 giri, sale casuale). La pagina lo decifra nel browser con WebCrypto.
// Uso:  PAROLA='…' node scripts/cifra_pagina.js <frammento.html> <uscita.json>
// Il risultato è un JSON {v, s, i, d}: versione, sale, vettore iniziale e dati, tutti in base64.
const fs = require('fs'), zlib = require('zlib'), { webcrypto } = require('crypto');
const [sorgente, uscita] = process.argv.slice(2), parola = process.env.PAROLA;
if (!sorgente || !uscita || !parola) { console.error('Uso: PAROLA=… node scripts/cifra_pagina.js <frammento.html> <uscita.json>'); process.exit(1); }
(async () => {
  const sale = webcrypto.getRandomValues(new Uint8Array(16)), iv = webcrypto.getRandomValues(new Uint8Array(12));
  const base = await webcrypto.subtle.importKey('raw', new TextEncoder().encode(parola.normalize('NFC')), 'PBKDF2', false, ['deriveKey']);
  const chiave = await webcrypto.subtle.deriveKey({ name: 'PBKDF2', salt: sale, iterations: 300000, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
  const chiaro = zlib.gzipSync(fs.readFileSync(sorgente), { level: 9 });
  const cifrato = new Uint8Array(await webcrypto.subtle.encrypt({ name: 'AES-GCM', iv }, chiave, chiaro));
  const b64 = a => Buffer.from(a).toString('base64');
  fs.writeFileSync(uscita, JSON.stringify({ v: 1, s: b64(sale), i: b64(iv), d: b64(cifrato) }));
  console.log(`cifrato: ${fs.statSync(sorgente).size.toLocaleString('it')} byte in chiaro → ${chiaro.length.toLocaleString('it')} compressi → ${fs.statSync(uscita).size.toLocaleString('it')} nel file ${uscita}`);
})();
