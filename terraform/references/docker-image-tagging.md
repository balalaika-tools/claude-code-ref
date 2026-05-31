# Docker Image Tagging

## The rule

Use git SHA tags for container images. Never use `latest` or branch names. The `image_tag` variable must have no default — CI is required to supply an explicit value.

```hcl
variable "worker_image_tag" {
  description = "ECR image tag for the worker (git SHA from CI, e.g. a3f9c12)"
  type        = string
  # No default — CI must supply this explicitly.
}
```

Task definition reference:

```hcl
image = "${aws_ecr_repository.worker.repository_url}:${var.image_tag}"
```

## Why git SHA tags are sufficient

- Tags are written once per commit by CI and never rewritten — immutable in practice.
- ECR write access is restricted to CI. Overwriting a tag requires a compromised pipeline or a rogue operator with ECR push permissions; at that point the threat is larger than image substitution.
- Running ECS tasks are unaffected by a tag overwrite — they already have their layers. Only new task launches would pull the changed image.

## Why not `latest` or branch tags

Mutable tags silently change what gets deployed on the next task launch or `terraform apply` without any diff in state. A git SHA makes the deployed version explicit and auditable in both the Terraform variable and the ECS task definition stored in AWS.

## Stricter alternative: digest pinning

For environments with strict supply-chain security requirements, pin by image digest instead of tag:

```hcl
variable "worker_image_digest" {
  description = "ECR image digest (sha256:...) produced by CI after push"
  type        = string
}

# In task definition:
image = "${aws_ecr_repository.worker.repository_url}@${var.worker_image_digest}"
```

CI extracts the digest after push:

```sh
DIGEST=$(aws ecr describe-images \
  --repository-name my-app \
  --image-ids imageTag=${GIT_SHA} \
  --query 'imageDetails[0].imageDigest' \
  --output text)

terraform apply -var="worker_image_digest=${DIGEST}"
```

Digest is content-addressed — it cannot be overwritten regardless of ECR permissions. Use this when compliance requirements mandate supply-chain immutability. For most projects, git SHA tags are the right default.
