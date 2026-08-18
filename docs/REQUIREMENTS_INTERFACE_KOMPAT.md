# Teilkatalog: Interface- und Kompatibilitätsvertrag (BDW-F07)

Untergeordnet zu `docs/REQUIREMENTS_BRAINLEHR.md`; lokale IDs sind nur Umsetzungsgates.

Stand: 2026-08-18T05:10:00+0200. Deckt genau die Naht
`openlehr_X → Brainlehr → Atelier` ab. Dies ist **kein** zweiter
Root-Lastenkatalog: die Produktnorm bleibt `BDW-F07` („Portable Wissenspakete“,
`BDW-F07-AC1`: Export/Import erhält IDs, Zeit, Provenienz, Rechte und Konflikte
atomar). Hier stehen nur die Interface-IDs, mit denen dieses AC prüfbar wird.

## Gemessener Ausgangsstand (2026-08-18)

- `kern/domaene.py` verlangt `("domaene", "quellen", "regeln", "dienst", "oberflaeche")`.
  Ein Versionsfeld existiert nicht — weder Paket noch Prüfer kennen es.
- `pakete/steuer.domaene.json` und
  `openlehr_einzelunternehmer/wissen/einzelunternehmer.domaene.json` tragen
  kein `contract_version`.
- `speichere()` schreibt mit `INSERT OR IGNORE`; gleiche IDs werden nie aktualisiert.
- `dienst` wird geprüft, aber nicht persistiert und nicht gestartet.
- `dienst/tests/test_euer_vorschlag.py::test_bildschirmbeschreibung_nennt_keine_bauform`
  ruft `pytest.skip`, wenn Brainlehr fehlt.
- Der OpenLehr-Envelope-Vertrag (`OPENLEHR_KERNEL_UND_APP_VERTRAG_V1.md`, §3)
  verlangt bereits `contract` und `contract_version`. Das Domänenpaket ist
  damit heute das einzige Stück der Strecke ohne Version.

## Interface-IDs und Producer/Consumer-Matrix

| ID | Interface | Producer | Consumer | Anforderung | Gate |
|---|---|---|---|---|---|
| INT-PKG-001 | Domänenpaket `*.domaene.json` | `openlehr_X` | `kern.domaene.pruefe` | Datenformat, nie Code; Pflichtschlüssel plus `contract_version`. | TEST-INT-PKG-001 |
| INT-VER-001 | `contract_version` = `1` (SemVer-Major) | Paketautor | Prüfer beider Repos | Fehlende oder unbekannte Major-Version wird fail-closed abgewiesen, nicht geraten. | TEST-INT-VER-001 |
| INT-VER-002 | Kompatibilitätsmatrix | Brainlehr | alle Klienten | Jede unterstützte Major-Version steht mit Von/Bis und Verhalten in diesem Katalog. | TEST-INT-VER-002 |
| INT-API-001 | `POST /api/domaene-import` | Atelier / CLI | Brainlehr-Dienst | Import ist atomar; Ablehnung schreibt nichts; Wirkung Null bleibt (ADR-018). | TEST-INT-API-001 |
| INT-API-002 | `GET /api/domaene-oberfläche` | Brainlehr | Atelier | Plattformblinde Beschreibung (ADR-024); keine Bauform, keine Fachlogik. | TEST-INT-API-002 |
| INT-REG-001 | Domänenregistry | Brainlehr | Atelier | Mehrere Domänen sind adressierbar; `einzelunternehmer` ist kein fester Wert im Klienten. | TEST-INT-REG-001 |
| INT-DNST-001 | Dienst-/Capability-Lifecycle | Paket | Brainlehr | Ein validierter `dienst` wird persistiert, hat Zustand (angemeldet/aktiv/stillgelegt) und wird nie implizit gestartet. | TEST-INT-DNST-001 |
| INT-UPD-001 | Reimport, Migration, Rollback | Paketautor | Brainlehr | Gleiche ID mit neuem Inhalt aktualisiert sichtbar und rücknehmbar; `INSERT OR IGNORE` genügt nicht. | TEST-INT-UPD-001 |
| INT-SNAP-001 | Snapshotgrenze (`cb24f119`) | Brainlehr | Abruf/Prüfkorpus | Ein Lauf liest einen festgehaltenen Stand, nicht bei jedem Aufruf die gegenwärtige DB. | TEST-INT-SNAP-001 |
| INT-GATE-001 | Cross-Repo-Gate | beide Repos | CI/Abnahme | Der repoübergreifende Vertragstest darf nicht `skip`en; fehlender Gegenpfad ist rot. | TEST-INT-GATE-001 |

## Versionsregeln

- **Additiv** (Major bleibt `1`): neue optionale Felder, neue Bildschirmarten,
  neue Regeln. Ein alter Consumer ignoriert Unbekanntes, ohne abzubrechen.
- **Brechend** (neue Major): Pflichtfeld entfernt oder umbenannt, Bedeutung
  eines Feldes geändert, Ablehnungsverhalten verschärft.
- **Unbekannte Major-Version ist rot**, nie „vorsichtshalber akzeptiert“ —
  dieselbe Fail-closed-Regel wie die Contract Registry in
  `OPENLEHR_KERNEL_UND_APP_VERTRAG_V1.md` §2 Nr. 1.

### Kompatibilitätsmatrix

| `contract_version` | Brainlehr-Prüfer | Verhalten |
|---|---|---|
| fehlt | ab v1 | Abweisung mit einem Satz für den Menschen |
| `1` | ab v1 | angenommen |
| `> 1` | v1 | Abweisung, kein Teilimport |

## Update, Migration, Rollback

1. Reimport derselben Paket-ID mit neuem Inhalt aktualisiert die betroffenen
   Zeilen und protokolliert die Vorfassung; in Kraft gesetzte Regeln behalten
   ihren Rang nur bei ausdrücklicher Entscheidung (ADR-018).
2. Jeder Import trägt eine Importkennung, über die genau dieser Import
   zurückgenommen werden kann.
3. Ein abgelehntes Paket verändert nichts — auch nicht teilweise.

## Was hier bewusst nicht steht

Rechte, Mandanten, Region und Export bleiben bei `BDW-E*`/`BDW-U*`. Dieser
Katalog beschreibt die Naht, nicht die Policy.

Konflikte werden hier ergänzt, nicht still aufgelöst.
