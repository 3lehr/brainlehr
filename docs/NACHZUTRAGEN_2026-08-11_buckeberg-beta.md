# Nachzutragen in den Wissensspeicher — 2026-08-11T14:50:00+0200

**Warum diese Datei existiert:** Der Eintrag unten sollte per `knowledge_add`
unter `/methodik/direktiven` abgelegt werden. Vier Versuche scheiterten mit
`database is locked`. Ein Python-Prozess (PID 25897, Laufzeit 2 h 21 min) hält
`knowledge.db` mit mehreren Schreib-Deskriptoren offen; `lsof` und ein
Schreibtest mit 3 s Zeitüberschreitung bestätigen die Sperre. Der
Sitzungsstart-Haken hatte bereits gewarnt, es liefen veraltete
`knowledge_mcp_server.py`-Prozesse. Der Inhalt liegt deshalb hier, damit er
nicht verloren geht — **nachzutragen, sobald die Sperre weg ist**, danach
diese Datei löschen.

---

**parent_path:** `/methodik/direktiven`
**title:** buckeberg ist aus dem Beta-Zustand heraus — Betreiberaussage 2026-08-11
**projects:** buckeberg, systemweit
**norm_entscheidung:** keine_norm — der Sache nach Hausnorm Rang 1, aber
`norm_rang` 1/2 verlangt einen namentlichen menschlichen Entscheider, und das
Feld ist über die Schnittstelle nicht setzbar. Die Schranke ist richtig: ein
Modell soll sich nicht selbst zur Quelle einer Hausnorm machen können.
Entschieden hat der Betreiber; Rang nachtragen, sobald das Feld beschreibbar ist.

**summary:** Der Betreiber hat buckeberg wörtlich als „schon aktiv eingesetzt"
bezeichnet und alle übrigen Apps als „noch im demo modus". Damit gilt die
systemweite Beta-Direktive für buckeberg nicht mehr.

**content:**

ANLASS: Frage des Assistenten, ob die geplanten App-Repos ihre Git-Historie
mitbekommen sollen.

ANTWORT DES BETREIBERS, wörtlich: *„ohne historie, wichtig ist das nur bei
bucke weg, das wird schon aktiv eingesetzt. alles andere ist noch im demo
modus!"*

1. Für buckeberg gilt „ALLES IST BETA. KEINE ECHTEN DATEN." nicht mehr. Kein
   Löschen, Neuerzeugen oder Überschreiben von Bestand ohne Rückfrage;
   Ausfallzeit ist dort wieder ein Argument; Migrationen für Bestandsdaten
   sind wieder nötig.
2. Für alle übrigen Apps gilt die Direktive unverändert weiter.
3. buckeberg ist die einzige App mit echten Personendaten Dritter
   (WEG-Unterlagen aus einem Verwalterportal, siehe `L-dc0f44`). Entwarnung
   durch Messung am 2026-08-11: `dokumente/` und `dokumente-anon/` stehen in
   `.gitignore` und wurden in der GESAMTEN Historie nie committet
   (`git log --all --diff-filter=A -- 'dokumente/*'` = 0 Treffer). Die
   Pseudonymisierung hat nicht nur gewirkt — die Dateien waren nie im Repo.

NACHTRAG ZUR HISTORIENFRAGE, entschieden am selben Tag: Die gewünschte
Ausnahme „buckeberg mit voller Historie" ist undurchführbar. Der Branch
`feature/buckeberg-australien` ist kein App-Repo, sondern ein Arbeitsbaum des
gemeinsamen hub-Repos; seine 896 Commits beginnen beim Initial-Commit von
**pflegelotse** und umfassen alle Apps. „buckeberg mit Historie" hätte das
ganze Monorepo unter dem Namen buckeberg veröffentlicht. Entscheidung des
Betreibers daraufhin: heutiger Stand, Historie bleibt lokal in `hub/.git` —
für buckeberg wie für alle anderen.

