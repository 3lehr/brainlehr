#!/bin/sh
# Baut und testet die macOS-App unter app/ mit einer Swift-Werkzeugkette,
# die es tatsaechlich kann -- statt sich auf den blanken Namen `swift` im
# PATH zu verlassen.
#
# FALLE 1: Auf diesem Rechner liefert `command -v swift` das swiftly-Swift
# 4.2.4 (x86_64). Dessen Paketmanager kennt das Format "swift-tools-version:
# 5.10" nicht und bricht mit "The version specifier ' 5.10' ... is not
# valid" ab, noch bevor eine Zeile Code kompiliert. `/usr/bin/xcrun swift`
# ist auf demselben Rechner Swift 6.2.4 und baut sofort durch. Ein Agent, der
# nur `swift build` tippt, und ein Mensch, der xcrun nimmt, sehen zwei
# verschiedene Ergebnisse vom selben Code -- gesucht wird darum nach der
# FAEHIGKEIT (baut das Paket ueberhaupt?), nicht nach einem festen Pfad.
#
# FALLE 2: `swift test` schliesst mit zwei Zusammenfassungen -- zuerst der
# XCTest-Laeufer ("Executed 12 tests, with 0 failures"), danach der neuere
# swift-testing-Laeufer, der hier keine Faelle hat ("Test run with 0 tests
# in 0 suites passed"). Wer nur die letzte Zeile (tail) liest, haelt einen
# Lauf ohne einen einzigen Fall fuer bestanden. Dieses Skript zaehlt darum
# die XCTest-Faelle selbst nach und laesst einen Lauf mit 0 Faellen
# durchfallen, gleich was die Schlusszeile sagt.

set -eu

HIER=$(cd "$(dirname "$0")" && pwd)

SWIFT=""
for kandidat in \
	"xcrun swift" \
	/Applications/Xcode.app/Contents/Developer/usr/bin/swift \
	swift
do
	# shellcheck disable=SC2086
	if command -v ${kandidat%% *} >/dev/null 2>&1; then
		if $kandidat package --package-path "$HIER" tools-version >/dev/null 2>&1; then
			SWIFT="$kandidat"
			break
		fi
	fi
done

if [ -z "$SWIFT" ]; then
	echo "Auf diesem Rechner fehlt eine Swift-Werkzeugkette, die dieses Paket bauen kann. Abhilfe: aktuelles Xcode installieren (liefert die noetige Swift-Version ueber 'xcrun swift'), danach erneut versuchen." >&2
	exit 1
fi

echo "Werkzeugkette: $SWIFT ($($SWIFT --version 2>&1 | head -1))"

echo "-- swift build --"
$SWIFT build --package-path "$HIER"

echo "-- swift test --"
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT
if $SWIFT test --package-path "$HIER" >"$LOG" 2>&1; then
	lauf_ok=1
else
	lauf_ok=0
fi
cat "$LOG"

# Die massgebliche Zeile ist die Gesamtzusammenfassung der XCTest-Suite
# "All tests", NICHT die letzte Zeile der Ausgabe (die gehoert dem
# swift-testing-Laeufer und redet ueber dessen eigene, hier leere Menge).
zeile=$(grep -A1 "Test Suite 'All tests'" "$LOG" | tail -1)
faelle=$(printf '%s' "$zeile" | sed -n 's/.*Executed \([0-9]*\) tests.*/\1/p')

if [ -z "$faelle" ] || [ "$faelle" -eq 0 ]; then
	echo "NICHT BESTANDEN: kein XCTest-Fall ausgefuehrt (gefundene Zusammenfassung: '${zeile:-keine}')." >&2
	exit 1
fi

if [ "$lauf_ok" -ne 1 ]; then
	echo "NICHT BESTANDEN: $faelle Faelle ausgefuehrt, mindestens einer schlug fehl." >&2
	exit 1
fi

echo "BESTANDEN: $faelle XCTest-Faelle, 0 Fehlschlaege."

# -- Anwendungsbuendel --
# Ein echtes atelier.app statt der blanken Binaerdatei, die `swift build`
# liefert: Contents/MacOS + Contents/Resources + Info.plist + Symbol,
# ad-hoc signiert. Ort bewusst NICHT der Schreibtisch (app/Ausgabe/,
# repo-lokal und in app/.gitignore ausgeschlossen) -- dorthin wird nur auf
# ausdruecklichen Wunsch kopiert.

REPO_WURZEL=$(cd "$HIER/.." && pwd)
FASSUNG=$(cat "$REPO_WURZEL/VERSION" 2>/dev/null || echo "0.0.0")
BAUNUMMER=$(cd "$REPO_WURZEL" && git rev-list --count HEAD 2>/dev/null || echo "0")

BUENDEL="$HIER/Ausgabe/atelier.app"
rm -rf "$BUENDEL"
mkdir -p "$BUENDEL/Contents/MacOS" "$BUENDEL/Contents/Resources"

cp "$HIER/.build/debug/Atelier" "$BUENDEL/Contents/MacOS/atelier"

sed -e "s/__FASSUNG__/$FASSUNG/" -e "s/__BAUNUMMER__/$BAUNUMMER/" \
	"$HIER/Resources/Info.plist" > "$BUENDEL/Contents/Info.plist"

echo "-- Symbol erzeugen --"
ICONSET="$HIER/Ausgabe/.AppIcon.iconset"
rm -rf "$ICONSET"
$SWIFT "$HIER/Resources/erzeuge_icon.swift" "$ICONSET"
iconutil -c icns "$ICONSET" -o "$BUENDEL/Contents/Resources/AppIcon.icns"
rm -rf "$ICONSET"

echo "-- Ad-hoc-Signatur --"
codesign --force --deep --sign - "$BUENDEL"

echo "BUENDEL: $BUENDEL (Fassung $FASSUNG, Bau $BAUNUMMER)"
