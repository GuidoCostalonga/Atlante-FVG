/* Consenso ai cookie statistici e Google Analytics 4 (GA4) per atlantefvg.it.
 *
 * Regole (Linee guida cookie del Garante per la protezione dei dati personali, 10 giugno 2021):
 * - finché la persona non sceglie, nessun cookie di Google e nessuna richiesta a Google: lo script di GA4
 *   si scarica solo dopo «Accetta»;
 * - «Accetta» e «Rifiuta» hanno la stessa evidenza; la X chiude il banner e vale come rifiuto;
 * - la scelta resta per 6 mesi, poi il banner si ripropone; si cambia in ogni momento con
 *   «Preferenze sui cookie» in fondo a ogni pagina (o con un elemento che abbia data-consenso-apri);
 * - Consent Mode v2: tutto negato per impostazione predefinita; con il consenso si concede solo
 *   analytics_storage, mai i segnali pubblicitari.
 * Finché ID_MISURAZIONE è il segnaposto lo script non fa nulla: niente banner, niente GA4.
 * La scelta sta nel browser (localStorage, chiave atlante-fvg:consenso): è uno strumento tecnico.
 */
(function () {
  'use strict';
  var ID_MISURAZIONE = 'G-380D56PCJN';
  var CHIAVE = 'atlante-fvg:consenso', VERSIONE = 1;
  var DURATA_SCELTA = 182 * 24 * 3600 * 1000; // 6 mesi
  var DURATA_COOKIE = 182 * 24 * 3600;        // i cookie di GA4 non durano più della scelta
  var INFORMATIVA = '/metodo/#cookie';

  if (!/^G-[A-Z0-9]{4,}$/.test(ID_MISURAZIONE) || /^G-X+$/.test(ID_MISURAZIONE)) return;
  if (window.atlanteConsenso) return;

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = window.gtag || gtag;
  gtag('consent', 'default', {
    ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
    analytics_storage: 'denied', functionality_storage: 'denied', personalization_storage: 'denied',
    security_storage: 'granted'
  });
  gtag('set', 'ads_data_redaction', true);

  function leggi() {
    try {
      var s = JSON.parse(localStorage.getItem(CHIAVE) || 'null');
      if (!s || s.v !== VERSIONE || (s.scelta !== 'si' && s.scelta !== 'no')) return null;
      if (!(Date.now() - new Date(s.data).getTime() < DURATA_SCELTA)) return null;
      return s.scelta;
    } catch (e) { return null; }
  }
  function salva(scelta) {
    try { localStorage.setItem(CHIAVE, JSON.stringify({ v: VERSIONE, scelta: scelta, data: new Date().toISOString() })); } catch (e) { /* senza memoria la scelta vale finché la pagina resta aperta */ }
  }

  var caricato = false;
  function attivaGA() {
    gtag('consent', 'update', { analytics_storage: 'granted' });
    if (caricato) return;
    caricato = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(ID_MISURAZIONE);
    document.head.appendChild(s);
    gtag('js', new Date());
    gtag('config', ID_MISURAZIONE, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      cookie_expires: DURATA_COOKIE,
      cookie_flags: 'SameSite=Lax;Secure'
    });
  }
  function cancellaCookieGA() {
    var nomi = document.cookie.split(';').map(function (c) { return c.split('=')[0].trim(); })
      .filter(function (n) { return n === '_ga' || n.indexOf('_ga_') === 0 || n === '_gid' || n === '_gat'; });
    var host = location.hostname, domini = ['', host, '.' + host];
    var parti = host.split('.');
    if (parti.length > 2) domini.push('.' + parti.slice(-2).join('.'));
    nomi.forEach(function (n) {
      domini.forEach(function (d) {
        document.cookie = n + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/' + (d ? '; domain=' + d : '');
      });
    });
  }

  var STILE = '' +
    '.cs-banner{position:fixed;left:12px;right:12px;bottom:12px;z-index:2147483000;max-width:640px;margin:0 auto;' +
    'background:#FBF8F1;color:#1F2A37;border:1px solid #C9B98F;border-radius:12px;box-shadow:0 10px 30px rgba(11,51,89,.25);' +
    'padding:18px 18px 16px;font:15px/1.5 "Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",sans-serif}' +
    '.cs-banner h2{margin:0 32px 6px 0;font:700 18px/1.3 "Source Serif 4",Georgia,serif;color:#0B3359}' +
    '.cs-banner p{margin:0 0 12px}' +
    '.cs-banner a{color:#0B3359;text-decoration:underline}' +
    '.cs-azioni{display:flex;gap:10px;flex-wrap:wrap}' +
    '.cs-azioni button{flex:1 1 140px;min-height:44px;padding:10px 16px;border-radius:8px;border:2px solid #0B3359;' +
    'background:#0B3359;color:#fff;font-weight:600;font-size:15px;line-height:1.2;font-family:inherit;cursor:pointer}' +
    '.cs-azioni button:hover{background:#082641;border-color:#082641}' +
    '.cs-banner button:focus-visible,.cs-piede button:focus-visible{outline:3px solid #C99A2E;outline-offset:2px}' +
    '.cs-chiudi{position:absolute;top:8px;right:8px;width:44px;height:44px;border:0;background:transparent;color:#0B3359;' +
    'font:400 26px/1 system-ui,sans-serif;cursor:pointer;border-radius:8px}' +
    '.cs-piede{margin:8px 0 0}' +
    '.cs-piede button{background:none;border:0;padding:0;color:inherit;font:inherit;text-decoration:underline;cursor:pointer}' +
    '@media print{.cs-banner{display:none}}';

  var banner = null, provenienza = null;
  function stile() {
    if (document.getElementById('cs-stile')) return;
    var st = document.createElement('style');
    st.id = 'cs-stile';
    st.textContent = STILE;
    document.head.appendChild(st);
  }
  function chiudi() {
    if (banner) { banner.remove(); banner = null; }
    if (provenienza && document.contains(provenienza)) provenienza.focus();
    provenienza = null;
  }
  function scegli(scelta) {
    var prima = leggi();
    salva(scelta);
    chiudi();
    if (scelta === 'si') { attivaGA(); return; }
    gtag('consent', 'update', { analytics_storage: 'denied' });
    cancellaCookieGA();
    // GA4 già avviato non si spegne da solo: si ricarica la pagina per fermarlo
    if (caricato || prima === 'si') location.reload();
  }
  function apri(daElemento) {
    if (banner) return;
    stile();
    provenienza = daElemento || null;
    banner = document.createElement('div');
    banner.className = 'cs-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-modal', 'false');
    banner.setAttribute('aria-labelledby', 'cs-titolo');
    banner.setAttribute('aria-describedby', 'cs-testo');
    banner.innerHTML =
      '<button type="button" class="cs-chiudi" data-cs="no" aria-label="Chiudi: continua senza cookie statistici">×</button>' +
      '<h2 id="cs-titolo">Ci aiuti a migliorare l’Atlante?</h2>' +
      '<p id="cs-testo">Senza il tuo permesso l’Atlante usa solo strumenti tecnici e un contatore di visite che non usa cookie. ' +
      'Se accetti, usiamo anche Google Analytics 4: cookie statistici che ci dicono quali pagine servono e dove migliorarle. ' +
      'Niente pubblicità e niente profili. I dati passano da Google e possono arrivare negli Stati Uniti d’America. ' +
      'Puoi cambiare idea quando vuoi con «Preferenze sui cookie» in fondo alla pagina. ' +
      '<a href="' + INFORMATIVA + '">Informativa sui cookie</a></p>' +
      '<div class="cs-azioni"><button type="button" data-cs="no">Rifiuta</button><button type="button" data-cs="si">Accetta</button></div>';
    banner.addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-cs]');
      if (b) scegli(b.getAttribute('data-cs'));
    });
    banner.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') scegli('no'); });
    document.body.appendChild(banner);
    if (daElemento) { var p = banner.querySelector('.cs-azioni button'); if (p) p.focus(); }
  }
  function collegamentoPiede() {
    var piedi = document.querySelectorAll('footer');
    if (!piedi.length || document.querySelector('.cs-piede')) return;
    stile();
    var p = document.createElement('p');
    p.className = 'cs-piede';
    p.innerHTML = '<button type="button" data-consenso-apri>Preferenze sui cookie</button>';
    piedi[piedi.length - 1].appendChild(p);
  }

  document.addEventListener('click', function (ev) {
    var el = ev.target.closest && ev.target.closest('[data-consenso-apri]');
    if (!el) return;
    ev.preventDefault();
    apri(el);
  });

  window.atlanteConsenso = { apri: function () { apri(null); }, stato: leggi };

  function avvia() {
    collegamentoPiede();
    var s = leggi();
    if (s === 'si') attivaGA();
    else if (s === null) apri(null);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', avvia);
  else avvia();
})();
