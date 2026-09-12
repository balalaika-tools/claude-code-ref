# Menu, brief and confirmation

This workflow is the user's requested product behavior. It applies to new diagram tasks, not to maintaining the skill itself. All three sources (description, repo, both) follow it.

## 1. Menu

Present exactly two main choices, in the user's language:

1. **Architecture overview** — services/systems, relevant infrastructure and main communications.
2. **Focused view** — internals of a service, detailed collaboration among services, or a selected pipeline/flow.

Do not introduce separate top-level options for ingestion, agents, MCP, deployment, AWS or neutral. Those are scope, subject or provider decisions inside these two categories. If the initial request explicitly chooses a category, display it as selected and continue using the supplied brief; don't require the user to select it again. If no category is explicit, recommend Overview for a general architecture request and await a choice. No diagram generation or broad repo scan while that required choice is pending.

## 2. Brief

After selection, invite a single bundled reply: “Describe the scope and detail you need, anything to exclude, and AWS/neutral/mixed preference; you can also say ‘use the repo’.” Adapt wording to what is already known. Do not force the user to fill a questionnaire, choose a provider prematurely, or repeat their initial description. A menu answer may include the whole brief.

Use these sources after scope/exclusions are established:

| Source | Behavior |
| --- | --- |
| Description only | Use it; don't inspect an unrelated repo merely because one exists. Mark material choices as assumptions. |
| “Use the repo” / repo-only | Inspect permitted code/configuration, including IaC when relevant and allowed. Infer a proposal for the final brief. No provider evidence means neutral logical components. |
| Description + repo | The user's scope, target changes and exclusions win. Fill remaining gaps using permitted evidence. |
| No description and no useful repo | Ask what system/service/flow to depict. |

Maintain a small working brief: `type`, `scope`, `detail`, `source`, `provider`, `include`, `exclude`, `external_context`, `assumptions`, and `confirmed`. It can live in conversation/working notes; no extra manifest is required. Carry it across turns. Do not mark it confirmed until the user approves the concrete summary.

Rules preventing category drift:

- “Only agent and MCP services” narrows scope; it does not request their internals.
- “Inside the ingestion service, show each processing stage” requests focused detail.
- “Follow this document through upload, ingestion and indexing” can be a focused cross-service flow. Preserve actual service boundaries.
- “More detail” on an existing overview expands useful overview information; don't silently change to focused. Ask once if the requested detail would require changing type.
- AWS/neutral/mixed changes provider representation, not type or application depth.
- Repository complexity never overrides the selected type. An agent framework in the repo is not a request for an agent-layer diagram.

## 3. Confirm the concrete scope

Analyze enough permitted evidence to propose something reviewable before confirmation. The summary should identify the chosen type, named service(s)/flow, depth, provider, relevant inclusions/exclusions, external dependencies and significant uncertainties. Name actual components discovered; don't ask the user to approve “I'll analyze the repo”.

Example:

> Focused view of Agent Service + MCP Service: orchestrator, research/execution agents, tool calls, input/output guardrails, trace export and offline evals. The model API, business APIs and curated eval cases are external dependencies. Cloud-neutral; Terraform/networking excluded. These components are a proposed example, not repo findings. Confirm this scope so I can generate the diagram?

Ask once, then wait. A proposed correction is not approval unless the user also says to proceed with it. Revise the summary if needed. Do not generate/export the final diagram before confirmation. A host may restrict which question tools can collect confirmation; use an ordinary question when required. If waiting due to this rule, identify [this reference](interaction-workflow.md) and its instruction: “Do not generate/export the final diagram before confirmation.”

## 4. Generate and revise

Once confirmed, complete XML generation, checks and delivery without further permission requests. Do not restart this workflow for icon size, color, label, routing or other routine edits. If a later instruction explicitly changes type/scope and authorizes the new work, carry that authorization forward; clarify only unresolved changes. User instructions can expressly waive the menu/confirmation for a task or ask for batch operation; don't insist on a redundant approval.

## Behavioral review cases

These are conversation acceptance cases, not claims that XML tests validate model behavior. Exercise them when evaluating the skill.

| Input / state | Expected next behavior |
| --- | --- |
| Bare activation with a repo | Show two-option menu; await selection; don't scan/generate yet |
| “Overview”; no brief yet | Ask for scope/constraints once; allow “use the repo” |
| “Overview of this repo, neutral, ignore Terraform” | Treat Overview as selected; inspect only permitted sources; summarize and await confirmation |
| Description already gives all details | Reuse it; don't repeat brief questions; still request the one concrete confirmation |
| “Focused view” only | Ask what service/group/flow to focus on |
| “Overview of agent + MCP services” | Keep service-level cards, no automatic sub-agent expansion |
| “Focused agent + MCP; include tools and sub-agents” | Expand internals across the two real service boundaries |
| “Focused ingestion; no embeddings or model calls” | Omit embedding even though the example includes it |
| Overview approved; “make it neutral” | Preserve Overview and application detail |
| Scope summary awaiting approval; no reply | Wait; no XML generation |
| Scope summary; “exclude evals” | Revise scope; don't treat the correction alone as approval |
| Scope summary; “yes, proceed without evals” | Apply exclusion and generate; no second confirmation |
| Delivered diagram; “enlarge the icons” | Edit and validate; no new menu |
| “Skip the menu and confirmation for this task” | Honor explicit override; retain source/scope rules |
