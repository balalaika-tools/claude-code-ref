# Subagents

> **Who this is for**: Claude Code users who understand skills and want specialized workers with isolated context and controlled tools.

Before reading this, understand skills: **[Skills Overview](../skills/01_skills_overview.md)**

---

## 1. What Is a Subagent?

A subagent is a specialized Claude Code instance with its own prompt, tools, model settings, and isolated context. Claude can delegate to a subagent, the subagent performs the work, and a summary returns to the main conversation.

```
Main conversation
  |
  | delegates "audit auth module"
  v
security-reviewer subagent
  -> reads files, searches patterns, runs approved tools
  -> returns findings
  (verbose tool output stays in the subagent context)
```

Use subagents for exploration, audits, large searches, or parallel work where the main thread should stay focused.

---

## 2. File Locations

| Scope | Path |
|-------|------|
| User | `~/.claude/agents/<agent-name>.md` |
| Project | `.claude/agents/<agent-name>.md` |
| Managed | Managed settings directory |
| Plugin | `<plugin-root>/agents/<agent-name>.md` |

Managed agents take precedence over project and user agents; project agents take precedence over user agents. Plugin agents are referenced with plugin namespaces when needed.

---

## 3. Format

Markdown with YAML frontmatter plus a system prompt:

```markdown
---
name: security-reviewer
description: Review code for security vulnerabilities, including injection, auth flaws, unsafe logging, and secrets.
tools: Read, Grep, Glob
model: opus
effort: high
---

You are a senior application security engineer.

For each finding, include:
- File path and line number
- Severity: Critical / High / Medium / Low
- Why it matters
- A concrete fix

Report only issues grounded in the code you inspected.
```

Common fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique lowercase/hyphen identifier; the filename does not have to match |
| `description` | Yes | Claude uses this to decide when to delegate |
| `tools` | No | Allowed tool list. Omit to inherit the default tool set |
| `disallowedTools` | No | Tools unavailable to this subagent |
| `model` | No | Model or alias override |
| `effort` | No | Reasoning effort when supported |
| `permissionMode` | No | Permission mode for the subagent |
| `maxTurns` | No | Turn limit for the subagent |
| `skills` | No | Skills to preload for this subagent |
| `mcpServers` | No | MCP servers made available |
| `hooks` | No | Agent-scoped hooks |
| `background` | No | `true` always runs the agent in the background; when omitted, Claude chooses |

Keep the prompt operational: role, boundaries, output format, and what not to do.

---

## 4. Writing Good Descriptions

The description is the routing contract:

```yaml
# Too vague
description: Helps with code review

# Better
description: Use for security-focused code review, auth/authorization audits, secret detection, and unsafe data handling checks.
```

Good descriptions say:

- Which tasks belong to the subagent
- Which tasks do not
- What artifact the subagent should return

> **Key insight**: Claude chooses which subagent to delegate to by matching the task against the `description` field alone, not the system prompt body — so a vague description makes a well-written subagent invisible to the router.

---

## 5. Subagents vs. Skills

| | Subagents | Skills |
|--|-----------|--------|
| Primary purpose | Specialized worker persona | Reusable workflow or reference |
| Context | Isolated | Main context, unless `context: fork` |
| File | `.claude/agents/<name>.md` | `.claude/skills/<name>/SKILL.md` |
| Supporting files | No dedicated skill directory | Yes |
| Invocation | Claude delegates, user can `@agent-name` | User or Claude invokes with `/skill-name` |
| Best for | Research, audits, parallel work | Procedures, templates, repeated tasks |

Skills with `context: fork` bridge the two: a repeatable workflow that runs in subagent isolation.

---

## 6. Creating and Reloading Agents

Ask Claude to create the file, or edit `.claude/agents/<name>.md` directly:

```text
Create a project subagent named security-reviewer with read-only tools.
Save it to .claude/agents/security-reviewer.md and show me the result.
```

`/agents` no longer opens an interactive creation wizard; it directs you to these
creation methods. Claude Code watches existing agent files and normally reloads edits
within seconds. Restart only when you create an `agents/` directory for the first time
and the current session has not discovered it.

Subagents run in the background by default. Set `background: false` only when the caller
must wait inline for the complete result before continuing.

You can also mention an agent explicitly:

```text
@agent-security-reviewer review the auth changes
```

Or start a whole session with an agent prompt:

```bash
claude --agent security-reviewer
```

---

## 7. Example

```markdown
---
name: test-writer
description: Write or improve unit and integration tests for a specific file, module, or bug fix.
tools: Read, Grep, Glob, Write, Edit, Bash(npm test *)
model: sonnet
effort: medium
---

You are a test engineer.

When given a source file or module:
- Identify public behavior before writing tests
- Cover happy paths, boundary values, and error cases
- Mock at external I/O boundaries, not internal helpers
- Mirror the source path under the project's existing test layout
- Run the narrowest relevant test command when possible

Avoid tests that assert private implementation details.
```

---

**Next**: [Hooks](../hooks/01_hooks_overview.md)
