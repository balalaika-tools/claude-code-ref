# EKS: Terraform Owns Substrate, GitOps Owns Workloads

EKS is the one exception to Terraform-driven application releases. Terraform
builds and maintains the cluster and everything the cluster needs in order to run
workloads. It does not deploy the workloads.

## Contents

- [The Ownership Boundary](#the-ownership-boundary)
- [Why Not the Helm and Kubernetes Providers for Workloads](#why-not-the-helm-and-kubernetes-providers-for-workloads)
- [Stack Layout and Provider Authentication](#stack-layout-and-provider-authentication)
- [Bootstrapping the Reconciler](#bootstrapping-the-reconciler)
- [The Application Release Flow](#the-application-release-flow)

## The Ownership Boundary

**Terraform owns:**

- The cluster, its version, its endpoint access configuration, and its logging.
- Node groups, or the Karpenter controller and its IAM.
- VPC, subnets, security groups, and CNI configuration.
- IRSA roles or EKS Pod Identity associations for workloads and controllers.
- Shared cluster controllers: AWS Load Balancer Controller, external-dns,
  cert-manager, metrics-server, CSI drivers.
- The **GitOps bootstrap**: installing Argo CD or Flux itself, its IAM role, its
  repository credentials, and the single root App-of-Apps or root Kustomization
  that points at the GitOps repository.

**Terraform does not own:** any application workload. No `helm_release` and no
`kubernetes_*` resources for application charts, Deployments, Services,
HPAs, Ingresses, or ConfigMaps that the reconciler will also manage.

The rule underneath both lists: **exactly one controller per object.** If Argo CD
manages the shared controllers through the App-of-Apps, then Terraform must not
also install them — pick one owner per component and write it down.

Karpenter is the usual grey area. Terraform installing the controller and its IAM
is substrate. The `NodePool` and `EC2NodeClass` custom resources can go either
way; choose one owner and keep every node pool with that owner rather than
splitting them.

## Why Not the Helm and Kubernetes Providers for Workloads

- **Two reconcilers fight over one object.** Argo CD or Flux continuously drives
  the cluster toward the Git state. Terraform drives it toward the state file.
  Each sees the other's work as drift, and the object flaps between them.
- **`kubernetes_manifest` needs a live cluster at plan time.** It performs a
  server-side dry run, so a plan fails when the cluster does not exist yet or
  the runner cannot reach the API. That breaks plan-on-PR and bootstrap in one
  step.
- **A Helm release is opaque in a plan.** A chart value change shows as a diff on
  a values blob, not as the Deployment and Service changes it will produce.
- **Rollback paths differ.** `terraform apply` cannot roll a bad workload back
  faster than the reconciler can, and a `helm_release` failure mid-apply leaves
  state and cluster disagreeing.

None of this argues against the providers for the bootstrap itself, which is a
one-time install of a component no reconciler is watching yet.

## Stack Layout and Provider Authentication

Use at least two platform stacks:

```text
Terraform/stacks/platform-eks-cluster/   # cluster, node groups, IRSA roles, networking
Terraform/stacks/platform-eks-addons/    # controllers + GitOps bootstrap
```

The split exists because the Kubernetes and Helm providers must be configured
from values that do not exist during the cluster's own first plan. Configuring a
provider from a resource attribute in the same apply produces provider
configuration that is unknown at plan time, which Terraform rejects or resolves
inconsistently.

In the addons stack, read the cluster through data sources and authenticate with
an `exec` plugin rather than a token attribute, so no short-lived token is
written into state:

```hcl
data "aws_eks_cluster" "this" {
  name = var.cluster_name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.this.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.this.certificate_authority[0].data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name, "--region", var.aws_region]
  }
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.this.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.this.certificate_authority[0].data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.cluster_name, "--region", var.aws_region]
    }
  }
}
```

Confirm the provider configuration syntax against the Kubernetes and Helm provider
majors in the lockfile before copying this; the Helm provider has changed how the
Kubernetes connection is expressed between major versions.

The runner needs the `aws` CLI on `PATH` and an identity mapped into the cluster.
Grant cluster access through EKS access entries or the cluster's auth
configuration deliberately; the creating principal's implicit admin access is not
a durable grant for CI.

## Bootstrapping the Reconciler

Install the reconciler, give it an identity, give it repository credentials, and
point it at one root object. Nothing more:

```hcl
resource "helm_release" "argocd" {
  name             = "argocd"
  namespace        = "argocd"
  create_namespace = true
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = var.argocd_chart_version # exact, never a range

  values = [yamlencode({
    server = { service = { type = "ClusterIP" } }
  })]
}

resource "kubernetes_manifest" "root_app" {
  manifest = yamldecode(templatefile("${path.module}/root-app.yaml", {
    repo_url        = var.gitops_repo_url
    target_revision = var.gitops_target_revision
    path            = "clusters/${var.environment_name}"
  }))

  depends_on = [helm_release.argocd]
}
```

- Pin the chart to an exact version. A range makes every apply a potential
  reconciler upgrade.
- Repository credentials are a secret: store them in the environment's selected
  secret store and have the reconciler read them (for example through External
  Secrets). An `ephemeral` variable is not a drop-in substitute here: it can
  only flow into an `ephemeral` block or a write-only argument, and neither
  `helm_release`'s `values` nor an ordinary `kubernetes_secret`'s `data` is one
  — assigning an ephemeral value there is a plan-time error, not a lesser
  protection. Reach for it only if the specific resource/argument you are using
  documents write-only support; otherwise the secret-store-plus-reconciler path
  above is the one that actually keeps the token out of state.
- One root Application or Kustomization per cluster. Everything else is a child
  in Git, not a Terraform resource.
- `kubernetes_manifest` is acceptable here specifically because the cluster
  already exists in the addons stack. It still requires API reachability at plan
  time, so plan this stack from a runner with cluster access.

**The first apply needs two passes.** `kubernetes_manifest.root_app` is a
custom resource of the `applications.argoproj.io` CRD that `helm_release.argocd`
itself installs. `depends_on` only orders the apply graph — it does not help
the *plan*, and `kubernetes_manifest` does a server-side dry run against the
live API at plan time. On a cluster where Argo CD has never been installed, the
CRD does not exist yet when this configuration is first planned, so the plan
fails regardless of `depends_on`. This is the same `kubernetes_manifest`
plan-time constraint called out above, applied to a CRD this same apply is
installing, not a pre-existing cluster.

Bootstrap it in two explicit steps instead of expecting one apply to work
end-to-end the first time:

```sh
terraform apply -target=helm_release.argocd   # installs the CRD; authorized, one-time
terraform apply                                # now root_app can plan and apply
```

This is the same class of exception as the bootstrap state bucket's imperative
import: a one-time, reviewed step for a resource that cannot exist before the
apply that creates it, not a routine pattern. After this first apply,
subsequent plans see the CRD already registered and proceed normally in one
step.

After this apply, Terraform's involvement in application delivery ends.

## The Application Release Flow

1. Build the image and push it to ECR with an immutable tag, then resolve its
   digest — see [`docker-image-tagging.md`](docker-image-tagging.md).
2. Commit the new digest to the GitOps source: `kustomize edit set image` or a
   `values.yaml` bump, on a branch or straight to the tracked revision.
3. Argo CD or Flux reconciles. Progressive delivery, health gates, and rollback
   are the reconciler's job.

The application pipeline **never runs `terraform apply`**. Its AWS permissions
are ECR push and nothing else; its cluster permissions are none. Rollback is a
Git revert in the GitOps repository, not a Terraform operation.

A cluster change and an application change are therefore two different
workflows with two different roles, and a release that needs both is sequenced:
platform apply first, then the GitOps commit.
