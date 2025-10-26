#!/usr/bin/env python3
"""
Test suite for TaskParser class and core functionality
Tests the internal logic without going through CLI
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add the src directory to the path to import the script
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "plugins" / "gosu-mcp-core" / "skills" / "task-list-md" / "scripts"))

from task_list_md import TaskParser, TaskStatus, Task, Colors, ProgressTracker


class TestTaskParser(unittest.TestCase):
    """Test suite for TaskParser class"""

    def setUp(self):
        """Set up each test with temporary files"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_tasks.md")

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_file(self, content):
        """Helper to create test file with content"""
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def test_task_status_enum(self):
        """Test TaskStatus enum functionality"""
        # Test from_checkbox conversion
        self.assertEqual(TaskStatus.from_checkbox("[ ]"), TaskStatus.PENDING)
        self.assertEqual(TaskStatus.from_checkbox("[-]"), TaskStatus.IN_PROGRESS)
        self.assertEqual(TaskStatus.from_checkbox("[x]"), TaskStatus.DONE)
        self.assertEqual(TaskStatus.from_checkbox("[+]"), TaskStatus.REVIEW)
        self.assertEqual(TaskStatus.from_checkbox("[*]"), TaskStatus.DEFERRED)

        # Test to_checkbox conversion
        self.assertEqual(TaskStatus.PENDING.to_checkbox(), "[ ]")
        self.assertEqual(TaskStatus.IN_PROGRESS.to_checkbox(), "[-]")
        self.assertEqual(TaskStatus.DONE.to_checkbox(), "[x]")
        self.assertEqual(TaskStatus.REVIEW.to_checkbox(), "[+]")
        self.assertEqual(TaskStatus.DEFERRED.to_checkbox(), "[*]")

    def test_colors_class(self):
        """Test Colors class functionality"""
        # Test status color mapping
        self.assertEqual(Colors.get_status_color(TaskStatus.PENDING), Colors.PENDING)
        self.assertEqual(Colors.get_status_color(TaskStatus.DONE), Colors.DONE)

        # Test colorize methods exist and return strings
        colored = Colors.colorize_status(TaskStatus.PENDING)
        self.assertIsInstance(colored, str)
        self.assertIn("pending", colored)

        # Test color enablement check
        enabled = Colors.is_colors_enabled()
        self.assertIsInstance(enabled, bool)

    def test_parse_simple_task(self):
        """Test parsing a simple task"""
        content = """# Test Tasks

- [x] 1. Simple completed task
  Basic task description

- [ ] 2. Simple pending task
  _Requirements: REQ1, REQ2_
  _Dependencies: 1_
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        # Check task count
        self.assertEqual(len(parser.tasks), 2)

        # Check first task
        task1 = parser.tasks["1"]
        self.assertEqual(task1.task_id, "1")
        self.assertEqual(task1.status, TaskStatus.DONE)
        self.assertEqual(task1.description, "Simple completed task")
        self.assertEqual(task1.line_number, 3)
        self.assertEqual(task1.requirements, [])
        self.assertEqual(task1.dependencies, [])

        # Check second task
        task2 = parser.tasks["2"]
        self.assertEqual(task2.task_id, "2")
        self.assertEqual(task2.status, TaskStatus.PENDING)
        self.assertEqual(task2.description, "Simple pending task")
        self.assertEqual(task2.requirements, ["REQ1", "REQ2"])
        self.assertEqual(task2.dependencies, ["1"])

    def test_parse_hierarchical_tasks(self):
        """Test parsing hierarchical tasks"""
        content = """# Hierarchical Tasks

- [x] 1. Parent task
  Main parent task

- [x] 1.1. First sub-task
  First sub-task description
  _Dependencies: 1_

- [ ] 1.2. Second sub-task
  Second sub-task description
  _Dependencies: 1.1_

