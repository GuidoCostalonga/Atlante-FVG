"""Compila il frammento cifrato della sezione riservata «Osservatorio sondaggi» (sondaggi/contenuto.json).

Unisce il modello scripts/sondaggi/frammento.html (struttura e stile) con il programma scripts/sondaggi/app.js
e cifra il risultato con scripts/cifra_pagina.js. Il sale resta quello già presente in sondaggi/contenuto.json
(MANTIENI_SALE=1), così la chiave con cui il flusso automatico cifra l'archivio non cambia.

Uso:  PAROLA='…' python3 scripts/sondaggi/compila_pagina.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent.parent
QUI = Path(__file__).resolve().parent


def main() -> None:
    if not os.environ.get('PAROLA'):
        raise SystemExit("Serve la parola d'ordine nella variabile PAROLA")
    modello = (QUI / 'frammento.html').read_text(encoding='utf-8')
    app = (QUI / 'app.js').read_text(encoding='utf-8')
    if '</script' in app.lower():
        raise SystemExit('app.js contiene «</script»: il frammento non si potrebbe inserire')
    if '<!--PROGRAMMA-->' not in modello:
        raise SystemExit('Segnaposto <!--PROGRAMMA--> mancante nel modello')
    frammento = modello.replace('<!--PROGRAMMA-->', f'<script>{app}</script>')
    uscita = RADICE / 'sondaggi' / 'contenuto.json'
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(frammento)
        tmp = f.name
    try:
        ambiente = dict(os.environ)
        if uscita.exists():
            ambiente['MANTIENI_SALE'] = '1'
        subprocess.run(['node', str(RADICE / 'scripts' / 'cifra_pagina.js'), tmp, str(uscita)], check=True, env=ambiente)
    finally:
        os.unlink(tmp)
    print(f'frammento: {len(frammento.encode()):,} byte → {uscita}'.replace(',', '.'))


if __name__ == '__main__':
    sys.exit(main())
