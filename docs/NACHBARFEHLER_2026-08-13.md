# Nachbarfehler — was bei vergleichbaren Systemen kaputtging

Erzeugt: 2026-08-13T07:45:34+0200
Auftrag: AUFGABE 66 (reine Recherche, kein Code, keine Tests, keine DB-Schreibzugriffe)
Methode: `git log`/`grep`/`Read` gegen den brainlehr-Quellcode im Arbeitsverzeichnis
`/Volumes/daten/Begod2026/brainlehr` (Stand des Arbeitsbaums zum Zeitpunkt der Recherche,
Branch `claude/wie-geht-es-weiter-3f4066`) + `WebSearch`/`WebFetch` gegen öffentliche
Quellen (GitHub Issues, ein Blogartikel). Keine Datenbank verändert, keine MCP-Schreibwerkzeuge
aufgerufen, keine Tests gestartet.

**Was hier NICHT geprüft wurde, steht ausdrücklich als "nicht gefunden", nicht als
"gibt es nicht"** — siehe Abschnitt am Ende jedes Fundes.

---

## Fund 1 — MCP-Speicherwerkzeug parst eigene Werkzeugaufrufe nicht

**Quelle:** GitHub, `modelcontextprotocol/servers`, Issue #2689, "Knowledge Graph
Memory Server failing to create memories", Reporter `kurokirasama`, 2025-09-06.
<https://github.com/modelcontextprotocol/servers/issues/2689>

**Wortlaut (zitiert):**
> "MCP error -32603: Unexpected non-whitespace character after JSON at position 102"

Der Fehler trat laut Bericht bei `create_entities` und `create_relations`
unabhängig von der Eingabestruktur konsequent auf — das MCP-Speicherwerkzeug
konnte grundsätzlich keine Daten mehr ablegen.

**Hat brainlehr diese Fehlerklasse?** UNGEPRÜFT.
Die brainlehr-MCP-Werkzeuge (`knowledge_add`, `lesson_record` u.a. in
`knowledge_mcp_server.py`) sind laut Auftrag tabu für Schreibzugriffe — ich habe
sie nicht live aufgerufen und daher keinen eigenen Beleg, ob ein kaputtes
JSON-Argument (z. B. unausbalancierte Anführungszeichen im Freitextfeld eines
Wissensknotens) am Server abgewiesen oder am Parsen zerbricht. Im Quelltext von
`knowledge_mcp_server.py` sind die Werkzeugsignaturen über das MCP-SDK
typisiert (Pydantic-ähnliche Parameterschemata), was diese konkrete Fehlerklasse
– Bruch beim Parsen der rohen JSON-RPC-Nutzlast – strukturell unwahrscheinlicher
macht als bei handgeschriebenem JSON-Parsing, aber das ist eine Bauform-Aussage,
kein Test dieser Fehlerklasse.

**Kosten, wenn es zuträfe:** Jeder Schreibversuch aus Claude Code heraus
(`knowledge_add`, `lesson_record`) würde lautlos oder mit kryptischer
JSON-RPC-Fehlermeldung scheitern — genau der Pfad, über den laut
`CLAUDE.md`-Reflex ("Wissen festhalten & abrufen") *jede* Sitzung am Ende
Erkenntnisse ablegt. Ein systematischer Ausfall hier bedeutet: kein einziger
Lernfund der Sitzung überlebt sie.

---

## Fund 2 — Stille Nullvektoren bei fehlgeschlagenem Embedding-Modell

**Quelle:** GitHub, `lyonzin/knowledge-rag`, README/Changelog-Abschnitt "Known
Issues" (Version, in der der Fix gelandet ist: v3.8.1), Datum am Dokument nicht
sicher datierbar (kein Commit-Datum im gefetchten Auszug).
<https://github.com/lyonzin/knowledge-rag>

**Wortlaut (zitiert):**
> "FastEmbedEmbeddings.__call__ no longer swallows exceptions and returns [[0.0]*dim, ...] when the ONNX model fails to load."

