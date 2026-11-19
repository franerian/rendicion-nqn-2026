#!/bin/bash
# Exporta el PDF (una página por pantalla, con texto buscable, marcadores y enlaces a los videos) y/o el ZIP offline
# a partir de lo que está PUBLICADO (la carpeta armada por publicar.sh, con doctype, idéntica al sitio vivo).
# Uso: herramientas/exportar.sh VERSION [pdf|zip|todo]
#   VERSION  número del informe, p. ej. 122  → Rendicion-de-cuentas-2026-presentacion-v122.pdf y Presentacion-completa_122.zip (en la raíz del proyecto)
#   PRUEBA="37" herramientas/exportar.sh 0 pdf   → captura y arma solo esas pantallas, en la carpeta de trabajo (no copia nada a la raíz)
# No publica ni toca scroll/ ni el sitio. Tarda ≈ 8 min el PDF (no publicar mientras captura: publicar.sh rehace la carpeta que lee) y ≈ 1 min el ZIP.
# El ZIP necesita internet (baja la fuente Manrope). Después de armar el PDF: mirar las hojas de contacto (se dejan en la carpeta de trabajo).
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
TMP="${RENDICION_TMP:-${TMPDIR:-/tmp}/rendicion-nqn}"
STAGING="${RENDICION_STAGING:-$TMP/deploy}"
SITIO=https://rendicionnqn2026.vercel.app
TOTAL="$(sed -n 's/^TOTAL=\([0-9]*\).*/\1/p' "$AQUI/medir.sh")"
VER="$1"; QUE="${2:-todo}"
[ -z "$VER" ] && { sed -n '2,8p' "$0"; exit 2; }
WORK="$TMP/export/v$VER"; SHOTS="$WORK/shots"
mkdir -p "$SHOTS"

[ -f "$STAGING/index.html" ] || { echo "No hay carpeta armada en $STAGING: corré antes herramientas/publicar.sh (o --sin-deploy)."; exit 1; }
if ! curl -s --max-time 20 "$SITIO/?x=$$" | cmp -s - "$STAGING/index.html"; then
  echo "AVISO: la carpeta armada NO es idéntica al sitio vivo. Corré herramientas/publicar.sh --solo-vivo (o publicar) antes de exportar."
  [ -z "$PRUEBA" ] && exit 1
fi

pdf() {
  local PORT=$((8700 + RANDOM % 200))
  ( cd "$STAGING" && exec python3 -m http.server $PORT --bind 127.0.0.1 >/dev/null 2>&1 ) &
  local SRV=$!
  trap 'kill $SRV 2>/dev/null' RETURN
  for i in $(seq 1 40); do curl -s -o /dev/null --max-time 1 "http://127.0.0.1:$PORT/" && break; sleep 0.25; done
  export DSF=2 HIDE='.hint'
  local BASE="http://127.0.0.1:$PORT/" CAP="$AQUI/pdf/cdp-pdf-capture.mjs"
  date '+inicio %H:%M:%S'
  if [ -n "$PRUEBA" ]; then
    for n in $PRUEBA; do node "$CAP" "$SHOTS" 2160 1080 $n $n "$BASE"; done
  else
    echo "== #01 con el primer cuadro del video"
    SEEK0='.hero video' node "$CAP" "$SHOTS" 2160 1080 1 1 "$BASE"
    echo "== #02 a #$TOTAL (la parada del mapa de «Más conectividad», #32, con el video frenado en su primer cuadro = el mapa)"
    node "$CAP" "$SHOTS" 2160 1080 2 31 "$BASE"
    SEEK0='.hab.tl .hab-vid video' node "$CAP" "$SHOTS" 2160 1080 32 32 "$BASE"
    node "$CAP" "$SHOTS" 2160 1080 33 $TOTAL "$BASE"
  fi
  date '+fin %H:%M:%S'
  [ -z "$PRUEBA" ] && python3 -I "$AQUI/pdf/check_meta.py" "$SHOTS" "$TOTAL"
  local OUT="$WORK/final.pdf" ONLY=""
  [ -n "$PRUEBA" ] && ONLY="$(echo $PRUEBA | tr ' ' ',')"
  ONLY="$ONLY" IMG_W=4320 Q=82 python3 -I "$AQUI/pdf/build_pdf.py" "$SHOTS" "$OUT" "$STAGING/index.html" > "$WORK/build.log" 2>&1
  head -1 "$WORK/build.log"; sed -n '2,60p' "$WORK/build.log"
  pdfinfo "$OUT" | grep -E 'Pages|Page size|File size'
  pdftotext -layout "$OUT" "$WORK/all.txt"
  for pal in 'Avanzar' 'millon' 'U\$D'; do printf '  %-10s %s\n' "$pal" "$(grep -c -i -- "$pal" "$WORK/all.txt")"; done
  shasum -a 256 "$OUT" | cut -c1-16
  if [ -z "$PRUEBA" ]; then
    "$AQUI/pdf/hojas.sh" "$SHOTS" "$WORK" "$TOTAL" > /dev/null
    cp "$OUT" "$RAIZ/Rendicion-de-cuentas-2026-presentacion-v$VER.pdf"
    echo "PDF: $RAIZ/Rendicion-de-cuentas-2026-presentacion-v$VER.pdf   (hojas de contacto: $WORK/sheet-*.jpg)"
  else
    echo "PRUEBA: PDF en $OUT"
  fi
}

zip_() {
  rm -rf "$WORK/zip"; mkdir -p "$WORK/zip"
  python3 -I "$AQUI/armar_demo.py" "$WORK/zip" --completo > "$WORK/zip.log" 2>&1 || { tail -5 "$WORK/zip.log"; exit 1; }
  tail -1 "$WORK/zip.log"
  unzip -tq "$WORK/zip/Presentacion-completa.zip" | tail -1
  echo "enlaces externos en el HTML del ZIP (solo debe verse xmlns):"
  unzip -p "$WORK/zip/Presentacion-completa.zip" '*index.html' | grep -o 'https\?://[^"'"'"' )]*' | grep -v 'w3.org' | sort -u | head
  cp "$WORK/zip/Presentacion-completa.zip" "$RAIZ/Presentacion-completa_$VER.zip"
  echo "ZIP: $RAIZ/Presentacion-completa_$VER.zip"
}

case "$QUE" in
  pdf) pdf ;;
  zip) zip_ ;;
  todo) zip_; pdf ;;
  *) echo "uso: exportar.sh VERSION [pdf|zip|todo]"; exit 2 ;;
esac
