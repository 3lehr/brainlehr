# Startprompt brainlehr — Abend des 2026-08-09

Der vorige Startprompt (`STARTPROMPT_2026-08-09.md`) ist ABGEARBEITET und
ueberholt. Er nennt Deckel 3/2, eine offene actor-Probe und die Frage nach 26
verfehlten Faellen — alles davon ist erledigt. Wer ihn befolgt, arbeitet den
Vormittag ein zweites Mal.

---

## Was heute geschah, in vier Zeilen

Der Abruf traf morgens 7 von 35 Pruefkorpus-Faellen. Gemessen wurde: kein
Vorfilter verliert etwas, aber BEIDE Kanaele ranken die Ziele tief (Median 101
und 96). Daraus folgt die Ursache — nicht der Mechanismus, sondern der Text,
den beide lesen. 350 von 388 Knoten wurden daraufhin neu formuliert, bei
gleichem Sachgehalt. Ergebnis: **16 von 35**, bei 9409 statt 2604 Zeichen je
Prompt (Deckel von 3/2 auf 10/7 erhoeht, Entscheidung des Betreibers).

## Der Stand ist belastbar, das Folgende ist gemessen

- Abruf **16/35** — und robust: gegen 2024 Ablenkungen (Gattungsfilter aus)
  exakt derselbe Wert wie gegen 386.
- Median-Rang des Ziels von 79 auf **27** gefallen. Darum wirkt der Deckel
  jetzt, wo er morgens flach war.
- Zweiter Relevanzkanal EIN. An alten Knoten brachte er +1 von 35, an
  umgeschriebenen +5. Er war nie das Problem.
- Reifegrad: 43 % abgeleitet, 34 erklaert, 218 unbestimmt (= Faelligkeit,
  kein Makel).
- Kanten 5814, alle zehn `analogous_to` erhalten.

## DIE naechste Aufgabe, und sie kommt von aussen

Ein **Feldbericht einer fahrtenbuch-Sitzung** (Knoten `1d2e6458`) sagt: der
Abruf trifft, aber er feuert zur falschen Zeit. Von acht Betreibernachrichten
loesten drei einen Recall aus; vier der sieben Einspielungen kamen auf
Systemmeldungen (nach einem TestFlight-Upload den Codeort einer fremden App).
Nachrichten, die waehrend laufender Arbeit eintreffen, loesen GAR KEINEN aus —
und das waren die inhaltlich schaerfsten.

**Eine Suche, die nicht gefragt wird, hat keine Trefferquote.**

Zu messen ist der AUSLOESER, nicht die Suche. Das Material liegt bereit:
`recall_log.jsonl` fuehrt je Zeile den ausloesenden Prompt. Zu beantworten:
bei welcher Art Eingabe feuert der Haken, bei welcher nicht, und woran liegt
es (MIN_HITS auf der Anfrageseite? Hook-Typ? Prompt-Laenge?).

Dieselbe Methode wie heute frueh, eine Station frueher in der Kette: je Fall
messen, nicht das Endergebnis. Und die Regel, die heute den Durchbruch
brachte: **keine These aufstellen und pruefen, sondern frei messen.**

## Danach, in dieser Reihenfolge

1. **Pruefkorpus vergroessern.** 35 Faelle rauschen nachweislich — die
   Deckelreihe lieferte bei groesserem Deckel WENIGER Treffer (12 gegen 13),
   was sachlich unmoeglich ist. Ohne groesseren Korpus laesst sich kuenftige
   Verbesserung nicht von Rauschen unterscheiden. Der NASA-Bestand (1640
   Knoten) ist dafuer laut Knoten `096669de` ausdruecklich **Heuhaufen, nicht
   Fragenquelle** — die Nadeln bleiben erfunden, damit die Bewertung
   konstruiert und die Schwierigkeit echt bleibt.
2. **Antwortqualitaet messen.** Der Deckel steht auf 10/7, das sind 9409
   Zeichen je Prompt. Ob ein Modell damit BESSER antwortet als mit 2604, ist
   nicht gemessen — bei jeder Zahl dieses Tages steht dieser Vorbehalt.
   Werkzeug vorhanden: `wissensnutzen.py`, `wissensnutzen_blind.py`.
3. Planschritte S3 (Papernetz-Bruecke), S4 (Promotion/Ebenen), S5
   (Oberflaeche), S7 (Darlegung). S1, S1b, S1c, S8, S9, S10, S11, S12 sind
   gebaut. S6 bewusst nicht (ein Rechtemodell mit einem Nutzer ist ein Schema
   ohne Schreiber).

## Was auf den Betreiber wartet

- `~/.claude.json` → `mcpServers.knowledge.env` mit
  `BEGOD_KNOWLEDGE_ACTOR=claude-code`. Gemessen: `hub/.mcp.json` ist der
  falsche Ort, die Desktop-App startet den Server inline aus `~/.claude.json`.
  Tippt er selbst, der Klient haelt die Datei offen.
- Papernetz-Umfang (9 Netze/297 Paper oder nur 2/56)
- sechs Knoten Rang 4/6 (buckeberg/Verwalterwahl) — Sachentscheidung
- 26 Hausnormen tragen weiter den alten Text. Bewusst: nur EINE davon ist ein
  Pruefkorpus-Ziel, aber 15 von 26 tragen Modalverben. Bei einer Norm IST die
  Formulierung der Inhalt, und der Pruefstein faengt verschobene Modalitaet
  nicht.

## Fallen, die heute Zeit gekostet haben

- **`knowledge_db_snapshot.py` ueberschreibt die Momentaufnahme desselben
  Tages.** Die von 12:11 (vor der Umschrift) ist dadurch weg. Rueckweg traegt
  noch ueber `knowledge_fassungen` (350 Zeilen) und `runs/umschrift_2026-08-09/`.
- **Arbeit auf einem Zweig ist fuer die naechste Sitzung unsichtbar.** Die
  Folgesitzung las `main` mit dem Stand von 11:55 und befolgte korrekt einen
  ueberholten Auftrag. Seit dem Merge liegt alles auf `main`.
- **`build_embeddings.py` achtet `BEGOD_KNOWLEDGE_DB` nicht** (fester Pfad).
- Der Selbsttest von `knowledge_recall_hook.py` war an fuenf Stellen rot, alle
  vorbestehend. Einer davon war gruen, ohne etwas zu pruefen (Testfixtur mit
  falschem Modellnamen). Lehre `L-9a45b7`.

## Grenzen

- Deckel 10/7 bleibt, bis die Antwortqualitaet gemessen ist.
- `haken/existenzpruefung.py` und `tests/test_existenzpruefung.py` gehoeren
  einer fremden Sitzung — nicht mitcommitten.
- `stash@{0}` auf main haelt eine aeltere Zwischenstufe von
  `knowledge_mcp_server.py`. Sie wird nicht gebraucht; der committete Stand
  ist vollstaendiger. Erst pruefen, bevor jemand sie zurueckholt.
