"""Dati aggiuntivi dell'Atlante: territori NUTS Eurostat (lotti 1 e 2 e API), indici DG REGIO e insiemi di dati dei lotti.

Chiamato da genera_dati.py con --eurostat, --eurostat-api, --regio e --insiemi (file prodotti da estrai_eurostat.py,
estrai_eurostat_api.py, estrai_regio.py ed estrai_lotti.py).
"""
import glob, gzip, json, os, re

TEMA_EU = 'eur'
NOME_TEMA_EU = 'Demografia regionale europea (Eurostat)'
NOME_TEMA_EU_ESTESO = 'Regioni europee (Eurostat e Commissione europea): popolazione, economia, lavoro, istruzione, salute, società, digitale, turismo, trasporti, agricoltura, ambiente, indici regionali e fondi europei'

ETA = {'TOTAL': None, 'Y_LT15': 'sotto i 15 anni', 'Y15-64': 'da 15 a 64 anni', 'Y_GE65': 'di 65 anni e oltre', 'UNK': 'età non nota'}
SESSO = {'T': None, 'M': 'uomini', 'F': 'donne'}
FIND3 = {
    'TOTFERRT': ('Figli per donna, regioni europee', 'nati per donna', 'Total fertility rate'),
    'AGEMOTH': ('Età media delle madri al parto', 'anni', 'Mean age of women at childbirth'),
    'MEDAGEMOTH': ('Età mediana delle madri al parto', 'anni', 'Median age of women at childbirth'),
}
DATASET_EU = {
    'demo_r_d3dens': ('Population density by NUTS 3 region', 1),
    'demo_r_pjanaggr3': ('Population on 1 January by broad age group, sex and NUTS 3 region', 1),
    'demo_r_births': ('Live births (total) by NUTS 3 region', 2),
    'demo_r_deaths': ('Deaths (total) by NUTS 3 region', 2),
    'demo_r_find3': ('Fertility indicators by NUTS 3 region', 2),
}
STATI_EU = {'b': 'interruzione della serie', 'c': 'riservato', 'd': 'definizione diversa', 'e': 'stimato',
            'f': 'previsione', 'n': 'non significativo', 'p': 'provvisorio', 'r': 'rivisto', 's': 'stima di Eurostat',
            'u': 'bassa affidabilità', 'z': 'non applicabile', ':': 'non disponibile'}
ISO3_EXTRA = {'UK': 'GBR', 'EL': 'GRC', 'BA': 'BIH', 'XK': 'XKX', 'UA': 'UKR', 'MD': 'MDA', 'GE': 'GEO', 'AM': 'ARM', 'AZ': 'AZE', 'BY': 'BLR', 'RU': 'RUS'}
AGG_EU_IT = {'DE_TOT': 'Germania, compresa l’ex RDT (Repubblica democratica tedesca)',
             'EFTA': 'Associazione europea di libero scambio (EFTA)', 'EU27_2007': 'Unione europea a 27 (2007/2013)',
             'EU27_2020': 'Unione europea a 27 (dal 2020)', 'EU28': 'Unione europea a 28 (2013/2020)',
             # aree metropolitane unite nell’indice di competitività regionale (RCI) della Commissione europea
             'AT_C': 'Area metropolitana di Vienna (regione della capitale unita al suo bacino di pendolarismo nell’indice RCI)',
             'BE_C': 'Area metropolitana di Bruxelles (regione della capitale unita al suo bacino di pendolarismo nell’indice RCI)',
             'CZ_C': 'Area metropolitana di Praga (regione della capitale unita al suo bacino di pendolarismo nell’indice RCI)',
             'DE_C': 'Area metropolitana di Berlino (regione della capitale unita al suo bacino di pendolarismo nell’indice RCI)',
             'HR_C': 'Area metropolitana di Zagabria (regione della capitale unita al suo bacino di pendolarismo nell’indice RCI)',
             'HU_C': 'Area metropolitana di Budapest (regione della capitale unita al suo bacino di pendolarismo nell’indice RCI)',
             'NL_C': 'Area metropolitana di Amsterdam (regione della capitale unita al suo bacino di pendolarismo nell’indice RCI)'}

