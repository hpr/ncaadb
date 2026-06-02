#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

SVG="public/favicon.svg"
DST="public"

magick convert -background none "$SVG" -resize 32x32 "$DST/favicon.ico"
magick convert -background none "$SVG" -resize 180x180 "$DST/apple-touch-icon.png"
magick convert -background none "$SVG" -resize 32x32 "$DST/favicon-32x32.png"
magick convert -background none "$SVG" -resize 16x16 "$DST/favicon-16x16.png"

echo "Generated favicons from $SVG"
