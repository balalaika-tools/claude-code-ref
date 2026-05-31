# Skills Overview

Before reading this, understand commands: **[Custom Commands](../commands/01_custom_commands.md)**

---

## 1. What Is a Skill?

A skill is a directory containing `SKILL.md`: YAML frontmatter plus Markdown instructions that Claude can load when relevant or when you type `/skill-name`.

Use skills when a workflow has a repeatable procedure, needs supporting files, should be shareable as a plugin, or has grown too large for `CLAUDE.md`. Unlike CLAUDE.md, a skill's full body loads only when the skill is invoked.

| Scope | Path |
|-------|------|
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` |
| Project | `.claude/skills/<skill-name>/SKILL.md` |
| Plugin | `<plugin-root>/skills/<skill-name>/SKILL.md` |
| Enterprise | Managed settings |

When non-plugin skills share a command name, higher-priority scopes win. Plugin skills are namespaced as `/plugin-name:skill-name`.

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
description: Review a pull request for bugs, security issues, and missing tests. Use when asked to review a diff, branch, or PR.
---

Review the target in $ARGUMENTS.

Focus on correctness first:
- Logic errors and edge cases
- Security or data exposure risks
- Missing tests for changed behavior
- Maintainability issues that matter now

Return findings first, ordered by severity, with file and line references.
```

All frontmatter fields are optional, but `description` is the field Claude relies on most for automatic invocation. Put the trigger condition early.

---

## 3. Frontmatter Reference

| Field | Default | Description |
|-------|---------|-------------|
| `name` | Directory name | Display label. Usually does **not** change the `/skill-name` command |
| `description` | First paragraph | What the skill does and when to use it |
| `when_to_use` | — | Extra trigger guidance appended to the description |
| `argument-hint` | — | Hint shown in autocomplete, such as `[file-path]` |
| `arguments` | — | Named positional arguments for `$name` substitutions |
| `disable-model-invocation` | `false` | `true` means only the user can invoke it |
| `user-invocable` | `true` | `false` hides it from the `/` menu but lets Claude invoke it |
| `allowed-tools` | — | Tools pre-approved while the skill is active |
| `disallowed-tools` | — | Tools unavailable while the skill is active |
| `model` | Session | Model or alias override, such as `sonnet`, `opus`, or `inherit` |
| `effort` | Session | `low`, `medium`, `high`, `xhigh`, or `max` when supported |
| `context` | Inline | `fork` runs the skill in a subagent context |
| `agent` | Default agent | Subagent type to use with `context: fork` |
| `hooks` | — | Skill-scoped hooks |
| `paths` | — | Glob patterns that limit automatic activation |
| `shell` | `bash` | Shell for `!` dynamic context blocks |

`allowed-tools` grants approvals; it does not restrict all other tools. Use `disallowed-tools` or permission `deny` rules when you need restrictions.

---

## 4. String Substitutions

| Variable | Expands to |
|----------|------------|
| `$ARGUMENTS` | Everything after the skill name. If absent, Claude Code appends arguments at the end |
| `$ARGUMENTS[0]` / `$0` | First argument |
| `$ARGUMENTS[1]` / `$1` | Second argument |
| `$name` | Named argument declared in `arguments` |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_EFFORT}` | Current effort level |
| `${CLAUDE_SKILL_DIR}` | Absolute path to this skill directory |

`${CLAUDE_SKILL_DIR}` is the stable way to reference supporting files:

```markdown
Generate a service following the template at ${CLAUDE_SKILL_DIR}/templates/service.ts.
Module name: $0
```

---

## 5. Invocation

```
/skill-name [arguments]
/plugin-name:skill-name [arguments]
```

| Frontmatter | User can invoke | Claude can invoke | Skill listing in context |
|-------------|-----------------|-------------------|--------------------------|
| Default | Yes | Yes | Name + description |
| `disable-model-invocation: true` | Yes | No | Hidden from Claude |
| `user-invocable: false` | No | Yes | Name + description |

Full skill content is added only after invocation and remains in context for the rest of the session or until compaction drops it.

---

## 6. `allowed-tools` Patterns

```yaml
allowed-tools: Read, Grep, Glob
allowed-tools: Bash(git diff *), Bash(git status *)
allowed-tools:
  - Read
  - Edit(src/**/*.ts)
```

Review project skills before trusting a repository. A checked-in skill can pre-approve tool use after the workspace is trusted.

---

## 7. Example

```markdown
---
description: Generate a typed TypeScript API client from an OpenAPI spec. Use when given an OpenAPI or Swagger file.
argument-hint: <spec-file-path>
allowed-tools: Read, Write, Glob
model: opus
effort: high
---

Generate a typed TypeScript API client from the OpenAPI spec at $ARGUMENTS.

Requirements:
- Use `fetch`; do not add dependencies unless asked
- One function per endpoint, named from `operationId` where available
- Preserve request/response types without `any`
- Write one output file at `src/api/client.ts`
```

Use aliases like `sonnet`, `opus`, and `haiku` in reusable notes. Pin full model IDs only when a team needs deterministic rollout across environments.

---

**Next**: [Advanced Skills](02_skills_advanced.md)
