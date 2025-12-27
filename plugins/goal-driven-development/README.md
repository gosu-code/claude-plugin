# Goal Driven Development (GDD) Plugin

A Claude plugin for implementing Goal Driven Development - a structured approach to software development that focuses on achieving long-term goals through iterative, constraint-aware task generation.

## Overview

Goal Driven Development (GDD) is a process that helps teams and AI assistants work together to achieve software goals by:

1. **Defining stable inputs** - Long-term goals and hard constraints that rarely change
2. **Analyzing working state** - Understanding the current repository snapshot each development cycle
3. **Generating focused outputs** - Creating limited, actionable task sets (up to 10 items)

## The GDD Process

### Inputs (Stable)

| Component | Description | Example |
|-----------|-------------|---------|
| **Goal** | Long-term, non-specific objective | "Make this payments service reliable and easy to change." |
| **Constraints** | Hard boundaries that must be respected | Tech stack, timeline, security rules, performance targets |

### Working State (Changes Every Cycle)

The repository snapshot is derived fresh each cycle:

- What exists today (services, modules, interfaces)
- Current quality signals (tests, CI, lint, coverage, error logs)
- Risks/tech debt hotspots
- Recent changes (git history)
- Known failures (CI red, flaky tests, runtime errors)

### Output (Always Limited)

A Task Set of **up to 10 items**, each containing:

| Field | Description |
|-------|-------------|
| Title | Short, descriptive name |
| Rationale | Why this helps achieve the Goal |
| Scope | Files/areas affected |
| Definition of Done | Clear completion criteria |
| Verification | Command/tests or manual steps to verify |
| Risk Level | Low/Medium/High |
| Estimated Size | S/M/L |
| Dependencies | Other tasks that must complete first |

## Installation

This plugin is part of the gosu-code plugin marketplace. To install:

```bash
# Install via the gosu plugin manager
/install-plugin goal-driven-development
```

## Commands

### `/define-goal <goal-name>`

Creates a new goal directory structure with templates for goal definition and constraints.

**Usage:**
```bash
/define-goal reliable-payments
/define-goal improve-performance
/define-goal refactor-auth-system
```

**Creates:**
```
docs/goal/<goal-name>/
  goal.md         # Long-term goal definition
  constraints.md  # Hard boundaries and rules
```

### `/analyze-repo` (Coming Soon)

Analyzes the current repository state to create a snapshot for task generation.

### `/generate-tasks` (Coming Soon)

Generates a task set based on the defined goal, constraints, and current repository state.

### `/list-goals` (Coming Soon)

Lists all defined goals and their current status.

## Directory Structure

Goals are stored in the `docs/goal/` directory:

```
docs/
  goal/
    reliable-payments/
      goal.md
      constraints.md
    improve-performance/
      goal.md
      constraints.md
```

## Goal Template

The `goal.md` file includes:

- **Vision** - The long-term, non-specific goal
- **Success Criteria** - Observable outcomes that indicate success
- **Context** - Why this goal is important
- **Scope** - What's in and out of scope
- **Related Goals** - Links to dependent goals

## Constraints Template

The `constraints.md` file includes:

- **Tech Stack & Libraries** - Allowed and forbidden technologies
- **Timeline & Cadence** - Development schedule
- **Security & Compliance** - Required security measures
- **Performance Targets** - Optional performance requirements
- **"Don't Touch" Areas** - Protected code/systems
- **Definition of "Safe Change"** - What makes a change acceptable

## Workflow Example

1. **Define your goal:**
   ```bash
   /define-goal reliable-payments
   ```

2. **Edit the goal and constraints:**
   - Open `docs/goal/reliable-payments/goal.md`
   - Define your vision and success criteria
   - Open `docs/goal/reliable-payments/constraints.md`
   - Set your tech stack, timeline, and rules

3. **Analyze your repository:**
   ```bash
   /analyze-repo reliable-payments
   ```

4. **Generate tasks:**
   ```bash
   /generate-tasks reliable-payments
   ```

5. **Work on tasks, repeat:**
   - Complete tasks from the generated set
   - Re-run `/analyze-repo` and `/generate-tasks` for the next cycle

## Best Practices

1. **Keep goals non-specific** - Goals should describe outcomes, not implementations
2. **Update constraints rarely** - Constraints should be stable; update only when genuinely needed
3. **Review task sets critically** - Not all generated tasks may be appropriate
4. **Iterate frequently** - Run the GDD cycle often for best results
5. **Track progress** - Use the success criteria to measure goal achievement

## Troubleshooting

### Goal directory already exists

If you see "Goal already exists", you can:
- View the existing goal files
- Choose a different goal name
- Delete the existing directory and recreate

### Command not found

Ensure the plugin is properly installed:
```bash
/list-plugins
```

## License

AGPL-3.0

## Contributing

Contributions are welcome! Please follow the plugin development guidelines in the main repository.
