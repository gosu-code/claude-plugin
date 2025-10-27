# gosu-claude
Gosu Claude Code Plugins &amp; Marketplace


## Quick start

Run these following slash command in Claude Code to add `gosu-code` marketplace and install Gosu plugins
```
/plugin marketplace add gosu-code/claude-plugin
```
Install `gosu-mcp-core` plugin
```
/plugin install gosu-mcp-core@gosu-code
```

Restart Claude Code, then run the slash command below to install the `gosu` MCP server (require `gh` CLI to be installed)
```
/gosu-mcp-core:install-gosu-model-context-protocol
```

## Plugins

- [gosu-mcp-core@gosu-code](plugins/gosu-mcp-core/README.md): Core MCP tools and skills for Gosu MCP server
- [codex-mcp@gosu-code](plugins/codex-mcp/README.md): Codex as a companion AI Agent for Claude Code via MCP
- [voice-coding@gosu-code](plugins/voice-coding/README.md): Use voice commands to do coding in Claude Code