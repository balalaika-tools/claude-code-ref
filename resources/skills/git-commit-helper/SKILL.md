---
name: git-commit-helper
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
---

# Git Commit Helper

## Step 1 — inspect what's staged

Never run `git add .` blindly. Start by seeing what's already staged:

```bash
git status
git diff --staged
git diff --staged --stat
```

If nothing is staged, show the user what's unstaged and ask which files to include before proceeding.

If a file has both staged and unstaged changes, make that explicit. The commit message must describe only the staged hunks, not the file's full working tree state.

## Step 2 — derive the commit type and scope

Read the diff and ask:

- **What changed?** Code, tests, config, docs, infra?
- **Why?** New behavior (feat), broken thing fixed (fix), same behavior different shape (refactor), test coverage (test), tooling/config (chore), docs only (docs)?
- **Where?** The scope is the subsystem, module, or layer affected — keep it short (`api`, `auth`, `db`, `ui`, `ci`, `infra`). Omit scope if the change is truly cross-cutting.

When multiple types apply, pick the one that describes the *primary* intent. A refactor that also fixes a latent bug is a `refactor`.

## Step 3 — write the message

Follow conventional commits format:

```
type(scope): description

- bullet: one logical change per line
- bullet: another change
```

**Summary line rules:**
- Lowercase after the colon: `feat(auth): add JWT support` not `feat(auth): Add JWT support`
- Imperative mood: "add", "fix", "remove" — not "added", "fixes", "removing"
- No period at the end
- ≤ 72 characters including the `type(scope): ` prefix
- Describe *what* changes, save *why* for the body

**Body rules:**
- Use bullets for multi-change commits; prose for a single focused change
- One bullet per logical change — never manually wrap a bullet to a second line
- Explain WHY when the reason isn't obvious from the summary

**Breaking changes:**
```
feat(api)!: restructure response format

BREAKING CHANGE: all responses now follow JSON:API spec
```

### Types reference

| Type | When |
|------|------|
| `feat` | New capability visible to users or callers |
| `fix` | Corrects unintended behavior |
| `refactor` | Same behavior, different shape |
| `test` | Adds or updates tests only |
| `perf` | Improves performance without changing behavior |
| `build` | Build system or dependency packaging changes |
| `ci` | CI pipeline or automation changes |
| `chore` | Tooling, deps, config, CI |
| `docs` | Documentation only |
| `style` | Formatting, whitespace — no logic change |
| `revert` | Reverts a previous commit |

## Step 4 — present and confirm

Show the full command and ask before running it. For a summary-only commit, use `git commit -m "type(scope): description"`. Use a heredoc only when the commit message includes a body.

### Heredoc rules

**Rule 1:** The closing `EOF` must be flush to the left margin — zero indentation. One indented space causes zsh to hang with `dquote cmdsubst heredoc>`.

**Rule 2:** `)"` goes on its own line immediately after `EOF`, also flush-left.

**WRONG:**
```bash
git commit -m "$(cat <<EOF
  type(scope): description

  - bullet one
  EOF
)"
```

**CORRECT:**
```bash
git commit -m "$(cat <<EOF
type(scope): description

- bullet one
EOF
)"
```

Ask: "Would you like me to run this commit?"

Only execute after explicit user confirmation.

**NEVER include a "Co-Authored-By" line in any commit message.**
