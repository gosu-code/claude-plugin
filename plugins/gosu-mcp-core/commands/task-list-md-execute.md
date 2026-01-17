---
name: "task-list-md-execute"
argument-hint: prompt --task-file path/to/tasks.md [--session-hook session-UUID] [--max-tasks 5] [--only-tasks 1,2.1,2.3]
description: "Execute all remaining tasks defined in a markdown task file using task-list-md skill"
arguments:
  - name: "prompt"
    description: "Main prompt with optional file reference for execution context"
    required: true
    type: "string"
  - name: "task-file"
    description: "Path to the markdown task file (e.g., tasks.md)"
    required: true
    type: "string"
    flag: "--task-file"
  - name: "max-tasks"
    description: "Maximum number of tasks to execute"
    required: false
    type: "number"
    flag: "--max-tasks"
  - name: "only-tasks"
    description: "Execute only specific task IDs (comma-separated)"
    required: false
    type: "string"
    flag: "--only-tasks"
  - name: "session-hook"
    description: "Session UUID to set up automatic progress tracking hooks (Stop and SessionStart events)"
    required: false
    type: "string"
    flag: "--session-hook"
type: "claude-slash-command"
category: "command"
version: "1.0"
---

Execute all remaining tasks defined in a markdown task file. Usage: `/task-list-md-execute main prompt @path/to/prd.txt --task-file path/to/tasks.md --max-tasks 5 --only-tasks 1,2.1,2.3`
User prompt: $ARGUMENTS
When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions and stop. Do not proceed further.

0. **Instructions MUST Follow When Executing This Command**

- Check if the "task_list_md" script is available at this path `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py`
  - If not available, stop and inform user to install gosu-code claude plugins with this slash command: `/plugin marketplace add gosu-code/claude-plugin`
  - Once user confirm the above slash command has been executed successfully, check the script path again to verify.
  - If the "task_list_md" script is available, follow instructions from "task-list-md" skill.
- Do not use the following operations: `add-task`, `update-task`, `delete-task` during execution

1. **COMMAND Arguments Analysis**:

- If "$ARGUMENTS" contains `--task-file`, extract the value for [task_file_path] and use it throughout the execution.
  - If not provided, you can skip the `[task_file_path]` argument in all script commands.
- If "$ARGUMENTS" contains `--max-tasks`, extract the value for [maximum_number_of_tasks] and use it in Phase 2 to limit the number of tasks executed.
- If "$ARGUMENTS" contains `--only-tasks`, extract the value for [do_only_task_ids] and use it to only execute these specific tasks.
  - When this argument is provided, if any of the specified task IDs in [do_only_tasks_ids] are not found in the task list, you must stop execution and return an error message to the user indicating that these task IDs are not found.
- If "$ARGUMENTS" contains `--non-stop`, we will execute this COMMAND in non-stop execution mode.
- If "$ARGUMENTS" contains `--session-hook`, extract the value for [session_id] and use it in the pre-execution step to set up session hooks.
  - The session ID must be a valid UUID format (e.g., `32502be3-59b3-4176-94c4-fd851d460417`)
  - If the session ID is invalid, display an error message and stop execution.
  - This argument requires `--task-file` to also be specified (needed for hook commands).

2. **COMMAND Pre-Execution: Analyze Task List**

**Step 1: Understand Implementation Plan and Validate Task Structure**

- Use `task_list_md.py list-tasks [task_file_path]` to list all existing tasks in the markdown file
- Use `task_list_md.py check-dependencies [task_file_path]` to validate all task dependencies
  - If there are invalid dependencies, report them to the user and stop execution
- Check the overall task structure and hierarchy
  - Verify task IDs follow the hierarchical format (e.g., "1", "1.1", "1.2.3")
  - Identify any missing or incomplete task descriptions
- If the task file is empty or has major structural issues, stop the execution and return an error message to the user.

3. **COMMAND Pre-Execution: Session Hook Setup** (only when `--session-hook` is provided):

This step sets up session-scoped hooks that will automatically check task progress. These hooks activate immediately without restarting Claude Code.

**Prerequisites Check:**

- Verify `--task-file` is also provided (required for hook commands)
  - If not provided, display error: "Error: `--session-hook` requires `--task-file` to be specified."
  - Stop execution

**Step 1: Validate Session ID**

- The [session_id] must match UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- If invalid, display error: "Error: Invalid session ID format. Use `/id` to get your current session ID."
- Stop execution

**Step 2: Resolve Plugin Root Path**

- Locate the plugin root at: `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core`
- Expand `~` to the user's home directory to get absolute path
- Store as [PLUGIN_ROOT] (e.g., `/Users/username/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core`)

**Step 3: Create Session Hook File**

- Target directory: `./.claude/hooks/`
- Create directory if it doesn't exist: `mkdir -p .claude/hooks`
- Target file: `./.claude/hooks/hooks.[session_id].json`

**Session hook configuration to create:**

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "[PLUGIN_ROOT]/skills/task-list-md/scripts/task_list_md.py track-progress check --claude-hook [task_file_path]",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "[PLUGIN_ROOT]/skills/task-list-md/scripts/task_list_md.py track-progress check --claude-hook [task_file_path]",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- MUST replace `[PLUGIN_ROOT]` with the resolved absolute path from Step 2
- MUST replace `[task_file_path]` with the task file path from `--task-file` argument

**Step 4: Verify Hook Setup**

- Re-read the `./.claude/hooks/hooks.[session_id].json` file
- Confirm the Stop hook exists with the correct command
- Confirm the SessionStart hook exists with matcher "compact" and the correct command
- If verification fails, display error and stop execution
- Display success message: "Session hooks created at ./.claude/hooks/hooks.[session_id].json"

4. **COMMAND Execution Process**:

- You must use `mcp__gosu__get_prompt` tool to retrieve the prompt with id: "workflow-of-command-task-list-md-execute" to be used as the workflow of this command execution process.
- Follow the multi-phase execution process defined in the retrieved workflow, executing each phase step by step as described.
- When unable to retrieve the workflow, MUST stop execution and return an error message to the user indicating the failure to retrieve the workflow.

5. **COMMAND Non-Stop Execution Mode**:

- Follow similar to steps in normal execution mode as defined in "2. COMMAND Execution Process".
- However, in non-stop mode, when you have completed all your tasks and there is no more pending task to do, you MUST not stop the execution.
- Instead, you MUST use skill `task-list-md` to get next task with additional param `--wait 8h` to work on from the task file at [task_file_path] e.g: `task_list_md.py get-next-task --wait 8h`. Do not attempt to kill/abort the python script command. Do not read/update the task file directly by yourself. You must patiently wait for the next task assignment from the `task_list_md.py get-next-task --wait 8h` command output.
- When you receive the next task assignment, you MUST execute the task as normal follow the steps defined in the retrieved workflow.
- Repeat this process until the output of `task_list_md.py get-next-task --wait 8h` is "All tasks have been completed! No more pending tasks." or "Wait duration of 28800s expired." shown in the command output.

6. **COMMAND Output Management**:

- Progress for tasks is automatically tracked in `.tasks.local.json` by the script
- Create a reports directory if needed with `mkdir -p .claude/reports`, all reports will be saved here

7. **Interactions With Other Claude Slash Commands**:

- No interactions.

8. **Interactions With Claude Subagents**:

- Refer to the interactions defined in the "workflow-of-task-list-md-execute" workflow retrieved in Step 2.
