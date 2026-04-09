# Subagents

Before reading this, understand skills: **[Skills Overview](../skills/01_skills_overview.md)**

---

## 1. What Is a Subagent?

A specialized Claude instance with its own system prompt, tool restrictions, and **isolated conversation history**. When Claude decides a task matches a subagent's description, it delegates. The subagent works in isolation and returns a summary — its tool calls don't consume main context.

```
Main conversation
  │
  │ delegates "security audit of auth module"
  ▼
security-reviewer subagent (isolated)
  → reads 50 files, greps patterns, produces findings
  → returns summary to main conversation
  (50 Read calls stay invisible to main context)
```

---

## 2. File Locations

| Scope | Path |
|-------|------|
| Project | `.claude/agents/<agent-name>.md` |
| Personal | `~/.claude/agents/<agent-name>.md` |

Filename = agent name.

---

## 3. Format

Markdown with YAML frontmatter + system prompt:

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities including injection, auth flaws, and secrets.
tools: Read, Grep, Glob
model: claude-opus-4-6
---

You are a senior application security engineer. For each finding provide:
- File path and line number
- Severity: Critical / High / Medium / Low
- Description and suggested fix

Be specific. Reference actual code. Don't report theoretical issues.
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Must match filename |
| `description` | Yes | Claude uses this to decide when to delegate — be specific |
| `tools` | No | Comma-separated tool list. Omit = all tools. |
| `model` | No | Model override |

---

## 4. Writing Good Descriptions

The description determines when Claude delegates:

```markdown
# Too vague — Claude won't know when to use it
description: Helps with code review

# Good — clear trigger condition
description: Use when reviewing code for security vulnerabilities,
auditing auth/authorization, or checking for secrets in source.
```

---

## 5. Subagents vs. Skills

| | Subagents | Skills |
|--|-----------|--------|
| Context | Isolated | Main conversation (unless `context: fork`) |
| File | `.claude/agents/<name>.md` | `.claude/skills/<name>/SKILL.md` |
| Supporting files | No | Yes |
| Invocation | Claude delegates automatically | User or Claude invokes |
| Good for | Long exploration, audits | Repeatable workflows, code gen |

Skills with `context: fork` bridge the gap — skill workflow with subagent isolation.

---

## 6. Interactive Setup

```
/agents
```

Walks through name, description, tools, model, and system prompt. Writes the file to `.claude/agents/`.

---

## 7. Example

```markdown
---
name: test-writer
description: Write unit and integration tests for a given file or module.
tools: Read, Grep, Glob, Write
model: claude-sonnet-4-6
---

You are a test engineer. When given a source file, produce tests covering:
- Happy path for all exports
- Edge cases: empty input, null, boundary values
- Error cases: what throws vs returns errors
- Mock at boundaries (external I/O), not internally

Location: mirror source path under `__tests__/`.
Aim for >80% branch coverage without testing implementation details.
```

---

**Next**: [Hooks](../hooks/01_hooks_overview.md)