# Nomi italiani dei dataset degli archivi parziali (dal catalogo FAOSTAT e OCSE)
DATASET_IT = {
    'CB': 'Bilanci delle merci non alimentari', 'EI': 'Intensità delle emissioni agroalimentari',
    'EK': 'Caratteristiche degli allevamenti', 'ESB': 'Bilancio dei nutrienti nei terreni coltivati',
    'FA': 'Spedizioni di aiuti alimentari del PAM (archivio storico)', 'RFB': 'Fertilizzanti per prodotto',
    'RFN': 'Fertilizzanti per nutriente', 'EM': 'Indicatori delle emissioni agroalimentari',
    'GPP': 'Emissioni prima e dopo la produzione agricola', 'SUA': 'Disponibilità alimentare da bilanci di utilizzo',
    'EMN': 'Letame degli allevamenti', 'GFDI': 'Quote di valore della filiera alimentare',
    'PA': 'Prezzi alla produzione (archivio storico)', 'FT': 'Flussi commerciali forestali (archivio storico)',
    'QV': 'Valore della produzione agricola',
    'DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA': 'Adulti per titolo di studio, età e sesso',
    'DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_GENDER': 'Adulti per sesso, titolo di studio ed età',
    'DSD_EAG_UOE_NON_FIN_PERS@DF_UOE_NF_PERS_RAW_INST2': 'Assistenti degli insegnanti',
    'RFM': 'Commercio di fertilizzanti per paese partner', 'GT': 'Emissioni totali dei sistemi agroalimentari',
    'FO': 'Produzione e commercio forestale', 'QCL': 'Produzione di colture e prodotti zootecnici',
    'FBS': 'Bilanci alimentari (dal 2010)', 'GLE': 'Emissioni degli allevamenti',
    'EA': 'Flussi di sviluppo verso l’agricoltura', 'TI': 'Indici del commercio agricolo',
    'FBSH': 'Bilanci alimentari storici (fino al 2013, vecchia metodologia)',
}
DATASET_IT.update({
    'AE': 'Spesa per ricerca agricola (ASTI)', 'AF': 'Ricercatori agricoli (ASTI)', 'BE': 'Bioenergia', 'CAHD': 'Costo e accessibilità di una dieta sana',
    'CBH': 'Bilanci delle merci non alimentari (fino al 2013, vecchia metodologia)', 'CP': 'Indici dei prezzi al consumo', 'CS': 'Stock di capitale',
    'ET': 'Variazione della temperatura sulla terraferma', 'FDI': 'Investimenti diretti esteri in agricoltura', 'FOP': 'Capacità di pasta di legno e carta (indagine)',
    'FS': 'Indicatori di sicurezza alimentare', 'GCE': 'Emissioni dalle colture', 'GF': 'Emissioni dalle foreste', 'GI': 'Emissioni dagli incendi',
    'GN': 'Emissioni dall’uso di energia in agricoltura', 'GV': 'Emissioni dai suoli organici drenati', 'HCES': 'Consumo alimentare apparente da indagini sulle famiglie',
    'HS': 'Indicatori da indagini sulle famiglie (archivio storico)', 'IC': 'Credito all’agricoltura', 'IG': 'Spesa pubblica per l’agricoltura',
    'LC': 'Copertura del suolo', 'MDDW': 'Diversità alimentare minima delle donne (MDD-W)', 'MK': 'Indicatori macroeconomici',
    'OA': 'Popolazione annuale', 'OEA': 'Occupazione in agricoltura e sistemi agroalimentari', 'OER': 'Occupazione rurale',
    'PD': 'Deflatori', 'PE': 'Tassi di cambio', 'PP': 'Prezzi alla produzione', 'QI': 'Indici della produzione agricola',
    'RA': 'Fertilizzanti (archivio storico)', 'RL': 'Uso del suolo', 'RLIS': 'Indicatori delle condizioni di vita rurali', 'RM': 'Macchine agricole (archivio storico)',
    'RP': 'Uso di pesticidi', 'RT': 'Commercio di pesticidi', 'RY': 'Macchine agricole (archivio storico, serie precedente)', 'SCL': 'Conti di approvvigionamento e utilizzo (dal 2010)',
    'SDGB': 'Indicatori degli Obiettivi di sviluppo sostenibile', 'SXS': 'Indicatori di genere', 'TCL': 'Commercio di prodotti agricoli e zootecnici',
    'TCLI': 'Indicatori del commercio agricolo', 'TM': 'Matrice dettagliata del commercio', 'WCAD': 'Censimenti agricoli mondiali (dati strutturali)',
    'WHO_GHO': 'Osservatorio sanitario mondiale (GHO): 20 indicatori',
    'SYB_1': 'Popolazione, densità e superficie', 'SYB_327': 'Migranti internazionali e rifugiati', 'SYB_246': 'Crescita della popolazione, fecondità e mortalità',
    'SYB_253': 'Popolazione urbana e capitali', 'SYB_309': 'Iscritti all’istruzione primaria e secondaria', 'SYB_323': 'Personale docente',
    'SYB_263': 'Produzione, commercio e offerta di energia', 'SYB_328': 'Omicidi volontari e altri reati', 'SYB_317': 'Seggi parlamentari occupati da donne',
    'SYB_319': 'Rapporto fra ragazze e ragazzi nell’istruzione', 'SYB_310': 'Stime delle emissioni di CO₂', 'SYB_315': 'Acqua potabile e servizi igienici',
    'SYB_313': 'Specie minacciate', 'SYB_314': 'Uso di internet',
    '7cae02f84ed547fbbd6210d90da19879': 'Rischio INFORM legato al clima', '9c3764c0efcc4c71934ab3988f219e0e': 'Concentrazione atmosferica di CO₂ (mondo)',
    'b13b69ee0dde43a99c811f592af4e821': 'Frequenza dei disastri legati al clima', '74561f6a-4783-4d70-b86a-008deec09441': 'Popolazione dei quartieri di Karlsruhe',
})
FONTE_IT = {'FAOSTAT': 'FAOSTAT (FAO, Organizzazione per l’alimentazione e l’agricoltura)', 'WHO': 'OMS (Organizzazione mondiale della sanità)',
            'OECD': 'OCSE (Organizzazione per la cooperazione e lo sviluppo economico)', 'UNSD': 'ONU (Divisione statistica delle Nazioni Unite, annuario statistico)',
            'IMF': 'FMI (Fondo monetario internazionale, cruscotto climatico)', 'DATA_EUROPA': 'data.europa.eu (portale europeo dei dati aperti)', 'ALTRO': 'Altra fonte'}
