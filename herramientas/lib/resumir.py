#!/usr/bin/env python3
"""Resume las medidas que deja medir.sh (un r*.log por tanda de pantallas). Uso:
  resumir.py <carpeta>          lista, por pantalla, lo que se sale (sin los avisos ya conocidos)
  resumir.py <carpeta> --todo   incluye también los avisos conocidos
  resumir.py --mapa <carpeta>   imprime el mapa número → nombre de las pantallas capturadas
Sale con código 1 si hay problemas nuevos, 2 si no hay resultados."""
import glob
import json
import os
import re
import sys


def conocido(aviso, vw):
    """Avisos anteriores a la v77 que no son errores (se compararon contra la v76 publicada)."""
    if 'Ley de Ficha Limpia' in aviso and 'dos renglones' in aviso:
        return True  # texto en .num m; el CSS de #12 lo baja a dos renglones a propósito
    if re.search(r'pasa [1-6]px por la izquierda de card light pair', aviso):
        return True  # 1280×720: hasta 3 px de sobra en #13/#14 (v76); a 1280×720 el .seg de #14 usa zoom y el medidor marca hasta 5 px: es del zoom, se ve entero
    if vw <= 320 and re.search(r'«=(32\.449|2\.100km)» pasa \d+px del borde útil de cl-tile t3', aviso):
        return True  # cierre a 320 px de ancho: igual en la v76
    return False


def leer(raiz):
    filas = []
    for f in sorted(glob.glob(os.path.join(raiz, 'r*.log'))):
        cur = None
        for ln in open(f, encoding='utf-8', errors='replace'):
            ln = ln.rstrip('\n')
            m = re.match(r'\s+eval: (.*)$', ln)
            if m:
                try:
                    s = json.loads(m.group(1))
                    cur = json.loads(s) if isinstance(s, str) else s
                except Exception:
                    cur = {'bad': ['no se pudo leer la medida']}
                continue
            m = re.match(r'#(\d+) (ok|XX)\s+(\S+) sy=(-?\d+) sw=(\d+)/(\d+) cut=(\d+)', ln)
            if m:
                filas.append((int(m.group(1)), m.group(2), int(m.group(5)), int(m.group(6)), cur or {}))
                cur = None
    filas.sort(key=lambda r: r[0])
    return filas


if len(sys.argv) >= 3 and sys.argv[1] == '--mapa':
    mapa = {}
    for f in glob.glob(os.path.join(sys.argv[2], 'r*', 'metrics.json')):
        try:
            for d in json.load(open(f)):
                if d.get('hash') and d.get('req'):
                    mapa[d['req']] = d['hash'].lstrip('#')
        except Exception:
            pass
    for n in sorted(mapa):
        print(mapa[n])
    sys.exit(0)

raiz = sys.argv[1]
todo = '--todo' in sys.argv
filas = leer(raiz)
if not filas:
    print('SIN RESULTADOS en %s (¿falló Chrome o la dirección?)' % raiz)
    sys.exit(2)
malas = 0
ignorados = 0
for n, ok, sw, vw, ev in filas:
    bad = ev.get('bad', [])
    reales = [b for b in bad if todo or not conocido(b, ev.get('vw', vw))]
    ignorados += len(bad) - len(reales)
    if ok != 'ok' or sw > vw or reales:
        malas += 1
        print('#%02d %s sw=%d/%d %s' % (n, ok, sw, vw, '; '.join(reales)[:400]))
print('RESULTADO %s: %d pantallas con problemas de %d medidas (%d avisos conocidos ignorados)' % (
    os.path.basename(raiz.rstrip('/')), malas, len(filas), ignorados))
sys.exit(1 if malas else 0)
