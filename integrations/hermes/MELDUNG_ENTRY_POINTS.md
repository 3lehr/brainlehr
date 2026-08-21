# Vorbereitete Meldungen an NousResearch/hermes-agent

Zwei Stück, beide ungesendet, beide derselben Klasse: eine Lücke in der
generischen Plugin-Fläche, nicht ein neuer Anbieter.

**Nicht abgeschickt.** Das Öffnen eines Issues in einem fremden Repo ist
Außenwirkung und gehört dem Betreiber. Der Text unten ist fertig zum Einfügen.

**Warum diese Meldung zulässig ist, während ein Anbieter-PR es nicht wäre:**
Ihre `CONTRIBUTING.md` Zeile 98 lädt sie ausdrücklich ein — *„If your plugin
needs a capability the framework doesn't expose, that's a feature request to
**widen the generic plugin surface**."* Es geht nicht um einen neuen Anbieter,
sondern um eine Lücke in ihrer eigenen Fläche.

**Belegstand:** Klon `~/.hermes/hermes-agent`, HEAD `643910afe3`, gelesen und
nachgeprüft am 2026-08-21. Alle drei Fundstellen selbst geöffnet, nicht aus
einer Zusammenfassung übernommen.

---

## Titel

`Memory providers are not discoverable via pip entry points, contrary to CONTRIBUTING.md`

## Text

CONTRIBUTING.md tells standalone memory plugin authors that entry points work:

> Use the same discovery system — `discover_memory_providers()` picks them up
> from user/project plugin directories **and pip entry points**
> — CONTRIBUTING.md, line 77

As far as I can tell from the code, `discover_memory_providers()` never looks
at entry points, and the general plugin loader cannot route one either. I may
be missing a path — if so, I'd be glad to be corrected, and the docs line is
then the only thing that needs a pointer.

**1. `discover_memory_providers()` iterates directories only.**
`plugins/memory/__init__.py:157` builds its result solely from
`_iter_provider_dirs()`. That helper (`:90`) scans the bundled directory and
the user/project plugin directories, and skips anything without an
`__init__.py` on disk. There is no `importlib.metadata` or `entry_points`
reference anywhere in the file.

**2. The general loader reads entry points, but its hand-off to memory
discovery needs a directory.** `hermes_cli/plugins.py:1749-1763` coerces a
user-installed plugin to `kind="exclusive"` — the memory route — by reading
`plugin_dir / "__init__.py"` and text-scanning it for `register_memory_provider`
or `MemoryProvider`. An entry-point distribution has neither a `plugin_dir`
nor that file in the expected place, so the coercion cannot fire.

**Effect:** a memory plugin packaged with `[project.entry-points."hermes_agent.plugins"]`
installs cleanly and is then invisible to `hermes memory` — no error, no log
line. It works only when symlinked or copied into `~/.hermes/plugins/`.

**Two possible resolutions**, and I have no stake in which:

* **Docs** — drop "and pip entry points" from line 77 for memory providers,
  and say plainly that they are directory-discovered. Cheapest, and it makes
  the promise true.
* **Code** — have `discover_memory_providers()` also consult
  `ENTRY_POINTS_GROUP` (`hermes_cli/plugins.py:221`) and resolve the module
  path of each matching distribution. This is the one that widens the generic
  surface, which is what CONTRIBUTING asks such requests to aim at.

I'm happy to open a PR for either, but I wanted to check the reading first
rather than send a patch built on a misunderstanding.

**Context, for what it's worth:** I hit this while packaging a standalone
memory provider exactly as CONTRIBUTING describes. The plugin itself is fine —
this is only about the discovery path. Symlink installation works; the
`pyproject.toml` sits there unused.

**Verified against** `643910afe3`.

---
---

# ZURÜCKGEZOGEN — die zweite Meldung war falsch

**Nicht senden.** Der Befund „Hermes hat keinen Kanal für eine Statuszeile"
ist **widerlegt**, und zwar durch eigenes Nachsehen auf Nachfrage des
Betreibers („bist du dir da 100 %? könnten wir es mit unserem plugin
nachrüsten?").

**Was ich übersehen hatte, an zwei Stellen:**

1. **`agent/agent_init.py:1735-1737`** — Hermes reicht einem Speicher-Anbieter
   in `initialize()` zwei Rückrufe mit, sobald die Plattform `cli` ist:
   ```python
   _init_kwargs["warning_callback"] = agent._emit_warning
   _init_kwargs["status_callback"] = agent._emit_status
   ```
2. **`run_agent.py:960`** beschreibt genau das Gewünschte: *„Emit a lifecycle
   status message to both CLI and gateway channels. CLI users see the message
   via `_vprint(force=True)` so it is always visible regardless of
   verbose/quiet mode."*

Der Kanal existiert also und ist für Anbieter gedacht. Zusätzlich hat
`PluginContext` eine Methode `inject_message` — für unseren Zweck ungeeignet
(sie startet einen Zug oder unterbricht einen laufenden), aber sie widerlegt
ebenfalls die pauschale Aussage „ausschließlich `register_*`".

**Warum ich es nicht gefunden habe, und das ist die Lehre:** Ich habe die
**ABC** und die **öffentlichen Methoden** abgesucht — `status_callback` steht
in keiner von beiden. Es kommt als `kwarg` in `initialize()` an, und die
ABC-Dokumentation zählt unter „kwargs may also include" sieben andere Namen
auf, diesen aber nicht. Eine Fähigkeit, die nur im **Aufrufer** steht, findet
nicht, wer beim Aufgerufenen sucht.

**Was daraus folgt:** Kein Beitrag an Hermes nötig. Die Statuszeile wird im
eigenen Plugin nachgerüstet — siehe `brainlehr_provider.py`.

**Die Einschränkung, die dabei gilt:** Die Rückrufe kommen nur bei
`platform == "cli"`. Im Gateway-, Telegram- oder Discord-Betrieb sind sie
nicht dabei; dort muss der Anbieter ohne auskommen, ohne zu stürzen.

