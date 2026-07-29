# Troubleshooting Claude Code Configuration

> **Who this is for**: Competent Claude Code users diagnosing broken settings, rules, skills, agents, hooks, MCP servers, plugins, permissions, or sessions.

Before reading this, understand where project and user configuration lives: **[The `.claude/` Directory](../settings/02_claude_directory.md)**.

---

## 1. Diagnose in Layers

Treat configuration debugging as an evidence problem. First prove which layer is broken, then inspect that layer:

```text
┌──────────────────────────────┐
│ 1. Installation and startup  │  claude doctor
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ 2. Resolved session state    │  /doctor, /status, /context
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ 3. Feature-specific state    │  /skills, /hooks, /mcp, /permissions
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ 4. Isolation                 │  --safe-mode, clean config, scope bisect
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ 5. Event trace               │  --debug, --debug-file, /debug
└──────────────────────────────┘
```

Record the launch directory, exact symptom, smallest reproducing prompt, and whether the failure occurs in a new session. Configuration discovery is path- and scope-dependent, so “same config” is not a useful comparison unless those inputs are also the same.

> **Principle**: Inspect what Claude Code loaded, not what you intended it to load.

---

## 2. Establish a Read-Only Baseline

Start outside the interactive client when Claude Code fails to launch or fails before you can enter a command:

```bash
# Capture the binary and installation state without starting a session.
claude --version
claude doctor
```

`claude doctor` prints read-only installation and settings diagnostics. It is the safest first check for invalid settings, duplicate or unhealthy installs, and startup problems.

When a session opens, run:

```text
/doctor
/status
/context
```

These commands answer different questions:

| Command | Use it to answer |
|---------|------------------|
| `claude doctor` | Can the installed CLI and settings be validated without opening a session? |
| `/doctor` | What setup, settings, extension, and context problems can the current session detect? |
| `/status` | Which settings sources are active, and is managed policy in effect? |
| `/context` | Which memory files, skills, agents, MCP tools, and other content actually entered this session? |

Unlike the terminal command, `/doctor` can propose fixes and applies them only after confirmation. Read its diagnosis before accepting a change. A valid file can still lose to a higher-precedence source, so pair `/doctor` with `/status`.

---

## 3. Isolate Customization Before Editing It

Launch the same project in safe mode:

```bash
cd /path/to/project
claude --safe-mode
```

Safe mode disables custom `CLAUDE.md`, rules, skills, plugins, hooks, MCP servers, commands, agents, output styles, and other customizations for that session. Authentication, model selection, built-in tools, and permissions still work. Managed settings policy still applies, including policy-configured hooks, so safe mode is not a bypass for organization controls.

Interpret the result:

| Result | Conclusion | Next check |
|--------|------------|------------|
| Failure disappears | A disabled customization is involved | Bisect by scope, then by component |
| Failure remains | Look outside ordinary customization | `/status`, permissions, installation, account/model errors, or runtime stability |
| Only project fails | Project or local scope is suspect | Compare `project` and `local` setting sources |
| Every project fails | User or managed scope is suspect | Compare user scope; inspect managed state in `/status` |

For a stronger isolation test, use a temporary configuration directory and a directory with no project configuration:

```bash
diagnostic_config_dir="$(mktemp -d)"
chmod 700 "$diagnostic_config_dir"

(
  cd /tmp
  CLAUDE_CONFIG_DIR="$diagnostic_config_dir" claude
)

printf 'Temporary diagnostic config: %s\n' "$diagnostic_config_dir"
```

This avoids loading your normal `~/.claude` state and project configuration. First-run setup may appear. Managed settings can still apply because they live outside the user configuration directory.

⚠️ Do not copy your entire real configuration into the temporary directory. Add one file or one scope at a time; otherwise the test stops isolating anything.

---

## 4. Inspect the Failing Surface

Use the narrowest inspection command that can prove whether a component loaded:

