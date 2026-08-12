# Vergleich mit Gattungsnachbar eugeniughelbur/obsidian-second-brain

Datum: 2026-08-13T00:00:00+0200
Auftrag: Lese- und Vergleichsauftrag, kein Produktivcode geändert.
Quelle: GitHub, `raw.githubusercontent.com`, Branch `main`, gelesen als Rohtext (kein zusammenfassender Abruf) am 2026-08-13.
Lizenz des Nachbarn: MIT (README-Badge, ungeprüft gegen LICENSE-Datei im Detail — nur der Badge-Text wurde gelesen). Nichts wörtlich übernommen, alles unten in eigenen Worten mit Fundstelle (Dateipfad + Zeile im gelesenen Rohtext).

## 1. Was gelesen wurde (Rohtext, nicht zusammenfassend)

| Datei | Zeilen | gelesen |
|---|---|---|
| `README.md` | 954 | vollständig, Kernaussage Z.794 |
| `scripts/eval/BASELINE.md` | 242 | vollständig |
| `scripts/eval/README.md` | 56 | vollständig |
| `scripts/eval/BENCHMARK.md` | 120 | vollständig |
| `scripts/eval/corpus.py` | 306 | grep + Funktionsköpfe, nicht jede Zeile |
| `scripts/eval/retrieval_eval.py` | 395 | grep + Kernfunktionen (`_rank_of_gold`, `evaluate`, recall/MRR-Formel) |
| `integrations/obsidian-mcp-server/vault_ops.py` | 1164 | Fusion/Freshness-Abschnitt (Z.140–650) vollständig, Rest nicht |

**Nicht gelesen** (bewusst ausgelassen, weil für den Auftrag nicht nötig oder Zeitbudget): `DEMOS.md`, `CHANGELOG.md`, `references/freshness-policy.md`, `scripts/eval/semantic_search.py` (Index-Bau), `scripts/freshness_lint.py`, `integrations/obsidian-mcp-server/server.py`, `LICENSE`-Volltext, der Rest von `vault_ops.py` nach Zeile 650. Sternezahl (3969) und Datum des letzten Pushs (2026-08-08) aus dem Auftrag übernommen, nicht selbst nachgemessen — dafür wäre die GitHub-API mit Zeitstempel nötig gewesen, was der Lese-Auftrag nicht verlangt.

## 2. Bauform der Rangfolge

Fundstelle: `integrations/obsidian-mcp-server/vault_ops.py`, Funktionen `_semantic_fuse` (Z.518–579) und `search` (Z.582ff), Konstanten Z.223–256.

**Grundmechanik ist dieselbe wie bei uns**: Reciprocal Rank Fusion, `score = 1/(K + rang_lexikalisch) + gewicht/(K + rang_semantisch)`, K=60. Ein Kanal, der einen Pfad nicht führt, trägt für diesen Pfad schlicht 0 bei — keine Strafe, nur Abwesenheit. Insofern ist die Fusionsformel technisch identisch mit unserer `rrf_fuse`.

**Drei Stellschrauben, die bei uns fehlen und den Unterschied machen:**

1. **Asymmetrisches Gewicht statt 1:1.** Der semantische Kanal zählt 20-fach (`_RRF_SEMANTIC_WEIGHT = 20.0`), der Stichwortkanal einfach. Das Gewicht wurde je Einbettungsmodell gemessen ("w=3 für mxbai; w=5/10/20 je strikt besser auf bge-m3") — kein fester Universalwert, sondern ein modellabhängiger Sweep-Treffer.
2. **Der Stichwortkanal ist auf seine Spitze begrenzt, nicht abgeschnitten auf einen Treffer.** `_FUSE_LEX_DEPTH = 25`: nur die obersten 25 Stichwort-Ränge dürfen überhaupt mitstimmen (Kommentar Z.242–246: "der Schwanz der Stichwort-Rangliste ist bei Paraphrasen-Anfragen reines Termfrequenz-Rauschen"). Das ist weder unser bisheriges `rrf_fuse` (alle Ränge zählen gleich) noch unser gemessenes `fuse_semantic_led` (nur der EINE beste Stichwort-Treffer zählt) — sondern ein Mittelweg: die besten 25 zählen, aber 20-fach schwächer als Bedeutung.
3. **Anfrage-abhängige Weiche vor der Fusion.** Bei genau einem Suchbegriff (`len(terms) == 1`) wird Bedeutung ganz abgeschaltet, reine Stichwortsuche (Z.600–605, Begründung: "ein einzelner exakter Begriff ist ein Nachschlagen, keine Frage — nackte Begriffe betten fast bedeutungslos ein"). Das ist keine Fusionsregel, sondern eine Vor-Klassifikation der Anfrage.

