#!/usr/bin/env bash
# Plate-solve a frame from the main camera (AT72EDII + ASI1600: 1.82"/px).
# Prints the field centre, size and rotation; writes FILE.wcs beside it.
#   solve.sh FRAME.fits [RA_DEG DEC_DEG]     a position hint is optional
set -euo pipefail
f=${1:?frame to solve}
hint=()
[ $# -ge 3 ] && hint=(--ra "$2" --dec "$3" --radius 10)
solve-field --overwrite --no-plots --downsample 4 \
  --scale-units arcsecperpix --scale-low "${SCALE_LOW:-1.6}" --scale-high "${SCALE_HIGH:-2.0}" \
  --cpulimit 120 --new-fits none --rdls none --match none --corr none \
  --index-xyls none --axy none --solved none --wcs "${f%.*}.wcs" \
  "${hint[@]}" "$f" 2>&1 | grep -E "^Field (center|size|rotation|parity)|Did not solve|pixel scale" || {
    echo "no solution for $f" >&2; exit 1; }