| Symptom | First check | Common cause |
|---------|-------------|--------------|
| Setting appears ignored | `/status`, then `/doctor` | Local, CLI, environment, or managed value overrides it |
| `CLAUDE.md` instruction is absent | `/context` | Wrong launch directory, wrong location, or excluded setting source |
| Rule applies to the wrong files | `/context`, then read a matching file | Incorrect `paths` glob; path-scoped rules trigger when matching files are read |
| Instruction loaded but is not followed | `/context` | Contradictory, vague, or overly long guidance; guidance is not enforcement |
| Skill is missing | `/skills` and `/context` | Expected `.claude/skills/<name>/SKILL.md` structure is not present |
| Skill never auto-invokes | `/skills` | `disable-model-invocation: true` or a description that does not match the request |
| Agent is missing or stale | `/context` | Wrong agent scope, duplicate name, or a new unwatched `agents/` directory |
| Hook is missing | `/hooks`, then `/doctor` | Hook is outside `settings.json`, its source settings file is invalid, or a plugin was not reloaded |
| Hook appears but never fires | `/hooks`, then `claude --debug hooks` | Misspelled or case-mismatched tool name; invalid matcher shape |
| MCP server is disabled | `/mcp` | Project server approval was dismissed |
| MCP server fails to start | `/mcp`, then `claude --debug mcp` | Relative command path, missing server environment, auth failure, or process error |
| MCP server connects with zero tools | `/mcp` and **Reconnect** | Server started but did not return a tool list |
| Plugin change is missing | `/plugin`, then `/reload-plugins` | Installed copy is disabled, has a load error, or has not reloaded |
| Allowed tool is still blocked | `/permissions`, then `/status` | A matching deny rule or managed policy wins |
| Session hangs | `Ctrl+C`, then restart and resume | A tool, server, hook, search, or runtime operation is stuck |

Hook matchers are strings, not arrays, and tool names are case-sensitive. Use a single matcher such as:

```json
{
  "matcher": "Edit|Write"
}
```

Project MCP definitions belong in the repository-root `.mcp.json`, not `.claude/.mcp.json` or a `settings.json` `mcpServers` key. For local MCP scripts, prefer an absolute path: relative `command` and `args` paths resolve from the directory where Claude Code was launched.

If a session becomes unresponsive, cancel the current operation with `Ctrl+C`. If the client must be closed, resume the conversation from the same project:

```bash
cd /path/to/project
claude --resume
```

---

## 5. Know What Reloads

Reload behavior differs by component. Testing with the wrong expectation can make a fixed file look broken.

| Component | Current-session behavior | When to restart or reload |
|-----------|--------------------------|---------------------------|
| `settings.json` and settings-based hooks | File watcher applies edits after a brief stability delay | Refresh `/hooks`; restart only if state remains stale |
| Standalone skill `SKILL.md` text | Changes under existing watched skill directories load in the current session | Restart if the top-level skills directory did not exist at session start |
| Standalone agent files | Changes under existing `~/.claude/agents/` and `.claude/agents/` directories are detected within seconds; the next delegation uses them | Restart after creating a scope’s first `agents/` directory |
| Plugin components | Installed plugin state is not fully refreshed by ordinary file watching | Run `/reload-plugins` after install, enable/disable, or component edits |
| Plugin MCP servers | Loaded with the plugin | Run `/reload-plugins` to connect or disconnect them |
| Project or user MCP configuration | Server configuration is established when the session starts | Start a new session after config edits; use **Reconnect** for a loaded server |
| MCP capabilities | Servers can announce dynamic capability changes | No reconnect is needed when the server sends `list_changed` |
| Root memory and unscoped rules | Loaded at session start | Use a fresh session to test startup loading |
| Nested memory and path-scoped rules | Load when Claude reads a matching file | Read the target file, then inspect `/context` |

`/reload-plugins` reloads plugin skills, agents, hooks, MCP servers, and other plugin components. It is not a general-purpose reload command for standalone project configuration. Likewise, `/compact` manages conversation context; do not use it as a configuration reload strategy.

---

## 6. Trace the Failure

Enable only the debug categories relevant to the symptom:

```bash
# Hooks: records event matching, exit status, stdout, and stderr.
claude --debug hooks

# MCP: includes connection diagnostics and server stderr.
claude --debug mcp

# Multiple categories can be combined.
claude --debug "hooks,mcp"
```

`--debug` writes a per-session log under `~/.claude/debug/`; it does not print the trace to the terminal. Use `--debug-file` when you need a known, access-controlled location:

```bash
debug_dir="$(mktemp -d)"
chmod 700 "$debug_dir"

(
  umask 077
  claude --debug "hooks,mcp" \
    --debug-file "$debug_dir/claude.log"
)

printf 'Debug log: %s\n' "$debug_dir/claude.log"
```

