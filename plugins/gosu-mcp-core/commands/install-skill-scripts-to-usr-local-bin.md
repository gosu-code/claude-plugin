---
allowed-tools: Bash(find:*), Bash(ln:*), Bash(chmod:*), Bash(ls:*), Bash(test:*)
argument-hint: [--help]
description: Install skill scripts to /usr/local/bin using symlinks
model: claude-haiku-4-5
---
Install all Python and Bash scripts from skill directories to /usr/local/bin using symlinks for easy command-line access. Usage: `/install-skill-scripts-to-usr-local-bin`
User prompt: $ARGUMENTS
When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions and stop. Do not proceed further.

1.  **COMMAND Arguments Analysis**:
  - This command takes no arguments. The installation process is fully automated.

2.  **COMMAND Execution Process**:
  **Phase 1: Verify Plugin Directory**
  - Check if the Claude plugin `gosu-mcp-core` directory exists at `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core`
  - If directory does not exist, stop execution immediately
    - Display clear message: "Claude plugin directory not found. Please ensure the plugin 'gosu-mcp-core' is installed correctly."
    - Do not proceed to installation phase
  - If directory exists, proceed to script discovery phase

  **Phase 2: Discover Skill Scripts**
  - Find all executable scripts in skill directories using: `find ~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills -type f \( -name "*.py" -o -name "*.sh" \)`
  - Expected scripts to be found (examples):
    - `task-list-md/scripts/task_list_md.py`
    - `git-worktree/scripts/create_git_worktree.py`
    - `github-pr-utils/scripts/list_merged_pr.sh`
    - `github-pr-utils/scripts/reply_pr_review_comments_thread.sh`
    - `github-pr-utils/scripts/get_pr_bot_review_comments.sh`
  - If no scripts are found, display message: "No scripts found in skills directories" and stop execution
  - If scripts are found, display count and proceed to installation phase

  **Phase 3: Install Scripts to /usr/local/bin**
  - For each script found in Phase 2:
    - Extract the script filename
    - Get the absolute path of the source script
    - Create symlink in `/usr/local/bin/` pointing to the absolute path: `ln -sf <absolute-path> /usr/local/bin/<filename>`
      - If failed due to user permissions, try create symlink in `~/.local/bin/` and suggest adding this directory to PATH if user has not done so
    - Ensure the source script has execute permissions: `chmod +x <absolute-path>`
  - After all symlinks are created, verify installation by listing created symlinks: `ls -la /usr/local/bin/ | grep -E '(.py|.sh)$'`
  - Display success message showing:
    - Number of scripts installed
    - List of installed script names
    - Example: "Successfully installed 5 scripts to /usr/local/bin/: task_list_md.py, create_git_worktree.py, list_merged_pr.sh, reply_pr_review_comments_thread.sh, get_pr_bot_review_comments.sh"
  - If any symlink creation fails, display error message with the specific script that failed and suggest checking permissions: "Failed to create symlink for <script>. You may need sudo privileges or write access to /usr/local/bin/"

  **Phase 4: Verify Installation**
  - Test that at least one key script is accessible in PATH: `which task_list_md.py`
  - If command is found, display final success message: "All scripts are now available in your PATH. You can run them directly from any directory."
  - If command is not found, suggest adding `/usr/local/bin` to PATH or verify symlinks were created correctly

3.  **COMMAND Output Directory**:
  - This command creates symlinks in `/usr/local/bin/` directory
  - No additional output files are generated

4.  **Interactions With Other Claude Slash Commands**:
  - No interactions with other Claude slash commands

5.  **Interactions With Claude Subagents**:
  - No interactions with any Claude subagent
