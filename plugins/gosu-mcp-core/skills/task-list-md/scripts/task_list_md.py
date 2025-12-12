#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Set


class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Status colors
    PENDING = '\033[93m'     # Yellow
    IN_PROGRESS = '\033[94m' # Blue
    DONE = '\033[92m'        # Green
    REVIEW = '\033[96m'      # Cyan
    DEFERRED = '\033[91m'    # Red

    # Other colors
    RED = '\033[91m'
    WHITE = '\033[97m'

    @classmethod
    def get_status_color(cls, status: 'TaskStatus') -> str:
        """Get the color code for a task status"""
        color_map = {
            TaskStatus.PENDING: cls.PENDING,
            TaskStatus.IN_PROGRESS: cls.IN_PROGRESS,
            TaskStatus.DONE: cls.DONE,
            TaskStatus.REVIEW: cls.REVIEW,
            TaskStatus.DEFERRED: cls.DEFERRED,
        }
        return color_map.get(status, cls.WHITE)

    @classmethod
    def colorize_status(cls, status: 'TaskStatus') -> str:
        """Colorize a status string"""
        color = cls.get_status_color(status)
        return f"{color}{status.value}{cls.RESET}"

    @classmethod
    def colorize_text(cls, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def is_colors_enabled(cls) -> bool:
        """Check if terminal supports colors and colors should be enabled"""
        # Simple check - can be enhanced to check for terminal capabilities
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    DONE = "done"
    REVIEW = "review"
    DEFERRED = "deferred"

    @classmethod
    def from_checkbox(cls, checkbox: str) -> 'TaskStatus':
        """Convert checkbox format to TaskStatus"""
        mapping = {
            "[ ]": cls.PENDING,
            "[-]": cls.IN_PROGRESS,
            "[x]": cls.DONE,
            "[+]": cls.REVIEW,
            "[*]": cls.DEFERRED,
        }
        return mapping.get(checkbox, cls.PENDING)

    def to_checkbox(self) -> str:
        """Convert TaskStatus to checkbox format"""
        mapping = {
            self.PENDING: "[ ]",
            self.IN_PROGRESS: "[-]",
            self.DONE: "[x]",
            self.REVIEW: "[+]",
            self.DEFERRED: "[*]",
        }
        return mapping[self]


@dataclass
class Task:
    task_id: str
    description: str
    status: TaskStatus
    requirements: List[str]
    dependencies: List[str]
    line_number: int
    indent_level: int
    full_content: str

    def __str__(self) -> str:
        if Colors.is_colors_enabled():
            colored_status = Colors.colorize_status(self.status)
        else:
            colored_status = self.status.value
        return f"ID {self.task_id} [{colored_status}]: {self.description}"


class ProgressTracker:
    def __init__(self, progress_file: str = ".tasks.local.json"):
        self.progress_file = progress_file
        self.data = self._load_progress_data()

    def _load_progress_data(self) -> Dict:
        """Load progress data from JSON file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}

    def _save_progress_data(self):
        """Save progress data to JSON file"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            print(f"Warning: Could not save progress data: filesystem error occurred")
        except PermissionError:
            print(f"Warning: Could not save progress data: permission denied")
        except Exception as e:
            # Log full error for debugging, but show generic message to user
            import logging
            logging.warning(f"Unexpected error saving progress: {e}")
            print(f"Warning: Could not save progress data: unexpected error")

    def update_task_status(self, file_path: str, task_id: str, status: TaskStatus, description: str):
        """Update task status with timestamp"""
        abs_file_path = os.path.abspath(file_path)

        if abs_file_path not in self.data:
            self.data[abs_file_path] = {
                "total_tasks": 0,
                "completed": 0,
                "done": 0,
                "in_progress": 0,
                "pending": 0,
                "review": 0,
                "deferred": 0,
                "percentage": 0.0,
                "last_modified": "",
                "tasks": {}
            }

        # Initialize task if not exists
        if task_id not in self.data[abs_file_path]["tasks"]:
            self.data[abs_file_path]["tasks"][task_id] = {
                "description": description,
                "status_history": []
            }

        # Update description if it has changed
        self.data[abs_file_path]["tasks"][task_id]["description"] = description

        # Add status change to history
        timestamp = datetime.now().isoformat()
        self.data[abs_file_path]["tasks"][task_id]["status_history"].append({
            "status": status.value,
            "timestamp": timestamp
        })

        # Update last modified timestamp
        self.data[abs_file_path]["last_modified"] = timestamp

        self._save_progress_data()

    def calculate_statistics(self, file_path: str, tasks: Dict[str, Task]):
        """Calculate and update statistics for a file"""
        abs_file_path = os.path.abspath(file_path)

        if abs_file_path not in self.data:
            self.data[abs_file_path] = {
                "total_tasks": 0,
                "completed": 0,
                "done": 0,
                "in_progress": 0,
                "pending": 0,
                "review": 0,
                "deferred": 0,
                "percentage": 0.0,
                "last_modified": datetime.now().isoformat(),
                "tasks": {}
            }

        # Count task statuses
        status_counts = {
            "pending": 0,
            "in-progress": 0,
            "done": 0,
            "review": 0,
            "deferred": 0
        }

        for task in tasks.values():
            status_counts[task.status.value] += 1

        # Update statistics
        total_tasks = len(tasks)
        # Consider done, review, and deferred as completion states
        completed_tasks = status_counts["done"] + status_counts["review"] + status_counts["deferred"]

        self.data[abs_file_path].update({
            "total_tasks": total_tasks,
            "completed": completed_tasks,
            "done": status_counts["done"],
            "in_progress": status_counts["in-progress"],
            "pending": status_counts["pending"],
            "review": status_counts["review"],
            "deferred": status_counts["deferred"],
            "percentage": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2),
            "last_modified": datetime.now().isoformat()
        })

        self._save_progress_data()

    def get_statistics(self, file_path: str) -> Dict:
        """Get statistics for a file"""
        abs_file_path = os.path.abspath(file_path)
        return self.data.get(abs_file_path, {})

    def get_task_history(self, file_path: str, task_id: str) -> List[Dict]:
        """Get status history for a specific task"""
        abs_file_path = os.path.abspath(file_path)
        if abs_file_path in self.data and task_id in self.data[abs_file_path]["tasks"]:
            return self.data[abs_file_path]["tasks"][task_id]["status_history"]
        return []

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to seconds. Supports h, m, s suffixes. No suffix defaults to seconds."""
        duration_str = duration_str.strip()

        if duration_str.endswith('h'):
            try:
                return int(duration_str[:-1]) * 3600  # hours to seconds
            except ValueError:
                raise ValueError(f"Invalid duration format: '{duration_str}'. Expected format: '1h', '30m', '45s' or plain number")
        elif duration_str.endswith('m'):
            try:
                return int(duration_str[:-1]) * 60    # minutes to seconds
            except ValueError:
                raise ValueError(f"Invalid duration format: '{duration_str}'. Expected format: '1h', '30m', '45s' or plain number")
        elif duration_str.endswith('s'):
            try:
                return int(duration_str[:-1])         # seconds
            except ValueError:
                raise ValueError(f"Invalid duration format: '{duration_str}'. Expected format: '1h', '30m', '45s' or plain number")
        else:
            try:
                return int(duration_str)              # assume seconds if no suffix
            except ValueError:
                raise ValueError(f"Invalid duration format: '{duration_str}'. Expected format: '1h', '30m', '45s' or plain number")

    def add_tracking_condition(self, file_path: str, task_ids: List[str], valid_for: str = "2h",
                              complete_more: Optional[int] = None, tasks: Dict[str, 'Task'] = None):
        """Add a tracking condition with validation"""
        abs_file_path = os.path.abspath(file_path)

        # Validate task IDs exist
        if tasks:
            for task_id in task_ids:
                if task_id not in tasks:
                    raise ValueError(f"Task '{task_id}' not found in the task file")

        # Parse duration and calculate valid_before timestamp
        try:
            duration_seconds = self._parse_duration(valid_for)
        except ValueError as e:
            raise ValueError(f"Invalid duration format: '{valid_for}'. {e}")

        valid_before = datetime.now() + timedelta(seconds=duration_seconds)

        # Calculate expect_completed if complete_more is provided
        expect_completed = None
        if complete_more is not None:
            current_stats = self.get_statistics(file_path)
            current_completed = current_stats.get('completed', 0)
            total_tasks = current_stats.get('total_tasks', 0)
            expect_completed = current_completed + complete_more

            # Validate that expect_completed doesn't exceed total_tasks
            if expect_completed > total_tasks:
                raise ValueError(
                    f"Invalid argument, completed: {current_completed} + complete_more: {complete_more} > total_tasks: {total_tasks}"
                    f"The maximum value of complete_more is: {total_tasks - current_completed}"
                )

        # Initialize file data structure if needed
        if abs_file_path not in self.data:
            self.data[abs_file_path] = {
                "total_tasks": 0,
                "completed": 0,
                "done": 0,
                "in_progress": 0,
                "pending": 0,
                "review": 0,
                "deferred": 0,
                "percentage": 0.0,
                "last_modified": datetime.now().isoformat(),
                "tasks": {},
                "tracking": []
            }

        # Initialize tracking field if it doesn't exist
        if "tracking" not in self.data[abs_file_path]:
            self.data[abs_file_path]["tracking"] = []

        # Create tracking condition
        condition = {
            "valid_before": valid_before.isoformat(),
            "tasks_to_complete": task_ids.copy()
        }

        if expect_completed is not None:
            condition["expect_completed"] = expect_completed

        # Add to tracking list
        self.data[abs_file_path]["tracking"].append(condition)

        # Save data
        self._save_progress_data()

        return condition

    def check_tracking_conditions(self, file_path: str, tasks: Dict[str, 'Task']) -> List[Dict]:
        """Check all completion conditions and return list of unmet conditions"""
        abs_file_path = os.path.abspath(file_path)

        if abs_file_path not in self.data or "tracking" not in self.data[abs_file_path]:
            return []

        unmet_conditions = []
        current_time = datetime.now()

        for condition in self.data[abs_file_path]["tracking"]:
            # Skip expired conditions
            valid_before = datetime.fromisoformat(condition["valid_before"])
            if current_time > valid_before:
                continue

            # Check if required tasks are completed (done, review, or deferred are all considered completed)
            tasks_to_complete = condition["tasks_to_complete"]
            unmet_tasks = []

            for task_id in tasks_to_complete:
                if task_id not in tasks:
                    unmet_tasks.append(f"Task '{task_id}' not found")
                elif tasks[task_id].status not in [TaskStatus.DONE, TaskStatus.REVIEW, TaskStatus.DEFERRED]:
                    unmet_tasks.append(f"Task '{task_id}' is not completed (status: {tasks[task_id].status.value})")

            # Check total completed count if specified
            total_count_issue = None
            if "expect_completed" in condition:
                expected_count = condition["expect_completed"]
                current_stats = self.get_statistics(file_path)
                actual_count = current_stats.get('completed', 0)
                if actual_count < expected_count:
                    total_count_issue = f"Expected {expected_count} completed tasks, but only {actual_count} are completed"

            # If any issues found, add to unmet conditions
            if unmet_tasks or total_count_issue:
                unmet_condition = {
                    "condition": condition,
                    "unmet_tasks": unmet_tasks,
                    "total_count_issue": total_count_issue
                }
                unmet_conditions.append(unmet_condition)

        return unmet_conditions

    def clear_tracking_conditions(self, file_path: str, force: bool = False) -> bool:
        """Clear all tracking completion conditions. Returns True if cleared, False if cancelled."""
        abs_file_path = os.path.abspath(file_path)

        if abs_file_path not in self.data or "tracking" not in self.data[abs_file_path]:
            print("No completion conditions to clear.")
            return True

        tracking_count = len(self.data[abs_file_path]["tracking"])
        if tracking_count == 0:
            print("No completion conditions to clear.")
            return True

        # Ask for confirmation unless force is True
        if not force:
            response = input(f"Are you sure you want to clear {tracking_count} tracking condition(s)? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Operation cancelled.")
                return False

        # Clear completion conditions
        self.data[abs_file_path]["tracking"] = []
        self._save_progress_data()

        print(f"Cleared {tracking_count} tracking condition(s).")
        return True

    def read_claude_hook_input(self) -> Dict:
        """Read Claude hook JSON input from stdin"""
        try:
            hook_input = sys.stdin.read().strip()
            if not hook_input:
                return {}
            return json.loads(hook_input)
        except (json.JSONDecodeError, Exception):
            return {}

    def detect_infinite_loop(self, transcript_path: str) -> bool:
        """Detect if we're in an infinite loop by checking transcript file for repeated hook calls"""
        try:
            # Expand tilde in path with validation
            # Its ok to trust this path since its coming from claude hook input
            expanded_path = os.path.expanduser(transcript_path)
            if not os.path.exists(expanded_path):
                return True  # If transcript doesn't exist, assume we should exit to be safe

            # Corrected regex pattern to match the hook command
            pattern = r'python3?\s+.*?task_list_md\.py\s+track-progress\s+check\s+.*?\s+--claude-hook'

            count = 0
            with open(expanded_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if re.search(pattern, line):
                        count += 1
                        if count > 3:
                            return True

            return False
        except (IOError, OSError, PermissionError) as e:
            # Log the specific error for debugging
            print(f"Warning: Could not read transcript file {expanded_path}: {e}", file=sys.stderr)
            return True  # If we can't read the file, be safe and assume loop
        except UnicodeDecodeError as e:
            print(f"Warning: Transcript file contains invalid characters: {e}", file=sys.stderr)
            return True
        except Exception as e:
            # Log unexpected errors for debugging
            import logging
            logging.warning(f"Unexpected error in detect_infinite_loop: {e}")
            return True

    def output_claude_hook_response(self, block: bool, reason: str = ""):
        """Output JSON response for Claude hook mode

        Args:
            block: If True, output decision="block" to prevent Claude from stopping.
                   If False, omit decision key to allow Claude to stop.
            reason: Reason message. Required when block=True, ignored when block=False.
        """
        response = {}
        if block:
            response["decision"] = "block"
            response["reason"] = reason
        else:
            response["reason"] = ""

        print(json.dumps(response))
        sys.stdout.flush()

    def output_claude_hook_session_start_response(self, reason: str):
        """Output JSON response for Claude SessionStart hook"""
        response = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": reason
            }
        }
        print(json.dumps(response))
        sys.stdout.flush()


class TaskParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.tasks: Dict[str, Task] = {}
        self.file_lines: List[str] = []
        self.progress_tracker = ProgressTracker()
        self._parse_file()
        # Calculate initial statistics
        self.progress_tracker.calculate_statistics(self.file_path, self.tasks)

    def _parse_file(self):
        """Parse the markdown file and extract tasks"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.file_lines = f.readlines()
        except FileNotFoundError:
            print(f"Error: File '{self.file_path}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

        current_task = None
        task_content_lines = []

        for line_num, line in enumerate(self.file_lines, 1):
            # Check if this is a task line
            # Escape any user-controlled input to prevent regex injection
            task_match = re.match(r'^(\s*)-\s*(\[[ \-x\+\*]\])\s*(\d+(?:\.\d+)*)\.?\s*(.*)$', line)

            if task_match:
                # Save previous task if exists
                if current_task:
                    current_task.full_content = '\n'.join(task_content_lines)
                    self.tasks[current_task.task_id] = current_task

                # Parse new task
                indent_str, checkbox, task_id, description = task_match.groups()
                indent_level = len(indent_str)
                status = TaskStatus.from_checkbox(checkbox)

                current_task = Task(
                    task_id=task_id,
                    description=description.strip() if description else "",
                    status=status,
                    requirements=[],
                    dependencies=[],
                    line_number=line_num,
                    indent_level=indent_level,
                    full_content=""
                )
                task_content_lines = [line]

            elif current_task:
                # This line belongs to the current task
                task_content_lines.append(line)

                # If the current task doesn't have a description and this is a content line
                # that contains text (not a sub-item, requirement, or dependency), use it as description
                stripped_line = line.strip()
                if (not current_task.description and stripped_line and
                    not stripped_line.startswith('-') and
                    not stripped_line.startswith('_Requirements:') and
                    not stripped_line.startswith('_Dependencies:')):
                    current_task.description = stripped_line

                # Parse requirements
                req_match = re.search(r'_Requirements:\s*([^_]+)_', line)
                if req_match:
                    req_text = req_match.group(1).strip()
                    requirements = [req.strip() for req in req_text.split(',')]
                    current_task.requirements.extend(requirements)

                # Parse dependencies
                dep_match = re.search(r'_Dependencies:\s*([^_]+)_', line)
                if dep_match:
                    dep_text = dep_match.group(1).strip()
                    dependencies = [dep.strip() for dep in dep_text.split(',')]
                    current_task.dependencies.extend(dependencies)

        # Don't forget the last task
        if current_task:
            current_task.full_content = '\n'.join(task_content_lines)
            self.tasks[current_task.task_id] = current_task

    def list_tasks(self):
        """List all tasks with their status and ID"""
        if not self.tasks:
            print("No tasks found in the file.")
            return

        print(f"Tasks from {self.file_path}:")
        print("-" * 60)

        # Sort tasks by ID (numeric sort for hierarchical IDs)
        sorted_task_ids = sorted(self.tasks.keys(), key=self._sort_key)

        for task_id in sorted_task_ids:
            task = self.tasks[task_id]
            indent = "    " * (task.task_id.count('.'))
            print(f"{indent}{task}")

    def show_task(self, task_id: str):
        """Show details of a specific task"""
        if task_id not in self.tasks:
            print(f"Error: Task '{task_id}' not found.")
            return

        task = self.tasks[task_id]

        # Use colored status
        if Colors.is_colors_enabled():
            colored_status = Colors.colorize_status(task.status)
        else:
            colored_status = task.status.value

        print(f"Task ID: {task.task_id}")
        print(f"Status: {colored_status}")
        print(f"Description: {task.description}")

        if task.requirements:
            print(f"Requirements: {', '.join(task.requirements)}")

        if task.dependencies:
            print(f"Dependencies: {', '.join(task.dependencies)}")

        # Show sub-tasks if this task has any
        if self._has_sub_tasks(task_id):
            sub_task_ids = self._get_sub_tasks(task_id)
            print(f"Sub-tasks ({len(sub_task_ids)}):")
            for sub_id in sub_task_ids:
                sub_task = self.tasks[sub_id]
                if Colors.is_colors_enabled():
                    sub_colored_status = Colors.colorize_status(sub_task.status)
                else:
                    sub_colored_status = sub_task.status.value
                print(f"  - {sub_id} [{sub_colored_status}]: {sub_task.description}")

        # Show parent task if this is a sub-task
        if self._is_sub_task(task_id):
            parent_id = self._get_parent_task_id(task_id)
            if parent_id and parent_id in self.tasks:
                parent_task = self.tasks[parent_id]
                if Colors.is_colors_enabled():
                    parent_colored_status = Colors.colorize_status(parent_task.status)
                else:
                    parent_colored_status = parent_task.status.value
                print(f"Parent Task: {parent_id} [{parent_colored_status}]: {parent_task.description}")

        print(f"Line Number: {task.line_number}")
        print(f"Indent Level: {task.indent_level}")
        print("\nFull Content:")
        print("-" * 40)
        print(task.full_content)

    def set_status(self, task_id: str, status_str: str):
        """Set the status of a specific task with validation and auto-updates"""
        if task_id not in self.tasks:
            print(f"Error: Task '{task_id}' not found.")
            return

        try:
            new_status = TaskStatus(status_str)
        except ValueError:
            valid_statuses = [s.value for s in TaskStatus]
            print(f"Error: Invalid status '{status_str}'. Valid statuses: {valid_statuses}")
            return

        task = self.tasks[task_id]
        old_status = task.status

        # Validate sub-task status change against parent
        if self._is_sub_task(task_id):
            parent_id = self._get_parent_task_id(task_id)
            if parent_id and parent_id in self.tasks:
                parent_task = self.tasks[parent_id]

                # Sub task can change from pending to other statuses only when parent is not pending or done
                if (old_status == TaskStatus.PENDING and
                    new_status != TaskStatus.PENDING and
                    parent_task.status in [TaskStatus.PENDING, TaskStatus.DONE]):
                    print(f"Error: Cannot change sub-task '{task_id}' from pending to '{new_status.value}' "
                          f"while parent task '{parent_id}' is '{parent_task.status.value}'. "
                          f"Please set parent task to 'in-progress' first.")
                    return

        # Update the task status
        task.status = new_status
        self._update_file_status(task)

        # Record the status change in progress tracker
        self.progress_tracker.update_task_status(self.file_path, task_id, new_status, task.description)

        # Recalculate statistics
        self.progress_tracker.calculate_statistics(self.file_path, self.tasks)

        if Colors.is_colors_enabled():
            colored_old = Colors.colorize_status(old_status)
            colored_new = Colors.colorize_status(new_status)
            print(f"Task '{task_id}' status changed from {colored_old} to {colored_new}")
        else:
            print(f"Task '{task_id}' status changed from '{old_status.value}' to '{new_status.value}'")

        # Auto-update parent task if all sub-tasks have the same status
        if self._is_sub_task(task_id):
            parent_id = self._get_parent_task_id(task_id)
            if parent_id:
                self._auto_update_parent_status(parent_id)

    def get_next_task(self):
        """Get the next task ID to work on, considering both parent tasks and sub-tasks"""
        # Find tasks that are pending or in-progress
        candidate_tasks = []

        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                # Check if all dependencies are satisfied
                dependencies_satisfied = True
                for dep_id in task.dependencies:
                    if dep_id not in self.tasks:
                        dependencies_satisfied = False
                        break
                    dep_task = self.tasks[dep_id]
                    if dep_task.status not in [TaskStatus.DONE, TaskStatus.REVIEW]:
                        dependencies_satisfied = False
                        break

                # For sub-tasks, also check if parent allows progression
                if self._is_sub_task(task_id):
                    parent_id = self._get_parent_task_id(task_id)
                    if parent_id and parent_id in self.tasks:
                        parent_task = self.tasks[parent_id]
                        # Sub-task can only be worked on if parent is not pending or done
                        if parent_task.status in [TaskStatus.PENDING, TaskStatus.DONE]:
                            dependencies_satisfied = False

                if dependencies_satisfied:
                    candidate_tasks.append((task_id, task))

        if not candidate_tasks:
            print("No tasks available to work on (all dependencies not satisfied, parent constraints, or no pending/in-progress tasks).")
            return

        # Prioritize sub-tasks over parent tasks when parent is in-progress
        # First, separate parent tasks and sub-tasks
        parent_tasks = [(tid, task) for tid, task in candidate_tasks if not self._is_sub_task(tid)]
        sub_tasks = [(tid, task) for tid, task in candidate_tasks if self._is_sub_task(tid)]

        # Prefer sub-tasks if their parent is in-progress
        preferred_tasks = []
        for tid, task in sub_tasks:
            parent_id = self._get_parent_task_id(tid)
            if parent_id and parent_id in self.tasks and self.tasks[parent_id].status == TaskStatus.IN_PROGRESS:
                preferred_tasks.append((tid, task))

        # If we have preferred sub-tasks, use them; otherwise use all candidates
        if preferred_tasks:
            candidate_tasks = preferred_tasks

        # Sort by task ID to get the first one
        candidate_tasks.sort(key=lambda x: self._sort_key(x[0]))
        next_task_id, next_task = candidate_tasks[0]

        # Use colored status
        if Colors.is_colors_enabled():
            colored_status = Colors.colorize_status(next_task.status)
        else:
            colored_status = next_task.status.value

        print(f"Next task to work on:")
        print(f"ID {next_task_id} [{colored_status}]: {next_task.description}")

        if next_task.dependencies:
            print(f"Dependencies (all satisfied): {', '.join(next_task.dependencies)}")

        # If this is a parent task with sub-tasks, show the sub-tasks
        if self._has_sub_tasks(next_task_id):
            sub_task_ids = self._get_sub_tasks(next_task_id)
            print(f"\nSub-tasks:")
            for sub_id in sub_task_ids:
                sub_task = self.tasks[sub_id]
                if Colors.is_colors_enabled():
                    sub_colored_status = Colors.colorize_status(sub_task.status)
                else:
                    sub_colored_status = sub_task.status.value
                print(f"    ID {sub_id} [{sub_colored_status}]: {sub_task.description}")

        # If this is a sub-task, show the parent context
        if self._is_sub_task(next_task_id):
            parent_id = self._get_parent_task_id(next_task_id)
            if parent_id and parent_id in self.tasks:
                parent_task = self.tasks[parent_id]
                if Colors.is_colors_enabled():
                    parent_colored_status = Colors.colorize_status(parent_task.status)
                else:
                    parent_colored_status = parent_task.status.value
                print(f"\nParent task:")
                print(f"    ID {parent_id} [{parent_colored_status}]: {parent_task.description}")

    def validate_dependencies(self):
        """Validate all task dependencies"""
        errors = []

        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                # Check if dependency exists
                if dep_id not in self.tasks:
                    errors.append(f"Task '{task_id}' has non-existent dependency '{dep_id}'")
                    continue

                # Check for self-dependency
                if dep_id == task_id:
                    errors.append(f"Task '{task_id}' has circular dependency on itself")
                    continue

                # Check for direct circular dependency
                dep_task = self.tasks[dep_id]
                if task_id in dep_task.dependencies:
                    errors.append(f"Circular dependency between tasks '{task_id}' and '{dep_id}'")

        if errors:
            print("Dependency validation errors found:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("All dependencies are valid.")

    def show_progress(self):
        """Show progress report in human-readable format"""
        # Refresh statistics first
        self.progress_tracker.calculate_statistics(self.file_path, self.tasks)

        stats = self.progress_tracker.get_statistics(self.file_path)

        if not stats:
            print("No progress data available for this file.")
            return

        print(f"Progress Report for: {self.file_path}")
        print("=" * 60)
        print(f"Total Tasks: {stats.get('total_tasks', 0)}")
        print(f"Completed (done+review+deferred): {stats.get('completed', 0)}")
        print(f"  Done: {stats.get('done', 0)}")
        print(f"  Review: {stats.get('review', 0)}")
        print(f"  Deferred: {stats.get('deferred', 0)}")
        print(f"In Progress: {stats.get('in_progress', 0)}")
        print(f"Pending: {stats.get('pending', 0)}")
        print(f"Completion Percentage: {stats.get('percentage', 0)}%")
        print(f"Last Modified: {stats.get('last_modified', 'Unknown')}")
        print()

        # Show task history if available
        task_data = stats.get('tasks', {})
        if task_data:
            print("Task Status History:")
            print("-" * 40)

            # Sort task IDs for consistent display
            sorted_task_ids = sorted(task_data.keys(), key=self._sort_key)

            for task_id in sorted_task_ids:
                task_info = task_data[task_id]
                print(f"\nTask {task_id}: {task_info.get('description', 'No description')}")

                history = task_info.get('status_history', [])
                if history:
                    print("  Status History:")
                    for entry in history:
                        timestamp = entry.get('timestamp', 'Unknown')
                        status = entry.get('status', 'Unknown')
                        # Format timestamp for better readability
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            formatted_time = timestamp
                        print(f"    {formatted_time}: {status}")
                else:
                    print("  No status history available")
        else:
            print("No detailed task history available.")

    def _update_file_status(self, task: Task):
        """Update the task status in the file"""
        try:
            # Use the known line number instead of searching through all lines
            line_index = task.line_number - 1
            if 0 <= line_index < len(self.file_lines):
                line = self.file_lines[line_index]
                # Verify this is the correct task line before updating
                if re.match(rf'^\s*-\s*\[[ \-x\+\*]\]\s*{re.escape(task.task_id)}\.?\s*', line):
                    updated_line = re.sub(r'\[[ \-x\+\*]\]', task.status.to_checkbox(), line)
                    self.file_lines[line_index] = updated_line
                else:
                    # Fallback to search if line number doesn't match
                    self._search_and_update_task_line(task)
            else:
                # Fallback to search if line number is out of range
                self._search_and_update_task_line(task)

            # Write the updated content back to the file
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.writelines(self.file_lines)

        except Exception as e:
            print(f"Error updating file: {e}")

    def _search_and_update_task_line(self, task: Task):
        """Fallback method to search for task line when line number doesn't match"""
        # Find the line with the task and update its checkbox
        for i, line in enumerate(self.file_lines):
            if re.match(rf'^\s*-\s*\[[ \-x\+\*]\]\s*{re.escape(task.task_id)}\.?\s*', line.strip()):
                # Replace the checkbox in the line
                updated_line = re.sub(r'\[[ \-x\+\*]\]', task.status.to_checkbox(), line)
                self.file_lines[i] = updated_line
                break

    def _sort_key(self, task_id: str):
        """Create a sort key for hierarchical task IDs"""
        # Convert "1.2.3" to [1, 2, 3] for proper numeric sorting
        parts = task_id.split('.')
        return [int(part) for part in parts]

    def _is_sub_task(self, task_id: str) -> bool:
        """Check if this is a sub-task (contains dots)"""
        return '.' in task_id

    def _get_parent_task_id(self, task_id: str) -> Optional[str]:
        """Get the parent task ID for a sub-task"""
        if not self._is_sub_task(task_id):
            return None
        parts = task_id.split('.')
        return '.'.join(parts[:-1])

    def _has_sub_tasks(self, task_id: str) -> bool:
        """Check if this task has sub-tasks"""
        for tid in self.tasks.keys():
            if tid.startswith(task_id + '.') and tid.count('.') == task_id.count('.') + 1:
                return True
        return False

    def _get_sub_tasks(self, task_id: str) -> List[str]:
        """Get direct sub-tasks of a given task"""
        sub_tasks = []
        for tid in self.tasks.keys():
            if tid.startswith(task_id + '.') and tid.count('.') == task_id.count('.') + 1:
                sub_tasks.append(tid)
        return sorted(sub_tasks, key=self._sort_key)

    def _auto_update_parent_status(self, parent_id: str):
        """Auto-update parent task status if all sub-tasks have the same status"""
        if parent_id not in self.tasks:
            return

        sub_task_ids = self._get_sub_tasks(parent_id)
        if not sub_task_ids:
            return

        # Get all sub-task statuses
        sub_statuses = [self.tasks[sub_id].status for sub_id in sub_task_ids]

        # If all sub-tasks have the same status, update parent
        if len(set(sub_statuses)) == 1:  # All statuses are the same
            new_status = sub_statuses[0]
            parent_task = self.tasks[parent_id]

            if parent_task.status != new_status:
                old_status = parent_task.status
                parent_task.status = new_status
                self._update_file_status(parent_task)
                if Colors.is_colors_enabled():
                    colored_old = Colors.colorize_status(old_status)
                    colored_new = Colors.colorize_status(new_status)
                    print(f"Auto-updated parent task '{parent_id}' from {colored_old} to {colored_new} "
                          f"(all sub-tasks are {colored_new})")
                else:
                    print(f"Auto-updated parent task '{parent_id}' from '{old_status.value}' to '{new_status.value}' "
                          f"(all sub-tasks are '{new_status.value}')")

    def add_task(self, task_id: str, description: str, dependencies: Optional[List[str]] = None,
                 requirements: Optional[List[str]] = None):
        """Add a new task to the file"""
        # Check if task ID already exists
        if task_id in self.tasks:
            print(f"Error: Task '{task_id}' already exists.")
            return

        # Validate dependencies exist
        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self.tasks:
                    print(f"Error: Dependency '{dep_id}' does not exist.")
                    return

        # Determine the position to insert the new task
        indent_level = task_id.count('.') * 4  # 4 spaces per level
        indent_str = ' ' * indent_level

        # Create the task content
        checkbox = TaskStatus.PENDING.to_checkbox()
        task_line = f"{indent_str}- {checkbox} {task_id}. {description}\n"

        # Add requirements and dependencies if provided
        additional_lines = []
        if requirements:
            req_text = ', '.join(requirements)
            additional_lines.append(f"{indent_str}  _Requirements: {req_text}_\n")

        if dependencies:
            dep_text = ', '.join(dependencies)
            additional_lines.append(f"{indent_str}  _Dependencies: {dep_text}_\n")

        # Find the appropriate position to insert the task
        insert_position = self._find_insert_position(task_id)

        # Ensure proper formatting with newlines
        new_lines = []

        # Handle the case where we're inserting at the end of file or after content
        if insert_position >= len(self.file_lines):
            # Inserting at the end of file
            if self.file_lines and not self.file_lines[-1].endswith('\n'):
                # Last line doesn't end with newline, fix it
                self.file_lines[-1] = self.file_lines[-1] + '\n'
            # Add a blank line before the new task
            new_lines.append('\n')
        else:
            # Inserting in the middle
            # Check if we need to add a newline before the task
            if insert_position > 0:
                prev_line = self.file_lines[insert_position - 1]
                if prev_line and not prev_line.endswith('\n'):
                    # Add newline to previous line
                    self.file_lines[insert_position - 1] = prev_line + '\n'

                # Add a blank line before the new task for better formatting
                if prev_line.strip() != "":
                    new_lines.append('\n')

        # Add the task and its additional lines
        new_lines.extend([task_line] + additional_lines)

        # Add a blank line after the task for consistency (except at the very end)
        if insert_position < len(self.file_lines):
            new_lines.append('\n')

        # Insert all the new lines
        for i, line in enumerate(new_lines):
            self.file_lines.insert(insert_position + i, line)

        # Write the updated content back to the file
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.writelines(self.file_lines)

            # Re-parse the file to update the tasks dictionary
            self._parse_file()
            self.progress_tracker.calculate_statistics(self.file_path, self.tasks)

            print(f"Added task '{task_id}': {description}")

        except Exception as e:
            print(f"Error adding task: {e}")

    def update_task(self, task_id: str,
                    add_dependencies: Optional[List[str]] = None,
                    add_requirements: Optional[List[str]] = None,
                    remove_dependencies: Optional[List[str]] = None,
                    remove_requirements: Optional[List[str]] = None,
                    clear_dependencies: bool = False,
                    clear_requirements: bool = False):
        """Update dependencies and requirements of an existing task"""
        # Validate task exists
        if task_id not in self.tasks:
            print(f"Error: Task '{task_id}' not found.")
            sys.exit(1)

        task = self.tasks[task_id]

        # Validate conflicting operations
        if clear_dependencies and (add_dependencies or remove_dependencies):
            print("Error: Cannot use --clear-dependencies with --add-dependencies or --remove-dependencies")
            sys.exit(1)

        if clear_requirements and (add_requirements or remove_requirements):
            print("Error: Cannot use --clear-requirements with --add-requirements or --remove-requirements")
            sys.exit(1)

        # Validate that dependencies being added exist
        if add_dependencies:
            for dep_id in add_dependencies:
                if dep_id not in self.tasks:
                    print(f"Error: Dependency '{dep_id}' does not exist.")
                    sys.exit(1)
                # Check for circular dependency
                if dep_id == task_id:
                    print(f"Error: Task '{task_id}' cannot depend on itself.")
                    sys.exit(1)
                # Check if adding this dependency would create a circular dependency
                if task_id in self.tasks[dep_id].dependencies:
                    print(f"Error: Adding dependency '{dep_id}' would create a circular dependency.")
                    sys.exit(1)

        # Validate that dependencies being removed exist in current task
        if remove_dependencies:
            for dep_id in remove_dependencies:
                if dep_id not in task.dependencies:
                    print(f"Error: Dependency '{dep_id}' is not currently in task '{task_id}'.")
                    sys.exit(1)

        # Validate that requirements being removed exist in current task
        if remove_requirements:
            for req_id in remove_requirements:
                if req_id not in task.requirements:
                    print(f"Error: Requirement '{req_id}' is not currently in task '{task_id}'.")
                    sys.exit(1)

        # Store original values for reporting
        original_dependencies = task.dependencies.copy()
        original_requirements = task.requirements.copy()

        # Update dependencies
        if clear_dependencies:
            task.dependencies = []
        else:
            if add_dependencies:
                for dep_id in add_dependencies:
                    if dep_id not in task.dependencies:
                        task.dependencies.append(dep_id)

            if remove_dependencies:
                for dep_id in remove_dependencies:
                    if dep_id in task.dependencies:
                        task.dependencies.remove(dep_id)

        # Update requirements
        if clear_requirements:
            task.requirements = []
        else:
            if add_requirements:
                for req_id in add_requirements:
                    if req_id not in task.requirements:
                        task.requirements.append(req_id)

            if remove_requirements:
                for req_id in remove_requirements:
                    if req_id in task.requirements:
                        task.requirements.remove(req_id)

        # Update the file content
        try:
            self._update_task_in_file(task)

            # Re-parse the file to update the tasks dictionary
            self._parse_file()
            self.progress_tracker.calculate_statistics(self.file_path, self.tasks)

            # Report changes
            changes = []
            if original_dependencies != task.dependencies:
                changes.append(f"dependencies: {original_dependencies} -> {task.dependencies}")
            if original_requirements != task.requirements:
                changes.append(f"requirements: {original_requirements} -> {task.requirements}")

            if changes:
                print(f"Updated task '{task_id}': {', '.join(changes)}")
            else:
                print(f"No changes made to task '{task_id}'")

        except Exception as e:
            print(f"Error updating task: {e}")

    def _update_task_in_file(self, task: Task):
        """Update the task's dependencies and requirements in the file"""
        task_start_line = task.line_number - 1  # Convert to 0-based index
        task_end_line = self._find_task_end_line(task.task_id)

        # Find the task content and rebuild it
        new_task_lines = []

        # First line is the task definition itself
        first_line = self.file_lines[task_start_line]
        new_task_lines.append(first_line)

        # Add description if it exists and is not on the first line
        if task.description and not task.description.strip() in first_line:
            indent_str = ' ' * (task.indent_level + 2)  # 2 extra spaces for content
            new_task_lines.append(f"{indent_str}{task.description}\n")

        # Add requirements if any
        if task.requirements:
            indent_str = ' ' * (task.indent_level + 2)
            req_text = ', '.join(task.requirements)
            new_task_lines.append(f"{indent_str}_Requirements: {req_text}_\n")

        # Add dependencies if any
        if task.dependencies:
            indent_str = ' ' * (task.indent_level + 2)
            dep_text = ', '.join(task.dependencies)
            new_task_lines.append(f"{indent_str}_Dependencies: {dep_text}_\n")

        # Replace the old task content with new content
        # Remove old lines
        for i in range(task_end_line - 1, task_start_line - 1, -1):
            if i < len(self.file_lines):
                del self.file_lines[i]

        # Insert new lines
        for i, line in enumerate(new_task_lines):
            self.file_lines.insert(task_start_line + i, line)

        # Write the updated content back to the file
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.writelines(self.file_lines)

    def delete_task(self, task_ids: List[str]):
        """Delete one or more tasks and handle dependency cleanup"""
        # Validate all task IDs exist
        for task_id in task_ids:
            if task_id not in self.tasks:
                print(f"Error: Task '{task_id}' not found.")
                return

        # Check for dependent tasks that would be broken
        dependent_tasks = []
        for task_id in task_ids:
            for tid, task in self.tasks.items():
                if tid not in task_ids and task_id in task.dependencies:
                    dependent_tasks.append((tid, task_id))

        if dependent_tasks:
            print("Error: Cannot delete tasks that have dependencies:")
            for dependent_id, dependency_id in dependent_tasks:
                print(f"  Task '{dependent_id}' depends on '{dependency_id}'")
            return

        # Find all lines to delete (including sub-tasks if parent is deleted)
        lines_to_delete = set()

        for task_id in task_ids:
            task = self.tasks[task_id]

            # Add the task's own lines
            start_line = task.line_number - 1  # Convert to 0-based index
            end_line = self._find_task_end_line(task_id)

            for line_idx in range(start_line, end_line):
                lines_to_delete.add(line_idx)

            # If this is a parent task, also delete all sub-tasks
            sub_tasks = self._get_all_sub_tasks(task_id)
            for sub_task_id in sub_tasks:
                if sub_task_id in self.tasks:
                    sub_task = self.tasks[sub_task_id]
                    sub_start = sub_task.line_number - 1
                    sub_end = self._find_task_end_line(sub_task_id)
                    for line_idx in range(sub_start, sub_end):
                        lines_to_delete.add(line_idx)

        # Remove lines in reverse order to maintain indices
        sorted_lines = sorted(lines_to_delete, reverse=True)
        for line_idx in sorted_lines:
            if 0 <= line_idx < len(self.file_lines):
                del self.file_lines[line_idx]

        # Write the updated content back to the file
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.writelines(self.file_lines)

            # Re-parse the file to update the tasks dictionary
            self._parse_file()
            self.progress_tracker.calculate_statistics(self.file_path, self.tasks)

            deleted_names = [f"'{task_id}'" for task_id in task_ids]
            print(f"Deleted task(s): {', '.join(deleted_names)}")

        except Exception as e:
            print(f"Error deleting task(s): {e}")

    def set_status_bulk(self, task_ids: List[str], status_str: str):
        """Set the status of multiple tasks"""
        # Validate status
        try:
            new_status = TaskStatus(status_str)
        except ValueError:
            valid_statuses = [s.value for s in TaskStatus]
            print(f"Error: Invalid status '{status_str}'. Valid statuses: {valid_statuses}")
            return

        # Validate all task IDs exist
        for task_id in task_ids:
            if task_id not in self.tasks:
                print(f"Error: Task '{task_id}' not found.")
                return

        # Set status for each task
        updated_tasks = []
        for task_id in task_ids:
            task = self.tasks[task_id]
            old_status = task.status

            # Validate sub-task status change against parent (same logic as single set_status)
            if self._is_sub_task(task_id):
                parent_id = self._get_parent_task_id(task_id)
                if parent_id and parent_id in self.tasks:
                    parent_task = self.tasks[parent_id]
                    if (old_status == TaskStatus.PENDING and
                        new_status != TaskStatus.PENDING and
                        parent_task.status in [TaskStatus.PENDING, TaskStatus.DONE]):
                        print(f"Warning: Skipping task '{task_id}' - cannot change from pending to '{new_status.value}' "
                              f"while parent task '{parent_id}' is '{parent_task.status.value}'")
                        continue

            # Update the task status
            task.status = new_status
            self._update_file_status(task)

            # Record the status change in progress tracker
            self.progress_tracker.update_task_status(self.file_path, task_id, new_status, task.description)

            updated_tasks.append((task_id, old_status, new_status))

        # Recalculate statistics
        self.progress_tracker.calculate_statistics(self.file_path, self.tasks)

        # Auto-update parent tasks for all updated sub-tasks
        parent_tasks_to_check = set()
        for task_id, _, _ in updated_tasks:
            if self._is_sub_task(task_id):
                parent_id = self._get_parent_task_id(task_id)
                if parent_id:
                    parent_tasks_to_check.add(parent_id)

        # Check and update parent tasks
        for parent_id in parent_tasks_to_check:
            self._auto_update_parent_status(parent_id)

        # Report results
        if updated_tasks:
            if Colors.is_colors_enabled():
                colored_new_status = Colors.colorize_status(new_status)
            else:
                colored_new_status = new_status.value
            print(f"Updated {len(updated_tasks)} task(s) to {colored_new_status}:")
            for task_id, old_status, new_status in updated_tasks:
                if Colors.is_colors_enabled():
                    colored_old = Colors.colorize_status(old_status)
                    colored_new = Colors.colorize_status(new_status)
                    print(f"  '{task_id}': {colored_old} -> {colored_new}")
                else:
                    print(f"  '{task_id}': {old_status.value} -> {new_status.value}")
        else:
            print("No tasks were updated.")

    def _find_insert_position(self, task_id: str) -> int:
        """Find the appropriate position to insert a new task"""
        # For root level tasks (no dots), find the position after the last root task
        if '.' not in task_id:
            last_root_position = 0
            target_id = int(task_id)

            for i, line in enumerate(self.file_lines):
                task_match = re.match(r'^(\s*)-\s*\[[ \-x\+\*]\]\s*(\d+)\.?\s*', line)
                if task_match:
                    indent_str, existing_id = task_match.groups()
                    # Only consider root tasks (no indentation)
                    if len(indent_str) == 0:
                        existing_num = int(existing_id)
                        if existing_num < target_id:
                            # Find the end of this task and its sub-tasks
                            last_root_position = self._find_task_end_line_by_index(i)
                        else:
                            break

            return last_root_position

        # For sub-tasks, find position within the parent task
        parent_id = self._get_parent_task_id(task_id)
        if parent_id and parent_id in self.tasks:
            parent_task = self.tasks[parent_id]
            parent_start = parent_task.line_number
            parent_end = self._find_task_end_line(parent_id)

            # Find the last sub-task at the same level
            target_parts = task_id.split('.')
            target_num = int(target_parts[-1])

            insert_pos = parent_start  # Default to after parent task line

            for i in range(parent_start, parent_end):
                if i >= len(self.file_lines):
                    break
                line = self.file_lines[i]
                task_match = re.match(r'^(\s*)-\s*\[[ \-x\+\*]\]\s*(\d+(?:\.\d+)*)\.?\s*', line)
                if task_match:
                    indent_str, existing_id = task_match.groups()
                    existing_parts = existing_id.split('.')

                    # Check if this is a sibling (same parent, same level)
                    if (len(existing_parts) == len(target_parts) and
                        existing_parts[:-1] == target_parts[:-1]):
                        existing_num = int(existing_parts[-1])
                        if existing_num < target_num:
                            insert_pos = self._find_task_end_line_by_index(i)
                        else:
                            break

            return insert_pos

        # Fallback: append at the end
        return len(self.file_lines)

    def _find_task_end_line(self, task_id: str) -> int:
        """Find the line number where a task ends (exclusive)"""
        if task_id not in self.tasks:
            return len(self.file_lines)

        task = self.tasks[task_id]
        return self._find_task_end_line_by_index(task.line_number - 1)

    def _find_task_end_line_by_index(self, start_index: int) -> int:
        """Find where a task ends starting from a given line index"""
        if start_index >= len(self.file_lines):
            return len(self.file_lines)

        # Get the indent level of the starting task
        start_line = self.file_lines[start_index]
        task_match = re.match(r'^(\s*)-\s*\[[ \-x\+\*]\]\s*(\d+(?:\.\d+)*)\.?\s*', start_line)
        if not task_match:
            return start_index + 1

        start_indent = len(task_match.group(1))

        # Find the next task at the same or higher level
        for i in range(start_index + 1, len(self.file_lines)):
            line = self.file_lines[i]
            task_match = re.match(r'^(\s*)-\s*\[[ \-x\+\*]\]\s*(\d+(?:\.\d+)*)\.?\s*', line)
            if task_match:
                line_indent = len(task_match.group(1))
                if line_indent <= start_indent:
                    return i

        return len(self.file_lines)

    def _get_all_sub_tasks(self, task_id: str) -> List[str]:
        """Get all sub-tasks (direct and indirect) of a given task"""
        all_sub_tasks = []
        for tid in self.tasks.keys():
            if tid.startswith(task_id + '.'):
                all_sub_tasks.append(tid)
        return sorted(all_sub_tasks, key=self._sort_key)

    def filter_tasks(self, status_filter: Optional[str] = None,
                    requirements_filter: Optional[List[str]] = None,
                    dependencies_filter: Optional[List[str]] = None):
        """Filter tasks by status, requirements, or dependencies"""
        filtered_tasks = {}

        for task_id, task in self.tasks.items():
            # Filter by status
            if status_filter and task.status.value != status_filter:
                continue

            # Filter by requirements (task must have ALL specified requirements)
            if requirements_filter:
                if not all(req in task.requirements for req in requirements_filter):
                    continue

            # Filter by dependencies (task must have ALL specified dependencies)
            if dependencies_filter:
                if not all(dep in task.dependencies for dep in dependencies_filter):
                    continue

            filtered_tasks[task_id] = task

        if not filtered_tasks:
            print("No tasks match the specified filters.")
            return

        print(f"Filtered Tasks from {self.file_path}:")
        if status_filter:
            print(f"  Status: {status_filter}")
        if requirements_filter:
            print(f"  Requirements: {', '.join(requirements_filter)}")
        if dependencies_filter:
            print(f"  Dependencies: {', '.join(dependencies_filter)}")
        print("-" * 60)

        # Sort and display filtered tasks
        sorted_task_ids = sorted(filtered_tasks.keys(), key=self._sort_key)
        for task_id in sorted_task_ids:
            task = filtered_tasks[task_id]
            indent = "    " * (task.task_id.count('.'))
            print(f"{indent}{task}")

    def search_tasks(self, keywords: List[str]):
        """Search tasks by keywords in description/content"""
        matching_tasks = {}

        # Convert keywords to lowercase for case-insensitive search
        lower_keywords = [kw.lower() for kw in keywords]

        for task_id, task in self.tasks.items():
            # Search in description and full content
            search_text = f"{task.description} {task.full_content}".lower()

            # Check if any keyword matches
            if any(keyword in search_text for keyword in lower_keywords):
                matching_tasks[task_id] = task

        if not matching_tasks:
            print(f"No tasks found containing keywords: {', '.join(keywords)}")
            return

        print(f"Search Results from {self.file_path}:")
        print(f"  Keywords: {', '.join(keywords)}")
        print("-" * 60)

        # Sort and display matching tasks
        sorted_task_ids = sorted(matching_tasks.keys(), key=self._sort_key)
        for task_id in sorted_task_ids:
            task = matching_tasks[task_id]
            indent = "    " * (task.task_id.count('.'))
            print(f"{indent}{task}")

    def ready_tasks(self):
        """Show only tasks that are ready to work on"""
        ready_tasks = {}

        for task_id, task in self.tasks.items():
            # Only consider pending tasks
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are satisfied
            dependencies_satisfied = True
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    dependencies_satisfied = False
                    break
                dep_task = self.tasks[dep_id]
                if dep_task.status not in [TaskStatus.DONE, TaskStatus.REVIEW]:
                    dependencies_satisfied = False
                    break

            # For sub-tasks, also check if parent allows progression
            if self._is_sub_task(task_id):
                parent_id = self._get_parent_task_id(task_id)
                if parent_id and parent_id in self.tasks:
                    parent_task = self.tasks[parent_id]
                    # Sub-task can only be worked on if parent is not pending or done
                    if parent_task.status in [TaskStatus.PENDING, TaskStatus.DONE]:
                        dependencies_satisfied = False

            if dependencies_satisfied:
                ready_tasks[task_id] = task

        if not ready_tasks:
            print("No tasks are ready to work on (all dependencies not satisfied or parent constraints).")
            return

        print(f"Ready Tasks from {self.file_path}:")
        print("-" * 60)

        # Sort and display ready tasks
        sorted_task_ids = sorted(ready_tasks.keys(), key=self._sort_key)
        for task_id in sorted_task_ids:
            task = ready_tasks[task_id]
            indent = "    " * (task.task_id.count('.'))
            print(f"{indent}{task}")

    def export_json(self, output_file: Optional[str] = None):
        """Export task data to JSON format"""
        export_data = {
            "file_path": self.file_path,
            "export_timestamp": datetime.now().isoformat(),
            "statistics": self.progress_tracker.get_statistics(self.file_path),
            "tasks": {}
        }

        # Export all task data
        for task_id, task in self.tasks.items():
            task_data = {
                "id": task.task_id,
                "description": task.description,
                "status": task.status.value,
                "requirements": task.requirements,
                "dependencies": task.dependencies,
                "line_number": task.line_number,
                "indent_level": task.indent_level,
                "full_content": task.full_content,
                "is_sub_task": self._is_sub_task(task_id),
                "parent_task": self._get_parent_task_id(task_id) if self._is_sub_task(task_id) else None,
                "sub_tasks": self._get_sub_tasks(task_id) if self._has_sub_tasks(task_id) else [],
                "status_history": self.progress_tracker.get_task_history(self.file_path, task_id)
            }
            export_data["tasks"][task_id] = task_data

        # Write to file or stdout
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                print(f"Exported task data to {output_file}")
            except Exception as e:
                print(f"Error writing to file {output_file}: {e}")
        else:
            # Print to stdout
            print(json.dumps(export_data, indent=2, ensure_ascii=False))



