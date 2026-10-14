#!/usr/bin/env python3
"""Aggiorna la sezione «Strutture ricettive» (dati/strutture_ricettive.json) dalle fonti ufficiali, solo con dati certi.

Fonti:
- portale ufficiale PromoTurismoFVG (https://www.turismofvg.it/tfvgb/booking/search): l'elenco per tipologia dà gli
  identificativi delle strutture visibili; la scheda di ogni struttura (TFVGB/Strutture/<id>) dà denominazione,
  indirizzo, telefono, posta elettronica, sito, CIN (Codice identificativo nazionale) e numero di camere, letti e bagni;
- dati aperti della Regione FVG (dati.friuliveneziagiulia.it): i nove elenchi delle strutture ricettive, per le voci
  presenti nel solo registro regionale.

Regole («solo dati certi»):
- un campo cambia solo se la fonte ufficiale lo riporta in modo esplicito e diverso da quello salvato;
- gli indirizzi integrati a mano nel file di partenza (campo «Note integrazioni») non si toccano;
- un sito web corretto o tolto dopo la verifica dei collegamenti del 14 ottobre 2026 non torna al vecchio indirizzo
  che il portale continua a mostrare: cambia solo se il portale indica un indirizzo nuovo;
- camere, posti letto e bagni si aggiornano solo per le schede con «Camere, Letti, Bagni» (in tutte le 3.136 schede
  di questo tipo il file usa esattamente quei tre numeri); per campeggi, villaggi e marina una differenza finisce
  nell'elenco «da verificare» senza cambiare i numeri;
- i prezzi medi stimati si ricalcolano con le stesse formule e gli stessi parametri del file di partenza
  (verificato: le formule riproducono tutti i 3.184 valori del file);
- una struttura nuova entra quando compare nell'elenco ufficiale e la sua scheda si legge; il comune è quello del
  codice ISTAT contenuto nel CIN (stesso metodo del file di partenza); senza CIN il comune resta da verificare;
- una struttura esce solo se manca dall'elenco ufficiale completo e la sua scheda non esiste più per due controlli
  mensili di fila;
- le voci del solo registro cambiano solo quando la Regione ripubblica i suoi elenchi: il confronto è con la copia
  salvata in dati/strutture_ricettive_fonti.json;
- se le fonti rispondono in modo anomalo (elenco ufficiale più corto del 95 per cento di quello attuale, oltre il
  10 per cento di schede illeggibili, oltre il 3 per cento di strutture da togliere) non cambia nulla e il flusso
  termina con errore.

Usa solo la libreria standard di Python.
Uso: python scripts/aggiorna_strutture.py [--prova] [--limite N] [--solo-registro] [--pausa SECONDI]
"""
import argparse, copy, datetime, http.cookiejar, html, json, math, re, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FILE = RADICE / 'dati' / 'strutture_ricettive.json'
FONTI = RADICE / 'dati' / 'strutture_ricettive_fonti.json'
PORTALE = 'https://www.turismofvg.it'
UA = 'Mozilla/5.0 (compatible; AtlanteFVG/1.0; +https://atlantefvg.it/)'
OGGI = datetime.date.today().isoformat()
ESCLUSE = {2540}
SENZA_ELENCO = False  # solo per le prove (--senza-elenco)  # «Struttura di test» del portale, esclusa anche dal file di partenza

# categorie del portale (valore del campo «Cat» della ricerca) e tipologia usata nel file
CATEGORIE = {1: 'Affittacamere', 2: 'Agriturismo (alloggio)', 3: 'Albergo diffuso', 4: 'Unità abitative / case e appartamenti vacanze',
             5: 'Bed & Breakfast', 6: 'Campeggio', 7: 'Country house', 8: 'Marina resort / dry marina', 10: 'Albergo / hotel',
             12: 'Residenza turistico-alberghiera', 13: 'Rifugio alpino / escursionistico', 14: 'Villaggio turistico', 15: 'Casa per ferie / struttura sociale'}
SOCIALI = {'Casa per ferie / struttura sociale', 'Ostello', 'Foresteria', 'Residenza universitaria / collegio'}
BASE_DI_TIPO = {'Affittacamere': 'Stima: camera doppia × indice zona', 'Bed & Breakfast': 'Stima: camera doppia × indice zona',
                'Agriturismo (alloggio)': 'Stima: camera doppia × indice zona', 'Albergo diffuso': 'Stima: camera doppia × indice zona',
                'Unità abitative / case e appartamenti vacanze': 'Stima: prezzo zona per alloggio',
                'Albergo / hotel': 'Stima: camera doppia hotel di zona', 'Residenza turistico-alberghiera': 'Stima: camera doppia hotel di zona',
                'Campeggio': 'Stima: prezzo per piazzola di zona', 'Villaggio turistico': 'Stima: prezzo per piazzola di zona',
                'Rifugio alpino / escursionistico': 'Tariffa CAI posto letto (mezza pensione ~60-80 €)',
                'Marina resort / dry marina': 'Stima: posto barca 12 m (Marina San Giusto)',
                **{t: 'Stima: posto letto in ostello/casa per ferie' for t in SOCIALI}}
