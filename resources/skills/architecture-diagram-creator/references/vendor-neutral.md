# Vendor-neutral presentation

Every component card still has a recognizable icon. For named technologies, prefer their specific official icons using the discovery order in [icons.md](icons.md), even in a neutral view. Use vendor-independent pictograms for generic responsibilities, explicit technology-agnostic presentation, or unavailable product assets. Do not substitute empty colored squares or undifferentiated geometric placeholders for icons. Keep consistent optical scale and the same nominal 48 × 48 placement as AWS icons. No `mxgraph.aws4.*` shapes, cloud branding or implied managed products.

The bundled SVGs in [assets/icons/neutral](../assets/icons/neutral/) use [Lucide](https://lucide.dev/), a consistent neutral icon library. Prefer this set and extend it with semantically appropriate Lucide icons when needed:

Keep the bundled set small. For an uncovered neutral role, search Lucide's official catalog first, download only the selected SVG, and cache/register it in the project's icon directory for reuse. Do not download the entire library or add speculative icons to the skill. Use another library only when Lucide has no suitable semantic icon or the user specifies one. Official service logos still follow the brand-source workflow in `icons.md`; Lucide-first applies to neutral pictograms.

| Component | Icon |
| --- | --- |
| Requester / person | [requester.svg](../assets/icons/neutral/requester.svg) — Lucide `user-round` |
| Input / API gateway | [gateway.svg](../assets/icons/neutral/gateway.svg) — Lucide `server-cog`, software-managed entry server |
| Orchestrator | [orchestrator.svg](../assets/icons/neutral/orchestrator.svg) — Lucide `workflow`, coordinated execution |
| State store / database | [database.svg](../assets/icons/neutral/database.svg) — Lucide `database` |
| Queue | [queue.svg](../assets/icons/neutral/queue.svg) — Lucide `list-ordered`, ordered work items |
| Automated executor | [tool.svg](../assets/icons/neutral/tool.svg) — Lucide `bot`; use a wrench for a generic tool rather than an automated worker |
| Object / artifact storage | [storage.svg](../assets/icons/neutral/storage.svg) — Lucide `hard-drive` |
| Integration gateway | [integration.svg](../assets/icons/neutral/integration.svg) — Lucide `router` |
| Model endpoint | [model.svg](../assets/icons/neutral/model.svg) — Lucide `brain-circuit` |

Embed the SVG using `scripts/icon_assets.py embed` as described in [icons.md](icons.md). The local SVGs are self-contained; no runtime package or network access is required. Sources, hashes and adaptations are recorded in [catalog.json](../assets/icons/neutral/catalog.json); retain the bundled [Lucide license](../assets/icons/neutral/LICENSE) when redistributing assets and include its notice in generated XML containing them, as in the example. Their colors match the example's functional categories; preserve geometry and consistent stroke weight when adapting the palette. Labels describe responsibilities: API, Queue, Worker, State Store, Model Gateway, Agent Orchestrator. For unfamiliar services follow [the discovery procedure](icons.md#unfamiliar-services-and-missing-icons).

Neutrality does not require erasing useful technologies: named NATS JetStream, PostgreSQL or Langfuse components retain their identities and prefer their specific icons. For an explicitly technology-agnostic or no-brand request, use “Message broker”, “Relational database” or “Observability” and semantic pictograms instead. Use best judgment from the user's wording; clarify only if the distinction changes the requested result materially.

Keep one meaningful system boundary when it distinguishes internal services from external callers/integrations. Add internal groups only when they explain a distinct subsystem, ownership/trust boundary or useful set of related components. Do not nest synonymous “Platform”, “Runtime” and “Service processes” frames around the same services, or wrap one database in a redundant persistence box. Do not substitute “VPC” for a logical subsystem. The same endpoint, spacing, typography and numbered-sidebar rules apply.

When producing a logical neutral view from a deployment diagram, omit infrastructure-only mechanisms that do not explain application responsibilities. For example, NAT egress becomes a direct caller → external API relationship, not an invented “Integration gateway” service. Include a proxy/gateway only when the user asks for it or evidence establishes an actual application component and its role. Neutralizing a diagram is not a one-to-one renaming exercise.

Preserve application detail: the same API, orchestrator, workers, queues, state stores, tools and interactions should remain when switching from provider-specific to neutral presentation, unless the user changes scope. Infrastructure-only cards disappearing must not cause application relationships to disappear; reconnect the logical caller and destination. A lower total card count due to omitting NAT/ALB is not permission to reduce service detail.

For the default neutral application/service view, show client → API service. Omit infrastructure-managed load balancing, ingress and NAT; do not add a generic replacement just to mirror AWS or Kubernetes plumbing. Retain a requested or evidenced custom API gateway when it has a substantive application responsibility such as authentication, policy enforcement, API aggregation or orchestration. Rename neither an ALB nor a Kubernetes ingress into such a service. If the user explicitly asks for a neutral deployment/Kubernetes/traffic-distribution view, show relevant real load balancers there without changing the requested application detail. “Neutral” alone never selects a less detailed view.

## Boundary headers

Use a small 24 × 24 neutral pictogram at the upper-left of meaningful system, subsystem or service frames. Reuse the bundled Lucide assets: workflow for a processing system/pipeline, server-cog for application services, bot for an agent service, plug for tool integration and flask-conical for offline evaluation. These illustrate responsibilities, not cloud infrastructure. Keep generic organizational frames text-only when no clear semantic icon adds information.

Embed each header SVG in a non-connectable root-level `archRole=icon` cell, inset about 12 px from the boundary corner. Reserve the title with `spacing=0;spacingLeft=48;spacingTop=14;archHeaderHeight=28;`, increasing height if it wraps. Do not parent it to the boundary or attach flow edges to it. The validator checks standalone icon rectangles against cards, text and routes; inspect the actual image as well. Preserve the Lucide license notice and use a subdued stroke matching the boundary.
