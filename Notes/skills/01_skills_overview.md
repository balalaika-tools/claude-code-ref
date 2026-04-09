# Skills Overview

Before reading this, understand commands: **[Custom Commands](../commands/01_custom_commands.md)**

---

## 1. What Is a Skill?

A skill is a named prompt stored in a directory with a `SKILL.md` file. Unlike single-file commands, skills can include supporting files and support auto-invocation, model control, and plugin distribution.

| Scope | Path |
|-------|------|
| Project | `.claude/skills/<skill-name>/SKILL.md` |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` |
| Plugin | `<plugin-root>/skills/<skill-name>/SKILL.md` |

```
.claude/skills/
├── pr-review/
│   ├── SKILL.md              ← /pr-review
│   └── review-checklist.md   ← supporting file
└── scaffold/
    ├── SKILL.md              ← /scaffold
    └── templates/
        └── service.ts
```

---

## 2. Minimal `SKILL.md`

```markdown
---
name: pr-review
description: Review a pull request for bugs, style, and test coverage.
---

Review the following PR or file: $ARGUMENTS

Check for: logic errors, missing tests, security issues, style consistency.
Return a bulleted list ordered by severity with line references.
```

---

## 3. Frontmatter Reference

| Field | Default | Description |
|-------|---------|-------------|
| `name` | dir name | Lowercase, hyphens only, max 64 chars |
| `description` | — | Used for autocomplete AND auto-invocation decisions |
| `argument-hint` | — | Shown in autocomplete (e.g., `[file-path]`) |
| `disable-model-invocation` | `false` | `true` = manual only, Claude won't auto-load |
| `user-invocable` | `true` | `false` = hidden from `/` menu, background knowledge only |
| `allowed-tools` | — | Pre-approved tools: `Read, Grep, Bash(git *)` |
| `model` | session | Model override |
| `effort` | session | `low`, `medium`, `high`, `max` |
| `context` | — | `fork` = run in isolated subagent context |
| `agent` | — | Subagent type (requires `context: fork`) |
| `paths` | — | Glob patterns; skill only activates for matching files |
| `shell` | `bash` | `bash` or `powershell` |

---

## 4. String Substitutions

| Variable | Expands to |
|----------|-----------|
| `$ARGUMENTS` | Everything after the skill name |
| `$1`, `$2`, `$3` | Positional arguments (whitespace-delimited) |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Absolute path to the skill directory |

`${CLAUDE_SKILL_DIR}` is useful for referencing supporting files:

```markdown
Generate a service following the template at ${CLAUDE_SKILL_DIR}/templates/service.ts.
Module name: $1
```

---

## 5. Invocation

```
/skill-name [arguments]
/plugin-name:skill-name [arguments]
```

| Mode | Trigger | Controlled by |
|------|---------|--------------|
| Manual | You type `/skill-name` | Always, unless `user-invocable: false` |
| Auto | Claude loads when relevant | `description` field; blocked by `disable-model-invocation: true` |
| Background | Silently loaded as knowledge | `user-invocable: false` |

---

## 6. `allowed-tools` Patterns

```yaml
allowed-tools: Read, Grep, Glob           # multiple tools
allowed-tools: Bash(git *)                 # git commands only
allowed-tools: Edit(src/**/*.ts)           # edits under src/, TS only
```

---

## 7. Example

```markdown
---
name: gen-api-client
description: Generate a typed TypeScript API client from an OpenAPI spec file.
argument-hint: "<spec-file-path>"
allowed-tools: Read, Write, Glob
model: claude-opus-4-6
effort: high
---

Generate a fully typed TypeScript API client from the OpenAPI spec at: $ARGUMENTS

Requirements:
- Use fetch (no external deps)
- One function per endpoint, named after operationId
- All types inferred from spec (no `any`)
- Single output file: `src/api/client.ts`
```

---

**Next**: [Advanced Skills](02_skills_advanced.md)
