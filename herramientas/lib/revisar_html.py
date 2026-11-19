#!/usr/bin/env python3
"""Revisa el index.html armado antes de publicar. Uso: revisar_html.py <index.html>
Sale con código 1 si encuentra algo que las reglas del proyecto prohíben (REGLAS)."""
import hashlib
import re
import sys

# Reglas del proyecto sobre el texto (se editan acá si el cliente las cambia):
REGLAS = [
    (r'\d\.000\.000', 'cifras con todos los ceros de millones (desde la v77 van con «M»: «U$S 450 M»)'),
    (r'(?i)mill', 'la palabra «millones» (los montos van con «M»)'),
    (r'U\$D', '«U$D» (los dólares son «U$S»)'),
]

raw = open(sys.argv[1], 'rb').read()
html = raw.decode('utf-8')
print('index.html: %s bytes, sha256 %s…' % (format(len(raw), ',').replace(',', '.'), hashlib.sha256(raw).hexdigest()[:16]))
malo = False
if html.lstrip().lower().startswith('<!doctype html'):
    print('  ok: doctype')
else:
    print('  MAL: falta el doctype (el HTML fuente no lo lleva: lo agrega build_deploy.py)')
    malo = True
print('  cifras con «M» (&nbsp;M): %d' % html.count('&nbsp;M'))
for pat, que in REGLAS:
    hits = list(re.finditer(pat, html))
    if hits:
        malo = True
        print('  MAL: %d veces %s' % (len(hits), que))
        for m in hits[:4]:
            a = max(0, m.start() - 40)
            print('       …%s…' % html[a:m.end() + 30].replace('\n', ' '))
    else:
        print('  ok: sin %s' % que.split(' (')[0])
sys.exit(1 if malo else 0)
