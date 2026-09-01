# Prompt Patterns

Use only the pattern that matches the request, and omit any section that does not change the result. These are starting shapes, not forms that must be filled completely.

## Minimal outcome prompt

Use for clear, low-risk, one-shot requests.

```text
[Create, explain, compare, or change the desired result] for [audience or use].
Prioritize [the quality that matters most]. Return [output form, if it matters].
```

If the first sentence already determines the audience and output, stop there.

## Source-based deliverable

Use when several inputs must become one reviewable artifact.

```text
Create [deliverable] for [audience and use]. Put [highest-priority content] first.

Context and sources:
- [SOURCE 1]: use it for [specific facts or decisions].
- [SOURCE 2]: use it for [specific facts or decisions].

Output:
- [format, length, organization]
- Distinguish source-reported facts from your analysis.

Boundaries:
- Preserve [approved fact, wording, value, or scope].
- Flag missing, conflicting, or unverifiable information instead of guessing.

Before finishing, verify [observable consistency or completeness check].
```

Do not attach sources without explaining their role. When the material is large, label documents and relevant metadata clearly. Ask for citations or evidence locations when the user must be able to audit the result.

## Current research or decision support

```text
Research [decision or question] as of [relevant date or date range] for [decision context].
Use current, authoritative sources and include links for material claims.
If current source access is unavailable, state that limitation instead of substituting memory for verified current facts.

Compare [options] using [decision criteria]. Keep recommendations within [budget, policy, geography, or other constraint].

Deliver [memo, table, shortlist, or recommendation] for [audience]. Separate sourced facts, assumptions, and analysis. Explain the decisive tradeoff and list unresolved questions that should be answered before acting.
```

Add cross-source verification when a claim is consequential or disputed. Ask for competing explanations only when genuine ambiguity warrants them; do not manufacture debate or numeric confidence scores.

## Coding: understand, fix, or change behavior

For explanation:

```text
Explain [behavior or flow] in [relevant files, functions, or selected code].
Focus on [specific concern]. Identify the files involved, important invariants, and practical risks of changing it.
```

For a reproducible bug or scoped change:

```text
Desired behavior: [target behavior]
Current behavior: [what happens now]

Reproduction or evidence:
1. [step, error, failing test, or observed output]
2. [...]

Relevant code: [paths, symbols, or selection]

Constraints:
- Preserve [public API, data shape, behavior, or compatibility requirement].
- Keep changes within [scope]; do not add unrelated cleanup.

Verify by [rerunning the reproduction] and [the smallest relevant checks]. Report the commands or checks and their results.
```

When adapting from a screenshot or mock, state behavior the image cannot show: interaction states, validation, responsive behavior, accessibility, routing, and implementation constraints.

When the user manually changes or reverts an edit between iterations, include that fact in the next prompt and state what the agent must preserve.

For a large refactor, define the stable external behavior and a reviewable milestone. Ask for a plan before edits only when the approach or migration order needs approval.

## Agentic or state-changing work

```text
Outcome: [single reviewable result]

Starting context:
- [workspace, artifacts, existing state]

Allowed work:
- [discovery, edits, tests, or reversible local actions]

Preserve:
- [critical artifact or invariant]

Ask before:
- [destructive, hard-to-reverse, shared-system, financial, or externally visible action]

Done when:
- [observable acceptance and verification criteria]

At completion, report [artifacts changed, checks run, unresolved issue].
```

Say explicitly whether the agent should only recommend, prepare a draft, or carry out the action. Name tools only when they are available and the choice matters. Independent discovery may run in parallel; operations that depend on earlier results must be sequenced. Missing tool parameters must be discovered or requested, never invented.

## Reusable system and user messages

Split messages only when the target surface supports roles and the distinction has value.

```text
SYSTEM
[Durable behavior, expertise, decision rules, and cross-request boundaries.]

USER
[Current goal, task-specific context and sources, requested output, and input.]
```

Keep enduring preferences in the platform's persistent-instruction mechanism when one exists. Keep current facts, temporary constraints, and the actual input in the task message. Do not repeat the same rule across every message layer.

For a reusable task prompt, group variable data under a clear delimiter:

```text
Task: [stable instruction]

Input:
[SOURCE_TEXT]

Return: [stable output contract]
```

## Few-shot pattern

Use examples when direct wording has not made a format, tone, label boundary, or edge case reliable.

```text
[Task and output rule]

Examples:

Example 1
Input: [representative input]
Output: [desired output]

Example 2
Input: [meaningfully different or edge-case input]
Output: [desired output]

Actual input:
[INPUT]
```

Examples must be correct, relevant, and varied. Remove accidental features the model could imitate. Prefer the smallest set that demonstrates the behavior; add examples because evaluation shows they help, not as decoration.

## Focused follow-up

Prefer a small follow-up over rewriting a long prompt when the first result is mostly correct.

```text
Change only [specific scope].
Make [concrete adjustment].
Keep [evidence, structure, tone, facts, or behavior] unchanged.
Also check [one observable condition].
```

If the target is already running and its interface distinguishes steering from queued work, say whether the change should affect the current run or the next one.

## Diagnose and revise an existing prompt

Use the observed output, not generic “best practice,” as the main evidence.

1. Restate the intended result and the concrete failure.
2. Locate the smallest likely cause: ambiguous goal, missing context, conflicting priority, unusable output contract, weak source grounding, absent boundary, assumed capability, or an unrepresented edge case.
3. Preserve instructions that are already working.
4. Revise the prompt and explain only material changes.
5. Suggest a representative test that could falsify the fix.

If several causes are plausible, change one variable at a time or compare a small number of variants against the same test inputs.
