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
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sys
import argparse


# Add the scripts directory to the path
script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "git-worktree" / "scripts"
sys.path.insert(0, str(script_path))

# Import the module under test
from create_git_worktree import GitWorktreeCreator, _try_clonefile


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
        """Test copy_git_ignored_files preserves directory structure to depth 5.

        The enumeration walk explores up to 5 directory levels (deep
        monorepos); entries nested beyond that are intentionally not
        picked up.
        """
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # 1 subdir deep — well within the scan range
            subdir = self.main_workspace / "subdir"
            subdir.mkdir()
            (subdir / ".env").write_text("SHALLOW=true")

            # 4 subdirs deep — still within the depth-5 walk
            deep = self.main_workspace / "l1" / "l2" / "l3" / "l4"
            deep.mkdir(parents=True)
            (deep / ".env").write_text("DEEP=true")

            # 5 subdirs deep — beyond the scan range
            too_deep = deep / "l5"
            too_deep.mkdir()
            (too_deep / ".env").write_text("TOO_DEEP=true")

            creator.copy_git_ignored_files()

            shallow_copy = worktree_dir / "subdir" / ".env"
            self.assertTrue(shallow_copy.exists())
            self.assertEqual(shallow_copy.read_text(), "SHALLOW=true")

            deep_copy = worktree_dir / "l1" / "l2" / "l3" / "l4" / ".env"
            self.assertTrue(deep_copy.exists(), "Files up to 4 subdirs deep should be picked up")
            self.assertEqual(deep_copy.read_text(), "DEEP=true")

            too_deep_copy = worktree_dir / "l1" / "l2" / "l3" / "l4" / "l5" / ".env"
            self.assertFalse(too_deep_copy.exists(), "Files deeper than the depth-5 walk should not be picked up")

    def test_link_tree_clonefile_independence(self):
        """_link_tree prefers clonefile on macOS; the clone is CoW-independent."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            src = self.main_workspace / "tree_src"
            (src / "nested").mkdir(parents=True)
            (src / "nested" / "file.txt").write_text("original")
            (src / "top.txt").write_text("top")

            dst = Path(self.temp_dir) / "tree_dst"
            mode = creator._link_tree(src, dst)

            # Contents must match regardless of the strategy used
            self.assertEqual((dst / "nested" / "file.txt").read_text(), "original")
            self.assertEqual((dst / "top.txt").read_text(), "top")

            # Only assert the clone path when the temp filesystem actually
            # supports clonefile (TMPDIR may point at a non-APFS mount).
            probe_src = Path(self.temp_dir) / "clone_probe_src"
            probe_src.write_text("probe")
            if _try_clonefile(probe_src, Path(self.temp_dir) / "clone_probe_dst"):
                self.assertEqual(mode, 'cloned', "clonefile should be preferred when supported")

            if mode == 'cloned':
                # In-place write in the clone must not leak back to the source
                with open(dst / "nested" / "file.txt", 'a') as f:
                    f.write("-worktree-edit")
                self.assertEqual((src / "nested" / "file.txt").read_text(), "original")

    def test_symlink_children_layout(self):
        """Symlink-children tier: packages symlinked, dot-entries materialized, .cache skipped."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            node_modules = self.main_workspace / "node_modules"
            (node_modules / "pkg-a").mkdir(parents=True)
            (node_modules / "pkg-a" / "index.js").write_text("module.exports = 1;")
            (node_modules / "@scope" / "pkg-b").mkdir(parents=True)
            (node_modules / "@scope" / "pkg-b" / "index.js").write_text("module.exports = 2;")
            bin_dir = node_modules / ".bin"
            bin_dir.mkdir()
            (bin_dir / "tool").symlink_to("../pkg-a/index.js")
            cache_dir = node_modules / ".cache"
            cache_dir.mkdir()
            (cache_dir / "junk.txt").write_text("cache junk")
            (node_modules / ".package-lock.json").write_text("{}")

            # Force the symlink-children tier by disabling clonefile
            with patch('create_git_worktree._try_clonefile', return_value=False):
                creator.copy_git_ignored_files()

            wt_nm = worktree_dir / "node_modules"
            self.assertTrue(wt_nm.is_dir())
            self.assertFalse(wt_nm.is_symlink(), "node_modules itself must be a real dir")

            pkg_a = wt_nm / "pkg-a"
            self.assertTrue(pkg_a.is_symlink(), "top-level packages should be symlinks")
            self.assertEqual(pkg_a.resolve(), (node_modules / "pkg-a").resolve())
            self.assertEqual((pkg_a / "index.js").read_text(), "module.exports = 1;")

            scope = wt_nm / "@scope"
            self.assertTrue(scope.is_symlink(), "@scope dirs should be symlinks")
            self.assertEqual((scope / "pkg-b" / "index.js").read_text(), "module.exports = 2;")

            wt_bin = wt_nm / ".bin"
            self.assertTrue(wt_bin.is_dir())
            self.assertFalse(wt_bin.is_symlink(), ".bin must not be symlinked to the main workspace")
            self.assertTrue((wt_bin / "tool").is_symlink(), "relative .bin shims should be preserved")

            self.assertFalse((wt_nm / ".cache").exists(), ".cache should be skipped entirely")

            lock = wt_nm / ".package-lock.json"
            self.assertTrue(lock.is_file())
            self.assertFalse(lock.is_symlink(), "metadata files must not be symlinked")

    def test_symlink_children_applies_to_venv_and_vendor(self):
        """Symlink-children tier applies to .venv and vendor dep dirs too."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            venv = self.main_workspace / ".venv"
            (venv / "lib" / "python3.12" / "site-packages").mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text("home = /usr/bin")
            vendor = self.main_workspace / "vendor"
            (vendor / "github.com").mkdir(parents=True)
            (vendor / "github.com" / "mod.go").write_text("package mod")

            with patch('create_git_worktree._try_clonefile', return_value=False):
                creator.copy_git_ignored_files()

            wt_venv = worktree_dir / ".venv"
            self.assertTrue(wt_venv.is_dir())
            self.assertFalse(wt_venv.is_symlink())
            self.assertTrue((wt_venv / "lib").is_symlink(), ".venv children should be symlinks")
            cfg = wt_venv / "pyvenv.cfg"
            self.assertTrue(cfg.is_file())
            self.assertFalse(cfg.is_symlink(), "pyvenv.cfg must not be symlinked")

            wt_vendor = worktree_dir / "vendor"
            self.assertFalse(wt_vendor.is_symlink())
            self.assertTrue((wt_vendor / "github.com").is_symlink(), "vendor children should be symlinks")
            self.assertEqual((wt_vendor / "github.com" / "mod.go").read_text(), "package mod")

    def test_parallel_materialization_all_targets(self):
        """Concurrent materialization still covers every enumerated target."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            (self.main_workspace / "node_modules" / "pkg").mkdir(parents=True)
            (self.main_workspace / "node_modules" / "pkg" / "index.js").write_text("1")
            (self.main_workspace / "packages" / "app1" / "node_modules" / "dep").mkdir(parents=True)
            (self.main_workspace / "packages" / "app1" / "node_modules" / "dep" / "index.js").write_text("2")
            (self.main_workspace / "packages" / "app2" / ".venv" / "lib").mkdir(parents=True)
            (self.main_workspace / ".env").write_text("KEY=value")

            creator.copy_git_ignored_files()

            self.assertTrue((worktree_dir / "node_modules" / "pkg" / "index.js").exists())
            self.assertTrue((worktree_dir / "packages" / "app1" / "node_modules" / "dep" / "index.js").exists())
            self.assertTrue((worktree_dir / "packages" / "app2" / ".venv" / "lib").exists())
            self.assertEqual((worktree_dir / ".env").read_text(), "KEY=value")

    def test_symlink_children_preserves_symlink_entries(self):
        """pnpm-style top-level symlink entries are recreated verbatim (incl. broken ones)."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            node_modules = self.main_workspace / "node_modules"
            real_pkg = node_modules / ".pnpm" / "pkg-c@1.0.0" / "node_modules" / "pkg-c"
            real_pkg.mkdir(parents=True)
            (real_pkg / "index.js").write_text("module.exports = 3;")
            (node_modules / "pkg-c").symlink_to(".pnpm/pkg-c@1.0.0/node_modules/pkg-c")
            (node_modules / "dangling").symlink_to("does-not-exist")

            with patch('create_git_worktree._try_clonefile', return_value=False):
                creator.copy_git_ignored_files()

            wt_nm = worktree_dir / "node_modules"
            pkg_c = wt_nm / "pkg-c"
            self.assertTrue(pkg_c.is_symlink())
            self.assertEqual(os.readlink(pkg_c), ".pnpm/pkg-c@1.0.0/node_modules/pkg-c",
                             "relative symlink target must be recreated verbatim")
            # Resolves inside THIS worktree because .pnpm was hard-linked in
            self.assertEqual((pkg_c / "index.js").read_text(), "module.exports = 3;")

            dangling = wt_nm / "dangling"
            self.assertTrue(dangling.is_symlink(), "broken symlinks should be recreated, not dropped")
            self.assertEqual(os.readlink(dangling), "does-not-exist")

    def test_symlink_children_per_child_fallback(self):
        """A failing symlink for one child falls back to hard-link/copy; siblings unaffected."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            node_modules = self.main_workspace / "node_modules"
            for name in ("pkg-good", "pkg-bad"):
                (node_modules / name).mkdir(parents=True)
                (node_modules / name / "index.js").write_text(f"// {name}")

            real_symlink_to = Path.symlink_to

            def flaky_symlink_to(path_self, target, *fn_args, **fn_kwargs):
                if path_self.name == 'pkg-bad':
                    raise OSError("simulated symlink failure")
                return real_symlink_to(path_self, target, *fn_args, **fn_kwargs)

            with patch('create_git_worktree._try_clonefile', return_value=False), \
                 patch.object(Path, 'symlink_to', flaky_symlink_to):
                creator.copy_git_ignored_files()

            wt_nm = worktree_dir / "node_modules"
            good = wt_nm / "pkg-good"
            self.assertTrue(good.is_symlink(), "healthy siblings must still be symlinked")
            bad = wt_nm / "pkg-bad"
            self.assertTrue(bad.exists(), "failed child must be materialized via fallback")
            self.assertFalse(bad.is_symlink())
            self.assertEqual((bad / "index.js").read_text(), "// pkg-bad")

    def test_parallel_materialization_failure_isolation(self):
        """One failing target must not prevent other targets from materializing."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            (self.main_workspace / "node_modules" / "pkg").mkdir(parents=True)
            (self.main_workspace / "node_modules" / "pkg" / "index.js").write_text("1")
            (self.main_workspace / ".env").write_text("KEY=value")

            real_materialize = GitWorktreeCreator._materialize_ignored_target

            def flaky_materialize(creator_self, src):
                if src.name == '.env':
                    raise OSError("simulated target failure")
                return real_materialize(creator_self, src)

            with patch.object(GitWorktreeCreator, '_materialize_ignored_target', flaky_materialize), \
                 self.assertLogs('create_git_worktree', level='WARNING') as logs:
                creator.copy_git_ignored_files()

            self.assertTrue(any("Failed to materialize" in line for line in logs.output))
            self.assertTrue((worktree_dir / "node_modules" / "pkg" / "index.js").exists(),
                            "other targets must still be materialized")
            self.assertFalse((worktree_dir / ".env").exists())

    def test_tracked_dep_dir_is_skipped(self):
        """A git-tracked vendor/ must not be clobbered by dep-dir materialization."""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            vendor = self.main_workspace / "vendor" / "github.com" / "dep"
            vendor.mkdir(parents=True)
            (vendor / "mod.go").write_text("package dep")
            subprocess.run(['git', 'add', 'vendor'], cwd=self.main_workspace,
                           capture_output=True, check=True)
            subprocess.run(['git', 'commit', '-m', 'vendor deps'], cwd=self.main_workspace,
                           capture_output=True, check=True)
            # An ignored dep dir alongside it must still be materialized
            (self.main_workspace / "node_modules" / "pkg").mkdir(parents=True)

            creator.copy_git_ignored_files()

            self.assertFalse((worktree_dir / "vendor").exists(),
                             "tracked vendor/ comes from the checkout, not from materialization")
            self.assertTrue((worktree_dir / "node_modules" / "pkg").exists())

    def test_untracked_user_code_never_symlinked(self):
        """User-code materialization must never symlink into the main workspace."""
        args = self.create_mock_args(copy_untracked=True)

        orig_dir = Path.cwd()
        try:
            os.chdir(self.main_workspace)
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            feature = self.main_workspace / "feature_dir" / "sub"
            feature.mkdir(parents=True)
            (feature / "a.py").write_text("print('a')")

            with patch('create_git_worktree._try_clonefile', return_value=False):
                creator.copy_untracked_files()

            copied = worktree_dir / "feature_dir"
            self.assertTrue((copied / "sub" / "a.py").exists())
            for path in [copied] + list(copied.rglob("*")):
                self.assertFalse(path.is_symlink(),
                                 f"user code must not be symlinked: {path}")
                self.assertTrue(str(Path(os.path.realpath(path))).startswith(str(worktree_dir.resolve())),
                                f"user code must stay inside the worktree: {path}")
        finally:
            os.chdir(orig_dir)

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

    def test_set_ownership(self):
        """Test set_ownership runs chown when target user differs from current"""
        args = self.create_mock_args(agent_user='testuser')
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Fake pwd entry whose uid/gid differ from the test runner so the
            # short-circuit doesn't trip.
            fake_entry = Mock()
            fake_entry.pw_uid = 999999
            fake_entry.pw_gid = 999999

            with patch('create_git_worktree.pwd.getpwnam', return_value=fake_entry), \
                 patch.object(creator, 'run_command') as mock_cmd:
                creator.set_ownership()

                mock_cmd.assert_called_once()
                call_args = mock_cmd.call_args[0][0]
                self.assertIn("chown", call_args)
                self.assertIn("testuser", call_args)
                self.assertIn(str(worktree_dir), call_args)

    def test_set_ownership_skipped_when_current_user(self):
        """Test set_ownership short-circuits when target uid/gid match the runner"""
        args = self.create_mock_args(agent_user='testuser')
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            # Fake pwd entry that *matches* the current effective ids — chown
            # should be skipped because the worktree is already owned correctly.
            fake_entry = Mock()
            fake_entry.pw_uid = os.geteuid()
            fake_entry.pw_gid = os.getegid()

            with patch('create_git_worktree.pwd.getpwnam', return_value=fake_entry), \
                 patch.object(creator, 'run_command') as mock_cmd:
                creator.set_ownership()
                mock_cmd.assert_not_called()

    def test_set_ownership_unknown_user(self):
        """Test set_ownership warns and skips when --agent-user is unknown"""
        args = self.create_mock_args(agent_user='definitely-not-a-real-user-xyz')
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            worktree_dir = Path(self.temp_dir) / "test_worktree"
            worktree_dir.mkdir()
            creator.worktree_dir = worktree_dir

            with patch.object(creator, 'run_command') as mock_cmd:
                creator.set_ownership()
                mock_cmd.assert_not_called()

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
                mock_cmd.assert_called_once_with('git branch --list develop', cwd=creator.main_workspace, check=False)

    def test_resolve_base_branch_remote_exists(self):
        """Test resolve_base_branch when branch exists on remote"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, **kwargs):
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
                def mock_run(cmd, **kwargs):
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""  # Branch not found
                    return mock_result

                mock_cmd.side_effect = mock_run

                with self.assertRaises(Exception) as context:
                    creator.resolve_base_branch('nonexistent')

                # Accept either error message (depends on whether remote is configured)
                error_msg = str(context.exception)
                self.assertTrue(
                    "not found locally or on remote" in error_msg or
                    "not found locally and no remote" in error_msg
                )

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
                mock_cmd.assert_called_once_with('git branch --list develop', cwd=creator.main_workspace, check=False)

    def test_resolve_base_branch_fetch_failure(self):
        """Test resolve_base_branch when fetch fails"""
        args = self.create_mock_args()
        with patch('os.getcwd', return_value=str(self.main_workspace)):
            creator = GitWorktreeCreator(args)

            with patch.object(creator, 'run_command') as mock_cmd:
                def mock_run(cmd, **kwargs):
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
                def mock_run(cmd, **kwargs):
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
                def mock_run(cmd, **kwargs):
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
                def mock_run(cmd, **kwargs):
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
                def mock_run(cmd, **kwargs):
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


