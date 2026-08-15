# ADR-019 — Fünf Entscheidungen vor dem ersten gespeicherten Dokument

> **Titel korrigiert 2026-08-15T12:55:00+0200.** Vorgelegt waren drei
> Entscheidungen; die unabhängige Entwurfsprobe fand zwei weitere Lücken
> derselben Art (Fassungen, Sprache), beide wurden entschieden. **Der Dateiname
> bleibt bei „drei"** — er ist die Adresse, auf die andere Dokumente und Commits
> zeigen, und Adressen werden nicht nachträglich geändert. Wer die Datei über
> ihren Namen sucht, findet fünf Entscheidungen darin.

**Status:** angenommen
**Datum:** 2026-08-15T10:07:20+0200
**Entschieden von:** Betreiber, auf Vorlage mit je drei Wahlmöglichkeiten
**Betrifft:** `kern/baustein.py`, `kern/dokument.py`, alle künftigen Dokumentarten
**Verwandt:** ADR-010 (Dokumentfenster), ADR-014 (Kern/Bestandteil/Domäne),
ADR-018 (Wirkungsvorrat und Wirkung Null), Linie F und Linie I des Gesamtplans

## Anlass

Der Betreiber will eine dritte Domänenfamilie: **Homepages**. Die Frage war
ausdrücklich nicht „bauen wir das", sondern: *was muss jetzt entschieden werden,
damit eine spätere Entscheidung nicht teuer wird?*

Vorausgegangen sind sechs Messungen an diesem Tag — Bestand der vorhandenen
WordPress-Seite, Tragfähigkeit des Baustein-Vertrags, Anker im laufenden System,
Landschaft der Verfahren. Der Befund, der diese ADR auslöst: **Drei Eigenschaften
sind billig, solange keine Daten existieren, und teuer, sobald welche existieren.**

## Der Zeitpunkt ist gemessen, nicht behauptet

Zum Entscheidungszeitpunkt gilt (2026-08-15T10:07:20+0200):

| | |
|---|---|
| `kern/baustein.py` `TYPEN` | `absatz`, `ueberschrift`, `tabelle`, `grafik`, `feld` |
| Tabellen `dokumente`/`bausteine` im Bestand | **existieren nicht** |
| `INSERT`/`UPDATE`/`commit()` in `dokument.py`, `dokumentdienst.py` | **0** |
| Zustand „veröffentlicht" in `dokument.py`/`dokumentdienst.py`/`baustein.py` | **0 Treffer** |

Dieselbe Lage wie bei `kern/domaene.py` in ADR-018: **Das Fenster ist offen und
schließt sich mit dem ersten Schreibvorgang.** Migrationskosten heute: null.

## Entscheidung 1 — Ein Baustein darf Kinder haben

Verschachtelung wird eingezogen, bevor Dokumente gespeichert werden.

**Grund:** Heute ist jeder Baustein ein Blatt. Eine Liste von Beiträgen, eine
Navigation, ein Abschnitt mit Unterabschnitten sind damit nicht abbildbar — auch
im Druck nicht. Einen Baum nachträglich auf flache Daten zu legen ist die
teuerste der drei Änderungen: jedes bis dahin bestehende Dokument wäre flach, und
seine Struktur müsste beim Lesen **geraten** werden.

**Verworfen:** „Liste später als eigener Typ". Preis wäre gewesen, dass
Wiederholung ein Sondertyp **neben** dem Rollenmodell wird statt eine Rolle
darin — und jede Ausgabeform bräuchte dafür eine Sonderbehandlung.

## Entscheidung 2 — Das Bild trägt Alternativtext getrennt von der Bildunterschrift

Der `grafik`-Baustein bekommt getrennte Felder: Bildquelle, Bildunterschrift,
Alternativtext.

**Grund:** Heute hat er **ein** Textfeld, das als Bildunterschrift dient, und
kein Feld für die Bildquelle. Bildunterschrift und Alternativtext sind
verschiedene Dinge — eine für alle sichtbar, eine für die Sprachausgabe.
Nachträglich getrennt hieße: bei jedem bestehenden Baustein ist unklar, welches
von beiden der eine Text war.

