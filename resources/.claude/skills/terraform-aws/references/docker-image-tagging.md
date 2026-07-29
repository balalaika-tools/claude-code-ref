# AWS Container Image Versioning

## Default Rule

Use Git SHA tags and enforce ECR tag immutability. Never deploy `latest` or a
branch tag. Make the image version an explicit input with no default:

```hcl
variable "worker_image_tag" {
  description = "Immutable Git SHA tag produced by CI"
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{7,40}$", var.worker_image_tag))
    error_message = "worker_image_tag must be a 7-40 character lowercase Git SHA."
  }
}
```

The ECR stack enforces the assumption:

```hcl
resource "aws_ecr_repository" "worker" {
  name                 = "${var.project_name}-${var.environment_name}-worker"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
}
```

ECR belongs to the platform tier: repositories and images outlive the services
that push to them. The application stack receives or discovers the repository
URL; do not reference an `aws_ecr_repository` resource owned by another state:

```hcl
variable "worker_image_repository_url" {
  description = "ECR repository URL published by the ECR stack"
  type        = string
}

image = "${var.worker_image_repository_url}:${var.worker_image_tag}"
```

## Why Git SHAs

- The deployed version maps to the source revision that produced it.
- ECR rejects an attempt to overwrite the tag when immutability is enabled.
- Terraform plans show the version transition explicitly.
- Running tasks keep their already resolved image layers.

A Git SHA identifies source, not necessarily reproducible build content. Record
build provenance and use digest pinning when the distinction matters.

## Stronger Default for Production: Digest Pinning

Use a digest when supply-chain policy requires the deployed bytes to be
content-addressed:

```hcl
variable "worker_image_digest" {
  description = "ECR image digest produced by CI after push"
  type        = string

  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.worker_image_digest))
    error_message = "worker_image_digest must be a sha256 digest."
  }
}

image = "${var.worker_image_repository_url}@${var.worker_image_digest}"
```

Resolve the digest after pushing the Git SHA tag:

```sh
DIGEST="$(aws ecr describe-images \
  --repository-name "$ECR_REPOSITORY_NAME" \
  --image-ids "imageTag=$GIT_SHA" \
  --query 'imageDetails[0].imageDigest' \
  --output text)"
```

Pass the digest through a transient artifact tfvars file or an explicit
`TF_VAR_*` value. The digest is not secret, but the generated plan remains
sensitive because it can contain other resolved values.

For multi-architecture images, deploy the manifest-list/index digest produced
for the supported platforms, not an arbitrary platform-specific child digest.
