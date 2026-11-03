// Painel de estoque por fornecedor. Os dados chegam em D (gerado por estoque/render.py).
// MODO = "painel" (interativo, celular e computador) ou "relatorio" (versão estática para PDF).
const D = __DADOS__;
const MODO = "__MODO__";
const P = D.p;

const brl0 = new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0});
const pct1 = v => (v*100).toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';
const mi = v => 'R$ '+(v/1e6).toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})+' mi';
const mil = v => Math.abs(v)>=1e6 ? mi(v) : 'R$ '+brl0.format(Math.round(v/1000))+' mil';
const esc = s => String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const sgn = (v,f) => (v>0?'+':v<0?'−':'')+f(Math.abs(v));
const gm = v => v!=null ? v.toFixed(2).replace('.',',') : '–';
const $ = id => document.getElementById(id);
const TEM_COMP = !!D.comp;

const R = D.rows.map(r=>({...r,
  mp: r.v>0? r.m/r.v : null, dde: r.v>0? r.e/r.v*30 : null, g: r.e>0? r.m*12/r.e : null,
  novo: TEM_COMP && r.ec==null,
  de: !TEM_COMP ? 0 : (r.ec==null? r.e : r.e-r.ec),
  ddec: r.vc>0? r.ec/r.vc*30 : null}));
const V = R.reduce((a,r)=>a+r.v,0), M = R.reduce((a,r)=>a+r.m,0), E = R.reduce((a,r)=>a+r.e,0);
const act = R.filter(r=>r.v>0);
const excess = t => act.map(r=>({...r, x: Math.max(0, r.e - r.v/30*t)}));
const exA = excess(P.alvo).reduce((a,r)=>a+r.x,0);
const TC = D.tc;
const narrow = () => window.matchMedia('(max-width: 640px)').matches;
function ddePill(d){const c=d>90?'t-crit':d>60?'t-warn':'t-good';return `<span class="pill ${c}">${Math.round(d)} d</span>`}

// ---------------------------------------------------------------- indicadores do topo
(function(){
  const dd = (txt,good) => TEM_COMP ? `<em class="${good?'t-good':'t-crit'}">${txt}</em>` : '';
  const fmt2 = v => v.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});
  const c = TC || {};
  $('kpis').innerHTML = [
    [mi(V),'Venda no mês', dd(sgn((V/c.v-1),pct1)+' vs '+D.comp, V>=c.v)],
    [pct1(M/V),'Margem bruta ('+mi(M)+')', dd(sgn((M/V-c.m/c.v)*100,v=>v.toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})+' p.p. vs '+D.comp), M/V>=c.m/c.v)],
    [mi(E),'Valor em estoque', dd(sgn(E-c.e,mil)+' vs '+D.comp, E<=c.e)],
    [Math.round(E/V*30)+' dias','Cobertura (~'+Math.round(E/(V-M)*30)+' a custo)', dd('era '+Math.round(c.e/c.v*30)+' dias', E/V<=c.e/c.v)],
    [fmt2(M*12/E),'GMROI anualizado', dd('era '+fmt2(c.m*12/c.e), M/E>=c.m/c.e)],
    [mi(exA),'Acima de '+P.alvo+' dias de cobertura', dd('era '+mi(c.x), exA<=c.x), 1]
  ].map(([b,s,d,a])=>`<div class="kpi${a?' alert':''}"><b>${b}</b><span>${s}</span>${d}</div>`).join('');
})();

