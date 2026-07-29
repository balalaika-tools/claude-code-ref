# Sessions and the Claude Code CLI

> **Who this is for**: Engineers who have installed and authenticated Claude Code and want to use it safely in daily terminal work and automation.

Before reading this, complete **[Getting Started](01_getting_started.md)**.

---

## 1. Choose the Execution Style First

Claude Code has two primary terminal styles:

```text
┌──────────────────────┐
│ One task or question │
└──────────┬───────────┘
           │
           ├── Needs dialogue, steering, or approvals?
           │      └── Interactive: claude
           │
           └── Needs deterministic stdin/stdout for a script?
                  └── Print mode: claude -p "..."
```

| Style | Command | Lifecycle | Best fit |
|---|---|---|---|
| Interactive | `claude` | Keeps a conversation open | Exploration, implementation, debugging, iterative review |
| Interactive with a first prompt | `claude "explain the authentication flow"` | Runs the prompt, then stays open | Starting a focused working session |
| Print mode | `claude -p "explain the authentication flow"` | Runs one prompt and exits | Scripts, CI, pipes, machine-readable output |

Start an interactive session from the project root so Claude gets the intended working directory and project configuration:

```bash
cd /path/to/project
claude
```

Use print mode when the caller, rather than a human at the terminal, owns control flow:

```bash
git diff --check |
  claude -p \
    --permission-mode dontAsk \
    --tools "" \
    "Explain any whitespace errors from stdin. Return only actionable findings."
```

`--tools ""` removes tools because the complete input is already on stdin. This narrows the run and avoids accidental repository access.

⚠️ Print mode disables the first-run trust prompt. Run it only in directories and with input you trust, and restrict tools and permissions for unattended jobs.

> **Rule**: Use interactive mode for uncertain work that benefits from steering. Use print mode when inputs, permissions, output, failure handling, and cost limits can be stated up front.

---

## 2. Work Effectively in an Interactive Session

An interactive session preserves the dialogue while Claude reads files, runs tools, and proposes or applies changes. A useful opening prompt gives the outcome, scope, constraints, and verification command:

```text
Fix the failing token-refresh tests in src/auth/.
Do not change the public API.
Run the focused auth test suite, then show me the diff and any remaining risks.
```

Use built-in commands to inspect or alter session behavior:

| Command or key | Purpose |
|---|---|
| `/model` | Select the session model |
| `/effort` | Select or reset reasoning effort |
| `Shift+Tab` | Cycle the enabled permission modes |
| `/context` | Show what occupies the context window |
| `/compact [focus]` | Summarize older context while preserving a stated focus |
| `/clear` | Start a fresh session while leaving the previous one resumable |
| `/usage` | Inspect session usage; API cost figures are estimates |
| `/rename name` | Give the session a stable, searchable name |
| `/doctor` | Check the current setup and offer fixes |

Prefix a command with `!` when you want to run it directly and include its output in the conversation:

```text
! git status --short
! npm test -- --runInBand
```

Direct shell mode is convenient, but its output consumes context. Prefer a focused command over dumping an entire build log or repository listing.

---

## 3. Continue, Resume, or Fork Deliberately

A **session** is a locally saved conversation associated with a project directory. Choose continuity based on whether new work should append to the original transcript:

| Intent | Command | Result |
|---|---|---|
| Reopen the latest session for this directory | `claude --continue` or `claude -c` | Reuses the existing session ID |
| Choose a saved session | `claude --resume` | Opens the session picker |
| Reopen a known session | `claude --resume auth-refactor` | Reuses the named session |
| Try an alternative without changing the original transcript | `claude --resume auth-refactor --fork-session` | Copies history into a new session ID |
| Branch the active conversation | `/branch try-cookie-sessions` | Switches to a new session and preserves the original |

Name important work at startup:

```bash
claude --name auth-refactor \
  "Map the current authentication flow before proposing changes."
```

Resume it later:

```bash
claude --resume auth-refactor \
  "Continue with the refresh-token implementation."
```

Fork when experimenting with a competing approach:

```bash
claude --resume auth-refactor \
  --fork-session \
  --name auth-refactor-cookie-variant \
  "Explore an HTTP-only cookie design without modifying the original session."
```

✅ Forking is also the safe choice when two terminals need to explore from the same history. Resuming the same session in both terminals can interleave messages into one transcript.

Sessions created by print mode do not appear in the interactive picker, but a caller can capture the returned session ID from JSON output and resume it directly. Use `--no-session-persistence` for a print-mode task whose transcript should not be saved locally:

```bash
claude -p \
  --no-session-persistence \
  --tools "" \
  "Summarize the release note supplied on stdin." < release-note.txt
```

⚠️ Ordinary sessions are written to local transcript files. Treat those files as potentially sensitive because prompts, file content, and tool results can appear in them.

---

## 4. Select a Model and Reasoning Effort

The unqualified `claude` command uses the runtime default for your account and provider. That is the right starting point for most work because model availability and defaults can vary.

Use `/model` interactively or `--model` at startup when you need an explicit choice:

```bash
claude --model sonnet \
  "Implement the approved pagination plan and run the focused tests."
```

