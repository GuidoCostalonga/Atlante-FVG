#!/usr/bin/env python3
"""Controlli sul sito pubblicato, da eseguire dopo ogni rilascio.

Verifica:
1. reindirizzamenti: http e www portano a https://atlantefvg.it conservando percorso e parametri;
2. robots.txt e sitemap.xml: presenti, nessuna pagina pubblica esclusa;
3. ogni indirizzo della sitemap: risponde 200, ha un solo H1, titolo e descrizione unici,
   indirizzo canonico uguale al proprio, dati strutturati leggibili, nessun «noindex»;
4. collegamenti interni delle pagine statiche: nessuno rotto;
5. pagina principale: i file di dati citati nell'elenco dei fogli rispondono tutti;
6. servizi esterni usati dalla pagina (fonti in tempo reale): rispondono (solo avviso).

Esce con codice 1 se trova errori. In GitHub Actions scrive il riepilogo nella pagina del lavoro.
Usa solo la libreria standard di Python.
Uso: python scripts/controlla_rilascio.py [indirizzo del sito]
"""
import time, concurrent.futures as cf, html.parser, json, os, re, sys, urllib.error, urllib.parse, urllib.request

SITO = (sys.argv[1] if len(sys.argv) > 1 else 'https://atlantefvg.it').rstrip('/')
UA = {'User-Agent': 'AtlanteFVG-controlli/1.0 (+https://atlantefvg.it/)'}
errori, avvisi, fatti = [], [], []


class SenzaRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def apri(url, segui=True, metodo='GET', tentativi=3):
    # nel minuto dopo la pubblicazione la rete di GitHub Pages risponde a volte 503 a un singolo file: si riprova
    op = urllib.request.build_opener() if segui else urllib.request.build_opener(SenzaRedirect)
    for k in range(tentativi):
        try:
            r = op.open(urllib.request.Request(url, headers=UA, method=metodo), timeout=30)
            return r.status, r.headers, r.read() if metodo == 'GET' else b'', r.geturl()
        except urllib.error.HTTPError as e:
            if e.code < 500 or k == tentativi - 1:
                return e.code, e.headers, b'', url
        except Exception as e:  # rete, certificati, tempo scaduto
            if k == tentativi - 1:
                return 0, {}, str(e).encode(), url
        time.sleep(5 * (k + 1))


