# AWS provider

AWS-specific knowledge stays here; the shared skill owns evidence, scope, geometry and readability. AWS is the first specialized provider, not the fallback for all diagrams.

## Icons

Prefer verified draw.io AWS4 stencils. Main-service pattern:

```
shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.lambda;fillColor=#ED7100;strokeColor=#FFFFFF;archRole=icon;
```

Use `connectable="0"`, empty icon value and 48 × 48 geometry inside a card. Search [services.md](services.md) and [resources.md](resources.md) for candidate identifiers. These are inherited lookup snapshots, not proof that a particular draw.io version supports a new icon. Visually verify; don't invent identifiers. Main services use `resourceIcon` + `resIcon`; subresources use their own `shape`.

When a stencil is absent or an SVG is preferable, download the **official AWS Architecture Icons asset package** from [AWS's icon page](https://aws.amazon.com/architecture/icons/), selecting its current package link instead of hardcoding an old ZIP URL. Follow [the shared icon workflow](../../icons.md) to cache, register and embed an extracted SVG. The prior local skill contained AWS4 shape mappings but no actual downloadable-package helper; this workflow makes the fallback explicit and reproducible.

Useful role tints/strokes: compute `#FFF2E8/#ED7100`, database `#F5E6F7/#C925D1`, storage `#E8F5E9/#3F8624`, networking `#EDE7F6/#8C4FFF`, integration `#FCE4EC/#E7157B`, security `#FFEBEE/#DD344C`, AI `#E0F2F1/#01A88D`. These are presentation choices inspired by the supplied diagrams.

## Semantics

For generalized AWS architecture diagrams, omit Route 53 hosted zones, environment labels (dev/staging/prod), concrete region/AZ names and deployment-specific identifiers by default, even when present in repository evidence. Include these only when explicitly requested or essential to the confirmed topic (for example DNS or multi-region design). Use generic role-based infrastructure labels such as “Agent VPC”, “Database VPC” or simply “VPC”, without project identifiers or environment suffixes. “Agent VPC (Private)” is appropriate when the shown network scope is private; omit “(Private)” for a VPC containing both public and private subnets. Preserve meaningful network context such as VPC/private-subnet boundaries and peering. Show account/region/VPC/subnet/AZ boundaries only when relevant to that scope and requested or evidenced. Verify unfamiliar service placement against official AWS documentation. Avoid blanket rules: Lambda isn't necessarily VPC-attached; a load balancer may be internal; S3 isn't a resource running inside a subnet; an ECS task's subnet comes from deployment configuration. Do not add NAT, IAM, monitoring, logs, encryption or multi-AZ components merely to make the diagram look complete.

For mixed architectures, use AWS service icons only for actual AWS services. Langfuse, a model provider or a payment API retains its own identity; locate hosted vs self-hosted components from evidence. A provider-specific SDK alone doesn't prove the whole application runs in that provider's cloud.

For software hosted on AWS infrastructure, follow [self-hosted products](../../self-hosted-products.md): product icon inside an accurate hosting boundary, or a compact product card with a hosting label. A multi-resource product may stay collapsed in an overview; do not imply all of it runs in one EC2 instance or subnet. Expand only the internal resources relevant to the requested view.

When VPC peering is evidenced or explicitly requested, make it visible on the relevant private traffic route, not only in the sidebar. Show the peer VPC boundary around the known destination resources and label the crossing route “VPC peering · private IP”. Keep application edges attached to component cards; the boundary supplies network context. Peering is a connection between VPCs, not a database service or an inline NAT/gateway appliance. Do not infer it merely from “external” or “another account”, or place unrelated external APIs inside the peer VPC without evidence. See [AWS VPC peering](https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html).

## Boundary header icons

Use small native AWS group icons in the upper-left corner of AWS Cloud and VPC boundaries: `shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud;` for AWS Cloud, and `shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc2;` for VPC. These are header decorations, not standalone service cards. Keep `archRole=boundary`, root coordinates, non-connectable boundaries and outer-card flow endpoints. Use opaque light fills, dark AWS Cloud outlines (`#232F3E`) and purple VPC outlines (`#8C4FFF`).

Reserve space for the icon and text, for example `verticalAlign=top;align=left;spacing=0;spacingLeft=40;spacingTop=8;archHeaderHeight=30;`. Visually check the entire header, including the icon, against cards and routes; text-band validation alone does not measure the native group glyph. Follow the updated AWS examples for appearance. Apply this styling to boundaries that belong in the architecture; it does not require adding a VPC to a managed-service request flow.

Apply the same small upper-left header treatment to concrete infrastructure groups: public and private subnets use the verified `grIcon=mxgraph.aws4.group_subnet` with their respective labels/colors, and ECS clusters use `grIcon=mxgraph.aws4.ecs`, all with `shape=mxgraph.aws4.group`. Keep the icon scale and heading spacing consistent with Cloud/VPC headers; use green public-subnet, blue private-subnet and orange ECS accents. Reserve enough height for wrapped titles and inspect the rendered glyphs. Leave generic organizational frames such as “Managed services” text-only: add icons for a specific infrastructure meaning, not merely because a box contains many elements.

The reference files’ `group_public_subnet` and `group_private_subnet` identifiers did not render in the locally tested draw.io Desktop version. Use `group_subnet` unless those specialized glyphs have been visually verified in the target renderer.
