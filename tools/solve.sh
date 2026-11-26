#!/usr/bin/env bash
# Plate-solve a frame from the main camera (AT72EDII + ASI1600: 1.82"/px).
# Prints the field centre, size and rotation; writes FILE.wcs beside it.
#   solve.sh FRAME.fits [RA_DEG DEC_DEG]     a position hint is optional
set -euo pipefail
f=${1:?frame to solve}
hint=()
[ $# -ge 3 ] && hint=(--ra "$2" --dec "$3" --radius 10)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# Everything solve-field writes goes to a scratch folder; only the WCS is kept.
solve-field --overwrite --no-plots --downsample 4 \
  --scale-units arcsecperpix --scale-low "${SCALE_LOW:-1.6}" --scale-high "${SCALE_HIGH:-2.0}" \
  --cpulimit 120 --dir "$tmp" --new-fits none --rdls none --match none --corr none \
  --index-xyls none "${hint[@]}" "$f" > "$tmp/log" 2>&1 || true
wcs=$(ls "$tmp"/*.wcs 2>/dev/null | head -1)
if [ -z "$wcs" ]; then
  echo "no solution for $f" >&2
  exit 1
fi
cp "$wcs" "${f%.*}.wcs"
grep -E "^Field (center|size|rotation|parity)" "$tmp/log"