**Frischesignale** (Fundstelle Z.154–198, `_freshness_rerank` / `_freshness_weight`): laufen NACH der Fusion, als Nachsortierung, nicht als dritter Fusionskanal.
- Notizen mit als "veraltet" markiertem Status werden immer abgewertet (`_STATUS_FADE`), unabhängig von der Anfrage.
- Eine Notiz, die eine andere per Wikilink explizit als abgelöst markiert, wertet die abgelöste Notiz ab (Rückwärtskante).
- Nur bei erkannter "was gilt jetzt"-Absicht (Wortliste `_CURRENT_INTENT`) wird zusätzlich nach Alter gewichtet: Standardband 0,92–1,0 (nur Beinah-Gleichstand betroffen), bei "jetzt"-Absicht 0,6–1,0 mit ~90-Tage-Halbwertszeit.

**Was mit einem Kanal passiert, der nichts beiträgt (die explizit gestellte Frage):**
- Semantischer Kanal komplett weg (kein Index, Ollama nicht erreichbar, jeder Fehler): `_semantic_fuse` gibt `None` zurück, der Aufrufer nutzt reine Stichwortsuche — stiller Komplettausfall auf die Ausweichebene, keine Fehlermeldung an den Nutzer, keine leere Ergebnisliste.
- Stichwortkanal trägt für einen einzelnen Pfad nichts bei (z. B. weil eine russische Anfrage keinen Begriff mit einer englischen Notiz teilt): dieser Pfad bekommt einfach den lexikalischen Summanden 0 — er verschwindet nicht aus der Fusion, er verliert nur den (ohnehin kleinen, weil 20-fach schwächer gewichteten) lexikalischen Anteil. Weil Bedeutung 20-fach zählt, dominiert sie in diesem Fall ohnehin fast vollständig; das eigentliche Sicherheitsnetz gegen einen komplett unbrauchbaren Index ist Punkt „semantischer Kanal weg" oben, nicht diese Fusionsregel.
- Umgekehrt beobachtet und dokumentiert (Z.247–252, BASELINE.md Z.151–167): Der semantische Index baut sich nicht selbst neu — eine nach dem letzten Indexlauf geänderte Notiz ist für den Bedeutungskanal unsichtbar. Bei einer real gemessenen Vault-Instanz waren so 29 % (525 von 1828 Notizen) ungeprüft blind, ohne Warnung, bis ein Abdeckungs-Check eingebaut wurde. Das ist ein eigenständig gefundener Fehler des Nachbarn, keine Ranganpassung — aber lehrreich, weil er zeigt: die 13→63-%-Zahl selbst war zeitweise auf einer 71-%-vollständigen Basis gemessen und änderte sich nach Nachbau NICHT (RU/ES recall@10 blieb 0,625) — die Indexlücke war nicht die Ursache der Sprachlücke.

## 3. Bauform der Messung

**Zwei getrennte, nicht austauschbare Messgrundlagen — das ist der wichtigste Fund für uns:**

### a) Die Schlagzahlen im README (13→63 %, keyword@10=1.0, paraphrase@10=77 %)
Fundstelle: `README.md` Z.794, Grundlage `scripts/eval/BASELINE.md` Z.13–14: gemessen auf des **Betreibers eigenem, privaten Vault mit ~2.350 Notizen**, Stichtag 2026-07-11, Modell `bge-m3`, Fusionsgewicht 20. Die Fallmengen: 35 englische Paraphrasen-Fragen, 30 englische Stichwort-Nachschlagen, 16 handgeschriebene Russisch/Spanisch-Paraphrasen — **alle drei Fallmengen sind per `.gitignore` ausgeschlossen**, weil sie echten Notizinhalt enthalten (BASELINE.md Z.9–10). Diese Zahlen sind für niemanden außerhalb nachvollziehbar oder nachrechenbar. Der Nachbar sagt das selbst offen (BENCHMARK.md Z.14–17: "jede Zahl war eine Behauptung, die niemand von außen prüfen, reproduzieren oder schlagen konnte").

