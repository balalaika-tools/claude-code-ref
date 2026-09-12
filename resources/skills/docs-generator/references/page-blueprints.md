# Page blueprints

Read when planning a manual or adding substantial pages. Select only relevant topics and combine them when that improves navigation. These are questions to answer from evidence, not headings to reproduce mechanically.

## Example blueprint for a deployable system

This example suits a multi-service application with deployment and operational workflows. Select and combine pages from repository evidence; do not require this directory tree in every repository.

```text
docs/
├── README.md
├── overview.md
├── architecture/
│   ├── system.md
│   └── request-lifecycle.md
├── services/                 # One page per independently operated deployable
├── guides/
│   ├── local-deployment.md
│   ├── first-deployment.md
│   ├── redeployment.md
│   ├── authentication.md
│   ├── smoke-test.md
│   └── testing.md
├── reference/
│   ├── configuration.md
│   ├── api.md
│   ├── integrations.md
│   ├── events.md
│   └── data-model.md
└── operations/
    ├── observability.md
    ├── troubleshooting.md
    └── recovery.md
```

Do not create empty pages for nonexistent features. A library may need installation, public API, compatibility and release guidance; a small system may combine related topics. Preserve canonical supplied assets. Add pages only for distinct necessary reader tasks. For an authorized clean rebuild, integrate verified legacy information into the blueprint, remove superseded pages within scope and repair inbound links; do not create an archive of loose notes by default. Targeted updates keep established paths unless restructuring was requested.

## Adapt coverage to the repository

| Repository kind | Typical reader tasks |
|---|---|
| Deployable application/service | Local setup, runtime configuration, contracts, deployment and operations where supported |
| Library | Installation, minimal usage, public API, compatibility, testing and package releases |
| CLI | Installation, command/option reference, configuration, examples and troubleshooting |
| Mobile/desktop app | Development setup, build/run, platform requirements and distribution where implemented |
| Mixed monorepo | Shared overview/navigation plus component-specific coverage; a library member does not inherit service deployment pages |

Use the smallest structure that answers the actual tasks. An agreed project blueprint can be retained without turning its service names, integrations or deployment assumptions into skill-wide requirements.

## Guide completion contract

The following outcomes apply only when the repository supports the corresponding workflow. They describe coverage, not mandatory filenames or a requirement to invent missing capabilities.

| Page | Required outcome |
|---|---|
| Local deployment | Tools, configuration/secrets/seed, dependencies, migrations, startup, health/auth smoke, full business-flow prerequisites, stop/restart and separately identified destructive reset |
| First deployment | Account/access, state bootstrap, infrastructure, secrets, network handoffs, identity, artifacts, migrations, rollout and verification in actual dependency order |
| Redeployment | Reuse resources/credentials; choose environment/component/immutable version; handle code/config/schema/infrastructure changes; verify and link recovery |
| Authentication | Distinguish human and machine identities; create once, store/retrieve credentials via an established mechanism, reuse from a fresh terminal, renew tokens, explain scopes/audience and supported rotation |
| Smoke test | Select local/remote environment, obtain auth, supply valid data, submit, capture IDs, poll to a deadline, assert results and side effects, handle no-data/failure cases and cleanup |
| Testing | Actual unit/integration/contract/end-to-end commands, selectors, infrastructure, fixtures, expected results and state effects |

Every procedure declares working directory, starting state, inputs and where they come from, commands, expected result, repeat behavior and relevant recovery. If a required external handoff is unknown, identify the missing input and how to obtain/verify it; do not substitute an invented command.

## Root README and documentation index

The root README should let a new visitor understand the project and choose a useful next step without opening several files. Use this order as a default, adapting to useful existing content:

1. **Name and summary:** What the project does, the problem it addresses, and its primary users or use case. Mention central components only when they explain behavior; avoid a dependency list as the introduction.
2. **Documentation entry:** A prominent relative link to `docs/README.md` or the established documentation entrypoint.
3. **Repository structure:** A shallow, annotated `text` tree of the important existing folders and entry files. Usually one or two levels are enough; include deeper children only to explain a meaningful boundary. Omit caches, generated artifacts, private data, personal notes and tool metadata. It is an orientation map, not a filesystem dump or a proposed structure.
4. **Get started / essential information:** The most useful starting route, essential prerequisites and a minimal verified example when it is genuinely self-contained. Link a setup guide when prerequisites make a short command misleading. Keep only a few high-value direct links such as local setup or the public API; the full manual index belongs in docs.
5. **Other essentials, when established:** Support/contribution entrypoints, compatibility constraints or license information that a visitor needs. Preserve useful badges or maintained project links; do not invent owners, support channels or licensing terms.

The summary, tree and first steps should be understandable independently of the docs index. Avoid full endpoint/settings catalogs, deployment runbooks, duplicated documentation link lists, generation history, verification reports and sprawling known-gap sections in the root README.

For a substantial manual, `docs/README.md` organizes all maintained pages by reader intent: understand, run/use, develop/test, deploy/release and operate where applicable. It is the complete navigation map, not a second project overview. Include a short `Known gaps` section only for unresolved facts or defects with a concrete impact on an applicable task; link to the affected procedure and next action. Ordinary environment differences, intentional constraints and a lack of execution during a documentation task belong in their relevant context or handoff, not an index audit report. Omit the section when there are no material gaps.

For a small repository with only a few documentation pages, the root README can serve as the sole navigation index; do not create a second index with duplicate links. An `overview.md` page is useful only when conceptual/domain detail warrants more space than the root summary. Define necessary terms and map component responsibilities there rather than copying the root README.

