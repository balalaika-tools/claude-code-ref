---
name: note-maker
description: "Create and extend layered Markdown technical study notes with concrete examples, explicit learning paths, cross-references, and production depth. Use whenever the user wants to create or extend a knowledge base, study notes, technical reference docs, learning materials, or a documentation repository on any topic."
---

# Technical Notes Scaffold

You are creating a structured technical knowledge base — a curated collection of markdown files that takes a first-time reader from the basic mental model to a useful baseline and then to production-grade awareness.

This is not a wiki dump or a flat list of files. It's an opinionated, layered learning resource designed for engineers. Every file should teach something specific, link to prerequisites, and point to what comes next.

New standalone collections default to plain Markdown with a root `README.md` as the canonical
learning map. Do not add a documentation framework, site generator, publishing workflow, or
dependency solely to present the notes. When extending an existing repository, preserve its current
layout and conventions without making site infrastructure part of this skill's output.

---

## Workflow

When the user provides a topic:

1. **Decide if a scout is needed** — If native knowledge is sparse or the topic is fast-moving, launch a scout subagent for a brief landscape summary (main sub-areas, versioning notes, recent shifts). Otherwise skip.
2. **Write the curriculum contract** — Read `references/curriculum-contract.md`. Define the audience, named paths, entry and exit capability of every path step, prerequisite edges, and one canonical owner for every core mechanism. Record whether each mechanism must be `mentioned`, `defined`, `explained`, `demonstrated`, or `operationalized`; a beginner-path mechanism normally reaches at least `demonstrated` in its owner. Persist the plan at `<collection>/_meta/learning_contract.json`; this is contributor metadata and stays out of learner navigation.
3. **Design the learning ladder** — Define the first correct thing the reader can run or trace, the explanation that lets them restate why it works, and the production concerns that belong later. Order paths **do → understand → harden**, but treat execution and understanding as separate payoffs: within the first two entries the reader both observes a concrete result and explains the state transition that produced it. Assign every file one role. A deep dive cannot be the first canonical owner of a core beginner-path mechanism. Build an example-coverage map and a teach-back prompt for each core owner.
4. **Propose structure** — Show the directory tree and planned Markdown files with a one-line reader outcome for each. Include the root `README.md`, section `README.md` files, the first-time path, its execution payoff, its separate understanding payoff, and its stop point, then ask: "Does this structure look right? Want to add or remove anything?"
5. **Create the collection and indexes** — After the user confirms the structure, create the root learning map, section indexes, and approved note files. For an existing or non-empty collection, preserve its layout and naming conventions. Do not introduce a site generator, documentation dependency, or publishing workflow unless the user separately asks for one.
6. **Write and gate the foundation path sequentially** — Read `references/how-we-write-notes.md` and use `references/example_note.md` as the concrete shape. Read `references/example-selection.md` for structured or interaction-shaped mechanisms. Write beginner-path notes in dependency order even when subagents are available. After each note, run its teach-back using only that note and earlier path entries. Do not draft production, operations, or ecosystem breadth until the complete foundation path passes both payoff gates.
7. **Write independent later material** — Only after the foundation gate passes, parallelize genuinely independent implementation, reliability, operations, decision, or reference notes. Every author receives the relevant curriculum-contract entries, not merely a filename and generic house style.
8. **Run the assembly pass** — Read every named path in order. Verify both payoffs, prerequisite closure, coverage levels, stop points, canonical ownership, and concrete carriers. Re-run teach-back for each core mechanism without borrowing from later notes or outside knowledge.
9. **Execute and record examples** — Run every block or composed setup described as runnable, copyable, integration, test, or end-to-end. Record command, environment, exit status, and observed output in `<collection>/_meta/example_verification.json`. If execution is unsafe or unavailable, narrow the claim to an explanatory excerpt and state the unverified dependency; never verify a runnable claim by inspection alone.
10. **Run an independent release gate** — When `note-reviewer` or an equivalent independent evaluator is available, have it audit the assembled first-time path and example evidence without giving it the intended verdict. Remediate all `FIX-CRITICAL` and `FIX-HIGH` findings in newly authored material, rerun affected examples, and repeat the gate. For edits to pre-existing notes, preserve the review/approval boundary requested by the user.
11. **Verify each gate separately** — Check relative links, run `python3 <skill-directory>/scripts/validate_notes.py <note paths or directories>`, and treat its result as structural validation only. Then run `python3 <skill-directory>/scripts/validate_learning_contract.py <collection>` and `python3 <skill-directory>/scripts/validate_example_verification.py <collection>`. If any semantic or execution gate was unavailable, report it explicitly; never collapse them into one `PASS`.

