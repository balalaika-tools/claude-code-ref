# Custom Commands

> **Who this is for**: Claude Code users who understand project guidance and want quick, repeatable slash-command workflows.

Before reading this, understand CLAUDE.md: **[Rules](../rules/01_claude_md.md)**

---

## 1. What Are Custom Commands?

Custom commands are Markdown prompts you can invoke with `/name`.

Modern Claude Code treats custom commands as **flat skills**: existing files in `.claude/commands/` still work, but new reusable workflows should usually go in `.claude/skills/<name>/SKILL.md` because skills support supporting files, richer invocation control, and plugin distribution.

| Scope | Path |
|-------|------|
| Project | `.claude/commands/<name>.md` |
| Personal | `~/.claude/commands/<name>.md` |

The command name comes from the filename: `.claude/commands/deploy.md` -> `/deploy`.

> Subdirectories are for organization, not invocation namespaces. `.claude/commands/db/migrate.md` is still invoked by its filename, not as `/db:migrate`. Use skills or plugin skills when you need clear namespacing.

---

## 2. Format

The file content is the prompt Claude receives. Add YAML frontmatter for autocomplete, tool permissions, argument hints, or model behavior:

```markdown
---
description: Review staged changes for bugs and regressions
argument-hint: [base-branch]
allowed-tools: Read, Grep, Glob, Bash(git diff *), Bash(git status *)
---

Review the diff against $0. Flag correctness, security, and test coverage risks.
If no base branch is provided, use `main`.
```

Common frontmatter:

| Field | Description |
|-------|-------------|
| `description` | Shown in autocomplete and used by Claude to understand the command |
| `argument-hint` | Hint shown while typing the command |
| `arguments` | Named positional arguments for `$name` substitutions |
| `allowed-tools` | Tools pre-approved while the command/skill is active |
| `model` | Optional model or alias override, such as `sonnet` or `opus` |

Because command files are skill-compatible, prefer the [Skills Overview](../skills/01_skills_overview.md) frontmatter reference when in doubt.

---

## 3. Arguments

Everything after the command name is available as `$ARGUMENTS`:

```
/explain the difference between JWT and sessions
         └──────────────────────────────────────┘
                      $ARGUMENTS
```

Use indexed arguments for structured prompts:

| Placeholder | Expands to |
|-------------|------------|
| `$ARGUMENTS` | The full raw argument string |
| `$ARGUMENTS[0]` or `$0` | First argument |
| `$ARGUMENTS[1]` or `$1` | Second argument |
| `$name` | Named argument declared in `arguments` frontmatter |

Quote multi-word arguments when you need them to stay together: `/migrate "Search Bar" React Vue`.

---

## 4. Dynamic Content

### Shell Injection

`` !`command` `` runs before Claude sees the command content and replaces the expression with command output:

```markdown
Recent commits:
!`git log --oneline -10`

Summarize what changed.
```

Multi-line:

````markdown
```!
git status
git diff --stat HEAD~1
```
````

You must grant the needed Bash permissions with `allowed-tools`.

> **Security**: Never place `$ARGUMENTS`, `$0`, or other user-controlled text inside dynamic shell commands. Use fixed shell commands, then pass user input only as Claude-visible prompt text.

### File References

`@path/to/file` attaches file contents:

```markdown
Review against our checklist: @docs/security-checklist.md
```

---

## 5. Example

```markdown
---
description: Generate a PR description from the current branch
allowed-tools: Bash(git rev-parse *), Bash(git log *), Bash(git diff *), Read
---

Generate a pull request description.

Base branch: main
Current branch: !`git rev-parse --abbrev-ref HEAD`
Commits: !`git log main..HEAD --oneline`
Diff: !`git diff main..HEAD --stat`

Format:
- Summary: 2-4 bullets
- Test plan: checklist
- Notes: migrations, env vars, rollout risks

Output only the PR description.
```

---

## 6. Commands vs. Skills

| | Command files | Skill directories |
|--|---------------|-------------------|
| File | `.claude/commands/*.md` | `.claude/skills/<name>/SKILL.md` |
| Best for | Short prompts and legacy shortcuts | Reusable workflows and shared procedures |
| Supporting files | No dedicated directory | Yes |
| Invocation | `/name` | `/name` or `/plugin:name` |
| Plugin distribution | Use plugin `commands/`, but prefer plugin `skills/` | Yes |

If a command and a skill have the same name, the skill takes precedence. Files
inside an already-discovered command or skill directory are watched and normally
reload automatically. Restart after creating a new top-level directory that the
current session did not discover.

---

**Next**: [Skills](../skills/01_skills_overview.md)