These principles align with [GitHub's README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes): explain purpose, usefulness, getting started and help. The folder tree and split between indexes are this skill's navigation conventions, adapted to the repository.

## Architecture and data flow

Answer:

- Who calls the system, and what problem does it solve?
- Which component owns each responsibility and each store of state?
- Where are process, network, tenant, and trust boundaries?
- How does a representative request or job enter, transform, persist, and exit?
- Which communication is synchronous or asynchronous?
- What are the actual timeout, retry, acknowledgement, idempotency, and partial-failure behaviors?
- How do components scale, and what constrains concurrency or throughput?
- Which integrations are required, optional, or replaceable in local development?
- Where are architectural constraints enforced in code or configuration?

Embed an available canonical diagram according to `SKILL.md`. Trace flow steps to actual handlers/producers/consumers. Use a communication table when useful:

| Source | Destination | Interface/protocol | Sync/async | Purpose | Failure behavior | Source evidence |
|---|---|---|---|---|---|---|

Security coverage should explain actual authentication, authorization enforcement, credential sources, network exposure, and sensitive-data handling. Distinguish policy intent from implementation. Avoid claims such as “secure” or “exactly once” without specific evidence.

## Service or component page

Use a consistent order across comparable services; omit unsupported or irrelevant fields.

1. **Purpose and boundaries:** Responsibilities, explicit non-responsibilities, source location, known ownership.
2. **Entrypoints and lifecycle:** Startup, shutdown, readiness, dependencies, internal modules that matter to changes.
3. **Contracts and state:** Inputs, outputs, API/event identifiers, stores, ownership, transaction boundaries.
4. **Configuration:** Essential settings and local prerequisites; link the canonical configuration reference.
5. **Development and testing:** Commands to run and test this component, required backing services, fixtures/mocks.
6. **Deployment and scaling:** Artifact, release path, health checks, concurrency, migrations where applicable.
7. **Operations:** Logs/metrics/traces, known failures, inspection and recovery procedures.
8. **Sources and related pages:** Links to implementation and deeper references.

Prefer precise statements such as “acknowledges after persistence in `<handler>`” when verified; “processes messages” alone does not explain operating behavior. Do not copy illustrative queue or service names into the actual output.

## Local development, testing, and change recipes

Cover the supported happy path from checkout to a working system: tool versions derived from manifests/CI, dependency installation, configuration, backing services, initialization or migrations, start command, and a concrete smoke check. Explain which external services can be mocked and any setup steps that require unavailable credentials.

Separate unit, integration, and end-to-end tests where the repository does. State working directories, prerequisites, selection commands, and effects such as creating or resetting a test database.

Choose change recipes matching the codebase: add an endpoint, migration, event consumer, CLI command, public library function, or configuration setting. Point to a real representative implementation, files to change, contract implications, and tests to run. Do not pretend every project supports every recipe.

## Deployment, infrastructure, and rollback

Describe the actual release path: trigger → build → artifact/version → environment → rollout → verification. Identify CI jobs, scripts, environment selection, credential roles, approvals encoded in the workflow, migration ordering, and health gates. Distinguish a configured pipeline from a confirmed successful deployment.

For Terraform, when present, inspect modules, environment roots, provider constraints, backend configuration, locking, state isolation, variables, outputs, and resource groups. Document the repository's wrappers and working directories before generic CLI commands. Explain how a plan is reviewed and applied, state access requirements, and destructive operations only to the extent supported by sources. Never expose state contents or credential values.

Rollback guidance must address artifact selection, configuration compatibility, schema/data changes, and post-rollback verification. Reverting a commit or selecting an older container is not automatically a safe data rollback. If there is no implemented or documented recovery mechanism, state the limitation; do not invent one.

## Observability and runbooks

Inventory concrete signals with source links:

- Metrics: instrument and exported name where established, type, unit, attributes, update conditions, meaning and emitter.
- Traces: custom span names/patterns, operation boundaries, attributes/errors, automatic instrumentations, propagation across network, queues and durable state.
- Logs: meaningful event names, levels, structured/correlation fields, destination and representative searches; avoid transcribing every incidental debug message.
- Export routes, health signals, provisioned dashboards/alerts: configuration location, queries/conditions, environment differences and diagnostic use. Local dashboards do not prove cloud export exists.

Explain where logs, metrics, traces, and health signals originate; how to correlate a request/job; and which dashboards or alerts exist in the repository. Do not invent live URLs or thresholds.

For each evidenced failure scenario, write:

1. Symptom and impact.
2. Relevant signals and diagnostic commands, with environment and prerequisites.
3. Likely causes supported by implementation or incident records.
4. Recovery action, its effects, and conditions under which it is appropriate.
5. Verification of recovery and recorded escalation ownership, if available.

Distinguish hypothetical failure analysis from known incidents. Explain duplicate-work and data-loss implications before replaying jobs, draining queues, or rerunning migrations.

## Exact references

Use structured facts with nearby sources; avoid enormous manually transcribed inventories when a maintained schema/generator exists.

- **Configuration:** Essential environment variables first, then every public setting from loaders/schemas, not only `.env.example`: YAML key, environment alias, type/constraints, required conditions, model/YAML defaults and environment overrides, purpose/consumer, secret status, precedence and reload behavior. Include selectors and secret-provider inputs; distinguish Compose interpolation and Terraform/release inputs. Reconcile against declared fields and inspect consumers for unused knobs. Generate large inventories from source where useful, without duplicating canonical schemas.
- **API:** Method/path or interface, authentication, request/response contract, errors, pagination and idempotency where implemented; link canonical specifications.
- **Data model:** Tables/entities, ownership, keys/relationships, constraints, migrations, retention and deletion behavior where established.
- **Events/queues:** Exact identifiers, producer/consumer, schema/version, routing, ordering, delivery/acknowledgement behavior, retry/dead-letter handling, deduplication, replay constraints.
- **Permissions/integrations:** Actual outbound operations, calling component, method/path or SDK operation, authentication/role/scope, sent and consumed fields, timeout/retry/error mapping and write effects. Distinguish client assumptions from independently verified provider contracts; avoid cataloging unused provider APIs.

Keep defaults distinct from values configured for particular environments. Cross-link authoritative references instead of maintaining competing copies.
