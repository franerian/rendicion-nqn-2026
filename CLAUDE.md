# Informe de gestión · Rendición de cuentas Neuquén (scroll)

Un solo HTML de presentación: `scroll/informe-scroll.html` (+ `scroll/img`, `scroll/video`), publicado en https://rendicionnqn2026.vercel.app (proyecto Vercel `rendicionnqn2026`, scope `franerians-projects`). Se proyecta en 2160×1080. 48 pantallas citadas `#NN` (el usuario cita el número de la versión que mira; si no coincide con el contenido, leer el CONTENIDO). Idioma: **español** con tildes. Base consolidada: `_base-v121/` (fuente y HTML publicado de v121, con el deploy para volver atrás).

## Flujo de un pedido (camino rápido)
1. Editar `scroll/informe-scroll.html` con un script `python3 -I` de reemplazos con `assert count==1` (o Edit). Para ubicarse: `herramientas/MAPA-HTML.md` (líneas por sección) y `grep -n` del texto; leer solo el tramo con `Read offset/limit`, nunca el archivo entero (≈ 280 KB).
2. Medios nuevos con nombre NUEVO (`-v2`…): el CDN cachea 24 h. Videos: `herramientas/lib/build_playlist.py` (ver memoria `reference-fondos-video-receta`); imágenes `cwebp`.
3. `herramientas/medir.sh [rapido|completo] --pantallas "37"` (rápido = 3 tamaños; completo si cambió el CSS).
4. `herramientas/publicar.sh --pantallas "37"` → debe terminar en **TODO OK** (el único «MAL» esperado es `vercel.json`). Se publica sin preguntar.
5. Documentar en la memoria (3–5 líneas): `informe-gestion-propuesta-html.md` (bloque «Cambios recientes») y una línea en `informe-gestion-deploy-vercel.md`.
- PDF + ZIP solo cuando el usuario los pide: `herramientas/exportar.sh NNN [pdf|zip|todo]` (NNN = versión; no publica nada).
- Páginas aparte: `scroll/opciones-*.html` y `scroll/opcion-*.html` (p. ej. `opciones-cuadro-2030.html`, doctype propio) se publican solas en `/<nombre>`; no son pantallas ni entran al PDF/ZIP.
- No publicar mientras corre una exportación (publicar rehace la carpeta que lee).
- Variables útiles: `RENDICION_TMP`, `RENDICION_STAGING` (por defecto bajo `$TMPDIR/rendicion-nqn`). Necesita Chrome en /Applications, node, python3 y `vercel whoami` con sesión. Detalle en `herramientas/LEEME.md`.

## Reglas fijas (el detalle está en la memoria `feedback-*`)
- Montos: «U$S 450 M», «$ 182.000 M» (M con espacio duro; nunca «millones» ni «U$D»; moneda en cada valor).
- Todo texto nuevo usa la escala tipográfica existente; sobre foto/video, bloque transparente con borde de color y texto blanco.
- Una sección = una parada. Medios en su orientación nativa. Videos de contenido: mudos, en loop, sin salto (`-an`, fundir final→inicio, cortar `-t 9.98` los clips de IA).
- Probar con alto real de navegador (375×667, 360×700, 390×664) además de escritorio.
- No regenerar PDF/ZIP sin pedido. Si el usuario interrumpe una herramienta: parar y esperar.
