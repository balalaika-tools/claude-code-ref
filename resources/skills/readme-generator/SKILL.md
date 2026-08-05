---
name: readme-generator
description: >
  Generates a complete, professional README.md and docs/ folder for any software
  project. Use this skill whenever the user wants to create, write, or generate a
  README for a repo — even if they just say "make a readme", "document this project",
  "write docs for this", or "add a readme". Also triggers when user asks to "document
  my project", "add documentation", "create project docs", or "write up what this does".
  Always use this skill for README generation — don't improvise your own format.
---

# README Generator

You produce a polished, concise README.md plus a `docs/` folder for any software project. The output should feel like the best open-source READMEs on GitHub: clean, navigable, technically precise, and not padded with fluff.

## Step 1 — Read the project

Collect everything you need in one pass (run reads in parallel where possible):

- `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod` / `requirements.txt` — for stack, versions, description, entry points
- `.env.example` — for environment variable docs
- `Dockerfile` / `docker-compose.yml` — for container deployment docs
- `README.md` (existing, if any) — for context, don't copy wholesale
- Main entry point file (e.g. `src/*/main.py`, `cmd/main.go`, `index.ts`) — to understand what the app actually does
- Top-level directory listing — to build the project tree

If you can't find a version for a dependency, do a quick web search for the current stable version rather than leaving a placeholder.

## Step 2 — Write README.md

Use this exact section order. Keep the total README under ~150 lines; push depth into `docs/`.

### Header

Choose one approach:
- **Icon + title**: If a logo/icon exists in the repo (common in `assets/`, `static/`, `.github/`), use it as an `<img>` tag before the H1.
- **ASCII art title**: Otherwise, generate tasteful ASCII block-letter art for the project name. Use wide, bold block letters — each letter should be full-width and dense, not narrow or cramped. Target this style:

```
███╗   ███╗███████╗██████╗ ██╗ █████╗ ███████╗ ██████╗ █████╗ ██╗     ███████╗
████╗ ████║██╔════╝██╔══██╗██║██╔══██╗██╔════╝██╔════╝██╔══██╗██║     ██╔════╝
██╔████╔██║█████╗  ██║  ██║██║███████║███████╗██║     ███████║██║     █████╗
██║╚██╔╝██║██╔══╝  ██║  ██║██║██╔══██║╚════██║██║     ██╔══██║██║     ██╔══╝
██║ ╚═╝ ██║███████╗██████╔╝██║██║  ██║███████║╚██████╗██║  ██║███████╗███████╗
╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝
                          F R O N T E N D
```

Key style rules:
- Letters must be **6 rows tall** with clean `╗`/`╔`/`╝`/`╚` corners — no malformed or uneven glyphs
- Letters should be **wide and full**, not narrow (e.g. `███████╗` not `██╗`)
- Subtitle line: **ALL CAPS**, one space between each letter (e.g. `F R O N T E N D` not `Frontend` or `F r o n t e n d`), indented to center under the title
- The subtitle should be the project's category, tagline, or type (e.g. `A P I`, `C L I   T O O L`, `I N F R A S T R U C T U R E`)

Follow immediately with the H1 title (if using ASCII art, H1 can be omitted or kept small).

### Badges

One line of shields.io badges representing the actual tech stack. Format:

```markdown
[![Python](https://img.shields.io/badge/Python-3.13-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
```

Rules for badges:
- Extract real version numbers from package manifests. `python = ">=3.13"` → `3.13+`; `fastapi = "^0.115"` → `0.115`
- Use the correct shields.io `logo=` slug and a color that matches the technology's brand. Common ones:
  - Python → `3776AB`, logo=`python`
  - FastAPI → `009688`, logo=`fastapi`
  - Node.js → `339933`, logo=`node.js`
  - TypeScript → `3178C6`, logo=`typescript`
  - Go → `00ADD8`, logo=`go`
  - Rust → `CE422B` (or `000000`), logo=`rust`
  - Docker → `2496ED`, logo=`docker`
  - PostgreSQL → `4169E1`, logo=`postgresql`
  - Redis → `DC382D`, logo=`redis`
  - React → `61DAFB`, logo=`react`
  - Gemini/Google AI → `4285F4`, logo=`google`
  - OpenAI → `412991`, logo=`openai`
- Link each badge to the relevant docs/homepage

### Description

2–4 sentences. What does this project do? What problem does it solve? Who uses it?
Infer from the code and package description — don't just restate the repo name.

### Project Structure

Annotated tree with emojis inline as comments. Go 2–3 levels deep; collapse deeper dirs with `...`.

```
ProjectName/
├── src/
│   └── myapp/
│       ├── api/              # 🌐 HTTP routers, schemas, middleware
│       ├── core/             # ⚙️  Config, logging, constants
│       ├── services/         # 💼 Business logic
│       └── main.py           # 🚀 Entry point
├── tests/                    # 🧪 Test suite
├── docs/                     # 📖 Extended documentation
├── Dockerfile                # 🐳 Container image
├── pyproject.toml            # 📦 Dependencies & metadata
└── README.md
```

