# Hook Handlers

Before reading this: **[Hooks Overview](01_hooks_overview.md)**

---

## 1. Handler Types

| Type | What it does | Use when |
|------|-------------|----------|
| `command` | Runs a local command or script | Formatting, linting, policy checks, logging |
| `http` | POSTs event JSON to a URL | Central audit service, webhook, external policy engine |
| `mcp_tool` | Calls a tool on an already connected MCP server | Reuse an MCP integration inside a hook |
| `prompt` | Asks a Claude model for a structured yes/no decision | Lightweight semantic checks |
| `agent` | Spawns a subagent with tools | Complex validation requiring file reads or searches |

Prefer `command` hooks for deterministic checks. Use prompt/agent hooks when the decision genuinely needs language understanding.

---

## 2. Command

```json
{
  "type": "command",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/check-edit.sh",
  "timeout": 60,
  "async": false,
  "statusMessage": "Checking edit..."
}
```

Hook context arrives on stdin:

```json
{
  "session_id": "abc123",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": { "file_path": "src/auth/login.ts" }
}
```

Use `args` for exec form when you do not need shell features:

```json
{
  "type": "command",
  "command": "node",
  "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/check-edit.js"]
}
```

Use shell form when you need pipes, redirects, `&&`, command substitution, or environment expansion.

---

## 3. Decision Output

For `PreToolUse`, a command can deny a tool call with JSON:

```bash
#!/usr/bin/env bash
command=$(jq -r '.tool_input.command // ""')

if [[ "$command" == *"rm -rf"* ]]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "rm -rf is blocked by project policy"
    }
  }'
fi
```

For `UserPromptSubmit` and `UserPromptExpansion`, use `decision: "block"` with a `reason`. Other events have their own decision fields or no decision control. Always check the event schema before relying on blocking.

Exit code guidance:

| Exit code | Meaning |
|-----------|---------|
| `0` | Success; stdout may be used by some events |
| `2` | Blocking/error signal for events that support it |
| Other non-zero | Hook failed; usually shown/logged but not a policy decision |

Structured JSON is easier to audit than exit-code-only behavior.

---

## 4. HTTP

```json
{
  "type": "http",
  "url": "https://hooks.example.com/audit",
  "headers": { "Authorization": "Bearer $MY_TOKEN" },
  "allowedEnvVars": ["MY_TOKEN"],
  "timeout": 30
}
```

The request body is the same JSON command hooks receive on stdin. The response uses the same JSON output format as command hooks.

Only environment variables listed in `allowedEnvVars` are interpolated into headers.

---

## 5. MCP Tool

```json
{
  "type": "mcp_tool",
  "server": "policy",
  "tool": "check_command",
  "input": {
    "command": "${tool_input.command}"
  },
  "timeout": 30
}
```

Use this when the logic already lives behind an MCP server. Keep in mind that hooks depend on the server already being connected and healthy.

---

## 6. Prompt

Prompt hooks perform a single-turn model check and return a structured decision.

```json
{
  "type": "prompt",
  "prompt": "Review this hook input JSON and decide whether it asks for secrets or credential exfiltration: $ARGUMENTS",
  "model": "haiku",
  "timeout": 30
}
```

Use the fastest adequate model. Do not use prompt hooks for checks a deterministic script can perform.

---

## 7. Agent

Agent hooks spawn a subagent that can use tools before returning a decision.

```json
{
  "type": "agent",
  "prompt": "Read the edited file and verify it is valid JSON with required fields: id, name, version.",
  "timeout": 60
}
```

Use agent hooks sparingly. They are powerful but slower, more complex, and still evolving.

---

## 8. Common Fields

| Field | Description |
|-------|-------------|
| `type` | `command`, `http`, `mcp_tool`, `prompt`, or `agent` |
| `if` | Permission rule filter for tool events |
| `timeout` | Seconds before cancellation |
| `statusMessage` | Spinner text while the hook runs |
| `once` | Honored for skill-frontmatter hooks only |
| `async` | Background execution for command hooks |
| `asyncRewake` | Background command hook can wake Claude on exit code 2 |

---

## 9. Full Example

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
            "async": true,
            "statusMessage": "Formatting..."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(rm *)",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh"
          }
        ]
      }
    ]
  }
}
```

---

**Back to**: [Hooks Index](README.md)
