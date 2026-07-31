# How we write notes

This is the house style for note prose. It governs two jobs: writing a new note, and applying approved audit fixes to an existing one. These are the standards every note is held to — an audit measures notes against them, and an edit should move the note toward them, not just patch the flagged line.

Most of what follows is a **required move**, not a prohibition. A note that only avoids the failure modes comes out accurate and teaches nothing. The devices below are what make it land on a first read and stick after.

## Who the note is for

Write for **a competent practitioner in the general domain, meeting this specific subject for the first time.** They know the general basics; they don't know this tool or concept yet.

- Don't re-explain general domain basics (what an API is, what latency means).
- Do explain the subject's own concepts, vocabulary, and mechanics from zero.
- Never assume the reader already knows the thing the note is supposed to teach.

Their existing expertise is also the cheapest teaching tool you have — see *Work with the model the reader already has*.

## The core balance: detail vs. simplicity

Aim for the middle of the spectrum between soundbite and reference-manual dump:

- Not **too simple** — stating that a thing exists without the mechanism to use it, or an analogy that never cashes out into how it actually works.
- Not **too dense** — jargon before intuition, one unknown explained via three more unknowns, every flag listed with no signal of which ones matter.

**The move:** build the correct mental model in plain language first, then attach the precise mechanism that makes it actionable. Say what to actually do, and which option is the default. One well-chosen example beats five abstract sentences.

## Lead with the problem, then state the *why*

Section 1 of every note has a fixed job: put the reader in the situation that makes this subject necessary, then answer it in one sentence. The definition comes after that, not before.

❌ "Hooks are user-defined handlers that run at specific lifecycle events."

✅ "You told Claude in CLAUDE.md to run prettier after every edit. It does — most of the time. Hooks are how you make it every time: the harness runs your command on a lifecycle event, with no model in the loop to forget."

The test: a reader who stops after three sentences should be able to say what this is *for*. If your opening would work equally well as a dictionary entry, it isn't an opening.

The same obligation holds section by section, not just at the top. For any concept, say what problem it solves — not just what it is. Cover what's easy to get wrong, and when to use it vs. when not to.

## Work with the model the reader already has

Readers don't arrive empty. They arrive with adjacent expertise and a guess about how this works. Both are leverage.

**Anchor to what they already know.** Where a mechanism has a genuine structural analogue in something this audience understands, name it once, precisely, and say where it stops holding.

> A `PreToolUse` hook is an admission controller for the agent loop: it sees the request before it executes and can allow, deny, or rewrite it. The analogy stops at scope — there's no cluster-wide policy object, just per-project config.

The "stops at" clause is not optional. An analogy without a boundary produces a confident wrong model, which costs more than no model. If you can't state the boundary, skip the device.

**Name the wrong model before you build the right one.** Where a specific, common misconception exists, say it out loud and kill it. This is the highest-retention move available, because the correct model attaches to a belief the reader already holds instead of to blank space. Write it as a contrast, not a warning:

> **The near-miss**: hooks look like "CLAUDE.md, but enforced." They're a different layer. CLAUDE.md is advice to the model — it can be reasoned around, compacted away, or overridden by a later instruction. A hook is harness behavior: it runs whether or not the model cooperates.

At most one per note, and only where the misconception is real. A manufactured "you might think X" is worse than nothing — it plants a wrong idea the reader didn't arrive with.

## Enumerations must be navigable

Any table or list longer than five entries needs a marked entry point, or it's a reference dump the reader has to triage alone. Two required moves:

1. **Mark the subset that matters.** Bold them, add a `★` column, or precede the table with "in practice you'll use three of these: X, Y, Z."
2. **Show one of them in use.** At least one marked entry appears in a worked example in the same note.

Applies to lifecycle events, CLI flags, config keys, IAM actions, model options — anywhere the full set is long and the used set is short. Listing everything is not the goal; the reader leaving with a default is. If you write "most people only need a few," name them in the same sentence.

## Every instruction ships with its success signal

If a note tells the reader to configure, install, or run something, it must also say how they know it worked — and what they see when it didn't. Without that, the reader can't tell a working setup from a silent no-op, and has no way to learn from their own attempt.

Cover both directions:

- **Worked:** the exact observable. The log line, the `/hooks` entry, the field in the response, the line in `terraform plan` output.
- **Didn't:** the most common silent failure and its tell. "Hook missing from `/hooks`? The JSON failed to parse — malformed hook blocks are skipped without warning."

⚠️ An unnamed silent failure is the most expensive gap a technical note can have. The reader either concludes the feature is broken, or — worse, for anything security-shaped — believes they're protected when they aren't.

## Completeness — answer the reader's questions, in priority order

These are the reader's questions, roughly in the order they'll ask them. Phrased as questions on purpose: a topic gets mentioned, a question gets answered.

**Non-negotiable — a note missing these is incomplete regardless of length:**

- *What breaks first when I use this for real?* — failure modes, with the error text or symptom the reader will actually see
- *When should I not use this?* — the boundary, and what to reach for past it
- *How do I know it's working?* — see the success-signal rule above

**Include where the subject warrants it:**

- *What did I just do that I can't undo?* — destructive or irreversible operations, cost and security exposure
- *What will a colleague ask me in review?* — the trade-off against the obvious alternative
- *Where does this stop scaling?* — limits, quotas, edge cases

Judge against the note's own stated scope first, general completeness second. The three non-negotiables are not scope-dependent: if the note teaches something the reader will act on, all three apply.

## Examples: minimal first, hardened second

"Production-grade" and "minimal runnable" are both required, in that order. The resolution is sequence, not compromise:

1. **The first example in a section is the smallest thing that runs and produces visible output.** No error handling, no config indirection, no retries. The reader's goal here is a baseline they can trust.
2. **Then harden it** in a second block, with a comment on each addition naming the failure it prevents.

```python
# Baseline — works, not safe for production
client = Client(api_key=os.environ["API_KEY"])

# Hardened — the default timeout is unbounded, so one hung request
# holds the worker until the process is restarted
client = Client(api_key=os.environ["API_KEY"], timeout=30.0)
```

One 60-line production block teaches less than these two blocks, despite containing more. The diff between them *is* the lesson.

Where the example shows several tools combined to solve a real problem, the hardened version must show how they genuinely fit together — real integration, correct structure, the non-obvious tactics a practitioner actually reaches for — not just that each piece runs. The test: could a reader who copied it explain *why* it's built that way? If the example is explicitly a minimal illustration, that's fine — keep it labeled as one.

## Headers make claims; one insight per note

**Section headers should answer, not label.** "Lifecycle Events" says what's in the section; "Which events you'll actually use" says what the reader leaves with. The second is also what a returning reader scans for six months later.

**Every note carries exactly one `> **Key insight**:`.** It must be *transferable* — true beyond this specific example — and *non-obvious* — not a restatement of a section's topic sentence. If you can't write one, the note hasn't found its point yet; that's a signal to revise, not to omit the line.

**`⚠️` marks failure modes and nothing else.** That turns a decorative marker into navigation: a returning reader scans for ⚠️ to find the landmines without re-reading the note.

## Currency — verify, don't assume

Anything time-sensitive (versions, deprecated APIs, pricing, "current best practice," product names) must reflect the live current state. If a fix depends on a fact that could have changed, confirm it against a current source before writing it in. Don't restore stale claims from training-data memory.

## Tone

Plain, direct, concrete. No filler, no hedging, no narration of your own process. Prefer a short accurate sentence over a long vague one.
