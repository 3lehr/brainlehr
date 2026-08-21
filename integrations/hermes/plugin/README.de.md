# brainlehr als Speicher-Anbieter fuer Hermes

*[English version: README.md](README.md) — die englische Fassung ist die
massgebliche Tuersprache fuer einen Beitrag an Hermes (`BDW-P14`).*

Hermes (Nous Research, github.com/NousResearch/Hermes-Agent) bietet unter
Einstellungen einen **Memory Provider**. Am 2026-08-20 standen dort acht
Anbieter zur Auswahl -- byterover, hindsight, holographic, honcho, mem0,
openviking, retaindb, supermemory -- und brainlehr nicht. Gemessen ueber
`hermes memory status`: sieben der acht brauchen einen API-Schluessel, nur
`holographic` laeuft rein lokal.

brainlehr ist damit der zweite lokale -- und der einzige, bei dem **jeder
Eintrag eine nachpruefbare Herkunft tragen muss**. Das ist keine Konvention,
sondern ein Datenbank-Trigger: Ein Eintrag ohne `source` entsteht gar nicht
erst. Der Abruf liefert die Herkunft deshalb mit. Sie wegzulassen hiesse, den
Unterschied zu verschenken.

## Voraussetzungen

* Ein **brainlehr-Arbeitsstand** auf demselben Rechner. brainlehr ist ein
  lokaler Wissensspeicher aus Python und SQLite; dieses Plugin ist nur ein
  Adapter darauf, so wie `holographic` einer fuer dessen SQLite-Datei ist.
* **Python 3**, um ihn zu starten. Das Plugin importiert brainlehrs Module
  NICHT: es startet brainlehrs eigenen MCP-Server als **eigenen Prozess** und
  spricht mit ihm ueber stdio (JSON-RPC 2.0). Zwei Programme, die Nachrichten
  tauschen -- genau wofuer dieser Server ausdruecklich gebaut ist (ADR-024,
  "portabler Kern").
* Ein **Einbettungsdienst**, vorgabemaessig Ollama auf
  `http://127.0.0.1:11434`. Ohne ihn entstehen Eintraege ohne Vektor und sind
  ueber die Bedeutungssuche unauffindbar -- der Anbieter meldet sich deshalb
  lieber als nicht verfuegbar.
* Ein **Ausweis** (handelnde Kennung). Eintraege werden ihm zugeschrieben;
  ohne ihn traegt die Zuschreibung dauerhaft das Praefix `unbeglaubigt:`.

**Kein API-Schluessel, kein Konto, keine Cloud.** Nichts an diesem Plugin
spricht mit einem entfernten Dienst. Der einzige Netzaufruf geht an die
eingestellte Adresse des Einbettungsdienstes, und die zeigt vorgabemaessig auf
localhost.

## brainlehr selbst installieren: eine Zeile, ohne Arbeitsstand

```bash
pip install brainlehr          # der Speicher (AGPL-3.0); [bedeutungskanal] fuer lokale Einbettungen
```

Danach in den Plugin-Einstellungen `mcp_command = brainlehr-mcp` eintragen --
das installierte Paket bringt diesen Befehl mit, ein Dateipfad oder ein
geklontes Repo ist damit nicht mehr noetig.

**Es sind zwei Dinge noetig, und der Grund gehoert dazu.** Es sind zwei
getrennte Werke unter zwei Lizenzen: der Speicher ist AGPL-3.0, dieser Adapter
ist MIT, und sie sprechen ueber MCP als zwei Prozesse miteinander.
`pip install brainlehr` holt den Speicher; der Adapter muss trotzdem noch bei
Hermes ankommen, und Hermes findet Anbieter durch Absuchen von Verzeichnissen,
nicht ueber pip-Eintragspunkte (Befund im Kopf von `pyproject.toml`) -- der
Symlink unten bleibt deshalb der Weg, der nachweislich traegt. Wer den Adapter
mit `pip install hermes-brainlehr[brainlehr]` installiert, zieht den
AGPL-Speicher als ZUSATZ mit: eine bewusste Entscheidung, keine stille.

## Installation: Symlink, keine Kopie

```bash
ln -s /pfad/zu/brainlehr/integrations/hermes/plugin ~/.hermes/plugins/brainlehr
hermes memory status    # muss brainlehr auffuehren
```

`/pfad/zu/brainlehr` durch den eigenen Arbeitsstand ersetzen.

