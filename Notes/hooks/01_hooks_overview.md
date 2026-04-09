# Hooks Overview

---

## 1. What Are Hooks?

User-defined handlers that fire at Claude Code lifecycle events. Unlike CLAUDE.md (advisory), hooks are **deterministic** — the harness executes them regardless of what Claude decides.

```
CLAUDE.md:  "Always run prettier after edits"  → Claude might forget
Hook:       PostToolUse → prettier              → runs every time
```

---

## 2. Configuration

Hooks live in `settings.json` (any scope — user, project, or local).

Three-level nesting: **Event → Matcher → Handler(s)**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "npx prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\"" }
        ]
      }
    ]
  }
}
```

---

## 3. Lifecycle Events

| Event | When it fires |
|-------|--------------|
| `SessionStart` | Session begins or resumes |
| `UserPromptSubmit` | Prompt submitted, before Claude processes |
| `PreToolUse` | Before tool call — **can block it** |
| `PostToolUse` | After tool call succeeds |
| `PostToolUseFailure` | After tool call fails |
| `PermissionRequest` | Permission dialog appears |
| `PermissionDenied` | Tool call denied |
| `Stop` | Claude finishes responding |
| `StopFailure` | Turn ends due to API error |
| `Notification` | Claude Code sends notification |
| `SubagentStart` / `SubagentStop` | Subagent spawned / finished |
| `TaskCreated` / `TaskCompleted` | Task lifecycle |
| `InstructionsLoaded` | CLAUDE.md or `.claude/rules/*.md` loaded |
| `ConfigChange` | Config file changes mid-session |
| `CwdChanged` | Working directory changes |
| `FileChanged` | Watched file changes on disk |
| `WorktreeCreate` / `WorktreeRemove` | Worktree lifecycle |
| `PreCompact` / `PostCompact` | Context compaction |
| `SessionEnd` | Session terminates |

---

## 4. Matchers

Filter which tool calls trigger a hook. Used with `PreToolUse`/`PostToolUse`:

```json
"matcher": "Write|Edit|MultiEdit"
```

The `if` field on a handler supports tool patterns:

```json
{ "if": "Bash(git *)" }
{ "if": "Edit(src/**/*.ts)" }
```

---

## 5. Environment Variables

| Variable | Description |
|----------|-------------|
| `$CLAUDE_TOOL_INPUT_FILE_PATH` | File path (Write/Edit/Read hooks) |
| `$CLAUDE_TOOL_INPUT_COMMAND` | Shell command (Bash hooks) |
| `$CLAUDE_TOOL_NAME` | Tool name |
| `$CLAUDE_SESSION_ID` | Session ID |

---

## 6. Common Patterns

**Auto-format after edits:**
```json
{ "matcher": "Write|Edit", "hooks": [
  { "type": "command", "command": "npx prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\"", "async": true }
]}
```

**Block writes to sensitive dirs:**
```json
{ "matcher": "Write|Edit", "hooks": [
  { "type": "command", "command": "bash -c 'if [[ \"$CLAUDE_TOOL_INPUT_FILE_PATH\" == */secrets/* ]]; then echo \"Blocked\"; exit 1; fi'" }
]}
```

**Log bash commands:**
```json
{ "matcher": "Bash", "hooks": [
  { "type": "command", "command": "bash -c 'echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) $CLAUDE_TOOL_INPUT_COMMAND\" >> ~/.claude/audit.log'", "async": true }
]}
```

Non-zero exit from `PreToolUse` → blocks the tool call.

---

**Next**: [Hook Handlers](02_hook_handlers.md)
