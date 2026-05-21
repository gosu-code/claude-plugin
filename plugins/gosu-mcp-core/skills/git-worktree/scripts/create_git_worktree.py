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
import json
import os
import pwd
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
        self.main_workspace = Path(args.cwd_override) if getattr(args, 'cwd_override', None) else Path.cwd()
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
        result = self.run_command(f"git branch --list {base_branch}", cwd=self.main_workspace, check=False)
        if result.returncode == 0 and base_branch in result.stdout:
            logger.info(f"Base branch '{base_branch}' found locally")
            return base_branch

        # Check if branch exists on remote
        result = self.run_command(f"git branch -r --list origin/{base_branch}", cwd=self.main_workspace, check=False)
        if result.returncode == 0 and f"origin/{base_branch}" in result.stdout:
            logger.info(f"Base branch 'origin/{base_branch}' found on remote, fetching...")

            # Fetch the branch from remote
            try:
                self.run_command(f"git fetch origin {base_branch}", cwd=self.main_workspace)
                logger.info(f"Successfully fetched branch '{base_branch}' from remote")
                return f"origin/{base_branch}"
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to fetch branch '{base_branch}' from remote: {e.stderr}")

        # Check if remote exists
        result = self.run_command("git remote", cwd=self.main_workspace, check=False)
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
            self.run_command(cmd, cwd=self.main_workspace)

            # Verify creation
            result = self.run_command("git worktree list", cwd=self.main_workspace)
            if str(self.worktree_dir) not in result.stdout:
                raise Exception(f"Failed to create worktree at {self.worktree_dir}")

            logger.info(f"Successfully created worktree with branch {self.branch_name}")
    
    def _link_or_copy_file(self, src, dst):
        """Hard-link a file from src to dst; fall back to copy2 on failure.

        Hard links avoid duplicating file content (same inode), making bulk
        materialization of large trees like node_modules essentially free.
        Falls back to a real copy if src/dst are on different filesystems
        or the OS rejects the link (e.g., cross-device, permission).
        """
        try:
            os.link(src, dst)
            return 'linked'
        except OSError:
            shutil.copy2(src, dst)
            return 'copied'

    @staticmethod
    def _clear_dst(dst):
        """Remove ``dst`` whether it's a symlink (broken or not), file, or dir.

        Idempotency helper used before materializing into ``dst``. ``Path.exists()``
        returns False for broken symlinks, so we always test ``is_symlink()`` too.
        """
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        elif dst.exists():
            shutil.rmtree(dst)

    def _link_tree(self, src_dir, dst_dir):
        """Recreate src_dir at dst_dir, hard-linking files instead of copying.

        Tries ``cp -al`` (C-implemented, batched syscalls) first since
        Python's ``shutil.copytree`` is significantly slower for trees with
        hundreds of thousands of files like ``node_modules``. Falls back to
        ``shutil.copytree(copy_function=os.link)``, then to a plain
        recursive copy if hard-linking is rejected (e.g., cross-device).
        """
        # Fast path: cp -al on POSIX. Both GNU (Linux) and BSD (macOS) cp
        # accept -a (archive) and -l (hard link). dst_dir must not exist.
        self._clear_dst(dst_dir)
        if os.name == 'posix' and shutil.which('cp'):
            result = subprocess.run(
                ['cp', '-al', str(src_dir), str(dst_dir)],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                return 'linked'
            logger.debug(f"cp -al failed for {src_dir} -> {dst_dir}: {result.stderr.strip()}; falling back")
            self._clear_dst(dst_dir)

        try:
            shutil.copytree(src_dir, dst_dir, copy_function=os.link, symlinks=True)
            return 'linked'
        except (OSError, shutil.Error):
            self._clear_dst(dst_dir)
            shutil.copytree(src_dir, dst_dir, symlinks=True)
            return 'copied'

    def _symlink_dir(self, src_dir, dst_dir):
        """Replace ``dst_dir`` with a symlink pointing at ``src_dir``.

        Used for shared content-addressed caches where sharing is the point.
        Symlinking is O(1) versus O(files) for the hard-link path.
        """
        self._clear_dst(dst_dir)
        dst_dir.parent.mkdir(parents=True, exist_ok=True)
        dst_dir.symlink_to(src_dir, target_is_directory=True)

    # Shared content-addressed caches — symlinked into the worktree so state
    # is naturally shared with the main workspace. pnpm stores content by
    # hash, ruff/mypy invalidate by hash, so sharing is safe and O(1).
    # NOTE: ``.venv`` is intentionally NOT here — ``pip install`` mutates
    # files in place, which would leak across worktrees through a symlink.
    _CACHE_DIR_NAMES = frozenset({'.pnpm-store', '.ruff_cache', '.mypy_cache'})
    # Dependency trees — hard-link copied so each worktree has an independent
    # directory entry that build tools can mutate without corrupting the main
    # workspace, while file contents are still shared via inodes.
    _HARDLINK_DIR_NAMES = frozenset({'node_modules', 'vendor', '.venv'})
    # Single files — always hard-linked.
    _IGNORED_FILE_NAMES = frozenset({'.env', 'go.work', 'go.work.sum'})

    def _enumerate_ignored_targets(self, all_names):
        """Find candidate ignored files/dirs at workspace root and one level deep.

        Returns a list of absolute source paths whose basename is in ``all_names``.
        Limiting traversal to depth 2 (root + immediate children) avoids the cost
        of a full workspace walk — these names virtually never appear deeper than
        ``packages/<pkg>/node_modules`` in real-world repos. Monorepos with deeper
        nesting can extend this if needed.
        """
        root = self.main_workspace
        targets = []
        seen = set()

        def scan_into(dir_path):
            try:
                with os.scandir(dir_path) as it:
                    for entry in it:
                        if entry.name in all_names:
                            p = Path(entry.path)
                            if p not in seen:
                                seen.add(p)
                                targets.append(p)
            except OSError as e:
                logger.debug(f"scandir({dir_path}) failed: {e}")

        # Depth 0: workspace root itself
        scan_into(root)

        # Depth 1: each immediate subdirectory of root
        try:
            with os.scandir(root) as it:
                children = list(it)
        except OSError as e:
            logger.debug(f"scandir({root}) failed: {e}")
            children = []

        for entry in children:
            if entry.name == '.git':
                continue
            if entry.name in all_names:
                # Already handled at depth 0 (or pruned to avoid descending into it)
                continue
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            child = Path(entry.path)
            # Don't descend into the worktree itself
            try:
                child.relative_to(self.worktree_dir)
                continue
            except ValueError:
                pass
            scan_into(child)

        return targets

    def copy_git_ignored_files(self):
        """Materialize selected git-ignored files/dirs from main workspace to worktree.

        Strategy:
          - Shared caches (``.pnpm-store``, ``.ruff_cache``, ``.mypy_cache``,
            ``.venv``) are *symlinked* — O(1), and these tools are designed to
            share state across workspaces.
          - Dependency trees (``node_modules``, ``vendor``) are *hard-linked*
            via ``cp -al`` so each worktree has an independent skeleton but
            file contents share inodes.
          - Single files (``.env``, ``go.work``, ``go.work.sum``) are
            hard-linked, falling back to copy on cross-device errors.
          - Search is limited to the workspace root and its immediate
            subdirectories, instead of a full recursive walk.
        """
        all_names = self._CACHE_DIR_NAMES | self._HARDLINK_DIR_NAMES | self._IGNORED_FILE_NAMES
        root = self.main_workspace
        symlinked = linked_dirs = copied_dirs = linked_files = copied_files = failed = 0

        for src in self._enumerate_ignored_targets(all_names):
            rel_path = src.relative_to(root)
            dst = self.worktree_dir / rel_path
            name = src.name
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if name in self._CACHE_DIR_NAMES and src.is_dir():
                    self._symlink_dir(src, dst)
                    symlinked += 1
                    logger.debug(f"symlinked cache: {rel_path}")
                elif name in self._HARDLINK_DIR_NAMES and src.is_dir():
                    mode = self._link_tree(src, dst)
                    if mode == 'linked':
                        linked_dirs += 1
                    else:
                        copied_dirs += 1
                    logger.debug(f"{'hard-linked' if mode == 'linked' else 'copied'} dir: {rel_path}")
                elif src.is_file():
                    self._clear_dst(dst)
                    mode = self._link_or_copy_file(src, dst)
                    if mode == 'linked':
                        linked_files += 1
                    else:
                        copied_files += 1
                    logger.debug(f"{'hard-linked' if mode == 'linked' else 'copied'} file: {rel_path}")
            except Exception as e:
                failed += 1
                logger.warning(f"Failed to materialize {rel_path}: {e}")

        if symlinked or linked_dirs or copied_dirs or linked_files or copied_files or failed:
            logger.info(
                f"Ignored materialization: {symlinked} cache symlink(s), "
                f"{linked_dirs} hard-linked dir(s), {copied_dirs} copied dir(s), "
                f"{linked_files} hard-linked file(s), {copied_files} copied file(s)"
                + (f", {failed} failed" if failed else "")
            )
    
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
        """Set ownership of worktree directory.

        Skipped when the requested ``--agent-user`` already matches the current
        effective UID *and* GID — ``chown -R`` would otherwise walk every entry
        in a tree that, after hard-linking, can contain hundreds of thousands
        of files.
        """
        agent_user = self.args.agent_user
        if not agent_user:
            return

        try:
            entry = pwd.getpwnam(agent_user)
        except KeyError:
            logger.warning(f"Unknown agent user '{agent_user}'; skipping ownership change")
            return

        if entry.pw_uid == os.geteuid() and entry.pw_gid == os.getegid():
            logger.info(f"Worktree already owned by '{agent_user}'; skipping chown")
            return

        try:
            cmd = f"chown -R {agent_user}: {self.worktree_dir}"
            self.run_command(cmd)
            logger.info(f"Changed ownership to {agent_user}")
        except Exception as e:
            logger.warning(f"Failed to change ownership: {e}")

    def verify_worktree(self):
        """Verify that the worktree is functional.

        Intentionally lightweight: ``git status`` confirms the worktree is wired
        up. ``go.work`` / ``package.json`` get presence-only checks — we used to
        run ``go work sync`` here but it hits the network and can take seconds
        on cold caches, which dominates the post-create wall time for Go repos.
        The hard-linked module cache already gives us the artifacts we need.
        """
        logger.info("Verifying worktree functionality...")

        try:
            self.run_command("git status", cwd=self.worktree_dir)
            logger.info("Git status check: PASSED")

            if (self.worktree_dir / 'go.work').exists():
                logger.info("Go workspace detected (go.work present)")

            if (self.worktree_dir / 'package.json').exists():
                logger.info("Node project detected (package.json present)")

        except Exception as e:
            logger.error(f"Worktree verification failed: {e}")
            raise

    def _workspace_changes(self):
        """Run ``git status`` once and return (staged, modified, untracked) lists.

        Cached on first access so callers can ask for each bucket independently
        without re-forking git. Uses ``--porcelain=v1 -z --untracked-files=all``
        to get a NUL-delimited, rename-aware listing safe for paths with spaces.
        Replaces three separate ``git diff`` / ``git ls-files`` invocations.
        """
        cached = getattr(self, '_workspace_changes_cache', None)
        if cached is not None:
            return cached

        staged, modified, untracked = [], [], []
        try:
            result = self.run_command(
                "git status --porcelain=v1 -z --untracked-files=all", check=False
            )
            if result.returncode != 0:
                logger.warning("Failed to read git status for workspace changes")
                self._workspace_changes_cache = (staged, modified, untracked)
                return self._workspace_changes_cache

            tokens = result.stdout.split('\x00')
            i = 0
            unmerged_seen = 0
            while i < len(tokens):
                entry = tokens[i]
                if not entry:
                    i += 1
                    continue
                if len(entry) < 4:
                    # Malformed line — every porcelain v1 record is "XY <path>".
                    i += 1
                    continue
                x, y, path = entry[0], entry[1], entry[3:]
                rename = x in 'RC' or y in 'RC'
                # Unmerged states: any of DD, AU, UD, UA, DU, AA, UU.
                # See `git status --short` docs.
                unmerged = (x == 'U' or y == 'U' or
                            (x == 'A' and y == 'A') or (x == 'D' and y == 'D'))

                if unmerged:
                    unmerged_seen += 1
                elif x == '?' and y == '?':
                    untracked.append(path)
                else:
                    # Staged changes: anything not "?", "!", " ", or pure-deletion.
                    if x not in ' ?!' and x != 'D':
                        staged.append(path)
                    # Unstaged modifications (skip pure deletions).
                    if y == 'M':
                        modified.append(path)

                # Renames/copies are encoded with an additional NUL-separated
                # source path immediately after — skip it.
                i += 2 if rename else 1

            if unmerged_seen:
                logger.warning(
                    f"Skipped {unmerged_seen} unmerged path(s) — resolve conflicts "
                    f"in the main workspace before creating worktrees if you need them."
                )
        except Exception as e:
            logger.warning(f"Failed to enumerate workspace changes: {e}")

        self._workspace_changes_cache = (staged, modified, untracked)
        return self._workspace_changes_cache

    def _materialize_workspace_files(self, rel_paths, label):
        """Materialize a list of repo-relative paths into the worktree.

        Used by the staged/modified/untracked copy methods. Hard-links files
        where possible, falls back to copy on cross-device errors. Per-file
        events are logged at DEBUG; a single summary line is logged at INFO.
        """
        linked = copied = skipped = 0
        for rel_path in rel_paths:
            src = self.main_workspace / rel_path
            dst = self.worktree_dir / rel_path
            if not src.exists():
                continue
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    mode = self._link_tree(src, dst)
                else:
                    self._clear_dst(dst)
                    mode = self._link_or_copy_file(src, dst)
                if mode == 'linked':
                    linked += 1
                else:
                    copied += 1
                logger.debug(f"{label}: {'hard-linked' if mode == 'linked' else 'copied'} {rel_path}")
            except Exception as e:
                skipped += 1
                logger.warning(f"Failed to materialize {label} {rel_path}: {e}")
        if linked or copied or skipped:
            logger.info(
                f"{label.capitalize()} materialization: linked={linked}, copied={copied}"
                + (f", skipped={skipped}" if skipped else "")
            )
    
    def copy_staged_files(self):
        """Materialize staged files from main workspace into worktree."""
        staged, _, _ = self._workspace_changes()
        self._materialize_workspace_files(staged, label='staged')

    def copy_non_staged_modified_files(self):
        """Materialize unstaged-modified files from main workspace into worktree."""
        _, modified, _ = self._workspace_changes()
        self._materialize_workspace_files(modified, label='modified')

    def copy_untracked_files(self):
        """Materialize untracked files from main workspace into worktree.

        Uses hard links where possible to avoid duplicating bulky untracked
        trees; falls back to a real copy if hard-linking fails.
        """
        _, _, untracked = self._workspace_changes()
        self._materialize_workspace_files(untracked, label='untracked')

    def run(self):
        """Run the complete worktree creation process."""
        try:
            logger.info("Starting git worktree creation process...")
            # Invalidate any cached workspace-change snapshot from a prior run.
            self._workspace_changes_cache = None
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

def run_as_claude_hook():
    """Run as a Claude Code WorktreeCreate hook.

    Reads JSON payload from stdin, creates a worktree, and prints the
    absolute worktree path to stdout on success. Exits with code 1 on failure.
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse JSON from stdin: {e}")
        sys.exit(1)

    hook_event = payload.get('hook_event_name', '')
    if hook_event != 'WorktreeCreate':
        logger.error(f"Unexpected hook event: {hook_event}, expected WorktreeCreate")
        sys.exit(1)

    cwd = payload.get('cwd')
    if not cwd:
        logger.error("Missing 'cwd' field in hook payload")
        sys.exit(1)

    # Map the optional 'name' field to prompt words for branch name generation
    name = payload.get('name', '')
    prompt_words = name.split() if name else []

    args = argparse.Namespace(
        prompt=prompt_words,
        branch=None,
        worktree=None,
        base_branch=None,
        plan_file=None,
        agent_user=None,
        copy_staged=True,
        copy_modified=False,
        copy_untracked=False,
        worktree_parent_dir=str(Path(cwd).parent),
        verbose=False,
        cwd_override=cwd,
    )

    # Required: copy_staged_files/copy_non_staged_modified_files/copy_untracked_files
    # call run_command() without cwd, so they rely on the process working directory.
    os.chdir(cwd)

    try:
        creator = GitWorktreeCreator(args)
        creator.run()
        print(str(creator.worktree_dir.resolve()))
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Hook failed: {e}")
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
    parser.add_argument('--claude-hook', action='store_true',
                        help='Run as Claude Code WorktreeCreate hook (reads JSON from stdin; all other arguments are ignored)')
    args = parser.parse_args()
    if args.claude_hook:
        run_as_claude_hook()
        return
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    creator = GitWorktreeCreator(args)
    creator.run()

if __name__ == '__main__':
    main()