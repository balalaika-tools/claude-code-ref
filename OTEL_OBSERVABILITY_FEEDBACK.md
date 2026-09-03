# Feedback: `otel-observability`

## Overall assessment

This is an unusually thorough observability skill. Its strongest qualities are the explicit boundary-ownership model, careful treatment of asynchronous and durable trace handoffs, versioned compatibility contract, privacy-aware GenAI content handling, and meaningful deterministic validation. It is closer to a maintained observability playbook plus implementation library than a typical prompt-only skill.

The main opportunity is to make the package easier to invoke and safer to reuse outside the organization that authored its policies. The content is strong, but the entry point currently combines discovery, organization policy, routing, and implementation invariants. That makes automatic selection broad, loads a large amount of context for small tasks, and presents several local choices as universal OpenTelemetry requirements.

## Highest-priority feedback

### 1. Separate organization policy from general OpenTelemetry guidance

Several rules are defensible house policies, but the description markets the skill as general OpenTelemetry implementation guidance. Examples include:

- prohibiting all first-party span events;
- always introducing `LOG_FULL_EXCEPTION_TRACE` with a production default of `true`;
- requiring OTLP push and excluding Prometheus pull readers and scrape verification;
- imposing `app.*` as the organization namespace;
- prescribing one particular GenAI destination-projection design.

The text calls the exception behavior a “house contract,” but the rest of the entry point makes these rules unconditional. Most importantly, full exception traces can contain secrets and personal data even after credential-oriented redaction, so a default of `true` should be an explicitly selected organizational policy rather than a silent cross-environment default.

Recommended change: introduce a short `references/policy.md` (or a named policy profile) that distinguishes:

- OpenTelemetry/spec constraints;
- safe defaults the agent may normally choose;
- organization-specific decisions that must be selected, discovered in repository guidance, or confirmed by the user.

Then have `SKILL.md` say that repository policy wins for all of these decisions, not only for most guidance while preserving a hard-coded exception for scrape transport. If these policies truly are mandatory for one organization, narrow the skill description accordingly so it does not present itself as a general-purpose skill.

### 2. Reduce the unconditional context footprint

The validator reports an unconditional load of **1,080/1,100 lines**, leaving only 20 lines of its self-imposed budget. That set consists of `SKILL.md`, naming, errors, and verification. The router alone is 298 lines.

This undercuts the package's otherwise good progressive-disclosure design. A missing-span troubleshooting request or narrow package upgrade does not need the full naming registry, error contract, and 334-line acceptance checklist before useful work begins. There is also routing tension between:

- “troubleshooting only, then the single file it points at”;
- “the two files every code sample depends on”; and
- “verification always, last.”

Recommended change:

1. Keep `SKILL.md` to mode selection, scope, a small set of genuine invariants, and links.
2. Route naming and errors only when code or a telemetry schema is being changed.
3. Route verification according to the affected signals and boundary rather than loading the entire checklist.
4. Move the long “What not to do” list beside the references that own each prohibition; much of it repeats earlier rules.

A target around 400–600 unconditional lines would make the skill meaningfully cheaper without weakening its implementation references.

### 3. Fix discovery blockers so they block only the work they actually affect

[`SKILL.md`](resources/skills/otel-observability/SKILL.md), lines 41–52, says the backend question blocks work, but its explanation says only exporter and Collector configuration depend on the answer and then correctly observes that application instrumentation can remain topology-neutral. [`references/discovery.md`](resources/skills/otel-observability/references/discovery.md), lines 163–199, repeats the requirement to ask.

This can unnecessarily stop a well-scoped request such as “add trace context propagation to this queue consumer.” Make the boundary explicit:

- backend choice blocks backend-specific exporters, credentials, Collector routing, and backend-specific projections;
- carrier shape blocks consumer propagation implementation;
- neither should block unrelated, topology-neutral instrumentation.

Also soften “Post this back before you start editing” for small tasks. A mandatory 14-line intake report is valuable for broad implementations, but noisy for a focused fix. Use it only when several discovery dimensions are relevant or when assumptions materially affect the design.

### 4. Make validation reproducible and less coupled to prose

The package validator passes when run in an environment containing `PyYAML`, but the documented command does not work in this repository as checked out:

```text
$ python3 resources/skills/otel-observability/scripts/validate_skill.py \
    resources/skills/otel-observability
PyYAML is required: install it before running validation
```

