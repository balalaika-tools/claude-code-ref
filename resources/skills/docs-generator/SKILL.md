---
name: docs-generator
description: Generate or update a repository's docs/ wiki from source code, configuration, tests, and infrastructure. Use for repository operating manuals, engineering onboarding documentation, or keeping architecture, service, development, deployment, and operations guides aligned with code. Not for standalone API-spec conversion or a small README-only edit.
---

# Repository Docs Generator

Build a human-readable, AI-navigable operating manual: what the system does, where behavior lives, how to run and change it, and how to operate and recover it. Adapt coverage to the actual repository. A library, CLI, mobile app, and multi-service platform need different manuals.

## Scope and defaults

- Use `docs/` unless the user or repository establishes another location. Preserve existing documentation tooling and language. For targeted updates preserve URLs and useful authored content. For an explicitly requested clean rebuild, consolidate verified information into the agreed blueprint, remove superseded pages within scope, and repair inbound links. Do not retain duplicate manuals, loose legacy notes, or restore user-deleted pages merely to preserve the old layout. Default new prose to the user's requested language, otherwise the existing documentation language, otherwise English.
- For full generation, discover the repository before choosing pages. For updates, inspect the requested changes and their consumers, then update affected pages and navigation. Do not regenerate unrelated prose or move established pages merely to match a suggested layout.
- Keep changes to documentation, its assets, and necessary navigation links. Do not change application code, CI, infrastructure, or agent instructions to make the documentation true. Report mismatches instead. Adding a docs platform or publishing the wiki is a separate task.
- Proceed with reasonable defaults. Ask only when a missing choice materially blocks useful work; record unavailable operational knowledge as a gap and complete the supported sections.

## 1. Discover sources and operating boundaries

Read repository instructions and check worktree status. Inventory files with `rg --files` and targeted searches; inspect entrypoints and representative implementations rather than dumping the entire repository. Exclude dependencies, build outputs, caches, and vendored code unless relevant to the requested scope.

Look for existing docs, manifests and lockfiles, task runners, executable scripts, application entrypoints, configuration loaders, example environment files, tests, migrations, API schemas, workers and event handlers, containers, infrastructure, CI/CD, authentication, and telemetry. Trace manifest script definitions before recommending their commands.

For monorepos, distinguish deployable services, shared libraries, applications, and infrastructure. Identify who owns state and interfaces. Trace representative end-to-end paths through producers, consumers, persistence, and error handling; do not infer behavior from directory names or dependencies alone.

Maintain a working evidence map: topic → relevant files/symbols → observed behavior → uncertainty → destination page. It can remain working notes; do not generate a second catalog that duplicates the manual.

## 2. Resolve facts before writing

- Inspect executable code, configuration loaders, deployment definitions, and scripts first: these establish implemented behavior. Consult Markdown and notes afterward for context or operational knowledge absent from code; validate claims before reuse. Specifications express intent and tests express expectations, neither overrides a contradictory execution path.
- Ground factual claims in inspected implementation, configuration, tests, or maintained specifications. Cite exact repository-relative paths with links and useful symbol names. Prefer stable paths over brittle line numbers.
- Distinguish implemented behavior, declared deployment configuration, test expectations, and observed runtime results. Repository configuration does not prove what is deployed. Tests that were only read were not executed.
- When sources disagree, trace the relevant execution path. Explain unresolved discrepancies with both sources; do not silently choose a convenient narrative. External documentation can explain a dependency but cannot establish how this repository uses it.
- Explain material gaps with the missing fact, practical impact and next verification step; use `Not determined from repository` when useful. Keep the search history in working notes. Omit inapplicable topics rather than filling the manual with `Not applicable` entries. Label proposals as recommendations, separate from current behavior.
- Do not invent architecture rationale, ownership, SLAs, environments, credentials, retry guarantees, rollback safety, or production procedures. Link existing ADRs; create historical decisions only from recorded evidence. New proposed decisions must be explicitly requested and labeled proposed.
- Do not copy secrets, private keys, tokens, production payloads, or credential-bearing URLs into docs. Derive configuration references from schemas/loaders and sanitized examples, using clearly marked placeholders for secret values.

## 3. Plan the smallest useful manual

Use [page-blueprints.md](references/page-blueprints.md) when choosing pages or writing a substantial new section. Treat its deployable-system blueprint as an example, not a universal template. Choose pages after discovering the repository type, supported workflows and reader needs; honor an explicitly agreed structure. Libraries, CLIs, mobile apps and mixed monorepos need different coverage. Omit unsupported topics rather than generating empty pages or repeated `Not applicable` entries. Required coverage means a usable reader workflow, not merely a heading; add pages only for substantial necessary material.

