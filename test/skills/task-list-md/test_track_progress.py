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
Test suite for track-progress functionality in task_list_md.py
Tests all track-progress sub-commands and their edge cases
"""

import unittest
import subprocess
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Import the ProgressTracker class for direct testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts"))
from task_list_md import ProgressTracker


class TestTrackProgress(unittest.TestCase):
    """Test suite for track-progress commands"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with paths and fixtures"""
        cls.script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts" / "task_list_md.py"
        cls.fixtures_dir = Path(__file__).parent / "fixtures"
        cls.simple_tasks = cls.fixtures_dir / "simple_tasks.md"

        # Ensure script exists
        if not cls.script_path.exists():
            raise FileNotFoundError(f"Script not found: {cls.script_path}")

    def setUp(self):
        """Set up each test with temporary working directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_tasks = Path(self.temp_dir) / "test_tasks.md"
        self.progress_file = Path(self.temp_dir) / ".tasks.local.json"

        # Copy fixture to temp directory
        shutil.copy2(self.simple_tasks, self.test_tasks)

        # Change to temp directory to ensure .tasks.local.json is created there
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)

    def run_command(self, *args, expect_success=True, expected_exit_code=None):
        """Helper to run CLI command and return result"""
        cmd = ["python3", str(self.script_path)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if expected_exit_code is not None:
            if result.returncode != expected_exit_code:
                self.fail(f"Expected exit code {expected_exit_code}, got {result.returncode}\n"
                         f"Command: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}")
        elif expect_success and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}")

        return result

    def load_progress_data(self):
        """Load progress data from JSON file"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def test_track_progress_help(self):
        """Test track-progress help command displays usage information"""
        result = self.run_command("track-progress", "--help")
        self.assertIn("track-progress", result.stdout)
        self.assertIn("add", result.stdout)
        self.assertIn("check", result.stdout)
        self.assertIn("clear", result.stdout)

    def test_track_progress_add_help(self):
        """Test track-progress add help"""
        result = self.run_command("track-progress", "add", "--help")
        self.assertIn("track-progress add", result.stdout)
        self.assertIn("--valid-for", result.stdout)
        self.assertIn("--complete-more", result.stdout)

    def test_add_tracking_condition_basic(self):
        """Test adding a basic tracking condition"""
        result = self.run_command("track-progress", "add", str(self.test_tasks), "1", "2")

        self.assertIn("Added tracking condition for tasks: 1, 2", result.stdout)
        self.assertIn("Valid until:", result.stdout)

        # Check JSON file was created with tracking data
        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        self.assertIn(abs_path, data)
        self.assertIn("tracking", data[abs_path])
        self.assertEqual(len(data[abs_path]["tracking"]), 1)

        condition = data[abs_path]["tracking"][0]
        self.assertEqual(condition["tasks_to_complete"], ["1", "2"])
        self.assertIn("valid_before", condition)

    def test_add_with_hours_duration(self):
        """Test adding condition with hours duration"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "1", "--valid-for", "2h")

        self.assertIn("Added tracking condition", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        # Check that valid_before is approximately 2 hours from now
        valid_before = datetime.fromisoformat(condition["valid_before"])
        expected_time = datetime.now() + timedelta(hours=2)
        time_diff = abs((valid_before - expected_time).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute tolerance

    def test_add_with_minutes_duration(self):
        """Test adding condition with minutes duration"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "1", "--valid-for", "30m")

        self.assertIn("Added tracking condition", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        # Check that valid_before is approximately 30 minutes from now
        valid_before = datetime.fromisoformat(condition["valid_before"])
        expected_time = datetime.now() + timedelta(minutes=30)
        time_diff = abs((valid_before - expected_time).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute tolerance

    def test_add_with_seconds_duration(self):
        """Test adding condition with seconds duration"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "1", "--valid-for", "45s")

        self.assertIn("Added tracking condition", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        # Check that valid_before is approximately 45 seconds from now
        valid_before = datetime.fromisoformat(condition["valid_before"])
        expected_time = datetime.now() + timedelta(seconds=45)
        time_diff = abs((valid_before - expected_time).total_seconds())
        self.assertLess(time_diff, 5)  # Within 5 seconds tolerance

    def test_add_with_no_suffix_duration(self):
        """Test adding condition with no suffix (should default to seconds)"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "1", "--valid-for", "60")

        self.assertIn("Added tracking condition", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        # Check that valid_before is approximately 60 seconds from now
        valid_before = datetime.fromisoformat(condition["valid_before"])
        expected_time = datetime.now() + timedelta(seconds=60)
        time_diff = abs((valid_before - expected_time).total_seconds())
        self.assertLess(time_diff, 5)  # Within 5 seconds tolerance

    def test_add_with_complete_more(self):
        """Test adding condition with complete-more option"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "2", "--complete-more", "3")

        self.assertIn("Added tracking condition", result.stdout)
        self.assertIn("Expected total completed tasks:", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        self.assertIn("expect_completed", condition)
        # Current completed tasks (from simple_tasks.md: tasks 1, 4, 5 are completed - done/review/deferred) + 3 more = 6
        self.assertEqual(condition["expect_completed"], 6)

    def test_add_default_valid_for(self):
        """Test adding condition with default valid-for duration (2h)"""
        result = self.run_command("track-progress", "add", str(self.test_tasks), "1")

        self.assertIn("Added tracking condition", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        # Check that valid_before is approximately 1 hour from now (default)
        valid_before = datetime.fromisoformat(condition["valid_before"])
        expected_time = datetime.now() + timedelta(hours=2)
        time_diff = abs((valid_before - expected_time).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute tolerance

    def test_add_invalid_task_ids(self):
        """Test adding condition with non-existent task IDs"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "999", expect_success=False, expected_exit_code=1)

        self.assertIn("Task '999' not found", result.stderr)

    def test_add_invalid_duration_format(self):
        """Test adding condition with invalid duration format"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "1", "--valid-for", "invalid",
                                 expect_success=False, expected_exit_code=1)

        self.assertIn("Invalid duration format", result.stderr)

    def test_check_conditions_all_met(self):
        """Test checking conditions when all are satisfied"""
        # Add tracking condition for task 1 (which is already done)
        self.run_command("track-progress", "add", str(self.test_tasks), "1")

        # Check conditions
        result = self.run_command("track-progress", "check", str(self.test_tasks))

        self.assertIn("All completion conditions are satisfied", result.stdout)

    def test_check_conditions_review_status_considered_complete(self):
        """Test that tasks with review status are considered completed"""
        # Add tracking condition for task 4 (which is in review status)
        self.run_command("track-progress", "add", str(self.test_tasks), "4")

        # Check conditions
        result = self.run_command("track-progress", "check", str(self.test_tasks))

        self.assertIn("All completion conditions are satisfied", result.stdout)

    def test_check_conditions_deferred_status_considered_complete(self):
        """Test that tasks with deferred status are considered completed"""
        # Add tracking condition for task 5 (which is deferred)
        self.run_command("track-progress", "add", str(self.test_tasks), "5")

        # Check conditions
        result = self.run_command("track-progress", "check", str(self.test_tasks))

        self.assertIn("All completion conditions are satisfied", result.stdout)

    def test_check_conditions_mixed_completion_statuses(self):
        """Test checking conditions with mixed completion statuses (done, review, deferred)"""
        # Add tracking condition for tasks 1 (done), 4 (review), 5 (deferred)
        self.run_command("track-progress", "add", str(self.test_tasks), "1", "4", "5")

        # Check conditions
        result = self.run_command("track-progress", "check", str(self.test_tasks))

        self.assertIn("All completion conditions are satisfied", result.stdout)

    def test_check_conditions_unmet_tasks(self):
        """Test checking conditions when tasks are not completed"""
        # Add tracking condition for task 2 (which is pending)
        self.run_command("track-progress", "add", str(self.test_tasks), "2")

        # Check conditions
        result = self.run_command("track-progress", "check", str(self.test_tasks),
                                 expect_success=False, expected_exit_code=2)

        self.assertIn("Completion conditions not met", result.stderr)
        self.assertIn("Task '2' is not completed", result.stderr)

    def test_check_conditions_unmet_total_count(self):
        """Test checking conditions when total completed count is insufficient"""
        # Add tracking condition with complete-more that won't be met
        # 3 are already completed, we can ask for up to 4 more (total 7 tasks)
        self.run_command("track-progress", "add", str(self.test_tasks),
                        "1", "--complete-more", "3")

        # Check conditions
        result = self.run_command("track-progress", "check", str(self.test_tasks),
                                 expect_success=False, expected_exit_code=2)

        self.assertIn("Completion conditions not met", result.stderr)
        # 3 tasks are completed (1-done, 4-review, 5-deferred) + 3 more expected = 6 total
        self.assertIn("Expected 6 completed tasks, but only 3 are completed", result.stderr)

    def test_check_expired_conditions_ignored(self):
        """Test that expired conditions are ignored"""
        # Add tracking condition with very short duration
        self.run_command("track-progress", "add", str(self.test_tasks),
                        "2", "--valid-for", "1s")

        # Wait for condition to expire
        import time
        time.sleep(2)

        # Check conditions - should be satisfied because expired condition is ignored
        result = self.run_command("track-progress", "check", str(self.test_tasks))

        self.assertIn("All completion conditions are satisfied", result.stdout)

    def test_check_multiple_conditions(self):
        """Test checking multiple completion conditions"""
        # Add multiple conditions
        self.run_command("track-progress", "add", str(self.test_tasks), "1")  # This should be met
        self.run_command("track-progress", "add", str(self.test_tasks), "2")  # This should not be met

        # Check conditions
        result = self.run_command("track-progress", "check", str(self.test_tasks),
                                 expect_success=False, expected_exit_code=2)

        self.assertIn("Completion conditions not met", result.stderr)
        self.assertIn("Condition 1:", result.stderr)  # Should show details of unmet condition

    def test_clear_with_confirmation_yes(self):
        """Test clearing conditions with user confirmation (yes)"""
        # Add a tracking condition first
        self.run_command("track-progress", "add", str(self.test_tasks), "1")

        # Verify condition was added
        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        self.assertEqual(len(data[abs_path]["tracking"]), 1)

        # Clear with yes confirmation
        result = self.run_command("track-progress", "clear", str(self.test_tasks), "--yes")

        self.assertIn("Cleared 1 tracking condition(s)", result.stdout)

        # Verify conditions were cleared
        data = self.load_progress_data()
        self.assertEqual(len(data[abs_path]["tracking"]), 0)

    def test_clear_no_conditions(self):
        """Test clearing when no conditions exist"""
        result = self.run_command("track-progress", "clear", str(self.test_tasks), "--yes")

        self.assertIn("No completion conditions to clear", result.stdout)

    def test_no_subcommand_error(self):
        """Test error when no sub-command is provided"""
        result = self.run_command("track-progress", str(self.test_tasks),
                                 expect_success=False, expected_exit_code=2)

        # Argparse should show the error about invalid choice
        self.assertIn("invalid choice", result.stderr)

    def test_multiple_task_ids(self):
        """Test adding condition with multiple task IDs"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "1", "3", "4")

        self.assertIn("Added tracking condition for tasks: 1, 3, 4", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        self.assertEqual(condition["tasks_to_complete"], ["1", "3", "4"])

    def test_hierarchical_task_ids(self):
        """Test adding condition with hierarchical task IDs"""
        result = self.run_command("track-progress", "add", str(self.test_tasks),
                                 "3.1", "3.2")

        self.assertIn("Added tracking condition for tasks: 3.1, 3.2", result.stdout)

        data = self.load_progress_data()
        abs_path = str(self.test_tasks.resolve())
        condition = data[abs_path]["tracking"][0]

        self.assertEqual(condition["tasks_to_complete"], ["3.1", "3.2"])

    def test_claude_hook_help(self):
        """Test track-progress check --claude-hook help"""
        result = self.run_command("track-progress", "check", "--help")
        self.assertIn("--claude-hook", result.stdout)
        self.assertIn("Claude hook mode", result.stdout)

    def test_claude_hook_with_stop_hook_active_no_transcript(self):
        """Test Claude hook mode with stop_hook_active but no transcript path"""
        import subprocess
        import json

        # Prepare hook input without transcript_path
        hook_input = {
            "session_id": "test123",
            "hook_event_name": "Stop",
            "stop_hook_active": True
        }

        cmd = ["python3", str(self.script_path), "track-progress", "check", str(self.test_tasks), "--claude-hook"]
        result = subprocess.run(cmd, input=json.dumps(hook_input), text=True, capture_output=True)

        self.assertEqual(result.returncode, 1)
        self.assertIn("No transcript path provided", result.stderr)

    def test_claude_hook_with_stop_hook_active_with_transcript(self):
        """Test Claude hook mode with stop_hook_active and transcript path"""
        import subprocess
        import json
        import tempfile

        # Create a mock transcript file with some hook calls (but not > 3)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"content": "python3 scripts/task_list_md/task_list_md.py track-progress check tasks.md --claude-hook"}\n')
            f.write('{"content": "some other content"}\n')
            f.write('{"content": "python3 scripts/task_list_md/task_list_md.py track-progress check tasks.md --claude-hook"}\n')
            transcript_path = f.name

        try:
            # Prepare hook input with transcript_path
            hook_input = {
                "session_id": "test123",
                "transcript_path": transcript_path,
                "hook_event_name": "Stop",
                "stop_hook_active": True
            }

            # Add a tracking condition first
            self.run_command("track-progress", "add", str(self.test_tasks), "1")

            cmd = ["python3", str(self.script_path), "track-progress", "check", str(self.test_tasks), "--claude-hook"]
            result = subprocess.run(cmd, input=json.dumps(hook_input), text=True, capture_output=True)

            # Should work normally since < 3 hook calls in transcript
            self.assertEqual(result.returncode, 0)
            self.assertIn("All completion conditions are satisfied", result.stdout)

        finally:
            os.unlink(transcript_path)

    def test_claude_hook_infinite_loop_detection(self):
        """Test Claude hook infinite loop detection"""
        import subprocess
        import json
        import tempfile

        # Create a mock transcript file with > 3 hook calls
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(5):  # More than 3
                f.write(f'{{"content": "python3 scripts/task_list_md/task_list_md.py track-progress check tasks.md --claude-hook"}}\n')
            transcript_path = f.name

        try:
            # Prepare hook input with transcript_path
            hook_input = {
                "session_id": "test123",
                "transcript_path": transcript_path,
                "hook_event_name": "Stop",
                "stop_hook_active": True
            }

            cmd = ["python3", str(self.script_path), "track-progress", "check", str(self.test_tasks), "--claude-hook"]
            result = subprocess.run(cmd, input=json.dumps(hook_input), text=True, capture_output=True)

            # Should exit with code 1 due to infinite loop detection
            self.assertEqual(result.returncode, 1)
            self.assertIn("Infinite loop detected", result.stderr)

        finally:
            os.unlink(transcript_path)

    def test_claude_hook_with_stop_hook_false(self):
        """Test Claude hook mode with stop_hook_active: false"""
        import subprocess
        import json

        # Prepare hook input with stop_hook_active: false
        hook_input = {
            "session_id": "test123",
            "hook_event_name": "Stop",
            "stop_hook_active": False
        }

        # Add a condition that should be met
        self.run_command("track-progress", "add", str(self.test_tasks), "1")

        cmd = ["python3", str(self.script_path), "track-progress", "check", str(self.test_tasks), "--claude-hook"]
        result = subprocess.run(cmd, input=json.dumps(hook_input), text=True, capture_output=True)

        # Should work normally since stop_hook_active is false
        self.assertEqual(result.returncode, 0)
        self.assertIn("All completion conditions are satisfied", result.stdout)

    def test_claude_hook_regex_pattern_variations(self):
        """Test the regex pattern matches various command formats"""
        import tempfile

        # Create a mock transcript with various command patterns
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # These should match the pattern
            f.write('{"content": "python3 /path/to/scripts/task_list_md/task_list_md.py track-progress check file.md --claude-hook"}\n')
            f.write('{"content": "python scripts/task_list_md/task_list_md.py track-progress check tasks.md --claude-hook"}\n')
            f.write('{"content": "python3 ./scripts/task_list_md/task_list_md.py track-progress check test.md --valid-for 1h --claude-hook"}\n')
            f.write('{"content": "python3 ../scripts/task_list_md/task_list_md.py track-progress check file.md --claude-hook"}\n')
            f.write('{"content": "Some other unrelated content"}\n')
            transcript_path = f.name

        try:
            # Test the infinite loop detection
            progress_tracker = ProgressTracker()
            is_loop = progress_tracker.detect_infinite_loop(transcript_path)

            # Should detect loop since we have 4 matching patterns > 3
            self.assertTrue(is_loop)

        finally:
            os.unlink(transcript_path)


if __name__ == '__main__':
    unittest.main()