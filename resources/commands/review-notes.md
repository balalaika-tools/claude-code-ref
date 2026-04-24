---
description: Review and improve a technical notes repository. Checks internal consistency, technical correctness, educational quality, and currency (uses web search for fast-moving topics), then applies the fixes directly to the files and reports what changed. Fans out to parallel subagents when the repo has more than two markdown files.
argument-hint: [path-to-notes-directory]
allowed-tools: Read, Glob, Grep, Bash, WebFetch, WebSearch, Agent, Edit, Write
---

# Review & Improve Notes

Review the technical notes repository at `$ARGUMENTS`. If no path is given, default to the current working directory — but first confirm the directory actually contains a notes repo (a root `README.md` and a handful of `.md` files); if not, stop and ask where the notes live.

You are acting as an independent technical editor. Your job is to make the notes correct, clear, and current — not to rewrite them in your own voice. Evaluate against general best practices for technical writing and the repo's own internal conventions, which you infer by reading the existing files.

---

## The editing bar

Default to **leaving things alone**. Only change something when one of these is true:

- It is **wrong** — broken code, incorrect facts, dead links, wrong version numbers, typos that change meaning.
- It is **unclear in a way a reader would trip over** — missing prerequisite, ambiguous pronoun, undefined term introduced as if already known.
- It is **stale** — deprecated API, removed CLI flag, superseded practice (confirmed via web search, not memory).
- It is **teaching a questionable technique** — the pattern shown is widely considered bad practice, has been superseded by a better approach the community has adopted, or has real downsides the notes do not acknowledge. Refactor the example to the current recommended pattern. If you are not confident the alternative is genuine consensus (not just your preference), confirm via web search first, or leave it and flag it in the report.
- It **breaks the repo's own conventions** — once you have read enough files to see the convention, inconsistent files should match.

**Do not** change prose because you would have phrased it differently, reorganize sections that already work, add "helpful" preambles, swap one valid code style for another, or expand terse-but-clear explanations into longer ones. Churn for its own sake makes diffs hard to review and erodes the author's voice. When in doubt, leave it and note it in the "skipped" section of the final report.

---

## What to check

Four axes. An issue must fall into one of these to be worth acting on.

### 1. Internal consistency

Infer conventions from the repo itself, then enforce them. Common things to notice:

- File naming (numbered prefixes, kebab-case vs snake_case) — once a pattern is established, outliers should conform.
- Per-file shape — if most files open with a one-line purpose and close with next-steps, files that skip this should add it.
- Terminology — if the same concept is called a "worker" in file 2 and a "runner" in file 5, pick the more common term and unify.
- Cross-links — every relative link and anchor must resolve. Use `Glob` / `Grep` to verify rather than skimming.
- Badges, callouts, emoji — whatever style the repo has established, keep it uniform.

### 2. Technical best practices

**Mechanics:**

- Code examples are **runnable, not pseudocode**: imports and setup are complete enough to copy-paste and have a real shot at working.
- Fenced blocks carry a language tag (```` ```python ````, not bare ```` ``` ````).
- No residual placeholders — `TODO`, `FIXME`, `lorem ipsum`, "your code here", unresolved `{{variables}}`.
- Version numbers, CLI flags, API shapes, default values, and config keys are accurate. Cross-check the ones that matter; fix the ones that don't.
- Code uses current idiomatic syntax, not deprecated forms (confirmed on the web when unsure — see axis 4).
- Security pitfalls (hard-coded secrets, `rm -rf` without guards, unquoted shell vars, SQL string concatenation) get called out or fixed.

**Technique and pattern soundness** — this is about *what* the notes teach, not how they write it. Even code that runs and reads cleanly can be teaching the wrong thing. Scrutinize the approach itself:

- **Deprecated patterns taught as current.** `var` where `let`/`const` is the norm; callback pyramids where `async`/`await` is standard; React class components as the default shape; `moment` where the ecosystem has moved to Temporal / `date-fns` / Luxon; old `enzyme`-style tests where `@testing-library` is consensus; pre-PEP-8 Python idioms; etc.
- **Anti-patterns.** Mutable global state where dependency injection is easy, bare `except:` in Python, `git push --force` without qualification, `pip install` shown without a virtualenv, Dockerfiles that bake in secrets or run as root, `curl | sh` installs demonstrated as the happy path, string-concatenated SQL (also a security hit), God-objects, premature optimization presented as the standard approach.
- **Missing community consensus.** Teaching one approach without mentioning the ecosystem has moved — e.g. hand-rolled Redux boilerplate without mentioning Redux Toolkit, raw `fetch` with manual retry logic where a library is the standard answer, manual Terraform state surgery instead of `moved`/`import`/`removed` blocks, hand-written CloudFormation where Terraform or CDK is the repo's standard.
- **Correct but out of context.** Imperative DOM manipulation shown inside a React file, `SELECT *` in application code (fine in a REPL, not in docs), classical inheritance hierarchies in a codebase that is otherwise composition-first.
- **Trade-offs silently hidden.** A technique is presented as "the way" when it is actually one of several, each with different costs. Either explain the trade-off or switch to the option with the clearer profile for the audience.