If the user asks to add a section to an existing repo, read the current landing page, propose where
the new content fits, and update all affected indexes, navigation, and cross-references.

---

## Collection landing page

The root `README.md` is the canonical learning map. Read
`references/templates/root_readme.md` for the full template.

Key rules:
- After the short introduction, lead with **Start here** choices organized by reader goal and
  visible outcome; do not make a first-time reader decode the taxonomy before choosing an entry
- Follow with a reader-oriented **Contents** overview by area, not a filesystem tree
- Use two navigation levels: the canonical landing page lists sections and routes to their indexes;
  each section index owns the detailed list of notes in that section
- Do not duplicate every leaf note on the canonical landing page when it already appears in a
  section index; learning paths may still link directly to selected leaf notes
- Use compact grouped Area / Covers / Start here tables for the area overview
- Keep directory layout out of the landing page unless it communicates information that the
  navigation cannot; if included, put a small plain tree in a secondary `Repository layout` section
- Group the Contents overview into a few meaningful categories so the complete collection remains
  discoverable without turning the landing page into an exhaustive catalog
- Learning paths: 2–4 named paths for different experience levels or goals
- At least one path is explicitly for a first-time reader, states the capability reached, and produces a runnable result or concrete worked outcome within its first two entries
- Every path says who can stop at its first useful milestone and what new requirement justifies continuing
- Paths follow **do → understand → harden**; if a path revisits an earlier note for depth, say so explicitly
- For badge hex codes and logo names, read `references/badges.md`
- Omit the `*Last updated*` line unless the user asks for it — it goes stale immediately

---

## Section index

Every content directory uses `README.md`. These files are **intentionally minimal** — just enough to orient the reader
within that section while listing its child sections and notes in useful reading order. They own
the detailed catalog that the landing page deliberately omits; do not repeat the landing page's
cross-collection area overview.

Read `references/templates/directory_readme.md` for the template.

---

## Note Files

These are the actual content. Each file teaches one focused topic.

### File naming

Numbered with zero-padded prefix: `01_topic_name.md`, `02_topic_name.md`. Numbers indicate reading order within a directory. Use lowercase with underscores.

### Note role

Choose one primary role before drafting; do not make one file serve as both first tutorial and exhaustive reference:

- **Foundation** — builds one central mental model and minimum vocabulary through a concrete trace; execution is optional.
- **Tutorial** — guides the reader through the smallest complete runnable result, then explains it.
- **Implementation** — assembles the smallest complete mechanism, then hardens it.
- **Deep dive** — explains one advanced mechanism after its prerequisite and need are already established.
- **Decision guide** — compares known alternatives and routes the reader to canonical implementation notes.
- **Reference** — optimizes for lookup; it may be dense, but no beginner path should require reading it front to back.

### Open with a role-appropriate payoff

Do not impose `## The short version` or one universal mini-tutorial on every file. Give the reader
an early payoff that fits the declared role:

