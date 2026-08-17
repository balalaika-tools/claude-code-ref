# Learning-curve and explanation audit

Read this file completely for every audit. Apply its two axes independently to every teaching note: a well-ordered note can still fail to explain, and a clear explanation can still bury the first useful result.

## Contents

- [Guardrails](#guardrails)
- [Measurement protocol](#measurement-protocol)
- [Ordering checks](#ordering-checks)
- [Safety check](#safety-check-toy-not-correct)
- [Explanation checks](#explanation-checks)
- [Concrete-carrier checks](#mechanism-left-without-a-concrete-carrier--fix-high-or-fix-med)
- [Reading-path checks](#reading-path-checks)
- [Repo metrics](#repo-metrics)

## Guardrails

- Preserve depth. Fix ordering with an entry point, a move, or a named split; do not delete hardening, citations, failure modes, or useful edge cases.
- Give conceptual notes a concrete worked trace with named values and visible output; do not demand executable code where nothing is executable.
- Treat a minimal example as safe only when it preserves correctness- and security-critical behavior. A warning or “simplified” label never excuses unsafe code.
- Treat code as evidence of execution, not as explanation. Judge execution and restatement separately.
- Fix an explanation deficit with causal prose: the mechanism, consequence, or adversary sequence. Do not add another rule or warning.
- Do not double-report one defect under overlapping labels. Prefer the most specific label. Buried baseline and assembly gap may both appear because one fixes the entry point and the other fixes composition.

## Measurement protocol

For each note, record the following before writing findings:

1. Count total physical lines.
2. Identify the note's role, then locate its first complete payoff: a concrete situation and useful mental model for a foundation/tutorial; a runnable result for an implementation; the motivating failure or constraint and the deeper mechanism's consequence for a deep dive; a named decision with criteria and an initial recommendation for a decision guide; or a lookup map and useful defaults for a reference. Do not demand the same artifact from every role.
3. Compute payoff distance as `payoff line / total lines`. Use `n/a` for a pure index, lookup reference, or link list whose role has no teaching sequence; record a reference's lookup orientation separately rather than inventing a runnable payoff.
4. Count prescriptive markers: `> **Rule**:`, `> **Principle**:`, `⚠️`, `❌`, and `✅`.
5. Count prose paragraphs that explain a mechanism, causal consequence, failure, or attack. Exclude headings, tables, code, captions, instructions that merely restate what to do, and the prescriptive markers themselves.
6. Compute the register ratio as `prescriptive markers : explanatory paragraphs`. Report raw counts too; do not hide a zero denominator.
7. Apply `example-selection.md` and inventory only the high-leverage mechanisms that meet its concrete-carrier triggers. Count how many lack a faithful local carrier at their point of need. Do not count all concepts, sections, code blocks, or examples.
8. Run the restatement test last with code, tables, and rules mentally removed: can the target reader explain the central concept and why the mechanism works in their own words?

Use semantic judgment for “composed,” “explanatory paragraph,” and the restatement test. Keyword counts can nominate candidates but cannot decide them.

## Ordering checks

### Buried role-appropriate payoff — FIX-HIGH

Flag when setup detail, taxonomy, or hardening occupies two or more substantive sections before the
reader reaches the payoff appropriate to the note's role. Report the exact payoff line, total lines,
percentage, and what precedes it. Prescribe the missing runnable baseline, concrete situation,
motivating failure, decision scenario, or lookup orientation—not a universal heading. Treat payoff
distance as evidence, not an automatic line-number verdict.

### Hardening-before-baseline inversion — FIX-HIGH

Apply this to a tutorial or implementation note that owns the runnable path. Check whether the
reader meets caching or TTL, rotation, retry or backoff, connection pooling, metadata or discovery
indirection, emergency or failover hooks, metrics or structured logging, or a multi-branch error
taxonomy before seeing the minimal form of that concept. A deep dive may start from the failure that
requires the advanced mechanism when it states or links the baseline it assumes; do not force it to
repeat the baseline.

### Missing or mismatched opening payoff — FIX-HIGH or FIX-MED

Require useful early traction, not `## The short version` or fixed fields:

- foundation/tutorial: a concrete situation and first correct mental model or worked outcome;
- implementation: the smallest runnable path, bounded inputs, and observable result;
- deep dive: the failure, constraint, or surprising behavior that requires the deeper mechanism;
- decision guide: a named decision, the criteria that change it, and an initial recommendation;
- reference: scope, lookup map, and defaults or common subset, with no forced tutorial.

Use `FIX-HIGH` when the note cannot deliver its promised capability without the missing payoff. Use
`FIX-MED` when the payoff exists but the opening form mismatches the role or makes the reader work
through avoidable detail first. Do not flag an exact heading, counted list, field order, or absence of
code by itself.

### Unbounded operational inputs — FIX-MED

When a note asks the reader to perform an operation, require a bounded account of the values,
credentials, endpoints, files, or state they supply. An explicit count is optional; “configure the
appropriate values” is still too vague.

### Missing deferral contract — FIX-HIGH

For a minimal, basic, or quickstart example that actually omits relevant production concerns,
require those omissions nearby with links to the sections that handle them. Name only concerns the
example or note makes relevant. `Not handled yet` is an optional label; the fix is a useful boundary,
not ceremonial syntax or a generic “not production-ready” warning.

### Uniform density or no skip path — FIX-MED

Sample the section rhythm. Flag a teaching note when core mechanism, production hardening, and rare edge cases all use the same visual and rhetorical weight, or when no marker tells a first-time reader what can be skipped. Prescribe `Core`, `Production`, and `Edge case` altitude markers at specific boundaries.

### Blocking prerequisite gate — FIX-MED

Flag a prerequisite gate only when it is optional background or exceeds what the stated audience
truly needs. A genuine prerequisite may appear before the payoff; keep it brief and supply small
missing context inline instead of forcing an unnecessary detour.

### Assembly gap — FIX-HIGH

Flag when a tutorial or implementation note promises an assembled result but its individually
explained pieces are never composed in one runnable block, or are composed only after unrelated
detail. State which pieces need joining and what observable end-to-end result the block must
produce. Do not demand assembly from a decision guide, deep dive, or reference that explicitly links
to the canonical implementation owner.

### Length without payoff proximity — FIX-MED

Always report payoff distance when the role has a teaching sequence. Use a value over 0.25 as a
regression signal that prompts a semantic inspection, not as an automatic finding. Flag only when
the reader is genuinely delayed by material that should follow the role-appropriate payoff. Also
flag a note over 500 lines with no `<!-- length-justification: ... -->`; prescribe a split with a
named boundary or add the concrete justification.

## Safety check: toy-not-correct

Report `FIX-CRITICAL` for any example, including an introductory one, that:

- lets untrusted input choose an algorithm or cipher;
- omits required issuer, audience, expiry, or freshness validation;
- compares secrets, message authentication codes, or signatures with ordinary equality instead of a constant-time function;
- disables TLS verification, including `verify=False`, `rejectUnauthorized: false`, `-k`, or `InsecureSkipVerify`;
- builds SQL or shell commands through string concatenation or interpolation;
- logs a token, key, password, full credential, or credential prefix; or
- uses a real-looking credential instead of an unmistakable placeholder.

Name the unsafe line and restore the missing safe operation. Never prescribe a warning as the fix, and never downgrade because the block says “simplified” or promises later hardening.

## Explanation checks

### Unglossed jargon at first use — FIX-HIGH

Identify domain terms from the title, headings, repeated abbreviations, protocol fields, and code identifiers. At each first prose occurrence, inspect the surrounding two lines for an acronym expansion or inline cue such as “is a,” “means,” an em-dash gloss, or a parenthetical definition. A cross-link does not count. Inspect the opening payoff first because it is where the note establishes its local reader contract. Name each term and first-use line; group terms in one finding only when one local glossary sentence can fix them together.

### Rule without mechanism — FIX-HIGH

For each rule, principle, warning, or correct/incorrect marker, read backward within the same section. Flag it when no preceding prose explains the causal mechanism, consequence, or attack that earns the conclusion. Quote the rule and prescribe the exact mechanism to walk through.

### Defense without adversary — FIX-HIGH

For a security control, require an attacker-ordered narrative: what the attacker has, what they send or change, what vulnerable code decides, and what they gain. A CVE or RFC citation is evidence, not an explanation. Prefer this label over “rule without mechanism” when both describe the same passage.

### Mechanism without its problem — FIX-HIGH

At a mechanism’s introduction, require the first paragraph to show what breaks without it and the consequence before defining the mechanism. Flag definition-first introductions and prescribe a concrete failure scenario, not a more elaborate definition.

### Abstract before concrete — FIX-MED

Flag a section that opens with a definition table, taxonomy, generalized rule, full schema, or topology before any real instance. Preserve the reference material but place one actor, value, transition, and consequence before it.

### Mechanism left without a concrete carrier — FIX-HIGH or FIX-MED

Apply the semantic triggers in `example-selection.md` to each high-leverage mechanism. Flag when a
reader must write, inspect, review, debug, or mentally simulate a policy, configuration, schema,
query, payload, command, state transition, precedence rule, or multi-part interaction but never sees
the smallest faithful form near the explanation.

Require three things from the local carrier:

1. the relevant artifact, request, state, or decision inputs are visible;
2. the note maps the important field, value, order, or transition to the outcome; and
3. when the distinction is non-obvious, one meaningful changed input produces a contrasting result.

Use `FIX-HIGH` when the note promises to teach the reader to create, evaluate, or debug the central
artifact and no complete correct example or usable carrier exists. Use `FIX-MED` when the task can
still be completed but the reader must mentally invent the artifact, detour to external material, or
wait for an unrelated later integration example before the local mechanism becomes concrete.

Do not also report `abstract before concrete` when absence of the carrier is the root cause. That
check owns bad ordering of an existing instance; this check owns the missing instance. Do not flag a
simple definition, a pure lookup reference, a mechanism already carried by a nearby example with the
same semantics, or a non-canonical note that provides a sufficient labeled excerpt and link.

Prescribe the carrier, not “more examples”: name whether the correction is a policy/config excerpt,
request/response, input/output rows, state trace, command/output, or changed-input decision table,
and state the behavior it must make predictable.

### Register imbalance — FIX-MED

Always report the register ratio in the explanation verdict. Flag ratios above 2:1 and name representative cold rules. Prescribe explanatory paragraphs at the sections that caused the imbalance; do not recommend removing useful warnings merely to improve the number.

### Restatement test — FIX-HIGH

Identify the central concept and state PASS or FAIL. Fail when, after removing rules, code, and tables, the note leaves only instructions or disconnected definitions. Prescribe the smallest set of missing causal explanations that would let the intended reader explain the problem, mechanism, and consequence without quoting the note.

## Reading-path checks

- `FIX-HIGH` a path when no runnable result or concrete worked outcome appears within its first two entries. Name the first payoff entry and reorder the path as do → understand → harden.
- `FIX-LOW` divergent copies of the same baseline across notes when they differ only in presentation. Raise severity by reader harm when the copies disagree on correctness or safety.
- Keep the existing cold-reader protocol: identify the earliest note responsible for an unexplained dependency or complexity jump, and do not borrow knowledge from later entries.

## Repo metrics

Aggregate after all per-file and path audits. Sum raw counts for the repo-wide register ratio; do not average per-note ratios. Report both tables on every run.

Ordering metrics:

- teaching notes with a role-appropriate opening payoff;
- notes whose payoff distance exceeds 0.25;
- notes over 500 lines without a length justification;
- reading paths with a runnable or worked result within two entries; and
- toy-not-correct examples.

Explanation metrics:

- repo-wide register ratio;
- unglossed first uses of jargon;
- notes containing any intuition-building construct;
- notes passing the restatement test; and
- rules or defenses with no mechanism or adversary explanation.
- example-demanding mechanisms without a local concrete carrier.

The intuition-building count is a trend signal, not a phrase quota. Count genuine analogies, restatements, causal “why this works” passages, or concrete explanatory scenarios; never create a per-file finding solely because a preferred phrase is absent.

For `auth-notes`, retain these pre-remediation regression anchors in the metrics report: the former
short-version contract passed 1/43 but is **not comparable** to the role-aware opening metric; payoff
distance exceeded 0.25 in 40+/43; notes over 500 lines were 7/43; runnable result within two entries
was 0/5; register ratio was about 21:1; unglossed first uses were 343; and notes with any
intuition-building construct were about 8/43. Label unknown historical counts as “not recorded”;
never invent them. For another repository, mark the historical baseline `n/a` and establish the
current run as its first baseline.
