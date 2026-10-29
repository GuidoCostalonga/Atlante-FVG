"""Indici e serie regionali della Commissione europea (DG REGIO), piattaforma aperta cohesiondata.ec.europa.eu,
individuati con la ricerca su data.europa.eu (catalogo "esif").

Uso:
  python3 estrai_regio.py <cartella con i CSV e le schede JSON> <uscita.json> [--scarica]

Con --scarica i file mancanti vengono scaricati nella cartella: <id>.csv (tutte le righe) e <id>.json (scheda del dataset).
Il JSON di uscita ha lo stesso formato di estrai_eurostat_api.py ed è letto da genera_dati.py con --regio.
Ogni voce porta organizzazione, indirizzo del dataset e definizione; le voci calcolate dall'Atlante hanno il campo 'calc',
quelle che la fonte stessa dichiara stimate o modellate hanno il campo 'stima'.
"""
import csv, datetime, json, os, re, subprocess, sys

BASE = 'https://cohesiondata.ec.europa.eu'
ORG = 'Commissione europea, DG REGIO (cohesiondata)'
GEO_ALIAS = {'EU27': 'EU27_2020', 'EU-27': 'EU27_2020'}
SCARTA = {'UKZZ'}
UE100 = 'punteggio (media UE = 100)'
P0100 = 'punteggio da 0 a 100'
STD = 'punteggio standardizzato (media europea = 0)'
EURO = 'euro (prezzi correnti)'

DESCR = {
    'ngxn-bw8m': 'Indice di competitività regionale RCI 2.0 della Commissione europea (DG REGIO): misura con oltre 70 indicatori la capacità di una regione di offrire un ambiente attraente e sostenibile a imprese e residenti. Punteggi relativi alla media dell’Unione europea (= 100), ricalcolati con la stessa metodologia per le edizioni 2016, 2019 e 2022; per sette capitali la regione è unita al suo bacino di pendolarismo.',
    '5nmd-5kax': 'Indice di progresso sociale regionale EU-SPI 2024 della Commissione europea: 53 indicatori sociali e ambientali in 12 componenti e 3 dimensioni (bisogni fondamentali, fondamenti del benessere, opportunità), senza grandezze economiche. Punteggi relativi alla media dell’Unione europea (= 100).',
    '99vh-w4e7': 'Indice di progresso sociale regionale EU-SPI, edizione 2020: 55 indicatori in 12 componenti e 3 dimensioni, punteggi da 0 a 100. Non confrontabile con l’edizione 2024, che usa un’altra scala.',
    'eqnk-pu8x': 'Indice europeo di qualità delle istituzioni EQI (Quality of Government Institute dell’Università di Göteborg per la Commissione europea): percezioni ed esperienze dei cittadini su corruzione, qualità e imparzialità di sanità, istruzione e polizia nella regione di residenza; indagini 2010, 2013, 2017, 2021 e 2024 (oltre 135.000 intervistati nel 2024). Punteggi standardizzati con media europea 0: valori più alti indicano qualità migliore.',
    'q6y9-dn7j': 'Monitor regionale di genere 2021 della Commissione europea: indice di realizzazione femminile (FemAI, quanto le donne ottengono in termini assoluti) e indice di svantaggio femminile (FemDI, divario rispetto agli uomini) in sette ambiti: lavoro, conoscenza, tempo, potere, salute, sicurezza, soddisfazione di vita. Punteggi da 0 a 100, edizione 2021.',
    '4bvr-jq77': 'Emissioni di gas serra per abitante nelle regioni europee, stima del Centro comune di ricerca (JRC) basata sulla banca dati EDGAR e sui dati ARDECO di popolazione: energia, industria, edifici, trasporti, agricoltura e rifiuti, escluse navigazione e aviazione. Valori modellati, non misurati.',
    'krps-v2iz': 'Intensità carbonica dell’economia regionale (gas serra per 1.000 euro di PIL), stima del Centro comune di ricerca (JRC) basata su EDGAR e ARDECO, escluse navigazione e aviazione. Valori modellati, non misurati.',
    'tc55-7ysv': 'Pagamenti annuali dell’Unione europea alle regioni (NUTS 2) per i fondi a gestione concorrente, in euro a prezzi correnti, ricostruiti dalla Commissione europea (DG REGIO) dal 1989 al 2022; la ripartizione regionale segue i programmi o regole di riparto. Quando in uno stesso anno si sovrappongono due periodi di programmazione i pagamenti sono sommati.',
    'dau5-jiss': 'Produzione attuale e potenziale non sfruttato di energia rinnovabile da sole e vento nelle province europee (NUTS 3), stima del Centro comune di ricerca (JRC) pubblicata nel 2024: la produzione è riferita al 2019, il potenziale è calcolato sul territorio disponibile. Nell’Atlante tutti i valori sono collocati sull’anno 2019.',
}

