#!/bin/bash
# Hojas de contacto 3×3 (cada vista de 720×360) de las capturas del PDF, para mirarlas de un vistazo.
# Uso: herramientas/pdf/hojas.sh <carpeta-capturas> <carpeta-salida> <total> [hojas…]   → sheet-1.jpg …
SH="$1"; OUT="$2"; TOTAL="$3"; shift 3
mkdir -p "$OUT/thumbs"
NH=$(( (TOTAL + 8) / 9 ))
for s in ${@:-$(seq 1 $NH)}; do
  from=$(( (s - 1) * 9 + 1 )); to=$(( s * 9 )); [ $to -gt $TOTAL ] && to=$TOTAL
  args=(); n=0
  for i in $(seq $from $to); do
    p=$(printf "%02d" $i)
    ffmpeg -loglevel error -y -i "$SH/s$p.png" -vf scale=720:360:flags=area -q:v 3 "$OUT/thumbs/t$p.jpg"
    args+=(-i "$OUT/thumbs/t$p.jpg"); n=$((n + 1))
  done
  lay=$(python3 -c "print('|'.join(f'{(i%3)*724}_{(i//3)*364}' for i in range($n)))")
  ffmpeg -loglevel error -y "${args[@]}" -filter_complex "xstack=inputs=$n:layout=$lay:fill=white" -frames:v 1 -update 1 -q:v 3 "$OUT/sheet-$s.jpg"
  echo "sheet-$s.jpg: #$from a #$to"
done
