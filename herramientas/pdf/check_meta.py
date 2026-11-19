#!/usr/bin/env python3
"""Revisa la captura del PDF (meta.json): numeración completa, 2160 px de ancho, dpr 2, texto y enlaces.
Uso: python3 -I check_meta.py <carpeta-capturas> <total-de-pantallas>"""
import json, sys
shots, total = sys.argv[1], int(sys.argv[2])
meta = json.load(open(shots + '/meta.json'))
print('pantallas:', len(meta), '| numeración completa:', [m['n'] for m in meta] == list(range(1, total + 1)))
print('sin "ok" (el hash no empieza con #NN):', [m['n'] for m in meta if not m.get('ok')])
print('ancho de scroll distinto de 2160:', [(m['n'], m.get('sw')) for m in meta if m.get('sw') != 2160])
print('dpr distinto de 2:', [(m['n'], m.get('dpr')) for m in meta if m.get('dpr') != 2])
print('con error de métricas:', [m['n'] for m in meta if 'error' in m])
w = [len(m['words']) for m in meta]
print('palabras por pantalla (mín/máx/total):', min(w), max(w), sum(w), '| pantallas sin palabras:', [m['n'] for m in meta if not m['words']])
print('enlaces:', {m['n']: [(l['src'], [round(x) for x in l['rect']]) for l in m['links']] for m in meta if m['links']})
txt = {m['n']: ' '.join(x[0] for x in m['words']) for m in meta}
for pal in ('Avanzar', 'millon', 'U$D', 'Gobernador'):
    print('  "%s" en:' % pal, [n for n, t in txt.items() if pal.lower() in t.lower()])
print('--- nombres de las paradas ---')
print('  '.join(m['hash'].lstrip('#') for m in sorted(meta, key=lambda m: m['n'])))
