#!/bin/bash
###############################################################################
# End-to-End Tests for voice_input_prompt_enhancer.py
#
# This script tests the hook as it would run in production, by feeding JSON
# input via stdin and checking the JSON output.
#
# Usage: ./test_voice_input_prompt_enhancer_e2e.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Get current script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# Script path
HOOK_SCRIPT_PATH="$PROJECT_ROOT/plugins/voice-coding/hooks/voice_input_prompt_enhancer.py"

# Function to test if hook triggers correctly
test_hook() {
    local test_name="$1"
    local prompt="$2"
    local should_trigger="$3"
    local cwd="${4:-/workspaces/gosu-mcp-server}"

    printf "%-50s " "Test: $test_name ..."

    # Run the hook
    result=$(echo "{\"prompt\": \"$prompt\", \"cwd\": \"$cwd\"}" | \
             python3 "$HOOK_SCRIPT_PATH" 2>/dev/null)

    # Check if output exists (triggered) or not (not triggered)
    if [ "$should_trigger" = "yes" ]; then
        if [ -n "$result" ]; then
            # Verify it's valid JSON
            if echo "$result" | python3 -m json.tool > /dev/null 2>&1; then
                # Verify it has the expected structure
                if echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); assert 'hookSpecificOutput' in data; assert 'additionalContext' in data['hookSpecificOutput']" 2>/dev/null; then
                    echo -e "${GREEN}✓ PASS${NC} (triggered with valid JSON)"
                    PASSED=$((PASSED + 1))
                else
                    echo -e "${RED}✗ FAIL${NC} (triggered but invalid structure)"
                    FAILED=$((FAILED + 1))
                fi
            else
                echo -e "${RED}✗ FAIL${NC} (triggered but invalid JSON)"
                FAILED=$((FAILED + 1))
            fi
        else
            echo -e "${RED}✗ FAIL${NC} (should trigger but didn't)"
            FAILED=$((FAILED + 1))
        fi
    else
        if [ -z "$result" ]; then
            echo -e "${GREEN}✓ PASS${NC} (not triggered)"
            PASSED=$((PASSED + 1))
        else
            echo -e "${RED}✗ FAIL${NC} (should not trigger but did)"
            FAILED=$((FAILED + 1))
        fi
    fi
}

# Function to test specific content in output
test_hook_content() {
    local test_name="$1"
    local prompt="$2"
    local expected_content="$3"
    local cwd="${4:-/workspaces/gosu-mcp-server}"

    printf "%-50s " "Test: $test_name ..."

    # Run the hook
    result=$(echo "{\"prompt\": \"$prompt\", \"cwd\": \"$cwd\"}" | \
             python3 "$HOOK_SCRIPT_PATH" 2>/dev/null)

    if [ -z "$result" ]; then
        echo -e "${RED}✗ FAIL${NC} (hook did not trigger)"
        FAILED=$((FAILED + 1))
        return
    fi

    # Extract additionalContext
    context=$(echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data['hookSpecificOutput']['additionalContext'])" 2>/dev/null)

    if echo "$context" | grep -q "$expected_content"; then
        echo -e "${GREEN}✓ PASS${NC} (contains: '$expected_content')"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (missing: '$expected_content')"
        FAILED=$((FAILED + 1))
    fi
}

###############################################################################
# Test Suite
###############################################################################

echo "========================================================================"
echo "End-to-End Tests for voice_input_prompt_enhancer.py"
echo "========================================================================"
echo ""

# Verify script exists
if [ ! -f "$HOOK_SCRIPT_PATH" ]; then
    echo -e "${RED}ERROR: Script not found at $HOOK_SCRIPT_PATH${NC}"
    exit 1
fi

echo "--- Placeholder Pattern Tests ---"
test_hook "Bracket placeholder" "Update [placeholder] config" "yes"
test_hook "Angle bracket placeholder" "<placeholder> component" "yes"
test_hook "Curly brace placeholder" "Fix {placeholder} setting" "yes"
test_hook "Plain placeholder" "Update placeholder in code" "yes"
test_hook "Place holder with space" "Fix place holder here" "yes"