Family aliases such as `sonnet`, `opus`, `haiku`, and `fable` follow the current model for that family. A full model ID is more reproducible for tested automation, but it requires deliberate upgrades when that version becomes unavailable or outdated.

**Effort** controls the reasoning-versus-latency and token-spend trade-off on models that support it:

```bash
# A bounded, straightforward task
claude --model sonnet --effort medium \
  "Rename the internal metric and update its focused tests."
```

Reset an interactive session to the selected model's default:

```text
/effort auto
```

| Need | Practical choice |
|---|---|
| Routine, tightly scoped edit | Default model; medium or default effort |
| Ambiguous bug or architectural decision | More capable model and higher effort |
| Latency- or cost-sensitive classification | Faster model and lower effort |
| Reproducible automation | Explicit model plus a tested effort level |

Supported effort levels depend on the selected model and organization policy. Confirm available choices in `/model` or `/effort`; an unsupported level may be reduced to the nearest supported one.

⚠️ Higher effort is not free accuracy. It increases latency and token spend and can overthink simple work. Thinking tokens are billed even when the thinking display is collapsed.

---

## 5. Match the Permission Mode to the Risk

A permission mode sets the baseline for which actions run without asking. Permission allow, ask, and deny rules can narrow or expand that baseline, except that `bypassPermissions` skips the permission layer.

| Mode | Baseline behavior | Use it for |
|---|---|---|
| `default` (`manual` alias) | Reads without asking; prompts for changes and commands | New projects and sensitive work |
| `acceptEdits` | Auto-accepts file edits and common filesystem operations | Interactive implementation you are reviewing |
| `plan` | Read-only analysis and planning | Understanding impact before any edit |
| `auto` | Runs actions through background safety checks instead of prompting | Long, trusted tasks when the account supports it |
| `dontAsk` | Denies anything that would prompt; pre-approved operations still run | Locked-down CI and scripts |
| `bypassPermissions` | Skips permission prompts and safety checks | Disposable, isolated containers or VMs only |

Start read-only when the scope is uncertain:

```bash
claude --permission-mode plan \
  "Trace all callers of the billing client and propose a migration plan."
```

For unattended analysis, fail closed and expose only the required tools:

```bash
claude -p \
  --permission-mode dontAsk \
  --tools "Read,Glob,Grep" \
  --allowedTools "Read" "Glob" "Grep" \
  "Find direct SQL string construction. Report file, line, and risk; do not edit."
```

`dontAsk` prevents a hidden prompt from hanging CI. If the task needs another operation, it fails instead of silently gaining authority.

❌ Do not use `bypassPermissions` on a developer workstation or a networked environment containing valuable credentials. It provides no protection against prompt injection or unintended actions.

💡 If you need less prompting without removing checks, prefer a sandbox, narrow allow rules, or supported `auto` mode over bypassing permissions.

---

## 6. Add Directories Without Losing the Security Boundary

Claude starts with the directory you launched it from. Add sibling repositories or shared packages explicitly:

```bash
cd /path/to/workspace/api
claude \
  --add-dir ../web \
  --add-dir ../shared \
  "Trace the user-profile contract across the API, web app, and shared types."
```

Each `--add-dir` path must already exist and be a directory. The flag grants Claude file access to a wider scope, so add the smallest directories that satisfy the task.

To persist known directories, configure them in a settings file:

```json
{
  "permissions": {
    "additionalDirectories": [
      "../web",
      "../shared"
    ]
  }
}
```

Adding a directory does not generally make its `.claude/` directory another full configuration root. Do not assume its settings, hooks, or other project configuration are active. Keep authoritative repository-wide instructions in the primary project configuration, or enable a documented feature explicitly when you intend to load content from added directories.

⚠️ Added paths enlarge both the accessible filesystem scope and the set of content that could contain hostile instructions. Review third-party repositories before granting unattended access.

---

## 7. Produce Output a Program Can Trust

Print mode supports three output formats:

| Format | Shape | Use it when |
|---|---|---|
| `text` | Plain response text | A human or simple pipe consumes the result |
| `json` | One JSON result with session and usage metadata | A script needs the final answer and metadata |
| `stream-json` | Newline-delimited JSON events | A process needs progress before completion |

`json` output wraps the answer; it is not the answer text by itself:

```bash
claude -p \
  --output-format json \
  --permission-mode dontAsk \
  --tools "Read,Glob,Grep" \
  "Summarize the public API surface."
```

Use `--json-schema` when downstream code requires validated fields. Claude may use tools and multiple turns, then validates the final result against the schema:

```bash
#!/usr/bin/env bash
set -euo pipefail

schema='{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "summary": {"type": "string"},
    "risks": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": ["summary", "risks"]
}'

review_output="${CLAUDE_REVIEW_OUTPUT:-claude-review.json}"
temporary_output="$(mktemp "${TMPDIR:-/tmp}/claude-review.XXXXXX")"
trap 'rm -f "$temporary_output"' EXIT

if ! claude -p \
  --permission-mode dontAsk \
  --tools "Read,Glob,Grep" \
  --allowedTools "Read" "Glob" "Grep" \
  --output-format json \
  --json-schema "$schema" \
  --max-turns 8 \
  --max-budget-usd 1.50 \
  "Review the authentication module. Return a concise summary and concrete risks." \
  >"$temporary_output"; then
  echo "Claude review failed; no validated result is available." >&2
  exit 1
fi

mv "$temporary_output" "$review_output"
trap - EXIT
echo "Validated response written to $review_output"
```

