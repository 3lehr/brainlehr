# Knowledge MCP contract

`knowledge_mcp_server.py` is the only supported read/write boundary. Clients must not write `brainlehr.db` directly.

## Nodes

- Discover: `knowledge_browse`, `knowledge_search`
- Read: `knowledge_read`
- Write: `knowledge_add`, `knowledge_update`

## Explicit links

- `knowledge_relation_add`: existing source/target ID or path, allowlisted type, confidence/weight, and evidence.
- `knowledge_relation_list`: canonical link query.
- `knowledge_relation_update`: evidence/provenance/weight/type; endpoints remain stable.
- `knowledge_relation_remove`: exact relation ID only; never deletes nodes.

No tool infers links from tags, source text, titles, or similarity. Create a link only when evidence exists.

## Identity and live events

Pass `actor`, `model`, and stable `session` to MCP tools. If a client cannot pass them, set `BEGOD_KNOWLEDGE_ACTOR`, `BEGOD_KNOWLEDGE_MODEL`, and `BEGOD_KNOWLEDGE_SESSION` in that MCP process. Missing identity remains SQL `NULL` and appears as `unbekannt`; it is never guessed. `access_log.status` is `started|completed|failed` and defaults to `completed`.
