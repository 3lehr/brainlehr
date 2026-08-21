# `hermes-brainlehr` als eigenständiges Repo ausliefern

Stand 2026-08-21. Betreiberentscheidung: Das Repo heißt **`hermes-brainlehr`**
— derselbe Name wie das Paket in `plugin/pyproject.toml`.

## Warum überhaupt ein eigenes Repo

Nicht aus Vorliebe, sondern weil Hermes es vorschreibt. `CONTRIBUTING.md`
Zeile 72 des Projekts `NousResearch/hermes-agent`:

> „We are no longer accepting new memory providers into this repo. […] publish
> it as a **standalone plugin repo**."

Zeile 84 nennt den Grund und stellt ausdrücklich klar, dass es kein
Qualitätsurteil ist: *„This isn't a quality bar — it's a
coupling-and-maintenance decision."* Ein Pull Request in ihren Baum wird nach
ihrer eigenen Ankündigung geschlossen.

## Die drei Namen, und nur einer ist gebunden

| | Wert | Bindung |
|---|---|---|
| Anbietername | `brainlehr` | **gebunden** — Verzeichnisname unter `~/.hermes/plugins/`, `find_provider_dir()` löst darüber auf, `config.yaml` trägt ihn |
| Paketname | `hermes-brainlehr` | frei gewählt, steht in `pyproject.toml` |
| Repo-Name | `hermes-brainlehr` | frei gewählt, in Hermes **nirgends sichtbar** |

Wer den Verzeichnisnamen ändert, bricht die Auflösung. Die anderen beiden
sind reine Auffindbarkeit für Menschen.

## Was ausgeliefert wird

Der Inhalt von `integrations/hermes/plugin/` — fünf Dateien plus zwei
READMEs:

```
brainlehr_provider.py   MemoryProvider-ABC, spricht brainlehr über MCP
config_schema.py        neun Felder, Erklärungen zweisprachig
cli.py                  register_cli(), Unterbefehl `pruefen`
plugin.yaml             Name, Version, Beschreibung
pyproject.toml          Paket + entry point `hermes_agent.plugins`
README.md / README.de.md
__init__.py
```

## Der Handgriff

```bash
mkdir hermes-brainlehr && cd hermes-brainlehr
cp -r /Volumes/daten/Begod2026/brainlehr/integrations/hermes/plugin/. .
rm -rf __pycache__
git init && git add -A && git commit -m "..."
```

Danach anlegen und pushen — **das ist Außenwirkung und gehört dem
Betreiber.** Kein Agent und keine Sitzung tut das ungefragt.

## Was VORHER entschieden sein muss

**Die Lizenz.** Sie ist bewusst nicht gesetzt, und der Grund ist eine
Prämissenänderung:

Am 2026-08-21 wurde erwogen, den Adapter unter MIT zu stellen, weil brainlehr
AGPL-3.0 trägt und Hermes MIT — eine AGPL-Datei in ihrem Baum wäre ein
Konflikt gewesen. Der Betreiber fand das „am sympathischsten". **Diese
Prämisse ist entfallen:** Da nichts in ihren Baum wandert, berührt unsere
Lizenz Hermes nicht mehr. Die Wahl ist damit frei, nicht mehr erzwungen — und
eine unter geänderter Prämisse getroffene Entscheidung wird nicht
stillschweigend fortgeschrieben.

Zwei Wege, beide vertretbar:

* **MIT** — der Adapter ist eine dünne Anbindung ohne brainlehr-Logik. Er
  spricht seit dem MCP-Umbau nur noch über die Schnittstelle; kein einziges
  brainlehr-Modul läuft im Hermes-Prozess (belegt: Server-PID ungleich
  eigener PID, `knowledge_mcp_server` nicht in `sys.modules`). Wer ihn
  übernimmt, bekommt nichts Schützenswertes.
* **AGPL-3.0** — dieselbe Lizenz wie der Kern, keine zweite Lizenzlage im
  Haus zu pflegen.

**Und wo sie hingehört:** an eine Stelle, die ein **Programm** lesen kann.
Am 2026-08-17 ging der öffentliche Export drei Tage lang mit der falschen
Lizenz hinaus, weil `push_guard.py` prüft, WOHIN etwas geht, und nie, WAS
darin steht (`L-0f4234`). Eine Lizenz in Prosa überlebt das nächste
Neuanlegen nicht.

## Was danach noch offen ist

* **Der pip-Weg ist auf Hermes' Seite tot.** Ihre `CONTRIBUTING.md` Zeile 77
  verspricht Auffindung über entry points; `plugins/memory/__init__.py`
  durchsucht ausschließlich Verzeichnisse, keine Zeile `importlib.metadata`.
  Belegbar trägt nur der Symlink. Die `pyproject.toml` liegt trotzdem bei —
  sie wirkt, sobald der Lader nachzieht.
* **Das wäre der Beitrag, den sie ausdrücklich wollen:** *„If your plugin
  needs a capability the framework doesn't expose, that's a feature request to
  widen the generic plugin surface."* Ein Pull Request, der die
  entry-point-Auffindung für Speicher-Anbieter nachrüstet, fällt nicht unter
  ihre Ablehnungsregel.
* **Bekanntmachung** über ihren Discord-Kanal `#plugins-skills-and-skins` —
  ebenfalls Außenwirkung.
