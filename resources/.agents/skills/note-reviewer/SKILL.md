---
name: note-reviewer
description: "Audit a technical notes repository for explanation quality, outdated content, incomplete coverage, and weak worked examples — producing a structured, per-file findings report for human review. Never edits note files or applies fixes; that happens in a separate follow-up phase. Use this skill whenever the user wants to audit, review, or fact-check a notes repo or knowledge base — e.g. 'audit my notes', 'review this notes repo for accuracy', 'check these docs for staleness', 'are these notes still correct', 'find gaps in this documentation'."
---

# Notes Repo Auditor

You are auditing a technical notes repository — inspecting `.md` files and producing a report of exactly what needs to change and why. You do not edit any note file. You do not decide whether findings get applied — a human reviews the report separately, and a fix-agent applies approved fixes in a later session. Don't step outside that boundary.

---

## Orchestration

The repo has several subfolders (e.g. `aws/`, `backend/`, `langfuse/`), each with several `.md` files.

> **Rule**: This section applies only when running in **Claude Code** (where the `Agent` tool is available). Outside Claude Code, audit subfolders one at a time yourself, in the same order, applying the same rules.

If there are multiple subfolders, launch one subagent per subfolder (all `Agent` tool calls in a single message so they run concurrently). Give each subagent this SKILL.md plus its assigned subfolder path. Rules for staying in your lane:

- Read and audit only the `.md` files inside the assigned subfolder. Don't wander into other subfolders — another sub-agent owns those and is working from an identical copy of these instructions.
- Notes in the same subfolder usually share vocabulary and cross-reference each other. Read the whole subfolder together, not file-by-file in isolation, so you catch inconsistencies between files — e.g. the same term defined two different ways in two notes.
- If a subfolder has 30+ files, split it into two passes rather than holding all of it in context at once. Otherwise one pass covers the whole subfolder.
- Write findings to a single audit file mirroring the subfolder's name, e.g. `_audit/aws.audit.md` for `aws/`. Don't touch any other audit file, and don't touch any note file.

---

## Who the note is written for

Calibrate every judgment against this exact reader: **a competent practitioner in the general domain, encountering this specific subject for the first time.**

Example: a backend engineer reading a note about Langfuse tracing. They know what an API is, what a decorator is, what latency means. They do *not* yet know Langfuse's specific concepts (traces, spans, generations, scores).

So the note should:
- Skip re-explaining general domain basics ("what is an API")
- Fully explain the specific subject's concepts, vocabulary, and mechanics from zero
- State *why* something exists / what problem it solves — not just *what* it is
- Cover what's easy to get wrong, and when to use it vs. not

If the note assumes the reader already knows the specific tool or concept it's supposed to be teaching, that's a failure — not an acceptable shortcut.

---

## What you're checking for

### 1. Explanation craft — the simplicity/fullness balance

Not a completeness check (that's #3), and not about whether the note's worked examples reflect production practice (that's #4). A section can contain every fact it needs and still fail here, because *how* it explains something matters as much as *what* it covers. For any concept there's a spectrum from "soundbite" to "reference-manual entry," and most explanations fail by collapsing to one end:

- **Too simple (loses fullness):** easy to read, but leaves the reader unable to actually use the thing. States the effect, skips the mechanism. Uses an analogy and never cashes it out into the real mechanics.
- **Too dense (loses simplicity):** technically accurate, but unreadable on a first pass. Leads with jargon before any intuition is built. Explains one unfamiliar concept by referencing three other unfamiliar concepts. Lists every option/flag with no signal of which ones matter.

**Target:** build the correct mental model in plain language first, then attach the precise mechanism that makes that model actionable. One well-chosen example beats five abstract sentences.

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

Look for these being conspicuously absent:
- Failure modes / common errors and how to debug them
- Limits, quotas, edge cases
- Trade-offs vs. alternatives — why this, not that
- Security or cost implications, if relevant to the subject
- A minimal working example the reader could actually run
- "When NOT to use this"

A note that only covers the happy path is incomplete, even if everything in it is accurate.

### 4. Example quality — does it actually show production-grade practice?

Notes in this repo often include a worked example that combines several tools to solve a real problem — e.g. a RAG pipeline instrumented with OpenTelemetry and Langfuse. That example's job is to show the reader how the pieces genuinely fit together at a production level, not just that each piece individually runs. Check:

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

---

## Output — the audit report

This is your only deliverable. Write it as instructions for a future fix-agent, not as a description of your process. No narration ("this report covers…"), no restating the rubric, no hedging. Every line under a file header is a direct, executable instruction. A fix-agent should be able to read this file top to bottom and act, with zero re-interpretation.

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

Each contains one block (as above) per `.md` file in that subfolder — nothing else in the file.

---

## Ground rules

- You do not edit note files. You do not apply fixes. That happens in a separate phase, separate session, after a human reviews this report.
- Every `FIX-CRITICAL` or currency claim needs a source and a date — not "this seems outdated."
- Audit a note against its own stated scope first, general completeness second — don't turn scope creep into a finding.
- If a file is genuinely solid, say so in one `NO-ACTION` line and move on. Don't manufacture findings to look thorough.
- Judge a worked example by the standard it sets for itself: if it's presented as the real way to do something, hold it to that; if it's explicitly a minimal illustration, don't grade it as if it were a reference implementation.

---

## What NOT to do

- Don't edit or rewrite any note file — this skill is audit-only.
- Don't apply or stage fixes yourself, even ones you're confident about.
- Don't bundle multiple distinct issues into one `FIX-*` line.
- Don't flag a currency issue without a source URL and the date checked.
- Don't skip a file's block when it's clean — emit `NO-ACTION` instead of silence.
- Don't manufacture findings on a solid file just to look thorough.
- Don't grade a minimal, explicitly-labeled illustration by the same bar as a note's main worked example.
