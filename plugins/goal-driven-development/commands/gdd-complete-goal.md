---
allowed-tools: SlashCommand, EnterPlanMode, Read, Glob
argument-hint: <goal-name> [--help]
description: Complete a goal by removing the hook and entering plan mode to work toward the goal
---

Complete work on a defined goal by removing the Stop hook and entering plan mode to systematically work through the goal. Usage: `/gdd-complete-goal <goal-name>`

User prompt: $ARGUMENTS

When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions below and stop:

```
Usage: /gdd-complete-goal <goal-name>

Completes work on a defined goal by:
  1. Removing the Stop hook for the specified goal (if set up)
  2. Entering plan mode to work toward the goal while respecting constraints
  3. Using tasks.md as the todo list for tracking progress

This command transitions from task-by-task execution (via Stop hooks) to
comprehensive goal completion in a single focused session.

Examples:
  /gdd-complete-goal reliable-payments
  /gdd-complete-goal improve-performance

The goal name should match an existing goal directory created by /gdd-define-goal.
The tasks.md file should exist (created by /gdd-generate-tasks).
```

## Command Execution Process

### Phase 1: Validate Arguments

1. **Parse command arguments**:
   - Check if $ARGUMENTS is empty or only whitespace
     - If empty, display error: "Error: Goal name is required. Usage: `/gdd-complete-goal <goal-name>`"
     - Stop execution

   - Extract the goal name from $ARGUMENTS (first non-flag word)
     - Normalize to lowercase and replace spaces with hyphens
     - Remove any special characters except hyphens and alphanumeric

2. **Validate the goal name**:
   - Must be at least 3 characters long
   - Must not contain path separators (/, \)
   - If invalid, display error with specific reason and stop

3. **Display action being taken**:
   - Display "Preparing to complete goal '<goal-name>'..."

### Phase 2: Verify Prerequisites

1. **Check if goal directory exists**:
   - Check if directory `docs/goal/<goal-name>/` exists
   - If not found, display error: "Error: Goal '<goal-name>' does not exist. Please create it first using `/gdd-define-goal <goal-name>`"
   - Stop execution

2. **Verify required files exist**:
   - Check if `docs/goal/<goal-name>/goal.md` exists
     - If not found, display error: "Error: goal.md not found for goal '<goal-name>'. Please define the goal first using `/gdd-define-goal <goal-name>`"
     - Stop execution

   - Check if `docs/goal/<goal-name>/constraints.md` exists
     - If not found, display warning: "⚠ Warning: constraints.md not found. Will proceed without constraint validation."
     - Continue execution (constraints are optional)

   - Check if `docs/goal/<goal-name>/tasks.md` exists
     - If not found, display error: "Error: tasks.md not found for goal '<goal-name>'. Please generate tasks first using `/gdd-generate-tasks <goal-name>`"
     - Stop execution

3. **Read goal context for confirmation**:
   - Read `docs/goal/<goal-name>/goal.md` to extract:
     - Goal title/name
     - Vision statement
     - Success criteria
   - Display brief summary:

     ```
     Goal: <Goal Title>
     Vision: <Brief vision statement>
     Success Criteria: <Count> criteria defined
     Tasks: docs/goal/<goal-name>/tasks.md
     ```

### Phase 3: Remove Stop Hook

1. **Invoke SlashCommand to remove hook**:
   - Use the SlashCommand tool to execute: `/gdd-setup-hook <goal-name> --remove`
   - This will:
     - Remove the Stop hook from `.claude/settings.local.json`
     - Prevent automatic task prompts when stopping/pausing
     - Allow continuous work without interruptions

2. **Handle hook removal result**:
   - If hook removal succeeds:
     - Inform "✓ Stop hook removed for goal '<goal-name>'" and continue
   - If hook removal fails or hook didn't exist:
     - Inform "ℹ No active hook found (or already removed)" and continue
   - Continue execution to Phase 4 regardless of hook status

### Phase 4: Enter Plan Mode

1. **Construct plan mode prompt**:
   - Create prompt with the following format:

     ```
     Work toward the goal defined in docs/goal/<goal-name>/goal.md while following the constraints defined in docs/goal/<goal-name>/constraints.md.

     Use docs/goal/<goal-name>/tasks.md as your todo list to track progress.

     Important guidelines:
     - Read and understand the goal vision and success criteria before starting
     - Respect all constraints defined in constraints.md
     - Follow the task list in tasks.md systematically
     - Mark tasks as complete only when all acceptance criteria are met
     - If you encounter blockers or need clarification, ask questions
     - Ensure all changes follow the "Definition of Safe Change"
     ```

2. **Invoke EnterPlanMode**:
   - Use the EnterPlanMode tool with the constructed prompt
   - This will:
     - Transition to plan mode where comprehensive planning occurs
     - Allow exploration of the codebase
     - Enable systematic work through the goal and tasks
     - Provide opportunity for user approval before implementation

3. **Display transition message**:
   - Before entering plan mode, display:

     ```
     ✓ Goal completion workflow initiated for '<goal-name>'

     Next steps:
     - Entering plan mode to design implementation approach
     - Will explore codebase and create detailed plan
     - You'll review and approve the plan before implementation begins

     Goal location: docs/goal/<goal-name>/
     Task list: docs/goal/<goal-name>/tasks.md
     ```

## Output Directory

- No files are created by this command
- Modifies: `.claude/settings.local.json` (removes Stop hook)
- Works with:
  - `docs/goal/<goal-name>/goal.md` (read-only)
  - `docs/goal/<goal-name>/constraints.md` (read-only)
  - `docs/goal/<goal-name>/tasks.md` (used as todo list in plan mode)

## Interactions With Other Commands

- **Prerequisites**:
  - `/gdd-define-goal <goal-name>` must be run first to create the goal
  - `/gdd-generate-tasks <goal-name>` must be run to create tasks.md
  - `/gdd-setup-hook <goal-name>` - must be run to setup hook to allow looping until goal completed

- **Workflow Position**:
  - This command is typically used when:
    - You want to complete a goal in a focused session
    - You've been working incrementally and want to finish
    - You want to work through multiple tasks systematically
    - You prefer plan-review-implement workflow over task-by-task

## Interactions With Claude Subagents

- **EnterPlanMode** will activate, which may use specialized subagents as needed

## Key Principles

1. **Seamless Transition**: Smoothly transition from incremental (hook-based) to comprehensive (plan mode) workflow
2. **Validation First**: Verify all prerequisites exist before starting the workflow
3. **Context Preservation**: Carry forward all goal context (vision, constraints, tasks) into plan mode
4. **User Approval**: Plan mode requires user approval before implementation, ensuring control
5. **Non-Destructive**: Only removes the hook; preserves all goal files and task progress
6. **Clear Guidance**: Provide clear messages at each transition point
7. **Flexible**: Works whether hook was set up or not (gracefully handles missing hook)
