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
Test suite for update-task command in task_list_md.py
Tests all functionality for updating task dependencies and requirements
"""

import unittest
import subprocess
import os
import tempfile
import shutil
from pathlib import Path


class TestUpdateTaskCommand(unittest.TestCase):
    """Test suite for update-task command functionality"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with paths and fixtures"""
        cls.script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts" / "task_list_md.py"
        cls.fixtures_dir = Path(__file__).parent / "fixtures"
        cls.complex_tasks = cls.fixtures_dir / "complex_tasks.md"

        # Ensure script exists
        if not cls.script_path.exists():
            raise FileNotFoundError(f"Script not found: {cls.script_path}")

    def setUp(self):
        """Set up each test with temporary working directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_tasks.md"

        # Create a test file with sample tasks
        test_content = """# Test Tasks

- [x] 1. Completed task
  Basic completed task for testing

- [ ] 2. Pending task with requirements
  _Requirements: REQ1, REQ2_

- [-] 3. In-progress task with dependencies
  _Dependencies: 1_

- [ ] 3.1. Sub-task of in-progress task
  First sub-task
  _Dependencies: 3_

- [ ] 3.2. Second sub-task
  Second sub-task
  _Requirements: REQ3_
  _Dependencies: 3.1_

- [+] 4. Review task
  Task in review status

- [*] 5. Deferred task
  Task that has been deferred
