#!/usr/bin/env python3
"""Arma el paquete sin internet para Windows (carpeta + .zip) con las primeras N pantallas del informe.

uso: armar_demo.py SALIDA_DIR [--completo]
  - sin flag: la demo (las primeras 10 pantallas); con --completo: TODAS las pantallas (Presentacion-completa.zip)
  - corta el HTML al final de la sección del giro (pantallas 1 a 10 de la versión vigente);
  - copia solo las imágenes y videos que esas pantallas usan;
  - baja la tipografía Manrope (latín y latín extendido, variable 300–800) y la usa desde la carpeta, sin Google Fonts;
  - agrega «Abrir presentacion.bat» (Edge o Chrome a pantalla completa, perfil aparte) y LEEME.txt.
Hace falta internet SOLO al armar el paquete (para bajar la fuente)."""
import os, re, shutil, subprocess, sys, urllib.request, zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(AQUI, '..', 'scroll')
COMPLETO = '--completo' in sys.argv
OUT = os.path.abspath([a for a in sys.argv[1:] if not a.startswith('--')][0])
NOMBRE = 'Presentacion-completa' if COMPLETO else 'Presentacion-demo'
RAIZ = os.path.join(OUT, NOMBRE)
PRES = os.path.join(RAIZ, 'Presentacion')

html = open(os.path.join(SRC, 'informe-scroll.html'), encoding='utf-8').read()

# ---- cortar: se queda hasta el final de la sección del giro (#giro) y se saca lo que va después, hasta </main> ----
if not COMPLETO:
    ini = html.index('<!-- ============ DESPUÉS: LO QUE HICIMOS')
    fin = html.index('</main>')
    assert ini < fin and html.index('id="giro"') < ini
    html = html[:ini] + '\n' + html[fin:]

# ---- tipografía local ----
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
req = urllib.request.Request('https://fonts.googleapis.com/css2?family=Manrope:wght@300..800&display=swap', headers={'User-Agent': UA})
css = urllib.request.urlopen(req, timeout=30).read().decode()
os.makedirs(os.path.join(PRES, 'fonts'), exist_ok=True)
bloques = re.findall(r'/\* ([a-z\-]+) \*/\s*(@font-face \{.*?\})', css, re.S)
out_css = []
for sub, b in bloques:
    if sub not in ('latin', 'latin-ext'):
        continue
    url = re.search(r'url\((https://[^)]+)\)', b).group(1)
    data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30).read()
    fn = 'manrope-%s.woff2' % sub
    open(os.path.join(PRES, 'fonts', fn), 'wb').write(data)
    out_css.append('/* %s */\n%s' % (sub, b.replace(url, fn)))
assert len(out_css) == 2
open(os.path.join(PRES, 'fonts', 'manrope.css'), 'w', encoding='utf-8').write('\n'.join(out_css) + '\n')
viejo = re.search(r'<link rel="preconnect" href="https://fonts.googleapis.com">\s*<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\s*<link rel="stylesheet" href="https://fonts.googleapis.com/css2[^>]*>', html)
assert viejo
html = html.replace(viejo.group(0), '<link rel="stylesheet" href="fonts/manrope.css">')
assert 'fonts.googleapis' not in html and 'fonts.gstatic' not in html

# ---- medios que usan las pantallas que quedaron ----
pat = re.compile(r'(?:img|video)/[A-Za-z0-9_./%\-]+\.(?:jpg|jpeg|png|webp|svg|gif|avif|mp4|webm)', re.I)
refs = sorted(set(pat.findall(html)))
faltan = [r for r in refs if not os.path.isfile(os.path.join(SRC, r))]
assert not faltan, faltan
total = 0
for r in refs:
    dst = os.path.join(PRES, r)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(SRC, r), dst)
    total += os.path.getsize(dst)
open(os.path.join(PRES, 'index.html'), 'w', encoding='utf-8').write('<!doctype html>\n<html lang="es">\n' + html)

