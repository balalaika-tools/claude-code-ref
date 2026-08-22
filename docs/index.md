# Claude Code Notes

> A practical reference for engineers using Claude Code — from safe first sessions through customization, automation, integrations, plugins, and troubleshooting.

[![Claude Code](https://img.shields.io/badge/Claude_Code-CLI-191919.svg?logo=anthropic&logoColor=white)](https://code.claude.com/docs)
[![Anthropic](https://img.shields.io/badge/Anthropic-API-FF6B35.svg?logoColor=white)](https://anthropic.com)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF.svg?logo=githubactions&logoColor=white)](github/index.md)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-Spec-000000.svg?logoColor=white)](https://modelcontextprotocol.io)
[![Markdown](https://img.shields.io/badge/Markdown-Notes-000000.svg?logo=markdown&logoColor=white)](index.md)

---

## Structure

```
claude-code/
│
│ ── FUNDAMENTALS ────────────────────────────────────────────
├── basics/
│   ├── 01_getting_started.md       Install, authenticate, trust, and run a safe first task
│   └── 02_sessions_and_cli.md      Sessions, modes, models, permissions, output, budgets
│
│ ── CUSTOMIZATION ───────────────────────────────────────────
├── commands/
│   └── 01_custom_commands.md       Flat skill-compatible slash commands
│
├── skills/
│   ├── 01_skills_overview.md       SKILL.md format, frontmatter, invocation
│   └── 02_skills_advanced.md       Supporting files, dynamic context, auto-invoke, forking
│
├── rules/
│   └── 01_claude_md.md             CLAUDE.md hierarchy, imports, rule paths and glob scoping
│
│ ── AUTOMATION ──────────────────────────────────────────────
├── hooks/
│   ├── 01_hooks_overview.md        Lifecycle events, config structure, common patterns
│   └── 02_hook_handlers.md         command/http/mcp_tool/prompt/agent handlers, blocking
│
│ ── AGENTS ──────────────────────────────────────────────────
├── agents/
│   └── 01_subagents.md             .claude/agents/, frontmatter, delegation, vs skills
│
│ ── INTEGRATIONS ────────────────────────────────────────────
├── github/
│   ├── 01_github_app.md            App install, @claude mentions, what it can do
│   ├── 02_github_actions.md        Action reference, inputs, auth, permissions
│   └── 03_workflow_recipes.md      Copy-paste workflows for common use cases
│
├── mcp/
│   └── 01_mcp_json.md              .mcp.json format, server definitions, credentials
│
├── settings/
│   ├── 01_settings_json.md         Scope precedence, permissions, env, hooks, MCP approval
│   └── 02_claude_directory.md      .claude/ layout, file roles, git hygiene
│
│ ── PLUGINS ─────────────────────────────────────────────────
├── plugins/
│   ├── 01_plugin_fundamentals.md   What plugins bundle, directory layout, plugin.json
│   ├── 02_install_and_scopes.md    plugin install, scopes, uninstalling
│   ├── 03_marketplaces.md          Official/third-party marketplaces, hosting, sharing
│   └── 04_managing_plugins.md      /plugin UI, enable/disable, updates, gotchas
│
│ ── OPERATIONS ──────────────────────────────────────────────
└── operations/
    └── 01_troubleshooting.md       doctor, safe mode, debug logs, component isolation
```

---

## Contents

### Basics — [full index](basics/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Basics-191919.svg?logo=anthropic&logoColor=white)](basics/index.md)

| Guide | Description |
|-------|-------------|
| [Getting Started](basics/01_getting_started.md) | Installation, authentication, project trust, and a safe first workflow |
| [Sessions and Core CLI](basics/02_sessions_and_cli.md) | Session lifecycle, permission modes, models, output formats, and budgets |

### Commands — [full index](commands/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Commands-191919.svg?logo=anthropic&logoColor=white)](commands/index.md)

| Guide | Description |
|-------|-------------|
| [Custom Commands](commands/01_custom_commands.md) | Flat skill-compatible command files, arguments, dynamic context, frontmatter |

### Skills — [full index](skills/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Skills-191919.svg?logo=anthropic&logoColor=white)](skills/index.md)

| Guide | Description |
|-------|-------------|
| [Skills Overview](skills/01_skills_overview.md) | SKILL.md format, all frontmatter fields, invocation syntax |
| [Advanced Skills](skills/02_skills_advanced.md) | Supporting files, dynamic context, auto-invocation, context forking |

### Rules — [full index](rules/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Rules-191919.svg?logo=anthropic&logoColor=white)](rules/index.md)

| Guide | Description |
|-------|-------------|
| [CLAUDE.md](rules/01_claude_md.md) | Memory hierarchy, imports, complete rule `paths` frontmatter, glob scoping |

### Hooks — [full index](hooks/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Hooks-191919.svg?logo=anthropic&logoColor=white)](hooks/index.md)

| Guide | Description |
|-------|-------------|
| [Hooks Overview](hooks/01_hooks_overview.md) | Lifecycle events, config structure, matchers, common patterns |
| [Hook Handlers](hooks/02_hook_handlers.md) | command/http/mcp_tool/prompt/agent handlers, JSON decisions, blocking behavior |

### Agents — [full index](agents/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Agents-191919.svg?logo=anthropic&logoColor=white)](agents/index.md)

| Guide | Description |
|-------|-------------|
| [Subagents](agents/01_subagents.md) | `.claude/agents/` format, frontmatter, isolation, delegation logic |

### GitHub — [full index](github/index.md)

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF.svg?logo=githubactions&logoColor=white)](github/index.md)

| Guide | Description |
|-------|-------------|
| [GitHub App](github/01_github_app.md) | Install, @claude mentions in PRs/issues, CLAUDE.md in CI |
| [GitHub Actions](github/02_github_actions.md) | `anthropics/claude-code-action@v1`, inputs, auth, permissions |
| [Workflow Recipes](github/03_workflow_recipes.md) | PR review, issue triage, security review, scheduled audit |

### MCP — [full index](mcp/index.md)

[![MCP](https://img.shields.io/badge/MCP-Servers-000000.svg?logoColor=white)](mcp/index.md)

| Guide | Description |
|-------|-------------|
| [.mcp.json](mcp/01_mcp_json.md) | Server definitions, credentials, common servers, vs settings.json |

### Settings — [full index](settings/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Settings-191919.svg?logo=anthropic&logoColor=white)](settings/index.md)

| Guide | Description |
|-------|-------------|
| [settings.json](settings/01_settings_json.md) | Scope precedence, permissions patterns, env vars, hooks wiring, MCP approval |
| [`.claude/` Directory](settings/02_claude_directory.md) | What belongs in `.claude/`, what does not, and how to configure it safely |

### Plugins — [full index](plugins/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugins-191919.svg?logo=anthropic&logoColor=white)](plugins/index.md)

| Guide | Description |
|-------|-------------|
| [Plugin Fundamentals](plugins/01_plugin_fundamentals.md) | What plugins bundle, directory layout, plugin.json manifest |
| [Install & Scopes](plugins/02_install_and_scopes.md) | `/plugin install`, shell install, scopes, uninstalling |
| [Marketplaces](plugins/03_marketplaces.md) | Official marketplace, third-party hosting, sharing with teammates |
| [Managing Plugins](plugins/04_managing_plugins.md) | `/plugin` UI, enable/disable, updates, key gotchas |

### Operations — [full index](operations/index.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Operations-191919.svg?logo=anthropic&logoColor=white)](operations/index.md)

| Guide | Description |
|-------|-------------|
| [Troubleshooting](operations/01_troubleshooting.md) | Layered diagnosis with doctor, safe mode, debug logs, and component checks |

---

## Reading Order

> [!TIP]
> Pick the path that matches your goal.

### New to Claude Code

1. [Getting Started](basics/01_getting_started.md) — install, authenticate, and inspect a project safely
2. [Sessions and Core CLI](basics/02_sessions_and_cli.md) — understand sessions, modes, and cost controls
3. [CLAUDE.md](rules/01_claude_md.md) — teach Claude about your project
4. [`.claude/` Directory](settings/02_claude_directory.md) — understand project configuration layout
5. [Custom Commands](commands/01_custom_commands.md) — quick flat skill-compatible shortcuts
6. [Skills Overview](skills/01_skills_overview.md) — reusable workflows
7. [settings.json](settings/01_settings_json.md) — control what Claude can do
8. [Troubleshooting](operations/01_troubleshooting.md) — isolate configuration and integration failures

### Setting up GitHub integration

1. [GitHub App](github/01_github_app.md) — install and configure @claude
2. [GitHub Actions](github/02_github_actions.md) — understand the action
3. [Workflow Recipes](github/03_workflow_recipes.md) — pick a recipe and go

### Building automation

1. [settings.json](settings/01_settings_json.md) — scopes and permissions
2. [`.claude/` Directory](settings/02_claude_directory.md) — shared vs local config files
3. [Hooks Overview](hooks/01_hooks_overview.md) — event model
4. [Hook Handlers](hooks/02_hook_handlers.md) — handler types and decisions
5. [.mcp.json](mcp/01_mcp_json.md) — external tool integrations
6. [Troubleshooting](operations/01_troubleshooting.md) — diagnose failures across layers

### Building and sharing plugins

1. [Plugin Fundamentals](plugins/01_plugin_fundamentals.md) — directory structure
2. [Skills Overview](skills/01_skills_overview.md) — authoring skills for plugins
3. [Install & Scopes](plugins/02_install_and_scopes.md) — how plugins are installed
4. [Marketplaces](plugins/03_marketplaces.md) — distributing to others
