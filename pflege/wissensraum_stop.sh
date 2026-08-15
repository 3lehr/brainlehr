#!/bin/sh
# Gegenstueck zu wissensraum_start.sh -- beendet den Wissensraum-Dienst
# (berichte/entscheidungen_server.py), falls einer auf dem Port lauscht.
#
# Hausregel "kein Dauerlaeufer ohne Aufraeumen": wer den Dienst manuell
# startet (Weg 3, ADR-020 -- ein Klient darf ihn nicht selbst mitstarten,
# siehe ADR-020), bekommt hiermit das Beenden gleich mitgeliefert.
#
# Nutzt lsof statt einer eigenen PID-Datei -- wissensraum_start.sh legt
# keine an (nohup + disown). Beendet NUR, wenn der Prozess auf dem Port
# nachweislich entscheidungen_server.py ist -- nie einen fremden Belegten
# (ein Dienst, der wem anders gehoert, wird nicht abgeschossen).
#
# Aufruf: wissensraum_stop.sh [PORT]   (Vorgabe 8799, wie beim Start)

set -eu

PORT="${1:-8799}"

PIDS=$(/usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)

if [ -z "$PIDS" ]; then
	echo "Der Dienst laeuft nicht."
	exit 0
fi

BEENDET=0
for PID in $PIDS; do
	if ps -o command= -p "$PID" 2>/dev/null | grep -q entscheidungen_server.py; then
		kill "$PID" 2>/dev/null || true
		i=0
		while kill -0 "$PID" 2>/dev/null && [ "$i" -lt 30 ]; do
			i=$((i + 1))
			/bin/sleep 0.1
		done
		kill -9 "$PID" 2>/dev/null || true
		BEENDET=1
	fi
done

if [ "$BEENDET" -eq 1 ]; then
	echo "Der Dienst wurde beendet."
	exit 0
fi

echo "An dieser Stelle laeuft etwas anderes; nichts beendet."
exit 1