- [ ] 1.2.1. Nested sub-task
  Deeply nested task
  _Dependencies: 1.2_
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        # Check task count
        self.assertEqual(len(parser.tasks), 4)

        # Check hierarchical relationships
        self.assertTrue(parser._is_sub_task("1.1"))
        self.assertTrue(parser._is_sub_task("1.2"))
        self.assertTrue(parser._is_sub_task("1.2.1"))
        self.assertFalse(parser._is_sub_task("1"))

        # Check parent-child relationships
        self.assertEqual(parser._get_parent_task_id("1.1"), "1")
        self.assertEqual(parser._get_parent_task_id("1.2"), "1")
        self.assertEqual(parser._get_parent_task_id("1.2.1"), "1.2")
        self.assertIsNone(parser._get_parent_task_id("1"))

        # Check sub-task identification
        self.assertTrue(parser._has_sub_tasks("1"))
        self.assertTrue(parser._has_sub_tasks("1.2"))
        self.assertFalse(parser._has_sub_tasks("1.1"))
        self.assertFalse(parser._has_sub_tasks("1.2.1"))

        # Check sub-task listing
        sub_tasks_1 = parser._get_sub_tasks("1")
        self.assertEqual(sorted(sub_tasks_1), ["1.1", "1.2"])

    def test_task_sorting(self):
        """Test task sorting functionality"""
        content = """# Sorting Test

- [ ] 2. Second task
- [ ] 1. First task
- [ ] 10. Tenth task
- [ ] 1.1. Sub-task
- [ ] 1.10. Another sub-task
- [ ] 1.2. Second sub-task
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        # Test sort key generation
        self.assertEqual(parser._sort_key("1"), [1])
        self.assertEqual(parser._sort_key("1.2"), [1, 2])
        self.assertEqual(parser._sort_key("1.10"), [1, 10])

        # Check that tasks are sorted correctly when listed
        sorted_ids = sorted(parser.tasks.keys(), key=parser._sort_key)
        expected_order = ["1", "1.1", "1.2", "1.10", "2", "10"]
        self.assertEqual(sorted_ids, expected_order)

    def test_task_with_multiline_content(self):
        """Test parsing task with multiline content"""
        content = """# Multiline Test

- [ ] 1. Task with multiline content
  This is a detailed description
  that spans multiple lines.

  It includes paragraphs and
  various formatting.

  _Requirements: REQ1_
  _Dependencies: none_

- [ ] 2. Next task
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        task1 = parser.tasks["1"]
        self.assertIn("detailed description", task1.full_content)
        self.assertIn("multiple lines", task1.full_content)
        self.assertIn("paragraphs", task1.full_content)
        self.assertEqual(task1.requirements, ["REQ1"])

    def test_empty_file(self):
        """Test parsing empty file"""
        content = """# Empty Tasks File

This file has no tasks.
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        self.assertEqual(len(parser.tasks), 0)

    def test_malformed_tasks(self):
        """Test handling malformed task entries"""
        content = """# Malformed Tasks

- [x] 1. Good task

- This is not a task

- [x] Not a proper task ID. Should be ignored

- [x] 2. Another good task
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        # Should only parse the good tasks
        self.assertEqual(len(parser.tasks), 2)
        self.assertIn("1", parser.tasks)
        self.assertIn("2", parser.tasks)

    def test_various_status_types(self):
        """Test parsing all status types"""
        content = """# Status Types

- [ ] 1. Pending task
- [-] 2. In-progress task
- [x] 3. Done task
- [+] 4. Review task
- [*] 5. Deferred task
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        self.assertEqual(parser.tasks["1"].status, TaskStatus.PENDING)
        self.assertEqual(parser.tasks["2"].status, TaskStatus.IN_PROGRESS)
        self.assertEqual(parser.tasks["3"].status, TaskStatus.DONE)
        self.assertEqual(parser.tasks["4"].status, TaskStatus.REVIEW)
        self.assertEqual(parser.tasks["5"].status, TaskStatus.DEFERRED)

    def test_task_description_extraction(self):
        """Test task description extraction from various formats"""
        content = """# Description Test

