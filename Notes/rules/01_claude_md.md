# CLAUDE.md — Rules & Memory

---

## 1. What Is CLAUDE.md?

A Markdown file Claude reads at the start of every session. Persistent memory for project conventions, build commands, and workflow rules.

> CLAUDE.md is read by Claude (the model). For behavioral configuration (permissions, hooks), use `settings.json`.

---

## 2. File Locations

| File | Scope | Committed? |
|------|-------|-----------|
| `~/.claude/CLAUDE.md` | All projects | No |
| `./CLAUDE.md` | This project, all team members | Yes |
| `./CLAUDE.local.md` | This project, you only | No (gitignore it) |
| `./.claude/rules/*.md` | This project, organized by topic | Yes |
| `<subdir>/CLAUDE.md` | Loaded when working in that subdir | Yes |

> **Case-sensitive**: Must be `CLAUDE.md` (uppercase). `claude.md` won't be loaded.

All files are loaded additively — there's no override between them. Conflicting instructions in different files cause unpredictable behavior.

---

## 3. What to Include

Claude follows ~150-200 instructions consistently. Keep it focused.

```markdown
# Build & Test
- Build: `npm run build`
- Test: `npm run test:unit`
- Lint: `npm run lint`

# Code Style
- ES modules (import/export), not CommonJS
- Destructure params when >2 arguments
- All async functions need explicit return types

# Git
- Branch naming: feat/, fix/, chore/
- Conventional commits format
- Never force-push to main

# Architecture
- DB access only through repos in src/repos/
- No business logic in controllers
- All env vars via src/config.ts, never process.env directly
```

**Don't include**: things Claude can see by reading code (language version, entry points), standard conventions (camelCase in TS), long tutorials, frequently changing data.

---

## 4. Import Syntax

Reference other files to keep CLAUDE.md short:

```markdown
See @README.md for architecture overview.
See @package.json for scripts.
@docs/api-conventions.md
```

Paths are relative to the CLAUDE.md file.

---

## 5. `.claude/rules/` Directory

Organize rules into topic files. Claude loads all `*.md` files here automatically:

```
.claude/rules/
├── testing.md
├── database.md
└── api.md
```

---

## 6. CLAUDE.local.md

Personal notes that don't belong in the shared CLAUDE.md. Add to `.gitignore`:

```markdown
# Local Dev Notes
- DB is at localhost:5434 (non-standard port)
- Use `npm run dev:local` — my .env overrides
- Integration tests are flaky locally; run in CI
```

---

## 7. Monorepos

Place `CLAUDE.md` in subdirectories. Claude loads them when working in that directory:

```
monorepo/
├── CLAUDE.md                 ← always loaded
├── packages/api/CLAUDE.md    ← loaded in packages/api/
└── packages/web/CLAUDE.md    ← loaded in packages/web/
```

Root CLAUDE.md: cross-package conventions only. Package-specific rules in the package's own file.

---

**Next**: [Agents](../agents/01_subagents.md)
