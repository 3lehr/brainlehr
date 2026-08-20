# Lehren-Mechanismus-Prüfung 2026-08-20T00:00:00+0200

Prüfung zweier Lehren aus `melder/ohne_mechanismus.py` (Stand: 59 Einträge) auf
Mechanisierbarkeit eines Auslösers. Quelle: `lessons_learned` (Wissensspeicher),
Feld für Feld gelesen, nicht per grep.

## L-1056bb — Subagent endet den Zug, während die Arbeit noch läuft

### 1. Die Vorkommen einzeln (Umstand, nicht Ergebnis)

- **Vorkommen 1** (2026-08-11T20:29:50Z, drei von vier Sonnet-Subagenten):
  Jeder Agent hatte einen Lauf gestartet, der länger dauerte als sein
  verbleibender Zug, und beendete den Zug mit einem Satz wie „ich warte auf
  die Benachrichtigung des Überwachers" — der Lauf war zu diesem Zeitpunkt in
  den Hintergrund verschoben.
- **Vorkommen 2** (2026-08-11T22:47:14+0200, Korrektur des ersten Befunds):
  Der Auftrag an den nächsten Agenten verlangte „im Vordergrund, großzügiges
  Zeitlimit" — eine Haltungsanweisung ohne Zahl. Der Agent rief Bash ohne
  `timeout`-Parameter auf; das Werkzeug bricht nach 120 s selbständig ab und
  verschiebt danach von sich aus in den Hintergrund.
- **Vorkommen 3** (2026-08-11T22:59:29+0200, zweite Korrektur): Der
  Auftraggeber selbst startete denselben Lauf mit `timeout=600000` — dem
  Höchstwert des Werkzeugs — und wurde trotzdem in den Hintergrund
  verschoben, weil die tatsächliche Laufzeit über 600 s lag. Die Dauer war
  zuvor geschätzt (78 Fälle × 2,7 s ≈ 4 min), nicht gemessen.
- **Vorkommen 4** (2026-08-15T08:34:02Z, sechs Fälle an einem Tag): In fünf
  der sechs Aufträge stand die Auflage „Vordergrund, timeout=600000, nicht
  warten" bereits wörtlich im Auftragstext — trotzdem endete der Agent mit
  Wartesatz. Der sechste Fall lieferte die Erklärung: die verlangte
  Suite braucht 628 s, das Höchstmaß des Werkzeugs ist 600 s. Die Auflage war
  durch den Auftrag selbst nicht erfüllbar.