AGG_FONTI_IT = {'WHO_GLOBAL': 'Mondo (OMS)', 'WHO_AFR': 'Africa (regione OMS)', 'WHO_AMR': 'Americhe (regione OMS)', 'WHO_SEAR': 'Sud-est asiatico (regione OMS)',
                'WHO_EUR': 'Europa (regione OMS)', 'WHO_EMR': 'Mediterraneo orientale (regione OMS)', 'WHO_WPR': 'Pacifico occidentale (regione OMS)',
                'WHO_WB_HI': 'Paesi ad alto reddito (OMS, classificazione Banca Mondiale)', 'WHO_WB_UMI': 'Paesi a reddito medio-alto (OMS, classificazione Banca Mondiale)',
                'WHO_WB_LMI': 'Paesi a reddito medio-basso (OMS, classificazione Banca Mondiale)', 'WHO_WB_LI': 'Paesi a basso reddito (OMS, classificazione Banca Mondiale)'}
STORICI_IT = {'TWN': 'Taiwan', 'AIA': 'Anguilla', 'SHN': 'Ascensione, Sant’Elena e Tristan da Cunha',
              'BES': 'Bonaire, Sint Eustatius e Saba', 'COK': 'Isole Cook', 'FAO_351': 'Cina (totale FAOSTAT)',
              'FAO_357': 'Cina, esclusi Hong Kong e Macao', 'FAO_15': 'Belgio e Lussemburgo (codice storico FAOSTAT)',
              'FAO_259': 'Isole del Canale', 'FAO_62': 'Etiopia (Repubblica popolare democratica, codice storico FAOSTAT)',
              # aggregati statistici FAOSTAT (archivi parziali)
              'FAO_5100': 'Africa (aggregato FAOSTAT)', 'FAO_5101': 'Africa orientale (aggregato FAOSTAT)',
              'FAO_5102': 'Africa centrale (aggregato FAOSTAT)', 'FAO_5207': 'America meridionale (aggregato FAOSTAT)',
              'FAO_5300': 'Asia (aggregato FAOSTAT)', 'FAO_5301': 'Asia centrale (aggregato FAOSTAT)',
              'FAO_5302': 'Asia orientale (aggregato FAOSTAT)', 'FAO_5303': 'Asia meridionale (aggregato FAOSTAT)',
              'FAO_5304': 'Asia sudorientale (aggregato FAOSTAT)', 'FAO_5501': 'Australia e Nuova Zelanda (aggregato FAOSTAT)',
              'FAO_5502': 'Melanesia (aggregato FAOSTAT)', 'FAO_5503': 'Micronesia (aggregato FAOSTAT)',
              'FAO_5801': 'Paesi meno sviluppati (aggregato FAOSTAT)', 'FAO_5802': 'Paesi in via di sviluppo senza sbocco sul mare (aggregato FAOSTAT)',
              'FAO_5803': 'Piccoli stati insulari in via di sviluppo (aggregato FAOSTAT)',
              'FAO_5848': 'Paesi dell’Allegato I della Convenzione sul clima (aggregato FAOSTAT)',
              'FAO_5849': 'Paesi non compresi nell’Allegato I della Convenzione sul clima (aggregato FAOSTAT)',
              'FAO_5873': 'Paesi OCSE (aggregato FAOSTAT)',
              'FAO_51010': 'Africa orientale, senza il commercio interno all’area (aggregato FAOSTAT)',
              'FAO_51020': 'Africa centrale, senza il commercio interno all’area (aggregato FAOSTAT)',
              'FAO_51030': 'Africa settentrionale, senza il commercio interno all’area (aggregato FAOSTAT)',
              'FAO_51040': 'Africa australe, senza il commercio interno all’area (aggregato FAOSTAT)',
              'FAO_613': 'Oceania, destinatari non specificati (aggregato FAOSTAT)',
              'FAO_620': 'Europa meridionale, destinatari non specificati (aggregato FAOSTAT)'}