`PyYAML` is not declared in the root [`pyproject.toml`](pyproject.toml), while [`references/compatibility.md`](resources/skills/otel-observability/references/compatibility.md), line 87, says the script runs “without any external toolchain.” Declare the dependency in a validation/dev dependency group, provide a self-contained supported command, or change the claim. The command that passed during this review was:

```bash
uv run --no-project --with pyyaml python \
  resources/skills/otel-observability/scripts/validate_skill.py \
  resources/skills/otel-observability
```

The 1,978-line validator also contains many exact string, phrase-count, and prose-heading assertions. These preserve known regressions, but they make harmless rewriting expensive and can create confidence without exercising actual behavior. Only specially tagged “complete” Python blocks are compiled; most Python examples are not tagged, and string matching is used for many of their invariants.

Recommended change:

- keep structural checks, allowlists, YAML parsing, fixture execution, and numeric calculator tests;
- convert important code templates into importable example modules or extract and execute them with lightweight stubs;
- replace exact prose assertions with semantic fixture tests where possible;
- keep a small number of wording checks only where exact wording is itself a required safety control;
- run `--collector-image` in CI so a passing local result cannot be mistaken for Collector-image validation.

## Additional improvements

### Narrow the discovery description

The frontmatter description is 98 words/787 characters and enumerates nearly every feature and runtime. It is likely to attract broad logging, metrics, upgrade, and troubleshooting requests even when another specialized skill would be a better match. A shorter description should identify the core capability, the principal Python/OTel boundary, and one or two important exclusions.

For example:

> Implement or review OpenTelemetry tracing, metrics, and correlated structured logging in Python services, including async work and GenAI calls. Use for service instrumentation, propagation, Collector routing, and telemetry-specific troubleshooting; do not use for generic application logging or backend operations unrelated to OpenTelemetry.

### Remove or populate the placeholder `references/local/`

The package includes an empty `references/local/` containing only `.gitkeep`, while the router says to load repository-specific mappings from it. Empty scaffolding adds a promise that the package does not currently fulfill. Remove it until a concrete local mapping exists, or add a small index explaining how and when maintainers should populate it.

### Add behavioral scenario tests for routing

The deterministic checks prove many package invariants, but they do not prove that an agent chooses the smallest correct reference set or avoids unnecessary questions. A small scenario suite would add more value than additional phrase assertions. Suggested cases:

- repair duplicate FastAPI spans in an already-instrumented service;
- add SQS propagation without changing deployment/export topology;
- audit a tracing-only service without loading GenAI or full logging implementation material;
- upgrade only the Collector image;
- troubleshoot missing streamed token usage;
- instrument a non-Python service using only the language-neutral portions.

Expected results should assert selected references, questions asked, files touched, and explicit non-goals—not generated prose.

## What is working especially well

- The mode table is the right architectural idea; it prevents a complex package from becoming one giant workflow.
- “One owner per boundary” is a crisp and useful rule that addresses a common real-world failure mode.
- Async handoff guidance distinguishes parentage from links and treats durable context as data that must be written atomically with work.
- GenAI content capture is opt-in and carefully separates canonical semantic attributes from backend presentation.
- The compatibility contract pins unstable surfaces, records review dates, and provides a concrete upgrade checklist.
- Production sampling guidance correctly demands measured traffic and trace-shape inputs rather than copying example percentages.
- The validator catches broken local references, invalid YAML/templates, naming drift, cardinality mistakes, and several previously observed regressions.

## Suggested implementation order

1. Fix the undeclared `PyYAML` validation dependency and add the full validator command to CI.
2. Split organization policy from portable OpenTelemetry guidance, especially exception detail and transport policy.
3. Resolve the discovery blocker contradiction and make the intake report conditional.
4. Slim `SKILL.md` and route verification/naming/error references per mode.
5. Gradually replace prose-coupled validation with executable fixtures and routing scenarios.
6. Remove the empty `references/local/` placeholder.

## Validation performed for this review

- Inspected the complete skill package structure: 53 tracked files and approximately 12,862 lines including scripts.
- Ran the official skill frontmatter/reference validator through the package validator.
- Ran `scripts/validate_skill.py` successfully with `PyYAML` supplied explicitly.
- Result: `PASS: otel-observability skill validation`.
- Reported context footprint: `1080/1100 lines (20 spare)`.
- Did not run `--collector-image`; therefore the Collector examples were parsed by the local validator but were not checked against the pinned Collector container image.
