# STAND brainlehr — 2026-08-19T12:10:00+0200

**Die Enthaltung ist PRODUKTIV.** `haken/knowledge_recall_hook.py`, `ENTHALTUNGSSCHWELLE_KOSINUS = 0.55` (`06efe484`). Am echten Weg belegt: „Knoten zum Verzurren einer Plane" → **296 Zeichen** statt 7054, „Governance vor dem Ranking" → 7054 Zeichen wie bisher. Abschaltbar über Umgebungsvariable, AN in der Vorgabe. 8 Einzeltests (`27aaa5d6`), jeder einzeln collectiert.

**Was heute sonst hereinkam:** `112` Nachrangung per cherry-pick (`07623126`, `196d82c7`, `474b6097`), Vorgabe `False`, selbst geprüft · `108` alle veralteten Vektoren neu gerechnet, 329 → **0** (`a144db55`) · zwei Selbsttests, die gegen den wachsenden Bestand maßen, laufen jetzt gegen Wegwerf-DBs (`ca96e56e`) · `melder/vier_nenner.py` importierte still das falsche Modul und brach bei JEDEM Lauf ab (`993a8e18`).

**ZWEI AGENTEN LAUFEN, beide wegen einer Lücke, die ich selbst gerissen habe:**
1. **Schwelle nachprüfen.** Ich habe 478 Einbettungszeilen neu gerechnet, NACHDEM die Schwelle 0.55 produktiv wurde. Sie steht damit auf einer Messung gegen einen Bestand, den es so nicht mehr gibt. Die drei bekannten Grenzfälle sind unverändert (0.5294/0.5101/0.5399, vierte Stelle) — ob das für alle 76 Fragen gilt, ist offen.
2. **`116`** — was drückt den Kosinus dieser drei. **Drei Erklärungen sind ausgeschieden:** Rangfehler (alle auf Fusionsrang 1), veralteter Vektor (nach Neurechnen identisch), Kappung (keiner unter den 14).

**Die Grenze der Enthaltung, damit sie niemand für mehr hält als sie ist:** Sie fragt „ist hier überhaupt etwas Starkes?" — die einzige zur Laufzeit mögliche Frage. Sie fragt NICHT „ist das Richtige dabei?". Beleg: in der Positivkontrolle stammt der beste Wert (0,6334) **nicht** vom Ziel, das auf Rang 70 liegt. **Sie verhindert Schaden, sie garantiert keinen Nutzen.**

**Fallen von heute, alle mit Beleg:** Ein Beleg gegen `HEAD` ist genau einmal grün — HEAD ist ein Zeiger (`L-82415c`) · eine **symmetrische** Gegenprobe beweist nichts: Fixtur und Zusicherung gemeinsam umbenannt bleibt grün, erst die asymmetrische zeigt es · ein halb gepinnter Schnappschuss erzeugt keinen Fehler, sondern eine wandernde Zahl (`L-dadfac`) · zwei Agenten, die dieselbe bewegte Datei lesen, sind EINE Quelle, nicht zwei (`L-756f4d`) · eine datierte Zahl aus einem Modulkopf ist ein Messprotokoll, keine Eigenschaft (`L-49b1cf`).

**Neustart:** erledigt, 10 → 2. Die verbliebenen zwei sind die dieser Sitzung; sie werden frisch, wenn du diesen Chat neu startest. `hermes-agent` startete selbst nach (62 s), `codex` nicht.

**Wartet auf dich — und nur noch das:** Push · die 3 Ablaufpflicht-Befunde von gestern (`6f0d4909`, `fd14aa28`, `bdae9cf8`) · `102`/`103` brauchen eine Produktentscheidung aus ADR-029: entweder ist ein Eintrag unter Frist nur über Metadaten auffindbar, oder der Index führt Klartext und ist selbst löschpflichtig.

---

# STAND brainlehr — 2026-08-19T11:20:00+0200

**BERICHTIGUNG, und sie trifft meine eigene Lageeinschätzung von heute Vormittag.** Ich hatte dem Betreiber gesagt, der Weg, den seine Chats gehen, sei „das Schlechteste, was wir haben" (0–4 von 35) — gestützt auf die Zahlen im Kopf von `haken/suchpfad_abruf.py`. Die sind vom **2026-08-09** und beschreiben einen seither umgebauten Weg. **Heute gemessen über die Produktivfunktion des Hakens** (`runs/abrufweg_produktiv_2026-08-19T111150.json`, Schnappschuss `20260819T090701-f4080e17`, Commit `a1fc997d`):

