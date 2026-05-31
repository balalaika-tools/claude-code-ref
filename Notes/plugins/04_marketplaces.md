# Marketplaces

Before reading this: **[Install & Scopes](03_install_and_scopes.md)**

---

## 1. What Is a Marketplace?

A marketplace is a catalog of plugins. Adding a marketplace makes plugins discoverable; installing a plugin copies that plugin into your local cache and enables it at a chosen scope.

---

## 2. Official Anthropic Marketplace

Built in:

```text
/plugin install github@claude-plugins-official
```

Also browsable in `/plugin` -> **Discover**.

If the catalog is missing or stale:

```text
/plugin marketplace update claude-plugins-official
/plugin marketplace add anthropics/claude-plugins-official
```

---

## 3. Community and Third-Party Marketplaces

Add the community marketplace:

```text
/plugin marketplace add anthropics/claude-plugins-community
```

Install from it:

```text
/plugin install <plugin-name>@claude-community
```

Add your own:

```text
/plugin marketplace add myorg/claude-plugins
/plugin marketplace add https://gitlab.com/company/plugins.git
/plugin marketplace add ./my-marketplace
/plugin marketplace add https://example.com/marketplace.json
```

Remove:

```text
/plugin marketplace remove myorg
```

Removing a marketplace uninstalls plugins installed from it.

---

## 4. Hosting Your Own

A marketplace repo contains `.claude-plugin/marketplace.json`:

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

Each entry's `name` should match the plugin's manifest name. The source can be a git repo, subdirectory, local path, URL, or other supported marketplace source.

Teams can add marketplaces through project settings with `extraKnownMarketplaces` so collaborators are prompted to install trusted team marketplaces after trusting the repo.

---

## 5. Submitting Plugins

The official marketplace is curated by Anthropic. Community plugin submission goes through the community marketplace flow, where entries are pinned to specific commit SHAs after validation.

For internal tools, a private organization marketplace is usually simpler and gives you control over review, versioning, and rollout.

---

## 6. `/plugin` UI

| Tab | What it shows |
|-----|---------------|
| **Discover** | Plugins from configured marketplaces |
| **Installed** | Enabled, disabled, and errored plugins by scope |
| **Marketplaces** | Configured catalogs, update/remove, auto-update |
| **Errors** | Plugin load failures |

Plugin detail views show components, estimated context cost, and what will be installed. Review these before enabling a plugin.

---

**Next**: [Managing Plugins](05_managing_plugins.md)
