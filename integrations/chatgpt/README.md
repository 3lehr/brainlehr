# ChatGPT über OpenAI Secure MCP Tunnel

Der Tunnel hält Datenbank und stdio-MCP lokal. OpenAI stellt den authentifizierten HTTPS-Transport bereit; Brainlehr öffnet keinen eingehenden Port.

Voraussetzungen: `tunnel-client`, ein `tunnel_id`, ein Runtime-API-Key mit `Tunnels Read + Use` und aktivierter ChatGPT Developer Mode. Der Schlüssel gehört weder in Git noch in eine Konfigurationsdatei.

```sh
brew install openai/tools/tunnel-client
read -rsp "OpenAI Runtime-API-Key: " CONTROL_PLANE_API_KEY; export CONTROL_PLANE_API_KEY; printf '\n'
tunnel-client init --sample sample_mcp_stdio_local --profile brainlehr-chatgpt --tunnel-id tunnel_... --mcp-command "env BRAINLEHR_TOOL_PROFILE=prompt-invariance BRAINLEHR_DB=/absolute/path/to/knowledge.db python3 /absolute/path/to/brainlehr/knowledge_mcp_server.py"
tunnel-client doctor --profile brainlehr-chatgpt --explain
tunnel-client run --profile brainlehr-chatgpt
```

Erst wenn `doctor` und der laufende Client gesund sind, in ChatGPT unter Plugins eine Developer-Mode-Verbindung vom Typ **Tunnel** mit derselben `tunnel_id` anlegen. Erwartet werden genau `prompt_invarianz_planen` und `prompt_invarianz_pruefen`.

Nach dem Beenden des Clients den Schlüssel aus der Shell entfernen: `unset CONTROL_PLANE_API_KEY`.

Offizielle Anleitung: <https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>
