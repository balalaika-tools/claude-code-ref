# Destroy Troubleshooting: ECS Drain and Stuck ENIs

Add these to `destroy-<stack>.sh` for any stack that runs workloads in a VPC.
They sit around the standard destroy workflow in `SKILL.md`: drain before the
destroy plan is applied, diagnose after it fails.

Both patterns belong to the **application tier**: ECS services, their task
security groups, and VPC Lambda ENIs live in app stacks. A platform-tier destroy
script does not need the drain loop, but it will hang on leftover ENIs if an app
stack is still up. Destroy app stacks before the platform stacks they depend on —
which is what reverse stack-list order gives you.

## Contents

- [ECS Drain-Before-Destroy](#ecs-drain-before-destroy)
- [ENI Diagnostic Pattern](#eni-diagnostic-pattern)

## ECS Drain-Before-Destroy

ECS stacks stall Terraform destroy if tasks are still running. Scale to 0 and
wait first. Read the service list as JSON, not `-raw` inside a loop — a `for x
in "$(terraform output -raw ...)"` loop over a single quoted string always
iterates exactly once, silently, regardless of how many services the stack
actually has:

```bash
AWS_REGION="${AWS_REGION:-$(awk -F'"' '/^[[:space:]]*aws_region[[:space:]]*=/ {print $2; exit}' "$VAR_FILE")}"
CLUSTER_NAME="$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")"

# Stack output: ecs_service_names = ["worker", "api"]  (a list, even for one service)
SERVICE_NAMES=()
while IFS= read -r service_name; do
  SERVICE_NAMES+=("$service_name")
done < <(terraform output -json ecs_service_names 2>/dev/null | jq -r '.[]')

for SERVICE_NAME in "${SERVICE_NAMES[@]}"; do
  [[ -z "$SERVICE_NAME" ]] && continue
  if aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" \
      --region "$AWS_REGION" --query 'services[0].status' --output text 2>/dev/null | grep -q ACTIVE; then
    print_info "Draining ECS service $SERVICE_NAME..."
    aws ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" \
      --desired-count 0 --region "$AWS_REGION" >/dev/null || true
    aws ecs wait services-stable --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" \
      --region "$AWS_REGION" || true
  fi
done
```

Add `jq` to this script's pre-flight tool check. Read service names from
`terraform output` — never hardcode values that can drift.

`SERVICE_NAMES=()` followed by `[[ -z "$SERVICE_NAME" ]] && continue` is
deliberate: under `set -u`, iterating an array that came back empty is itself an
error on bash 3.2, and an empty `terraform output` yields one empty element
rather than none.

## ENI Diagnostic Pattern

Lambda and ECS resources in a VPC hold ENIs that block Terraform destroy. This
is the reactive counterpart to the SG/ENI guardrails in the `terraform-aws`
skill (`timeouts { delete = "30m" }`, `replace_security_groups_on_destroy`) —
those reduce how often a destroy gets stuck; this is what to run when it still
does. Surface the blocking ENIs on failure:

```bash
get_state_resource_id() {
  terraform state show -no-color "$1" 2>/dev/null \
    | awk -F' = ' '/^[[:space:]]*id[[:space:]]*=/{gsub(/"/, "", $2); print $2; exit}'
}

describe_sg_enis() {
  local label="$1" sg_id="$2"
  [[ -z "$sg_id" ]] && return 0
  print_warning "ENIs referencing $label SG $sg_id:"
  aws ec2 describe-network-interfaces \
    --region "$AWS_REGION" \
    --filters "Name=group-id,Values=$sg_id" \
    --query 'NetworkInterfaces[].{Id:NetworkInterfaceId,Status:Status,Type:InterfaceType}' \
    --output table 2>/dev/null || true
}

if terraform apply -input=false "$DESTROY_PLAN_FILE"; then
  print_success "<Stack> stack destroyed"
else
  print_error "Destroy failed. Checking security-group ENI attachments..."
  describe_sg_enis "<service>" "$(get_state_resource_id "module.<stack>.aws_security_group.<service>")"
  exit 1
fi
```

This branch replaces the plain `terraform apply "$DESTROY_PLAN_FILE"` at the end
of the standard destroy workflow. Both diagnostic helpers end in `|| true` or a
`return 0` guard so the diagnostic itself can never mask the real destroy
failure — the script still exits 1.

An ENI with `Status: in-use` and `InterfaceType: lambda` normally means a
function is still executing or its ENI teardown is in progress, which can take
several minutes after the last invocation. `requester-managed` ENIs belong to an
AWS service (VPC endpoints, RDS Proxy, NAT) and are released only when that
resource is destroyed — look for the owning resource rather than deleting the
ENI by hand.
