# CLAUDE.md — Rules & Memory

> **Who this is for**: Engineers configuring persistent Claude Code guidance for a project, monorepo, or personal workflow.

Before reading this, complete a safe first session: **[Getting Started](../basics/01_getting_started.md)**

---

## 1. What Is CLAUDE.md?

`CLAUDE.md` is a Markdown memory file Claude Code loads into the conversation as project guidance. Use it for stable facts Claude should know every session: build commands, project conventions, architecture boundaries, and team workflow rules.

> `CLAUDE.md` guides the model; it is not an enforcement mechanism. Use `settings.json`, permissions, and hooks for behavior the harness must enforce.

---

## 2. File Locations

Claude Code walks upward from the current working directory and loads relevant memory files additively.

| File | Scope | Committed? |
|------|-------|-----------|
| `~/.claude/CLAUDE.md` | All projects | No |
| `~/.claude/rules/**/*.md` | Personal rules, organized by topic | No |
| `./CLAUDE.md` | This project, all team members | Yes |
| `./CLAUDE.local.md` | This project, you only | No |
| `./.claude/rules/**/*.md` | This project, organized recursively by topic | Usually yes |
| `<subdir>/CLAUDE.md` | Loaded when work enters that subtree | Yes |

> **Case-sensitive**: Use `CLAUDE.md`. Do not rely on `claude.md`.

If your repository already has `AGENTS.md`, create a short `CLAUDE.md` that imports it:

```markdown
@AGENTS.md

## Claude Code
- Use plan mode for changes under `src/billing/`.
```

---

## 3. What to Include

Keep memory short, stable, and specific.

```markdown
# Build & Test
- Build: `npm run build`
- Unit tests: `npm run test:unit`
- Lint: `npm run lint`

# Code Style
- Use ES modules.
- Public async functions need explicit return types.
- Prefer existing helpers in `src/lib/` before adding utilities.

# Git
- Branch naming: `feat/`, `fix/`, `chore/`
- Conventional commits
- Never force-push to `main`

# Architecture
- DB access only through `src/repos/`
- No business logic in controllers
- Env vars go through `src/config.ts`, never `process.env` directly
```

Avoid:

- Facts Claude can discover quickly from code
- Long tutorials or copied documentation
- Frequently changing data
- Vague preferences such as "write clean code"
- Instructions that conflict with settings, hooks, or other memory files

---

## 4. Import Syntax

Use `@path` imports to keep CLAUDE.md focused:

```markdown
See @README.md for architecture overview.
See @package.json for scripts.
@docs/api-conventions.md
```

Paths are relative to the memory file. External imports may require approval the first time Claude Code encounters them.

---

## 5. `.claude/rules/` and Complete Frontmatter

Use `.claude/rules/` when one `CLAUDE.md` would become cluttered. Claude Code
discovers Markdown files recursively, so subfolders are valid:

```text
.claude/rules/
├── general.md
├── frontend/
│   └── react.md
└── backend/
    ├── api.md
    └── database.md
```

A rule with no YAML frontmatter is unconditional and loads with project memory:

```markdown
# Testing

- Run the narrowest relevant test before the full suite.
- Keep integration tests behind explicit external-service markers.
```

Claude Code documents exactly one public frontmatter field for rule files:

[Official path-specific rules reference](https://code.claude.com/docs/en/memory#path-specific-rules)

| Field | Type / default | Behavior |
|-------|----------------|----------|
| `paths` | YAML list of glob strings / unconditional | Loads the rule when Claude reads a file matching any listed pattern |

Use `paths` to point a rule at a folder, file type, or set of related paths:

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "src/workers/**/*.{ts,tsx}"
  - "tests/api/*.test.ts"
---

# API and Worker Rules

- Validate external input at the transport boundary.
- Keep retry policy in the worker, not the domain service.
- Add an integration test for every new API error response.
```

The patterns are ORed: one match activates the rule. Path matching happens when
Claude reads a file, not before every tool call.

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | TypeScript files at any depth |
| `src/**/*` | Every file under `src/` |
| `*.md` | Markdown files at the project root |
| `src/components/*.tsx` | Direct `.tsx` children of `src/components/` |
| `src/**/*.{ts,tsx}` | TypeScript and TSX files under `src/` |

Brace expansion is limited per rule file to 1,000 expanded patterns and 4 MiB
for the entire `paths` list. A brace expression that exceeds the budget is left
unexpanded and normally matches nothing. Invalid bracket expressions such as an
unclosed `[` also match nothing; escape a literal bracket as `\[`.

> **Rule**: `description`, `name`, `scope`, `globs`, `folders`, `include`,
> `exclude`, and `alwaysApply` are not supported Claude Code rule-frontmatter
> fields. Use `paths` for conditional loading and prose for the rule itself.

> **Key insight**: `paths` is the only frontmatter field Claude Code actually honors in a rule file, so frontmatter keys borrowed from other conventions (like `alwaysApply` or `globs`) silently do nothing instead of erroring.

Personal rules under `~/.claude/rules/` load before project rules, so project
guidance has higher priority. Symlinked rule files and directories are supported,
and circular links are ignored safely.

Rules in directories passed through `--add-dir` do not load merely because file
access was granted. Set `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` when
those additional directories should also contribute `CLAUDE.md` and
`.claude/rules/` guidance.

Unconditional rules can be re-injected after compaction. Path-scoped rules are
loaded again only after Claude reads another matching file.

---

## 6. CLAUDE.local.md

Use local memory for personal or machine-specific notes. Add it to `.gitignore`.

```markdown
# Local Dev Notes
- DB runs on localhost:5434 on this machine.
- Use `npm run dev:local`; my `.env` overrides defaults.
- Integration tests need Docker Desktop running.
```

Do not put secrets in any memory file. Use environment variables or local settings for secret references.

---

## 7. Monorepos

Place broad guidance at the root and package-specific guidance in package directories:

```
monorepo/
├── CLAUDE.md                 ← repo-wide conventions
├── packages/api/CLAUDE.md    ← API-specific rules
└── packages/web/CLAUDE.md    ← web-specific rules
```

Root CLAUDE.md should cover cross-package conventions only. Package files should cover commands, architecture, and caveats unique to that package.

---

**Next**: [Agents](../agents/01_subagents.md)
