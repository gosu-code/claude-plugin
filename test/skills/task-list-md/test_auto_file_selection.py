#!/usr/bin/env python3
"""
Test suite for task_list_md.py auto file selection functionality
Tests the new optional file argument with .tasks.local.json auto-selection
"""

import unittest
import subprocess
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta


class TestAutoFileSelection(unittest.TestCase):
    """Test suite for auto file selection functionality"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with paths and fixtures"""
        cls.script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts" / "task_list_md.py"
        cls.fixtures_dir = Path(__file__).parent / "fixtures"
        cls.simple_tasks = cls.fixtures_dir / "simple_tasks.md"
        cls.complex_tasks = cls.fixtures_dir / "complex_tasks.md"

        # Ensure script exists
        if not cls.script_path.exists():
            raise FileNotFoundError(f"Script not found: {cls.script_path}")

    def setUp(self):
        """Set up each test with temporary working directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create test task files
        self.test_tasks1 = Path(self.temp_dir) / "tasks1.md"
        self.test_tasks2 = Path(self.temp_dir) / "tasks2.md"
        shutil.copy2(self.simple_tasks, self.test_tasks1)
        shutil.copy2(self.complex_tasks, self.test_tasks2)

    def tearDown(self):
        """Clean up temporary directory and restore working directory"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)

    def run_command(self, *args, expect_success=True):
        """Helper to run CLI command and return result"""
        cmd = ["python3", str(self.script_path)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if expect_success and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}\nStdout: {result.stdout}")

        return result

    def create_tasks_local_json(self, file_entries):
        """Helper to create .tasks.local.json with given entries"""
        tasks_local_path = Path(self.temp_dir) / ".tasks.local.json"
        with open(tasks_local_path, 'w') as f:
            json.dump(file_entries, f, indent=2)
        return tasks_local_path

    def test_auto_selection_most_recent_file(self):
        """Test that the most recently modified file is automatically selected"""
        # Create .tasks.local.json with two entries, tasks2 more recent
        now = datetime.now()
        older_time = (now - timedelta(hours=1)).isoformat()
        newer_time = now.isoformat()

        self.create_tasks_local_json({
            str(self.test_tasks1): {
                "total_tasks": 3,
                "completed": 1,
                "in_progress": 0,
                "pending": 2,
                "review": 0,
                "deferred": 0,
                "percentage": 33.33,
                "last_modified": older_time,
                "tasks": {}
            },
            str(self.test_tasks2): {
                "total_tasks": 5,
                "completed": 2,
                "in_progress": 1,
                "pending": 2,
                "review": 0,
                "deferred": 0,
                "percentage": 40.0,
                "last_modified": newer_time,
                "tasks": {}
            }
        })

        # Run command without file argument
        result = self.run_command("list-tasks")

        # Should auto-select tasks2.md (the more recent one)
        self.assertIn(f"Auto-selected task file: {self.test_tasks2}", result.stdout)
        self.assertIn("Setup phase", result.stdout)  # Content from complex_tasks fixture

    def test_explicit_file_path_overrides_auto_selection(self):
        """Test that explicitly providing a file path overrides auto-selection"""
        # Create .tasks.local.json
        now = datetime.now()
        self.create_tasks_local_json({
            str(self.test_tasks1): {
                "total_tasks": 3,
                "last_modified": now.isoformat(),
                "tasks": {}
            },
            str(self.test_tasks2): {
                "total_tasks": 5,
                "last_modified": (now + timedelta(hours=1)).isoformat(),
                "tasks": {}
            }
        })

        # Run command with explicit file path (should override auto-selection)
        result = self.run_command("list-tasks", str(self.test_tasks1))

        # Should NOT show auto-selection message
        self.assertNotIn("Auto-selected task file:", result.stdout)
        # Should use the specified file (tasks1)
        self.assertIn("Completed task", result.stdout)  # Content from simple_tasks fixture

    def test_error_when_no_tasks_local_json(self):
        """Test error when .tasks.local.json doesn't exist and no file provided"""
        # Ensure no .tasks.local.json file exists
        tasks_local_path = Path(self.temp_dir) / ".tasks.local.json"
        if tasks_local_path.exists():
            tasks_local_path.unlink()

        # Run command without file argument
        result = self.run_command("list-tasks", expect_success=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn(".tasks.local.json file not found", result.stderr)
        self.assertIn("Please provide a valid file path to a tasks.md file", result.stderr)

    def test_error_when_tasks_local_json_empty(self):
        """Test error when .tasks.local.json is empty and no file provided"""
        # Create empty .tasks.local.json
        self.create_tasks_local_json({})

        # Run command without file argument
        result = self.run_command("list-tasks", expect_success=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn(".tasks.local.json is empty", result.stderr)
        self.assertIn("Please provide a valid file path to a tasks.md file", result.stderr)

    def test_error_when_tasks_local_json_malformed(self):
        """Test error when .tasks.local.json contains invalid JSON"""
        # Create malformed .tasks.local.json
        tasks_local_path = Path(self.temp_dir) / ".tasks.local.json"
        with open(tasks_local_path, 'w') as f:
            f.write("{ invalid json content")

        # Run command without file argument
        result = self.run_command("list-tasks", expect_success=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not read .tasks.local.json", result.stderr)
        self.assertIn("Please provide a valid file path to a tasks.md file", result.stderr)

    def test_error_when_no_valid_entries_in_tasks_local_json(self):
        """Test error when .tasks.local.json has no valid entries with last_modified"""
        # Create .tasks.local.json with invalid entries
        self.create_tasks_local_json({
            "invalid_entry": "not_a_dict",
            str(self.test_tasks1): {
                "total_tasks": 3,
                # Missing last_modified
                "tasks": {}
            },
            str(self.test_tasks2): {
                "total_tasks": 5,
                "last_modified": "invalid_timestamp",
                "tasks": {}
            }
        })

        # Run command without file argument
        result = self.run_command("list-tasks", expect_success=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("No valid task files found in .tasks.local.json", result.stderr)
        self.assertIn("Please provide a valid file path to a tasks.md file", result.stderr)

    def test_auto_selection_with_other_commands(self):
        """Test auto-selection works with commands other than list-tasks"""
        # Create .tasks.local.json
        now = datetime.now()
        self.create_tasks_local_json({
            str(self.test_tasks1): {
                "total_tasks": 3,
                "completed": 1,
                "in_progress": 0,
                "pending": 2,
                "review": 0,
                "deferred": 0,
                "percentage": 33.33,
                "last_modified": now.isoformat(),
                "tasks": {}
            }
        })

        # Test show-progress command
        result = self.run_command("show-progress")
        self.assertIn(f"Auto-selected task file: {self.test_tasks1}", result.stdout)
        self.assertIn("Progress Report for:", result.stdout)

        # Test get-next-task command
        result = self.run_command("get-next-task")
        self.assertIn(f"Auto-selected task file: {self.test_tasks1}", result.stdout)

    def test_auto_selection_with_track_progress_commands(self):
        """Test auto-selection works with track-progress commands"""
        # Create .tasks.local.json
        now = datetime.now()
        self.create_tasks_local_json({
            str(self.test_tasks1): {
                "total_tasks": 3,
                "completed": 1,
                "in_progress": 0,
                "pending": 2,
                "review": 0,
                "deferred": 0,
                "percentage": 33.33,
                "last_modified": now.isoformat(),
                "tasks": {}
            }
        })

        # Test track-progress check command
        result = self.run_command("track-progress", "check")
        self.assertIn(f"Auto-selected task file: {self.test_tasks1}", result.stdout)
        self.assertIn("All completion conditions are satisfied", result.stdout)


if __name__ == '__main__':
    unittest.main()