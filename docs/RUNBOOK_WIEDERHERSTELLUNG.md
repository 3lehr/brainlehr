# Wiederherstellung — wenn die Wissensdatenbank kaputt ist

Gilt für: `shared-knowledge/knowledge.db`.

Kein git nötig, keine Python-Kenntnisse nötig. Nur die Befehle unten, in
dieser Reihenfolge.

## Womit NICHT anfangen

**Nie zuerst die Live-Datenbank überschreiben.** Erst prüfen, welche
Sicherung überhaupt etwas taugt — danach erst zurückspielen. Das Werkzeug
verweigert von sich aus, wenn `--ziel` auf `knowledge.db` zeigt.

## Schritt 1: Welche Sicherungen taugen etwas?

Terminal öffnen, dann:

```
cd /Volumes/daten/Begod2026/hub/shared-knowledge
python3 pflege/wiederherstellung.py pruefe --alle
```

Das listet jede vorhandene Sicherung mit einem Urteil:

- **brauchbar** — vollständig, kann zurückgespielt werden.
- **veraltetes Schema** — älter als der heutige Aufbau (fehlende Spalten
  werden genannt). Kann trotzdem zurückgespielt werden — nur eben mit dem
  Stand von damals, nicht mit den neuesten Feldern.
- **beschädigt** — nicht verwendbar. Nächste Sicherung in der Liste probieren.

Dazu je Sicherung: Anzahl Einträge und der Zeitraum, den sie abdeckt — damit
erkennbar ist, wie viel Verlust ein Rückspielen bedeutet.

Nur eine bestimmte Sicherung prüfen (Dateiname aus der Liste):

```
python3 pflege/wiederherstellung.py pruefe knowledge.db.bak-20260805T230122
```

## Schritt 2: Sicherung zurückspielen

**Niemals ohne `--ziel`, und `--ziel` niemals `knowledge.db`.** Erst an
einen ANDEREN Ort zurückspielen, dort prüfen, danach von Hand entscheiden,
ob die Live-Datenbank ersetzt wird.

```
python3 pflege/wiederherstellung.py stelle_her knowledge.db.bak-20260805T230122 --ziel /tmp/wiederhergestellt.db
```

Ausgabe zeigt `stimmt ueberein: True` oder `False`. Bei `False` stehen die
Abweichungen einzeln darunter — dann diese Sicherung nicht weiterverwenden,
sondern eine andere aus Schritt 1 probieren.

Ein Versuch mit `--ziel knowledge.db` bricht sofort ab, ohne irgendetwas
anzufassen — das ist Absicht, keine Fehlfunktion.

## Schritt 3: Live-Datenbank ersetzen (von Hand, nicht durch das Werkzeug)

Erst wenn Schritt 2 `stimmt ueberein: True` zeigt UND klar ist, dass der
abgedeckte Zeitraum aus Schritt 1 akzeptabel ist:

```
cd /Volumes/daten/Begod2026/hub/shared-knowledge
cp knowledge.db knowledge.db.vor-wiederherstellung-$(date +%Y%m%dT%H%M%S)
cp /tmp/wiederhergestellt.db knowledge.db
rm -f knowledge.db-shm knowledge.db-wal
```

Die erste Zeile sichert den kaputten Stand, falls sich die Entscheidung als
falsch herausstellt. Die letzte Zeile entfernt Reste der alten
Journal-Dateien, damit die neue `knowledge.db` sauber startet.

## Was diese Prüfung NICHT beweist

„Brauchbar" heißt: die Datei lässt sich lesen und hat alle Tabellen und
Spalten, die der heutige Aufbau erwartet. Es heißt NICHT, dass jeder
einzelne Eintrag inhaltlich richtig ist — nur, dass die Sicherung
strukturell vollständig ist.
