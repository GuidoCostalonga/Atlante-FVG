"""Estrae gli indicatori regionali Eurostat dai file TSV dell'API di diffusione (regioni e province NUTS).

Uso: python3 estrai_eurostat_api.py <cartella con <dataset>.tsv.gz e codelist/> <uscita.json> [--scarica]

Con --scarica i file mancanti vengono scaricati dall'API pubblica di Eurostat
(https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/<dataset>?format=TSV&compressed=true)
insieme alle liste di codici delle dimensioni usate e all'indice (toc) con le date di aggiornamento.
Ogni indicatore del CATALOGO è una selezione di una combinazione di dimensioni di un dataset:
i valori sono copiati senza modifiche, con i contrassegni originali della fonte.
"""
import datetime, gzip, json, os, re, subprocess, sys

API = 'https://ec.europa.eu/eurostat/api/dissemination'

# codice, dataset, filtri sulle dimensioni, nome italiano, unità italiana, nome inglese
CATALOGO = [
    # --- struttura per età (demo_r_pjanind3, NUTS 3) ---
    ('EU_STR_ETAMEDIANA', 'demo_r_pjanind3', {'indic_de': 'MEDAGEPOP', 'unit': 'YR'}, 'Età mediana della popolazione', 'anni', 'Median age of population'),
    ('EU_STR_DIPANZ', 'demo_r_pjanind3', {'indic_de': 'OLDDEP1', 'unit': 'PC'}, 'Indice di dipendenza degli anziani (65 anni e oltre su 15-64)', '% della popolazione in età lavorativa', 'Old-age dependency ratio (65+ to 15-64)'),
    ('EU_STR_DIPGIOV', 'demo_r_pjanind3', {'indic_de': 'YOUNGDEP1', 'unit': 'PC'}, 'Indice di dipendenza dei giovani (0-14 anni su 15-64)', '% della popolazione in età lavorativa', 'Young-age dependency ratio (0-14 to 15-64)'),
    ('EU_STR_DIPTOT', 'demo_r_pjanind3', {'indic_de': 'DEPRATIO1', 'unit': 'PC'}, 'Indice di dipendenza strutturale (0-14 e 65 e oltre su 15-64)', '% della popolazione in età lavorativa', 'Age dependency ratio (0-14 and 65+ to 15-64)'),
    ('EU_STR_Q80', 'demo_r_pjanind3', {'indic_de': 'PC_Y80_MAX', 'unit': 'PC'}, 'Quota di popolazione di 80 anni e oltre', '% della popolazione', 'Proportion of population aged 80 years and more'),
    ('EU_STR_Q1529', 'demo_r_pjanind3', {'indic_de': 'PC_Y15_29', 'unit': 'PC'}, 'Quota di popolazione da 15 a 29 anni', '% della popolazione', 'Proportion of population aged 15-29 years'),
    ('EU_STR_DONNE', 'demo_r_pjanind3', {'indic_de': 'PC_FM', 'unit': 'PC'}, 'Donne ogni 100 uomini', 'donne per 100 uomini', 'Women per 100 men'),
    # --- dinamica demografica (demo_r_gind3, NUTS 3; demo_r_find2, NUTS 2) ---
    ('EU_DIN_CRESCITA', 'demo_r_gind3', {'indic_de': 'GROWRT'}, 'Variazione totale della popolazione', 'per 1.000 abitanti', 'Crude rate of total population change'),
    ('EU_DIN_NATURALE', 'demo_r_gind3', {'indic_de': 'NATGROWRT'}, 'Saldo naturale (nati meno decessi)', 'per 1.000 abitanti', 'Crude rate of natural change of population'),
    ('EU_DIN_MIGRATORIO', 'demo_r_gind3', {'indic_de': 'CNMIGRATRT'}, 'Saldo migratorio (compreso l’aggiustamento statistico)', 'per 1.000 abitanti', 'Crude rate of net migration plus statistical adjustment'),
    ('EU_DIN_MIGRANUM', 'demo_r_gind3', {'indic_de': 'CNMIGRAT'}, 'Saldo migratorio in persone (compreso l’aggiustamento statistico)', 'persone', 'Net migration plus statistical adjustment'),
    ('EU_DIN_NATALITA', 'demo_r_gind3', {'indic_de': 'GBIRTHRT'}, 'Tasso di natalità', 'nati per 1.000 abitanti', 'Crude birth rate'),
    ('EU_DIN_MORTALITA', 'demo_r_gind3', {'indic_de': 'GDEATHRT'}, 'Tasso di mortalità', 'decessi per 1.000 abitanti', 'Crude death rate'),
    ('EU_TOTFERRT2', 'demo_r_find2', {'indic_de': 'TOTFERRT', 'unit': 'NR'}, 'Figli per donna, regioni (serie dal 1990)', 'nati per donna', 'Total fertility rate by NUTS 2 region'),
    ('EU_AGEMOTH2', 'demo_r_find2', {'indic_de': 'AGEMOTH', 'unit': 'YR'}, 'Età media delle madri al parto, regioni (serie dal 1990)', 'anni', 'Mean age of women at childbirth by NUTS 2 region'),
    # --- economia (contabilità regionale) ---
    ('EU_ECO_PIL_AB', 'nama_10r_3gdp', {'unit': 'EUR_HAB'}, 'Prodotto interno lordo (PIL) per abitante', 'euro per abitante', 'GDP per inhabitant at current market prices'),
    ('EU_ECO_PIL_PPS', 'nama_10r_3gdp', {'unit': 'PPS_EU27_2020_HAB'}, 'PIL per abitante in parità di potere d’acquisto (PPS)', 'PPS per abitante', 'GDP per inhabitant in purchasing power standard'),
    ('EU_ECO_PIL_UE', 'nama_10r_3gdp', {'unit': 'PPS_HAB_EU27_2020'}, 'PIL per abitante rispetto alla media dell’Unione europea', '% della media UE a 27 (= 100)', 'GDP per inhabitant in PPS as percentage of the EU27 average'),
    ('EU_ECO_PIL_TOT', 'nama_10r_3gdp', {'unit': 'MIO_EUR'}, 'PIL totale', 'milioni di euro', 'GDP at current market prices'),
    ('EU_ECO_CRESCITA', 'nama_10r_2gvagr', {'na_item': 'B1GQ', 'unit': 'PCH_PRE'}, 'Crescita reale del PIL', '% rispetto all’anno precedente', 'GDP in volume, percentage change on previous period'),
    ('EU_ECO_REDDITO', 'nama_10r_2hhinc', {'unit': 'EUR_HAB', 'direct': 'BAL', 'na_item': 'B6N'}, 'Reddito disponibile netto delle famiglie per abitante', 'euro per abitante', 'Net disposable income of households per inhabitant'),
    ('EU_ECO_REDDITO_PPS', 'nama_10r_2hhinc', {'unit': 'PPS_EU27_2020_HAB', 'direct': 'BAL', 'na_item': 'B6N'}, 'Reddito disponibile delle famiglie per abitante in parità di potere d’acquisto (PPS)', 'PPS per abitante', 'Net disposable income of households per inhabitant in PPS'),
    ('EU_ECO_PRODUTT', 'nama_10r_2nlp', {'na_item': 'NLPR_PER', 'unit': 'EUR'}, 'Produttività del lavoro per occupato', 'euro per occupato', 'Nominal labour productivity per person employed'),
    ('EU_ECO_PRODUTT_ORA', 'nama_10r_2nlp', {'na_item': 'NLPR_HW', 'unit': 'EUR'}, 'Produttività del lavoro per ora lavorata', 'euro per ora', 'Nominal labour productivity per hour worked'),
    ('EU_ECO_INVEST', 'nama_10r_2gfcf', {'sector': 'S1', 'currency': 'MIO_EUR', 'nace_r2': 'TOTAL'}, 'Investimenti fissi lordi', 'milioni di euro', 'Gross fixed capital formation, total economy'),
    ('EU_ECO_OCC_TOT', 'nama_10r_3empers', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'TOTAL'}, 'Occupati (contabilità regionale)', 'migliaia di persone', 'Employment, total (regional accounts)'),
    ('EU_ECO_OCC_AGR', 'nama_10r_3empers', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'A'}, 'Occupati in agricoltura, silvicoltura e pesca', 'migliaia di persone', 'Employment in agriculture, forestry and fishing'),
    ('EU_ECO_OCC_IND', 'nama_10r_3empers', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'B-E'}, 'Occupati nell’industria (escluse le costruzioni)', 'migliaia di persone', 'Employment in industry (except construction)'),
    ('EU_ECO_OCC_EDI', 'nama_10r_3empers', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'F'}, 'Occupati nelle costruzioni', 'migliaia di persone', 'Employment in construction'),
    ('EU_ECO_OCC_COM', 'nama_10r_3empers', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'G-J'}, 'Occupati in commercio, trasporti, alloggio e ristorazione, informazione', 'migliaia di persone', 'Employment in trade, transport, accommodation, information'),
    ('EU_ECO_OCC_FIN', 'nama_10r_3empers', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'K-N'}, 'Occupati in finanza, immobiliare, servizi professionali e alle imprese', 'migliaia di persone', 'Employment in financial, real estate, professional and administrative services'),
    ('EU_ECO_OCC_PA', 'nama_10r_3empers', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'O-U'}, 'Occupati in amministrazione pubblica, istruzione, sanità e altri servizi', 'migliaia di persone', 'Employment in public administration, education, health and other services'),
    # --- lavoro ---
    ('EU_LAV_OCC2064', 'lfst_r_lfe2emprt', {'unit': 'PC', 'sex': 'T', 'age': 'Y20-64'}, 'Tasso di occupazione (20-64 anni)', '% della popolazione di 20-64 anni', 'Employment rate, 20-64 years'),
    ('EU_LAV_OCC2064_F', 'lfst_r_lfe2emprt', {'unit': 'PC', 'sex': 'F', 'age': 'Y20-64'}, 'Tasso di occupazione delle donne (20-64 anni)', '% delle donne di 20-64 anni', 'Employment rate, females, 20-64 years'),
    ('EU_LAV_OCC2064_M', 'lfst_r_lfe2emprt', {'unit': 'PC', 'sex': 'M', 'age': 'Y20-64'}, 'Tasso di occupazione degli uomini (20-64 anni)', '% degli uomini di 20-64 anni', 'Employment rate, males, 20-64 years'),
    ('EU_LAV_OCC1564', 'lfst_r_lfe2emprt', {'unit': 'PC', 'sex': 'T', 'age': 'Y15-64'}, 'Tasso di occupazione (15-64 anni)', '% della popolazione di 15-64 anni', 'Employment rate, 15-64 years'),
    ('EU_LAV_OCC5564', 'lfst_r_lfe2emprt', {'unit': 'PC', 'sex': 'T', 'age': 'Y55-64'}, 'Tasso di occupazione dei lavoratori anziani (55-64 anni)', '% della popolazione di 55-64 anni', 'Employment rate, 55-64 years'),
    ('EU_LAV_OCC1524', 'lfst_r_lfe2emprt', {'unit': 'PC', 'sex': 'T', 'age': 'Y15-24'}, 'Tasso di occupazione dei giovani (15-24 anni)', '% della popolazione di 15-24 anni', 'Employment rate, 15-24 years'),
    ('EU_LAV_DIS', 'lfst_r_lfu3rt', {'isced11': 'TOTAL', 'sex': 'T', 'age': 'Y15-74', 'unit': 'PC'}, 'Tasso di disoccupazione (15-74 anni)', '% della forza lavoro', 'Unemployment rate, 15-74 years'),
    ('EU_LAV_DIS_F', 'lfst_r_lfu3rt', {'isced11': 'TOTAL', 'sex': 'F', 'age': 'Y15-74', 'unit': 'PC'}, 'Tasso di disoccupazione delle donne (15-74 anni)', '% della forza lavoro femminile', 'Unemployment rate, females, 15-74 years'),
    ('EU_LAV_DIS_M', 'lfst_r_lfu3rt', {'isced11': 'TOTAL', 'sex': 'M', 'age': 'Y15-74', 'unit': 'PC'}, 'Tasso di disoccupazione degli uomini (15-74 anni)', '% della forza lavoro maschile', 'Unemployment rate, males, 15-74 years'),
    ('EU_LAV_DIS_GIOV', 'lfst_r_lfu3rt', {'isced11': 'TOTAL', 'sex': 'T', 'age': 'Y15-24', 'unit': 'PC'}, 'Tasso di disoccupazione giovanile (15-24 anni)', '% della forza lavoro di 15-24 anni', 'Unemployment rate, 15-24 years'),
    ('EU_LAV_DIS_LUNGA', 'lfst_r_lfu2ltu', {'isced11': 'TOTAL', 'sex': 'T', 'age': 'Y15-74', 'unit': 'PC_ACT'}, 'Tasso di disoccupazione di lunga durata (12 mesi e oltre)', '% della forza lavoro', 'Long-term unemployment rate, 15-74 years'),
    ('EU_LAV_ATT1564', 'lfst_r_lfp2actrt', {'unit': 'PC', 'sex': 'T', 'age': 'Y15-64'}, 'Tasso di attività (15-64 anni)', '% della popolazione di 15-64 anni', 'Labour force participation rate, 15-64 years'),
    ('EU_LAV_ATT1564_F', 'lfst_r_lfp2actrt', {'unit': 'PC', 'sex': 'F', 'age': 'Y15-64'}, 'Tasso di attività delle donne (15-64 anni)', '% delle donne di 15-64 anni', 'Labour force participation rate, females, 15-64 years'),
    ('EU_LAV_NEET', 'edat_lfse_22', {'sex': 'T', 'age': 'Y15-29', 'training': 'NO_FE_NO_NFE', 'wstatus': 'NEMP', 'unit': 'PC'}, 'Giovani che non studiano e non lavorano (NEET, 15-29 anni)', '% della popolazione di 15-29 anni', 'Young people neither in employment nor in education and training, 15-29 years'),
    ('EU_LAV_NEET_F', 'edat_lfse_22', {'sex': 'F', 'age': 'Y15-29', 'training': 'NO_FE_NO_NFE', 'wstatus': 'NEMP', 'unit': 'PC'}, 'Giovani donne che non studiano e non lavorano (NEET, 15-29 anni)', '% delle donne di 15-29 anni', 'NEET rate, females, 15-29 years'),
    ('EU_LAV_NEET_M', 'edat_lfse_22', {'sex': 'M', 'age': 'Y15-29', 'training': 'NO_FE_NO_NFE', 'wstatus': 'NEMP', 'unit': 'PC'}, 'Giovani uomini che non studiano e non lavorano (NEET, 15-29 anni)', '% degli uomini di 15-29 anni', 'NEET rate, males, 15-29 years'),
    # --- istruzione e formazione ---
    ('EU_IST_LAUREATI', 'edat_lfse_04', {'sex': 'T', 'isced11': 'ED5-8', 'age': 'Y25-64', 'unit': 'PC'}, 'Laureati e diplomati dell’istruzione terziaria (25-64 anni)', '% della popolazione di 25-64 anni', 'Tertiary educational attainment, 25-64 years'),
    ('EU_IST_LAUREATI3034', 'edat_lfse_04', {'sex': 'T', 'isced11': 'ED5-8', 'age': 'Y30-34', 'unit': 'PC'}, 'Laureati tra i 30 e i 34 anni', '% della popolazione di 30-34 anni', 'Tertiary educational attainment, 30-34 years'),
    ('EU_IST_LAUREATI_F', 'edat_lfse_04', {'sex': 'F', 'isced11': 'ED5-8', 'age': 'Y25-64', 'unit': 'PC'}, 'Donne laureate (25-64 anni)', '% delle donne di 25-64 anni', 'Tertiary educational attainment, females, 25-64 years'),
    ('EU_IST_BASSA', 'edat_lfse_04', {'sex': 'T', 'isced11': 'ED0-2', 'age': 'Y25-64', 'unit': 'PC'}, 'Adulti con al massimo la licenza media (25-64 anni)', '% della popolazione di 25-64 anni', 'Less than primary, primary and lower secondary education, 25-64 years'),
    ('EU_IST_ABBANDONO', 'edat_lfse_16', {'unit': 'PC', 'sex': 'T', 'age': 'Y18-24'}, 'Abbandono precoce degli studi (18-24 anni)', '% della popolazione di 18-24 anni', 'Early leavers from education and training, 18-24 years'),
    ('EU_IST_ABBANDONO_F', 'edat_lfse_16', {'unit': 'PC', 'sex': 'F', 'age': 'Y18-24'}, 'Abbandono precoce degli studi, donne (18-24 anni)', '% delle donne di 18-24 anni', 'Early leavers from education and training, females'),
    ('EU_IST_ABBANDONO_M', 'edat_lfse_16', {'unit': 'PC', 'sex': 'M', 'age': 'Y18-24'}, 'Abbandono precoce degli studi, uomini (18-24 anni)', '% degli uomini di 18-24 anni', 'Early leavers from education and training, males'),
    ('EU_IST_FORMAZIONE', 'trng_lfse_04', {'unit': 'PC', 'sex': 'T', 'age': 'Y25-64'}, 'Adulti in formazione nelle ultime 4 settimane (25-64 anni)', '% della popolazione di 25-64 anni', 'Participation rate in education and training (last 4 weeks), 25-64 years'),
    # --- ricerca, innovazione e cultura ---
    ('EU_RIC_SPESA', 'rd_e_gerdreg', {'sectperf': 'TOTAL', 'unit': 'PC_GDP'}, 'Spesa in ricerca e sviluppo', '% del PIL', 'Gross domestic expenditure on R&D, all sectors'),
    ('EU_RIC_SPESA_AB', 'rd_e_gerdreg', {'sectperf': 'TOTAL', 'unit': 'EUR_HAB'}, 'Spesa in ricerca e sviluppo per abitante', 'euro per abitante', 'Gross domestic expenditure on R&D per inhabitant'),
    ('EU_RIC_SPESA_IMP', 'rd_e_gerdreg', {'sectperf': 'BES', 'unit': 'PC_GDP'}, 'Spesa in ricerca e sviluppo delle imprese', '% del PIL', 'R&D expenditure of the business enterprise sector'),
    ('EU_RIC_PERSONALE', 'rd_p_persreg', {'prof_pos': 'TOTAL', 'sex': 'T', 'sectperf': 'TOTAL', 'unit': 'PC_ACT_FTE'}, 'Personale di ricerca e sviluppo', '% della forza lavoro, equivalenti a tempo pieno', 'R&D personnel, all sectors, % of labour force (FTE)'),
    ('EU_RIC_RICERCATORI', 'rd_p_persreg', {'prof_pos': 'RSE', 'sex': 'T', 'sectperf': 'TOTAL', 'unit': 'PC_ACT_FTE'}, 'Ricercatori', '% della forza lavoro, equivalenti a tempo pieno', 'Researchers, all sectors, % of labour force (FTE)'),
    ('EU_RIC_ALTATEC', 'htec_emp_reg2', {'nace_r2': 'HTC', 'unit': 'PC_EMP', 'sex': 'T'}, 'Occupati nei settori ad alta tecnologia', '% degli occupati', 'Employment in high-technology sectors'),
    ('EU_RIC_KIS', 'htec_emp_reg2', {'nace_r2': 'KIS', 'unit': 'PC_EMP', 'sex': 'T'}, 'Occupati nei servizi ad alta intensità di conoscenza', '% degli occupati', 'Employment in knowledge-intensive services'),
    ('EU_RIC_HRST', 'hrst_st_rcat', {'category': 'HRST', 'unit': 'PC_ACT'}, 'Risorse umane in scienza e tecnologia', '% della popolazione attiva', 'Human resources in science and technology (HRST)'),
    ('EU_RIC_SCIENZIATI', 'hrst_st_rcat', {'category': 'SE', 'unit': 'PC_ACT'}, 'Scienziati e ingegneri', '% della popolazione attiva', 'Scientists and engineers'),
    ('EU_RIC_BREVETTI', 'pat_ep_rtot', {'unit': 'P_MHAB'}, 'Domande di brevetto all’Ufficio europeo dei brevetti (serie storica fino al 2012)', 'per milione di abitanti', 'Patent applications to the EPO by priority year (1977-2012)'),
    ('EU_RIC_CULTURA', 'cult_emp_reg', {'unit': 'PC_EMP'}, 'Occupazione culturale', '% degli occupati', 'Cultural employment'),
    # --- salute ---
    ('EU_SAL_VITA', 'demo_r_mlifexp', {'unit': 'YR', 'sex': 'T', 'age': 'Y_LT1'}, 'Speranza di vita alla nascita, regioni europee', 'anni', 'Life expectancy at birth'),
    ('EU_SAL_VITA_F', 'demo_r_mlifexp', {'unit': 'YR', 'sex': 'F', 'age': 'Y_LT1'}, 'Speranza di vita alla nascita, donne', 'anni', 'Life expectancy at birth, females'),
    ('EU_SAL_VITA_M', 'demo_r_mlifexp', {'unit': 'YR', 'sex': 'M', 'age': 'Y_LT1'}, 'Speranza di vita alla nascita, uomini', 'anni', 'Life expectancy at birth, males'),
    ('EU_SAL_VITA65', 'demo_r_mlifexp', {'unit': 'YR', 'sex': 'T', 'age': 'Y65'}, 'Speranza di vita a 65 anni', 'anni', 'Life expectancy at age 65'),
    ('EU_SAL_MORTINF', 'demo_r_minfind', {'unit': 'RT'}, 'Mortalità infantile, regioni europee', 'decessi sotto l’anno per 1.000 nati vivi', 'Infant mortality rate'),
    ('EU_SAL_LETTI', 'hlth_rs_bdsrg2', {'unit': 'P_HTHAB'}, 'Posti letto ospedalieri, regioni europee', 'per 100.000 abitanti', 'Available beds in hospitals'),
    ('EU_SAL_MEDICI', 'hlth_rs_physreg', {'unit': 'P_HTHAB'}, 'Medici, regioni europee', 'per 100.000 abitanti', 'Physicians'),
    ('EU_SAL_MORT_TOT', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'A-R_V-Y'}, 'Mortalità standardizzata, tutte le cause', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, all causes of death'),
    ('EU_SAL_MORT_TUMORI', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'C'}, 'Mortalità per tumori maligni', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, malignant neoplasms'),
    ('EU_SAL_MORT_POLMONE', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'C33_C34'}, 'Mortalità per tumore di trachea, bronchi e polmone', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, malignant neoplasm of trachea, bronchus and lung'),
    ('EU_SAL_MORT_CIRC', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'I'}, 'Mortalità per malattie del sistema circolatorio', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, diseases of the circulatory system'),
    ('EU_SAL_MORT_CUORE', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'I20-I25'}, 'Mortalità per cardiopatie ischemiche', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, ischaemic heart diseases'),
    ('EU_SAL_MORT_ICTUS', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'I60-I69'}, 'Mortalità per malattie cerebrovascolari', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, cerebrovascular diseases'),
    ('EU_SAL_MORT_RESP', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'J'}, 'Mortalità per malattie respiratorie', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, diseases of the respiratory system'),
    ('EU_SAL_MORT_DIAB', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'E10-E14'}, 'Mortalità per diabete', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, diabetes mellitus'),
    ('EU_SAL_MORT_DEMENZA', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'F01_F03'}, 'Mortalità per demenza', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, dementia'),
    ('EU_SAL_MORT_ALZHEIMER', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'G30'}, 'Mortalità per malattia di Alzheimer', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, Alzheimer disease'),
    ('EU_SAL_MORT_FEGATO', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'K70_K73_K74'}, 'Mortalità per malattie croniche del fegato', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, chronic liver disease'),
    ('EU_SAL_MORT_ESTERNE', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'V01-Y89'}, 'Mortalità per cause esterne (incidenti e violenze)', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, external causes of morbidity and mortality'),
    ('EU_SAL_MORT_TRASPORTI', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'V_Y85'}, 'Mortalità per incidenti di trasporto', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, transport accidents'),
    ('EU_SAL_MORT_SUICIDIO', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'X60-X84_Y870'}, 'Mortalità per suicidio', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, intentional self-harm'),
    ('EU_SAL_MORT_COVID', 'hlth_cd_asdr2', {'unit': 'RT', 'sex': 'T', 'age': 'TOTAL', 'icd10': 'U071'}, 'Mortalità per COVID-19 (virus identificato)', 'decessi per 100.000 abitanti (tasso standardizzato per età)', 'Standardised death rate, COVID-19, virus identified'),
    ('EU_SAL_CURE', 'hlth_silc_08_r', {'reason': 'TXP_TFAR_WLIST', 'unit': 'PC'}, 'Visite mediche necessarie ma rinunciate per costo, distanza o liste d’attesa', '% della popolazione di 16 anni e oltre', 'Self-reported unmet needs for medical examination: too expensive, too far or waiting list'),
    # --- condizioni di vita e sicurezza ---
    ('EU_SOC_POVESCL', 'ilc_peps11n', {'unit': 'PC'}, 'Persone a rischio di povertà o esclusione sociale', '% della popolazione', 'People at risk of poverty or social exclusion'),
    ('EU_SOC_POV', 'ilc_li41', {'unit': 'PC'}, 'Persone a rischio di povertà (reddito sotto il 60% della mediana nazionale)', '% della popolazione', 'At-risk-of-poverty rate'),
    ('EU_SOC_LAVOROBASSO', 'ilc_lvhl21n', {'unit': 'PC'}, 'Persone in famiglie a bassissima intensità di lavoro', '% della popolazione sotto i 65 anni', 'People living in households with very low work intensity'),
    ('EU_SOC_DEPRIV', 'ilc_mdsd18', {'unit': 'PC'}, 'Deprivazione materiale e sociale grave', '% della popolazione', 'Severe material and social deprivation rate'),
    ('EU_SOC_S80S20', 'ilc_di11_r', {'unit': 'INX'}, 'Disuguaglianza dei redditi: rapporto fra il 20% più ricco e il 20% più povero (S80/S20)', 'rapporto', 'Income quintile share ratio S80/S20'),
    ('EU_SOC_CASA', 'ilc_lvho07_r', {'unit': 'PC'}, 'Famiglie con costi dell’abitazione eccessivi (oltre il 40% del reddito)', '% della popolazione', 'Housing cost overburden rate'),
    ('EU_SOC_FREDDO', 'ilc_mdes01_r', {'unit': 'PC'}, 'Persone che non possono riscaldare adeguatamente la casa', '% della popolazione', 'Inability to keep home adequately warm'),
    ('EU_SOC_STANZE', 'ilc_lvho04n', {'unit': 'AVG'}, 'Stanze per persona', 'numero medio di stanze', 'Average number of rooms per person'),
    ('EU_SOC_OMICIDI', 'crim_gen_reg', {'unit': 'P_HTHAB', 'iccs': 'ICCS0101'}, 'Omicidi volontari registrati dalla polizia', 'per 100.000 abitanti', 'Police-recorded intentional homicide'),
    ('EU_SOC_AGGRESSIONI', 'crim_gen_reg', {'unit': 'P_HTHAB', 'iccs': 'ICCS02011'}, 'Aggressioni registrate dalla polizia', 'per 100.000 abitanti', 'Police-recorded assault'),
    ('EU_SOC_RAPINE', 'crim_gen_reg', {'unit': 'P_HTHAB', 'iccs': 'ICCS0401'}, 'Rapine registrate dalla polizia', 'per 100.000 abitanti', 'Police-recorded robbery'),
    ('EU_SOC_FURTICASA', 'crim_gen_reg', {'unit': 'P_HTHAB', 'iccs': 'ICCS05012'}, 'Furti in abitazione registrati dalla polizia', 'per 100.000 abitanti', 'Police-recorded burglary of private residential premises'),
    ('EU_SOC_FURTI', 'crim_gen_reg', {'unit': 'P_HTHAB', 'iccs': 'ICCS0502'}, 'Furti registrati dalla polizia', 'per 100.000 abitanti', 'Police-recorded theft'),
    ('EU_SOC_FURTIAUTO', 'crim_gen_reg', {'unit': 'P_HTHAB', 'iccs': 'ICCS050211'}, 'Furti di veicoli a motore registrati dalla polizia', 'per 100.000 abitanti', 'Police-recorded theft of a motorized land vehicle'),
    # --- digitale ---
    ('EU_DIG_FAMIGLIE', 'isoc_r_iacc_h', {'unit': 'PC_HH'}, 'Famiglie con accesso a internet da casa', '% delle famiglie', 'Households with access to the internet at home'),
    ('EU_DIG_QUOTID', 'isoc_r_iuse_i', {'indic_is': 'I_IDAY', 'unit': 'PC_IND'}, 'Persone che usano internet ogni giorno', '% delle persone di 16-74 anni', 'Individuals, frequency of internet access: daily'),
    ('EU_DIG_MAI', 'isoc_r_iuse_i', {'indic_is': 'I_IUX', 'unit': 'PC_IND'}, 'Persone che non hanno mai usato internet', '% delle persone di 16-74 anni', 'Individuals, internet use: never'),
    ('EU_DIG_BANCA', 'isoc_r_iuse_i', {'indic_is': 'I_IUBK', 'unit': 'PC_IND'}, 'Persone che usano i servizi bancari in rete', '% delle persone di 16-74 anni', 'Individuals, internet use: internet banking'),
    ('EU_DIG_ACQUISTI', 'isoc_r_blt12_i', {'indic_is': 'I_BLT12', 'unit': 'PC_IND'}, 'Persone che hanno fatto acquisti in rete negli ultimi 12 mesi', '% delle persone di 16-74 anni', 'Individuals, last online purchase in the 12 months'),
    ('EU_DIG_PA', 'isoc_r_gov_i', {'indic_is': 'I_IUGOV12', 'unit': 'PC_IND'}, 'Persone che usano internet per rapporti con la pubblica amministrazione (serie fino al 2021)', '% delle persone di 16-74 anni', 'Individuals, internet use: interaction with public authorities (last 12 months)'),
    # --- turismo ---
    ('EU_TUR_NOTTI', 'tour_occ_nin2', {'c_resid': 'TOTAL', 'unit': 'NR', 'nace_r2': 'I551-I553'}, 'Presenze turistiche (notti negli esercizi ricettivi)', 'notti', 'Nights spent at tourist accommodation establishments'),
    ('EU_TUR_NOTTI_EST', 'tour_occ_nin2', {'c_resid': 'FOR', 'unit': 'NR', 'nace_r2': 'I551-I553'}, 'Presenze di turisti stranieri', 'notti', 'Nights spent by non-residents at tourist accommodation establishments'),
    ('EU_TUR_NOTTI_AB', 'tour_occ_nin2', {'c_resid': 'TOTAL', 'unit': 'P_THAB', 'nace_r2': 'I551-I553'}, 'Presenze turistiche per abitante', 'notti per 1.000 abitanti', 'Nights spent at tourist accommodation establishments per thousand inhabitants'),
    ('EU_TUR_ARRIVI', 'tour_occ_arn2', {'c_resid': 'TOTAL', 'unit': 'NR', 'nace_r2': 'I551-I553'}, 'Arrivi negli esercizi ricettivi', 'arrivi', 'Arrivals at tourist accommodation establishments'),
    ('EU_TUR_LETTI', 'tour_cap_nuts2', {'accomunit': 'BEDPL', 'unit': 'NR', 'nace_r2': 'I551-I553'}, 'Posti letto negli esercizi ricettivi', 'posti letto', 'Bed-places in tourist accommodation establishments'),
    ('EU_TUR_PIATTAFORME', 'tour_ce_oan3', {'indic_to': 'NGT_SP', 'c_resid': 'TOTAL', 'unit': 'NR'}, 'Notti prenotate tramite piattaforme in rete (alloggi brevi)', 'notti', 'Guest nights spent at short-stay accommodation offered via online platforms'),
    # --- trasporti ---
    ('EU_TRA_MORTI', 'tran_r_acci', {'victim': 'KIL', 'unit': 'P_MHAB'}, 'Morti in incidenti stradali', 'per milione di abitanti', 'Persons killed in road accidents per million inhabitants'),
    ('EU_TRA_MORTI_N', 'tran_r_acci', {'victim': 'KIL', 'unit': 'NR'}, 'Morti in incidenti stradali, numero', 'persone', 'Persons killed in road accidents'),
    ('EU_TRA_FERITI', 'tran_r_acci', {'victim': 'INJ', 'unit': 'P_MHAB'}, 'Feriti in incidenti stradali', 'per milione di abitanti', 'Persons injured in road accidents per million inhabitants'),
    ('EU_TRA_INCIDENTI', 'tran_sf_roadnu', {'unit': 'P_MHAB'}, 'Incidenti stradali con feriti o morti', 'per milione di abitanti', 'Road accidents per million inhabitants'),
    ('EU_TRA_INCIDENTI_N', 'tran_sf_roadnu', {'unit': 'NR'}, 'Incidenti stradali con feriti o morti, numero', 'incidenti', 'Road accidents'),
    ('EU_TRA_AUTO', 'tran_r_vehst', {'vehicle': 'CAR', 'unit': 'P_THAB'}, 'Automobili ogni 1.000 abitanti', 'automobili per 1.000 abitanti', 'Passenger cars per thousand inhabitants'),
    ('EU_TRA_AUTO_N', 'tran_r_vehst', {'vehicle': 'CAR', 'unit': 'NR'}, 'Parco automobili', 'automobili', 'Stock of passenger cars'),
    ('EU_TRA_ELETTRICHE', 'tran_r_elvehst', {'vehicle': 'CAR', 'unit': 'PC'}, 'Automobili elettriche', '% del parco automobili', 'Electric passenger cars, share of stock'),
    ('EU_TRA_ELETTRICHE_N', 'tran_r_elvehst', {'vehicle': 'CAR', 'unit': 'NR'}, 'Automobili elettriche, numero', 'automobili', 'Stock of electric passenger cars'),
    ('EU_TRA_AUTOSTRADE', 'tran_r_net', {'tra_infr': 'MWAY', 'unit': 'KM'}, 'Autostrade', 'km', 'Motorways, length'),
    ('EU_TRA_AUTOSTRADE_D', 'tran_r_net', {'tra_infr': 'MWAY', 'unit': 'KM_TKM2'}, 'Densità di autostrade', 'km per 1.000 km²', 'Motorways per thousand square kilometres'),
    ('EU_TRA_FERROVIE', 'tran_r_net', {'tra_infr': 'RL', 'unit': 'KM'}, 'Linee ferroviarie', 'km', 'Total railway lines, length'),
    ('EU_TRA_FERROVIE_EL', 'tran_r_net', {'tra_infr': 'RL_ELC', 'unit': 'KM'}, 'Linee ferroviarie elettrificate', 'km', 'Electrified railway lines, length'),
    ('EU_TRA_AEREO', 'tran_r_avpa_nm', {'tra_meas': 'PAS_CRD', 'unit': 'THS_PAS'}, 'Passeggeri del trasporto aereo', 'migliaia di passeggeri', 'Air transport of passengers'),
    ('EU_TRA_MARE', 'tran_r_mapa_nm', {'tra_meas': 'PAS', 'unit': 'THS_PAS'}, 'Passeggeri del trasporto marittimo (imbarcati e sbarcati)', 'migliaia di passeggeri', 'Maritime transport of passengers, embarked and disembarked'),
    # --- agricoltura, territorio e clima ---
    ('EU_AGR_SAU', 'apro_cpshr', {'crops': 'UAA', 'strucpro': 'MAR_THS_HA'}, 'Superficie agricola utilizzata', 'migliaia di ettari', 'Utilised agricultural area, main area'),
    ('EU_AGR_SEMINATIVI', 'apro_cpshr', {'crops': 'ARA', 'strucpro': 'MAR_THS_HA'}, 'Seminativi', 'migliaia di ettari', 'Arable land, main area'),
    ('EU_AGR_CEREALI', 'apro_cpshr', {'crops': 'C0000', 'strucpro': 'HPRD_HUMD_EU_THS_T'}, 'Produzione di cereali', 'migliaia di tonnellate', 'Cereals for the production of grain, harvested production'),
    ('EU_AGR_CEREALI_HA', 'apro_cpshr', {'crops': 'C0000', 'strucpro': 'AR_THS_HA'}, 'Superficie a cereali', 'migliaia di ettari', 'Cereals for the production of grain, area'),
    ('EU_AGR_GRANO', 'apro_cpshr', {'crops': 'C1100', 'strucpro': 'HPRD_HUMD_EU_THS_T'}, 'Produzione di grano e farro', 'migliaia di tonnellate', 'Wheat and spelt, harvested production'),
    ('EU_AGR_MAIS', 'apro_cpshr', {'crops': 'C1500', 'strucpro': 'HPRD_HUMD_EU_THS_T'}, 'Produzione di mais da granella', 'migliaia di tonnellate', 'Grain maize and corn-cob-mix, harvested production'),
    ('EU_AGR_UVA', 'apro_cpshr', {'crops': 'W1000', 'strucpro': 'HPRD_HUMD_EU_THS_T'}, 'Produzione di uva', 'migliaia di tonnellate', 'Grapes, harvested production'),
    ('EU_AGR_ORTAGGI', 'apro_cpshr', {'crops': 'V0000_S0000', 'strucpro': 'HPRD_HUMD_EU_THS_T'}, 'Produzione di ortaggi freschi e fragole', 'migliaia di tonnellate', 'Fresh vegetables and strawberries, harvested production'),
    ('EU_AGR_BOVINI', 'apro_mt_ls_r', {'animals': 'A2000', 'unit': 'THS_HD'}, 'Bovini', 'migliaia di capi', 'Live bovine animals'),
    ('EU_AGR_VACCHE', 'apro_mt_ls_r', {'animals': 'A2300', 'unit': 'THS_HD'}, 'Vacche', 'migliaia di capi', 'Cows'),
    ('EU_AGR_SUINI', 'apro_mt_ls_r', {'animals': 'A3100', 'unit': 'THS_HD'}, 'Suini', 'migliaia di capi', 'Live swine, domestic species'),
    ('EU_AGR_OVINI', 'apro_mt_ls_r', {'animals': 'A4100', 'unit': 'THS_HD'}, 'Ovini', 'migliaia di capi', 'Live sheep'),
    ('EU_AGR_CAPRINI', 'apro_mt_ls_r', {'animals': 'A4200', 'unit': 'THS_HD'}, 'Caprini', 'migliaia di capi', 'Live goats'),
    ('EU_AGR_LATTE', 'agr_r_milkpr', {'milkitem': 'PRO', 'dairyprod': 'D1110A'}, 'Latte vaccino prodotto nelle aziende agricole', 'migliaia di tonnellate', 'Raw cows’ milk produced on farms'),
    ('EU_AGR_ARTIFICIALE', 'lan_lcv_art', {'unit': 'PC', 'landcover': 'A00'}, 'Superficie artificiale (edifici, strade, altre aree artificiali)', '% del territorio', 'Artificial land cover, share of total area'),
    ('EU_AGR_ARTIFICIALE_AB', 'lan_lcv_art', {'unit': 'M2_HAB', 'landcover': 'A00'}, 'Superficie artificiale per abitante', 'm² per abitante', 'Artificial land cover per capita'),
    ('EU_AGR_FORESTE', 'lan_lcv_fao', {'unit': 'PC', 'landcover': 'FOR_FAO'}, 'Foreste (definizione FAO)', '% del territorio', 'Forest (FAO definition), share of total area'),
    ('EU_AGR_USOAGRI', 'lan_use_ovw', {'unit': 'PC', 'landuse': 'U110'}, 'Territorio a uso agricolo', '% del territorio', 'Land use: agriculture, share of total area'),
    ('EU_AGR_USOFOREST', 'lan_use_ovw', {'unit': 'PC', 'landuse': 'U120'}, 'Territorio a uso forestale', '% del territorio', 'Land use: forestry, share of total area'),
    ('EU_AGR_AREA', 'reg_area3', {'landuse': 'TOTAL', 'unit': 'KM2'}, 'Superficie del territorio', 'km²', 'Total area'),
    ('EU_AGR_GRADIGIORNO', 'nrg_chddr2_a', {'unit': 'NR', 'indic_nrg': 'HDD'}, 'Gradi giorno di riscaldamento (rigidità del clima invernale)', 'gradi giorno', 'Heating degree days'),
    ('EU_AGR_GRADIGIORNO_C', 'nrg_chddr2_a', {'unit': 'NR', 'indic_nrg': 'CDD'}, 'Gradi giorno di raffrescamento (caldo estivo)', 'gradi giorno', 'Cooling degree days'),
    # --- imprese (demografia d'impresa, NUTS 3) ---
    ('EU_IMP_ATTIVE', 'bd_size_r', {'sizeclas': 'TOTAL', 'indic_sbs': 'ENT_NR', 'nace_r2': 'B-S_X_O_S94'}, 'Imprese attive (industria, costruzioni e servizi di mercato)', 'imprese', 'Active enterprises, industry, construction and market services'),
    ('EU_IMP_ADDETTI', 'bd_size_r', {'sizeclas': 'TOTAL', 'indic_sbs': 'EMP_NR', 'nace_r2': 'B-S_X_O_S94'}, 'Addetti delle imprese attive', 'persone', 'Persons employed in active enterprises'),
    ('EU_IMP_NATE', 'bd_size_r', {'sizeclas': 'TOTAL', 'indic_sbs': 'ENT_BRTH_NR', 'nace_r2': 'B-S_X_O_S94'}, 'Imprese nate nell’anno', 'imprese', 'Enterprise births'),
    ('EU_IMP_NATALITA', 'bd_size_r', {'sizeclas': 'TOTAL', 'indic_sbs': 'ENT_BRTHR_PC', 'nace_r2': 'B-S_X_O_S94'}, 'Tasso di natalità delle imprese', '% delle imprese attive', 'Enterprise birth rate'),
    ('EU_IMP_MORTALITA', 'bd_size_r', {'sizeclas': 'TOTAL', 'indic_sbs': 'ENT_DTHR_PC', 'nace_r2': 'B-S_X_O_S94'}, 'Tasso di mortalità delle imprese', '% delle imprese attive', 'Enterprise death rate'),
    ('EU_IMP_SOPRAVV', 'bd_size_r', {'sizeclas': 'TOTAL', 'indic_sbs': 'ENT_SRVLR_Y3_PC', 'nace_r2': 'B-S_X_O_S94'}, 'Imprese sopravvissute tre anni dopo la nascita', '% delle imprese nate tre anni prima', 'Three-year survival rate of enterprises'),
    ('EU_IMP_CRESCITA', 'bd_size_r', {'sizeclas': 'TOTAL', 'indic_sbs': 'GRW_ENT_PC', 'nace_r2': 'B-S_X_O_S94'}, 'Crescita netta del numero di imprese', '% delle imprese attive', 'Net business population growth'),
]

