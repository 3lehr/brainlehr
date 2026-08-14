#!/usr/bin/env bash
# Spike: PDF/A-3u + eingebettete factur-x.xml + PDF/UA-1 gleichzeitig.
# Baut, extrahiert die eingebettete XML zurueck (Byte-Vergleich), prueft
# pdfaid/pdfuaid in XMP und faehrt verapdf -f ua1 und -f 3u.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Bau (2x wg. Querverweisen) =="
lualatex -interaction=nonstopmode -halt-on-error rechnung.tex >/dev/null
lualatex -interaction=nonstopmode -halt-on-error rechnung.tex

echo
echo "== (a) Einbettung: Rueckholung + Byte-Vergleich =="
rm -rf extracted; mkdir extracted
pdfdetach -saveall -o extracted rechnung.pdf >/dev/null
if diff -q factur-x.xml extracted/factur-x.xml >/dev/null; then
  echo "BYTE-IDENTISCH: $(shasum -a 256 factur-x.xml | cut -d' ' -f1)"
else
  echo "UNTERSCHIED zwischen Original und rueckgeholter Datei"
fi

echo
echo "== (b) Kennzeichnung PDF/A und PDF/UA in XMP =="
python3 - <<'PY'
import re
data = open('rechnung.pdf','rb').read()
m = re.search(rb'<x:xmpmeta.*?</x:xmpmeta>', data, re.S)
xmp = m.group(0).decode('utf-8', 'replace') if m else ''
for tag in ('pdfaid:part', 'pdfaid:conformance', 'pdfuaid:part'):
    hit = re.search(re.escape(tag) + r'>([^<]*)<', xmp)
    print(f"{tag} = {hit.group(1) if hit else 'NICHT GEFUNDEN'}")
PY

echo
echo "== (c) verapdf -f ua1 =="
verapdf -f ua1 --format text rechnung.pdf | grep -v '^WARNING'

echo
echo "== (c') verapdf -f 3u (Kontrolle) =="
verapdf -f 3u --format text rechnung.pdf | grep -v '^WARNING'
