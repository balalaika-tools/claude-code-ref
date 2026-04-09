# Claude Code Notes

> A practical reference for engineers who want to master Claude Code — from commands and skills to hooks, agents, GitHub integration, and plugins.

[![Claude Code](https://img.shields.io/badge/Claude_Code-CLI-191919.svg?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Anthropic](https://img.shields.io/badge/Anthropic-API-FF6B35.svg?logoColor=white)](https://anthropic.com)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF.svg?logo=githubactions&logoColor=white)](github/README.md)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-Spec-000000.svg?logoColor=white)](https://modelcontextprotocol.io)
[![Markdown](https://img.shields.io/badge/Markdown-Notes-000000.svg?logo=markdown&logoColor=white)](.)

---

## Structure

```
claude-code/
│
│ ── CUSTOMIZATION ───────────────────────────────────────────
├── commands/
│   └── 01_custom_commands.md       Slash commands from .claude/commands/
│
├── skills/
│   ├── 01_skills_overview.md       SKILL.md format, frontmatter, invocation
│   └── 02_skills_advanced.md       Supporting files, shell injection, auto-invoke, forking
│
├── rules/
│   └── 01_claude_md.md             CLAUDE.md, .claude/rules/, hierarchy, imports
│
│ ── AUTOMATION ──────────────────────────────────────────────
├── hooks/
│   ├── 01_hooks_overview.md        Lifecycle events, config structure, common patterns
│   └── 02_hook_handlers.md         command/http/prompt/agent handlers, blocking
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
│   └── 01_settings_json.md         All scopes, permissions, env, hooks, MCP control
│
│ ── PLUGINS ─────────────────────────────────────────────────
└── plugins/
    ├── 01_plugin_fundamentals.md   What plugins bundle, directory layout, plugin.json
    ├── 03_install_and_scopes.md    claude plugin install, three scopes, uninstalling
    ├── 04_marketplaces.md          Official/third-party marketplaces, hosting, sharing
    └── 05_managing_plugins.md      /plugin UI, enable/disable, auto-updates, gotchas
```

---

## Contents

### Commands — [full index](commands/README.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Commands-191919.svg?logo=anthropic&logoColor=white)](commands/README.md)

| Guide | Description |
|-------|-------------|
| [Custom Commands](commands/01_custom_commands.md) | `.claude/commands/*.md`, `$ARGUMENTS`, shell injection, frontmatter |

### Skills — [full index](skills/README.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Skills-191919.svg?logo=anthropic&logoColor=white)](skills/README.md)

| Guide | Description |
|-------|-------------|
| [Skills Overview](skills/01_skills_overview.md) | SKILL.md format, all frontmatter fields, invocation syntax |
| [Advanced Skills](skills/02_skills_advanced.md) | Supporting files, shell injection, auto-invocation, context forking |

### Rules — [full index](rules/README.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Rules-191919.svg?logo=anthropic&logoColor=white)](rules/README.md)

| Guide | Description |
|-------|-------------|
| [CLAUDE.md](rules/01_claude_md.md) | File hierarchy, what to include, imports, `.claude/rules/`, monorepos |

### Hooks — [full index](hooks/README.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Hooks-191919.svg?logo=anthropic&logoColor=white)](hooks/README.md)

| Guide | Description |
|-------|-------------|
| [Hooks Overview](hooks/01_hooks_overview.md) | Lifecycle events, config structure, matchers, common patterns |
| [Hook Handlers](hooks/02_hook_handlers.md) | command/http/prompt/agent types, exit codes, blocking behavior |

### Agents — [full index](agents/README.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Agents-191919.svg?logo=anthropic&logoColor=white)](agents/README.md)

| Guide | Description |
|-------|-------------|
| [Subagents](agents/01_subagents.md) | `.claude/agents/` format, frontmatter, isolation, delegation logic |

### GitHub — [full index](github/README.md)

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF.svg?logo=githubactions&logoColor=white)](github/README.md)

| Guide | Description |
|-------|-------------|
| [GitHub App](github/01_github_app.md) | Install, @claude mentions in PRs/issues, CLAUDE.md in CI |
| [GitHub Actions](github/02_github_actions.md) | `anthropics/claude-code-action@v1`, inputs, auth, permissions |
| [Workflow Recipes](github/03_workflow_recipes.md) | PR review, issue triage, security review, scheduled audit |

### MCP — [full index](mcp/README.md)

[![MCP](https://img.shields.io/badge/MCP-Servers-000000.svg?logoColor=white)](mcp/README.md)

| Guide | Description |
|-------|-------------|
| [.mcp.json](mcp/01_mcp_json.md) | Server definitions, credentials, common servers, vs settings.json |

### Settings — [full index](settings/README.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Settings-191919.svg?logo=anthropic&logoColor=white)](settings/README.md)

| Guide | Description |
|-------|-------------|
| [settings.json](settings/01_settings_json.md) | Four scopes, permissions patterns, env vars, hooks wiring, MCP control |

### Plugins — [full index](plugins/README.md)

[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugins-191919.svg?logo=anthropic&logoColor=white)](plugins/README.md)

| Guide | Description |
|-------|-------------|
| [Plugin Fundamentals](plugins/01_plugin_fundamentals.md) | What plugins bundle, directory layout, plugin.json manifest |
| [Install & Scopes](plugins/03_install_and_scopes.md) | `claude plugin install`, three scopes, what each writes, uninstalling |
| [Marketplaces](plugins/04_marketplaces.md) | Official marketplace, third-party hosting, sharing with teammates |
| [Managing Plugins](plugins/05_managing_plugins.md) | `/plugin` UI, enable/disable, auto-updates, key gotchas |

---

## Reading Order

> [!TIP]
> Pick the path that matches your goal.

### New to Claude Code

1. [CLAUDE.md](rules/01_claude_md.md) — teach Claude about your project
2. [Custom Commands](commands/01_custom_commands.md) — quick personal shortcuts
3. [Skills Overview](skills/01_skills_overview.md) — reusable workflows
4. [settings.json](settings/01_settings_json.md) — control what Claude can do
5. [Hooks Overview](hooks/01_hooks_overview.md) — automate around Claude's actions

### Setting up GitHub integration

1. [GitHub App](github/01_github_app.md) — install and configure @claude
2. [GitHub Actions](github/02_github_actions.md) — understand the action
3. [Workflow Recipes](github/03_workflow_recipes.md) — pick a recipe and go

### Building automation

1. [settings.json](settings/01_settings_json.md) — scopes and permissions
2. [Hooks Overview](hooks/01_hooks_overview.md) — event model
3. [Hook Handlers](hooks/02_hook_handlers.md) — all four handler types
4. [.mcp.json](mcp/01_mcp_json.md) — external tool integrations

### Building and sharing plugins

1. [Plugin Fundamentals](plugins/01_plugin_fundamentals.md) — directory structure
2. [Skills Overview](skills/01_skills_overview.md) — authoring skills for plugins
3. [Install & Scopes](plugins/03_install_and_scopes.md) — how plugins are installed
4. [Marketplaces](plugins/04_marketplaces.md) — distributing to others

---

*Last updated: April 2026*
