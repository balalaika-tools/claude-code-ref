# Curriculum contract and release gates

Use this contract before choosing files. It records what the collection promises to teach and gives
the author, validator, and independent reviewer the same acceptance target.

## Coverage levels

Use the lowest level that fully describes the intended reader outcome:

| Level | Evidence required |
|---|---|
| `mentioned` | The mechanism is named only for orientation. |
| `defined` | Its kind and basic purpose are grounded locally. |
| `explained` | The note shows the problem, owned state, causal mechanism, and consequence. |
| `demonstrated` | `explained` plus a faithful named trace or artifact and a meaningful contrast when needed. |
| `operationalized` | `demonstrated` plus verification, first real failure, recovery or rollback, and production boundary. |

A mechanism is not covered merely because a heading or definition exists. Core mechanisms on a
first-time path normally reach `demonstrated`; implementation mechanisms promised as production
ready reach `operationalized`.

## Machine-readable plan

Write `<collection>/_meta/learning_contract.json` before drafting. Every path is relative to the
collection root, such as `fundamentals/01_first_result.md`. A path `kind` is one of
`first-time`, `production`, `decision`, or `reference`. Use this shape:

```json
{
  "audience": "Backend engineer with no prior knowledge of this subject",
  "paths": [
    {
      "name": "First-time path",
      "kind": "first-time",
      "entries": ["fundamentals/01_first_result.md", "fundamentals/02_mental_model.md"],
      "execution_payoff_by": 1,
      "understanding_payoff_by": 2,
      "stop_point": "Can run and explain the baseline"
    }
  ],
  "notes": [
    {
      "path": "fundamentals/02_mental_model.md",
      "role": "foundation",
      "prerequisites": ["fundamentals/01_first_result.md"],
      "entry_capability": "Can observe one result",
      "exit_capability": "Can explain the state transition that produced it"
    }
  ],
  "mechanisms": [
    {
      "name": "partition ownership",
      "owner": "fundamentals/02_mental_model.md",
      "required_level": "demonstrated",
      "reader_must_explain": ["why it exists", "who changes it", "what happens on failure"],
      "carrier": "three actors, two partitions, one ownership change"
    }
  ]
}
```

## Foundation decomposition test

A foundation note owns one central mental model. Split or explicitly justify the composition when
its mechanisms have independently changing state, different prerequisites, or separate faithful
carriers. A multi-noun title is a prompt to inspect the composition, not an automatic failure and
not a reason to split simple adjacent definitions.

A deep dive may refine a core mechanism only after an earlier foundation owner has established the
beginner-level model. It cannot silently become the first place where the path teaches that model.

## Evidence-backed teach-back

After each foundation entry, answer using only that entry and earlier path entries:

1. What problem existed before the mechanism?
2. What state or decision does it own?
3. Who or what changes that state?
4. Which named input and transition produce the visible result?
5. Which plausible wrong model does the explanation rule out?
6. What breaks first, and why is the next layer needed?

If any answer requires outside knowledge, later material, or repeating a rule without its cause, the
entry has not reached `demonstrated`.

## Example verification manifest

Write `<collection>/_meta/example_verification.json` with one record for every runnable claim:

```json
{
  "examples": [
    {
      "id": "first-round-trip",
      "note": "fundamentals/01_first_result.md",
      "claim": "runnable",
      "command": "uv run python example.py",
      "environment": "temporary local service",
      "exit_code": 0,
      "observed_output": ["created id=42", "read id=42"],
      "verified": true
    }
  ]
}
```

Use a `claim` value of `runnable`, `copyable`, `integration`, `test`, or `end-to-end`.

Inspection is not execution. If a dependency cannot be run, change the note's claim to an
explanatory excerpt or record it as unverified and report the missing gate. Never manufacture output.

## Release gate

Before delivery, require separate verdicts for:

- structural validation;
- execution verification;
- first-time-path execution payoff;
- first-time-path understanding payoff;
- mechanism coverage at the promised levels;
- independent audit;

Do not summarize these as one undifferentiated `PASS`.
