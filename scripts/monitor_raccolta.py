"""Raccolta e analisi per il Monitor della percezione pubblica (sezione riservata monitor/).

Eseguito da .github/workflows/monitor.yml ogni 30 minuti:
1. legge lo stato precedente (file cifrato, ramo monitor-dati);
2. scarica le fonti di scripts/monitor_fonti.json e, per ogni nome del segreto MONITOR_NOMI,
   le notizie di Google News che lo citano; facoltativamente i post di Bluesky;
3. fa analizzare le menzioni nuove da un modello linguistico aperto e gratuito (Qwen3 4B, licenza
   Apache 2.0) eseguito sul computer di GitHub: i testi non vengono inviati a nessun servizio esterno;
4. calcola le allerte di crisi e di consenso e, se configurato, le manda su Telegram;
5. riscrive lo stato, cifrato con la stessa chiave della pagina monitor/ (parola d'ordine + sale
   di monitor/contenuto.json), così il cruscotto lo apre con la chiave che ha già.

Segreti (variabili d'ambiente): MONITOR_PAROLA obbligatorio; MONITOR_NOMI, BLUESKY_UTENTE,
BLUESKY_PASSWORD_APP, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_STAFF facoltativi. Senza MONITOR_PAROLA lo
script esce senza errori e senza scrivere nulla. MONITOR_MODELLO_FILE indica il file del modello
(predefinito: modelli/Qwen3-4B-Q4_K_M.gguf, scaricato dal flusso di lavoro e verificato con SHA-256).

Uso: python scripts/monitor_raccolta.py <stato precedente o file assente> <stato nuovo>
"""
from __future__ import annotations

import base64
import calendar
import gzip
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from urllib.parse import quote

import feedparser
import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

RADICE = Path(__file__).resolve().parent.parent
ADESSO = datetime.now(timezone.utc)

MODELLO_FILE = os.getenv('MONITOR_MODELLO_FILE', str(RADICE / 'modelli' / 'Qwen3-4B-Q4_K_M.gguf'))
MOTORE = 'Qwen3 4B (Apache 2.0), eseguito in locale'
MAX_PER_GIRO = int(os.getenv('MONITOR_MAX_PER_GIRO', '60'))     # circa 15 secondi a menzione su 4 processori
MINUTI_MAX = float(os.getenv('MONITOR_MINUTI_MAX', '20'))       # le menzioni rimaste passano al giro dopo; il giro dura comunque 29 minuti
ORE_MENZIONI = 72          # menzioni e allerte conservate nello stato
GIORNI_VISTE = 30          # impronte dei contenuti già visti (evitano analisi doppie)
ORE_RECENTI = 26           # alla prima raccolta si prendono solo le notizie dell'ultimo giorno

# Soglie delle allerte, tarate su una raccolta ogni 30 minuti (le notizie arrivano a gruppi)
FINESTRA_MIN, BASE_ORE, VOLUME_MINIMO = 120, 24, 6
CALO_CRISI, QUOTA_NEG_CRISI = 30, 0.6
CRESCITA_OPP, INDICE_OPP = 2.0, 40
PAUSA_ORE = 6

UA = {'User-Agent': 'AtlanteFVG-monitor/1.0 (+https://atlantefvg.it/)'}


def registro(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- cifratura

def chiave() -> bytes:
    """Stessa chiave della pagina: PBKDF2 sulla parola d'ordine in maiuscolo, sale di monitor/contenuto.json."""
    parola = unicodedata.normalize('NFC', os.environ['MONITOR_PAROLA'].strip().upper())
    sale = base64.b64decode(json.loads((RADICE / 'monitor' / 'contenuto.json').read_text())['s'])
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sale, iterations=300000).derive(parola.encode())


def decifra(percorso: Path, k: bytes) -> dict:
    p = json.loads(percorso.read_text())
    return json.loads(gzip.decompress(AESGCM(k).decrypt(base64.b64decode(p['i']), base64.b64decode(p['d']), None)))


def cifra(dati: dict, k: bytes) -> dict:
    iv = os.urandom(12)
    corpo = gzip.compress(json.dumps(dati, ensure_ascii=False, separators=(',', ':')).encode(), 9)
    return {'v': 1, 'i': base64.b64encode(iv).decode(), 'd': base64.b64encode(AESGCM(k).encrypt(iv, corpo, None)).decode()}


# --------------------------------------------------------------------------- raccolta

