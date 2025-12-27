---
allowed-tools: Bash(find:*), Bash(cp:*), Bash(mkdir:*), Bash(ls:*), Bash(test:*), Bash(rm:*)
argument-hint: [skill-name] [--help]
description: Install gosu-mcp-core skills to Codex CLI (~/.codex/skills)
model: claude-haiku-4-5
---
Install gosu-mcp-core skills to Codex CLI user directory (~/.codex/skills). Skills are reusable bundles with SKILL.md instructions and optional scripts/resources. Usage: `/install-gosu-skills-to-codex [skill-name]` or `/install-gosu-skills-to-codex` to install all.

User prompt: $ARGUMENTS

When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions and stop. Do not proceed further.

1. **COMMAND Arguments Analysis**:

- This command accepts an optional skill name argument to install a specific skill
- If no argument is provided, all available skills will be installed
- Valid skill names: `task-list-md`, `git-worktree`, `github-pr-utils`
- Extract the skill name from $ARGUMENTS if provided (first non-flag argument)
- If an invalid skill name is provided, display error: "Unknown skill: <name>. Available skills: task-list-md, git-worktree, github-pr-utils"

2. **COMMAND Execution Process**:
  **Phase 1: Verify Plugin Directory**

- Check if the Claude plugin `gosu-mcp-core` directory exists at `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core`
- If directory does not exist, stop execution immediately
  - Display clear message: "Claude plugin directory not found. Please ensure the plugin 'gosu-mcp-core' is installed correctly."
  - Do not proceed to installation phase
- If directory exists, proceed to next phase

  **Phase 2: Prepare Target Directory**

- Ensure the Codex skills directory exists: `mkdir -p ~/.codex/skills`
- Verify the directory was created successfully
- If creation fails, display error: "Failed to create ~/.codex/skills directory. Please check permissions."

  **Phase 3: Discover Available Skills**

- List all skill directories: `find ~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills -maxdepth 1 -type d | tail -n +2`
- Expected skills to be found:
  - `task-list-md` - Task list management in markdown files
  - `git-worktree` - Git worktree management utility
  - `github-pr-utils` - GitHub pull request utilities
- If no skills are found, display message: "No skills found in plugin directory" and stop execution
- If a specific skill name was provided in arguments:
  - Filter to only that skill directory
  - If skill not found, display error: "Skill '<name>' not found" and stop
- Display the skills that will be installed

  **Phase 4: Install Skills**

- For each skill directory found in Phase 3:
  - Extract the skill name (basename of the directory path)
  - Check if skill already exists at `~/.codex/skills/<skill-name>`
    - If exists, display warning: "Skill '<skill-name>' already exists. Removing old version..."
    - Remove the existing directory: `rm -rf ~/.codex/skills/<skill-name>`
  - Copy the entire skill directory to `~/.codex/skills/<skill-name>`: `cp -r <source-path> ~/.codex/skills/<skill-name>`
  - Verify the SKILL.md file exists: `test -f ~/.codex/skills/<skill-name>/SKILL.md`
  - If SKILL.md is missing, display error: "Installation failed for '<skill-name>': SKILL.md not found"
  - If scripts directory exists, ensure scripts are executable:
    - `find ~/.codex/skills/<skill-name>/scripts -type f \( -name "*.py" -o -name "*.sh" \) -exec chmod +x {} \;`
  - Display success for each skill: "✓ Installed skill: <skill-name>"

  **Phase 5: Verify Installation**

- List installed skills: `ls -d ~/.codex/skills/*/`
- Count the number of successfully installed gosu-mcp-core skills
- Display final summary:
  - If installing all: "Successfully installed X gosu-mcp-core skills to ~/.codex/skills/"
  - If installing specific skill: "Successfully installed skill '<skill-name>' to ~/.codex/skills/"
  - List of installed skill names
  - Usage hint: "You can invoke skills with $skill-name (e.g., $task-list-md) in Codex CLI"
- If any installation fails, display error message with the specific skill that failed

  **Phase 6: Post-Installation Information**

- Display information about available skills:
  - "Available skills:"
  - For each installed skill, show name and description from SKILL.md metadata
- Suggest next steps:
  - "Run 'codex' or use your IDE extension to start using these skills"
  - "Type $skill-name to invoke a skill explicitly, or let Codex select automatically"

3. **COMMAND Output Directory**:

- This command installs skills to `~/.codex/skills/` directory
- Each skill is a subdirectory containing:
  - Required: `SKILL.md` (instructions and metadata)
  - Optional: `scripts/` (executable code)
  - Optional: `references/` (documentation)
  - Optional: `assets/` (templates, resources)
- No additional output files are generated

4. **Interactions With Other Claude Slash Commands**:

- This command is complementary to `/install-skill-scripts-to-usr-local-bin`
- Skills installed by this command make their capabilities available to Codex CLI
- Scripts within skills can be separately installed to PATH using the other command

5. **Interactions With Claude Subagents**:

- No interactions with any Claude subagent

6. **Error Handling**:

- If plugin directory doesn't exist: suggest running `/install-gosu-model-context-protocol` first
- If skill name is invalid: list available skills
- If target directory creation fails: check permissions and suggest manual creation
- If copy operation fails: display specific error and suggest checking disk space/permissions
- If SKILL.md is missing from a skill: warn user and skip that skill
