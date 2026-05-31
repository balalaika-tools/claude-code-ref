# CLAUDE.md — Rules & Memory

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
| `./CLAUDE.md` | This project, all team members | Yes |
| `./CLAUDE.local.md` | This project, you only | No |
| `./.claude/rules/*.md` | This project, organized by topic | Usually yes |
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

## 5. `.claude/rules/`

Use `.claude/rules/` when one CLAUDE.md would become cluttered:

```
.claude/rules/
├── testing.md
├── database.md
└── api.md
```

Rules can be broad or path-specific. Path-specific rules should state their trigger clearly and avoid duplicating root guidance.

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
