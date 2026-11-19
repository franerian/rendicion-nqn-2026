#!/bin/bash
# Publica el informe en Vercel y lo deja verificado, todo en UNA llamada (unos 2 a 3 minutos).
# Uso: herramientas/publicar.sh [--sin-deploy] [--solo-vivo] [--pantallas "20 36"] [--forzar]
#   (sin opciones)        arma la carpeta, revisa el HTML, publica en producción, compara el HTML vivo,
#                         calienta el CDN (carga en frío + HEAD de todos los archivos) y verifica.
#   --sin-deploy          solo arma y revisa el HTML (no publica).
#   --solo-vivo           no arma ni publica: compara el sitio vivo con la última carpeta armada,
#                         calienta el CDN y verifica.
#   --pantallas "20 36"   además mide esas pantallas en el sitio vivo (1440×900).
#   --forzar              sigue aunque la revisión del HTML marque algo.
# Si termina con «TODO OK» se puede avisar al usuario.
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
SRC="$RAIZ/scroll"
TMP="${RENDICION_TMP:-${TMPDIR:-/tmp}/rendicion-nqn}"
STAGING="${RENDICION_STAGING:-$TMP/deploy}"
LOGS="$TMP/logs"
SITIO=https://rendicionnqn2026.vercel.app
PROYECTO=rendicionnqn2026
EQUIPO=franerians-projects
SIN_DEPLOY=0
SOLO_VIVO=0
PANTALLAS=""
FORZAR=0
while [ $# -gt 0 ]; do
  case "$1" in
    --sin-deploy) SIN_DEPLOY=1 ;;
    --solo-vivo) SOLO_VIVO=1 ;;
    --pantallas) PANTALLAS="$2"; shift ;;
    --forzar) FORZAR=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "opción desconocida: $1"; exit 2 ;;
  esac
  shift
done
mkdir -p "$LOGS" "$(dirname "$STAGING")"
FALLAS=0
VERCEL_BIN="${VERCEL_BIN:-vercel}"   # (para probar el script sin publicar: un «vercel» simulado)
paso() { echo; echo "== $1  (${SECONDS} s)"; }

if [ "$SOLO_VIVO" = 0 ]; then
  paso "1. Armar la carpeta y revisar el HTML"
  python3 -I "$AQUI/lib/build_deploy.py" "$SRC" "$STAGING" "$SITIO" > "$LOGS/armado.log" 2>&1 || { cat "$LOGS/armado.log"; exit 1; }
  head -2 "$LOGS/armado.log"
  if ! python3 -I "$AQUI/lib/revisar_html.py" "$STAGING/index.html"; then
    if [ "$FORZAR" = 1 ]; then echo "(--forzar: sigo igual)"; else echo "ABORTADO: corregí lo marcado arriba (o usá --forzar)."; exit 1; fi
  fi
  if [ "$SIN_DEPLOY" = 1 ]; then echo; echo "No se publicó (--sin-deploy). Carpeta lista en $STAGING"; exit 0; fi

  paso "2. Publicar en producción"
  cd "$STAGING" || exit 1
  if [ ! -f .vercel/project.json ]; then
    "$VERCEL_BIN" link --yes --project "$PROYECTO" --scope "$EQUIPO" > "$LOGS/link.log" 2>&1 || { cat "$LOGS/link.log"; exit 1; }
  fi
  LOG="$LOGS/deploy-$(date +%Y%m%d-%H%M%S).log"
  "$VERCEL_BIN" deploy --prod --yes --scope "$EQUIPO" > "$LOG" 2>&1
  if ! python3 -I "$AQUI/lib/parse_deploy.py" "$LOG"; then tail -25 "$LOG"; exit 1; fi
  cd "$RAIZ" || exit 1
elif [ ! -f "$STAGING/index.html" ]; then
  echo "No hay carpeta armada en $STAGING: corré sin --solo-vivo."; exit 1
fi

paso "3. Comparar el HTML vivo con el armado"
IGUAL=0
for i in 1 2 3 4; do
  curl -s "$SITIO/?cb=$(date +%s)$i" -o "$LOGS/vivo-index.html"
  if cmp -s "$LOGS/vivo-index.html" "$STAGING/index.html"; then IGUAL=1; break; fi
  sleep 5
done
if [ "$IGUAL" = 1 ]; then
  echo "OK: el HTML servido es idéntico al armado ($(wc -c < "$STAGING/index.html" | tr -d ' ') bytes)"
else
  echo "ATENCIÓN: el HTML vivo es distinto del armado"; FALLAS=$((FALLAS+1))
fi

paso "4. Calentar el CDN y verificar los archivos"
PERFIL="$(mktemp -d "$TMP/perfil.XXXXXX")"
node "$AQUI/lib/cdp-netprofile.mjs" "$PERFIL" "$SITIO/" 1440 900 12 > "$LOGS/netprofile.log" 2>&1
sed -n '2p;4p' "$LOGS/netprofile.log" | cut -c1-150
ERRORES="$(grep -E '\| *[45][0-9][0-9] *\|' "$LOGS/netprofile.log" | grep -vc favicon)"
echo "pedidos con error (sin contar favicon.ico): $ERRORES"
if [ "$ERRORES" != 0 ]; then FALLAS=$((FALLAS+1)); fi
rm -rf "$PERFIL"
python3 -I "$AQUI/lib/verify_deploy.py" "$SITIO" "$STAGING" > "$LOGS/verify.log" 2>&1
grep -E 'archivos revisados|^  MAL' "$LOGS/verify.log"
echo "  (vercel.json y .gitignore no se sirven: un «MAL» en ellos es lo esperado)"
MAL="$(grep -E '^  MAL' "$LOGS/verify.log" | grep -vc -E 'vercel\.json|\.gitignore')"
if [ "$MAL" != 0 ]; then echo "ATENCIÓN: hay archivos con problema aparte de vercel.json y .gitignore (que no se sirven)"; FALLAS=$((FALLAS+1)); fi

if [ -n "$PANTALLAS" ]; then
  paso "5. Medir pantallas del sitio vivo (1440×900)"
  rm -rf "$LOGS/vivo"; mkdir -p "$LOGS/vivo"
  EVAL_JS="$(cat "$AQUI/lib/eval-cifras.js")"
  PIDS=()
  for n in $PANTALLAS; do
    EVAL="$EVAL_JS" node "$AQUI/lib/cdp-capture.mjs" "$LOGS/vivo/r$n" 1440 900 "$n" "$n" "$SITIO/" > "$LOGS/vivo/r$n.log" 2>&1 &
    PIDS+=($!)
  done
  wait "${PIDS[@]}"
  python3 -I "$AQUI/lib/resumir.py" "$LOGS/vivo" || FALLAS=$((FALLAS+1))
  echo "capturas en $LOGS/vivo/r<N>/sNN.png"
fi

echo
if [ "$FALLAS" = 0 ]; then
  echo "TODO OK (${SECONDS} s): el sitio vivo es lo que se armó y la caché está caliente."
else
  echo "HAY $FALLAS PUNTOS PARA REVISAR (arriba)."
fi
[ "$FALLAS" = 0 ]
