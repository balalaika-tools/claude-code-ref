---
name: simplify-code
description: Inspect and simplify Python-first codebases by removing accidental complexity, redundant abstractions, verbose control or data flow, duplication, and unnecessary indirection while preserving observable behavior, under explicit audit/apply modes with safety gates and verification. Use for code cleanup, clarity refactors, overengineering audits, complexity reduction, changed-code simplification, or repository-wide simplification planning and implementation, including integration with `review-code` / `auto-review-code`. Apply the language-independent structural rubric to non-Python code without claiming framework-specific expertise. For a quick, ungoverned single-file or single-module Python pass instead, use `python-simplifier`.
---

# Simplify Code

Reduce conceptual and maintenance cost, not merely line count. Preserve essential complexity, real boundaries, and observable behavior.

## Resolve mode before substantive work

Require one explicit mode:

- `audit`: inspect and return ranked findings and a proposed plan without editing code.
- `apply`: audit first, then implement safe in-scope changes in verified batches.

If a standalone request does not unambiguously choose a mode, ask exactly one short question in the user's language: "Do you want an audit/report only, or should I apply the safe simplifications as well?" Do not infer mutation permission from a path, repository size, or words such as "check" or "look at."

When invoked by `auto-review-code`, select `audit` without asking. Return candidates only; let that caller own mutation, provenance, safety gates, and convergence. Do not invoke `review-code` or `auto-review-code` from this skill.

## Establish scope and authority

Resolve scope separately from mode:

- For a diff, changed files, or named files, include only directly affected callers and tests needed to judge behavior.
- For a named package or directory, map and rank it before editing.
- For a whole repository, build a repository map and ranked audit first. In `apply`, disclose and edit a bounded set unless the user explicitly requested a broad rewrite.

Exclude generated and vendored code, migrations, snapshots, caches, virtual environments, and build output by default. Inspect `git status` before editing. Preserve all pre-existing work and never overwrite or broadly restore unrelated changes.

## Discover repository constraints

Before proposing changes:

1. Read applicable repository instruction files.
2. Inspect supported Python versions, dependencies, package boundaries, public exports, entry points, framework registration, formatter, linter, type-checker, and test configuration.
3. Read the target code, its focused tests, callers, and implementations. Inspect relevant history when unusual code may be a compatibility workaround.
4. Record existing verification failures before attributing them to a simplification.

Use the repository's configured tools where available. Do not install a tool or add a dependency without authorization.

For repeatable Python inventory, run `python <skill-dir>/scripts/inventory_scope.py ...`; resolve `<skill-dir>` from this installed skill, not the caller's working directory. The script supports explicit paths, manifests, and Git changed-file scopes. Treat its errors, exclusions, and truncation fields as part of the result.

## Build and rank candidates

Read [references/simplicity-rubric.md](references/simplicity-rubric.md) before auditing. For Python, also read [references/python-patterns.md](references/python-patterns.md). Read [references/python-framework-patterns.md](references/python-framework-patterns.md) only when the repository uses a covered framework or facility.

Combine code reading with deterministic evidence. `analyze_structure.py` may generate structural leads; `rank_findings.py` may deduplicate, baseline, suppress, budget, and rank them. Never treat analyzer output as a command to refactor or zero findings as proof of simplicity. Surface parse failures, tool failures, skipped files, and incomplete coverage.

Each retained candidate must identify:

- Exact location and affected files.
- The concept, branch, layer, representation, or duplication that appears unnecessary.
- Current evidence, including callers and counter-evidence.
- A concrete simpler design.
- Observable behavior to preserve.
- Confidence and risk as separate dimensions.
- Targeted verification and any ownership boundary crossed.

Prefer high conceptual reduction with strong evidence, narrow surface, and meaningful tests. Deprioritize cosmetic idioms, uncertain dead code, and changes that introduce a larger abstraction to remove small repetition.

## Protect behavior and real boundaries

Preserve public APIs, imports, values, ordering, mutation, I/O, side effects, exception contracts, serialization, transactions, concurrency, cancellation, and relevant performance.

Keep an abstraction when it materially encodes a domain concept or invariant, enforces policy, separates an I/O/trust/process/ownership boundary, supports current meaningful variation, stabilizes a public contract, isolates volatile external behavior, or improves testing without worsening production navigation.

Never auto-apply without case-specific evidence:

- Public signature, export, CLI, schema, persistence, or wire-format changes.
- Deletion in code using reflection, registries, entry points, callbacks, fixtures, dependency injection, or framework discovery.
- Exception type/message, sync/async, eager/lazy, ordering, cache, transaction, concurrency, or performance-sensitive changes.
- Consolidation across security, tenancy, process, package, or ownership boundaries.
- Removal of test-double or dependency-inversion seams.
- Changes to migrations, generated code, or compatibility shims.

When evidence is insufficient, keep the code and report the candidate or add a characterization test if that is in scope. Never describe inferred equivalence as proven.

## Apply in coherent batches

In `apply` mode:

1. Select one coherent, low-risk structural change.
2. State the behavior contract and the checks that can establish it.
3. Edit only the disclosed files. Avoid unrelated formatting churn.
4. Preserve rationale, invariant, compatibility, performance, and security comments; remove only narration or stale comments.
5. Run the narrowest reliable checks first, then broaden according to risk.
6. Inspect the diff for behavior drift before starting another batch.
7. Stop when the next change has weak evidence, increases indirection, requires broader authority, or cannot be verified proportionally.

Do not weaken, delete, or over-mock tests to make a refactor pass. Read [references/verification.md](references/verification.md) for the verification matrix and behavior checklist.

## Delegate only bounded repository work

For large or disconnected scopes, read [references/delegation.md](references/delegation.md). Delegate only when the user or active environment permits subagents. Partition by cohesive package or dependency cluster after a coordinator maps the scope. Keep one owner per editable file, tests with their production module, and cross-cutting files under coordinator ownership. Run whole-scope duplicate and abstraction analysis once centrally.

Use `shard_plan.py` only to produce a deterministic proposal for worker ownership; it does not authorize delegation or edits.

## Return a reviewable result

For `audit`, report:

- Scope, exclusions, constraints, and coverage gaps.
- Ranked findings with evidence, confidence, risk, behavior contract, and proposed simplification.
- Tempting changes rejected because the complexity is essential.
- Suggested batches and exact verification commands.
- Analyzer/tool failures and remaining uncertainty.

For `apply`, report:

- Files changed and concepts, branches, layers, or representations removed.
- Important behavior deliberately preserved.
- Checks run and exact outcomes, distinguishing pre-existing failures.
- Deferred high-risk or cross-cutting candidates.
- Any incomplete scope or worker shard.

When integrating with `review-code` or `auto-review-code`, emit fingerprints as `{relative_path}:{start_line}|{category}|{short-summary-slug}`. Use `design` or `quality` for ordinary simplification findings, normally at `P3` or rarely `Nit`. Use `P2` only for a material design problem with a concrete failure mode. Route correctness, security, compatibility, data, concurrency, or operational defects through `review-code` rather than relabeling them as simplification.
