# Install & Scopes

> **Who this is for**: Claude Code users who understand plugin structure and need to install, test, share, or remove plugins safely.

Before reading this: **[Plugin Fundamentals](01_plugin_fundamentals.md)**

---

## 1. Installing

Inside Claude Code:

```text
/plugin install github@claude-plugins-official
/plugin install formatter@my-team-tools
```

From the shell:

```bash
claude plugin install formatter@my-team-tools
claude plugin install formatter@my-team-tools --scope project
```

The official Anthropic marketplace is `claude-plugins-official`. If it is missing or stale:

```text
/plugin marketplace update claude-plugins-official
/plugin marketplace add anthropics/claude-plugins-official
```

Marketplace plugins are copied into the local plugin cache, not used in-place from the source repo.

---

## 2. Scopes

| Scope | Config file | Committed? | Applies to |
|-------|------------|-----------|-----------|
| User (default) | `~/.claude/settings.json` | No | You, all projects |
| Project | `.claude/settings.json` | Yes | Everyone who trusts this repo |
| Local | `.claude/settings.local.json` | No | You, this repo only |
| Managed | Managed settings | Admin-controlled | Organization policy |

Project scope shares the plugin reference, not the plugin source. Teammates still install/cache the plugin locally after trusting the project.

---

## 3. Testing Locally

Load a plugin for the current session without installing:

```bash
claude --plugin-dir ./my-plugin
```

Nothing is written to settings. To pick up plugin changes mid-session:

```text
/reload-plugins
```

For iterative development, `claude plugin init my-tool` can scaffold a plugin inside your skills directory so Claude Code loads it automatically as a skills-directory plugin.

---

## 4. Uninstalling

```text
/plugin uninstall formatter@my-team-tools
```

```bash
claude plugin uninstall formatter@my-team-tools
claude plugin uninstall formatter@my-team-tools --scope project
```

Use `--keep-data` when you want to preserve the plugin's persistent data directory.

---

## 5. Summary

| Action | Result |
|--------|--------|
| `install --scope user` | Adds to user settings |
| `install --scope project` | Adds to project settings |
| `install --scope local` | Adds to local project settings |
| `--plugin-dir` | Session-only load |
| `uninstall` | Removes plugin reference from the chosen scope |
| `/reload-plugins` | Reloads active plugin components without restarting |

---

**Next**: [Marketplaces](03_marketplaces.md)
