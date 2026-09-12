# Larger paired platform examples

Read when an architecture needs several boundaries, service processes, durable work and external integrations. The AWS example has 11 component cards, eleven connections and nine narrative steps; the cloud-neutral example has nine cards, eight connections and eight steps. They demonstrate different anchors on shared cards, separated parallel lanes, long return routes, custom brand SVGs, the orange title separator and matching sidebar/canvas badges. A paired logical view need not have a one-to-one component mapping with its deployment view.

- [AWS Fargate agent platform](../assets/examples/aws-fargate-agent-platform.drawio): AWS Cloud → Agent VPC → public/private subnet groups, plus an ECS cluster; Fargate service task cards; RDS PostgreSQL; regional SQS/S3 outside the VPC; NAT egress to an external model and hosted Langfuse.
- [Cloud-neutral agent platform](../assets/examples/neutral-agent-platform.drawio): one system boundary with useful service and messaging/artifact groups; client → API service; named services instead of Fargate deployment tasks; NATS JetStream, PostgreSQL and object storage; direct orchestrator calls to the model API and hosted Langfuse. Redundant platform/runtime/process frames and AWS network boundaries are absent.

## Mapping and limits

Both examples deliberately show **externally hosted Langfuse**, not a self-hosted installation. Keep that placement when applying icon or abstraction improvements; a self-hosted variant would be a different deployment proposal. For such a variant, follow [self-hosted products](self-hosted-products.md) to show accurate hosting while collapsing internals outside the selected scope.

| AWS view | Cloud-neutral view | What the mapping means |
| --- | --- | --- |
| Internet-facing ALB | Omitted; client calls API service | Load distribution is outside this application-flow view |
| ECS/Fargate API, orchestrator and worker tasks | API, orchestrator and worker services | Deployment runtime abstracted to application responsibilities |
| Amazon SQS | NATS JetStream stream and durable pull consumer | Durable work delivery role; not API or delivery-semantics equivalence |
| Amazon RDS for PostgreSQL | PostgreSQL | Managed hosting detail removed |
| Amazon S3 | Object storage | Shared artifact responsibility |
| NAT Gateway | Omitted; direct logical calls | Network egress is abstracted away, not replaced with an invented application gateway |
| Public/private subnets and ECS cluster | Logical application tiers | Different boundary semantics, not renamed network isolation |

These are illustrative proposals, not diagrams inferred from a repository. AWS AZs/subnets are aggregated; each Fargate card represents a service's task role, not a guarantee of a single replica. ALB public placement and private task placement follow [AWS ECS inbound-network guidance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/networking-inbound.html). Internet gateways, route tables, service discovery, task-start dependencies, VPC endpoints, replication and failure handling are omitted from this selected-flow view. Do not treat direct arrows to SQS/S3 as proof of a particular network-access mechanism.

An application integration/model gateway belongs in a logical view only if it is requested or evidenced as a real component with a responsibility such as model routing, authentication, rate limiting or protocol translation. An infrastructure NAT or route configuration alone is not evidence for that component. The neutral example preserves all application roles and interactions; its lower card count comes from omitting infrastructure ALB/NAT intermediaries, not reducing application detail. Those deployment components belong in an explicitly requested deployment or Kubernetes view; a neutral request alone is not a reason to add them or to simplify the services.

The queue → orchestrator arrow follows **message delivery**, while the consumer initiates polling. The JetStream example uses a durable pull consumer and acknowledges successful handling; see the [official JetStream consumer documentation](https://docs.nats.io/nats-concepts/jetstream/consumers). A production design still needs retry/idempotency and failure policy; don't clutter an overview with those implementation details unless requested.

Double-headed request arrows include their response. Dashed gray edges mean queued work, dashed rose edges mean telemetry. The final three steps (AWS 7–9; neutral 6–8) are related effects, not a total ordering. Follow-up result-query APIs are outside this example's selected flow.

NATS JetStream and PostgreSQL are explicit technologies because this is **cloud-neutral**, not technology-neutral. The neutral example embeds the official NATS project mark for JetStream and PostgreSQL elephant for the database, following the product-icon priority in [icons.md](icons.md). Sources, originals and SVG compatibility adaptations are recorded in [the brand catalog](../assets/icons/brands/catalog.json). For an explicitly technology-agnostic request, replace those labels with “Durable work queue” and “Relational database”, and hosted Langfuse with “Observability”. Never choose a deployment provider from the technology names alone.

## Asset and geometry notes

The external Langfuse SVG is the user-provided reference asset. Its [catalog entry](../assets/icons/brands/catalog.json) records that its original upstream source is unverified. Lucide provenance and license are in [the neutral catalog](../assets/icons/neutral/catalog.json). Both XMLs embed their images and the Lucide license notice.

Nested boundaries are decorative root-coordinate rectangles; only icon/text cells are nested under component cards. This follows the shared contract and makes cross-boundary routing deterministic. All connectors terminate on the visible outer card, and the explicit lanes pass the bundled 20 px parallel-line and 10 px unrelated-card clearance checks. Render after editing; the validator cannot measure text in boundary headings.
