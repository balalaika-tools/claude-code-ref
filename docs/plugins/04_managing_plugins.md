# Managing Plugins

> **Who this is for**: Claude Code users responsible for installed plugin lifecycle, updates, diagnostics, and trust decisions.

Before reading this: **[Install & Scopes](02_install_and_scopes.md)**

---

## 1. Listing

```bash
claude plugin list
claude plugin list --json
claude plugin details formatter@my-team-tools
```

The `/plugin` UI is usually the easiest way to inspect components, errors, and scope.

---

## 2. Enable / Disable

```text
/plugin disable formatter@my-team-tools
/plugin enable formatter@my-team-tools
```

Or use `/plugin` -> **Installed**.

Disabling leaves the plugin installed but prevents its components from loading.

---

## 3. Updating

```bash
claude plugin update formatter@my-team-tools
claude plugin update formatter@my-team-tools --scope project
```

Marketplace auto-update is configured per marketplace. Official Anthropic marketplaces auto-update by default; third-party and local development marketplaces usually do not.

If plugins update during a session, run:

```text
/reload-plugins
```

Versioning caveat: if a plugin sets `version` in `plugin.json`, users receive updates only when that version changes. For fast-moving internal plugins, omitting `version` can make the git commit SHA drive updates.

> **Key insight**: A pinned `version` field in `plugin.json` silently freezes users on that version until you bump it, so fast-moving internal plugins often need to omit `version` and rely on git SHA-driven updates instead.

---

## 4. Quick Reference

| Task | Command |
|------|---------|
| Install | `/plugin install <name>@<marketplace>` |
| Shell install | `claude plugin install <name>@<marketplace>` |
| Load local dir | `claude --plugin-dir ./path` |
| List | `claude plugin list` |
| Details | `claude plugin details <name>@<marketplace>` |
| Disable / Enable | `/plugin disable <name>@<marketplace>` / `/plugin enable ...` |
| Update | `claude plugin update <name>@<marketplace>` |
| Uninstall | `/plugin uninstall <name>@<marketplace>` |
| Reload mid-session | `/reload-plugins` |
| Plugin manager UI | `/plugin` |
| Add marketplace | `/plugin marketplace add owner/repo` |

---

## 5. Key Things to Remember

1. **Plugins are trusted code.** Review source, components, hooks, MCP servers, and marketplace provenance.

2. **Installed marketplace plugins live in a local cache.** Do not write plugin logic that reaches outside the plugin directory.

3. **Project scope shares the reference, not the cached source.** Teammates still install/cache locally after trusting the repo.

4. **Plugin skills are namespaced.** Invoke with `/plugin-name:skill-name`.

5. **Use `/reload-plugins` after mid-session changes.** Restarting also reloads plugins.

6. **Check the Errors tab** when a skill, hook, MCP server, or LSP server does not appear.

For reload behavior, component isolation, and safe bisection, see
[Troubleshooting](../operations/01_troubleshooting.md).

---

**Back to**: [Plugins Index](index.md)