Vorher: Beim Laden-Fehlschlag des Embedding-Modells wurden Nullvektoren
gespeichert, `smart-reindex` erkannte diese Zeilen fälschlich als "bereits
indiziert" und übersprang sie beim nächsten Lauf — Anfragen lieferten
Ähnlichkeits-Ergebnisse ohne jede sichtbare Fehlermeldung.

**Hat brainlehr diese Fehlerklasse?** TEILWEISE NICHT, mit einer offenen Flanke.
`kern/embeddings.py::cosine_similarity()` (Zeile 128) prüft
`len(a) != len(b)` und liefert dann `0.0` statt eines falschen Werts — ein
Nullvektor oder ein dimensionsloser Rest würde also nicht als hoher Treffer
durchrutschen. Bei einem echten Ladefehler des Ollama-Modells wirft
`kern/embeddings.py::embed_text()` aber, soweit im Code sichtbar, keinen
expliziten Leer-Vektor zurück (kein `[0.0]*dim`-Muster gefunden) — das spricht
gegen diese konkrete stille Fehlerklasse. Die offene Flanke: Es gibt **keinen
Vergleich zwischen dem beim Schreiben verwendeten Modell (`knowledge_config`,
Schlüssel `embed_model`, gesetzt in `kern/build_embeddings.py:328`) und dem
aktuell aktiven `DEFAULT_EMBED_MODEL`** zum Zeitpunkt der Anfrage
(`kern/embeddings.py:50`) — dazu mehr in Fund 4.

**Kosten, wenn es zuträfe:** Nullvektoren mit gleicher Dimension wie echte
Vektoren würden von `cosine_similarity()` NICHT abgefangen (die Länge stimmt ja) —
Ähnlichkeit zu allem wäre 0 (weil `norm_a == 0.0`), also praktisch unsichtbar
im Ranking. Das ist der günstige Fall. Der teure Fall ist Fund 4.

---

## Fund 3 — Hook-Registrierung von Claude Code selbst ist nicht robust gegen Bearbeitung

**Quelle:** GitHub, `anthropics/claude-code`, Issue #56631, "Hook re-evaluation:
UserPromptSubmit drops after mid-session script edits; Stop hook may miss
first cold-start turn", Reporter `deserin`, 2026-05-06, Claude Code 2.1.131,
macOS Darwin 25.4.0.
<https://github.com/anthropics/claude-code/issues/56631>

**Wortlaut (zitiert):**
> "When a UserPromptSubmit hook is installed via mid-session settings.json edit AND the hook script file is subsequently edited (e.g. for bug fixes), the UserPromptSubmit registration appears to drop intermittently. Stop hook on the same install does NOT drop."

> "On a fresh session start, a Stop hook configured in settings.json may fail to fire on the very first assistant turn (or fires but is unable to read the transcript JSONL because it hasn't been flushed yet)."

**Hat brainlehr diese Fehlerklasse?** JA — brainlehr HAT sie, aber nur die
verwandte, nicht diese identische Ausprägung, und die Deckung ist lückenhaft.

Genauer: brainlehr besitzt `haken/mcp_veraltet.py`, das erkennt, wenn der
**MCP-Serverprozess** (`knowledge_mcp_server.py`) älter ist als die zuletzt
geänderte Quelldatei (Vergleich `ps lstart` gegen `mtime`, siehe
Moduldocstring) und meldet das einmal pro Sitzung. Das ist dieselbe *Klasse*
von Fehler wie im Issue — "laufender Prozess hält alten Code, Quelldatei wurde
seither repariert" — aber am MCP-Server, nicht am Hook selbst.

