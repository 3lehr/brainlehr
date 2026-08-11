# STAND brainlehr — 2026-08-11T15:00:00+0200

Offen: die Kernzahl (nuetzt eingespieltes Wissen der Antwort) ist WEITER OFFEN — der Lauf von heute ist kontaminiert, der Abruf-Haken spielte den Subagenten die Loesung ein (4360a82 widerruft cade91d).
knowledge_browse und knowledge_search filtern `freigabe` nicht — gesperrter Knoten erscheint mit Titel und Summary (cda47024, fremder Zweig b4-ausweis).

Naechstes: Aufgaben bauen, deren Traeger NUR im Bestand steht — solange die Loesung im Kontext des Antwortenden auftauchen kann, misst kein OHNE/MIT-Vergleich.
Danach: Pruefkorpus vergroessern (3 Aufgaben sind eine Anekdote), dann die drei restlichen Antwortlaeufe dreiteilen.

Wartet auf: freies Schreibfenster der knowledge.db (WAL seit 14:10 gesperrt) fuer die geparkte Lehre in docs/nachzutragen/ · `mcpServers.knowledge.env` (actor) · Push-Freigabe fuer 8 lokale Commits.

Nicht vergessen: Subagenten sind keine leeren Gefaesse — Haken feuern auf ihren Auftragstext. Vor jeder Messung `python3 kontamination.py --protokolle <agentdir> --aufgaben <datei>`.
Dieser Arbeitsbaum hat KEINE eigene knowledge.db; lesend immer `mode=ro` (L-0f4036).