**Zwei Belege dafür, dass das kein Formalismus ist:** WordPress führt den
Alternativtext seit jeher als eigenes Feld am Medium — unser Modell ist an dieser
Stelle **ärmer** als das, was wir ablösen wollen. Und auf der laufenden Seite des
Betreibers tragen 301 von 593 Bildern einen Alternativtext, in der
Medienbibliothek dagegen 0 von 20 geprüften: Die Texte entstehen dort beim
Ausliefern und gehören nicht der Seite. Genau das soll hier nicht passieren.

## Entscheidung 3 — „Veröffentlicht" ist ein Zustand am Dokument, Vorgabe „nein"

Veröffentlichen wird ein **Akt** mit Urheber und Zeitpunkt, nicht die Abwesenheit
einer Sperre.

**Grund:** Heute existiert der Zustand nicht. Die vorhandene `freigabe`-Spalte
(`offen`/`intern`/`gesperrt`) wirkt ausschließlich auf `knowledge_nodes` und
`lessons_learned`, also auf den Wissensgraphen — ein anderes Datenmodell.
Nachträglich eingeführt müsste für jedes bestehende Dokument jemand **raten**, ob
es öffentlich war.

**Was diese Entscheidung erst möglich macht:** Eine Domäne kann eine Pflicht an
den Übergang hängen. Eine kommunale Seite dürfte dann ohne Alternativtext nicht
veröffentlichen; bei einer privaten Seite bliebe derselbe Prüfschritt ein
Hinweis. **Gleicher Baustein, anderer Maßstab** — und genau das ist der Grund,
warum „Homepage" eine Dokumentart mit mehreren Domänen ist und nicht eine Domäne.

## Was ausdrücklich NICHT entschieden ist

Alles Folgende bleibt offen, weil es später **nichts kostet**:

- Ob „Homepage" überhaupt eine Domäne wird, und welche (privat, Unternehmen,
  kommunal). Das ist ein Maßstab, kein Datenmodell.
- Ob WordPress Quelle oder Ausgabeform wird. Die Anker sind additiv
  nachrüstbar (gemessen: ≈51 Zeilen `register_post_meta` an bekannter Stelle),
  ohne den Editor anzufassen und ohne die Gestaltungsbeschränkung aufzuweichen.
- Der Token-Erzeuger für LaTeX. Hängt an nichts, ist in jedem Weg nützlich.
- Die Frage, welche Ausgabeform zuerst gebaut wird.

**Eine Auflage gilt trotzdem:** Das Baustein-Modell wird **nicht** nach Gutenberg
oder einer anderen Ausgabeform geformt. Rollen beschreiben, was ein Bestandteil
**ist**, nicht wie er dargestellt wird. Sonst erbt jede spätere Dokumentart die
Eigenheiten der ersten.

## Folgen

- `kern/baustein.py` bekommt Verschachtelung und die getrennten Bildfelder,
  `kern/dokument.py` den Veröffentlicht-Zustand — **vor** dem ersten
  Schreibvorgang. Danach ist es eine Migration.
- Der Satzweg (`kern/satz.py`) muss mit Verschachtelung umgehen können; gemessen
  sind dort ~63 von 138 Zeilen hart LaTeX, der generische Kern ist klein.
- Der Prüfstand für Dokumentarten bekommt damit einen Fall, den er heute nicht hat:
  ein Bild ohne Alternativtext muss sichtbar brechen, nicht still durchlaufen.

## Entwurfsprobe, unabhängig gefahren (2026-08-15T10:20:00+0200)

Ein Agent prüfte die Entscheidungen gegen den Code, **ohne die Begründung oben zu
kennen**. Er hat die Lage nachgemessen und drei Auflagen geliefert.

**Korrektur an der Lage:** „Noch nichts gespeichert" gilt nur relational.
`Raum._sichern()` in `kern/dokumentdienst.py` schreibt bei gesetzter Ablage den
vollen CRDT-Stand als Binärdatei. Es gibt Persistenz, nur kein Schema — für die
Korrekturkosten eher günstig, aber die ursprüngliche Aussage war zu absolut.

