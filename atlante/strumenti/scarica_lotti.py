"""Scarica dalla cartella Drive condivisa i file dei lotti indicati, verificando dimensione e SHA256.
Uso: python3 scarica_lotti.py <indice.csv> <cartella uscita> <lotto> [<lotto> ...]
L'indice e' "open data/Open data internazionali  indice completo dei lotti 1-31 su Drive.csv"
(separatore ;). I file gia' presenti e verificati non vengono riscaricati, quindi il comando
si puo' rilanciare dopo un'interruzione. Ogni lotto finisce in <cartella uscita>/L<lotto>/."""
import csv, hashlib, os, subprocess, sys, time
indice, uscita, lotti = sys.argv[1], sys.argv[2], sys.argv[3:]
righe = [r for r in csv.DictReader(open(indice, encoding='utf-8-sig'), delimiter=';') if r['lotto'] in lotti]
print(len(righe), 'file da scaricare', flush=True)
import re, html
def scarica(fid, dest):
    url = f"https://drive.google.com/uc?id={fid}&export=download&confirm=t"
    subprocess.run(['curl', '-sS', '-L', '-m', '900', '-o', dest, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(dest) or os.path.getsize(dest) > 20000:
        return
    testo = open(dest, 'rb').read(20000).decode('utf-8', 'replace')
    if 'Virus scan warning' not in testo and '<form' not in testo:
        return
    # pagina di avviso antivirus: si segue il modulo di conferma
    m = re.search(r'<form[^>]*action="([^"]+)"', testo)
    if not m:
        return
    azione = html.unescape(m.group(1))
    campi = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', testo))
    q = '&'.join(f'{k}={v}' for k, v in campi.items())
    subprocess.run(['curl', '-sS', '-L', '-m', '900', '-o', dest, f'{azione}?{q}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
ok = 0
for r in righe:
    cart = os.path.join(uscita, 'L' + r['lotto']); os.makedirs(cart, exist_ok=True)
    dest = os.path.join(cart, r['file_originale'])
    if os.path.exists(dest) and os.path.getsize(dest) == int(r['byte']) and sha(dest) == r['sha256']:
        ok += 1; continue
    for tent in range(4):
        scarica(r['drive_file_id'], dest)
        if os.path.exists(dest) and os.path.getsize(dest) == int(r['byte']) and sha(dest) == r['sha256']:
            ok += 1; break
        time.sleep(5 * (tent + 1))
    else:
        print('ERRORE', r['lotto'], r['file_originale'], flush=True)
    if ok % 10 == 0: print(ok, 'ok', flush=True)
print('completati', ok, 'su', len(righe), flush=True)
