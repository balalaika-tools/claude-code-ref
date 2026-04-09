# Advanced Skills

Before reading this: **[Skills Overview](01_skills_overview.md)**

---

## 1. Supporting Files

A skill directory can contain files alongside `SKILL.md`. Reference them with `${CLAUDE_SKILL_DIR}`:

```
.claude/skills/db-migrate/
├── SKILL.md
├── checklist.md
└── templates/
    ├── up.sql.template
    └── down.sql.template
```

```markdown
Pre-flight checklist: read ${CLAUDE_SKILL_DIR}/checklist.md
Use templates at ${CLAUDE_SKILL_DIR}/templates/
```

---

## 2. Shell Command Injection

Same syntax as commands — `` !`command` `` executes at invocation time:

```markdown
Recent commits since last tag:
!`git log $(git describe --tags --abbrev=0)..HEAD --oneline`

Current version: !`git describe --tags --abbrev=0`
```

Multi-line with `` ```! `` blocks.

---

## 3. Auto-Invocation Control

Claude reads all skill descriptions at session start. When a task matches, it auto-loads the skill.

| `disable-model-invocation` | `user-invocable` | You invoke | Claude auto-invokes |
|---------------------------|-----------------|------------|---------------------|
| `false` (default) | `true` (default) | Yes | Yes |
| `true` | `true` | Yes | **No** |
| `false` | `false` | **No** | Yes |
| `true` | `false` | **No** | **No** |

Write descriptions as clear trigger conditions:

```markdown
# Bad — too vague
description: Helps with code

# Good — specific trigger
description: Use when writing or reviewing database migrations to ensure
safety, rollback coverage, and index correctness.
```

---

## 4. Path Scoping

Restrict activation to matching files:

```yaml
paths: "src/**/*.tsx,src/**/*.ts"
```

A React skill won't load during Python work in the same monorepo.

---

## 5. Context Forking

`context: fork` runs the skill in an isolated subagent. Tool calls stay out of the main context window:

```markdown
---
name: deep-audit
description: Comprehensive security audit of the codebase.
context: fork
agent: general-purpose
model: claude-opus-4-6
effort: max
---

Perform a full security audit. Check for hardcoded secrets, injection risks,
missing auth checks, and dependency vulnerabilities.
Return a structured report with severity levels and file:line references.
```

Use for long-running exploration (audits, large refactors) where hundreds of tool calls would clutter the main conversation.

---

## 6. Skill-Scoped Hooks

Skills can declare lifecycle hooks in frontmatter:

```yaml
hooks:
  Stop:
    - type: command
      command: "npx jest --testPathPattern=$ARGUMENTS --no-coverage"
      once: true
```

`once: true` means the hook fires only once per skill invocation.

---

## 7. Monorepo Discovery

Claude auto-discovers skills in subdirectory `.claude/skills/` directories. Package-specific skills only load when working in that package:

```
monorepo/
├── .claude/skills/          ← always loaded
├── packages/api/.claude/skills/   ← loaded in packages/api/
└── packages/web/.claude/skills/   ← loaded in packages/web/
```

---

**Back to**: [Skills Index](README.md)
