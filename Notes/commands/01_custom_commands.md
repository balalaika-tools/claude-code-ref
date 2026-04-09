# Custom Commands

Before reading this, understand CLAUDE.md: **[Rules](../rules/01_claude_md.md)**

---

## 1. What Are Custom Commands?

Markdown files that become slash commands. Drop `deploy.md` in `.claude/commands/` and `/deploy` is available.

| Scope | Path |
|-------|------|
| Project | `.claude/commands/<name>.md` |
| Personal | `~/.claude/commands/<name>.md` |

Filename = command name. Subdirectories create namespaces: `commands/db/migrate.md` → `/db:migrate`.

---

## 2. Format

The file content is the prompt Claude receives. Add optional YAML frontmatter:

```markdown
---
description: Review staged changes for bugs and regressions
allowed-tools: Read, Grep, Glob, Bash(git *)
---

Review the git diff for the current branch. Flag anything risky.
```

| Field | Description |
|-------|-------------|
| `description` | Shown in autocomplete |
| `allowed-tools` | Tools pre-approved for this command. Supports patterns: `Bash(git *)` |

---

## 3. `$ARGUMENTS`

Everything after the command name:

```
/explain the difference between JWT and sessions
         └──────────────────────────────────────┘
                      $ARGUMENTS
```

Positional access: `$1`, `$2`, `$3` for whitespace-delimited arguments.

---

## 4. Dynamic Content

### Shell injection

`` !`command` `` executes at invocation time, output replaces the block:

```markdown
Recent commits:
!`git log --oneline -10`

Summarize what was worked on.
```

Multi-line:

````markdown
```!
git status
git diff --stat HEAD~1
```
````

### File references

`@path/to/file` inlines file contents (relative to project root):

```markdown
Review against our checklist: @docs/security-checklist.md
```

---

## 5. Example

```markdown
---
description: Generate a PR description from current branch
allowed-tools: Bash(git *), Read
---

Generate a pull request description.

Branch: !`git rev-parse --abbrev-ref HEAD`
Commits: !`git log main..HEAD --oneline`
Diff: !`git diff main..HEAD --stat`

Format: Summary (2-4 bullets), Test plan (checklist), Notes (migrations/env).
Output only the PR description.
```

---

## 6. Commands vs. Skills

| | Commands | Skills |
|--|----------|--------|
| File | `.claude/commands/*.md` | `.claude/skills/<name>/SKILL.md` |
| Supporting files | No | Yes |
| Frontmatter | `description`, `allowed-tools` | Full set (model, effort, context, hooks, paths, ...) |
| Auto-invocation | No | Yes |
| Plugin distribution | No | Yes |

Prefer commands for quick shortcuts. Use skills when you need auto-invocation, supporting files, or plugin distribution.

---

**Next**: [Skills](../skills/01_skills_overview.md)
