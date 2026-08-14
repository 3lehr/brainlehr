# STAND brainlehr — 2026-08-14T09:15:00+0200

**EINE SACHE BLOCKIERT ALLES ANDERE: Sitzungen neu starten.** Die laufenden MCP-Prozesse tragen den Code von 21:44 im Speicher. Sie schreiben (a) keine Vektoren, (b) weiter Ortszeit statt UTC. Belegt: der juengste Knoten traegt `+02:00`, waehrend `access_log` schon `Z` bekommt — dessen Vorgabewert sitzt in der Datenbank, nicht im Prozess. **Solange sie laufen, ist Aufgabe 111 Schritt 3 gesperrt** (Umrechnen wuerde sofort wieder mischen).

**UTC (111), dein Beschluss von heute — und er war schon vom 2026-08-06** (`8ea7b6c`, „innen UTC, aussen Ortszeit"). Er hielt acht Tage nicht, weil 104 Stellen in 74 Dateien ihren Zeitstempel selbst bauten. Jetzt: eine Quelle (`kern/zeitmarke.jetzt`), zwei Ratschen (Daten und Code), 46 Erzeuger umgestellt, Spalten-Vorgabewerte der DB migriert. Schritt 3 (38 000 Werte) ist geprueft und wartet auf den Neustart.

**Drei Fehler, die erst dadurch sichtbar wurden:** mein Tabellenneubau loeschte 52 von 96 Schemaobjekten (`DROP TABLE` nimmt Indizes und Trigger mit) — gefunden vom Schemamelder, wiederhergestellt aus einer Dateikopie, Skript repariert · `_REPEAT_MARKER_RE` kannte kein `Z`, die Deckelung von Wiederholungen lief still ins Leere · meine eigene Ratsche uebersah vier `now_iso()`-Klone, weil `isoformat(BERLIN)` weder `%z` noch fester Versatz ist — gefunden von einem Test mit **anderem** Massstab.

**Ausserdem erledigt:** 110 (Erstinstallation brach an `lessons_learned.pruefstelle`) · 88 Schritt 1 (Zeitfenster im Abruf) · beide Defekte der Eilmeldung (Widerruf archiviert; Einspielung 20 KB auf 8 KB mit ehrlicher Restzahl).

**Suite:** 1435 passed. Rot: `test_zeitform_utc` (bis Schritt 3, gewollt) · `kandidatendiagnose`, `sicherung_s12`, `vektorlage` (Bestandsdrift der Parallelsitzung, vorbestehend).

**Wartet sonst auf dich:** Push · #105 Repo-Trennung · #29 oeffentliches Repo · #101 App zeigt nur Freigegebenes · #20 Ausweisordner.