// ---------------------------------------------------------------- evolução entre as fotos
(function(){
  const el=$('trend'); if(!el || D.fotos.length<2) return;
  const Pf=D.fotos, N=Pf.length, lab=Pf.map(f=>f.rot);
  const iComp = TEM_COMP ? lab.indexOf(D.comp) : N-2;
  const series=[
    ['Valor em estoque', Pf.map(t=>t.e), v=>mi(v), false],
    ['Cobertura (dias)', Pf.map(t=>t.e/t.v*30), v=>Math.round(v)+' dias', false],
    ['Acima de '+P.alvo+' dias', Pf.map(t=>t.x), v=>mi(v), false],
    ['Margem bruta', Pf.map(t=>t.m/t.v), v=>pct1(v), true]];
  el.innerHTML=series.map(([nm,vals,fmt,up])=>{
    const W=300,H=132,L=14,Rr=14,T=30,B=38, mn=Math.min(...vals), mx=Math.max(...vals), pad=(mx-mn)*0.25||1;
    const sx=i=>L+(W-L-Rr)*i/(N-1), sy=v=>T+(H-T-B)*(1-(v-mn+pad)/(mx-mn+2*pad));
    const last=vals[N-1], prev=vals[Math.max(iComp,0)], good=up? last>=prev : last<=prev;
    const showVal = i => N<=6 || i===0 || i===N-1 || i===iComp;
    let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${nm}: ${vals.map(fmt).join(', ')}">`;
    s+=`<polyline points="${vals.map((v,i)=>`${sx(i)},${sy(v)}`).join(' ')}" fill="none" stroke="var(--accent)" stroke-width="2"/>`;
    vals.forEach((v,i)=>{const end=i===N-1, anc=i===0?'start':end?'end':'middle';
      s+=`<circle cx="${sx(i)}" cy="${sy(v)}" r="${end?5:3.5}" fill="${end?'var(--accent)':'var(--panel)'}" stroke="var(--accent)" stroke-width="2"/>`;
      const below = i===0 ? v<vals[1] : end ? v<vals[N-2] : (v<vals[i-1] && v<vals[i+1]);
      if(showVal(i)) s+=`<text class="ax" x="${sx(i)}" y="${below? sy(v)+17 : sy(v)-10}" text-anchor="${anc}">${fmt(v)}</text>`;
      if(N<=8 || i%2===0 || end) s+=`<text class="ax" x="${sx(i)}" y="${H-6}" text-anchor="${anc}">${lab[i]}</text>`});
    s+=`</svg>`;
    const pill = TEM_COMP ? `<span class="pill ${good?'t-good':'t-crit'}">${good?'melhorou':'piorou'}</span>` : '';
    return `<div class="panel tcard"><div class="thd"><h3>${nm}</h3>${pill}</div>${s}</div>`}).join('');
})();

// ---------------------------------------------------------------- CD por m²
(function(){
  const el=$('m2'); if(!el) return;
  const A=P.area, f=v=>'R$ '+brl0.format(Math.round(v));
  el.innerHTML=[
    [f(V/A),'Venda por m² no mês'],[f(M/A),'Margem bruta por m² no mês'],
    [f(E/A),'Estoque por m²'+(TEM_COMP?' (era '+f(TC.e/A)+' em '+D.comp+')':'')],[f(exA/A),'Excesso acima de '+P.alvo+' dias por m²',1]
  ].map(([b,t,a])=>`<div class="kpi${a?' alert':''}"><b>${b}</b><span>${t}</span></div>`).join('');
})();

// ---------------------------------------------------------------- dicas (toque no celular, mouse no computador)
const tip = $('tip');
function showTip(e,html){if(!tip)return;tip.innerHTML=html;tip.hidden=false;const x=Math.max(8,Math.min(e.clientX+14, innerWidth-tip.offsetWidth-8));let y=e.clientY+14;if(y+tip.offsetHeight>innerHeight-8) y=e.clientY-tip.offsetHeight-14;tip.style.left=x+'px';tip.style.top=Math.max(8,y)+'px'}
function hideTip(){if(tip) tip.hidden=true}
function bindTips(root){ if(MODO!=='painel') return; root.querySelectorAll('[data-tip]').forEach(el=>{
  el.addEventListener('mousemove',e=>{if(e.pointerType!=='touch') showTip(e,el.dataset.tip)});
  el.addEventListener('mouseleave',hideTip);
  el.addEventListener('click',e=>{e.stopPropagation();showTip(e,el.dataset.tip)});
})}
document.addEventListener('click',hideTip); window.addEventListener('scroll',hideTip,{passive:true});
const tipFor = r => esc(`<b>${r.f}</b><br>Venda ${mil(r.v)} · Margem ${r.mp!=null?pct1(r.mp):'–'}<br>Estoque ${mil(r.e)} · ${r.dde!=null?Math.round(r.dde)+' dias':'sem venda'}<br>GMROI ${gm(r.g)} · ${r.s} SKUs`);