| Note role | Opening payoff |
|---|---|
| Foundation | A concrete situation, faithful trace, and the first correct mental model. |
| Tutorial | The smallest runnable path, bounded inputs, visible output, and the explanation that makes it intelligible. |
| Implementation | The smallest runnable path, bounded inputs, and visible output. |
| Deep dive | The failure, constraint, or surprising behavior that makes the deeper mechanism necessary. |
| Decision guide | A named decision, the few criteria that change it, and an initial recommendation. |
| Reference | Scope, lookup map, defaults, or common subset; no forced tutorial. |

Use whatever heading makes the payoff clear: `Quick start`, `Worked example`, a claim-specific
heading, or no dedicated heading when the opening prose already delivers it. Exact labels such as
`What you need`, `Success signal`, and `Not handled yet` are optional. Their information remains
required only when it applies: bound inputs for an action, show its observable success, and name
relevant production omissions near a deliberately minimal example.

For code-heavy tutorial or implementation notes, show the smallest correct end-to-end example,
make its output visible, explain why it works, then add hardening. For concept-heavy foundation
notes, use a concrete worked trace before abstract tables. Deep dives, decision guides, and
references do not recreate a baseline already owned elsewhere merely to satisfy an opening form.

See `references/example_note.md` for one complete **tutorial** example, not a universal
template. A general teaching-note skeleton is:

````markdown
# {Descriptive Title}

> **Who this is for**: {Audience only; prerequisites do not gate the payoff.}

{Optional genuine prerequisite; keep optional background advisory.}

## {Role-appropriate opening claim or payoff}

{A concrete situation, runnable baseline, motivating failure, decision scenario, or lookup map.
Include bounded inputs and an observable result when the reader is asked to act.}

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

The opening must earn attention before setup detail, exhaustive taxonomy, or hardening, but it has
no fixed heading, field order, line count, or percentage threshold. A title plus a generic summary
does not count. Genuine prerequisites may precede the payoff when the intended audience cannot
proceed without them; keep optional background advisory and brief.

### Section numbering

Use one style consistently within a file:
- **Plain numbers** for technical deep-dives: `## 1. Section Name`
- **Emoji numbers** for introductory/concept files: `## 1️⃣ Section Name`

Don't mix styles within a single file.

### Writing quality

Each note file should feel like it was written by a senior engineer explaining things to a competent colleague. The prose itself is governed by `references/how-we-write-notes.md`. Read it before drafting — it isn't just a list of things to avoid. Its required moves:

