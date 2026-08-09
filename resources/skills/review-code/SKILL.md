---
name: review-code
description: Perform read-only, evidence-backed code reviews against requirements and repository conventions. Use when asked to review a pull request, branch, commit range, staged or working-tree changes, explicit files, a completed implementation, refactor, bug fix, migration, dependency update, or AI-generated code before merge. Return prioritized findings with file-and-line evidence, stable fingerprints, verification gaps, and a merge verdict; never modify the reviewed code.
---

# Review Code

Review a defined change for user-impacting defects and material maintainability risks. Optimize for risk reduction and precision, not finding volume. Approve code that improves the codebase even when it is not how you would have written it.

## Preserve the consent boundary

Keep the review read-only. Do not edit files, update snapshots, format code, install dependencies, stage changes, commit, move `HEAD`, switch branches, create worktrees, or change repository state. Do not invoke an auto-fix workflow unless the user separately requests mutation.

Treat tests, linters, type checks, and builds as observational verification only. Before running them, inspect the worktree and avoid commands that generate tracked files, apply fixes, or update dependencies. Recheck repository state afterward. If a command creates or changes artifacts, report them and do not silently remove them.

## Establish the review contract

Resolve scope, intent, and ground rules before judging the implementation.

### Resolve scope

Honor caller-supplied scope exactly. Do not widen explicit paths into a repository audit or mix staged, unstaged, and committed changes without saying so.

Use one of these modes:

- **Pull request or branch:** prefer the caller or PR base. Otherwise resolve the remote default branch, `main`, or `master`, in that order. Do not mistake a feature branch's tracked remote branch for its merge base. Review branch-introduced changes from the merge base, such as `git diff BASE...HEAD`; do not assume `main..HEAD` describes a PR accurately after the base branch advances. Do not fetch solely to discover a base unless authorized.
- **Commit range:** inspect the exact endpoints supplied by the caller.
- **Staged:** use the index diff only.
- **Working tree:** inspect unstaged changes and explicitly listed untracked files; state whether staged changes are excluded.
- **Paths:** inspect only the supplied files or directories as they currently exist, plus the minimum surrounding context needed to understand them.

If plausible scopes differ materially and local context cannot resolve them, ask for the scope instead of guessing.

### Resolve intent

Read the task, plan, acceptance criteria, PR description, issue, or caller summary. If none is available, infer intent from tests, commit messages, and surrounding code, then label the inference. Compare the implementation with the requirements and report both omissions and unjustified deviations. If the requirements or plan are defective, distinguish that from an implementation defect.

### Load ground rules

Read applicable repository instruction and review-guideline files before reviewing code. Honor caller-supplied notes such as intentional compatibility breaks or excluded findings. Treat conventions as evidence, not a substitute for engineering judgment.

## Inspect the change

1. **Frame the change.** Summarize the intended behavior in one or two sentences. Inspect the diff summary and changed-file list before individual patches. Treat change size as a review-risk signal, never an automatic blocker.
2. **Read tests first.** Use tests to understand intended behavior and assumptions. Ask whether they would fail for the regression at issue, not merely whether tests exist.
3. **Read implementation in context.** Open every reported location. Trace changed call sites, data flow, error handling, and invariants far enough to judge system behavior. Read contextual code outside scope when necessary, but do not report unrelated pre-existing defects.
4. **Inspect non-code changes.** Review migrations, configuration, generated artifacts, dependency manifests, lockfiles, CI, deployment files, and documentation whenever the change touches them.
5. **Run focused verification when safe.** Prefer the smallest relevant tests, type checks, lint, build, or manual/visual checks. Never claim a check passed unless it was executed successfully.
6. **Refute candidate findings.** For each candidate, name the concrete input, state, timing, or call sequence that causes failure. Search for guards, validation, callers, and tests that may disprove it. Drop pattern-only suspicions. When decisive evidence is unavailable, lower confidence and state exactly what remains unverified; uncertainty never raises priority.

## Apply the review sweep

Always assess:

- **Requirements and correctness:** behavior, edge cases, failure paths, unintended side effects, state consistency, and backward compatibility.
- **Security and authorization:** untrusted inputs, injection, output encoding, secret exposure, authentication, ownership scoping, and least privilege.
- **Data integrity and concurrency:** transactions, ordering, idempotency, races, retries, timeouts, cancellation, and cleanup.
- **Tests and verification:** meaningful regression coverage, realistic boundaries, negative cases, and whether the verification story supports the claim.
- **Architecture and maintainability:** separation of concerns, dependency direction, duplication, explicit type boundaries, and whether a refactor removes complexity instead of relocating it.
- **Performance and operations:** query count, bounded work, blocking operations, hot paths, resource use, failure visibility, rollout, and rollback.
- **Change hygiene:** dependencies, migrations, configuration contracts, documentation, and orphaned code introduced by refactors.

