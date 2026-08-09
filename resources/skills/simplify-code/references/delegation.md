# Repository delegation

Use delegation only when the user or active environment permits subagents. Repository size alone is not a trigger.

## Coordinator workflow

1. Resolve mode, scope, exclusions, repository rules, tests, and public boundaries.
2. Run deterministic inventory and whole-scope analyzers once.
3. Partition relevant work by cohesive package, subsystem, or dependency cluster.
4. Assign non-overlapping inspection or edit ownership.
5. Collect structured candidates; deduplicate and decide cross-cutting issues centrally.
6. Run shard-level checks for owned edits.
7. Inspect the combined diff and run integrated verification centrally.

Delegate judgment and bounded implementation. Do not rerun the same deterministic scan over arbitrary slices.

## Default sizing

| Relevant scope after exclusions | Strategy |
| --- | --- |
| 1–7 ordinary files, roughly under 1,000 LOC | Coordinator handles directly |
| 8–30 files or several independent modules | 1–3 workers after mapping |
| More than 30 files, roughly over 3,000 LOC, or several subsystems | Package-based bounded waves |

Stop each editing shard at the first applicable soft limit: 5–10 related production files plus tests, roughly 1,000–2,000 source lines, or 15–25 credible findings. Use 1–3 files for core, persistence, concurrency, framework, or public-API modules. With four total slots, use at most three workers and keep the coordinator active.

## Ownership

- Assign one owner per editable file.
- Keep tests with the production module they cover.
- Keep shared configuration, exports, central models, and public interfaces under coordinator ownership.
- Return a `cross_shard` proposal instead of editing outside ownership.
- Do not let workers commit, revert, run repository-wide formatters, clean the worktree, or alter another shard.
- If a shared-worktree check fails, stop and report owned hunks and the failure. Only the coordinator may reverse an exact run-owned patch; never use broad restore operations.
- Run duplicate, abstraction, import/export, and dependency analysis over the complete scope centrally.

## Worker input

Provide owned files, exclusions, relevant findings, repository rules, behavior/public boundaries, allowed risk tier, targeted checks, and the result schema. Do not leak the coordinator's desired verdict; workers must independently accept or reject candidates from evidence.

## Worker result

```json
{
  "shard": "billing",
  "files_inspected": ["billing/tax.py"],
  "files_changed": ["billing/tax.py"],
  "applied": [{"id": "...", "summary": "...", "risk": "low"}],
  "rejected": [{"id": "...", "reason": "abstraction owns a real boundary"}],
  "cross_shard": [{"file": "common/money.py", "proposal": "..."}],
  "checks": [{"command": "pytest tests/billing -q", "result": "pass"}],
  "uncertainty": []
}
```

## Stopping rules

- Rank packages by credible finding density and expected conceptual reduction, not raw file count.
- Disclose bounded waves and never imply an incomplete audit is complete.
- Use at most two simplification passes per shard; report the remainder.
- Run targeted checks per shard and integrated checks once after accepted edits.
- Stop on ownership conflicts, weak evidence, overlapping edits, or required expansion beyond assigned scope.
