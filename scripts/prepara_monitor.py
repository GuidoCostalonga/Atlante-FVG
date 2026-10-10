"""Prepara il frammento della sezione riservata «Monitor della percezione pubblica» (monitor/).

Unisce la grafica dell'Atlante (scripts/monitor_frammento.html: stile e struttura) con il programma del
cruscotto (app.js del progetto sentiment-fvg di costalonga.org) e con la libreria Chart.js, che viaggia
dentro il frammento cifrato: così la pagina non scarica nulla da siti esterni.

Uso:
  python3 -I scripts/prepara_monitor.py <app.js> <chart.umd.min.js 4.4.1> /tmp/frammento.html
  PAROLA='…' node scripts/cifra_pagina.js /tmp/frammento.html monitor/contenuto.json
"""
import base64
import hashlib
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
# Impronta SHA-384 pubblicata da cdnjs per Chart.js 4.4.1 (chart.umd.min.js)
CHART_SHA384 = 'bs/nf9FbdNouRbMiFcrcZfLXYPKiPaGVGplVbv7dLGECccEXDW+S3zjqSKR5ZEaD'


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    programma, libreria, uscita = (Path(a) for a in sys.argv[1:])
    chart = libreria.read_bytes()
    if base64.b64encode(hashlib.sha384(chart).digest()).decode() != CHART_SHA384:
        raise SystemExit('chart.umd.min.js non corrisponde alla versione 4.4.1 attesa')
    app = programma.read_text(encoding='utf-8')
    chart_testo = chart.decode('utf-8')
    for nome, testo in (('app.js', app), ('Chart.js', chart_testo)):
        if '</script' in testo.lower():
            raise SystemExit(f'{nome} contiene «</script»: il frammento non si potrebbe inserire')
    modello = (RADICE / 'scripts' / 'monitor_frammento.html').read_text(encoding='utf-8')
    if '<!--PROGRAMMA-->' not in modello:
        raise SystemExit('Segnaposto <!--PROGRAMMA--> mancante nel modello')
    # La pagina esegue gli script <script>…</script> uno dopo l'altro: prima la libreria, poi il programma
    frammento = modello.replace('<!--PROGRAMMA-->', f'<script>{chart_testo}</script>\n<script>{app}</script>')
    Path(uscita).write_text(frammento, encoding='utf-8')
    print(f'frammento scritto: {uscita} ({len(frammento.encode()):,} byte)'.replace(',', '.'))


if __name__ == '__main__':
    main()