**Auflage zu Entscheidung 1 — und sie ist die wichtigste dieser ADR.** Drei
bestehende Codepfade iterieren flach über `bausteine(doc)`: `kern/satz.py:86`,
`kern/satzwache.py:90,99`, `kern/dokument.py:147` (`verwaiste`). Werden Kinder
eingezogen, ohne diese drei auf Rekursion umzustellen, gilt: Kind-Bausteine
werden **nie gesetzt**, **nie auf Label geprüft**, und Anker auf sie **nie als
verwaist erkannt** — ohne Fehler, ohne Ausnahme. Stille falsche Blätter. Genau
die Fehlerklasse, die `kern/baustein.py` im eigenen Kopftext als Anlass nennt.

**Bauform geändert: Verschachtelung über ein Elternfeld statt echter Kind-Arrays.**
Grund ist ein gemessener Preis, nicht Geschmack: Yjs kennt kein konfliktfreies
Verschieben eines Knotens zwischen Eltern (bekanntes Problem bei Baum-CRDTs,
Kleppmann 2020). Zwei gleichzeitige „verschiebe X unter A" / „unter B" sind nicht
auflösbar. Mit einem Elternfeld bleibt die Liste flach, Umhängen ist eine
Feldänderung, der Baum entsteht beim Lesen. **Preis, ausdrücklich benannt:** Die
Geschwister-Reihenfolge ist dann nicht mehr implizit über die Array-Position
gegeben und braucht ein eigenes Sortierfeld.

**Auflage zu Entscheidung 2: Alternativtext generisch an JEDEM Baustein**, nicht
als Sonderfeld am Bild. WCAG 2.2 verlangt ihn auch bei Tabellen; ein Sonderfeld
pro Typ wäre der Präzedenzfall für lauter Sonderfelder. Bildquelle und
Bildunterschrift bleiben grafik-spezifisch.

**Auflage zu Entscheidung 3:** Die Identität wird heute nicht bis zum Dokument
durchgereicht — `_anmeldung()` liefert nur wahr/falsch, keinen Namen. Ohne diesen
Datenfluss ist „Urheber" behauptet, nicht belegt.

## Zwei nachgetragene Entscheidungen (2026-08-15T10:25:00+0200)

Die Entwurfsprobe fand zwei Lücken, die dasselbe Kriterium erfüllen — jetzt
billig, später teuer. Beide vom Betreiber entschieden:

**Entscheidung 4 — Fassungen: der veröffentlichte Stand bleibt rekonstruierbar.**
Heute überschreibt die Ablage bei jedem Update den vollen Stand; eine
Versionskennung existiert nicht. Zusammen mit Entscheidung 3 hieße das: bekannt
ist, **dass** veröffentlicht wurde, nicht **was**. Bei einer kommunalen Seite
oder einer Rechnung ist genau das die Frage, die im Streitfall zählt.

**Entscheidung 5 — das Dokument trägt seine Sprache.** Gemessen: 0 Treffer für
ein Sprachfeld, die Sprache steht fest verdrahtet im LaTeX-Vorspann
(`pdflang=de-DE`). Eine HTML-Ausgabe braucht denselben Wert für `lang` — ohne ihn
ist die Seite für die Sprachausgabe fehlerhaft und verletzt WCAG. Sprachwechsel
**innerhalb** eines Dokuments (Zitat, Fachbegriff) ist damit noch nicht
abgedeckt; das bleibt bewusst offen, weil es ein Feld je Baustein wäre und
später ohne Datenverlust nachrüstbar ist.

## Was diese Entscheidung widerlegen würde

Wenn sich zeigt, dass Verschachtelung im Satzweg zu Mehrdeutigkeiten führt, die
flache Bausteine nicht haben (Beispiel: zwei gleichwertige Bäume ergeben
dasselbe Blatt), ist Entscheidung 1 zu überdenken — **vor** dem ersten
gespeicherten Dokument, danach nicht mehr billig. Der Spike
`html_quelle()` neben `satz_quelle()` ist der billigste Weg, das zu prüfen.
