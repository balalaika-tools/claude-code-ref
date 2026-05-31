# settings.json

---

## 1. What Is settings.json?

`settings.json` configures the Claude Code harness: permissions, environment variables, hooks, MCP server approval, model defaults, UI options, and other runtime behavior.

```
CLAUDE.md      -> what Claude should know       (model guidance)
settings.json  -> what Claude Code should allow (harness config)
.mcp.json      -> which MCP servers exist       (tool definitions)
```

---

## 2. Scopes and Precedence

| Scope | Path | Committed? | Use for |
|-------|------|-----------|---------|
| Managed | Admin-deployed managed settings | Yes, by IT | Org policy; highest priority |
| CLI flags | `claude --model ...` etc. | No | One session |
| Local project | `.claude/settings.local.json` | No | Personal project overrides |
| Shared project | `.claude/settings.json` | Yes | Team-shared project config |
| User | `~/.claude/settings.json` | No | Personal defaults |

Higher-priority settings override lower-priority settings for most scalar fields.

Permissions are special:

- Rules are evaluated `deny` -> `ask` -> `allow`.
- A matching `deny` wins even if another scope allows the same tool.
- Some arrays merge across scopes instead of replacing; check the docs for field-specific behavior.

---

## 3. Permissions

```json
{
  "permissions": {
    "allow": ["Read", "Grep", "Glob", "Bash(git diff *)"],
    "ask": ["Write", "Edit", "Bash(git push *)"],
    "deny": ["Bash(sudo *)", "Read(./.env)", "Read(./secrets/**)"],
    "additionalDirectories": ["../docs"]
  }
}
```

| Key | Behavior |
|-----|----------|
| `allow` | Use without prompting when the rule matches |
| `ask` | Prompt when the rule matches |
| `deny` | Block when the rule matches |
| `additionalDirectories` | Grant file access to extra directories |
| `defaultMode` | Set default permission mode: `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, or `bypassPermissions` |

Permission rules use `Tool` or `Tool(specifier)`:

```json
{
  "allow": [
    "Bash(npm test *)",
    "Edit(src/**/*.ts)",
    "mcp__github__get_issue"
  ],
  "deny": [
    "WebFetch",
    "Read(./.env*)"
  ]
}
```

MCP permission wildcards are not the same as shell globs. To allow all tools from an MCP server, allow the server name such as `mcp__github`; to allow one tool, list that full tool name.

---

## 4. Environment Variables

```json
{
  "env": {
    "NODE_ENV": "development",
    "LOG_LEVEL": "debug",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4-6"
  }
}
```

All values must be strings. Do not commit secrets to shared project settings. Use shell environment, secret managers, local settings, or provider-specific auth instead.

---

## 5. Hooks

Hooks are configured here unless they come from a plugin, skill, or agent. See [Hooks Overview](../hooks/01_hooks_overview.md).

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -lc 'file=$(jq -r .tool_input.file_path); npx prettier --write \"$file\"'",
            "async": true
          }
        ]
      }
    ]
  }
}
```

Prefer command hooks that read the event JSON from stdin for non-trivial logic. Use `disableAllHooks: true` only for emergency troubleshooting.

---

## 6. MCP Server Control

`.mcp.json` defines project MCP servers. Settings control which project servers are approved:

```json
{
  "enableAllProjectMcpServers": false,
  "enabledMcpjsonServers": ["postgres", "github"],
  "disabledMcpjsonServers": ["slack"]
}
```

Security rule of thumb: define project servers in `.mcp.json`, but approve only the servers the project actually needs.

---

## 7. Full Example

```json
{
  "model": "sonnet",
  "permissions": {
    "allow": ["Read", "Grep", "Glob", "Bash(git diff *)", "Bash(npm test *)"],
    "ask": ["Write", "Edit"],
    "deny": ["Bash(sudo *)", "Read(./.env)", "Read(./secrets/**)"],
    "defaultMode": "default"
  },
  "env": {
    "NODE_ENV": "development"
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -lc 'file=$(jq -r .tool_input.file_path); npx prettier --write \"$file\"'",
            "async": true
          }
        ]
      }
    ]
  },
  "enableAllProjectMcpServers": false,
  "enabledMcpjsonServers": ["postgres"]
}
```

Use model aliases in shared config unless you intentionally need to pin a full model ID.

---

## 8. Config File Summary

| File | Read by | Controls |
|------|---------|----------|
| `CLAUDE.md` | Claude | Project knowledge and guidance |
| `settings.json` | Claude Code harness | Permissions, env, hooks, model, MCP approval |
| `.mcp.json` | Claude Code harness | MCP server definitions |
| `.claude/agents/*.md` | Harness and model | Subagent definitions |
| `.claude/skills/*/SKILL.md` | Harness and model | Skill prompts and behavior |
| `.claude/commands/*.md` | Harness and model | Flat skill-compatible commands |

---

**Back to**: [Root](../README.md)
