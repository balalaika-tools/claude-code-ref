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

| Guide | Role | Reader outcome |
|-------|------|----------------|
| [Title](category/01_file.md) | Foundation | What the reader can explain or decide afterward |
| [Title](category/02_file.md) | Implementation | What the reader can build or verify afterward |

---

## Reading Order

> [!TIP]
> Not sure where to start? Pick the path that matches your goal.

### Path Name

**For**: {reader starting point and goal}

**Outcome**: {the useful capability reached before advanced material}

1. [Topic](path/to/file.md) — why to read this first
2. [Topic](path/to/file.md) — builds on the previous

**Stop here if**: {the baseline already meets the reader's need}. Continue to {next path/note} when {specific production or specialist requirement appears}.
```

---

## Key rules

- The ASCII tree uses box-drawing: `├──`, `└──`, `│` — with inline descriptions after directory names
- Category headers in the tree use `── CAPS ──` decorative lines
- The Contents section groups files by category with a markdown table per group
- Reading Order has 2–4 named paths for different experience levels or goals
- One named path is for a first-time reader and reaches a complete useful outcome before production deep dives or references
- Each path states its audience, outcome, and stop point; if a path exceeds five files before any useful milestone, split it or add an intermediate milestone
- Omit the `*Last updated*` line unless the user requests it — it goes stale immediately
