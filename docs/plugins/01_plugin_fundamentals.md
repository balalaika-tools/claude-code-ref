# Plugin Fundamentals

> **Who this is for**: Claude Code users who want to package reusable skills, agents, hooks, MCP servers, or other extensions.

Before reading this, understand reusable skills: **[Skills Overview](../skills/01_skills_overview.md)**

---

## 1. What Is a Plugin?

A plugin is a trusted, distributable directory of Claude Code components. It can bundle:

| Component | What it does |
|-----------|-------------|
| **Skills** | Prompt workflows invoked as `/plugin:skill` |
| **Commands** | Flat skill-compatible command files; use `skills/` for new work |
| **Agents** | Custom subagents |
| **Hooks** | Lifecycle automation and enforcement |
| **MCP Servers** | External tools and data sources |
| **LSP Servers** | Code intelligence such as definitions and references |
| **Output styles / themes / monitors** | UI and background behavior |
| **bin/** | Executables added to the Bash tool's `PATH` while enabled |

Plugins can run code on your machine. Treat them like developer tooling you install from npm, Homebrew, or a CI action.

> **Key insight**: A plugin is not sandboxed config like a skill file — it can bundle hooks, MCP servers, and executables that run arbitrary code, so installing one is a trust decision equivalent to installing a third-party package.

---

## 2. When to Use a Plugin

**Standalone `.claude/` config** is best for one repository: CLAUDE.md, project skills, project hooks, or project settings.

**Plugin** is best when the same capability should be reused across projects or distributed to a team/community with versioning and marketplace discovery.

---

## 3. Directory Structure

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json               ← manifest (optional but recommended)
├── skills/
│   └── review/
│       └── SKILL.md
├── agents/
│   └── tester.md
├── hooks/
│   └── hooks.json
├── .mcp.json
├── .lsp.json
├── monitors/
│   └── monitors.json
└── bin/
    └── my-tool
```

> **Common mistake**: Putting `skills/`, `agents/`, `commands/`, or `hooks/` inside `.claude-plugin/`. Only plugin metadata belongs there; components live at the plugin root.

---

## 4. `plugin.json` Manifest

```json
{
  "name": "my-plugin",
  "displayName": "My Plugin",
  "version": "1.0.0",
  "description": "A short description of what this plugin does."
}
```

If a manifest exists, `name` is the only required field. The manifest is still worth adding because it documents identity, metadata, and non-default component paths.

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes, if manifest exists | Kebab-case identifier used for namespacing |
| `displayName` | No | Human-readable name in UI |
| `version` | No | Semver. If omitted, git commit SHA can be used for updates |
| `description` | No | Shown in plugin UI and marketplaces |
| `author` | No | Author object or metadata |
| `homepage` | No | Docs or repo URL |
| `repository` | No | Source URL |
| `license` | No | License identifier |
| `keywords` | No | Discovery tags |
| `dependencies` | No | Other plugins this plugin requires |
| `userConfig` | No | Values prompted at enable time |

Not all components are required. A plugin with only one skill is valid.

---

**Next**: [Install & Scopes](02_install_and_scopes.md)
