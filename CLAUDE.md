# Agent Instructions

This document provides comprehensive guidelines for developing and maintaining Claude plugins in this repository.

## Table of Contents
- [Plugin Structure](#plugin-structure)
- [Version Management](#version-management)
- [Marketplace Registration](#marketplace-registration)
- [Documentation Requirements](#documentation-requirements)
- [Skill Development](#skill-development)
- [MCP Server Integration](#mcp-server-integration)
- [Git Workflow](#git-workflow)
- [Code Quality Standards](#code-quality-standards)
- [Testing Guidelines](#testing-guidelines)
- [Best Practices](#best-practices)

## Plugin Structure

Every plugin MUST follow this directory structure:

```
plugins/<plugin-name>/
├── .claude-plugin/
│   └── plugin.json           # Plugin metadata and configuration
├── skills/                   # Optional: Plugin skills
│   └── <skill-name>/
│       ├── SKILL.md          # Skill instructions and documentation
│       └── *.md              # Additional skill reference docs
├── README.md                 # Plugin documentation
└── LICENSE                   # Optional: Plugin license
```

### Required Files

1. **`.claude-plugin/plugin.json`**: Plugin metadata
   - Must include: name, description, version, author, license
   - May include: keywords, mcpServers, dependencies

2. **`README.md`**: Comprehensive plugin documentation
   - Overview and features
   - Installation instructions
   - Usage examples
   - Configuration options
   - Troubleshooting guide
   - License information

### Optional Files

1. **Skills**: Located in `skills/<skill-name>/SKILL.md`
2. **Additional Documentation**: Reference docs for skills
3. **LICENSE**: Plugin-specific license file

## Version Management

### Version Bumping Rules

- **ALWAYS** bump the version when making changes to plugin files (except README.md)
- **ALWAYS** bump the patch version (third digit) regardless of the type of change
- **ONLY** update the `.claude-plugin/plugin.json` file of the plugin you are modifying
- **NEVER** modify README.md-only changes require a version bump

### Version Format

Use semantic versioning: `MAJOR.MINOR.PATCH`

Examples:
- `1.0.5` → `1.0.6` (patch bump for any code change)
- Documentation-only changes do NOT require version bumps

### What Requires Version Bumps

- ✅ Changes to SKILL.md files
- ✅ Changes to plugin.json (except version field itself)
- ✅ Changes to skill reference documentation (*.md in skills/)
- ✅ Changes to MCP server configurations
- ✅ Code or logic changes
- ❌ Changes to README.md only
- ❌ Changes to LICENSE files
- ❌ Changes to comments or formatting

## Marketplace Registration

### Adding a New Plugin

Every plugin MUST be registered in `.claude-plugin/marketplace.json` before it can be used.

**Steps:**
1. Add plugin entry to the `plugins` array in `.claude-plugin/marketplace.json`
2. Specify the plugin name and source path
3. Create the plugin directory structure
4. Add plugin.json with metadata
5. Create README.md documentation

**Example marketplace.json entry:**
```json
{
  "name": "my-plugin",
  "source": "./plugins/my-plugin"
}
```

### Marketplace Metadata

The marketplace.json should include:
- `name`: Marketplace identifier (e.g., "gosu-code")
- `owner`: Marketplace owner details (name, email)
- `plugins`: Array of plugin entries

## Documentation Requirements

### Plugin README.md

Every plugin README.md MUST include:

1. **Overview**: Brief description of what the plugin does
2. **Features**: List of key capabilities
3. **Installation**: Step-by-step installation instructions
4. **Prerequisites**: Required dependencies or tools
5. **Usage Examples**: Clear examples showing how to use the plugin
6. **Configuration**: Available configuration options
7. **Troubleshooting**: Common issues and solutions
8. **License**: License information

### Skill Documentation (SKILL.md)

Every skill MUST have a SKILL.md file with:

1. **Frontmatter**: YAML metadata with name and description
   ```yaml
   ---
   name: skill-name
   description: Brief description of when to use this skill
   ---
   ```

2. **Prerequisites Check**: Instructions for checking tool availability
   ```markdown
   You MUST check whether `tool` CLI is available with: `tool --version`
   ```

3. **Tool Documentation**: List all available tools and their parameters
4. **Operational Requirements**: How the skill should be used
5. **Examples**: Usage examples and patterns
6. **Known Integrations**: Related tools or MCP servers

### Reference Documentation

Skill reference docs (e.g., `mcp-github-usage.md`) should include:
- Detailed usage instructions
- API documentation
- Code examples
- Common patterns
- Troubleshooting tips

## Skill Development

### Creating a New Skill

1. Create skill directory: `plugins/<plugin-name>/skills/<skill-name>/`
2. Create `SKILL.md` with proper frontmatter
3. Document all tools and capabilities
4. Add usage examples
5. Include prerequisite checks
6. Test the skill thoroughly

### Skill Best Practices

- **Be Specific**: Clearly define when the skill should be used
- **Check Prerequisites**: Always verify required tools are available
- **Document Parameters**: List all parameters with types and descriptions
- **Provide Examples**: Include clear, practical examples
- **Reference External Docs**: Link to related documentation files
- **Handle Errors**: Document common errors and solutions

### Skill Naming Conventions

- Use lowercase with hyphens: `my-skill-name`
- Be descriptive: Name should indicate purpose
- Avoid redundancy: Don't repeat plugin name

## MCP Server Integration

### Adding MCP Server Support

To integrate an MCP server in a plugin:

1. Add `mcpServers` configuration to `plugin.json`:
   ```json
   {
     "mcpServers": {
       "server-name": {
         "type": "stdio",
         "command": "command-name",
         "args": ["arg1", "arg2"]
       }
     }
   }
   ```

2. Document the MCP server in README.md
3. Create skills that use the MCP server tools
4. Document MCP tool usage patterns

### MCP Server Configuration

- **type**: Usually "stdio" for standard I/O communication
- **command**: The CLI command to start the server
- **args**: Array of command-line arguments

### MCP Tool Documentation

When documenting MCP tools in skills:
- Use format: `mcp__<server>__<tool>`
- Document all parameters with types
- Show example usage
- Explain return values

## Git Workflow

### Branch Naming

- Feature branches: `claude/<feature-name>-<session-id>`
- Always include the session ID at the end
- Use descriptive feature names with hyphens

### Commit Messages

Follow conventional commit format:

```
<type>: <short summary>

<detailed description>

<additional context>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Example:**
```
Update codex-mcp skill to use 'codex mcp list' instead of 'codex --version'

This change improves the availability check by verifying both the codex CLI
and MCP server availability simultaneously, providing a more comprehensive
validation of the plugin's prerequisites.

Changes:
- Updated SKILL.md to use 'codex mcp list' for checking CLI and MCP server
- Updated README.md troubleshooting sections to use 'codex mcp list'
- Bumped plugin version from 1.0.5 to 1.0.6
```

### Push Guidelines

- Always push to the designated feature branch
- Use: `git push -u origin <branch-name>`
- Include session ID in branch name
- Retry on network failures (up to 4 times with exponential backoff)

## Code Quality Standards

### File Formatting

- Use consistent indentation (tabs or spaces)
- Keep lines under 100 characters when possible
- Use clear, descriptive variable names
- Add comments for complex logic

### Markdown Formatting

- Use ATX-style headers (`#` syntax)
- Include table of contents for long documents
- Use code blocks with language specifiers
- Keep paragraphs concise and focused

### JSON Formatting

- Use 2-space indentation (or tabs if project uses tabs)
- No trailing commas
- Use double quotes for strings
- Validate JSON before committing

## Testing Guidelines

### Manual Testing Checklist

Before committing changes:

1. ✅ Verify all affected commands work
2. ✅ Test error handling and edge cases
3. ✅ Check documentation accuracy
4. ✅ Validate JSON files
5. ✅ Test MCP server connections (if applicable)
6. ✅ Verify skill activation and usage
7. ✅ Check for broken links in documentation

### Integration Testing

- Test plugin installation process
- Verify MCP server connectivity
- Test skill activation and execution
- Check prerequisite detection
- Validate error messages

## Best Practices

### General Development

1. **Start Small**: Make focused, incremental changes
2. **Test Thoroughly**: Verify changes work as expected
3. **Document Everything**: Keep documentation up-to-date
4. **Follow Conventions**: Maintain consistency with existing code
5. **Review Changes**: Double-check before committing

### Plugin Development

1. **Single Responsibility**: Each plugin should have a clear, focused purpose
2. **Minimal Dependencies**: Avoid unnecessary external dependencies
3. **Clear Prerequisites**: Document all requirements clearly
4. **Graceful Failures**: Handle errors elegantly with helpful messages
5. **User-Friendly**: Provide clear instructions and examples

### Skill Development

1. **Precise Activation**: Define clear conditions for when to use the skill
2. **Comprehensive Docs**: Document all parameters and return values
3. **Example-Driven**: Include practical, real-world examples
4. **Error Guidance**: Help users troubleshoot common issues
5. **Reference Links**: Link to related documentation and resources

### Documentation

1. **Clarity**: Write clear, concise explanations
2. **Examples**: Show don't just tell
3. **Completeness**: Cover all features and options
4. **Maintainability**: Keep docs in sync with code
5. **Accessibility**: Use simple language and good formatting

### MCP Integration

1. **Validate Availability**: Always check if MCP server is connected
2. **Clear Tool Docs**: Document all MCP tools thoroughly
3. **Usage Patterns**: Provide common usage patterns
4. **Error Handling**: Document failure scenarios
5. **Dependencies**: Clearly list MCP server requirements

## Quick Reference

### Common Tasks

**Adding a new plugin:**
1. Add entry to `.claude-plugin/marketplace.json`
2. Create plugin directory structure
3. Create `plugin.json` with metadata
4. Write comprehensive `README.md`
5. Add skills if needed
6. Test installation and usage

**Updating a plugin:**
1. Make your changes
2. Bump version in `plugin.json` (if not README-only)
3. Update documentation
4. Test changes
5. Commit with descriptive message
6. Push to feature branch

**Creating a skill:**
1. Create `skills/<skill-name>/` directory
2. Write `SKILL.md` with frontmatter
3. Document tools and usage
4. Add examples
5. Test skill activation
6. Bump plugin version

**Adding MCP server:**
1. Add configuration to `plugin.json`
2. Document in README.md
3. Create skills using MCP tools
4. Test connection and tools
5. Bump plugin version

---

## Summary

Key points to remember:

- ✅ Register plugins in marketplace.json first
- ✅ Always bump versions for non-README changes
- ✅ Follow the standard directory structure
- ✅ Write comprehensive documentation
- ✅ Test thoroughly before committing
- ✅ Use descriptive commit messages
- ✅ Check prerequisites in skills
- ✅ Document MCP servers and tools clearly

Following these guidelines ensures consistent, high-quality plugin development and maintenance.