PROVINCE = {'030': 'Udine', '031': 'Gorizia', '032': 'Trieste', '093': 'Pordenone'}
DATASET = {'jzsu-f86x': 'Bed and Breakfast', '6var-2hht': 'Affittacamere', 'yg8e-47jy': 'Alloggi Agrituristici', '69j3-9hcp': 'Alberghi Diffusi',
           'fiiw-i5su': 'Strutture Alberghiere e RTA', 'c2n8-qhph': 'Campeggi e Villaggi Turistici', 'qnwt-cjvq': 'Rifugi Alpini Escursionistici',
           'csiv-njht': 'Strutture ricettive a carattere Sociale', '6xk5-2p3e': 'Dry Marina e Marina Resort'}
TIPO_DATASET = {'jzsu-f86x': 'Bed & Breakfast', '6var-2hht': 'Affittacamere', 'yg8e-47jy': 'Agriturismo (alloggio)', '69j3-9hcp': 'Albergo diffuso',
                'fiiw-i5su': 'Albergo / hotel o RTA', 'c2n8-qhph': 'Campeggio / villaggio turistico', 'qnwt-cjvq': 'Rifugio alpino / escursionistico',
                'csiv-njht': 'Struttura a carattere sociale (ostello, casa per ferie)', '6xk5-2p3e': 'Marina resort / dry marina'}


def norm(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFD', str(s or '').lower()).encode('ascii', 'ignore').decode())


def pulisci(s):
    s = re.sub(r'\s+', ' ', html.unescape(str(s or ''))).strip()
    return s or None


# ---------------------------------------------------------------- rete
class Rete:
    def __init__(self, pausa):
        self.pausa = pausa
        self.nuova_sessione()

    def nuova_sessione(self):
        self.cookie = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie))

    def leggi(self, url, dati=None, tentativi=4):
        """Restituisce (indirizzo finale, testo). Riprova sugli errori di rete; solleva l'ultimo errore."""
        errore = None
        for t in range(tentativi):
            time.sleep(self.pausa if t == 0 else 10 * t)
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode(dati).encode() if dati else None, headers={'User-Agent': UA})
                with self.op.open(req, timeout=60) as r:
                    return r.geturl(), r.read().decode('utf-8', 'replace')
            except Exception as e:  # rete instabile o risposta vuota: riprova
                errore = e
        raise errore


# ---------------------------------------------------------------- portale
def elenco_categoria(rete, cat):
    """Identificativi delle strutture di una categoria. Restituisce (insieme, totale dichiarato dal portale).

    Il portale gira su più server e ciascuno ricorda la ricerca per conto suo: una pagina chiesta a un server che non
    conosce la ricerca torna vuota («pagina 2 di 0»). Per questo la ricerca si ripete più volte all'inizio e di nuovo a
    ogni pagina vuota. I server non ordinano allo stesso modo, quindi l'elenco si rilegge con ordinamenti diversi
    (nome, prezzo, stelle; crescente e decrescente) finché si raggiungono tutte le strutture dichiarate.
    """
    rete.nuova_sessione()
    modulo = {'id_canale': 0, 'No_Deciso': 'true', 'Aree': 0, 'LocalitaId': 0, 'Cat': cat, 'Classi': '', 'nome': ''}
    totale, pagine, ids = 0, 1, set()
    for _ in range(4):
        _, s = rete.leggi(PORTALE + '/TFVGB/Booking/Search', modulo)
        m = re.search(r'([\d.]+) (?:strutture trovate|structures found)', s)
        if m:
            totale = max(totale, int(m.group(1).replace('.', '')))
            pagine = max([pagine] + [int(x) for x in re.findall(r'Paginazione_New\?pagina=(\d+)', s)])
            ids |= set(int(x) for x in re.findall(r'/TFVGB/Strutture/(\d+)/', s))
    if not totale:
        return set(), 0
    for ordine, asc in ((0, 1), (1, 1), (1, 0), (2, 1), (2, 0), (0, 0)):
        if len(ids) >= totale:
            break
        for p in range(1, pagine + 1):
            trovati = set()
            for _ in range(8):
                _, s = rete.leggi(PORTALE + f'/TFVGB/Booking/Paginazione_New?pagina={p}&ordine={ordine}&asc={asc}')
                trovati = set(int(x) for x in re.findall(r'/TFVGB/Strutture/(\d+)/', s))
                if trovati:
                    break
                rete.leggi(PORTALE + '/TFVGB/Booking/Search', modulo)
            ids |= trovati
    return ids, totale