"""
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)

    def run_command(self, *args, expect_success=True):
        """Helper to run CLI command and return result"""
        cmd = ["python3", str(self.script_path)] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.temp_dir
        )

        if expect_success and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}")
        elif not expect_success and result.returncode == 0:
            self.fail(f"Command should have failed: {' '.join(cmd)}\nStdout: {result.stdout}")

        return result

    def read_task_file(self):
        """Helper to read the test task file"""
        with open(self.test_file, 'r', encoding='utf-8') as f:
            return f.read()

    def test_add_dependencies(self):
        """Test adding dependencies to a task"""
        # Add dependency to task 4
        result = self.run_command("update-task", str(self.test_file), "4", "--add-dependencies", "1", "2")
        self.assertIn("Updated task '4'", result.stdout)
        self.assertIn("dependencies: [] -> ['1', '2']", result.stdout)

        # Verify the file was updated
        content = self.read_task_file()
        self.assertIn("- [+] 4. Review task", content)
        self.assertIn("_Dependencies: 1, 2_", content)

    def test_add_requirements(self):
        """Test adding requirements to a task"""
        # Add requirements to task 1
        result = self.run_command("update-task", str(self.test_file), "1", "--add-requirements", "REQ_NEW", "REQ_EXTRA")
        self.assertIn("Updated task '1'", result.stdout)
        self.assertIn("requirements: [] -> ['REQ_NEW', 'REQ_EXTRA']", result.stdout)

        # Verify the file was updated
        content = self.read_task_file()
        self.assertIn("_Requirements: REQ_NEW, REQ_EXTRA_", content)

    def test_remove_dependencies(self):
        """Test removing dependencies from a task"""
        # Remove dependency from task 3 (which has dependency on 1)
        result = self.run_command("update-task", str(self.test_file), "3", "--remove-dependencies", "1")
        self.assertIn("Updated task '3'", result.stdout)
        self.assertIn("dependencies: ['1'] -> []", result.stdout)

        # Verify the file was updated (no Dependencies line should remain)
        content = self.read_task_file()
        # Check that the task line is there but Dependencies line is removed
        lines = content.split('\n')
        task_3_found = False
        for i, line in enumerate(lines):
            if "- [-] 3. In-progress task with dependencies" in line:
                task_3_found = True
                # Check the next few lines don't contain Dependencies
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip().startswith("- "):  # Next task
                        break
                    self.assertNotIn("_Dependencies:", lines[j])
                break
        self.assertTrue(task_3_found, "Task 3 not found in file")

    def test_remove_requirements(self):
        """Test removing requirements from a task"""
        # Remove one requirement from task 2 (which has REQ1, REQ2)
        result = self.run_command("update-task", str(self.test_file), "2", "--remove-requirements", "REQ1")
        self.assertIn("Updated task '2'", result.stdout)
        self.assertIn("requirements: ['REQ1', 'REQ2'] -> ['REQ2']", result.stdout)

        # Verify the file was updated
        content = self.read_task_file()
        self.assertIn("_Requirements: REQ2_", content)
        self.assertNotIn("_Requirements: REQ1, REQ2_", content)

    def test_clear_dependencies(self):
        """Test clearing all dependencies from a task"""
        # Clear dependencies from task 3.2 (which has dependency on 3.1)
        result = self.run_command("update-task", str(self.test_file), "3.2", "--clear-dependencies")
        self.assertIn("Updated task '3.2'", result.stdout)
        self.assertIn("dependencies: ['3.1'] -> []", result.stdout)

        # Verify the file was updated
        content = self.read_task_file()
        lines = content.split('\n')
        task_found = False
        for i, line in enumerate(lines):
            if "- [ ] 3.2. Second sub-task" in line:
                task_found = True
                # Check the next few lines don't contain Dependencies
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip().startswith("- "):  # Next task
                        break
                    self.assertNotIn("_Dependencies:", lines[j])
                break
        self.assertTrue(task_found, "Task 3.2 not found in file")

    def test_clear_requirements(self):
        """Test clearing all requirements from a task"""
        # Clear requirements from task 2 (which has REQ1, REQ2)
        result = self.run_command("update-task", str(self.test_file), "2", "--clear-requirements")
        self.assertIn("Updated task '2'", result.stdout)
        self.assertIn("requirements: ['REQ1', 'REQ2'] -> []", result.stdout)

        # Verify the file was updated
        content = self.read_task_file()
        lines = content.split('\n')
        task_found = False
        for i, line in enumerate(lines):
            if "- [ ] 2. Pending task with requirements" in line:
                task_found = True
                # Check the next few lines don't contain Requirements
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip().startswith("- "):  # Next task
                        break
                    self.assertNotIn("_Requirements:", lines[j])
                break
        self.assertTrue(task_found, "Task 2 not found in file")

    def test_combined_operations(self):
        """Test combining add and remove operations"""
        # Add and remove different dependencies and requirements
        result = self.run_command(
            "update-task", str(self.test_file), "2",
            "--add-dependencies", "1",
            "--remove-requirements", "REQ1",
            "--add-requirements", "REQ_NEW"
        )
        self.assertIn("Updated task '2'", result.stdout)
        self.assertIn("dependencies: [] -> ['1']", result.stdout)
        self.assertIn("requirements: ['REQ1', 'REQ2'] -> ['REQ2', 'REQ_NEW']", result.stdout)

        # Verify the file was updated
        content = self.read_task_file()
        self.assertIn("_Requirements: REQ2, REQ_NEW_", content)
        self.assertIn("_Dependencies: 1_", content)

    def test_no_changes(self):
        """Test when no actual changes are made"""
        # Try to add a dependency that already exists
        result = self.run_command("update-task", str(self.test_file), "3", "--add-dependencies", "1")
        self.assertIn("No changes made to task '3'", result.stdout)

    def test_error_nonexistent_task(self):
        """Test error when trying to update non-existent task"""
        result = self.run_command("update-task", str(self.test_file), "99", "--add-dependencies", "1", expect_success=False)
        self.assertIn("Error: Task '99' not found", result.stdout)

    def test_error_nonexistent_dependency(self):
        """Test error when trying to add non-existent dependency"""
        result = self.run_command("update-task", str(self.test_file), "2", "--add-dependencies", "99", expect_success=False)
        self.assertIn("Error: Dependency '99' does not exist", result.stdout)

    def test_error_self_dependency(self):
        """Test error when trying to add self as dependency"""
        result = self.run_command("update-task", str(self.test_file), "2", "--add-dependencies", "2", expect_success=False)
        self.assertIn("Error: Task '2' cannot depend on itself", result.stdout)

    def test_error_circular_dependency(self):
        """Test error when trying to create circular dependency"""
        # Task 3.1 depends on 3, so making 3 depend on 3.1 would create a circle
        result = self.run_command("update-task", str(self.test_file), "3", "--add-dependencies", "3.1", expect_success=False)
        self.assertIn("Error: Adding dependency '3.1' would create a circular dependency", result.stdout)

    def test_error_remove_nonexistent_dependency(self):
        """Test error when trying to remove non-existent dependency"""
        result = self.run_command("update-task", str(self.test_file), "2", "--remove-dependencies", "1", expect_success=False)
        self.assertIn("Error: Dependency '1' is not currently in task '2'", result.stdout)

    def test_error_remove_nonexistent_requirement(self):
        """Test error when trying to remove non-existent requirement"""
        result = self.run_command("update-task", str(self.test_file), "1", "--remove-requirements", "REQ1", expect_success=False)
        self.assertIn("Error: Requirement 'REQ1' is not currently in task '1'", result.stdout)

    def test_error_conflicting_clear_and_add(self):
        """Test error when using clear with add operations"""
        result = self.run_command(
            "update-task", str(self.test_file), "2",
            "--clear-dependencies", "--add-dependencies", "1",
            expect_success=False
        )
        self.assertIn("Error: Cannot use --clear-dependencies with --add-dependencies", result.stdout)

        result = self.run_command(
            "update-task", str(self.test_file), "2",
            "--clear-requirements", "--add-requirements", "REQ1",
            expect_success=False
        )
        self.assertIn("Error: Cannot use --clear-requirements with --add-requirements", result.stdout)

    def test_error_conflicting_clear_and_remove(self):
        """Test error when using clear with remove operations"""
        result = self.run_command(
            "update-task", str(self.test_file), "3",
            "--clear-dependencies", "--remove-dependencies", "1",
            expect_success=False
        )
        self.assertIn("Error: Cannot use --clear-dependencies with --add-dependencies or --remove-dependencies", result.stdout)

    def test_preserve_other_properties(self):
        """Test that other task properties are preserved during update"""
        # Update task 3 (which is in-progress status)
        result = self.run_command("update-task", str(self.test_file), "3", "--add-requirements", "REQ_TEST")
        self.assertIn("Updated task '3'", result.stdout)

        # Verify the status and description are preserved
        content = self.read_task_file()
        self.assertIn("- [-] 3. In-progress task with dependencies", content)  # Status preserved
        self.assertIn("_Requirements: REQ_TEST_", content)

    def test_hierarchical_task_update(self):
        """Test updating hierarchical (sub) tasks"""
        # Update sub-task 3.1
        result = self.run_command("update-task", str(self.test_file), "3.1", "--add-requirements", "SUB_REQ")
        self.assertIn("Updated task '3.1'", result.stdout)

        # Verify the hierarchical structure is preserved
        content = self.read_task_file()
        self.assertIn("- [ ] 3.1. Sub-task of in-progress task", content)
        self.assertIn("_Requirements: SUB_REQ_", content)


if __name__ == '__main__':
    unittest.main()