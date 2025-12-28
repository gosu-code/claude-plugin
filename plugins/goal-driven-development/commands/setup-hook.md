---
allowed-tools: Bash(mkdir:*), Write, Read, Edit
argument-hint: <goal-name> [--remove] [--help]
description: Setup or remove Stop hook to automatically prompt for next task from goal tasks
---

Setup or remove a Stop hook that prompts for the next task from a goal's task list. Usage: `/setup-hook <goal-name> [--remove]`

User prompt: $ARGUMENTS

When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions below and stop:

```
Usage: /setup-hook <goal-name> [--remove]

Sets up or removes a Stop hook in .claude/settings.local.json that will
automatically prompt for the next task from docs/goal/<goal-name>/tasks.md
when you stop or pause your conversation with Claude.

Options:
  --remove    Remove the Stop hook for the specified goal instead of adding it

The hook will:
  - Wait up to 60 seconds for a task to become available
  - Display the next pending task from your goal's task list
  - Help you maintain focus on goal-driven development

Examples:
  /setup-hook reliable-payments              # Add hook
  /setup-hook improve-performance            # Add hook
  /setup-hook reliable-payments --remove     # Remove hook

The goal name should match an existing goal directory created by /define-goal.
For adding a hook, the tasks.md file should exist (created by /generate-tasks).
```

## Command Execution Process

### Phase 1: Validate Arguments and Determine Action

1. **Parse command arguments**:
   - Check if $ARGUMENTS is empty or only whitespace
     - If empty, display error: "Error: Goal name is required. Usage: `/setup-hook <goal-name> [--remove]`"
     - Stop execution

   - Check if `--remove` flag is present in $ARGUMENTS
     - Set `REMOVE_MODE = true` if found
     - Set `REMOVE_MODE = false` otherwise

   - Extract the goal name from $ARGUMENTS (first non-flag word)
     - Normalize to lowercase and replace spaces with hyphens
     - Remove any special characters except hyphens and alphanumeric

2. **Validate the goal name**:
   - Must be at least 3 characters long
   - Must not contain path separators (/, \)
   - If invalid, display error with specific reason and stop

3. **Display action being taken**:
   - If `REMOVE_MODE = true`: Display "Removing Stop hook for goal '<goal-name>'..."
   - If `REMOVE_MODE = false`: Display "Setting up Stop hook for goal '<goal-name>'..."

### Phase 2: Verify Prerequisites (Skip if REMOVE_MODE = true)

**Note**: If `REMOVE_MODE = true`, skip this entire phase and proceed directly to Phase 3.

**For ADD mode only** (`REMOVE_MODE = false`):

1. Check if directory `docs/goal/<goal-name>/` exists
   - If not found, display error: "Error: Goal '\<goal-name\>' does not exist. Please create it first using `/define-goal <goal-name>`"
   - Stop execution

2. Check if `docs/goal/<goal-name>/tasks.md` exists
   - If not found, display error: "Error: Tasks file not found for goal '\<goal-name\>'. Please generate tasks first using `/generate-tasks <goal-name>`"
   - Stop execution

3. Verify task_list_md.py script exists
   - Check path: `${CLAUDE_PLUGIN_ROOT}/skills/task-list-md/scripts/task_list_md.py`
   - Resolve `${CLAUDE_PLUGIN_ROOT}` to the actual plugin directory path
     - Typically: `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core`
   - If not found, display error: "Error: task_list_md.py script not found. Please install gosu-code claude plugins: `/plugin marketplace add gosu-code/claude-plugin`"
   - Stop execution

### Phase 3: Modify settings.local.json

1. **Determine settings file path**:
   - Target file: `.claude/settings.local.json`
   - Expand tilde to user's home directory

2. **Read or initialize settings**:
   - If file exists:
     - Read the existing JSON content
     - Parse it into a JSON object
   - If file does not exist and `REMOVE_MODE = true`:
     - Display info message: "ℹ Hook already removed (settings file doesn't exist)"
     - Skip to Phase 4 (success scenario)
   - If file does not exist and `REMOVE_MODE = false`:
     - Initialize as empty JSON object: `{}`

3. **Create backup** (before any modifications):
   - If file exists, create a backup
   - Backup location: `.claude/settings.local.json.backup`
   - Include timestamp in backup for safety

4. **Check current hook status**:
   - Navigate to `hooks.Stop` array (if it exists)
   - Search for existing hook matching this goal:
     - Look for hook entries where the command contains `docs/goal/<goal-name>/tasks.md`
   - Set `HOOK_EXISTS = true` if found, otherwise `HOOK_EXISTS = false`
   - Store the index of the existing hook if found

