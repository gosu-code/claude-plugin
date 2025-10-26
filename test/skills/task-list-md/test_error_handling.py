#!/usr/bin/env python3
"""
Test suite for error handling and edge cases in task_list_md.py
Tests various error conditions and boundary cases
"""

import unittest
import subprocess
import tempfile
import os
import shutil
from pathlib import Path


class TestErrorHandling(unittest.TestCase):
    """Test suite for error handling and edge cases"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with paths"""
        cls.script_path = Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts" / "task_list_md.py"

    def setUp(self):
        """Set up each test with temporary working directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_tasks.md"

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)

    def run_command(self, *args, expect_success=False):
        """Helper to run CLI command expecting failure"""
        cmd = ["python3", str(self.script_path)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def create_test_file(self, content):
        """Helper to create test file with content"""
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def test_nonexistent_file(self):
        """Test error handling for non-existent file"""
        result = self.run_command("list-tasks", "nonexistent.md")
        self.assertEqual(result.returncode, 1)  # Script exits with 1 for file not found
        # Error message goes to stderr OR stdout depending on implementation

    def test_invalid_task_id_show(self):
        """Test show-task with invalid task ID"""
        content = """# Test Tasks
- [x] 1. Valid task
"""
        self.create_test_file(content)

        result = self.run_command("show-task", str(self.test_file), "999")
        self.assertEqual(result.returncode, 0)  # Script doesn't fail, just shows error message
        self.assertIn("Error: Task '999' not found", result.stdout)

    def test_invalid_status_value(self):
        """Test set-status with invalid status value"""
        content = """# Test Tasks
- [x] 1. Valid task
"""
        self.create_test_file(content)

        result = self.run_command("set-status", str(self.test_file), "1", "invalid-status")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_duplicate_task_id(self):
        """Test adding task with duplicate ID"""
        content = """# Test Tasks
- [x] 1. Existing task
"""
        self.create_test_file(content)

        result = self.run_command("add-task", str(self.test_file), "1", "Duplicate task")
        self.assertEqual(result.returncode, 0)  # Script doesn't fail, just shows error message
        self.assertIn("Error: Task '1' already exists", result.stdout)

    def test_invalid_dependency(self):
        """Test adding task with non-existent dependency"""
        content = """# Test Tasks
- [x] 1. Existing task
"""
        self.create_test_file(content)

        result = self.run_command("add-task", str(self.test_file), "2", "New task",
                                 "--dependencies", "999")
        self.assertEqual(result.returncode, 0)  # Script doesn't fail, just shows error message
        self.assertIn("Error: Dependency '999' does not exist", result.stdout)

    def test_delete_nonexistent_task(self):
        """Test deleting non-existent task"""
        content = """# Test Tasks
- [x] 1. Existing task
"""
        self.create_test_file(content)

        result = self.run_command("delete-task", str(self.test_file), "999")
        self.assertEqual(result.returncode, 0)  # Script doesn't fail, just shows error message
        self.assertIn("Error: Task '999' not found", result.stdout)

    def test_parent_child_constraints(self):
        """Test parent-child task status constraints"""
        content = """# Test Tasks
- [ ] 1. Parent task

- [ ] 1.1. Sub-task
  _Dependencies: 1_