def leggi_scheda(s):
    """Campi di una scheda del portale (due impaginazioni: strutture e agriturismi). None se non è una scheda."""
    # impaginazione «agriturismi»: etichette in grassetto
    if 'c-poi__auxtexts' in s:
        h1 = re.search(r'<h1 class="c-poi_header__title">(.*?)</h1>', s, re.S)
        aux = re.search(r'<section class="c-poi__auxtexts">(.*?)</section>', s, re.S)
        if not h1 or not aux:
            return None
        campi = {}
        for k, v in re.findall(r'<strong>([^<]+)</strong><br>(.*?)<br>\s*<br>', aux.group(1), re.S):
            link = re.search(r"href='(?:mailto:)?([^']+)'", v)
            campi[INGLESE.get(k.strip(), k.strip())] = pulisci(link.group(1) if link else re.sub(r'<[^>]+>', '', v))
        allog = re.search(r'>(?:Alloggi|Accommodation)</h2>\s*<div class="c-poi_section__text">(.*?)</div>', s, re.S)
        kv = [(k.strip(), int(n)) for n, k in re.findall(r'(\d+)\s+([A-Za-zÀ-ú ]+?)\s*(?:<br>|$)', allog.group(1))] if allog else []
        return {'den': pulisci(re.sub(r'<[^>]+>', '', h1.group(1))), 'email': campi.get('Email'), 'tipo': None,
                'ind': campi.get('Indirizzo'), 'cap': campi.get('CAP'), 'loc': campi.get('Località'), 'tel': campi.get('Telefono'),
                'cin': campi.get('CIN'), 'web': campi.get('Web'), 'kv': kv}
    # impaginazione «strutture»
    m = re.search(r'/InfoRequest/InfoAlloggi\?([^"\']+)', s)
    blocco = re.search(r'<div class="indirizzo">(.*?)</div>', s, re.S)
    if not m or not blocco:
        return None
    q = urllib.parse.parse_qs(html.unescape(m.group(1)))
    b = re.sub(r'<h3>.*?</h3>', '', blocco.group(1), flags=re.S)
    web = re.search(r"<a href='([^']+)'[^>]*class=\"link_web\"", b)
    b = re.sub(r'<a [^>]*>.*?</a>', '', b, flags=re.S)
    righe = [pulisci(re.sub(r'<[^>]+>', '', x)) for x in re.split(r'<br\s*/?>', b)]
    righe = [x for x in righe if x]
    tel = next((x[4:].strip() for x in righe if x.startswith('Tel ')), None)
    if tel is None:  # senza «Tel» il file usa il cellulare
        tel = next((x[6:].strip() for x in righe if x.startswith('Cell. ')), None)
    cin = next((x[4:].strip() for x in righe if x.startswith('CIN ')), None)
    altre = [x for x in righe if not re.match(r'^(Tel|Cell\.|Fax|CIN)(\s|$)', x)]
    allog = re.search(r'<h3>Numero di alloggi</h3>\s*<div>(.*?)</div>', s, re.S)
    kv = [(k.strip(), int(v)) for k, v in re.findall(r'<span>([^<:]+):</span>\s*(\d+)', allog.group(1))] if allog else []
    cap = re.match(r'^(\d{5}) ', altre[-1]) if altre else None
    return {'den': pulisci((q.get('title') or [None])[0]), 'email': pulisci((q.get('mailTo') or [None])[0]), 'tipo': (q.get('tipo') or [None])[0],
            'ind': altre[0] if len(altre) > 1 else None, 'cap': cap.group(1) if cap else None,
            'loc': re.sub(r'^\d{5} ', '', altre[-1]) if altre else None, 'tel': tel, 'cin': cin,
            'web': pulisci(web.group(1)) if web else None, 'kv': kv}


# il sito degli agriturismi a volte risponde in inglese anche sugli indirizzi italiani: cambiano solo le etichette
INGLESE = {'Mobile': 'Cellulare', 'Telephone': 'Telefono', 'Certified email': 'Pec', 'Address': 'Indirizzo', 'Places': 'Località',
           'Postal Code': 'CAP', 'Owner': 'Titolare'}


def in_italiano(s):
    """Pagina con le etichette attese. Le schede «strutture» di alcuni server, dopo una ricerca, arrivano in inglese:
    si rileggono con una sessione nuova; le schede degli agriturismi in inglese si leggono traducendo le etichette."""
    return '<h3>Indirizzo</h3>' in s or '<strong>Indirizzo</strong>' in s or '<strong>Address</strong>' in s


def scheda(rete, i):
    """('ok', campi) | ('assente', None) se il portale rimanda alla pagina di errore | ('errore', motivo)."""
    motivo = 'impaginazione non riconosciuta'
    for _ in range(4):
        try:
            finale, s = rete.leggi(PORTALE + f'/TFVGB/Strutture/{i}/x?sez=0')
        except Exception as e:
            motivo = str(e); rete.nuova_sessione(); continue
        if 'Error.html' in finale:
            return 'assente', None
        if not in_italiano(s):
            motivo = 'pagina non in italiano'; rete.nuova_sessione(); continue
        c = leggi_scheda(s)
        if c:
            return 'ok', c
    return 'errore', motivo


# ---------------------------------------------------------------- prezzi (stesse formule del foglio «Strutture»)
def arrotonda(x, cifre=0):
    m = 10 ** cifre
    return math.floor(abs(x) * m + 0.5) / m * (1 if x >= 0 else -1)


def intero(x):
    return int(arrotonda(x))


