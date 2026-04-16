---
name: note-maker
description: "Scaffold and write structured technical study notes with shields.io badges, ASCII diagrams, numbered files, cross-linked READMEs, and multiple reading paths. Uses emoji only for section numbering (1️⃣–9️⃣) and callouts (✅❌⚠️💡). Use this skill whenever the user wants to create a new knowledge base, study notes, technical reference docs, learning materials, or documentation repository on any topic — even if they just say 'notes on X' or 'write up what I learned about Y' or 'create a guide for Z'. Also use when the user wants to add a new section or file to an existing notes repo that follows this structure."
---

# Technical Notes Scaffold

You are creating a structured technical knowledge base — a curated collection of markdown files organized into directories, with badges, cross-references, reading paths, and production-grade code examples.

This is not a wiki dump or a flat list of files. It's an opinionated, layered learning resource designed for engineers. Every file should teach something specific, link to prerequisites, and point to what comes next.

If the user already has an existing notes repo and wants to add to it, read the existing README.md first to understand the current structure, then extend it consistently.

---

## Workflow

When the user provides a topic:

1. **Decide if a scout is needed** — If native knowledge is sparse or the topic is fast-moving, launch a scout subagent for a brief landscape summary (main sub-areas, versioning notes, recent shifts). Otherwise skip.
2. **Propose structure** — Show the directory tree and list of planned files with one-line descriptions. Ask: "Does this structure look right? Want to add or remove anything?"
3. **Create root README.md and directory READMEs** — Write these directly; they're structural, not research-heavy. Use the templates in `references/templates/`.
4. **Write note files** — If running in Claude Code with 3+ independent files, launch subagents in parallel (see Parallelizing section). Otherwise write files sequentially. See `references/example_note.md` for a complete worked example of a finished note.
5. **Verify cross-references** — Check all internal links point to files that exist.

If the user asks to add a section to an existing repo, read the current README.md, propose where the new content fits, and update all affected READMEs and cross-references.

---

## Root README.md

When writing a root README, read `references/templates/root_readme.md` for the full template.

Key rules:
- ASCII tree with box-drawing characters (`├──`, `└──`, `│`) and inline directory descriptions
- Category headers in the tree use `── CAPS ──` decorative lines
- Contents section: one markdown table per category, grouped by category
- Reading Order: 2–4 named paths for different experience levels or goals
- For badge hex codes and logo names, read `references/badges.md`
- Omit the `*Last updated*` line unless the user asks for it — it goes stale immediately

---

## Directory README.md

Directory READMEs are **intentionally minimal** — just enough to orient the reader within that section. Do not mirror the root's ASCII trees or decorative category dividers.

When writing a directory README, read `references/templates/directory_readme.md` for the template.

---

## Note Files

These are the actual content. Each file teaches one focused topic.

### File naming

Numbered with zero-padded prefix: `01_topic_name.md`, `02_topic_name.md`. Numbers indicate reading order within a directory. Use lowercase with underscores.

### Topic type

**Code-heavy topics** (frameworks, APIs, languages, tools): lead with a code example early; aim for high code-to-text ratio; use production-grade examples with real imports and error handling.

**Concept-heavy topics** (system design, distributed systems theory, architecture patterns): replace code blocks with ASCII diagrams, decision matrices, and annotated tables. The same structural conventions apply — "concrete scenario or worked trace" substitutes for "runnable code example."

### Structure

See `references/example_note.md` for a complete, filled-in example that demonstrates all conventions. The key skeleton:

```
# {Descriptive Title}

> **Who this is for**: {Audience and prerequisites.}

---

## 1. Section Name

{Explanation. Code example or diagram.}

---

## 2. Next Section

{Table or deeper dive.}

> **Key insight**: {Mental model or principle worth remembering.}

---

**Next**: [Part 2: Title](02_next_file.md)
```

### Section numbering

Use one style consistently within a file:
- **Plain numbers** for technical deep-dives: `## 1. Section Name`
- **Emoji numbers** for introductory/concept files: `## 1️⃣ Section Name`

Don't mix styles within a single file.

### Writing quality

Each note file should feel like it was written by a senior engineer explaining things to a competent colleague:

- **Production-grade code examples** — real imports, realistic variable names, error handling where it matters. Not `foo`/`bar` toy code.
- **Inline comments that explain "why"** — not what the code does, but why this approach was chosen.
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

- **End of file**: `**Next**: [Part N: Title](next_file.md)` pointing to the next file in sequence
- **Prerequisites**: At the top: `Before reading this, understand X: **[Guide](path/to/guide.md)**`
- **Inline links**: `see [Connection Pooling](../database/05_connection_pooling.md)` when referencing concepts from other files
- Use **relative paths** for all internal links

---

## Directory organization principles

Organize directories by **learning progression**, not alphabetically:

1. **Fundamentals / Basics** — entry-level concepts everyone needs
2. **Core tools / Frameworks** — the main technologies
3. **Infrastructure** — supporting systems (databases, caches, queues)
4. **Architecture / Patterns** — advanced system design
5. **Operations** — testing, deployment, monitoring

Within each directory, files go from foundational to advanced. Sub-directories are for topics that need 3+ files of their own. If a topic needs only one file, keep it in the parent directory.

---

## Parallelizing with subagents

> **Rule**: This section applies only when running in **Claude Code** (where the `Agent` tool is available). In other surfaces, write files sequentially.

> **Rule**: The main agent never calls WebSearch or WebFetch directly. Delegate to a subagent if external context is needed. This keeps the main context clean for coordination and assembly.

### Scout subagent (for structure)

If the topic is current, niche, or fast-moving and native knowledge isn't enough to propose a solid directory structure, launch **one scout subagent** first. It returns a short bullet list — what the topic covers, its main sub-areas, any recent shifts or versioning notes. Use that to propose structure to the user. Skip if native knowledge is clearly sufficient.

### File subagents (for content)

After the user confirms structure, if there are **3+ independent files**, launch one subagent per file in parallel (all Agent tool calls in a single message). Each subagent writes its own `.md` file to disk following this skill's conventions, then returns a short confirmation — not the file contents.

Prompt each subagent with: the topic, target file path, audience, adjacent files for cross-linking, and a pointer to this SKILL.md. If the user wants current information, tell the subagent to use web search for its topic; otherwise it writes from native knowledge.

The main agent handles: launching the scout (if needed), proposing structure, writing root and directory READMEs, launching file subagents, and verifying cross-references at the end.

---

## What NOT to do

- Don't write thin, surface-level notes. Each file should be a genuine deep-dive that teaches something useful.
- Don't use emojis decoratively. Only `1️⃣`–`9️⃣` for section numbering in intro files, and `✅❌⚠️💡` for callouts.
- Don't write pseudocode. Code examples should be complete and runnable (or, for concept-heavy topics, replaced with concrete diagrams/traces).
- Don't create flat structures. If you have 15+ files, organize into directories.
- Don't skip the ASCII tree diagram in the root README.
- Don't forget cross-references. Every file should link to its "next" and mention prerequisites.
