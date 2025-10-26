#!/bin/bash
# Automated test runner for task_list_md.py CLI script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

echo -e "${BLUE}Task List MD CLI - Automated Test Runner${NC}"
echo "==========================================="

# Check if script exists
SCRIPT_PATH="$REPO_ROOT/plugins/gosu-mcp-core/skills/task-list-md/scripts/task_list_md.py"
if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}❌ Error: Script not found at $SCRIPT_PATH${NC}"
    echo "Please ensure the task_list_md.py script exists in src/scripts/task_list_md/"
    exit 1
fi

echo -e "${GREEN}✅ Found script at: $SCRIPT_PATH${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}✅ Python version: $PYTHON_VERSION${NC}"

# Check script runnable
python3 $SCRIPT_PATH --help

# Change to test directory
cd "$SCRIPT_DIR"

echo ""
echo -e "${YELLOW}Running comprehensive test suite...${NC}"
echo ""

# Run tests with different verbosity based on argument
if [ "$1" = "--quiet" ]; then
    python3 test_suite.py --quiet
elif [ "$1" = "--verbose" ]; then
    python3 test_suite.py --verbose
else
    python3 test_suite.py
fi

EXIT_CODE=$?

echo ""
echo "==========================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests completed successfully!${NC}"
    echo ""
    echo "The task_list_md.py CLI script is working correctly."
    echo "You can use it with confidence for managing your task lists."
else
    echo -e "${RED}💥 Some tests failed!${NC}"
    echo ""
    echo "Please review the test output above and fix any issues."
    echo "You can run individual test files for more detailed debugging:"
    echo "  python3 -m unittest test_cli_commands.py -v"
    echo "  python3 -m unittest test_task_parser.py -v"
    echo "  python3 -m unittest test_error_handling.py -v"
    echo "  python3 -m unittest test_track_progress.py -v"
fi

exit $EXIT_CODE