echo ""
echo "--- Ellipsis Pattern Tests ---"
test_hook "Three dots" "Update files in src/..." "yes"
test_hook "Unicode ellipsis" "Fix bugs in handlers… controllers" "yes"
test_hook "etc keyword" "Add auth, logging, etc" "yes"
test_hook "etc. with period" "Add auth, logging, etc." "yes"
test_hook "and so on" "Implement A, B, and so on" "yes"
test_hook "and so forth" "Fix X, Y, and so forth" "yes"

echo ""
echo "--- File/Directory Reference Tests ---"
test_hook "in this file" "Add function in this file" "yes"
test_hook "to this file" "Add import to this file" "yes"
test_hook "in this directory" "Check files in this directory" "yes"
test_hook "to this directory" "Copy files to this directory" "yes"

echo ""
echo "--- Non-Triggering Tests ---"
test_hook "Normal prompt" "Update authentication module" "no"
test_hook "Simple request" "Add new feature" "no"
test_hook "Feature request" "Implement user login" "no"
test_hook "Bug fix" "Fix bug in parser" "no"

echo ""
echo "--- Content Validation Tests ---"
test_hook_content "Placeholder count" "Update [placeholder] and <placeholder>" "2 placeholders"
test_hook_content "Ellipsis count" "Update src/... and test/... etc" "3 ellipsis pattern"
test_hook_content "Ellipsis instructions" "Update files in src/..." "infer and fill in"
test_hook_content "General guidance" "Update placeholder" "Glob tool"

echo ""
echo "--- Multiple Pattern Tests ---"
test_hook "Placeholder + Ellipsis" "Update [placeholder] in src/..." "yes"
test_hook "Ellipsis + File ref" "Update files in src/... in this directory" "yes"
test_hook "All patterns" "Update [placeholder] in src/... in this file" "yes"

echo ""
echo "--- Edge Case Tests ---"
test_hook "Case insensitive trigger" "Add function IN THIS FILE" "yes"
test_hook "Four dots" "Update files...." "yes"
test_hook "Multiple spaces in 'place holder'" "Update place   holder" "yes"

echo ""
echo "--- Invalid Input Tests (Error Exit Code & Stderr) ---"
printf "%-50s " "Test: Invalid JSON input ..."
set +e  # Temporarily disable exit on error
stderr=$(echo "invalid json" | python3 "$HOOK_SCRIPT_PATH" 2>&1 >/dev/null)
exit_code=$?
set -e  # Re-enable exit on error
if [ $exit_code -eq 1 ] && [ -n "$stderr" ]; then
    echo -e "${GREEN}✓ PASS${NC} (exit code 1 with stderr)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (expected exit code 1 with stderr, got exit $exit_code)"
    FAILED=$((FAILED + 1))
fi

printf "%-50s " "Test: Missing prompt field ..."
set +e
stderr=$(echo '{"cwd": "/tmp"}' | python3 "$HOOK_SCRIPT_PATH" 2>&1 >/dev/null)
exit_code=$?
set -e
if [ $exit_code -eq 1 ] && [ -n "$stderr" ]; then
    echo -e "${GREEN}✓ PASS${NC} (exit code 1 with stderr)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (expected exit code 1 with stderr, got exit $exit_code)"
    FAILED=$((FAILED + 1))
fi

printf "%-50s " "Test: Invalid cwd ..."
set +e
stderr=$(echo '{"prompt": "Update placeholder", "cwd": "/nonexistent/path/12345"}' | python3 "$HOOK_SCRIPT_PATH" 2>&1 >/dev/null)
exit_code=$?
set -e
if [ $exit_code -eq 1 ] && [ -n "$stderr" ]; then
    echo -e "${GREEN}✓ PASS${NC} (exit code 1 with stderr)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (expected exit code 1 with stderr, got exit $exit_code)"
    FAILED=$((FAILED + 1))
fi

printf "%-50s " "Test: Invalid input type (not dict) ..."
set +e
stderr=$(echo '["not", "a", "dict"]' | python3 "$HOOK_SCRIPT_PATH" 2>&1 >/dev/null)
exit_code=$?
set -e
if [ $exit_code -eq 1 ] && [ -n "$stderr" ]; then
    echo -e "${GREEN}✓ PASS${NC} (exit code 1 with stderr)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (expected exit code 1 with stderr, got exit $exit_code)"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "========================================================================"
echo "Test Results Summary"
echo "========================================================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo "Total:  $((PASSED + FAILED))"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All E2E tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some E2E tests failed${NC}"
    exit 1
fi