Emoji mapping (use these consistently):
- `api/` `routes/` `routers/` → 🌐
- `core/` `config/` `settings/` → ⚙️
- `services/` → 💼
- `domain/` `models/` → 📐
- `llm/` `ai/` `ml/` → 🤖
- `utils/` `helpers/` → 🔧
- `bootstrap/` `factory/` → 🚀
- Entry point files → 🚀
- `logs/` `Logs/` → 📝
- `Dockerfile` `docker-compose*` → 🐳
- `pyproject.toml` `package.json` `Cargo.toml` → 📦
- `docs/` → 📖
- `tests/` `__tests__/` → 🧪
- `db/` `migrations/` → 🗄️
- `scripts/` → 📜
- `.env.example` → 🔑

### Quick Start (`## 🚀 Quick Start`)

**Prerequisites** — bulleted list with versions and clickable links:
```markdown
- Python 3.13+ 
- [uv](https://docs.astral.sh/uv/) package manager
- Gemini API key ([get one free](https://aistudio.google.com/apikey))
```

**Numbered setup steps** (use emoji numbers: 1️⃣ 2️⃣ 3️⃣):

1. **Clone** — `git clone` + `cd` command
2. **Configure** — `cp .env.example .env`, then show the `.env` contents with inline comments explaining each variable
3. **Deploy** — use `<details>` collapsibles for each deployment option:

```markdown
<details>
<summary><b>🔧 Option 1: Local Development</b></summary>

<br>

Steps here...

</details>

<details>
<summary><b>🐳 Option 2: Docker</b></summary>

<br>

Steps here...

</details>
```

For local dev: install deps, activate venv (if applicable), run command, access URLs.
For Docker: `docker build` + `docker run` with flags, access URLs.

Always include access URLs as clickable links (Swagger UI, main endpoint, etc.) if the project exposes an HTTP server.

### Example Usage (`## 📮 Example [API Call / Usage]`)

Include this section if the project has an API, CLI tool, or any interactive usage.

- Show a complete, working `curl` command or CLI invocation
- Put the expected response in a `<details>` collapsible
- If the response is structured (JSON, table), add a **Response Breakdown** table after the collapsible:

```markdown
| Field | Description |
|-------|-------------|
| `status` | `success` or `error` |
| `data` | The computed result |
```

### Documentation (`## 📖 Documentation`)

Link to the docs files you'll create:

```markdown
| File | Description |
|------|-------------|
| [ENVIRONMENT.md](docs/ENVIRONMENT.md) | Environment variables reference |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | App configuration guide |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the codebase works |
```

---

## Step 3 — Write docs/ files

Create a `docs/` directory and generate the following. Write real content — don't use placeholder text.

### docs/ENVIRONMENT.md

Title: `# Environment Variables`

For each variable found in `.env.example` or referenced in config files:

```markdown
## `VARIABLE_NAME`
- **Required**: Yes / No
- **Default**: `value` (or none)
- **Valid values**: `option1` | `option2` | any string
- **Description**: What it controls and why it matters.
```

Group logically (e.g. "API Keys", "App Settings", "Logging").

### docs/CONFIGURATION.md

Title: `# Configuration`

Cover: config file locations, how settings are loaded, environment-specific behavior (`dev` vs `prod`), any feature flags, and how to override defaults. Include code snippets from the actual config code where helpful.

### docs/ARCHITECTURE.md

Title: `# Architecture`

Sections:
1. **Overview** — what the system does end-to-end in plain language
2. **Key Components** — brief description of each major module/package
3. **Request Flow** (for APIs) or **Execution Flow** (for CLIs) — numbered steps or a simple ASCII diagram showing data flow
4. **Design Decisions** — 2–3 notable choices made in the codebase and why

### Additional docs (add as needed)

- `docs/API.md` — if the project is a REST/GraphQL API: endpoints, request/response schemas, auth
- `docs/DEPLOYMENT.md` — if deployment is non-trivial (K8s, cloud functions, multi-service): full deployment guide
- `docs/DEVELOPMENT.md` — if the project is a library or has a complex dev setup: how to contribute, run tests, release

---

## Step 4 — Write all files

Write every file to disk: `README.md`, `docs/ENVIRONMENT.md`, `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, and any additional docs files you created.

Verify:
- No placeholder text (`TODO`, `...`, `your-value-here`) left in any file
- All links in README point to real files you wrote
- Versions in badges match what you found in the project manifests

---

## Style rules

- **Concise main README** — the reader should get oriented in 30 seconds. Depth lives in `docs/`.
- **Real commands only** — every code block must be a command someone can actually run as-is.
- **Collapsibles for length** — use `<details>`/`<summary>` any time a section would exceed ~20 lines.
- **Emoji section headers** — every `##` section gets an emoji prefix.
- **No trailing meta-commentary** — don't end files with "Feel free to update this" or "This was generated by...".
- **No filler sentences** — "This project is designed to..." → cut. Start with what it does.
