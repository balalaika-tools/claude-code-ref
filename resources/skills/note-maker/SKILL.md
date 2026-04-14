---
name: note-maker
description: "Scaffold and write structured technical study notes with shields.io badges, ASCII diagrams, numbered files, cross-linked READMEs, and multiple reading paths. Use this skill whenever the user wants to create a new knowledge base, study notes, technical reference docs, learning materials, or documentation repository on any topic — even if they just say 'notes on X' or 'write up what I learned about Y' or 'create a guide for Z'. Also use when the user wants to add a new section or file to an existing notes repo that follows this structure."
---

# Technical Notes Scaffold

You are creating a structured technical knowledge base — a curated collection of markdown files organized into directories, with badges, cross-references, reading paths, and production-grade code examples.

This is not a wiki dump or a flat list of files. It's an opinionated, layered learning resource designed for engineers. Every file should teach something specific, link to prerequisites, and point to what comes next.

## How this works

When the user invokes this skill, they provide a topic (e.g., "Kubernetes", "React Hooks", "Go concurrency"). Your job:

1. **Clarify scope** — Ask what sub-topics to cover if not already clear. Propose a directory structure and get confirmation before writing files.
2. **Scaffold the repo** — Create the root README.md, category directories, and directory-level READMEs.
3. **Write the note files** — Numbered markdown files with the formatting conventions below.

If the user already has an existing notes repo and wants to add to it, read the existing README.md first to understand the current structure, then extend it consistently.

---

## Root README.md

This is the landing page. It tells readers what the repo covers, how it's organized, and where to start.

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

---

*Last updated: {Month Year}*
```

**Important details:**
- The ASCII tree uses box-drawing: `├──`, `└──`, `│` — with inline descriptions after directory names
- Category headers in the tree use `── CAPS ──` decorative lines
- The Contents section groups files by category with a markdown table per group
- Reading Order has 2-4 named paths for different experience levels or goals
- Badges use shields.io with brand colors (see Badge Reference below)

---

## Directory README.md

Every directory gets one. It's shorter than the root README — just enough to orient the reader within that section.

```markdown
# {Section Title}

> {One-line description of what this section covers.}