def parametri(par):
    z = {}
    for row in par:
        if row and row[0] in ('Trieste città', 'Costa e lagune', 'Udine città', 'Pordenone città', 'Gorizia città', 'Montagna (località turistiche)', 'Resto del territorio regionale'):
            z[row[0]] = {'ua': row[1], 'hotel': row[3] if len(row) > 3 and row[3] is not None else intero(row[1] * 1.11), 'camp': row[4]}
    media = z['Resto del territorio regionale']['ua']
    for k in z:
        z[k]['indice'] = z[k]['ua'] / media
    rif = {r[0]: r[1] for r in par if r and isinstance(r[0], str) and len(r) > 1}
    p = {'bb': rif['Prezzo medio regionale camera doppia B&B / affittacamere / agriturismo / albergo diffuso €/notte'], 'ppc': rif['Persone per camera doppia'],
         'rif': rif['Rifugio: pernottamento €/persona/notte (non soci CAI, solo posto letto)'], 'camp_pers': rif['Campeggio: persone per piazzola se il dato non è disponibile'],
         'ost': rif['Ostelli, case per ferie, foresterie, residenze: €/persona/notte (posto letto)'], 'mar': rif['Marina resort: €/notte per posto barca (barca 12 m, transito)'],
         'mar_pers': rif['Marina resort: persone per posto barca se il dato non è disponibile']}
    coef = sorted((r[0], r[1]) for r in par if r and isinstance(r[0], (int, float)) and len(r) > 1 and isinstance(r[1], (int, float)))
    return z, p, coef


def prezzi(base, zona, cam, pl, par):
    """(posti letto per camera, prezzo per unità, prezzo per persona); None dove la formula non dà un valore."""
    z, p, coef = parametri(par)
    plc = arrotonda(pl / cam, 1) if isinstance(cam, (int, float)) and isinstance(pl, (int, float)) and cam > 0 else None
    if plc is not None and float(plc).is_integer():
        plc = int(plc)
    coeff = lambda v: [c for s, c in coef if v >= s][-1]
    if base in ('Stima: camera doppia × indice zona', 'Stima: prezzo zona per alloggio', 'Stima: camera doppia hotel di zona', 'Stima: prezzo per piazzola di zona') and zona not in z:
        return plc, None, None
    if base == 'Stima: camera doppia × indice zona':
        pu = intero(p['bb'] * z[zona]['indice']); return plc, pu, intero(pu / p['ppc'])
    if base == 'Stima: prezzo zona per alloggio':
        b = z[zona]['ua']; pu = b if plc is None else intero(b * coeff(plc))
        return plc, pu, intero(pu / 4) if plc is None else intero(pu / max(plc, 1))
    if base == 'Stima: camera doppia hotel di zona':
        pu = z[zona]['hotel']; return plc, pu, intero(pu / p['ppc'])
    if base == 'Stima: prezzo per piazzola di zona':
        pu = z[zona]['camp']; return plc, pu, intero(pu / p['camp_pers']) if plc is None else intero(pu / max(plc, 1))
    if base == 'Tariffa CAI posto letto (mezza pensione ~60-80 €)':
        return plc, p['rif'], p['rif']
    if base == 'Stima: posto letto in ostello/casa per ferie':
        return plc, p['ost'] if plc is None else intero(p['ost'] * plc), p['ost']
    if base == 'Stima: posto barca 12 m (Marina San Giusto)':
        return plc, p['mar'], intero(p['mar'] / p['mar_pers']) if plc is None else intero(p['mar'] / max(plc, 1))
    return plc, None, None


# ---------------------------------------------------------------- file
def carica():
    d = json.loads(FILE.read_text(encoding='utf-8'))
    dic = d.pop('dic', {})
    d['recs'] = [{k: (dic[k][v] if k in dic and isinstance(v, int) else v) for k, v in o.items()} for o in d['recs']]
    return d


def salva(d):
    d = copy.deepcopy(d)
    conta = {}
    for r in d['recs']:
        for k, v in r.items():
            if isinstance(v, str):
                conta.setdefault(k, {}).setdefault(v, 0)
                conta[k][v] += 1
    dic = {k: sorted(c) for k, c in conta.items() if len(c) <= 600 and sum(c.values()) > 2 * len(c) and k != 'den'}
    idx = {k: {v: i for i, v in enumerate(vals)} for k, vals in dic.items()}
    d['recs'] = [{k: (idx[k][v] if k in idx and isinstance(v, str) else v) for k, v in r.items() if v is not None and v != []} for r in d['recs']]
    d['dic'] = dic
    FILE.write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def coordinate_wikidata(istat):
    """Coordinate del comune da Wikidata (proprietà P625) per codice ISTAT (P635), come per gli altri comuni della sezione."""
    q = f'SELECT ?l ?c WHERE {{ ?i wdt:P635 "{istat}"; wdt:P625 ?c. FILTER NOT EXISTS {{ ?i wdt:P576 ?f }} ?i rdfs:label ?l FILTER(LANG(?l)="it") }}'
    url = 'https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
            b = json.load(r)['results']['bindings']
        if len(b) == 1:
            lng, lat = re.match(r'Point\(([-\d.]+) ([-\d.]+)\)', b[0]['c']['value']).groups()
            return b[0]['l']['value'], round(float(lat), 5), round(float(lng), 5)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- aggiornamento del portale