Separate conceptual explanations, task-oriented procedures, and exact references. The root README introduces the project: a short summary, a shallow annotated tree of relevant repository folders, a prominent documentation entry link, and only the most important getting-started or usage information. For a substantial manual, `docs/README.md` is the task-based navigation index; do not duplicate its full link inventory in the root README. Small repositories can use the root README as their only index. Follow the detailed [README guidance](references/page-blueprints.md#root-readme-and-documentation-index), preserving useful existing project-specific content.

Give each independently operated service a consistent page. For small projects, combine related topics instead of creating thin pages. Omit nonexistent technologies and unsupported sections; preserve consequential unknowns in a short gap section rather than empty placeholder pages.

## 4. Write executable, traceable documentation

Use descriptive, stable headings, exact identifiers, short explanations, and tables for comparable facts. Explain acronyms on first use. Put prerequisites before actions and expected outcomes after them.

Start each page with its title and a short statement of purpose when useful, then the content the reader came for. Do not prepend repeated Scope/Audience, commit-SHA, Sources or Verification metadata blocks. Put implementation links beside the claims they support, or use a concise `Implementation references` section at the end when several sources underpin the page. Avoid duplicating sources already linked usefully in the body; navigation pages usually need no source appendix.

Keep documentation-generation history, inspected revisions, dirty-worktree notes, check counts and test-run results in the handoff or PR, not in the permanent manual. Preserve established version metadata only when it identifies supported product behavior or a repository publishing convention. Put a concrete unverified procedure or missing input near the affected step when it changes how the reader can proceed; a generic “not executed” disclaimer is not a known gap. Record only actionable, material known gaps in the documentation index, linking to the affected guide or reference.

Every operational procedure should identify its working directory, prerequisites, environment, exact repository-supported command, expected result, and relevant failure/recovery path. Mark substitutions clearly; avoid runnable-looking invented commands. Explain effects of migrations, deployment, data repair, and other mutating procedures. Documenting such a command does not authorize executing it.

Repeat short critical facts locally when needed to use a page safely, while linking to one canonical reference for long inventories and procedures. For example, include the worker's acknowledgement boundary on its service page and link to the event reference for the full schema.

Start configuration documentation with essential environment variables and first-setup inputs, then inventory all supported settings: key, environment alias, type/constraints, defaults and environment overrides, required conditions, purpose/consumer, secret status, and restart/reload behavior. Include configuration selectors and secret-provider inputs; distinguish application settings from Compose and deployment inputs. Trace actual precedence and validation. Check consumers: an accepted setting may be unwired or unused, which must be stated. For APIs and events, include semantics and failure behavior that a schema alone cannot explain. Prefer existing generators for large reference inventories; preserve their generated-file boundaries.

### Operational coverage and executable commands

For applicable systems cover first deployment separately from repeat deployment, local deployment, identity creation and credential reuse, authenticated smoke tests, automated tests, and recovery. Discover project-specific prerequisites such as app clients, private seeds, network handoffs, and external model access; put each before the dependent action. Distinguish stack readiness from successful business execution.

Procedures must work from their declared starting state, including a fresh terminal. Default interactive command blocks to zsh unless the user or repository requires another shell. Invoke scripts through their shebang; do not source Bash scripts into zsh. Define variables before use, quote expansions, avoid reserved shell variables and personal absolute paths, and separate manual choices from executable blocks. Discover resource identifiers through real outputs. Include expected responses, bounded polling with explicit failure/timeout handling, repeat-run effects, and cleanup that preserves reusable identities and data. Never disguise missing operational knowledge as an invented executable command.

Keep one canonical procedure or inventory per topic. Service pages link to full contracts and configuration. Document inbound contracts and actual outbound operations, including authentication, payloads, errors, retries and side effects. Inventory emitted metrics, spans and automatic instrumentations, structured log events/correlation fields, export routes, dashboards and alerts. Distinguish implemented instrumentation, configured export and observed runtime availability.

### Canonical architecture diagrams

Architecture diagrams are supplied externally. Reuse the canonical asset and embed a preview linked to its full-resolution asset:

```markdown
[![System architecture](./assets/system-architecture.png)](./assets/system-architecture.png)
```

Resolve paths relative to the containing page and add explanatory text for accessibility. Verify that the asset exists before linking. Do not recreate, alter, or infer diagrams unless the user requests diagram work. If none is available, explain the architecture in text without a broken image link; treat the missing asset as a gap only when a requested deliverable depends on it. If a diagram conflicts with code, describe the discrepancy instead of changing its meaning silently.

## 5. Validate and maintain

Before finishing, apply [verification.md](references/verification.md). Check navigation, source references, commands, consistency, and whether a new engineer can perform the applicable workflows. Fix gaps supported by available evidence and surface the remaining ones honestly.

For updates, trace changed sources to affected conceptual pages, procedures, service pages, and references. Use the diff as a starting point, not the only evidence: inspect current call sites and configuration. Remove stale assertions and repair inbound links when pages change. Keep changes reviewable and avoid stylistic churn.

End with the documentation entry path, scope covered, checks actually completed, and material gaps or unverified procedures. Do not claim operational completeness when key knowledge is unavailable.
