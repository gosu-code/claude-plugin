---
allowed-tools: Bash(mkdir:*), Write, Read, Edit
argument-hint: <goal-name> <session-id> [--help]
description: Setup session hooks and start working toward the goal immediately
---

Setup session hooks for goal-driven development and immediately start working on the first task. Usage: `/gdd:start-working <goal-name> <session-id>`

User prompt: $ARGUMENTS

When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions below and stop:

```
Usage: /gdd:start-working <goal-name> <session-id>

Sets up session-scoped hooks and immediately starts working toward the goal.
Creates a session hook file with Stop and SessionStart hooks, then
begins working on tasks from docs/goal/<goal-name>/tasks.md using `task-list-md` skill

Arguments:
  <goal-name>   Name of the goal (must match existing goal directory)
  <session-id>  Current session ID (UUID format, use /id to find it)

The command will:
  1. Set up a Stop hook that blocks until you get the next task
  2. Set up a SessionStart hook for task status tracking
  3. Read goal.md and constraints.md to understand the goal
  4. Get and start working on the first pending task

The hooks will:
  - Block stopping until you run the get-next-task command
  - Help you maintain focus on goal-driven development
  - Activate immediately (no restart required)
  - Auto-expire when session ends or ID changes

Examples:
  /gdd:start-working reliable-payments abc12345-1234-5678-9abc-def012345678
  /gdd:start-working improve-performance 32502be3-59b3-4176-94c4-fd851d460417

The goal name should match an existing goal directory created by /gdd:define-goal.
The tasks.md file should exist (created by /gdd:generate-tasks).

To remove the hooks, simply delete the session hook file:
  rm .claude/hooks.<session-id>.json
```

## Command Execution Process

### Phase 1: Validate Arguments

1. **Parse command arguments**:
   - Check if $ARGUMENTS has at least 2 arguments (goal-name and session-id)
     - If missing arguments, display error: "Error: Both goal name and session ID are required. Usage: `/gdd:start-working <goal-name> <session-id>`"
     - Stop execution

   - Extract the `<goal-name>` from first argument: $1
     - Normalize to lowercase and replace spaces with hyphens
     - Remove any special characters except hyphens and alphanumeric

   - Extract the `<session-id>`from second argument: $2
     - Must be a valid UUID format (e.g., `32502be3-59b3-4176-94c4-fd851d460417`)

2. **Validate the goal name**:
   - Must be at least 3 characters long
   - Must not contain path separators (/, \)
   - If invalid, display error with specific reason and stop

3. **Validate the session ID**:
   - Must match UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - If invalid, display error: "Error: Invalid session ID format. Use `/id` to get your current session ID."
   - Stop execution

4. **Display action being taken**:
   - Display "Setting up session hooks and starting work on goal '<goal-name>' (session: <session-id>)..."

### Phase 2: Verify Prerequisites

1. Check if directory `docs/goal/<goal-name>/` exists
   - If not found, display error: "Error: Goal '\<goal-name\>' does not exist. Please create it first using `/gdd:define-goal <goal-name>`"
   - Stop execution

2. Check if `docs/goal/<goal-name>/tasks.md` exists
   - If not found, display error: "Error: Tasks file not found for goal '\<goal-name\>'. Please generate tasks first using `/gdd:generate-tasks <goal-name>`"
   - Stop execution

3. Verify task_list_md.py script exists
   - Check path: `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py`
   - Expand `~` to the user's home directory to get absolute path
   - If not found, display error: "Error: task_list_md.py script not found. Please install gosu-code claude plugins: `/plugin marketplace add gosu-code/claude-plugin`"
   - Stop execution
   - Store the resolved absolute path as `<SCRIPT_PATH>` for use in Phase 3 (e.g., `/Users/username/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py`)

### Phase 3: Create Session Hook File

1. **Determine session hook file path**:
   - Target file: `./.claude/hooks.<session-id>.json`
   - Create `.claude` directory if it doesn't exist: `mkdir -p .claude`

