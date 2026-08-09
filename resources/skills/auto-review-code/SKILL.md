---
name: auto-review-code
description: Iteratively review, safely fix, verify, and re-review code until safe automation converges or requires a decision. Use only when the user explicitly asks to auto-review, auto-fix review findings, clean up a branch, or repeat review-and-fix without approving each local change. Mutates the working tree under a conservative change-shape gate, test-first policy, provenance tracking, round limits, and hard stops; do not use for a read-only review.
---

# Auto Review Code

Use the sibling `review-code` skill as the read-only judgment layer, then apply only changes that are demonstrably safe for automation. Treat the boundary between review and mutation as user consent: a request to review never authorizes this skill.

## Confirm preconditions

Require an explicit auto-fix request. Resolve the same review scope and intent in every round. Require the sibling `review-code` skill. Invoke it by name when the host supports skill invocation; otherwise read `../review-code/SKILL.md` completely and follow it as the review phase. If neither route is available, stop instead of inventing a substitute review policy. Use an available code-simplification skill only as an optional pass; skip it and note the omission when absent.

Before editing:

- Read repository instructions and caller overrides.
- Record `HEAD`, the exact scope, `git status --short`, staged changes, unstaged changes, and relevant untracked files.
- Preserve every pre-existing change as user-owned. Never stage, commit, push, switch branches, move `HEAD`, or rewrite history.
- Choose a caller-supplied log path when provided. Otherwise use `.agent-work/auto-review-code-log.md` only when that tool-neutral directory already exists or repository rules explicitly allow it; fall back to an operating-system temporary path when it does not. Exclude the log from review scope and never overwrite a tracked file.
- Set a maximum of five rounds unless the user requests a smaller limit.

Send concise progress updates during a long run, but defer detailed findings to the stop or final summary.

## Classify by change shape

Scan the complete review report for `P0` before applying anything. A `P0` halts the round immediately.

Auto-apply a non-`P0` finding only when every condition holds:

1. The fix is local and isolated, normally at most 5 files and about 50 changed lines excluding a focused regression test.
2. The required edit is concrete and has one unambiguous implementation.
3. The intended behavior is established by requirements, existing behavior, or a regression test—not by the finding's wording alone.
4. The fix introduces no package, dependency, module, production file, service, or infrastructure.
5. The fix does not touch generated or vendored files, lockfiles, snapshots, migrations, schemas, deployment policy, or build topology.
6. The fix does not change a public API or exported type, configuration/default contract, authorization policy, data migration, concurrency protocol, user-facing behavior/copy, or observability semantics.
7. The edit does not overlap user-owned changes, and its exact patch can be reversed independently.
8. Relevant focused verification exists and can run successfully.

Priority expresses impact, not edit safety. A `P1` may require approval while a `P3` may be safely mechanical. When any gate is uncertain, request approval rather than applying.

Allow narrow security fixes such as parameterizing a proven injection sink or escaping output only when a safe regression test demonstrates the exploit, valid-input semantics stay unchanged, and every other gate passes. Always require approval for authorization changes, ownership scoping, validation tightening, trust-boundary changes, cryptography, secret handling, or security fixes whose compatibility impact is uncertain.

Examples that always require approval include:

- Changing config defaults, schemas, migrations, public signatures, serialization, or error contracts.
- Adding dependencies, modules, services, or broad architectural refactors.
- Changing permissions, accepted inputs, return shapes, UI/copy, logs, metrics, or external side effects.
- Inlining a production helper that may be an extension point.
- Replacing a public primitive type with a codebase alias, even when structurally equivalent.
- Touching many call sites or relying on an unstated product decision.

## Verify before and after

For correctness, security, compatibility, performance, and behavior findings, prefer a regression test before the fix:

1. Add the smallest test that reproduces the exact failure using safe local fixtures.
2. Run it before the fix and confirm it fails for the expected reason.
3. If it passes unchanged, attempt to refute the finding. Reject it when the test genuinely covers the scenario; otherwise move it to approval with the missing evidence stated.
4. Apply the isolated fix.
5. Run the new test, its containing test file or nearest focused suite, and any cheap relevant type/lint check.
6. Confirm the test fails again if the fix alone is temporarily reversed when practical; use this mutation check for subtle fixes where a false-positive test is plausible.

Do not auto-apply a testable behavior or security fix when test infrastructure is missing, unsafe, or prohibitively slow. Move it to approval. Never exercise an exploit against production, shared services, or real user data.

For mechanical, behavior-preserving edits, rely on existing focused tests plus applicable lint/type/build checks. Documentation-only edits need only format/link verification when available.