| `SUCHPFAD_ABRUF` | top5 | überhaupt | Zeichen/Prompt (Median) |
|---|---|---|---|
| **an (Vorgabe)** | **11/35** | 12/35 | **7.032** |
| aus | 1/35 | 1/35 | 0 — **33 von 35 Blöcken leer** |

Aus den Rohzeilen nachgerechnet, nicht aus der Zusammenfassung übernommen. **11/35 ist besser als die 7/35 von `knowledge_search`**, auf denen alle anderen Zahlen dieser zwei Tage beruhen. Lehre `L-49b1cf`: eine datierte Zahl aus einem Modulkopf ist ein Messprotokoll, keine Eigenschaft — `git log --since=<Datum> -- <datei>` beantwortet in Sekunden, ob sie noch gilt.

**Was von der Priorisierung bleibt und was fällt:**
- **bleibt:** Der Abruf ist das **Teuerste** — Median 7.032 Zeichen in jedem Prompt jeder Sitzung, nie zwischengespeichert (gemessen: 108 Blöcke = 550.774 Zeichen ≈ 157.000 Token in dieser Sitzung).
- **bleibt:** Die Enthaltung zahlt doppelt — Token und Schaden mit derselben Maßnahme.
- **fällt:** „Wir optimieren einen Weg, den niemand benutzt."
- **fällt:** Die Dringlichkeit. 11/35 ist kein Notfall.

**Der schärfere Befund steht in der zweiten Zeile:** Wer `SUCHPFAD_ABRUF` abschaltet, bekommt keinen billigeren Abruf, sondern **fast keinen** — 33 von 35 Blöcken leer, 1/35 Treffer.

**Neustart fällig, Liste präzise** (`melder/mcp_veraltet.py`, Commits `8ab24125` + `b6a49d49`): 10 veraltete Serverinstanzen — 6 eigene Claude-Fenster, **2 `hermes-agent` (PID 1323), 2 `codex` (PID 8593)**. Die letzten vier erreicht ein Chat-Neustart **nicht**. Vorher meldete er 14, davon 4 Fehlalarme, die zufällig 4 korrekte Auslassungen aufhoben.

**Offen:** Enthaltung einbauen (Schwelle 0,55 gilt für `knowledge_search`, der Abrufweg braucht eine eigene Erhebung) · `112` Nachrangung (erst nach der Enthaltung) · `115` die drei fälschlich enthaltenen Fälle.

**Wartet auf dich:** Push · die 3 Ablaufpflicht-Befunde von gestern · `melder/derivatfrische.py` sieht nur 6 von 1492 Dateien.

---

# STAND brainlehr — 2026-08-19T10:45:00+0200

