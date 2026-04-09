# .mcp.json — MCP Server Configuration

---

## 1. What Is MCP?

**Model Context Protocol** — an open standard for connecting AI assistants to external tools. An MCP server exposes tools to Claude Code (query a database, call an API, etc.).

---

## 2. File Locations

| File | Scope | Committed? |
|------|-------|-----------|
| `.mcp.json` (project root) | This project | Yes |
| `~/.claude.json` (home) | All projects | No |

---

## 3. Format

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "$DATABASE_URL"
      }
    }
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"stdio"` (only supported transport for local servers) |
| `command` | Yes | Executable: `npx`, `node`, `python`, or absolute path |
| `args` | No | Array of CLI arguments |
| `env` | No | Environment variables (all values must be strings) |

Use `$VAR` in env values to read from your shell environment at server start time. Never commit real credentials — use env var references.

---

## 4. Common Servers

**PostgreSQL:**
```json
"postgres": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres"],
  "env": { "DATABASE_URL": "$DATABASE_URL" }
}
```

**GitHub:**
```json
"github": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_TOKEN": "$GITHUB_TOKEN" }
}
```

**Filesystem (expanded access):**
```json
"filesystem": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/Documents"]
}
```

---

## 5. `.mcp.json` vs. `settings.json`

| | `.mcp.json` | `settings.json` |
|--|-------------|-----------------|
| Purpose | Define servers (command, args, env) | Enable/disable servers per scope |
| Committed | Yes | Depends on scope |

```json
// settings.json — control which servers are active
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["postgres", "github"],
  "disabledMcpjsonServers": ["slack"]
}
```

---

## 6. Applying Changes

Changes require a Claude Code restart. Check `/plugin` UI Errors tab if a server fails to start.

---

**Next**: [Settings](../settings/01_settings_json.md)
