# How we write notes

This is the house style for note prose. It governs two jobs: writing a new note, and applying approved audit fixes to an existing one. These are the standards every note is held to — an audit measures notes against them, and an edit should move the note toward them, not just patch the flagged line.

Most of what follows is a **required move**, not a prohibition. A note that only avoids the failure modes comes out accurate and teaches nothing. The devices below are what make it land on a first read and stick after.

## Contents

- [Audience and teaching balance](#who-the-note-is-for)
- [Collection and note ordering](#the-collection-has-a-learning-contract)
- [The short version](#open-with-a-result-that-also-teaches)
- [Explanation moves](#ground-every-term-at-first-use)
- [Examples and safety](#examples-baseline-first-hardened-second)
- [Density, altitude, and completion](#mark-altitude-and-control-prescriptive-density)

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

## The collection has a learning contract

The goal is not merely complete notes. It is a path that takes a first-time reader through four layers in order:

1. **Concept** — the problem, plain-language mental model, and minimum vocabulary.
2. **Minimal usable mechanism** — the smallest complete implementation or worked trace that produces an observable result.
3. **Production hardening** — the defaults and safeguards that make the mechanism safe under real load and failure.
4. **Operational awareness** — failure symptoms, limits, trade-offs, recovery procedures, and the practitioner tricks that prevent or diagnose them.

A single file does not need to carry all four layers. The **full learning path as a whole does**; shorter paths may stop at a declared milestone. Each file needs one primary role: foundation/tutorial, implementation, deep dive, decision guide, or reference. Do not turn every foundation note into a production reference in the name of completeness.

Four rules keep the progression usable:

- **Order paths do → understand → harden.** Every reading path produces a runnable result or concrete worked outcome within its first two entries. A path may revisit an earlier note for greater depth later; label the revisit instead of pretending the sequence is linear.
- **Teach the smallest complete system before its advanced variants.** A reader should see one durable task before a stateful workflow, one claim before fencing and reconciliation, or one request before a full deployment topology.
- **Provide stop points.** After the conceptual and minimal layers, say who can stop there and which new requirement makes the next layer necessary.
- **Give each mechanism one canonical owner.** One note owns the full schema, implementation, or option set. Other notes use a small trace or excerpt and link to that owner instead of repeating the reference material.

A first-time path fails this contract if every individual note is accurate but the reader must learn several production mechanisms before they can explain or build the baseline.

## Open with a result that also teaches

Every actionable note opens with `## The short version` after the title and audience line, before prerequisites and numbered sections. It is neither an abstract nor a contents list. A cold reader who stops there gets a small correct result and enough explanation to say why it works.

The block contains, in order:

1. Two to four sentences stating the problem, the one-line mental model, and why the inputs are sufficient.
2. `**What you need (N things):**` followed by an enumerated list of the concrete inputs. The count is required: it bounds the task for a reader who does not yet know how much machinery is involved.
3. `**The code:**` with 10–25 runnable lines, or `**Worked example:**` with named actors, real values, one transition, and one observable outcome.
4. `**Success signal:**` with the exact output, status, or observation.
5. `**Not handled yet:**` with every deferred production concern linked to its later section.

Keep the block at 40 lines or fewer and end it by line 80. Runnable code appears by line 80 or 15% of the note, whichever comes first. A prerequisite never sits before the block; if one sentence of context is essential, supply it inline. Put advisory prerequisite links after the payoff.

The short version has two independent acceptance tests:

- **Execution:** a reader can run or follow it and observe the stated result.
- **Restatement:** a competent reader new to the subject can explain what the inputs are, why those inputs are sufficient, and why the mechanism produces that result.

A code block can pass execution and fail restatement. Both must pass.

## Lead with the problem, then state the *why*

Section 1 of every note has a fixed job: put the reader in the situation that makes this subject necessary, then answer it in one sentence. The definition comes after that, not before.

❌ "Hooks are user-defined handlers that run at specific lifecycle events."

✅ "You told Claude in CLAUDE.md to run prettier after every edit. It does — most of the time. Hooks are how you make it every time: the harness runs your command on a lifecycle event, with no model in the loop to forget."

The test: a reader who stops after three sentences should be able to say what this is *for*. If your opening would work equally well as a dictionary entry, it isn't an opening.

The same obligation holds section by section, not just at the top. For any concept, say what problem it solves — not just what it is. Cover what's easy to get wrong, and when to use it vs. when not to.

## Ground every term at first use

Never require the reader to leave the note to learn its vocabulary. At the first use **in this note**, expand acronyms and add a short inline gloss that answers: *what kind of thing is this?* Keep cross-links for depth, not as the only definition.

❌ "The verifier picks a key from the JWKS using `kid`."

✅ "The verifier picks a key from the **JWKS** — a JSON file the issuer publishes with its current public keys — using `kid`, the short key identifier in the token header."

This applies inside *The short version*. Familiarity elsewhere in the collection does not excuse an ungrounded first use here; search-engine readers and readers following a different path still need the six-word gloss.

## Introduce a mechanism through the problem it solves

Before describing how a mechanism works, show the world without it and the consequence. "A JWKS lists public keys" describes a thing. "A pasted public key works until rotation makes every request fail; a JWKS lets the verifier follow the issuer's current keys" explains why the thing exists.

For every mechanism introduced, ask: **what breaks if this does not exist?** If the reader cannot answer, the mechanism was described but not explained. State the rule only after this causal explanation; a rule is the conclusion of understanding, not a substitute for it.

## Explain the adversary before the defense

For security controls, the attack is the explanation. Walk through the attacker's input, the verifier or system decision they exploit, and the observable consequence before prescribing the defense. End by naming exactly which choice the defense moves from untrusted input to trusted configuration.

Do not stop at "pin the algorithm." Show that an attacker changes `alg`, why a permissive verifier obeys it, which key material is reused incorrectly, and how an explicit algorithm list prevents the token from choosing the verification method. Keep the attack concrete enough that the reader can recognize the same bug in differently shaped code.

## Put concrete instances before abstractions

Use a real value before a definition table. Show `"aud": "https://api.orders.example.com"` reaching the billing API and being refused before listing every claim type. Tables, taxonomies, full schemas, and production topologies remain valuable reference material, but they follow the instance that gives their rows meaning.

The test is simple: could the reader point to one actor, value, transition, and consequence before being asked to generalize? If not, the section started too high.

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

## Examples: baseline first, hardened second

**No production mechanism may appear before the baseline runs end to end.** Caching, rotation, retries, pooling, discovery or metadata indirection, emergency hooks, observability, and failure taxonomies are hardening. None may be the reader's first encounter with a concept. Show the baseline, state its operational risk in one line, link forward, and only then harden it.

Use this structural test: **delete every section after the first runnable end-to-end example. Does what remains still teach a correct, usable baseline?** If not, the note is ordered wrong.

The sequence inside the note is:

1. Run the smallest correct end-to-end example and show its visible output.
2. Explain why it works until the reader can restate the mechanism.
3. Name omissions in **Not handled yet** and link each one forward.
4. Harden in a later block, with a comment on each addition naming the failure it prevents.
5. Finish with an integration or end-to-end check that you execute exactly as displayed. Include the required database connections, services, fixtures, and synchronization; a comment explaining why the shown block cannot run in its stated environment makes it a sketch, not a test.

> **Principle**: simplify the operational, never the correctness-critical. A minimal example should be acceptable in a junior engineer's pull request: small and unpolished, not unsafe.

Never omit these when they apply:

- algorithm or cipher pinning; untrusted input never chooses the algorithm
- audience, issuer, expiry, or freshness validation
- constant-time comparison for secrets or signatures
- TLS certificate verification; never use `verify=False` or `rejectUnauthorized: false`
- parameterized queries; never build SQL through string interpolation
- keeping secrets, credentials, and tokens out of logs and error strings

Safe deferrals include caching and connection reuse, retries and backoff, key rotation, metrics and tracing, granular error mapping, configuration indirection, and dependency injection. Every deferral must appear in **Not handled yet** with a link to the section that owns it; a minimal example without this contract is not publishable.

One 60-line production block teaches less than a small baseline followed by a hardened diff.

Concept-heavy notes follow the same ladder without pretending diagrams are code:

1. Start with a small concrete trace: named actors or rows, one input, one transition, and one visible outcome.
2. Explain the causal mechanism behind the outcome.
3. Replay the trace with the first crash, race, or scale constraint that requires hardening.
4. Only then introduce the full schema, decision matrix, or production topology.

A 100-line SQL block is not minimal merely because it is self-contained. The reader must be able to state what changed and why before reading the complete implementation.

## Mark altitude and control prescriptive density

Uniform density makes core ideas and rare edge cases look equally important. Mark the reading altitude explicitly:

- `> **Core:**` — required to understand or use the baseline
- `> **Production:**` — required before shipping, skippable while learning
- `> **Edge case:**` — conditional material to read only when its condition occurs

Rules, warnings, and correct/incorrect markers are conclusions. They follow the mechanism or consequence that earns them. In a teaching note, write at least one paragraph of mechanism or consequence for every two `> **Rule:**`, `⚠️`, `❌`, or `✅` markers. A large imbalance is a checklist wearing a tutorial's clothes.

Split notes over 500 lines unless one file is necessary for a concrete reason; record that reason near the top as `<!-- length-justification: ... -->`. Hardening may occupy most of a note, but never precedes the baseline.

## Finish with the restatement test

Accuracy and runnable code are necessary, not sufficient. Before shipping, ask:

> Could a competent engineer who is new to this subject, having read only this note, explain the concept correctly to a colleague in their own words without quoting it?

If the reader can only recite rules, the note transferred instructions rather than understanding. Apply this test to *The short version* separately and to the completed note as a whole.

## Headers make claims; one insight per note

**Section headers should answer, not label.** "Lifecycle Events" says what's in the section; "Which events you'll actually use" says what the reader leaves with. The second is also what a returning reader scans for six months later.

**Every note carries exactly one `> **Key insight**:`.** It must be *transferable* — true beyond this specific example — and *non-obvious* — not a restatement of a section's topic sentence. If you can't write one, the note hasn't found its point yet; that's a signal to revise, not to omit the line.

**`⚠️` marks failure modes and nothing else.** That turns a decorative marker into navigation: a returning reader scans for ⚠️ to find the landmines without re-reading the note.

## Currency — verify, don't assume

Anything time-sensitive (versions, deprecated APIs, pricing, "current best practice," product names) must reflect the live current state. If a fix depends on a fact that could have changed, confirm it against a current source before writing it in. Don't restore stale claims from training-data memory.

## Tone

Plain, direct, concrete. No filler, no hedging, no narration of your own process. Prefer a short accurate sentence over a long vague one.