**Warum ausdruecklich ein Symlink:** Bis zum 2026-08-21 lag dort eine KOPIE.
Sie war beim Anlegen identisch und driftete danach lautlos -- eine Aenderung im
Repo erreichte Hermes nie, und niemand konnte es sehen. Genau diese Fehlklasse
hat dieses Haus schon mehrfach getroffen (`L-55075a`: ein korrigierter Trigger
erreicht eine gewachsene Datenbank nicht von selbst).

**Der Ort ist nicht beliebig.** `~/.hermes/plugins/` ist der Nutzerbereich und
ueberlebt ein Hermes-Update. Der naheliegende Ort waere
`~/.hermes/hermes-agent/plugins/memory/` gewesen, wo die acht mitgelieferten
liegen -- der wird beim Update ersetzt.

Gegenprobe nach der Installation:

```bash
readlink ~/.hermes/plugins/brainlehr   # muss den eigenen Arbeitsstand nennen
ls ~/.hermes/plugins/brainlehr/        # muss config_schema.py enthalten
```

Eine aeltere Kopie unter `~/.hermes/plugins/brainlehr.kopie-*` kann entfernt
werden, sobald der Symlink einmal benutzt wurde.

## Einstellungen

Das Plugin bringt ein Einstellungspanel mit, die Felder sind also in Hermes
selbst bedienbar. Jedes Feld ist zusaetzlich ueber eine Umgebungsvariable
lesbar, fuer Aufrufe ohne Panel.

| Einstellung | Umgebungsvariable | Bedeutung |
|---|---|---|
| `brainlehr_home` | `BRAINLEHR_HOME` | Wo brainlehr liegt. Nur noetig, wenn kopiert statt verlinkt wurde. |
| `mcp_command` | `BRAINLEHR_MCP_COMMAND` | Startbefehl des MCP-Servers. Leer: wird aus dem Fundort abgeleitet. |
| `db_path` | `BRAINLEHR_DB` | Die Bestandsdatei, falls sie nicht am Vorgabeort des Arbeitsstands liegt. |
| `ausweis` | `BRAINLEHR_AUSWEIS` | Die Kennung, der Eintraege zugeschrieben werden. |
| `embed_service_url` | `KNOWLEDGE_OLLAMA_URL` | Adresse des Einbettungsdienstes. |

**Wie brainlehr gefunden wird**, der Reihe nach -- die erste Quelle, die
antwortet, gewinnt:

1. die Einstellung `mcp_command` bzw. `$BRAINLEHR_MCP_COMMAND`, unveraendert
   uebernommen,
2. die Einstellung `brainlehr_home`, dann `$BRAINLEHR_HOME`,
3. der Ort, aus dem dieses Plugin installiert wurde -- ueber den empfohlenen
   Symlink fuehrt das in den Arbeitsstand zurueck, der haeufige Fall braucht
   also gar keine Einstellung,
4. `~/brainlehr`.

Aus den Quellen 2 bis 4 wird der Startbefehl ABGELEITET (`<dieser Interpreter>
<Arbeitsstand>/knowledge_mcp_server.py`), nie auf einen bestimmten Rechner
festgeschrieben.

Antwortet daraufhin kein Server, liefert `is_available()` `False` und schreibt
ins Log, welche Quellen geprueft wurden und was zu setzen ist. Der Anbieter
wird dann gar nicht erst registriert, statt registriert und kaputt zu sein.
Dasselbe gilt, wenn der Server startet, sein Bestand aber nicht antwortet.

## Wie mit brainlehr gesprochen wird

Ueber **MCP (stdio, JSON-RPC 2.0)**, als eigener Prozess -- nicht per
Bibliotheksimport. Das zaehlt doppelt:

* Der Adapter kennt nur die **Schnittstelle**, nicht brainlehrs Interna. Er
  bricht nicht, wenn sich `knowledge_mcp_server.py` intern aendert; die
  fruehere, importierende Fassung waere gebrochen.
* Von brainlehr wird nie etwas in den Hermes-Prozess geladen.

Benutzt werden genau drei der 32 Werkzeuge des Servers: `knowledge_search` fuer
den Abruf, `knowledge_add` fuers Schreiben und `knowledge_stats`, um den
echten Datenbankort fuer die Sicherung zu erfragen.

## Grenzen

Offen benannt, weil sie entscheiden, ob dieses Plugin nuetzlich ist:

* **Nur EIN externer Speicher-Anbieter kann gleichzeitig laufen.** Hermes'
  `agent/memory_manager.py` weist einen zweiten ab. brainlehr einzuschalten
  heisst, mem0, holographic oder was sonst benutzt wird, abzuschalten.
