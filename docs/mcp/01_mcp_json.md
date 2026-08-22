# .mcp.json — MCP Server Configuration

> **Who this is for**: Engineers comfortable with JSON and the terminal who want Claude Code to use external tools or data safely.

Before reading this, understand project settings and permissions: **[settings.json](../settings/01_settings_json.md)**

---

## 1. What Is MCP?

**Model Context Protocol (MCP)** is an open protocol for connecting Claude Code to external tools and data sources: databases, issue trackers, internal APIs, docs, browsers, cloud services, and more.

An MCP server can expose:

- Tools Claude can call
- Resources you can reference with `@server:...`
- Prompts that appear as slash commands
- Elicitation requests for structured user input

Use MCP to extend what Claude can do. Use hooks to react to what Claude Code is doing.

---

## 2. Where Configuration Lives

| Scope | Storage | Committed? | Use for |
|-------|---------|-----------|---------|
| Local (default CLI add) | User config for current project | No | Personal project server |
| Project | `.mcp.json` | Yes | Team-shared server definitions |
| User | User-level Claude config | No | Servers available across projects |
| Plugin | Plugin `.mcp.json` | Yes | Servers bundled with a plugin |

Project `.mcp.json` servers require trust/approval before use. Settings can approve all project servers or only named ones.

---

## 3. Stdio Server Format

Use `stdio` for local processes Claude Code starts.

```json
{
  "mcpServers": {
    "local-tool": {
      "type": "stdio",
      "command": "node",
      "args": ["./scripts/mcp-server.js"],
      "env": {
        "API_TOKEN": "$API_TOKEN"
      }
    }
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | No for stdio | Transport type; `stdio` for local process servers |
| `command` | Yes | Executable to start |
| `args` | No | CLI arguments |
| `env` | No | Environment variables for the server |

Use `$VAR` or `${VAR}` references instead of committing secrets. The variable is resolved from the environment at server start.

---

## 4. Remote Server Format

Use `http` for remote MCP servers:

```json
{
  "mcpServers": {
    "internal-api": {
      "type": "http",
      "url": "https://mcp.internal.example.com/mcp",
      "headers": {
        "X-Workspace": "payments"
      }
    }
  }
}
```

Remote servers may use OAuth. Claude Code handles interactive authentication through `/mcp` when the server supports it.

For custom short-lived auth, use `headersHelper`:

```json
{
  "mcpServers": {
    "internal-api": {
      "type": "http",
      "url": "https://mcp.internal.example.com/mcp",
      "headersHelper": "/opt/bin/get-mcp-auth-headers.sh"
    }
  }
}
```

`headersHelper` runs a shell command, so review project-scoped definitions carefully before trusting them.

---

## 5. Adding Servers

Prefer the CLI when possible; it writes the right scope and avoids JSON mistakes.

```bash
# Local stdio server
claude mcp add my-server -- node ./scripts/mcp-server.js

# Project-scoped server shared through .mcp.json
claude mcp add my-server --scope project -- node ./scripts/mcp-server.js

# Remote HTTP server
claude mcp add --transport http docs https://mcp.example.com/mcp

# Inspect configured servers
claude mcp list
claude mcp get my-server
```

Use `/mcp` inside Claude Code to check connection status, authenticate OAuth servers, and inspect available tools/prompts.

For startup, authentication, or zero-tool failures, use the MCP diagnostics in
[Troubleshooting](../operations/01_troubleshooting.md).

---

## 6. `.mcp.json` vs. `settings.json`

| | `.mcp.json` | `settings.json` |
|--|-------------|-----------------|
| Purpose | Define MCP servers | Approve/disable project MCP servers and set env |
| Shared? | Usually yes | Depends on scope |
| Contains secrets? | No | No, except local-only references |

```json
{
  "enableAllProjectMcpServers": false,
  "enabledMcpjsonServers": ["postgres", "github"],
  "disabledMcpjsonServers": ["slack"]
}
```

---

## 7. MCP vs. Hooks

| | MCP | Hooks |
|--|-----|-------|
| Purpose | Give Claude new tools/data | Automate or enforce lifecycle behavior |
| Runs | When Claude chooses or user references a resource/prompt | At configured events |
| Can block actions | Not directly | Yes, for supported events |
| Example | Query database, read issue tracker, call internal API | Auto-format, deny unsafe Bash, log tool usage |

MCP can introduce prompt-injection risk because external tools return text Claude may act on. Prefer trusted servers, least-privilege credentials, and narrow tool permissions.

> **Key insight**: Every MCP tool result is untrusted input that Claude reads and may act on, so the real security boundary for MCP is server trust and least-privilege credentials, not the protocol itself.

---

## 8. Resources and Tool Search

MCP resources can be referenced with `@` mentions:

```text
Analyze @github:issue://123 and propose a fix.
Compare @postgres:schema://users with @docs:file://database/user-model.
```

Claude Code also uses MCP tool search to avoid loading every tool schema into context upfront. Server descriptions matter: concise, specific descriptions help Claude discover the right tools.

---

**Next**: [Settings](../settings/01_settings_json.md)
