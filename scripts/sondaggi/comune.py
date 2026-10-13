"""Funzioni comuni dell'Osservatorio sondaggi: date, rete, cifratura, archivio, registro.

L'archivio è un unico documento JSON (vedi LEGGIMI.md per lo schema) che vive, cifrato, nel ramo
`sondaggi-dati` del repository. La chiave è la stessa della pagina riservata sondaggi/: PBKDF2 sulla
parola d'ordine (segreto SONDAGGI_PAROLA, in mancanza MONITOR_PAROLA) con il sale di
sondaggi/contenuto.json. Senza parola d'ordine le funzioni lavorano in chiaro su file locali, per le prove.
"""
from __future__ import annotations

import base64
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zoneinfo
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent.parent
CARTELLA_DATI = RADICE / 'dati' / 'sondaggi'
ROMA = zoneinfo.ZoneInfo('Europe/Rome')
UTENTE = 'Mozilla/5.0 (X11; Linux x86_64) AtlanteFVG/1.0 (+https://atlantefvg.it; info@atlantefvg.it)'
VERSIONE_ARCHIVIO = 1

MESI = {m: i + 1 for i, m in enumerate(['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
                                         'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'])}
MESI_ABBR = {'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8, 'set': 9, 'sett': 9,
             'ott': 10, 'nov': 11, 'dic': 12}
MESI_EN = {m: i + 1 for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                            'september', 'october', 'november', 'december'])}


# ----------------------------------------------------------------------------------------------------- testo e date

def adesso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def oggi_roma() -> dt.date:
    return dt.datetime.now(ROMA).date()


def pulisci(testo: str) -> str:
    """Normalizza spazi e caratteri tipografici di un testo estratto da HTML o PDF."""
    testo = unicodedata.normalize('NFC', testo or '')
    testo = testo.replace('\xa0', ' ').replace('’', "'").replace('`', "'").replace('‘', "'")
    return re.sub(r'\s+', ' ', testo).strip()


