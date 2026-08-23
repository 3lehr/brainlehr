# Vorbereitete Meldung an NousResearch/hermes-agent

**Stand 2026-08-23. Belege gegen Hermes-Commit `1684877868` nachgemessen.**

Zum Absenden: <https://github.com/NousResearch/Hermes-Agent/issues/new> —
Titel und Text unten sind kopierfertig. Der Betreiber entscheidet, ob und
wann; ein Beitrag an ein fremdes Projekt ist Aussenwirkung.

---

## Titel

`Docs never name the entry-point group for memory providers — and there are two different ones in the tree`

## Text

CONTRIBUTING.md points standalone memory-plugin authors at pip entry points
twice:

> publish it as a **standalone plugin repo** that users install into
> `~/.hermes/plugins/` (or via a pip entry point) — line 72
>
> Use the same discovery system — `discover_memory_providers()` picks them up
> from user/project plugin directories and pip entry points — line 77

Both are accurate: `discover_memory_providers()` does read entry points
(`plugins/memory/__init__.py::_iter_entry_points`). What neither line says is
**which group name to declare** — and there are two in the tree, with
different values:

| constant | file | value |
|---|---|---|
| `ENTRY_POINTS_GROUP` | `hermes_cli/plugins.py:399` | `hermes_agent.plugins` |
| `ENTRY_POINTS_GROUP` | `plugins/memory/__init__.py:50` | `hermes_agent.memory_providers` |

Memory providers are found only through the second. A plugin that declares the
first installs cleanly, and is then invisible to `hermes memory` — no error, no
log line.

I searched `CONTRIBUTING.md`, `README.md` and `docs/` for either literal:
no match. And none of the eight bundled providers ships a `pyproject.toml`, so
there is no example in the repository to read it off either. The name is
discoverable only by reading `plugins/memory/__init__.py`.

**A second, smaller trap in the same place:** the entry-point *value* has to
resolve to something `_load_provider_from_entry_point()` can use — an instance,
a `MemoryProvider` subclass, an object with `.register`, or a callable. Pointing
it at the module (the shape most plugin ecosystems accept) falls through all
four branches and returns `None`, again silently.

**Suggested fix, docs only:** name the group in CONTRIBUTING.md next to line
77, and show one line of `pyproject.toml`:

```toml
[project.entry-points."hermes_agent.memory_providers"]
myprovider = "my_module:MyProvider"     # a class, not the module
```

I'm happy to open that PR if it's welcome. I have no view on whether the two
constants should be reconciled in code — that's a design question for you, and
naming the right one in the docs already removes the trap.

**Context:** found while packaging a standalone memory provider. I had declared
`hermes_agent.plugins`, having read only `hermes_cli/plugins.py`, and the
plugin was silently undiscoverable until I read the memory package. Everything
else in CONTRIBUTING worked as written.

---

# Was aus der ersten Fassung wurde

**ZURUECKGEZOGEN am 2026-08-23.** Die urspruengliche Meldung behauptete,
`discover_memory_providers()` lese ueberhaupt keine entry points, und
CONTRIBUTING.md verspreche damit etwas Unzutreffendes. Beim Nachmessen gegen
den heutigen Stand: `plugins/memory/__init__.py` traegt sechs Bezuege auf
`importlib.metadata`/`entry_points` (Zeilen 36, 161, 164, 237, 257, 298). Die
Luecke ist geschlossen; die Meldung waere ein Fehlbericht gewesen.

Das ist die ZWEITE vorbereitete Meldung an dieses Projekt, die sich beim
Nachpruefen als falsch erwies (die erste betraf einen Statuskanal, den Hermes
sehr wohl hat). Beide waren mit Fundstellen und Belegstand geschrieben, also
besonders glaubwuerdig -- und beide haetten einem fremden Projekt einen Mangel
gemeldet, den es nicht hat.

**Die Lehre daraus, und sie steht hier statt im Wissensspeicher, weil sie
genau hier gebraucht wird:** Ein Befund ueber fremden Code altert schneller
als einer ueber eigenen. Vor dem Absenden wird er gegen den TAGESAKTUELLEN
Stand des fremden Repos neu gemessen -- nicht gegen den Commit, an dem er
entstand. Zwischen Entstehen und Absenden lagen hier zwei Tage.

**Und der Ertrag der Nachpruefung war groesser als die Meldung:** Sie fand
einen Fehler in UNSEREM Paket (falsche Eintragspunkt-Gruppe, `d219fbb3`), der
dazu gefuehrt haette, dass das Plugin per pip nie gefunden wird.
