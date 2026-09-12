# Scope and evidence

After the interaction workflow establishes a brief, keep **type** (overview/focused), **scope** (system/service/service group/flow), **detail** (requested depth), **source** (prompt/repo/both), and **provider** (explicit/inferred/neutral/mixed) separate. If the user chooses a neutral agent layer while Terraform describes AWS, retain the application relationships but abstract deployment services and omit irrelevant networking.

Keep the requested application granularity when changing provider presentation: neutral is not synonymous with high-level, simplified or fewer services. In paired views, account for every application responsibility and relationship. Omit infrastructure-only intermediaries only by reconnecting their logical endpoints; preserve actual custom gateways, adapters, agents and workers. Explicitly requested deployment detail remains in scope even without a named cloud provider.

## Repository discovery

Use `rg --files` excluding dependencies, build output, vendored code and secrets. Start with manifests, entry points, route handlers, workers, orchestration graphs, clients, persistence adapters and deployment definitions. Follow actual calls and configuration references; a dependency in a lockfile alone doesn't establish an active integration. Don't dump environment secrets, credentials or Terraform state into context or output.

Inspect Terraform resources/modules/provider aliases, CloudFormation, CDK, Kubernetes or deployment configuration if permitted. Follow local module references and environment selection. Conditional counts, unresolved variables, remote modules and external dependencies can leave gaps: indicate them. IaC describes intended infrastructure; it does **not** prove runtime deployment, drift, reachability or application request flow. Never apply Terraform, fetch secrets or query a cloud account just to draw a repo-based diagram.

Provider evidence must be concrete (provider-specific resource definitions, configured service clients, endpoints), not a casual README mention or the presence of this skill's AWS examples. Distinguish test fixtures and example deployments from application code. With code only, draw logical services and integrations without guessing ECS, Lambda, VPCs or managed database products.

Keep a working table: component/relationship, supporting path and line, confidence (`explicit`, `code-backed`, `declared-infra`, `assumed`), and inclusion reason. Where sources disagree, prefer current executable code/configuration over stale prose unless the user specifies the prose as authoritative. Never hide a material ambiguity behind an official-looking icon.

## Focused views

Read [focused-diagrams.md](focused-diagrams.md) for service internals, cross-service flows and pipeline diagrams. Agent layers are one example of this general capability, not a separate top-level category.

An agent-layer view may show entry point, orchestrator, relevant agents, model gateway, tools, memory/state, retrieval, guardrails and human review **when evidenced or requested**. Increase detail within the chosen layer; show other layers as small external dependencies. Do not inventory every class, method, table or SDK call.

On overview diagrams, “Acquire work” or “Persist session” is usually sufficient. SQL such as `FOR UPDATE SKIP LOCKED`, `state=NEW`, transactions and payload fields belong only where the user requests that detail or the mechanism explains an essential architectural distinction and remains legible. A technically true detail is not automatically worth showing.

## Behavioral acceptance scenarios

- Prompt describing API → queue → worker: retain the description through the menu/brief stages; generate after scope confirmation and label unspecified implementation choices as assumptions.
- Repo with web server + PostgreSQL and no provider evidence: logical web/API/database, no AWS boundary or AWS glyphs.
- Same repo with AWS Terraform: declared deployment view plus code-backed flows, with unresolved environments noted.
- “Ignore Terraform; only agent layer, vendor neutral”: never read Terraform; use permitted agent code and neutral components.
- “Use AWS; replace the current queue with SQS”: depict SQS as requested target, even if repo uses RabbitMQ.
- Mixed AWS + Langfuse: determine whether Langfuse is hosted externally or self-hosted from evidence; its brand icon alone does not determine placement.
