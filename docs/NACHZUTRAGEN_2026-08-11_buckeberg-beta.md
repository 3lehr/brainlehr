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
