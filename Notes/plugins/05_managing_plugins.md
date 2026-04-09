# Managing Plugins

Before reading this: **[Install & Scopes](03_install_and_scopes.md)**

---

## 1. Listing

```bash
claude plugin list
claude plugin list --scope project
```

---

## 2. Enable / Disable

Toggle without uninstalling:

```bash
claude plugin disable git-tools
claude plugin enable git-tools
```

Or toggle in `/plugin` → **Installed** tab.

---

## 3. Updating

```bash
claude plugin update git-tools
claude plugin update --all
```

Claude Code checks for updates at startup and shows them in the Installed tab. Updates are manual unless you opt in:

```json
{ "plugins": { "git-tools": { "version": "latest", "autoUpdate": true } } }
```

> ⚠️ Be cautious with `autoUpdate` for plugins with hooks — unexpected behavior changes can affect all projects.

---

## 4. Quick Reference

| Task | Command |
|------|---------|
| Install | `claude plugin install <name>@<marketplace>` |
| Load from local dir | `claude --plugin-dir ./path` |
| List | `claude plugin list` |
| Disable / Enable | `claude plugin disable/enable <name>` |
| Update one / all | `claude plugin update <name>` / `--all` |
| Uninstall | `claude plugin uninstall <name>` |
| Reload mid-session | `/reload-plugins` |
| Plugin manager UI | `/plugin` |
| Add marketplace | `/plugin marketplace add owner/repo` |

---

## 5. Key Things to Remember

1. **Plugin code lives in `~/.claude/plugins/`** — not in your project. Committing `.claude/settings.json` shares the config reference, not the source.

2. **Local scope only applies in the install directory.**

3. **`/reload-plugins` only needed mid-session.** Restart always reloads from disk.

4. **Scope order: `local > project > user`.**

5. **Check the Errors tab** when a skill or hook stops working.

---

**Back to**: [Plugins Index](README.md)
