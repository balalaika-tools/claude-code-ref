# GitHub Actions

> **Who this is for**: GitHub Actions users configuring Claude workflows with least-privilege authentication and repository permissions.

Before reading this: **[GitHub App](01_github_app.md)**

---

## 1. The Action

```yaml
uses: anthropics/claude-code-action@v1
```

**Source:** [github.com/anthropics/claude-code-action](https://github.com/anthropics/claude-code-action)

Runs Claude Code inside a GitHub Actions workflow. It can respond to `@claude` mentions, issue assignments/labels, or explicit automation prompts. It supports direct Anthropic API auth, Claude Code OAuth, Anthropic workload identity federation, AWS Bedrock, Google Vertex AI, and Microsoft Foundry.

---

## 2. Core Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `prompt` | No | Explicit instructions. If omitted, the action can respond to trigger events |
| `claude_args` | No | Extra Claude CLI flags such as `--model`, `--max-turns`, `--allowedTools` |
| `settings` | No | Claude Code settings JSON string or path |
| `github_token` | No | Token with repo/PR permissions. Optional if using the Claude GitHub App token flow |
| `trigger_phrase` | No | Mention phrase; default `@claude` |
| `assignee_trigger` | No | Username assignment that triggers the action |
| `label_trigger` | No | Label that triggers the action; default `claude` |
| `plugins` | No | Newline-separated plugins to install |
| `plugin_marketplaces` | No | Newline-separated marketplace Git URLs |

Auth-related inputs:

| Input | Use |
|-------|-----|
| `anthropic_api_key` | Direct Anthropic API |
| `claude_code_oauth_token` | Claude Code OAuth token |
| `anthropic_federation_rule_id` + org/workspace/service-account fields | Anthropic workload identity federation |
| `use_bedrock` | AWS Bedrock |
| `use_vertex` | Google Vertex AI |
| `use_foundry` | Microsoft Foundry |

Security-sensitive inputs such as `allowed_non_write_users`, `allowed_bots`, and `show_full_output` should be used only with narrow permissions and trusted workflows.

---

## 3. Authentication

### Direct Anthropic API

```yaml
- uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add `ANTHROPIC_API_KEY` to **Settings -> Secrets and variables -> Actions**.

### AWS Bedrock (OIDC)

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
    aws-region: us-west-2

- uses: anthropics/claude-code-action@v1
  with:
    use_bedrock: "true"
    claude_args: "--model us.anthropic.claude-sonnet-4-6 --max-turns 10"
```

### Google Vertex AI (OIDC)

```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
    service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

- uses: anthropics/claude-code-action@v1
  with:
    use_vertex: "true"
    claude_args: "--model sonnet --max-turns 10"
```

For cloud providers, pin provider-specific model IDs during enterprise rollouts if you need deterministic behavior.

---

## 4. Permissions

Typical implementation workflow:

```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
  id-token: write   # needed for OIDC auth
  actions: read
```

Minimal read-only review:

```yaml
permissions:
  contents: read
  pull-requests: write
```

Use the least privilege that still lets Claude complete the task. Public repositories require extra care: untrusted comments can become prompt input.

> **Key insight**: On a public repository, any commenter can inject instructions into the prompt Claude reads — so the workflow's `permissions` block is the real security boundary, not the trigger phrase or who is "allowed" to mention `@claude`.

---

## 5. `claude_args`

Pass Claude Code CLI flags:

```yaml
claude_args: "--model sonnet --max-turns 5"
claude_args: "--allowedTools Read,Grep,Glob,Bash(git diff *)"
claude_args: "--disallowedTools Bash(rm *)"
```

Multi-line:

```yaml
claude_args: |
  --model opus
  --max-turns 10
  --allowedTools "Read,Grep,Glob,Bash(git diff *),Bash(git log *)"
```

Common allowlists:

```yaml
# Read-only review
--allowedTools "Read,Grep,Glob,Bash(git diff *),Bash(git log *)"

# PR commenting
--allowedTools "Read,Grep,Bash(gh pr comment *),mcp__github_inline_comment__create_inline_comment"

# Implementation
--allowedTools "Read,Write,Edit,Grep,Glob,Bash(git *),Bash(npm test *)"
```

Use aliases (`sonnet`, `opus`, `haiku`) in general recipes. Pin full IDs only for controlled provider rollouts.

---

## 6. Mode Detection

- **`prompt` set** -> automation mode using the prompt directly
- **`prompt` omitted** -> event-driven mode; the action looks for configured triggers such as `@claude`, assignment, or label

No `mode` input is needed for v1 workflows.

---

## 7. Event Triggers

| Event | YAML trigger | Use case |
|-------|-------------|----------|
| Issue comment | `issue_comment: types: [created]` | `@claude` in issues or PR conversations |
| PR review comment | `pull_request_review_comment: types: [created]` | Inline PR comments |
| PR review submitted | `pull_request_review: types: [submitted]` | Review body mentions |
| Issue opened/assigned/labeled | `issues: types: [opened, assigned, labeled]` | Triage or implementation |
| PR opened/updated | `pull_request: types: [opened, synchronize]` | Automated review |
| Scheduled | `schedule: - cron: "0 9 * * 1"` | Maintenance |
| Manual | `workflow_dispatch:` | On-demand automation |

---

**Next**: [Workflow Recipes](03_workflow_recipes.md)
