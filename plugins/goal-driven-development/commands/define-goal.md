---
allowed-tools: Bash(mkdir:*), Write, Read, Glob
argument-hint: <goal-name> [--help]
description: Define a new goal with constraints for Goal Driven Development
---
Create a new goal directory structure for Goal Driven Development (GDD). Usage: `/define-goal <goal-name>`

User prompt: $ARGUMENTS

When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions below and stop:

```
Usage: /define-goal <goal-name>

Creates a new goal directory at docs/goal/<goal-name>/ containing:
  - goal.md        Long-term, non-specific goal definition
  - constraints.md Hard boundaries and rules for achieving the goal

Examples:
  /define-goal reliable-payments
  /define-goal improve-performance
  /define-goal refactor-auth-system

The goal name should be lowercase with hyphens (kebab-case).
```

## Command Execution Process

### Phase 1: Validate Arguments

1. Check if $ARGUMENTS is empty or only whitespace
   - If empty, display error: "Error: Goal name is required. Usage: `/define-goal <goal-name>`"
   - Stop execution

2. Extract the goal name from $ARGUMENTS (first word, ignore any extra arguments)
   - Normalize to lowercase and replace spaces with hyphens
   - Remove any special characters except hyphens and alphanumeric

3. Validate the goal name:
   - Must be at least 3 characters long
   - Must not contain path separators (/, \)
   - If invalid, display error with specific reason and stop

### Phase 2: Check for Existing Goal

1. Check if directory `docs/goal/<goal-name>/` already exists
   - Use Glob to check for existing files in that path

2. If the directory exists:
   - Display warning: "Goal '<goal-name>' already exists at docs/goal/<goal-name>/"
   - Use `AskUserQuestion` tool to ask user if they want to update the existing goal or create a new one with a different name
      - If user choose update the existing goal, skip Phase 3 and go to Phase 4.
      - If user specified a different name for <goal-name>, repeat this Phase 2 with the new <goal-name>

### Phase 3: Create Goal Directory Structure

1. Create the directory: `docs/goal/<goal-name>/`

2. Create `goal.md` with the following template:

```markdown
# Goal

<Goal Name (Title Case)>

## Vision

<!-- Describe the long-term, non-specific goal. What does success look like? -->

Example: "Make this payments service reliable and easy to change."

## Success Criteria

<!-- How will you know when this goal is achieved? List observable outcomes. -->

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Context

<!-- Why is this goal important? What problem does it solve? -->

## Scope

### In Scope

<!-- What is in scope? -->

### Out of Scope

<!-- What is explicitly out of scope? -->

---

*This goal is part of the Goal Driven Development (GDD) process.*
```

3. Create `constraints.md` with the following template:

```markdown
# Constraints

These constraints define the hard boundaries for achieving the goal "<Goal Name (Title Case)>" defined in [goal.md](./goal.md).

## Tech Stack & Libraries

<!-- Allowed technologies, frameworks, and libraries -->

| Category | Allowed | Not Allowed |
|----------|---------|-------------|
| Language | | |
| Framework | | |
| Database | | |
| Libraries | | |

## Timeline & Cadence

<!-- Development timeline and iteration cadence -->

- **Target Completion**:
- **Review Cadence**:
- **Check-in Frequency**:

## Security & Compliance

<!-- Security requirements and compliance rules that must be followed -->

- [ ] Requirement 1
- [ ] Requirement 2

## Performance Targets

<!-- Optional: Specific performance requirements. -->

| Metric | Target | Current |
|--------|--------|---------|
| | | |

## "Don't Touch" Areas

<!-- Code, systems, or areas that should NOT be modified -->

-

## Definition of "Safe Change"

<!-- What constitutes a safe, acceptable change? -->

- All existing tests pass (both unit-test and integration-test)
- New tests added for new functionality
- No breaking API changes
- Code review completed and all feedback are addressed
- Documentation updated to reflect new functionality

## Additional Constraints

<!-- Any other hard boundaries or rules -->

-

---

*These constraints are part of the Goal Driven Development (GDD) process.*
```

### Phase 4: Interactive Goal Defining

1. **Interactive Prompt for Goal**
   - Go through `docs/goal/<goal-name>/goal.md` and use `AskUserQuestion` tool to ask and let user filling in the missing information in the goal file.
   - All sections must be filled with good enough information. You must analyze user response to your questions and ask for clarification until you have good enough info to update the goal file
   - Update the goal file and use Code editor to open `docs/goal/<goal-name>/goal.md` so the user can review it.
   - Proceed to next step only when user happy with the goal definition.

2. **Interactive Prompt for Constrains (Optional)**:
   - Go through `docs/goal/<goal-name>/constraints.md` and use `AskUserQuestion` tool to ask and let user filling in the missing information in the constrains file.
   - All sections here are optional, MUST allow user to skip them during the interactive process.
   - Update the constrains file and use Code editor to open `docs/goal/<goal-name>/constraints.md` so the user can review it.
   - Proceed to next step only when user happy with the constrains.

3. **Notify Success**:
   - Print a message confirming the goal structure has been created.
   - List the paths of the created/updated files:
     - `docs/goal/<goal-name>/goal.md`
     - `docs/goal/<goal-name>/constraints.md`

## Output Directory

- All goal files are created in `docs/goal/<goal-name>/`
- Create directories as needed if not yet exist.

## Interactions With Other Commands

- No interactions
