/* Atlante dei dati: nucleo. Configurazione dei temi, stato, caricamento dei dati, formati,
   componenti comuni (ricerca, tendine, miniserie, avvisi) e instradamento fra le pagine. */
window.Atlante = (function () {
  'use strict';
  const A = {};
  const $ = (s, el) => (el || document).querySelector(s);
  A.$ = $;
  A.ridotto = matchMedia('(prefers-reduced-motion: reduce)');

  /* ---------- configurazione ---------- */
  const ICONE = {
    pop: 'M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM17 11a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M15 14.5c2.8 0 5 2.2 5 5',
    sal: 'M3 12h4l2-6 3 12 2-8 2 4h5',
    ist: 'M4 5h6a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H4zM20 5h-6a3 3 0 0 0-3 3v12a2 2 0 0 1 2-2h7z',
    amb: 'M4 20c0-9 6-15 16-15-1 10-6 15-16 15zM4 20c4-5 8-8 12-10',
    ene: 'M13 2L5 14h6l-1 8 8-12h-6z',
    acq: 'M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z',
    agr: 'M12 22V8M12 8c-3 0-5-2-5-5 3 0 5 2 5 5zM12 8c3 0 5-2 5-5-3 0-5 2-5 5zM12 14c-3 0-5-2-5-5 3 0 5 2 5 5zM12 14c3 0 5-2 5-5-3 0-5 2-5 5z',
    dig: 'M2 9a15 15 0 0 1 20 0M6 13a9 9 0 0 1 12 0M9.5 16.5a4 4 0 0 1 5 0M12 20h.01',
    eur: 'M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14',
    arc: 'M3 7h18v4H3zM5 11v9h14v-9M10 15h4',
    andamento: 'M3 17l5-6 4 3 7-9M3 21h18',
    mappa: 'M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14',
    classifica: 'M4 6h16M4 11h11M4 16h13M4 21h7',
    tabella: 'M3 5h18v14H3zM3 10h18M3 15h18M9 5v14',
    cerca: 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13zM16 16l5 5',
    pieno: 'M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5',
    scarica: 'M12 4v11M7 10l5 5 5-5M4 20h16',
    collega: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1.5 1.5M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1.5-1.5',
    piu: 'M12 5v14M5 12h14', meno: 'M5 12h14', reset: 'M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5',
    sinistra: 'M15 5l-7 7 7 7', destra: 'M9 5l7 7-7 7', chiudi: 'M6 6l12 12M18 6L6 18', avanti: 'M5 12h14M13 6l6 6-6 6',
  };
  A.icona = (n, cls) => `<svg class="${cls || 'icona'}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONE[n] || ''}"/></svg>`;

  A.TEMI = {
    pop: { n: 'Popolazione', breve: 'Quanti siamo, come cresciamo e invecchiamo, dove viviamo.', flag: ['SP.POP.TOTL', 'SP.POP.65UP.TO.ZS', 'SP.DYN.TFRT.IN'] },
    sal: { n: 'Salute', breve: 'Speranza di vita, mortalità, vaccinazioni, medici e posti letto.', flag: ['SP.DYN.LE00.IN', 'SH.DYN.MORT', 'SH.MED.PHYS.ZS'] },
    ist: { n: 'Istruzione', breve: 'Alfabetizzazione, iscrizioni a scuola e università, parità di genere.', flag: ['SE.ADT.LITR.ZS', 'SE.TER.ENRR', 'SE.PRM.CMPT.ZS'] },
    amb: { n: 'Ambiente e clima', breve: 'Gas serra, qualità dell’aria, foreste, aree protette, rischi.', flag: ['EN.GHG.ALL.PC.CE.AR5', 'EN.ATM.PM25.MC.M3', 'AG.LND.FRST.ZS'] },
    ene: { n: 'Energia', breve: 'Accesso all’elettricità, fonti di produzione, rinnovabili, consumi.', flag: ['EG.ELC.ACCS.ZS', 'EG.FEC.RNEW.ZS', 'EG.USE.ELEC.KH.PC'] },
    acq: { n: 'Acqua e servizi igienici', breve: 'Risorse idriche, prelievi, acqua potabile e servizi igienici sicuri.', flag: ['SH.H2O.SMDW.ZS', 'ER.H2O.FWST.ZS', 'SH.STA.SMSS.ZS'] },
    agr: { n: 'Agricoltura, territorio e pesca', breve: 'Superfici coltivate, produzione e rese, fertilizzanti, pesca.', flag: ['AG.LND.AGRI.ZS', 'AG.YLD.CREL.KG', 'ER.FSH.PROD.MT'] },
    dig: { n: 'Digitale e comunicazioni', breve: 'Internet, banda larga, telefonia mobile e fissa.', flag: ['IT.NET.USER.ZS', 'IT.CEL.SETS.P2', 'IT.NET.BBND.P2'] },
    eur: { n: 'Regioni europee', breve: 'Popolazione, economia, lavoro, istruzione, salute, società, digitale, turismo, trasporti, agricoltura e ambiente nelle regioni e province d’Europa (Eurostat), con gli indici di competitività, progresso sociale, qualità delle istituzioni e parità di genere e i pagamenti dei fondi europei (Commissione europea).', flag: ['EU_ECO_PIL_AB', 'EU_LAV_DIS', 'EU_SAL_VITA'] },
    arc: { n: 'Insiemi di dati', breve: 'FAOSTAT, OMS, OCSE, ONU e FMI: tutte le serie degli insiemi di dati dei lotti su agricoltura, alimentazione, emissioni, commercio, salute, istruzione e clima.', flag: [] },
  };
  A.ORDINE_TEMI = ['pop', 'sal', 'ist', 'amb', 'ene', 'acq', 'agr', 'dig', 'eur', 'arc'];

  // sottogruppi degli indicatori: per ogni tema, in ordine, [nome, espressione sul codice]
  A.SOTTOGRUPPI = {
    pop: [['Struttura per età', /^SP\.POP\.(0014|1564|65UP|DPND)/], ['Crescita, nascite e decessi', /^(SP\.POP\.TOTL$|SP\.POP\.GROW|SP\.DYN\.(CBRT|CDRT|TFRT)|SP\.ADO|SP\.POP\.TOTL\.FE)/], ['Città e campagna', /^(SP\.URB|SP\.RUR|EN\.POP\.DNST)/]],
    sal: [['Speranza di vita', /^SP\.DYN\.LE00/], ['Mortalità e malattie', /^(SH\.DYN\.MORT|SP\.DYN\.IMRT|SH\.STA\.MMRT|SH\.TBS)/], ['Vaccinazioni', /^SH\.IMM/], ['Sistema sanitario', /^SH\.MED/], ['Nutrizione dei bambini', /^SH\.STA\.(STNT|WAST|OWGH)/], ['Contraccezione', /^SP\.DYN\.CONU/]],
    ist: [['Parità di genere', /\.FM\.ZS$/], ['Alfabetizzazione', /^SE\.ADT/], ['Iscrizioni e completamento', /^(SE\.PRM|SE\.SEC|SE\.TER|SE\.COM)/], ['Apprendimento', /^SE\.LPV/]],
    amb: [['Gas serra', /^EN\.GHG/], ['Qualità dell’aria', /^EN\.ATM/], ['Foreste e aree protette', /^(AG\.LND\.FRST|ER\.LND|ER\.MRN|ER\.PTD)/], ['Specie minacciate', /^EN\.(BIR|FSH)/], ['Rischi e clima', /^(EN\.CLC|AG\.LND\.EL5M|AG\.LND\.PRCP)/]],
    ene: [['Accesso all’energia', /^EG\.(ELC|CFT)\.ACCS/], ['Produzione elettrica per fonte', /^EG\.ELC\.(COAL|NGAS|PETR|FOSL|NUCL|HYRO|RNEW|RNWX)/], ['Consumi e importazioni', /^EG\.(USE|FEC|IMP|ELC\.LOSS)/]],
    acq: [['Risorse e stress idrico', /^ER\.H2O\.(INTR|FWST)/], ['Prelievi di acqua', /^ER\.H2O\.FW/], ['Acqua potabile e servizi igienici', /^SH\.(H2O|STA\.(BASS|SMSS))/]],
    agr: [['Superfici', /^(AG\.LND|AG\.SRF)/], ['Produzione e rese', /^(AG\.PRD|AG\.YLD)/], ['Fertilizzanti', /^AG\.CON/], ['Pesca e acquacoltura', /^ER\.FSH/]],
    dig: [['Internet', /^IT\.NET/], ['Telefonia', /^IT\.(CEL|MLT)/]],
    eur: [['Popolazione e densità', /^EU_(POP|DENS|AGR_AREA)/], ['Struttura per età', /^EU_(QUOTA|STR_)/], ['Nascite, decessi, fecondità e migrazioni', /^EU_(NATI|MORTI|TOTFERRT|AGEMOTH|MEDAGEMOTH|DIN_)/],
      ['Proiezioni di popolazione al 2100 (Eurostat)', /^EU_PRJ_/],
      ['Economia', /^EU_ECO_/], ['Lavoro', /^EU_LAV_/], ['Istruzione e formazione', /^EU_IST_/], ['Ricerca, innovazione e cultura', /^EU_RIC_/], ['Salute', /^EU_SAL_/],
      ['Condizioni di vita e sicurezza', /^EU_SOC_/], ['Digitale', /^EU_DIG_/], ['Turismo', /^EU_TUR_/], ['Trasporti', /^EU_TRA_/], ['Agricoltura, territorio e clima', /^EU_AGR_/],
      ['Ambiente, gas serra ed energia rinnovabile', /^EU_(AMB|CLI|ENE)_/], ['Imprese', /^EU_IMP_/],
      ['Competitività regionale: indice RCI 2.0 (Commissione europea)', /^EU_RCI_/], ['Progresso sociale: indice EU-SPI (Commissione europea)', /^EU_SPI/],
      ['Qualità delle istituzioni: indice EQI (Commissione europea)', /^EU_EQI_/], ['Parità di genere: monitor regionale 2021 (Commissione europea)', /^EU_GEN_/],
      ['Fondi europei: pagamenti per regione (Commissione europea)', /^EU_FON_/]],
  };
  A.sottogruppo = (i) => { const r = (A.SOTTOGRUPPI[i.t] || []).find(([, re]) => re.test(i.c)); return r ? r[0] : 'Altri indicatori'; };

  /* macro argomenti degli insiemi di dati (per codice FAOSTAT o per fonte) */
  A.GRUPPI_ARCHIVI = [
    ['Produzione agricola, prezzi e valore', ['QCL', 'QI', 'QV', 'PA', 'PP', 'CP', 'PD', 'PE', 'GFDI', 'WCAD', 'MK', 'CS']],
    ['Bilanci alimentari, disponibilità e dieta', ['FBS', 'FBSH', 'SUA', 'SCL', 'CB', 'CBH', 'FS', 'HCES', 'FDIQ', 'MDDW', 'CAHD', 'HS']],
    ['Commercio agricolo', ['TCL', 'TCLI', 'TI', 'TM', 'FT']],
    ['Fertilizzanti, pesticidi, terreni e bioenergia', ['RFB', 'RFN', 'RFM', 'RA', 'RP', 'RT', 'ESB', 'RL', 'LC', 'RM', 'RY', 'BE']],
    ['Emissioni, clima e allevamenti', ['EI', 'EM', 'GPP', 'GLE', 'GCE', 'GF', 'GI', 'GN', 'GV', 'GT', 'EMN', 'EK', 'ET']],
    ['Foreste', ['FO', 'FOP']],
    ['Popolazione, lavoro e condizioni di vita rurali', ['OA', 'OEA', 'OER', 'RLIS', 'SXS', 'SDGB']],
    ['Aiuti, investimenti e ricerca agricola', ['FA', 'EA', 'FDI', 'IC', 'IG', 'AE', 'AF']],
  ];
  A.GRUPPI_FONTI = { WHO: 'Salute (OMS)', OECD: 'Istruzione (OCSE)', UNSD: 'Annuario statistico ONU', IMF: 'Clima ed economia (FMI)', DATA_EUROPA: 'Dati comunali (data.europa.eu)' };
  A.gruppoArchivio = (a) => {
    if (A.GRUPPI_FONTI[a.src]) return A.GRUPPI_FONTI[a.src];
    if (/^OCSE/.test(a.fonte)) return 'Istruzione (OCSE)';
    const g = A.GRUPPI_ARCHIVI.find(([, codici]) => codici.includes(a.cod));
    return g ? g[0] : 'Altri insiemi di dati';
  };
  // contrassegni delle osservazioni negli insiemi di dati (FAOSTAT e altre fonti)
  A.FLAG = { A: 'dato ufficiale', E: 'stima della fonte', I: 'valore imputato dalla fonte', X: 'dato di organizzazione internazionale', M: 'dato mancante', F: 'previsione', T: 'dato non ufficiale', P: 'provvisorio', O: 'valore mancante', K: 'serie interrotta', Q: 'dato non ufficiale', Fc: 'valore calcolato', B: 'interruzione della serie' };
  A.VISTE = [['andamento', 'Andamento'], ['mappa', 'Mappa'], ['classifica', 'Classifica'], ['tabella', 'Tabella']];
  A.AREE = {
    mondo: { n: 'Mondo' }, europa: { n: 'Europa', b: [-25, 34, 45, 71] }, africa: { n: 'Africa', b: [-19, -36, 53, 38] },
    asia: { n: 'Asia', b: [26, -11, 150, 56] }, nordamerica: { n: 'America settentrionale e centrale', b: [-168, 7, -52, 72] },
    sudamerica: { n: 'America meridionale', b: [-92, -56, -33, 13] }, oceania: { n: 'Oceania', b: [110, -48, 180, 0] },
  };
  A.LIVELLI = ['Paesi (NUTS 0)', 'Macroregioni (NUTS 1)', 'Regioni (NUTS 2)', 'Province e aree (NUTS 3)'];
  A.PRESET = [
    { n: 'Friuli Venezia Giulia e vicini', ids: ['EU:ITH4', 'EU:ITH3', 'EU:AT21', 'EU:SI04', 'EU:IT'] },
    { n: 'Province del Friuli Venezia Giulia', ids: ['EU:ITH41', 'EU:ITH42', 'EU:ITH43', 'EU:ITH44', 'EU:ITH4'] },
    { n: 'Regioni italiane', ids: ['EU:ITH4', 'EU:ITH3', 'EU:ITC4', 'EU:ITI4', 'EU:ITF3', 'EU:ITG1', 'EU:IT'] },
    { n: 'Italia e grandi paesi europei', ids: ['ITA', 'DEU', 'FRA', 'ESP', 'POL', 'EUU'] },
    { n: 'Italia e vicini', ids: ['ITA', 'FRA', 'CHE', 'AUT', 'SVN'] },
    { n: 'Grandi economie del mondo', ids: ['ITA', 'USA', 'CHN', 'IND', 'JPN', 'BRA'] },
    { n: 'Regioni del mondo', ids: ['SSF', 'ECS', 'SAS', 'EAS', 'LCN', 'NAC', 'MEA', 'WLD'] },
  ];
  A.PREDEF = { ind: 'SP.DYN.LE00.IN', sel: ['ITA', 'DEU', 'FRA', 'ESP', 'USA', 'CHN'], eu: { ind: 'EU_QUOTA_Y_GE65', sel: ['EU:ITH4', 'EU:ITH3', 'EU:AT21', 'EU:SI04', 'EU:IT'] } };
  A.STORIE = [
    { c: 'EU_ECO_PIL_AB', t: 'PIL per abitante in Friuli Venezia Giulia', k: 'fvg' },
    { c: 'EU_LAV_DIS', t: 'Disoccupazione in Friuli Venezia Giulia', k: 'fvg', basso: true },
    { c: 'SP.DYN.LE00.IN', t: 'Speranza di vita in Italia', k: 'it' },
    { c: 'EU_QUOTA_Y_GE65', t: 'Over 65 in Friuli Venezia Giulia', k: 'fvg' },
    { c: 'EU_IST_LAUREATI', t: 'Laureati in Friuli Venezia Giulia', k: 'fvg' },
    { c: 'EU_TUR_NOTTI', t: 'Presenze turistiche in Friuli Venezia Giulia', k: 'fvg' },
    { c: 'EU_RCI_TOT', t: 'Competitività del Friuli Venezia Giulia (indice RCI, media UE = 100)', k: 'fvg' },
    { c: 'SP.POP.65UP.TO.ZS', t: 'Italiani con 65 anni e oltre', k: 'it' },
    { c: 'SP.DYN.TFRT.IN', t: 'Figli per donna in Italia', k: 'it', basso: true },
    { c: 'IT.NET.USER.ZS', t: 'Italiani che usano Internet', k: 'it' },
    { c: 'EG.FEC.RNEW.ZS', t: 'Rinnovabili sui consumi finali di energia', k: 'it' },
    { c: 'EN.GHG.ALL.PC.CE.AR5', t: 'Gas serra per abitante in Italia', k: 'it', basso: true },
    { c: 'EU_TOTFERRT', t: 'Figli per donna in Friuli Venezia Giulia', k: 'fvg', basso: true },
  ];
  A.RITARDO_MAX = 10;

  /* ---------- stato ---------- */
  A.S = {
    ind: A.PREDEF.ind, sel: A.PREDEF.sel.slice(), vista: 'andamento', anno: null, area: 'mondo', livello: 2, paeseEU: '',
    log: {}, ultimo: false, aggregati: false, zoom: null, nBarre: 25, ordine: 'desc', ordTab: { col: 'v', dir: 'desc' },
    sfondo: true, inRiproduzione: false, regione: null, temaConf: 'sal',
  };
  const CHIAVI = ['sel', 'ultimo', 'aggregati', 'area', 'livello', 'paeseEU', 'temaConf', 'sfondo'];
  A.leggiStato = () => { try { const s = JSON.parse(localStorage.getItem('atlante-v2') || 'null'); if (s) CHIAVI.forEach((k) => { if (s[k] !== undefined) A.S[k] = s[k]; }); } catch (e) { /* memoria non disponibile */ } };
  A.salvaStato = () => { try { const o = {}; CHIAVI.forEach((k) => { o[k] = A.S[k]; }); localStorage.setItem('atlante-v2', JSON.stringify(o)); } catch (e) { /* ignora */ } };

  /* ---------- formati ---------- */
  const nf = (o) => new Intl.NumberFormat('it-IT', o);
  const F = { int: nf({ maximumFractionDigits: 0, useGrouping: 'always' }), d1: nf({ maximumFractionDigits: 1 }), d2: nf({ maximumFractionDigits: 2 }), s3: nf({ maximumSignificantDigits: 3 }) };
  A.F = F;
  A.fmt = function fmt(v) {
    if (v == null || Number.isNaN(v)) return 'n.d.';
    if (v < 0) return '−' + fmt(-v);
    const a = Math.abs(v);
    if (a >= 1e9) { const t = F.s3.format(v / 1e9); return t + (t === '1' ? ' miliardo' : ' miliardi'); }
    if (a >= 1e6) { const t = F.s3.format(v / 1e6); return t + (t === '1' ? ' milione' : ' milioni'); }
    if (a >= 1000) return F.int.format(v);
    if (a >= 10) return F.d1.format(v);
    if (a >= 1) return F.d2.format(v);
    if (a === 0) return '0';
    return F.s3.format(v);
  };
  A.fmtAsse = (v) => {
    const a = Math.abs(v);
    if (a >= 1e9) return F.s3.format(v / 1e9) + ' mld';
    if (a >= 1e6) return F.s3.format(v / 1e6) + ' mln';
    if (a >= 1000) return F.int.format(v);
    return F.s3.format(v);
  };
  const MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'];
  A.data = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ''); return m ? `${+m[3]} ${MESI[+m[2] - 1]} ${m[1]}` : (s || 'n.d.'); };
  A.norm = (s) => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  A.esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  A.ordinale = (k, femminile) => `${k}${femminile ? 'ª' : 'º'}`;

  /* ---------- colori dal tema ---------- */
  A.colori = {};
  A.leggiColori = () => {
    const cs = getComputedStyle(document.documentElement), g = (n) => cs.getPropertyValue(n).trim();
    A.colori = { seq0: g('--seq-0'), seq1: g('--seq-1'), grafite: g('--grafite'), grafite2: g('--grafite-2'), carta: g('--carta'), vuoto: g('--vuoto'), trama: g('--vuoto-trama'), altro: g('--carta-3'), neutro: g('--grafite-3'), griglia: g('--griglia') };
    A.META.regioni.forEach((r, i) => { A.colori[r.k] = g('--r' + (i + 1)); });
    A.ORDINE_TEMI.forEach((k) => { A.colori['t_' + k] = g('--t-' + k); });
  };
  A.coloreRegione = (id) => {
    const t = A.T[id]; if (!t) return A.colori.grafite;
    if (t.r) return A.colori[t.r];
    return t.k === 'agg' || t.k === 'agg_eu' || t.k === 'aggf' ? A.colori.grafite : A.colori.neutro;
  };
  A.eAggregato = (id) => { const t = A.T[id]; return !!t && (t.k === 'agg' || t.k === 'agg_eu' || t.k === 'aggf'); };

  /* ---------- dati ---------- */
  A.T = {}; A.PAESI = []; A.IND = {}; A.REG = {}; A.ARC = {}; A.NUTS0 = {}; A.PANO = {};
  const cache = {}, cacheNote = {}, noteRisolte = {}, cacheArch = {}, cacheProf = {}, statistiche = {};
  A.cache = cache;
  A.fam = (cod) => (A.IND[cod] ? A.IND[cod].fam : 'wb');
  A.famTerr = (cod) => (A.fam(cod) === 'eu' ? 'nuts' : 'paesi');
  A.temaDi = (cod) => (A.IND[cod] ? (A.IND[cod].fam === 'arc' ? 'arc' : A.IND[cod].t) : 'pop');
  const caricaJson = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); });
  A.caricaJson = caricaJson;
  A.carica = async (cod) => {
    if (!cache[cod]) {
      const i = A.IND[cod];
      if (i && i.fam === 'arc') { const m = /^A:([^:]+):(\d+)$/.exec(cod); cache[cod] = caricaGz(`dati/archivi/${m[1]}/${m[2]}.json.gz`).then((d) => { if (d.f) { noteRisolte[cod] = {}; Object.entries(d.f).forEach(([t, anni]) => { noteRisolte[cod][t] = {}; Object.entries(anni).forEach(([y, fl]) => { noteRisolte[cod][t][y] = [A.FLAG[fl] ? `${fl}: ${A.FLAG[fl]}` : fl, null]; }); }); } return d; }); }
      else cache[cod] = caricaJson(i && i.fam === 'eu' ? `dati/eurostat/${cod}.json` : `dati/indicatori/${cod}.json`);
    }
    const d = await cache[cod];
    cache[cod + '_r'] = d;
    return d;
  };
  // file compressi (gzip) degli insiemi di dati: decompressione nel browser, o lettura diretta se il server li ha già decompressi
  const caricaGz = async (u) => {
    const r = await fetch(u); if (!r.ok) throw new Error(u);
    const buf = await r.arrayBuffer(); const b = new Uint8Array(buf);
    if (b.length > 2 && b[0] === 0x1f && b[1] === 0x8b) { const testo = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text(); return JSON.parse(testo); }
    return JSON.parse(new TextDecoder().decode(buf));
  };
  A.caricaGz = caricaGz;
  A.dati = (cod) => cache[cod + '_r'];
  A.caricaNote = (cod) => {
    const i = A.IND[cod];
    if (!i || !i.note) return Promise.resolve(null);
    if (i.fam === 'arc') return A.carica(cod).then(() => noteRisolte[cod] || null);
    if (!cacheNote[cod]) cacheNote[cod] = caricaJson(`dati/note/${cod}.json`).catch(() => null).then((n) => { noteRisolte[cod] = n; return n; });
    return cacheNote[cod];
  };
  A.notaDi = (cod, id, y) => { const n = noteRisolte[cod]; const x = y && n && n[id] && n[id][y]; return x ? [x[0], x[1]].filter(Boolean).join(' · ') : null; };
  A.caricaArchivio = (f) => { if (!cacheArch[f]) cacheArch[f] = caricaJson(`dati/archivi/${f}.json`); return cacheArch[f]; };
  A.caricaProfilo = (id) => {
    const t = A.T[id]; if (!t || t.k === 'aggf' || t.k === 'storico') return Promise.resolve(null);
    const u = t.k === 'nuts' ? `dati/profili/nuts_${t.p}.json` : `dati/profili/${id}.json`;
    if (!cacheProf[u]) cacheProf[u] = caricaJson(u).catch(() => null);
    return cacheProf[u].then((p) => (p && t.k === 'nuts' ? { id, ind: p[id] || {} } : p));
  };
  // una serie di un insieme di dati diventa un indicatore con codice A:<file>:<indice>; i valori stanno in un file a parte
  A.registraSerie = async (id) => {
    if (A.IND[id]) return true;
    const m = /^A:([^:]+):(\d+)$/.exec(id); if (!m || !A.ARC[m[1]]) return false;
    const a = await A.caricaArchivio(m[1]); const s = a.s[+m[2]]; if (!s) return false;
    const c = A.ARC[m[1]];
    A.IND[id] = { c: id, fam: 'arc', t: 'arc', n: s.l, u: s.u || 'unità non indicata', en: `${c.en}: ${s.l}`, y0: s.y0, y1: s.y1, arch: c, interi: s.i, lotto: c.lotto, agg: c.agg, url: c.url, note: true, nterr: s.n, dims: s.dims, cods: s.cod };
    return true;
  };
  A.universo = (cod) => {
    const f = A.fam(cod), S = A.S;
    if (f === 'eu') return A.META.territori.filter((t) => t.k === 'nuts' && t.l === S.livello && (!S.paeseEU || t.p === S.paeseEU));
    if (f === 'arc') { const a = A.IND[cod].arch; const aggr = new Set(a.aggr || []); return a.terr.filter((id) => A.T[id] && !aggr.has(id)).map((id) => A.T[id]); }
    return A.PAESI;
  };
  A.aggregatiDi = (cod) => {
    const f = A.fam(cod);
    if (f === 'eu') return A.META.territori.filter((t) => t.k === 'agg_eu');
    if (f === 'arc') return (A.IND[cod].arch.aggr || []).map((id) => A.T[id]).filter(Boolean);
    return A.META.territori.filter((t) => t.k === 'agg');
  };
  // traduce un territorio selezionato nel territorio equivalente della famiglia dell'indicatore
  A.idPer = (cod, id) => {
    const t = A.T[id]; if (!t) return null;
    const f = A.fam(cod);
    if (f === 'eu') {
      if (t.k === 'nuts' || t.k === 'agg_eu') return id;
      if (t.k === 'paese') return A.NUTS0[id] || null;
      if (id === 'EUU') return 'EU:EU27_2020';
      return null;
    }
    if (t.k === 'nuts') return t.l === 0 ? t.p : null;
    if (t.k === 'agg_eu') return t.cod === 'EU27_2020' ? 'EUU' : null;
    if (f === 'arc') return A.IND[cod].arch.terr.includes(id) ? id : null;
    return t.k === 'paese' || t.k === 'agg' ? id : null;
  };
  A.selezionato = (cod, id) => A.S.sel.some((s) => A.idPer(cod, s) === id);
  A.stat = (cod) => {
    const S = A.S, chiave = A.fam(cod) === 'eu' ? `${cod}|${S.livello}|${S.paeseEU}` : cod;
    if (!statistiche[chiave]) statistiche[chiave] = calcolaStatistiche(A.dati(cod), A.universo(cod));
    return statistiche[chiave];
  };
  function calcolaStatistiche(d, univ) {
    const vals = [], perAnno = new Array(d.y1 - d.y0 + 1).fill(0);
    for (const p of univ) { const a = d.d[p.id]; if (!a) continue; a.forEach((v, i) => { if (v != null) { vals.push(v); perAnno[i]++; } }); }
    if (!vals.length) return { min: 0, max: 1, p02: 0, p98: 1, positivi: false, perAnno, logAuto: false, vuoto: true };
    vals.sort((x, y) => x - y);
    const q = (p) => vals[Math.min(vals.length - 1, Math.max(0, Math.round(p * (vals.length - 1))))];
    const min = vals[0], max = vals[vals.length - 1], positivi = min > 0;
    return { min, max: max === min ? min + 1 : max, p02: q(0.02), p98: q(0.98), positivi, perAnno, logAuto: positivi && q(0.95) / q(0.05) > 150 };
  }
  A.valore = (d, id, anno) => {
    const a = d && id && d.d[id]; if (!a) return null;
    const i = anno - d.y0;
    if (i >= 0 && i < a.length && a[i] != null) return { v: a[i], y: anno };
    if (A.S.ultimo) for (let k = 1; k <= A.RITARDO_MAX; k++) { const j = i - k; if (j >= 0 && j < a.length && a[j] != null) return { v: a[j], y: anno - k }; }
    return null;
  };
  A.ultimo = (d, id) => { const a = d && d.d[id]; if (!a) return null; for (let i = a.length - 1; i >= 0; i--) if (a[i] != null) return { v: a[i], y: d.y0 + i }; return null; };
  A.usaLog = (cod) => { const st = A.stat(cod); if (!st.positivi) return false; return A.S.log[cod] != null ? A.S.log[cod] : st.logAuto; };
  A.descriviTerritorio = (t) => {
    if (t.k === 'nuts') return `NUTS ${t.l}${t.l ? ' · ' + (A.T[t.p] ? A.T[t.p].n : t.p) : ''}`;
    if (t.k === 'agg') return 'aggregato Banca Mondiale';
    if (t.k === 'agg_eu') return 'aggregato Eurostat';
    if (t.k === 'aggf') return 'aggregato FAOSTAT';
    if (t.k === 'storico') return 'codice FAOSTAT';
    return t.r ? A.REG[t.r].n : 'senza regione';
  };
  A.nomeRif = (id) => (id === 'WLD' ? 'Mondo' : id === 'EU:EU27_2020' ? 'Unione europea a 27' : A.T[id] ? A.T[id].n : id);

  /* ---------- componenti ---------- */
  let toastTimer;
  A.toast = (testo) => { const t = $('#toast'); t.textContent = testo; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 2400); };

  const sug = () => $('#suggerimento');
  let sugTimer;
  A.mostraSuggerimento = (ev, html) => {
    clearTimeout(sugTimer);
    const s = sug(); s.innerHTML = html; s.hidden = false;
    const w = s.offsetWidth, h = s.offsetHeight, vw = innerWidth, vh = innerHeight;
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + w > vw - 8) x = ev.clientX - w - 14;
    if (y + h > vh - 8) y = ev.clientY - h - 14;
    s.style.left = Math.max(8, x) + 'px'; s.style.top = Math.max(8, y) + 'px';
    if (ev.pointerType === 'touch') sugTimer = setTimeout(A.nascondiSuggerimento, 2800);
  };
  A.nascondiSuggerimento = () => { sug().hidden = true; };
  A.intestazioneSug = (id) => { const t = A.T[id]; return `<div class="suggerimento__nome"><span class="pallino" style="background:${A.coloreRegione(id)}"></span>${A.esc(t.n)}</div><div class="suggerimento__riga"><span>${A.esc(A.descriviTerritorio(t))}</span></div>`; };
  A.rigaValore = (cod, id) => {
    const d = A.dati(cod), r = A.valore(d, id, A.S.anno), i = A.IND[cod], nota = A.notaDi(cod, id, r && r.y);
    return `${r ? `<div class="suggerimento__valore">${A.fmt(r.v)}</div><div class="suggerimento__riga"><span>${A.esc(i.u)}</span></div>${r.y !== A.S.anno ? `<div class="suggerimento__nota">Ultimo dato disponibile: ${r.y}</div>` : ''}` : `<div class="suggerimento__vuoto">Dato mancante nel ${A.S.anno}</div>`}${nota ? `<div class="suggerimento__nota">Nota della fonte: ${A.esc(nota)}</div>` : ''}`;
  };

  // numeri che salgono fino al valore finale
  A.animaNumero = (el, valore, formatta) => {
    if (A.ridotto.matches || valore == null || !isFinite(valore)) { el.textContent = formatta(valore); return; }
    const t0 = performance.now(), durata = 750;
    const passo = (t) => { const p = Math.min(1, (t - t0) / durata), e = 1 - Math.pow(1 - p, 3); el.textContent = formatta(valore * e); if (p < 1) requestAnimationFrame(passo); else el.textContent = formatta(valore); };
    requestAnimationFrame(passo);
  };

  // miniserie: linea con area leggera, ultimo punto in evidenza; un riferimento tratteggiato facoltativo
  const osservatore = 'IntersectionObserver' in window ? new IntersectionObserver((voci) => voci.forEach((v) => { if (v.isIntersecting) { v.target.classList.add('visto'); osservatore.unobserve(v.target); } }), { rootMargin: '40px' }) : null;
  A.sparkline = (el, o) => {
    const w = o.w || 120, h = o.h || 40, m = 3;
    const serie = [o.valori, o.rif && o.rif.valori].filter(Boolean);
    const tutte = serie.flat().filter((v) => v != null);
    if (!tutte.length) { el.innerHTML = ''; return; }
    const y0 = Math.min(o.y0, o.rif ? o.rif.y0 : o.y0);
    const y1 = Math.max(o.y0 + o.valori.length - 1, o.rif ? o.rif.y0 + o.rif.valori.length - 1 : 0);
    const x = d3.scaleLinear().domain([y0, Math.max(y1, y0 + 1)]).range([m, w - m]);
    const ext = d3.extent(tutte);
    const y = d3.scaleLinear().domain(ext[0] === ext[1] ? [ext[0] - 1, ext[1] + 1] : ext).range([h - m, m]);
    const linea = (yy0) => d3.line().defined((v) => v != null).x((v, i) => x(yy0 + i)).y((v) => y(v));
    const area = d3.area().defined((v) => v != null).x((v, i) => x(o.y0 + i)).y0(h - m).y1((v) => y(v));
    let k = o.valori.length - 1; while (k >= 0 && o.valori[k] == null) k--;
    const col = o.colore || 'currentColor';
    el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
      ${o.rif ? `<path class="traccia traccia--rif" d="${linea(o.rif.y0)(o.rif.valori) || ''}"/>` : ''}
      <path class="area" fill="${col}" d="${area(o.valori) || ''}"/>
      <path class="traccia" stroke="${col}" d="${linea(o.y0)(o.valori) || ''}"/>
      ${k >= 0 ? `<circle class="punto" cx="${x(o.y0 + k)}" cy="${y(o.valori[k])}" r="2.8" fill="${col}"/>` : ''}
    </svg>`;
    if (o.anima !== false && osservatore && !A.ridotto.matches) {
      const p = el.querySelector('.traccia:not(.traccia--rif)');
      if (p) { const L = p.getTotalLength ? p.getTotalLength() : 0; if (L) { p.style.strokeDasharray = L; p.style.strokeDashoffset = L; p.style.transition = 'stroke-dashoffset .9s ease-out'; el.classList.add('mini--pronta'); const avvia = () => { p.style.strokeDashoffset = 0; }; new MutationObserver((m2, obs) => { if (el.classList.contains('visto')) { avvia(); obs.disconnect(); } }).observe(el, { attributes: true, attributeFilter: ['class'] }); osservatore.observe(el); } }
    }
  };

  // casella con tendina di scelta: cerca(q) restituisce gruppi [{titolo, voci:[{id, html, testo}]}]
  A.combobox = (o) => {
    const input = o.input, lista = o.lista;
    let voci = [], attivo = -1, aperta = false;
    input.setAttribute('role', 'combobox'); input.setAttribute('aria-autocomplete', 'list'); input.setAttribute('aria-expanded', 'false');
    const chiudi = () => { lista.hidden = true; aperta = false; attivo = -1; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); };
    const disegna = () => {
      const gruppi = o.cerca(input.value.trim());
      voci = []; lista.innerHTML = '';
      gruppi.forEach((g) => {
        if (!g.voci.length) return;
        if (g.titolo) { const li = document.createElement('li'); li.className = 'gruppo'; li.textContent = g.titolo; lista.appendChild(li); }
        g.voci.forEach((v) => {
          const li = document.createElement('li'); li.setAttribute('role', 'option'); li.id = lista.id + '-' + voci.length; li.innerHTML = v.html;
          li.addEventListener('mousedown', (e) => { e.preventDefault(); scegli(v); });
          lista.appendChild(li); voci.push({ v, li });
        });
      });
      if (!voci.length) { const li = document.createElement('li'); li.className = 'vuoto'; li.textContent = o.vuoto || 'Nessun risultato'; lista.appendChild(li); }
      attivo = voci.length && input.value.trim() ? 0 : -1;
      evidenzia();
      lista.hidden = false; aperta = true; input.setAttribute('aria-expanded', 'true');
    };
    const evidenzia = () => { voci.forEach((x, i) => x.li.setAttribute('aria-selected', i === attivo ? 'true' : 'false')); if (attivo >= 0) { input.setAttribute('aria-activedescendant', voci[attivo].li.id); voci[attivo].li.scrollIntoView({ block: 'nearest' }); } };
    const scegli = (v) => { chiudi(); o.scegli(v); };
    input.addEventListener('input', disegna);
    input.addEventListener('focus', () => { if (o.apriSubito) disegna(); });
    input.addEventListener('click', () => { if (!aperta && o.apriSubito) disegna(); });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { chiudi(); return; }
      if (!aperta) { if (e.key === 'ArrowDown' || e.key === 'Enter') { disegna(); e.preventDefault(); } return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); attivo = Math.min(voci.length - 1, attivo + 1); evidenzia(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); attivo = Math.max(0, attivo - 1); evidenzia(); }
      else if (e.key === 'Enter') { e.preventDefault(); if (attivo >= 0) scegli(voci[attivo].v); else if (voci.length) scegli(voci[0].v); }
    });
    input.addEventListener('blur', () => setTimeout(chiudi, 150));
    return { chiudi, apri: disegna };
  };

  /* ---------- ricerca globale ---------- */
  A.indice = [];
  A.costruisciIndice = () => {
    const idx = [];
    Object.values(A.IND).filter((i) => i.fam !== 'arc').forEach((i) => idx.push({ tipo: 'ind', id: i.c, n: i.n, alt: `${i.en} ${i.c}`, tema: i.t, sotto: `${A.TEMI[i.t].n} · ${i.u}` }));
    A.META.territori.forEach((t) => { if (t.k === 'storico' || t.k === 'aggf') return; idx.push({ tipo: 'terr', id: t.id, n: t.n, alt: `${t.en} ${t.cod || t.id}`, sotto: A.descriviTerritorio(t), k: t.k, l: t.l }); });
    A.ORDINE_TEMI.forEach((k) => idx.push({ tipo: 'tema', id: k, n: A.TEMI[k].n, alt: A.TEMI[k].breve, sotto: 'tema' }));
    (A.META.archivi || []).forEach((a) => idx.push({ tipo: 'arch', id: a.f, n: a.n, alt: `${a.en} ${a.cod} ${a.fonte}`, sotto: `archivio ${a.fonte.replace(/ \(.*/, '')} · ${A.gruppoArchivio(a)}` }));
    idx.push({ tipo: 'pagina', id: 'scheda-fvg.html', n: 'Scheda: Friuli Venezia Giulia in Europa', alt: 'scheda fvg italia europa confronto', sotto: 'scheda' });
    idx.push({ tipo: 'pagina', id: '#/confronta', n: 'Confronta paesi e regioni', alt: 'confronto confronta', sotto: 'strumento' });
    // matrici bilaterali FAOSTAT: vista Partner
    [['TM', 'Partner: commercio di prodotti agricoli per paese partner', 'commercio scambi importazioni esportazioni prodotti agricoli trade matrix TM lotto 31'],
     ['RFM', 'Partner: commercio di fertilizzanti per paese partner', 'fertilizzanti concimi importazioni esportazioni fertilizers trade matrix RFM lotto 19'],
     ['EA', 'Partner: flussi di sviluppo verso l’agricoltura per donatore', 'aiuti donatori destinatari cooperazione sviluppo development flows EA lotto 26']]
      .forEach(([k, n, alt]) => idx.push({ tipo: 'pagina', id: `#/partner/${k}`, n, alt: `partner bilaterale matrice ${alt}`, sotto: 'vista Partner, FAOSTAT' }));
    A.indice = idx.map((v) => Object.assign(v, { nn: A.norm(v.n), na: A.norm(v.alt) }));
  };
  const ORD_TERR = { paese: 0, nuts: 1, agg: 2, agg_eu: 3 };
  const PAROLE_PARTNER = [
    [/^(commerc|scamb|import|esport|partner)/, 'TM', (n) => `Commercio di prodotti agricoli: ${n} e i suoi partner`],
    [/^(fertilizz|concim)/, 'RFM', (n) => `Commercio di fertilizzanti: ${n} e i suoi partner`],
    [/^(aiut|donat|destinat|cooperaz)/, 'EA', (n) => `Aiuti all’agricoltura ricevuti: ${n} e i suoi donatori`],
  ];
  A.cercaIndice = (q, limiti) => {
    const nq = A.norm(q); if (!nq) return [];
    const parole = nq.split(/\s+/).filter(Boolean);
    const punteggio = (v) => {
      let p = 0;
      for (const w of parole) { if (v.nn.startsWith(w)) p += 5; else if (v.nn.split(/[\s,()]+/).some((x) => x.startsWith(w))) p += 3; else if (v.nn.includes(w)) p += 2; else if (v.na.includes(w)) p += 1; else return 0; }
      if (v.tipo === 'terr') p += (3 - (ORD_TERR[v.k] ?? 3)) * 0.1 - (v.l || 0) * 0.02;
      return p;
    };
    const trov = A.indice.map((v) => ({ v, p: punteggio(v) })).filter((x) => x.p > 0).sort((a, b) => b.p - a.p || a.v.nn.length - b.v.nn.length);
    const per = {}; trov.forEach((x) => { (per[x.v.tipo] = per[x.v.tipo] || []).push(x.v); });
    // "Italia commercio", "fertilizzanti Francia", "aiuti Etiopia": collegamento diretto alla vista Partner del paese
    const conPartner = parole.map((w) => PAROLE_PARTNER.find(([re]) => re.test(w)));
    if (conPartner.some(Boolean) && conPartner.some((x) => !x)) {
      const resto = parole.filter((w, i) => !conPartner[i]);
      const paesi = A.indice.filter((v) => v.tipo === 'terr' && v.k === 'paese' && resto.every((w) => v.nn.split(/[\s,()]+/).some((x) => x.startsWith(w)) || v.na.includes(w))).slice(0, 2);
      const insiemi = [...new Set(conPartner.filter(Boolean))];
      const voci = paesi.flatMap((t) => insiemi.map(([, k, testo]) => ({ tipo: 'pagina', id: `#/partner/${k}?t=${t.id}`, n: testo(t.n), sotto: 'vista Partner, FAOSTAT' })));
      per.pagina = voci.concat(per.pagina || []);
    }
    const L = limiti || { terr: 6, ind: 7, tema: 3, arch: 3, pagina: 4 };
    return [['tema', 'Temi'], ['ind', 'Indicatori'], ['terr', 'Territori'], ['arch', 'Archivi'], ['pagina', 'Pagine']].map(([k, titolo]) => ({ titolo, voci: (per[k] || []).slice(0, L[k] || 0) }));
  };
  A.vociRicerca = (gruppi) => gruppi.map((g) => ({ titolo: g.titolo, voci: g.voci.map((v) => ({ id: v.id, v, html: v.tipo === 'terr' ? `<span class="pallino" style="background:${A.coloreRegione(v.id)}"></span><span>${A.esc(v.n)}</span><span class="tipo">${A.esc(v.sotto)}</span>` : v.tipo === 'ind' ? `${A.icona(v.tema, 'icona')}<span>${A.esc(v.n)}<span class="sotto">${A.esc(v.sotto)}</span></span>` : v.tipo === 'tema' ? `${A.icona(v.id, 'icona')}<span>${A.esc(v.n)}</span><span class="tipo">tema</span>` : `${A.icona(v.tipo === 'arch' ? 'arc' : 'cerca', 'icona')}<span>${A.esc(v.n)}<span class="sotto">${A.esc(v.sotto)}</span></span>` })) }));
  A.vaiA = (v) => {
    if (v.tipo === 'ind') A.vai(`#/i/${v.id}`);
    else if (v.tipo === 'terr') A.vai(`#/t/${v.id}`);
    else if (v.tipo === 'tema') A.vai(v.id === 'arc' ? '#/archivi' : `#/tema/${v.id}`);
    else if (v.tipo === 'arch') A.vai(`#/archivi/${v.id}`);
    else if (v.tipo === 'pagina') { if (v.id.startsWith('#')) A.vai(v.id); else location.href = v.id; }
  };

  /* ---------- testata ---------- */
  A.preparaTestata = () => {
    const input = $('#cerca'), lista = $('#cerca-risultati');
    lista.id = 'cerca-risultati';
    A.combobox({ input, lista, cerca: (q) => A.vociRicerca(A.cercaIndice(q)), vuoto: 'Nessun risultato: prova con un altro nome, anche in inglese', scegli: (x) => { input.value = ''; A.vaiA(x.v); } });
    document.addEventListener('keydown', (e) => { if (e.key === '/' && !e.target.closest('input, select, textarea, [contenteditable]')) { e.preventDefault(); input.focus(); } });
    // tendine della barra
    const apri = (btn, pannello) => {
      const on = () => !pannello.hidden;
      const chiudi = () => { pannello.hidden = true; btn.setAttribute('aria-expanded', 'false'); };
      btn.addEventListener('click', () => { const era = on(); document.querySelectorAll('.megamenu, .tendina').forEach((p) => { p.hidden = true; }); document.querySelectorAll('.nav__voce[aria-expanded]').forEach((b) => b.setAttribute('aria-expanded', 'false')); if (!era) { pannello.hidden = false; btn.setAttribute('aria-expanded', 'true'); } });
      document.addEventListener('click', (e) => { if (on() && !pannello.contains(e.target) && e.target !== btn && !btn.contains(e.target)) chiudi(); });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && on()) { chiudi(); btn.focus(); } });
      pannello.addEventListener('click', (e) => { if (e.target.closest('a')) chiudi(); });
    };
    const mega = $('#megamenu');
    mega.innerHTML = A.ORDINE_TEMI.map((k) => `<a class="megamenu__tema" data-tema="${k}" href="${k === 'arc' ? '#/archivi' : '#/tema/' + k}">${A.icona(k)}<strong>${A.esc(A.TEMI[k].n)}</strong><span>${A.esc(A.TEMI[k].breve)}</span></a>`).join('');
    apri($('#apri-temi'), mega);
    apri($('#apri-schede'), $('#tendina-schede'));
    // menu per telefono
    const mm = $('#menu-mobile'), hb = $('#apri-menu');
    mm.innerHTML = `<div class="menu-mobile__titolo">Temi</div>${A.ORDINE_TEMI.map((k) => `<a data-tema="${k}" href="${k === 'arc' ? '#/archivi' : '#/tema/' + k}">${A.icona(k)}${A.esc(A.TEMI[k].n)}</a>`).join('')}<div class="menu-mobile__titolo">Strumenti</div><a href="#/confronta">${A.icona('classifica')}Confronta paesi e regioni</a><a href="scheda-fvg.html">${A.icona('eur')}Scheda: Friuli Venezia Giulia in Europa</a><a href="#/t/ITA">${A.icona('mappa')}Profilo dell’Italia</a><a href="#/archivi">${A.icona('arc')}Insiemi di dati</a><a href="#/partner">${A.icona('mappa')}Partner: commercio, fertilizzanti e aiuti</a><a href="#/fonti">${A.icona('tabella')}Fonti e metodo</a>`;
    hb.addEventListener('click', () => { const era = !mm.hidden; mm.hidden = era; hb.setAttribute('aria-expanded', era ? 'false' : 'true'); });
    mm.addEventListener('click', (e) => { if (e.target.closest('a')) { mm.hidden = true; hb.setAttribute('aria-expanded', 'false'); } });
    addEventListener('scroll', () => { $('#testa').classList.toggle('scorre', scrollY > 4); }, { passive: true });
  };

  /* ---------- instradamento ---------- */
  A.rotta = () => { const h = location.hash.slice(1) || '/'; const [path, qs] = h.split('?'); return { parti: path.split('/').filter(Boolean), q: new URLSearchParams(qs || '') }; };
  A.vai = (hash) => { if (location.hash === hash) A.instrada(); else location.hash = hash; };
  A.sostituisci = (hash) => { try { history.replaceState(null, '', hash); } catch (e) { /* ignora */ } };
  A.pagine = {};
  let paginaCorrente = null;
  A.instrada = async () => {
    const { parti, q } = A.rotta();
    const nome = parti[0] || 'home';
    const f = A.pagine[nome] || A.pagine.home;
    const main = $('#contenuto');
    if (paginaCorrente && paginaCorrente.distruggi) { try { paginaCorrente.distruggi(); } catch (e) { /* ignora */ } }
    A.nascondiSuggerimento();
    document.querySelectorAll('.megamenu, .tendina').forEach((p) => { p.hidden = true; });
    $('#menu-mobile').hidden = true; $('#apri-menu').setAttribute('aria-expanded', 'false');
    const stessa = paginaCorrente && paginaCorrente.nome === nome && nome === 'i';
    try { paginaCorrente = await f(main, parti, q) || {}; paginaCorrente.nome = nome; } catch (e) { console.error(e); main.innerHTML = `<div class="entra prosa"><h1>Qualcosa non ha funzionato</h1><p>${A.esc(e.message)}</p><p><a href="#/">Torna alla prima pagina</a></p></div>`; }
    if (!stessa) window.scrollTo({ top: 0, behavior: 'auto' });
  };

  return A;
})();