RCI = {
    'RCI 2.0 - 2016': ('EU_RCI_TOT', 'Indice di competitività regionale (RCI 2.0)', 'Regional Competitiveness Index 2.0'),
    'RCI 2.0 - 2019': ('EU_RCI_TOT', None, None), 'RCI 2.0 - 2022': ('EU_RCI_TOT', None, None),
    'BASIC SUB-INDEX': ('EU_RCI_BASE', 'RCI 2.0: sottoindice di base (istituzioni, stabilità macroeconomica, infrastrutture, salute, istruzione di base)', 'RCI 2.0, basic sub-index'),
    'EFFICIENCY SUB-INDEX': ('EU_RCI_EFFICIENZA', 'RCI 2.0: sottoindice di efficienza (istruzione superiore, mercato del lavoro, dimensione del mercato)', 'RCI 2.0, efficiency sub-index'),
    'INNOVATION SUB-INDEX': ('EU_RCI_INNOVAZIONE', 'RCI 2.0: sottoindice di innovazione (prontezza tecnologica, maturità delle imprese, innovazione)', 'RCI 2.0, innovation sub-index'),
    'Institutions': ('EU_RCI_ISTITUZIONI', 'RCI 2.0: pilastro istituzioni', 'RCI 2.0, institutions'),
    'Macroeconomic': ('EU_RCI_MACRO', 'RCI 2.0: pilastro stabilità macroeconomica', 'RCI 2.0, macroeconomic stability'),
    'Infrastructure': ('EU_RCI_INFRASTRUTTURE', 'RCI 2.0: pilastro infrastrutture', 'RCI 2.0, infrastructure'),
    'Health': ('EU_RCI_SALUTE', 'RCI 2.0: pilastro salute', 'RCI 2.0, health'),
    'Basic education': ('EU_RCI_ISTRUZIONE_BASE', 'RCI 2.0: pilastro istruzione di base', 'RCI 2.0, basic education'),
    'Higher education and LLL': ('EU_RCI_ISTRUZIONE_SUP', 'RCI 2.0: pilastro istruzione superiore e apprendimento permanente', 'RCI 2.0, higher education and lifelong learning'),
    'Labour market': ('EU_RCI_LAVORO', 'RCI 2.0: pilastro efficienza del mercato del lavoro', 'RCI 2.0, labour market efficiency'),
    'Market size': ('EU_RCI_MERCATO', 'RCI 2.0: pilastro dimensione del mercato', 'RCI 2.0, market size'),
    'Technological readiness': ('EU_RCI_TECNOLOGIA', 'RCI 2.0: pilastro prontezza tecnologica', 'RCI 2.0, technological readiness'),
    'Business sophistication': ('EU_RCI_IMPRESE', 'RCI 2.0: pilastro maturità delle imprese', 'RCI 2.0, business sophistication'),
    'Innovation': ('EU_RCI_INNOV', 'RCI 2.0: pilastro innovazione', 'RCI 2.0, innovation'),
}
SPI24 = {
    'EU-SPI': ('EU_SPI24_TOT', 'Indice di progresso sociale regionale (EU-SPI 2024)', 'EU regional Social Progress Index 2024'),
    'BASIC NEEDS': ('EU_SPI24_BISOGNI', 'EU-SPI 2024: dimensione bisogni fondamentali', 'EU-SPI 2024, basic needs'),
    'FOUNDATIONS OF WELLBEING': ('EU_SPI24_BENESSERE', 'EU-SPI 2024: dimensione fondamenti del benessere', 'EU-SPI 2024, foundations of wellbeing'),
    'OPPORTUNITY': ('EU_SPI24_OPPORTUNITA', 'EU-SPI 2024: dimensione opportunità', 'EU-SPI 2024, opportunity'),
    'Nutrition and medical care': ('EU_SPI24_NUTRIZIONE', 'EU-SPI 2024: nutrizione e cure mediche', 'EU-SPI 2024, nutrition and medical care'),
    'Water and sanitation': ('EU_SPI24_ACQUA', 'EU-SPI 2024: acqua e servizi igienici', 'EU-SPI 2024, water and sanitation'),
    'Housing': ('EU_SPI24_CASA', 'EU-SPI 2024: abitazione', 'EU-SPI 2024, housing'),
    'Safety': ('EU_SPI24_SICUREZZA', 'EU-SPI 2024: sicurezza personale', 'EU-SPI 2024, safety'),
    'Basic education': ('EU_SPI24_ISTRUZIONE_BASE', 'EU-SPI 2024: istruzione di base', 'EU-SPI 2024, basic education'),
    'Information and communications': ('EU_SPI24_INFORMAZIONE', 'EU-SPI 2024: informazione e comunicazione', 'EU-SPI 2024, information and communications'),
    'Health': ('EU_SPI24_SALUTE', 'EU-SPI 2024: salute', 'EU-SPI 2024, health'),
    'Environmental quality': ('EU_SPI24_AMBIENTE', 'EU-SPI 2024: qualità ambientale', 'EU-SPI 2024, environmental quality'),
    'Freedom and choice': ('EU_SPI24_LIBERTA', 'EU-SPI 2024: libertà e scelta personale', 'EU-SPI 2024, freedom and choice'),
    'Trust and governance': ('EU_SPI24_FIDUCIA', 'EU-SPI 2024: fiducia e qualità del governo', 'EU-SPI 2024, trust and governance'),
    'Inclusive society': ('EU_SPI24_INCLUSIONE', 'EU-SPI 2024: società inclusiva', 'EU-SPI 2024, inclusive society'),
    'Advanced education': ('EU_SPI24_ISTRUZIONE_SUP', 'EU-SPI 2024: istruzione avanzata', 'EU-SPI 2024, advanced education'),
}
SPI20 = {
    'EU SOCIAL PROGRESS INDEX': ('EU_SPI20_TOT', 'Indice di progresso sociale regionale, edizione 2020 (scala da 0 a 100)', 'EU Social Progress Index 2020'),
    'BASIC SUB-INDEX': ('EU_SPI20_BISOGNI', 'EU-SPI 2020: dimensione bisogni fondamentali', 'EU-SPI 2020, basic human needs'),
    'FOUNDATION SUB-INDEX': ('EU_SPI20_BENESSERE', 'EU-SPI 2020: dimensione fondamenti del benessere', 'EU-SPI 2020, foundations of wellbeing'),
    'OPPORTUNITY SUB-INDEX': ('EU_SPI20_OPPORTUNITA', 'EU-SPI 2020: dimensione opportunità', 'EU-SPI 2020, opportunity'),
    'Nutrition and Care': ('EU_SPI20_NUTRIZIONE', 'EU-SPI 2020: nutrizione e cure mediche di base', 'EU-SPI 2020, nutrition and basic medical care'),
    'Water and Sanitation': ('EU_SPI20_ACQUA', 'EU-SPI 2020: acqua e servizi igienici', 'EU-SPI 2020, water and sanitation'),
    'Shelter': ('EU_SPI20_CASA', 'EU-SPI 2020: abitazione', 'EU-SPI 2020, shelter'),
    'Personal Security': ('EU_SPI20_SICUREZZA', 'EU-SPI 2020: sicurezza personale', 'EU-SPI 2020, personal security'),
    'Basic Knowledge': ('EU_SPI20_ISTRUZIONE_BASE', 'EU-SPI 2020: conoscenze di base', 'EU-SPI 2020, access to basic knowledge'),
    'ICT Access': ('EU_SPI20_INFORMAZIONE', 'EU-SPI 2020: accesso alle tecnologie dell’informazione e della comunicazione', 'EU-SPI 2020, access to ICT'),
    'Health and Wellness': ('EU_SPI20_SALUTE', 'EU-SPI 2020: salute e benessere', 'EU-SPI 2020, health and wellness'),
    'Environmental Quality': ('EU_SPI20_AMBIENTE', 'EU-SPI 2020: qualità ambientale', 'EU-SPI 2020, environmental quality'),
    'Personal Rights': ('EU_SPI20_DIRITTI', 'EU-SPI 2020: diritti personali', 'EU-SPI 2020, personal rights'),
    'Personal Freedom and Choice': ('EU_SPI20_LIBERTA', 'EU-SPI 2020: libertà e scelta personale', 'EU-SPI 2020, personal freedom and choice'),
    'Tolerance Inclusion': ('EU_SPI20_INCLUSIONE', 'EU-SPI 2020: tolleranza e inclusione', 'EU-SPI 2020, tolerance and inclusion'),
    'Advanced Education': ('EU_SPI20_ISTRUZIONE_SUP', 'EU-SPI 2020: istruzione avanzata', 'EU-SPI 2020, access to advanced education'),
}
EQI = {
    'EQI': ('EU_EQI_TOT', 'Indice europeo di qualità delle istituzioni (EQI)', 'European Quality of Government Index'),
    'Quality': ('EU_EQI_QUALITA', 'EQI: qualità dei servizi pubblici (sanità, istruzione, polizia)', 'EQI, quality pillar'),
    'Impartiality': ('EU_EQI_IMPARZIALITA', 'EQI: imparzialità dei servizi pubblici', 'EQI, impartiality pillar'),
    'Corruption': ('EU_EQI_CORRUZIONE', 'EQI: pilastro corruzione (valori più alti indicano minore corruzione percepita)', 'EQI, corruption pillar'),
}
GENERE = [('index_score', '', 'indice complessivo', 'index score'), ('work', '_LAVORO', 'ambito lavoro', 'work'),
          ('knowledge', '_CONOSCENZA', 'ambito conoscenza', 'knowledge'), ('time', '_TEMPO', 'ambito tempo', 'time'),
          ('power', '_POTERE', 'ambito potere', 'power'), ('health', '_SALUTE', 'ambito salute', 'health'),
          ('safety', '_SICUREZZA', 'ambito sicurezza', 'safety'), ('life_satisf', '_SODDISFAZIONE', 'ambito soddisfazione di vita', 'life satisfaction')]