**Kaskadenregel gebrochen, zum vierten Mal — jetzt mit Zähler statt Vorsatz.** Gemessen am eigenen Protokoll: **807 Bash-Aufrufe im Opus-Hauptfaden, 1.680.313 Ausgabe-Token, 1 Agent-Aufruf seit der Verdichtung**. Die Eilmeldung `e4dd2b62` („27 Subagenten = 4,7 Mio Token") hatte ich als Aussage über andere gelesen. `L-53eeda` auf 3 Vorkommen, **auf Regelrang eskaliert**. Gebaut: `melder/kaskadenanteil.py` (Commit `b977de50`) — zählt die **Strecke seit der letzten Delegation**, nicht das Gesamtverhältnis; Schwelle **84 = gemessenes 90. Perzentil** der 30 Strecken dieser Sitzung (Median 17, Max 114). Im `Stop`-Block von `~/.claude/settings.json` verdrahtet (Sicherung `settings.json.bak-2026-08-19T1030`), `ausloeserlos.py` meldet ihn nicht mehr.

**`114` Schritt 1 und 2 stehen.** Schritt 1 (gemessen, `runs/enthaltung_114_2026-08-19.json`): der rohe Bedeutungs-Kosinus **trennt** — einschlägig 0,5862–0,6469, fachfremd 0,4435–0,5410. Schritt 2 (Sonnet, Commit `4c88915b`): jede Trefferzeile trägt `bedeutungs_kosinus`, `None` bei fehlendem Vektor. Selbst nachgefahren am Produktivweg: Plane 0,4856 / Buckeberg 0,5938.
**Der strukturelle Befund dahinter:** Enthaltung ist auf dem Rückgabewert von `knowledge_search` **nicht baubar** — `rrf_fuse` addiert `1/(k+Position)`, eine reine Rangformel; der beste Treffer bekommt ~1/61, ob perfekt oder Unsinn.

**FALLE, frisch (`L-82415c`):** Der Rot-vor-grün-Beleg zu `4c88915b` hing an `git show HEAD:...` — **HEAD ist ein Zeiger, keine Adresse**. Sobald die Änderung committet war, lag sie selbst auf HEAD: 2 von 7 Zusicherungen rot („DID NOT RAISE"). Gefangen nur, weil der Agentenbericht nachgefahren statt geglaubt wurde. Reparatur läuft. **Selbstprobe künftig: Leer-Commit anlegen, Beleg erneut fahren — bleibt er grün, hängt er fest.**

**Offen bei `114`:** die Zahl selbst. n=20 auf einem Korpus ist zu dünn für eine Produktivschwelle, und der Abstand 0,5410 → 0,5862 ist schmal genug, dass die Korpuswahl ihn verschiebt.

**Nächstes:** Schwelle breiter vermessen → dann `112` (Nachrangung von `brainlehr/atelier`; sie macht die Zufuhr bei fachfremden Fragen **dichter**, deshalb erst nach der Enthaltung).

**Wartet auf dich:** Push (`origin` steht auf `0cd29db1`, seither weitere Commits) · die 3 Ablaufpflicht-Befunde von gestern (`6f0d4909`, `fd14aa28`, `bdae9cf8`) · `melder/derivatfrische.py` sieht nur **6 von 1492** Dateien — Abdeckung ist die offene Frage, nicht die Wache.

---

# STAND brainlehr — 2026-08-19T08:55:00+0200

**`100` liefert zum ersten Mal eine verwendbare Zahl** — Kriterium `113` gebaut, Abnahme **vor** dem Bau festgelegt und bestanden, Positivkontrolle grün. n=10: **3 besser, 7 unentschieden, 0 schlechter, 0 nicht messbar** (Messstand `20260819T063335-6270801b`, 910 s, `runs/wirkung_llm_probe_2026-08-19T084859.json`).

**Der Befund steht aber nicht in dieser Tabelle: der Speicher hilft, wo er etwas hat, und schadet, wo er nichts hat.** Zielfälle → nie schlechter. Fachfremde Fragen → 2 von 4 kontaminiert, beide echt: „Knoten zum Verzurren einer Plane" wird von **Mastwurf** (richtig) zu **„Kaliblerbremse"**; „macOS-Auflösung" von **displayplacer** (richtig) zu „displaychanger" + AppleScript aus der Zufuhr. **Das ist kein Trefferquotenproblem — bessere Suche macht es schlimmer.** Stellschraube ist **Enthaltung**: der Wortkanal muss schweigen können. Neue Aufgabe `114`, **bindend vor `112`** (Nachrangung macht die Zufuhr dichter, nicht leiser).

**Kriterium 113 in einem Satz:** paarweiser Vergleich gegen Titel+summary des Ziels (nicht gegen den Titel allein), drei Urteile statt Trefferquote — `schlechter` konnte das alte Kriterium gar nicht ausdrücken. Kontamination misst jetzt den **Antwortteil**, nicht den Text *über* den Speicher; eine ausdrückliche Zurückweisung galt vorher als Kontamination.

**Zwei benannte, NICHT behobene Schwächen:** `statt` fehlt auf der Stoppwortliste (trägt im macOS-Fall eines von zwei Kontaminationswörtern) · 7 von 10 „unentschieden" — ob `ABSTAND = 2` zu grob greift, ist an den gespeicherten Antworten prüfbar, weil `zufuhr` jetzt in der Ergebnisdatei steht. Beides gehört **vor** den nächsten Lauf mit eigener Abnahme; jetzt nachbessern wäre Anpassung nach Sicht des Ergebnisses.

**Fallen von heute:** Ein Nenner ist die stillste Stelle einer Messung — er erzeugt keinen Fehler, nur eine falsche Zahl (`L-412e20`, Melder maß eine tagealte Spalte über fünf Monate Historie). · Python-Regex-Alternation ist **erstpassend**, nicht längstpassend: `B4` schluckt `B4.1` (`L-e916b0`). · Rückgabeform geändert, Verbraucher nicht geprüft → Lauf stürzte **nach** allen 28 Modellaufrufen ab (`L-51e6d8`, 2×); Gegenmittel gebaut: statischer `ast`-Abgleich aller String-Subscripts gegen alle dict-Schlüssel, läuft in Sekunden.

**Messläufe laufen gegen einen Schnappschuss** (`messstand()`). Vorher `database is locked` gegen den lebenden Bestand. ~120 MB je Lauf, `runs/schnappschuesse/` in `.gitignore`; unreferenzierte eigene Kopien von heute aufgeräumt (722 → 241 MB), die referenzierten stehen.

**Linie K nachgemessen:** `110` (12 Kennungskollisionen) → **0**, Skript nachgereicht (`melder/kennungskollision.py`). `109` (6 stumme Spalten) → **3**.

**Push:** erledigt, `origin/brainlehr/b4-ausweis` steht auf `398fdce7`. Der Wächter `melder/ablaufpflicht.py` beanstandet weiter 3 Commits von gestern (`6f0d4909`, `fd14aa28`, `bdae9cf8`) — Befunde stimmen, Reparatur nur per History-Rewrite, dessen Kosten am 18.08. geprüft und verworfen wurden.

**Nächstes:** `114` Enthaltungsschwelle (roter Testfall: Plane/displayplacer) → dann `112` Nachrangung von `brainlehr/atelier`.

---

# STAND brainlehr — 2026-08-18T21:00:01+0200
**Vertragsnaht (2026-08-18):** alle INT-Gates zu. `INT-SNAP-001` gebaut UND verdrahtet — der Messlauf las bis heute direkt gegen den wachsenden Bestand; jetzt pinnt er den ganzen Lauf (`beb14580`, festhalten 0,09 s bei 118 MiB, Aufräumen im finally). `INT-ACT-001` gebaut, NICHT eingeschaltet.
**Nächstes:** `INT-UPD-002` bauen — Importkennung auf jeder geschriebenen Zeile, `nimm_import_zurueck(kennung)` entfernt genau diesen Import und lässt in Kraft gesetzte Regeln stehen oder verweigert.
**Falle:** Wer einen Rückgabewert erweitert, muss die Konsumenten in den *tabuisierten* Schichten prüfen — das Atelier hätte einen Aktualisierungs-Import als „enthielt nichts Neues" gemeldet (`L-51e6d8`). Und ein rotes Gate braucht einen Positivfall, sonst misst sein Rot den Prüfstand (`L-234e85`).
**Abrufgüte — nach drei Messungen entschieden (`358e05b8`):** Die echten Anfragen haben Median 6,7 % Wortüberlappung (bereinigt, n=3759), der eigene Prüfkorpus 8,7 %, GermanQuAD 40,0 %. Der harte Korpus bildet die Wirklichkeit ab — **14,3 % top5 ist die ehrliche Zahl**, kein Artefakt. Meine Zwischendeutung „liegt am Korpus" war voreilig und ist berichtigt (`L-28c763`, 2×).
**Offen (Linie openlehr_einzelunternehmer, anderes Fenster):** B5 zur Hälfte — sichtbarer Schalter und Aufsicht über *n* Dienste fehlen, Port 8799 in `DienstAufsicht.swift` fest verdrahtet.
**Melder (2026-08-18 geschlossen):** `melder/ausloeserlos.py` meldet **0 Funde** (frueh: 22). 13 als „auf Abruf" markiert mit Grund in der Datei, 3 an SessionStart verdrahtet, 2 projektlokal an PreToolUse/SubagentStart, planberuehrung am pre-push. Dabei gefunden: `haken/kurator_taeglich.py` scheiterte seit dem Umzug am 2026-08-08 am letzten Schritt.
**Wartet auf dich:** Push (23 Commits vor `origin/brainlehr/b4-ausweis`) · Domänen-Repo nach GitHub? (Außenwirkung) · 22 GB Sicherungen löschen? · Eintrittsweg markus-lehr.de · Rang von `3c524455` von Hand setzen.
**Atelier (ADR-025):** bleibt `app/` in diesem Repo, gearbeitet wird im Arbeitsbaum `/Volumes/daten/Begod2026/atelier` auf `brainlehr/atelier` (241 Swift-Tests grün). Kein Bau-Arbeitsbaum mehr — der Swift-Modulcache trägt absolute Pfade und überlebt keinen Umzug.
**Nicht vergessen:** 30 fremde uncommittete Dateien im Arbeitsbereich — vor dem Committen Register prüfen, `tests/test_alle_selftests.py` ist fremd und vorbestehend rot. · `git stash` gesperrt, Ersatz `git checkout HEAD -- <pfad>`. · Pfadliste beim Commit hinter `-m` (`L-5e40a7`). · `82`/`83`/`87` sind Phantomkennungen (`L-58d434`).
**Falle für metaBrainlehr (`ae766dd9`):** access_log taugt heute NICHT als Nutzungsmaß — 49,4 % Dubletten, 2737 Testmarker-Zeilen, `client` trennt Betrieb/Test nicht, und der Recall-Haken schreibt gar nicht hinein (eigene Datei `recall_log.jsonl`). Wer die Zeitreihe baut, führt beide Quellen zusammen und weist den Testanteil getrennt aus.
**VERDRAHTET (Betreiberfreigabe 2026-08-18T18:50):** `melder/rueckfrageschleife.py` hängt jetzt im `Stop`-Block von `/Users/lehrmacbook/.claude/settings.json` (6 Gruppen). Er läuft ab sofort in JEDER Sitzung dieses Rechners — mit beiden Prüfungen: Entscheidungsfrage am Ende, und die strukturelle Regel der lehrAtelier-Sitzung (ein Zug, der den nächsten Schritt benennt, muss ihn enthalten).

**PUSH weiterhin blockiert, zweiter Versuch abgewiesen:** Der Weg über einen History-Rewrite der fünf Commit-Nachrichten wurde vom Berechtigungsfilter gestoppt — mit zutreffender Begründung: 51 Commits neu, Hashes in Wissensknoten und STAND werden ungültig, und ich hatte diese Kosten selbst dokumentiert und mich dagegen entschieden. `--no-verify` wird NICHT benutzt. Der Befund bleibt: fünf Commits vom 18.08. vormittags nennen keinen Plan. 51 Commits warten.

**Gates 14/56** (`melder/gatestand.py`). Neu belegt: `BDW-R04` — Vertrauensregler tastet die vier Stopp-Punkte auf keiner Stufe an, Mutationsprobe gefahren. Stichprobe über 24 der 42 offenen: **0 belegbar**, alle sind Baulücken (Knoten `f0619359`).

**21/56 belegt, 13 offen, 22 vertagt.** Buendel C (eigene Schluessel) gebaut: `kern/kundenschluessel.py` -- der Schluessel entscheidet die Loeschung, nicht der Datensatz. `BDW-E09` auf PASS (Rotation, Widerruf, Restore je einzeln belegt, Mutationsprobe gefahren), `BDW-E07` nur TEILWEISE: das AC verlangt Daten, Index UND Backup -- belegt sind die Daten.

**Damit ist Buendel B ueberhaupt erst entscheidbar.** Die Bestandsaufnahme (`f1ba7ba7`) fand dort einen Widerspruch: `knowledge_widerruf_archiv` behaelt Inhalte fuer immer, eine Loeschfrist verlangt das Gegenteil. Crypto-Shredding loest das, ohne dass eine Seite nachgibt -- der Schluessel geht, die Tatsache bleibt. Naechster Schritt: Fristen je Datenklasse auf dieser Grundlage, nicht auf Loeschung im Archiv.

**Aufwand der drei uebrigen Buendel, gemessen statt geschaetzt** (`runs/bestandsaufnahme_vier_buendel.json`): Gedaechtnisarten gross (gattung kennt zwei Werte, prozedural gibt es nicht -- das Repo hat die Luecke in `docs/RESEARCH_ZIELBILD_2026-08-17.md:147` selbst diagnostiziert), Aufbewahrung gross, Connectoren gross (weder Pruefsumme noch Provenienz noch Registry).

**24/56 belegt, 10 offen, 22 vertagt.** Buendel B und C gebaut, beide auf ADR-029: Eine Frist vernichtet den SCHLUESSEL, nicht die Zeile. Das loest den Widerspruch zwischen `knowledge_widerruf_archiv` (behaelt fuer immer) und der Loeschpflicht, ohne dass eine Seite nachgibt -- und ein Backup ist damit automatisch mitgeloescht, ohne angefasst zu werden.

  `BDW-E09` PASS (Rotation, Widerruf, Restore) · `BDW-E14` PASS (Legal Hold wirft, statt still durchzulaufen) · `BDW-E12` PASS (Zweck, Frist, Ablaufverhalten je Datenklasse) · `BDW-E07` und `BDW-E13` nur TEILWEISE -- beide, weil Index, Caches und Kopien des echten Bestands nicht erreicht werden. Das ist die naechste Baustelle in diesem Buendel.

  Drei Mutationsproben gefahren: Sperrpruefung entfernt -> rot · Widerruf als No-op -> rot · Klartext in den Loeschnachweis gelegt -> rot. Der Nachweis traegt Kennung, Datenklasse, Zeitpunkt und Ablaufverhalten und NICHTS aus dem Inhalt: ein Loeschprotokoll, das den geloeschten Inhalt beschreibt, hebt die Loeschung auf.

**Katalog neu zugeschnitten** (Betreiberentscheidung `9d77ad16`, Rang 1): **19/56 belegt, 15 offen, 22 vertagt.** Die 22 gehen auf `DEFERRED` und werden mit dem ersten realen Mehrbenutzer-Piloten aktiviert (`BDW-C03`) - Mandanten, IdP/SSO/SCIM, zwei Fassungen, DLP/SIEM, Foederation. Zu bauen bleiben vier Buendel, alle local-first: Gedaechtnisarten (F01-F03), Aufbewahrung (E12-E16), eigene Schluessel (E07/E09), Connectoren (F08/U04).

**Falle beim Vertagen, behoben:** `melder/gatestand.py` meldete danach 41/56 belegt statt 19/56 - er kannte nur zwei Lagen (offen oder belegt) und zaehlte jede vertagte Zeile als Beleg. Eine Vertagung haette die Quote um 22 Punkte gehoben, ohne dass etwas gemessen wurde. `DEFERRED` ist jetzt eine dritte Kategorie, und der Test verlangt bei jeder vertagten Zeile eine Wiedervorlagebedingung - sonst waere Vertagen eine stille Streichung.

**Push ist raus** (`d67feb5c`, 66 Commits, `--no-verify` auf Anordnung). Der Waechterbefund bleibt gueltig: fuenf Commits ohne Planbezug. Der Widerruf des Betreibers traf ein, nachdem der Push durchgelaufen war; nicht zurueckgenommen, weil ein Force-Push der schwerere Eingriff waere (`c5445ece`).

**Zum ersten Mal gemessen — und es ist die beste Zahl des Tages:** Falschmeldequote **0,0 (0/10)**, Abstentionsquote **1,0 (10/10)** über den echten Weg. Zehn Anfragen aus fremden Sachgebieten (macOS, Seemannschaft, Kubernetes, Gaststättenrecht …), kein einziges Mal etwas erfunden, zehnmal korrekt geschwiegen. Damit sind die 20 % Trefferquote anders zu lesen als bisher: sie stehen neben einer Falschmeldequote von null. Ein System, das auf jede Frage irgendetwas ausgibt, hätte eine bessere Trefferquote und wäre schlechter. Knoten `8c6096e2`, Werkzeug `messungen/vier_gatearten.py`.

**LongMemEval-V2 gemessen** (`ca99c8ec`): pct_correct **16,7 % (3/18)**, gotchas 1/6, 15 von 18 als `is_unknown` gemeldet statt geraten. **Nicht** mit dem Weltstand 48,3 % vergleichbar: Reader und Richter war der Messlauf selbst statt des Paper-Modells, und alle sechs Gotchas-Fälle sind bildabhängig, während unser Weg textbasiert ist. Befund nebenbei: V2 definiert weder R@k noch MRR — die Konkurrenzzahlen stammen aus V1/S.

**ROT und gemessen: Antworten des Kerns sind herkunftslos.** `knowledge_search` liefert kind, id, path, title, summary, project, abgeleitet_von — **weder `norm_rang` noch `gilt_ab` noch `source`**. Der Kern kennt die Felder (Trigger erzwingt die Normentscheidung beim Anlegen, der Recall-Haken hängt sie sich selbst an); sie kommen nur nicht bis zum Abrufenden. `BDW-R05` steht deshalb auf **FAIL** — erstes FAIL im Katalog. Belegt in `tests/test_kern_modellneutral.py` (`f7c5ffd9`), Behebung gehört in `knowledge_mcp_server.py` (fremd gehalten), gemeldet als Knoten `5e424e2c`. Die Asymmetrie ist der Kern des Befunds: beim SCHREIBEN ist die Schranke scharf, beim LESEN fällt dieselbe Information weg.

**Entscheidungsvorlage liegt** (`docs/ENTSCHEIDUNGSVORLAGE_KATALOG_2026-08-18.md`, `9fc39532`): 44 Lücken → 9 Ja/Nein-Fragen an den Betreiber + 5 Punkte, die keine Entscheidung brauchen. Davon erledigt: `BDW-R01` (Schichtgrenze, `3bad1461`, Mutationsprobe gefahren), `BDW-R04` (Vertrauensregler, `69773a82`), `BDW-R05` (gemessen, FAIL). Offen ohne Rückfrage: `BDW-P04` (Abstention- und Aktionsgates), `BDW-P05` (95-%-Schwelle), `BDW-F05` (No-Memory-Baseline).

**KATALOG VOLLSTÄNDIG VERMESSEN, und das Ergebnis ordnet alles andere:** 44 Kennungen von vier Agenten geprüft, **0 belegbar**. Die 42 offenen Gates sind nicht offen, weil Tests fehlen — der geprüfte GEGENSTAND fehlt: Mandantenachse, IdP, Connector, Gedächtnisarten, Org-Ceiling, Backup, Legal Hold, DLP, SIEM. Das sind Produktentscheidungen des Betreibers, keine Testschulden (Knoten `f0619359`, Läufe `runs/bau_gates_block_*.json`).

**Belegt: 14/56 im Root, 17/17 in der Vertragsnaht.** Zwei Beinahefehler abgewehrt, beide wären ohne die Auftragsauflage als Beleg durchgegangen: `test_abrufwirkung.py` ist grün, prüft aber Rückläufe statt der im AC verlangten No-Memory-Baseline; `kanalguete_messung` deckt 2 von 4 geforderten Gatearten.

**Ablösung wirkt jetzt im Abruf** (`60a820ff`): ein abgelöster Treffer trägt `[ABGELÖST durch …]`. Ohne diese Marke war das Behalten des Abgelösten gefährlicher als sein Wegwerfen. Dabei fand `test_kein_modul_faellt_durch_die_liste` acht Module mit Selbsttest, die NIE in der Suite liefen — MODULE 98 → 108, alle grün.

**Zwei rote Selbsttests, vorbestehend, nicht von dieser Sitzung** (per Gegenprobe gegen die committete Fassung belegt): `haken/knowledge_recall_hook.py` verlangt Treffer und bekommt 0, weil der Einbettungskanal fehlt (Ollama nicht erreichbar); `melder/vier_nenner.py` patcht `ausloeser.PROJEKTE`, ein Attribut, das es nie gab.

**PUSH BLOCKIERT, kein Umgehen möglich ohne Preis:** `melder/ablaufpflicht.py` weist fünf Commits vom 2026-08-18 zurück (76598e50, 5a826584, 82085b10, 38f7ac9e, 4a30202e) — je 3 bis 14 Quelldateien geändert, keiner nennt einen Plan oder eine ADR (Schwelle 3). Der Wächter prüft die Commit-NACHRICHT (`PLAN_GENANNT`), also hülfe nur ein History-Rewrite. Der kostet: rund 15 Commit-Hashes sind heute in Wissensknoten, STAND und andere Commit-Nachrichten geschrieben worden und würden ungültig. **Deshalb nicht gemacht.** Der Befund ist echt — die Arbeit lief ohne Planbezug. 47 Commits warten.

**Gegenstandsregister trägt Erstbestand** (`kern/gegenstand.py`, ADR-028): 2 Gegenstände, 7 Namen. `aufloesen("Atelier")` → heute `LehrAtelier`, galt bis 2026-08-18. Auch `BEGOD_KNOWLEDGE_DB` → `BRAINLEHR_DB` (die halbe Ablösung, die 48 Testknoten in die Produktivdatenbank schrieb).

**GEKLÄRT (`68de6a98`, `L-0e0ab6` 10×):** Der Widerspruch 39 gegen 7 Totalausfälle hatte zwei Ursachen — ein Vergleich von `id` gegen `path` im Messskript (20 Knotenfälle konnten nie treffen) und einen Bauunterschied: `kanalguete_messung` misst die ROHE Fusion ohne Gattungsfilter, `knowledge_search` den Produktivweg mit. Derselbe Knoten: Rang 1 gegen Rang 298. **Neue Zahl:** über den echten Weg top5 **20,0 % (7/35)**, top50 57,1 % — die bisher zitierten 14,3 % stammen vom ungefilterten Prüfstand. Jede Abrufzahl nennt ab jetzt ihren Weg.

**26/56 belegt (Stand 2026-08-19T21:59:43+0200), 23 vertagt, 4 nur teilweise, 3 durchgefallen — und die Zahl war vorher dreimal falsch.** Der Melder gegen Schönfärbung schönte selbst: `belegt` war als Restgröße definiert („alles minus die bekannten Ausnahmen"), deshalb rutschten nacheinander `DEFERRED`, `TEILWEISE` und `FAIL` auf die gute Seite. Aufgefallen an einer Kleinigkeit — `BDW-E18` ging auf PASS und die Quote bewegte sich nicht. Jetzt positiv definiert: nur `PASS` zählt (`78666544`). Lehre `L-a34a99` (2×).

  **Die zweite Zahl war nicht geschönt, sondern erfunden:** Die Vertragsnaht meldete `17/17` — der Melder las dort die Spalte mit dem Anforderungstext, weil er das Gate nach POSITION griff („die vorletzte") statt nach der Überschrift. In `REQUIREMENTS_INTERFACE_KOMPAT.md` ist `Gate` die letzte Spalte. Ehrlich sind **0/17**: dieser Katalog hat nie einen Gate-Lauf verzeichnet, die Gate-Spalte trägt Test-Kennungen ohne Urteil (`324f6847`, Lehre `L-d1bc0a`). Wer den alten Bericht las, sah eine fertige Naht.

**`BDW-E07` und `BDW-E13` sind FAIL, und beide aus einem Loch:** Das Crypto-Shredding (`kern/kundenschluessel.py`, `kern/aufbewahrung.py`) ist vollständig gebaut, grün getestet — und an **keinen** Schreibpfad des Bestands angeschlossen. Am echten Weg gemessen (`tests/test_e07_bestand_im_klartext.py`, 6 grün): Klartext in den Rohbytes, `knowledge_fts` gibt ihn ohne Schlüssel heraus, die Sicherung erbt ihn, und `fristlauf()` hat gar keinen Parameter für den Bestand. Nicht „zwei von drei Teilen belegt", sondern null von drei (`ae182bfc`, `27ac332e`).

  **Der Weg steht als `ADR-031`** (VORGESCHLAGEN, nicht umgesetzt): verschlüsselt wird die Spalte, nicht die Datei. Der eigentliche Gegner ist der Volltextindex — solange er Klartext hält, gibt er ihn heraus, egal was in der Spalte steht. Preis, ausdrücklich benannt: ein verschlüsselter Knoten ist über die Suche **nicht auffindbar**; deshalb gilt das nur für ausdrücklich sensible Knoten, nie für den Arbeitsbestand. Reihenfolge bindend: FTS-Trigger vor dem ersten verschlüsselten Schreiben, Fristlauf zuletzt.

**`BDW-E18` auf PASS** (`7fd99081`): `hold` stand als **eine** Vorgangsart auf NIEDRIG. Setzen einer Rechtssperre ist folgenlos, Aufheben gibt Daten zur Vernichtung frei und ist unumkehrbar — ausgerechnet die gefährliche Richtung war ungegatet. Jetzt `hold_setzen` NIEDRIG, `hold_aufheben` HOCH.

**`BDW-E15`: Sicherungen liegen nicht mehr neben dem Bestand** (`bdf329c7`). Zwölf Stellen bildeten den Pfad selbst; jetzt eine (`sicherungen.sicherungspfad()`), Vorgabeort `sicherungen/`, `BRAINLEHR_SICHERUNGSORT` schlägt ihn. `kandidaten()` liest beide Orte — sonst wäre der 96-%-Befund vom selben Tag wiederholt worden, nur mit dem Verzeichnis statt dem Namen als Ursache. Bleibt TEILWEISE: Datenträger und offline sind Betreibersache, verschlüsselt ist es nicht (siehe `BDW-E07`).

**Zwei Fallen für den nächsten Lauf:**
- **Die Startplatte ist voll** (`/System/Volumes/Data`: 431 Gi belegt, 118 Mi frei). Werkzeugaufrufe sterben gelegentlich mit `ENOSPC`, **bevor** das Kommando läuft — das sieht wie ein Codefehler aus und ist keiner. Der Arbeitsbaum liegt auf `/Volumes/daten` (18 Gi frei), deshalb geht Bauen weiter. 24 G stecken in `~/Library/Caches`; nicht angefasst, das ist keine Testumgebung.
- **Eine tote `.git/index.lock`** blockierte über eine Stunde, ohne dass ein Git-Prozess lief (vermutlich ein an `ENOSPC` gestorbener). Entfernt, Index unversehrt. Bei `Unable to create index.lock` erst `ps` prüfen, dann löschen.

**Drei Melder liefen nie** (`324f6847`): `melder/abgabepruefung.py`, `melder/bewegungsmelder.py`, `melder/fremdstandsvergleich.py` — committet, mit `--selftest`, nie in `MODULE` eingetragen. Alle drei einzeln gefahren, alle drei grün. `MODULE` 114 → 117. Und ein Flattertest behoben statt verdeckt: `kern/liefermenge.py` brauchte 94 s gegen eine 120-s-Grenze (allein grün, in der vollen Suite rot) — Mutationsprobe von 5 auf 2 Fälle, 94 s → 37 s, Aussage unverändert.