Für die im Issue konkret beschriebenen zwei Fehler — (a) `UserPromptSubmit`
verliert seine Registrierung nach nachträglicher Bearbeitung von
`haken/knowledge_recall_hook.py` mitten in der Sitzung, (b) der `Stop`-Hook
(`haken/knowledge_capture_hook.py`) feuert beim allerersten Zug einer neuen
Sitzung nicht oder liest ein noch nicht geschriebenes Transkript — habe ich
**keinen Mechanismus im Quelltext gefunden** (Suche nach `cold.start`,
`Kaltstart`, `nicht geflusht`, `erster Zug` in `haken/*.py` und den beiden
Hook-Dateien; die einzigen Treffer für "erster Zug" liegen in
`haken/antwort_abruf.py` und behandeln den ersten Zug der *fachlichen*
Rückruf-Logik, nicht das Feuern des Hooks selbst). Das ist ein Befund über
die Grenze der Suche, nicht ein Beweis der Abwesenheit im gesamten Repo —
siehe unten "wo gesucht, warum nichts passte".

**Kosten, wenn es zuträfe:** Fehler (a) bedeutet: Nach jeder Reparatur an
`haken/knowledge_recall_hook.py` — und die Datei wird laut `git log`
regelmäßig geändert — bekäme man mit einer gewissen Wahrscheinlichkeit
lautlos KEINEN Recall mehr, ohne Fehlermeldung, bis zum nächsten
`/hooks`-Aufruf oder Neustart. Genau die Fehlerklasse, die `mcp_veraltet.py`
für den Serverprozess schon abdeckt, aber nicht für den Hook-Eintrag selbst.
Fehler (b) bedeutet: die allererste Antwort einer neuen Sitzung würde nichts
in `knowledge.db`/`lessons_learned` festhalten — bei einer Sitzung, die genau
einen Edit macht und dann endet, wäre das der einzige Speicherversuch, der
lautlos verpufft.

---

## Fund 4 — Ollama-Embedding-Modellwechsel propagiert Dimension nicht konsistent

**Quelle:** GitHub, `mem0ai/mem0`, Issue #4695, "Ollama embedding dimensions
not propagated to Qdrant vector store (bge-m3: 1024 vs hardcoded 1536)",
Reporter `obbax`, 2026-04-04, mem0ai 1.0.9/1.0.10, Ubuntu 24.04.
<https://github.com/mem0ai/mem0/issues/4695>

**Wortlaut (zitiert):**
> "When using Ollama as the embedding provider with models that output dimensions != 1536 (e.g., bge-m3 outputs 1024, nomic-embed-text outputs 768), the Qdrant vector store collection is still created with the hardcoded default of 1536 dimensions."

Bemerkenswert: **dasselbe Modell** — `bge-m3` — ist brainlehrs
`DEFAULT_EMBED_MODEL` (`kern/embeddings.py:50`,
`os.environ.get("KNOWLEDGE_OLLAMA_EMBED_MODEL", "bge-m3")`).

**Hat brainlehr diese Fehlerklasse?** NICHT die harte Variante (kein
hartkodiertes Dimensionsfeld in der DB-Erstellung), aber eine verwandte,
schwächere Lücke ist offen.

Belegt: `schema.sql:839` und `kern/build_embeddings.py`
(`ENSURE_DIM_COLUMN_SQL = "ALTER TABLE knowledge_embeddings ADD COLUMN dim INTEGER"`,
Zeile 88) legen `dim` **pro Zeile** ab, nicht global fest — der Kommentar in
`kern/build_embeddings.py:85` nennt ausdrücklich "Modellwechsel bge-m3" als
Auftragsgrund für diese Spalte. Es gibt also KEINE feste 1536er-Annahme wie im
Fund. `cosine_similarity()` (Fund 2) fängt unterschiedliche Längen ab.

Die offene Lücke: Zwei Ollama-Modelle mit **derselben** Ausgabedimension (z. B.
zwei 1024-dim-Modelle) würden von der reinen Längenprüfung NICHT erkannt —
`knowledge_config.embed_model` wird beim Schreiben gesetzt
(`kern/build_embeddings.py:328`), aber ich habe **keine Stelle gefunden**, die
beim Lesen/Vergleichen (`haken/knowledge_recall_hook.py:625`,
`haken/suchpfad_abruf.py:178`) das gespeicherte `model`-Feld der jeweiligen
Zeile in `knowledge_embeddings` gegen das aktuell aktive
`DEFAULT_EMBED_MODEL` prüft. Ob die Kosinus-Ähnlichkeit zwischen einem
Vektor aus Modell A und einem Vektor aus Modell B danach "nur" schlecht oder
irreführend gut ist, ist inhaltlich UNGEPRÜFT — dafür bräuchte es einen
tatsächlichen Modellwechsel-Testlauf, den dieser Auftrag ausdrücklich
ausschließt (keine Schreibzugriffe, keine Tests).

