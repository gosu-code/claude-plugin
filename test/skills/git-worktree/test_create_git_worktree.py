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
Unit tests for create_git_worktree.py

Tests the GitWorktreeCreator class functionality including:
- Branch name generation and uniqueness
- Worktree path finding
- File copying (git-ignored, staged, modified, untracked)
- Symlink creation
- Command execution
"""

import unittest
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sys
import argparse


# Add the scripts directory to the path
script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "git-worktree" / "scripts"
sys.path.insert(0, str(script_path))

# Import the module under test
from create_git_worktree import GitWorktreeCreator


class TestGitWorktreeCreator(unittest.TestCase):
    """Test suite for GitWorktreeCreator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.main_workspace = Path(self.temp_dir) / "main_workspace"
        self.main_workspace.mkdir()

        # Initialize a git repo in the temp directory
        subprocess.run(['git', 'init'], cwd=self.main_workspace, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.main_workspace, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.main_workspace, capture_output=True)

        # Create initial commit
        test_file = self.main_workspace / "README.md"
        test_file.write_text("# Test Repo")
        subprocess.run(['git', 'add', 'README.md'], cwd=self.main_workspace, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.main_workspace, capture_output=True)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def create_mock_args(self, **kwargs):
        """Helper to create mock arguments"""
        defaults = {
            'prompt': [],
            'branch': None,
            'worktree': None,
            'base_branch': None,
            'plan_file': None,
            'agent_user': None,
            'copy_staged': True,
            'copy_modified': False,
            'copy_untracked': False,
            'worktree_parent_dir': str(self.temp_dir),
            'verbose': False
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_initialization(self):
        """Test GitWorktreeCreator initialization"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            self.assertEqual(creator.main_workspace, Path(self.main_workspace))
            self.assertEqual(creator.worktree_parent_dir, Path(self.temp_dir))
            self.assertEqual(creator.branch_name, "agent/default-branch-name")

    def test_generate_branch_name_simple(self):
        """Test branch name generation from simple prompt"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            branch_name = creator.generate_branch_name("clean up todos comment")
            self.assertEqual(branch_name, "agent/clean-todos-comment")

    def test_generate_branch_name_with_short_words(self):
        """Test branch name generation filters out short words"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            branch_name = creator.generate_branch_name("fix a bug in the api")
            # Takes first 3 meaningful words (length > 2): fix, bug, the
            self.assertEqual(branch_name, "agent/fix-bug-the")

    def test_generate_branch_name_with_special_chars(self):
        """Test branch name generation with special characters"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            branch_name = creator.generate_branch_name("refactor API-errors & warnings")
            self.assertEqual(branch_name, "agent/refactor-api-errors")

    def test_generate_branch_name_empty_prompt(self):
        """Test branch name generation with empty prompt"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            branch_name = creator.generate_branch_name("")
            self.assertEqual(branch_name, "agent/task")

    def test_make_branch_unique_no_conflict(self):
        """Test make_branch_unique with no conflicts"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Mock run_command to return no matching branch
            with patch.object(creator, 'run_command') as mock_cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = ""
                mock_cmd.return_value = mock_result

                result = creator.make_branch_unique("agent/test-branch")
                self.assertEqual(result, "agent/test-branch")

    def test_make_branch_unique_with_conflict(self):
        """Test make_branch_unique with existing branch"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Mock run_command to simulate existing branch
            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_return(cmd, check=True):
                    result = Mock()
                    result.returncode = 0
                    if "agent/test-branch-1" in cmd:
                        result.stdout = ""
                    else:
                        result.stdout = "agent/test-branch"
                    return result

                mock_cmd.side_effect = mock_return

                result = creator.make_branch_unique("agent/test-branch")
                self.assertEqual(result, "agent/test-branch-1")

    def test_find_unique_worktree_path_no_conflict(self):
        """Test find_unique_worktree_path with no conflicts"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Mock run_command to return empty worktree list
            with patch.object(creator, 'run_command') as mock_cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = ""
                mock_cmd.return_value = mock_result

                base_path = str(Path(self.temp_dir) / "worktree-agent-no1")
                result = creator.find_unique_worktree_path(base_path)
                self.assertEqual(result, str(Path(self.temp_dir) / "worktree-agent-no1"))

    def test_find_unique_worktree_path_with_conflict(self):
        """Test find_unique_worktree_path with existing worktree"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create an existing worktree directory
            existing_dir = Path(self.temp_dir) / "worktree-agent-no1"
            existing_dir.mkdir()

            # Mock run_command to return existing worktree
            with patch.object(creator, 'run_command') as mock_cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = f"{existing_dir} abc123 [main]\n"
                mock_cmd.return_value = mock_result

                base_path = str(Path(self.temp_dir) / "worktree-agent-no1")
                result = creator.find_unique_worktree_path(base_path)
                self.assertEqual(result, str(Path(self.temp_dir) / "worktree-agent-no2"))

    def test_find_unique_worktree_path_extracts_number(self):
        """Test find_unique_worktree_path correctly extracts and increments numbers"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = ""
                mock_cmd.return_value = mock_result

                # Test with path containing no5
                base_path = str(Path(self.temp_dir) / "worktree-agent-no5")
                result = creator.find_unique_worktree_path(base_path)
                self.assertEqual(result, str(Path(self.temp_dir) / "worktree-agent-no5"))

    def test_run_command_success(self):
        """Test run_command with successful execution"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            result = creator.run_command("echo 'test'")
            self.assertEqual(result.returncode, 0)
            self.assertIn("test", result.stdout)

    def test_run_command_failure(self):
        """Test run_command with failed execution"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with self.assertRaises(subprocess.CalledProcessError):
                creator.run_command("false")

    def test_run_command_no_check(self):
        """Test run_command with check=False"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            result = creator.run_command("false", check=False)
            self.assertNotEqual(result.returncode, 0)

    def test_copy_git_ignored_files_directories(self):
        """Test copy_git_ignored_files with directories"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create node_modules directory in main workspace
            node_modules = self.main_workspace / "node_modules"
            node_modules.mkdir()
            (node_modules / "package1").mkdir()
            (node_modules / "package1" / "index.js").write_text("console.log('test');")

            creator.copy_git_ignored_files()

            # Verify directory was copied
            copied_dir = worktree_dir / "node_modules"
            self.assertTrue(copied_dir.exists())
            self.assertTrue((copied_dir / "package1" / "index.js").exists())

    def test_copy_git_ignored_files_single_files(self):
        """Test copy_git_ignored_files with single files"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create .env file in main workspace
            env_file = self.main_workspace / ".env"
            env_file.write_text("API_KEY=secret")

            creator.copy_git_ignored_files()

            # Verify file was copied
            copied_file = worktree_dir / ".env"
            self.assertTrue(copied_file.exists())
            self.assertEqual(copied_file.read_text(), "API_KEY=secret")

    def test_copy_git_ignored_files_avoids_git_dir(self):
        """Test copy_git_ignored_files doesn't traverse .git"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create a file matching our pattern inside .git (should not be copied)
            git_dir = self.main_workspace / ".git"
            git_dir.mkdir(exist_ok=True)
            (git_dir / ".env").write_text("SHOULD_NOT_COPY=true")

            with patch.object(creator, 'copy_git_ignored_files', wraps=creator.copy_git_ignored_files):
                creator.copy_git_ignored_files()

            # Verify the .env from .git was not copied
            copied_file = worktree_dir / ".git" / ".env"
            self.assertFalse(copied_file.exists())

    def test_copy_git_ignored_files_nested_structure(self):
        """Test copy_git_ignored_files preserves directory structure"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create nested structure
            nested_dir = self.main_workspace / "subdir" / "nested"
            nested_dir.mkdir(parents=True)
            env_file = nested_dir / ".env"
            env_file.write_text("NESTED=true")

            creator.copy_git_ignored_files()

            # Verify structure was preserved
            copied_file = worktree_dir / "subdir" / "nested" / ".env"
            self.assertTrue(copied_file.exists())
            self.assertEqual(copied_file.read_text(), "NESTED=true")

    def test_create_symlinks(self):
        """Test create_symlinks functionality"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create .claude/settings.local.json in main workspace
            claude_dir = self.main_workspace / ".claude"
            claude_dir.mkdir()
            settings_file = claude_dir / "settings.local.json"
            settings_file.write_text('{"key": "value"}')

            creator.create_symlinks()

            # Verify symlink was created
            symlink = worktree_dir / ".claude" / "settings.local.json"
            self.assertTrue(symlink.is_symlink())
            self.assertEqual(symlink.resolve(), settings_file.resolve())

    def test_create_symlinks_no_claude_dir(self):
        """Test create_symlinks when .claude directory doesn't exist"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Don't create .claude directory
            # This should not raise an error
            creator.create_symlinks()

            # Verify no symlink was created
            symlink = worktree_dir / ".claude" / "settings.local.json"
            self.assertFalse(symlink.exists())

    def test_create_symlinks_replaces_existing(self):
        """Test create_symlinks replaces existing symlink"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create .claude/settings.local.json in main workspace
            claude_dir = self.main_workspace / ".claude"
            claude_dir.mkdir()
            settings_file = claude_dir / "settings.local.json"
            settings_file.write_text('{"key": "value"}')

            # Create existing symlink
            worktree_claude = worktree_dir / ".claude"
            worktree_claude.mkdir()
            existing_symlink = worktree_claude / "settings.local.json"
            existing_symlink.write_text("old content")

            creator.create_symlinks()

            # Verify symlink was replaced
            self.assertTrue(existing_symlink.is_symlink())
            self.assertEqual(existing_symlink.resolve(), settings_file.resolve())

    def test_copy_plan_file_success(self):
        """Test copy_plan_file with existing file"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create plan file
            plan_file = Path(self.temp_dir) / "task-plan.md"
            plan_file.write_text("# Task Plan\n- Task 1\n- Task 2")

            creator.args.plan_file = str(plan_file)
            creator.copy_plan_file()

            # Verify plan file was copied
            copied_file = worktree_dir / "worktree-agent-task-plan.md"
            self.assertTrue(copied_file.exists())
            self.assertEqual(copied_file.read_text(), "# Task Plan\n- Task 1\n- Task 2")

    def test_copy_plan_file_not_found(self):
        """Test copy_plan_file with non-existent file"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            creator.args.plan_file = "/nonexistent/file.md"
            # Should not raise an error, just log warning
            creator.copy_plan_file()

    def test_copy_plan_file_none(self):
        """Test copy_plan_file with no plan file specified"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Should not raise an error
            creator.copy_plan_file()

    def test_set_ownership(self):
        """Test set_ownership functionality"""
        args = self.create_mock_args(agent_user='testuser')
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            with patch.object(creator, 'run_command') as mock_cmd:
                creator.set_ownership()

                # Verify chown command was called
                mock_cmd.assert_called_once()
                call_args = mock_cmd.call_args[0][0]
                self.assertIn("chown", call_args)
                self.assertIn("testuser", call_args)
                self.assertIn(str(worktree_dir), call_args)

    def test_set_ownership_no_user(self):
        """Test set_ownership with no user specified"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            with patch.object(creator, 'run_command') as mock_cmd:
                creator.set_ownership()

                # Verify chown was not called
                mock_cmd.assert_not_called()

    def test_copy_staged_files(self):
        """Test copy_staged_files functionality"""
        args = self.create_mock_args()

        # Save original directory
        orig_dir = Path.cwd()
        try:
            # Change to main workspace directory
            import os
            os.chdir(self.main_workspace)

            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create and stage a file
            test_file = self.main_workspace / "staged.txt"
            test_file.write_text("staged content")
            result = subprocess.run(['git', 'add', 'staged.txt'], cwd=self.main_workspace, capture_output=True)

            # Only test if git add succeeded
            if result.returncode == 0:
                creator.copy_staged_files()

                # Verify file was copied
                copied_file = worktree_dir / "staged.txt"
                self.assertTrue(copied_file.exists())
                self.assertEqual(copied_file.read_text(), "staged content")
            else:
                # Git operations not available, skip test verification
                pass
        finally:
            # Restore original directory
            import os
            os.chdir(orig_dir)

    def test_copy_non_staged_modified_files(self):
        """Test copy_non_staged_modified_files functionality"""
        args = self.create_mock_args()

        # Save original directory
        orig_dir = Path.cwd()
        try:
            # Change to main workspace directory
            import os
            os.chdir(self.main_workspace)

            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Modify existing file
            readme = self.main_workspace / "README.md"
            readme.write_text("# Modified content")

            # Check if file shows as modified
            result = subprocess.run(['git', 'diff', '--name-only'],
                                  cwd=self.main_workspace,
                                  capture_output=True,
                                  text=True)

            if result.returncode == 0 and "README.md" in result.stdout:
                creator.copy_non_staged_modified_files()

                # Verify file was copied
                copied_file = worktree_dir / "README.md"
                self.assertTrue(copied_file.exists())
                self.assertEqual(copied_file.read_text(), "# Modified content")
            else:
                # Git operations not available or file not modified, skip test verification
                pass
        finally:
            # Restore original directory
            import os
            os.chdir(orig_dir)

    def test_copy_untracked_files(self):
        """Test copy_untracked_files functionality"""
        args = self.create_mock_args()

        # Save original directory
        orig_dir = Path.cwd()
        try:
            # Change to main workspace directory
            import os
            os.chdir(self.main_workspace)

            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create untracked file
            untracked = self.main_workspace / "untracked.txt"
            untracked.write_text("untracked content")

            # Verify file is untracked
            result = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'],
                                  cwd=self.main_workspace,
                                  capture_output=True,
                                  text=True)

            if result.returncode == 0 and "untracked.txt" in result.stdout:
                creator.copy_untracked_files()

                # Verify file was copied
                copied_file = worktree_dir / "untracked.txt"
                self.assertTrue(copied_file.exists())
                self.assertEqual(copied_file.read_text(), "untracked content")
            else:
                # Git operations not available or file not untracked, skip test verification
                pass
        finally:
            # Restore original directory
            import os
            os.chdir(orig_dir)

    def test_copy_untracked_files_directory(self):
        """Test copy_untracked_files with directory"""
        args = self.create_mock_args()

        # Save original directory
        orig_dir = Path.cwd()
        try:
            # Change to main workspace directory
            import os
            os.chdir(self.main_workspace)

            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Create untracked directory with files
            untracked_dir = self.main_workspace / "untracked_dir"
            untracked_dir.mkdir()
            (untracked_dir / "file.txt").write_text("content")

            # Verify files are untracked
            result = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'],
                                  cwd=self.main_workspace,
                                  capture_output=True,
                                  text=True)

            if result.returncode == 0 and "untracked_dir" in result.stdout:
                creator.copy_untracked_files()

                # Verify directory was copied
                copied_dir = worktree_dir / "untracked_dir"
                self.assertTrue(copied_dir.exists())
                self.assertTrue((copied_dir / "file.txt").exists())
            else:
                # Git operations not available or dir not untracked, skip test verification
                pass
        finally:
            # Restore original directory
            import os
            os.chdir(orig_dir)

    def test_verify_worktree_git_status(self):
        """Test verify_worktree checks git status"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory with git
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            subprocess.run(['git', 'init'], cwd=worktree_dir, capture_output=True)
            creator.worktree_dir = worktree_dir

            # Should not raise an error
            creator.verify_worktree()

    def test_verify_worktree_with_go_work(self):
        """Test verify_worktree checks go work sync"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory with git
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            subprocess.run(['git', 'init'], cwd=worktree_dir, capture_output=True)

            # Create go.work file
            (worktree_dir / "go.work").write_text("go 1.21\n")
            creator.worktree_dir = worktree_dir

            # Should not raise an error (go work sync might fail but that's ok)
            creator.verify_worktree()

    def test_verify_worktree_with_package_json(self):
        """Test verify_worktree checks npm version"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Create a mock worktree directory with git
            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            subprocess.run(['git', 'init'], cwd=worktree_dir, capture_output=True)

            # Create package.json file
            (worktree_dir / "package.json").write_text('{"name": "test"}')
            creator.worktree_dir = worktree_dir

            # Should not raise an error (npm might not be available but that's ok)
            creator.verify_worktree()

    def test_create_worktree_with_existing_worktree(self):
        """Test create_worktree with existing worktree argument"""
        existing_worktree = Path(self.temp_dir) / "existing_worktree"
        existing_worktree.mkdir()

        args = self.create_mock_args(worktree=str(existing_worktree))
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            creator.create_worktree()

            # Verify worktree_dir was set to existing directory
            self.assertEqual(creator.worktree_dir, existing_worktree)

    def test_create_worktree_with_branch(self):
        """Test create_worktree with specified branch"""
        args = self.create_mock_args(branch='feature/test-branch')
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                # Mock git commands with appropriate responses
                def mock_run(cmd, cwd=None, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    if 'git worktree list' in cmd:
                        # Return the worktree in the list
                        mock_result.stdout = f"{Path(self.temp_dir) / 'worktree-agent-no1'} abc123 [feature/test-branch]\n"
                    else:
                        mock_result.stdout = ""
                    return mock_result

                mock_cmd.side_effect = mock_run

                with patch.object(creator, 'find_unique_worktree_path') as mock_find:
                    mock_find.return_value = str(Path(self.temp_dir) / "worktree-agent-no1")

                    creator.create_worktree()

                    # Verify branch name was set
                    self.assertEqual(creator.branch_name, 'feature/test-branch')

    def test_create_worktree_generates_branch_from_prompt(self):
        """Test create_worktree generates branch name from prompt"""
        args = self.create_mock_args(prompt=['fix', 'critical', 'bug'])
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                # Mock git commands with appropriate responses
                def mock_run(cmd, cwd=None, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    if 'git worktree list' in cmd:
                        # Return the worktree in the list
                        mock_result.stdout = f"{Path(self.temp_dir) / 'worktree-agent-no1'} abc123 [agent/fix-critical-bug]\n"
                    else:
                        mock_result.stdout = ""
                    return mock_result

                mock_cmd.side_effect = mock_run

                with patch.object(creator, 'find_unique_worktree_path') as mock_find:
                    mock_find.return_value = str(Path(self.temp_dir) / "worktree-agent-no1")

                    creator.create_worktree()

                    # Verify branch name was generated from prompt
                    self.assertEqual(creator.branch_name, 'agent/fix-critical-bug')

    # ==================== Base Branch Resolution Tests ====================

    def test_resolve_base_branch_local_exists(self):
        """Test resolve_base_branch when branch exists locally"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            # Mock git branch --list to show branch exists locally
            with patch.object(creator, 'run_command') as mock_cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "  develop\n"
                mock_cmd.return_value = mock_result

                result = creator.resolve_base_branch('develop')

                self.assertEqual(result, 'develop')
                mock_cmd.assert_called_once_with('git branch --list develop', check=False)

    def test_resolve_base_branch_remote_exists(self):
        """Test resolve_base_branch when branch exists on remote"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    if 'git branch --list develop' in cmd:
                        mock_result.stdout = ""  # Not local
                    elif 'git branch -r --list origin/develop' in cmd:
                        mock_result.stdout = "  origin/develop\n"  # On remote
                    elif 'git fetch origin develop' in cmd:
                        mock_result.stdout = "Fetched develop"
                    return mock_result

                mock_cmd.side_effect = mock_run

                result = creator.resolve_base_branch('develop')

                self.assertEqual(result, 'origin/develop')
                self.assertEqual(mock_cmd.call_count, 3)

    def test_resolve_base_branch_not_found(self):
        """Test resolve_base_branch when branch doesn't exist"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""  # Branch not found
                    return mock_result

                mock_cmd.side_effect = mock_run

                with self.assertRaises(Exception) as context:
                    creator.resolve_base_branch('nonexistent')

                self.assertIn("not found locally or on remote", str(context.exception))

    def test_resolve_base_branch_with_origin_prefix(self):
        """Test resolve_base_branch when user provides 'origin/develop'"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "  develop\n"
                mock_cmd.return_value = mock_result

                result = creator.resolve_base_branch('origin/develop')

                # Should normalize to just 'develop'
                self.assertEqual(result, 'develop')
                mock_cmd.assert_called_once_with('git branch --list develop', check=False)

    def test_resolve_base_branch_fetch_failure(self):
        """Test resolve_base_branch when fetch fails"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    if 'git branch --list develop' in cmd:
                        mock_result.stdout = ""
                    elif 'git branch -r --list origin/develop' in cmd:
                        mock_result.stdout = "  origin/develop\n"
                    elif 'git fetch origin develop' in cmd:
                        raise subprocess.CalledProcessError(1, cmd, stderr="Network error")
                    return mock_result

                mock_cmd.side_effect = mock_run

                with self.assertRaises(Exception) as context:
                    creator.resolve_base_branch('develop')

                self.assertIn("Failed to fetch branch", str(context.exception))

    def test_resolve_base_branch_no_remote(self):
        """Test resolve_base_branch when no remote is configured"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, check=True):
                    mock_result = Mock()
                    if 'git remote' in cmd:
                        mock_result.returncode = 0
                        mock_result.stdout = ""  # No remotes
                    else:
                        mock_result.returncode = 0
                        mock_result.stdout = ""  # Branch not found locally
                    return mock_result

                mock_cmd.side_effect = mock_run

                with self.assertRaises(Exception) as context:
                    creator.resolve_base_branch('develop')

                self.assertIn("no remote 'origin' configured", str(context.exception))

    def test_create_worktree_with_base_branch(self):
        """Test create_worktree with base branch specified"""
        args = self.create_mock_args(
            branch='feature/new-api',
            base_branch='develop'
        )

        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    if 'git branch --list feature/new-api' in cmd:
                        mock_result.stdout = ""  # Branch unique
                    elif 'git branch --list develop' in cmd:
                        mock_result.stdout = "  develop\n"  # Base exists locally
                    elif 'git worktree add' in cmd:
                        mock_result.stdout = "Preparing worktree"
                    elif 'git worktree list' in cmd:
                        mock_result.stdout = f"{creator.worktree_dir}\n"
                    return mock_result

                mock_cmd.side_effect = mock_run

                with patch.object(creator, 'find_unique_worktree_path') as mock_find:
                    mock_find.return_value = str(Path(self.temp_dir) / "worktree-agent-no1")

                    creator.create_worktree()

                    # Verify worktree add was called with base branch
                    worktree_add_calls = [call for call in mock_cmd.call_args_list if 'git worktree add' in str(call)]
                    self.assertEqual(len(worktree_add_calls), 1)
                    self.assertIn('develop', str(worktree_add_calls[0]))

    def test_create_worktree_without_base_branch(self):
        """Test backward compatibility: create_worktree without base branch"""
        args = self.create_mock_args(branch='feature/test')

        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    if 'git branch --list feature/test' in cmd:
                        mock_result.stdout = ""
                    elif 'git worktree add' in cmd:
                        mock_result.stdout = "Preparing worktree"
                    elif 'git worktree list' in cmd:
                        mock_result.stdout = f"{creator.worktree_dir}\n"
                    return mock_result

                mock_cmd.side_effect = mock_run

                with patch.object(creator, 'find_unique_worktree_path') as mock_find:
                    mock_find.return_value = str(Path(self.temp_dir) / "worktree-agent-no1")

                    creator.create_worktree()

                    # Verify worktree add was called without base branch
                    worktree_add_calls = [call for call in mock_cmd.call_args_list if 'git worktree add' in str(call)]
                    self.assertEqual(len(worktree_add_calls), 1)
                    # Should not have a third argument (base ref)
                    cmd_str = str(worktree_add_calls[0])
                    # Count tokens: should be "git worktree add -b <branch> <path>" (no base ref)
                    self.assertNotIn('develop', cmd_str)
                    self.assertNotIn('origin/', cmd_str)

    def test_create_worktree_base_branch_invalid(self):
        """Test create_worktree with invalid base branch"""
        args = self.create_mock_args(
            branch='feature/test',
            base_branch='invalid-branch'
        )

        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, check=True):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""  # Branch not found
                    return mock_result

                mock_cmd.side_effect = mock_run

                with patch.object(creator, 'find_unique_worktree_path') as mock_find:
                    mock_find.return_value = str(Path(self.temp_dir) / "worktree-agent-no1")

                    with self.assertRaises(Exception) as context:
                        creator.create_worktree()

                    self.assertIn("not found", str(context.exception))


class TestGitWorktreeCreatorIntegration(unittest.TestCase):
    """Integration tests for GitWorktreeCreator (requires git)"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.main_workspace = Path(self.temp_dir) / "main_workspace"
        self.main_workspace.mkdir()

        try:
            # Initialize a git repo
            subprocess.run(['git', 'init'], cwd=self.main_workspace, capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.main_workspace, capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.main_workspace, capture_output=True, check=True)

            # Set default branch to main
            subprocess.run(['git', 'config', 'init.defaultBranch', 'main'], cwd=self.main_workspace, capture_output=True)
            subprocess.run(['git', 'checkout', '-b', 'main'], cwd=self.main_workspace, capture_output=True)

            # Create initial commit
            test_file = self.main_workspace / "README.md"
            test_file.write_text("# Test Repo")
            subprocess.run(['git', 'add', 'README.md'], cwd=self.main_workspace, capture_output=True, check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.main_workspace, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            # If git setup fails, mark as skipped
            self.skipTest(f"Git setup failed: {e}")

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up any worktrees first
        try:
            result = subprocess.run(['git', 'worktree', 'list'],
                                  cwd=self.main_workspace,
                                  capture_output=True,
                                  text=True,
                                  check=False)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and str(self.main_workspace) not in line:
                        worktree_path = line.split()[0]
                        subprocess.run(['git', 'worktree', 'remove', worktree_path, '--force'],
                                     cwd=self.main_workspace,
                                     capture_output=True,
                                     check=False)
        except Exception:
            pass

        shutil.rmtree(self.temp_dir)

    def create_mock_args(self, **kwargs):
        """Helper to create mock arguments"""
        defaults = {
            'prompt': [],
            'branch': None,
            'worktree': None,
            'base_branch': None,
            'plan_file': None,
            'agent_user': None,
            'copy_staged': True,
            'copy_modified': False,
            'copy_untracked': False,
            'worktree_parent_dir': str(self.temp_dir),
            'verbose': False
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_full_workflow_with_new_worktree(self):
        """Test complete workflow of creating a new worktree"""
        args = self.create_mock_args(
            prompt=['test', 'feature'],
            copy_untracked=True
        )

        # Create some test files
        (self.main_workspace / "node_modules").mkdir()
        (self.main_workspace / "node_modules" / "package.txt").write_text("test")
        (self.main_workspace / ".env").write_text("KEY=value")

        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)
            creator.run()

            # Verify worktree was created
            self.assertTrue(creator.worktree_dir.exists())

            # Verify files were copied
            self.assertTrue((creator.worktree_dir / "node_modules" / "package.txt").exists())
            self.assertTrue((creator.worktree_dir / ".env").exists())

            # Verify it's a valid git worktree
            result = subprocess.run(['git', 'status'],
                                  cwd=creator.worktree_dir,
                                  capture_output=True,
                                  text=True,
                                  check=True)
            self.assertIn("On branch", result.stdout)

    def test_create_worktree_with_local_base_branch(self):
        """Integration test: Create worktree from local base branch"""
        # Create a develop branch
        subprocess.run(['git', 'checkout', '-b', 'develop'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)
        (self.main_workspace / "develop.txt").write_text("develop branch file")
        subprocess.run(['git', 'add', 'develop.txt'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)
        subprocess.run(['git', 'commit', '-m', 'Add develop file'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)

        # Go back to main
        subprocess.run(['git', 'checkout', 'main'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)

        # Create worktree from develop
        args = self.create_mock_args(
            branch='feature/from-develop',
            base_branch='develop'
        )

        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)
            creator.create_worktree()

            # Verify worktree was created
            self.assertTrue(creator.worktree_dir.exists())

            # Verify the worktree has the develop.txt file
            self.assertTrue((creator.worktree_dir / "develop.txt").exists())

            # Verify branch is based on develop
            result = subprocess.run(['git', 'log', '--oneline'],
                                  cwd=creator.worktree_dir,
                                  capture_output=True,
                                  text=True,
                                  check=True)
            self.assertIn("Add develop file", result.stdout)

    def test_create_worktree_with_remote_base_branch(self):
        """Integration test: Create worktree from remote base branch"""
        # Create a bare remote repository
        remote_dir = Path(self.temp_dir) / "remote.git"
        subprocess.run(['git', 'init', '--bare', str(remote_dir)],
                      capture_output=True,
                      check=True)

        # Add remote and push
        subprocess.run(['git', 'remote', 'add', 'origin', str(remote_dir)],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)
        subprocess.run(['git', 'push', '-u', 'origin', 'main'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)

        # Create and push a release branch
        subprocess.run(['git', 'checkout', '-b', 'release-1.0'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)
        (self.main_workspace / "release.txt").write_text("release file")
        subprocess.run(['git', 'add', 'release.txt'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)
        subprocess.run(['git', 'commit', '-m', 'Add release file'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)
        subprocess.run(['git', 'push', '-u', 'origin', 'release-1.0'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)

        # Go back to main and delete local release branch
        subprocess.run(['git', 'checkout', 'main'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)
        subprocess.run(['git', 'branch', '-D', 'release-1.0'],
                      cwd=self.main_workspace,
                      capture_output=True,
                      check=True)

        # Create worktree from remote release branch
        args = self.create_mock_args(
            branch='hotfix/security-patch',
            base_branch='release-1.0'
        )

        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)
            creator.create_worktree()

            # Verify worktree was created
            self.assertTrue(creator.worktree_dir.exists())

            # Verify the worktree has the release.txt file
            self.assertTrue((creator.worktree_dir / "release.txt").exists())

            # Verify branch is based on release-1.0
            result = subprocess.run(['git', 'log', '--oneline'],
                                  cwd=creator.worktree_dir,
                                  capture_output=True,
                                  text=True,
                                  check=True)
            self.assertIn("Add release file", result.stdout)


if __name__ == '__main__':
    unittest.main()