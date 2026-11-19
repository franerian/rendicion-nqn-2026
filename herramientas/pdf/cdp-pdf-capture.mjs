// Captura cada pantalla (parada) del informe para armar el PDF de la presentación.
// Una imagen por pantalla al tamaño de la ventana de proyección (2160×1080), con factor de escala DSF
// (2 = el doble de píxeles, texto nítido), las fotos que rotan quietas, y el texto visible de cada pantalla
// palabra por palabra (para una capa de texto invisible que permita buscar y copiar).
// Uso: DSF=2 node cdp-pdf-capture.mjs <carpeta> <ancho> <alto> <desde> <hasta> [url-base]
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const [, , outDir, Ws, Hs, fromS = '1', toS = '48', baseArg] = process.argv;
const W = +Ws, H = +Hs, FROM = +fromS, TO = +toS;
const DSF = +(process.env.DSF || 2);
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

// fotos que rotan (fichas de Rutas, natatorio): se dejan quietas con el mismo evento que las pausa con el mouse
const FREEZE = `(()=>{let k=0;document.querySelectorAll('.cl-tile.multi,.nv-rot').forEach(t=>{try{t.dispatchEvent(new PointerEvent('pointerenter',{pointerType:'mouse'}));k++}catch(e){}});return k})()`;

// texto visible palabra por palabra: [palabra, left, top, ancho, alto, tamaño de fuente, escala horizontal (%) contra Arial]
const TEXTS = `(()=>{
 const vw=innerWidth, vh=innerHeight;
 const cv=document.createElement('canvas').getContext('2d');
 const out=[];
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 let t;
 while(t=walker.nextNode()){
   const s=t.textContent; if(!s.trim()) continue;
   const e=t.parentElement; if(!e) continue;
   if(e.closest('script,style,noscript,[hidden],.sr')) continue;
   const cs=getComputedStyle(e); if(cs.visibility==='hidden'||cs.display==='none') continue;
   let o=1,x=e; while(x&&x!==document.body){o*=+getComputedStyle(x).opacity; x=x.parentElement}
   if(o<.05) continue;
   const fs=parseFloat(cs.fontSize);
   const noPE=cs.pointerEvents==='none';
   const owner=e.closest('p,h1,h2,h3,h4,h5,h6,li,figcaption,button,a,td,th,label,dt,dd')||e;
   const re=/\\S+/g; let m;
   while(m=re.exec(s)){
     const rg=document.createRange(); rg.setStart(t,m.index); rg.setEnd(t,m.index+m[0].length);
     const rs=[...rg.getClientRects()].filter(r=>r.width>1&&r.height>1);
     if(!rs.length) continue;
     const r=rs[0];
     if(r.bottom<=0||r.top>=vh||r.right<=0||r.left>=vw) continue;
     if(!noPE){
       /* tapado por otra pantalla encima (sus fondos son opacos): lo que está abajo no se ve y no va en el texto.
          Las capas transparentes (los .steps que dan el largo del scroll) no cuentan como tapa */
       const cx=Math.min(Math.max(r.left+r.width/2,1),vw-1), cy=Math.min(Math.max(r.top+r.height/2,1),vh-1);
       let hidden=false;
       for(const x of document.elementsFromPoint(cx,cy)){
         if(owner.contains(x)||x.contains(owner)) break;
         const xs=getComputedStyle(x);
         if(xs.visibility==='hidden'||+xs.opacity<.6) continue;
         let cover=/^(IMG|VIDEO|CANVAS|PICTURE)$/i.test(x.tagName)||xs.backgroundImage!=='none';
         if(!cover&&xs.backgroundColor!=='transparent'){const p=xs.backgroundColor.replace(/[^0-9.,]/g,'').split(',').map(Number); cover=(p.length>3?p[3]:1)>=.6}
         if(cover){hidden=true;break}
       }
       if(hidden) continue;
     }
     cv.font=fs+'px Arial'; const nat=cv.measureText(m[0]).width;
     out.push([m[0], +r.left.toFixed(1), +r.top.toFixed(1), +r.width.toFixed(1), +r.height.toFixed(1), +fs.toFixed(1), nat?+(100*r.width/nat).toFixed(1):100]);
   }
 }
 return JSON.stringify(out);
})()`;

// videos a la vista: ¿decodifican?, ¿en qué cuadro están?
const VIDS = `(()=>{
 const vw=innerWidth, vh=innerHeight;
 return JSON.stringify([...document.querySelectorAll('video')].map(v=>{const r=v.getBoundingClientRect();
   if(r.bottom<=0||r.top>=vh||r.right<=0||r.left>=vw||r.width<2) return null;
   return {src:(v.currentSrc||v.getAttribute('data-src')||'').split('/').pop(), rs:v.readyState, paused:v.paused, t:+v.currentTime.toFixed(2), w:v.videoWidth, h:v.videoHeight}}).filter(Boolean));
})()`;

