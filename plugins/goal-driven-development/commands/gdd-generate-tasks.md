---
argument-hint: <goal-name> [--help]
description: "Generate up to 5 small, specific, actionable tasks with clear expectations to work toward a defined goal"
arguments:
  - name: "goal-name"
    description: "Name of the goal (must match a directory in docs/goal/)"
    required: true
    type: "string"
tools:
  - "Bash(python3 ~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py:*)"
  - "Bash(git add:*)"
type: "claude-slash-command"
category: "command"
version: "1.0"
---

Generate up to 5 small, specific, actionable tasks with clear expectations to work toward a defined goal. Usage: `/gdd-generate-tasks <goal-name>`

User prompt: $ARGUMENTS

When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions and stop. Do not proceed further.

```
Usage: /gdd-generate-tasks <goal-name>

Generates up to 5 small, specific, actionable tasks with clear expectations to progress
toward the specified goal. Each task MUST be:
  - Small scope: Can be completed in a focused work session
  - Specific: Well-defined with concrete deliverables
  - Actionable: Clear what needs to be done
  - Clear expectations: Unambiguous acceptance criteria

Reads from docs/goal/<goal-name>/goal.md and constraints.md to create focused tasks.

Examples:
  /gdd-generate-tasks reliable-payments
  /gdd-generate-tasks improve-performance

The goal name should match an existing goal directory created by /gdd-define-goal.
```

## Command Execution Process

### Phase 1: Validate Arguments and Load Goal

1. **Validate Arguments**:
   - Check if $ARGUMENTS is empty or only whitespace
     - If empty, display error: "Error: Goal name is required. Usage: `/gdd-generate-tasks <goal-name>`"
     - Stop execution

   - Extract the goal name from $ARGUMENTS (first word)
   - Normalize to lowercase and replace spaces with hyphens

2. **Check Goal Existence**:
   - Verify that `docs/goal/<goal-name>/` directory exists
   - Check that both `goal.md` and `constraints.md` files exist
   - If the goal doesn't exist, display error: "Error: Goal '<goal-name>' not found. Please create it first using `/gdd-define-goal <goal-name>`"
   - Stop execution if goal not found

   - **Check for Existing Tasks**:
     - Check if `docs/goal/<goal-name>/tasks.md` already exists
     - If it exists:
       - Read the existing tasks.md file
       - Parse and extract all existing task IDs, titles, and descriptions
       - Store this information for duplicate detection in Phase 2
       - Note: New tasks will be ADDED to the existing file, not replace it

3. **Load Goal Context**:
   - Read `docs/goal/<goal-name>/goal.md` to understand:
     - Vision: What success looks like
     - Success Criteria: Observable outcomes
     - Context: Why this goal matters
     - Scope: What's in and out of scope

   - Read `docs/goal/<goal-name>/constraints.md` to understand:
     - Tech Stack & Libraries allowed
     - Timeline & Cadence requirements
     - Security & Compliance rules
     - Performance Targets
     - "Don't Touch" Areas
     - Definition of "Safe Change"
     - Additional Constraints

4. **Analyze Current Codebase State Using Explore Subagent**:

   **CRITICAL**: Use the `Explore` subagent (via Task tool with subagent_type='Explore') to thoroughly understand the current state of the codebase before generating tasks. This ensures tasks are grounded in reality.

   - **Launch Explore Subagent** with thoroughness level "medium" or "very thorough":

     ```text
     Prompt for Explore subagent:
     "Analyze the current codebase to understand the state relevant to the goal: <goal-name>

     Based on the goal definition in docs/goal/<goal-name>/goal.md:
     - Vision: [paste vision from goal.md]
     - Success Criteria: [paste success criteria from goal.md]
     - Scope: [paste scope from goal.md]

     Please explore the codebase and provide:
     1. Current Implementation State:
        - What components/modules exist that relate to this goal?
        - What's the current architecture and patterns used?
        - What functionality is already implemented?

     2. Gap Analysis:
        - What's missing compared to the success criteria?
        - What needs improvement or refactoring?
        - What technical debt exists in related areas?

     3. Constraint Validation:
        - What code areas should NOT be touched (from constraints.md)?
        - What technologies/patterns are currently in use?
        - Are there any conflicts with the defined constraints?

     4. Actionable Insights:
        - What are the most impactful areas to work on first?
        - What dependencies exist between components?
        - What quick wins could move us toward the goal?

     Be specific: mention actual file paths, function names, and code patterns you find."
     ```

   - **Analyze Explore Results**:
     - Review the comprehensive codebase analysis from the Explore subagent
     - Identify concrete, specific areas that need work
     - Map findings to goal success criteria
     - Note any "Don't Touch" areas identified
     - Understand architectural constraints and patterns

   - **Document Key Findings**:
     - Create mental notes (or brief summary) of:
       - Existing components and their state
       - Specific gaps preventing goal achievement
       - Technical dependencies and blockers
       - Priority areas based on impact and feasibility

