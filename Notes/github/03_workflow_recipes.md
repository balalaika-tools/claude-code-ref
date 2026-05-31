# Workflow Recipes

Before reading this: **[GitHub Actions](02_github_actions.md)**

---

## 1. @claude Mention Handler

The foundational workflow: respond to `@claude` in issues, PR comments, and reviews.

```yaml
# .github/workflows/claude.yml
name: Claude Code

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  pull_request_review:
    types: [submitted]
  issues:
    types: [opened, assigned]

jobs:
  claude:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review' && contains(github.event.review.body, '@claude')) ||
      (github.event_name == 'issues' && (contains(github.event.issue.body, '@claude') || contains(github.event.issue.title, '@claude')))
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      actions: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add `id-token: write` when using OIDC auth for Anthropic federation, Bedrock, Vertex, or Foundry.

---

## 2. Automated PR Review

Runs on every PR open and push. Keeps permissions read-only except for PR comments.

```yaml
# .github/workflows/claude-review.yml
name: Claude PR Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Review this pull request for correctness.

            Prioritize:
            - Logic errors and edge cases
            - Security or data exposure risks
            - Missing tests for changed behavior
            - Maintainability issues that materially affect this PR

            Post concise inline comments for concrete findings only.
          claude_args: |
            --model sonnet
            --max-turns 5
            --allowedTools "Read,Grep,Glob,Bash(git diff *),mcp__github_inline_comment__create_inline_comment"
```

---

## 3. Security Review on Critical Paths

Only fires when auth, API, or config files change.

```yaml
# .github/workflows/security-review.yml
name: Security Review

on:
  pull_request:
    types: [opened, synchronize]
    paths:
      - "src/auth/**"
      - "src/api/**"
      - "config/**"
      - "**/*.env.example"

jobs:
  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Perform a security-focused review of the changed files.

            Check for:
            - Injection vulnerabilities
            - Authentication or authorization flaws
            - Hardcoded secrets or credentials
            - Unsafe logging or handling of sensitive data
            - Missing input validation

            Post critical or high-confidence findings as inline comments.
            Summarize residual risk in one PR comment.
          claude_args: |
            --model opus
            --max-turns 8
            --allowedTools "Read,Grep,Glob,Bash(git diff *),mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment *)"
```

---

## 4. Issue Triage

Labels and categorizes new issues. This workflow uses limited permissions and does not edit code.

```yaml
# .github/workflows/triage.yml
name: Issue Triage

on:
  issues:
    types: [opened]

jobs:
  triage:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Triage issue #${{ github.event.issue.number }}.

            1. Classify as bug, feature-request, question, documentation, or duplicate.
            2. Assign priority: critical, high, medium, or low.
            3. Apply existing labels only.
            4. Post a short comment asking for missing reproduction steps or use-case details when needed.
          claude_args: |
            --model haiku
            --max-turns 5
            --allowedTools "Bash(gh issue *),Bash(gh label list)"
```

---

## 5. Scheduled Dependency Audit

Runs weekly and opens issues only for actionable problems.

```yaml
# .github/workflows/weekly-audit.yml
name: Weekly Audit

on:
  schedule:
    - cron: "0 9 * * 1"  # Monday 09:00 UTC
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "22"

      - run: npm ci

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Perform a weekly maintenance audit:

            1. Run `npm audit` and summarize vulnerabilities by severity.
            2. Check outdated packages with `npm outdated`.
            3. Identify TODO/FIXME/HACK comments in src/.
            4. Open a GitHub issue only for actionable critical or high-risk items.

            Be factual and avoid noisy issue creation.
          claude_args: |
            --model sonnet
            --max-turns 10
            --allowedTools "Read,Grep,Glob,Bash(npm audit),Bash(npm outdated),Bash(gh issue *)"
```

---

## 6. Model Selection

| Use case | Model alias | Why |
|----------|-------------|-----|
| Quick PR review | `sonnet` | Strong default for coding tasks |
| Security audit | `opus` | Deeper reasoning for subtle risks |
| Issue triage | `haiku` | Fast and cheap for classification |
| Implementation | `sonnet` or `opus` | Use `opus` for complex design or high-risk changes |

Set via:

```yaml
claude_args: "--model opus"
```

Prefer aliases in examples. Pin exact model IDs only when rollout control matters.

---

## 7. Tips

- **Concurrency**: cancel redundant reviews on force-pushes with a workflow-level `concurrency` group.
- **Timeouts**: set `timeout-minutes` so broken workflows do not burn budget.
- **Least privilege**: keep read-only reviews read-only; grant write permissions only for workflows that commit or edit issues.
- **CLAUDE.md**: the action reads repository guidance, so put review standards there instead of repeating them in every prompt.
- **Secrets**: never hardcode API keys, tokens, or cloud credentials. Avoid `show_full_output` except in trusted debugging workflows.
- **Untrusted users**: be extremely cautious with `allowed_non_write_users` or `allowed_bots: "*"`, especially on public repositories.

---

**Back to**: [GitHub Index](README.md)
