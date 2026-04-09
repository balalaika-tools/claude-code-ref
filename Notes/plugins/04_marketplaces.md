# Marketplaces

Before reading this: **[Install & Scopes](03_install_and_scopes.md)**

---

## 1. What Is a Marketplace?

A git repo that indexes available plugins via a `marketplace.json` file. Claude Code fetches this index for discovery and installation.

---

## 2. Official Anthropic Marketplace

Built-in, no configuration needed:

```bash
claude plugin install some-plugin@anthropic
```

Also browsable in `/plugin` → **Discover** tab.

---

## 3. Third-Party Marketplaces

Add:
```
/plugin marketplace add myorg/claude-plugins
```

Install from it:
```bash
claude plugin install db-utils@myorg
```

Remove:
```
/plugin marketplace remove myorg
```

---

## 4. Hosting Your Own

Any git repo with `.claude-plugin/marketplace.json`:

```json
{
  "name": "MyOrg Plugins",
  "description": "Internal plugins for the engineering team.",
  "plugins": [
    {
      "name": "db-utils",
      "description": "Database migration and introspection utilities.",
      "version": "1.3.2",
      "repository": "https://github.com/myorg/db-utils-plugin",
      "keywords": ["database", "postgres"]
    }
  ]
}
```

Each entry's `name` must match the plugin's own `plugin.json` name. The `repository` field points to the actual plugin repo.

Teammates add it with `/plugin marketplace add myorg/my-org-plugins`.

---

## 5. Submitting to Official Marketplace

1. Ensure valid `plugin.json` with name, version, description, author, homepage, license
2. Open a PR against `anthropics/claude-plugins` adding your plugin to the marketplace.json
3. Anthropic reviews before merging

---

## 6. `/plugin` UI

| Tab | What it shows |
|-----|---------------|
| **Discover** | All plugins from configured marketplaces |
| **Installed** | Installed plugins (any scope) |
| **Marketplaces** | Configured sources, add/remove |
| **Errors** | Plugin load failures |

---

**Next**: [Managing Plugins](05_managing_plugins.md)
