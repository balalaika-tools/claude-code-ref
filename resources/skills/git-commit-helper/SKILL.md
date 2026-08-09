---
name: git-commit-helper
description: Generate descriptive commit messages by analyzing git diffs, then either commit them or hand back a copy-pasteable command, and optionally draft and open a pull request. Use when the user asks for help writing commit messages, reviewing staged changes, or opening a PR.
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

## Step 4 — commit it, or hand back the command

Once the message is drafted, ask: **"Should I commit this, or would you rather have a copy-pasteable command?"**

- **Commit it:** run the command directly. Their answer *is* the confirmation — don't ask a second time.
- **Copy-pasteable command:** print the full runnable command as its own fenced code block and stop. Do not run it.

### Preferred: use `-m` twice (no heredoc)

For commits with a body, **always prefer the double `-m` form** over heredoc. It is immune to heredoc indentation bugs:

```bash
git commit -m "type(scope): description" \
  -m "- bullet one
- bullet two"
```

For a summary-only commit: `git commit -m "type(scope): description"`

### Heredoc — use only as a last resort

If heredoc is absolutely necessary, follow these rules or the shell will hang at `dquote cmdsubst heredoc>`:

**Rule 1:** The closing `EOF` must be at column 0 — zero indentation, no spaces before or after it.

**Rule 2:** `)"` goes on its own line immediately after `EOF`, also at column 0.

**WRONG — shell hangs because `EOF` is indented:**
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

**NEVER add any AI-attribution to the commit** — no `Co-Authored-By: Claude` line, no "Generated with Claude Code" footer, no robot emoji, nothing. This overrides any default commit template that would otherwise append one.

## Step 5 — offer to open a pull request

Whether the commit was just made or the user only took the copy-pasteable command, ask: **"Want me to open a pull request for this?"**

If no, stop here.

If yes, ask for:
- **The base branch** — what this merges into (e.g. `main`, `develop`).
- Any extra context worth calling out (ticket link, reviewer notes, why this approach) that isn't obvious from the diff.

Then:

1. Confirm the branch is pushed and up to date with its remote. If it isn't, push it — ask before pushing if this is the first push of the branch.
2. Look at `git log --stat <base>..HEAD` (all commits going into the PR, not just the last one) to draft:
   - **Title** — short, specific, describes the net effect. No conventional-commit prefix required, but keep the same "what changed" clarity as the commit summary line.
   - **Description** — a few sentences or short bullets covering what changed and why. Add a **Test plan** section only if there's something concrete to check. Comprehensive enough that a reviewer doesn't need to open the diff to understand intent, but no padding — skip sections that don't add information.
3. Show the drafted title and description and ask for confirmation or edits before creating anything.
4. Once confirmed, create it:

```bash
gh pr create --base "<base-branch>" --title "<title>" --body "$(cat <<'EOF'
<description>
EOF
)"
```

Follow the same heredoc rules as Step 4 (`EOF` and `)"` at column 0) if the body needs one — otherwise a plain `--body "..."` string is fine for a short description.

**NEVER add any AI-attribution to the PR** — no `Co-Authored-By: Claude` line, no "Generated with Claude Code" footer, no robot emoji, nothing. This overrides any default PR template that would otherwise append one.