[![Tech](https://img.shields.io/badge/Tech-version-COLOR.svg)](URL)

---

## Contents

| File | Topic | Description |
|------|-------|-------------|
| [01_name.md](01_name.md) | Topic | What it covers |
| [02_name.md](02_name.md) | Topic | What it covers |

---

## Reading Order

1. **Topic** — why this comes first
2. **Topic** — builds on the previous

---

## Prerequisites

- Basic understanding of X
- [Other Section](../path/README.md) — if relevant
```

---

## Note Files

These are the actual content. Each file teaches one focused topic.

### File naming

Numbered with zero-padded prefix: `01_topic_name.md`, `02_topic_name.md`. Numbers indicate reading order within a directory. Use lowercase with underscores.

### Structure template

```markdown
# {Descriptive Title}

> **Who this is for**: {Audience and what they should already know.}

---

## 1. Section Name

{Explanation with **bold** for key terms on first use.}

\```python
# Production-grade example — not toy code
code_here()
\```

---

## 2. Next Section

| Feature | Detail |
|---------|--------|
| Row 1   | Value  |
| Row 2   | Value  |

> **Key insight**: {Mental model or principle worth remembering.}

---

## 3. Architecture / Flow

\```
┌─────────────┐
│  Component  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Next Step  │
└─────────────┘
\```

---

**Next**: [Part 2: Title](02_next_file.md)
```

### Section numbering

Use one of two styles consistently within a file:
- **Plain numbers** for technical deep-dives: `## 1. Section Name`
- **Emoji numbers** for introductory/concept files: `## 1️⃣ Section Name`

Don't mix styles within a single file.

### Writing quality

Each note file should feel like it was written by a senior engineer explaining things to a competent colleague. This means:

- **Production-grade code examples** — real imports, realistic variable names, error handling where it matters. Not `foo`/`bar` toy code.
- **Inline comments that explain "why"** — not what the code does (the reader can see that), but why this approach was chosen.
- **Real-world failure modes** — what breaks in production, common mistakes, and how to avoid them.
- **Progressive complexity** — start with the mental model, build to practical usage, end with advanced patterns or edge cases.
- **High code-to-text ratio** — show, don't just tell. A code block with a two-line explanation beats a paragraph with no code.

### Formatting conventions

- **Horizontal rules** (`---`): Separate major sections. Every `## N.` section ends with one.
- **Bold** (`**term**`): Key terms on first introduction. Don't bold the same term twice.
- **Backticks** (`` `code` ``): Function names, variable names, CLI commands, file names.
- **Blockquotes**: For principles, rules, and mental models:
  - `> **Principle**: ...`
  - `> **Rule**: ...`
  - `> **Key insight**: ...`
- **Callout markers** (used sparingly, not decoratively):
  - `✅` — correct approach
  - `❌` — incorrect / anti-pattern
  - `⚠️` — warning / gotcha
  - `💡` — tip
- **Markdown tables**: For feature comparisons, concept summaries, decision matrices.
- **ASCII diagrams**: For architecture, data flow, and layered systems. Use box-drawing characters: `┌ ─ ┐ │ └ ┘ ├ ┤ ┬ ┴ ┼ → ↓ ↑ ←`

### Cross-referencing

Files don't exist in isolation. Connect them:
- **End of file**: `**Next**: [Part N: Title](next_file.md)` pointing to the next file in sequence
- **Prerequisites**: At the top: `Before reading this, understand X: **[Guide](path/to/guide.md)**`
- **Inline links**: `see [Connection Pooling](../database/05_connection_pooling.md)` when referencing concepts from other files
- Use **relative paths** for all internal links

---

## Badge Reference

Badges make the README scannable and visually identify the tech stack at a glance.

**Format:**
```
[![Label](https://img.shields.io/badge/Label-version-HEXCOLOR.svg?logo=logoname&logoColor=white)](URL)
```

**Common brand colors:**
| Technology | Color  | Logo name     |
|-----------|--------|---------------|
| Python    | 3776AB | python        |
| FastAPI   | 009688 | fastapi       |
| PostgreSQL| 336791 | postgresql    |
| Redis     | DC382D | redis         |
| Docker    | 2496ED | docker        |
| Kubernetes| 326CE5 | kubernetes    |
| React     | 61DAFB | react         |
| TypeScript| 3178C6 | typescript    |
| Node.js   | 339933 | nodedotjs     |
| Go        | 00ADD8 | go            |
| Rust      | 000000 | rust          |
| AWS       | FF9900 | amazonaws     |
| GCP       | 4285F4 | googlecloud   |
| Terraform | 844FBA | terraform     |
| GitHub Actions | 2088FF | githubactions |
| Nginx     | 009639 | nginx         |
| GraphQL   | E10098 | graphql       |
| MongoDB   | 47A248 | mongodb       |
| Kafka     | 231F20 | apachekafka   |
| Elasticsearch | 005571 | elasticsearch |
| pytest    | 0A9EDC | pytest        |
| Pydantic  | E92063 | pydantic      |
| SQLAlchemy| D71F00 | (none)        |

**Rules:**
- Version ranges use `+` suffix: `3.11+`, `0.100+`, `2.0+`
- Use `(none)` for logo when no SimpleIcons logo exists — omit the `?logo=` param entirely
- Group related badges on one line (e.g., all database badges together)
- Root README gets the full set; directory READMEs get only the badges relevant to that section

---

## Directory organization principles

Organize directories by **learning progression**, not alphabetically:

1. **Fundamentals / Basics** — entry-level concepts everyone needs
2. **Core tools / Frameworks** — the main technologies
3. **Infrastructure** — supporting systems (databases, caches, queues)
4. **Architecture / Patterns** — advanced system design
5. **Operations** — testing, deployment, monitoring

Within each directory, files go from foundational to advanced. The numbering (`01_`, `02_`, ...) reflects this progression.

Sub-directories are for topics that need 3+ files of their own. If a topic only needs one file, keep it in the parent directory.

---

## Workflow

When the user provides a topic:

1. **Propose structure first** — Show the directory tree and list of planned files with one-line descriptions. Ask: "Does this structure look right? Want to add or remove anything?"
2. **Create root README.md** — With full badges, structure tree, contents tables, and reading paths.
3. **Create directory READMEs** — One per directory, with contents and reading order.
4. **Write note files in order** — Starting from the most foundational. Each file should be 200-600 lines, dense with code and diagrams.
5. **Verify cross-references** — After writing all files, check that all internal links point to files that exist.

If the user asks to add a section to an existing repo, read the current README.md, propose where the new content fits, and update all affected READMEs and cross-references.

---

## What NOT to do

- Don't write thin, surface-level notes. Each file should be a genuine deep-dive that teaches something useful.
- Don't use emojis decoratively. The only emojis are `1️⃣`-`9️⃣` for section numbering in intro files, and `✅❌⚠️💡` for callouts.
- Don't write pseudocode. Code examples should be complete and runnable.
- Don't create flat structures. If you have 15+ files, organize into directories.
- Don't skip the ASCII tree diagram in the root README.
- Don't forget cross-references. Every file should link to its "next" and mention prerequisites.