- **Audience calibration** and the detail-vs-simplicity balance
- **The collection learning contract** — concept → minimal usable mechanism → production hardening → operational awareness, with file roles, stop points, and one canonical owner per mechanism
- **Ground vocabulary locally** — expand acronyms and give every domain term a short "what kind of thing is this?" gloss at first use in this note, including inside the opening payoff; links provide depth, never the only definition
- **Introduce mechanisms through their need** — show the world without the mechanism and the consequence before defining it; for security controls, walk through the attack before stating the defense
- **Concrete before abstract** — put one instance with real values before the definition table, taxonomy, full schema, or topology
- **Work with the model the reader already has** — an analogy to their existing expertise with its boundary stated, and the common misconception named and killed
- **Navigable enumerations** — any list over five entries marks the subset that matters and shows one of them in use
- **A success signal for every instruction** — what the reader observes when it worked, and the tell for the common silent failure
- **Completeness** — the three non-negotiables (what breaks first, when not to use it, how you know it's working) plus whatever else the subject warrants
- **Examples: minimal first, hardened second**
- **Concrete carriers at the point of need** — structured and interaction-shaped mechanisms show the smallest faithful policy, config, request/response, query/result, state trace, or decision contrast that makes their behavior inspectable
- **Headers that make claims**, exactly one `> **Key insight**:`, `⚠️` reserved for failure modes
- **Currency** and tone

Apply that standard while drafting — don't wait for an audit pass to catch what was missing.

What's specific to authoring:

- **No hardening before the baseline in notes that own it** — a tutorial or implementation note puts caching, rotation, retries, pooling, discovery indirection, emergency hooks, observability, and failure taxonomies after its first end-to-end result. A deep dive may start from the failure that requires one of these mechanisms when it states or links the baseline it assumes.
- **Simplify the operational, never the correctness-critical** — the baseline may defer caching, retries, rotation, metrics, granular errors, config indirection, and dependency injection. It never defers algorithm/cipher pinning, issuer/audience/freshness checks, constant-time secret comparison, TLS verification, parameterized queries, or keeping secrets out of logs. Read the full rule in `references/how-we-write-notes.md` before choosing omissions.
- **Carry a relevant deferral contract** — when a minimal example omits production concerns that matter to its claim, name them nearby and link forward. `Not handled yet` is an optional label, and irrelevant concerns do not need ceremonial mention.
- **Code examples follow the minimal-first, hardened-second sequence** — the baseline is small and correct; the hardened block after it carries the real imports, error handling, and a comment per addition naming the failure it prevents. Neither block is `foo`/`bar` toy code.
- **Inline comments that explain "why"** — not what the code does, but why this approach was chosen.
- **Progressive complexity across the collection and the file** — the reading path establishes the baseline before advanced mechanisms; each file then starts at its declared role and adds only the next necessary layer.
- **The load-bearing example must teach** — after showing the runnable baseline, explain the mechanism and consequence until a new reader can restate why it works. A code block proves execution, not understanding.
- **Example coverage is semantic, not numeric** — use the internal coverage map to ask which mechanisms need a carrier, not how many examples the note contains. One annotated example may cover several adjacent concepts; a simple definition may need none.
- **Put the carrier beside the explanation it unlocks** — do not count an unrelated opening or end-to-end example as coverage for a later mechanism whose fields, states, or interactions remain invisible.
- **Distinguish excerpts from copyable examples** — a copyable block is complete, valid, and safe. A smaller explanatory excerpt is allowed when labeled, syntactically faithful, locally mapped to an outcome, and free of omitted correctness- or security-critical context; link to the canonical complete owner. Put prose labels outside the fence when its declared language does not support comments: a `json` excerpt must still parse as JSON.
- **The final composition check runs as shown** — execute it in the documented environment and show the observed output. A comment saying that a real test needs different connections, services, fixtures, or synchronization is an admission that the block is a sketch; supply that setup or narrow the claim.
- **Canonical ownership** — keep the full schema, code path, or exhaustive table in one note. Elsewhere, show only the fragment needed for the local teaching point and link to the owner.
- **Production tricks have a reason** — attach every advanced tactic to the failure, scaling limit, review concern, or operational symptom it addresses; do not collect unexplained "best practices."

### Density and altitude budgets

- Put the role-appropriate payoff before setup detail, exhaustive reference material, or hardening that the reader does not yet need. Do not use a universal line or percentage quota.
- Tutorial and implementation notes reach their runnable baseline early; concept notes place the first useful trace near the mechanism it explains. Deep dives, decision guides, and references use their own payoff forms instead of forced code.
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
- **Prerequisites**: Keep optional background advisory. Put a genuine prerequisite near the audience statement only when the intended reader cannot use the note without it.
- **Inline links**: `see [Connection Pooling](../database/05_connection_pooling.md)` when referencing concepts from other files
- Use **relative paths** for all internal links
- Keep authored links as `.md` paths so they work directly in repository source viewers.

### Navigation maintenance

- Treat the root and section `README.md` files as expressions of the learning ladder, not exhaustive
  filesystem dumps.
- Update affected indexes and reading paths in the same change that adds, removes, renames, or
  reorders notes.
- Put the first-time path first, then deeper or reference material.

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

Use subagents only when delegation is available and permitted. Otherwise perform research and write
sequentially in the main agent. Tool brand does not determine the workflow; capability and the
dependency structure do. External research may be delegated to keep the assembly context small, but
the main agent may research directly when delegation is unavailable.

### Scout subagent (for structure)

If the topic is current, niche, or fast-moving and native knowledge isn't enough to propose a solid directory structure, launch **one scout subagent** first when delegation is available; otherwise perform the same primary-source landscape check directly. It returns a short bullet list — what the topic covers, its main sub-areas, and recent shifts or versioning notes. Use that to propose structure to the user. Skip only if native knowledge is clearly sufficient and the subject is stable.

### File subagents (for content)

Never parallelize the notes on a first-time path merely because they are separate files. They share cumulative vocabulary and must be authored and teach-back checked in dependency order. After that path passes, if there are **3+ genuinely independent later files**, launch one subagent per file in parallel. Each subagent writes its own `.md` file and returns a short confirmation.

Prompt each subagent with the topic, path, role, entry knowledge, exit capability, relevant `_meta/learning_contract.json` entries, canonical mechanisms, adjacent files, and required references. Require local grounding, problem-before-mechanism explanation, concrete carriers, the never-defer safety list, an executed integration check when claimed, and evidence-backed teach-back. Each subagent records execution evidence and runs structural validation before returning.

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
- Don't write ambiguous pseudocode or present fragments as runnable. Baseline and copyable blocks must be complete and correct. A deliberately labeled explanatory excerpt may omit irrelevant outer structure, but it must remain syntactically faithful, map to a concrete outcome, preserve every correctness- and security-critical property relevant to its claim, and link to the canonical complete owner. For concept-heavy topics, use the matching concrete trace instead of forcing code.
- Don't call a block an integration test while explaining in prose that its database, connection, service, fixture, or concurrency setup cannot execute it as written.
- Don't begin a concept-heavy note with the full schema or production topology. Show the smallest concrete trace first, then replay it with the failure that requires hardening.
- Don't repeat a full implementation across overview, architecture, reliability, and operations notes. Choose a canonical owner and cross-link it.
- Don't call a collection beginner-friendly because each file has an introductory paragraph. Follow the actual first-time path and verify its cumulative complexity.
- Don't count a title, glossary sentence, warning, or isolated diagram as proof that a core mechanism was taught; compare the achieved coverage level with the curriculum contract.
- Don't let a deep dive become the first canonical owner of a beginner-path concept.
- Don't parallelize an interdependent first-time path; dependency order and teach-back are part of authorship.
- Don't call an example runnable, copyable, integration, test, or end-to-end unless its exact composed command was executed and recorded.
- Don't create flat structures. If you have 15+ files, organize into directories.
- Don't turn the canonical landing page into a decorated filesystem dump. Route readers by topic
  and goal; document repository layout only when it adds useful contributor information.
- Don't forget cross-references. Every file links to its next step; optional background remains advisory, while genuine prerequisites may be stated briefly near the audience contract.
- Don't add, remove, rename, or reorder a note without updating the affected `README.md` indexes and
  reading paths.
- Don't ship a file that fails any of the three non-negotiables in `references/how-we-write-notes.md`: what breaks first when the reader uses this for real, when *not* to use it, and how they know it's working. The subject-dependent items (limits, cost/security, trade-offs vs. alternatives) can be skipped where they genuinely don't apply — those three can't.
- Don't add a site generator, documentation dependency, generated-site directory, or publishing
  workflow unless the user explicitly requests that separate deliverable.

---

## Final verification

Run `python3 <skill-directory>/scripts/validate_notes.py <note paths or directories>` first. Then
read each teaching note as a cold reader and check every item below. Anything unchecked is a defect,
not a preference.

### Per collection

- [ ] The root `README.md` is the canonical learning map and every content directory has a concise
  `README.md` index.
- [ ] Navigation order matches the documented learning paths rather than alphabetical file order.
- [ ] Every learner-facing note is reachable through a section index or named learning path.
- [ ] All internal links are relative, resolve to tracked Markdown files or relevant artifacts, and
  are updated when notes move.

### Per note

- [ ] Every core mechanism reaches the coverage level promised in `_meta/learning_contract.json`; a heading or definition alone is not counted as teaching.
- [ ] A foundation owner supports the six-part evidence-backed teach-back: problem, owned state/decision, actor, named transition/result, misconception boundary, and first failure.
- [ ] No deep dive is the first canonical owner of a core beginner-path mechanism.
- [ ] A foundation note that combines multiple stateful mechanisms either teaches their composition or is split at a real prerequisite/carrier boundary.
- [ ] The opening delivers the payoff appropriate to the note's declared role; it is not merely a generic summary.
- [ ] A tutorial or implementation opening bounds the inputs and shows an observable result; a foundation, deep dive, decision guide, or reference uses the matching payoff form instead of forced code.
- [ ] Any minimal example that omits relevant production concerns names them nearby and links forward, without requiring a particular label.
- [ ] No correctness- or security-critical parameter from the never-defer list was simplified away.
- [ ] In a tutorial or implementation note that owns the runnable path, no caching, rotation, retries, pooling, discovery indirection, metrics, or failure taxonomy appears before the end-to-end baseline.
- [ ] For a note that owns a baseline, the delete-everything-after-that-baseline test passes: what remains is correct, usable, and self-sufficient. A deep dive states or links the baseline it assumes instead of reproducing it.
- [ ] Genuine prerequisites are brief and audience-relevant; optional background is advisory and is not the only definition of a term.
- [ ] Every new acronym and domain term is grounded at first use in this note, including the opening payoff.
- [ ] Every introduced mechanism first shows the problem and consequence it solves; every security defense walks through the adversary's move before stating the rule.
- [ ] A real instance appears before any abstract table, taxonomy, schema, or topology.
- [ ] Every high-leverage mechanism that requires the reader to write, inspect, review, debug, or mentally simulate a structured artifact or interaction has the smallest faithful concrete carrier near its first explanation.
- [ ] Each such carrier maps its important field, value, or transition to an outcome; a changed-input contrast appears when the distinction is non-obvious.
- [ ] No example was added merely to satisfy a section or count; existing examples are reused when they already carry the same semantics, and non-canonical notes use excerpts plus links instead of duplicate full implementations.
- [ ] Rules and `⚠️`/`❌`/`✅` callouts follow explanations; there is at least one mechanism-or-consequence paragraph per two prescriptive markers.
- [ ] `> **Core:**`, `> **Production:**`, and `> **Edge case:**` make the applicable altitude visible.
- [ ] The note is under 500 lines or contains an explicit `<!-- length-justification: ... -->`.
- [ ] Section 1 is problem-first; section headers make claims; exactly one `> **Key insight**:` is present.
- [ ] Every instruction has a success signal and silent-failure tell; the note names what breaks first and when not to use the mechanism.
- [ ] When the note presents an integration or end-to-end check, it was executed exactly as shown; its dependencies and concurrency setup are present, and its observed output matches the stated success signal.
- [ ] Restatement test: a competent engineer new to the subject could explain the mechanism to a colleague in their own words, not merely recite its rules.

### Per reading path

- [ ] An actually executed result or faithful concrete trace appears within the first two entries.
- [ ] Independently, evidence-backed teach-back succeeds within the first two entries.
- [ ] The path reads **do → understand → harden**, with any deliberate revisit named explicitly.
- [ ] After every file, the reader can state what they can now explain, choose, or build.
- [ ] No term or mechanism appears before its need and local definition.
- [ ] The reader reaches a complete useful baseline before production hardening, with a clear stop point and concrete reason to continue.
- [ ] Full implementations and option sets appear only in their canonical owner; other notes link instead of repeating them.
- [ ] Every runnable, copyable, integration, test, or end-to-end claim has matching execution evidence in `_meta/example_verification.json`, or is relabeled as an unverified explanatory excerpt.
- [ ] An independent reviewer evaluated the assembled path without being told the intended verdict; all critical/high findings in newly authored material were remediated and rechecked.