5. **Perform action based on mode**:

   **If REMOVE_MODE = true** (removing hook):
   - If `HOOK_EXISTS = false`:
     - Display info message: "ℹ Hook already removed for goal '\<goal-name\>'"
     - Skip writing file, proceed to Phase 4 (success scenario)
   - If `HOOK_EXISTS = true`:
     - Remove the hook entry at the stored index from `hooks.Stop` array
     - If `hooks.Stop` array becomes empty after removal, remove the entire `Stop` key
     - If `hooks` object becomes empty after removal, remove the entire `hooks` key
     - Proceed to step 6 to write the file

   **If REMOVE_MODE = false** (adding/updating hook):

   **Hook structure to add**:

   ```json
   {
     "hooks": {
       "Stop": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "echo '{\"decision\":\"block\",\"reason\":\"Must run the following command ${CLAUDE_PLUGIN_ROOT}\/skills\/task-list-md\/scripts\/task_list_md.py get-next-task --wait 60m docs\/goal\/<goal-name>\/tasks.md (Do not attempt to kill\/abort the python script command. Do not read\/update the task file directly by yourself). You must patiently wait for the next task assignment from the task_list_md.py get-next-task --wait 60m command output.\"}'",
               "timeout": 10
             }
           ]
         }
       ]
     }
   }
   ```

   - If `HOOK_EXISTS = true`:
     - Display info message: "ℹ Hook already exists for goal '\<goal-name\>', updating..."
     - Update the existing hook entry with the new command (in case script path changed)
   - If `HOOK_EXISTS = false`:
     - If `hooks` field doesn't exist, create it
     - If `hooks.Stop` doesn't exist, create it as an empty array
     - Add the new hook entry to the `hooks.Stop` array
   - Preserve all other hooks in the `hooks` section (e.g., Notification, Start, etc.)
   - Preserve all other settings in the file (e.g., permissions, env, model, etc.)
   - Use proper JSON formatting with 2-space indentation

6. **Write updated settings**:
   - Convert the JSON object back to formatted JSON string
   - Write to `.claude/settings.local.json`
   - Ensure proper file permissions (readable/writable by user)

### Phase 4: Verify and Confirm

1. **Verify the operation succeeded**:

   **If REMOVE_MODE = true**:
   - Re-read the `.claude/settings.local.json` file (if it exists)
   - Confirm the Stop hook for this goal no longer exists
   - If verification fails, display error and stop

   **If REMOVE_MODE = false**:
   - Re-read the `.claude/settings.local.json` file
   - Confirm the Stop hook exists and contains the correct command
   - Confirm the goal name is correctly embedded in the command
   - If verification fails, display error and stop

2. **Display success message**:

   **If REMOVE_MODE = true**:

   ```
   ✓ Stop hook removed successfully for goal '<goal-name>'

   Details:
   - Location: .claude/settings.local.json
   - Backup saved: .claude/settings.local.json.backup

   The hook will no longer activate when you stop or pause conversations.

   To re-enable the hook, run:
   /setup-hook <goal-name>
   ```

   **If REMOVE_MODE = false**:

   ```
   ✓ Stop hook configured successfully for goal '<goal-name>'

   Hook details:
   - Location: .claude/settings.local.json
   - Task file: docs/goal/<goal-name>/tasks.md
   - Wait timeout: 60 seconds

   The hook will activate when you:
   - Type /stop or /pause in the conversation
   - Use Ctrl+C to interrupt Claude
   - End a conversation session

   Next steps:
   - Start working on tasks: Use the Stop hook to get prompted for next task
   - Generate more tasks: /generate-tasks <goal-name>
   - Review goal progress: Check completed vs pending tasks

   To remove the hook, run:
   /setup-hook <goal-name> --remove
   ```

3. **Warn about restart** (if applicable):
   - Display: "Note: You may need to restart your Claude session (type `/exit` and start again) for the hook changes to take effect."

## Output Directory

- Configuration file: `.claude/settings.local.json`
- Backup file (if created): `.claude/settings.local.json.backup`

## Interactions With Other Commands

- **Prerequisites for ADD mode**:
  - `/define-goal <goal-name>` must be run first to create the goal
  - `/generate-tasks <goal-name>` must be run to create the tasks.md file

- **Prerequisites for REMOVE mode**:
  - No prerequisites (can remove hook even if goal or tasks don't exist)

- **Related Commands**:
  - Use `/generate-tasks <goal-name>` to add more tasks as you progress
  - Use `/setup-hook <goal-name> --remove` to disable the hook when switching goals

## Interactions With Claude Subagents

- No interactions with Claude subagents

## Key Principles

1. **Non-destructive**: Never remove or modify existing hooks for other goals or features (only affects the specified goal)
2. **Idempotent**: Running the command multiple times produces consistent results:
   - ADD mode: Updates existing hook, doesn't duplicate
   - REMOVE mode: Gracefully handles already-removed hooks
3. **User-friendly**:
   - Provide clear error messages and next steps
   - Display informative messages when hook already exists/removed
   - Guide users on prerequisites and related commands
4. **Safe**:
   - Create backups before modifying existing configuration files
   - Preserve all other settings and hooks
   - Verify operations succeeded before reporting success
5. **Verifiable**: Always confirm the operation completed correctly before reporting success
6. **Flexible**: Support both adding and removing hooks with clear separation of modes