class TestClaudeHookMode(unittest.TestCase):
    """Test suite for --claude-hook mode (WorktreeCreate hook)"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.main_workspace = Path(self.temp_dir) / "main_workspace"
        self.main_workspace.mkdir()

        # Initialize a git repo
        subprocess.run(['git', 'init'], cwd=self.main_workspace, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.main_workspace, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.main_workspace, capture_output=True, check=True)
        subprocess.run(['git', 'checkout', '-b', 'main'], cwd=self.main_workspace, capture_output=True)

        # Create initial commit
        test_file = self.main_workspace / "README.md"
        test_file.write_text("# Test Repo")
        subprocess.run(['git', 'add', 'README.md'], cwd=self.main_workspace, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.main_workspace, capture_output=True, check=True)

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up any worktrees first
        try:
            result = subprocess.run(['git', 'worktree', 'list'],
                                    cwd=self.main_workspace,
                                    capture_output=True, text=True, check=False)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and str(self.main_workspace) not in line:
                        worktree_path = line.split()[0]
                        subprocess.run(['git', 'worktree', 'remove', worktree_path, '--force'],
                                       cwd=self.main_workspace,
                                       capture_output=True, check=False)
        except Exception:
            pass
        shutil.rmtree(self.temp_dir)

    def _run_hook(self, payload_dict):
        """Helper to run the script in --claude-hook mode with given payload.

        Returns (stdout, stderr, returncode).
        """
        script = str(script_path / "create_git_worktree.py")
        payload = json.dumps(payload_dict)
        result = subprocess.run(
            [sys.executable, script, '--claude-hook'],
            input=payload, capture_output=True, text=True,
        )
        return result.stdout.strip(), result.stderr, result.returncode

    def test_run_as_claude_hook_success(self):
        """Valid payload produces absolute worktree path on stdout, exit 0"""
        payload = {
            "session_id": "test-session",
            "cwd": str(self.main_workspace),
            "hook_event_name": "WorktreeCreate",
            "name": "test-feature",
        }
        stdout, stderr, rc = self._run_hook(payload)
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stderr: {stderr}")
        # stdout must contain exactly one line: the absolute worktree path
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 1, f"Expected exactly one line on stdout, got {len(lines)}: {lines}")
        worktree_path = Path(lines[0])
        self.assertTrue(worktree_path.is_absolute(), f"Path should be absolute: {stdout}")
        self.assertTrue(worktree_path.exists(), f"Worktree path should exist: {stdout}")

    def test_run_as_claude_hook_invalid_json(self):
        """Invalid JSON on stdin causes exit 1"""
        script = str(script_path / "create_git_worktree.py")
        result = subprocess.run(
            [sys.executable, script, '--claude-hook'],
            input="not valid json{{{",
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "")

    def test_run_as_claude_hook_wrong_event(self):
        """Wrong hook_event_name causes exit 1"""
        payload = {
            "session_id": "test-session",
            "cwd": str(self.main_workspace),
            "hook_event_name": "SessionStart",
            "name": "test",
        }
        stdout, stderr, rc = self._run_hook(payload)
        self.assertEqual(rc, 1)
        self.assertEqual(stdout, "")

    def test_run_as_claude_hook_missing_cwd(self):
        """Missing cwd field causes exit 1"""
        payload = {
            "session_id": "test-session",
            "hook_event_name": "WorktreeCreate",
            "name": "test",
        }
        stdout, stderr, rc = self._run_hook(payload)
        self.assertEqual(rc, 1)
        self.assertEqual(stdout, "")

    def test_run_as_claude_hook_empty_name(self):
        """Empty/missing name still works with default branch name"""
        payload = {
            "session_id": "test-session",
            "cwd": str(self.main_workspace),
            "hook_event_name": "WorktreeCreate",
        }
        stdout, stderr, rc = self._run_hook(payload)
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stderr: {stderr}")
        # stdout must contain exactly one line: the absolute worktree path
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 1, f"Expected exactly one line on stdout, got {len(lines)}: {lines}")
        worktree_path = Path(lines[0])
        self.assertTrue(worktree_path.is_absolute())
        self.assertTrue(worktree_path.exists())

    def test_cwd_override_in_init(self):
        """cwd_override sets main_workspace correctly"""
        args = argparse.Namespace(
            prompt=[], branch=None, worktree=None, base_branch=None,
            agent_user=None, copy_staged=True,
            copy_modified=False, copy_untracked=False,
            worktree_parent_dir=str(self.temp_dir), verbose=False,
            cwd_override=str(self.main_workspace),
        )
        creator = GitWorktreeCreator(args)
        self.assertEqual(creator.main_workspace, self.main_workspace)

    def test_cwd_override_not_set(self):
        """No cwd_override falls back to Path.cwd() (backward compat)"""
        args = argparse.Namespace(
            prompt=[], branch=None, worktree=None, base_branch=None,
            agent_user=None, copy_staged=True,
            copy_modified=False, copy_untracked=False,
            worktree_parent_dir=str(self.temp_dir), verbose=False,
        )
        creator = GitWorktreeCreator(args)
        self.assertEqual(creator.main_workspace, Path.cwd())


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