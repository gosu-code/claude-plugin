---
name: codex-mcp
description: MUST use Codex MCP server tool `mcp__codex__codex` and `mcp__codex__codex-reply` when you are facing one of the following scnearios, 1. another MCP tool is requested that is not available, 2. you going to run a bash command that would emit large stdout output but only a subset of that output is needed
---
# codex-mcp

You MUST check whether `codex` CLI is available in the current bash environment with this bash command: `codex --version`. If not available, run the following bash command to install the `codex` CLI: `npm install -g @openai/codex`. Then inform user to perform authentication with an OpenAI account by running `codex login`. Ignore this instruction if the CLI is already available.

## Tools

### mcp__codex__codex

Run a Codex session. Accepts configuration parameters matching the Codex Config struct. Supported properties:

| Property                | Type   | Description                                                                                                                                            |
| ----------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`prompt`** (required) | string | Initial user prompt that seeds the Codex conversation.                                                                                                 |
| `approval-policy`       | string | Approval policy for generated shell commands: `untrusted`, `on-failure`, `on-request`, `never`.                                                        |
| `base-instructions`     | string | Overrides the default base instructions for the session.                                                                                               |
| `config`                | object | Path to individual config settings toml file that override `$CODEX_HOME/config.toml` (see codex-config-toml-structure.md to understand how to create this file).                 |
| `cwd`                   | string | Working directory for the session. Relative paths resolve from the server process root.                                                                |
| `model`                 | string | Optional override for the model name (e.g., `gpt-5`, `o4-mini`) default is `gpt-5-codex`.                                                                                       |
| `profile`               | string | Name of the profile providing default options (defined in `config.toml`).                                                                                           |
| `sandbox`               | string | Sandbox mode: `read-only`, `workspace-write`, or `danger-full-access`.                                                                                 |

### mcp__codex__codex-reply

Continue a Codex session by providing the conversation id and follow-up prompt. Supported properties:

| Property                        | Type   | Description                                              |
| ------------------------------- | ------ | -------------------------------------------------------- |
| **`prompt`** (required)         | string | Next user prompt to continue the Codex conversation.     |
| **`conversationId`** (required) | string | Identifier of the conversation to continue.              |

## Operational Requirements

- Always route qualifying requests through `mcp__codex__codex` with `sandbox` set to `danger-full-access` (MUST) and `approval-policy` set to `never`.
- When another MCP tool is requested, use `ListMcpResourcesTool` to confirm if it is available. Delegate to `codex` to invoke this MCP tool by crafting a `prompt` with all necessary information and file referrences. 
- When you need to run a command that would emit large stdout output but only a subset of that output is needed, MUST provide a precise `prompt` when delegating via `mcp__codex__codex` so the downstream agent knows which portion of the large output to collect or which external tool to execute.
- When `mcp__codex__codex` returns a result requiring your follow-up, continue the conversation with `mcp__codex__codex-reply`, reusing the `conversationId` present in the previous response.

## Known MCP Server Tools

- When `github` MCP server tool (`mcp__github`, `mcp__github__*`) is requested, see mcp-github-usage.md for detailed usage instructions. Use the information in this mcp-github-usage.md file to craft a precise `prompt` when delegating via `mcp__codex__codex` so the downstream agent can use the `github` MCP server tool exactly as intended.