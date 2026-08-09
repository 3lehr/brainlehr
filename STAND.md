# STAND brainlehr — 2026-08-09T18:45:00+0200

Offen: 117 Knoten tragen project_id 'shared', obwohl ihr Pfad das Projekt
nennt (37 brainlehr, 29 openlehr, 26 fahrtenbuch, 12 buckeberg, Rest einzeln)
— nachtragbar, aber mit dem jetzigen Pruefkorpus nicht als Gewinn messbar.
Dazu 9 Knoten, die der Pruefstein weiter abweist (`runs/umschrift_abgelehnt.json`),
und 26 Hausnormen, die bewusst den alten Text behalten.
Naechstes: Vorgabewert von project_id in knowledge_add aus parent_path
ableiten statt 'shared' — dieser bequeme Default hat die 117 erzeugt.
Danach Aehnlichkeitskanten neu rechnen (die 5799 beschreiben die alten Texte)
und beide Plaene fortschreiben.
Wartet auf: `~/.claude.json` -> `mcpServers.knowledge.env` (actor) · Papernetz-
Umfang · sechs Knoten Rang 4/6 · abgelaufene Norm buckeberg-anbieterabend.
Nicht vergessen: Rueckweg ist `snapshots/knowledge_2026-08-09.db` plus 350
Zeilen in `knowledge_fassungen`; Abruf steht bei 13/35 (vorher 7/35) bei 2604
statt 2735 Zeichen je Prompt.
