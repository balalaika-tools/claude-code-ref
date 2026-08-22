# Getting Started Safely with Claude Code

> **Who this is for**: Engineers who are comfortable with a terminal and Git but have not used Claude Code. You need access through a Claude Pro, Max, Teams, Enterprise, or Console account, or through an organization-managed cloud provider.

Before starting, use a disposable branch or a clean working tree in a project you understand. This makes Claude's changes easy to inspect and reverse.

---

## 1️⃣ Install One Copy and Verify It

The **native installer** is the recommended path. Choose the command for your platform; do not install Claude Code through several package managers because duplicate binaries can make updates appear to fail.

macOS, Linux, or WSL:

```bash
curl -fsSL https://claude.ai/install.sh | bash

# Open a new shell if the installer changed PATH, then verify both resolution and health.
command -v claude
claude --version
claude doctor
```

Windows PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex

# Restart PowerShell if the command is not immediately available.
Get-Command claude
claude --version
claude doctor
```

The native installation checks for updates in the background; an update takes effect the next time Claude Code starts. Apply one immediately with:

```bash
claude update
claude --version
```

Package-manager installations update through their package manager by default:

| Installation | Install | Update |
|---|---|---|
| Homebrew | `brew install --cask claude-code` | `brew upgrade claude-code` |
| WinGet | `winget install Anthropic.ClaudeCode` | `winget upgrade Anthropic.ClaudeCode` |
| npm fallback | `npm install -g @anthropic-ai/claude-code` | `npm install -g @anthropic-ai/claude-code@latest` |

The npm package requires Node.js 18 or later. Prefer `npm install ...@latest` to `npm update -g`, which can remain inside the version range from the original installation.

> ⚠️ **Installer trust**: A pipe-to-shell command downloads and executes remote code. Use Homebrew, WinGet, or your organization's approved distribution path if policy requires package review or version pinning.

---

## 2️⃣ Choose the Authentication and Billing Path

Run `claude` after installation. For first-party accounts, Claude Code opens a browser login. If a browser cannot reach the local callback—common over SSH, WSL2, or in a container—press `c` to copy the login URL, complete authentication elsewhere, and paste the displayed code into the terminal when prompted.

| Path | Best fit | What to know |
|---|---|---|
| Claude Pro or Max | Individual development | Claude Code usage is included subject to the plan's usage limits. A free Claude.ai plan does not include Claude Code access. |
| Claude for Teams or Enterprise | Organization-managed users | Sign in with the Claude.ai account invited by the organization; administrators can apply organization policy. |
| Claude Console | API-funded work | Usage is charged by API token consumption and tracked in the Console. |
| Amazon Bedrock, Google Vertex AI, or Microsoft Foundry | Organizations that require their cloud provider | Configure the provider's environment and credentials before launch; this path does not use the browser login flow. |

Confirm which credential Claude Code selected:

```bash
if ! claude auth status; then
  printf 'Claude Code authentication failed; complete login before continuing.\n' >&2
  exit 1
fi

claude
```

Inside Claude Code, `/status` shows the active authentication method. Use `/logout` when switching accounts, then start the login flow again. Avoid exporting a personal API key into a shared shell profile; use your organization's credential mechanism and provider-specific setup instead.

---

## 3️⃣ Inspect a Project Before Trusting It

Claude Code asks for **project trust** the first time it opens a codebase. Trust is not a statement about the source code alone: it allows project configuration such as `.claude/settings.json`, `.mcp.json`, hooks, and marketplace settings to take effect.

Inspect the repository with ordinary shell tools first:

```bash
project_dir="/absolute/path/to/your/project"

if [ ! -d "$project_dir/.git" ]; then
  printf 'Not a Git worktree: %s\n' "$project_dir" >&2
  exit 1
fi

cd "$project_dir"
printf 'Working directory: %s\n' "$PWD"
git status --short --branch

# These files can alter Claude Code's instructions, permissions, tools, or hooks.
find . -maxdepth 3 \
  \( -name 'CLAUDE.md' -o -name '.mcp.json' -o -path './.claude/*' \) \
  -print
```

Read any files listed before accepting the trust dialog. Pay particular attention to hooks that execute commands, MCP servers that launch local processes or contact services, permission allowlists, and instructions that request credentials or external uploads.

Start from the project directory, not your home directory:

```bash
cd "/absolute/path/to/your/project"
claude --permission-mode plan
```

Trust accepted in a project directory is saved for that directory. Trust accepted when Claude Code starts directly in the home directory lasts only for that session, so the prompt returns on the next launch. Do not use non-interactive `-p` mode for a first inspection: normal trust verification is disabled there, except for `--worktree`.

> **Rule**: If you would not execute a repository's setup script, do not trust its Claude Code configuration. Inspect it in a sandbox or VM first.

---

## 4️⃣ Make the First Session Read-Only

**Plan mode** lets Claude read and search the project and run read-only exploration commands, but it does not edit source files. It is a good first-session default because the initial result is an explanation you can verify.

Paste this as the first prompt:

```text
Read this repository without changing files. Summarize:
1. the main entry points and runtime boundaries,
2. the documented build and test commands,
3. any project-specific Claude configuration,
4. the smallest safe validation command for a later step.