A standalone coverage finding may add at most 5 concrete cases and 100 lines to an existing test file. Permit one new test file only when the repository has an established colocated layout and the file requires no new fixtures, services, harnesses, or infrastructure. Run the tests against unchanged production code; if they fail, treat the result as a newly reproduced defect and stop for triage.

## Preserve edit provenance

Record the exact patch for each test and fix before moving to the next finding. Recheck repository status after each application. Attribute only those recorded hunks to this run.

If verification fails, reverse only the run-owned patch. Never use broad `git restore`, `git checkout`, `git reset`, or file replacement that could discard user changes. If an owned patch overlaps pre-existing or newly arrived edits, or cannot be reversed independently, stop and ask for direction. Report any unowned change detected during the run; continue only when it is clearly disjoint from the active scope.

## Run the convergence loop

For each round:

1. Invoke the `review-code` skill read-only with the unchanged scope, intent, repository rules, and caller overrides.
2. Scan for `P0`; halt before all mutations if present.
3. Refute and classify every remaining finding as `auto-apply`, `approval-needed`, or `rejected`.
4. Build approval dossiers while context is fresh.
5. Compare each auto-apply fingerprint with prior rounds; do not reapply a returning finding.
6. Apply eligible review fixes one at a time with provenance and verification.
7. If a code-simplification skill is available, run it on the same scope. Treat its proposals as new candidates and apply the same gates; do not assume a simplification is behavior-preserving.
8. Run the strongest focused verification justified by the accumulated edits.
9. Append the round's findings, actions, owned patches, checks, and status to the log.
10. Re-review the same scope unless an exit condition applies.

Preserve the review fingerprint `{relative_path}:{start_line}|{category}|{short-summary-slug}`. Match a returning finding when path, category, and slug agree and the line moves by at most three lines. If a broader refactor moves the code farther, use semantic judgment and record the mapping rather than evading oscillation detection.

## Stop deliberately

Stop on the first applicable condition:

- **P0 halt:** report the evidence and wait for direction.
- **Safe convergence:** a full review plus optional simplification round produces no auto-applied changes and no unresolved blockers.
- **Approval boundary:** only approval-needed findings remain. Return them together for one decision pass.
- **Round limit:** complete five rounds without convergence.
- **Oscillation:** an applied fingerprint returns; move it to approval. Stop immediately if the same finding returns a second time.
- **Verification loop:** three consecutive candidate fixes fail verification.
- **Ownership conflict:** an edit cannot be isolated from user work or repository state changes unexpectedly.
- **User override or stop:** honor new constraints immediately and record them.

Convergence means safe automation is dry; it does not mean unresolved approval items are correct to ignore.

## Build approval dossiers

For each approval-needed item, include:

- **Proposal:** one precise before-to-after change. Test whether an apparent either/or choice has a stronger conditional or hybrid resolution.
- **What the user sees:** required for UI, copy, API responses surfaced to people, or other user-visible changes; show exact before/after behavior.
- **Pros if applied:** concrete benefits tied to actual callers, files, or behavior.
- **Cons if applied:** concrete failure scenarios, affected actors, and operational cost.
- **Recommendation:** use exactly `apply`, `skip`, `apply if <condition>, else skip`, or `no strong opinion — depends on <question>`, with confidence when making a recommendation.
- **To apply:** state the exact approval phrase or prerequisite.

Do not disguise indecision with `consider` or `may be acceptable`. Name the missing decision or evidence.

## Maintain the run log

Keep the log compact and machine-readable enough for later audit:

```markdown
# Auto review log
Scope: origin/main...HEAD
Baseline: <HEAD and initial status>
Started: <ISO-8601 timestamp>

## Round 1
- <fingerprint> | <priority> | <auto-applied|approval-needed|rejected>
  - patch: <owned files/hunks>
  - test: <before result> -> <after result>

## Exit
- reason: <condition>
- final status: <status summary>
```

Never put secrets, full source files, or exploit payloads beyond what is necessary into the log.

## Return the final summary

Report:

```markdown
## Auto review complete
**Scope:** <scope> · **Rounds:** <count> · **Exit:** <condition>

### Auto-applied
- [P1] `path:line` — concise fix (+ regression test/check)

### Approval needed
1. **[P2] Title** — `path:line`
   **Proposal:** ...
   **Pros if applied:** ...
   **Cons if applied:** ...
   **Recommendation:** ...
   **To apply:** ...

### Rejected or unverified findings
- <finding and refutation or missing evidence>

### Verification
- Ran: ...
- Not run: ...
- Failures/oscillations: ...
- Pre-existing changes preserved: ...

Log: `<path>`
```

Omit empty finding sections, but always report verification, the exit reason, log location, and preservation of pre-existing changes.