# Secondo blocco (ottobre 2026): dataset regionali individuati con la ricerca su data.europa.eu.
# Nel filtro la chiave speciale '_geo' indica la dimensione che contiene il territorio quando non è 'geo'.
CATALOGO += [
    # popolazione e struttura per età
    ('EU_POP_FAMIGLIE', 'lfst_r_lfsd2hh', {'deg_urb': 'TOTAL', 'unit': 'THS_HH'}, 'Famiglie (nuclei familiari privati)', 'migliaia di famiglie', 'Private households'),
    ('EU_POP_T_YGE85', 'demo_r_pjangrp3', {'sex': 'T', 'unit': 'NR', 'age': 'Y_GE85'}, 'Popolazione di 85 anni e oltre al 1° gennaio', 'persone', 'Population on 1 January, aged 85 and over'),
    ('EU_POP_T_YLT5', 'demo_r_pjangrp3', {'sex': 'T', 'unit': 'NR', 'age': 'Y_LT5'}, 'Bambini sotto i 5 anni al 1° gennaio', 'persone', 'Population on 1 January, aged under 5'),
    ('EU_STR_ETAMEDIANA_L', 'demo_r_pjanind2', {'indic_de': 'MEDAGEPOP', 'unit': 'YR'}, 'Età mediana della popolazione, regioni (serie dal 1990)', 'anni', 'Median age of population, NUTS 2 regions (from 1990)'),
    ('EU_STR_DIPANZ_L', 'demo_r_pjanind2', {'indic_de': 'OLDDEP1', 'unit': 'PC'}, 'Indice di dipendenza degli anziani, regioni (serie dal 1990)', '% della popolazione in età lavorativa', 'Old-age dependency ratio, NUTS 2 regions (from 1990)'),
    ('EU_STR_Q65_L', 'demo_r_pjanind2', {'indic_de': 'PC_Y65_MAX', 'unit': 'PC'}, 'Quota di popolazione di 65 anni e oltre, regioni (serie dal 1990)', '% della popolazione', 'Proportion of population aged 65 years and more, NUTS 2 regions (from 1990)'),
    ('EU_STR_Q014_L', 'demo_r_pjanind2', {'indic_de': 'PC_Y0_14', 'unit': 'PC'}, 'Quota di popolazione da 0 a 14 anni, regioni (serie dal 1990)', '% della popolazione', 'Proportion of population aged 0-14 years, NUTS 2 regions (from 1990)'),
    ('EU_STR_Q2064', 'demo_r_pjanind2', {'indic_de': 'PC_Y20_64', 'unit': 'PC'}, 'Quota di popolazione in età lavorativa (20-64 anni)', '% della popolazione', 'Proportion of population aged 20-64 years'),
    # proiezioni di popolazione (scenario di base e prova di sensibilità senza migrazioni)
    ('EU_PRJ_POP', 'proj_25rp5', {'sex': 'T', 'age': 'TOTAL', 'projection': 'BSL', 'unit': 'PER'}, 'Popolazione proiettata al 1° gennaio, scenario di base (proiezione Eurostat)', 'persone', 'Projected population on 1 January, baseline projections'),
    ('EU_PRJ_POP_NOMIG', 'proj_25rp5', {'sex': 'T', 'age': 'TOTAL', 'projection': 'NMIGR', 'unit': 'PER'}, 'Popolazione proiettata senza migrazioni, prova di sensibilità (proiezione Eurostat)', 'persone', 'Projected population on 1 January, sensitivity test: no migration'),
    ('EU_PRJ_POP65', 'proj_25rp5', {'sex': 'T', 'age': 'Y_GE65', 'projection': 'BSL', 'unit': 'PER'}, 'Popolazione di 65 anni e oltre proiettata, scenario di base (proiezione Eurostat)', 'persone', 'Projected population aged 65 and over, baseline projections'),
    ('EU_PRJ_POP_LT15', 'proj_25rp5', {'sex': 'T', 'age': 'Y_LT15', 'projection': 'BSL', 'unit': 'PER'}, 'Popolazione sotto i 15 anni proiettata, scenario di base (proiezione Eurostat)', 'persone', 'Projected population aged under 15, baseline projections'),
    ('EU_PRJ_ETAMEDIANA', 'proj_25rpind', {'indic_de': 'MEDAGEPOP', 'projection': 'BSL'}, 'Età mediana proiettata, scenario di base (proiezione Eurostat)', 'anni', 'Projected median age of population, baseline projections'),
    ('EU_PRJ_DIPANZ', 'proj_25rpind', {'indic_de': 'OLDDEP1', 'projection': 'BSL'}, 'Indice di dipendenza degli anziani proiettato, scenario di base (proiezione Eurostat)', '% della popolazione in età lavorativa', 'Projected old-age dependency ratio, baseline projections'),
    ('EU_PRJ_Q65', 'proj_25rpind', {'indic_de': 'PC_Y65_MAX', 'projection': 'BSL'}, 'Quota di popolazione di 65 anni e oltre proiettata, scenario di base (proiezione Eurostat)', '% della popolazione', 'Projected proportion of population aged 65 years and more, baseline projections'),
    ('EU_PRJ_Q80', 'proj_25rpind', {'indic_de': 'PC_Y80_MAX', 'projection': 'BSL'}, 'Quota di popolazione di 80 anni e oltre proiettata, scenario di base (proiezione Eurostat)', '% della popolazione', 'Projected proportion of population aged 80 years and more, baseline projections'),
    # economia: valore aggiunto per provincia e settore, retribuzioni, ore, produttività
    ('EU_ECO_VA', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'TOTAL'}, 'Valore aggiunto lordo a prezzi correnti, province (NUTS 3)', 'milioni di euro', 'Gross value added at basic prices, all NACE activities'),
    ('EU_ECO_VA_AGR', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'A'}, 'Valore aggiunto in agricoltura, silvicoltura e pesca', 'milioni di euro', 'Gross value added, agriculture, forestry and fishing'),
    ('EU_ECO_VA_IND', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'B-E'}, 'Valore aggiunto nell’industria (escluse le costruzioni)', 'milioni di euro', 'Gross value added, industry (except construction)'),
    ('EU_ECO_VA_MANIF', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'C'}, 'Valore aggiunto nell’industria manifatturiera', 'milioni di euro', 'Gross value added, manufacturing'),
    ('EU_ECO_VA_EDI', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'F'}, 'Valore aggiunto nelle costruzioni', 'milioni di euro', 'Gross value added, construction'),
    ('EU_ECO_VA_COM', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'G-J'}, 'Valore aggiunto in commercio, trasporti, alloggio e ristorazione, informazione', 'milioni di euro', 'Gross value added, wholesale and retail trade, transport, accommodation and food, information and communication'),
    ('EU_ECO_VA_FIN', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'K-N'}, 'Valore aggiunto in finanza, immobiliare, servizi professionali e alle imprese', 'milioni di euro', 'Gross value added, financial, real estate, professional and administrative services'),
    ('EU_ECO_VA_PA', 'nama_10r_3gva', {'unit': 'CP_MEUR', 'nace_r2': 'O-U'}, 'Valore aggiunto in amministrazione pubblica, istruzione, sanità e altri servizi', 'milioni di euro', 'Gross value added, public administration, education, health and other services'),
    ('EU_ECO_RETRIB', 'nama_10r_2lp10', {'nace_r2': 'TOTAL', 'na_item': 'D1_SAL_PER', 'unit': 'EUR'}, 'Retribuzione lorda annua per dipendente (contabilità regionale)', 'euro per dipendente', 'Compensation per employee'),
    ('EU_ECO_RETRIB_UE', 'nama_10r_2lp10', {'nace_r2': 'TOTAL', 'na_item': 'D1_SAL_PER', 'unit': 'PC_EU27_2020_MEUR_CP'}, 'Retribuzione per dipendente rispetto alla media dell’Unione europea', '% della media UE a 27 (= 100)', 'Compensation per employee, percentage of EU27 average'),
    ('EU_ECO_RETRIB_ORA', 'nama_10r_2lp10', {'nace_r2': 'TOTAL', 'na_item': 'D1_SAL_HW', 'unit': 'EUR'}, 'Retribuzione lorda per ora lavorata', 'euro per ora', 'Compensation of employees per hour worked'),
    ('EU_ECO_ORE_OCC', 'nama_10r_2lp10', {'nace_r2': 'TOTAL', 'na_item': 'HW_EMP', 'unit': 'HW'}, 'Ore lavorate nell’anno per occupato', 'ore per occupato', 'Hours worked per employed person'),
    ('EU_ECO_ORE_TOT', 'nama_10r_2emhrw', {'unit': 'THS', 'wstatus': 'EMP', 'nace_r2': 'TOTAL'}, 'Ore lavorate in totale (contabilità regionale)', 'migliaia di ore', 'Employment, thousand hours worked, all NACE activities'),
    ('EU_ECO_PRODUTT3', 'nama_10r_3nlp', {'na_item': 'NLPR_PER', 'unit': 'EUR'}, 'Produttività del lavoro per occupato, province (NUTS 3)', 'euro per occupato', 'Nominal labour productivity per person, NUTS 3 regions'),
    ('EU_ECO_PRODUTT_UE', 'nama_10r_3nlp', {'na_item': 'NLPR_PER', 'unit': 'PC_EU27_2020_MEUR_CP'}, 'Produttività del lavoro rispetto alla media dell’Unione europea, province (NUTS 3)', '% della media UE a 27 (= 100)', 'Nominal labour productivity per person, percentage of EU27 average, NUTS 3 regions'),
    # lavoro
    ('EU_LAV_ORE', 'lfst_r_lfe2ehour', {'unit': 'HR', 'age': 'Y15-64', 'sex': 'T'}, 'Ore settimanali abitualmente lavorate nel lavoro principale (15-64 anni)', 'ore a settimana', 'Average usual weekly hours worked in the main job'),
    ('EU_LAV_ORE_F', 'lfst_r_lfe2ehour', {'unit': 'HR', 'age': 'Y15-64', 'sex': 'F'}, 'Ore settimanali lavorate dalle donne (15-64 anni)', 'ore a settimana', 'Average usual weekly hours worked in the main job, females'),
    ('EU_LAV_ORE_M', 'lfst_r_lfe2ehour', {'unit': 'HR', 'age': 'Y15-64', 'sex': 'M'}, 'Ore settimanali lavorate dagli uomini (15-64 anni)', 'ore a settimana', 'Average usual weekly hours worked in the main job, males'),
    ('EU_LAV_SLACK', 'lfst_r_sla_ga', {'wstatus': 'SLACK', 'age': 'Y15-74', 'sex': 'T', 'unit': 'PC_ELF'}, 'Manodopera potenziale inutilizzata: disoccupati, sottoccupati e persone disponibili ma non in cerca (15-74 anni)', '% della forza lavoro estesa', 'Labour market slack'),
    ('EU_LAV_SLACK_N', 'lfst_r_sla_ga', {'wstatus': 'SLACK', 'age': 'Y15-74', 'sex': 'T', 'unit': 'THS_PER'}, 'Manodopera potenziale inutilizzata, persone (15-74 anni)', 'migliaia di persone', 'Labour market slack, thousand persons'),
    ('EU_LAV_DIS_STRANIERI', 'lfst_r_lfur2gan', {'unit': 'PC', 'citizen': 'FOR', 'sex': 'T', 'age': 'Y15-74'}, 'Tasso di disoccupazione dei cittadini stranieri (15-74 anni)', '% della forza lavoro straniera', 'Unemployment rate, foreign citizens'),
    ('EU_LAV_DIS_EXTRAUE', 'lfst_r_lfur2gan', {'unit': 'PC', 'citizen': 'NEU27_2020_FOR', 'sex': 'T', 'age': 'Y15-74'}, 'Tasso di disoccupazione dei cittadini di paesi non UE (15-74 anni)', '% della forza lavoro di cittadini non UE', 'Unemployment rate, non-EU27 citizens'),
    ('EU_LAV_DIS_NAZIONALI', 'lfst_r_lfur2gan', {'unit': 'PC', 'citizen': 'NAT', 'sex': 'T', 'age': 'Y15-74'}, 'Tasso di disoccupazione dei cittadini del paese (15-74 anni)', '% della forza lavoro nazionale', 'Unemployment rate, nationals'),
    ('EU_LAV_OCC_STRANIERI', 'lfst_r_lfe2emprtn', {'citizen': 'FOR', 'isced11': 'TOTAL', 'age': 'Y20-64', 'sex': 'T', 'unit': 'PC'}, 'Tasso di occupazione dei cittadini stranieri (20-64 anni)', '% della popolazione straniera di 20-64 anni', 'Employment rate, foreign citizens'),
    ('EU_LAV_OCC_NAZIONALI', 'lfst_r_lfe2emprtn', {'citizen': 'NAT', 'isced11': 'TOTAL', 'age': 'Y20-64', 'sex': 'T', 'unit': 'PC'}, 'Tasso di occupazione dei cittadini del paese (20-64 anni)', '% della popolazione nazionale di 20-64 anni', 'Employment rate, nationals'),
    ('EU_LAV_OCC_LAUREATI', 'lfst_r_lfe2emprtn', {'citizen': 'TOTAL', 'isced11': 'ED5-8', 'age': 'Y20-64', 'sex': 'T', 'unit': 'PC'}, 'Tasso di occupazione dei laureati (20-64 anni)', '% dei laureati di 20-64 anni', 'Employment rate, tertiary education'),
    ('EU_LAV_OCC_BASSA', 'lfst_r_lfe2emprtn', {'citizen': 'TOTAL', 'isced11': 'ED0-2', 'age': 'Y20-64', 'sex': 'T', 'unit': 'PC'}, 'Tasso di occupazione di chi ha al massimo la licenza media (20-64 anni)', '% della popolazione di 20-64 anni con titolo basso', 'Employment rate, less than primary, primary and lower secondary education'),
    ('EU_LAV_DISGIOV_POP', 'yth_empl_140', {'sex': 'T', 'age': 'Y15-24', 'unit': 'PC'}, 'Giovani disoccupati in rapporto alla popolazione (15-24 anni)', '% della popolazione di 15-24 anni', 'Youth unemployment ratio'),
    ('EU_LAV_PENDOLARI', 'lfst_r_lfe2ecomm', {'age': 'Y15-64', 'c_work': 'OUTR', 'sex': 'T', 'unit': 'THS_PER'}, 'Occupati che lavorano in un’altra regione del paese (pendolari interregionali)', 'migliaia di persone', 'Employed persons working in another region of the country'),
    ('EU_LAV_FRONTALIERI', 'lfst_r_lfe2ecomm', {'age': 'Y15-64', 'c_work': 'FOR', 'sex': 'T', 'unit': 'THS_PER'}, 'Occupati che lavorano all’estero (frontalieri)', 'migliaia di persone', 'Employed persons working in a foreign country'),
    # istruzione
    ('EU_IST_UNIVERSITARI', 'educ_uoe_enrt06', {'unit': 'NR', 'isced11': 'ED5-8', 'sex': 'T'}, 'Studenti dell’istruzione terziaria (università e istituti equivalenti)', 'studenti', 'Students enrolled in tertiary education'),
    ('EU_IST_UNIVERSITARI_F', 'educ_uoe_enrt06', {'unit': 'NR', 'isced11': 'ED5-8', 'sex': 'F'}, 'Studentesse dell’istruzione terziaria', 'studentesse', 'Students enrolled in tertiary education, females'),
    ('EU_IST_DOTTORANDI', 'educ_uoe_enrt06', {'unit': 'NR', 'isced11': 'ED8', 'sex': 'T'}, 'Dottorandi (dottorato di ricerca)', 'studenti', 'Students enrolled in doctoral or equivalent level'),
    ('EU_IST_INFANZIA', 'educ_uoe_enrp03', {'unit': 'NR', 'sex': 'T', 'isced11': 'ED0'}, 'Bambini iscritti all’educazione della prima infanzia (nido e scuola dell’infanzia)', 'bambini', 'Pupils enrolled in early childhood education'),
    # salute
    ('EU_SAL_RICOVERI', 'hlth_rinpat2_reg', {'_geo': 'c_resid', 'icd10': 'TOTAL', 'age': 'TOTAL', 'hospcare': 'INPAT', 'sex': 'T', 'unit': 'P_HTHAB'}, 'Dimissioni ospedaliere di pazienti ricoverati, tutte le diagnosi, per regione di residenza', 'per 100.000 abitanti', 'Hospital discharges of resident in-patients, all diagnoses'),
    ('EU_SAL_DEGENZA', 'hlth_ralos1_reg', {'_geo': 'c_resid', 'icd10': 'TOTAL', 'age': 'TOTAL', 'hospcare': 'ALOS', 'sex': 'T', 'unit': 'NR'}, 'Degenza media dei ricoveri ospedalieri, tutte le diagnosi, per regione di residenza', 'giorni', 'In-patients average length of stay of residents, all diagnoses'),
    ('EU_SAL_LETTI_LT', 'hlth_rs_bdsrg', {'unit': 'P_HTHAB', 'facility': 'HBEDT_LT'}, 'Posti letto ospedalieri per lungodegenza (serie storica fino al 2021)', 'per 100.000 abitanti', 'Long-term care beds in hospitals'),
    ('EU_SAL_LETTI_PSI', 'hlth_rs_bdsrg', {'unit': 'P_HTHAB', 'facility': 'HBEDI_PSY'}, 'Posti letto ospedalieri psichiatrici (serie storica fino al 2021)', 'per 100.000 abitanti', 'Psychiatric care beds in hospitals'),
    ('EU_SAL_LETTI_CUR', 'hlth_rs_bdsrg', {'unit': 'P_HTHAB', 'facility': 'HBEDT_CUR'}, 'Posti letto ospedalieri per cure acute (serie storica fino al 2021)', 'per 100.000 abitanti', 'Curative care beds in hospitals'),
    ('EU_SAL_LETTI_RIAB', 'hlth_rs_bdsrg', {'unit': 'P_HTHAB', 'facility': 'HBEDT_REH'}, 'Posti letto ospedalieri per riabilitazione (serie storica fino al 2021)', 'per 100.000 abitanti', 'Rehabilitative care beds in hospitals'),
    ('EU_SAL_LETTI_RSA', 'hlth_rs_bdsns', {'unit': 'P_HTHAB', 'facility': 'NRCBED'}, 'Posti letto nelle strutture residenziali di assistenza (case di riposo e simili, serie storica fino al 2021)', 'per 100.000 abitanti', 'Available beds in nursing and residential care facilities'),
    ('EU_SAL_INFERMIERI', 'hlth_rs_prsrg', {'unit': 'P_HTHAB', 'isco08': 'OC222_322'}, 'Infermieri e ostetriche (serie storica fino al 2021)', 'per 100.000 abitanti', 'Nurses and midwives'),
    ('EU_SAL_DENTISTI', 'hlth_rs_prsrg', {'unit': 'P_HTHAB', 'isco08': 'OC2261'}, 'Dentisti (serie storica fino al 2021)', 'per 100.000 abitanti', 'Dentists'),
    ('EU_SAL_FARMACISTI', 'hlth_rs_prsrg', {'unit': 'P_HTHAB', 'isco08': 'OC2262'}, 'Farmacisti (serie storica fino al 2021)', 'per 100.000 abitanti', 'Pharmacists'),
    ('EU_SAL_FISIOTERAPISTI', 'hlth_rs_prsrg', {'unit': 'P_HTHAB', 'isco08': 'OC2264'}, 'Fisioterapisti (serie storica fino al 2021)', 'per 100.000 abitanti', 'Physiotherapists'),
    # condizioni di vita
    ('EU_SOC_POV_PRETRASF', 'ilc_li10_r', {'unit': 'PC'}, 'Rischio di povertà prima dei trasferimenti sociali (pensioni escluse dai trasferimenti)', '% della popolazione', 'At-risk-of-poverty rate before social transfers (pensions excluded from social transfers)'),
    ('EU_SOC_PASTO', 'ilc_mdes03_r', {'unit': 'PC'}, 'Persone che non possono permettersi un pasto con carne, pesce o equivalente ogni due giorni', '% della popolazione', 'Inability to afford a meal with meat, chicken, fish (or vegetarian equivalent) every second day'),
    ('EU_SOC_IMPREVISTI', 'ilc_mdes04_r', {'unit': 'PC'}, 'Persone che non possono far fronte a spese impreviste', '% della popolazione', 'Inability to face unexpected financial expenses'),
    ('EU_SOC_ARRETRATI', 'ilc_mdes05_r', {'unit': 'PC'}, 'Persone in arretrato con mutuo, affitto, bollette o rate', '% della popolazione', 'Arrears (mortgage or rent, utility bills or hire purchase)'),
    ('EU_SOC_DEPRIV_MS', 'ilc_mdsd08', {'unit': 'PC'}, 'Deprivazione materiale e sociale (almeno 5 voci su 13)', '% della popolazione', 'Material and social deprivation rate'),
    # digitale: imprese
    ('EU_DIG_IMP_IA', 'isoc_r_eb_ain2', {'nace_r2': 'C10-S951_X_K', 'size_emp': 'GE10', 'indic_is': 'E_AI_TANY', 'unit': 'PC_ENT'}, 'Imprese che usano almeno una tecnologia di intelligenza artificiale (10 addetti e oltre)', '% delle imprese', 'Enterprises using at least one AI technology'),
    ('EU_DIG_IMP_NUVOLA', 'isoc_r_cicce_usen2', {'nace_r2': 'C10-S951_X_K', 'size_emp': 'GE10', 'indic_is': 'E_CC', 'unit': 'PC_ENT'}, 'Imprese che acquistano servizi informatici in rete (cloud computing), 10 addetti e oltre', '% delle imprese', 'Enterprises buying cloud computing services used over the internet'),
    ('EU_DIG_IMP_VENDITE', 'isoc_r_ec_eseln2', {'nace_r2': 'C10-S951_X_K', 'size_emp': 'GE10', 'indic_is': 'E_AWSELL', 'unit': 'PC_ENT'}, 'Imprese che vendono tramite siti, applicazioni o mercati in rete (10 addetti e oltre)', '% delle imprese', 'Enterprises with web sales'),
    ('EU_DIG_IMP_DATI', 'isoc_r_eb_dan2', {'nace_r2': 'C10-S951_X_K', 'size_emp': 'GE10', 'indic_is': 'E_DA', 'unit': 'PC_ENT'}, 'Imprese che svolgono analisi di dati (10 addetti e oltre)', '% delle imprese', 'Enterprises performing data analytics'),
    ('EU_DIG_IMP_SPECIALISTI', 'isoc_r_ske_itspen2', {'nace_r2': 'C10-S951_X_K', 'size_emp': 'GE10', 'indic_is': 'E_ITSP2', 'unit': 'PC_ENT'}, 'Imprese che impiegano specialisti informatici (10 addetti e oltre)', '% delle imprese', 'Enterprises that employ ICT specialists'),
    # turismo
    ('EU_TUR_OCC_LETTI', 'tour_occ_anor2', {'accomunit': 'BEDPL', 'unit': 'PC'}, 'Tasso netto di occupazione dei posti letto negli alberghi', '% dei posti letto disponibili', 'Net occupancy rate of bed-places in hotels and similar accommodation'),
    ('EU_TUR_OCC_CAMERE', 'tour_occ_anor2', {'accomunit': 'BEDRM', 'unit': 'PC'}, 'Tasso netto di occupazione delle camere negli alberghi', '% delle camere disponibili', 'Net occupancy rate of bedrooms in hotels and similar accommodation'),
    # trasporti
    ('EU_TRA_RICARICA', 'road_if_rchden', {'acs': 'PUB', 'unit': 'P_KM2'}, 'Punti di ricarica pubblici per veicoli elettrici (statistica sperimentale)', 'punti per km²', 'Recharging points density, public access'),
    ('EU_TRA_AEREO_MERCI', 'tran_r_avgo_nm', {'unit': 'THS_T', 'tra_meas': 'FRM_LD_NLD'}, 'Merci trasportate per via aerea (caricate e scaricate)', 'migliaia di tonnellate', 'Air transport of freight, loaded and unloaded'),
    ('EU_TRA_MARE_MERCI', 'tran_r_mago_nm', {'tra_meas': 'FR_LD_NLD', 'unit': 'THS_T'}, 'Merci movimentate nei porti (caricate e scaricate)', 'migliaia di tonnellate', 'Maritime transport of freight, loaded and unloaded'),
    # ambiente: impianti per i rifiuti ed erosione del suolo
    ('EU_AMB_DISCARICHE', 'env_wasfac', {'indic_env': 'FAC', 'wst_oper': 'DSP_L'}, 'Discariche in esercizio', 'impianti', 'Landfill facilities (D1, D5, D12)'),
    ('EU_AMB_DISCARICHE_CAP', 'env_wasfac', {'indic_env': 'CAP_RST', 'wst_oper': 'DSP_L'}, 'Capacità residua delle discariche', 'metri cubi', 'Rest capacity of landfills'),
    ('EU_AMB_INCENERITORI', 'env_wasfac', {'indic_env': 'FAC', 'wst_oper': 'DSP_I'}, 'Impianti di incenerimento dei rifiuti senza recupero di energia', 'impianti', 'Incineration facilities (D10)'),
    ('EU_AMB_RECUPERO_ENERGIA', 'env_wasfac', {'indic_env': 'FAC', 'wst_oper': 'RCV_E'}, 'Impianti di recupero energetico dai rifiuti', 'impianti', 'Energy recovery facilities (R1)'),
    ('EU_AMB_RICICLO', 'env_wasfac', {'indic_env': 'FAC', 'wst_oper': 'RCV_R'}, 'Impianti di riciclo dei rifiuti', 'impianti', 'Recycling facilities'),
    ('EU_AMB_EROSIONE', 'aei_pr_soiler', {'levels': 'SEV', 'clc18': 'CLC2_3X331_332_335', 'unit': 'PC'}, 'Superficie con erosione grave del suolo per acqua, oltre 10 tonnellate per ettaro l’anno (stima)', '% dell’area agricola, forestale e seminaturale', 'Estimated soil erosion by water, severe erosion, share of area'),
    ('EU_AMB_EROSIONE_KM2', 'aei_pr_soiler', {'levels': 'SEV', 'clc18': 'CLC2_3X331_332_335', 'unit': 'KM2'}, 'Superficie con erosione grave del suolo per acqua (stima)', 'km²', 'Estimated soil erosion by water, severe erosion, area'),
    ('EU_AMB_EROSIONE_TASSO', 'aei_pr_soiler', {'levels': 'TOTAL', 'clc18': 'CLC2_3X331_332_335', 'unit': 'T_HA'}, 'Tasso medio di erosione del suolo per acqua (stima)', 'tonnellate per ettaro l’anno', 'Estimated soil erosion by water, mean erosion rate'),
    # agricoltura: struttura delle aziende, biologico, conti economici
    ('EU_AGR_AZIENDE', 'ef_m_farmleg', {'statinfo': 'TOTAL', 'leg_form': 'TOTAL', 'farmtype': 'TOTAL', 'so_eur': 'TOTAL', 'uaarea': 'TOTAL', 'unit': 'HLD'}, 'Aziende agricole', 'aziende', 'Agricultural holdings'),
    ('EU_AGR_AZIENDE_SAU', 'ef_m_farmleg', {'statinfo': 'TOTAL', 'leg_form': 'TOTAL', 'farmtype': 'TOTAL', 'so_eur': 'TOTAL', 'uaarea': 'TOTAL', 'unit': 'HA'}, 'Superficie agricola utilizzata delle aziende (censimenti e indagini sulla struttura)', 'ettari', 'Utilised agricultural area of holdings'),
    ('EU_AGR_LAVORO', 'ef_m_farmleg', {'statinfo': 'TOTAL', 'leg_form': 'TOTAL', 'farmtype': 'TOTAL', 'so_eur': 'TOTAL', 'uaarea': 'TOTAL', 'unit': 'AWU'}, 'Lavoro agricolo in unità di lavoro annue (ULA)', 'unità di lavoro annue', 'Agricultural labour, annual working units'),
    ('EU_AGR_BESTIAME', 'ef_m_farmleg', {'statinfo': 'TOTAL', 'leg_form': 'TOTAL', 'farmtype': 'TOTAL', 'so_eur': 'TOTAL', 'uaarea': 'TOTAL', 'unit': 'LSU'}, 'Bestiame in unità di bestiame adulto (UBA)', 'unità di bestiame', 'Livestock, livestock units'),
    ('EU_AGR_PRODSTD', 'ef_m_farmleg', {'statinfo': 'TOTAL', 'leg_form': 'TOTAL', 'farmtype': 'TOTAL', 'so_eur': 'TOTAL', 'uaarea': 'TOTAL', 'unit': 'EUR'}, 'Produzione standard delle aziende agricole', 'euro', 'Standard output of holdings'),
    ('EU_AGR_BIO', 'ef_lus_org', {'statinfo': 'TOTAL', 'so_eur': 'TOTAL', 'uaarea': 'TOTAL', 'agriprod': 'UAAXK0000_ORG', 'unit': 'HA'}, 'Superficie agricola biologica (certificata e in conversione)', 'ettari', 'Organic utilised agricultural area, fully converted and under conversion'),
    ('EU_AGR_BIO_AZIENDE', 'ef_lus_org', {'statinfo': 'TOTAL', 'so_eur': 'TOTAL', 'uaarea': 'TOTAL', 'agriprod': 'UAAXK0000_ORG', 'unit': 'HLD'}, 'Aziende agricole con superficie biologica', 'aziende', 'Holdings with organic utilised agricultural area'),
    ('EU_AGR_VALORE', 'aact_eaa01_r', {'am_item': 'AM160000', 'indic_agr': 'PRD_BP', 'unit': 'MIO_EUR'}, 'Valore della produzione agricola (conti economici dell’agricoltura, prezzi base)', 'milioni di euro', 'Agricultural output, production value at basic price'),
    ('EU_AGR_VALORE_VEG', 'aact_eaa01_r', {'am_item': 'AM100000', 'indic_agr': 'PRD_BP', 'unit': 'MIO_EUR'}, 'Valore della produzione vegetale (prezzi base)', 'milioni di euro', 'Crop output, production value at basic price'),
    ('EU_AGR_VALORE_ZOO', 'aact_eaa01_r', {'am_item': 'AM130000', 'indic_agr': 'PRD_BP', 'unit': 'MIO_EUR'}, 'Valore della produzione zootecnica (prezzi base)', 'milioni di euro', 'Animal output, production value at basic price'),
    ('EU_AGR_VALORE_CEREALI', 'aact_eaa01_r', {'am_item': 'AM010000', 'indic_agr': 'PRD_BP', 'unit': 'MIO_EUR'}, 'Valore della produzione di cereali (prezzi base)', 'milioni di euro', 'Cereals, production value at basic price'),
    ('EU_AGR_VALORE_VINO', 'aact_eaa01_r', {'am_item': 'AM070000', 'indic_agr': 'PRD_BP', 'unit': 'MIO_EUR'}, 'Valore della produzione di vino (prezzi base)', 'milioni di euro', 'Wine, production value at basic price'),
    ('EU_AGR_VALORE_FRUTTA', 'aact_eaa01_r', {'am_item': 'AM060000', 'indic_agr': 'PRD_BP', 'unit': 'MIO_EUR'}, 'Valore della produzione di frutta (prezzi base)', 'milioni di euro', 'Fruit, production value at basic price'),
    ('EU_AGR_VALORE_ORTAGGI', 'aact_eaa01_r', {'am_item': 'AM040000', 'indic_agr': 'PRD_BP', 'unit': 'MIO_EUR'}, 'Valore della produzione di ortaggi e prodotti orticoli (prezzi base)', 'milioni di euro', 'Vegetables and horticultural products, production value at basic price'),
    # imprese: statistiche strutturali per unità locale e indagine sull’innovazione
    ('EU_IMP_MANIF_UL', 'sbs_r_nuts2021', {'nace_r2': 'C', 'indic_sbs': 'LOC_NR'}, 'Unità locali dell’industria manifatturiera', 'unità locali', 'Local units, manufacturing'),
    ('EU_IMP_MANIF_ADD', 'sbs_r_nuts2021', {'nace_r2': 'C', 'indic_sbs': 'EMP_LOC_NR'}, 'Addetti dell’industria manifatturiera', 'persone', 'Persons employed in local units, manufacturing'),
    ('EU_IMP_MANIF_COSTOLAV', 'sbs_r_nuts2021', {'nace_r2': 'C', 'indic_sbs': 'LC_EMP_LOC_TEUR'}, 'Costo del lavoro per addetto nell’industria manifatturiera', 'migliaia di euro per addetto', 'Labour costs per person employed in local units, manufacturing'),
    ('EU_IMP_COSTR_ADD', 'sbs_r_nuts2021', {'nace_r2': 'F', 'indic_sbs': 'EMP_LOC_NR'}, 'Addetti delle costruzioni', 'persone', 'Persons employed in local units, construction'),
    ('EU_IMP_COMMERCIO_ADD', 'sbs_r_nuts2021', {'nace_r2': 'G', 'indic_sbs': 'EMP_LOC_NR'}, 'Addetti del commercio', 'persone', 'Persons employed in local units, wholesale and retail trade'),
    ('EU_IMP_RICETT_UL', 'sbs_r_nuts2021', {'nace_r2': 'I', 'indic_sbs': 'LOC_NR'}, 'Unità locali di alloggio e ristorazione', 'unità locali', 'Local units, accommodation and food service activities'),
    ('EU_IMP_RICETT_ADD', 'sbs_r_nuts2021', {'nace_r2': 'I', 'indic_sbs': 'EMP_LOC_NR'}, 'Addetti di alloggio e ristorazione', 'persone', 'Persons employed in local units, accommodation and food service activities'),
    ('EU_IMP_ICT_ADD', 'sbs_r_nuts2021', {'nace_r2': 'J', 'indic_sbs': 'EMP_LOC_NR'}, 'Addetti dei servizi di informazione e comunicazione', 'persone', 'Persons employed in local units, information and communication'),
    ('EU_IMP_INNOVATIVE', 'inn_cis13_bas_r', {'unit': 'NR', 'sizeclas': '10-249', 'nace_r2': 'B-M73_INN', 'indic_inn': 'ENT', 'enterpr': 'INN'}, 'Imprese con attività di innovazione (10-249 addetti, indagine CIS 2022)', 'imprese', 'Innovation active enterprises, 10-249 employees'),
    ('EU_IMP_INNOV_PRODOTTO', 'inn_cis13_bas_r', {'unit': 'NR', 'sizeclas': '10-249', 'nace_r2': 'B-M73_INN', 'indic_inn': 'ENT', 'enterpr': 'PRD'}, 'Imprese con innovazione di prodotto (10-249 addetti, indagine CIS 2022)', 'imprese', 'Enterprises with product innovation, 10-249 employees'),
    ('EU_IMP_INNOV_TOTALE', 'inn_cis13_bas_r', {'unit': 'NR', 'sizeclas': '10-249', 'nace_r2': 'B-M73_INN', 'indic_inn': 'ENT', 'enterpr': 'TOTAL'}, 'Imprese considerate dall’indagine sull’innovazione (10-249 addetti, CIS 2022)', 'imprese', 'Enterprises in the innovation survey population, 10-249 employees'),
]

