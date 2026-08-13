---
name: note-maker
description: "Scaffold and write layered technical study notes that teach unfamiliar vocabulary and mechanisms through concrete examples, deliver a minimal correct result before production hardening, and then add operational depth, with structured READMEs, reading paths, examples, and cross-links. Use whenever the user wants to create or extend a knowledge base, study notes, technical reference docs, learning materials, or a documentation repository on any topic."
---

# Technical Notes Scaffold

You are creating a structured technical knowledge base — a curated collection of markdown files that takes a first-time reader from the basic mental model to a useful baseline and then to production-grade awareness.

This is not a wiki dump or a flat list of files. It's an opinionated, layered learning resource designed for engineers. Every file should teach something specific, link to prerequisites, and point to what comes next.

If the user already has an existing notes repo and wants to add to it, read the existing README.md first to understand the current structure, then extend it consistently.

---

## Workflow

When the user provides a topic:

1. **Decide if a scout is needed** — If native knowledge is sparse or the topic is fast-moving, launch a scout subagent for a brief landscape summary (main sub-areas, versioning notes, recent shifts). Otherwise skip.
2. **Design the learning ladder** — Define what a first-time reader already knows, the first correct thing they can run or trace, the explanation that lets them restate why it works, and the production concerns that belong later. Order paths **do → understand → harden**; every path reaches a runnable result or concrete worked outcome within its first two entries. Assign each planned file one role: foundation/tutorial, implementation, deep dive, decision guide, or reference. Name the canonical owner of every full schema, implementation, or option set.
3. **Propose structure** — Show the directory tree and planned files with a one-line reader outcome for each. Include a short first-time path, the working result reached by entry two, and its stop point, then ask: "Does this structure look right? Want to add or remove anything?"
4. **Create root README.md and directory READMEs** — Write these directly; they're structural learning maps, not merely indexes. Use the templates in `references/templates/`.
5. **Write note files** — Read `references/how-we-write-notes.md` before drafting and use `references/example_note.md` as the concrete shape. If running in Claude Code with 3+ independent files, launch subagents in parallel (see *Parallelizing with subagents*). Otherwise write files sequentially.
6. **Run the assembly pass** — Read the first-time path in order as one course. Verify that it delivers a working baseline before hardening, grounds every new term locally, explains each mechanism through the problem it solves, provides useful stop points, and does not repeat canonical reference material across files.
7. **Verify files and paths** — Check every internal link, run `python <skill-directory>/scripts/validate_notes.py <note paths or directories>`, then complete the manual checklist under *Final verification*. Resolve `<skill-directory>` to the directory containing this `SKILL.md`. A clean mechanical check does not prove that the note teaches.

If the user asks to add a section to an existing repo, read the current README.md, propose where the new content fits, and update all affected READMEs and cross-references.

---

## Root README.md

When writing a root README, read `references/templates/root_readme.md` for the full template.

Key rules:
- ASCII tree with box-drawing characters (`├──`, `└──`, `│`) and inline directory descriptions
- Category headers in the tree use `── CAPS ──` decorative lines
- Contents section: one markdown table per category, grouped by category
- Reading Order: 2–4 named paths for different experience levels or goals
- At least one path is explicitly for a first-time reader, states the capability reached, and produces a runnable result or concrete worked outcome within its first two entries
- Every path says who can stop at its first useful milestone and what new requirement justifies continuing
- Paths follow **do → understand → harden**; if a path revisits an earlier note for depth, say so explicitly
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

**Code-heavy topics** (frameworks, APIs, languages, tools): put the smallest correct end-to-end example in *The short version*, make its output visible, explain why it works, then add the production-grade version with real imports, error handling, limits, and operational evidence.

**Concept-heavy topics** (system design, distributed systems theory, architecture patterns): put one concrete worked trace with real values in *The short version*. Use diagrams, decision matrices, and annotated tables only after the instance has made the abstraction necessary.

