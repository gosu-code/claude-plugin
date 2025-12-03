---
name: git-worktree
description: Utility tool to create new git worktrees with proper setup for development environments. Automates creation, copying, symlinking, and ownership management for smooth developer onboarding or isolated task/feature work.
---
# git-worktree

This skill provides tools for creating and managing Git worktrees, handling both the setup of a clean environment and synchronization of relevant files (including gitignored or untracked files). The main entrypoint is the Python script `scripts/create_git_worktree.py`.

## Key Features
- Create a new git worktree, or initialize a worktree at a target location
- Generate or customize branch names from task prompts
- Copy over selected git-ignored files and directories (e.g., node_modules, .env, .venv, vendor, etc.)
- Create symbolic links for local settings (e.g., .claude/settings.local.json)
- Optionally copy staged, modified, or untracked files into the new worktree
- Copy a plan/description file into the worktree for agent-based workflows
- Change the worktree directory owner (if needed, e.g., for VSCode agents)
- Run environment-specific checks to verify the new worktree's integrity (git, go, npm, etc.)

## Requirements
- Python 3.x
- `git` CLI
- sudo/root access for chown (if using --agent-user)

## Usage

```bash
python3 scripts/create_git_worktree.py [prompt words ...] [--branch BRANCH | --worktree WORKTREE_DIR] [--plan-file FILE] [--agent-user USER] [--no-copy-staged] [--copy-modified] [--copy-untracked] [--worktree-parent-dir DIR] [--verbose]
```

### Main Arguments
- `prompt` (positional, optional): Task description (used to generate branch name, and perform verification checks e.g., "fix login bug in auth module").
### Named Arguments (optional)
- `--branch`: Branch name for new worktree (overrides prompt-based naming)
- `--base-branch`: Base branch to create the new worktree from (local or remote). If not specified, worktree is created from current HEAD. Examples: `develop`, `origin/main`, `release-1.0`
- `--worktree`: Use an _existing_ worktree directory path instead of creating a new one
- `--plan-file`: Optional project/plan file to copy into the worktree
- `--agent-user`: The OS user to set as owner of new worktree dir (for agent that run with a separate OS user)
- `--no-copy-staged`: Prevents copying staged files into the new worktree (default = copy staged files)
- `--copy-modified`: Also copy modified-but-not-staged files
- `--copy-untracked`: Also copy untracked files
- `--worktree-parent-dir`: The parent dir in which to place the new worktree dir
- `--verbose`, `-v`: Enable debug/verbose logging

### Example Usages

```bash
# Create a new worktree with a branch name based on the prompt
python3 scripts/create_git_worktree.py feature add user auth --plan-file path/to/plan.md --agent-user vscode --copy-untracked

# Create with explicit branch and copy all types of files
python3 scripts/create_git_worktree.py --branch feat/apply-fixes --copy-modified --copy-untracked

# Create worktree from a different base branch
python3 scripts/create_git_worktree.py implement new API --branch feature/new-api --base-branch develop

# Create worktree from remote branch
python3 scripts/create_git_worktree.py hotfix critical bug --branch hotfix/security-patch --base-branch origin/release-1.0

# Use an existing worktree dir created earlier
python3 scripts/create_git_worktree.py "apply patch" --worktree /workspaces/worktree-agent-no1 --plan-file path/to/plan.md

```

### Troubleshooting

- If failed to create git worktree, try to invoke the script again with different arguments based on the error message you see.
- Do not attempt more than 3 times; if it still fails after 3 attempts, STOP and ask the user to create git worktree manually. (use `AskUserQuestion` tool)

## Worktree Verification

- Always verify the new worktree exist by run `git worktree list` to ensure the worktree is actually created (regardless of whether the script output say success or not)
- Run `git status` inside the new worktree to check for active branch is correctly set to [branch_name].

### Additional Verification
- Verify worktree is setup properly by run the following bash command in the worktree directory based on the tech-stack of the current project:
  - `go mod verify` if this is a Go project to ensure all dependencies are downloaded and valid.
  - `go work sync` if this Go project is setup as a Go workspace with `go.work` file.
  - `npm list` if this is a Node.js project to ensure all dependencies are installed.
  - `pnpm dedupe --check` if this this Node.js project is using `pnpm`
  - `python -m pip freeze -r requirements.txt` if this is a Python project contain a requirements file.
  - `uv tree` if this Python project  is using `uv`

## Notes
- The new worktree directory will be created in the parent directory specified by `--worktree-parent-dir` (default: cwd's parent directory) and have the name "worktree-agent-no1" (or "worktree-agent-no2" and so on to avoid directory name conflicts)
- The script will copied staged files and a known list of git ignored files and directories (e.g., node_modules, .env, .venv, vendor, etc.) to the worktree directory to help fast setup the worktree for development.
- Symlinks are created for certain dev-local secrets/settings to avoid copying them into the worktree directory.
- Changing ownership requires appropriate system permissions.
