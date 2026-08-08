# STAND brainlehr — 2026-08-08T12:10:00+0200
**Neu hier:** brainlehr ist am 2026-08-08 aus hub/shared-knowledge ausgezogen — eigenes Repo, vollstaendige Historie (132 Commits per `git subtree split`). `hub/shared-knowledge` ist ein **Uebergangsverweis** hierher.
**Offen:** Den Verweis entfernen, sobald die alten Sitzungen und Hermes neu gestartet sind — danach die vier `UserPromptSubmit`-Melder ERNEUT pruefen. Solange er lebt, faellt ein vergessener alter Pfad nicht auf.
**Wartet auf Betreiber:** Push (hub 30 Commits, brainlehr 5 ueber der uebernommenen Historie, beide nie gepusht) · fuenf Knoten mit undokumentierten Raengen 4 und 6 im Buckeberg-Ast · `_VERWAIST_shared-knowledge-2026-08-08` im Verbund-Ordner: umbenannt statt geloescht, Inhalt eine 0-Byte-Datenbank und BSI-Dateien vom April.
**Nicht vergessen:** `knowledge.db` ist NICHT mehr versioniert. Sicherung ist `auszug/bestand_2026-08-08.jsonl` — nach groesseren Aenderungen `python3 brainlehr.py raus auszug/bestand_<datum>.jsonl` und committen, sonst haengt der Bestand an einer Platte.
Nach einem Wiederaufbau (`brainlehr.py rein`) fehlen die Vektoren — `build_embeddings.py` laufen lassen, sonst ist nur die Volltextsuche da.
`hub/scripts` ist NICHT mitgezogen: `knowledge_recall_hook.py` und `knowledge_capture_hook.py` liegen weiter im hub. Wer nur brainlehr klont, bekommt Kern und Werkzeuge, aber nicht die Automatik.
Testlauf: 658 gruen, 7 rot — alle sieben vorbestehend (instructions, caveman-policy, Umlautfaltung), keiner beruehrt den Schreibweg.
