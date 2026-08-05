---
name: note-maker
description: "Scaffold and write layered technical study notes that lead readers from basic concept understanding through a minimal usable implementation to production hardening, operational issues, and practitioner tricks, with structured READMEs, reading paths, examples, and cross-links. Use whenever the user wants to create or extend a knowledge base, study notes, technical reference docs, learning materials, or a documentation repository on any topic."
---

# Technical Notes Scaffold

You are creating a structured technical knowledge base — a curated collection of markdown files that takes a first-time reader from the basic mental model to a useful baseline and then to production-grade awareness.

This is not a wiki dump or a flat list of files. It's an opinionated, layered learning resource designed for engineers. Every file should teach something specific, link to prerequisites, and point to what comes next.

If the user already has an existing notes repo and wants to add to it, read the existing README.md first to understand the current structure, then extend it consistently.

---

## Workflow

When the user provides a topic:

1. **Decide if a scout is needed** — If native knowledge is sparse or the topic is fast-moving, launch a scout subagent for a brief landscape summary (main sub-areas, versioning notes, recent shifts). Otherwise skip.
2. **Design the learning ladder** — Define what a first-time reader already knows, the smallest useful capability they should gain, the production concerns that belong later, and the prerequisite order. Assign each planned file one role: foundation/tutorial, implementation, deep dive, decision guide, or reference. Name the canonical owner of every full schema, implementation, or option set.
3. **Propose structure** — Show the directory tree and planned files with a one-line reader outcome for each. Include a short first-time path and its stop point, then ask: "Does this structure look right? Want to add or remove anything?"
4. **Create root README.md and directory READMEs** — Write these directly; they're structural learning maps, not merely indexes. Use the templates in `references/templates/`.
5. **Write note files** — If running in Claude Code with 3+ independent files, launch subagents in parallel (see Parallelizing section). Otherwise write files sequentially. See `references/example_note.md` for a complete worked example of a finished note.
6. **Run the assembly pass** — Read the first-time path in order as one course. Verify that it teaches concept → minimal usable mechanism → production hardening → operational awareness, introduces no mechanism before its need is visible, provides useful stop points, and does not repeat canonical reference material across files.
7. **Verify files and paths** — Check every internal link, then apply the per-file and path-level checklist under *Final verification*.

If the user asks to add a section to an existing repo, read the current README.md, propose where the new content fits, and update all affected READMEs and cross-references.

---

## Root README.md

When writing a root README, read `references/templates/root_readme.md` for the full template.

Key rules:
- ASCII tree with box-drawing characters (`├──`, `└──`, `│`) and inline directory descriptions
- Category headers in the tree use `── CAPS ──` decorative lines
- Contents section: one markdown table per category, grouped by category
- Reading Order: 2–4 named paths for different experience levels or goals
- At least one path is explicitly for a first-time reader, states the capability reached, and normally reaches a useful stop point within 3–5 files; if it must be longer, add an intermediate milestone before the advanced material
- Every path says who can stop at its first useful milestone and what new requirement justifies continuing
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

**Code-heavy topics** (frameworks, APIs, languages, tools): lead with the smallest runnable example early, make its output visible, then add the production-grade version with real imports, error handling, limits, and operational evidence.

**Concept-heavy topics** (system design, distributed systems theory, architecture patterns): replace code blocks with ASCII diagrams, decision matrices, and annotated tables. The same structural conventions apply — "concrete scenario or worked trace" substitutes for "runnable code example."

### Note role

Choose one primary role before drafting; do not make one file serve as both first tutorial and exhaustive reference:

- **Foundation/tutorial** — builds the mental model and minimum vocabulary; ends at the first useful decision or result.
- **Implementation** — assembles the smallest complete mechanism, then hardens it.
- **Deep dive** — explains one advanced mechanism after its prerequisite and need are already established.
- **Decision guide** — compares known alternatives and routes the reader to canonical implementation notes.
- **Reference** — optimizes for lookup; it may be dense, but no beginner path should require reading it front to back.

### Structure

See `references/example_note.md` for a complete, filled-in example that demonstrates all conventions. The key skeleton:

```
# {Descriptive Title}

> **Who this is for**: {Audience and prerequisites.}

---

## 1. {The problem this solves — a claim, not a label}

{The reader's situation first, then the one-sentence answer, then the mechanism.}

---

## 2. {Next claim}

{Table or deeper dive. Any enumeration over five entries marks its default subset.}

> **Key insight**: {The transferable, non-obvious thing. Exactly one per file — required.}

---

## N. {What breaks, and when not to use this}

{Failure modes with the symptom the reader will actually see, each marked ⚠️. Then the boundary.}

---

**Next**: [Part 2: Title](02_next_file.md)
```

### Section numbering

Use one style consistently within a file:
- **Plain numbers** for technical deep-dives: `## 1. Section Name`
- **Emoji numbers** for introductory/concept files: `## 1️⃣ Section Name`

Don't mix styles within a single file.

### Writing quality

Each note file should feel like it was written by a senior engineer explaining things to a competent colleague. The prose itself is governed by `references/how-we-write-notes.md`. Read it before drafting — it isn't just a list of things to avoid. Its required moves:

- **Audience calibration** and the detail-vs-simplicity balance
- **The collection learning contract** — concept → minimal usable mechanism → production hardening → operational awareness, with file roles, stop points, and one canonical owner per mechanism
- **Lead with the problem**, then the definition — section 1 opens on the reader's situation, not a glossary sentence
- **Work with the model the reader already has** — an analogy to their existing expertise with its boundary stated, and the common misconception named and killed
- **Navigable enumerations** — any list over five entries marks the subset that matters and shows one of them in use
- **A success signal for every instruction** — what the reader observes when it worked, and the tell for the common silent failure
- **Completeness** — the three non-negotiables (what breaks first, when not to use it, how you know it's working) plus whatever else the subject warrants
- **Examples: minimal first, hardened second**
- **Headers that make claims**, exactly one `> **Key insight**:`, `⚠️` reserved for failure modes
- **Currency** and tone

Apply that standard while drafting — don't wait for an audit pass to catch what was missing.

What's specific to authoring:

- **Code examples follow the minimal-first, hardened-second sequence** from the rules file — the baseline block is deliberately bare, and the hardened block after it carries the real imports, error handling, and a comment per addition naming the failure it prevents. Neither block is `foo`/`bar` toy code.
- **Inline comments that explain "why"** — not what the code does, but why this approach was chosen.
- **Progressive complexity across the collection and the file** — the reading path establishes the baseline before advanced mechanisms; each file then starts at its declared role and adds only the next necessary layer.
- **Evidence over exposition** — prefer the smallest runnable example or concrete trace that proves the claim. Use more code only when it teaches the mechanism; a large self-contained block is not automatically a good first example.
- **Canonical ownership** — keep the full schema, code path, or exhaustive table in one note. Elsewhere, show only the fragment needed for the local teaching point and link to the owner.
- **Production tricks have a reason** — attach every advanced tactic to the failure, scaling limit, review concern, or operational symptom it addresses; do not collect unexplained "best practices."

### Formatting conventions

- **Horizontal rules** (`---`): Separate major sections. Every `## N.` section ends with one.
- **Bold** (`**term**`): Key terms on first introduction. Don't bold the same term twice.
- **Backticks** (`` `code` ``): Function names, variable names, CLI commands, file names.
- **Blockquotes**: For principles, rules, and mental models:
  - `> **Principle**: ...`
  - `> **Rule**: ...`
  - `> **Key insight**: ...` — required, exactly one per file
  - `> **The near-miss**: ...` — the misconception this note corrects, where one genuinely exists
- **Callout markers** (used sparingly, not decoratively):
  - `✅` — correct approach, paired with the `❌` it corrects
  - `❌` — incorrect / anti-pattern
  - `⚠️` — a failure mode or gotcha, and nothing else. A reader returning to the note scans for these to find the landmines, so don't spend the marker on general emphasis.
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

Do not equate file numbering with a usable learning path. The README must identify the shortest first-time route, its intermediate outcome, and the branch where production or specialist material begins.

## Final verification

### Per file

- Section 1 is problem-first, and exactly one `> **Key insight**:` is present.
- Every enumeration longer than five entries marks the default subset and shows one default in use.
- The first example is runnable or a concrete trace with a visible outcome; the hardened example follows it rather than replacing it.
- The note fulfills its declared role and does not pull reference-level detail into a foundation/tutorial.
- Instructions have success and silent-failure signals; the note names what breaks first and when not to use the mechanism.

### Per reading path

Read the first-time path in full prose, in order, and answer after every file:

1. What can the reader now explain, choose, or build?
2. Which new term or mechanism appeared before its need or definition?
3. Did the reader reach a complete useful baseline before production hardening?
4. Is there a clear stop point and a concrete reason to continue?
5. Did another file repeat the canonical owner's full implementation instead of linking to it?

If any answer is unclear, revise the structure or handoff before shipping. Passing the per-file checklist does not compensate for a broken reading path.

---

## Parallelizing with subagents

> **Rule**: This section applies only when running in **Claude Code** (where the `Agent` tool is available). In other surfaces, write files sequentially.

> **Rule**: The main agent never calls WebSearch or WebFetch directly. Delegate to a subagent if external context is needed. This keeps the main context clean for coordination and assembly.

### Scout subagent (for structure)

If the topic is current, niche, or fast-moving and native knowledge isn't enough to propose a solid directory structure, launch **one scout subagent** first. It returns a short bullet list — what the topic covers, its main sub-areas, any recent shifts or versioning notes. Use that to propose structure to the user. Skip if native knowledge is clearly sufficient.

### File subagents (for content)

After the user confirms structure, if there are **3+ independent files**, launch one subagent per file in parallel (all Agent tool calls in a single message). Each subagent writes its own `.md` file to disk following this skill's conventions, then returns a short confirmation — not the file contents.

Prompt each subagent with: the topic, target file path, note role, exact knowledge the reader enters with, capability the reader leaves with, canonical mechanisms this file owns, adjacent files for cross-linking, and a pointer to this SKILL.md plus `references/how-we-write-notes.md`. Explicitly name reference material owned elsewhere that the subagent must link rather than reproduce. Per the currency rule, verify any time-sensitive claim with web search before it goes in the file.

The main agent handles: launching the scout (if needed), designing and proposing the learning ladder, writing READMEs, launching file subagents, and reading the assembled first-time path in full. Subagent confirmations are not evidence that the collection has a coherent difficulty curve.

---

## What NOT to do

- Don't write thin, surface-level notes, but do not force every file to become a deep dive. Give each file enough depth for its declared role and let later notes own later layers.
- Don't open a note with a definition. Section 1 leads with the reader's problem; the definition comes after.
- Don't drop a table of every available option without marking the ones a reader actually reaches for. "Most workflows need only a few" is not a substitute for naming them.
- Don't tell the reader to configure or run something without telling them what success looks like and how the common silent failure shows up.
- Don't reach for an analogy you can't bound. State where it stops holding, or leave it out.
- Don't use emojis decoratively. Only `1️⃣`–`9️⃣` for section numbering in intro files, and `✅❌⚠️💡` for callouts — with `⚠️` reserved for failure modes.
- Don't write pseudocode. Every code block should be complete and runnable, the minimal baseline block included — minimal means fewer concerns, not fewer working lines. For concept-heavy topics, replace code with concrete diagrams or traces.
- Don't begin a concept-heavy note with the full schema or production topology. Show the smallest concrete trace first, then replay it with the failure that requires hardening.
- Don't repeat a full implementation across overview, architecture, reliability, and operations notes. Choose a canonical owner and cross-link it.
- Don't call a collection beginner-friendly because each file has an introductory paragraph. Follow the actual first-time path and verify its cumulative complexity.
- Don't create flat structures. If you have 15+ files, organize into directories.
- Don't skip the ASCII tree diagram in the root README.
- Don't forget cross-references. Every file should link to its "next" and mention prerequisites.
- Don't ship a file that fails any of the three non-negotiables in `references/how-we-write-notes.md`: what breaks first when the reader uses this for real, when *not* to use it, and how they know it's working. The subject-dependent items (limits, cost/security, trade-offs vs. alternatives) can be skipped where they genuinely don't apply — those three can't.