def pulisci(testo: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', testo or ''))).strip()


def schema_parole(parole: list[str]):
    return re.compile(r'(?<!\w)(' + '|'.join(re.escape(p) for p in parole) + r')(?!\w)', re.I) if parole else None


def chiave_menzione(fonte: str, ident: str) -> str:
    return hashlib.sha256(f'{fonte}:{ident}'.encode()).hexdigest()[:24]


def data_voce(voce) -> datetime:
    t = voce.get('published_parsed') or voce.get('updated_parsed')
    return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc) if t else ADESSO


def leggi_feed(http: httpx.Client, url: str):
    try:
        r = http.get(url)
        if r.status_code != 200:
            registro(f'  fonte non raggiungibile ({r.status_code}): {url}')
            return []
        return feedparser.parse(r.content).entries
    except httpx.HTTPError as e:
        registro(f'  fonte non raggiungibile ({e.__class__.__name__}): {url}')
        return []


def raccogli(fonti: dict, nomi: list[str], viste: dict) -> list[dict]:
    territorio = schema_parole(fonti['territorio'] + nomi)
    politica = schema_parole(fonti['politica'] + nomi)
    escludi = schema_parole(fonti.get('escludi', []))
    limite = ADESSO - timedelta(hours=ORE_RECENTI)
    nuove: dict[str, dict] = {}

    def aggiungi(fonte, ident, testo, url, testata, quando, autore=None, interazioni=0):
        k = chiave_menzione(fonte, ident)
        if k in viste or k in nuove or not testo or quando < limite:
            return
        nuove[k] = {'chiave': k, 'fonte': fonte, 'testo': testo[:4000], 'url': url, 'testata': testata,
                    'autore_pseudonimo': hashlib.sha256(autore.lower().encode()).hexdigest()[:16] if autore else None,
                    'pubblicato': min(quando, ADESSO).isoformat(), 'interazioni': interazioni}

    with httpx.Client(timeout=20, follow_redirects=True, headers=UA) as http:
        for f in fonti['feed']:
            for v in leggi_feed(http, f['url']):
                testo = pulisci(f"{v.get('title', '')}. {v.get('summary', '')}")
                if f.get('territorio') and not territorio.search(testo):
                    continue
                if f.get('politica') and not politica.search(escludi.sub(' ', testo) if escludi else testo):
                    continue
                aggiungi('rss', v.get('id') or v.get('link') or testo[:120], testo, v.get('link'), f['nome'], data_voce(v))
        # notizie che citano i nomi da seguire (segreto MONITOR_NOMI)
        for nome in nomi:
            for v in leggi_feed(http, fonti['google_news_per_nome'].format(nome=quote(nome))):
                testata = (v.get('source') or {}).get('title') or 'Google News'
                aggiungi('rss', v.get('id') or v.get('link'), pulisci(v.get('title', '')), v.get('link'), testata, data_voce(v))
        # Bluesky, se configurato
        if os.getenv('BLUESKY_UTENTE') and os.getenv('BLUESKY_PASSWORD_APP'):
            s = http.post('https://bsky.social/xrpc/com.atproto.server.createSession',
                          json={'identifier': os.environ['BLUESKY_UTENTE'], 'password': os.environ['BLUESKY_PASSWORD_APP']})
            if s.status_code == 200:
                tok = s.json()['accessJwt']
                for ricerca in ['Friuli Venezia Giulia', 'Regione FVG', *nomi]:
                    r = http.get('https://bsky.social/xrpc/app.bsky.feed.searchPosts', headers={'Authorization': f'Bearer {tok}'},
                                 params={'q': f'"{ricerca}"', 'lang': 'it', 'sort': 'latest', 'limit': 50})
                    for p in (r.json().get('posts', []) if r.status_code == 200 else []):
                        handle, rk = p['author']['handle'], p['uri'].rsplit('/', 1)[-1]
                        aggiungi('bluesky', p['uri'], p['record'].get('text', ''), f'https://bsky.app/profile/{handle}/post/{rk}', 'Bluesky',
                                 datetime.fromisoformat(p['record'].get('createdAt', ADESSO.isoformat()).replace('Z', '+00:00')),
                                 p['author']['did'], p.get('likeCount', 0) + p.get('repostCount', 0) + p.get('replyCount', 0))
            else:
                registro(f'  accesso a Bluesky non riuscito ({s.status_code})')
    elenco = sorted(nuove.values(), key=lambda m: m['pubblicato'], reverse=True)
    registro(f'Menzioni nuove trovate: {len(elenco)}')
    return elenco