2. **Create session hook configuration**:

   **Session hook structure to create**:

   ```json
   {
     "hooks": {
       "Stop": [
         {
           "hooks": [
             {
               "type": "json",
               "json": {
                 "decision": "block",
                 "reason": "Must run the following command: `<SCRIPT_PATH> get-next-task --wait 1h docs/goal/<goal-name>/tasks.md` (Do not attempt to kill/abort the python script command. Do not read/update the task file directly by yourself). You must patiently wait for the next task assignment from the command output."
               }
             }
           ]
         }
       ],
       "SessionStart": [
         {
           "matcher": "compact",
           "hooks": [
             {
               "type": "json",
               "json": {
                 "hookSpecificOutput": {
                   "hookEventName": "SessionStart",
                   "additionalContext": "<system-prompt>Read & understand the `goal.md` and `constraints.md` in the `docs/goal/<goal-name>/` directory before you do any task. Use script `<SCRIPT_PATH>` to change task status as you progress. Start working: \"pending\" -> \"in-progress\", Completion: \"in-progress\" -> \"review\". After complete a task, use subagent `general-purpose` to verify and evaluate the true status of the task. Run the subagent in background then once its finish, update the task status according to the result from subagent. Mark \"review\" task as \"done\" only when it is truly completed. If all remaining tasks are completed or there is no more pending tasks, must run SlashCommand `/gdd:generate-tasks <goal-name>`</system-prompt>"
                 }
               }
             }
           ]
         }
       ]
     }
   }
   ```

   - MUST replace `<goal-name>` with the actual goal name from arguments
   - MUST replace `<SCRIPT_PATH>` with the resolved absolute path from Phase 2 step 3
   - Refer to skill `session-hook` as needed to create a valid temporary session hook configuration

### Phase 4: Verify Hook Setup

1. **Verify the operation succeeded**:
   - Re-read the `./.claude/hooks.<session-id>.json` file
   - Confirm the Stop hook exists and contains the correct details
   - Confirm the SessionStart hook exists and contains the correct details
   - If verification fails, display error and stop execution

### Phase 5: Start Working Toward the Goal

1. **Understand Goal & Constraints**

- Read the `goal.md` and `constraints.md` in the `docs/goal/<goal-name>/` directory
- Run: `<SCRIPT_PATH> get-next-task docs/goal/<goal-name>/tasks.md` to pick up a first task to work on
- Do not read/update the task file directly by yourself. Always use `task_list_md.py` script to do so

2. **Start Working**

- Use `<SCRIPT_PATH>` to change task status as you progress:
  - Start working: `<SCRIPT_PATH> set-status docs/goal/<goal-name>/tasks.md <task-id> in-progress`
  - Completion: `<SCRIPT_PATH> set-status docs/goal/<goal-name>/tasks.md <task-id> review`
- After complete a task, use subagent `general-purpose` to verify and evaluate the true status of the task. Run the subagent in background then once its finish, update the task status according to the result from subagent. Mark "review" task as "done" only when it is truly completed
- If all remaining tasks are completed or there is no more pending tasks, must run SlashCommand `/gdd:generate-tasks <goal-name>`
- Else, must run `<SCRIPT_PATH> get-next-task --wait 1h docs/goal/<goal-name>/tasks.md`. You must patiently wait for the next task assignment from the command output

**Note**: `<SCRIPT_PATH>` is the resolved absolute path from Phase 2 step 3 (e.g., `/Users/username/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py`)

## Output Directory

- Session hook file: `./.claude/hooks.<session-id>.json`

## Interactions With Other Commands

- **Prerequisites**:
  - `/gdd:define-goal <goal-name>` must be run first to create the goal
  - `/gdd:generate-tasks <goal-name>` must be run to create the tasks.md file

- **Related Commands**:
  - Use `/gdd:generate-tasks <goal-name>` to add more tasks as you progress

## Interactions With Claude Subagents

- Uses subagent `general-purpose` to verify and evaluate task completion status (run in background)

## Key Principles

1. **Session-scoped**: Hook is tied to specific session ID, auto-expires when session ends
2. **Immediate activation**: No restart required, hook takes effect instantly and work begins immediately
3. **Non-destructive**: Creates a new session-specific file, doesn't modify global settings
4. **Idempotent**: Running the command multiple times overwrites the same session hook file
5. **User-friendly**:
   - Provide clear error messages and next steps
   - Guide users on prerequisites and related commands
6. **Safe**:
   - Session hooks are isolated from permanent configuration
   - Easy to remove by deleting the file
7. **Verifiable**: Always confirm the operation completed correctly before reporting success
8. **Goal-focused**: Immediately starts working toward the goal after setup