Do not install dependencies, access the network, read secret files, or modify anything.
Cite the file path supporting each conclusion and call out anything uncertain.
```

Check the answer against the cited files. If the repository is large, narrow the task to one service or package instead of asking Claude to ingest unrelated directories.

When you are ready to leave plan mode, use `Shift+Tab` to cycle back to **default mode**. Default mode allows reads without prompting but asks before file edits, shell commands, and network requests.

> ⚠️ **Read access matters**: A tool approval dialog is not a data-loss-prevention boundary. Claude can normally read in-scope project files without prompting, so keep secrets out of the workspace or deny access to them in permission settings.

---

## 5️⃣ Approve One Bounded Tool Action

Ask for a validation action that has a known command and no installation or deployment side effects:

```text
Run the smallest existing unit-test command that does not install packages,
change files, access the network, use credentials, start a long-lived process,
or contact external services. Before requesting permission, show the exact
command, working directory, expected duration, and why repository files support it.
Stop after reporting the result.
```

When Claude requests permission, verify:

1. The executable and every argument are visible and expected.
2. The working directory is inside the intended project.
3. The command does not contain a pipe, redirect, command substitution, installer, deployment, or destructive flag you did not request.
4. No credential, environment secret, or sensitive path appears in the command.
5. The scope is one action. Choose a one-time approval rather than a persistent “don't ask again” rule while learning the project.

Deny the request if any detail is wrong, explain the constraint, and ask Claude to propose a narrower command. A denial is feedback, not a failed session.

After any edit, review with your normal tooling:

```bash
git status --short
git diff --check
git diff
```

Do not approve based only on Claude's natural-language description. The command and diff are the artifacts that matter.

---

## 6️⃣ Recognize Common Failure Modes

| Symptom | Likely cause | Safe next step |
|---|---|---|
| `claude: command not found` | The install directory is not on `PATH`, or the shell has not reloaded it | Open a new terminal, then follow the platform-specific PATH steps in the installation troubleshooting guide |
| The version does not change after updating | Multiple installations resolve to different binaries | Run `which -a claude` on macOS/Linux/WSL or `where.exe claude` on Windows; retain one installation method |
| Browser login never completes | The local OAuth callback is unreachable | Copy the login URL with `c`, authenticate in a browser, and paste the code back into the terminal |
| Claude repeatedly asks for login | Expired credentials, an incorrect system clock, or a locked macOS Keychain | Run `claude doctor`, correct the clock or credential-store issue, then use `/login` |
| A project asks for surprising permissions | Unreviewed project configuration or an over-broad task | Deny the action, exit, and inspect `.claude/`, `.mcp.json`, and `CLAUDE.md` |
| A command hangs or the direction is wrong | A long-running tool or misunderstood task | Press `Esc` to interrupt, then restate a smaller task with explicit stop conditions |
| Usage is exhausted or the API rejects more work | A subscription allowance, API balance, or rate limit was reached | Run `/usage`, read the reset or billing message, and wait or use the approved billing path |

Use `claude doctor` from the shell if Claude Code will not start. Use `/doctor` inside a running session to check installation health, settings, MCP servers, and context usage.

---

## 7️⃣ Protect Data and Control Cost

Claude Code runs locally, but model requests send prompts, model outputs, and relevant project content over the network. Local session transcripts are also stored in plaintext under `~/.claude/projects/` for 30 days by default. Check your account's data controls, your organization's policy, and the selected provider before using regulated or confidential code.

Practical safeguards:

- Keep credentials outside the repository and add explicit deny rules for `.env`, key, and secret paths.
- Review commands before approval, especially network access and text copied from issues, web pages, or generated files; those inputs can contain prompt injection.
- Use a VM or isolated container for untrusted repositories, downloaded scripts, or risky tool calls.
- Keep the Git worktree clean, work on a branch, and inspect every diff before commit.
- Never use `bypassPermissions` on a normal workstation. It is intended only for controlled, isolated environments.

For cost control, run `/usage` and keep context focused. Subscription plans show allowance and activity information; API users see token usage and an estimated session cost, while the Console remains the authoritative billing record. Use `/clear` when switching to an unrelated task so stale context is not processed again.

> **Key insight**: Permission prompts limit actions, not what context is sent to the model. Data policy, file-access rules, task scope, and an isolated runtime are separate controls.

---

## 8️⃣ Know When Not to Use Claude Code

Do not use Claude Code when:

- The repository or its Claude configuration is untrusted and you cannot inspect it in an isolated environment.
- Policy forbids sending the necessary code or data to the configured model provider.
- The task requires deterministic, formally verified output with no human review.
- A production incident demands a known runbook and predictable commands rather than exploratory agent behavior.
- The work involves irreversible infrastructure, credential rotation, data deletion, or production migration without backups, review, and a purpose-built sandbox.
- A formatter, compiler, codemod, or short deterministic script already performs the transformation more cheaply and repeatably.

Claude Code is most useful when the task benefits from codebase reasoning and you can review both the proposed actions and the resulting diff.

Official references:

- [Advanced setup and installation](https://code.claude.com/docs/en/installation)
- [Authentication](https://code.claude.com/docs/en/authentication)
- [Quickstart](https://code.claude.com/docs/en/quickstart)
- [Security](https://code.claude.com/docs/en/security)
- [Permission modes](https://code.claude.com/docs/en/permission-modes)
- [Configure permissions](https://code.claude.com/docs/en/permissions)
- [Data usage](https://code.claude.com/docs/en/data-usage)
- [Manage costs](https://code.claude.com/docs/en/costs)
- [Troubleshoot installation and login](https://code.claude.com/docs/en/troubleshoot-install)

---

**Next**: [Sessions and Core CLI](02_sessions_and_cli.md)
