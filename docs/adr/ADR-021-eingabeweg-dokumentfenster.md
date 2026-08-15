# ADR-021: Wird die Dokumentbearbeitung ein Eingabeweg für den Wissensbestand?

**Stand** 2026-08-15T00:00:00+0200
**Status** Vorschlag — Entscheidung offen, nicht getroffen
**Betrifft** `kern/baustein.py`, `kern/dokument.py`, `kern/driftwaechter.py`, `kern/domaene.py`,
ADR-010, ADR-018 (Wirkungsvorrat und Wirkung Null), ADR-019 (fünf Entscheidungen vor dem ersten
Dokument)
**Entscheider** Betreiber — diese ADR entscheidet nichts, sie legt die Rechnung vor

Sieht der Code an einer Stelle anders aus als hier beschrieben: an den Code halten, Abweichung
melden.

## Anlass, so nah wie möglich am Wortlaut

Der Betreiber, 2026-08-15: Wenn er im Dokumentfenster eine Zahl ändert („drei haben zugestimmt"
statt fünf) oder einen Text („Treppensanierung noch offen" wird zu „Treppensanierung selbst
ausgeführt") — soll dann in der Datenbank stehen, dass die Treppensanierung ausgeführt ist? Also:
wird die Dokumentbearbeitung zu einem Eingabeweg für den Wissensbestand?

Heute ist die Antwort **nein, an keiner gemessenen Stelle**: `grep -rn "knowledge_add\|domaene"
kern/dokument.py kern/baustein.py kern/driftwaechter.py` liefert null Treffer. Das Dokumentfenster
und der Wissensbestand sind zwei getrennte Inseln. Diese ADR fragt, ob eine Brücke gebaut wird —
nicht, wie sie aussieht.

## Was heute steht, mit Fundstelle

- **Wirkung Null ist Systemlinie, nicht Vorschlag.** ADR-018 belegt an `kern/domaene.py`
  (`_regel_zeile`, Zeile 424 `art, _ = herkunftsart(quelle)`, gemeinsam mit den Triggern
  `knowledge_nodes_normrang_herkunft_bi/_bu` aus `schema.sql`): Importiertes schreibt
  `norm_rang = NULL`, kommt „nie höher herein als ‚keine Wirkung'", und alles darüber ist ein
  Willensakt eines Menschen HIER. Jeder Eingabeweg in den Bestand — auch ein künftiger aus dem
  Dokumentfenster — erbt diese Linie, sonst widerspricht er einer bereits getroffenen
  Architekturentscheidung.
- **`mitwirkende(doc)`** (`kern/dokument.py:236`) trennt Mensch und Modell — aber nur über
  `Anmerkung.von_wem`, an der **Anmerkung**, nicht am Baustein-Inhalt selbst. Sie beantwortet „wer
  hat kommentiert", nicht „wer hat den Fließtext zuletzt geschrieben".
- **`Baustein`** (`kern/baustein.py:86`) trägt sieben Felder: `kennung`, `typ`, `text`,
  `feldname`, `eltern`, `rang`, `alt`. Kein Feld für Herkunft, Quelle oder „abgeleitet aus". Der
  `_selftest` in `kern/baustein.py:357` prüft das Vertragsmuster wörtlich gegen genau diese
  Menge — ein achtes Feld wäre eine bewusste Erweiterung, kein Versehen.
- **`Anmerkung`** (`kern/baustein.py:143`) trägt `zustand`, `verlauf`, `selbstaendig_umgesetzt` —
  ein vollständiger Zustandsautomat mit Verlauf für den **Auftrag am Rand**. Für den
  **Bausteintext selbst** gibt es keinen Verlauf: `baustein_text_setzen`
  (`kern/dokument.py:188`) überschreibt `eintrag_map["text"]` ohne vorherigen Wert festzuhalten.
- **Der Typ `feld`** (`kern/baustein.py:52`, `feldname`-Pflicht in `__post_init__`) ist die
  einzige Stelle mit einer **eindeutigen, vergebenen Zuordnung** zwischen Baustein und Bedeutung —
  ein `feldname="rechnungsnummer"` sagt unzweideutig, wofür der Wert steht. Fließtext trägt keine
  vergleichbare Zuordnung; welcher Satz „Treppensanierung: Status" bedeutet, ist eine Deutung, kein
  Vertragsfeld.
- **Der Drift-Wächter** (`kern/driftwaechter.py`, `pruefe_drift`) vergleicht die schnelle
  Darstellung gegen das gesetzte Blatt und **meldet** eine Abweichung
  (`DriftBericht.nur_in_darstellung`/`nur_im_blatt`). Er schreibt nichts in den Bestand und
  verhindert nichts — er ist ein Diagnosewerkzeug für zwei Ableitungen desselben Baustein-Baums,
  kein Schreibpfad und kein Schutz vor Datenverlust am nächsten Satzlauf.
- **`veroeffentlichen`** (`kern/dokument.py:364`) ist der einzige heute gebaute Vorgang mit
  Urheber, Zeitpunkt und Beleg (`fassungen`, `base64`-CRDT-Snapshot). Er wirkt aber nur auf das
  Dokument selbst („veröffentlicht: ja/nein"), nicht auf den Wissensbestand.

## Frage 1 — zwei Fälle trennen: getipptes Feld gegen Fließtext

Der Typ `feld` und der Typ `absatz`/`ueberschrift` sind heute **strukturell verschieden weit**,
nicht nur inhaltlich:

| | `feld` | Fließtext (`absatz` u.a.) |
|---|---|---|
| Zuordnung Wert → Bedeutung | vergeben (`feldname`), eindeutig | keine — müsste erkannt/gedeutet werden |
| Vertragsprüfung | `__post_init__` erzwingt `feldname` bei `typ == "feld"` | keine analoge Prüfung möglich, es gibt kein Ziel-Schema |
| Beispiel aus dem Anlass | „Betrag: 42,00" — ein Formularfeld einer Rechnung | „Treppensanierung noch offen" — ein Satz in einem Protokoll |

Ein getipptes Feld ließe sich mechanisch einem Wissensknoten zuordnen (`feldname` als Schlüssel).
Ein Satz im Fließtext bräuchte dieselbe Art Deutung, die heute schon Anmerkungen der Klasse
`inhalt`/`rechtssatz` beim Umsetzen braucht — also **keine mechanische Zuordnung, sondern ein
Sprachmodell, das den Satz liest und interpretiert.** Das ist derselbe Unterschied, den ADR-018
zwischen Wirkungsvorrat A (endlich aufzählbar) und einer nicht aufzählbaren Wirkungsmenge zieht:
ein Feld ist aufzählbar, Fließtext-Deutung ist es nicht.

**Die Frage, die offenbleibt:** Sind beide zulässige Eingabewege, oder nur der erste (`feld`)? Der
Code liefert dafür keinen Automatismus — er liefert nur den Befund, dass beide Fälle heute
unterschiedlich weit tragen.

## Frage 2 — Quelle oder Ansicht: der abgeleitete Wert

Beispiel aus dem Anlass: ein Wert im Dokument steht dort, weil er aus dem Bestand **übernommen**
wurde (z. B. ein Baustein, der beim Erzeugen des Dokuments mit einem bestehenden Wissensknoten
befüllt wurde). Der Mensch überschreibt ihn im Dokumentfenster von Hand. Was gilt dann?

**Gemessen: Kein Baustein kann heute sagen, ob er abgeleitet ist.** Die sieben Felder aus
`kern/baustein.py:86` enthalten keine Herkunftsangabe — anders als `kern/domaene.py`, das
`_herkunft`-Tags für genau diesen Zweck führt (`herkunftsart`, `kern/belegvertrag.py`). Ein
Baustein, der aus dem Bestand befüllt wurde, sieht identisch aus wie einer, den ein Mensch frei
eingetippt hat.

**Das ist die eigentliche Lücke, nicht der fehlende Konflikt-Mechanismus.** Der im Auftrag
genannte Drift-Wächter (`kern/driftwaechter.py`) prüft ohnehin ein anderes Paar (Darstellung
gegen gesetztes Blatt, siehe Modulkopf Zeile 15–22) und würde eine solche Überschreibung gar nicht
erfassen — selbst wenn er es täte, käme die Meldung zu spät: Ein Wächter, der nach dem nächsten
Satzlauf meldet „Darstellung weicht ab", hat die von-Hand-Eingabe nicht gerettet, wenn ein
Ableitungslauf sie vorher stillschweigend überschrieben hätte. **Melden ersetzt keine Sperre, und
für ein Sperr-Feld fehlt der Grundbaustein: die Kennzeichnung „dieser Wert ist abgeleitet, jener
ist frei getippt" existiert nicht.**

Ohne diese Kennzeichnung ist die Frage „was gilt bei Konflikt" nicht einmal stellbar — es gibt
keine zwei Kategorien, zwischen denen entschieden werden müsste.

## Frage 3 — Wirkung Null für einen aus dem Dokument abgeleiteten Satz

ADR-018 verlangt: Was von außen hereinkommt, kommt **wirkungslos** herein und wird erst durch
einen Willensakt eines Menschen in Kraft gesetzt (`kern/domaene.py`, Vorbild). Übertragen auf das
Dokumentfenster: Ein aus einem Baustein abgeleiteter Satz für den Bestand dürfte **nicht** beim
Speichern des Dokuments automatisch in `knowledge_add`/eine Domänen-Quelle wandern.

**Was ADR-019s Fassungen dafür bereits tragen — geprüft, nicht angenommen:**

- `veroeffentlichen` (`kern/dokument.py:364`) hat Urheber, Zeitpunkt und einen vollständigen
  CRDT-Snapshot (`base64.b64encode(doc.get_update())`) — das ist ein außergewöhnlich guter Beleg:
  Dokument-Fassung, Zeitpunkt, Urheber sind vorhanden und im Selbsttest (Zeile 661–675) belegt
  rekonstruierbar.
- **Was fehlt: die Baustein-Kennung als Bezug im Beleg.** Eine Fassung (`fassungen(doc)`,
  Zeile 394) hält `urheber`, `zeitpunkt`, `stand` — nicht, **welcher Baustein** den fraglichen
  Satz trug. Um „dieser Satz im Bestand stammt aus Baustein X, Fassung Y, Zeitpunkt Z, Urheber W"
  zu belegen, müsste ein künftiger Schreibvorgang die Baustein-Kennung selbst mitführen. Sie ist
  vorhanden (`Baustein.kennung`, vergeben und stabil, siehe `baustein.py` Entscheidung 1) — sie
  wird nur heute nirgends mit einer Fassung verknüpft gespeichert.
- **Was fehlt: der Urheber ist an keiner Netzwerkstelle belegt.** Der Modulkopf von
  `kern/dokument.py` (Zeile 341–348) sagt es selbst: `veroeffentlichen` verlangt `urheber` als
  Pflichtparameter, aber `kern/dokumentdienst.py::_anmeldung` liefert heute nur wahr/falsch, keine
  Identität. Der Aufruf „vorgesehen, nicht verdrahtet" gilt für jeden künftigen Schreibpfad in den
  Bestand identisch: ohne Identität ist „wer hat diesen Satz freigegeben" nicht zu belegen, egal
  wie gut das Feld im Datenmodell aussieht.

**Ergebnis:** Der Beleg-Unterbau (Fassung, Zeitpunkt) steht; der Bezug auf den einzelnen Baustein
und der Urheber am Netzwerkende fehlen beide. Ein Eingabeweg, der heute gebaut würde, stünde auf
einem Beleg mit genau dieser Lücke.

## Ein Grund GEGEN den Eingabeweg

**Der Bestand trägt laut `CLAUDE.md` Daten Dritter** (WEG-Rechtsfälle aus buckeberg, Steuerdaten
aus openlehr), mit Vorgabewert `intern` für die Freigabe. Ein Eingabeweg vom Dokumentfenster in
den Bestand verwischt eine Grenze, die heute klar ist: **Wer im Dokument tippt, weiß nicht
zwangsläufig, dass er damit den Wissensbestand ändert** — anders als beim direkten Aufruf von
`knowledge_add`, wo der Handelnde den Bestand als Ziel kennt. Ein Textfenster, das nebenbei Fakten
schreibt, verschiebt die Verantwortung für eine Bestandsänderung an eine Stelle, die dafür nicht
gebaut ist: keine Kategorie-Auswahl (Code/Rechtslage/Steuer/Lehre, siehe `CLAUDE.md` „Worüber wird
hier Wissen geführt"), keine Freigabe-Entscheidung, kein bewusster Akt. Genau die Eigenschaft, die
ADR-018 am Web-Weg als „nachgiebigste Stelle des ganzen Entwurfs" kritisiert — ein Leser mit nicht
aufzählbarem Wirkungsvorrat —, träfe hier auf der Schreibseite zu, wenn Fließtext-Deutung
(Frage 1) ungeprüft ankäme.

## Der Nebenbefund, benannt und nicht mitentschieden

Der Betreiber hat selbst aufgeworfen: Zusammenarbeit am Dokument (Modell schlägt vor über eine
Anmerkung, Mensch nimmt an oder verwirft über `zustand_setzen`) erzeugt **Präferenzpaare** —
strukturell dasselbe Nebenprodukt wie bei der Prüfungskorrektur im Knoten zur Berufsschule
Bankwesen. Der Zustandsautomat dafür existiert bereits (`ZUSTAENDE`, `UEBERGAENGE`,
`Anmerkung.verlauf`, belegt im Selbsttest `kern/dokument.py:580` „verworfen ist nicht
verschwunden").

**Diese ADR entscheidet das ausdrücklich nicht mit.** Bevor Präferenzpaare als Trainingsdaten
gälten, wären Personenbezug, Zweckbindung und Urheberschaft zu klären — und Urheberschaft steht
laut Betreiber ausdrücklich auf dessen eigener Warteliste. Die Abhängigkeit wird hier benannt,
damit sie nicht zwischen den beiden Themen verloren geht, nicht aufgelöst.

## Was NICHT entschieden werden muss — es kostet später nichts

- **Die genaue Bauform eines Herkunftsfelds am Baustein** (Frage 2), falls die Grundfrage mit
  „ja" beantwortet wird. Ein Feld ist additiv nachrüstbar wie die Felder aus ADR-019
  (Verschachtelung, Alternativtext) — solange noch keine Dokumente gespeichert sind, ist die
  Migrationskosten-Rechnung aus ADR-018/ADR-019 identisch null.
- **Ob Fließtext-Deutung (Frage 1, zweiter Fall) je gebaut wird.** Der `feld`-Fall ist unabhängig
  entscheidbar; Fließtext kann offenbleiben, ohne dass der einfachere Fall darunter leidet.
- **Die genaue Verknüpfung Fassung↔Baustein-Kennung** (Frage 3). Solange kein Schreibpfad
  existiert, der sie bräuchte, ist ihr Fehlen ein Befund, kein Blocker.
- **Die Präferenzpaar-Frage selbst** — siehe oben, hängt an einer fremden Warteliste.

## Die Frage an den Betreiber

Soll die Dokumentbearbeitung ein Eingabeweg für den Wissensbestand werden — und wenn ja: nur für
den Typ `feld` mit seiner vergebenen, eindeutigen Zuordnung, oder auch für gedeuteten Fließtext?
Und, falls ja in irgendeiner Form: Wie soll ein Baustein, dessen Wert aus dem Bestand abgeleitet
ist, das heute nirgends tragen kann, das nach außen zeigen — und was soll gelten, wenn ein Mensch
einen solchen Wert im Dokumentfenster von Hand überschreibt, bevor der nächste Ableitungslauf ihn
sonst stillschweigend ersetzen würde?
