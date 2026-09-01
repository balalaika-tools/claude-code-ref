---
name: prompt-writing
description: Create, critique, revise, or adapt prompts for LLM chat and agent workflows. Use when the user asks for a prompt, prompt template, reusable instructions, system/user message design, or improvement for an existing prompt; do not activate merely because an ordinary task contains instructions.
---

# Prompt Writing

Turn the user's goal into the smallest prompt that communicates the intended result reliably. Produce a prompt the user can use; do not perform the underlying task unless they explicitly ask for both.

## Resolve the request

Determine whether the user wants a new prompt, a revision, an adaptation to another model or surface, a reusable template, or a diagnosis of a prompt that underperformed.

Identify the target model, product, or agent only when it changes available capabilities, message roles, syntax, or the appropriate level of autonomy. If the target is unstated and a portable prompt will work, write one without blocking. Ask a concise question only when the missing answer would materially change the prompt and cannot be inferred safely. Otherwise use a clearly named placeholder or state a brief assumption.

Extract only the dimensions that matter:

- **Goal:** the concrete result or behavior wanted.
- **Context:** facts, inputs, prior decisions, and sources that can change the result.
- **Output:** audience, intended use, format, length, detail, and ordering.
- **Boundaries:** invariants, exclusions, scope limits, and actions requiring approval.
- **Verification:** observable evidence that the result is complete or correct.

For an existing prompt, also identify the observed failure. Preserve requirements that already work and make the narrowest change likely to address the failure. Do not restructure it merely to impose a preferred framework.

When a prompt depends on current provider capabilities, tool names, model behavior, syntax, or limits, verify those details in the provider's current official documentation when access is available. Do not invent tools, browsing, memory, filesystem access, context capacity, or permissions that the target does not have.

## Draft the prompt

Start with the desired result. A simple task may need only one or two direct sentences. Add structure only when it removes real ambiguity or protects an important constraint; there is no required formula.

Use these elements conditionally:

- State the deliverable with a precise action verb and put the highest-priority result first.
- Include only context that could alter the answer. Name each source or attachment and say what it contributes. For an image or large file, point to the relevant region or information rather than relying on the attachment alone.
- Describe how the result will be used when that changes its audience, depth, format, or organization.
- Separate required work from optional polish. For ordinary tasks, keep boundaries to the few that prevent consequential mistakes; use more only when risk or complexity warrants it.
- Prefer positive output directions such as “write concise prose” over negative style lists. Keep explicit prohibitions for genuine scope, safety, legal, privacy, or authorization boundaries.
- For current or source-grounded work, request appropriate current sources, distinguish sourced facts from inference, and require missing or conflicting information to be flagged instead of guessed.
- Add an observable final check for important, format-sensitive, factual, coding, or agentic work. Do not substitute vague instructions such as “ensure high quality.”
- Explain the reason behind a non-obvious behavioral rule when the rationale helps the model generalize.
- Prescribe sequential steps only when order, auditability, or completeness matters. Otherwise leave room for the target to choose an effective approach.
- Assign a role only when it supplies relevant expertise, perspective, tone, or decision standards. Omit decorative personas.
- Add examples only when the desired format, tone, classification boundary, or edge case is difficult to specify directly. Use the minimum useful set; make examples relevant, varied, and clearly separated from the actual input.
- Use descriptive headings or delimiters when instructions, source material, examples, and variable input could be confused. Keep simple prompts simple.

Do not request private or hidden chain-of-thought. Ask for the answer, supporting evidence, decision factors, uncertainty, or a check against explicit criteria when those are useful.

For a reusable prompt, use stable, descriptive placeholders such as `[AUDIENCE]` or `[SOURCE_TEXT]`, define any non-obvious placeholder once, and avoid placeholders for facts already available in the conversation.

## Handle action and autonomy explicitly

When the target can use tools or change state, make the requested mode unambiguous: explain, recommend, draft, implement, send, publish, or deploy are different outcomes.

State which important artifacts must remain unchanged and where approval is required. Already-authorized, in-scope local discovery and verification can usually be left to the agent's judgment; destructive, hard-to-reverse, shared-system, financial, or externally visible actions need an explicit boundary. Reversibility alone does not grant permission. Never broaden the user's authorization while rewriting their prompt.

For detailed source-based, research, coding, agentic, reusable, and follow-up shapes, read only the relevant section of [references/prompt-patterns.md](references/prompt-patterns.md). These are assembly patterns, not mandatory templates.

When the target is Claude or the Anthropic API, read [references/claude-additions.md](references/claude-additions.md). Apply those techniques conditionally and do not turn Claude-specific guidance into universal rules.

## Deliver the result

Match the user's requested language and level of detail.

- Put the ready-to-use prompt first in a copyable block. If the target uses distinct system, developer, user, or tool messages, label only the components the user actually needs.
- If the user asks for “just the prompt,” return only the prompt. Otherwise add only brief assumptions, required setup, or material adaptation notes.
- Keep attachment or configuration instructions outside the prompt when they are actions the user must complete before pasting it.
- When revising or diagnosing, include a short explanation of material changes only if requested or useful; do not bury the revised prompt beneath theory or framework names.
- Do not claim that wording is “optimal” or guaranteed to work. If target behavior is uncertain, say what should be tested.

## Validate and refine

Before delivering, check that:

- the desired result appears early and can be understood without hidden context;
- every included context item can affect the result;
- the intended audience and output are usable as written;
- requirements, preferences, and approval boundaries are distinguishable;
- source use, uncertainty handling, and verification are concrete where needed;
- examples and structure earn their extra length;
- the prompt assumes only capabilities the target actually has.

For consequential or recurring workflows, recommend testing the prompt on representative inputs and at least one meaningful edge case. Refine from observed failures one issue at a time. Use a draft → review against criteria → revise sequence only when inspecting the intermediate result has value; automate or reuse the workflow after it behaves reliably.

For consequential or externally shared work, advise the user to review the result after the model's final check and before acting on, sending, or publishing it.

## Source basis

The common guidance is based primarily on OpenAI's [Prompting guide](https://learn.chatgpt.com/docs/prompting). Compatible additions are drawn from Anthropic's [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices). Treat provider-specific behavior as time-sensitive and re-check official documentation when it matters.
