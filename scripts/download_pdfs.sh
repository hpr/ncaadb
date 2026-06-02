#!/bin/bash
cd "$(dirname "$0")/.."
BASE="https://trackandfieldnews.com/wp-content/uploads/2018/06"

mkdir -p pdfs/men
mkdir -p pdfs/women

# Men's PDFs
for f in ncaam100 ncaam200 ncaam400 ncaam800 ncaam1500 ncaam5000 ncaam10000 ncaamst ncaam110h ncaam400h ncaam220h ncaam4x1 ncaam4x4 ncaamhj ncaampv ncaamlj ncaamtj ncaamsp ncaamdt ncaamht ncaamjt ncaamdec; do
  curl -sL "$BASE/${f}.pdf" -o "pdfs/men/${f}.pdf" &
done

# Women's PDFs
for f in ncaaw100 ncaaw200 ncaaw400 ncaaw800 ncaaw1500 ncaaw5000 ncaaw10000 ncaawst ncaaw100h ncaaw400h ncaaw4x1 ncaaw4x4 ncaawhj ncaawpv ncaawlj ncaawtj ncaawsp ncaawdt ncaawht ncaawjt ncaaw3000 ncaawhept; do
  curl -sL "$BASE/${f}.pdf" -o "pdfs/women/${f}.pdf" &
done

wait
echo "Done downloading"
ls -la pdfs/men/ pdfs/women/
