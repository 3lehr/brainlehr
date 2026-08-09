# STAND brainlehr — 2026-08-09T16:55:00+0200

Offen: 53 % der Betreibernachrichten erreichen den Speicher nie — gemessen mit
der Warteschlange als Nenner (`ausloeser.py`, `runs/ausloeser_2026-08-09.json`,
94 Nachrichten ab Commit e3ef28f): 28 nie am Haltepunkt (waehrend laufender
Arbeit eingereiht, 5-8 Stichworte), 22 unter MIN_HITS (kurze Zurufe),
44 eingespielt, 0 leer. Die 16/35 Abrufguete gilt fuer die andere Haelfte.
Naechstes: die 28 angehen — vermutlich Haltepunkt, nicht brainlehr; erst
messen, ob eingereihte Nachrichten den Hook ueberhaupt erreichen koennen.
Danach die 22 (Prompt traegt keinen Inhalt, der Arbeitskontext schon,
Knoten `745f7ac1`), dann Pruefkorpus vergroessern, Antwortqualitaet messen.
Wartet auf: `~/.claude.json` -> `mcpServers.knowledge.env` (actor, tippt der
Betreiber selbst) · Papernetz-Umfang · sechs Knoten Rang 4/6.
Falle: ein Protokoll taugt erst als Nenner, seit es den Negativfall schreibt
(`L-cb3f28`); eine Widerlegung erst, wenn ihr Einzelfall im Nenner steht
(`L-bd4e5f`, Verfahren dagegen `L-1c9dc8`).
Uebergabe wird seit hub-Commit 4dea71518 beim Sitzungsstart genannt.