**Befund zur Protokollqualität:** Die vier Einträge protokollieren den
Umstand zunehmend genauer (von „er wartet" über „Parameter fehlt" zu „Dauer
über Werkzeug-Maximum"), sind also nicht bloße Ergebnis-Wiederholungen — dieser
Fall ist für alle vier Vorkommen mit Umstand belegt.

### 2. Kandidatenorte für einen Auslöser

1. Stop-Hook (bei Sitzungsende/Turn-Ende eines Agenten)
2. PreToolUse auf Bash (vor dem Start eines Laufs)
3. PostToolUse auf Bash (nachdem ein Lauf automatisch in den Hintergrund
   verschoben wurde)
4. pre-push/commit-msg-Hook
5. Datenbank-Trigger
6. Zähler ohne Sperre (z. B. Anzahl „im Hintergrund verschoben" pro Sitzung)
7. Auftrags-Textprüfung durch den Auftraggeber selbst vor dem Versenden
8. gar keiner, weil strukturell im SDK verankert

### 3. Tabelle Vorkommen × Kandidat

| Kandidat | Vorkommen 1 | Vorkommen 2 | Vorkommen 3 | Vorkommen 4 |
|---|---|---|---|---|
| Stop-Hook | Nein — der Zug ist beim Hook-Aufruf bereits beendet, der Hook kann den Wartesatz zwar erkennen, aber niemanden mehr zum Weiterlaufen bewegen; er käme erst beim NÄCHSTEN Wiederaufnehmen zum Tragen | Nein — gleicher Grund | Nein — hier lief sogar der Hauptthread selbst, kein Subagent-Stop betroffen | Teilweise — könnte im Bericht des Agenten nach Wartesätzen wie „waiting for" suchen und den Abschluss verweigern, würde aber Fall 6 (strukturell unerfüllbar) nicht lösen, nur Fall 1–5 abfangen |
| PreToolUse auf Bash | Ja, wenn er `timeout` erzwingt oder mit Vorgabewert 600000 füllt | Ja — genau dieser Fehlerpunkt (Parameter fehlte) ist mechanisch abfangbar: Vorgabewert setzen statt auf Erinnerung verlassen | Nein — Parameter war bereits maximal gesetzt, das Problem lag hinter dem Werkzeuglimit, nicht am Parameter | Nein für Fall 6 — jeder erlaubte Wert liegt unter der echten Laufzeit von 628 s, ein Hook kann die Dauer vorab nicht kennen |
| PostToolUse auf Bash | Ja — könnte erkennen „Lauf wurde automatisch backgroundet" und dem Agenten sofort eine synchrone Wartepflicht auferlegen statt Turn-Ende zuzulassen | Ja, gleicher Mechanismus | Ja — würde zumindest sichtbar machen, dass der Hintergrundwechsel erzwungen war, nicht gewählt | Ja, einzig hier greifbar: der Hook kann erkennen, dass ein Lauf > 600 s lief, und dem AUFTRAGGEBER (nicht dem Agenten) melden, dass die Auflage strukturell unerfüllbar war |
| pre-push/commit-msg | Nein — Problem entsteht vor jedem Commit, es gibt zu dem Zeitpunkt oft noch keinen Commit-Versuch | Nein, gleicher Grund | Nein | Nein — die uncommittete Arbeit ist das Symptom, nicht der Ort des Fehlers |
| DB-Trigger | Nein — kein Datenbankvorgang beteiligt | Nein | Nein | Nein |
| Zähler ohne Sperre | Teilweise — ein Zähler „Turns mit Wartesatz + uncommitteter Änderung" hätte Muster früher sichtbar gemacht, aber erst im Rückblick, nicht vorab | Teilweise, gleiche Einschränkung | Nein — Einzelfall, kein wiederkehrendes Muster zum Zeitpunkt des Vorkommens | Ja als Frühwarnung — sechs Fälle an einem Tag hätten einen Schwellwert-Zähler ausgelöst, der den Auftraggeber vor dem siebten Versuch stoppt |
| gar keiner (strukturell) | Nein — Fehlerpunkt (Wartesatz + Timeout-Semantik) war real behebbar | Nein | Ja teilweise — die Werkzeuggrenze 600 s ist eine feste SDK-Eigenschaft, kein Auftrags- oder Codefehler | Ja für den Kernfall — ein Subagent kann strukturell nicht auf eine Benachrichtigung warten, die erst nach seinem Turn-Ende eintrifft; das ist eine Eigenschaft des Ausführungsmodells, kein Ort im Repo kann das beheben |

### 4. Urteil

**Teilweise mechanisierbar, an zwei verschiedenen Orten, für zwei verschiedene
Teilursachen — und ein Rest bleibt strukturell.**

- Der Teil „Parameter falsch/fehlend gesetzt" (Vorkommen 2) ist mechanisierbar:
  **PreToolUse auf Bash**, das bei absehbar langen Läufen automatisch
  `timeout=600000` statt des Default-Timeouts erzwingt, statt sich auf eine
  Anweisung im Fließtext zu verlassen.
- Der Teil „Lauf überschreitet das Werkzeug-Maximum" (Vorkommen 3 und der
  Kernfall in Vorkommen 4) ist **nicht durch einen Hook lösbar**, weil die
  Dauer erst nach dem Start bekannt ist — das ist keine Struktur, sondern eine
  Messgröße, die vorher fehlt. Der einzige wirksame Ort ist **außerhalb des
  Auslöser-Rasters**: der Auftrag selbst muss die Laufzeit vorher MESSEN
  (nicht schätzen) und einen Lauf > ca. 500 s in Teilaufgaben zerlegen, die
  einzeln unter das Limit passen — das ist eine Auftrags-Disziplin, keine
  Mechanik.
- Der Teil „Subagent kann nach Turn-Ende keine Benachrichtigung mehr
  empfangen" ist **nicht mechanisierbar innerhalb dieses Repos**: Es ist eine
  Eigenschaft des Ausführungsmodells (ein beendeter Turn hat keinen Zustand
  mehr, in dem „warten" stattfinden könnte). Kein Hook, Trigger oder Zähler in
  brainlehr oder einem anderen Repo kann einem bereits beendeten Prozess eine
  Nachricht zustellen. Diese Teilursache gehört als **Grenze in die Lehre**
  geschrieben, nicht als offene Aufgabe.

## L-bbd7fb — Entfernter Eingang, Gesamtbewertung behauptet unverändert dieselbe Reichweite

### 1. Die Vorkommen einzeln (Umstand, nicht Ergebnis)

Das Feld `occurrences` der Lehre steht auf 3, der Volltext beschreibt jedoch
vier konkret benannte Code-Stellen (Erstfund + drei „Wiederholung"-Absätze,
von denen der zweite zwei Stellen zugleich nennt). Beide Zahlen werden hier
genannt, ohne sie zu glätten — das ist selbst ein Befund zur
Protokollqualität dieser Lehre.

- **Fund A** (Ersteintrag, `lib/core/calculations/ampel_config.dart`,
  `overallAmpelConfigured`): Eine geschätzte Eckentemperatur wurde an ihrem
  Erzeugungsort entfernt, weil sie unbelegt war (keine Infrarot-Messung). Die
  Prüfung der Konsumenten dieses Werts blieb aus — vier von fünf Teilurteilen
  lagen bereits hinter `if (hasIrData)`, sodass im Basis-Modus nur noch die
  Raumluftfeuchte das Gesamturteil bildete.
- **Fund B** (Wiederholung 2026-08-02T07:30:51+0100, erste Stelle,
  `RadarNormalizer._normalizeSurface`): Ein Verbund aus drei Messgrößen nach
  Schlechtesten-Prinzip ersetzte eine fehlende Teilgröße durch den neutralen
  Füllwert `0.5`, meldete den Achswert aber weiterhin als `isEstimated=false`
  nach außen.
- **Fund C** (derselbe Absatz, zweite Stelle, `room_risk_providers.dart`,
  `_computeRiskScore`): Gleiches Muster (`?? 0.5`-Fallback in einem Komposit),
  gefunden beim gezielten Suchen nach demselben Signaturmuster wie Fund B,
  nicht durch unabhängige Prüfung.
- **Fund D** (Wiederholung 2026-08-02T07:50:00+0100, `TrendsScreen._getValue`
  und `HistoryScreen._ChartTab._val`): Andere Bauform als A–C — kein
  Komposit-Score mit `?? 0.5`, sondern ein einfacher Zwei-Feld-Fallback
  zwischen zwei fachlich verschiedenen, aber gleich skalierten Messgrößen
  (Wandoberflächenfeuchte vs. Raumluftfeuchte, beide 0–100 % rF). Die
  Ähnlichkeit der Skala machte die Vermischung unauffällig.

### 2. Kandidatenorte für einen Auslöser

1. Stop-Hook (Sitzungsende, prüft geänderte Dateien)
2. PreToolUse/PostToolUse auf Edit (beim Entfernen/Ändern eines Feld-Zugriffs)
3. pre-push/commit-msg-Hook (grep-basierter Lint vor dem Push)
4. Datenbank-Trigger
5. Zähler ohne Sperre
6. Statischer Linter auf bekanntes Signaturmuster (`?? 0.5`, `if (has…)`)
7. gar keiner, weil die Erkennung Fachwissen über „was behauptet die Ausgabe
   im Vergleich zu ihren Eingaben" braucht

### 3. Tabelle Vorkommen × Kandidat

| Kandidat | Fund A (Ampel) | Fund B (RadarNormalizer) | Fund C (room_risk) | Fund D (Trends/History) |
|---|---|---|---|---|
| Stop-Hook, Diff nach `if (has` + entferntem Bezeichner durchsucht | Teilweise — könnte grep nach `if (hasIrData)` im Diff-Umkreis der entfernten Zeile auslösen, aber nur wenn Entfernung und Gate in derselben Sitzung geändert wurden | Nein — hier wurde nichts entfernt, ein Fallback-Wert war von Anfang an so gebaut | Nein, gleicher Grund | Nein — kein Gate, ein einfacher `??`-Ausdruck zwischen zwei Feldern |
| PreToolUse/PostToolUse auf Edit, sucht Aufrufer des geänderten Feldnamens | Ja, am ehesten treffsicher — der entfernte Feldname (z. B. Eckentemperatur) lässt sich vor dem Edit im Repo nach Konsumenten durchsuchen | Nein — kein Feld wurde entfernt, das Problem ist die Kodierung des Fallback-Zustands selbst | Nein, gleicher Grund | Nein — kein Feld wurde entfernt, zwei bestehende Felder wurden neu kombiniert |
| pre-push/commit-msg-Lint auf `?? 0.5`-Signatur | Nein — Fund A hat keine `?? 0.5`-Fallback-Zeile, das Problem liegt in der Gate-Logik `if (hasIrData)`, nicht im Fallback-Wert | Ja — exakt das gesuchte Muster | Ja — exakt das gesuchte Muster (wurde im Original sogar per gezieltem Grep so gefunden) | Nein — andere Bauform, kein `0.5`, kein Komposit, ein reiner Feld-Fallback |
| Statischer Linter „Aggregat ohne Unvollständig-Zustand" (prüft, ob ein `switch`/`if`-Verbund einen Zustand für „Datengrundlage fehlt" kennt) | Ja — genau die Reparatur, die tatsächlich gewählt wurde (`AmpelStatus.gray` in die Rangfolge aufgenommen), wäre als Regel formulierbar: jedes Aggregat mit optionalen Teilurteilen braucht einen Unvollständig-Zweig | Ja, mit Anpassung — der Linter müsste auch `isEstimated`-Flags gegen tatsächliche Fallback-Nutzung prüfen | Ja, gleiche Anpassung nötig | Nein — hier gibt es gar kein Aggregat mit Rangfolge, sondern eine Zeitreihen-Kurve; der Linter träfe die falsche Kategorie |
| Zähler ohne Sperre | Nein — Einzelfall, kein wiederkehrender Zustand zum Zeitpunkt des Funds | Nein | Nein | Nein |
| gar keiner (Fachwissen nötig) | Teilweise zutreffend — ohne Wissen, dass „Wärmebrücke entsteht an der Wandoberfläche, nicht in der Raummitte" WIRKUNG hat, erkennt kein Muster-Linter, dass die verbleibende Größe (Raumluftfeuchte) fachlich unzureichend ist; ein Linter kann nur die STRUKTUR (Gate ohne Fallback-Zustand) prüfen, nicht die fachliche Hinlänglichkeit | Nein — hier reicht Struktursuche, kein Fachwissen nötig | Nein, gleicher Grund wie B | Ja, größtenteils — die Erkennung „zwei Felder mit gleicher Skala, aber verschiedener Bedeutung, hinter einem `??`" erfordert Wissen über die fachliche Bedeutung der Felder, kein Struktur-Grep würde `surfaceRhPct` von `correctedRhPct` als „gefährlich ähnlich" markieren, ohne eine Liste solcher Feldpaare vorzuhalten |

### 4. Urteil

**Mechanisierbar für die Hälfte der Fälle, an einem Ort — nicht für alle vier
Bauformen mit demselben Mittel.**

- Fund B und Fund C teilen exakt dieselbe Signatur (`?? 0.5`-Fallback in einem
  Komposit-Score) und sind durch einen **statischen Linter/pre-push-Lint auf
  dieses Muster** direkt fangbar — das ist derselbe Suchbegriff, mit dem sie
  im Original tatsächlich gefunden wurden, nur vorgezogen vor den Commit statt
  nachträglich per Grep.
- Fund A ist über einen breiteren, aber noch strukturellen Linter fangbar:
  „jedes Aggregat mit optionalen Teilurteilen braucht einen Zustand für
  unvollständige Datengrundlage, einsortiert in die Rangfolge" — das lässt
  sich als Regel für `switch`/Rangfolgen-Aggregate formulieren und als
  **pre-push-Lint** prüfen (Dart erzwingt bei enum-`switch` ohne `default`
  ohnehin Vollständigkeit, ein Linter müsste nur zusätzlich prüfen, ob ein
  „unvollständig"-Wert in der Rangfolge vorkommt und erreichbar ist).
- Fund D fällt bei **jedem** der geprüften Kandidaten durch: kein Gate, kein
  Fallback-Wert, kein Aggregat mit Rangfolge — nur zwei fachlich verschiedene
  Felder gleicher Skala hinter einem einfachen `??`. Diesen Fall zu fangen
  bräuchte eine **Liste fachlich nicht-austauschbarer, aber gleich skalierter
  Feldpaare** (z. B. `surfaceRhPct` ↔ `correctedRhPct`), die im Code nirgends
  steht und erst aus der Domäne (Bauphysik) folgt. Das ist keine Struktur,
  sondern Fachwissen — **nicht mechanisierbar durch einen generischen Auslöser
  in diesem Raster**, ohne eine domänenspezifische Paarliste eigens
  anzulegen und zu pflegen (ein neues Artefakt, kein bestehender Ort).

**Gesamturteil:** Die Lehre zerfällt in zwei mechanisierbare Teilklassen
(Signatur-Fallback und Rangfolgen-Aggregat, beide über pre-push-Lint fangbar)
und eine dritte, nicht mechanisierbare Klasse (fachlich verwandte, gleich
skalierte Felder ohne Struktursignal) — dieser Rest gehört als Grenze
ausdrücklich in die Lehre, nicht als offene Aufgabe.

## Hinweis zur Herkunft der Beispiele

Die Codepfade zu L-bbd7fb (`lib/core/calculations/ampel_config.dart`,
`RadarNormalizer`, `room_risk_providers.dart`, `TrendsScreen`,
`HistoryScreen`) liegen im Projekt **wohlair**, nicht in diesem Arbeitsbaum
(brainlehr). Sie wurden ausschließlich aus dem Lehrtext zitiert, nicht erneut
im Code gelesen — dieser Auftrag verlangte nur das Lesen aus dem
Wissensspeicher. Der Agentenanker zu dieser Prüfung nennt zusätzlich einen
bestehenden Test `wohlair/test/features/radar/room_risk_surface_completeness_test.dart`
und einen Commit „Kategorie 'eskaliert ohne Regel'" — das deutet auf einen
bereits vorhandenen Regressionstest für mindestens einen der vier Funde hin,
wurde aber nicht verifiziert, da außerhalb des Auftragsumfangs (nur diese eine
Datei, nur dieses Repo).
