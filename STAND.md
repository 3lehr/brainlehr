# STAND brainlehr — 2026-08-11T15:55:00+0200

Offen: die Kernzahl (nuetzt eingespieltes Wissen der Antwort) ist WEITER OFFEN — der Lauf von heute war kontaminiert, der Abruf-Haken spielte den Subagenten die Loesung ein (4360a82 widerruft cade91d).
Prozess 25897 (fremde Sitzung) haelt die Schreibsperre der knowledge.db seit 14:10 mit altem Code — bis zu seinem Ende kann niemand schreiben; der Fix wirkt erst fuer neu gestartete Server.

Naechstes: Naht weiterziehen — 69 Produktivdateien oeffnen noch eigene Verbindungen, Ratsche in tests/naht_basis.json haelt den Stand. Zweiter Rechner steht an, danach wird der Transport entschieden (Dienst oder Postgres).
Danach: Aufgaben bauen, deren Traeger NUR im Bestand steht — solange die Loesung im Kontext des Antwortenden auftauchen kann, misst kein OHNE/MIT-Vergleich.

Wartet auf: freies Schreibfenster der knowledge.db fuer die geparkte Lehre in docs/nachzutragen/ · `mcpServers.knowledge.env` (actor) · Push-Freigabe fuer 11 lokale Commits.

Nicht vergessen: neue DB-Zugriffe gehen durch `speicher.lesen()` / `speicher.schreiben()`, sonst faellt die Ratsche.
Subagenten sind keine leeren Gefaesse — Haken feuern auf ihren Auftragstext; vor jeder Messung `python3 kontamination.py`.
