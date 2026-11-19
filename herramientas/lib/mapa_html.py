#!/usr/bin/env python3
"""Mapa del HTML fuente: en qué línea empieza cada sección (pantalla) y cada bloque grande de CSS/JS,
para saltar directo con Read offset/limit en vez de buscar. Uso: python3 -I mapa_html.py <informe-scroll.html>  > MAPA-HTML.md"""
import re, sys
L = open(sys.argv[1], encoding='utf-8').read().split('\n')
print('# Mapa de informe-scroll.html (%d líneas) — se rehace con `python3 -I herramientas/lib/mapa_html.py scroll/informe-scroll.html > herramientas/MAPA-HTML.md`\n' % len(L))
print('## Secciones del cuerpo (línea · etiqueta)')
for i, l in enumerate(L, 1):
    m = re.match(r'\s*<(section|header|footer|main)\b([^>]*)>', l)
    if m:
        cls = re.search(r'class="([^"]*)"', m.group(2)); lab = re.search(r'aria-labelledby="([^"]*)"', m.group(2)); idd = re.search(r'\bid="([^"]*)"', m.group(2))
        print('- %d · <%s class="%s"%s%s>' % (i, m.group(1), cls.group(1) if cls else '', ' id=' + idd.group(1) if idd else '', ' labelledby=' + lab.group(1) if lab else ''))
    m = re.match(r'\s*<!-- =+ (.+?) =+ -->', l)
    if m: print('  - %d · «%s»' % (i, m.group(1)))
print('\n## Bloques de CSS / JS')
for i, l in enumerate(L, 1):
    if re.match(r'\s*<(style|script)\b', l): print('- %d · %s' % (i, l.strip()[:60]))
    m = re.match(r'/\* -{5,} (.{10,90})', l)
    if m: print('  - %d · %s…' % (i, m.group(1)))