UNITA_IT = {
    '1000 USD': 'migliaia di dollari USA', 't': 'tonnellate', 'mg/cap/d': 'mg per persona al giorno', 'm3': 'm³',
    'PT_POP_SEX_AGE': '% della popolazione dello stesso sesso ed età', 'PT_POP_SUB': '% del sottogruppo di popolazione',
    'g/cap/d': 'g per persona al giorno', 'kt': 'migliaia di tonnellate', 'μg/cap/d': 'µg per persona al giorno',
    'kg/ha': 'kg per ettaro', '1000 SLC': 'migliaia in valuta locale standard', 'million USD': 'milioni di dollari USA',
    'TJ': 'terajoule', '1000 Int$': 'migliaia di dollari internazionali', 't CO2eq/cap': 't di CO₂ equivalente per abitante',
    'LCU': 'valuta locale', 'kcal/cap/d': 'kcal per persona al giorno', 'million LCU': 'milioni in valuta locale',
    'million SLC': 'milioni in valuta locale standard', '%LSU': '% delle unità di bestiame adulto', 'LSU': 'unità di bestiame adulto',
    'LSU/ha': 'unità di bestiame adulto per ettaro', 'kg CO2eq/kg': 'kg di CO₂ equivalente per kg di prodotto', 'An': 'capi',
    'PS': 'persone', 't CO2eq/ha': 't di CO₂ equivalente per ettaro', 'kg CO2eq/Int$': 'kg di CO₂ equivalente per dollaro internazionale',
    'kg/cap': 'kg per persona', 'g/Int$': 'g per dollaro internazionale', 'PS_FTE': 'persone equivalenti a tempo pieno',
}
LOTTO_ARCHIVIO = {}  # lotto -> archivi presenti, per gli insiemi parziali (oggi nessuno)
BILATERALI = {(19, 'RFM'), (26, 'EA'), (31, 'TM')}
FONTE_LOTTO = {5: 'OCSE (Organizzazione per la cooperazione e lo sviluppo economico)'}
UNITA_IT.update({
    'ha': 'ettari', '100 g/An': 'ettogrammi per capo', 'hg/An': 'ettogrammi per capo', '100 g/ha': 'ettogrammi per ettaro',
    'kg/ha': 'kg per ettaro', '1000 No': 'migliaia di capi', 'No': 'numero', '1000 m3': 'migliaia di m³', 'kg/cap/yr': 'kg per persona all’anno',
    'g/cap/d': 'g per persona al giorno', '1000 t': 'migliaia di tonnellate', '1000 An': 'migliaia di capi', '1000 cap': 'migliaia di persone',
    '1000 persons': 'migliaia di persone', 'kcal/cap/d': 'kcal per persona al giorno', 'million USD': 'milioni di dollari USA',
    'kt': 'migliaia di tonnellate', 'Mt': 'milioni di tonnellate', 'g/cap/yr': 'g per persona all’anno', '': 'indice',
})


def _scrivi(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, separators=(',', ':'), ensure_ascii=False)


def _serie_annuale(per_terr, arrotonda, interi):
    anni = sorted({int(y) for t in per_terr.values() for y, v in t.items() if v[0] is not None})
    if not anni:
        return None
    y0, y1 = anni[0], anni[-1]
    dati = {}
    for c, t in per_terr.items():
        arr = [arrotonda(t.get(str(y), [None])[0], interi) for y in range(y0, y1 + 1)]
        if any(x is not None for x in arr):
            dati[c] = arr
    return y0, y1, dati


def _voce_eu(uscita, arrotonda, ident, per_terr, nome, unita, ds, en, agg, nome_ds, lotto, extra=None):
    """Scrive il file di un indicatore Eurostat (chiavi territoriali con prefisso EU:) e ne restituisce la voce di catalogo."""
    pt = {'EU:' + c: t for c, t in per_terr.items()}
    interi = all(float(v[0]).is_integer() for t in pt.values() for v in t.values() if v[0] is not None)
    y = _serie_annuale(pt, arrotonda, interi)
    if not y:
        return None
    y0, y1, dati = y
    _scrivi(os.path.join(uscita, 'eurostat', ident + '.json'), {'c': ident, 'y0': y0, 'y1': y1, 'd': dati})
    note = {}
    for c, t in pt.items():
        for anno, v in t.items():
            if v[1]:
                testo = ', '.join(STATI_EU.get(x, x) for x in v[1].strip())
                note.setdefault(c, {})[anno] = [testo, None]
    if note:
        _scrivi(os.path.join(uscita, 'note', ident + '.json'), note)
    voce = {'c': ident, 'fam': 'eu', 't': TEMA_EU, 'n': nome, 'u': unita, 'en': en,
            'def': f'Dataset Eurostat {ds}: {nome_ds}.', 'org': 'Eurostat',
            'agg': agg, 'url': f'https://ec.europa.eu/eurostat/databrowser/view/{ds}/default/table?lang=it',
            'y0': y0, 'y1': y1, 'righe': sum(len(t) for t in pt.values()),
            'valori': sum(1 for t in pt.values() for v in t.values() if v[0] is not None),
            'interi': interi, 'note': bool(note), 'lotto': lotto, 'ds': ds}
    if extra:
        voce.update(extra)
    return voce


