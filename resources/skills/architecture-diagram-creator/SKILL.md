---
name: architecture-diagram-creator
description: Create or refine editable .drawio XML architecture diagrams from a description, repository code and infrastructure, or both. Supports architecture overviews and focused views of service internals, collaborating services or pipelines, with AWS, vendor-neutral or mixed representation.
---

# Architecture diagram creator

Produce editable, uncompressed draw.io XML plus a PNG preview. Favor readable architecture over implementation inventories. Default presentation: component cards tinted by responsibility, component icons, small upper-left header icons on meaningful system/service/infrastructure boundaries, numbered flow badges, and concise explanations in a right sidebar. Apply header icons in AWS, neutral and focused views using the appropriate provider or neutral assets; keep generic organizational frames text-only. Use a restrained role-based palette instead of one color for every card.

## How to use the examples

Examples are visual and structural guidance, not templates to copy literally. Reuse the presentation language and routing techniques; independently choose the components, providers, boundaries, flow, step count, canvas size and arrangement from the user's request and permitted evidence. Do not add a VPC, queue, NAT, model gateway or Langfuse merely because an example includes it. A focused layer may need a completely different layout.

Keep the quality requirements: valid portable XML, meaningful icons with comparable optical size, outer-card connections, clear routing/spacing and consistent numbering. The orange separator and matching blue/black badges are this skill's chosen default style. User instructions can override presentation defaults; never override the user's requested architecture to resemble an example. The bundled validator implements the documented generation/style contract, so explicitly requested departures need corresponding checks or a disclosed exception rather than a false claim of full validation.

## Start: choose, describe, confirm

Follow [interaction-workflow.md](references/interaction-workflow.md) for every new diagram task: **two-option menu → brief → one scope confirmation before generation**. Apply this workflow to description-only, repository-only and combined requests.

1. Present the menu: **Architecture overview** (services/systems and their main relationships) or **Focused view** (internal components or a selected flow across one or more services). Wait for the choice if not already explicit in the user's message. A recommendation is not a selection. Keep an explicit choice from the initial prompt and show it as selected rather than asking the same question again.
2. Invite the user to explain scope, constraints/exclusions and provider presentation in one message; “use the repo” is a valid brief. Reuse information already supplied and ask only for material gaps. Apply exclusions before repository analysis.
3. Analyze permitted evidence and prepare a concrete brief: type, scope, detail, source/exclusions, provider, included relationships, external context and material assumptions. Ask **one explicit scope confirmation before generating the XML**. Do not infer confirmation from silence, tool defaults or elapsed time. User-requested changes to the brief must be incorporated before approval.
4. After confirmation, generate, validate, visually review and deliver autonomously. Do not request a second delivery approval. Routine revisions continue with the established brief; don't reopen the menu or reconfirm every edit.

The menu is conversational, not a standalone application UI. Use a suitable choice tool when the host provides one, otherwise a numbered text menu. Obey host tool rules for questions/confirmation; no particular tool is a dependency. When pausing, explain briefly that the scope-confirmation step comes from this user-requested workflow and link the relevant reference.

User instructions override repository evidence, examples and defaults. A requested target architecture may intentionally differ from code: label it as proposed. Never read excluded sources indirectly through summaries/generated artifacts.

Read [scope-and-evidence.md](references/scope-and-evidence.md) for repository work. For Focused view also read [focused-diagrams.md](references/focused-diagrams.md). Type, scope, detail and provider are independent: a small scope can still be an overview, and changing AWS to neutral must not change type or application detail. Without an explicit choice, suggest Overview for a general architecture request, but wait for the menu answer.

Neutral application views preserve services, responsibilities and interactions while abstracting deployment-only plumbing. Explicitly requested deployment/Kubernetes detail stays in scope even without a named cloud provider. Do not use AWS “generic” icons as a neutral library.

For self-hosted products, read [self-hosted-products.md](references/self-hosted-products.md). Preserve the product identity and accurate hosting context; collapse supporting-product internals unless they explain the requested scope. Provider-specific presentation does not require a full infrastructure inventory.

## Build after scope confirmation