The schema-conforming value is in the response’s `structured_output` field; the surrounding object contains metadata such as the session ID and usage. A schema error or exhausted validation retries produces a failure, so callers must check the exit status before consuming the file.

`stream-json` is newline-delimited events, not one JSON document. Parse it one line at a time:

```bash
claude -p \
  --output-format stream-json \
  --verbose \
  --permission-mode dontAsk \
  --tools "Read,Glob,Grep" \
  "Inventory deprecated API calls in src/."
```

---

## 8. Bound Cost and Failure in Automation

Unattended agent loops need both capability restrictions and stopping conditions:

```bash
claude -p \
  --permission-mode dontAsk \
  --tools "Read,Glob,Grep" \
  --allowedTools "Read" "Glob" "Grep" \
  --max-turns 6 \
  --max-budget-usd 1.00 \
  --output-format json \
  "Review the current diff for correctness and security risks."
```

| Control | What it limits | Failure behavior |
|---|---|---|
| `--max-turns N` | Agentic turns in print mode | Exits with an error when the limit is reached |
| `--max-budget-usd N` | API-call spend in print mode, including subagents | Stops further work when the cap is reached |
| `--tools` | Which built-in tools are available | Omitted tools cannot be selected |
| `--allowedTools` | Which matching tools run without prompting | Other actions follow the permission mode |
| `dontAsk` | Whether an unmatched action can prompt | Unapproved actions are denied |

A budget or turn limit can stop a run before it produces a complete answer. Treat a non-zero exit status as a failed job and never publish a partial artifact automatically.

JSON output includes local cost estimates, but those figures can drift from authoritative billing. Use provider billing data for financial controls, and use CLI budgets as per-run guardrails rather than accounting records.

Avoid piping secrets or untrusted issue text into a tool-enabled agent. Content can contain prompt injection, and command-line arguments may also be visible in shell history or process listings. Prefer stdin for sensitive prompt data, minimize enabled tools, and use short-lived credentials in CI.

---

## 9. Manage Context and Diagnose Failures

The context window contains conversation history, file contents, command output, project instructions, loaded skills, and system instructions:

```text
files + tool output + conversation + instructions
                         │
                         ▼
                 context approaches limit
                         │
              ┌──────────┴──────────┐
              │                     │
       remove old tool output   summarize history
              │                     │
              └──────────┬──────────┘
                         ▼
                    keep working
```

Claude compacts automatically near the limit. Compaction first clears older tool output and then summarizes conversation history as needed. Important early details can still be lost, so put durable project rules in `CLAUDE.md`, not only in the opening prompt.

Use the narrowest operation that solves the problem:

```text
/context
/compact preserve the accepted API decisions and outstanding test failures
/clear
```

| Situation | Best action |
|---|---|
| You need to understand context usage | `/context` |
| The task is still the same but history is noisy | `/compact` with a concrete focus |
| You are starting an unrelated task | `/clear` or a new named session |
| A huge file or tool result repeatedly refills context | Read a smaller range, filter output, or start fresh |
| You need a reversible alternative approach | Fork the session; do not compact away the decision point |

Common operational failures:

| Symptom | Likely cause | Recovery |
|---|---|---|
| CI waits or fails on a tool request | The run needs interactive approval | Use `dontAsk` plus narrow, explicit allow rules |
| `--add-dir` fails immediately | Path is missing or is not a directory | Resolve and validate the path before launching |
| JSON parser fails on streamed output | `stream-json` is NDJSON | Parse each line as a separate event |
| Structured output is absent | Invalid schema, validation exhaustion, budget limit, or turn limit | Check stderr and exit status; simplify the schema or task |
| A resumed session contains mixed conversations | The same session was used concurrently | Fork before parallel exploration |
| Context compaction repeats or errors | One file or tool result is too large | Narrow the read or command output, then compact or clear |
| Claude behaves incorrectly only in one project | A hook, skill, MCP server, or instruction is broken | Run `claude doctor`, then compare with `claude --safe-mode` |
| The failure still lacks detail | Runtime or integration issue | Reproduce with `claude --debug "api,hooks,mcp"` |

> **Key insight**: A reliable Claude Code run has four explicit boundaries: working directories, available tools, stopping conditions, and output contract.

### Official references

- [CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Manage sessions](https://code.claude.com/docs/en/sessions)
- [Non-interactive mode](https://code.claude.com/docs/en/headless)
- [Permission modes](https://code.claude.com/docs/en/permission-modes)
- [Model configuration](https://code.claude.com/docs/en/model-config)
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- [Security](https://code.claude.com/docs/en/security)
- [Costs](https://code.claude.com/docs/en/costs)

---

**Next**: [CLAUDE.md — Rules & Memory](../rules/01_claude_md.md)