### Note role

Choose one primary role before drafting; do not make one file serve as both first tutorial and exhaustive reference:

- **Foundation/tutorial** — builds the mental model and minimum vocabulary; ends at the first useful decision or result.
- **Implementation** — assembles the smallest complete mechanism, then hardens it.
- **Deep dive** — explains one advanced mechanism after its prerequisite and need are already established.
- **Decision guide** — compares known alternatives and routes the reader to canonical implementation notes.
- **Reference** — optimizes for lookup; it may be dense, but no beginner path should require reading it front to back.

### Structure

See `references/example_note.md` for a complete, filled-in example that demonstrates all conventions. The key skeleton:

````markdown
# {Descriptive Title}

> **Who this is for**: {Audience only; prerequisites do not gate the payoff.}

## The short version

{2–4 sentences: the problem, the mental model, and why the inputs are sufficient.
Gloss every domain term at first use.}

**What you need ({N} things):**

1. {Concrete input}
2. {Concrete input}

**The code:**

```{lang}
{10–25 runnable, minimal-but-correct lines with visible output}
```

**Success signal:** {Exact output, status, or observation.}

**Not handled yet:** [{Deferred production concern}](#later-section), ...

---

## 1. {The problem this solves — a claim, not a label}

{Concrete situation first. Show the world without the mechanism, its consequence,
then the one-sentence answer. Introduce the mechanism with an inline gloss.}

Before going deeper, it helps to know X: **[Guide](path/to/guide.md)**.

---

## 2. {Next claim}

{Table or deeper dive. Any enumeration over five entries marks its default subset.}

> **Key insight**: {The transferable, non-obvious thing. Exactly one per file — required.}

> **Production:** {Hardening that is required before shipping but skippable while learning.}

> **Edge case:** {Specialist material to read only when this condition occurs.}

---

## N. {What breaks, and when not to use this}

{Failure modes with the symptom the reader will actually see, each marked ⚠️. Then the boundary.}

---

**Next**: [Part 2: Title](02_next_file.md)
````

The short-version block is mandatory for every actionable note. It is a result, not an abstract or table of contents: a cold reader can run the code or follow the worked trace, observe the stated result, and explain the mechanism in plain language. Keep it to 40 lines and end it by line 80; the first runnable code must appear by line 80 or 15% of the file, whichever is sooner. For a conceptual note, replace **The code** with **Worked example** and show named actors, real values, a transition, and an outcome.

Prerequisites are advisory and come after the short version. If the short version needs one prerequisite to make sense, supply one sentence of inline context instead of sending the reader away.

### Section numbering

Use one style consistently within a file:
- **Plain numbers** for technical deep-dives: `## 1. Section Name`
- **Emoji numbers** for introductory/concept files: `## 1️⃣ Section Name`

Don't mix styles within a single file.

### Writing quality

Each note file should feel like it was written by a senior engineer explaining things to a competent colleague. The prose itself is governed by `references/how-we-write-notes.md`. Read it before drafting — it isn't just a list of things to avoid. Its required moves:

- **Audience calibration** and the detail-vs-simplicity balance
- **The collection learning contract** — concept → minimal usable mechanism → production hardening → operational awareness, with file roles, stop points, and one canonical owner per mechanism
- **Ground vocabulary locally** — expand acronyms and give every domain term a short "what kind of thing is this?" gloss at first use in this note, including inside *The short version*; links provide depth, never the only definition
- **Introduce mechanisms through their need** — show the world without the mechanism and the consequence before defining it; for security controls, walk through the attack before stating the defense
- **Concrete before abstract** — put one instance with real values before the definition table, taxonomy, full schema, or topology
- **Work with the model the reader already has** — an analogy to their existing expertise with its boundary stated, and the common misconception named and killed
- **Navigable enumerations** — any list over five entries marks the subset that matters and shows one of them in use
- **A success signal for every instruction** — what the reader observes when it worked, and the tell for the common silent failure
- **Completeness** — the three non-negotiables (what breaks first, when not to use it, how you know it's working) plus whatever else the subject warrants
- **Examples: minimal first, hardened second**
- **Headers that make claims**, exactly one `> **Key insight**:`, `⚠️` reserved for failure modes
- **Currency** and tone

Apply that standard while drafting — don't wait for an audit pass to catch what was missing.

What's specific to authoring:

- **No hardening before the baseline** — caching, rotation, retries, pooling, discovery indirection, emergency hooks, observability, and failure taxonomies come only after the first end-to-end result. Delete everything after that result: what remains must still be a correct, usable baseline.
- **Simplify the operational, never the correctness-critical** — the baseline may defer caching, retries, rotation, metrics, granular errors, config indirection, and dependency injection. It never defers algorithm/cipher pinning, issuer/audience/freshness checks, constant-time secret comparison, TLS verification, parameterized queries, or keeping secrets out of logs. Read the full rule in `references/how-we-write-notes.md` before choosing omissions.
- **Carry a deferral contract** — every short version ends with **Not handled yet**, naming and linking every production concern it omits. A minimal example without that list is not publishable.
- **Code examples follow the minimal-first, hardened-second sequence** — the baseline is small and correct; the hardened block after it carries the real imports, error handling, and a comment per addition naming the failure it prevents. Neither block is `foo`/`bar` toy code.
- **Inline comments that explain "why"** — not what the code does, but why this approach was chosen.
- **Progressive complexity across the collection and the file** — the reading path establishes the baseline before advanced mechanisms; each file then starts at its declared role and adds only the next necessary layer.
- **The load-bearing example must teach** — after showing the runnable baseline, explain the mechanism and consequence until a new reader can restate why it works. A code block proves execution, not understanding.
- **The final composition check runs as shown** — execute it in the documented environment and show the observed output. A comment saying that a real test needs different connections, services, fixtures, or synchronization is an admission that the block is a sketch; supply that setup or narrow the claim.
- **Canonical ownership** — keep the full schema, code path, or exhaustive table in one note. Elsewhere, show only the fragment needed for the local teaching point and link to the owner.
- **Production tricks have a reason** — attach every advanced tactic to the failure, scaling limit, review concern, or operational symptom it addresses; do not collect unexplained "best practices."

### Density and altitude budgets

- *The short version* is at most 40 lines and ends by line 80.
- Runnable code appears by line 80 or 15% of the note, whichever comes first; conceptual notes place their concrete worked trace under the same budget.
- Split a note over 500 lines, or add `<!-- length-justification: ... -->` near the top with the concrete reason it must remain one file.
- Hardening may occupy most of a note, but all of it follows the baseline.
- Use `> **Core:**` for material the learning path cannot skip, `> **Production:**` for pre-ship hardening, and `> **Edge case:**` for conditional specialist material.
- Rules and callouts are conclusions. Write at least one paragraph explaining mechanism or consequence for every two `> **Rule:**`, `⚠️`, `❌`, or `✅` markers in a teaching note.

### Formatting conventions

- **Horizontal rules** (`---`): Separate major sections. Every `## N.` section ends with one.
- **Bold** (`**term**`): Key terms on first introduction. Don't bold the same term twice.
- **Backticks** (`` `code` ``): Function names, variable names, CLI commands, file names.
- **Blockquotes**: For principles, rules, and mental models:
  - `> **Principle**: ...`
  - `> **Rule**: ...`
  - `> **Key insight**: ...` — required, exactly one per file
  - `> **The near-miss**: ...` — the misconception this note corrects, where one genuinely exists
  - `> **Core:** ...` — required to understand the baseline
  - `> **Production:** ...` — required before shipping, skippable while learning
  - `> **Edge case:** ...` — conditional material to read only when its condition occurs
- Place rules and callouts after the explanation that earns them; never open a mechanism with a prescription whose reason has not appeared.
- **Callout markers** (used sparingly, not decoratively):
  - `✅` — correct approach, paired with the `❌` it corrects
  - `❌` — incorrect / anti-pattern
  - `⚠️` — a failure mode or gotcha, and nothing else. A reader returning to the note scans for these to find the landmines, so don't spend the marker on general emphasis.
  - `💡` — tip
- **Markdown tables**: For feature comparisons, concept summaries, decision matrices.
- **ASCII diagrams**: For architecture, data flow, and layered systems. Use box-drawing characters: `┌ ─ ┐ │ └ ┘ ├ ┤ ┬ ┴ ┼ → ↓ ↑ ←`

### Cross-referencing

- **End of file**: `**Next**: [Part N: Title](next_file.md)` pointing to the next file in sequence
- **Prerequisites**: Advisory and placed after *The short version*: `For more background on X, see **[Guide](path/to/guide.md)**`
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

## Parallelizing with subagents

> **Rule**: This section applies only when running in **Claude Code** (where the `Agent` tool is available). In other surfaces, write files sequentially.

> **Rule**: The main agent never calls WebSearch or WebFetch directly. Delegate to a subagent if external context is needed. This keeps the main context clean for coordination and assembly.

### Scout subagent (for structure)

If the topic is current, niche, or fast-moving and native knowledge isn't enough to propose a solid directory structure, launch **one scout subagent** first. It returns a short bullet list — what the topic covers, its main sub-areas, any recent shifts or versioning notes. Use that to propose structure to the user. Skip if native knowledge is clearly sufficient.

### File subagents (for content)

After the user confirms structure, if there are **3+ independent files**, launch one subagent per file in parallel (all Agent tool calls in a single message). Each subagent writes its own `.md` file to disk following this skill's conventions, then returns a short confirmation — not the file contents.

Prompt each subagent with: the topic, target file path, note role, exact knowledge the reader enters with, capability the reader leaves with, canonical mechanisms this file owns, adjacent files for cross-linking, and a pointer to this `SKILL.md`, `references/how-we-write-notes.md`, and `references/example_note.md`. Require the short-version contract, local term grounding, problem-before-mechanism explanations, the never-defer safety list, an actually executed final integration check, and the restatement test explicitly; do not assume a pointer alone will make these survive parallel drafting. Name reference material owned elsewhere that the subagent must link rather than reproduce. Per the currency rule, verify any time-sensitive claim with web search before it goes in the file. Each subagent runs both its displayed code/integration commands and `scripts/validate_notes.py` on its file before returning.

The main agent handles: launching the scout (if needed), designing and proposing the learning ladder, writing READMEs, launching file subagents, and reading the assembled first-time path in full. Subagent confirmations are not evidence that the collection has a coherent difficulty curve.

---

## What NOT to do

- Don't write thin, surface-level notes, but do not force every file to become a deep dive. Give each file enough depth for its declared role and let later notes own later layers.
- Don't remove technical precision, source or RFC citations, failure modes, CVE context, or useful anti-patterns in the name of simplicity. Reorder them after the baseline and explain their cause.
- Don't open a note with a definition. Section 1 leads with the reader's problem; the definition comes after.
- Don't use a term before grounding it locally, and don't make a cross-link carry the only definition.
- Don't state a security defense before walking through the adversary's move that makes it necessary.
- Don't lead with a table, taxonomy, schema, or topology when one concrete instance can give it meaning first.
- Don't drop a table of every available option without marking the ones a reader actually reaches for. "Most workflows need only a few" is not a substitute for naming them.
- Don't tell the reader to configure or run something without telling them what success looks like and how the common silent failure shows up.
- Don't reach for an analogy you can't bound. State where it stops holding, or leave it out.
- Don't use emojis decoratively. Only `1️⃣`–`9️⃣` for section numbering in intro files, and `✅❌⚠️💡` for callouts — with `⚠️` reserved for failure modes.
- Don't write pseudocode. Every code block should be complete and runnable, the minimal baseline block included — minimal means fewer concerns, not fewer working lines. For concept-heavy topics, replace code with concrete diagrams or traces.
- Don't call a block an integration test while explaining in prose that its database, connection, service, fixture, or concurrency setup cannot execute it as written.
- Don't begin a concept-heavy note with the full schema or production topology. Show the smallest concrete trace first, then replay it with the failure that requires hardening.
- Don't repeat a full implementation across overview, architecture, reliability, and operations notes. Choose a canonical owner and cross-link it.
- Don't call a collection beginner-friendly because each file has an introductory paragraph. Follow the actual first-time path and verify its cumulative complexity.
- Don't create flat structures. If you have 15+ files, organize into directories.
- Don't skip the ASCII tree diagram in the root README.
- Don't forget cross-references. Every file links to its next step; relevant prerequisites remain advisory and appear only after the short version.
- Don't ship a file that fails any of the three non-negotiables in `references/how-we-write-notes.md`: what breaks first when the reader uses this for real, when *not* to use it, and how they know it's working. The subject-dependent items (limits, cost/security, trade-offs vs. alternatives) can be skipped where they genuinely don't apply — those three can't.

---

## Final verification

Run `python <skill-directory>/scripts/validate_notes.py <note paths or directories>` first. Then read each teaching note as a cold reader and check every item below. Anything unchecked is a defect, not a preference.

### Per note

- [ ] *The short version* is present, no longer than 40 lines, and ends by line 80.
- [ ] **What you need** enumerates and counts the minimal concrete inputs, and the prose explains why those inputs are sufficient.
- [ ] The short-version code actually runs and produces its exact **Success signal**, or the conceptual worked example has real values and a visible outcome.
- [ ] **Not handled yet** names every deferred production concern and links each one forward.
- [ ] No correctness- or security-critical parameter from the never-defer list was simplified away.
- [ ] No caching, rotation, retries, pooling, discovery indirection, metrics, or failure taxonomy appears before the end-to-end baseline.
- [ ] The delete-everything-after-the-baseline test passes: what remains is correct, usable, and self-sufficient.
- [ ] Prerequisites appear after the short version, are advisory, and are not the only definition of a term.
- [ ] Every new acronym and domain term is grounded at first use in this note, including the short version.
- [ ] Every introduced mechanism first shows the problem and consequence it solves; every security defense walks through the adversary's move before stating the rule.
- [ ] A real instance appears before any abstract table, taxonomy, schema, or topology.
- [ ] Rules and `⚠️`/`❌`/`✅` callouts follow explanations; there is at least one mechanism-or-consequence paragraph per two prescriptive markers.
- [ ] `> **Core:**`, `> **Production:**`, and `> **Edge case:**` make the applicable altitude visible.
- [ ] The note is under 500 lines or contains an explicit `<!-- length-justification: ... -->`.
- [ ] Section 1 is problem-first; section headers make claims; exactly one `> **Key insight**:` is present.
- [ ] Every instruction has a success signal and silent-failure tell; the note names what breaks first and when not to use the mechanism.
- [ ] The displayed integration or end-to-end check was executed exactly as shown; its dependencies and concurrency setup are present, and its observed output matches the stated success signal.
- [ ] Restatement test: a competent engineer new to the subject could explain the mechanism to a colleague in their own words, not merely recite its rules.

### Per reading path

- [ ] A runnable result or concrete worked outcome appears within the first two entries.
- [ ] The path reads **do → understand → harden**, with any deliberate revisit named explicitly.
- [ ] After every file, the reader can state what they can now explain, choose, or build.
- [ ] No term or mechanism appears before its need and local definition.
- [ ] The reader reaches a complete useful baseline before production hardening, with a clear stop point and concrete reason to continue.
- [ ] Full implementations and option sets appear only in their canonical owner; other notes link instead of repeating them.