def _territori_nuts(d_territori, uscita, territori):
    """Aggiunge ai territori i codici NUTS e gli aggregati non ancora presenti (nomi dalla fonte)."""
    geo = json.load(open(os.path.join(uscita, 'nuts.topo.json')))
    iso3 = {}
    geometrie = geo['objects'][next(iter(geo['objects']))]['geometries']
    for g in geometrie:
        p = g['properties']
        if p['l'] == 0:
            iso3[p['id']] = p['c']
    iso3.update(ISO3_EXTRA)
    per_id = {t['id']: t for t in territori}
    con_geo = {g['properties']['id'] for g in geometrie}
    for cod, nome in sorted(d_territori.items()):
        if 'EU:' + cod in per_id:
            continue
        paese = iso3.get(cod[:2])
        if not re.match(r'^[A-Z]{2}[0-9A-Z]{0,3}$', cod) or not paese:
            voce = {'id': 'EU:' + cod, 'n': AGG_EU_IT.get(cod, nome), 'en': nome, 'k': 'agg_eu', 'cod': cod}
        else:
            l = len(cod) - 2
            base = per_id.get(paese)
            voce = {'id': 'EU:' + cod, 'n': base['n'] if (l == 0 and base) else nome, 'en': nome, 'k': 'nuts', 'l': l,
                    'p': paese, 'cod': cod, 'r': base.get('r') if base else None, 'g': cod in con_geo}
        territori.append(voce)
        per_id[voce['id']] = voce


# indicatori Eurostat che la fonte stessa presenta come proiezioni o stime modellate
STIME_EU = {'EU_PRJ_': 'Proiezione di Eurostat, non un dato osservato: lo scenario è indicato nella selezione.',
            'EU_AMB_EROSIONE': 'Stima modellata (Eurostat la presenta come “estimated”), non una misurazione.'}


def eurostat_api(percorso, uscita, territori, arrotonda, lotto='api'):
    """Indicatori regionali nel formato intermedio di estrai_eurostat_api.py (Eurostat) o estrai_regio.py (Commissione europea,
    DG REGIO); restituisce (indicatori, data di scarico). Le voci possono portare 'org', 'url', 'def', 'calc' e 'stima' propri."""
    d = json.load(open(percorso))
    _territori_nuts(d['territori'], uscita, territori)
    indicatori = []
    for voce in d['indicatori']:
        titolo = voce.get('titolo', voce['ds'])
        extra = {'def': voce.get('def') or f"Dataset Eurostat {voce['ds']}: {titolo}. Selezione: {voce.get('sel', '')}.",
                 'sel': voce.get('sel', '')}
        for k in ('org', 'url', 'calc', 'stima'):
            if voce.get(k):
                extra[k] = voce[k]
        for prefisso, testo in STIME_EU.items():
            if voce['c'].startswith(prefisso) and 'stima' not in extra:
                extra['stima'] = testo
        v = _voce_eu(uscita, arrotonda, voce['c'], d['serie'].get(voce['c'], {}), voce['n'], voce['u'], voce['ds'], voce['en'],
                     (d['agg'].get(voce['ds']) or '')[:10], titolo, lotto, extra)
        if v:
            indicatori.append(v)
    return indicatori, d.get('scaricato', '')