# --------------------------------------------------------------------------- analisi

ISTRUZIONI = """Analista politico del Friuli Venezia Giulia. Valuta il tono reale dell'autore del testo.
- Notizia che riporta fatti senza giudizio: neutro.
- Proteste, critiche, attacchi, disservizi, reati, disagi: negativo.
- Apprezzamenti sinceri, buone notizie: positivo.
- sarcasmo = true quando il testo loda, si complimenta o ringrazia in modo ironico per qualcosa di negativo (es. «Complimenti, cantiere fermo da mesi», «Grazie per il treno soppresso»); in quel caso il tono è negativo. Un elogio sincero di una cosa bella ha sarcasmo = false.
- Il testo può essere in italiano, friulano, triestino, veneto o sloveno.
intensita: forza del tono da 0 a 1. temi: uno o due dell'elenco consentito, il primo è il principale. persone_partiti: nomi di persone o partiti citati. motivo: massimo 12 parole."""
TEMI = ['sanità', 'viabilità', 'trasporti', 'scuola', 'sicurezza', 'lavoro', 'economia', 'ambiente', 'casa', 'sociale', 'cultura',
        'sport', 'turismo', 'agricoltura', 'immigrazione', 'protezione civile', 'bilancio', 'istituzioni', 'elezioni', 'altro']
EMOZIONI = ['rabbia', 'paura', 'entusiasmo', 'fiducia', 'tristezza', 'indifferenza']
SCHEMA = {'type': 'object', 'required': ['polarita', 'intensita', 'sarcasmo', 'emozione', 'temi', 'persone_partiti', 'motivo'], 'properties': {
    'polarita': {'type': 'string', 'enum': ['positivo', 'neutro', 'negativo']}, 'intensita': {'type': 'number'},
    'sarcasmo': {'type': 'boolean'}, 'emozione': {'type': 'string', 'enum': EMOZIONI},
    'temi': {'type': 'array', 'items': {'type': 'string', 'enum': TEMI}, 'minItems': 1, 'maxItems': 2},
    'persone_partiti': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 3}, 'motivo': {'type': 'string'}}}
SIGLE_PARTITI = {'pd', 'fdi', 'lega', 'fi', 'm5s', 'avs', 'azione', 'italia viva', 'forza italia', 'fratelli d\'italia',
                 'partito democratico', 'movimento 5 stelle', 'patto per l\'autonomia', 'alleanza verdi e sinistra'}


def limita(v, a, b):
    return max(a, min(b, float(v)))


def carica_modello():
    from llama_cpp import Llama
    return Llama(model_path=MODELLO_FILE, n_ctx=2048, n_threads=os.cpu_count() or 4, verbose=False)


def analizza(llm, m: dict) -> dict | None:
    """Analisi di una menzione con il modello locale; None se la risposta non è utilizzabile."""
    try:
        r = llm.create_chat_completion(
            messages=[{'role': 'system', 'content': ISTRUZIONI},
                      {'role': 'user', 'content': f"Testata: {m['testata']}\nTesto: {m['testo'][:1500]} /no_think"}],
            response_format={'type': 'json_object', 'schema': SCHEMA}, temperature=0.1, max_tokens=180)
        x = json.loads(r['choices'][0]['message']['content'])
        pol, forza = x['polarita'], limita(x['intensita'], 0, 1)
        emo = x['emozione'] if x['emozione'] in EMOZIONI and pol != 'neutro' else 'indifferenza'
    except Exception as e:  # risposta troncata o non valida: la menzione resta per il giro dopo
        registro(f'  analisi non riuscita ({e.__class__.__name__})')
        return None
    forza_emo = max(forza, 0.5) if emo != 'indifferenza' else 0
    temi = list(dict.fromkeys(t for t in x['temi'] if t in TEMI and t != 'altro'))[:1] or ['altro']
    # solo nomi propri (iniziale maiuscola) o sigle di partito: si scartano parole come «ministro» o «sindaco»
    entita = [{'testo': n.strip(), 'tipo': 'partito' if n.strip().lower() in SIGLE_PARTITI or 'partito' in n.lower() else 'persona'}
              for n in x['persone_partiti']
              if 1 < len(n.strip()) <= 80 and (n.strip()[0].isupper() or n.strip().lower() in SIGLE_PARTITI)][:3]
    return {
        'polarita': pol, 'punteggio': {'positivo': 1, 'negativo': -1}.get(pol, 0) * forza, 'confidenza': 0.8,
        'sarcasmo': bool(x['sarcasmo']) and pol == 'negativo', 'emozione_dominante': emo,
        'emozioni': {e: (forza_emo if e == emo else 0.0) for e in EMOZIONI if e != 'indifferenza'},
        'dialetto': None, 'entita': entita, 'temi': temi, 'bersaglio': None,
        'ostilita': 0.0,  # non misurata da questo modello: meglio nessun dato che un dato inaffidabile
        'motivazione': str(x['motivo'])[:160], 'motore': MOTORE,
    }