INDICI_GENERE = {'FemAI': ('EU_GEN_FEMAI', 'Indice di realizzazione femminile (FemAI, monitor regionale di genere 2021)', 'Female Achievement Index'),
                 'FemDI': ('EU_GEN_FEMDI', 'Indice di svantaggio femminile (FemDI, monitor regionale di genere 2021)', 'Female Disadvantage Index')}
FONDI = {
    'ERDF': ('EU_FON_FESR', 'Pagamenti UE del FESR (Fondo europeo di sviluppo regionale) alla regione', 'EU payments, ERDF'),
    'CF': ('EU_FON_FC', 'Pagamenti UE del Fondo di coesione alla regione', 'EU payments, Cohesion Fund'),
    'ESF': ('EU_FON_FSE', 'Pagamenti UE del FSE (Fondo sociale europeo) alla regione', 'EU payments, ESF'),
    'EAFRD': ('EU_FON_FEASR', 'Pagamenti UE del FEASR (Fondo europeo agricolo per lo sviluppo rurale, in passato FEAOG) alla regione', 'EU payments, EAFRD/EAGGF'),
    'EMFF': ('EU_FON_FEAMP', 'Pagamenti UE del FEAMP (Fondo europeo per gli affari marittimi e la pesca) alla regione', 'EU payments, EMFF'),
    'YEI': ('EU_FON_IOG', 'Pagamenti UE dell’IOG (Iniziativa a favore dell’occupazione giovanile) alla regione', 'EU payments, YEI'),
    'FEAD': ('EU_FON_FEAD', 'Pagamenti UE del FEAD (Fondo di aiuti europei agli indigenti) alla regione', 'EU payments, FEAD'),
}
RINNOVABILI = [
    ('total_current_production', 'EU_ENE_RINN_PROD', 'Produzione di energia rinnovabile da sole e vento, 2019 (stima JRC)', 'terawattora', 'Current renewable production from solar and wind, 2019'),
    ('total_technical_potential', 'EU_ENE_RINN_POT', 'Potenziale tecnico di energia rinnovabile da sole e vento (stima JRC)', 'terawattora', 'Total technical potential of solar and wind'),
    ('total_untapped_potential', 'EU_ENE_RINN_INUT', 'Potenziale di energia rinnovabile da sole e vento non ancora sfruttato (stima JRC)', 'terawattora', 'Total untapped potential of solar and wind'),
    ('total_untapped_potential_1', 'EU_ENE_RINN_INUT_KM2', 'Potenziale rinnovabile non sfruttato per km² (stima JRC)', 'megawattora per km²', 'Untapped potential per km²'),
    ('total_current_production_1', 'EU_ENE_RINN_PROD_KM2', 'Produzione di energia rinnovabile da sole e vento per km², 2019 (stima JRC)', 'megawattora per km²', 'Current production per km²'),
]
NOMI = {'ngxn-bw8m': 'nuts_name', '5nmd-5kax': 'region_name', '99vh-w4e7': 'region_name', 'eqnk-pu8x': 'region_name',
        'q6y9-dn7j': 'unit_name', '4bvr-jq77': 'name', 'krps-v2iz': 'name', 'tc55-7ysv': 'nuts2_name', 'dau5-jiss': 'name_of_the_region'}


