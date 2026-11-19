// Captura cada pantalla (parada) del informe a un tamaño de ventana exacto con Chrome sin cabeza.
// Uso: node cdp-capture.mjs <carpeta-salida> <ancho> <alto> <desde> <hasta> [url-base]
// Cada parada se abre con su código (#NN), igual que entra el usuario con el link; se espera a que
// el script de la página termine de acomodarla (settle) y de contar las cifras, y se saca la captura.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const [, , outDir, Ws, Hs, fromS = '1', toS = '46', baseArg] = process.argv;
const W = +Ws, H = +Hs, FROM = +fromS, TO = +toS;
const BASE = baseArg || 'http://localhost:8791/informe-scroll.html';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 20000 + (process.pid % 20000);
const PROF = path.join(outDir, '.profile');
fs.mkdirSync(outDir, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const pad = (n) => (n < 10 ? '0' + n : '' + n);

const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROF}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio',
  '--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1',
  `--window-size=${W},${H}`, '--disable-background-timer-throttling',
  '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
  '--disable-features=Translate,MediaRouter', 'about:blank',
], { stdio: 'ignore' });
const bye = () => { try { chrome.kill('SIGKILL'); } catch (e) {} };
process.on('exit', bye);
process.on('SIGINT', () => { bye(); process.exit(1); });

async function waitDevtools() {
  for (let i = 0; i < 80; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) return; } catch (e) {}
    await sleep(250);
  }
  throw new Error('Chrome no abrió el puerto de depuración');
}

function connect(url) {
  return new Promise((res, rej) => {
    const ws = new WebSocket(url);
    let id = 0;
    const pend = new Map();
    const handlers = new Set();
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && pend.has(m.id)) {
        const { ok, ko } = pend.get(m.id); pend.delete(m.id);
        m.error ? ko(new Error(JSON.stringify(m.error))) : ok(m.result);
      } else handlers.forEach((h) => h(m));
    };
    ws.onopen = () => res({
      send: (method, params = {}) => new Promise((ok, ko) => { const i = ++id; pend.set(i, { ok, ko }); ws.send(JSON.stringify({ id: i, method, params })); }),
      once: (name, ms) => new Promise((ok) => { const t = setTimeout(() => { handlers.delete(h); ok(false); }, ms); const h = (m) => { if (m.method === name) { clearTimeout(t); handlers.delete(h); ok(true); } }; handlers.add(h); }),
      close: () => ws.close(),
    });
    ws.onerror = (e) => rej(e);
  });
}

const METRICS = `(()=>{
 const vw=innerWidth, vh=innerHeight, d=document.documentElement;
 const res={sy:Math.round(scrollY),vw,vh,sw:d.scrollWidth,sh:d.scrollHeight,hash:location.hash};
 let L=1e9,R=-1e9,T=1e9,B=-1e9,n=0;const cut=[];
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 let t;
 while(t=walker.nextNode()){
   const s=t.textContent.trim(); if(!s) continue;
   const e=t.parentElement; if(!e) continue;
   if(e.closest('script,style,noscript,[hidden]')) continue;
   const cs=getComputedStyle(e); if(cs.visibility==='hidden'||cs.display==='none') continue;
   let o=1,x=e; while(x&&x!==document.body){o*=+getComputedStyle(x).opacity; x=x.parentElement}
   if(o<.05) continue;
   const rg=document.createRange(); rg.selectNodeContents(t);
   const rs=[...rg.getClientRects()].filter(r=>r.width>1&&r.height>1);
   for(const r of rs){
     if(r.bottom<=0||r.top>=vh||r.right<=0||r.left>=vw) continue;
     n++; L=Math.min(L,r.left);R=Math.max(R,r.right);T=Math.min(T,r.top);B=Math.max(B,r.bottom);
     if(r.left<-1||r.right>vw+1||r.top<-1||r.bottom>vh+1){ if(cut.length<6) cut.push((e.className&&e.className.baseVal===undefined?e.className:e.tagName)+': '+s.slice(0,40)+' ['+Math.round(r.left)+','+Math.round(r.top)+','+Math.round(r.right)+','+Math.round(r.bottom)+']'); }
   }
 }
 res.n=n;res.bbox=[Math.round(L),Math.round(T),Math.round(R),Math.round(B)];res.cut=cut;
 return JSON.stringify(res);
})()`;