def chiave_testo(testo: str) -> str:
    """Forma canonica per confronti: minuscolo, senza accenti né punteggiatura."""
    t = unicodedata.normalize('NFKD', testo or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()


def slug(testo: str) -> str:
    return re.sub(r'\s+', '-', chiave_testo(testo))[:80]


def impronta(*parti: str) -> str:
    return hashlib.sha256('\x1f'.join(parti).encode()).hexdigest()[:16]


def data_italiana(testo: str) -> dt.date | None:
    """Legge «5 ottobre 2026», «05/10/2026», «5-10-2026», «2026-10-05», «1° marzo 2020», «5 ott 2026»."""
    if not testo:
        return None
    t = pulisci(testo).lower().replace('º', '').replace('°', '')
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', t)
    if m:
        return _data(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b', t)
    if m:
        return _data(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r'\b(\d{1,2})\s+([a-zà]+)\.?\s+(\d{4})\b', t)
    if m:
        mese = MESI.get(m.group(2)) or MESI_ABBR.get(m.group(2)) or MESI_EN.get(m.group(2))
        if mese:
            return _data(int(m.group(3)), mese, int(m.group(1)))
    m = re.search(r'\b([a-z]+)\s+(\d{1,2}),?\s+(\d{4})\b', t)  # inglese: October 5, 2026
    if m and m.group(1) in MESI_EN:
        return _data(int(m.group(3)), MESI_EN[m.group(1)], int(m.group(2)))
    return None


def _data(a: int, m: int, g: int) -> dt.date | None:
    try:
        return dt.date(a, m, g)
    except ValueError:
        return None


def intervallo_date(testo: str, anno_rif: int | None = None) -> tuple[dt.date | None, dt.date | None]:
    """Legge un periodo di interviste: «30 settembre – 2 ottobre 2026», «4-6 maggio 2026», «23 – 28 settembre 2026»,
    «dal 30/09 al 02/10/2026». Restituisce (inizio, fine); mancando l'anno dell'inizio usa quello della fine."""
    if not testo:
        return None, None
    t = pulisci(testo).lower().replace('º', '').replace('°', '')
    t = re.sub(r'\b(dal|al|tra|fra|il|e|ed)\b', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    m = re.search(r'(\d{1,2})(?:\s+([a-zà]+))?\s*[-–—/]\s*(\d{1,2})\s+([a-zà]+)\s+(\d{4})', t)
    if m:
        mese_fine = MESI.get(m.group(4)) or MESI_ABBR.get(m.group(4))
        mese_inizio = (MESI.get(m.group(2)) or MESI_ABBR.get(m.group(2))) if m.group(2) else mese_fine
        if mese_fine and mese_inizio:
            anno = int(m.group(5))
            inizio = _data(anno - 1 if mese_inizio > mese_fine else anno, mese_inizio, int(m.group(1)))
            return inizio, _data(anno, mese_fine, int(m.group(3)))
    m = re.search(r'(\d{1,2})[/.](\d{1,2})(?:[/.](\d{4}))?\s*[-–—]\s*(\d{1,2})[/.](\d{1,2})[/.](\d{4})', t)
    if m:
        anno_fine = int(m.group(6))
        fine = _data(anno_fine, int(m.group(5)), int(m.group(4)))
        anno_inizio = int(m.group(3)) if m.group(3) else (anno_fine - 1 if int(m.group(2)) > int(m.group(5)) else anno_fine)
        return _data(anno_inizio, int(m.group(2)), int(m.group(1))), fine
    date = re.findall(r'\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b', t)
    if len(date) >= 2:
        a = _data(int(date[0][2]), int(date[0][1]), int(date[0][0]))
        b = _data(int(date[-1][2]), int(date[-1][1]), int(date[-1][0]))
        if a and b and a <= b:
            return a, b
    d = data_italiana(t)
    return (d, d) if d else (None, None)


def numero(testo: str) -> float | None:
    """«27,7%» → 27.7; «1.037» → 1037; «-0,2» → -0.2; nulla se non è un numero."""
    if testo is None:
        return None
    t = str(testo).strip().replace('%', '').replace('−', '-').replace('–', '-').replace(' ', '')
    t = t.replace('O', '0').replace('o', '0') if re.fullmatch(r'[-+]?[0-9Oo]+[,.][0-9Oo]+', t) else t
    if re.fullmatch(r'[-+]?\d{1,3}(\.\d{3})+(,\d+)?', t):
        t = t.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'[-+]?\d+,\d+', t):
        t = t.replace(',', '.')
    elif not re.fullmatch(r'[-+]?\d+(\.\d+)?', t):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def iso(d: dt.date | None) -> str | None:
    return d.isoformat() if d else None


# ---------------------------------------------------------------------------------------------------------- rete

def indirizzo_sicuro(url: str) -> str:
    """Codifica i caratteri non ASCII e gli spazi del percorso (per esempio «tecnè.png»)."""
    parti = urllib.parse.urlsplit(url.strip())
    percorso = urllib.parse.quote(parti.path, safe='/%:@!$&\'()*+,;=')
    query = urllib.parse.quote(parti.query, safe='=&%+/:,;@!$\'()*')
    return urllib.parse.urlunsplit((parti.scheme, parti.netloc, percorso, query, ''))


class Rete:
    """Scaricamento con pausa minima tra richieste allo stesso sito, tentativi e timeout.
    Registra ogni indirizzo che non ha risposto in `fallimenti`."""

    def __init__(self, pausa: float = 1.0, tentativi: int = 3, timeout: int = 60):
        self.pausa, self.tentativi, self.timeout = pausa, tentativi, timeout
        self.ultimo: dict[str, float] = {}
        self.fallimenti: list[dict] = []
        self.richieste = 0

    def scarica(self, url: str, binario: bool = False, intestazioni: dict | None = None, dati: bytes | None = None):
        url = indirizzo_sicuro(url)
        host = urllib.parse.urlsplit(url).netloc
        attesa = self.pausa - (time.monotonic() - self.ultimo.get(host, 0))
        if attesa > 0:
            time.sleep(attesa)
        errore = None
        for tentativo in range(self.tentativi):
            try:
                req = urllib.request.Request(url, data=dati, headers={'User-Agent': UTENTE, **(intestazioni or {})})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    corpo = r.read()
                    self.ultimo[host] = time.monotonic()
                    self.richieste += 1
                    if binario:
                        return corpo
                    tipo = r.headers.get_content_charset() or 'utf-8'
                    try:
                        return corpo.decode(tipo)
                    except (UnicodeDecodeError, LookupError):
                        return corpo.decode('utf-8', 'replace')
            except urllib.error.HTTPError as e:
                errore = f'HTTP {e.code}'
                if e.code in (400, 401, 403, 404, 410):
                    break
            except Exception as e:  # noqa: BLE001
                errore = type(e).__name__ + ': ' + str(e)[:120]
            self.ultimo[host] = time.monotonic()
            time.sleep(2 * (tentativo + 1))
        self.fallimenti.append({'url': url, 'errore': errore, 'quando': adesso()})
        raise ConnectionError(f'{url}: {errore}')

    def json(self, url: str):
        return json.loads(self.scarica(url))


# ---------------------------------------------------------------------------------------------------- cifratura

_CHIAVE_CACHE: dict = {}


def _chiave() -> bytes | None:
    """Chiave AES dalla parola d'ordine (SONDAGGI_PAROLA, in mancanza MONITOR_PAROLA) e dal sale della pagina.
    Prova la parola com'è scritta e poi in maiuscolo e in minuscolo: vale la prima variante che apre la pagina."""
    parola = os.environ.get('SONDAGGI_PAROLA') or os.environ.get('MONITOR_PAROLA')
    if not parola:
        return None
    if 'k' in _CHIAVE_CACHE:
        return _CHIAVE_CACHE['k']
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    pagina = json.loads((RADICE / 'sondaggi' / 'contenuto.json').read_text())
    sale = base64.b64decode(pagina['s'])
    base = unicodedata.normalize('NFC', parola.strip())
    varianti = [base, base.upper(), base.lower()]
    prima = None
    for v in dict.fromkeys(varianti):
        k = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sale, iterations=300000).derive(v.encode())
        prima = prima or k
        try:
            AESGCM(k).decrypt(base64.b64decode(pagina['i']), base64.b64decode(pagina['d']), None)
            _CHIAVE_CACHE['k'] = k
            return k
        except Exception:  # noqa: BLE001
            continue
    _CHIAVE_CACHE['k'] = prima  # nessuna variante apre la pagina: verifica_parola() lo segnalerà
    return prima


def verifica_parola() -> bool:
    """Vero se la parola d'ordine apre sondaggi/contenuto.json (quindi la pagina leggerà ciò che cifriamo)."""
    k = _chiave()
    if not k:
        return False
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    p = json.loads((RADICE / 'sondaggi' / 'contenuto.json').read_text())
    try:
        AESGCM(k).decrypt(base64.b64decode(p['i']), base64.b64decode(p['d']), None)
        return True
    except Exception:  # noqa: BLE001
        return False


def cifra_json(oggetto, k: bytes | None = None) -> bytes:
    corpo = gzip.compress(json.dumps(oggetto, ensure_ascii=False, separators=(',', ':')).encode(), 9)
    k = k or _chiave()
    if not k:
        return corpo
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iv = os.urandom(12)
    return json.dumps({'v': 1, 'i': base64.b64encode(iv).decode(),
                       'd': base64.b64encode(AESGCM(k).encrypt(iv, corpo, None)).decode()}).encode()


def decifra_json(dati: bytes, k: bytes | None = None):
    k = k or _chiave()
    if dati[:2] == b'\x1f\x8b':
        return json.loads(gzip.decompress(dati))
    p = json.loads(dati)
    if 'd' not in p:
        return p
    if not k:
        raise RuntimeError('file cifrato ma nessuna parola d\'ordine in SONDAGGI_PAROLA o MONITOR_PAROLA')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return json.loads(gzip.decompress(AESGCM(k).decrypt(base64.b64decode(p['i']), base64.b64decode(p['d']), None)))


def cifra_byte(dati: bytes, k: bytes | None = None) -> bytes:
    k = k or _chiave()
    if not k:
        return dati
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iv = os.urandom(12)
    return json.dumps({'v': 1, 'i': base64.b64encode(iv).decode(),
                       'd': base64.b64encode(AESGCM(k).encrypt(iv, dati, None)).decode()}).encode()


def decifra_byte(dati: bytes, k: bytes | None = None) -> bytes:
    k = k or _chiave()
    try:
        p = json.loads(dati)
    except ValueError:
        return dati
    if not isinstance(p, dict) or 'd' not in p:
        return dati
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(k).decrypt(base64.b64decode(p['i']), base64.b64decode(p['d']), None)


# ----------------------------------------------------------------------------------------------------- archivio

def archivio_vuoto() -> dict:
    return {
        'v': VERSIONE_ARCHIVIO, 'generato': None,
        'istituti': {},      # id → {nome, alias[], sito, tipo, note, fonti[]}
        'fonti': {},         # id → stato della fonte (vedi aggiorna.py)
        'documenti': {},     # id → {url, tipo, titolo, fonte, acquisito, sha256, rilevazioni[], testo}
        'rilevazioni': {},   # id → scheda della rilevazione con domande e valori
        'serie': {},         # id → serie comparabile (domanda ricorrente dello stesso istituto)
        'coda': {},          # id → voce «da verificare»
        'revisioni': [],     # correzioni e decisioni applicate, in ordine
        'esecuzioni': [],    # registro delle esecuzioni (ultime 200)
        'ultimoTentativo': None, 'ultimoRiuscito': None, 'ultimaRilevazione': None,
    }


def leggi_archivio(percorso: Path) -> dict:
    if not percorso.exists():
        return archivio_vuoto()
    a = decifra_json(percorso.read_bytes())
    base = archivio_vuoto()
    base.update(a)
    return base


def scrivi_archivio(archivio: dict, percorso: Path) -> None:
    archivio['generato'] = adesso()
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_bytes(cifra_json(archivio))


def leggi_json_locale(nome: str, predefinito=None):
    p = CARTELLA_DATI / nome
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else predefinito


def registro(messaggio: str) -> None:
    print(f'[{dt.datetime.now(ROMA).strftime("%H:%M:%S")}] {messaggio}', file=sys.stderr, flush=True)