**Kosten, wenn es zuträfe:** Nach einem stillschweigenden Ollama-Modell-Update
(z. B. `bge-m3` erhält ein Patch-Release mit leicht geänderter Ausgabe, oder
ein Betreiber setzt `KNOWLEDGE_OLLAMA_EMBED_MODEL` versehentlich auf ein
anderes 1024-dim-Modell) würde der Bedeutungskanal der Hybridsuche
Ähnlichkeitswerte zwischen inkompatiblen Vektorräumen berechnen — nicht
crashen, sondern falsch-plausible Zahlen liefern, die in die RRF-Fusion
(`rrf_fuse`, `kern/embeddings.py:139`) einfließen und Rang-Reihenfolgen leise
verfälschen. Das ist die teuerste Sorte Fehler: kein Absturz, kein Log-Eintrag,
nur graduell schlechtere Treffer.

---

## Fund 5 — SQLite "database is locked" bei mehreren gleichzeitigen Schreibern

**Quelle (allgemeine Fehlerklasse, mehrfach öffentlich belegt, keine einzelne
Quelle als repräsentativ herausgegriffen):** GitHub-Issues zu SQLite-Nebenläufigkeit
u. a. `mattn/go-sqlite3` #50 ("database table is locked" bei parallelen
Schreibern) und `aiidateam/aiida-core` #6532 ("SQLite backend often raises
`Database is locked` when dealing with multiple processes"); als
Erklärartikel `tenthousandmeters.com`, "SQLite concurrent writes and
'database is locked' errors" (Blogquelle, keine Firma/Werbeseite, aber auch
keine Primärquelle — als solche gekennzeichnet).

**Wortlaut sinngemäß (mehrere Quellen übereinstimmend):** SQLite erlaubt genau
einen Schreiber gleichzeitig; ohne ausreichenden `busy_timeout` wirft ein
zweiter gleichzeitiger Schreibversuch sofort `SQLITE_BUSY`/"database is
locked" statt zu warten, und SQLites eigener Busy-Retry ist nicht fair/FIFO.

**Hat brainlehr diese Fehlerklasse?** JA — **das ist der geforderte
Selbsttreffer.** brainlehr hat dieses Problem nicht nur potenziell, sondern
nachweislich schon SELBST gehabt und dokumentiert das im eigenen Quelltext.
`knowledge_mcp_server.py:146-158` (Kommentar über `_WRITE_LOCK_TIMEOUT_S`):

> "Prozessuebergreifende Schreibsperre (Auftrag 2026-08-08 Punkt 3: mehrere
> gleichzeitige knowledge_mcp_server-Prozesse kollidierten in SQLite mit
> "database is locked", weil busy_timeout=2000ms bei echtem Gedraenge nicht
> reicht und SQLites eigener Busy-Retry nicht fair/FIFO ist)."

Als Gegenmaßnahme wurde eine eigene, dateibasierte Schreibsperre NEBEN der DB
eingeführt (`_write_lock()`, `_WRITE_LOCK_TIMEOUT_S = 10.0`,
`# ponytail: harte Obergrenze -- danach ehrlicher Fehler statt endlosem
Haengen`), zusätzlich zu `PRAGMA busy_timeout=2000` (`BUSY_TIMEOUT_MS = 2000`,
Zeile 144, auch in `kern/doctor.py:153` mit `busy_timeout=5000`). Das ist ein
gebauter, aber **eigen-terminierter** Schutz — ein Schreiber, der länger als
10 s wartet, scheitert ehrlich statt zu hängen; er wird nicht automatisch
erneut versucht.

