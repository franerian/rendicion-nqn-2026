#!/bin/bash
# Mide con Chrome sin cabeza si las cifras (y el resto) entran en su tarjeta, en varios tamaños de ventana.
# Uso: herramientas/medir.sh [rapido|completo] [--pantallas "6-7 13-15 20"] [--todas] [--tamanos "1440x900 375x667"] [--base URL] [--armar]
#   rapido (por defecto)  3 tamaños: 1440×900, 2160×1080 y 375×667.
#   completo              11 tamaños, de 2160×1080 a 320×640: usarlo si cambió el CSS o antes de presentar.
#   --pantallas           rangos «desde-hasta» separados por espacios (por defecto, las 17 pantallas con montos).
#   --todas               las pantallas de la 1 a la TOTAL y deja el mapa número → nombre (mapa.txt) en la salida.
#   --tamanos             lista de tamaños propia (reemplaza a rapido/completo).
#   --base URL            mide otra página (p. ej. el sitio vivo) en vez de armar y servir la carpeta local.
#   --armar               fuerza armar la carpeta aunque parezca al día.
# Muestra solo los problemas nuevos (los avisos conocidos se descartan: ver lib/resumir.py).
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
SRC="$RAIZ/scroll"
TMP="${RENDICION_TMP:-${TMPDIR:-/tmp}/rendicion-nqn}"
STAGING="${RENDICION_STAGING:-$TMP/deploy}"
SITIO=https://rendicionnqn2026.vercel.app
TOTAL=48  # cantidad de pantallas: actualizar si se agregan o se sacan
MODO=rapido
RANGOS="6-7 13-18 36-37 40-46"
TAMANOS=""
BASE=""
ARMAR=0
TODAS=0
while [ $# -gt 0 ]; do
  case "$1" in
    rapido|completo) MODO="$1" ;;
    --pantallas) RANGOS="$2"; shift ;;
    --todas) TODAS=1 ;;
    --tamanos) TAMANOS="$2"; shift ;;
    --base) BASE="$2"; shift ;;
    --armar) ARMAR=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "opción desconocida: $1"; exit 2 ;;
  esac
  shift
done
if [ "$TODAS" = 1 ]; then RANGOS="1-8 9-16 17-24 25-32 33-40 41-$TOTAL"; fi
if [ -z "$TAMANOS" ]; then
  if [ "$MODO" = completo ]; then
    TAMANOS="1440x900 2160x1080 1920x1080 1366x768 1280x720 1100x800 1024x768 390x844 375x667 360x700 320x640"
  else
    TAMANOS="1440x900 2160x1080 375x667"
  fi
fi
mkdir -p "$TMP"
SERVER_PID=""
if [ -z "$BASE" ]; then
  if [ "$ARMAR" = 1 ] || [ ! -f "$STAGING/index.html" ] || [ "$SRC/informe-scroll.html" -nt "$STAGING/index.html" ]; then
    echo "Armando la carpeta local…"
    python3 -I "$AQUI/lib/build_deploy.py" "$SRC" "$STAGING" "$SITIO" > "$TMP/armado.log" 2>&1 || { cat "$TMP/armado.log"; exit 1; }
  fi
  PUERTO="$(python3 -I -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')"
  python3 -I "$AQUI/lib/rangeserver.py" "$PUERTO" "$STAGING" > "$TMP/servidor.log" 2>&1 &
  SERVER_PID=$!
  trap '[ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null' EXIT
  BASE="http://localhost:$PUERTO/index.html"
  for i in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null "$BASE" && break; sleep 0.5; done
fi
OUT="$TMP/medidas/$(date +%H%M%S)"
mkdir -p "$OUT"
EVAL_JS="$(cat "$AQUI/lib/eval-cifras.js")"
MALAS=0
PRIMERO=""
echo "Midiendo en $BASE"
echo "Tamaños: $TAMANOS | Pantallas: $RANGOS"
for sz in $TAMANOS; do
  W="${sz%x*}"
  H="${sz#*x}"
  D="$OUT/$sz"
  mkdir -p "$D"
  [ -z "$PRIMERO" ] && PRIMERO="$D"
  PIDS=()
  for r in $RANGOS; do
    a="${r%%-*}"
    b="${r##*-}"
    EVAL="$EVAL_JS" node "$AQUI/lib/cdp-capture.mjs" "$D/r$a" "$W" "$H" "$a" "$b" "$BASE" > "$D/r$a.log" 2>&1 &
    PIDS+=($!)
  done
  wait "${PIDS[@]}"
  python3 -I "$AQUI/lib/resumir.py" "$D" || MALAS=$((MALAS+1))
done
if [ "$TODAS" = 1 ] && [ -n "$PRIMERO" ]; then
  python3 -I "$AQUI/lib/resumir.py" --mapa "$PRIMERO" > "$OUT/mapa.txt"
  echo "mapa número → nombre: $OUT/mapa.txt"
fi
echo
if [ "$MALAS" = 0 ]; then
  echo "TODO LIMPIO en $(echo $TAMANOS | wc -w | tr -d ' ') tamaños (${SECONDS} s). Capturas y registros: $OUT"
else
  echo "HAY PROBLEMAS en $MALAS tamaños (arriba). Capturas y registros: $OUT"
fi
[ "$MALAS" = 0 ]
