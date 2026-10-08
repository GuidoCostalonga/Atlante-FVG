// ---------- filtri unici delle comunali
// Un solo pannello (#filtriCom) governa mappa, indicatori, sintesi e tabelle della vista «Comunali».
// EL(i) è l'elezione del comune i scelta con il filtro «Elezione»; passaFiltri(i) dice se il comune resta nell'ambito.
const FC_DIM=[["","Tutte le dimensioni"],["1","Fino a 1.000 elettori"],["2","Da 1.001 a 3.000 elettori"],["3","Da 3.001 a 12.000 elettori"],["4","Oltre 12.000 elettori"]];
const FC_ESITO=[["","Tutti gli esiti"],["unico","Candidato sindaco unico"],["piu","Più candidati sindaco"],["ball","Con ballottaggio"],["partito","Sindaco sostenuto da una lista di partito"]];
const FC_ANNI=[...new Set(CONS.filter(c=>c.o>0).map(anno))].sort((a,b)=>b-a);
function EL(i){
  const e=PER_COM[i];
  if (S.fcEl==="1"||S.fcEl==="2"||S.fcEl==="3") return e.find(c=>c.o===+S.fcEl);
  return e.find(c=>c.o>0 && anno(c)===+S.fcEl);
}
const ELC = i => EL(i) || ULT[i];
function fasciaEl(i){ const el=D23.comuni[i].el; return el<=1000?"1":el<=3000?"2":el<=12000?"3":"4"; }
function passaFiltri(i){
  const c=EL(i); if(!c) return false;
  if (S.fcPart!=="" && !c.L.some(l=>l.pa.includes(+S.fcPart))) return false;
  if (S.fcDim && fasciaEl(i)!==S.fcDim) return false;
  if (S.fcEsito==="unico" && c.S.length!==1) return false;
  if (S.fcEsito==="piu" && c.S.length<2) return false;
  if (S.fcEsito==="ball" && !c.ba) return false;
  if (S.fcEsito==="partito"){ const w=vincitore(c); if(!w || !c.L.some(l=>l.s===w.s.n && l.pa.length)) return false; }
  return true;
}
function ambitoCom(){ return (S.circ ? TUTTI.filter(i=>C[i].ci===S.circ) : TUTTI).filter(passaFiltri); }
// etichetta dell'elezione scelta: «all'ultima elezione», «alla penultima elezione», «nell'elezione del 2024»
function etEl(){ return S.fcEl==="1"?"all'ultima elezione":S.fcEl==="2"?"alla penultima elezione":S.fcEl==="3"?"alla terzultima elezione":"nell'elezione del "+S.fcEl; }
function etElBreve(){ return S.fcEl==="1"?"ultima elezione":S.fcEl==="2"?"penultima elezione":S.fcEl==="3"?"terzultima elezione":"elezione del "+S.fcEl; }
const cap = s => s.charAt(0).toUpperCase()+s.slice(1);
const normTesto = s => String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"");
function filtriAttivi(){ return S.fcEl!=="1" || S.fcPart!=="" || S.fcDim!=="" || S.fcEsito!=="" || S.fcCerca!==""; }
function descriviFiltri(){
  const v=[];
  v.push(etElBreve()+(S.fcEl==="1"||S.fcEl==="2"||S.fcEl==="3"?" di ogni comune":""));
  if (S.fcPart!=="") v.push("liste con il nome "+PART[+S.fcPart].n);
  if (S.fcDim) v.push(FC_DIM.find(x=>x[0]===S.fcDim)[1].toLowerCase());
  if (S.fcEsito) v.push(FC_ESITO.find(x=>x[0]===S.fcEsito)[1].toLowerCase());
  return v.join(", ");
}
function riepilogoFiltri(){
  const terr=S.circ ? TUTTI.filter(i=>C[i].ci===S.circ) : TUTTI, n=ambitoCom().length;
  const dove=S.circ?"nella circoscrizione di "+S.circ:"in regione";
  const ricerca=S.fcCerca?` La ricerca «${esc(S.fcCerca)}» agisce sulle tabelle.`:"";
  d3.select("#fcRiepilogo").html(n===terr.length
    ? `Tutti i <b>${N(n)}</b> comuni ${dove}: ${esc(descriviFiltri())}.${ricerca}`
    : n===0 ? `<b>Nessun comune</b> su ${N(terr.length)} ${dove} corrisponde ai filtri: ${esc(descriviFiltri())}. Cambia una scelta o azzera i filtri.`
    : `<b>${N(n)}</b> ${n===1?"comune":"comuni"} su ${N(terr.length)} ${dove}: ${esc(descriviFiltri())}. Gli altri sono in grigio sulla mappa.${ricerca}`);
  d3.select("#fcAzzera").classed("pieno",filtriAttivi());
}
function applicaFiltriCom(){
  if (S.com!=null && EL(S.com)) S.consO=EL(S.com).o;
  if (S.fcPart!=="") S.partito=+S.fcPart;
  S.cpMostra=50;
  disegnaMappa(); disegnaComunali();
}
(function(){
  const sel=d3.select("#fcEl");
  sel.selectAll("option").data([["1","Ultima di ogni comune"],["2","Penultima di ogni comune"],["3","Terzultima di ogni comune"],...FC_ANNI.map(y=>[String(y),"Anno "+y+": solo i comuni al voto quell'anno"])]).join("option").attr("value",d=>d[0]).text(d=>d[1]);
  sel.on("change",function(){ S.fcEl=this.value; applicaFiltriCom(); });
  d3.select("#fcPart").selectAll("option").data([["","Tutte le liste"],...PART.map((p,k)=>[String(k),p.n])]).join("option").attr("value",d=>d[0]).text(d=>d[1]);
  d3.select("#fcPart").on("change",function(){ S.fcPart=this.value; applicaFiltriCom(); });
  d3.select("#fcDim").selectAll("option").data(FC_DIM).join("option").attr("value",d=>d[0]).text(d=>d[1]);
  d3.select("#fcDim").on("change",function(){ S.fcDim=this.value; applicaFiltriCom(); });
  d3.select("#fcEsito").selectAll("option").data(FC_ESITO).join("option").attr("value",d=>d[0]).text(d=>d[1]);
  d3.select("#fcEsito").on("change",function(){ S.fcEsito=this.value; applicaFiltriCom(); });
  d3.select("#fcCerca").on("input",function(){ S.fcCerca=normTesto(this.value.trim()); S.cpMostra=50; disegnaClassificaCom(); disegnaTabComuniCom(); riepilogoFiltri(); });
  d3.select("#fcAzzera").on("click",()=>{ S.fcEl="1"; S.fcPart=""; S.fcDim=""; S.fcEsito=""; S.fcCerca="";
    d3.select("#fcEl").property("value","1"); d3.select("#fcPart").property("value",""); d3.select("#fcDim").property("value",""); d3.select("#fcEsito").property("value",""); d3.select("#fcCerca").property("value","");
    applicaFiltriCom(); });
})();
