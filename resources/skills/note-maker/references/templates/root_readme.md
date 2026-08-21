# Site Index Template

The canonical landing page for the notes collection. In an MkDocs collection this is
`docs/index.md`; in a Markdown-only collection it is the root `README.md`. It tells readers what
the collection covers, how it is organized, and where to start.

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
docs/
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

**Working result by entry 2**: {the command, implementation, or concrete trace the reader can complete}

1. [Do: Topic](path/to/file.md) — produces the first visible result
2. [Understand: Topic](path/to/file.md) — explains why that result works; may revisit entry 1 explicitly
3. [Harden: Topic](path/to/file.md) — adds the first production requirement, only if needed

**Stop here if**: {the baseline already meets the reader's need}. Continue to {next path/note} when {specific production or specialist requirement appears}.
```

---

## Key rules

- The ASCII tree uses box-drawing: `├──`, `└──`, `│` — with inline descriptions after directory names
- Category headers in the tree use `── CAPS ──` decorative lines
- The Contents section groups files by category with a markdown table per group
- Reading Order has 2–4 named paths for different experience levels or goals
- Every path reaches a runnable result or concrete worked outcome within its first two entries
- Paths follow **do → understand → harden**; explicitly label any revisit to an earlier note for greater depth
- One named path is for a first-time reader and reaches a complete useful outcome before production deep dives or references
- Each path states its audience, working result, and stop point
- Omit the `*Last updated*` line unless the user requests it — it goes stale immediately
- In MkDocs mode, write this template to `docs/index.md`; do not duplicate it in the repository
  `README.md`
