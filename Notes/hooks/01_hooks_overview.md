# Hooks Overview

> **Who this is for**: Claude Code users who understand `settings.json` and need deterministic automation or policy at lifecycle boundaries.

Before reading this, understand project settings: **[settings.json](../settings/01_settings_json.md)**

---

## 1. What Are Hooks?

Hooks are user-defined handlers that run at specific Claude Code lifecycle events. They are deterministic harness behavior, not model guidance.

```
CLAUDE.md:  "Run prettier after edits"   -> Claude may remember
Hook:       PostToolUse + Write/Edit      -> Claude Code runs it every time
```

Use hooks for enforcement, automation, logging, and validation. Keep advisory instructions in CLAUDE.md.

---

## 2. Configuration

Hooks use three levels: **event -> matcher group -> handler(s)**.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -lc 'file=$(jq -r .tool_input.file_path); npx prettier --write \"$file\"'"
          }
        ]
      }
    ]
  }
}
```

Command hooks receive event context as JSON on stdin. HTTP hooks receive the same JSON as the POST body.

Hook locations:

| Location | Scope |
|----------|-------|
| `~/.claude/settings.json` | All projects for one user |
| `.claude/settings.json` | Shared project config |
| `.claude/settings.local.json` | Local project config |
| Managed settings | Organization policy |
| Plugin `hooks/hooks.json` | When plugin is enabled |
| Skill or agent frontmatter | While that component is active |

---

## 3. Lifecycle Events

Most workflows need only a few events:

| Event | When it fires |
|-------|--------------|
| `UserPromptSubmit` | Prompt submitted, before Claude processes it |
| `UserPromptExpansion` | Slash command/skill expands before reaching Claude |
| `PreToolUse` | Before a tool call; can block or defer |
| `PermissionRequest` | Permission dialog appears |
| `PermissionDenied` | Auto mode denies a tool call |
| `PostToolUse` | After a tool call succeeds |
| `PostToolUseFailure` | After a tool call fails |
| `PostToolBatch` | After a batch of parallel tools completes |
| `Stop` | Claude finishes responding |
| `StopFailure` | Turn ends due to API error |
| `SessionStart` / `SessionEnd` | Session lifecycle |
| `Setup` | Explicit setup runs via init/maintenance flows |
| `InstructionsLoaded` | CLAUDE.md or `.claude/rules/*.md` loaded |
| `SubagentStart` / `SubagentStop` | Subagent lifecycle |
| `TaskCreated` / `TaskCompleted` | Background task lifecycle |
| `TeammateIdle` | An agent-team teammate is about to become idle |
| `WorktreeCreate` / `WorktreeRemove` | Claude Code creates or removes an isolated worktree |
| `Notification` | Claude Code sends a notification |
| `ConfigChange` | Config changes during a session |
| `CwdChanged` | Working directory changes |
| `FileChanged` | Watched file changes on disk |
| `PreCompact` / `PostCompact` | Context compaction |
| `Elicitation` / `ElicitationResult` | MCP server requests and receives user input |

Do not build hooks on events you do not need. Every blocking hook adds latency to the user experience.

---

## 4. Matchers and `if`

For tool events, `matcher` filters on tool name:

```json
{
  "matcher": "Write|Edit"
}
```

Matcher values are exact strings or `|`-separated exact strings when they contain only word characters and `|`. Values with other regex characters are treated as JavaScript regular expressions.

Use `if` on individual handlers for permission-rule-style filtering:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "if": "Bash(git push *)",
      "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/audit-push.sh"
    }
  ]
}
```

`if` is evaluated only on tool events. It is a single permission rule, not a boolean expression.

MCP tools match like normal tool names: `mcp__server__tool`. To match all tools from a server in a hook matcher, use a regex such as `mcp__github__.*`.

---

## 5. Input and Output

All hooks receive common fields such as:

```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/me/.claude/projects/.../session.jsonl",
  "cwd": "/Users/me/project",
  "hook_event_name": "PreToolUse"
}
```

Tool events also include:

```json
{
  "tool_name": "Bash",
  "tool_input": { "command": "git status" }
}
```

Prefer structured JSON output for decisions:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by project policy."
  }
}
```

Exit codes are useful for simple scripts, but JSON decisions are clearer and event-specific.

---

## 6. Common Patterns

**Format after edits:**

```json
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
```

**Block dangerous Bash:**

```json
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
```

**Log commands:**

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash -lc 'jq -r .tool_input.command >> ~/.claude/bash-audit.log'",
      "async": true
    }
  ]
}
```

---

**Next**: [Hook Handlers](02_hook_handlers.md)
