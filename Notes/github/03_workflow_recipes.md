# Workflow Recipes

Before reading this: **[GitHub Actions](02_github_actions.md)**

---

## 1. @claude Mention Handler

The foundational workflow — respond to `@claude` in any PR or issue comment.

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
      id-token: write
      actions: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## 2. Automated PR Review

Runs on every PR open and push. Posts review comments automatically.

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
            Review this pull request for:
            - Logic errors and edge cases
            - Missing test coverage
            - Security vulnerabilities
            - Code style consistency

            Post your findings as inline review comments. Be concise — flag
            issues with severity (critical/medium/low) and suggested fixes.
          claude_args: |
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
            - Injection vulnerabilities (SQL, command, XSS)
            - Authentication/authorization flaws
            - Hardcoded secrets or credentials
            - Insecure data handling or logging
            - Missing input validation

            Post critical findings as inline comments. Summarize in a PR comment.
          claude_args: |
            --model claude-opus-4-6
            --max-turns 8
            --allowedTools "Read,Grep,Glob,Bash(git diff *),mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment *)"
```

---

## 4. Issue Triage

Automatically labels and categorizes new issues.

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
    steps:
      - uses: actions/checkout@v4

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Triage this new issue (#${{ github.event.issue.number }}):

            1. Classify as: bug, feature-request, question, documentation, or duplicate
            2. Assign priority: critical, high, medium, or low
            3. Apply appropriate labels using `gh issue edit`
            4. Post a brief comment acknowledging the issue and asking for
               any missing information (steps to reproduce for bugs,
               use case for features)
          claude_args: |
            --max-turns 5
            --allowedTools "Bash(gh issue *),Bash(gh label *)"
```

---

## 5. Scheduled Dependency Audit

Runs weekly, opens issues for outdated or vulnerable packages.

```yaml
# .github/workflows/weekly-audit.yml
name: Weekly Audit

on:
  schedule:
    - cron: "0 9 * * 1"  # Monday 9am UTC
  workflow_dispatch:      # allow manual trigger

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
          node-version: "20"

      - run: npm install

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Perform a weekly maintenance audit:

            1. Run `npm audit` and summarize vulnerabilities by severity
            2. Check for outdated packages with `npm outdated`
            3. Identify any TODO/FIXME/HACK comments in src/
            4. If critical vulnerabilities exist, open a GitHub issue with
               remediation steps

            Be factual. Only open an issue if there's something actionable.
          claude_args: |
            --max-turns 10
            --allowedTools "Read,Grep,Glob,Bash(npm audit),Bash(npm outdated),Bash(gh issue *)"
```

---

## 6. Model Selection Guide

| Use case | Recommended model | Why |
|----------|------------------|-----|
| Quick PR review | `claude-sonnet-4-6` (default) | Fast, cost-efficient |
| Security audit | `claude-opus-4-6` | Deeper reasoning |
| Issue triage | `claude-haiku-4-5` | Simple classification, cheapest |
| Implementation | `claude-opus-4-6` | Best code generation |

Set via `claude_args: "--model claude-opus-4-6"`.

---

## 7. Cost Reference

Approximate costs using Sonnet (2025 pricing):

| Workflow | Typical cost |
|----------|-------------|
| PR review (400-line diff) | ~$0.04 |
| Issue triage | ~$0.01 |
| Security audit | ~$0.08–0.15 |
| Weekly maintenance | ~$0.10–0.20 |

20 PR reviews/day ≈ ~$24/month. Use `--max-turns` to cap runaway sessions.

---

## 8. Tips

- **Concurrency control**: Add `concurrency: group: ${{ github.workflow }}-${{ github.event.pull_request.number }}` to cancel redundant runs when a PR is force-pushed.
- **Timeout**: Set `timeout-minutes: 10` on the job to prevent stuck runs from burning API budget.
- **CLAUDE.md**: The action reads your repo's `CLAUDE.md` — use it to enforce review standards and coding conventions without repeating them in every workflow prompt.
- **Secrets**: Never hardcode the API key. Always use `${{ secrets.ANTHROPIC_API_KEY }}`.

---

**Back to**: [GitHub Index](README.md)
