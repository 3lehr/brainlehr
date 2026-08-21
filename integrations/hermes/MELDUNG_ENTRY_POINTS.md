# Vorbereitete Meldung an NousResearch/hermes-agent

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
