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

## Start here

| If you want to… | Start with | Working outcome |
|---|---|---|
| {Reader goal} | [{First useful entry}]({path}.md) | {Visible result or concrete capability} |
| {Reader goal} | [{First useful entry}]({path}.md) | {Visible result or concrete capability} |

---

## Contents

<div class="grid cards" markdown>

-   **{Area name}**

    {One sentence describing the questions this area helps the reader answer.}

    [{Start or explore label} →]({area}/index.md)

-   **{Area name}**

    {One sentence describing the concrete capabilities covered here.}

    [{Start or explore label} →]({area}/index.md)

-   **{Area name}**

    {One sentence describing the systems, trade-offs, or workflows covered here.}

    [{Start or explore label} →]({area}/index.md)

</div>

The landing page stops at section-level navigation. Each linked section index owns its detailed
list of guides; learning paths below may link directly to selected guides.

---

## Learning paths

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

- Put **Start here** immediately after the introduction and route common reader goals to a useful
  first result
- Follow it with **Contents** organized around reader intent, not directory shape
- Use two navigation levels: landing page → section index → individual notes
- The landing page lists areas and sections; section indexes own exhaustive guide listings
- Learning paths may link directly to the few leaf notes that form the route
- In MkDocs Material, Contents may use a card grid linking to section `index.md` pages
- In Markdown-only collections, replace the cards with compact grouped Area / Covers / Start here tables
- Keep card titles and descriptions parallel, concise, and free of decorative emoji
- Add a small `Repository layout` tree only when contributors genuinely need it; it is secondary,
  never the primary navigation
- The Contents section groups files by category with a markdown table per group
- Learning paths has 2–4 named paths for different experience levels or goals
- Every path reaches a runnable result or concrete worked outcome within its first two entries
- Paths follow **do → understand → harden**; explicitly label any revisit to an earlier note for greater depth
- One named path is for a first-time reader and reaches a complete useful outcome before production deep dives or references
- Each path states its audience, working result, and stop point
- Omit the `*Last updated*` line unless the user requests it — it goes stale immediately
- In MkDocs mode, write this template to `docs/index.md`; do not duplicate it in the repository
  `README.md`
