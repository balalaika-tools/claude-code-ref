# Install & Scopes

Before reading this: **[Plugin Fundamentals](01_plugin_fundamentals.md)**

---

## 1. Installing

```bash
claude plugin install <name>@<marketplace>
claude plugin install git-tools@anthropic
claude plugin install git-tools@anthropic --scope project
```

Downloads plugin source to `~/.claude/plugins/<name>/` and registers at the selected scope.

---

## 2. Three Scopes

| Scope | Config file | Committed? | Applies to |
|-------|------------|-----------|-----------|
| User (default) | `~/.claude/settings.json` | No | All projects |
| Project | `.claude/settings.json` | Yes | This project, all teammates |
| Local | `.claude/settings.local.json` | No | This project, you only |

**Override order**: `local > project > user` (most specific wins).

> Project scope is the right choice for team-wide enforcement — teammates get the plugin automatically.

> Local scope **only applies in the directory where installed**. `/projects/api` local doesn't load in `/projects/frontend`.

---

## 3. Testing Locally

Load a plugin for the current session without installing:

```bash
claude --plugin-dir ./my-plugin
```

Nothing written to config. To pick up edits mid-session:

```
/reload-plugins
```

`/reload-plugins` is only needed during an active session — restarting always reloads from disk.

---

## 4. Uninstalling

```bash
claude plugin uninstall git-tools
claude plugin uninstall git-tools --scope project
```

---

## 5. Summary

| Action | File modified |
|--------|--------------|
| `install --scope user` | `~/.claude/settings.json` |
| `install --scope project` | `.claude/settings.json` |
| `install --scope local` | `.claude/settings.local.json` |
| `--plugin-dir` | Nothing (session-only) |
| `uninstall` | Removes from relevant file |

---

**Next**: [Marketplaces](04_marketplaces.md)
