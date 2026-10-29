"""Estrae i fogli DATI_EUROSTAT, TERRITORI e DIZ_EUROSTAT dagli Excel dei lotti 1 e 2 già decompressi.

Uso: python3 estrai_eurostat.py <cartella con PAESI/ e AGGREGATI/> <uscita.json>
"""
import glob, json, sys
import openpyxl

radice, uscita = sys.argv[1], sys.argv[2]
serie, territori, diz, agg = {}, {}, {}, {}
for f in sorted(glob.glob(radice + '/PAESI/*/L0[12]_*.xlsx') + glob.glob(radice + '/AGGREGATI/*/L0[12]_*.xlsx')):
    lotto = 1 if '/L01_' in f else 2
    wb = openpyxl.load_workbook(f, read_only=True)
    if 'DATI_EUROSTAT' not in wb.sheetnames:
        continue
    for r in wb['DATI_EUROSTAT'].iter_rows(min_row=4, values_only=True):
        r = r[1:]
        if not r or r[0] is None:
            continue
        if lotto == 1:
            cod, nome, liv, ds, anno, val, txt, unita, sesso, eta, freq, stato, agg_f, url = r[:14]
            chiave = '|'.join([ds, unita or '', sesso or '', eta or ''])
        else:
            cod, nome, liv, ds, anno, val, txt, unita, ind, ind_n, freq, stato, dims, agg_f, url = r[:15]
            chiave = '|'.join([ds, unita or '', '', '', ind or ''])
        territori.setdefault(cod, [nome, liv])
        agg[ds] = agg_f
        serie.setdefault(chiave, {}).setdefault(cod, {})[anno] = [val, stato]
    for r in wb['DIZ_EUROSTAT'].iter_rows(min_row=4, values_only=True):
        r = r[1:]
        if r and r[0]:
            diz['|'.join(str(x) for x in r[:3])] = r[3]
    wb.close()
json.dump({'serie': serie, 'territori': territori, 'diz': diz, 'agg': agg}, open(uscita, 'w'))
print(len(serie), 'serie;', len(territori), 'territori')
