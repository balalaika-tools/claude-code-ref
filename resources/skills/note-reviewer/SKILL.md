---
name: note-reviewer
description: "Audit a technical notes repository for explanation quality, accuracy, completeness, worked examples, production awareness, and the cold-reader journey from basic concepts to a usable baseline and advanced operations. Produces per-file findings, reading-path findings, and a repo-level missing-note report without editing notes. Use whenever the user wants to audit, review, fact-check, or find learning-curve and coverage gaps in a notes repo or knowledge base."
---

# Notes Repo Auditor

You are auditing a technical notes repository — inspecting `.md` files and producing a report of exactly what needs to change and why. The audit has three required parts:

1. A **per-file pass** grades notes that exist (dimensions 1–5).
2. A **reader-journey pass** follows the named learning paths in order and tests whether a first-time reader reaches a useful baseline before production complexity.
3. A **repo-level gap pass** asks which notes or pedagogical bridges should exist and do not.

A clean result in one pass does not compensate for a failure in another. You do not edit note files or decide whether findings get applied; a human reviews the reports and a fix-agent applies approved changes later.

---

## Orchestration

The repo has several subfolders (e.g. `aws/`, `backend/`, `langfuse/`), each with several `.md` files.

> **Rule**: This section applies only when running in **Claude Code** (where the `Agent` tool is available). Outside Claude Code, audit subfolders one at a time yourself, then run the reader-journey pass and finally the gap pass over the whole tree.

If there are multiple subfolders, launch one subagent per subfolder (all `Agent` tool calls in a single message so they run concurrently). Give each subagent this SKILL.md, the rules file at `references/how-we-write-notes.md`, and its assigned subfolder path. Rules for staying in your lane:

- Read and audit only the `.md` files inside the assigned subfolder. Don't wander into other subfolders — another sub-agent owns those and is working from an identical copy of these instructions.
- Notes in the same subfolder usually share vocabulary and cross-reference each other. Read the whole subfolder together, not file-by-file in isolation, so you catch inconsistencies between files — e.g. the same term defined two different ways in two notes.
- If a subfolder has 30+ files, split it into two passes rather than holding all of it in context at once. Otherwise one pass covers the whole subfolder.
- Write findings to a single audit file mirroring the subfolder's name, e.g. `_audit/aws.audit.md` for `aws/`. Don't touch any other audit file, and don't touch any note file.

Launch the whole-tree reader-journey agent and gap agent alongside the per-subfolder agents. They write different files and must not be merged into a per-folder pass.

### The reader-journey pass is one whole-tree cold read

This pass writes only `_audit/reader_paths.audit.md`. It reads the root and directory READMEs, identifies every explicitly named beginner/first-time/default path, and follows those paths in order. It also follows the shortest task-oriented path when no beginner path exists. Read the **full prose** of every note on the selected path; headers and cross-links are not enough to judge cumulative cognitive load.

For each path, start with only the knowledge promised by its audience statement. After every file, record what the reader can now explain, choose, build, or verify. Do not grant the reader knowledge from later notes, adjacent folders, or your own familiarity with the subject.

### The gap pass is one whole-tree agent, not one per subfolder

Launch it in the same message as the per-subfolder agents — it's read-only and writes only `_audit/gaps.audit.md`, so it can't collide with them. Give it this SKILL.md, the rules file, and the repo root.

It must see the **entire tree at once**, including every subfolder's READMEs and reading paths. That's not an efficiency preference: an absence is only visible against the full picture, and a subfolder-scoped agent will always conclude that its own folder's silence on a topic is someone else's folder's job. Never split this pass by subfolder, and never let a per-subfolder agent write gap findings — a per-file audit that starts speculating about missing files stops being an audit.

To fit a large tree, this agent reads breadth-first rather than every word: every README and index, every file's headers and cross-links, and full prose only where it's chasing a specific suspected gap. Its unit of output is the subfolder, not the file.

---

## The standard you're auditing against

The house style lives in `references/how-we-write-notes.md`. **Read it before auditing anything.** It is the single source of truth for the audience definition, the detail-vs-simplicity balance, the required teaching moves, the completeness questions, currency, and tone — and it is the standard these notes were written to. Don't audit against a paraphrase of it, and don't apply a criterion you can't point to in it.

This skill adds only what's specific to auditing: the calibration anchors below, the per-file checks, the cold-reader journey protocol, the severity ladder, the report formats, the orchestration rules, and the audit-only boundary.

