# Herramientas del informe scroll

Dos comandos reemplazan la tanda de pasos que antes se hacía a mano (armar, publicar, comparar, calentar el CDN, verificar, medir).

```bash
herramientas/publicar.sh                       # arma, revisa, publica, compara el HTML vivo, calienta el CDN y verifica
herramientas/publicar.sh --pantallas "20 36"   # además mide esas pantallas en el sitio vivo
herramientas/publicar.sh --sin-deploy          # solo arma y revisa el HTML
herramientas/publicar.sh --solo-vivo           # solo compara, calienta y verifica el sitio que ya está publicado

herramientas/medir.sh                          # rápido: 3 tamaños (1440×900, 2160×1080, 375×667) en las pantallas con montos
herramientas/medir.sh --pantallas "35-36 44"   # otras pantallas (rangos «desde-hasta»)
herramientas/medir.sh completo                 # 11 tamaños, de 2160×1080 a 320×640 (si cambió el CSS o antes de presentar)
herramientas/medir.sh --todas --tamanos 1440x900   # las 46 pantallas en un tamaño y deja mapa.txt (número → nombre)
```

Cada uno termina con **TODO OK** / **TODO LIMPIO** o con la lista de lo que hay que mirar. Los avisos que ya se sabe que no son errores se descartan solos (`lib/resumir.py`).

- Necesitan: Chrome en `/Applications`, `node`, `python3` y la CLI de Vercel con sesión (`vercel whoami`).
- La carpeta que se sube y los registros se arman en `$TMPDIR/rendicion-nqn/` (se rehacen solos; cambiar con `RENDICION_TMP` o `RENDICION_STAGING`).
- Las reglas de texto que se revisan antes de publicar están al principio de `lib/revisar_html.py` (hoy: cifras de millones con «M» y sin ceros, nunca «millones», dólares «U$S»).
- Cantidad de pantallas: variable `TOTAL` al principio de `medir.sh` (hoy 48).
- `lib/` guarda las piezas: `build_deploy.py` (arma la carpeta con los medios que el HTML referencia), `verify_deploy.py`, `cdp-capture.mjs` (captura por pantalla), `cdp-netprofile.mjs` (carga en frío), `rangeserver.py`, `eval-cifras.js`, `revisar_html.py`, `parse_deploy.py`, `resumir.py`.

**Exportar (PDF y ZIP)**: `herramientas/exportar.sh NNN [pdf|zip|todo]` toma lo publicado (la carpeta armada, que debe ser idéntica al sitio vivo), captura las 46 pantallas con Chrome (≈ 8 min), arma `Rendicion-de-cuentas-2026-presentacion-vNNN.pdf` y/o `Presentacion-completa_NNN.zip` en la raíz y deja hojas de contacto en `$TMP/export/vNNN/`. `PRUEBA="37" herramientas/exportar.sh 0 pdf` prueba una sola pantalla sin tocar la raíz. Piezas en `pdf/` (`cdp-pdf-capture.mjs`, `build_pdf.py`: ojo, `TITLE_ONLY` guarda los títulos de marcadores de las pantallas 45 y 46; `check_meta.py`, `hojas.sh`). `MAPA-HTML.md` = líneas del HTML por sección (se rehace con `lib/mapa_html.py`).