// ---------------------------------------------------------------- o que mudou (barras divergentes)
(function(){
  const el=$('c-delta'); if(!el || !TEM_COMP) return;
  const srt=[...R].sort((a,b)=>a.de-b.de), dn=srt.slice(0,8).filter(r=>r.de<0), up=srt.slice(-8).reverse().filter(r=>r.de>0);
  const mxN=Math.abs(dn[0]?.de||1), mxP=up[0]?.de||1;
  const cob=r=> (r.novo?'novo':(r.ddec!=null?Math.round(r.ddec):'–'))+' → '+(r.dde!=null?Math.round(r.dde):'–')+' dias';
  const row=r=>{const neg=r.de<0;
    return `<div class="bar-row" data-tip="${tipFor(r)}<br>Variação ${sgn(r.de,mil)}${r.novo?' (fornecedor novo)':''}">
      <div class="nm">${esc(r.n)}</div>
      <div class="tr"><div class="dv" style="grid-template-columns:${mxN}fr ${mxP}fr">
        <div class="neg">${neg?`<span class="bar" style="width:${Math.abs(r.de)/mxN*100}%;background:var(--accent)"></span>`:''}</div>
        <div class="pos">${neg?'':`<span class="bar" style="width:${r.de/mxP*100}%;background:var(--s2)"></span>`}</div>
      </div><div class="val"><b class="${neg?'t-good':'t-crit'}">${sgn(r.de,mil)}</b> · cobertura ${cob(r)}</div></div></div>`};
  el.innerHTML=`<div class="bars"><div class="grp">Maiores reduções</div>${dn.map(row).join('')}<div class="grp">Maiores aumentos</div>${up.map(row).join('')}</div>`;
  bindTips(el);
})();

// ---------------------------------------------------------------- peso na venda × peso no estoque
(function(){
  const el=$('c-share'); if(!el) return;
  const top=[...R].sort((a,b)=>b.v-a.v).slice(0,15), mx=Math.max(...top.map(r=>Math.max(r.v/V,r.e/E)));
  el.innerHTML=`<div class="bars">${top.map(r=>{const pv=r.v/V,pe=r.e/E;
    return `<div class="bar-row" data-tip="${tipFor(r)}"><div class="nm">${esc(r.n)}</div><div class="tr">
      <div class="bar-line"><span class="bar" style="width:${pv/mx*60}%;background:var(--accent)"></span><span class="val">${pct1(pv)} venda</span></div>
      <div class="bar-line"><span class="bar" style="width:${pe/mx*60}%;background:var(--s2)"></span><span class="val${pe>pv*1.15?' t-crit':''}">${pct1(pe)} estoque</span></div>
    </div></div>`}).join('')}</div>`;
  bindTips(el);
})();

const avgM = M/V;
const quad = r => r.dde>P.alvo && r.mp<avgM ? 'crit' : r.dde>P.alvo ? 'warn' : r.mp<avgM ? 'serious' : 'good';