AGGREGATI_TENUTI = {'EU27_2020', 'EU28', 'EU27_2007', 'EA20', 'EA19', 'EFTA'}


def scarica(url, dest):
    r = subprocess.run(['curl', '-sS', '-o', dest, '-w', '%{http_code}', url], capture_output=True, text=True)
    if r.stdout.strip() != '200':
        raise SystemExit(f'scaricamento fallito ({r.stdout.strip()}): {url}')


def leggi_codelist(cartella, nome):
    f = os.path.join(cartella, 'codelist', f'{nome}.tsv')
    etich = {}
    if os.path.exists(f):
        for ln in open(f, encoding='utf-8'):
            p = ln.rstrip('\n').split('\t')
            if len(p) >= 2:
                etich[p[0]] = p[1]
    return etich


def leggi_toc(cartella):
    """Indice di Eurostat: titolo e data dell'ultimo aggiornamento dei dati per ogni dataset."""
    toc = {}
    f = os.path.join(cartella, 'toc.txt')
    if not os.path.exists(f):
        return toc
    import csv
    for r in csv.reader(open(f, encoding='utf-8'), delimiter='\t'):
        if len(r) > 7 and r[2] == 'dataset':
            g, m, a = (r[3].strip().split('.') + ['', '', ''])[:3]
            toc[r[1]] = (r[0].strip(), f'{a}-{m}-{g}' if a else '')
    return toc