# ---- lanzador de Windows (solo ASCII y saltos CRLF) ----
bat = r'''@echo off
setlocal
rem Abre la presentacion a pantalla completa, sin internet. Para salir: Alt + F4.
set "PAGINA=%~dp0Presentacion\index.html"
if not exist "%PAGINA%" (
  echo No encuentro Presentacion\index.html. Descomprima TODO el zip antes de abrir.
  pause
  exit /b 1
)
set "URL=file:///%PAGINA:\=/%"
set "PERFIL=%TEMP%\presentacion-nqn-perfil"
set "OPC=--kiosk --user-data-dir="%PERFIL%" --no-first-run --no-default-browser-check --autoplay-policy=no-user-gesture-required"
set "EDGE1=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
set "EDGE2=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
set "CHR1=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHR2=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set "CHR3=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if exist "%EDGE1%" ( start "" "%EDGE1%" %OPC% --edge-kiosk-type=fullscreen "%URL%" & exit /b 0 )
if exist "%EDGE2%" ( start "" "%EDGE2%" %OPC% --edge-kiosk-type=fullscreen "%URL%" & exit /b 0 )
if exist "%CHR1%" ( start "" "%CHR1%" %OPC% "%URL%" & exit /b 0 )
if exist "%CHR2%" ( start "" "%CHR2%" %OPC% "%URL%" & exit /b 0 )
if exist "%CHR3%" ( start "" "%CHR3%" %OPC% "%URL%" & exit /b 0 )
rem Sin Edge ni Chrome: el navegador que tenga el equipo (en ventana comun; F11 para pantalla completa)
start "" "%PAGINA%"
'''
open(os.path.join(RAIZ, 'Abrir presentacion.bat'), 'w', encoding='ascii', newline='').write(bat.replace('\n', '\r\n'))

leeme = '''PRESENTACION · RENDICION DE CUENTAS (%s)
================================================================

Funciona SIN internet. Esta carpeta es todo lo que hace falta.

1) Copiar la carpeta completa al disco de la notebook (o abrirla desde el pendrive).
   Si llego como .zip: clic derecho > "Extraer todo..." y abrir la carpeta extraida
   (no abrir los archivos desde adentro del zip).
2) Doble clic en  "Abrir presentacion.bat".
   Se abre a pantalla completa en Microsoft Edge (o en Chrome si no hay Edge).
   Si Windows avisa "Windows protegio su PC": Mas informacion > Ejecutar de todas formas.

Para moverse
   Avanzar:  flecha derecha / flecha abajo / barra espaciadora / rueda del mouse
   Volver:   flecha izquierda / flecha arriba
   Salir:    Alt + F4
   Consulta rapida (para el que presenta):  1 = cuadro 2030,  2 = Fondos soberanos,  3 = cuadro RIGI.
   La misma tecla (o Esc) lo cierra y la presentacion sigue en el mismo punto.

Si el .bat no abre nada: abrir con doble clic  Presentacion\\index.html  (se ve en cualquier
navegador; para pantalla completa, tecla F11).

Para probar antes de presentar
   - Desconectar el wifi y abrir la presentacion: tiene que verse igual (letra incluida).
   - Pasar las pantallas con las flechas y mirar que los videos arranquen.
   - Probar en la pantalla o proyector real (la presentacion esta pensada para 2160 x 1080).
'''
open(os.path.join(RAIZ, 'LEEME.txt'), 'w', encoding='utf-8-sig', newline='').write((leeme % ('COMPLETA: todas las pantallas' if COMPLETO else 'DEMO: primeras 10 pantallas')).replace('\n', '\r\n'))

# ---- zip ----
zpath = os.path.join(OUT, NOMBRE + '.zip')
if os.path.exists(zpath):
    os.remove(zpath)
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_STORED) as z:  # los mp4 y los webp ya vienen comprimidos
    for d, _, fs in os.walk(RAIZ):
        for f in sorted(fs):
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, OUT))
print('medios: %d archivos, %.1f MB | zip: %s (%.1f MB)' % (len(refs), total / 1e6, zpath, os.path.getsize(zpath) / 1e6))