**When you find one, refactor the example itself** — do not just add a footnote saying "there is a better way," because readers skim examples and copy them. If the fix is large (e.g. rewriting a whole file's running example from class-based to hook-based React), make the change and note it prominently in the "Changes applied" section so the author can sanity-check.

**Guardrail:** refactor only when the better approach is genuine community consensus for the domain, not just a preference you hold. If you are unsure, `WebSearch` for recent authoritative sources (official docs, widely-cited posts, style guides from the project/community). If consensus is murky, leave the code alone and flag it in "Deliberately not changed" with your reasoning — dragging notes toward a contested position is worse than leaving them at a defensible one.

### 3. Educational quality

Be honest here — this is what makes notes useful vs. a dump.

- The learning progression holds: a reader who finishes file N should be ready for file N+1.
- Prerequisites and next-steps are **meaningful**, not decorative. "Prerequisite: basic programming" is filler; "Prerequisite: file 02, specifically the generators section" is real.
- Examples illustrate a *concept*, not just demonstrate syntax. A hello-world that teaches nothing non-obvious is a missed opportunity — flag it or replace the example, but do not just polish the prose.
- Trade-offs and *why* are present. Notes that say *how* to do X without ever saying *when* are weak.
- Hard bits are called out (⚠️ / 💡 / bold / block-quote — whatever style the repo uses) instead of buried mid-paragraph.

### 4. Currency (use the web deliberately)

For version- or API-specific content, confirm it matches the state of the world today. Use `WebSearch` / `WebFetch` — do not rely on memory for version numbers or deprecation status.

- Out-of-date version numbers.
- APIs / flags / config options deprecated or removed in current releases.
- Materially important new features the notes miss. ("The framework added X and it changes the recommended pattern" is worth flagging; "the framework released a minor version last week with bug fixes" is not.)

**Be decisive about when to search.** Search liberally for fast-moving areas: JS frameworks, AI/ML libraries, cloud provider features, Kubernetes, LLM APIs. Skip for stable areas: POSIX, SQL, CS fundamentals, classical algorithms. The goal is to catch real staleness, not burn tokens confirming that `SELECT` still works.

---

## How to work the repo

1. Read the root `README.md` to understand structure, audience, and any reading paths.
2. Use `Glob` to list every `*.md` file under the target directory, including nested ones.
3. Count them, then choose the approach:
   - **0–2 markdown files:** review and edit inline yourself.
   - **3 or more markdown files:** fan out to subagents. Group files into chunks of 2–4 (prefer grouping by directory, since files in the same directory typically share context). Spawn one subagent per chunk **in parallel** (one message, multiple `Agent` tool calls). Each subagent should:
     - Receive the full editing bar and four-axis criteria from this command (paste them in — subagents have no memory of this conversation).
     - Receive the specific file paths it owns.
     - Apply edits directly to those files, honoring the "default to leaving things alone" rule.
     - Return a compact per-file report: what it changed, what it deliberately did not change and why, and any currency findings. Cap the report at 400 words.
4. While subagents run, handle cross-cutting things yourself: the root `README.md`, any reading-paths index, terminology unification across files (which a per-chunk subagent cannot see end-to-end).
5. Aggregate the subagents' reports and fold them into a single final report.

If two subagents would propose conflicting changes (e.g. both rename the same shared term differently), prefer the change that matches the repo's existing majority usage, and note the conflict in the final report.

---

## Output format

After all edits are applied, produce one report in this structure:

```
# Notes Review: <repo-name>

## Summary
<2–3 sentences: overall state of the repo now, how much needed fixing, whether anything material was out of date>

## Changes applied
- [file:line] What was wrong — What it was changed to (and why)
- …

## Deliberately not changed
- [file:line] Issue noticed — Why it was left alone (e.g. stylistic, debatable, out of scope)
- …

## Currency findings (from web lookups)
- <topic> — <what was outdated / newly deprecated>, with source URL. Note whether it was fixed in-place or only flagged.
- …

## What's working well
- <specific strengths worth preserving>
- …

## Coverage
- Files reviewed: N
- Files edited: M
- Reviewed via subagents: Y/N (and how many subagents spawned)
- Topics searched on the web: <list>
```

If the number of changes is very large, cap the "Changes applied" and "Deliberately not changed" sections at the 10 most important items each and append "… and N more of the same kind" — don't silently drop them.
