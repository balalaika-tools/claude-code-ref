# Advanced Skills

> **Who this is for**: Skill authors who know the basic `SKILL.md` format and need dynamic context, path scoping, hooks, or isolated execution.

Before reading this: **[Skills Overview](01_skills_overview.md)**

---

## 1. Supporting Files

A skill directory can contain files alongside `SKILL.md`. Keep `SKILL.md` short and let Claude read supporting files only when needed.

```
.claude/skills/db-migrate/
├── SKILL.md
├── checklist.md
└── templates/
    ├── up.sql.template
    └── down.sql.template
```

```markdown
Before writing a migration, read ${CLAUDE_SKILL_DIR}/checklist.md.
Use the SQL templates in ${CLAUDE_SKILL_DIR}/templates/.
```

Good supporting files:

- Checklists and rubrics
- Templates
- Example outputs
- Scripts Claude can run
- Long reference material that should not always load

---

## 2. Dynamic Context

Same syntax as command files: `` !`command` `` runs before the skill content is sent to Claude.

```markdown
Recent commits since the last tag:
!`git log $(git describe --tags --abbrev=0)..HEAD --oneline`

Current version:
!`git describe --tags --abbrev=0`
```

Multi-line blocks use `` ```! `` fences. Dynamic commands are recognized only
at the start of a line or after whitespace. Claude Code evaluates them once
before invocation; command output becomes plain prompt text and is not scanned
again for nested dynamic commands.

> **Security**: Never interpolate `$ARGUMENTS`, `$0`, or named arguments into dynamic shell commands. Use fixed commands and make user input visible to Claude as text instead.

Administrators can disable skill shell preprocessing with
`disableSkillShellExecution`. A skill that depends on dynamic commands should
state that requirement and fail clearly when the resulting context is absent.

---

## 3. Auto-Invocation Control

Claude sees skill names and descriptions, then loads full skill content only when a skill is invoked.

| Setting | Effect |
|---------|--------|
| Default | User and Claude can invoke |
| `disable-model-invocation: true` | Manual only; useful for side effects like deploys |
| `user-invocable: false` | Claude-only; useful for background knowledge |
| `skillOverrides` in settings | Hide, collapse, or disable skills without editing `SKILL.md` |

Write descriptions as trigger conditions:

```yaml
# Too vague
description: Helps with code.

# Better
description: Review database migrations for locking risk, rollback safety, index correctness, and data-loss hazards.
```

Descriptions and `when_to_use` text are truncated in the skill listing, so put the must-know trigger first.

---

## 4. Path Scoping

Restrict automatic activation to matching files:

```yaml
paths:
  - "src/**/*.tsx"
  - "src/**/*.ts"
```

A React skill should not activate while Claude is working only in a Python package. Path scoping limits automatic activation; the user can still invoke the skill manually unless `user-invocable: false`.

`paths` accepts a comma-separated string or YAML list. It uses the same glob
semantics as [path-specific rules](../rules/01_claude_md.md):

| Pattern | Scope |
|---------|-------|
| `src/**/*` | Everything under one folder |
| `**/*.tsx` | A file type at any depth |
| `src/**/*.{ts,tsx}` | Brace-expanded alternatives |
| `packages/*/src/**` | Matching folders in each direct package |

Keep patterns narrow enough to communicate intent. Brace expansion is limited
per `paths` list to 1,000 expanded patterns and 4 MiB.

---

## 5. Context Forking

`context: fork` runs the skill in a subagent context. This is useful when the workflow needs broad exploration but the main conversation should receive only the result.

```markdown
---
description: Perform a comprehensive security audit of authentication and authorization code.
context: fork
agent: general-purpose
background: false
model: opus
effort: max
---

Audit the requested area for:
- Hardcoded secrets
- Injection risks
- Missing auth or authorization checks
- Unsafe logging of sensitive data
- Dependency or configuration hazards

Return concrete findings with severity and file:line references.
```

Forked skills run in the background by default. Set `background: false` when the
invoking turn must wait for the completed result. Non-interactive sessions,
scheduled tasks, disabled background execution, and duplicate concurrent
invocations may still wait inline.

Use forks for audits, large codebase searches, or long research tasks. Keep
normal generation and small reviews inline so Claude retains working context.
Background forks receive a narrower tool set, and their edits are not included
in the main session's `/rewind` checkpoints.

---

## 6. Skill-Scoped Hooks

Skills can declare hooks in frontmatter. They use the same hook event model as `settings.json`, but `once: true` is honored only for hooks declared in skill frontmatter.

```yaml
hooks:
  Stop:
    - hooks:
        - type: command
          command: "npm test -- --runInBand"
          once: true
```

Use skill-scoped hooks for checks tightly coupled to a workflow. Use project settings hooks for team-wide policy or formatting.

---

## 7. Discovery and Reloading

Claude Code discovers skills from:

- Personal skills in `~/.claude/skills/`
- Project skills in `.claude/skills/` from the starting directory and parent directories
- Nested `.claude/skills/` directories when working in subdirectories
- `.claude/skills/` inside directories added with `/add-dir` or `--add-dir`
- Enabled plugins

Skill and command files in an already-discovered directory are watched and
normally reload automatically. Restart when you create a top-level skills
directory that the current session did not discover. When developing a plugin,
use `/reload-plugins` after changing non-skill plugin components.

---

**Back to**: [Skills Index](README.md)
