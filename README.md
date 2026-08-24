# Brainlehr

> **Public Alpha.** Dieser Main-Stand ist eine frische, datenfreie Veröffentlichung; er ersetzt weder den privaten Betrieb noch behauptet er vollständige Funktionsparität.

Lokaler Wissensspeicher mit einer JSON-RPC-Schnittstelle über Standard-Ein-/Ausgabe, primär für Claude MCP. Implementiert sind Knoten, Suche, Beziehungen, Annahmen, Freigabe/Rücknahme, Lehren, Statistik, neutrale Claude Recall-/Capture-Hooks und agentneutrale Prompt-Invarianz für Claude, ChatGPT und Hermes. Die maschinenlesbare [Funktionsmatrix](docs/FEATURE_MATRIX.json) nennt weitere noch zu generalisierende Engine-Funktionen.

## Schnellstart

Brainlehr benötigt Python 3.11 oder neuer.

```sh
python3.11 schnellstart.py
python3.11 knowledge_mcp_server.py
```

`schnellstart.py` erstellt eine lokale Beispieldatenbank. Diese Datei ist absichtlich nicht versioniert.

## Entwicklung

```sh
python3.11 -m pytest -q -p no:cacheprovider tests
python3.11 tools/privacy_check.py
```

Die öffentliche Ausgabe enthält Quellcode, Tests, allgemeine Dokumentation und einen **Auszug des freigegebenen Wissens** (siehe unten). Betriebsdaten, personenbezogene Angaben und Wissen über konkrete Projekte, Orte oder Betriebsereignisse gehören nicht in dieses Repository.

Für Claude: `integrations/claude/settings.template.json` mit eigenen lokalen Pfaden kopieren; die Hook-Vorlagen liegen unter `integrations/claude/hooks/`.

Für ChatGPT bleibt derselbe stdio-MCP lokal. Der [offizielle Secure-MCP-Tunnel](integrations/chatgpt/README.md) stellt den authentifizierten HTTPS-Transport bereit und exponiert im Profil `prompt-invariance` ausschließlich die beiden Vergleichswerkzeuge. Hermes nutzt ebenfalls stdio; eine minimale [Konfigurationsvorlage](integrations/hermes/config.template.yaml) liegt bei.

Prompt-Invarianz wird nur für Bewertungen, Rangfolgen und Entscheidungen aktiviert: normal `light`, bei gemeinsamen, irreversiblen, sicherheits-, Datenmodell- oder Automationsfolgen `strong`. Faktensuche, Extraktion, Ausführung und Tests bleiben `off`. Das gilt unabhängig von der App: Anbieter-Rankings in Buckenberg nutzen sie; Brainlehr-, Openlehr- oder Fahrtenbuch-Coding nur bei einer echten Architektur- oder Produktentscheidung, nicht bei jedem Edit oder Testlauf.

```sh
python3.11 -m pytest -q -p no:cacheprovider tests
python3.11 tools/privacy_check.py
```

Der Privacy-Check ist ein technischer Schutz, keine DSGVO- oder Compliance-Zusage.

## Was im Wissensauszug steht — und was nicht

`auszug-offen/bestand.jsonl` enthält ausschließlich Einträge mit ausdrücklicher
Freigabe. Die Vorgabe im Speicher ist Zurückhaltung: ein neuer Eintrag ist per
Datenbank-Standard *intern*, Freigabe ist ein einzelner, begründeter Akt. Der
Auszug wird mit `pflege/export_offen.py` erzeugt; das Werkzeug entscheidet
nicht, **was** freigegeben ist, es führt nur aus, was entschieden wurde.

**Enthalten:**

| | |
|---|---|
| NASA Lessons Learned (LLIS) | rund 1 640 Einträge, Nachschlagewerk |
| eigene freigegebene Sachverhalte | rund 250 Einträge |
| abstrakte Fehlerlehren | rund 720 Einträge — Ursache, Behebung, Vermeidung, ohne Projektbezug |

**Herkunft und Lizenz des Fremdmaterials, ehrlich benannt:** Der NASA-Bestand
stammt aus dem *Lessons Learned Information System* (llis.nasa.gov). Werke von
US-Bundesbehörden sind nach 17 U.S.C. §105 gemeinfrei — **an der Primärquelle
nicht nachgeprüft.** Wer darauf aufbaut, prüft das selbst.

**Nicht enthalten: das Testwissen.** Die Messungen der Abrufgüte laufen gegen
zwei Prüfkorpora. Der eigene, harte Korpus (45 Fälle, Wortüberlappung zwischen
Frage und Ziel im Median 8,7 %) liegt bei; der zweite besteht aus rund 2 700
Einträgen des öffentlichen deutschen Frage-Antwort-Datensatzes **GermanQuAD**
(deepset). Dieser Datensatz ist **nicht Teil dieses Repositories** — er hat
eigene Lizenzbedingungen und ist bei seinem Urheber zu beziehen. Im Bestand
dient er ausschließlich als Vergleichsmaßstab: derselbe Abruf erreicht dort
95 %, gegen 42,9 % beim eigenen Korpus. Wer nur die höhere Zahl liest, misst
die Leichtigkeit der Aufgabe, nicht die Güte des Systems.

## Was die Zahlen bedeuten

Dieses Repository misst sich selbst und veröffentlicht auch die schlechten
Werte. Drei Beispiele aus dem Stand vom 20. August 2026, jeweils mit ihrem
Bezugsrahmen — eine Zahl ohne Nenner ist hier keine:

- **Trefferquote 22 von 35** über den eigenen Prüfkorpus, in einer Betriebsart
  ohne Schweigepflicht. Im Auslieferungszustand liegt sie bei 1 von 35 — dort
  schweigt das System lieber, als zu raten.
- **Aufgriffsquote 247 von 1 275** (19,4 %): So oft wurde ein automatisch
  eingespielter Eintrag später nachweislich verwendet. Lehren 30,5 %,
  Sachknoten 8,2 %.
- **Drei Verfahren geprüft, drei Nullbefunde** bei der Frage, ob sich aus einem
  Ähnlichkeitswert ablesen lässt, ob ein Treffer auch *richtig* ist. Der Wert
  sagt zuverlässig, ob überhaupt etwas Passendes vorliegt — und nichts darüber,
  ob es stimmt.

## Lizenz

**AGPL-3.0.** Wer die Software als Dienst betreibt, legt seinen Quelltext
ebenfalls unter der AGPLv3 offen. Der Wortlaut steht in [LICENSE](LICENSE),
der Beitragsablauf samt CLA in [CONTRIBUTING.md](CONTRIBUTING.md).

Diese Angabe steht hier und nicht nur in der Lizenzdatei, weil genau das
gefehlt hat: Vom 2026-08-17 bis zum 2026-08-20 trug dieses Repository **MIT**
— als Vorgabewert beim Neuanlegen des Exports übernommen, nicht als
Entscheidung. Aufgefallen ist es niemandem, weil die Datei von Anfang an so
dastand und deshalb in keinem Vergleich auffiel, und weil die Lizenz des
eigenen Codes nirgends erwähnt wurde, wo man sie liest. Für die drei Tage,
in denen die MIT-Fassung öffentlich stand, lässt sich die Erlaubnis nicht
zurücknehmen — wer damals kopiert hat, hat sie unter MIT.

Die Lizenzangaben zum **Fremdmaterial** im Wissensauszug (NASA LLIS,
GermanQuAD) stehen weiter oben und sind davon unberührt.