def eurostat(percorso, uscita, territori, arrotonda):
    """Aggiunge territori NUTS e indicatori Eurostat; restituisce l'elenco degli indicatori."""
    d = json.load(open(percorso))
    geo = json.load(open(os.path.join(uscita, 'nuts.topo.json')))
    iso3 = {}
    for g in geo['objects'][next(iter(geo['objects']))]['geometries']:
        p = g['properties']
        if p['l'] == 0:
            iso3[p['id']] = p['c']
    iso3.update(ISO3_EXTRA)
    per_id = {t['id']: t for t in territori}
    con_geo = {g['properties']['id'] for g in geo['objects'][next(iter(geo['objects']))]['geometries']}
    for cod, (nome, liv) in sorted(d['territori'].items()):
        paese = iso3.get(cod[:2])
        if liv == 'Aggregato' or not re.match(r'^[A-Z]{2}[0-9A-Z]{0,3}$', cod) or not paese:
            territori.append({'id': 'EU:' + cod, 'n': AGG_EU_IT.get(cod, nome), 'en': nome, 'k': 'agg_eu', 'cod': cod})
            continue
        l = len(cod) - 2
        base = per_id.get(paese)
        n_it = base['n'] if (l == 0 and base) else nome
        territori.append({'id': 'EU:' + cod, 'n': n_it, 'en': nome, 'k': 'nuts', 'l': l, 'p': paese, 'cod': cod,
                          'r': base.get('r') if base else None, 'g': cod in con_geo})

    def scrivi(ident, per_terr, nome, unita, ds, en, extra=None):
        nome_ds, lotto = DATASET_EU[ds]
        return _voce_eu(uscita, arrotonda, ident, per_terr, nome, unita, ds, en, (d['agg'].get(ds) or '')[:10], nome_ds, lotto, extra)

    indicatori = []
    S = d['serie']
    for chiave, per_terr in S.items():
        parti = chiave.split('|')
        ds = parti[0]
        if ds == 'demo_r_d3dens':
            v = scrivi('EU_DENS', per_terr, 'Densità di popolazione, regioni europee', 'abitanti per km²', ds, 'Population density')
        elif ds == 'demo_r_pjanaggr3':
            sesso, eta = parti[2], parti[3]
            pezzi = ['Popolazione al 1° gennaio'] + [x for x in (ETA[eta], SESSO[sesso]) if x]
            v = scrivi(f'EU_POP_{sesso}_{eta.replace("-", "")}', per_terr, ', '.join(pezzi), 'persone', ds,
                       f'Population on 1 January, sex {sesso}, age {eta}')
        elif ds == 'demo_r_births':
            v = scrivi('EU_NATI', per_terr, 'Nati vivi', 'nati nell’anno', ds, 'Live births')
        elif ds == 'demo_r_deaths':
            v = scrivi('EU_MORTI', per_terr, 'Decessi', 'decessi nell’anno', ds, 'Deaths')
        elif ds == 'demo_r_find3':
            n, u, en = FIND3[parti[4]]
            v = scrivi('EU_' + parti[4], per_terr, n, u, ds, en)
        else:
            continue
        if v:
            indicatori.append(v)

    # Quote per età calcolate dall'Atlante: stessa fonte, stesso territorio, stesso anno
    tot = S['demo_r_pjanaggr3|NR|T|TOTAL']
    for eta, nome in (('Y_LT15', 'sotto i 15 anni'), ('Y15-64', 'da 15 a 64 anni'), ('Y_GE65', 'di 65 anni e oltre')):
        num = S[f'demo_r_pjanaggr3|NR|T|{eta}']
        quota = {}
        for c, t in num.items():
            for anno, v in t.items():
                den = tot.get(c, {}).get(anno)
                if v[0] is not None and den and den[0]:
                    quota.setdefault(c, {})[anno] = [round(100 * v[0] / den[0], 4), None]
        v = scrivi(f'EU_QUOTA_{eta.replace("-", "")}', quota, f'Quota di popolazione {nome}', '% della popolazione al 1° gennaio',
                   'demo_r_pjanaggr3', f'Share of population, age {eta} (computed)',
                   {'calc': f'Calcolato dall’Atlante: popolazione {nome} divisa per popolazione totale, stesso territorio e stesso anno, per 100.'})
        if v:
            indicatori.append(v)
    return indicatori, NOME_TEMA_EU


