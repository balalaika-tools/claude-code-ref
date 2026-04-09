# GitHub App

---

## 1. What Is the GitHub App?

The Claude GitHub App integrates Claude directly into your repository workflow. Once installed, Claude acts as a virtual teammate — responding to `@claude` mentions in PRs and issues, creating PRs, fixing CI errors, and implementing changes from review comments.

---

## 2. Installation

**Recommended — from Claude terminal:**

```
/install-github-app
```

This walks through setup interactively.

**Manual:**

1. Go to [github.com/apps/claude](https://github.com/apps/claude) and install on your repo
2. Add `ANTHROPIC_API_KEY` to your repo secrets:
   - **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `ANTHROPIC_API_KEY`

**Required GitHub permissions the app needs:**

| Permission | Level | Why |
|------------|-------|-----|
| Contents | Read & Write | Read code, create commits |
| Issues | Read & Write | Respond to issues, add labels |
| Pull Requests | Read & Write | Create PRs, post review comments |

---

## 3. @claude Mentions

After installation, Claude responds to `@claude` in:

- Issue comments
- PR review comments
- PR review body
- Issue title or body (on open/assign)

**Example comment triggers:**

```text
@claude implement the feature described in this issue

@claude review this PR for security vulnerabilities

@claude fix the failing tests in the CI run

@claude explain why this approach might cause performance issues
```

Claude reads the full PR diff, repo context, and your `CLAUDE.md` when responding.

> Use `@claude` (not `/claude`) to trigger responses in GitHub comments.

---

## 4. What Claude Can Do

| Task | How to trigger |
|------|---------------|
| Answer questions about code | `@claude how does X work?` |
| Implement a feature | `@claude implement this based on the issue` |
| Fix a bug | `@claude fix the TypeError on line 42` |
| Review for security | `@claude review for security issues` |
| Respond to reviewer feedback | `@claude address the review comments` |
| Fix CI failures | `@claude fix the failing tests` |
| Create a PR | `@claude create a PR for this issue` |

---

## 5. CLAUDE.md in GitHub Workflows

Your repository's `CLAUDE.md` is read by Claude when responding to GitHub events. Use it to enforce team standards automatically:

```markdown
# Code Review Standards
- All functions need JSDoc comments
- No console.log in production code
- Prefer async/await over callbacks

# PR Guidelines
- PRs must update CHANGELOG.md for user-facing changes
- Security changes must include a threat model note
```

Claude applies these rules when reviewing PRs or implementing changes via `@claude`.

---

**Next**: [GitHub Actions](02_github_actions.md)
