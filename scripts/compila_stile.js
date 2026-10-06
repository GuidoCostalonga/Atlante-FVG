#!/usr/bin/env node
/*
 Compila lo stile e le icone dell'Atlante dentro index.html, così il telefono non deve generarli
 mentre apre la pagina.

 - Stile: Tailwind CSS 3.4 legge le classi usate in index.html e scrive solo quelle, compresse,
   fra i segni tailwind:inizio e tailwind:fine.
 - Icone: dalla raccolta Lucide 0.469 prende solo le icone nominate nella pagina e le scrive,
   con una piccola funzione lucide.createIcons(), fra i segni icone:inizio e icone:fine.

 Preparazione (una volta): npm i --no-save tailwindcss@3.4.19 lucide@0.469.0
 Uso: node scripts/compila_stile.js [percorso di index.html]
*/
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const RADICE = path.resolve(__dirname, '..');
const FILE = path.resolve(process.argv[2] || path.join(RADICE, 'index.html'));
let html = fs.readFileSync(FILE, 'utf8');
const sostituisci = (nome, testo) => {
  const re = new RegExp(`/\\*${nome}:inizio\\*/[\\s\\S]*?/\\*${nome}:fine\\*/`);
  if (!re.test(html)) throw new Error(`segni ${nome} non trovati in ${FILE}`);
  html = html.replace(re, () => `/*${nome}:inizio*/${testo}/*${nome}:fine*/`);
};

// 1. stile: si svuota prima il vecchio, perché le classi vanno lette dalla pagina e non dallo stile già compilato
sostituisci('tailwind', '');
const tmp = path.join(require('os').tmpdir(), 'atlante-' + process.pid + '.html');
fs.writeFileSync(tmp, html);
const bin = require.resolve('tailwindcss/lib/cli.js');
const css = execFileSync(process.execPath, [bin, '-c', path.join(RADICE, 'stile/tailwind.config.js'), '-i', path.join(RADICE, 'stile/ingresso.css'), '--content', tmp, '--minify'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
fs.unlinkSync(tmp);
sostituisci('tailwind', css.replace(/<\//g, '<\\/').trim());

// 2. icone: tutte le parole della pagina che sono nomi di icone Lucide
const { icons } = require('lucide');
const pascal = s => s.replace(/(^|-)([a-z0-9])/g, (m, a, b) => b.toUpperCase());
const usate = {};
for (const w of new Set(html.match(/[a-z][a-z0-9]*(?:-[a-z0-9]+)*/g))) { const ic = icons[pascal(w)]; if (ic && /[a-z]/.test(w)) usate[w] = ic[2]; }
const js = `window.lucide=(()=>{const I=${JSON.stringify(usate)},N='http://www.w3.org/2000/svg',A={xmlns:N,width:24,height:24,viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':2,'stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true'};`
  + `const nodo=([t,a,f])=>{const e=document.createElementNS(N,t);for(const k in a)e.setAttribute(k,a[k]);(f||[]).forEach(x=>e.appendChild(nodo(x)));return e};`
  + `return{createIcons(){document.querySelectorAll('i[data-lucide]').forEach(el=>{const n=el.getAttribute('data-lucide'),d=I[n];if(!d)return;const s=nodo(['svg',A,d]);`
  + `for(const at of el.attributes)if(at.name!=='class')s.setAttribute(at.name,at.value);s.setAttribute('class',('lucide lucide-'+n+' '+(el.getAttribute('class')||'')).trim());el.replaceWith(s)})}}})();`;
sostituisci('icone', js.replace(/<\//g, '<\\/'));
fs.writeFileSync(FILE, html);
console.log(`Stile: ${Math.round(css.length / 1024)} KB · icone: ${Object.keys(usate).length}`);