ABGRENZUNG: Die Aussage betrifft Datenbestand und Betriebszustand, nicht die
Handlungsfreigabe vom 2026-08-11T08:15. Deren Widerruf ist das Wort „es wird
ernst" und ist nicht gefallen. Unberührt bleiben die vier Stopp-Punkte:
Zugangsdaten, Außenwirkung gegenüber Dritten, Unumkehrbares, Geld.

---

## Zweiter Eintrag: Lehre (Typ antipattern), ebenfalls nachzutragen

**type:** antipattern · **severity:** high · **projects:** systemweit, hub
**anlass:** selbst

**description:** `rsync` kennt `.gitignore` nicht — und ein frischer `git init`
im Ziel kennt die Regeln des Quellbaums auch nicht. Beim Herauslösen von 19 Apps
aus einem Monorepo in eigene Repos am 2026-08-11 wurde jedes App-Verzeichnis per
`rsync` kopiert. Dateien, die Git im Quellbaum durch eine **verschachtelte**
`.gitignore` ausblendete, wurden physisch mitkopiert und im neuen Repo dann
eingecheckt, weil dessen frische `.gitignore` sie nicht kannte. Konkret gelangte
`ios/7KV9N3VKXL.p12` — ein privater RSA-Schlüssel — in das Repo `3lehr/wohlairr`
und wurde gepusht. Im Quell-Repo war die Datei **nie getrackt**. Der Fehler
entstand also beim Herauslösen, nicht im Bestand, und ein Geheimnis-Scan, der
vorher den QUELLBAUM prüft, kann ihn strukturell nicht finden.

Gleiche Klasse, vorher abgefangen: `android/key.properties` (Keystore-Passwort im
Klartext) bei fahrtenbuch_legacy sowie `android/local.properties` bei drg und
pflegelotse — ein späterer Agent bemerkte das Muster von sich aus. Nach dem Fund
lagen zusätzlich zehn ungetrackte Kopien solcher Dateien in den neuen
Verzeichnissen.

**root_cause:** Der Scan lief auf der falschen Seite der Kopie. Geprüft wurde,
was im Quellbaum getrackt ist; entstanden ist die Gefahr durch das, was im
Zielverzeichnis LIEGT. Zwischen beidem steht ein Werkzeug, das Git-Regeln nicht
kennt. Verstärkend: verschachtelte `.gitignore`-Dateien tiefer im Baum sind beim
Lesen der obersten nicht sichtbar.

**resolution:** Datei aus dem Commit entfernt, Commit neu gefasst, erzwungen
gepusht; im Remote-Baum per GitHub-API nachgewiesen, dass keine Schlüsseldatei
mehr enthalten ist. Zehn physische Reste in allen Repo-Verzeichnissen gelöscht.
`.gitignore` der neuen Repos um `*.p12`, `*.p8`, `*.keystore`, `*.jks`,
`android/key.properties`, `android/local.properties` ergänzt. Der Schlüssel gilt
trotzdem als kompromittiert und muss beim Aussteller zurückgezogen werden — ein
erzwungener Push entfernt den Verweis, nicht zwingend das Objekt beim Anbieter.

**prevention:** Bei jedem Kopiervorgang zwischen Repos gilt: **der Scan gehört
ans ZIEL, nach dem Kopieren und vor dem ersten Commit** — nicht an die Quelle.
Ein `git status --ignored` bzw. ein `find` über das Zielverzeichnis nach
`*.p12`, `*.p8`, `*.keystore`, `*.jks`, `key.properties`, `local.properties`,
`.env` kostet Sekunden und findet genau das, was ein Quell-Scan strukturell
nicht sehen kann. Zweitens: `rsync --filter=':- .gitignore'` respektiert
`.gitignore`-Dateien, auch verschachtelte — das ist die Werkzeugantwort auf
dieselbe Frage. Drittens, als Abnahme statt als Vorsatz: nach dem Push den
Dateibaum gegen die API des Anbieters prüfen, nicht gegen die lokale Kopie.