def tipo_sociale(nome):
    n = (nome or '').lower()
    if 'ostello' in n: return 'Ostello'
    if 'foresteria' in n: return 'Foresteria'
    if re.search(r'residenza universitaria|collegio|convitto', n): return 'Residenza universitaria / collegio'
    return 'Casa per ferie / struttura sociale'


def dett_da_kv(kv):
    return '; '.join(f'{k}: {v}' for k, v in kv) or None


def kv_da_dett(dett):
    return [(k.strip(), int(v)) for k, v in re.findall(r'([^:;]+):\s*(\d+)', dett or '')]


def aggiorna_portale(d, rete, limite, esito):
    P = {r['id']: r for r in d['recs'] if r['src'] == 'P'}
    meta = d['meta']
    # 1. elenco ufficiale per categoria
    elenco, completo = {}, True
    for cat, tipo in ({} if SENZA_ELENCO else CATEGORIE).items():
        try:
            ids, tot = elenco_categoria(rete, cat)
        except Exception as e:
            print(f'Elenco «{tipo}» non letto: {e}'); completo = False; continue
        if tot and len(ids) < tot:
            print(f'Elenco «{tipo}» incompleto: {len(ids)} su {tot}'); completo = False
        for i in ids:
            elenco.setdefault(i, cat)
        esito['elenco'][tipo] = tot
        print(f'  elenco «{tipo}»: {len(ids)} su {tot}', flush=True)
    if SENZA_ELENCO:
        elenco, completo = {i: None for i in P}, False
    elenco = {i: c for i, c in elenco.items() if i not in ESCLUSE}
    print(f'Elenco ufficiale: {len(elenco)} strutture ({"completo" if completo else "incompleto"}); nel file: {len(P)}')
    if len(elenco) < 0.95 * len(P):
        raise SystemExit(f'Fermato: l\'elenco ufficiale ({len(elenco)}) è molto più corto di quello attuale ({len(P)}). Nessuna modifica.')
    # 2. schede
    zone = {}
    for r in P.values():
        zone.setdefault(r['istat'], set()).add(r.get('zona'))
    fontep = {}
    for r in P.values():
        fontep.setdefault((r.get('base'), r.get('zona')), set()).add(r.get('fontep'))
    rete.nuova_sessione()  # sessione nuova, in italiano, per le schede
    da_leggere = sorted(set(P) | set(elenco))
    if limite:
        da_leggere = da_leggere[:limite]
    letti, illeggibili, assenti = {}, [], []
    for n, i in enumerate(da_leggere, 1):
        stato, c = scheda(rete, i)
        if stato == 'ok': letti[i] = c
        elif stato == 'assente': assenti.append(i)
        else: illeggibili.append((i, c))
        if n % 250 == 0:
            print(f'  schede lette: {n} su {len(da_leggere)}')
    esito['schede_lette'] = len(letti)
    if len(illeggibili) > 0.10 * len(da_leggere):
        raise SystemExit(f'Fermato: {len(illeggibili)} schede illeggibili su {len(da_leggere)}. Nessuna modifica.')
    for i, motivo in illeggibili[:50]:
        esito['da_verificare'].append(f'ID portale {i}: scheda non letta ({motivo}); dati lasciati come prima')
    # 3. strutture esistenti
    mancanti = meta.setdefault('mancanti', {})
    togliere = []
    for i, r in P.items():
        if i not in letti and i not in assenti:
            continue
        if i in assenti:
            if completo and i not in elenco:
                if str(i) in mancanti and mancanti[str(i)][:7] != OGGI[:7]:
                    togliere.append(i)
                else:
                    mancanti.setdefault(str(i), OGGI)
                    esito['da_verificare'].append(f'{r["den"]} (ID portale {i}): la scheda non esiste più; si toglie se manca ancora al prossimo controllo')
            else:
                esito['da_verificare'].append(f'{r["den"]} (ID portale {i}): scheda non trovata ma struttura ancora nell\'elenco ufficiale')
            continue
        mancanti.pop(str(i), None)
        c = letti[i]
        campi = []

        def cambia(k, v):
            if (v or None) != (r.get(k) or None):
                esito['modifiche'].append(f'{r["den"]} (ID portale {i}) {k}: «{r.get(k)}» → «{v}»')
                r[k] = v; campi.append(k)
        cambia('den', c['den'])
        nota = r.get('noteint') or ''
        if not re.search(r'indirizzo|cap', nota, re.I):
            if c['ind']: cambia('ind', c['ind'])
            if c['cap']: cambia('cap', c['cap'])
            if c['loc']: cambia('loc', c['loc'])
        cambia('tel', c['tel']); cambia('email', c['email'])
        if c['cin'] and c['cin'] != r.get('cin'):
            if len(c['cin']) >= 8 and c['cin'][2:8] != r.get('istat'):
                esito['da_verificare'].append(f'{r["den"]} (ID portale {i}): il nuovo CIN {c["cin"]} indica un comune diverso; CIN e comune lasciati come prima')
            else:
                cambia('cin', c['cin'])
        # sito: non tornare al vecchio indirizzo già corretto o tolto; «http://https://…» è lo stesso indirizzo scritto male
        if c['web']:
            c['web'] = re.sub(r'^https?://(?=https?://)', '', c['web'], flags=re.I)
        vecchio = (r.get('vl') or {}).get('url')
        if c['web'] and c['web'] != r.get('web') and c['web'] != vecchio:
            esito['modifiche'].append(f'{r["den"]} (ID portale {i}) web: «{r.get("web")}» → «{c["web"]}»')
            r['web'] = c['web']; r['sito'] = 'Non ancora verificato'; r['ver'] = f'Sito indicato dal portale al controllo del {OGGI}, non ancora verificato'; campi.append('web')
        elif not c['web'] and r.get('web') and r.get('sito') != 'Corretto con nuovo sito ufficiale':
            esito['modifiche'].append(f'{r["den"]} (ID portale {i}) web: «{r.get("web")}» → nessuno')
            r['web'] = None; r['sito'] = 'Non indicato'; r['ver'] = f'Sito non più indicato dal portale al controllo del {OGGI}'; campi.append('web')
        # ricettività
        nuovo = dict(c['kv']); prima = dict(kv_da_dett(r.get('dett')))
        if 'Camere' in prima:
            diversi = [k for k in ('Camere', 'Letti', 'Bagni') if k in prima and prima.get(k) != nuovo.get(k)]
            if diversi:
                if all(k in nuovo for k in ('Camere', 'Letti', 'Bagni') if k in prima):
                    for k in diversi:
                        prima[k] = nuovo[k]
                    r['cam'], r['pl'] = prima.get('Camere'), prima.get('Letti')
                    if 'Bagni' in prima: r['bagni'] = prima['Bagni']
                    esito['modifiche'].append(f'{r["den"]} (ID portale {i}) ricettività: «{r.get("dett")}» → «{dett_da_kv(list(prima.items()))}»')
                    r['dett'] = dett_da_kv(list(prima.items())); campi += ['cam', 'pl', 'bagni']
                    r['plc'], r['pu'], r['pp'] = prezzi(r.get('base'), r.get('zona'), r.get('cam'), r.get('pl'), d['par'])
                else:
                    esito['da_verificare'].append(f'{r["den"]} (ID portale {i}): ricettività non più completa sul portale ({dett_da_kv(c["kv"])}); numeri lasciati come prima')
        elif prima and any(prima.get(k) != nuovo.get(k) for k in prima):
            esito['da_verificare'].append(f'{r["den"]} (ID portale {i}): ricettività cambiata sul portale ({dett_da_kv(c["kv"])}, prima {r.get("dett")}); numeri lasciati come prima')
        # tipologia: categoria dell'elenco ufficiale
        cat = elenco.get(i)
        if cat and not (CATEGORIE[cat] == r['tip'] or (cat == 15 and r['tip'] in SOCIALI) or (cat == 4 and r['tip'].startswith('Unità abitative'))):
            esito['da_verificare'].append(f'{r["den"]} (ID portale {i}): il portale la elenca ora fra «{CATEGORIE[cat]}» (nel file: {r["tip"]})')
        if campi:
            r['agg'] = {'data': OGGI, 'campi': sorted(set(campi))}
            esito['cambiati'] += 1
    if len(togliere) > 0.03 * len(P):
        raise SystemExit(f'Fermato: {len(togliere)} strutture da togliere, troppe per un mese. Nessuna modifica.')
    if togliere:
        d['recs'] = [r for r in d['recs'] if not (r['src'] == 'P' and r['id'] in togliere)]
        for i in togliere:
            mancanti.pop(str(i), None)
            esito['tolte_elenco'].append(f'{P[i]["den"]} (ID portale {i})')
    esito['tolte'] += len(togliere)
    # 4. strutture nuove
    for i in sorted(set(elenco) - set(P)):
        c = letti.get(i)
        if not c:
            continue
        tip = CATEGORIE[elenco[i]]
        if elenco[i] == 15:
            tip = tipo_sociale(c['den'])
        istat = c['cin'][2:8] if c['cin'] and re.match(r'^IT\d{6}', c['cin']) else None
        com = d['comuni'].get(istat, {}).get('nome') if istat else None
        if istat and istat not in d['comuni']:
            w = coordinate_wikidata(istat)
            if w and istat[:3] in PROVINCE:
                d['comuni'][istat] = {'nome': w[0], 'prov': PROVINCE[istat[:3]], 'lat': w[1], 'lng': w[2], 'wd': w[0]}
                com = w[0]
            else:
                istat = None
        if not istat:
            esito['da_verificare'].append(f'{c["den"]} (ID portale {i}): struttura nuova senza CIN leggibile, comune da verificare (località indicata: {c["loc"]})')
        kv = dict(c['kv'])
        cam, pl, bagni = (kv.get('Camere'), kv.get('Letti'), kv.get('Bagni')) if 'Camere' in kv else (None, None, None)
        zs = zone.get(istat) or set()
        zona = next(iter(zs)) if len(zs) == 1 else None
        base = BASE_DI_TIPO.get(tip)
        plc, pu, pp = prezzi(base, zona, cam, pl, d['par']) if base else (None, None, None)
        fp = fontep.get((base, zona)) or set()
        d['recs'].append({
            'src': 'P', 'n': None, 'id': i, 'den': c['den'], 'tip': tip, 'ind': c['ind'], 'cap': c['cap'], 'loc': c['loc'],
            'com': com or c['loc'], 'prov': PROVINCE.get((istat or '')[:3]), 'istat': istat, 'cin': c['cin'],
            'cam': cam, 'pl': pl, 'bagni': bagni, 'plc': plc, 'tel': c['tel'], 'email': c['email'], 'web': c['web'],
            'scheda': f'{PORTALE}/TFVGB/Strutture/{i}/x?sez=0', 'zona': zona, 'pu': pu, 'pp': pp, 'base': base if pu is not None else None,
            'dett': dett_da_kv(c['kv']), 'fonte': 'PromoTurismoFVG, scheda struttura sul portale ufficiale turismofvg.it (anagrafica, CIN, contatti, ricettività)',
            'risc': 'Non verificato (struttura aggiunta con l\'aggiornamento mensile)', 'fontep': next(iter(fp)) if len(fp) == 1 and pu is not None else None,
            'ver': f'Struttura aggiunta il {OGGI}: sito non ancora verificato' if c['web'] else f'Struttura aggiunta il {OGGI}: sito non indicato sul portale',
            'sito': 'Non ancora verificato' if c['web'] else 'Non indicato', 'agg': {'data': OGGI, 'campi': ['nuova']}})
        esito['nuove'] += 1
        esito['nuove_elenco'].append(f'{c["den"]} (ID portale {i}, {tip}, {com or c["loc"]})')


