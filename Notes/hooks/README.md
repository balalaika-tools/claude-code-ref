# Hooks

> Deterministic shell commands, HTTP calls, and LLM prompts that fire automatically at Claude Code lifecycle events.

[![Claude Code](https://img.shields.io/badge/Claude_Code-Hooks-191919.svg?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)

---

## Contents

| File | Topic | Description |
|------|-------|-------------|
| [01_hooks_overview.md](01_hooks_overview.md) | Overview | What hooks are, all lifecycle events, configuration structure, common patterns |
| [02_hook_handlers.md](02_hook_handlers.md) | Handler Types | command, http, prompt, agent handlers — fields, exit codes, blocking behavior |

---

## Reading Order

1. **Hooks Overview** — understand the event model and how hooks are configured
2. **Hook Handlers** — deep dive into the four handler types and how to block/allow tool calls

---

## Prerequisites

- Understand settings.json scopes: [Settings](../settings/01_settings_json.md)
- [Back to root](../README.md)
