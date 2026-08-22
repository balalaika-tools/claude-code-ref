# The `.claude/` Directory

> **Who this is for**: Project maintainers deciding which Claude Code configuration belongs in version control and which must remain local.

Before reading this, understand the difference between model guidance and harness config: **[settings.json](01_settings_json.md)**.

---

## 1. What `.claude/` Is For

`.claude/` is the project-local home for Claude Code configuration and extensions. Use it for files that should travel with a repository: shared settings, rules, skills, agents, commands, and hook scripts.

There are two common `.claude/` locations:

| Location | Scope | Usually committed? |
|----------|-------|--------------------|
| `.claude/` | Current project | Partly |
| `~/.claude/` | Your user account | No |

Project `.claude/` teaches Claude Code how to work in this repo. User `~/.claude/` holds your personal defaults, private skills, installed plugin cache, and local state.

---

## 2. Typical Project Layout

```text
.claude/
├── settings.json              # shared harness config
├── settings.local.json        # personal project overrides; gitignore
├── rules/
│   ├── testing.md             # extra project guidance
│   └── database.md
├── commands/
│   └── pr-description.md      # flat skill-compatible slash command
├── skills/
│   └── migration-review/
│       ├── SKILL.md
│       └── checklist.md
├── agents/
│   └── security-reviewer.md
└── hooks/
    ├── block-rm.sh
    └── format-edited-file.sh
```

Only some paths are loaded automatically. A script in `.claude/hooks/` does nothing until a hook in `settings.json`, a plugin, a skill, or an agent references it.

---

## 3. What Each File Controls

| Path | Purpose | Commit? |
|------|---------|---------|
| `.claude/settings.json` | Shared permissions, hooks, env defaults, MCP approval, model defaults | Yes |
| `.claude/settings.local.json` | Your local overrides | No |
| `.claude/rules/*.md` | Topic-specific project guidance loaded as memory | Usually yes |
| `.claude/commands/*.md` | Quick slash commands | Usually yes |
| `.claude/skills/<name>/SKILL.md` | Reusable workflows, optionally with supporting files | Usually yes |
| `.claude/agents/*.md` | Custom subagents | Usually yes |
| `.claude/hooks/*` | Scripts called by hook config | Usually yes, if referenced by shared hooks |

Keep `.claude/` small and intentional. If a file is just documentation for humans, put it in `docs/` and import/reference it from CLAUDE.md or a skill only when useful.

---

## 4. What Does Not Belong There

Some Claude Code config lives outside `.claude/`:

| Path | Why |
|------|-----|
| `CLAUDE.md` | Project memory can live at the root; `.claude/CLAUDE.md` is also valid |
| `CLAUDE.local.md` | Personal project memory, gitignored |
| `.mcp.json` | Project MCP server definitions live at the project root |
| `~/.claude/settings.json` | User-wide settings |
| `~/.claude/skills/` | Personal skills |
| `~/.claude/agents/` | Personal agents |
| `~/.claude/commands/` | Personal command files |

Do not put secrets in any committed file. Use environment variables, local settings, GitHub secrets, or a secrets manager.

---

## 5. Hierarchy and Precedence Scoring

There is no single numeric "score" shown in the UI. Think in three different ranking systems:

| System | Strongest signal | How conflicts are resolved |
|--------|------------------|----------------------------|
| Settings | Managed -> CLI -> local project -> shared project -> user | Higher scope wins for scalars; arrays usually merge |
| Permissions | Any matching `deny` | A deny blocks even when another layer allows |
| Memory/guidance | More specific and later-loaded instructions | Additive context, not hard enforcement |
| Skills/commands | Explicit user invocation | Auto-selection depends on description, path scope, and task relevance |
| Agents | Explicit `@agent` mention or clear description match | Project/managed definitions outrank user definitions on name conflicts |

Settings precedence, highest to lowest:

```text
Managed settings
CLI flags
.claude/settings.local.json
.claude/settings.json
~/.claude/settings.json
```

Memory/guidance load order is additive. Broader instructions load first; more local instructions appear later in context and tend to carry more weight when there is a conflict:

```text
Managed CLAUDE.md / managed claudeMd
~/.claude/CLAUDE.md
~/.claude/rules/*.md
project CLAUDE.md or .claude/CLAUDE.md
.claude/rules/*.md without path filters
directory CLAUDE.md files from repo root down to cwd
CLAUDE.local.md next to each loaded CLAUDE.md
path-scoped rules and subdirectory CLAUDE.md files when matching files are opened
```

Important caveats:

- `CLAUDE.md` guidance is context, not enforcement. Use settings and hooks when the rule must be guaranteed.
- More specific/later memory usually wins in a conflict, but contradictory guidance still reduces reliability.
- Permission arrays merge across scopes, so lower-priority scopes can still add entries; `deny` remains the safest way to block.
- Skill auto-selection is relevance-based. Put the trigger words early in `description`/`when_to_use`; path-scope specialized skills; use `/doctor` if skill descriptions are being shortened by the listing budget.
- Use `/status` to confirm which settings sources loaded for the current session.

> **Key insight**: There is no single global precedence order in Claude Code — settings, permissions, memory, and skill/agent selection each resolve conflicts by a different rule (scope rank, deny-wins, recency/specificity, and relevance respectively), so "what wins" depends on which system you're asking about.

---

## 6. How To Configure It

Start with a small shared config:

```json
{
  "permissions": {
    "allow": ["Read", "Grep", "Glob", "Bash(git diff *)"],
    "ask": ["Write", "Edit"],
    "deny": ["Bash(sudo *)", "Read(./.env)", "Read(./secrets/**)"]
  },
  "enableAllProjectMcpServers": false,
  "enabledMcpjsonServers": []
}
```

Then add only what the repo needs:

1. Put durable project guidance in `CLAUDE.md` or `.claude/rules/*.md`.
2. Put quick shortcuts in `.claude/commands/*.md`.
3. Put repeatable workflows in `.claude/skills/<name>/SKILL.md`.
4. Put specialized isolated workers in `.claude/agents/*.md`.
5. Put deterministic enforcement in hooks configured from `settings.json`.
6. Put external tool/server definitions in root `.mcp.json`, then approve them from settings.

Ask Claude to create an agent or edit `.claude/agents/<name>.md` directly; existing agent
files are watched and normally reload within seconds. Skill and command files in
already-discovered directories are watched as well; restart after creating a new
top-level directory. Use `/reload-plugins` after changing non-skill plugin components.

---

## 7. Git Hygiene

Commit:

- `.claude/settings.json` when it contains team-safe config
- `.claude/rules/*.md`
- `.claude/commands/*.md`
- `.claude/skills/**`
- `.claude/agents/*.md`
- Hook scripts referenced by shared settings

Do not commit:

- `.claude/settings.local.json`
- Machine-specific paths
- Secrets, tokens, or real credentials
- Generated caches, logs, transcripts, or plugin cache directories

Suggested `.gitignore`:

```gitignore
.claude/settings.local.json
CLAUDE.local.md
```

---

## 8. Review Checklist

Before trusting or merging `.claude/` changes:

- Check permission changes for broad `Bash(*)`, `Write(*)`, or `bypassPermissions`.
- Review hook commands as executable code.
- Review skills and commands for dynamic shell blocks.
- Check MCP server approvals against `.mcp.json`.
- Confirm local-only settings and memory are gitignored.
- Prefer model aliases in shared config unless exact model pinning is intentional.

---

**Back to**: [Settings Index](index.md)