- [ ] 1. Task with immediate description

- [ ] 2.
  Task with description on next line

- [ ] 3. Task with title
  More detailed description here
  that continues on multiple lines

- [ ] 4.
  No title, just description
"""
        self.create_test_file(content)
        parser = TaskParser(self.test_file)

        self.assertEqual(parser.tasks["1"].description, "Task with immediate description")
        self.assertEqual(parser.tasks["2"].description, "Task with description on next line")
        self.assertEqual(parser.tasks["3"].description, "Task with title")
        self.assertEqual(parser.tasks["4"].description, "No title, just description")


class TestProgressTracker(unittest.TestCase):
    """Test suite for ProgressTracker class"""

    def setUp(self):
        """Set up each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.progress_file = os.path.join(self.temp_dir, ".tasks.test.json")
        self.tracker = ProgressTracker(self.progress_file)

    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_progress_tracking(self):
        """Test progress tracking functionality"""
        test_file = "test.md"

        # Update task status
        self.tracker.update_task_status(test_file, "1", TaskStatus.DONE, "Test task")

        # Check if data was saved
        self.assertTrue(os.path.exists(self.progress_file))

        # Check task history
        history = self.tracker.get_task_history(test_file, "1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], "done")

        # Check statistics
        stats = self.tracker.get_statistics(test_file)
        self.assertIn("total_tasks", stats)
        self.assertIn("last_modified", stats)

    def test_statistics_calculation(self):
        """Test statistics calculation"""
        test_file = "test.md"

        # Create mock tasks
        tasks = {
            "1": Task("1", "Task 1", TaskStatus.DONE, [], [], 1, 0, ""),
            "2": Task("2", "Task 2", TaskStatus.PENDING, [], [], 2, 0, ""),
            "3": Task("3", "Task 3", TaskStatus.IN_PROGRESS, [], [], 3, 0, ""),
        }

        # Calculate statistics
        self.tracker.calculate_statistics(test_file, tasks)

        # Check statistics
        stats = self.tracker.get_statistics(test_file)
        self.assertEqual(stats["total_tasks"], 3)
        self.assertEqual(stats["completed"], 1)  # Only done task
        self.assertEqual(stats["done"], 1)  # New field for done count
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["in_progress"], 1)
        self.assertAlmostEqual(stats["percentage"], 33.33, places=2)

    def test_statistics_calculation_with_review_and_deferred(self):
        """Test statistics calculation with review and deferred statuses counted as completed"""
        test_file = "test.md"

        # Create mock tasks with various completion statuses
        tasks = {
            "1": Task("1", "Task 1", TaskStatus.DONE, [], [], 1, 0, ""),
            "2": Task("2", "Task 2", TaskStatus.REVIEW, [], [], 2, 0, ""),
            "3": Task("3", "Task 3", TaskStatus.DEFERRED, [], [], 3, 0, ""),
            "4": Task("4", "Task 4", TaskStatus.PENDING, [], [], 4, 0, ""),
            "5": Task("5", "Task 5", TaskStatus.IN_PROGRESS, [], [], 5, 0, ""),
        }

        # Calculate statistics
        self.tracker.calculate_statistics(test_file, tasks)

        # Check statistics
        stats = self.tracker.get_statistics(test_file)
        self.assertEqual(stats["total_tasks"], 5)
        self.assertEqual(stats["completed"], 3)  # done + review + deferred
        self.assertEqual(stats["done"], 1)  # Only done task
        self.assertEqual(stats["review"], 1)
        self.assertEqual(stats["deferred"], 1)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["in_progress"], 1)
        self.assertEqual(stats["percentage"], 60.0)  # 3/5 = 60%


if __name__ == "__main__":
    unittest.main()