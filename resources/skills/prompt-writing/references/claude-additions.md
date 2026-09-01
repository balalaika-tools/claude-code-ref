# Claude-Specific Additions

Read this reference only when the target is Claude or the Anthropic API, or when adapting an existing prompt specifically for Claude. The source is Anthropic's current [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices).

These additions supplement the common workflow in `../SKILL.md`. They do not replace its “smallest sufficient prompt” rule. Model behavior and API features change; verify current model-specific documentation before relying on a capability, setting, or message-format detail.

## Examples

Anthropic emphasizes examples as a reliable way to steer Claude's format, tone, structure, classifications, and edge cases. Follow the entrypoint's relevance, variety, and correctness rules. Anthropic commonly recommends several examples, but example count is not a target: start with the minimum that demonstrates the behavior and add more only when evaluation shows a gap. For complex prompts, `<examples>` and `<example>` tags are useful separators.

## XML and other delimiters

When a user message mixes instructions, context, multiple documents, examples, and variable input, XML can reduce ambiguity:

```xml
<instructions>
Summarize the evidence relevant to the decision criteria.
</instructions>

<documents>
  <document index="1">
    <source>...</source>
    <document_content>...</document_content>
  </document>
</documents>

<input>...</input>
```

Use consistent, descriptive tag names and nest only where the content has a real hierarchy. Plain headings are sufficient for simple prompts; XML is not intrinsically better and should not be added decoratively.

## System prompt and long-context placement

If the Anthropic Messages API is the target, put a useful role in the API's top-level `system` field, not inside the `messages` array. Use a role only when relevant expertise, perspective, tone, or decision rules will improve the task. Keep task-specific source material and input in the user message.

For large, multi-document user inputs, Anthropic recommends placing the long material near the top and putting the query, instructions, and examples after it, with document content and metadata clearly labeled. This is a narrow Claude-specific exception to the entrypoint's default outcome-first ordering: keep the outcome explicit, but place the operational query after the documents. Do not apply this ordering to ordinary inputs. For evidence-heavy work, ask Claude to identify the relevant evidence or cite its source location before drawing conclusions; do not require unnecessary long quotations.

## Output and trigger calibration

The style and structure of a prompt can influence Claude's response. When format adherence remains difficult, use a clean structure similar to the desired output in addition to the entrypoint's positive output instructions.

Specify visible response length directly when it matters. Do not assume a reasoning or effort setting will control user-facing verbosity.

If evaluation shows that a Claude prompt overtriggers tools, replace blanket `CRITICAL`, `MUST`, or “when in doubt” language with normal, targeted conditions such as “use this tool when it would improve the result.” Retune from observed behavior and re-check the exact model's current documentation.

## Agentic Claude workflows

When subagents are available, use them for independent parallel work or isolated-context workstreams. Work directly for simple, sequential, single-file, or shared-state tasks where delegation adds overhead or fragments context.

For coding agents, do not treat an obstacle as authorization to delete or overwrite unfamiliar work, bypass safeguards, weaken tests, or take another shortcut outside the approved scope. Keep the entrypoint's impact-based approval boundary.

State tracking or checkpoints can help long-running work only when the runtime actually supports persistence or context compaction. Use structured data for machine-readable status and prose for contextual progress notes. Do not add “use the entire context,” “never stop,” or similar blanket persistence instructions.

## Do not generalize these provider details

Do not make XML, role assignment, a fixed number of examples, long-input placement, prompt chaining, or manual reasoning scaffolds mandatory in provider-neutral prompts. Do not copy model-name-specific defaults, token settings, prefill behavior, or other volatile API details without checking the current official documentation for the exact target model.