# --------------------------------------------------------------------------- allerte

def indice(lista):
    pesi = sum(m['analisi']['confidenza'] for m in lista)
    return 100 * sum(m['analisi']['punteggio'] * m['analisi']['confidenza'] for m in lista) / pesi if pesi else 0.0


def quota_neg(lista):
    return sum(m['analisi']['polarita'] == 'negativo' for m in lista) / len(lista) if lista else 0.0


def media_em(lista, e):
    return mean(m['analisi']['emozioni'].get(e, 0) for m in lista) if lista else 0.0


def rileva(menzioni: list[dict], ultime: dict) -> list[dict]:
    t = lambda m: datetime.fromisoformat(m['pubblicato'])
    inizio_f = ADESSO - timedelta(minutes=FINESTRA_MIN)
    inizio_b = inizio_f - timedelta(hours=BASE_ORE)
    recenti, base = defaultdict(list), defaultdict(list)
    for m in menzioni:
        q = t(m)
        if q < inizio_b:
            continue
        dest = recenti if q >= inizio_f else base
        a = m['analisi']
        for amb in ['generale', *[f'tema:{x}' for x in a['temi']],
                    *[f"{e['tipo']}:{e['testo']}" for e in a['entita'] if e['tipo'] in ('persona', 'partito')]]:
            dest[amb].append(m)
    nuove = []

    def crea(tipo, sotto, amb, grav, descr, f):
        k = f'{tipo}|{sotto}|{amb}'
        if k in ultime and ADESSO - datetime.fromisoformat(ultime[k]) < timedelta(hours=PAUSA_ORE):
            return
        ultime[k] = ADESSO.isoformat()
        nome = amb.split(':', 1)[-1]
        esempi = sorted(f, key=lambda m: m['analisi']['confidenza'], reverse=True)[:3]
        nuove.append({'id': uuid.uuid4().hex, 'tipo': tipo, 'sottotipo': sotto, 'ambito': amb, 'gravita': grav, 'descrizione': descr,
                      'titolo': ('Allerta crisi' if tipo == 'crisi' else 'Opportunità di consenso') + f': {nome}',
                      'temi_collegati': [x for x, _ in Counter(y for m in f for y in m['analisi']['temi']).most_common(3)],
                      'esempi': [{'testo': m['testo'][:280], 'url': m.get('url'), 'fonte': m['fonte']} for m in esempi],
                      'metriche': {}, 'creata': ADESSO.isoformat()})

    for amb, f in recenti.items():
        b = base.get(amb, [])
        crescita = (len(f) / FINESTRA_MIN) / max(len(b) / (BASE_ORE * 60), 1e-9)
        ind, neg, rabbia = indice(f), quota_neg(f), media_em(f, 'rabbia')
        if len(f) >= VOLUME_MINIMO:
            calo = indice(b) - ind if b else 0
            crollo, indign = calo >= CALO_CRISI and neg >= 0.5, neg >= QUOTA_NEG_CRISI and rabbia >= 0.5
            if crollo or indign:
                crea('crisi', 'indignazione' if indign else 'calo improvviso', amb, 3 if neg >= 0.8 else 2,
                     f'{len(f)} menzioni nelle ultime {FINESTRA_MIN // 60} ore, ' +
                     (f'indice sceso di {calo:.0f} punti rispetto alle {BASE_ORE} ore precedenti.' if crollo else f'{neg:.0%} negative con rabbia diffusa.'), f)
            gruppi = defaultdict(set)
            for m in f:
                if m['fonte'] != 'rss':
                    gruppi[re.sub(r'\s+', ' ', re.sub(r'https?://\S+|@\w+|#', '', m['testo'].lower()))[:90]].add(m.get('autore_pseudonimo'))
            massimo = max((len(s) for s in gruppi.values()), default=0)
            if massimo >= 5 and massimo >= 0.25 * len(f):
                crea('crisi', 'ondata coordinata', amb, 3, f'{massimo} profili diversi pubblicano lo stesso testo: possibile azione organizzata.', f)
        if amb != 'generale' and len(f) >= max(3, VOLUME_MINIMO // 2) and crescita >= CRESCITA_OPP and ind >= INDICE_OPP and media_em(f, 'entusiasmo') >= 0.4:
            crea('opportunita', 'tema in crescita favorevole', amb, 3 if ind >= 60 else 2,
                 f'Volume {crescita:.1f} volte superiore alla media, indice {ind:+.0f}.', f)
    return nuove


def notifica(allerte: list[dict]) -> None:
    tok, chat = os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_STAFF')
    if not (tok and chat):
        return
    with httpx.Client(timeout=15) as http:
        for a in allerte:
            righe = [('🔴 ' if a['tipo'] == 'crisi' else '🟢 ') + a['titolo'], f"{a['sottotipo']} · gravità {a['gravita']}/3", a['descrizione']]
            righe += [f"• {e['testo'][:160]}" + (f"\n  {e['url']}" if e.get('url') else '') for e in a['esempi']]
            righe.append('https://atlantefvg.it/monitor/')
            try:
                http.post(f'https://api.telegram.org/bot{tok}/sendMessage', json={'chat_id': chat, 'text': '\n'.join(righe), 'disable_web_page_preview': True})
            except httpx.HTTPError:
                registro('  avviso Telegram non inviato')


# --------------------------------------------------------------------------- giro completo

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    precedente, uscita = Path(sys.argv[1]), Path(sys.argv[2])
    if not os.getenv('MONITOR_PAROLA'):
        registro('Segreto MONITOR_PAROLA assente: nessuna raccolta (vedi README, sezione Monitor).')
        return
    k = chiave()
    stato = {'menzioni': [], 'allerte': [], 'viste': {}, 'ultime_allerte': {}}
    if precedente.exists() and precedente.stat().st_size:
        try:
            stato.update(decifra(precedente, k))
        except Exception:
            registro('Stato precedente non leggibile (parola d\'ordine cambiata?): si riparte da zero.')
    nomi = [n.strip() for n in os.getenv('MONITOR_NOMI', '').split(',') if len(n.strip()) >= 2][:20]
    fonti = json.loads((RADICE / 'scripts' / 'monitor_fonti.json').read_text(encoding='utf-8'))

    # Se le menzioni nuove superano il limite, si analizzano prima quelle che citano un nome seguito, poi le più recenti:
    # le altre restano non viste e passano al giro dopo.
    schema_nomi = schema_parole(nomi)
    candidate = sorted(raccogli(fonti, nomi, stato['viste']), key=lambda m: m['pubblicato'], reverse=True)
    candidate = sorted(candidate, key=lambda m: not (schema_nomi and schema_nomi.search(m['testo'])))[:MAX_PER_GIRO]
    nuove = []
    if candidate:
        llm, inizio = carica_modello(), time.monotonic()
        for m in candidate:
            if time.monotonic() - inizio > MINUTI_MAX * 60:
                registro('  tempo massimo raggiunto: le altre menzioni passano al giro successivo')
                break
            a = analizza(llm, m)
            if a:
                nuove.append({**m, 'raccolto': ADESSO.isoformat(), 'analisi': a})
                stato['viste'][m['chiave']] = ADESSO.isoformat()
    registro(f'Menzioni analizzate: {len(nuove)} su {len(candidate)}')

    limite = (ADESSO - timedelta(hours=ORE_MENZIONI)).isoformat()
    stato['menzioni'] = [m for m in stato['menzioni'] + nuove if m['raccolto'] >= limite]
    allerte = rileva(stato['menzioni'], stato['ultime_allerte'])
    if allerte:
        registro(f'Allerte nuove: {len(allerte)}')
        notifica(allerte)
    stato['allerte'] = [a for a in stato['allerte'] + allerte if a['creata'] >= limite]
    lim_viste = (ADESSO - timedelta(days=GIORNI_VISTE)).isoformat()
    stato['viste'] = {x: q for x, q in stato['viste'].items() if q >= lim_viste}
    stato['ultime_allerte'] = {x: q for x, q in stato['ultime_allerte'].items() if q >= limite}
    stato['generato'] = ADESSO.isoformat()
    stato['nomi_seguiti'] = nomi
    uscita.write_text(json.dumps(cifra(stato, k)))
    registro(f"Stato scritto: {len(stato['menzioni'])} menzioni, {len(stato['allerte'])} allerte nelle ultime {ORE_MENZIONI} ore")


if __name__ == '__main__':
    main()