def insiemi(cartella, uscita, territori, arrotonda):
    """Insiemi di dati completi o parziali estratti dai lotti (estrai_lotti.py): per ogni dataset un indice delle serie
    (dati/archivi/<f>.json) e un file compresso per serie (dati/archivi/<f>/<k>.json.gz). Restituisce il catalogo."""
    per_id = {t['id']: t for t in territori}
    catalogo, esclusi = [], []
    for percorso in sorted(glob.glob(os.path.join(cartella, 'L*.json'))):
        ds = json.load(open(percorso, encoding='utf-8'))
        lotto, codice, fonte = ds['lotto'], ds['ds'], ds['fonte']
        if (lotto, codice) in BILATERALI:  # matrici bilaterali: vista Partner (estrai_partner.py, genera_partner.py)
            continue
        n_serie = len(ds['ind'])
        n_oss = sum(len(t) for x in ds['ind'].values() for t in x['s'].values())
        # insiemi organizzati per indagine o per censimento, con una sola osservazione per serie: non sono serie annuali
        if n_serie and (n_oss / n_serie < 2 or n_serie > 50000):
            esclusi.append({'lotto': lotto, 'cod': codice, 'n': DATASET_IT.get(codice, ds['n']), 'en': ds['n'], 'fonte': FONTE_IT.get(fonte, fonte),
                            'serie': n_serie, 'righe': n_oss, 'motivo': 'organizzato per indagine o censimento, con una sola osservazione per serie: non rappresentabile come serie annuale'})
            print(f'L{lotto:02d}_{codice}: escluso ({n_serie} serie, {n_oss} osservazioni)', flush=True)
            continue
        terr, aggr = {}, []
        for c, info in ds['terr'].items():
            e_agg = bool(info.get('agg'))
            if c not in per_id:
                nuovo = {'id': c, 'n': STORICI_IT.get(c, AGG_FONTI_IT.get(c, info['n'])), 'en': info['n'], 'k': 'aggf' if e_agg else 'storico'}
                territori.append(nuovo)
                per_id[c] = nuovo
            if e_agg or per_id[c]['k'] in ('agg', 'aggf'):
                aggr.append(c)
            terr[c] = info['n']
        # etichette ripetute dentro lo stesso insieme: si distinguono con i codici delle dimensioni
        conta = {}
        for ind in ds['ind'].values():
            conta[(ind['n'], ind['u'])] = conta.get((ind['n'], ind['u']), 0) + 1
        serie = []
        for chiave, ind in ds['ind'].items():
            pt = ind['s']
            interi = all(float(v[0]).is_integer() for t in pt.values() for v in t.values() if v[0] is not None)
            y = _serie_annuale(pt, arrotonda, interi)
            if not y:
                continue
            y0, y1, dati = y
            flag = {}
            for c, t in pt.items():
                for anno, v in t.items():
                    if v[1]:
                        flag.setdefault(c, {})[str(anno)] = v[1]
            etich = ind['n'] or codice
            if conta[(ind['n'], ind['u'])] > 1:
                codici = ', '.join(f'{k} {v}' for k, v in ind['dims'].items() if k != 'Unit' and 'Code' in k or k in ('Indicator',))
                etich = f"{etich} [{codici}]" if codici else etich
            unita = UNITA_IT.get(ind['u'], ind['u']) if ind['u'] else ('indice (2014-2016 = 100)' if codice == 'QI' else 'unità nella descrizione')
            serie.append({'l': etich, 'u': unita, 'uo': ind['u'] or '', 'y0': y0, 'y1': y1, 'i': interi,
                          'n': len(dati), 'cod': ind.get('cod', codice), 'dims': ind['dims'], 'd': dati, 'fl': flag})
        if not serie:
            continue
        serie.sort(key=lambda x: (x['l'], x['u']))
        nome_file = f'L{lotto:02d}_{re.sub(r"[^A-Za-z0-9]+", "_", codice)}'
        cart = os.path.join(uscita, 'archivi', nome_file)
        os.makedirs(cart, exist_ok=True)
        byte = 0
        indice = []
        for k, x in enumerate(serie):
            corpo = {'c': f'A:{nome_file}:{k}', 'y0': x['y0'], 'y1': x['y1'], 'd': x['d']}
            if x['fl']:
                corpo['f'] = x['fl']
            testo = json.dumps(corpo, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
            with open(os.path.join(cart, f'{k}.json.gz'), 'wb') as fh:
                with gzip.GzipFile(fileobj=fh, mode='wb', mtime=0, compresslevel=9) as gz:
                    gz.write(testo)
            byte += os.path.getsize(os.path.join(cart, f'{k}.json.gz'))
            indice.append({'l': x['l'], 'u': x['u'], 'uo': x['uo'], 'y0': x['y0'], 'y1': x['y1'], 'i': x['i'], 'n': x['n'], 'cod': x['cod'],
                           'dims': {kk: vv for kk, vv in x['dims'].items() if kk != 'Unit'}})
        _scrivi(os.path.join(uscita, 'archivi', nome_file + '.json'), {'s': indice})
        catalogo.append({
            'mb': round(byte / 1e6, 1), 'f': nome_file, 'lotto': lotto, 'cod': codice, 'n': DATASET_IT.get(codice, ds['n']), 'en': ds['n'],
            'fonte': FONTE_IT.get(fonte, fonte), 'src': fonte, 'archivio': LOTTO_ARCHIVIO.get(lotto, ''), 'url': ds['url'], 'agg': (ds['agg'] or '')[:10],
            'terr': sorted(terr), 'aggr': sorted(aggr), 'serie': len(serie), 'righe': sum(len(t) for x in ds['ind'].values() for t in x['s'].values()),
            'y0': min(x['y0'] for x in serie), 'y1': max(x['y1'] for x in serie),
        })
        print(f"{nome_file}: {len(serie)} serie, {len(terr)} territori, {byte / 1e6:.1f} MB", flush=True)
    catalogo.sort(key=lambda a: (a['lotto'], a['cod']))
    return catalogo, esclusi


# Indicatori in evidenza per i profili dei territori e la prima pagina
FLAG_WB = ['SP.POP.TOTL', 'SP.DYN.LE00.IN', 'SP.DYN.TFRT.IN', 'SP.POP.65UP.TO.ZS', 'SH.DYN.MORT', 'SP.URB.TOTL.IN.ZS',
           'EN.POP.DNST', 'IT.NET.USER.ZS', 'EG.ELC.ACCS.ZS', 'EG.FEC.RNEW.ZS', 'EN.GHG.ALL.PC.CE.AR5', 'EN.ATM.PM25.MC.M3',
           'AG.LND.FRST.ZS', 'SE.TER.ENRR', 'SH.MED.PHYS.ZS', 'SH.H2O.SMDW.ZS', 'SE.ADT.LITR.ZS', 'AG.LND.AGRI.ZS']
FLAG_EU = ['EU_POP_T_TOTAL', 'EU_DENS', 'EU_QUOTA_Y_GE65', 'EU_STR_ETAMEDIANA', 'EU_NATI', 'EU_MORTI', 'EU_TOTFERRT', 'EU_DIN_MIGRATORIO',
           'EU_ECO_PIL_AB', 'EU_ECO_PIL_UE', 'EU_ECO_REDDITO', 'EU_LAV_OCC2064', 'EU_LAV_DIS', 'EU_LAV_NEET', 'EU_IST_LAUREATI',
           'EU_SAL_VITA', 'EU_SOC_POVESCL', 'EU_DIG_QUOTID', 'EU_TUR_NOTTI', 'EU_TRA_MORTI', 'EU_RIC_SPESA', 'EU_IMP_ATTIVE',
           'EU_RCI_TOT', 'EU_SPI24_TOT', 'EU_EQI_TOT', 'EU_CLI_GHG_AB']
SPARK_ANNI = 30


def _ultimo(d, tid):
    a = d['d'].get(tid)
    if not a:
        return None
    for i in range(len(a) - 1, -1, -1):
        if a[i] is not None:
            return d['y0'] + i, a[i]
    return None


def _in(d, tid, y):
    a = d['d'].get(tid)
    i = y - d['y0']
    return a[i] if a and 0 <= i < len(a) else None


def _spark(d, tid, sig=4):
    a = d['d'].get(tid)
    if not a:
        return None
    u = _ultimo(d, tid)
    if not u:
        return None
    fine = u[0] - d['y0']
    inizio = max(0, fine - SPARK_ANNI + 1)
    vals = [None if v is None else float(f'{v:.{sig}g}') for v in a[inizio:fine + 1]]
    vals = [int(v) if v is not None and v == int(v) and abs(v) < 1e15 else v for v in vals]
    return [d['y0'] + inizio, vals]


def _posizione(d, tid, y, ids):
    vals = [(_in(d, t, y), t) for t in ids]
    vals = [(v, t) for v, t in vals if v is not None]
    if not any(t == tid for _, t in vals):
        return None
    vals.sort(key=lambda x: -x[0])
    return [next(i for i, (_, t) in enumerate(vals) if t == tid) + 1, len(vals)]


def sintesi(uscita, indicatori, territori):
    """Scrive panoramica.json (Italia, mondo, Unione europea e FVG per ogni indicatore) e i profili per territorio."""
    paesi = [t['id'] for t in territori if t['k'] == 'paese']
    nuts = {}
    for t in territori:
        if t['k'] == 'nuts':
            nuts.setdefault(t['l'], []).append(t['id'])
    pano = {}
    cache = {}

    def leggi(i):
        if i['c'] not in cache:
            cart = 'eurostat' if i['fam'] == 'eu' else 'indicatori'
            cache[i['c']] = json.load(open(os.path.join(uscita, cart, i['c'] + '.json')))
        return cache[i['c']]

    for i in indicatori:
        if i['fam'] not in ('wb', 'eu'):
            continue
        d = leggi(i)
        if i['fam'] == 'eu':
            f = _ultimo(d, 'EU:ITH4')
            pano[i['c']] = {'fvg': f, 'it': _ultimo(d, 'EU:IT'), 'eu': _ultimo(d, 'EU:EU27_2020'),
                            'pos': _posizione(d, 'EU:ITH4', f[0], nuts.get(2, [])) if f else None,
                            'sp': _spark(d, 'EU:ITH4'), 'spw': _spark(d, 'EU:IT')}
        else:
            it = _ultimo(d, 'ITA')
            pano[i['c']] = {'it': it, 'wld': _ultimo(d, 'WLD'), 'eu': _ultimo(d, 'EUU'),
                            'pos': _posizione(d, 'ITA', it[0], paesi) if it else None,
                            'sp': _spark(d, 'ITA'), 'spw': _spark(d, 'WLD')}
    _scrivi(os.path.join(uscita, 'panoramica.json'), {'ind': pano})

    # profili dei paesi e degli aggregati
    flag = [i for i in indicatori if i['c'] in FLAG_WB]
    flag.sort(key=lambda i: FLAG_WB.index(i['c']))
    for t in territori:
        if t['k'] not in ('paese', 'agg'):
            continue
        prof = {}
        for i in flag:
            d = leggi(i)
            u = _ultimo(d, t['id'])
            if not u:
                continue
            pos = _posizione(d, t['id'], u[0], paesi) if t['k'] == 'paese' else None
            sp = _spark(d, t['id'])
            prof[i['c']] = [u[0], u[1], pos[0] if pos else None, pos[1] if pos else None, sp[0], sp[1]]
        _scrivi(os.path.join(uscita, 'profili', t['id'] + '.json'), {'id': t['id'], 'ind': prof})

    # profili delle regioni europee, un file per paese
    flag_eu = [i for i in indicatori if i['c'] in FLAG_EU]
    flag_eu.sort(key=lambda i: FLAG_EU.index(i['c']))
    per_paese = {}
    for t in territori:
        if t['k'] == 'nuts':
            per_paese.setdefault(t['p'], []).append(t)
    for p, elenco in per_paese.items():
        out = {}
        for t in elenco:
            prof = {}
            for i in flag_eu:
                d = leggi(i)
                u = _ultimo(d, t['id'])
                if not u:
                    continue
                pos = _posizione(d, t['id'], u[0], nuts.get(t['l'], []))
                sp = _spark(d, t['id'])
                prof[i['c']] = [u[0], u[1], pos[0] if pos else None, pos[1] if pos else None, sp[0], sp[1]]
            out[t['id']] = prof
        _scrivi(os.path.join(uscita, 'profili', 'nuts_' + p + '.json'), out)
    return len(pano)