def scarica(url, dest):
    subprocess.run(['curl', '-sS', '-L', '--retry', '3', '-o', dest, url], check=True)


def leggi(cartella, ds):
    with open(os.path.join(cartella, ds + '.csv'), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def scheda(cartella, ds):
    f = os.path.join(cartella, ds + '.json')
    if not os.path.exists(f):
        return ds, ''
    m = json.load(open(f, encoding='utf-8'))
    agg = m.get('rowsUpdatedAt')
    data = datetime.datetime.fromtimestamp(agg, datetime.timezone.utc).date().isoformat() if agg else ''
    return m.get('name', ds), data


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def anno(x):
    v = num(x)
    return str(int(v)) if v is not None and 1000 <= v <= 2999 else None


def geo_ok(cod):
    cod = GEO_ALIAS.get(cod, cod)
    if cod in SCARTA:
        return None
    if re.match(r'^[A-Z]{2}[0-9A-Z]{0,3}$', cod) or cod.endswith('_C') or cod == 'EU27_2020':
        return cod
    return None


class Raccolta:
    def __init__(self):
        self.serie, self.indicatori, self.territori, self.agg, self.titoli = {}, [], {}, {}, {}

    def voce(self, cod, ds, nome, unita, en, sel, extra=None):
        if any(i['c'] == cod for i in self.indicatori):
            return
        titolo = self.titoli[ds]
        v = {'c': cod, 'ds': ds, 'n': nome, 'u': unita, 'en': en, 'sel': sel, 'titolo': titolo, 'org': ORG,
             'url': f'{BASE}/d/{ds}', 'def': f'{DESCR[ds]} Dataset “{titolo}” della piattaforma cohesiondata ({BASE}/d/{ds}), trovato su data.europa.eu. Selezione: {sel}.'}
        if extra:
            v.update(extra)
        self.indicatori.append(v)
        self.serie.setdefault(cod, {})

    def metti(self, cod, geo, a, val, nome_terr=None, somma=False):
        geo = geo_ok(geo)
        if geo is None or a is None or val is None:
            return
        t = self.serie[cod].setdefault(geo, {})
        if somma and a in t:
            t[a] = [t[a][0] + val, None]
        else:
            t[a] = [val, None]
        if nome_terr:
            self.territori.setdefault(geo, nome_terr)


def main():
    arg = [a for a in sys.argv[1:] if not a.startswith('--')]
    cartella, uscita = arg[0], arg[1]
    os.makedirs(cartella, exist_ok=True)
    if '--scarica' in sys.argv:
        for ds in DESCR:
            if not os.path.exists(os.path.join(cartella, ds + '.csv')):
                scarica(f'{BASE}/resource/{ds}.csv?$limit=500000', os.path.join(cartella, ds + '.csv'))
                print('scaricato', ds, flush=True)
            if not os.path.exists(os.path.join(cartella, ds + '.json')):
                scarica(f'{BASE}/api/views/{ds}.json', os.path.join(cartella, ds + '.json'))
    R = Raccolta()
    for ds in DESCR:
        R.titoli[ds], R.agg[ds] = scheda(cartella, ds)

    # indice di competitività regionale RCI 2.0 (2016, 2019, 2022)
    ds = 'ngxn-bw8m'
    for comp, (cod, nome, en) in RCI.items():
        if nome:
            R.voce(cod, ds, nome, UE100, en, f'colonna component = {comp}' if cod != 'EU_RCI_TOT' else 'colonna component = RCI 2.0 - 2016, RCI 2.0 - 2019, RCI 2.0 - 2022')
    for r in leggi(cartella, ds):
        m = RCI.get(r['component'])
        if m:
            R.metti(m[0], r['nuts_code_2016'], anno(r['year']), num(r['value']), r[NOMI[ds]])

    # indice di progresso sociale 2024 e 2020
    ds = '5nmd-5kax'
    for comp, (cod, nome, en) in SPI24.items():
        R.voce(cod, ds, nome, UE100, en, f'colonna component = {comp}')
    for r in leggi(cartella, ds):
        m = SPI24.get(r['component'])
        if m:
            R.metti(m[0], r['nuts_code'], anno(r['year']), num(r['value']), r[NOMI[ds]])
    ds = '99vh-w4e7'
    for comp, (cod, nome, en) in SPI20.items():
        R.voce(cod, ds, nome, P0100, en, f'colonna component = {comp}; anno di edizione 2020')
    for r in leggi(cartella, ds):
        m = SPI20.get(r['component'])
        if m:
            R.metti(m[0], r['region_code'], '2020', num(r['value']), r[NOMI[ds]])

    # qualità delle istituzioni EQI
    ds = 'eqnk-pu8x'
    for comp, (cod, nome, en) in EQI.items():
        R.voce(cod, ds, nome, STD, en, f'colonna component = {comp}')
    for r in leggi(cartella, ds):
        m = EQI.get(r['component'])
        if m:
            R.metti(m[0], r['region_code'], anno(r['year']), num(r['value']), r[NOMI[ds]])

    # monitor regionale di genere 2021
    ds = 'q6y9-dn7j'
    for idx, (base, nome_idx, en_idx) in INDICI_GENERE.items():
        for col, suff, descr, en in GENERE:
            R.voce(base + suff, ds, nome_idx if not suff else f'{idx}: {descr}', P0100, en_idx if not suff else f'{en_idx}, {en}',
                   f'colonna index = {idx}, colonna {col}; anno di edizione 2021')
    for r in leggi(cartella, ds):
        base = INDICI_GENERE.get(r['index'])
        if base:
            for col, suff, _, _ in GENERE:
                R.metti(base[0] + suff, r['unit_code'], '2021', num(r[col]), r[NOMI[ds]])

    # gas serra: per abitante e intensità carbonica (stime JRC)
    for ds, cod, nome, unita, en in [('4bvr-jq77', 'EU_CLI_GHG_AB', 'Emissioni di gas serra per abitante (stima JRC su dati EDGAR)', 'tonnellate di CO₂ equivalente per abitante', 'GHG emissions per capita, JRC estimate'),
                                     ('krps-v2iz', 'EU_CLI_GHG_INT', 'Intensità carbonica dell’economia: gas serra per 1.000 euro di PIL (stima JRC su dati EDGAR)', 'tonnellate di CO₂ equivalente per 1.000 euro', 'Carbon intensity, JRC estimate')]:
        R.voce(cod, ds, nome, unita, en, 'colonne nuts_code, year, value', {'stima': 'Stima del Centro comune di ricerca (JRC) della Commissione europea: valore modellato, non misurato.'})
        for r in leggi(cartella, ds):
            R.metti(cod, r['nuts_code'], anno(r['year']), num(r['value']), r[NOMI[ds]])

    # pagamenti dei fondi europei per regione
    ds = 'tc55-7ysv'
    for fondo, (cod, nome, en) in FONDI.items():
        R.voce(cod, ds, nome, EURO, en, f'colonna fund = {fondo}, colonna eu_payment_annual')
    calc_tot = 'Calcolato dall’Atlante: somma dei pagamenti annuali dei sette fondi (FESR, Fondo di coesione, FSE, FEASR, FEAMP, IOG, FEAD) per la stessa regione e lo stesso anno.'
    R.voce('EU_FON_TOT', ds, 'Pagamenti UE di tutti i fondi a gestione concorrente alla regione (somma calcolata)', EURO, 'EU payments, all funds (sum)',
           'colonna eu_payment_annual, somma di tutti i fondi', {'calc': calc_tot})
    R.voce('EU_FON_TOT_MOD', ds, 'Spesa effettiva stimata di tutti i fondi UE nella regione (modello della Commissione, somma calcolata)', EURO, 'Modelled annual expenditure, all funds (sum)',
           'colonna modelled_annual_eu_payments, somma di tutti i fondi',
           {'calc': calc_tot.replace('dei pagamenti annuali', 'della spesa annuale modellata'), 'stima': 'Stima della Commissione europea: media di 100.000 simulazioni che ricollocano i pagamenti sugli anni di spesa effettiva; valore modellato, non misurato.'})
    for r in leggi(cartella, ds):
        m = FONDI.get(r['fund'])
        if not m:
            continue
        a, geo, nome = anno(r['year']), r['nuts2_id'], r[NOMI[ds]]
        R.metti(m[0], geo, a, num(r['eu_payment_annual']), nome, somma=True)
        R.metti('EU_FON_TOT', geo, a, num(r['eu_payment_annual']), nome, somma=True)
        R.metti('EU_FON_TOT_MOD', geo, a, num(r['modelled_annual_eu_payments']), nome, somma=True)

    # energia rinnovabile da sole e vento: produzione e potenziale (stima JRC, riferita al 2019)
    ds = 'dau5-jiss'
    for col, cod, nome, unita, en in RINNOVABILI:
        R.voce(cod, ds, nome, unita, en, f'colonna {col}; anno 2019', {'stima': 'Stima del Centro comune di ricerca (JRC) pubblicata nel 2024; i valori sono collocati sull’anno 2019, quello dei dati di produzione usati dallo studio.'})
    for r in leggi(cartella, ds):
        for col, cod, *_ in RINNOVABILI:
            R.metti(cod, r['nuts3_id'], '2019', num(r[col]), r[NOMI[ds]])

    for i in R.indicatori:
        print(f"{i['c']:26s} {i['ds']:10s} territori {len(R.serie[i['c']]):4d}", flush=True)
    json.dump({'indicatori': R.indicatori, 'serie': R.serie, 'territori': R.territori, 'agg': R.agg, 'titoli': R.titoli,
               'scaricato': datetime.date.today().isoformat()}, open(uscita, 'w'))
    print(len(R.indicatori), 'indicatori;', len(R.territori), 'territori')


if __name__ == '__main__':
    main()