1. Record a small working inventory of components, boundaries, meaningful directed relationships, and assumptions. For repo-derived elements, retain file/line evidence in working notes; don't clutter the canvas with it.
2. Read [drawio-contract.md](references/drawio-contract.md) and [layout-and-quality.md](references/layout-and-quality.md). Select cards and flow steps before allocating geometry.
3. For AWS, read [providers/aws/README.md](references/providers/aws/README.md). For neutral views, use [vendor-neutral.md](references/vendor-neutral.md): prefer specific icons for named technologies, including in neutral diagrams; use Lucide for generic roles or as a fallback after searching official product assets. Empty colored blocks are not icons. Only load relevant provider references. To add another provider later, put its semantics, icon sources and examples under `references/providers/<provider>/`; keep geometry provider-independent.
4. For missing/brand icons or downloading an icon package, read [icons.md](references/icons.md). Use native verified AWS4 shapes where supported; preserve the official icon-package fallback. Embed custom SVGs so the diagram is portable.
5. Generate the XML using the contract. Load only an example matching the confirmed type and scope:
   - Small overview view: [AWS request flow](assets/examples/aws-request-flow.drawio).
   - Overview of larger platforms with deployment boundaries, asynchronous work and external integrations: [AWS Fargate agent platform](assets/examples/aws-fargate-agent-platform.drawio) or [cloud-neutral agent platform](assets/examples/neutral-agent-platform.drawio). Read [the paired-example notes](references/paired-platform-examples.md) for scope, mappings and deliberate simplifications.
   - Focused views: [ingestion service pipeline](assets/examples/focused-ingestion-service.drawio) for internal stages; [agent + MCP services](assets/examples/focused-agent-mcp-services.drawio) for cross-service internals. See [focused-diagrams.md](references/focused-diagrams.md) for interpretation.
   Adapt topology to evidence; examples are not architecture requirements. The cloud-neutral platform retains named technologies such as NATS JetStream and PostgreSQL; use responsibility labels when the user explicitly requests technology-agnostic presentation.

**Outer-card endpoints are mandatory:** every architectural edge connects to the visible outer component card, never to its icon or text. The icon is a non-connectable child. Anchor on a card face, route outward, and avoid all component-card interiors. A VPC/system boundary enclosing several cards is not the endpoint of each internal service: crossing it is expected when the flow crosses that boundary.

## Check and deliver

Run the bundled validator explicitly; no hooks or `${PLUGIN_ROOT}` are assumed:

```bash
python3 <skill-directory>/scripts/validate_drawio.py docs/<name>.drawio
```

Check fidelity to the confirmed brief: overview must remain at service/system granularity; focused views must expose the requested internals/flow and distinguish components from deployable services. The XML validator cannot establish this semantic match. Fix errors and review warnings. The strict generation contract uses explicit rectilinear segments so card intersections and parallel-line spacing are measurable. For imported/editor-rerouted files, an unrecognized route is **unverified**, never silently passed. Read the contract before converting such routes.

Export the PNG with `scripts/export_png.py`; do not assemble a separate draw.io CLI command. Follow [layout-and-quality.md](references/layout-and-quality.md) for usage and visual acceptance criteria. If rendering is unavailable, deliver the XML with that limitation stated; don't claim visual verification or a successful PNG export.

Complete the composition review in that reference before delivery: inspect whitespace, boundary proportions, alignment and routing detours. A collision fix must not introduce needless empty space. Improve visible defects, revalidate and inspect a fresh render after the final layout change; zero validator errors alone do not establish presentation quality.

Unless the user specifies a destination, save both outputs with the same descriptive kebab-case stem, using `.drawio` (or `.xml` when explicitly requested) for the editable XML and `.png` for the image. Choose the destination directory in this order: an existing `docs/` directory in the project root; otherwise the project root; otherwise the current working directory when no project root can be identified. Keep the XML and PNG together. Avoid overwriting unrelated files. Always retain the editable XML even if another format was requested. Return links to both files, scope, material assumptions, validation result, PNG background/alpha verification and any unresolved visual limitation. Do not automatically upload repository-derived diagrams or open a URL containing their content.
