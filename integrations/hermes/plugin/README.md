# brainlehr as a memory provider for Hermes

*[Deutsche Fassung: README.de.md](README.de.md)*

Hermes (Nous Research, github.com/NousResearch/Hermes-Agent) offers a **memory
provider** setting. As of 2026-08-20 it listed eight providers — byterover,
hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory — and
measured via `hermes memory status`, seven of the eight require an API key.
Only `holographic` runs purely locally.

This plugin makes brainlehr the second purely local one, and the only one where
**every entry must carry a verifiable origin**. That is not a convention but a
database trigger: an entry without a `source` is never created in the first
place. Retrieval passes that origin along.

## Requirements

* A **brainlehr checkout** on the same machine. brainlehr is a local Python
  and SQLite knowledge store; this plugin is only an adapter to it, the same
  way `holographic` is an adapter to its own SQLite file.
* **Python 3** to run it. The plugin does not import brainlehr's modules: it
  starts brainlehr's own MCP server as a **separate process** and talks to it
  over stdio (JSON-RPC 2.0). The two are separate programs exchanging
  messages, which is what that server is explicitly built for.
* An **embedding service**, by default Ollama at `http://127.0.0.1:11434`.
  Without it, entries are written without a vector and become unfindable
  through semantic search, so the provider reports itself unavailable instead.
* An **`ausweis`** (acting identity). Entries are attributed to it; without
  one the attribution is permanently marked `unbeglaubigt:` (uncertified).

**No API key, no account, no cloud.** Nothing in this plugin talks to a remote
service. The only network call it makes is to the embedding service address you
configure, which points at localhost by default.

## Installing brainlehr itself

**Today, this is a checkout — not a pip install.** The line below is what it
will be; it does not work yet, and saying otherwise would waste your first ten
minutes:

```bash
pip install brainlehr          # NOT YET ON PyPI — see below
```

Checked on 2026-08-23: the name `brainlehr` is unclaimed on PyPI, so the
command fails with *No matching distribution found* rather than installing
somebody else's package. `pip install git+https://github.com/3lehr/brainlehr`
fails too — the public repository does not yet carry the packaging metadata.

**What works today:**

```bash
git clone https://github.com/3lehr/brainlehr.git
cd brainlehr && python3 schnellstart.py
```

Then point `brainlehr_home` at that directory in the plugin settings, or use
the symlink below — the provider derives the start command from it.

Once the package is published, `mcp_command = brainlehr-mcp` replaces all of
that: the installed package brings the command, and no path and no clone are
needed. The provider already supports that setting; only the upload is
missing.

**Two things are needed, and it is worth saying why.** They are two separate
works under two licenses: the store is AGPL-3.0, this adapter is MIT, and they
talk over MCP as two processes. `pip install brainlehr` gets you the store;
this adapter still has to reach Hermes, and Hermes finds providers by scanning
directories, not by reading pip entry points (see the note in `pyproject.toml`)
— so the symlink below stays the way that demonstrably works. Installing the
adapter with `pip install hermes-brainlehr[brainlehr]` pulls the AGPL store in
as an *optional* extra: a deliberate choice of yours, never a silent one.

## Installing: symlink, not a copy

```bash
ln -s /path/to/brainlehr/integrations/hermes/plugin ~/.hermes/plugins/brainlehr
hermes memory status    # must list brainlehr
```

Replace `/path/to/brainlehr` with your own checkout.

**Why a symlink is spelled out here:** until 2026-08-21 a *copy* lived at that
location. It was identical when created and drifted silently afterwards — a
change in the repository never reached Hermes, and nothing made that visible.

**The location is not arbitrary.** `~/.hermes/plugins/` is the user area and
survives a Hermes update. The obvious location would have been
`~/.hermes/hermes-agent/plugins/memory/`, where the eight bundled providers
live — that one is replaced on update.

Check afterwards:

```bash
readlink ~/.hermes/plugins/brainlehr   # must name your checkout
ls ~/.hermes/plugins/brainlehr/        # must contain config_schema.py
```

## Configuration

The plugin declares a settings panel, so the fields are editable inside Hermes.
Every field is also readable from an environment variable, for use without the
panel.

| Setting | Environment variable | Meaning |
|---|---|---|
| `brainlehr_home` | `BRAINLEHR_HOME` | Where brainlehr lives. Only needed if you copied instead of symlinked. |
| `mcp_command` | `BRAINLEHR_MCP_COMMAND` | Command that starts brainlehr's MCP server. Derived from the checkout if empty. |
| `db_path` | `BRAINLEHR_DB` | The store file, if it is not at the checkout's default location. |
| `ausweis` | `BRAINLEHR_AUSWEIS` | The acting identity writes are attributed to. |
| `embed_service_url` | `KNOWLEDGE_OLLAMA_URL` | Embedding service address. |