def validate_task_id(task_id: str) -> bool:
    """
    Validate that a task ID follows the correct format: digits with optional dot-separated hierarchy.
    Valid formats: "1", "1.2", "1.2.3", etc.

    Args:
        task_id: The task ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not task_id or not isinstance(task_id, str):
        return False

    # Pattern: start with digit, then optionally dot and digit, repeating
    pattern = r'^\d+(\.\d+)*$'
    return bool(re.match(pattern, task_id.strip()))


def validate_task_ids(task_ids: List[str]) -> tuple[bool, Optional[str]]:
    """
    Validate a list of task IDs.

    Args:
        task_ids: List of task IDs to validate

    Returns:
        tuple: (is_valid: bool, error_message: Optional[str])
    """
    if not task_ids:
        return False, "No task IDs provided"

    for task_id in task_ids:
        if not validate_task_id(task_id):
            return False, f"Invalid task ID format: '{task_id}'. Expected format: digits with optional dots (e.g., '1', '1.2', '1.2.3')"

    return True, None


def detect_file_path_in_args(args, tasks_local_data: Optional[Dict] = None) -> tuple[Optional[str], object]:
    """
    Detect if any string argument is actually a file path that exists in .tasks.local.json.
    If found, return the detected file path and update args to remove it from other fields.

    Args:
        args: Parsed arguments object
        tasks_local_data: Optional pre-loaded .tasks.local.json data

    Returns:
        tuple: (detected_file_path: Optional[str], updated_args: object)
    """
    # Load .tasks.local.json if not provided
    if tasks_local_data is None:
        tasks_local_file = ".tasks.local.json"
        if not os.path.exists(tasks_local_file):
            return None, args

        try:
            with open(tasks_local_file, 'r', encoding='utf-8') as f:
                tasks_local_data = json.load(f)
        except (json.JSONDecodeError, Exception):
            return None, args

    if not tasks_local_data:
        return None, args

    # Get absolute paths from .tasks.local.json for comparison
    known_file_paths = set()
    for file_path in tasks_local_data.keys():
        known_file_paths.add(os.path.abspath(file_path))
        known_file_paths.add(file_path)  # Also add original path

    # Check different argument fields that could contain a mistaken file path
    detected_file_path = None

    # Check task_id field (for show-task command)
    if hasattr(args, 'task_id') and args.task_id:
        abs_path = os.path.abspath(args.task_id)
        if abs_path in known_file_paths or args.task_id in known_file_paths:
            detected_file_path = args.task_id
            args.task_id = ""  # Clear the mistaken field

    # Check description field (for add-task command)
    if hasattr(args, 'description') and args.description:
        abs_path = os.path.abspath(args.description)
        if abs_path in known_file_paths or args.description in known_file_paths:
            detected_file_path = args.description
            args.description = ""  # Clear the mistaken field

    # Check keywords field (for search-tasks command)
    if hasattr(args, 'keywords') and args.keywords:
        for i, keyword in enumerate(args.keywords):
            abs_path = os.path.abspath(keyword)
            if abs_path in known_file_paths or keyword in known_file_paths:
                detected_file_path = keyword
                # Remove this keyword from the list
                args.keywords = [kw for j, kw in enumerate(args.keywords) if j != i]
                break

    # Check task_ids field (for set-status, delete-task commands)
    if hasattr(args, 'task_ids') and args.task_ids:
        for i, task_id in enumerate(args.task_ids):
            abs_path = os.path.abspath(task_id)
            if abs_path in known_file_paths or task_id in known_file_paths:
                detected_file_path = task_id
                # Remove this item from task_ids
                args.task_ids = [tid for j, tid in enumerate(args.task_ids) if j != i]
                break

    return detected_file_path, args


def resolve_file_path(file_argument: str, is_running_as_claude_hook: bool) -> str:
    """
    Resolve the file path argument. If file_argument is empty or None,
    automatically select the task file with the most recent last_modified
    from .tasks.local.json.

    Args:
        file_argument: The file path argument from command line
        is_running_as_claude_hook: True indicate this CLI is being used as claude hook script

    Returns:
        str: The resolved file path

    Raises:
        SystemExit: If .tasks.local.json doesn't exist or is empty when needed
    """
    # If file argument is provided and not empty, use it as-is
    if file_argument and file_argument.strip():
        return file_argument.strip()
    # Define a fail fast mechanism to be used to exit with code 0 when running as claude hook
    failfastFunc = lambda: sys.exit(0) if is_running_as_claude_hook else None

    # Try to read .tasks.local.json
    tasks_local_file = ".tasks.local.json"
    if not os.path.exists(tasks_local_file):
        failfastFunc()
        print(f"Error: .tasks.local.json file not found. Please provide a valid file path to a tasks.md file.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(tasks_local_file, 'r', encoding='utf-8') as f:
            tasks_data = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        failfastFunc()
        print(f"Error: Could not read .tasks.local.json: {e}. Please provide a valid file path to a tasks.md file.", file=sys.stderr)
        sys.exit(1)

    # Check if the data is empty
    if not tasks_data or tasks_data == {}:
        failfastFunc()
        print(f"Error: .tasks.local.json is empty. Please provide a valid file path to a tasks.md file.", file=sys.stderr)
        sys.exit(1)

    # Find the entry with the most recent last_modified timestamp
    most_recent_file = None
    most_recent_timestamp = None

    for file_path, file_data in tasks_data.items():
        if not isinstance(file_data, dict) or 'last_modified' not in file_data:
            continue

        # Skip files that don't exist on the filesystem
        if not os.path.exists(file_path):
            continue

        try:
            timestamp_str = file_data['last_modified']
            # Parse ISO format timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            if most_recent_timestamp is None or timestamp > most_recent_timestamp:
                most_recent_timestamp = timestamp
                most_recent_file = file_path
        except (ValueError, TypeError):
            # Skip entries with invalid timestamps
            continue

    if most_recent_file is None:
        failfastFunc()
        print(f"Error: No valid task files found in .tasks.local.json. Please provide a valid file path to a tasks.md file.", file=sys.stderr)
        sys.exit(1)

    print(f"Auto-selected task file: {most_recent_file}")
    return most_recent_file


def main():
    parser = argparse.ArgumentParser(
        description='Task List MD CLI - Parse and manage hierarchical tasks list from markdown files (tasks.md)',
        epilog='Examples:\n'
               '  %(prog)s list-tasks tasks.md\n'
               '  %(prog)s show-task tasks.md 2.1\n'
               '  %(prog)s set-status tasks.md 2.1 2.2 "done"\n'
               '  %(prog)s filter-tasks tasks.md --status pending --requirements "FR1"\n'
               '  %(prog)s export tasks.md --output tasks.json',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available task management commands')

    # List tasks command
    list_parser = subparsers.add_parser('list-tasks',
        help='Display all tasks in hierarchical order with colored status indicators')
    list_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks (e.g., tasks.md, project-tasks.md). If not specified, automatically selects the most recently modified file from .tasks.local.json')

    # Show task command
    show_parser = subparsers.add_parser('show-task',
        help='Show detailed information about a specific task including sub-tasks and dependencies')
    show_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    show_parser.add_argument('task_id',
        help='Task ID to display details for (e.g., "1", "2.1", "3.2.1" for hierarchical tasks)')

    # Set status command (updated to support multiple task IDs)
    status_parser = subparsers.add_parser('set-status',
        help='Update the status of one or more tasks with automatic parent task updates')
    status_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    status_parser.add_argument('task_ids', nargs='+',
        help='One or more task IDs to update (e.g., "1" or "1.1 1.2 1.3" for bulk updates)')
    status_parser.add_argument('status',
        help='New status to set for the specified task(s). Available statuses map to checkboxes: '
             'pending [ ], in-progress [-], done [x], review [+], deferred [*]',
        choices=[s.value for s in TaskStatus])

    # Add task command
    add_parser = subparsers.add_parser('add-task',
        help='Create a new task with optional dependencies and requirements')
    add_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file where the task will be added. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    add_parser.add_argument('task_id',
        help='Unique identifier for the new task (e.g., "1" for root task, "1.1" for sub-task, "1.1.1" for nested sub-task)')
    add_parser.add_argument('description',
        help='Brief description of what the task involves (will be displayed after the task ID)')
    add_parser.add_argument('--dependencies', nargs='*',
        help='List of task IDs that must be completed before this task can start (e.g., --dependencies "1" "2.1")')
    add_parser.add_argument('--requirements', nargs='*',
        help='List of requirements or tags associated with this task (e.g., --requirements "FR1" "NFR1")')

    # Update task command
    update_parser = subparsers.add_parser('update-task',
        help='Update dependencies and requirements of an existing task')
    update_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing the task to update. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    update_parser.add_argument('task_id',
        help='Task ID to update (e.g., "1", "2.1", "3.2.1" for hierarchical tasks)')
    update_parser.add_argument('--add-dependencies', nargs='*',
        help='Add new dependencies to the task (e.g., --add-dependencies "1" "2.1")')
    update_parser.add_argument('--add-requirements', nargs='*',
        help='Add new requirements to the task (e.g., --add-requirements "FR1" "NFR1")')
    update_parser.add_argument('--remove-dependencies', nargs='*',
        help='Remove specific dependencies from the task (e.g., --remove-dependencies "1" "2.1")')
    update_parser.add_argument('--remove-requirements', nargs='*',
        help='Remove specific requirements from the task (e.g., --remove-requirements "FR1" "NFR1")')
    update_parser.add_argument('--clear-dependencies', action='store_true',
        help='Remove all dependencies from the task')
    update_parser.add_argument('--clear-requirements', action='store_true',
        help='Remove all requirements from the task')

    # Delete task command
    delete_parser = subparsers.add_parser('delete-task',
        help='Remove one or more tasks and handle dependency cleanup automatically')
    delete_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks to delete. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    delete_parser.add_argument('task_ids', nargs='+',
        help='One or more task IDs to delete (e.g., "1" or "1.1 1.2"). Note: deleting a parent task also deletes all its sub-tasks')

    # Get next task command
    next_parser = subparsers.add_parser('get-next-task',
        help='Find the next task ready to work on based on dependencies and status')
    next_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks. If not specified, automatically selects the most recently modified file from .tasks.local.json')

    # Check dependencies command
    validate_parser = subparsers.add_parser('check-dependencies',
        help='Validate all task dependencies and detect circular references')
    validate_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks to validate. If not specified, automatically selects the most recently modified file from .tasks.local.json')

    # Show progress command
    progress_parser = subparsers.add_parser('show-progress',
        help='Display comprehensive progress report with statistics and task history')
    progress_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file to generate progress report for. If not specified, automatically selects the most recently modified file from .tasks.local.json')

    # Filter tasks command
    filter_parser = subparsers.add_parser('filter-tasks',
        help='Filter and display tasks based on status, requirements, or dependencies')
    filter_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks to filter. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    filter_parser.add_argument('--status',
        help='Filter tasks by their current status (pending, in-progress, done, review, deferred)',
        choices=[s.value for s in TaskStatus])
    filter_parser.add_argument('--requirements', nargs='*',
        help='Filter tasks that have ALL specified requirements (e.g., --requirements "FR1" "NFR1")')
    filter_parser.add_argument('--dependencies', nargs='*',
        help='Filter tasks that depend on ALL specified task IDs (e.g., --dependencies "1" "2.1")')

    # Search tasks command
    search_parser = subparsers.add_parser('search-tasks',
        help='Search for tasks containing specific keywords in descriptions or content')
    search_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks to search. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    search_parser.add_argument('keywords', nargs='+',
        help='One or more keywords to search for in task descriptions and content (case-insensitive)')

    # Ready tasks command
    ready_parser = subparsers.add_parser('ready-tasks',
        help='Show only tasks that are ready to work on (dependencies satisfied)')
    ready_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks. If not specified, automatically selects the most recently modified file from .tasks.local.json')

    # Export command
    export_parser = subparsers.add_parser('export',
        help='Export all task data and statistics to JSON format for external tools')
    export_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks to export. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    export_parser.add_argument('--output',
        help='Path to save the JSON export file. If not specified, output will be printed to stdout for piping to other commands')

    # Track progress command
    track_parser = subparsers.add_parser('track-progress',
        help='Manage completion completion conditions for tasks')
    track_subparsers = track_parser.add_subparsers(dest='track_command',
        help='Track progress sub-commands')

    # Track progress add sub-command
    track_add_parser = track_subparsers.add_parser('add',
        help='Add a completion tracking condition')
    track_add_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    track_add_parser.add_argument('task_ids', nargs='+',
        help='One or more task IDs to track for completion (e.g., "1" "2.1" "3")')
    track_add_parser.add_argument('--valid-for', default='2h',
        help='Duration the tracking condition is valid. Supports "h" (hours), "m" (minutes), "s" (seconds), or plain numbers (seconds). Default: "2h"')
    track_add_parser.add_argument('--complete-more', type=int,
        help='Additional tasks expected to be completed (added to current completed count)')

    # Track progress check sub-command
    track_check_parser = track_subparsers.add_parser('check',
        help='Check all completion conditions and report unmet ones')
    track_check_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    track_check_parser.add_argument('--claude-hook', action='store_true',
        help='Enable Claude hook mode with infinite loop detection via stdin JSON input')

    # Track progress clear sub-command
    track_clear_parser = track_subparsers.add_parser('clear',
        help='Clear all completion conditions')
    track_clear_parser.add_argument('file', nargs='?', default='',
        help='Path to the markdown file containing tasks. If not specified, automatically selects the most recently modified file from .tasks.local.json')
    track_clear_parser.add_argument('--yes', action='store_true',
        help='Skip confirmation prompt and clear immediately')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Detect if any string argument is actually a file path from .tasks.local.json
    detected_file_path, args = detect_file_path_in_args(args)

    # If we detected a file path in other arguments, use it to override the file argument
    if detected_file_path:
        print(f"Detected file path in arguments: {detected_file_path}")
        args.file = detected_file_path

    # Validate task IDs for commands that use them
    if hasattr(args, 'task_id'):
        if not args.task_id or not args.task_id.strip():
            print("Error: Task ID is required for this command.", file=sys.stderr)
            sys.exit(1)
        if not validate_task_id(args.task_id):
            print(f"Error: Invalid task ID format: '{args.task_id}'. Expected format: digits with optional dots (e.g., '1', '1.2', '1.2.3')", file=sys.stderr)
            sys.exit(1)

    if hasattr(args, 'task_ids') and args.task_ids:
        is_valid, error_message = validate_task_ids(args.task_ids)
        if not is_valid:
            print(f"Error: {error_message}", file=sys.stderr)
            sys.exit(1)

    # Validate that required string arguments are not empty after file path detection
    if hasattr(args, 'description') and hasattr(args, 'task_id'):  # add-task command
        if not args.description or not args.description.strip():
            print("Error: Description argument is required for add-task command.", file=sys.stderr)
            sys.exit(1)

    if hasattr(args, 'keywords') and args.keywords is not None:  # search-tasks command
        if not args.keywords or all(not kw.strip() for kw in args.keywords):
            print("Error: At least one keyword is required for search-tasks command.", file=sys.stderr)
            sys.exit(1)

    if hasattr(args, 'task_ids') and args.task_ids is not None:  # Commands with task_ids
        if not args.task_ids:
            if args.command in ['set-status', 'delete-task']:
                print(f"Error: At least one task ID is required for {args.command} command.", file=sys.stderr)
                sys.exit(1)

    # Resolve the file path (auto-select from .tasks.local.json if not provided)
    resolved_file_path = resolve_file_path(args.file, hasattr(args, 'claude_hook') and args.claude_hook)

    # Initialize task parser
    task_parser = TaskParser(resolved_file_path)

    # Execute the requested command
    if args.command == 'list-tasks':
        task_parser.list_tasks()
    elif args.command == 'show-task':
        task_parser.show_task(args.task_id)
    elif args.command == 'set-status':
        if len(args.task_ids) == 1:
            task_parser.set_status(args.task_ids[0], args.status)
        else:
            task_parser.set_status_bulk(args.task_ids, args.status)
    elif args.command == 'add-task':
        task_parser.add_task(args.task_id, args.description, args.dependencies, args.requirements)
    elif args.command == 'update-task':
        task_parser.update_task(
            args.task_id,
            add_dependencies=args.add_dependencies,
            add_requirements=args.add_requirements,
            remove_dependencies=args.remove_dependencies,
            remove_requirements=args.remove_requirements,
            clear_dependencies=args.clear_dependencies,
            clear_requirements=args.clear_requirements
        )
    elif args.command == 'delete-task':
        task_parser.delete_task(args.task_ids)
    elif args.command == 'get-next-task':
        task_parser.get_next_task()
    elif args.command == 'check-dependencies':
        task_parser.validate_dependencies()
    elif args.command == 'show-progress':
        task_parser.show_progress()
    elif args.command == 'filter-tasks':
        task_parser.filter_tasks(args.status, args.requirements, args.dependencies)
    elif args.command == 'search-tasks':
        task_parser.search_tasks(args.keywords)
    elif args.command == 'ready-tasks':
        task_parser.ready_tasks()
    elif args.command == 'export':
        task_parser.export_json(args.output)
    elif args.command == 'track-progress':
        if not hasattr(args, 'track_command') or args.track_command is None:
            print("Error: No sub-command specified for track-progress.", file=sys.stderr)
            print("Use 'track-progress add', 'track-progress check', or 'track-progress clear'.", file=sys.stderr)
            sys.exit(1)

        if args.track_command == 'add':
            try:
                condition = task_parser.progress_tracker.add_tracking_condition(
                    resolved_file_path,
                    args.task_ids,
                    args.valid_for,
                    args.complete_more,
                    task_parser.tasks
                )

                # Format confirmation message
                valid_until = condition['valid_before']
                tasks_str = ', '.join(args.task_ids)
                print(f"Added tracking condition for tasks: {tasks_str}")
                print(f"Valid until: {valid_until}")

                if 'expect_completed' in condition:
                    print(f"Expected total completed tasks: {condition['expect_completed']}")

            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        elif args.track_command == 'check':
            # Handle Claude hook mode (switch the exit_code if detect infinite hook situation)
            is_claude_hook_mode = hasattr(args, 'claude_hook') and args.claude_hook

            if is_claude_hook_mode:
                # Use exit code 1 if in Claude hook mode to prevent infinite loop
                # Use exit code 2 will make Claude continue and not stopping if hook is enabled
                hook_input = task_parser.progress_tracker.read_claude_hook_input()
                is_session_start = hook_input.get('hook_event_name') == "SessionStart"

                if hook_input.get('hook_event_name') == "Stop" and hook_input.get('stop_hook_active') is True:
                    # Check for infinite loop prevention
                    transcript_path = hook_input.get('transcript_path')

                    if transcript_path:
                        if task_parser.progress_tracker.detect_infinite_loop(transcript_path):
                            # Use exit code 1 to prevent infinite loop
                            print("Infinite loop detected in Claude hook. Exiting to prevent further execution.", file=sys.stderr)
                            # Output JSON response for Claude hook (allow Claude to stop)
                            task_parser.progress_tracker.output_claude_hook_response(block=False)
                            sys.exit(1)
                    else:
                        # No transcript path, use exit code 1 to be safe
                        print("No transcript path provided in Claude hook. Exiting to prevent potential infinite loop.", file=sys.stderr)
                        # Output JSON response for Claude hook (allow Claude to stop)
                        task_parser.progress_tracker.output_claude_hook_response(block=False)
                        sys.exit(1)

            # Proceed with normal tracking condition check
            unmet_conditions = task_parser.progress_tracker.check_tracking_conditions(
                resolved_file_path, task_parser.tasks
            )

            if unmet_conditions:
                # Build detailed reason message for Claude
                reason_parts = ["Completion conditions not met:"]
                for i, unmet in enumerate(unmet_conditions, 1):
                    condition = unmet['condition']
                    reason_parts.append(f"\nCondition {i}:")
                    reason_parts.append(f"  Required tasks: {', '.join(condition['tasks_to_complete'])}")

                    if unmet['unmet_tasks']:
                        reason_parts.append("  Issues:")
                        for issue in unmet['unmet_tasks']:
                            reason_parts.append(f"    - {issue}")

                    if unmet['total_count_issue']:
                        reason_parts.append(f"  Total count issue: {unmet['total_count_issue']}")

                reason_message = '\n'.join(reason_parts)

                if is_claude_hook_mode:
                    # Output JSON response for Claude hook (block Claude from stopping)
                    reason_message += "\n\nIMPORTANCE: Please continue working on the remaining tasks to meet the completion conditions. Task file location: " + resolved_file_path
                    if is_session_start and hook_input.get('source') == "compact":
                        reason_message += "\n\nSYSTEM: You MUST use `mcp__gosu__get_prompt` tool to retrieve the prompt with id: \"workflow-of-command-task-list-md-execute\" and follow the workflow step by steps. You should start from **Phase 2: Execute Tasks One by One**"
                    if is_session_start:
                        task_parser.progress_tracker.output_claude_hook_session_start_response(reason_message)
                    else:
                        task_parser.progress_tracker.output_claude_hook_response(block=True, reason=reason_message)
                else:
                    # Normal mode: print to stderr
                    print(reason_message, file=sys.stderr)

                sys.exit(2)
            else:
                if is_claude_hook_mode:
                    # Output JSON response for Claude hook (allow Claude to stop)
                    if is_session_start:
                        task_parser.progress_tracker.output_claude_hook_session_start_response("")
                    else:
                        task_parser.progress_tracker.output_claude_hook_response(block=False)
                else:
                    print("All completion conditions are satisfied.")

        elif args.track_command == 'clear':
            success = task_parser.progress_tracker.clear_tracking_conditions(
                resolved_file_path, force=args.yes
            )
            if not success:
                sys.exit(1)


if __name__ == '__main__':
    main()