if (MODO === 'painel') {
  // -------------------------------------------------------------- mapa cobertura × margem
  let lastMapW=0;
  function drawMap(){
    const el=$('c-map'), cw=el.clientWidth; if(!cw||cw===lastMapW) return; lastMapW=cw;
    const nr=cw<600, W=Math.max(cw,300), H=nr?Math.round(W*1.0):420, L=nr?38:52, Rr=nr?10:20, T=16, B=40;
    const pts=act.filter(r=>r.v>=P.vmin_mapa);
    const mxX=Math.max(120, Math.min(360, Math.ceil(Math.max(...pts.map(r=>Math.min(r.dde,360)))/30)*30));
    const mnY=Math.min(-0.03, Math.floor(Math.min(...pts.map(r=>r.mp))*20)/20), mxY=Math.max(0.26, Math.ceil(Math.max(...pts.map(r=>r.mp))*20)/20+0.01);
    const sx=v=>L+(W-L-Rr)*Math.min(v,mxX)/mxX, sy=v=>T+(H-T-B)*(mxY-v)/(mxY-mnY);
    const maxE=Math.max(...pts.map(r=>r.e)), rad=e=>(nr?3:4)+(nr?18:30)*Math.sqrt(e/maxE);
    const cor={crit:'var(--crit)',warn:'var(--warn)',serious:'var(--serious)',good:'var(--good)'};
    let s=`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Dispersão de cobertura em dias versus margem percentual por fornecedor">`;
    for(let x=0;x<=mxX;x+=(nr?60:30)){s+=`<line class="grid" x1="${sx(x)}" x2="${sx(x)}" y1="${T}" y2="${H-B}"/><text class="ax" x="${sx(x)}" y="${H-B+16}" text-anchor="middle">${x}</text>`}
    for(let y=Math.ceil(mnY*20)/20;y<=mxY+1e-9;y+=0.05){s+=`<line class="grid" x1="${L}" x2="${W-Rr}" y1="${sy(y)}" y2="${sy(y)}"/><text class="ax" x="${L-6}" y="${sy(y)+4}" text-anchor="end">${Math.round(y*100)}%</text>`}
    s+=`<text class="ax" x="${(L+W-Rr)/2}" y="${H-6}" text-anchor="middle">cobertura (dias)</text>`;
    s+=`<line x1="${sx(P.alvo)}" x2="${sx(P.alvo)}" y1="${T}" y2="${H-B}" stroke="var(--ink-3)" stroke-dasharray="4 4"/>`;
    s+=`<line x1="${L}" x2="${W-Rr}" y1="${sy(avgM)}" y2="${sy(avgM)}" stroke="var(--ink-3)" stroke-dasharray="4 4"/>`;
    s+=`<text class="ax" x="${sx(P.alvo)+4}" y="${T+10}">${P.alvo} dias</text><text class="ax" x="${W-Rr-4}" y="${sy(avgM)-5}" text-anchor="end">média ${pct1(avgM)}</text>`;
    [...pts].sort((a,b)=>b.e-a.e).forEach(r=>{s+=`<circle data-tip="${tipFor(r)}" cx="${sx(r.dde)}" cy="${sy(r.mp)}" r="${rad(r.e)}" fill="${cor[quad(r)]}" fill-opacity=".55" stroke="var(--panel)" stroke-width="1.5"/>`});
    const rot = nr ? D.rotulos_mapa.slice(0,6) : D.rotulos_mapa;
    // rótulos: tenta à direita, à esquerda, acima e abaixo; descarta o que não couber sem sobrepor
    const ocupado=[], cabe=(x0,y0,x1,y1)=>x0>=2 && x1<=W-2 && y0>=T && y1<=H-B && !ocupado.some(o=>x0<o[2]&&x1>o[0]&&y0<o[3]&&y1>o[1]);
    pts.filter(r=>rot.includes(r.f)).sort((a,b)=>b.e-a.e).forEach(r=>{
      const cx=sx(r.dde), cy=sy(r.mp), rr=rad(r.e), w=r.n.length*6.4+4, h=13;
      const opc=[[cx+rr+4,cy+4,'start'],[cx-rr-4,cy+4,'end'],[cx,cy-rr-5,'middle'],[cx,cy+rr+13,'middle'],[cx+rr+4,cy+17,'start'],[cx+rr+4,cy-9,'start']];
      for(const [x,y,a] of opc){
        const x0 = a==='start'?x : a==='end'? x-w : x-w/2, y0=y-10;
        if(cabe(x0,y0,x0+w,y0+h)){ ocupado.push([x0,y0,x0+w,y0+h]); s+=`<text class="lb" pointer-events="none" x="${x}" y="${y}" text-anchor="${a}">${esc(r.n)}</text>`; break; }
      }});
    s+=`</svg>`;
    el.innerHTML=s; bindTips(el);
  }
  drawMap();
  let rz; window.addEventListener('resize',()=>{clearTimeout(rz);rz=setTimeout(()=>{drawMap();table()},150)});

  // -------------------------------------------------------------- simulador
  const tgt=$('tgt'), cc=$('cc');
  tgt.value=P.alvo; cc.value=(P.cc*100).toFixed(1);
  function sim(){
    const t=+tgt.value, c=+cc.value/100;
    $('tgt-o').textContent=t+' dias';
    $('cc-o').textContent=(+cc.value).toLocaleString('pt-BR',{minimumFractionDigits:1})+'% a.m.';
    const ex=excess(t).sort((a,b)=>b.x-a.x), tot=ex.reduce((a,r)=>a+r.x,0), n=ex.filter(r=>r.x>0).length;
    $('simout').innerHTML=[
      ['Capital acima do alvo',mi(tot)],['Custo mensal de carregar',mil(tot*c)],['Equivale a',pct1(tot*c/M)+' da margem'],['Fornecedores acima do alvo',n+' de '+act.length]
    ].map(([a,b])=>`<div><span class="small">${a}</span><b>${b}</b></div>`).join('');
    const top=ex.slice(0,12), mx=Math.max(top[0].x,1);
    const el=$('c-exc');
    el.innerHTML=`<div class="bars">${top.map(r=>`<div class="bar-row" data-tip="${tipFor(r)}<br>Excesso ${mil(r.x)}"><div class="nm">${esc(r.n)}</div><div class="tr"><div class="bar-line"><span class="bar" style="width:${r.x/mx*72}%;background:var(--accent)"></span><span class="val">${mil(r.x)}</span></div></div></div>`).join('')}</div>`;
    bindTips(el);
  }
  tgt.addEventListener('input',sim); cc.addEventListener('input',sim); sim();

  // -------------------------------------------------------------- tabela (cartões no celular)
  const cols=[['f','Fornecedor'],['abc','Curva'],['v','Venda mês'],['mp','Margem %'],['s','SKUs'],['e','Estoque']]
    .concat(TEM_COMP?[['de','Δ estoque'],['ddec','Cob. '+D.comp]]:[])
    .concat([['dde','Cobertura'],['g','GMROI'],['xa','Exc. '+P.alvo+'d']]);
  const exMap=Object.fromEntries(excess(P.alvo).map(r=>[r.f,r.x]));
  const T=act.map(r=>({...r,xa:exMap[r.f]||0}));
  let sortK='v', sortD=-1, filt='all', showAll=false;
  const ord=$('ord');
  if(!TEM_COMP){ ord.querySelector('option[value="de"]')?.remove(); document.querySelector('.chip[data-f="up"]')?.remove(); }
  $('th').innerHTML=cols.map(([k,l])=>`<th><button data-k="${k}">${l}</button></th>`).join('');
  function setSort(k){ if(sortK===k) sortD*=-1; else {sortK=k; sortD=k==='f'||k==='abc'?1:-1} ord.value=sortK; table() }
  document.querySelectorAll('#th button').forEach(b=>b.addEventListener('click',()=>setSort(b.dataset.k)));
  ord.addEventListener('change',()=>{sortK=ord.value; sortD=sortK==='f'?1:-1; table()});
  document.querySelectorAll('.chip[data-f]').forEach(b=>b.addEventListener('click',()=>{filt=b.dataset.f;showAll=false;document.querySelectorAll('.chip[data-f]').forEach(c=>c.setAttribute('aria-pressed',c===b));table()}));
  $('q').addEventListener('input',()=>{showAll=false;table()});
  $('more').addEventListener('click',()=>{showAll=true;table()});
  window.table = table;
  function table(){
    const q=$('q').value.trim().toUpperCase();
    let rows=T.filter(r=>(!q||r.f.includes(q)||r.n.toUpperCase().includes(q)) && (filt==='all'||r.abc===filt||(filt==='exc'&&r.dde>90)||(filt==='low'&&r.mp<P.margem_baixa)||(filt==='up'&&r.de>0)));
    rows.sort((a,b)=>{const x=a[sortK],y=b[sortK];return (typeof x==='string'?x.localeCompare(y):(x??-1e9)-(y??-1e9))*sortD});
    document.querySelectorAll('#th button').forEach(b=>{const l=cols.find(c=>c[0]===b.dataset.k)[1]; if(b.dataset.k===sortK){b.dataset.active='';b.textContent=l+(sortD>0?' ↑':' ↓')}else{delete b.dataset.active;b.textContent=l}});
    const lim = narrow() && !showAll ? 15 : rows.length, shown=rows.slice(0,lim);
    const cell = (k,r) => ({
      f:`<td>${esc(r.f)}</td>`, abc:`<td data-label="Curva">${r.abc}</td>`, v:`<td data-label="Venda mês">${brl0.format(r.v)}</td>`,
      mp:`<td data-label="Margem %"${r.mp<P.margem_baixa?' class="t-crit"':''}>${pct1(r.mp)}</td>`, s:`<td data-label="SKUs" class="sku">${r.s}</td>`,
      e:`<td data-label="Estoque">${brl0.format(r.e)}</td>`,
      de:`<td data-label="Δ estoque" class="${r.de>0?'t-crit':r.de<0?'t-good':''}">${r.novo?'novo':sgn(r.de,v=>brl0.format(v))}</td>`,
      ddec:`<td data-label="Cob. ${D.comp}">${r.ddec!=null?Math.round(r.ddec)+' d':'–'}</td>`,
      dde:`<td data-label="Cobertura">${ddePill(r.dde)}</td>`, g:`<td data-label="GMROI">${gm(r.g)}</td>`,
      xa:`<td data-label="Exc. ${P.alvo}d">${r.xa>0?brl0.format(r.xa):'–'}</td>`})[k];
    $('tb').innerHTML=shown.map(r=>`<tr>${cols.map(([k])=>cell(k,r)).join('')}</tr>`).join('');
    const more=$('more'); more.hidden = shown.length>=rows.length; more.textContent='Mostrar todos os '+rows.length+' fornecedores';
    $('tcount').textContent=rows.length+' fornecedores · estoque '+mi(rows.reduce((a,r)=>a+r.e,0))+(TEM_COMP?' · variação '+sgn(rows.reduce((a,r)=>a+r.de,0),mil):'')+' · excesso a '+P.alvo+' dias '+mi(rows.reduce((a,r)=>a+r.xa,0));
  }
  table();
} else {
  // -------------------------------------------------------------- relatório: matriz no lugar do mapa
  const pts=act.filter(r=>r.v>=P.vmin_mapa);
  const Q=[['crit','Reduzir primeiro',`Cobertura acima de ${P.alvo} dias e margem abaixo da média`],
           ['warn','Rever cobertura',`Cobertura acima de ${P.alvo} dias, margem na média ou acima`],
           ['serious','Rever preço ou mix',`Até ${P.alvo} dias, margem abaixo da média`],
           ['good','Saudável',`Até ${P.alvo} dias, margem na média ou acima`]];
  $('matrix').innerHTML=Q.map(([c,t,d])=>{
    const l=pts.filter(r=>quad(r)===c).sort((a,b)=>b.e-a.e), est=l.reduce((a,r)=>a+r.e,0), top=l.slice(0,8);
    return `<div class="quad q-${c}"><div class="qh"><span class="pill t-${c}">${t}</span><span class="qd">${d}</span>
      <span class="qt">${l.length} fornecedores · ${mi(est)} em estoque (${pct1(est/E)})</span></div>
      <table class="qtab"><thead><tr><th>Fornecedor</th><th>Cobertura</th><th>Margem</th><th>Estoque</th></tr></thead><tbody>
      ${top.map(r=>`<tr><td>${esc(r.n)}</td><td>${Math.round(r.dde)} d</td><td>${pct1(r.mp)}</td><td>${mil(r.e)}</td></tr>`).join('')}
      </tbody></table>${l.length>8?`<p class="small muted">+ ${l.length-8} outros</p>`:''}</div>`}).join('');

  // cenários de cobertura-alvo no lugar do simulador
  const alvos=[...new Set([30,P.alvo,60,90])].sort((a,b)=>a-b);
  $('captab').innerHTML=`<table class="ctab"><thead><tr><th>Cobertura-alvo</th><th>Capital acima do alvo</th><th>Custo mensal de carregar</th><th>% da margem</th><th>Fornecedores acima</th></tr></thead><tbody>${
    alvos.map(t=>{const ex=excess(t), tot=ex.reduce((a,r)=>a+r.x,0), n=ex.filter(r=>r.x>0).length;
      return `<tr${t===P.alvo?' class="hl"':''}><td>${t} dias</td><td>${mi(tot)}</td><td>${mil(tot*P.cc)}</td><td>${pct1(tot*P.cc/M)}</td><td>${n} de ${act.length}</td></tr>`}).join('')
  }</tbody></table>`;
  const ex=excess(P.alvo).sort((a,b)=>b.x-a.x), top=ex.slice(0,12), mx=top[0].x;
  $('c-exc').innerHTML=`<div class="bars">${top.map(r=>`<div class="bar-row"><div class="nm">${esc(r.n)}</div><div class="tr"><div class="bar-line"><span class="bar" style="width:${r.x/mx*72}%;background:var(--accent)"></span><span class="val">${mil(r.x)} · ${Math.round(r.dde)} dias</span></div></div></div>`).join('')}</div>`;

  // 30 maiores no lugar da tabela completa
  const exMap=Object.fromEntries(excess(P.alvo).map(r=>[r.f,r.x]));
  const t30=[...act].sort((a,b)=>b.v-a.v).slice(0,30);
  const sv=t30.reduce((a,r)=>a+r.v,0), se=t30.reduce((a,r)=>a+r.e,0);
  $('topnote').textContent=`Os 30 maiores somam ${pct1(sv/V)} da venda e ${pct1(se/E)} do estoque. A lista completa dos ${act.length} fornecedores com venda está no painel HTML.`;
  $('ptab-head').innerHTML=`<tr><th>Fornecedor</th><th>Curva</th><th>Venda mês</th><th>Margem</th><th>Estoque</th>${TEM_COMP?`<th>Δ vs ${D.comp}</th><th>Cob. ${D.comp}</th>`:''}<th>Cobertura</th><th>Exc. ${P.alvo}d</th></tr>`;
  $('tb').innerHTML=t30.map((r,i)=>`<tr><td>${i+1}. ${esc(r.n)}</td><td>${r.abc}</td><td>${mil(r.v)}</td><td${r.mp<P.margem_baixa?' class="t-crit"':''}>${pct1(r.mp)}</td><td>${mil(r.e)}</td>
    ${TEM_COMP?`<td class="${r.de>0?'t-crit':r.de<0?'t-good':''}">${r.novo?'novo':sgn(r.de,mil)}</td><td>${r.ddec!=null?Math.round(r.ddec):'–'}</td>`:''}<td>${ddePill(r.dde)}</td><td>${exMap[r.f]>0?mil(exMap[r.f]):'–'}</td></tr>`).join('');
}