**Kosten, wenn der Rest zuträfe (Restrisiko oberhalb der 10 s):** Bei mehr
gleichzeitigen Schreibern als die Sperre in 10 s abarbeiten kann (z. B. mehrere
Agenten-Sitzungen, die zeitgleich `knowledge_add`/`lesson_record` aufrufen,
plus `kurator_taeglich.py` im Hintergrund) würde ein Schreibversuch mit
explizitem Fehler abbrechen statt lautlos zu verlieren — das ist bereits die
bessere Variante (sprechender Fehler statt Silent-Success, Walkthrough-Doktrin
Punkt 5), kostet aber eine fehlgeschlagene Wissensaufnahme, die der Aufrufer
bemerken und wiederholen muss.

---

## Fund 6 — Retrieval erkennt keine "veraltete" Erinnerung (Implicit Conflict)

**Quelle:** arXiv, "STALE: Can LLM Agents Know When Their Memories Are No
Longer Valid?", <https://arxiv.org/html/2605.06527v1> (akademische Vorab-
Veröffentlichung, kein Peer-Review-Siegel geprüft — als solche gekennzeichnet).
Ergänzend, als Sammelreferat ohne eigene Primärquelle zitiert: ein
Übersichtsartikel (sitepoint.com) beschreibt "Implicit Conflict" als
Fehlermodus, bei dem eine spätere Beobachtung eine frühere Erinnerung
entwertet, ohne dass eine explizite Verneinung existiert — Erkennung würde
Kontext-Inferenz statt reinem Abgleich brauchen. Die sitepoint-Quelle war zum
Zeitpunkt der Recherche per `WebFetch` nicht direkt abrufbar (HTTP 403); der
Wortlaut stammt aus der Suchergebnis-Zusammenfassung, nicht aus dem
Volltext — entsprechend vorsichtig zu behandeln, nicht wörtlich zitierbar.

**Hat brainlehr diese Fehlerklasse?** UNGEPRÜFT, mit einem Hinweis, der
dagegen spricht, aber keinen Beleg liefert.

brainlehr hat ein `knowledge_zurueckziehen`-Werkzeug (in der MCP-Werkzeugliste
sichtbar) und eine `trust_score`-Funktion (`knowledge_trust_score`) — beides
Mechanik, die AUF eine spätere Entwertung reagieren KANN, wenn ein Mensch oder
ein Agent sie aktiv auslöst. Was fehlt und wozu ich keinen Beleg im Code
gefunden habe: eine automatische Erkennung, dass zwei gespeicherte
Wissenseinträge sich inhaltlich widersprechen, OHNE dass einer der beiden das
andere per Relation explizit als "ersetzt" markiert. Das ist dieselbe Lücke,
die die Quelle beschreibt: Implizite Widersprüche brauchen Verständnis des
Inhalts, keine reine ID-Verknüpfung. Ich habe nicht systematisch nach einer
Widerspruchserkennung gesucht (das wäre eine inhaltliche Analyse über
`kern/`-Module, die den Rahmen dieses Auftrags sprengt) — als UNGEPRÜFT
markiert, nicht als "gibt es nicht".

**Kosten, wenn es zuträfe:** Zwei sich widersprechende Lehren/Knoten könnten
beide mit hohem `trust_score` gefunden werden und der Recall-Hook liefert dem
Agenten beide, ohne dass der Widerspruch markiert ist — der Agent müsste ihn
selbst im Fließtext bemerken. Bei einer Regel, die einmal so und einmal anders
im Speicher steht (z. B. zwei verschiedene Werte für denselben Schwellenwert
aus unterschiedlichen Sitzungen), wäre das ein leiser, aber teurer Fehler:
falsches Wissen sieht genauso vertrauenswürdig aus wie richtiges.

---

## Wo gesucht wurde und wo nichts passte (ausdrücklich, wie gefordert)