Fallgenerierung (`scripts/eval/README.md` Z.20–24): Notizen werden gestichprobt, ein Sprachmodell schreibt je Notiz eine Frage, deren Antwort in genau dieser Notiz steht, unter bewusster Vermeidung der Titelwörter der Notiz. Die Ziel-Notiz selbst ist die Goldantwort — keine unabhängige Verifikation, kein Mehrfach-Gold.

recall@k-Berechnung (`retrieval_eval.py` Z.194 `_rank_of_gold`, Z.319 `recall = Anteil der Fälle mit 0 < rang ≤ k`): Standardformel, ein Gold-Treffer pro Frage, MRR = Mittelwert von 1/Rang (0 bei Verfehlung). k-Werte 1/3/5/10.

### b) Die reproduzierbare Baseline (das eigentlich Wertvolle für uns)
Fundstelle: `scripts/eval/BENCHMARK.md` vollständig, `scripts/eval/corpus.py`.

Der Nachbar hat selbst erkannt, dass (a) unprüfbar ist, und dagegen einen **deterministisch generierten synthetischen 300-Notizen-Korpus** gebaut, der IM Repo mitgeliefert wird (`corpus.py --out <pfad>`, fester Seed, Hash prüfbar über `corpus.py --manifest`). Kein echter Inhalt, jede Notiz trägt `synthetic: true`.

Baubauform (`corpus.py`, `TOPICS`-Liste + `build()`): Für jedes Thema wird EINE kurze kanonische Notiz erzeugt und mehrere längere Rivalinnen (Tagebucheinträge, Meeting-Notizen, Recherche-Schreiben), die das Thema öfter erwähnen als die kanonische Notiz selbst — der Generator erzwingt mindestens drei solcher Rivalinnen pro Thema (BENCHMARK.md Z.56). Das bildet gezielt das Muster nach, an dem reine Termfrequenz-Rangfolge in der Praxis scheitert (Frequenz-Notiz schlägt die richtige Notiz). Gold ist per Konstruktion bekannt, keine Handbewertung.

Drei getrennte Fallmengen (BENCHMARK.md Z.61–67): `keyword` (12 Fälle, der eine unterscheidende Begriff), `paraphrase` (12, Thema ohne Titelwörter beschrieben), `multilingual` (24, dieselben Paraphrasen auf Spanisch/Russisch gegen englische Notizen). Die Trennung ist bewusst: „eine einzelne Schlagzahl über alle drei versteckt Zielkonflikte" (Z.100–102) — bei ihnen verbesserten mehrere Änderungen Paraphrase und verschlechterten Mehrsprachigkeit gleichzeitig, exakt das Muster, das wir mit `fuse_semantic_led` selbst gemessen haben.

**Auf diesem 300-Notizen-Korpus liegen die Zahlen deutlich anders** als im README-Schlagwort (BENCHMARK.md Z.74–81, `v0.14.0`, Korpus-Hash `a932e94f850830e9`):

| Fallmenge | Engine | recall@1 | recall@10 | MRR |
|---|---|---|---|---|
| keyword | lexikalisch | 25,0 % | 100,0 % | 0,500 |
| keyword | hybrid | 25,0 % | 100,0 % | 0,500 |
| paraphrase | lexikalisch | 25,0 % | 58,3 % | 0,375 |
| paraphrase | hybrid | 66,7 % | 83,3 % | 0,711 |
| multilingual | lexikalisch | 4,2 % | 8,3 % | 0,062 |
| multilingual | hybrid | 62,5 % | 75,0 % | 0,652 |

