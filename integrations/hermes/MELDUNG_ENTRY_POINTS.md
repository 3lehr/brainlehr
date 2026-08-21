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

# Zweite Meldung: kein Kanal für eine Statuszeile an den Menschen

**Anlass, aus dem Betrieb:** In Claude Code zeigt brainlehrs Abruf bei jedem
Prompt eine Zeile wie „eingespielt: Lehren L-14acea, L-1228cf, L-ce1bd8".
Unter Hermes fehlt sie — der Nutzer sieht nicht, ob der Speicher etwas
geliefert hat oder geschwiegen.

**Warum das mehr ist als Kosmetik:** Gemessen liefert unser Abruf in 34,1 %
der Fälle nichts. Ohne sichtbare Zeile sind „hat nichts gefunden" und „wurde
gar nicht gefragt" für den Nutzer ununterscheidbar — und ein Speicher, dessen
Schweigen man nicht von seinem Ausfall unterscheiden kann, ist im Zweifel
wertlos.

**Gemessener Stand** (Klon `643910afe3`):
* `agent/memory_provider.py` — keine `notify`/`status`/`emit`/`inform`-Methode
  in der ABC. `prefetch()` hat genau einen Rückgabewert, und der geht an das
  MODELL, nicht auf den Bildschirm.
* `hermes_cli/plugins.py` — `PluginContext` bietet ausschließlich
  `register_*` (Werkzeuge, Befehle, Anbieter). Kein Kanal zum Menschen.

## Titel

`No way for a plugin to surface a status line to the user`

## Text

A memory provider can inject context via `prefetch()`, but that string goes to
the model. There seems to be no way to put a short line in front of the *user*
— "recalled 3 lessons" or, just as important, "nothing found".

Claude Code has this: a hook returns a `systemMessage` field alongside the
injected context, and the client renders it as one line. It is a small thing
that turns out to matter: our recall returns nothing in 34% of turns, and
without that line "found nothing" and "was never asked" look identical to the
user. A memory whose silence you cannot distinguish from its failure is hard
to trust.

I looked at `MemoryProvider` (no `notify`/`status`-style method) and at
`PluginContext` (`register_*` only). If there's an existing path I missed, a
pointer is all I need.

If not, this would be a small widening of the generic surface — something
like an optional `ctx.notify(text)` or a second return channel on `prefetch()`
that plugins may use and the CLI/TUI may render or ignore. It would serve any
plugin that does background work the user should know happened, not just
memory ones.

Happy to open a PR if you tell me which shape you'd accept.

**Verified against** `643910afe3`.

---

## Was wir bis dahin tun

Nichts nachbauen, das auf dem Modell beruht. Ein Hinweis im `prefetch()`-Text
wäre eine Bitte an das Modell, ihn zu wiederholen — und damit genau die
Selbstauskunft, der dieses Haus nicht traut.

Was es stattdessen gibt und ehrlich ist: `hermes brainlehr pruefen` aus
`cli.py` beantwortet die Frage auf Nachfrage. Weniger bequem, aber wahr.