def estrai_dataset(cartella, ds, voci):
    """Legge un TSV compresso e restituisce {codice indicatore: {geo: {anno: [valore, contrassegno]}}}."""
    f = os.path.join(cartella, f'{ds}.tsv.gz')
    with gzip.open(f, 'rt', encoding='utf-8') as fh:
        testa = fh.readline().rstrip('\n').split('\t')
        dims = testa[0].split('\\')[0].split(',')
        anni = [h.strip() for h in testa[1:]]
        filtri = []
        for cod, _, filtro, *_ in voci:
            i_geo = dims.index(filtro.get('_geo', 'geo'))
            filtri.append((cod, [(dims.index(k), v) for k, v in filtro.items() if not k.startswith('_')], i_geo))
        out = {cod: {} for cod, _, _ in filtri}
        for ln in fh:
            parti = ln.rstrip('\n').split('\t')
            chiave = parti[0].split(',')
            for cod, cond, i_geo in filtri:
                geo = chiave[i_geo]
                if all(chiave[i] == v for i, v in cond):
                    serie = {}
                    for anno, cella in zip(anni, parti[1:]):
                        cella = cella.strip()
                        if not cella or cella.startswith(':'):
                            continue
                        pezzi = cella.split(' ')
                        try:
                            val = float(pezzi[0])
                        except ValueError:
                            continue
                        if not re.match(r'^\d{4}$', anno):
                            continue
                        serie[anno] = [val, ' '.join(pezzi[1:]) or None]
                    if serie:
                        out[cod][geo] = serie
    return out