For high-volume matcher details, add `CLAUDE_CODE_DEBUG_LOG_LEVEL=verbose` only while reproducing the issue:

```bash
CLAUDE_CODE_DEBUG_LOG_LEVEL=verbose \
  claude --debug hooks --debug-file /path/to/private/claude-hooks.log
```

Inside an existing session, `/debug [issue]` enables logging and asks Claude to diagnose the described problem using the log and active settings paths:

```text
/debug skill appears in /skills but never invokes
```

⚠️ Treat debug logs as sensitive. Hook traces can contain full stdout and stderr; MCP traces can contain server errors; paths and configuration details can reveal internal structure. Store logs in a private directory, reproduce with test credentials when possible, inspect locally, and redact secrets, tokens, cookies, headers, personal data, and proprietary content before sharing. Delete shared copies according to your retention policy after the investigation.

---

## 7. Bisect Without Destroying State

Once safe mode proves customization is involved, reintroduce one dimension at a time.

First separate settings scopes:

```bash
# Test one source at a time.
claude --setting-sources user
claude --setting-sources project
claude --setting-sources local

# Then test combinations to expose precedence conflicts.
claude --setting-sources user,project
claude --setting-sources user,project,local
```

Then bisect within the failing scope:

1. Reproduce with only settings and memory.
2. Add skills and agents.
3. Add MCP servers one at a time.
4. Enable half the suspect plugins, run `/reload-plugins`, and test.
5. Split the failing half again until one plugin or component remains.
6. For hooks, use `/hooks` to confirm the source, then reproduce with `--debug hooks`.
7. Reduce the final component to the smallest failing definition.

Keep a short matrix of test conditions and outcomes. Change one variable per run and use the same prompt, working directory, permission mode, and model.

> **Key insight**: Safe mode identifies the side of the boundary; bisection identifies the component.

---

## 8. Failure Modes and Unsafe Shortcuts

| Shortcut | Why it misleads or causes harm | Safer alternative |
|----------|--------------------------------|-------------------|
| Delete `~/.claude` | Removes unrelated state and destroys evidence | Point `CLAUDE_CONFIG_DIR` at a temporary empty directory |
| Reinstall immediately | Can hide the original failure without proving its cause | Run `claude doctor`, record the version, then isolate configuration |
| Use `--dangerously-skip-permissions` | Changes the security boundary and invalidates a permissions diagnosis | Inspect `/permissions` and `/status`; reproduce in the normal mode |
| Disable every component permanently | Loses the known-good state and makes restoration error-prone | Record state and bisect reversibly |
| Share a raw debug log | May disclose secrets, tool output, paths, or server errors | Redact a copy and share only the minimum relevant lines |
| Edit several scopes together | Makes the causal change unknowable | Change one scope or component per test |
| Purge project state to fix config | Deletes transcripts, history, and diagnostics but does not repair bad config | Use `claude project purge <path> --dry-run` only when intentional state deletion is the actual goal |

Do not delete authentication data, transcripts, file history, plugin caches, or lock files as a first-line fix. Destructive cleanup is appropriate only after you know which state is corrupt, understand what will be lost, have preserved required evidence, and have a recovery path.

Escalate with a minimal reproduction that includes:

- `claude --version` output
- operating system and terminal or IDE surface
- sanitized `claude doctor` result
- whether `--safe-mode` reproduces the issue
- active scopes from `/status`
- failing component status from `/hooks`, `/mcp`, `/skills`, or `/permissions`
- the smallest relevant, sanitized debug excerpt

---

## 9. Official References

- [Debug your configuration](https://code.claude.com/docs/en/debug-your-config)
- [Troubleshooting](https://code.claude.com/docs/en/troubleshooting)
- [CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code commands](https://code.claude.com/docs/en/commands)
- [Skills](https://code.claude.com/docs/en/skills)
- [Subagents](https://code.claude.com/docs/en/sub-agents)
- [Hooks reference](https://code.claude.com/docs/en/hooks)
- [MCP](https://code.claude.com/docs/en/mcp)
- [Memory and rules](https://code.claude.com/docs/en/memory)
- [Permissions](https://code.claude.com/docs/en/permissions)
- [Plugins](https://code.claude.com/docs/en/discover-plugins)

---

**Back to**: [Root](../README.md)