One reminder from that file, because every judgment here rests on it — the reader is **a competent practitioner in the general domain, encountering this specific subject for the first time.** Concretely: a backend engineer reading a note on Langfuse tracing knows what an API, a decorator, and latency are; they do not yet know traces, spans, generations, or scores. If a note assumes the reader already knows the thing it is supposed to be teaching, that's a failure, not an acceptable shortcut.

---

## What you're checking for in each file

Dimensions 1–5 are the per-file pass. Every one of them grades a file that exists. They cannot prove that several individually good files form a usable learning path, and they cannot grade a note that was never written; the reader-journey and gap passes own those questions.

### 1. Explanation craft — the simplicity/fullness balance

Not a completeness check (that's #3), not about whether the note's worked examples reflect production practice (that's #4), and not the structural check on whether tables and lists mark their defaults (that's #5). This dimension is about *prose*: an unmarked option dump inside a table belongs to #5, and gets flagged once, there. A section can contain every fact it needs and still fail here, because *how* it explains something matters as much as *what* it covers. For any concept there's a spectrum from "soundbite" to "reference-manual entry," and most explanations fail by collapsing to one end:

- **Too simple (loses fullness):** easy to read, but leaves the reader unable to actually use the thing. States the effect, skips the mechanism. Uses an analogy and never cashes it out into the real mechanics.
- **Too dense (loses simplicity):** technically accurate, but unreadable on a first pass. Leads with jargon before any intuition is built. Explains one unfamiliar concept by referencing three other unfamiliar concepts. Lists every option/flag with no signal of which ones matter.

**Target:** the balance set out under *The core balance* in the rules file — the correct mental model in plain language first, then the precise mechanism that makes that model actionable. One well-chosen example beats five abstract sentences.

**Calibration examples** (same underlying facts, different craft — use these to anchor your judgment across files):

> *Too simple:* "Redis uses eviction policies to manage memory when it fills up." — states that a thing exists, gives no mechanism, reader can't configure anything from this.
>
> *Too dense:* "Redis implements approximated LRU via a sampling algorithm configurable through maxmemory-policy, selecting from allkeys-lru, volatile-lru, allkeys-lfu, volatile-lfu, allkeys-random, volatile-random, noeviction, and volatile-ttl, each applying eviction across differently scoped keyspaces." — accurate, but front-loads eight options with no signal of which one a reader would actually reach for.
>
> *Right balance:* "When Redis hits its memory limit, it has to evict something. Two decisions matter: which keys are eligible (all of them, or only ones with a TTL set), and which gets picked first (least-recently-used is the sane default). Set both via `maxmemory-policy` — `allkeys-lru` is right for a pure cache; reach for a `volatile-*` variant only if some keys must never be evicted." — model first, mechanism attached, tells the reader what to actually do.

### 2. Outdated content

Anything time-sensitive must be **verified**, not assumed:
- Version numbers, changelogs, "latest" claims
- Deprecated/renamed APIs, SDKs, CLI flags, config keys
- Pricing, quotas, free-tier limits
- "Current best practice" / "recommended way" statements
- Product or service names (these rebrand constantly, especially AWS)
- Anything phrased as "as of [date]" where that date has clearly passed

**Protocol:** for each flagged claim, run a web search, compare the live current state against what the note says, and record the delta with a source and date. Don't rely on training-data knowledge for anything that could have changed — check it.

### 3. Incomplete coverage

Audit against the priority-ordered question list under *Completeness* in the rules file, and carry its priorities into your severity:

- The **three non-negotiables** — what breaks first when the reader uses this for real, when *not* to use it, and how they know it's working. A note missing any one of these is `FIX-HIGH`, however complete it is otherwise, and regardless of its stated scope.
- The **subject-dependent** items — irreversible operations and cost/security exposure, the trade-off against the obvious alternative, limits and quotas. Missing one is `FIX-MED`, and only where the subject genuinely warrants it. Don't flag a missing quota section on a note about a language feature.

A note that only covers the happy path is incomplete even if everything in it is accurate.

### 4. Example quality — does it actually show production-grade practice?

Notes in this repo often include a worked example that combines several tools to solve a real problem — e.g. a RAG pipeline instrumented with OpenTelemetry and Langfuse. That example's job is to show the reader how the pieces genuinely fit together at a production level, not just that each piece individually runs. Check:

- **The example ladder exists.** Before production integration, is there a minimal runnable baseline or, for a concept-heavy note, a small concrete trace with named inputs, state changes, and visible output? A full schema, topology, or 100-line script as the first example is `FIX-MED`; `FIX-HIGH` when the note is the beginner path's only implementation and the reader cannot isolate the baseline mechanism.

- **Real integration, not a sketch.** Does it show how these specific tools actually connect to each other — trace context propagated correctly across the pipeline's steps, correct span/trace hierarchy — or does it just wrap one function in a decorator and call it "instrumented"?
- **The non-obvious tactics.** Does it include the specific moves a practitioner reaches for with *this combination* of tools — the stuff that isn't obvious from reading each tool's docs separately? For a RAG + OTel + Langfuse example: separate spans for retrieval vs. generation, retrieved-document metadata attached to the right span, the Langfuse trace ID correlated with the OTel trace so either tool can be used to debug the other.
- **Current integration guidance, verified.** Does it reflect how these tools are recommended to be combined *today*? This is exactly the kind of guidance that shifts as SDKs evolve — verify via web search, same protocol as #2, aimed at integration patterns rather than plain facts.
- **Production concerns specific to this integration**, not generic ones: what happens to a trace if a pipeline step times out, sampling strategy so tracing overhead doesn't dominate at real volume, what shouldn't end up in trace metadata (raw PII in prompts, full documents when an ID would do).
- **The "why" test.** If someone followed this example and a colleague asked "why did we structure it this way," could they give a real answer — or would they just be repeating steps with no grasp of why it's built that way?

**Calibration example** (same tools, same goal, different production-readiness):

> *Shallow:* wraps a RAG query function in `@observe()` and calls it done. One flat span for the whole call. No distinction between retrieval and generation, no metadata on which documents were retrieved, no link back to any OTel trace already running in the service.
>
> *Production-grade:* separate spans for embedding, retrieval, and generation; retrieved document IDs and scores attached as span metadata; the Langfuse trace ID injected into the OTel span so either system can be used to pivot into the other; sampling configured so trace volume doesn't blow up at scale; explicit note on what not to put in trace metadata.

**Distinction to hold onto:** severity depends on how the note frames the example. If it's explicitly labeled a minimal illustration with a pointer to further reading, a shallow example is a `FIX-MED` at most. If it's the note's main worked example and a reader would reasonably copy it into a real project, treat gaps here as `FIX-HIGH` or higher — the same standard as the note's own explanations, not a discount for being "just an example."

One thing *not* to flag here: a bare minimal block that is immediately followed by a hardened one is the required minimal-first, hardened-second sequence from the rules file, not a shallow example. Judge the pair, not the first block.

### 5. Reader traction — does the note land?

Dimensions 1–4 measure the content. This one measures the reader's experience of it, and it's the dimension a technically flawless note most often fails. Every check is mechanical — verifiable by looking — which makes it cheap to audit and hard to argue with.

- **Opening** — does section 1 lead with the reader's problem, or with a definition? A definitional opening is `FIX-MED`; `FIX-HIGH` if the note never states the problem anywhere.
- **Role discipline** — does a foundation/tutorial stay focused on the mental model and first useful result, or does it turn into an exhaustive reference before the baseline lands? A tutorial/reference collision is `FIX-MED`; `FIX-HIGH` when every beginner route is forced through it.
- **Navigable enumerations** — any table or list over five entries with no marked default subset is `FIX-HIGH`. Name the specific table in the finding. If the note says "you only need a few of these" without naming them, quote that line back — it's the clearest possible version of this defect.
- **Success signal** — does every "configure X / run Y" instruction say what the reader observes on success, plus the tell for the most common silent failure? Missing on a destructive or security-relevant operation is `FIX-CRITICAL`.
- **Misconception left standing** — is there a plausible, specific wrong model a first-time reader would arrive with that the note never addresses? `FIX-MED`. State the misconception in the finding so the fix-agent doesn't invent one.
- **One key insight** — present, transferable, non-obvious? Missing, or merely restating a section's topic sentence, is `FIX-LOW`; say what the real insight should be.
- **Headers as claims** — topic labels rather than answers is one `FIX-LOW` for the whole file, not one per header.
- **`⚠️` spent correctly** — reserved for failure modes, not general emphasis. `FIX-LOW`, and only if it's actually misleading the reader's scan.

Don't apply this dimension to a file whose stated scope is a reference index or a link list. And don't let its mechanical checks turn into six findings per file — the "don't manufacture findings" rule in *Ground rules* binds here hardest, because these checks are the easiest in the skill to run up a score with.

---

## The reader-journey pass — does the collection teach in the right order?

The per-file pass asks whether each note is good. This pass asks whether the reader can actually move through them. Audit every selected path against the four-layer contract in `references/how-we-write-notes.md`: concept → minimal usable mechanism → production hardening → operational awareness.

### Cold-reader protocol

For each file in path order, answer without borrowing from later material:

1. **Entry contract** — what does the path claim the reader already knows?
2. **Exit capability** — what can the reader now explain, choose, build, or verify?
3. **First unexplained dependency** — which term, mechanism, or invariant appears before its need and plain-language model?
4. **Complexity step** — did the file add one necessary layer, or jump from concept to several production mechanisms at once?
5. **Useful baseline** — has the reader completed the smallest real system before alternatives, scaling, recovery, or exhaustive reference material?
6. **Stop point** — can a reader whose needs are already met stop confidently, and is the reason to continue concrete?
7. **Canonical ownership** — is a full schema, implementation, or option set repeated instead of linked to its owner?
8. **Production continuation** — does the collection provide a clear continuation from this path to failure modes, operational symptoms, limits, recovery, and the tricks that address them, without forcing those details into the foundation?

Run a teach-back test at each milestone: can the reader state the problem, default mechanism, visible success, first real failure, and reason for the next layer in plain language? If not, identify the earliest file where the chain broke. Do not blame a later note for a prerequisite the earlier path failed to establish.

### Reader-journey severity

- `FIX-HIGH`: the path never reaches its promised useful capability, requires an advanced mechanism before any complete baseline, or has no first-time route at all.
- `FIX-MED`: the path works only after rereading, detouring into references, carrying several unexplained concepts, or reading duplicated full implementations.
- `FIX-LOW`: the path is coherent but its audience, outcome, milestone, or stop-point labeling is weak.

### Output — `_audit/reader_paths.audit.md`

Use one block per audited path:

```
# <README path> :: <path name>
Outcome: <capability the path promises>
Files: <ordered relative paths>
Summary: N high, N med, N low

FIX-HIGH: <earliest break in the path> — <specific structural or file change>.
FIX-MED: <cognitive-load, bridge, role, or duplication problem> — <specific correction>.
FIX-LOW: <path-labeling problem> — <specific correction>.
NO-ACTION: <why the path progresses cleanly, only when worth recording>.
```

Every finding names the earliest responsible README or note and the correction. Do not copy per-file findings unless their reader harm only becomes visible in sequence. If the repo defines no named learning paths, emit one `FIX-HIGH` block against the root README instead of inventing a path silently.

---

## The gap pass — which notes or learning bridges should exist and don't

Everything above asks whether existing files and paths work. This asks the question no per-file check can: **given what's already here, what concept or pedagogical bridge is the reader expected to cross without a note capable of teaching it?**

A folder can pass the per-file audit completely clean and still have a hole in it. If `langfuse/` covers tracing and scoring thoroughly but never covers evals — while three of its notes casually lean on evals as if the reader already has them — every file earns `NO-ACTION` and the hole is invisible. Nothing was there to grade.

### Evidence, strongest first

Work from the repo's own text outward. The order matters: it's what keeps this pass an audit rather than a curriculum wishlist.

1. **Leaned-on but never explained** (strongest, and the signal you should be spending most of your effort on). A concept that notes reference, build on, or assume as a prerequisite, with no note that teaches it. Tells to look for:
   - A term used in two or more notes as if already known, defined in none of them.
   - "See the X note", "as covered in X", or a cross-link whose target file doesn't exist.
   - A prerequisite stated in prose — "this assumes you've set up X" — where X has no note.
   - A concept that appears in a note's *comparison* or *when not to use this* section as the alternative to reach for, and nowhere else.
2. **Missing learning bridge** (strong, but must be evidenced by the path). The notes define the terms on both sides yet omit the simplest complete mechanism that connects them — for example, they explain tasks and production workflow recovery but never assemble one durable task before introducing state machines, leases, and reconciliation. Use `learning-bridge` only when adding the baseline to an existing file would break that file's declared role or leave the path without a useful stop point.
3. **Promised but not delivered** (structural, easy to verify). A subfolder README, reading path, or numbered sequence advertises a topic with no corresponding file — a reading path with a step that goes nowhere, or a numbering gap where a file was clearly planned.
4. **Domain expectation** (weakest — use sparingly). A topic a practitioner would expect in a folder with this scope, with no internal evidence behind it. Allowed, but cap it at two per subfolder, and label the signal honestly so a human can discount it. This is where the pass turns into guessing about the ecosystem at large, which is not what it's for.

### What not to suggest

- A topic already covered inside an existing note, adequately for its scope. "This deserves its own file" is a real finding only when the existing treatment is too thin to carry what other notes lean on it for — say that explicitly when you claim it.
- A bridge that can be repaired by adding one small first-pass trace or clearer handoff to an existing note. That is a reader-journey or per-file finding, not a new-note proposal.
- A topic outside the subfolder's scope. The gap is measured against what *this folder* holds itself out as covering, same as the per-file scope rule.
- Something that belongs in a neighbouring subfolder — say which one instead of proposing a duplicate.
- A wishlist of everything adjacent to the domain. A subfolder with no gaps is a normal, common result; say so and move on.

### Output — `_audit/gaps.audit.md`

One file for the whole repo, separate from the per-file audits, and **not written for a fix-agent**. It's a triage list: a human reads it and decides what's worth writing. No fix-agent creates a note from it. Because of that, gap lines carry no `FIX-*` severity — the reader-harm ladder grades notes that exist, and mixing the two vocabularies invites an automated pass to act on a suggestion no one approved.

Format, one block per subfolder:

```
# <subfolder>/
Suggested new notes: N

GAP: <proposed note topic> — <why a reader needs it, one sentence>.
  SIGNAL: leaned-on | learning-bridge | promised | domain-expectation
  EVIDENCE: <file:section or quoted line where the notes lean on it, or "none — domain expectation">
```

Rules:
- Every subfolder gets a block. If it has no gaps, emit its header with a single `NO-GAPS: <one line on why coverage looks complete>` line — same reason as `NO-ACTION` in the per-file pass: silence reads as unchecked.
- One proposed note per `GAP` line. Don't bundle three missing topics into one.
- `EVIDENCE` must quote or cite something real for `leaned-on`, `learning-bridge`, and `promised`. A learning bridge cites both sides of the jump and the README path that forces it. A `GAP` line whose evidence you cannot point at is a `domain-expectation`; do not dress a guess up as internal evidence.
- Name the topic, not the filename. Numbering and placement are the note-maker's job.
- Order blocks so subfolders with gaps come first, and `leaned-on` plus `learning-bridge` lines before weaker signals within a block.
- Nothing else in the file — no narration, no rubric, no per-file findings.

---

## Severity is keyed to reader harm

The question is always what happens to the reader — never which category the finding falls into.

| Level | The reader… |
|-------|-------------|
| `FIX-CRITICAL` | is **actively misled** — follows the note and gets a broken, insecure, or expensive result. Includes stale facts that now produce failures, and missing warnings on irreversible operations. |
| `FIX-HIGH` | **can't complete the task** from this note — the mechanism, the default, or the success signal is absent. |
| `FIX-MED` | completes it **slower or with less confidence** — has to re-read, guess, or go find an external source for something the note should have carried. |
| `FIX-LOW` | is **unaffected in outcome** — wording, consistency, a missing cross-link. |

Two consequences worth stating outright, because they invert the intuitive default:

- A stale version number the reader would never act on is `FIX-LOW`, not `FIX-CRITICAL`. Currency alone doesn't make something critical; consequence does.
- "This note never actually explains its own central concept" is `FIX-HIGH` or above, even when every fact in it is correct and current.

---

## Output — the per-file audit report

The per-file audit files, `_audit/reader_paths.audit.md`, and `_audit/gaps.audit.md` are your only deliverables. Write per-file findings as instructions for a future fix-agent, not as a description of your process. No narration ("this report covers…"), no restating the rubric, no hedging. Every line under a file header is a direct, executable instruction.

Format, one block per note file, using its path relative to the repo root:

```
# <relative/path/to/note.md>
Summary: N critical, N high, N med, N low

FIX-CRITICAL: <what's wrong> — <what the correction is>. Source: <url>, checked <date>.
FIX-HIGH: <what's missing> — <what to add>.
FIX-MED: <what section/line> — <what to change and why, in one sentence>.
FIX-LOW: <the nit> — <the fix>.
NO-ACTION: <what's already solid, one line, only if worth flagging>.
```

Rules for writing these lines:
- One instruction per line. Three currency issues in a file means three `FIX-CRITICAL` lines, not one bundled paragraph.
- `Summary:` is the only non-instruction line — a human triage aid for the review step between phases, not an action for the fix-agent. Everything else is a command.
- Every `FIX-CRITICAL` tied to a currency issue must include a source URL and the date you checked it — a fix-agent can't correct what it can't verify, and a human reviewer can't sanity-check a bare assertion.
- Be concrete enough that the fix-agent doesn't have to guess. Bad: "explain caching better." Good: "add what the cache key is and when it invalidates — currently states results are cached but not on what."
- If a file has no issues worth flagging, still emit its header with a single `NO-ACTION` line. Silence reads as "I forgot to check this," not "this passed."
- Don't invent a finding to avoid an empty section. A short block is a legitimate result.

One audit file per subfolder, e.g.:

```
_audit/aws.audit.md
_audit/backend.audit.md
_audit/langfuse.audit.md
```

Each contains one block (as above) per `.md` file in that subfolder — nothing else in the file. Missing notes never appear here; they go in `_audit/gaps.audit.md`, in that file's own format.

---

## Ground rules

- You do not edit note files. You do not apply fixes. That happens in a separate phase, separate session, after a human reviews this report.
- Every `FIX-CRITICAL` or currency claim needs a source and a date — not "this seems outdated."
- Severity comes from the reader-harm ladder above, not from which dimension the finding came out of.
- Audit a note against its own stated scope first, general completeness second — don't turn scope creep into a finding. The one exception is the three completeness non-negotiables; those apply to any note the reader will act on, whatever its scope says.
- If a file is genuinely solid, say so in one `NO-ACTION` line and move on. Don't manufacture findings to look thorough. The same holds for the gap pass and `NO-GAPS`.
- A clean per-file audit is not a clean audit. The reader-journey and gap passes run regardless of how the files score; individually strong notes can still form an unusable course or omit the bridge between two well-covered topics.
- Judge a worked example by the standard it sets for itself: if it's presented as the real way to do something, hold it to that; if it's explicitly a minimal illustration, don't grade it as if it were a reference implementation.
- Do not excuse an abrupt learning path because every advanced fact is accurate. Grade when the reader encounters the mechanism, not only whether it is eventually explained.
- Production awareness is the destination, not the entry price. Require failure modes, limits, recovery, and practitioner tactics eventually, while preserving a concept-first baseline and useful stop point.

---

## What NOT to do

- Don't edit or rewrite any note file — this skill is audit-only.
- Don't apply or stage fixes yourself, even ones you're confident about.
- Don't bundle multiple distinct issues into one `FIX-*` line.
- Don't flag a currency issue without a source URL and the date checked.
- Don't rank every currency finding as `FIX-CRITICAL` — rank it by what happens to the reader who acts on it.
- Don't apply a criterion you can't point to in the rules file, and don't restate one in your own words where citing it would do.
- Don't skip a file's block when it's clean — emit `NO-ACTION` instead of silence.
- Don't skip the full-prose reader-journey pass because READMEs, links, or individual files look well structured.
- Don't manufacture findings on a solid file just to look thorough — dimension 5's checks are the easiest place to do this by accident.
- Don't grade a minimal, explicitly-labeled illustration by the same bar as a note's main worked example, or flag a deliberately bare baseline block that a hardened block follows.
- Don't create the missing notes, stub them, or edit a README to point at them — the gap pass proposes, a human decides.
- Don't put `GAP` lines in a per-file audit file, or `FIX-*` lines in `gaps.audit.md`. The two vocabularies stay separate so nothing automated acts on an unapproved suggestion.
- Don't run the gap pass per subfolder — an absence is only visible against the whole tree.
- Don't report a missing learning bridge as a vague readability complaint. Name the two sides of the jump, the path that forces it, and whether the fix belongs in an existing note, the README, or a new bridge note.
- Don't pad `gaps.audit.md` with everything adjacent to the domain. No internal evidence means it's labeled `domain-expectation`, capped at two per subfolder, or left out.
