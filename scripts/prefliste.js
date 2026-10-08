// ---------- preferenze dei candidati di una lista, comune per comune (sezione aggiunta per l'Atlante)
let PL_COL=[], PL_RIGHE=[];
function disegnaPrefListe(){
  const box=d3.select("#sez-prefliste"); if (box.empty()) return;
  if (!S.plCirc || !CIRC.includes(S.plCirc)) S.plCirc = S.circ || (S.com!=null ? C[S.com].ci : CIRC[0]);
  const circ=S.plCirc;
  const sc=d3.select("#plCirc"); sc.selectAll("option").data(CIRC).join("option").attr("value",d=>d).text(d=>"Circoscrizione di "+d); sc.property("value",circ);
  const listeCirc=L.map((l,i)=>i).filter(i=>K.some(k=>k.l===i && k.ci===circ)).sort((a,b)=>L[b].v-L[a].v);
  if (S.plLista==null || !listeCirc.includes(S.plLista)) S.plLista = listeCirc.includes(S.lista) ? S.lista : listeCirc[0];
  const sl=d3.select("#plLista"); sl.selectAll("option").data(listeCirc).join("option").attr("value",d=>d).text(d=>L[d].s.toLowerCase()===titolo(L[d].n).toLowerCase()?L[d].s:L[d].s+" · "+titolo(L[d].n)); sl.property("value",S.plLista);
  const l=S.plLista, cands=K.filter(k=>k.l===l && k.ci===circ).sort((a,b)=>b.v-a.v);
  const comuni=TUTTI.filter(i=>C[i].ci===circ && !assente(i)).sort((a,b)=>C[a].n.localeCompare(C[b].n,"it"));
  const t=d3.select("#tabPrefListe");
  const intesta=`<th scope="col">Comune</th><th scope="col" class="num">Voti alla lista</th>${cands.map(k=>`<th scope="col" class="num">${esc(titolo(k.n))}${k.e?' <span class="eletto">Eletto</span>':""}</th>`).join("")}<th scope="col" class="num">Totale preferenze</th>`;
  if (!D.prefComuni){
    const totL=d3.sum(comuni,i=>C[i].L[l]||0), totP=d3.sum(cands,k=>k.v||0);
    t.html(`<thead><tr>${intesta}</tr></thead><tbody><tr class="totale"><td class="nome">Circoscrizione di ${esc(circ)}</td><td class="cel">${N(totL)}</td>${cands.map(k=>`<td class="cel">${N(k.v)}</td>`).join("")}<td class="cel">${N(totP)}</td></tr></tbody>`);
    d3.select("#plSotto").html(`<b>${esc(titolo(L[l].n))}</b>, circoscrizione di ${esc(circ)}: ${cands.length} candidati. Per il ${D.anno} la fonte pubblica le preferenze solo per circoscrizione, non per comune.`);
    d3.select("#plNota").text(""); PL_COL=[]; PL_RIGHE=[]; return;
  }
  const righe=comuni.map(i=>({i, n:C[i].n, vl:C[i].L[l], p:cands.map(k=>k.m.get(i)||0)}));
  righe.forEach(r=>{ r.tot=d3.sum(r.p); });
  const totC=cands.map((k,j)=>d3.sum(righe,r=>r.p[j])), totL=d3.sum(righe,r=>r.vl||0), totP=d3.sum(totC);
  const mx=d3.max(righe,r=>d3.max(r.p))||1, col=L[l].c;
  const cella=v=>{ if(!v) return `<td class="cel"><span class="avv">0</span></td>`; const al=Math.round(8+47*Math.sqrt(v/mx)); return `<td class="cel" style="background:color-mix(in srgb,${col} ${al}%,transparent)">${N(v)}</td>`; };
  t.html(`<thead><tr>${intesta}</tr></thead><tbody>${righe.map(r=>`<tr class="${r.i===S.com?"scelta":""}"><td class="nome">${esc(r.n)}</td><td class="cel">${N(r.vl)}</td>${r.p.map(cella).join("")}<td class="cel" style="font-weight:800">${N(r.tot)}</td></tr>`).join("")}
    <tr class="totale"><td class="nome">Totale circoscrizione</td><td class="cel">${N(totL)}</td>${totC.map(v=>`<td class="cel">${N(v)}</td>`).join("")}<td class="cel">${N(totP)}</td></tr></tbody>`);
  d3.select("#plSotto").html(`<b>${esc(titolo(L[l].n))}</b> (${esc(L[l].s)}), circoscrizione di ${esc(circ)}: ${cands.length} candidati e ${comuni.length} comuni. Colonne in ordine di preferenze totali; il colore è più intenso dove il candidato ha preso più voti.`);
  d3.select("#plNota").html(`«Voti alla lista» sono i voti di lista nel comune; le preferenze sono voti espressi ai singoli candidati e possono essere più di una per scheda, quindi non si sommano ai voti di lista. Comuni in ordine alfabetico; la riga finale somma tutta la circoscrizione. Fonte: ${esc(D.anno===2018?"archivio elettorale storico della Regione, pagine comunali delle preferenze":"portale elezioni della Regione, flussi ufficiali")}.`);
  PL_COL=[{t:"Comune",f:r=>r.n},{t:"Voti alla lista",f:r=>r.vl==null?"":r.vl},...cands.map((k,j)=>({t:titolo(k.n)+(k.e?" (eletto)":""),f:r=>r.p[j]})),{t:"Totale preferenze",f:r=>r.tot}];
  PL_RIGHE=[...righe,{n:"Totale circoscrizione",vl:totL,p:totC,tot:totP}];
}
d3.select("#plCirc").on("change",function(){ S.plCirc=this.value; S.plLista=null; disegnaPrefListe(); });
d3.select("#plLista").on("change",function(){ S.plLista=+this.value; disegnaPrefListe(); });
d3.select("#plCsv").on("click",()=>{ if(PL_COL.length) scaricaCsv(`preferenze-${(L[S.plLista]||{s:"lista"}).s.toLowerCase().replace(/[^a-z0-9]+/g,"-")}-${S.plCirc.toLowerCase()}-${D.anno}.csv`,PL_COL,PL_RIGHE); });
