# GitHub Actions

Before reading this: **[GitHub App](01_github_app.md)**

---

## 1. The Action

```yaml
uses: anthropics/claude-code-action@v1
```

**Source:** [github.com/anthropics/claude-code-action](https://github.com/anthropics/claude-code-action)

Runs Claude Code in a GitHub Actions workflow. Supports direct API, AWS Bedrock, and Google Vertex AI.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `anthropic_api_key` | Yes* | Anthropic API key |
| `prompt` | No | Instructions for Claude (overrides trigger phrase detection) |
| `claude_args` | No | Extra CLI flags: `--model`, `--max-turns`, `--allowedTools` |
| `github_token` | No | Defaults to `${{ github.token }}` |
| `trigger_phrase` | No | Custom trigger (default: `@claude`) |
| `use_bedrock` | No | Use AWS Bedrock instead of direct API |
| `use_vertex` | No | Use Google Vertex AI |

*Not required when using Bedrock or Vertex.

---

## 3. Authentication

### Direct Anthropic API

```yaml
- uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add `ANTHROPIC_API_KEY` to **Settings → Secrets and variables → Actions**.

### AWS Bedrock (OIDC)

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
    aws-region: us-east-1

- uses: anthropics/claude-code-action@v1
  with:
    use_bedrock: "true"
    claude_args: "--model us.anthropic.claude-sonnet-4-6"
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
    claude_args: "--model claude-sonnet-4-5@20250929"
```

---

## 4. Permissions

Most workflows need these:

```yaml
permissions:
  contents: write       # read/write files, create commits
  pull-requests: write  # post PR comments and reviews
  issues: write         # respond to issues
  id-token: write       # required for OIDC (Bedrock/Vertex)
  actions: read         # read workflow context
```

Minimal read-only review:

```yaml
permissions:
  contents: read
  pull-requests: write
```

---

## 5. `claude_args` Options

Pass any Claude Code CLI flag:

```yaml
claude_args: "--model claude-opus-4-6"
claude_args: "--max-turns 5"
claude_args: "--allowedTools Read,Grep,Glob,Bash(git *)"
claude_args: "--disallowedTools Bash(rm *)"
```

Multi-line:

```yaml
claude_args: |
  --model claude-opus-4-6
  --max-turns 10
  --allowedTools "Read,Grep,Glob,Bash(git *)"
```

### Common tool allowlists

```yaml
# Read-only review
--allowedTools "Read,Grep,Glob,Bash(git diff *),Bash(git log *)"

# PR commenting
--allowedTools "Read,Grep,Bash(gh pr comment *),mcp__github_inline_comment__create_inline_comment"

# Implementation (read + write)
--allowedTools "Read,Write,Edit,Grep,Glob,Bash(git *),Bash(npm run *)"
```

---

## 6. Mode Detection

The action auto-detects whether to run in interactive or automated mode:

- **`prompt` set** → automated mode, uses the prompt directly
- **`prompt` not set** → detects trigger phrase (`@claude`) in the event payload and responds to it

No need to configure `mode` explicitly (that was the old beta API).

---

## 7. Event Triggers

Common events to combine with the action:

| Event | YAML trigger | Use case |
|-------|-------------|----------|
| PR opened/updated | `pull_request: types: [opened, synchronize]` | Automated review |
| Issue comment | `issue_comment: types: [created]` | @claude in comments |
| PR review comment | `pull_request_review_comment: types: [created]` | @claude in PR reviews |
| Issue opened | `issues: types: [opened]` | Auto-triage |
| PR review submitted | `pull_request_review: types: [submitted]` | @claude in review body |
| Scheduled | `schedule: - cron: "0 0 * * 0"` | Weekly maintenance |
| Path-filtered PR | `pull_request: paths: [src/auth/**]` | Security-critical files |

---

**Next**: [Workflow Recipes](03_workflow_recipes.md)
