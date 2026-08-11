#!/bin/sh
# Startet den Ausweis-Helfer mit einem Python, das scrypt beherrscht.
#
# BEFUND, der dieses Skript veranlasst hat (2026-08-11): Apples System-Python
# unter /usr/bin/python3 (3.9.6) hat KEIN hashlib.scrypt -- es ist gegen ein
# OpenSSL ohne scrypt gebaut. kern/ausweis.py leitet damit seine Pruefsummen
# ab und stuerzt dort mit AttributeError ab, bevor auch nur eine Zeile Ausgabe
# entsteht. Die Ausweisstelle.app haette also gar nicht funktioniert.
#
# Die Tests hatten das NICHT gefangen: sie liefen unter sys.executable, also
# unter dem Projekt-Python 3.14 -- die App dagegen unter `do shell script`,
# wo der PATH auf /usr/bin:/bin zusammenschrumpft und /usr/bin/python3 der
# einzige Treffer ist. Gruen im Kopflauf, tot im Feld.
#
# WARUM SUCHEN STATT FESTSCHREIBEN: Ein fester Pfad wie /opt/homebrew/bin/
# python3 ist auf einem Intel-Mac falsch (/usr/local/bin), nach einem
# Python-Wechsel veraltet und auf einem fremden Rechner gar nicht vorhanden.
# Gesucht wird nach der FAEHIGKEIT, nicht nach dem Ort -- dieselbe Regel wie
# beim Auffinden der Repo-Wurzel an schema.sql statt an einer Ebenenzahl.
#
# Aufruf:  echo -n "<geheimnis>" | ausweis_start.sh <befehl> [argumente...]

set -eu

HIER=$(cd "$(dirname "$0")" && pwd)
HELFER="$HIER/ausweis_helfer.py"

for kandidat in \
	/opt/homebrew/bin/python3 \
	/usr/local/bin/python3 \
	/usr/bin/python3 \
	python3
do
	pfad=$(command -v "$kandidat" 2>/dev/null) || continue
	[ -x "$pfad" ] || continue
	if "$pfad" -c 'import hashlib,sys; sys.exit(0 if hasattr(hashlib,"scrypt") else 1)' 2>/dev/null; then
		exec "$pfad" "$HELFER" "$@"
	fi
done

# Kein tauglicher Interpreter. Als JSON melden, damit die Oberflaeche denselben
# Weg nimmt wie bei jedem anderen Fehler -- und mit einem Satz, der sagt, was
# zu tun ist, statt die Ursache zu nennen.
cat <<'ENDE'
{"fehler": "Auf diesem Rechner fehlt ein Python, das die noetige Verschluesselung beherrscht. Abhilfe: Python 3.10 oder neuer installieren (z. B. ueber Homebrew), danach die App erneut starten."}
ENDE
exit 1