class Pagina(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.h1 = 0; self.titolo = ''; self.descr = None; self.can = None; self.robots = ''; self.ld = []; self.link = []
        self._t = self._ld = False

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == 'h1': self.h1 += 1
        elif tag == 'title': self._t = True
        elif tag == 'meta' and a.get('name') == 'description': self.descr = a.get('content')
        elif tag == 'meta' and a.get('name') == 'robots': self.robots = a.get('content', '')
        elif tag == 'link' and a.get('rel') == 'canonical': self.can = a.get('href')
        elif tag == 'script' and a.get('type') == 'application/ld+json': self._ld = True; self.ld.append('')
        elif tag == 'a' and a.get('href'): self.link.append(a['href'])

    def handle_endtag(self, tag):
        if tag == 'title': self._t = False
        if tag == 'script': self._ld = False

    def handle_data(self, d):
        if self._t: self.titolo += d
        if self._ld: self.ld[-1] += d


def controlla_redirect():
    ospite = urllib.parse.urlparse(SITO).netloc
    for da in (f'http://{ospite}/c/udine/?prova=1', f'https://www.{ospite}/c/udine/?prova=1', f'http://www.{ospite}/c/udine/?prova=1'):
        st, _, corpo, finale = apri(da)
        if st != 200 or finale != f'{SITO}/c/udine/?prova=1':
            (errori if st else avvisi).append(f'Reindirizzamento: {da} arriva a {finale} con stato {st} {corpo[:80] if not st else ""}')
        else:
            fatti.append(f'{da} → {finale}')


def controlla_pagina(url):
    st, h, corpo, _ = apri(url)
    if st != 200:
        return url, None, [f'{url}: stato {st}']
    p = Pagina(); p.feed(corpo.decode('utf-8', 'replace'))
    e = []
    if p.h1 != 1: e.append(f'{url}: {p.h1} titoli H1 invece di uno')
    if not p.titolo.strip(): e.append(f'{url}: manca il titolo')
    if not p.descr: e.append(f'{url}: manca la descrizione')
    if p.can != url: e.append(f'{url}: indirizzo canonico {p.can}')
    if 'noindex' in p.robots.lower() or 'noindex' in (h.get('X-Robots-Tag') or '').lower(): e.append(f'{url}: escluso dai motori di ricerca (noindex)')
    for x in p.ld:
        try: json.loads(x)
        except ValueError: e.append(f'{url}: dati strutturati non leggibili')
    return url, p, e


def main():
    controlla_redirect()
    st, _, rob, _ = apri(SITO + '/robots.txt')
    if st != 200 or b'Sitemap:' not in rob or re.search(rb'Disallow:\s*/\s*$', rob, re.M):
        errori.append(f'robots.txt: stato {st} o contenuto inatteso')
    st, _, sm, _ = apri(SITO + '/sitemap.xml')
    indirizzi = re.findall(r'<loc>([^<]+)</loc>', sm.decode()) if st == 200 else []
    if len(indirizzi) < 200:
        errori.append(f'sitemap.xml: stato {st}, {len(indirizzi)} indirizzi')
    pagine = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for url, p, e in ex.map(controlla_pagina, indirizzi):
            errori.extend(e); pagine[url] = p
    titoli, descr = {}, {}
    for url, p in pagine.items():
        if p:
            titoli.setdefault(p.titolo.strip(), []).append(url); descr.setdefault(p.descr, []).append(url)
    errori.extend(f'Titolo ripetuto in {len(v)} pagine: {k}' for k, v in titoli.items() if len(v) > 1)
    errori.extend(f'Descrizione ripetuta in {len(v)} pagine: {v[0]}' for k, v in descr.items() if len(v) > 1)
    # collegamenti interni delle pagine statiche (senza parametri: quelli li gestisce la pagina principale)
    interni = set()
    for url, p in pagine.items():
        for l in (p.link if p else []):
            a = urllib.parse.urljoin(url, l)
            if a.startswith(SITO) and '?' not in a and '#' not in a:
                interni.add(a)
    with cf.ThreadPoolExecutor(8) as ex:
        for a, (st, *_) in zip(interni, ex.map(lambda u: apri(u, metodo='HEAD'), interni)):
            if st != 200: errori.append(f'Collegamento interno rotto: {a} (stato {st})')
    # file di dati della pagina principale
    st, _, home, _ = apri(SITO + '/')
    m = re.search(rb'^const MAN = (.*);$', home, re.M)
    file_dati = sorted({f for x in json.loads(m.group(1))['manifest'] for f in x['files']}) if m else []
    file_dati += ['dati/_mappe_0.txt', 'dati/_punti_0.txt', 'dati/_tpl_0.txt', 'dati/bandi.json', 'dati/aggiornamenti.json', 'dati/opere_meta.json', 'dati/comuni_slug.json']
    with cf.ThreadPoolExecutor(8) as ex:
        for f, (st, *_) in zip(file_dati, ex.map(lambda f: apri(f'{SITO}/{f}', metodo='HEAD'), file_dati)):
            if st != 200: errori.append(f'File di dati mancante: {f} (stato {st})')
    # servizi esterni: solo avviso, non dipendono dal rilascio
    for nome, u in (('Grafici (Chart.js)', 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js'),
                    ('Excel (SheetJS)', 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js'),
                    ('Arrivi degli autobus (BusOne)', 'https://proxy.busone.app/TPLFVG/gtfs.zip'),
                    ('Qualità dell\'aria (dati aperti della Regione)', 'https://www.dati.friuliveneziagiulia.it/api/views/metadata/v1?limit=1'),
                    ('Bollettino di criticità (Protezione civile)', 'https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/master/README.md')):
        st, *_ = apri(u, metodo='HEAD')
        (fatti if st == 200 else avvisi).append(f'{nome}: stato {st}')
    rip = [f'## Controlli dopo il rilascio di {SITO}', '',
           f'- Pagine della sitemap controllate: {len(indirizzi)}', f'- Collegamenti interni controllati: {len(interni)}', f'- File di dati controllati: {len(file_dati)}',
           f'- Errori: **{len(errori)}** · Avvisi: {len(avvisi)}', '']
    rip += ['### Errori', *[f'- {x}' for x in errori[:200]], ''] if errori else []
    rip += ['### Avvisi', *[f'- {x}' for x in avvisi], ''] if avvisi else []
    rip += ['### Verifiche riuscite', *[f'- {x}' for x in fatti]]
    testo = '\n'.join(rip)
    print(testo)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f: f.write(testo + '\n')
    sys.exit(1 if errori else 0)


if __name__ == '__main__':
    main()