**How brainlehr is located**, in order — the first source that answers wins:

1. the `mcp_command` setting or `$BRAINLEHR_MCP_COMMAND`, used as given,
2. the `brainlehr_home` setting, then `$BRAINLEHR_HOME`,
3. the directory this plugin was installed from — through the recommended
   symlink this resolves back into the checkout, so the common case needs no
   configuration at all,
4. `~/brainlehr`.

From sources 2–4 the start command is *derived* (`<this interpreter>
<checkout>/knowledge_mcp_server.py`), never hard-coded to any one machine.

If none of them yields a server that answers, `is_available()` returns `False`
and logs which sources were tried and what to set. The provider is then not
registered at all, rather than registered and broken. The same applies when the
server starts but its store does not answer.

## How it talks to brainlehr

Over **MCP (stdio, JSON-RPC 2.0)**, as a separate process — not as a library
import. That matters twice over:

* The adapter only knows the **interface**, not brainlehr's internals. It does
  not break when `knowledge_mcp_server.py` changes internally; the earlier
  import-based version would have.
* Nothing of brainlehr is ever loaded into the Hermes process.

It uses exactly three of the server's 32 tools: `knowledge_search` for
retrieval, `knowledge_add` for writes, and `knowledge_stats` to report the real
database location for backups.

## Limitations

Stated plainly, because they decide whether this plugin is useful to you:

* **Only one external memory provider can be active at a time.** Hermes'
  `agent/memory_manager.py` rejects a second one. Enabling brainlehr means
  disabling mem0, holographic or whichever you use today.
* **The built-in provider keeps running alongside.** brainlehr is added to
  Hermes' own memory, it does not replace it. Both contribute context.
* **Retrieval waits at most 3 seconds** and then returns whatever is ready.
  Against a cold or slow embedding service the first turns may get no context
  rather than a delayed answer. This mirrors mem0, retaindb and supermemory.
* **Nothing is written from non-primary contexts** (cron runs, subagents).
  Their system prompts are not knowledge, and storing them would corrupt the
  store. Those contexts read only.
* **`is_available()` makes one short local request** to the embedding service,
  with a 1.5 s deadline. Hermes' base class says availability checks should not
  make network calls; this is a deliberate deviation, because a missing
  embedding service otherwise fails silently — it did so thirteen times on
  2026-08-20.
* **One extra process.** brainlehr's MCP server runs alongside Hermes for as
  long as the provider is in use. Calls carry a deadline; if the server hangs
  or dies, the call is abandoned and the process restarted on the next one.
* **Only stdio, no network transport.** brainlehr's server speaks MCP over
  stdio only, so it must run on the same machine as Hermes. There is no way to
  point this plugin at a brainlehr on another host.
* **Reading is automatic, writing is not.** Context is retrieved before every
  turn on its own, but nothing is stored unless the model calls
  `brainlehr_merken`. There is no `sync_turn`: brainlehr requires a verifiable
  origin on every entry, and a turn-by-turn auto-writer cannot supply an honest
  one. This is a deliberate omission, not a gap to be filled casually.
* **The store is mostly German.** Measured at 3573 German against 1609 English
  entries. Retrieved context arrives in the language it was written in.

## What was adopted from the other providers

Each of these because it appeared in *several* of the eight — what three of
four solve the same way is closer to state of the art than to taste:

* **Background retrieval with a short deadline** instead of blocking (mem0
  waits 3 s, as do retaindb and supermemory). It counts double here, because
  brainlehr's retrieval may compute local embeddings.
* **The triviality filter** before retrieval. The interface ships one
  (`is_trivial_prompt`) — byterover and supermemory reimplement it anyway. This
  plugin uses the one that already exists.
* **No writes from concurrent contexts.** The interface warns about this
  explicitly.

Deliberately not adopted: honcho's race of three background threads with seven
time windows and a staleness guard in a single method.

## Scope, and how this differs from just adding the MCP server

You can already add brainlehr's MCP server to Hermes' `mcp_servers` yourself.
That gives the model tools it *may* call. This plugin uses the same server over
the same protocol, but plugs it into the memory pipeline: context is fetched
**automatically before every turn**, without the model choosing to. The
difference is "the model can look it up" versus "it already knows".

Both can coexist. This provider reads and writes the real store.
