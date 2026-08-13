# Learning-curve and explanation audit

Read this file completely for every audit. Apply its two axes independently to every teaching note: a well-ordered note can still fail to explain, and a clear explanation can still bury the first useful result.

## Contents

- [Guardrails](#guardrails)
- [Measurement protocol](#measurement-protocol)
- [Ordering checks](#ordering-checks)
- [Safety check](#safety-check-toy-not-correct)
- [Explanation checks](#explanation-checks)
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
2. Locate the first complete payoff: one runnable, composed, end-to-end block that produces the title’s promised outcome. Earlier fragments do not count. For a conceptual note, use the first concrete worked trace with named actors or rows, real values, one transition, and a visible outcome.
3. Compute payoff distance as `payoff line / total lines`. Use `n/a` only for a pure index, lookup reference, or link list whose declared role has no teaching sequence.
4. Count prescriptive markers: `> **Rule**:`, `> **Principle**:`, `⚠️`, `❌`, and `✅`.
5. Count prose paragraphs that explain a mechanism, causal consequence, failure, or attack. Exclude headings, tables, code, captions, instructions that merely restate what to do, and the prescriptive markers themselves.
6. Compute the register ratio as `prescriptive markers : explanatory paragraphs`. Report raw counts too; do not hide a zero denominator.
7. Run the restatement test last with code, tables, and rules mentally removed: can the target reader explain the central concept and why the mechanism works in their own words?

Use semantic judgment for “composed,” “explanatory paragraph,” and the restatement test. Keyword counts can nominate candidates but cannot decide them.

## Ordering checks

### Buried baseline — FIX-HIGH

Flag when the first complete payoff starts after line 80 or after 15% of the file, whichever boundary is earlier. Report the exact line, total lines, percentage, and how many sections precede it. Prescribe a short-version entry point; do not merely say “move code earlier.”

### Hardening-before-baseline inversion — FIX-HIGH

At each concept’s first appearance, check whether the reader meets caching or TTL, rotation, retry or backoff, connection pooling, metadata or discovery indirection, emergency or failover hooks, metrics or structured logging, or a multi-branch error taxonomy before seeing the minimal form of that concept. Name the concept, the production concerns front-loaded, and the minimal form to show first.

### Missing short-version contract — FIX-HIGH

Before the first numbered section, every teaching note needs `## The short version` containing:

1. the problem and mental model in no more than four sentences;
2. a bounded, counted `What you need` list;
3. runnable code, an exact concrete procedure, or a concrete worked trace;
4. an exact success signal; and
5. a `Not handled yet` list linking deferred concerns forward.

Report every missing part in one short-version finding because they share one structural fix. Do not apply this requirement to a pure index, lookup reference, or link list.

### Un-enumerated inputs — FIX-MED

For an operational note, require an explicit count and a bounded list of the values, credentials, endpoints, files, or state the reader supplies. “Configure the appropriate values” does not bound the task.

### Missing deferral contract — FIX-HIGH

For every minimal, basic, or quickstart example, require a nearby explicit list of omitted production concerns with links to the sections that handle them. Name the omissions the note itself later introduces. The fix is a deferral contract, not a generic “not production-ready” warning.

### Uniform density or no skip path — FIX-MED

Sample the section rhythm. Flag a teaching note when core mechanism, production hardening, and rare edge cases all use the same visual and rhetorical weight, or when no marker tells a first-time reader what can be skipped. Prescribe `Core`, `Production`, and `Edge case` altitude markers at specific boundaries.

### Blocking prerequisite gate — FIX-MED

Flag prerequisite links or “before reading” gates above the first substantive payoff. Move them below the short version and make them advisory; supply any indispensable term inline.

### Assembly gap — FIX-HIGH

Flag when individually explained pieces are never composed in one runnable block, or are composed only in the final 20% of the note. State which pieces need joining and what observable end-to-end result the block must produce.

### Length without payoff proximity — FIX-MED

Always report payoff distance in the ordering verdict. Add a finding when it exceeds 0.25 unless a stronger buried-baseline finding already owns the same correction. Also flag a note over 500 lines with no `<!-- length-justification: ... -->`; prescribe a split with a named boundary or add the concrete justification.

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

Identify domain terms from the title, headings, repeated abbreviations, protocol fields, and code identifiers. At each first prose occurrence, inspect the surrounding two lines for an acronym expansion or inline cue such as “is a,” “means,” an em-dash gloss, or a parenthetical definition. A cross-link does not count. Inspect the short version first and most strictly because it is the universal entry point. Name each term and first-use line; group terms in one finding only when one local glossary sentence can fix them together.

### Rule without mechanism — FIX-HIGH

For each rule, principle, warning, or correct/incorrect marker, read backward within the same section. Flag it when no preceding prose explains the causal mechanism, consequence, or attack that earns the conclusion. Quote the rule and prescribe the exact mechanism to walk through.

### Defense without adversary — FIX-HIGH

For a security control, require an attacker-ordered narrative: what the attacker has, what they send or change, what vulnerable code decides, and what they gain. A CVE or RFC citation is evidence, not an explanation. Prefer this label over “rule without mechanism” when both describe the same passage.

### Mechanism without its problem — FIX-HIGH

At a mechanism’s introduction, require the first paragraph to show what breaks without it and the consequence before defining the mechanism. Flag definition-first introductions and prescribe a concrete failure scenario, not a more elaborate definition.

### Abstract before concrete — FIX-MED

Flag a section that opens with a definition table, taxonomy, generalized rule, full schema, or topology before any real instance. Preserve the reference material but place one actor, value, transition, and consequence before it.

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

- teaching notes with a complete short-version contract;
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

The intuition-building count is a trend signal, not a phrase quota. Count genuine analogies, restatements, causal “why this works” passages, or concrete explanatory scenarios; never create a per-file finding solely because a preferred phrase is absent.

For `auth-notes`, retain these pre-remediation regression anchors in the metrics report: short version 1/43, payoff distance over 0.25 in 40+/43, notes over 500 lines 7/43, runnable result within two entries 0/5, register ratio about 21:1, unglossed first uses 343, and notes with any intuition-building construct about 8/43. Label unknown historical counts as “not recorded”; never invent them. For another repository, mark the historical baseline `n/a` and establish the current run as its first baseline.
