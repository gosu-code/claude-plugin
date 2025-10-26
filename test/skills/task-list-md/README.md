# Task List MD CLI - Automated Test Suite

This directory contains comprehensive automated tests for the `task_list_md.py` CLI script.

## Test Structure

```
test/skills/task-list-md/
├── fixtures/                    # Test data files
│   ├── simple_tasks.md         # Simple task list for basic testing
│   ├── complex_tasks.md        # Complex hierarchical tasks
│   └── empty_tasks.md          # Empty file for edge case testing
├── test_cli_commands.py        # CLI command integration tests
├── test_task_parser.py         # TaskParser class unit tests
├── test_error_handling.py      # Error handling and edge case tests
├── test_suite.py              # Test runner and suite
└── README.md                  # This file
```

## Test Coverage

### 1. CLI Command Tests (`test_cli_commands.py`)
- **Help Commands**: `--help`, command-specific help
- **Task Listing**: `list-tasks` with different file types
- **Task Details**: `show-task` for various task types
- **Status Management**: `set-status` single and bulk operations
- **Task Management**: `add-task`, `delete-task`
- **Query & Filter**: `get-next-task`, `filter-tasks`, `search-tasks`, `ready-tasks`
- **Progress & Reporting**: `show-progress`, `check-dependencies`, `export`

### 2. TaskParser Unit Tests (`test_task_parser.py`)
- **TaskStatus Enum**: Checkbox conversion, status mapping
- **Colors Class**: Color functionality and enablement
- **Task Parsing**: Simple and hierarchical task parsing
- **Task Sorting**: Hierarchical ID sorting
- **Content Handling**: Multiline content, descriptions
- **Progress Tracking**: Status history, statistics calculation

### 3. Error Handling Tests (`test_error_handling.py`)
- **File Errors**: Non-existent files, invalid paths
- **Invalid Inputs**: Invalid task IDs, status values, dependencies
- **Constraint Violations**: Parent-child task constraints
- **Dependency Issues**: Circular dependencies, self-dependencies
- **Edge Cases**: Unicode content, very long content, deep nesting
- **Malformed Data**: Invalid markdown, empty descriptions

## Running Tests

### Run All Tests
```bash
# From the repository root
cd test/scripts/task_list_md/
python3 test_suite.py
```

### Run Specific Test Files
```bash
# CLI command tests only
python3 -m unittest test_cli_commands.py

# TaskParser tests only
python3 -m unittest test_task_parser.py

# Error handling tests only
python3 -m unittest test_error_handling.py
```

### Run Individual Test Classes
```bash
# Specific test class
python3 -m unittest test_cli_commands.TestTaskListMDCLI

# Specific test method
python3 -m unittest test_cli_commands.TestTaskListMDCLI.test_list_tasks_simple
```

### Verbosity Options
```bash
# Quiet mode (less output)
python3 test_suite.py --quiet

# Verbose mode (detailed output)
python3 test_suite.py --verbose
```

## Test Features

### Automatic Test Data Management
- Each test uses temporary files and directories
- Test fixtures are automatically copied to temp locations
- Cleanup happens automatically after each test

### Comprehensive Error Testing
- Tests all documented error conditions
- Validates error messages are user-friendly
- Ensures proper exit codes

### Real CLI Testing
- Tests actual CLI commands via subprocess
- Validates both stdout and stderr output
- Tests command-line argument parsing

### Progress Tracking Testing
- Tests `.tasks.local.json` file creation
- Validates status history tracking
- Tests statistics calculation

## Expected Results

When all tests pass, you should see output like:
```
Test Summary:
Tests run: 50+
Failures: 0
Errors: 0
Skipped: 0
Success rate: 100.0%
✅ ALL TESTS PASSED!
```

## Test Data

### Simple Tasks (`fixtures/simple_tasks.md`)
- 7 tasks with all status types
- Basic requirements and dependencies
- Parent-child relationships

### Complex Tasks (`fixtures/complex_tasks.md`)
- 11 tasks in hierarchical structure
- Multiple dependency chains
- Mixed completion states

### Empty Tasks (`fixtures/empty_tasks.md`)
- No tasks (for edge case testing)

## Integration with CI/CD

These tests can be integrated into your CI/CD pipeline:

```bash
# Add to your build script
cd test/scripts/task_list_md/
python3 test_suite.py --quiet
```

The test suite exits with code 0 on success and 1 on failure, making it suitable for automated testing environments.

## Troubleshooting

### Common Issues

1. **Script Not Found**
   ```
   Error: Script not found at src/scripts/task_list_md.py
   ```
   - Ensure the script exists in the correct location
   - Run tests from the repository root

2. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'task_list_md'
   ```
   - Make sure you're running tests from the test directory
   - Check Python path configuration

3. **Permission Errors**
   - Ensure the script has execute permissions
   - Check temporary directory write permissions

### Debugging Failed Tests

1. **Run with verbose output**:
   ```bash
   python3 test_suite.py --verbose
   ```

2. **Run individual failing tests**:
   ```bash
   python3 -m unittest test_cli_commands.TestTaskListMDCLI.test_failing_method -v
   ```

3. **Check test output manually**:
   ```bash
   python3 ../../../src/scripts/task_list_md.py list-tasks fixtures/simple_tasks.md
   ```

## Contributing

When adding new features to `task_list_md.py`, please:

1. Add corresponding tests to the appropriate test file
2. Update test fixtures if needed
3. Run the full test suite to ensure no regressions
4. Update this README if new test categories are added

## Test Maintenance

- Tests use the actual CLI script, so they validate real functionality
- Test fixtures are minimal but cover all major use cases
- Error conditions are thoroughly tested to ensure robustness
- Performance is not heavily tested as the script is designed for small to medium task files