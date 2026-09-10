---
name: docs-generator
description: Generate or update a repository's docs/ wiki from source code, configuration, tests, and infrastructure. Use for repository operating manuals, engineering onboarding documentation, or keeping architecture, service, development, deployment, and operations guides aligned with code. Not for standalone API-spec conversion or a small README-only edit.
---

# Repository Docs Generator

Build a human-readable, AI-navigable operating manual: what the system does, where behavior lives, how to run and change it, and how to operate and recover it. Adapt coverage to the actual repository. A library, CLI, mobile app, and multi-service platform need different manuals.

## Scope and defaults

- Use `docs/` unless the user or repository establishes another location. Preserve existing documentation tooling, language, URLs, and useful authored content. Default new prose to the user's requested language, otherwise the existing documentation language, otherwise English.
- For full generation, discover the repository before choosing pages. For updates, inspect the requested changes and their consumers, then update affected pages and navigation. Do not regenerate unrelated prose or move established pages merely to match a suggested layout.
- Keep changes to documentation, its assets, and necessary navigation links. Do not change application code, CI, infrastructure, or agent instructions to make the documentation true. Report mismatches instead. Adding a docs platform or publishing the wiki is a separate task.
- Proceed with reasonable defaults. Ask only when a missing choice materially blocks useful work; record unavailable operational knowledge as a gap and complete the supported sections.

## 1. Discover sources and operating boundaries

Read repository instructions and check worktree status. Inventory files with `rg --files` and targeted searches; inspect entrypoints and representative implementations rather than dumping the entire repository. Exclude dependencies, build outputs, caches, and vendored code unless relevant to the requested scope.

Look for existing docs, manifests and lockfiles, task runners, executable scripts, application entrypoints, configuration loaders, example environment files, tests, migrations, API schemas, workers and event handlers, containers, infrastructure, CI/CD, authentication, and telemetry. Trace manifest script definitions before recommending their commands.

For monorepos, distinguish deployable services, shared libraries, applications, and infrastructure. Identify who owns state and interfaces. Trace representative end-to-end paths through producers, consumers, persistence, and error handling; do not infer behavior from directory names or dependencies alone.

Maintain a working evidence map: topic → relevant files/symbols → observed behavior → uncertainty → destination page. It can remain working notes; do not generate a second catalog that duplicates the manual.

## 2. Resolve facts before writing

- Ground factual claims in inspected implementation, configuration, tests, or maintained specifications. Cite exact repository-relative paths with links and useful symbol names. Prefer stable paths over brittle line numbers.
- Distinguish implemented behavior, declared deployment configuration, test expectations, and observed runtime results. Repository configuration does not prove what is deployed. Tests that were only read were not executed.
- When sources disagree, trace the relevant execution path. Explain unresolved discrepancies with both sources; do not silently choose a convenient narrative. External documentation can explain a dependency but cannot establish how this repository uses it.
- Label material gaps `Not determined from repository`, including the missing fact, where you looked, and how it could be verified. Use `Not applicable` only when evidence supports it. Label proposals as recommendations, separate from current behavior.
- Do not invent architecture rationale, ownership, SLAs, environments, credentials, retry guarantees, rollback safety, or production procedures. Link existing ADRs; create historical decisions only from recorded evidence. New proposed decisions must be explicitly requested and labeled proposed.
- Do not copy secrets, private keys, tokens, production payloads, or credential-bearing URLs into docs. Derive configuration references from schemas/loaders and sanitized examples, using clearly marked placeholders for secret values.

## 3. Plan the smallest useful manual

Use [page-blueprints.md](references/page-blueprints.md) when choosing pages or writing a substantial new section. Its layout and prompts are adaptable, not a requirement to generate every page or heading.

Separate conceptual explanations, task-oriented procedures, and exact references. Make `docs/README.md` a task-based landing page with links for understanding, local setup, changes, testing, deployment, and troubleshooting where applicable. Keep the root README useful and concise; add entry links without discarding existing badges, installation guidance, or project-specific information.

Give each independently operated service a consistent page. For small projects, combine related topics instead of creating thin pages. Omit nonexistent technologies and unsupported sections; preserve consequential unknowns in a short gap section rather than empty placeholder pages.

## 4. Write executable, traceable documentation

Use descriptive, stable headings, exact identifiers, short explanations, and tables for comparable facts. Explain acronyms on first use. Put prerequisites before actions and expected outcomes after them.

For important pages, provide lightweight provenance suited to the repository's format:

```markdown
> **Audience:** Engineers and coding agents
> **Scope:** <component or workflow>
> **Sources:** [<source path>](<relative link from this page>)
> **Source revision inspected:** <actual commit SHA; note relevant local changes>
> **Verification:** <source review and any commands actually executed>
```

Use actual values in the output. If Git metadata is unavailable, say so. A commit SHA identifies reviewed source; it is not evidence that commands work. Note relevant dirty/untracked source separately. Refresh provenance only for pages substantively rechecked, not every page on every run.

Every operational procedure should identify its working directory, prerequisites, environment, exact repository-supported command, expected result, and relevant failure/recovery path. Mark substitutions clearly; avoid runnable-looking invented commands. Explain effects of migrations, deployment, data repair, and other mutating procedures. Documenting such a command does not authorize executing it.

Repeat short critical facts locally when needed to use a page safely, while linking to one canonical reference for long inventories and procedures. For example, include the worker's acknowledgement boundary on its service page and link to the event reference for the full schema.

Document configuration from actual precedence and validation logic: names, required conditions, defaults, secret status, consumers, and restart/reload behavior when established. For APIs and events, include semantics and failure behavior that a schema alone cannot explain. Prefer existing generators for large reference inventories; preserve their generated-file boundaries.

### Canonical architecture diagrams

Architecture diagrams are supplied externally. Reuse the canonical asset and embed a preview linked to its full-resolution asset:

```markdown
[![System architecture](./assets/system-architecture.png)](./assets/system-architecture.png)
```

Resolve paths relative to the containing page and add explanatory text for accessibility. Verify that the asset exists before linking. Do not recreate, alter, or infer diagrams unless the user requests diagram work. If none is available, explain the architecture in text and record the missing asset without a broken image link. If a diagram conflicts with code, describe the discrepancy instead of changing its meaning silently.

## 5. Validate and maintain

Before finishing, apply [verification.md](references/verification.md). Check navigation, source references, commands, consistency, and whether a new engineer can perform the applicable workflows. Fix gaps supported by available evidence and surface the remaining ones honestly.

For updates, trace changed sources to affected conceptual pages, procedures, service pages, and references. Use the diff as a starting point, not the only evidence: inspect current call sites and configuration. Remove stale assertions and repair inbound links when pages change. Keep changes reviewable and avoid stylistic churn.

End with the documentation entry path, scope covered, checks actually completed, and material gaps or unverified procedures. Do not claim operational completeness when key knowledge is unavailable.