# ---------------------------------------------------------------- registro regionale (dati aperti)
def leggi_dataset(f):
    with urllib.request.urlopen(urllib.request.Request(f'https://www.dati.friuliveneziagiulia.it/api/views/{f}.json', headers={'User-Agent': UA}), timeout=60) as r:
        agg = json.load(r).get('rowsUpdatedAt')
    with urllib.request.urlopen(urllib.request.Request(f'https://www.dati.friuliveneziagiulia.it/resource/{f}.json?$limit=50000', headers={'User-Agent': UA}), timeout=120) as r:
        righe = [{'comune': x.get('comune'), 'provincia': x.get('provincia'), 'denominazione': x.get('denominazione'), 'email': x.get('email'),
                  'sito': (x.get('sito') or {}).get('url') if isinstance(x.get('sito'), dict) else x.get('sito')} for x in json.load(r)]
    return agg, righe


def chiave(x):
    return (norm(x['denominazione']), norm(x['comune']))


def aggiorna_registro(d, esito):
    fonti = json.loads(FONTI.read_text(encoding='utf-8'))
    istat_nome = {}
    for k, c in d['comuni'].items():
        istat_nome[norm(c['nome'])] = k
    for r in d['recs']:
        if r.get('istat'):
            istat_nome.setdefault(norm(r['com']), r['istat'])
    portale = {(norm(r['den']), r.get('istat')) for r in d['recs'] if r['src'] == 'P'}
    email_portale = {(r.get('email') or '').lower() for r in d['recs'] if r['src'] == 'P' and r.get('email')}
    for f, nome in DATASET.items():
        try:
            agg, righe = leggi_dataset(f)
        except Exception as e:
            esito['da_verificare'].append(f'Dati aperti «{nome}» non letti ({e}): voci del registro lasciate come prima'); continue
        salvato = fonti['dataset'].get(f, {})
        if agg == salvato.get('agg'):
            continue
        if len(righe) < 0.8 * len(salvato.get('righe', [])):
            esito['da_verificare'].append(f'Dati aperti «{nome}»: {len(righe)} righe contro {len(salvato.get("righe", []))}, aggiornamento non applicato'); continue
        prima = {}
        for x in salvato.get('righe', []):
            prima.setdefault(chiave(x), []).append(x)
        dopo = {}
        for x in righe:
            dopo.setdefault(chiave(x), []).append(x)
        link = f'https://www.dati.friuliveneziagiulia.it/d/{f}'
        mie = [r for r in d['recs'] if r['src'] == 'R' and r.get('linkreg') == link]
        # voci tolte dalla Regione
        via = {k for k in prima if k not in dopo}
        for r in mie:
            if (norm(r['den']), norm(r['com'])) in via:
                r['_via'] = True; esito['tolte'] += 1; esito['tolte_elenco'].append(f'{r["den"]} ({r["com"]}, solo registro)')
        # contatti cambiati
        for r in mie:
            k = (norm(r['den']), norm(r['com']))
            if k in prima and k in dopo and len(prima[k]) == len(dopo[k]) == 1:
                a, b = prima[k][0], dopo[k][0]
                campi = []
                if (a['email'] or None) != (b['email'] or None):
                    r['email'] = b['email']; campi.append('email')
                if (a['sito'] or None) != (b['sito'] or None):
                    r['web'] = b['sito']; r['sito'] = 'Non ancora verificato' if b['sito'] else 'Non indicato'
                    r['ver'] = f'Sito cambiato nei dati aperti al controllo del {OGGI}, non ancora verificato'; campi.append('web')
                if campi:
                    r['agg'] = {'data': OGGI, 'campi': campi}; esito['cambiati'] += 1
        # voci nuove della Regione
        for k in dopo:
            if k in prima:
                continue
            for x in dopo[k]:
                ist = istat_nome.get(norm(x['comune']))
                if (k[0], ist) in portale or ((x['email'] or '').lower() in email_portale and x['email']):
                    esito['da_verificare'].append(f'{x["denominazione"]} ({x["comune"]}): nuova nei dati aperti «{nome}», forse già presente sul portale')
                    continue
                d['recs'].append({'src': 'R', 'n': None, 'tip': TIPO_DATASET[f], 'den': pulisci(x['denominazione']), 'com': pulisci(x['comune']),
                                  'prov': (x['provincia'] or '').title() or None, 'istat': ist, 'email': x['email'], 'web': x['sito'],
                                  'nota': 'Nel registro regionale (open data) ma non sul portale: indirizzo e posti letto non pubblicati',
                                  'fonte': f'Open data Regione FVG – {nome}', 'linkreg': link,
                                  'ver': f'Voce aggiunta il {OGGI}: sito non ancora verificato' if x['sito'] else 'Sito non indicato',
                                  'sito': 'Non ancora verificato' if x['sito'] else 'Non indicato', 'agg': {'data': OGGI, 'campi': ['nuova']}})
                esito['nuove'] += 1; esito['nuove_elenco'].append(f'{x["denominazione"]} ({x["comune"]}, solo registro)')
        d['recs'] = [r for r in d['recs'] if not r.get('_via')]
        fonti['dataset'][f] = {'nome': nome, 'agg': agg, 'righe': righe}
    return fonti


