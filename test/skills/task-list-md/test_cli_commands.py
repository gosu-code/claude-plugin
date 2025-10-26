#!/usr/bin/env python3
"""
Test suite for task_list_md.py CLI commands
Tests all major CLI functionality based on comprehensive manual testing
"""

import unittest
import subprocess
import os
import json
import tempfile
import shutil
from pathlib import Path


class TestTaskListMDCLI(unittest.TestCase):
    """Test suite for task_list_md.py CLI commands"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with paths and fixtures"""
        cls.script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts" / "task_list_md.py"
        cls.fixtures_dir = Path(__file__).parent / "fixtures"
        cls.simple_tasks = cls.fixtures_dir / "simple_tasks.md"
        cls.complex_tasks = cls.fixtures_dir / "complex_tasks.md"
        cls.empty_tasks = cls.fixtures_dir / "empty_tasks.md"

        # Ensure script exists
        if not cls.script_path.exists():
            raise FileNotFoundError(f"Script not found: {cls.script_path}")

    def setUp(self):
        """Set up each test with temporary working directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_simple = Path(self.temp_dir) / "test_simple.md"
        self.test_complex = Path(self.temp_dir) / "test_complex.md"
        self.test_empty = Path(self.temp_dir) / "test_empty.md"

        # Copy fixtures to temp directory
        shutil.copy2(self.simple_tasks, self.test_simple)
        shutil.copy2(self.complex_tasks, self.test_complex)
        shutil.copy2(self.empty_tasks, self.test_empty)

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)

    def run_command(self, *args, expect_success=True):
        """Helper to run CLI command and return result"""
        cmd = ["python3", str(self.script_path)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if expect_success and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}")

        return result

    def test_help_command(self):
        """Test help command displays usage information"""
        result = self.run_command("--help")
        self.assertIn("Task List MD CLI", result.stdout)
        self.assertIn("list-tasks", result.stdout)
        self.assertIn("show-task", result.stdout)
        self.assertIn("set-status", result.stdout)

    def test_command_help(self):
        """Test specific command help"""
        result = self.run_command("list-tasks", "--help")
        self.assertIn("list-tasks", result.stdout)
        self.assertIn("file", result.stdout)

    def test_list_tasks_simple(self):
        """Test list-tasks command with simple file"""
        result = self.run_command("list-tasks", str(self.test_simple))

        # Check for task IDs and statuses
        self.assertIn("ID 1 [done]", result.stdout)
        self.assertIn("ID 2 [pending]", result.stdout)
        self.assertIn("ID 3 [in-progress]", result.stdout)
        self.assertIn("ID 3.1 [pending]", result.stdout)
        self.assertIn("ID 3.2 [pending]", result.stdout)
        self.assertIn("ID 4 [review]", result.stdout)
        self.assertIn("ID 5 [deferred]", result.stdout)

    def test_list_tasks_complex(self):
        """Test list-tasks command with complex file"""
        result = self.run_command("list-tasks", str(self.test_complex))

        # Check hierarchical structure
        self.assertIn("ID 1 [done]", result.stdout)
        self.assertIn("ID 2 [done]", result.stdout)
        self.assertIn("ID 2.1 [done]", result.stdout)
        self.assertIn("ID 2.2 [done]", result.stdout)
        self.assertIn("ID 2.3 [done]", result.stdout)
        self.assertIn("ID 3 [pending]", result.stdout)
        self.assertIn("ID 3.1 [pending]", result.stdout)
        self.assertIn("ID 3.2 [pending]", result.stdout)

    def test_list_tasks_empty_file(self):
        """Test list-tasks command with empty file"""
        result = self.run_command("list-tasks", str(self.test_empty))
        self.assertIn("No tasks found in the file", result.stdout)

    def test_show_task_root(self):
        """Test show-task command for root task"""
        result = self.run_command("show-task", str(self.test_simple), "1")

        self.assertIn("Task ID: 1", result.stdout)
        self.assertIn("Status: done", result.stdout)
        self.assertIn("Description: Completed task", result.stdout)
        self.assertIn("Line Number:", result.stdout)
        self.assertIn("Full Content:", result.stdout)

    def test_show_task_with_requirements(self):
        """Test show-task command for task with requirements"""
        result = self.run_command("show-task", str(self.test_simple), "2")

        self.assertIn("Task ID: 2", result.stdout)
        self.assertIn("Status: pending", result.stdout)
        self.assertIn("Requirements: REQ1, REQ2", result.stdout)

    def test_show_task_with_dependencies(self):
        """Test show-task command for task with dependencies"""
        result = self.run_command("show-task", str(self.test_simple), "3")

        self.assertIn("Task ID: 3", result.stdout)
        self.assertIn("Dependencies: 1", result.stdout)
        self.assertIn("Sub-tasks (2):", result.stdout)

    def test_show_task_subtask(self):
        """Test show-task command for sub-task"""
        result = self.run_command("show-task", str(self.test_simple), "3.1")

        self.assertIn("Task ID: 3.1", result.stdout)
        self.assertIn("Parent Task: 3 [in-progress]", result.stdout)

    def test_set_status_single(self):
        """Test set-status command for single task"""
        result = self.run_command("set-status", str(self.test_simple), "2", "in-progress")

        self.assertIn("Task '2' status changed from 'pending' to 'in-progress'", result.stdout)

        # Verify the change
        verify_result = self.run_command("show-task", str(self.test_simple), "2")
        self.assertIn("Status: in-progress", verify_result.stdout)

    def test_set_status_bulk(self):
        """Test set-status command for multiple tasks"""
        # First set parent task to in-progress so sub-tasks can be changed
        self.run_command("set-status", str(self.test_complex), "3", "in-progress")

        result = self.run_command("set-status", str(self.test_complex), "3.1", "3.2", "done")

        self.assertIn("Updated 2 task(s) to done", result.stdout)

        # Verify the changes
        verify_result = self.run_command("show-task", str(self.test_complex), "3.1")
        self.assertIn("Status: done", verify_result.stdout)

    def test_add_task_simple(self):
        """Test add-task command"""
        result = self.run_command("add-task", str(self.test_simple), "6", "New test task",
                                 "--dependencies", "1", "--requirements", "TEST1")

        self.assertIn("Added task '6': New test task", result.stdout)

        # Verify the task was added and can be found
        verify_result = self.run_command("show-task", str(self.test_simple), "6")
        self.assertIn("Task ID: 6", verify_result.stdout)
        self.assertIn("New test task", verify_result.stdout)
        self.assertIn("Dependencies: 1", verify_result.stdout)
        self.assertIn("Requirements: TEST1", verify_result.stdout)

    def test_add_subtask(self):
        """Test add-task command for sub-task"""
        result = self.run_command("add-task", str(self.test_simple), "3.3", "New sub-task",
                                 "--dependencies", "3.1")

        self.assertIn("Added task '3.3': New sub-task", result.stdout)

        # Verify the sub-task was added
        verify_result = self.run_command("show-task", str(self.test_simple), "3.3")
        self.assertIn("Task ID: 3.3", verify_result.stdout)
        self.assertIn("Parent Task: 3", verify_result.stdout)

    def test_add_task_formatting(self):
        """Test that add-task creates proper formatting with newlines"""
        # Add a task to test formatting
        result = self.run_command("add-task", str(self.test_simple), "6", "Formatting test task")
        self.assertIn("Added task '6': Formatting test task", result.stdout)

        # Read the file directly to check formatting
        with open(self.test_simple, 'r', encoding='utf-8') as f:
            content = f.read()

        # The new task should be properly separated from the previous content
        # and should be on its own line
        self.assertIn("\n- [ ] 6. Formatting test task\n", content)

        # The task should not be concatenated to the previous line
        self.assertNotIn("deferred- [ ] 6.", content)

        # Verify the task can be parsed and found
        verify_result = self.run_command("show-task", str(self.test_simple), "6")
        self.assertIn("Task ID: 6", verify_result.stdout)

    def test_delete_task(self):
        """Test delete-task command"""
        # Test deleting an existing task
        result = self.run_command("delete-task", str(self.test_simple), "4")
        self.assertIn("Deleted task(s): '4'", result.stdout)

        # Verify it's gone
        verify_result = self.run_command("show-task", str(self.test_simple), "4", expect_success=False)
        self.assertIn("Error: Task '4' not found", verify_result.stdout)

    def test_get_next_task(self):
        """Test get-next-task command"""
        result = self.run_command("get-next-task", str(self.test_complex))

        self.assertIn("Next task to work on:", result.stdout)
        self.assertIn("ID 3", result.stdout)  # Should be task 3 based on dependencies

    def test_filter_tasks_by_status(self):
        """Test filter-tasks command by status"""
        result = self.run_command("filter-tasks", str(self.test_simple), "--status", "pending")

        self.assertIn("Filtered Tasks", result.stdout)
        self.assertIn("Status: pending", result.stdout)
        self.assertIn("ID 2 [pending]", result.stdout)
        self.assertIn("ID 3.1 [pending]", result.stdout)
        self.assertIn("ID 3.2 [pending]", result.stdout)

    def test_filter_tasks_by_requirements(self):
        """Test filter-tasks command by requirements"""
        result = self.run_command("filter-tasks", str(self.test_simple), "--requirements", "REQ1")

        self.assertIn("Filtered Tasks", result.stdout)
        self.assertIn("Requirements: REQ1", result.stdout)
        self.assertIn("ID 2 [pending]", result.stdout)

    def test_search_tasks(self):
        """Test search-tasks command"""
        result = self.run_command("search-tasks", str(self.test_complex), "documentation")

        self.assertIn("Search Results", result.stdout)
        self.assertIn("Keywords: documentation", result.stdout)
        self.assertIn("ID 4", result.stdout)  # Documentation task

    def test_ready_tasks(self):
        """Test ready-tasks command"""
        result = self.run_command("ready-tasks", str(self.test_complex))

        self.assertIn("Ready Tasks", result.stdout)
        # Task 3 should be ready (dependencies satisfied)
        self.assertIn("ID 3", result.stdout)

    def test_check_dependencies(self):
        """Test check-dependencies command"""
        result = self.run_command("check-dependencies", str(self.test_simple))

        self.assertIn("All dependencies are valid", result.stdout)

    def test_show_progress(self):
        """Test show-progress command"""
        result = self.run_command("show-progress", str(self.test_simple))

        self.assertIn("Progress Report", result.stdout)
        self.assertIn("Total Tasks:", result.stdout)
        self.assertIn("Completed (done+review+deferred):", result.stdout)
        self.assertIn("Done:", result.stdout)
        self.assertIn("Review:", result.stdout)
        self.assertIn("Deferred:", result.stdout)
        self.assertIn("Pending:", result.stdout)
        self.assertIn("Completion Percentage:", result.stdout)

    def test_export_to_stdout(self):
        """Test export command to stdout"""
        result = self.run_command("export", str(self.test_simple))

        # Should be valid JSON
        try:
            data = json.loads(result.stdout)
            self.assertIn("file_path", data)
            self.assertIn("export_timestamp", data)
            self.assertIn("statistics", data)
            self.assertIn("tasks", data)
        except json.JSONDecodeError:
            self.fail("Export output is not valid JSON")

    def test_export_to_file(self):
        """Test export command to file"""
        output_file = Path(self.temp_dir) / "export_test.json"
        result = self.run_command("export", str(self.test_simple), "--output", str(output_file))

        self.assertIn(f"Exported task data to {output_file}", result.stdout)
        self.assertTrue(output_file.exists())

        # Verify file content
        with open(output_file, 'r') as f:
            data = json.load(f)
            self.assertIn("file_path", data)
            self.assertIn("tasks", data)

    def test_update_task_command(self):
        """Test update-task command integration"""
        # Test adding dependencies and requirements
        result = self.run_command("update-task", str(self.test_simple), "2",
                                "--add-dependencies", "1",
                                "--add-requirements", "NEW_REQ")
        self.assertIn("Updated task '2'", result.stdout)

        # Test error cases
        result = self.run_command("update-task", str(self.test_simple), "99",
                                "--add-dependencies", "1", expect_success=False)
        self.assertIn("Error: Task '99' not found", result.stdout)

        # Test conflicting arguments
        result = self.run_command("update-task", str(self.test_simple), "2",
                                "--clear-dependencies", "--add-dependencies", "1",
                                expect_success=False)
        self.assertIn("Error: Cannot use --clear-dependencies with --add-dependencies", result.stdout)


if __name__ == "__main__":
    unittest.main()