def main():
    arg = [a for a in sys.argv[1:] if not a.startswith('--')]
    cartella, uscita = arg[0], arg[1]
    if '--scarica' in sys.argv:
        os.makedirs(os.path.join(cartella, 'codelist'), exist_ok=True)
        scarica(f'{API}/catalogue/toc/txt?lang=en', os.path.join(cartella, 'toc.txt'))
        scarica(f'{API}/sdmx/2.1/codelist/ESTAT/GEO?format=TSV&lang=en', os.path.join(cartella, 'codelist', 'GEO.tsv'))
        dims = sorted({k.upper() for _, _, f, *_ in CATALOGO for k in f if not k.startswith('_')})
        for d in dims:
            scarica(f'{API}/sdmx/2.1/codelist/ESTAT/{d}?format=TSV&lang=en', os.path.join(cartella, 'codelist', f'{d}.tsv'))
        for ds in sorted({v[1] for v in CATALOGO}):
            dest = os.path.join(cartella, f'{ds}.tsv.gz')
            if not os.path.exists(dest):
                scarica(f'{API}/sdmx/2.1/data/{ds}?format=TSV&compressed=true', dest)
                print('scaricato', ds, flush=True)
    toc = leggi_toc(cartella)
    geo_nomi = leggi_codelist(cartella, 'GEO')
    etichette = {}
    per_ds = {}
    for voce in CATALOGO:
        per_ds.setdefault(voce[1], []).append(voce)
    serie, territori, indicatori, agg, titoli = {}, {}, [], {}, {}
    for ds, voci in sorted(per_ds.items()):
        estratto = estrai_dataset(cartella, ds, voci)
        titolo, data = toc.get(ds, (ds, ''))
        agg[ds], titoli[ds] = data, titolo
        for cod, _, filtro, nome, unita, en in voci:
            dati = {}
            for geo, s in estratto[cod].items():
                if geo.endswith(('ZZ', 'ZZZ', 'XX', 'XXX')):
                    continue
                if not re.match(r'^[A-Z]{2}[0-9A-Z]{0,3}$', geo) and geo not in AGGREGATI_TENUTI:
                    continue
                dati[geo] = s
                territori.setdefault(geo, geo_nomi.get(geo, geo))
            serie[cod] = dati
            desc = []
            for k, v in filtro.items():
                if k.startswith('_'):
                    continue
                et = etichette.get(k)
                if et is None:
                    et = etichette[k] = leggi_codelist(cartella, k.upper())
                desc.append(f'{k} = {v} ({et.get(v, v)})')
            indicatori.append({'c': cod, 'ds': ds, 'n': nome, 'u': unita, 'en': en, 'sel': '; '.join(desc),
                               'titolo': titolo})
            print(f'{cod:24s} {ds:18s} territori {len(dati):5d}', flush=True)
    json.dump({'indicatori': indicatori, 'serie': serie, 'territori': territori, 'agg': agg, 'titoli': titoli,
               'scaricato': datetime.date.today().isoformat()}, open(uscita, 'w'))
    print(len(indicatori), 'indicatori;', len(territori), 'territori')


if __name__ == '__main__':
    main()