# ---------------------------------------------------------------- principale
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--prova', action='store_true', help='non scrive nulla')
    ap.add_argument('--limite', type=int, default=0, help='legge solo le prime N schede (prove)')
    ap.add_argument('--solo-registro', action='store_true')
    ap.add_argument('--senza-elenco', action='store_true', help='prove: rilegge solo le schede già nel file, senza cercare strutture nuove o tolte')
    ap.add_argument('--pausa', type=float, default=0.8, help='secondi fra una richiesta e l\'altra al portale')
    a = ap.parse_args()
    global SENZA_ELENCO
    SENZA_ELENCO = a.senza_elenco
    d = carica()
    prima = json.dumps(d['recs'], sort_keys=True, ensure_ascii=False)
    d.setdefault('meta', {})
    esito = {'data': OGGI, 'nuove': 0, 'tolte': 0, 'cambiati': 0, 'nuove_elenco': [], 'tolte_elenco': [], 'modifiche': [], 'da_verificare': [], 'elenco': {}, 'schede_lette': 0}
    if not a.solo_registro:
        aggiorna_portale(d, Rete(a.pausa), a.limite, esito)
    fonti = aggiorna_registro(d, esito)
    cambiato = json.dumps(d['recs'], sort_keys=True, ensure_ascii=False) != prima
    reg = d['meta'].setdefault('registro', [])
    reg.append({'data': OGGI, 'esito': 'dati aggiornati' if cambiato else 'nessuna differenza', 'nuove': esito['nuove'], 'tolte': esito['tolte'],
                'cambiati': esito['cambiati'], 'da_verificare': len(esito['da_verificare']), 'schede_lette': esito['schede_lette']})
    del reg[:-24]
    d['meta']['ultimo_controllo'] = OGGI
    d['meta']['da_verificare'] = esito['da_verificare']
    d['meta']['conteggi'] = {'portale': sum(1 for r in d['recs'] if r['src'] == 'P'), 'registro': sum(1 for r in d['recs'] if r['src'] == 'R')}
    # riepilogo per il messaggio del commit
    print(f'Strutture nuove: {esito["nuove"]}; tolte: {esito["tolte"]}; con dati cambiati: {esito["cambiati"]}; da verificare: {len(esito["da_verificare"])}')
    for x in esito['nuove_elenco'][:40]: print('  nuova: ' + x)
    for x in esito['tolte_elenco'][:40]: print('  tolta: ' + x)
    quanti = None if a.prova else 60  # in prova si stampa tutto
    for x in esito['modifiche'][:quanti]: print('  cambiato: ' + x)
    if quanti and len(esito['modifiche']) > quanti: print(f'  … e altre {len(esito["modifiche"]) - quanti} modifiche')
    for x in esito['da_verificare'][:quanti or None]: print('  da verificare: ' + x)
    if a.prova:
        print('Prova: nessun file scritto.'); return
    if a.limite:
        print('Lettura parziale (--limite): nessun file scritto.'); return
    salva(d)
    FONTI.write_text(json.dumps(fonti, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


if __name__ == '__main__':
    main()
