# ADR-035 — Die zentrale produktive Oberfläche ist die WebUI

Angelegt 2026-08-28.
Status: **entschieden** (Betreiber).

## Anlass

Betreiberentscheidung, wörtlich: *„Ja, alles andere soll Legacy werden, hatten
wir schon einmal besprochen.“*

Damit wird die sichtbare Produktgrenze eindeutig festgelegt: Es gibt eine
produktive Brainlehr-Oberfläche. Frühere native, OpenLehr- und sonstige UIs
bleiben nur als Legacy-Blaupausen für Inventar und Ersatzzuordnung erhalten.

## Entscheidung

**Die zentrale produktive Brainlehr-Oberfläche ist die WebUI.** Eine spätere
Mac-App bettet dieselbe WebUI ein und ergänzt ausschließlich ausdrücklich
autorisierte Betriebssystemfähigkeiten. Sie erhält keinen zweiten Renderer,
keine zweite Produktoberfläche und keine abweichende UI-Wahrheit.

Diese ADR supersediert ADR-024 für die Wahl der produktiven Oberfläche; die
fachlichen Grenzen und die Plattformneutralität der Beschreibungen bleiben
erhalten, soweit sie diesem Beschluss nicht widersprechen.

Alle bisherigen Oberflächen werden erst nach einem Inventar und einer
Zuordnung **übernehmen / ersetzen / verwerfen** als Legacy markiert. Sie sind
keine parallelen Implementierungsziele.

Beim Start darf die letzte aktive Actor-/Projekt-/Worktree-Projektion nur nach
serverseitiger Revalidierung wieder erscheinen. Bis PASS werden aus ihr weder
Wissens-/Domänendaten noch Aktionen bereitgestellt. Eine fehlgeschlagene
Revalidierung leert nur
aktive Projektion, Cache und Subscriptions, zeigt den leeren Kontextpicker und
verändert kein dauerhaftes Brainlehr-Wissen. Die sichtbaren
Dashboard-Fähigkeiten `BDW-P63`, `BDW-P65` und `BDW-P66` sind Module dieser
WebUI, keine eigenständigen Renderer.

## Verworfen

Ein paralleler nativer Renderer neben der WebUI. Er würde zwei sichtbare
Wahrheiten, doppelte Bedienlogik und getrennte Änderungswege erzeugen.

## Abnahme und offene Gates

* Der vertikale WebUI-Durchstich ist noch **nicht ausgeführt**.
* Das Legacy-Inventar mit Ersatzzuordnung ist noch **nicht ausgeführt**.
* Beide Gates müssen vor produktiver Umsetzung bzw. endgültiger Ablage alter
  UIs nachgewiesen werden.
* Sein erster Scope ist nur Anmeldung/gesperrt, revalidierter Kontext,
  Wissensabruf, Vertrauensregler und wahre Eingriffsherkunft. Das ist kein
  finaler Produktscope; die Entwicklungsassistent-Domäne bleibt bis zu einer
  quellengestützten User Journey vertagt. ADR-023 impliziert keine V1 davon.
* Das Webframework ist mit diesem Beschluss nicht entschieden.
