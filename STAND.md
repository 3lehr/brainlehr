# STAND brainlehr — 2026-08-14T07:40:00+0200

**Wartet auf dich:** Sitzung neu starten (die laufenden MCP-Prozesse sind aelter als die Fixes und schreiben weiter keine Vektoren) · Push · #105 Repo-Trennung · #29 Schnitt oeffentliches Repo · #101 App zeigt nur Freigegebenes · **neu: die 1680 Zeitstempel** (siehe unten).

**Der Befund, der eine Entscheidung braucht** (`5415321b`): Der DB-Vorgabewert stempelt `strftime('...+01:00','now','localtime')` — Ortszeit als Wert, fester `+01:00` als Offset. In der Sommerzeit ist das als absolute Zeit **eine Stunde falsch**. Gemessen: 1680 Knoten `+01:00`, 510 Knoten `+02:00` — zwei Erzeuger in derselben Spalte. Eine Korrektur des Bestands waere eine Schaetzung (aus dem String allein ist CET/CEST nicht ablesbar), keine Rechnung.

**Erledigt seit gestern Abend:** 80 Vektor-Identitaet · 86 Metaphern (Nullergebnis) · 91 Rollensperre erreichbar gemacht · 69 Abschneidegrenze · 88 Schritt 1 Zeitfenster im Abruf (`5d777e6`) · beide Defekte der Eilmeldung: Widerruf archiviert statt zu loeschen, Einspielung von 20 KB auf 8 KB mit ehrlicher Restzahl (`5934067`) · 110 Hauptdefekt (`f4fe41f`).

**110 auseinandergezogen** — die 19 waren zu grob: 6 nur Kommentare · 3 Zeitzone (oben) · 2 Trigger (der INSTALLIERTE ist strenger, ihm fehlt die Ausnahme fuer `anlass='betreiber'`) · 2 fehlende Spalten (behoben) · 7 nur installiert (`lost_and_found`, `mycel_*`, 3 Trigger) — noch offen.

**Suite:** 1412 passed, 1 skipped, 11 xfailed, kein roter Test. 110 Aufgaben: 85 erledigt, 10 angefangen, 15 offen.

**Fallen:** ein Test, der sein Schema selbst baut, kann keine Schemaluecke finden (`raum_daten._selftest`) · eine Vorrichtung kleiner als die Kappungsgrenze kann keinen Kappungsfehler sehen · ein Zeitstempel ist eine Angabe, kein Schluessel · zsh zerlegt unquotierte Variablen nicht (`L-103548`) · Melder an `UserPromptSubmit` sind im Selbstlauf blind (`L-1228cf`).
