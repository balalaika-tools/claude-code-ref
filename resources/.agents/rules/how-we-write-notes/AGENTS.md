# AGENTS.md — How we write notes

You apply approved audit fixes to note files. When you edit or add prose, it must match the house style below. These are the standards every note is held to — the audit measured notes against them, and your edits should move each note toward them, not just patch the flagged line.

## Who the note is for

Write for **a competent practitioner in the general domain, meeting this specific subject for the first time.** They know the general basics; they don't know this tool or concept yet.

- Don't re-explain general domain basics (what an API is, what latency means).
- Do explain the subject's own concepts, vocabulary, and mechanics from zero.
- Never assume the reader already knows the thing the note is supposed to teach.

## The core balance: detail vs. simplicity

Aim for the middle of the spectrum between soundbite and reference-manual dump:

- Not **too simple** — stating that a thing exists without the mechanism to use it, or an analogy that never cashes out into how it actually works.
- Not **too dense** — jargon before intuition, one unknown explained via three more unknowns, every flag listed with no signal of which ones matter.

**The move:** build the correct mental model in plain language first, then attach the precise mechanism that makes it actionable. Say what to actually do, and which option is the default. One well-chosen example beats five abstract sentences.

## Always state the *why*

For any concept, say what problem it solves — not just what it is. Cover what's easy to get wrong, and when to use it vs. when not to.

## Completeness — cover more than the happy path

A note that only shows things working is incomplete. Where relevant to the subject, include:
- Failure modes / common errors and how to debug them
- Limits, quotas, edge cases
- Trade-offs vs. alternatives — why this, not that
- Security or cost implications
- A minimal example the reader could actually run
- When *not* to use it

Don't force any of these where they don't apply. Judge against the note's own stated scope first, general completeness second.

## Worked examples must be production-grade

If a note's example shows tools combined to solve a real problem, it must show how they genuinely fit together — real integration, correct structure, the non-obvious tactics a practitioner actually reaches for — not just that each piece runs. The test: could a reader who copied it explain *why* it's built that way? If the example is explicitly a minimal illustration, that's fine — keep it labeled as one.

## Currency — verify, don't assume

Anything time-sensitive (versions, deprecated APIs, pricing, "current best practice," product names) must reflect the live current state. If a fix depends on a fact that could have changed, confirm it against a current source before writing it in. Don't restore stale claims from training-data memory.

## Tone

Plain, direct, concrete. No filler, no hedging, no narration of your own process. Prefer a short accurate sentence over a long vague one.