- **Fund 3, Kaltstart-/Registrierungslücke:** Grep auf `cold.start`,
  `Kaltstart`, `nicht geflusht`, `erster Zug`, `Registrierung`, `watchdog`
  über `haken/*.py` und die Wurzeldatei `knowledge_mcp_server.py`. Getroffen
  wurden nur fachliche Treffer in `haken/antwort_abruf.py` (Konversationslogik,
  nicht Hook-Feuerung). Keine Datei mit einem Mechanismus gefunden, der prüft,
  ob der `Stop`- oder `UserPromptSubmit`-Hook in dieser Sitzung schon mindestens
  einmal gefeuert hat.
- **Fund 4, Modell-Konsistenzprüfung beim Lesen:** Grep auf `embed_model` über
  `kern/*.py` und `haken/*.py`. Alle vier Treffer beziehen sich auf das
  SCHREIBEN/Ablegen des Konfigurationswerts (`build_embeddings.py`,
  `messparameter.py`, `nachtlaeufer.py`) oder eine unrelated Anmerkung in
  `knowledge_recall_hook.py:124` über einen fehlenden Datenschutz-Schlüssel.
  Keine Stelle vergleicht `embed_model` aus `knowledge_config` mit
  `DEFAULT_EMBED_MODEL` zur Anfragezeit.
- **Fund 6, Widerspruchserkennung:** Keine gezielte Suche über den vollen
  Inhalt der `kern/`-Module (das wäre eine inhaltliche Analyse, kein
  Fundstellen-Grep) — bewusst als UNGEPRÜFT statt NICHT HAT eingeordnet.
- **Fund 1, MCP-JSON-Parsing:** Kein Live-Aufruf der Schreibwerkzeuge (laut
  Auftrag verboten) — daher UNGEPRÜFT statt eines echten Funktionstests.

---

## Was daraus zu tun wäre — nach Aufwand sortiert, NICHT umgesetzt

1. **Kleinster Aufwand:** Bei `haken/knowledge_recall_hook.py` (Zeile ~625,
   dort wo `cosine_similarity()` gegen `unpack_embedding()` aufgerufen wird)
   und in `haken/suchpfad_abruf.py:178` einen Vergleich der Zeilen-Spalte
   `knowledge_embeddings.model` gegen `embeddings.DEFAULT_EMBED_MODEL`
   ergänzen und bei Abweichung die Zeile ausschließen statt stillschweigend
   zu vergleichen (schließt die in Fund 4 offene Flanke). Eine Bedingung,
   keine neue Tabelle.
2. **Kleiner Aufwand:** In `haken/mcp_veraltet.py` (das die Melde-Bauform
   schon hat: "hoechstens 1x pro Session, IMMER exit 0, nur melden") einen
   zweiten, analogen Melder ergänzen, der beim ersten `UserPromptSubmit`
   einer Sitzung einen Marker schreibt und beim `Stop`-Hook prüft, ob dieser
   Marker existiert — fehlt er, ist das ein Indiz für die in Fund 3
   beschriebene Registrierungslücke von Claude Code selbst (nicht behebbar,
   aber meldbar, dieselbe Idee wie schon für den veralteten Serverprozess).
3. **Mittlerer Aufwand:** Ein Gegenlese-Testfall (kein Testlauf JETZT, aber ein
   künftiger `tests/`-Fall), der `cosine_similarity()` mit zwei gleich langen,
   aber aus verschiedenen `model`-Werten stammenden Vektoren füttert und
   erwartet, dass Fund-4-Fix (Punkt 1) sie ausschließt — Grenzwertprüfung
   "gleiche Länge, verschiedenes Modell" fehlt heute nachweislich.
4. **Größerer, unklarer Aufwand:** Eine Heuristik für Fund 6
   (Widerspruchserkennung zwischen zwei hoch bewerteten Treffern derselben
   Anfrage) — das ist ein inhaltliches Problem (braucht vermutlich einen
   LLM-Vergleichsschritt, kein reiner SQL-Filter) und sollte zuerst an drei
   bis fünf echten Fällen aus `knowledge.db` gemessen werden, bevor irgendein
   Code entsteht — sonst wird an einem Verdacht gebaut, nicht an einem Befund.
