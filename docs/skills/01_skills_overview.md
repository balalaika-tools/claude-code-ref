# Skills Overview

> **Who this is for**: Claude Code users who know custom commands and want reusable workflows with richer discovery, scoping, and supporting files.

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

## 3. Complete Frontmatter Reference

These are all documented Claude Code behavior fields for `SKILL.md`:

[Official frontmatter reference](https://code.claude.com/docs/en/skills#frontmatter-reference)

| Field | Type / default | Behavior and constraints |
|-------|----------------|--------------------------|
| `name` | String / directory name | Display label. For personal and project skills, invocation still uses the directory or filename. For plugin skills, it replaces only the final command segment; the plugin namespace remains |
| `description` | String / first Markdown paragraph | Summary and automatic-invocation trigger. Put the most important trigger first |
| `when_to_use` | String / none | Additional automatic-invocation guidance appended to `description` |
| `argument-hint` | String / none | Autocomplete hint, such as `[file-path]` |
| `arguments` | Space-separated string or YAML list / none | Names positional arguments in order so `$name` substitutions work |
| `disable-model-invocation` | Boolean / `false` | `true` makes the skill manual-only and hides its description from Claude |
| `user-invocable` | Boolean / `true` | `false` hides the skill from the `/` menu but still lets Claude invoke it |
| `allowed-tools` | String or YAML list / none | Pre-approves matching tools for the invoking turn; does not remove unlisted tools |
| `disallowed-tools` | String or YAML list / none | Removes matching tools for the invoking turn |
| `model` | `/model` value or `inherit` / session model | Overrides the model for the rest of the invoking turn, then restores the session model |
| `effort` | `low`, `medium`, `high`, `xhigh`, or `max` / session effort | Overrides reasoning effort when the selected model supports it |
| `context` | `fork` / inline | `fork` runs the skill in a subagent instead of expanding it into the current conversation |
| `agent` | Built-in or custom agent name / `general-purpose` | Agent used with `context: fork`; built-ins include `Explore`, `Plan`, and `general-purpose` |
| `background` | Boolean / `true` for forked skills | With `context: fork`, `false` makes the invoking turn wait for the result |
| `hooks` | Mapping / none | Skill-scoped hooks in the normal hooks configuration shape |
| `paths` | Comma-separated string or YAML list of globs / all relevant paths | Limits automatic activation to matching files; manual invocation still works |
| `shell` | `bash` or `powershell` / `bash` | Shell used by `!` dynamic-context commands |

The combined `description` and `when_to_use` listing text is capped at 1,536
characters. Keep the trigger near the start so truncation does not remove it.

Boolean fields accept YAML booleans. Current Claude Code also accepts
`yes`/`no`, `on`/`off`, and `1`/`0`, but `true` and `false` are clearest in
shared files.

`allowed-tools` is a one-turn approval grant, not a complete tool allowlist.
`disallowed-tools` removes tools for that turn. Both clear when the user sends
the next message. Use project permission `deny` rules when a restriction must
persist independently of skill invocation.

> **Key insight**: `allowed-tools`/`disallowed-tools` only pre-approve or strip tools for the single turn that invokes the skill, so they cannot be used as a lasting security boundary — persistent restrictions belong in project permission `deny` rules instead.

> **Rule**: Keys such as `license`, `compatibility`, and `metadata` may exist in
> other Agent Skills ecosystems, but they are not documented Claude Code behavior
> fields. Do not rely on them to control Claude Code.

---

## 4. String Substitutions

| Variable | Expands to |
|----------|------------|
| `$ARGUMENTS` | Everything after the skill name. If absent, Claude Code appends arguments at the end |
| `$ARGUMENTS[N]` | Zero-based positional argument `N`, such as `$ARGUMENTS[0]` |
| `$N` | Short form of `$ARGUMENTS[N]`, such as `$0` or `$1` |
| `$name` | Named argument declared in `arguments` |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_EFFORT}` | Current effort level |
| `${CLAUDE_SKILL_DIR}` | Absolute path to this skill directory |
| `${CLAUDE_PROJECT_DIR}` | Absolute path to the current project root |

`${CLAUDE_SKILL_DIR}` is the stable way to reference supporting files. For a
plugin skill, it points to that skill's folder, not the plugin root.
`${CLAUDE_PROJECT_DIR}` is stable when a workflow must address a file from the
project root:

```markdown
Generate a service following the template at ${CLAUDE_SKILL_DIR}/templates/service.ts.
Write the result under ${CLAUDE_PROJECT_DIR}/src/services/.
Module name: $0
```

`${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` also expand inside
`Bash(...)` entries in `allowed-tools`. Argument, session, and effort
substitutions apply to skill content, not permission patterns.

Missing indexed arguments remain literal so Claude can see the unresolved
placeholder. Missing named arguments expand to an empty string. Arguments use
shell-style quoting; prefix a substitution with `\` when the dollar sign should
remain literal.

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

Full skill content is added only after invocation. After compaction, Claude Code
can re-inject invoked skill bodies up to 5,000 tokens per skill and 25,000 tokens
total; older skills are dropped first when that budget is exceeded.

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
