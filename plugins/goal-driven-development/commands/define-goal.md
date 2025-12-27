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
   - Ask user if they want to view the existing goal or create a new one with a different name
   - Stop execution

### Phase 3: Create Goal Directory Structure

1. Create the directory: `docs/goal/<goal-name>/`

2. Create `goal.md` with the following template:

```markdown
# Goal: <Goal Name (Title Case)>

> Created: <current date YYYY-MM-DD>

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

<!-- What is in scope? What is explicitly out of scope? -->

### In Scope

-

### Out of Scope

-

## Related Goals

<!-- Link to any related or dependent goals -->

- None

---

*This goal is part of the Goal Driven Development (GDD) process.*
```

3. Create `constraints.md` with the following template:

```markdown
# Constraints: <Goal Name (Title Case)>

> Last Updated: <current date YYYY-MM-DD>

These constraints define the hard boundaries for achieving the goal defined in [goal.md](./goal.md).

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

<!-- Optional: Specific performance requirements -->

| Metric | Target | Current |
|--------|--------|---------|
| | | |

## "Don't Touch" Areas

<!-- Code, systems, or areas that should NOT be modified -->

-

## Definition of "Safe Change"

<!-- What constitutes a safe, acceptable change? -->

- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] No breaking API changes
- [ ] Code review completed
- [ ] Documentation updated

## Additional Constraints

<!-- Any other hard boundaries or rules -->

-

---

*These constraints are part of the Goal Driven Development (GDD) process.*
```

### Phase 4: Confirm Creation

1. Display success message:
   ```
   Goal '<goal-name>' created successfully!

   Created files:
     - docs/goal/<goal-name>/goal.md
     - docs/goal/<goal-name>/constraints.md

   Next steps:
     1. Edit docs/goal/<goal-name>/goal.md to define your goal
     2. Edit docs/goal/<goal-name>/constraints.md to set your constraints
     3. Run /analyze-repo to generate a repository snapshot
     4. Run /generate-tasks to create your first task set
   ```

2. Open the goal.md file for the user to review

## Output Directory

- All goal files are created in `docs/goal/<goal-name>/`

## Interactions With Other Commands

- `/analyze-repo` - Analyzes the repository to create a snapshot (working state)
- `/generate-tasks` - Generates a task set based on the goal and current repository state
- `/list-goals` - Lists all defined goals