### Phase 2: Generate Goal-Aligned Tasks Based on Codebase Analysis

1. **Retrieve Task Creation Guidelines**:
   - Retrieve the "task-list-creation-guideline" prompt using `mcp__gosu__get_prompt` tool
   - This provides the structure and format for creating quality tasks

2. **Synthesize Findings**:
   - Combine insights from:
     - Goal definition (vision, success criteria, scope)
     - Constraints (tech stack, don't touch areas, safe change definition)
     - Explore subagent analysis (current state, gaps, opportunities)
     - **Existing tasks** (if tasks.md already exists - what's already planned/done)

   - Identify the most impactful, concrete next steps based on:
     - What the codebase exploration revealed as high-priority gaps
     - Which success criteria are furthest from being met
     - Which changes would be "safe" per constraint definitions
     - What dependencies exist between potential tasks
     - **What's NOT already covered by existing tasks** (avoid duplication)

3. **Verify Completed Tasks** (if tasks.md exists):

   **IMPORTANT**: If existing tasks.md has tasks marked as done [x], verify they are actually complete based on codebase analysis.

   - **For each task marked as done [x] in existing tasks.md**:

     - **Extract Task Details**:
       - Read the task's description, acceptance criteria, and expected deliverables
       - Identify specific files, functions, or components mentioned in the task
       - Understand what "done" means for this task

     - **Verify Against Codebase** (using Explore subagent findings):
       - Check if the files/functions mentioned in the task exist and contain the expected changes
       - Verify acceptance criteria are actually met in the current codebase
       - Look for evidence of implementation (code changes, tests, documentation)
       - Cross-reference with Explore subagent findings about current implementation state

     - **Determine Actual Status**:
       - ✅ **Truly Complete**: Implementation exists, acceptance criteria met, tests pass
       - 🟡 **Partially Complete**: Some work done but acceptance criteria not fully met
       - ❌ **Not Complete**: No evidence of implementation or acceptance criteria not met
       - ⚠️ **Regressed**: Was completed but changes have been reverted or broken

     - **Update Task Status**:
       - If task is **Truly Complete**: Keep [x] status, no changes needed
       - If task is **Partially Complete**, **Not Complete**, or **Regressed**:
         - Update task status from [x] to [ ] (mark as incomplete)
         - Add a note to the task explaining why it was marked incomplete:

           ```markdown
           > **Status Update (YYYY-MM-DD)**: Task was marked as done but verification shows:
           > - [Specific reason why it's not complete based on codebase analysis]
           > - Acceptance criteria not fully met: [details]
           ```

         - Use Edit tool to update the tasks.md file with corrected status

   - **Summary of Verification**:
     - Count how many tasks were verified as truly complete
     - Count how many tasks were marked incomplete (with reasons)
     - This information will be displayed to the user later

4. **Evaluate Goal Achievement Status**:

   **CRITICAL**: Before generating any tasks, evaluate if the goal is already achieved.

   - **Compare Current State vs Success Criteria**:
     - Review each success criterion from goal.md
     - Based on Explore subagent findings, determine if each criterion is:
       - ✅ **Fully Satisfied**: Current implementation meets this criterion completely
       - 🟡 **Partially Satisfied**: Some progress, but gaps remain
       - ❌ **Not Satisfied**: Criterion not met or significant work needed

   - **Assess Improvement Potential**:
     - For each satisfied criterion, check if meaningful improvements are still possible
     - Consider if improvements would provide significant value vs being marginal tweaks
     - Evaluate if improvements align with constraints and "safe change" definition

   - **Decision Point**:
     - **If ALL success criteria are fully satisfied AND no meaningful improvements are possible**:
       - Stop task generation immediately
       - Display congratulatory message: "🎉 Congratulations! All success criteria for goal `<goal-name>` are already satisfied!"
       - Show summary of satisfied criteria
       - Suggest user review the goal or define a new goal
       - **Exit command - DO NOT generate any tasks**

     - **If ANY success criteria are not satisfied OR meaningful improvements are possible**:
       - Continue to task generation (next step)
       - Prioritize tasks based on which criteria need the most work
       - Consider verified incomplete tasks from Step 3 when planning new tasks

5. **Generate Small, Specific, Actionable Tasks**:

   **NOTE**: This step is only reached if Step 4 determined that tasks are still needed (i.e., not all success criteria are satisfied).

   **CRITICAL LIMITATION - Task Capacity Control**:
   - Calculate how many tasks were updated from [x] to [ ] in Step 3 (let's call this `reverted_count`)
   - **If `reverted_count >= 5`**:
     - DO NOT generate any new tasks
     - Display message: "⚠️ Task capacity reached: {reverted_count} tasks were marked incomplete and need to be completed first. Focus on completing these tasks before generating new ones."
     - Skip to Phase 3 (Validation)
     - **Exit this step - DO NOT generate any tasks**

   - **If `reverted_count < 5`**:
     - Calculate maximum new tasks: `max_new_tasks = 5 - reverted_count`
     - Generate UP TO `max_new_tasks` new tasks (not more)
     - This ensures: (new tasks + reverted tasks) ≤ 5
     - Display message: "ℹ️ Generating up to {max_new_tasks} new tasks ({reverted_count} tasks were marked incomplete)"

   **IMPORTANT**: If tasks.md already exists, generate NEW tasks that complement existing ones. Do NOT duplicate existing tasks. Consider tasks marked incomplete in Step 3 when generating new tasks.

   **CRITICAL REQUIREMENTS - Each task MUST be:**

   - **Small Scope**:
     - Can be completed in a single focused work session (2-4 hours max)
     - Touches minimal number of files (ideally 1-3 files)
     - Has a single, clear objective
     - Does NOT try to solve multiple problems at once

   - **Specific**:
     - Concrete deliverable (e.g., "Add error handling to payment.processRefund()" not "Improve error handling")
     - Well-defined boundaries (exactly which files, functions, or components)
     - No vague language like "improve", "enhance", "optimize" without specifics

   - **Actionable**:
     - Clear what code needs to be written/modified
     - No research-only tasks unless they have concrete output (e.g., "Document findings in X.md")
     - Includes implementation details or approach

   - **Clear Expectations**:
     - Unambiguous acceptance criteria (how to verify it's done)
     - Expected behavior is defined (input → output)
     - Definition of "complete" is obvious
     - Success is measurable/testable

   **Task Generation Guidelines** (informed by Explore subagent findings):
   - Create tasks based on ACTUAL codebase state revealed by exploration:
     - Reference specific files, functions, and components found by Explore subagent
     - Address specific gaps identified in the codebase analysis
     - Build on existing patterns and architecture discovered
     - Avoid duplicating functionality that already exists

   - **Duplicate Detection** (if tasks.md already exists):
     - Compare each new task against ALL existing tasks
     - A task is a duplicate if it:
       - Has the same or very similar title
       - Targets the same files/functions/components
       - Has the same objective or deliverable
     - If a potential task is a duplicate, either:
       - Skip it entirely and generate a different task
       - Modify it to address a different aspect or component
     - NEVER add tasks that are already in the existing tasks.md file

   - Ensure each task:
     - Aligns with the goal's vision and success criteria
     - Respects all constraints defined in constraints.md
     - Represents meaningful progress toward the goal
     - Follows the "Definition of Safe Change" (tests, reviews, documentation)
     - Is grounded in actual code locations (not hypothetical)
     - **Is NOT a duplicate of any existing task** (critical requirement)
     - **Addresses unsatisfied or partially satisfied success criteria** (from Step 3 evaluation)

   - Prioritize tasks by:
     - **Which success criteria are not yet satisfied** (highest priority)
     - Impact on success criteria (even small tasks should move the needle)
     - Findings from Explore subagent (quick wins, high-impact areas)
     - Dependencies between tasks (discovered during exploration)
     - Risk level (respect "Don't Touch" areas identified)
     - Alignment with timeline constraints

   **Examples of GOOD tasks** (small, specific, actionable, clear, grounded in real code):
   - "Add email format validation to User.validateEmail() in pkg/models/user.go with test cases"
   - "Extract database connection logic from api/server.go:45-78 into new db/connection.go"
   - "Write integration test for POST /api/checkout endpoint in api/handlers/checkout_test.go with mock payment gateway"
   - "Refactor error handling in payment.processRefund() (payment/refund.go:120-150) to use custom error types"

   **Examples of BAD tasks** (too vague, large scope, unclear, not grounded in actual code):
   - "Improve error handling" (not specific - which errors? which files? where exactly?)
   - "Refactor authentication system" (too large scope - not broken into small tasks)
   - "Make the app faster" (no clear expectations, no specific code locations)
   - "Add better logging" (no specific files or functions mentioned)

6. **Create or Update Task File**:

   **NOTE**: This step is only reached if tasks were generated in Step 5 (i.e., `reverted_count` < 5).

   **Case 1: tasks.md does NOT exist** (creating new file):
   - Generate task list markdown file following the task-list-creation-guideline format
   - Include task metadata:
     - Reference to goal: `Goal: [<goal-name>](../goal.md)`
     - Constraints reference: `Constraints: [constraints.md](../constraints.md)`
     - Success criteria being addressed by each task
     - Brief summary of Explore subagent findings that informed task creation

   - Ensure clear task structure with CONCRETE details:
     - Task ID and title
     - Description with context (reference actual files/functions from exploration)
     - **Which success criterion this task addresses** (link to specific criterion from goal.md)
     - Specific implementation approach (based on discovered architecture)
     - Acceptance criteria (testable, measurable)
     - Dependencies (if any, based on code analysis)
     - Estimated complexity (S/M/L)
     - File paths and code locations involved (from Explore findings)

   **Case 2: tasks.md ALREADY exists** (adding new tasks):
   - **CRITICAL**: Read the existing tasks.md file to understand its structure
   - Determine the next available task ID (continue numbering from last task)
   - **Append** the new tasks to the existing file using the Edit tool:
     - Maintain the same formatting and structure as existing tasks
     - Add a separator comment like: `<!-- New tasks added on YYYY-MM-DD -->`
     - Add the 5 new tasks below the separator
     - Ensure new task IDs don't conflict with existing ones
     - Update any milestone summaries if they exist in the file

   - **Verify no duplicates**:
     - After adding tasks, review to ensure none of the new tasks duplicate existing ones
     - If duplicates are found, remove them and generate replacement tasks

### Phase 3: Validation and Completion

1. **Validate Task File**:
   - Check if the "task_list_md" script is available at `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py`
     - If not available, stop and inform user to install gosu-code claude plugins: `/plugin marketplace add gosu-code/claude-plugin`
     - Once user confirms installation, verify script path again

   - If script is available, run validation:
     - `task_list_md.py list-tasks [task-file-path]` to list all tasks
     - `task_list_md.py check-dependencies [task-file-path]` to validate dependencies

   - Fix any validation errors and re-validate until clean
   - Stage the created task file: `git add [task-file-path]`

2. **Confirm Task Alignment**:
   - Display summary showing:
     - **Task Verification Results** (if tasks.md existed):
       - Number of tasks verified as truly complete
       - Number of tasks marked incomplete (with brief reasons)
       - List tasks that were updated from [x] to [ ]
       - **If reverted_count >= 5**: Show message that no new tasks were generated due to capacity limit
     - **Goal Achievement Status**: Show which success criteria are satisfied vs not satisfied
     - **Task Generation Results**:
       - **If new file**: Number of tasks generated (max 5)
       - **If existing file with reverted tasks**:
         - Number of tasks reverted to incomplete: {reverted_count}
         - Number of NEW tasks added: {actual_new_tasks} (max was 5 - reverted_count)
         - Total pending tasks needing attention: {reverted_count + actual_new_tasks}
       - **If existing file without reverted tasks**: Number of NEW tasks added (max 5)
     - Which success criteria each task addresses
     - Any constraints being respected
     - Task file location
     - Confirmation that no duplicates were added (if tasks.md existed)

   - **If goal is already achieved**: Display congratulatory message and skip task generation (handled in Phase 2, Step 4)

   - Ask user to review the tasks and confirm they align with the goal

## Output Directory

- Always output to this location: `docs/goal/<goal-name>/`
- Task file naming convention: `tasks.md`
- **Behavior**:
  - If `tasks.md` does NOT exist: Create new file with up to 5 tasks
  - If `tasks.md` ALREADY exists:
    - Append up to (5 - reverted_count) NEW tasks (no duplicates)
    - If reverted_count >= 5: DO NOT append any new tasks
    - Total pending work (reverted + new tasks) never exceeds 5

## Interactions With Other Commands

- **Prerequisite**: `/gdd-define-goal <goal-name>` must be run first to create the goal definition
- **Next Steps**: After task generation, inform user they can:
  - Review the newly created tasks against the target Goal definition
  - Start working on the goal: `/gdd-start-working <goal-name> <session-id>` this command will also force Claude to work autonomously until the target Goal is achieved.

## Interactions With Claude Subagents

- Use the `Explore` subagent to analyze the codebase before generating tasks
- Use Explore findings to verify completed tasks are actually done

## Key Principles

1. **Verification-First**: Always verify existing done tasks against codebase before generating new tasks
2. **Capacity-Aware**: Total pending work (reverted tasks + new tasks) must not exceed 5 tasks
3. **Achievement-Aware**: Always check if goal success criteria are already satisfied before generating tasks
4. **Small Scope**: Tasks must be completable in a single focused work session (2-4 hours)
5. **Specific**: Concrete deliverables with well-defined boundaries, no vague language
6. **Actionable**: Clear implementation path, not research-only unless producing concrete output
7. **Clear Expectations**: Unambiguous acceptance criteria and measurable success
8. **Goal-Focused**: Every task must contribute to achieving the goal defined success criteria
9. **Constraint-Aware**: All tasks must respect the boundaries set in constraints.md
10. **Safe**: Follow the "Definition of Safe Change" to ensure quality and stability
