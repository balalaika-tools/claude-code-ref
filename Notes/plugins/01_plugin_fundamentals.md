# Plugin Fundamentals

---

## 1. What Is a Plugin?

A distributable bundle that extends Claude Code. It packages one or more of:

| Component | What it does |
|-----------|-------------|
| **Skills** | Named prompts via `/plugin-name:skill-name` |
| **Agents** | Specialized subagents |
| **Hooks** | Shell commands on lifecycle events |
| **MCP Servers** | External tools via Model Context Protocol |

---

## 2. When to Use a Plugin

**Standalone `.claude/` config** — project-specific, not shared externally, just a CLAUDE.md or hook.

**Plugin** — shared across projects/teams, combines multiple components, version-managed, marketplace-discoverable.

---

## 3. Directory Structure

```
my-plugin/                        ← plugin root
├── .claude-plugin/
│   └── plugin.json               ← manifest (required)
├── skills/
│   └── review/
│       └── SKILL.md
├── agents/
│   └── tester/
│       └── AGENT.md
├── hooks/
│   └── pre-commit.sh
└── .mcp.json
```

> ⚠️ **Common mistake**: Putting `skills/`, `agents/` inside `.claude-plugin/` instead of at the plugin root. Only `plugin.json` goes in `.claude-plugin/`.

---

## 4. `plugin.json` Manifest

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "A short description of what this plugin does."
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Lowercase, hyphens. Used in invocation: `/my-plugin:skill-name` |
| `version` | Yes | Semver. Used for marketplace update checks |
| `description` | Yes | Shown in `/plugin` UI and marketplace |
| `author` | No | Your name |
| `homepage` | No | Links to repo in UI |
| `license` | No | License identifier |
| `keywords` | No | Improves marketplace search |

Not all components are required. A plugin with only skills and no hooks is valid.

---

**Next**: [Install & Scopes](03_install_and_scopes.md)
