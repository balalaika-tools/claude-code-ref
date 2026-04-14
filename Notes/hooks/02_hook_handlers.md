# Hook Handlers

Before reading this: **[Hooks Overview](01_hooks_overview.md)**

---

## 1. Four Types

| Type | What it does | Use when |
|------|-------------|----------|
| `command` | Runs a shell script | Formatting, linting, logging, blocking |
| `http` | POSTs JSON to a URL | External logging, CI triggers, webhooks |
| `prompt` | Asks Claude yes/no | Safety checks, policy enforcement |
| `agent` | Spawns a subagent with tools | Complex validation requiring file reads |

---

## 2. Command

```json
{
  "type": "command",
  "command": "npx prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\"",
  "timeout": 60,
  "async": false,
  "statusMessage": "Formatting..."
}
```

Hook context arrives on **stdin** as JSON:

```json
{
  "session_id": "abc123",
  "event": "PostToolUse",
  "tool_name": "Write",
  "tool_input": { "file_path": "src/auth/login.ts" }
}
```

**Exit codes** (for `PreToolUse`):

| Code | Effect |
|------|--------|
| `0` | Allow |
| `1` | Block, show stdout |
| `2` | Block, show as error |

---

## 3. HTTP

```json
{
  "type": "http",
  "url": "https://hooks.example.com/audit",
  "headers": { "Authorization": "Bearer $MY_TOKEN" },
  "allowedEnvVars": ["MY_TOKEN"],
  "timeout": 30
}
```

Request body is the same JSON as command stdin. Response controls blocking:

```json
{ "allow": false, "message": "Rejected by audit service" }
```

---

## 4. Prompt

Single-turn LLM evaluation returning YES/NO:

```json
{
  "type": "prompt",
  "prompt": "Is this command safe? $ARGUMENTS\nAnswer YES or NO.",
  "model": "claude-haiku-4-5-20251001",
  "timeout": 30
}
```

YES → allow. NO → block. Use `claude-haiku-4-5-20251001` for speed.

---

## 5. Agent

Spawns a subagent that can use tools (Read, Grep, etc.) to validate:

```json
{
  "type": "agent",
  "prompt": "Verify the file at $CLAUDE_TOOL_INPUT_FILE_PATH is valid JSON with required fields: id, name, version.",
  "timeout": 60
}
```

Use when a simple prompt isn't enough — the hook needs to *read files* to decide.

---

## 6. Common Fields

| Field | Description |
|-------|-------------|
| `if` | Tool pattern filter: `Bash(git *)`, `Edit(*.ts)` |
| `statusMessage` | Custom spinner text |
| `once` | Run only once per session (skill hooks) |
| `async` | Fire-and-forget, don't block Claude (command type only) |

---

## 7. Full Example

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "npx prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\"", "async": true, "statusMessage": "Formatting..." }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "prompt", "prompt": "Command: $CLAUDE_TOOL_INPUT_COMMAND\nIs this safe? YES or NO.", "model": "claude-haiku-4-5-20251001" }
        ]
      }
    ]
  }
}
```

---

**Back to**: [Hooks Index](README.md)