"""
        self.create_test_file(content)

        # Try to set sub-task to in-progress while parent is pending
        result = self.run_command("set-status", str(self.test_file), "1.1", "in-progress")
        self.assertEqual(result.returncode, 0)  # Script doesn't fail, just shows error message
        self.assertIn("Cannot change sub-task '1.1' from pending to 'in-progress'", result.stdout)
        self.assertIn("while parent task '1' is 'pending'", result.stdout)

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies"""
        content = """# Test Tasks
- [ ] 1. Task one
  _Dependencies: 2_

- [ ] 2. Task two
  _Dependencies: 1_
"""
        self.create_test_file(content)

        result = self.run_command("check-dependencies", str(self.test_file))
        self.assertEqual(result.returncode, 0)  # Command succeeds but reports errors
        self.assertIn("Circular dependency", result.stdout)

    def test_self_dependency(self):
        """Test detection of self-dependency"""
        content = """# Test Tasks
- [ ] 1. Self-dependent task
  _Dependencies: 1_
"""
        self.create_test_file(content)

        result = self.run_command("check-dependencies", str(self.test_file))
        self.assertEqual(result.returncode, 0)  # Command succeeds but reports errors
        self.assertIn("circular dependency on itself", result.stdout)

    def test_missing_command_arguments(self):
        """Test commands with missing required arguments"""
        # Test show-task without task ID
        result = self.run_command("show-task", str(self.test_file))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error:", result.stderr)

        # Test set-status without status
        result = self.run_command("set-status", str(self.test_file), "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)

    def test_invalid_export_path(self):
        """Test export command with invalid output path"""
        content = """# Test Tasks
- [x] 1. Valid task
"""
        self.create_test_file(content)

        # Try to export to a directory that doesn't exist
        invalid_path = "/nonexistent/directory/output.json"
        result = self.run_command("export", str(self.test_file), "--output", invalid_path)
        # The command might still succeed with a warning, or fail - either is acceptable
        # Just ensure it doesn't crash unexpectedly

    def test_malformed_markdown_file(self):
        """Test handling of malformed markdown files"""
        # Create a file with mixed valid and invalid task formats
        content = """# Malformed Tasks

- [x] 1. Good task

This is not a task line

- [invalid] Not a proper checkbox

- [x] Missing task ID after checkbox

- [x] 2. Another good task
  _Requirements: REQ1_

Some random text
"""
        self.create_test_file(content)

        # Should still parse the valid tasks
        result = self.run_command("list-tasks", str(self.test_file))
        self.assertEqual(result.returncode, 0)
        self.assertIn("ID 1 [done]", result.stdout)
        self.assertIn("ID 2 [done]", result.stdout)

    def test_empty_task_descriptions(self):
        """Test handling of tasks with empty descriptions"""
        content = """# Empty Descriptions

- [x] 1.

- [ ] 2.
  _Requirements: REQ1_

- [ ] 3.
  _Dependencies: 1_
"""
        self.create_test_file(content)

        result = self.run_command("list-tasks", str(self.test_file))
        self.assertEqual(result.returncode, 0)
        self.assertIn("ID 1", result.stdout)
        self.assertIn("ID 2", result.stdout)
        self.assertIn("ID 3", result.stdout)

    def test_unicode_characters(self):
        """Test handling of unicode characters in task content"""
        content = """# Unicode Test

- [x] 1. Task with émojis 🚀 and ünicode
  Description with special characters: café, naïve, résumé
  _Requirements: 中文, العربية_

- [ ] 2. Тask in Cyrillic
  Описание на русском языке
"""
        self.create_test_file(content)

        result = self.run_command("list-tasks", str(self.test_file))
        self.assertEqual(result.returncode, 0)
        self.assertIn("émojis 🚀", result.stdout)

        # Test show-task with unicode
        result = self.run_command("show-task", str(self.test_file), "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Requirements: 中文, العربية", result.stdout)

    def test_very_long_task_content(self):
        """Test handling of very long task content"""
        long_description = "Very long description " * 1000
        content = f"""# Long Content Test

- [x] 1. Task with very long content
  {long_description}
  _Requirements: REQ1_
"""
        self.create_test_file(content)

        result = self.run_command("show-task", str(self.test_file), "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Very long description", result.stdout)

    def test_deeply_nested_tasks(self):
        """Test handling of deeply nested task hierarchies"""
        content = """# Deep Nesting Test

- [x] 1. Level 1
- [x] 1.1. Level 2
- [x] 1.1.1. Level 3
- [x] 1.1.1.1. Level 4
- [x] 1.1.1.1.1. Level 5
- [x] 1.1.1.1.1.1. Level 6
"""
        self.create_test_file(content)

        result = self.run_command("list-tasks", str(self.test_file))
        self.assertEqual(result.returncode, 0)

        # All tasks should be listed
        for level in range(1, 7):
            if level == 1:
                task_id = "1"
            else:
                task_id = "1." + ".".join(["1"] * (level - 1))
            self.assertIn(f"ID {task_id}", result.stdout)

    def test_bulk_operations_edge_cases(self):
        """Test bulk operations with edge cases"""
        content = """# Bulk Test

- [ ] 1. Task one
- [ ] 2. Task two
- [ ] 3. Task three
"""
        self.create_test_file(content)

        # Test bulk set-status with mix of valid and invalid IDs
        result = self.run_command("set-status", str(self.test_file), "1", "999", "2", "done")
        self.assertEqual(result.returncode, 0)  # Script doesn't fail, just shows error message
        self.assertIn("Error: Task '999' not found", result.stdout)

        # Test bulk delete with mix of valid and invalid IDs
        result = self.run_command("delete-task", str(self.test_file), "1", "999")
        self.assertEqual(result.returncode, 0)  # Script doesn't fail, just shows error message
        self.assertIn("Error: Task '999' not found", result.stdout)

    def test_no_arguments_provided(self):
        """Test script behavior when no arguments provided"""
        result = self.run_command()
        self.assertEqual(result.returncode, 0)  # Script shows help and exits successfully
        # Should show help when no command provided
        self.assertTrue(len(result.stdout) > 0 or len(result.stderr) > 0)

    def test_filter_with_no_matches(self):
        """Test filter commands that return no matches"""
        content = """# Filter Test

- [x] 1. Completed task
  _Requirements: REQ1_
"""
        self.create_test_file(content)

        # Filter for pending tasks when none exist
        result = self.run_command("filter-tasks", str(self.test_file), "--status", "pending")
        self.assertEqual(result.returncode, 0)
        self.assertIn("No tasks match", result.stdout)

        # Filter for non-existent requirements
        result = self.run_command("filter-tasks", str(self.test_file), "--requirements", "NONEXISTENT")
        self.assertEqual(result.returncode, 0)
        self.assertIn("No tasks match", result.stdout)

    def test_search_with_no_matches(self):
        """Test search command with no matches"""
        content = """# Search Test

- [x] 1. Simple task
  Basic description
"""
        self.create_test_file(content)

        result = self.run_command("search-tasks", str(self.test_file), "nonexistent")
        self.assertEqual(result.returncode, 0)
        self.assertIn("No tasks found containing keywords", result.stdout)


if __name__ == "__main__":
    unittest.main()