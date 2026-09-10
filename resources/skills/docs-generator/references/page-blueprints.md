# Page blueprints

Read when planning a manual or adding substantial pages. Select only relevant topics and combine them when that improves navigation. These are questions to answer from evidence, not headings to reproduce mechanically.

## Example layout for a multi-service repository

```text
docs/
├── README.md
├── overview/
│   ├── system-overview.md
│   ├── repository-structure.md
│   └── glossary.md
├── architecture/
│   ├── architecture.md
│   ├── data-flow.md
│   ├── integrations.md
│   ├── security.md
│   └── decisions/             # Existing or evidence-backed decisions
├── services/                 # One page per independently operated service
├── development/
│   ├── local-setup.md
│   ├── testing.md
│   └── adding-a-feature.md
├── deployment/
│   ├── deployment.md
│   ├── infrastructure.md
│   └── rollback.md
├── operations/
│   ├── observability.md
│   └── troubleshooting.md
└── reference/
    ├── configuration.md
    ├── api.md
    ├── data-model.md
    └── events.md
```

Keep existing numbered directories if present; numbering is optional. A small project may need only an index, architecture, development, and reference page. A library may need installation, public API, compatibility, and release guidance instead of service deployment and on-call runbooks.

## Landing page and overview

Explain purpose, intended users, primary workflows, and scope. Map key directories to responsibilities, entrypoints, and extension points. Distinguish first-party components from external dependencies. Define domain terms necessary to understand the system.

Organize navigation by reader intent: understand the system, run it, change it, test it, release it, diagnose it. Include relevant known gaps and link to deeper pages. An index should not duplicate the manual.

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

- **Configuration:** Name, type, required/conditional requirement, actual default, secret status, consumers, validation, precedence, reload behavior.
- **API:** Method/path or interface, authentication, request/response contract, errors, pagination and idempotency where implemented; link canonical specifications.
- **Data model:** Tables/entities, ownership, keys/relationships, constraints, migrations, retention and deletion behavior where established.
- **Events/queues:** Exact identifiers, producer/consumer, schema/version, routing, ordering, delivery/acknowledgement behavior, retry/dead-letter handling, deduplication, replay constraints.
- **Permissions/integrations:** Calling component, external interface, role/scope, enforcement source, configuration, and relevant failure behavior.

Keep defaults distinct from values configured for particular environments. Cross-link authoritative references instead of maintaining competing copies.
