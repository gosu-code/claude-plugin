#!/usr/bin/env python3
# ------------------- LICENSE -------------------
# Copyright (C) 2025 gosu-code 0xgosu@gmail.com

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Source: http://opensource.org/licenses/AGPL-3.0
# ------------------- LICENSE -------------------
"""
Git Worktree Creation Script
This script creates git worktrees with proper setup for development environments.
It handles file copying, symlink creation, and ownership management.
Usage:
    python3 create_git_worktree.py clean up todos comment --branch branch_name --plan-file path/to/task-plan.md --agent-user vscode
    python3 create_git_worktree.py refactor API errors --worktree /workspaces/worktree-agent-no1 --plan-file path/to/task-plan.md --agent-user vscode
"""

import argparse
import os
import subprocess
import sys
import shutil
import logging
from pathlib import Path
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitWorktreeCreator:
    def __init__(self, args):
        self.args = args
        self.main_workspace = Path.cwd()
        # Support a customizable worktree parent directory
        self.worktree_parent_dir = Path(args.worktree_parent_dir or '.')
        self.worktree_dir: Path = self.worktree_parent_dir / 'worktree'
        self.branch_name = "agent/default-branch-name"
        self.base_branch = args.base_branch if hasattr(args, 'base_branch') else None
        
    def run_command(self, cmd, cwd=None, check=True):
        """Execute a shell command and return the result."""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, check=check)
            logger.debug(f"Command: {cmd}")
            logger.debug(f"Output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Stderr: {result.stderr}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd}")
            logger.error(f"Error: {e.stderr}")
            raise
    
    def generate_branch_name(self, prompt):
        """Generate a short branch name based on the prompt."""
        # Extract meaningful words and create a branch name
        words = re.findall(r'\b[a-zA-Z]+\b', prompt.lower())
        # Take first few meaningful words
        meaningful_words = [w for w in words if len(w) > 2][:3]
        if not meaningful_words:
            meaningful_words = ['task']
        branch_name = f"agent/{'-'.join(meaningful_words)}"
        return branch_name
    
    def make_branch_unique(self, branch_name):
        """Make branch name unique by adding suffix if needed."""
        # Check if branch exists
        result = self.run_command(f"git branch --list {branch_name}", check=False)
        if result.returncode == 0 and branch_name in result.stdout:
            # Branch exists, add suffix
            counter = 1
            while True:
                new_name = f"{branch_name}-{counter}"
                result = self.run_command(f"git branch --list {new_name}", check=False)
                if result.returncode == 0 and new_name not in result.stdout:
                    return new_name
                counter += 1
        return branch_name

    def resolve_base_branch(self, base_branch_arg):
        """Resolve base branch reference and ensure it's available locally.

        Args:
            base_branch_arg: Base branch name, can be 'branch', 'origin/branch', or remote ref

        Returns:
            str: Resolved branch reference suitable for git worktree add

        Raises:
            Exception: If branch doesn't exist locally or remotely, or fetch fails
        """
        # Normalize input: strip 'origin/' prefix if provided
        base_branch = base_branch_arg.replace('origin/', '') if base_branch_arg.startswith('origin/') else base_branch_arg

        logger.info(f"Resolving base branch: {base_branch_arg} -> {base_branch}")

        # Check if branch exists locally
        result = self.run_command(f"git branch --list {base_branch}", check=False)
        if result.returncode == 0 and base_branch in result.stdout:
            logger.info(f"Base branch '{base_branch}' found locally")
            return base_branch

        # Check if branch exists on remote
        result = self.run_command(f"git branch -r --list origin/{base_branch}", check=False)
        if result.returncode == 0 and f"origin/{base_branch}" in result.stdout:
            logger.info(f"Base branch 'origin/{base_branch}' found on remote, fetching...")

            # Fetch the branch from remote
            try:
                self.run_command(f"git fetch origin {base_branch}")
                logger.info(f"Successfully fetched branch '{base_branch}' from remote")
                return f"origin/{base_branch}"
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to fetch branch '{base_branch}' from remote: {e.stderr}")

        # Check if remote exists
        result = self.run_command("git remote", check=False)
        if result.returncode != 0 or 'origin' not in result.stdout:
            raise Exception(f"Base branch '{base_branch}' not found locally and no remote 'origin' configured")

        # Branch not found
        raise Exception(f"Base branch '{base_branch}' not found locally or on remote 'origin'")

    def find_unique_worktree_path(self, base_path):
        """Find a unique worktree path by incrementing the number."""
        # Parse the base path to extract the pattern
        path_obj = Path(base_path)
        base_name = path_obj.stem
        parent_dir = path_obj.parent
        
        # Extract number from base name (e.g., "worktree-agent-no1" -> 1)
        match = re.search(r'-no(\d+)$', base_name)
        if match:
            base_prefix = base_name[:match.start()]
            current_num = int(match.group(1))
        else:
            base_prefix = base_name
            current_num = 1
        
        # Check existing worktrees
        result = self.run_command("git worktree list", check=False)
        existing_paths = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Extract path from worktree list output
                    path_part = line.split()[0]
                    existing_paths.append(path_part)
        
        # Find unique path
        while True:
            new_name = f"{base_prefix}-no{current_num}"
            new_path = parent_dir / new_name
            if str(new_path) not in existing_paths and not new_path.exists():
                return str(new_path)
            current_num += 1
    
    def create_worktree(self):
        """Create a new git worktree."""
        if self.args.worktree:
            # Use existing worktree directory
            self.worktree_dir = Path(self.args.worktree)
            logger.info(f"Using existing worktree directory: {self.worktree_dir}")
        else:
            # Create new worktree
            if self.args.branch:
                self.branch_name = self.args.branch
            else:
                # Generate branch name from prompt arguments
                prompt = ' '.join(self.args.prompt) if self.args.prompt else 'default task'
                self.branch_name = self.generate_branch_name(prompt)

            # Make branch name unique
            self.branch_name = self.make_branch_unique(self.branch_name)
            logger.info(f"Using branch name: {self.branch_name}")

            # Find unique worktree path (now using self.worktree_parent_dir)
            base_worktree_path = str(self.worktree_parent_dir / "worktree-agent-no1")
            worktree_dir = self.find_unique_worktree_path(base_worktree_path)
            if not worktree_dir:
                raise Exception("Failed to find a unique worktree path.")
            self.worktree_dir = Path(worktree_dir)
            logger.info(f"Creating worktree at: {self.worktree_dir}")

            # Resolve base branch if provided
            base_ref = None
            if self.base_branch:
                base_ref = self.resolve_base_branch(self.base_branch)
                logger.info(f"Using base branch: {base_ref}")

            # Create the worktree
            if base_ref:
                cmd = f"git worktree add -b {self.branch_name} {self.worktree_dir} {base_ref}"
            else:
                cmd = f"git worktree add -b {self.branch_name} {self.worktree_dir}"
            self.run_command(cmd)

            # Verify creation
            result = self.run_command("git worktree list")
            if str(self.worktree_dir) not in result.stdout:
                raise Exception(f"Failed to create worktree at {self.worktree_dir}")

            logger.info(f"Successfully created worktree with branch {self.branch_name}")
    
    def copy_git_ignored_files(self):
        """Recursively copy selected git-ignored files/dirs from main workspace to worktree.

        - Walks the entire `self.main_workspace` tree.
        - If a directory matches, copies it and prunes that subtree from traversal.
        - If a file matches, copies it preserving relative structure.
        """
        names_to_copy = {
            'node_modules',
            '.pnpm-store',
            '.env',
            'go.work',
            'go.work.sum',
            'vendor',
            '.venv',
            '.ruff_cache',
            '.mypy_cache',
        }

        root = self.main_workspace

        # Detect if the worktree dir is inside the main workspace to avoid copying into itself
        worktree_inside_main = False
        try:
            self.worktree_dir.relative_to(root)
            worktree_inside_main = True
        except Exception:
            worktree_inside_main = False

        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            current = Path(dirpath)

            # If worktree is inside main workspace, don't traverse into it
            if worktree_inside_main:
                try:
                    current.relative_to(self.worktree_dir)
                    # We're inside the worktree subtree; stop traversing further
                    dirnames[:] = []
                    continue
                except Exception:
                    pass

            # Also don't traverse into .git
            if '.git' in dirnames:
                dirnames.remove('.git')

            # Handle matching directories first and prune them from traversal
            to_prune = []
            for d in list(dirnames):
                if d in names_to_copy:
                    src_dir = current / d
                    # Destination path preserves relative structure
                    rel_path = src_dir.relative_to(root)
                    dst_dir = self.worktree_dir / rel_path
                    try:
                        if dst_dir.exists():
                            shutil.rmtree(dst_dir)
                        dst_dir.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(src_dir, dst_dir)
                        logger.info(f"Copied directory: {rel_path}")
                    except Exception as e:
                        logger.warning(f"Failed to copy directory {rel_path}: {e}")
                    # Prune this directory from traversal
                    to_prune.append(d)

            # Apply pruning so we don't descend into copied directories
            for d in to_prune:
                if d in dirnames:
                    dirnames.remove(d)

            # Handle matching files in the current directory
            for f in filenames:
                if f in names_to_copy:
                    src_file = current / f
                    rel_path = src_file.relative_to(root)
                    dst_file = self.worktree_dir / rel_path
                    try:
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        logger.info(f"Copied file: {rel_path}")
                    except Exception as e:
                        logger.warning(f"Failed to copy file {rel_path}: {e}")
    
    def create_symlinks(self):
        """Create symlinks for gitignore files require for development"""
        # TODO: enhance symlink creation to gracefully handle errors, allow continue with other symlinks in case of failure
        
        # Create symlink for files in .claude
        # settings.local.json -> require for claude code to use existing local settings
        claude_src = self.main_workspace / '.claude'
        claude_dst = self.worktree_dir / '.claude'
        if claude_src.exists():
            claude_dst.mkdir(exist_ok=True)
            settings_src = claude_src / 'settings.local.json'
            settings_dst = claude_dst / 'settings.local.json'
            if settings_src.exists():
                if settings_dst.exists() or settings_dst.is_symlink():
                    settings_dst.unlink()
                settings_dst.symlink_to(settings_src)
                logger.info(f"Created symlink: {settings_dst} -> {settings_src}")
    
    def copy_plan_file(self):
        """Copy plan file to worktree if specified."""
        if self.args.plan_file:
            plan_src = Path(self.args.plan_file)
            if plan_src.exists():
                plan_dst = self.worktree_dir / 'worktree-agent-task-plan.md'
                shutil.copy2(plan_src, plan_dst)
                logger.info(f"Copied plan file: {plan_dst.name}")
            else:
                logger.warning(f"Plan file not found: {self.args.plan_file}")
    
    def set_ownership(self):
        """Set ownership of worktree directory."""
        if self.args.agent_user:
            try:
                cmd = f"chown -R {self.args.agent_user}: {self.worktree_dir}"
                self.run_command(cmd)
                logger.info(f"Changed ownership to {self.args.agent_user}")
            except Exception as e:
                logger.warning(f"Failed to change ownership: {e}")
    
    def verify_worktree(self):
        """Verify that the worktree is functional."""
        logger.info("Verifying worktree functionality...")
        
        try:
            # Test git command
            result = self.run_command("git status", cwd=self.worktree_dir)
            logger.info("Git status check: PASSED")
            
            # Test go command if go.work exists
            if (self.worktree_dir / 'go.work').exists():
                result = self.run_command("go work sync", cwd=self.worktree_dir, check=False)
                if result.returncode == 0:
                    logger.info("Go work sync check: PASSED")
                else:
                    logger.warning("Go work sync check: FAILED")
            
            # Test npm command if package.json exists
            if (self.worktree_dir / 'package.json').exists():
                result = self.run_command("npm --version", cwd=self.worktree_dir, check=False)
                if result.returncode == 0:
                    logger.info("NPM version check: PASSED")
                else:
                    logger.warning("NPM version check: FAILED")
                    
        except Exception as e:
            logger.error(f"Worktree verification failed: {e}")
            raise
    
    def copy_staged_files(self):
        """copy staged files in the worktree with those from the main workspace."""
        try:
            result = self.run_command("git diff --cached --name-only", check=False)
            if result.returncode != 0:
                logger.warning("Failed to get staged files list.")
                return
            files = [f for f in result.stdout.strip().split('\n') if f]
            for rel_path in files:
                src = self.main_workspace / rel_path
                dst = self.worktree_dir / rel_path
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    logger.info(f"Overrode staged file: {rel_path}")
        except Exception as e:
            logger.warning(f"Error overriding staged files: {e}")

    def copy_non_staged_modified_files(self):
        """copy modified files in the worktree with those from the main workspace."""
        try:
            result = self.run_command("git diff --name-only", check=False)
            if result.returncode != 0:
                logger.warning("Failed to get modified files list.")
                return
            files = [f for f in result.stdout.strip().split('\n') if f]
            for rel_path in files:
                src = self.main_workspace / rel_path
                dst = self.worktree_dir / rel_path
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    logger.info(f"Overrode modified file: {rel_path}")
        except Exception as e:
            logger.warning(f"Error overriding modified files: {e}")

    def copy_untracked_files(self):
        """Copy untracked files from the main workspace to the worktree."""
        try:
            result = self.run_command("git ls-files --others --exclude-standard", check=False)
            if result.returncode != 0:
                logger.warning("Failed to get untracked files list.")
                return
            files = [f for f in result.stdout.strip().split('\n') if f]
            for rel_path in files:
                src = self.main_workspace / rel_path
                dst = self.worktree_dir / rel_path
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if src.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                        logger.info(f"Copied untracked directory: {rel_path}")
                    else:
                        shutil.copy2(src, dst)
                        logger.info(f"Copied untracked file: {rel_path}")
        except Exception as e:
            logger.warning(f"Error copying untracked files: {e}")

    def run(self):
        """Run the complete worktree creation process."""
        try:
            logger.info("Starting git worktree creation process...")
            # Step 1: Create worktree
            self.create_worktree()
            # Step 2: Copy git-ignored files
            self.copy_git_ignored_files()
            # Step 3: copy modified file
            # Controlled by --no-copy-staged, --copy-modified
            if self.args.copy_staged:
                self.copy_staged_files()
            if self.args.copy_modified:
                self.copy_non_staged_modified_files()
            # Step 4: Copy untracked file & plan file
            # Controlled by --copy-untracked
            if self.args.copy_untracked:
                self.copy_untracked_files()
            # Ensure plan file is available in the worktree if provided
            self.copy_plan_file()
            # Step 5: Create symlinks for gitignore files require for dev
            try:
                self.create_symlinks()
            except Exception as e:
                logger.warning(f"Failed to create symlinks: {e}")
            # Step 6: Set ownership
            self.set_ownership()
            # Step 7: Verify worktree
            self.verify_worktree()
            logger.info(f"Successfully created and configured worktree at: {self.worktree_dir}")
        except Exception as e:
            logger.error(f"Failed to create worktree: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Create and configure git worktrees')
    parser.add_argument('prompt', nargs='*', help='Task description prompt (used to generate branch name if --branch not specified)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--branch', help='Branch name for new worktree')
    group.add_argument('--worktree', help='Existing worktree directory path')
    parser.add_argument('--base-branch',
                        help='Base branch to create worktree from (local or remote, e.g., develop, origin/develop)')
    parser.add_argument('--plan-file', help='Path to task plan file')
    parser.add_argument('--agent-user', help='User to set as owner of worktree directory')
    parser.add_argument('--no-copy-staged', dest='copy_staged', action='store_false', help='Do not copy staged files in worktree')
    parser.set_defaults(copy_staged=True)
    parser.add_argument('--copy-modified', dest='copy_modified', action='store_true', help='copy non-staged modified files in worktree')
    parser.set_defaults(copy_modified=False)
    parser.add_argument('--copy-untracked', dest='copy_untracked', action='store_true', help='copy untracked files in worktree')
    parser.set_defaults(copy_untracked=False)
    # Add new argument for worktree parent directory
    parser.add_argument('--worktree-parent-dir',
        default=str(Path.cwd().parent),
        help='Parent directory in which to place the worktree (default: parent of current directory)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    creator = GitWorktreeCreator(args)
    creator.run()

if __name__ == '__main__':
    main()