* **Der eingebaute Speicher laeuft daneben weiter.** brainlehr tritt zu Hermes'
  eigenem Speicher hinzu, es ersetzt ihn nicht. Beide liefern Kontext.
* **Der Abruf wartet hoechstens 3 Sekunden** und liefert dann, was fertig ist.
  Gegen einen kalten oder langsamen Einbettungsdienst bekommen die ersten Zuege
  eher keinen Kontext als eine verzoegerte Antwort. Dieselbe Bauform wie mem0,
  retaindb und supermemory.
* **Aus nebenlaeufigen Kontexten wird nichts geschrieben** (Cron-Laeufe,
  Unteragenten). Ihre Systemprompts sind kein Wissen; sie aufzunehmen wuerde
  den Bestand verderben. Diese Kontexte lesen nur.
* **`is_available()` macht einen kurzen lokalen Aufruf** an den
  Einbettungsdienst, mit 1,5 s Frist. Hermes' Basisklasse sagt, eine
  Verfuegbarkeitspruefung solle keine Netzaufrufe machen -- das ist eine
  bewusste Abweichung, weil ein fehlender Einbettungsdienst sonst still
  scheitert; am 2026-08-20 dreizehnmal.
* **Ein zusaetzlicher Prozess.** brainlehrs MCP-Server laeuft neben Hermes,
  solange der Anbieter benutzt wird. Jeder Aufruf hat eine Frist; haengt oder
  stirbt der Server, wird der Aufruf aufgegeben und der Prozess beim naechsten
  neu gestartet.
* **Nur stdio, kein Netztransport.** brainlehrs Server spricht MCP
  ausschliesslich ueber stdio, muss also auf demselben Rechner laufen wie
  Hermes. Auf eine brainlehr-Instanz auf einem anderen Rechner laesst sich
  dieses Plugin nicht richten.
* **Gelesen wird automatisch, geschrieben nicht.** Kontext wird vor jedem Zug
  von selbst geholt, aber es entsteht kein Eintrag, solange das Modell nicht
  `brainlehr_merken` ruft. Es gibt kein `sync_turn`: brainlehr verlangt an
  jedem Eintrag eine nachpruefbare Herkunft, und ein Automat, der Zug fuer Zug
  mitschreibt, kann keine ehrliche liefern. Das Fehlen ist eine Entscheidung,
  keine Luecke zum Nachruesten nebenbei.
* **Der Bestand ist ueberwiegend deutsch.** Gemessen 3573 deutsche gegen 1609
  englische Eintraege. Kontext kommt in der Sprache zurueck, in der er
  geschrieben wurde.

## Was von den anderen uebernommen wurde

Aus dem Quelltext der acht, jeweils weil es MEHRFACH vorkam -- was in drei von
vier Anbietern gleich geloest ist, ist eher Stand der Technik als Geschmack:

* **Abruf im Hintergrund mit kurzer Wartefrist** statt blockierend (mem0
  wartet 3 s, ebenso retaindb und supermemory). Zaehlt hier doppelt, weil
  brainlehrs Abruf lokale Einbettungen rechnen kann.
* **Trivialfilter** vor Abruf. Die Schnittstelle bringt ihn selbst mit
  (`is_trivial_prompt`) -- byterover und supermemory bauen ihn trotzdem nach.
  Wir nehmen den vorhandenen.
* **Kein Schreiben aus nebenlaeufigen Kontexten.** Die Schnittstelle warnt
  ausdruecklich: Cron-Systemprompts wuerden die Nutzerdarstellung verderben.

Bewusst NICHT uebernommen: honchos Wettlauf aus drei Hintergrund-Threads mit
sieben Zeitfenstern und Veraltungswaechter in einer Methode.

## Grenze zum blossen MCP-Eintrag

brainlehrs MCP-Server laesst sich in Hermes auch selbst unter `mcp_servers`
eintragen. Dann bekommt das Modell Werkzeuge, die es rufen KANN. Dieses Plugin
benutzt denselben Server ueber dasselbe Protokoll, haengt ihn aber in die
Speicherkette: Kontext wird **vor jedem Zug automatisch** geholt, ohne dass das
Modell sich dafuer entscheidet. Der Unterschied zwischen "kann nachschlagen"
und "weiss es schon".

Beides geht nebeneinander. Dieser Anbieter liest und schreibt den echten
Bestand.
