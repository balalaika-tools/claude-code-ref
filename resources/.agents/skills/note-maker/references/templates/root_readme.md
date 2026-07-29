# Root README.md Template

The landing page for the entire notes repo. Tells readers what it covers, how it's organized, and where to start.

For badge hex codes and logo names, see `../badges.md`.

---

## Template

```markdown
# {Topic} Notes

> {One-line tagline describing the scope — practical, not academic.}

[![Badge1](https://img.shields.io/badge/Label-version-COLOR.svg?logo=name&logoColor=white)](URL)
[![Badge2](https://img.shields.io/badge/Label-version-COLOR.svg?logo=name&logoColor=white)](URL)

---

## Structure

\```
{repo-name}/
│
│ ── CATEGORY NAME ──────────────────────────────────────
├── category/
│   ├── sub_topic/       Short description of what's here
│   └── other_topic/     Short description
│
│ ── ANOTHER CATEGORY ───────────────────────────────────
└── another/
    └── sub/             Description
\```

---

## Contents

### Category Name — [full index](category/README.md)

[![Tech](https://img.shields.io/badge/Tech-version-COLOR.svg?logo=tech&logoColor=white)](URL)

| Guide | Description |
|-------|-------------|
| [Title](category/01_file.md) | What this file covers |
| [Title](category/02_file.md) | What this file covers |

---

## Reading Order

> [!TIP]
> Not sure where to start? Pick the path that matches your goal.

### Path Name

1. [Topic](path/to/file.md) — why to read this first
2. [Topic](path/to/file.md) — builds on the previous
```

---

## Key rules

- The ASCII tree uses box-drawing: `├──`, `└──`, `│` — with inline descriptions after directory names
- Category headers in the tree use `── CAPS ──` decorative lines
- The Contents section groups files by category with a markdown table per group
- Reading Order has 2–4 named paths for different experience levels or goals
- Omit the `*Last updated*` line unless the user requests it — it goes stale immediately
