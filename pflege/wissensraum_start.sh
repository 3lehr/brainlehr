#!/bin/sh
# Startet die Entscheidungsoberflaeche (berichte/entscheidungen_server.py),
# falls sie nicht schon laeuft, und gibt ihre URL aus.
#
# BEFUND, der diese Suche noetig macht: entscheidungen_server.py importiert
# ueber kern/knowledge_lint.py -> kern/ankerverfahren.py das Paket
# "cryptography". Apples Systempython (/usr/bin/python3) hat es nicht --
# derselbe Fallenkreis wie bei pflege/ausweis_start.sh (scrypt), nur ein
# anderes fehlendes Paket. Unter `do shell script` schrumpft PATH auf
# /usr/bin:/bin, darum wird hier wie dort nach der FAEHIGKEIT gesucht,
# nicht nach einem festen Pfad.
#
# Aufruf: wissensraum_start.sh [PORT]   (Vorgabe 8799, kein Geheimnis noetig)
# Der optionale Port ist nur fuer Tests gedacht (eigener Port statt des
# echten 8799) -- ohne Argument unveraendertes Verhalten.

set -eu

HIER=$(cd "$(dirname "$0")" && pwd)
WURZEL=$(cd "$HIER/.." && pwd)
SERVER="$WURZEL/berichte/entscheidungen_server.py"
PORT="${1:-8799}"
URL="http://127.0.0.1:$PORT/"

# Laeuft schon jemand auf dem Port -- egal wer, dann ist nichts zu tun.
if /usr/bin/curl -s -o /dev/null -m 1 "$URL"; then
	echo "$URL"
	exit 0
fi

PYTHON=""
for kandidat in \
	/opt/homebrew/bin/python3 \
	/usr/local/bin/python3 \
	/usr/bin/python3 \
	python3
do
	pfad=$(command -v "$kandidat" 2>/dev/null) || continue
	[ -x "$pfad" ] || continue
	if "$pfad" -c 'import cryptography' 2>/dev/null; then
		PYTHON="$pfad"
		break
	fi
done

if [ -z "$PYTHON" ]; then
	echo "Auf diesem Rechner fehlt ein Python mit den noetigen Paketen fuer den Wissensraum. Abhilfe: Projekt-Python installieren (siehe requirements.txt), danach erneut versuchen." >&2
	exit 1
fi

nohup "$PYTHON" "$SERVER" --port "$PORT" >/tmp/brainlehr-wissensraum.log 2>&1 &
disown

# Kurz warten, bis der Server antwortet -- hoechstens 5 Sekunden.
i=0
while [ "$i" -lt 25 ]; do
	if /usr/bin/curl -s -o /dev/null -m 1 "$URL"; then
		echo "$URL"
		exit 0
	fi
	i=$((i + 1))
	/bin/sleep 0.2
done

echo "Der Wissensraum-Server startet, antwortet aber noch nicht. Bitte gleich noch einmal versuchen." >&2
exit 1
