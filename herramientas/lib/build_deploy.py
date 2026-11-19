import json
import os
import re
import shutil
import sys

SRC = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
URL = sys.argv[3] if len(sys.argv) > 3 else 'https://rendicionnqn2026.vercel.app'
assert os.path.basename(OUT) in ('deploy', 'rendicion-nqn-deploy') and OUT != SRC, OUT  # solo se limpia una carpeta de trabajo propia (se conserva su .vercel)

html = open(os.path.join(SRC, 'informe-scroll.html'), encoding='utf-8').read()

# ---- todo lo que el HTML usa de img/ y video/ ----
pat = re.compile(r'(?:img|video)/[A-Za-z0-9_./%\-]+\.(?:jpg|jpeg|png|webp|svg|gif|avif|mp4|webm)', re.I)
# páginas aparte (scroll/opciones-*.html y scroll/opcion-*.html, p. ej. las opciones de diseño del cuadro 2030): se publican en /<nombre> (cleanUrls) y sus medios también
extras = sorted(f for f in os.listdir(SRC) if re.fullmatch(r'opcion(?:es)?-[a-z0-9-]+\.html', f))
extra_html = {f: open(os.path.join(SRC, f), encoding='utf-8').read() for f in extras}
refs = sorted(set(pat.findall(html)).union(*[set(pat.findall(h)) for h in extra_html.values()]))
missing = [r for r in refs if not os.path.isfile(os.path.join(SRC, r))]
if missing:
    print('FALTAN archivos referenciados:')
    for m in missing:
        print('  -', m)
    sys.exit(1)

# ---- carpeta de salida limpia (se conserva .vercel, el enlace al proyecto) ----
os.makedirs(OUT, exist_ok=True)
for name in os.listdir(OUT):
    if name == '.vercel':
        continue
    p = os.path.join(OUT, name)
    if os.path.isdir(p):
        shutil.rmtree(p)
    else:
        os.remove(p)

total = 0
rows = []
for r in refs:
    dst = os.path.join(OUT, r)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(SRC, r), dst)
    n = os.path.getsize(dst)
    total += n
    rows.append((n, r))

# ---- index.html: doctype, idioma y datos para vista previa al compartir el link ----
desc = 'Rendición de cuentas · Gobernador Cr. Rolando Figueroa'
meta = (
    '<meta name="description" content="%s">\n'
    '<meta property="og:type" content="website">\n'
    '<meta property="og:locale" content="es_AR">\n'
    '<meta property="og:title" content="Rendición de cuentas del gobierno de la provincia del Neuquén">\n'
    '<meta property="og:description" content="%s">\n'
    '<meta property="og:url" content="%s/">\n'
    '<meta property="og:image" content="%s/img/fondos/hero-mil-razones.jpg">\n'
    '<meta name="twitter:card" content="summary_large_image">\n'
) % (desc, desc, URL, URL)
anchor = '<meta name="claude:viewport-fit-sides" content="cover">\n'
assert html.count(anchor) == 1
out_html = '<!doctype html>\n<html lang="es">\n' + html.replace(anchor, anchor + meta, 1)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(out_html)

for f, h in extra_html.items():
    assert h.lstrip().lower().startswith('<!doctype'), f
    open(os.path.join(OUT, f), 'w', encoding='utf-8').write(h)
if extras:
    print('páginas aparte: ' + ', '.join(extras))

# ---- vercel.json: sitio estático, caché de medios y cabeceras básicas ----
cfg = {
    'cleanUrls': True,
    'trailingSlash': False,
    'headers': [
        {'source': '/(.*)', 'headers': [
            {'key': 'X-Content-Type-Options', 'value': 'nosniff'},
            {'key': 'Referrer-Policy', 'value': 'strict-origin-when-cross-origin'},
        ]},
        {'source': '/img/(.*)', 'headers': [
            {'key': 'Cache-Control', 'value': 'public, max-age=86400, stale-while-revalidate=604800'},
        ]},
        {'source': '/video/(.*)', 'headers': [
            {'key': 'Cache-Control', 'value': 'public, max-age=86400, stale-while-revalidate=604800'},
        ]},
    ],
}
open(os.path.join(OUT, 'vercel.json'), 'w', encoding='utf-8').write(json.dumps(cfg, indent=2) + '\n')

# ---- resumen ----
all_files = []
for base, _, files in os.walk(SRC):
    for f in files:
        rel = os.path.relpath(os.path.join(base, f), SRC)
        if rel.startswith(('img/', 'video/')):
            all_files.append(rel)
unused = sorted(set(all_files) - set(refs))
print('referenciados: %d archivos, %.1f MB (+ index.html %.0f KB)' % (len(refs), total / 1048576, len(out_html.encode('utf-8')) / 1024))
print('sin usar (no se publican): %d archivos' % len(unused))
for n, r in sorted(rows, reverse=True)[:8]:
    print('  %6.2f MB  %s' % (n / 1048576, r))
print('OUT', OUT)
