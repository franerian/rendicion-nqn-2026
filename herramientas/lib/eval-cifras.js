(()=>{
 const bad=[];
 const out={vw:innerWidth,vh:innerHeight,docOverflow:document.documentElement.scrollWidth>innerWidth};
 const vis=e=>{
   const r=e.getBoundingClientRect();
   if(r.width<2||r.height<2) return false;
   for(let x=e;x&&x!==document.body;x=x.parentElement){const cs=getComputedStyle(x);if(cs.display==='none'||cs.visibility==='hidden') return false;}
   return true;
 };
 // 1) valores de #20: ningún hijo de .fv se sale por la izquierda de su columna
 document.querySelectorAll('.fv').forEach(fv=>{
   if(!vis(fv)) return;
   const fb=fv.getBoundingClientRect();
   [...fv.children].forEach(c=>{
     const r=c.getBoundingClientRect();
     if(r.left<fb.left-0.6) bad.push('fv: '+c.textContent.replace(/ /g,'_').trim().slice(0,18)+' sale '+Math.round(fb.left-r.left)+'px por la izquierda');
   });
 });
 // 2) cifras sin corte de línea: su contenido no puede ser más ancho que su caja ni que la tarjeta que las contiene
 const sel='.num,.ps-d b,.nv-d b,.nv-kpi li,.zv b';
 document.querySelectorAll(sel).forEach(e=>{
   if(!vis(e)) return;
   const cs=getComputedStyle(e);
   const rg=document.createRange();rg.selectNodeContents(e);
   const tr=rg.getBoundingClientRect();
   const host=e.closest('.card,.tile,.cl-tile,.nv-pair,.nv-head,.fin-col');
   if(host){
     const hr=host.getBoundingClientRect();
     const hcs=getComputedStyle(host);
     const hz=(host.offsetWidth&&hr.width/host.offsetWidth)||1; /* v125: zoom efectivo (la columna de #14 usa zoom < 1): el relleno se mide en px de pantalla */
     const padR=(parseFloat(hcs.paddingRight)||0)*hz, padL=(parseFloat(hcs.paddingLeft)||0)*hz;
     if(tr.right>hr.right-padR+1.5 && !/normal|pre-wrap|break/.test(cs.whiteSpace)) bad.push('num: «'+e.textContent.replace(/ /g,'_').trim().slice(0,22)+'» pasa '+Math.round(tr.right-(hr.right-padR))+'px del borde útil de '+host.className.slice(0,28));
     if(tr.left<hr.left+padL-1.5) bad.push('num: «'+e.textContent.replace(/ /g,'_').trim().slice(0,22)+'» pasa '+Math.round(hr.left+padL-tr.left)+'px por la izquierda de '+host.className.slice(0,28));
   }
   if(tr.right>innerWidth+1||tr.left<-1) bad.push('num: «'+e.textContent.trim().slice(0,22)+'» fuera de la ventana');
 });
 // 3) renglones: una cifra que debería ir en uno solo y ocupa dos (alto > 1,6 líneas de su tamaño)
 document.querySelectorAll('.num,.fin-sum .num,.ps-d b,.nv-d b,.fv b').forEach(e=>{
   if(!vis(e)) return;
   const fs=parseFloat(getComputedStyle(e).fontSize);
   const h=e.getBoundingClientRect().height;
   const z=parseFloat(getComputedStyle(e).zoom)||1;
   if(h/z>fs*1.75 && !e.classList.contains('full') && !e.classList.contains('s')) bad.push('num: «'+e.textContent.replace(/ /g,'_').trim().slice(0,22)+'» en dos renglones (alto '+Math.round(h)+' con letra de '+Math.round(fs)+')');
 });
 // 4) medidas útiles para comparar
 const e20=document.querySelector('.fin-sum .num');
 if(e20) out.sum20=Math.round(parseFloat(getComputedStyle(e20).fontSize)*10)/10;
 const mon=document.querySelector('.cl-tile.money .num');
 if(mon) out.money=Math.round(parseFloat(getComputedStyle(mon).fontSize)*10)/10;
 const tt=document.querySelector('.pasos .tile.t');
 if(tt){const r=tt.getBoundingClientRect();out.pasosTile=[Math.round(r.width),Math.round(r.height)];const b=tt.querySelector('.ps-d b');out.pasosB=b?Math.round(parseFloat(getComputedStyle(b).fontSize)*10)/10:null;}
 const pd=document.querySelector('.pasos .tile.t .ps-data');
 if(pd){out.pasosData=[...pd.children].map(x=>{const r=x.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.width)]});}
 const n7=document.querySelector('.card.deficit .num.m');
 if(n7){out.num7=Math.round(parseFloat(getComputedStyle(n7).fontSize)*10)/10;}
 const ps=document.querySelector('section.pasos');
 if(ps&&innerWidth>760){const sr=ps.getBoundingClientRect(),wb=ps.querySelector('.tile.wide');out.pasosAlto=[Math.round(sr.height),innerHeight];if(sr.top<innerHeight/2&&sr.bottom>innerHeight/2&&sr.height>innerHeight+2) bad.push('pasos: la parada mide '+Math.round(sr.height)+'px y la ventana '+innerHeight+'px (se corta el último bloque)');}
 out.bad=bad;
 return JSON.stringify(out);
})()
