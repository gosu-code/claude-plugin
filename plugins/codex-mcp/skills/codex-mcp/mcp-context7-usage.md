# Context7 MCP Server Usage

This file describes how to use the Context7 MCP Server tools (`mcp__context7`, `mcp__context7__*`, `context7` MCP) effectively when delegate related requests to this tools via the `codex-mcp` skill.

## Available Tools

Context7 MCP provides the following tools that LLMs can use:

- `resolve-library-id`: Resolves a general library name into a Context7-compatible library ID.
  - `libraryName` (required): The name of the library to search for

- `get-library-docs`: Fetches documentation for a library using a Context7-compatible library ID.
  - `context7CompatibleLibraryID` (required): Exact Context7-compatible library ID (e.g., `/mongodb/docs`, `/vercel/next.js`)
  - `topic` (optional): Focus the docs on a specific topic (e.g., "routing", "hooks")
  - `tokens` (optional, default 5000): Max number of tokens to return. Values less than 1000 are automatically increased to 1000.
