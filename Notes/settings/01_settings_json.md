# settings.json

---

## 1. What Is settings.json?

Behavioral configuration for the Claude Code harness. Controls permissions, env vars, hooks, and MCP.

```
CLAUDE.md      → what Claude knows    (read by model)
settings.json  → how Claude behaves   (read by harness)
.mcp.json      → which servers exist  (read by harness)
```

---

## 2. Scopes

| Scope | Path | Committed? | Use for |
|-------|------|-----------|---------|
| Managed | System-deployed | Yes (IT) | Org-wide policies, can't be overridden |
| User | `~/.claude/settings.json` | No | Personal defaults |
| Project | `.claude/settings.json` | Yes | Team-shared project config |
| Local | `.claude/settings.local.json` | No | Personal project overrides |

**Merge behavior**: Managed settings always win. For `deny` permissions, all scopes are merged (union — you can't un-deny). For other fields, more specific scopes override broader ones.

---

## 3. Permissions

```json
{
  "permissions": {
    "allow": ["Read", "Grep", "Glob", "Bash(git *)"],
    "deny": ["Bash(rm *)", "Bash(sudo *)"],
    "ask": ["Write", "Edit"]
  }
}
```

| Key | Behavior |
|-----|----------|
| `allow` | No permission prompt |
| `deny` | Always blocked |
| `ask` | Must request permission each time |

Tool patterns use globs: `Bash(git *)`, `Edit(src/**/*.ts)`, `Write(/etc/*)`.

---

## 4. Environment Variables

```json
{
  "env": {
    "NODE_ENV": "development",
    "LOG_LEVEL": "debug"
  }
}
```

All values must be strings. Don't put secrets in committed files — use `.claude/settings.local.json`.

---

## 5. Hooks

Configured here. See [Hooks Overview](../hooks/01_hooks_overview.md) for the full reference.

```json
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Write|Edit", "hooks": [
        { "type": "command", "command": "npx prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\"", "async": true }
      ]}
    ]
  }
}
```

---

## 6. MCP Server Control

Enable/disable servers defined in `.mcp.json`:

```json
{
  "enableAllProjectMcpServers": false,
  "enabledMcpjsonServers": ["postgres", "github"],
  "disabledMcpjsonServers": ["slack"]
}
```

---

## 7. Full Example

```json
{
  "permissions": {
    "allow": ["Read", "Grep", "Glob", "Bash(git *)", "Bash(npm run *)"],
    "ask": ["Write", "Edit"],
    "deny": ["Bash(rm -rf *)", "Bash(sudo *)"]
  },
  "env": {
    "NODE_ENV": "development"
  },
  "hooks": {
    "PostToolUse": [
      { "matcher": "Write|Edit", "hooks": [
        { "type": "command", "command": "npx prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\"", "async": true }
      ]}
    ]
  },
  "enableAllProjectMcpServers": true
}
```

---

## 8. Config File Summary

| File | Read by | Controls |
|------|---------|---------|
| `CLAUDE.md` | Claude (model) | Project knowledge, rules |
| `settings.json` | Harness | Permissions, env, hooks, MCP |
| `.mcp.json` | Harness | MCP server definitions |
| `.claude/agents/*.md` | Both | Subagent definitions |
| `.claude/skills/*/SKILL.md` | Both | Skill prompts |
| `.claude/commands/*.md` | Both | Custom slash commands |

---

**Back to**: [Root](../README.md)