// videos con reproductor (figure.video: cartel con botón ▶) a la vista, con su caja y el archivo que reproducen (ruta tal como está en el HTML)
const LINKS = `(()=>{
 const vw=innerWidth, vh=innerHeight, out=[];
 document.querySelectorAll('figure.video').forEach(f=>{
   const v=f.querySelector('video'), s=v&&v.querySelector('source'), r=f.getBoundingClientRect();
   if(!v||r.width<2||r.bottom<=0||r.top>=vh||r.right<=0||r.left>=vw) return;
   out.push({kind:'video',src:(s&&s.getAttribute('src'))||v.getAttribute('src')||'',title:v.getAttribute('aria-label')||'',rect:[r.left,r.top,r.right,r.bottom].map(x=>+x.toFixed(1))});
 });
 return JSON.stringify(out);
})()`;

const METRICS = `(()=>{
 const vw=innerWidth, vh=innerHeight, d=document.documentElement;
 return JSON.stringify({sy:Math.round(scrollY),vw,vh,dpr:devicePixelRatio,sw:d.scrollWidth,sh:d.scrollHeight,hash:location.hash});
})()`;

await waitDevtools();
const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find((t) => t.type === 'page');
const cdp = await connect(page.webSocketDebuggerUrl);
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
await cdp.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: DSF, mobile: false, screenWidth: W, screenHeight: H });
await cdp.send('Emulation.setFocusEmulationEnabled', { enabled: true });

const metaPath = path.join(outDir, 'meta.json');
const all = fs.existsSync(metaPath) ? JSON.parse(fs.readFileSync(metaPath, 'utf8')).filter((m) => m.n < FROM || m.n > TO) : [];
for (let n = FROM; n <= TO; n++) {
  const url = `${BASE}?pdf=${W}x${H}&n=${n}#${pad(n)}`;
  const loaded = cdp.once('Page.loadEventFired', 25000);
  await cdp.send('Page.navigate', { url });
  await loaded;
  await cdp.send('Runtime.evaluate', { expression: 'document.fonts&&document.fonts.ready?document.fonts.ready.then(()=>1):1', awaitPromise: true });
  await sleep(3800); // settle (4 pasadas de 700 ms) + cifras que cuentan 1600 ms
  let prev = -1;
  for (let k = 0; k < 6; k++) {
    const r = await cdp.send('Runtime.evaluate', { expression: 'Math.round(scrollY)', returnByValue: true });
    if (r.result.value === prev) break;
    prev = r.result.value; await sleep(400);
  }
  const fz = await cdp.send('Runtime.evaluate', { expression: FREEZE, returnByValue: true });
  await sleep(fz.result.value > 0 ? 1600 : 300);
  // texto de ayuda de la página web (teclas) que no corresponde en un PDF: se oculta antes de capturar y de leer el texto
  if (process.env.HIDE) await cdp.send('Runtime.evaluate', { expression: `document.querySelectorAll(${JSON.stringify(process.env.HIDE)}).forEach(e=>{e.style.visibility='hidden'})` });
  // SEEK0='<selector>': los videos que coinciden se frenan en su primer cuadro (la página no los vuelve a arrancar)
  if (process.env.SEEK0) {
    const sk = await cdp.send('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression: `(async()=>{
      const vs=[...document.querySelectorAll(${JSON.stringify(process.env.SEEK0)})];
      for(const v of vs){
        v.play=()=>Promise.resolve(); v.pause();
        await new Promise(res=>{ const h=()=>{v.removeEventListener('seeked',h);res()}; v.addEventListener('seeked',h); v.currentTime=0; setTimeout(res,3000) });
      }
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      return JSON.stringify(vs.map(v=>({t:v.currentTime,rs:v.readyState,paused:v.paused})));
    })()` });
    console.log('  seek0:', sk.result.value);
    await sleep(900);
  }
  const mr = await cdp.send('Runtime.evaluate', { expression: METRICS, returnByValue: true });
  let met = {};
  try { met = JSON.parse(mr.result.value); } catch (e) { met = { error: String(mr.result && mr.result.description) }; }
  const tr = await cdp.send('Runtime.evaluate', { expression: TEXTS, returnByValue: true });
  let words = [];
  try { words = JSON.parse(tr.result.value); } catch (e) { words = []; }
  const vr = await cdp.send('Runtime.evaluate', { expression: VIDS, returnByValue: true });
  let vids = [];
  try { vids = JSON.parse(vr.result.value); } catch (e) { vids = []; }
  if (!process.env.NOSHOT) { // NOSHOT=1: solo el texto (sin captura), para rehacer la capa de texto sin volver a sacar las imágenes
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, `s${pad(n)}.png`), Buffer.from(shot.data, 'base64'));
  }
  const ok = met.hash && met.hash.startsWith('#' + pad(n));
  const lr = await cdp.send('Runtime.evaluate', { expression: LINKS, returnByValue: true });
  let links = [];
  try { links = JSON.parse(lr.result.value); } catch (e) { links = []; }
  all.push({ n, ok: !!ok, ...met, frozen: fz.result.value, vids, links, words });
  if (links.length) console.log('  enlaces:', JSON.stringify(links));
  console.log(`#${pad(n)} ${ok ? 'ok ' : 'XX '} ${met.hash || '(sin hash)'} sy=${met.sy} dpr=${met.dpr} words=${words.length} frozen=${fz.result.value} vids=${vids.map((v) => v.src + ':' + v.rs + (v.paused ? 'P' : '>') + v.t).join(',')}`);
  all.sort((a, b) => a.n - b.n);
  fs.writeFileSync(metaPath, JSON.stringify(all));
}
cdp.close();
bye();
console.log('FIN');
process.exit(0);
