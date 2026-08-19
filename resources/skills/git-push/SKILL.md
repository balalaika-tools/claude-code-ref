---
name: git-push
description: Commit and push staged changes with a well-written conventional-commit message, and optionally draft and open a pull request with a well-structured description. Use when the user asks to commit, push, or "commit and push" their changes, or to open/draft a PR.
---

# Git Push

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

## Step 4 — commit and push by default

Once the message is drafted, commit it directly and push — do not ask whether to commit first or hand back a command instead. Drafting the message already implied the intent to commit; the only thing worth asking about afterward is the PR (Step 5).

```bash
git push
```

If the current branch has no upstream yet, push with `git push -u origin <branch>` instead of a bare `git push`.

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

After committing and pushing, ask: **"Want me to open a pull request for this?"**

If no, stop here.

If yes, ask for:
- **The base branch** — what this merges into (e.g. `main`, `develop`).
- Any extra context worth calling out (ticket link, reviewer notes, why this approach) that isn't obvious from the diff.

Then draft the PR:

1. Look at `git log --stat <base>..HEAD` (all commits going into the PR, not just the last one) to understand the full scope.
2. **Title** — same conventional-commit prefix as a commit summary line: `type(scope): description`, e.g. `refactor: reorganize api into responsibility-based packages` or `fix(scraper): make pdp extraction resilient to hidden content`. Short, specific, describes the net effect — not "misc fixes" or "updates."
3. **Description** — read `references/pr-examples.md` before drafting this. It has two synthesized examples (a large multi-section fix, and a small callout-led refactor) plus a breakdown of what makes each work. They illustrate a *style*, not a *template* — do not copy their section names, headings, or wording onto an unrelated PR just because they're there. Judge each PR on its own diff:
   - `Summary` is nearly always worth having — for some reviewers it's the only section they'll read.
   - Beyond that, sections are a menu, not a checklist: `Why this was needed`, `What changed`, `Live verification` / manual test evidence, `Automated tests`, `Operational considerations`, `Review checklist`, etc. Include only the ones that carry real information for *this* change — an empty or boilerplate section is worse than omitting it. A small mechanical PR might need only `Summary` and `Verification`; a complex fix with rejected alternatives and edge cases earns most of the list. Feel free to use a different section name, or none of the above, when the change calls for it — e.g. a `Migration steps` section for a schema change, or a `Rollback plan` for a risky infra change.
   - Lead with a `> [!IMPORTANT]` (or `[!WARNING]`/`[!NOTE]`) callout only when there's one fact a reviewer must not miss — a deliberate non-goal ("no behavior change intended"), a breaking change, a required migration step. Most PRs don't need one; don't add it reflexively just because the examples have it.
   - Prefer concrete detail (file paths, counts, before/after numbers, table comparisons) over adjectives like "greatly improved" or "much more robust."
   - State explicitly what's deliberately *not* included or *not* changed when a reviewer might otherwise wonder if it was forgotten.
   - Comprehensive enough that a reviewer doesn't need to open the diff to understand intent, but no padding.
4. Show the drafted title and description and ask for confirmation or edits before creating anything.
5. Once confirmed, create it:

```bash
gh pr create --base "<base-branch>" --title "<title>" --body "$(cat <<'EOF'
<description>
EOF
)"
```

Follow the same heredoc rules as the commit message (`EOF` and `)"` at column 0) if the body needs one — otherwise a plain `--body "..."` string is fine for a short description.

**NEVER add any AI-attribution to the PR** — no `Co-Authored-By: Claude` line, no "Generated with Claude Code" footer, no robot emoji, nothing. This overrides any default PR template that would otherwise append one.
