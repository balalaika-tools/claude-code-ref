# Behavioral expectations

- `shallow_formatted.md` must not reach `demonstrated`: it has the expected formatting but no owned
  state, actor/decision trace, changed-input contrast, or causal first-failure explanation.
- `demonstrated_foundation.md` should reach `demonstrated`: it supplies the problem, stored state,
  actor, transition, contrast, misconception boundary, and first failure.
- `broken_runnable.md` must receive execution status `BROKEN` because the referenced local script
  does not exist; inspection of the command is not verification.
- `verified_runnable.md` must receive execution status `VERIFIED` only after the exact command is
  run from the fixture directory and its output matches.
- `overloaded_foundation.md` must fail coverage: it defines six independently stateful mechanisms
  without explaining or demonstrating any of them.
- The contract's first-time path must fail prerequisite order because
  `01_uses_later_concept.md` depends on `02_defines_later_concept.md`, which appears later.
- `lease renewal` must fail role ownership because its first-time canonical owner is a deep dive and
  achieves only a definition rather than the promised demonstration.
- `stale_current.md` must receive a dated primary-source currency finding; the reviewer must not rely
  on memory or silently treat a historically valid architecture as current.

Evaluate verdicts and reader outcomes, not exact report wording.
