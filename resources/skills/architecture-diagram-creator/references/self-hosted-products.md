# Self-hosted products and hosting infrastructure

Read when a named software product runs on infrastructure operated by the system owner. Keep product identity, hosting and internal implementation distinct. Apply these rules to overview and focused views across providers.

## Default overview representation

Represent a supporting product as one recognizable component with its official icon, relevant interfaces and a concise hosting indication. An AWS overview is not automatically an inventory of every resource behind each product. Preserve the requested application services and their relationships while collapsing supporting-product internals outside the selected scope.

- For simple, evidenced hosting, use a hosting boundary such as “Amazon EC2” with the AWS icon around the “NATS JetStream” product card with its own icon. Communication edges terminate on the outer product card, never its inner icon. The hosting frame is decorative; do not add an EC2 → NATS edge to express containment.
- For a product spanning multiple infrastructure resources, use a logical product boundary or aggregate card such as “Self-hosted Langfuse”. Add a concise hosting label only when supported. Do not enclose the entire product in a single EC2/runtime boundary if that would misrepresent its deployment.
- Place an aggregate only within a boundary that contains everything it represents. If its deployment spans subnets, a VPC-level placement may be appropriate; if it spans VPC and regional resources, do not force the aggregate into a subnet or VPC. Use the accurate common scope and explain hosting briefly.
- In a dense overview, a single product card with “Self-hosted on Amazon EC2” may replace the hosting frame. Keep the product icon primary and its hosting legible. Do not add redundant nested frames solely to show more logos.
- Mark collapsed internals with a short note such as “Internal deployment omitted”, in the subtitle/sidebar or product caption. This indicates abstraction, not a claim that the product has only one process or resource.

Generic example: Agent service → Self-hosted Langfuse. The overview shows the integration and relevant hosting context without automatically expanding every internal service, database, cache or storage dependency. This is a representation example, not a specification of Langfuse's requirements.

## When to expand

Expose internal resources when the user requests them or they materially explain the selected question: a shared dependency used by the application, a significant network/trust boundary, or deployment/availability behavior in scope. Show the useful subset and identify remaining abstraction; do not expand the entire product merely because one dependency matters. Preserve edges to the actual shared resource instead of hiding them behind the aggregate.

For a focused view of that product, expand its relevant internal services, stages and infrastructure from the permitted evidence. For a focused view of a different service, the product can remain a compact external dependency. Neither “AWS” nor “focused” alone requires expanding all supporting products.

## Evidence and geometry

Determine hosted versus self-hosted and actual hosting from the user's brief and permitted deployment/configuration evidence. Do not infer EC2, Fargate, Kubernetes, replica counts or internal dependencies from the brand logo or a generic upstream installation guide. For a proposed architecture, label material hosting choices as assumptions and include them in scope confirmation. Consult current official product documentation when establishing actual deployment requirements.

Retain the shared XML contract: hosting/product boundaries are root-coordinate decorative vertices; product cards are the connection targets; icons and labels are non-connectable children. Leave space for boundary headings and icon clearances. Hosting containment does not introduce a communication hop. Product icons follow [icons.md](icons.md); AWS hosting icons follow [providers/aws/README.md](providers/aws/README.md).