Add depth only when the change touches the area:

| Area | Inspect |
| --- | --- |
| Database or ORM | N+1 behavior, transaction and lock scope, migration ordering/reversibility, indexes, rollback |
| Public API or serialization | Compatibility, versioning, request/response and error shapes, defaults, unknown fields |
| Authentication or permissions | IDOR, tenant/owner scoping, privilege changes, policy enforcement point, auditability |
| Frontend | State/effect dependencies, stale closures, rendering cost, accessibility, responsive behavior, loading/error/empty states |
| CI or deployment | Untrusted input execution, token permissions, secret exposure, environment parity, rollout and rollback |
| Dependencies | Need, changelog/migration notes, lockfile and transitive changes, license, maintenance, vulnerabilities |
| Async or concurrent code | Ordering, cancellation, timeout, retry safety, idempotency, races, resource cleanup |

## Make findings actionable

Report an issue only when it is introduced by the reviewed change, made reachable or materially worse by it, or required to establish the change's correctness. Anchor it to the smallest useful changed line or the closest line that must be repaired.

For every finding:

- State what is wrong and the concrete failure scenario.
- Explain the affected user or system and why the impact matters.
- Recommend one repair direction when the fix is not obvious.
- Assign one priority and one category.
- Generate a stable fingerprint.

Deduplicate findings that share a root cause. Lead with correctness and security, then material design, resilience, performance, and test gaps. Keep nits sparse. Do not report personal style preferences, vague future-proofing, or code you did not read. Report newly orphaned code, but never delete it during review.

For structural issues, name the move: collapse duplicate branches; replace repeated conditionals with an explicit model or dispatcher; separate orchestration from business logic; move feature behavior into its owning module; reuse the canonical helper; make the type boundary explicit; or delete a pass-through wrapper. Prefer the remedy that removes concepts and moving pieces.

## Calibrate priority and verdict

Assign priority from impact and likelihood, never fix difficulty:

| Priority | Meaning | Merge action |
| --- | --- | --- |
| `P0` | Demonstrable RCE, injection reaching code or protected data, authorization bypass, data loss/corruption, exposed production secret, or broadly broken critical path | Surface immediately and stop; require direction |
| `P1` | Reproducible correctness, security, compatibility, or operational defect likely to affect users | Fix before merge |
| `P2` | Material design, resilience, performance, or test gap with a nameable failure mode | Fix before merge or defer with explicit owner and justification |
| `P3` | Localized maintainability, simplification, or low-risk coverage improvement | Non-blocking follow-up |
| `Nit` | Style or polish with no meaningful risk | Optional; use rarely |

Use one verdict:

- **Ready:** no blocking findings.
- **Ready with follow-ups:** only `P3`/`Nit` findings remain, or every `P2` has already been explicitly accepted with an owner and justification.
- **Not ready:** any `P0`, `P1`, or unresolved `P2` remains.

## Return this report

Put findings first and omit empty optional sections. If no defects meet the bar, write `No actionable findings.` instead of inventing suggestions.

```markdown
## Findings

### [P1] Scope order lookup to the authenticated account
`src/orders.py:84` · `access`
Fingerprint: `src/orders.py:84|access|scope-order-to-account`

The query loads an order by ID without constraining the authenticated account. A user who learns another order ID can read that account's data.

**Fix:** add the account constraint at the query boundary and a cross-account regression test.

## Verdict
**Not ready.** One access-control blocker must be fixed.

## Verification
- Scope: merge-base diff `origin/main...HEAD` (6 files).
- Inspected: all changed files and relevant order call sites.
- Ran: `pytest tests/test_orders.py` — passed.
- Not run: full suite.
- Residual gap: upstream gateway scoping was not independently verified.

## Strengths
- The new error mapping preserves the public response shape at `src/errors.py:31`.
```

Use fingerprint format `{relative_path}:{start_line}|{category}|{short-summary-slug}`. Use a lowercase hyphenated slug of at most 40 characters. Prefer these categories: `correctness`, `compatibility`, `security`, `access`, `data`, `concurrency`, `performance`, `design`, `testing`, `quality`, `operations`, `dependency`, or `documentation`.

Always include `Verdict` and `Verification`, including reviewed scope, what was inspected, commands actually run, commands not run, and residual uncertainty. Keep `Strengths` short, specific, and evidence-backed; omit it when it would be filler.
