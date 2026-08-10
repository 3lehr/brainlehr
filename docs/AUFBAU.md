# Aufbau, Vektoren und Sicherung

Ausgelagert aus `README.md` (2026-08-10T09:10:00+0200).

### Vektoren: bewusst nicht mitgeliefert

Der Beispielbestand enthält **keine** Embeddings. Das ist kein Vergessen:

- **Ein Vektor gehört zu genau einem Modell.** Mitgelieferte Vektoren würden
  die Modellwahl vorwegnehmen — ein Datenbank-Trigger erzwingt ohnehin, dass
  alle Vektoren im Bestand vom selben Modell stammen.
- **Sie sind nicht nötig, um anzufangen.** FTS5 trägt die Suche allein; oben
  liefert sie ohne einen einzigen Vektor Treffer.
- **Sie sind reproduzierbar.** Wer sie will, rechnet sie selbst — das kostet
  einmal Rechenzeit und einen Modell-Download, aber niemand muss fremden
  Zahlenkolonnen vertrauen, deren Herkunft er nicht prüfen kann.

```bash
pip install -r requirements.txt
python3 kern/build_embeddings.py          # einmalig, dauert je nach Gerät
```

Danach läuft die hybride Suche (FTS5 + Vektoren, per RRF verschmolzen). Ein
näherungsweiser Index (HNSW) ist bewusst **nicht** gebaut: er fände den besten
Treffer nicht garantiert und würde damit die Gütemessung entwerten, an der
dieses Projekt hängt.

### Bestand sichern und wiederherstellen

Die Datenbank selbst gehoert **nicht** in die Versionsverwaltung: Git fuehrt eine
Binaerdatei nicht zusammen, es ueberschreibt sie — ein Arbeitstag der Gegenseite
verschwindet dann ohne Konflikthinweis. Versioniert wird stattdessen ein
zeilenweiser Textauszug, aus dem sich der Bestand vollstaendig wiederherstellen
laesst:

```bash
python3 brainlehr.py raus     # Bestand -> auszug/ (Text, vergleichbar)
python3 brainlehr.py rein     # auszug/ -> Bestand
python3 brainlehr.py init     # leere Datenbank anlegen
python3 brainlehr.py haken    # Hooks im Klienten verdrahten
```

Anbindung an einen MCP-Klienten über dessen Konfiguration; der Server spricht
JSON-RPC über Standardein- und -ausgabe.

---


## Aufbau

```
knowledge_mcp_server.py   MCP-Schnittstelle, 23 Werkzeuge, ein Choke-Point
ausweis.py                Identität, Rollen, Mandate, Einladungen
werkzeugrechte.py         Durchsetzung an tools/call, Bezug own/published
foederation.py            Instanzkennung, Vertrauensliste zwischen Instanzen
normbezug.py              meldet Normzitate ohne Beleg in eigenen Antworten
embeddings.py             lokale Vektoren + RRF-Fusion
hebb_kanten.py            assoziative Kanten aus gemeinsamem Abruf
kanonymitaet.py           misst k-Anonymität (misst, anonymisiert nicht)
haken/                    Hooks für Abruf und Erfassung
schreibpruefstand/        Messläufe gegen lokale Modelle
berichte/                 Übersichten: Fähigkeitsbestand, Vorschläge, Erstverwendung
messungen/                Messläufe und Diagnosen des Abrufs
pflege/                   Bestandspflege: Entdopplung, Auszug, Wiederherstellung
docs/adr/                 Entscheidungen mit Begründung und Abbruchbedingung
migrationen/              historische Läufe — für eine Neuanlage nicht nötig
quellen/                  Lizenzampel der Fremdbestände
```

> **Das Wurzelverzeichnis ist immer noch zu voll — 69 Python-Dateien.**
> Am 2026-08-10 sind 19 davon nach `messungen/`, `pflege/` und `berichte/`
> gewandert: genau die, die nachweislich niemand nennt. Die übrigen 69
> zerfallen in drei Klassen, die verschieden brechen — 9 sind als absoluter
> Pfad in einer Hook-Konfiguration verdrahtet und fallen bei einem Umzug
> **lautlos** aus, 49 werden importiert, 11 werden als Zeichenkette
> aufgerufen. Der Umbau auf `src/brainlehr/` plus `werkzeuge/` braucht
> deshalb eine eigene Runde mit Testabsicherung, statt nebenbei zu
> passieren. Plan und Messung: `docs/PLAN_WURZELORDNUNG_2026-08-10.md`.

Was die vielen Dateien wenigstens einlösen: jedes Werkzeug ist für sich
aufrufbar, hat einen `--selftest` und einen Modulkopf, der seine **Fehlklasse**
benennt — wogegen es schützt und was ein Fehlalarm kostet.

---

---