await waitDevtools();
const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find((t) => t.type === 'page');
const cdp = await connect(page.webSocketDebuggerUrl);
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
await cdp.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false, screenWidth: W, screenHeight: H });
await cdp.send('Emulation.setFocusEmulationEnabled', { enabled: true });

const all = [];
for (let n = FROM; n <= TO; n++) {
  const url = `${BASE}?z=${W}x${H}&n=${n}#${pad(n)}`;
  const loaded = cdp.once('Page.loadEventFired', 25000);
  await cdp.send('Page.navigate', { url });
  await loaded;
  await cdp.send('Runtime.evaluate', { expression: 'document.fonts&&document.fonts.ready?document.fonts.ready.then(()=>1):1', awaitPromise: true });
  await sleep(3800); // settle (4 pasadas de 700 ms) + cifras que cuentan 1600 ms
  // estabilidad del scroll
  let prev = -1;
  for (let k = 0; k < 6; k++) {
    const r = await cdp.send('Runtime.evaluate', { expression: 'Math.round(scrollY)', returnByValue: true });
    if (r.result.value === prev) break;
    prev = r.result.value; await sleep(400);
  }
  const mr = await cdp.send('Runtime.evaluate', { expression: METRICS, returnByValue: true });
  let met = {};
  try { met = JSON.parse(mr.result.value); } catch (e) { met = { error: String(mr.result && mr.result.description) }; }
  met.req = n;
  const SELTEXT = process.env.SELTEXT || '';
  if (process.env.EVAL) {
    const ev = await cdp.send('Runtime.evaluate', { expression: process.env.EVAL, returnByValue: true, awaitPromise: true });
    console.log('  eval:', JSON.stringify(ev.result.value));
  }
  if (SELTEXT) {
    // centra la tarjeta que tiene ese título oculto (.sr) y mide sus cifras, la línea y el desborde
    await cdp.send('Runtime.evaluate', { expression: `(()=>{const h=[...document.querySelectorAll('.sr')].find(e=>e.textContent.trim()===${JSON.stringify(SELTEXT)}); const c=h&&h.closest('.card'); if(c) c.scrollIntoView({block:'center',behavior:'instant'}); return !!c})()`, returnByValue: true });
    await sleep(1800);
    const cm = await cdp.send('Runtime.evaluate', { returnByValue: true, expression: `(()=>{const h=[...document.querySelectorAll('.sr')].find(e=>e.textContent.trim()===${JSON.stringify(SELTEXT)}); const c=h&&h.closest('.card'); if(!c) return 'sin tarjeta';
      const r=c.getBoundingClientRect(); const cs=getComputedStyle(c); const padL=parseFloat(cs.paddingLeft), padR=parseFloat(cs.paddingRight);
      const nums=[...c.querySelectorAll('.num')].map(e=>{const b=e.getBoundingClientRect(); return {t:e.textContent.trim(), w:Math.round(b.width), sw:e.scrollWidth, right:Math.round(b.right), fs:getComputedStyle(e).fontSize}});
      const say=c.querySelector('.say'); const ul=c.querySelector('ul.rows'); const ucs=ul?getComputedStyle(ul):null;
      const lis=[...c.querySelectorAll('ul.rows>li')].map(e=>{const b=e.getBoundingClientRect(); const s=getComputedStyle(e); return {top:Math.round(b.top), h:Math.round(b.height), bt:s.borderTopWidth}});
      return JSON.stringify({card:[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)], innerRight:Math.round(r.right-padR), docOverflow: document.documentElement.scrollWidth>innerWidth, nums, sayFs: say&&getComputedStyle(say).fontSize, ulBorderTop: ucs&&ucs.borderTopWidth, ulPadTop: ucs&&ucs.paddingTop, lis});
    })()` });
    console.log('  tarjeta:', cm.result.value);
  }
  const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(outDir, `s${pad(n)}.png`), Buffer.from(shot.data, 'base64'));
  all.push(met);
  const ok = met.hash && met.hash.startsWith('#' + pad(n));
  console.log(`#${pad(n)} ${ok ? 'ok ' : 'XX '} ${met.hash || '(sin hash)'} sy=${met.sy} sw=${met.sw}/${met.vw} cut=${(met.cut || []).length}`);
  fs.writeFileSync(path.join(outDir, 'metrics.json'), JSON.stringify(all, null, 1));
}
cdp.close();
bye();
console.log('FIN');
process.exit(0);
