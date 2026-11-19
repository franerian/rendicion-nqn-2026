// Perfil de red de UNA carga con Chrome sin cabeza + CDP.
// Uso: node cdp-netprofile.mjs <carpeta-perfil> <url> [ancho=1440] [alto=900] [segundos-despues-del-load=12] [kbps-bajada]
// Perfil nuevo = caché fría (primera visita); repetir con la misma carpeta = visita de vuelta (caché tibia).
import { spawn } from 'node:child_process';
import fs from 'node:fs';

const [, , profDir, url, Ws = '1440', Hs = '900', extraS = '12', kbps] = process.argv;
const W = +Ws, H = +Hs;
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 20000 + (process.pid % 20000);
fs.mkdirSync(profDir, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profDir}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio',
  '--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1',
  `--window-size=${W},${H}`, '--disable-background-timer-throttling',
  '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
  '--disable-features=Translate,MediaRouter', 'about:blank',
], { stdio: 'ignore' });
const bye = () => { try { chrome.kill('SIGKILL'); } catch (e) {} };
process.on('exit', bye);
process.on('SIGINT', () => { bye(); process.exit(1); });

for (let i = 0; i < 80; i++) {
  try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) break; } catch (e) {}
  await sleep(250);
}
const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((ok, ko) => { ws.onopen = ok; ws.onerror = ko; });
let id = 0; const pend = new Map(); const evs = [];
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pend.has(m.id)) { const { ok, ko } = pend.get(m.id); pend.delete(m.id); m.error ? ko(new Error(JSON.stringify(m.error))) : ok(m.result); }
  else evs.push(m);
};
const send = (method, params = {}) => new Promise((ok, ko) => { const i = ++id; pend.set(i, { ok, ko }); ws.send(JSON.stringify({ id: i, method, params })); });

await send('Page.enable'); await send('Network.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
if (kbps) await send('Network.emulateNetworkConditions', { offline: false, latency: 40, downloadThroughput: (+kbps * 1024) / 8, uploadThroughput: (+kbps * 1024) / 8 });

const wall0 = Date.now();
await send('Page.navigate', { url });
// esperar el evento load
let loadAt = null;
for (let i = 0; i < 600 && loadAt === null; i++) {
  await sleep(100);
  const e = evs.find((x) => x.method === 'Page.loadEventFired');
  if (e) loadAt = Date.now() - wall0;
}
await sleep(+extraS * 1000);

// ---- armar la tabla de pedidos ----
const reqs = new Map(); let tBase = null;
for (const e of evs) {
  const p = e.params || {};
  if (e.method === 'Network.requestWillBeSent') {
    if (tBase === null) tBase = p.timestamp;
    if (!reqs.has(p.requestId)) reqs.set(p.requestId, { url: p.request.url, type: p.type, t0: p.timestamp, status: 0, bytes: 0, t1: null, cache: false, proto: '', redirects: 0 });
    else reqs.get(p.requestId).redirects++;
  } else if (e.method === 'Network.responseReceived') {
    const r = reqs.get(p.requestId); if (!r) continue;
    r.status = p.response.status; r.cache = !!p.response.fromDiskCache || !!p.response.fromServiceWorker; r.proto = p.response.protocol || ''; r.mime = p.response.mimeType;
    r.xcache = (p.response.headers['x-vercel-cache'] || '');
    r.tResp = p.timestamp;
  } else if (e.method === 'Network.dataReceived') {
    const r = reqs.get(p.requestId); if (r) { r.bytes += p.encodedDataLength || 0; (r.chunks ||= []).push([p.timestamp, p.encodedDataLength || 0]); }
  } else if (e.method === 'Network.loadingFinished') {
    const r = reqs.get(p.requestId); if (r) { r.t1 = p.timestamp; if (p.encodedDataLength > r.bytes) r.bytes = p.encodedDataLength; }
  } else if (e.method === 'Network.loadingFailed') {
    const r = reqs.get(p.requestId); if (r) { r.t1 = p.timestamp; r.failed = p.errorText; }
  }
}
const rows = [...reqs.values()].map((r) => ({ ...r, s: +(r.t0 - tBase).toFixed(2), e: r.t1 ? +(r.t1 - tBase).toFixed(2) : null }));
rows.sort((a, b) => a.s - b.s);
const short = (u) => { try { const x = new URL(u); return (x.host === 'rendicionnqn2026.vercel.app' || x.host.startsWith('localhost') ? '' : x.host) + x.pathname.slice(-60) + (x.search ? '?…' : ''); } catch (e) { return u.slice(0, 70); } };
console.log(`URL ${url}  ventana ${W}x${H}${kbps ? '  limitada a ' + kbps + ' kbps' : ''}`);
console.log(`evento load a los ${loadAt === null ? 'NO LLEGÓ' : (loadAt / 1000).toFixed(2) + ' s'} (reloj de pared desde navigate)`);
const nav = await send('Runtime.evaluate', { returnByValue: true, expression: `(()=>{const n=performance.getEntriesByType('navigation')[0]||{};const fcp=(performance.getEntriesByName('first-contentful-paint')[0]||{}).startTime;const v=[...document.querySelectorAll('video')];return {ttfb:Math.round(n.responseStart),dcl:Math.round(n.domContentLoadedEventEnd),load:Math.round(n.loadEventEnd),fcp:Math.round(fcp||0),transfer:n.transferSize,decoded:n.decodedBodySize,encoding:n.encodedBodySize,videos:v.length,videosConSrc:v.filter(x=>x.currentSrc).length,videosReproduciendo:v.filter(x=>!x.paused).length,imgs:document.images.length,imgsCargadas:[...document.images].filter(i=>i.complete&&i.naturalWidth>0).length,readyState:document.readyState,fonts:[...document.fonts].filter(f=>f.status==='loaded').length}})()` });
console.log('navegación (ms):', JSON.stringify(nav.result.value));
const totalBytes = rows.reduce((a, r) => a + r.bytes, 0);
const byType = {};
for (const r of rows) { const k = r.type || '?'; (byType[k] ||= { n: 0, bytes: 0 }); byType[k].n++; byType[k].bytes += r.bytes; }
console.log(`pedidos: ${rows.length}, bytes por la red (codificados): ${(totalBytes / 1048576).toFixed(2)} MiB`);
console.log('por tipo:', Object.entries(byType).map(([k, v]) => `${k}: ${v.n} pedidos / ${(v.bytes / 1048576).toFixed(2)} MiB`).join(' | '));
// bytes acumulados en el tiempo
const marks = [0.5, 1, 2, 3, 5, 8, 12, 20];
const cum = marks.map((m) => { let b = 0; for (const r of rows) for (const [t, n] of (r.chunks || [])) if (t - tBase <= m) b += n; return `${m}s:${(b / 1048576).toFixed(1)}MiB`; });
console.log('acumulado:', cum.join('  '));
console.log('--- pedidos (inicio→fin en s | estado | tipo | KiB | caché | ruta)');
for (const r of rows) {
  console.log(`${String(r.s).padStart(6)}→${String(r.e ?? '…').padStart(6)} | ${r.status}${r.cache ? ' (disco)' : ''}${r.failed ? ' FALLÓ ' + r.failed : ''} | ${(r.type || '?').padEnd(10)} | ${(r.bytes / 1024).toFixed(0).padStart(6)} | ${(r.xcache || '').padEnd(5)} | ${short(r.url)}`);
}
ws.close(); bye();
