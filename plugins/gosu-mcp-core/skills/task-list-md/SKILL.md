---
name: task-list-md
description: Parse and manage tasks list in a markdown file using checklist format (tasks.md, checklist.md)
---
# task-list-md

Using Task List MD CLI at `scripts/task_list_md.py` to Parse and manage tasks list in a markdown file

Markdown Task List Status Mapping (extend from standard checklist format):
  - [ ] -> pending (yellow)
  - [-] -> in-progress (blue)
  - [x] -> done (green)
  - [+] -> review (cyan)
  - [*] -> deferred (red)

Progress Tracking:
  Automatically creates .tasks.local.json to track:
  - Task completion percentages
  - Status change timestamps
  - Project statistics

## Examples
<file> is the path to the markdown file contain the task list

Basic Usage:
  python3 path/to/task_list_md.py list-tasks <file>
  python3 path/to/task_list_md.py show-task <file> <task_id>
  python3 path/to/task_list_md.py set-status <file> <task_id1> [task_id2...] <status>
  python3 path/to/task_list_md.py get-next-task <file>
  python3 path/to/task_list_md.py check-dependencies <file>
  python3 path/to/task_list_md.py show-progress <file>

Task Management:
  python3 path/to/task_list_md.py add-task <file> <task_id> "<description>" [--dependencies dep1 dep2] [--requirements req1 req2]
  python3 path/to/task_list_md.py update-task <file> <task_id> [--add-dependencies dep1 dep2] [--add-requirements req1 req2] [--remove-dependencies dep1] [--remove-requirements req1] [--clear-dependencies] [--clear-requirements]
  python3 path/to/task_list_md.py delete-task <file> <task_id1> [task_id2...]

Advanced Filtering & Search:
  python3 path/to/task_list_md.py filter-tasks <file> [--status pending] [--requirements req1] [--dependencies dep1]
  python3 path/to/task_list_md.py search-tasks <file> keyword1 [keyword2...]
  python3 path/to/task_list_md.py ready-tasks <file>

Export:
  python3 path/to/task_list_md.py export <file> [--output filename.json]