Das ist NICHT dieselbe Zahl wie „13→63 %" — auf dem reproduzierbaren Korpus liegt Mehrsprachigkeit bei 8,3 %→75,0 % recall@10 (bzw. Ausgangswert lexikalisch, nicht direkt vergleichbar mit dem Vorher-Wert 13 % aus dem privaten Vault, der schon mit einer älteren Fusion gemessen wurde). Wer nur den README-Satz zitiert, zitiert die unprüfbare private Zahl, nicht die nachrechenbare.

**Der Auftrag nannte „rund 300 Notizen im Repo" — das trifft auf Zusammenhang (b), NICHT auf die Schlagzahlen aus Abschnitt (a) zu.** Das ist eine Präzisierung des Auftragstexts: Die zitierten Prozentzahlen (13→63, keyword=1.0, paraphrase=77 %) stammen aus dem privaten 2.350-Notizen-Vault; der 300-Notizen-Korpus liefert eigene, andere Zahlen und ist der Teil, der bei uns tatsächlich nachbaubar wäre.

## 4. Was übertragbar ist, was nicht — mit Begründung

### Übertragbar (Bauform, kein Code, keine Zahl)

**a) Reproduzierbarer synthetischer Korpus statt "Adressen tragen 0,9 % der Fragen".** Unser Korpus-Problem ist strukturell identisch mit dem, das der Nachbar selbst als Schwäche benannte (BENCHMARK.md Z.14–17) und behoben hat. Ein deterministischer Generator mit Kanon-Notiz + mehreren Rivalinnen pro Thema, fester Seed, Hash-Manifest zur Reproduktionsprüfung — das ist ohne Sprachmodell-Kosten und ohne echte Nutzerdaten nachbaubar und würde unser 0,9-%-Problem direkt lösen: wir hätten beliebig viele Zielangaben statt der seltenen Adress-Treffer. Das ist laut Auftrag „womöglich wertvoller als die Rangfolge" — nach Lektüre teile ich diese Einschätzung: das Verfahren ist eigenständig von der Rangfolgen-Bauform und unabhängig von Sprache/Einbettungsmodell nachbaubar.

**b) Getrennte Fallmengen statt einer Gesamtzahl.** Unser eigener Befund (Bedeutung-führt behebt den Leitfall, kostet 14 andere Fälle) ist exakt das Muster, das der Nachbar mit der Drei-Mengen-Trennung sichtbar macht, statt es hinter einer Durchschnittszahl zu verstecken. Unabhängig von Korpusgröße oder Sprache übertragbar: eine Kennzahl je Fehlerart (Stichwort/Paraphrase/Sprache) statt einer.

**c) Anfrage-abhängige Vorweiche bei genau einem Suchbegriff.** Die Regel „ein einzelner Token ist ein Nachschlagen, keine Frage → Bedeutung abschalten" ist eine reine Textanalyse der ANFRAGE, unabhängig von Korpus, Sprache oder Einbettungsmodell. Prüfbar auf unseren eigenen Fällen ohne Neumessung des Bestands nötig.

**d) Nachsortierung nach Frische als eigener Schritt nach der Fusion, nicht als dritter Summand in der RRF-Formel.** Trennt zwei verschiedene Fragen (was ist relevant / was gilt noch), die wir laut Auftragskontext ("Freigabe-Achse", Commit-Historie) ohnehin schon konzeptionell auseinanderhalten.

### Nicht direkt übertragbar — und warum (angeforderter Widerspruchs-Check)

Der Auftrag verlangt ausdrücklich die Klärung: Bedeutung-führt-Modelle (dort das 20:1-Gewicht) funktionieren beim Nachbarn, kosteten uns 14 Fälle. Nach Lektüre sind es **nicht dieselbe Änderung**, sondern zwei verschiedene Eingriffstiefen:

1. **Unser gemessenes `fuse_semantic_led` reduziert den Stichwortkanal auf GENAU EINEN Beitrag** (nur der beste Treffer zählt). Der Nachbar reduziert ihn auf die **obersten 25 Ränge, gewichtet 1:20** — das lässt dem Stichwortkanal noch differenzierten Einfluss auf Beinah-Gleichstände, nur eben stark gedämpft. Das ist ein sanfterer Eingriff als unserer, keine bloße Parameterwahl am selben Mechanismus. Unsere 14 verlorenen Fälle waren laut Auftrag genau die, in denen NUR der Stichwortkanal den richtigen Treffer trug (7 von 44 Zielinstanzen) — bei einer 1-Treffer-Reduktion verliert man diesen Kanal für alle Fälle jenseits des einen besten Rangs; bei einer Tiefe-25-plus-Gewicht-20-Lösung bleibt der Kanal für diese Fälle beteiligt, nur unterlegen statt abwesend.
2. **Anderes Einbettungsmodell.** Der Nachbar misst durchgehend mit `bge-m3`, einem explizit mehrsprachigen Modell, und beschreibt sogar, dass frühere Modelle (`mxbai-embed-large`) ein deutlich niedrigeres Fusionsgewicht (w=3) brauchten, um nicht zu schaden. Das Gewicht 20 ist an DIESES Modell gekoppelt, nicht universell. Ob unser Bedeutungskanal (Modell laut Auftrag nicht genannt — hier nicht geprüft, da außerhalb der gelesenen Dateien) dieselbe mehrsprachige Trennschärfe hat, ist offen und wäre vor jeder Gewichtsübernahme zu messen, nicht anzunehmen.
3. **Anderer Korpus/Sprache.** Die 300-Notizen-Baseline ist Englisch-Notizen gegen Fremdsprachen-Anfragen (BENCHMARK.md Z.112: „Multilingual set testet sprachübergreifende Anfragen gegen englischen Inhalt, nicht einen mehrsprachig geschriebenen Vault"). Unser Leitfall (deutsche Anfrage, 1638 englische NASA-Knoten) hat dieselbe Form — das spricht eher FÜR Übertragbarkeit dieses speziellen Testmusters, nicht dagegen.

**Kurz:** Die Widerspruchs-Auflösung ist nicht „anderer Fall, andere Antwort", sondern „gleiche Grundidee (Bedeutung stärker gewichten), zwei verschiedene Eingriffstiefen". Was bei uns 14 Fälle kostete, war die scharfe Variante (Stichwort auf 1 Treffer reduziert). Die vom Nachbarn gemessene, gemäßigtere Variante (Tiefenbegrenzung + Gewicht statt Kappung auf einen Treffer) ist ungetestet bei uns — sie zu messen ist eine neue, eigenständige Messung, keine Bestätigung der vorliegenden Zahlen.

## 5. Vorsicht vor dem zu guten Fund

Die README-Schlagzahlen (13→63 %, „5x-Gewinn") lesen sich wie eine direkte Blaupause für unser Problem. Nach Prüfung der Rohquelle: Sie stammen aus einem für Dritte nicht nachprüfbaren privaten Korpus, und die einzige öffentlich nachrechenbare Fassung (BENCHMARK.md) liefert andere, niedrigere Ausgangswerte und ein anderes Zielformat (8,3 %→75,0 % statt 13 %→63 %). Das ist kein Beleg für Täuschung — der Nachbar benennt die Einschränkung selbst und hat aktiv einen zweiten, ehrlicheren Maßstab gebaut — aber es ist der Unterschied zwischen einer Marketingzahl im README und der Zahl, die tatsächlich zum Nachrechnen einlädt. Für uns zählt nur Letztere als Vergleichsgrundlage.

## Zusammenfassung für die Weiterarbeit

- Wertvoller als die Rangfolgen-Formel: der reproduzierbare 300-Notizen-Generator (Kanon + Rivalinnen-Muster) als Vorbild für einen eigenen synthetischen Korpus — löst unser 0,9-%-Problem strukturell.
- Bei der Rangfolge: die Idee ist nicht „Bedeutung führt total", sondern „Bedeutung 20-fach gewichtet, Stichwort auf Tiefe 25 begrenzt aber nicht auf einen Treffer" — ein Mittelweg zwischen unserem bisherigen `rrf_fuse` und unserem gemessenen `fuse_semantic_led`, den wir noch nicht gemessen haben.
- Vor jeder Übernahme des Gewichts 20: eigenes Einbettungsmodell und eigene Fallmengen prüfen, nicht die fremde Zahl kopieren — der Nachbar selbst zeigt, dass das Gewicht modellabhängig ist (w=3 vs. w=20 je nach Modell).
