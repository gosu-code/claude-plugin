#!/bin/bash
# ------------------- LICENSE -------------------
# Copyright (C) 2025 gosu-code 0xgosu@gmail.com

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Source: http://opensource.org/licenses/AGPL-3.0
# ------------------- LICENSE -------------------
###############################################################################
# Master Test Runner for Hook Scripts
#
# Runs both unit tests and end-to-end tests in sequence for:
# - voice_input_prompt_enhancer.py
# - block_dangerous_tool_usages.py
#
# Usage: ./run_all_tests.sh
#        ./run_all_tests.sh --verbose    # For verbose output
###############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VERBOSE=false
if [ "$1" = "--verbose" ] || [ "$1" = "-v" ]; then
    VERBOSE=true
fi

# Get current script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}Hook Scripts - Test Suite${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Test Directory: $SCRIPT_DIR"
echo ""

# Change to project root for consistent paths
cd "$PROJECT_ROOT"

###############################################################################
# Run Unit Tests - Block Dangerous Tool Usages
###############################################################################

echo -e "${YELLOW}>>> Running Block Dangerous Tool Usages Unit Tests...${NC}"
echo ""

if [ "$VERBOSE" = true ]; then
    python3 test/scripts/hooks/test_block_dangerous_tool_usages_unit.py
    BLOCK_UNIT_TEST_EXIT=$?
else
    python3 test/scripts/hooks/test_block_dangerous_tool_usages_unit.py > /tmp/block_unit_test_output.txt 2>&1
    BLOCK_UNIT_TEST_EXIT=$?

    if [ $BLOCK_UNIT_TEST_EXIT -eq 0 ]; then
        # Count passed tests
        PASSED_COUNT=$(grep -c "✓ PASS\|ok" /tmp/block_unit_test_output.txt || echo "0")
        echo -e "${GREEN}✓ Block Dangerous Tool Usages Unit Tests Passed${NC}"
    else
        echo -e "${RED}✗ Block Dangerous Tool Usages Unit Tests Failed${NC}"
        echo ""
        cat /tmp/block_unit_test_output.txt
    fi
fi

echo ""

###############################################################################
# Run End-to-End Tests - Block Dangerous Tool Usages
###############################################################################

echo -e "${YELLOW}>>> Running Block Dangerous Tool Usages E2E Tests...${NC}"
echo ""

if [ "$VERBOSE" = true ]; then
    bash test/scripts/hooks/test_block_dangerous_tool_usages_e2e.sh
    BLOCK_E2E_TEST_EXIT=$?
else
    bash test/scripts/hooks/test_block_dangerous_tool_usages_e2e.sh > /tmp/block_e2e_test_output.txt 2>&1
    BLOCK_E2E_TEST_EXIT=$?

    if [ $BLOCK_E2E_TEST_EXIT -eq 0 ]; then
        # Extract summary
        tail -n 10 /tmp/block_e2e_test_output.txt | grep -E "Passed:|Failed:|Total:"
        echo -e "${GREEN}✓ Block Dangerous Tool Usages E2E Tests Passed${NC}"
    else
        echo -e "${RED}✗ Block Dangerous Tool Usages E2E Tests Failed${NC}"
        echo ""
        cat /tmp/block_e2e_test_output.txt
    fi
fi

echo ""

###############################################################################
# Summary
###############################################################################

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

if [ $BLOCK_UNIT_TEST_EXIT -eq 0 ]; then
    echo -e "Block Dangerous Tool Usages Unit Tests:    ${GREEN}PASSED ✓${NC}"
else
    echo -e "Block Dangerous Tool Usages Unit Tests:    ${RED}FAILED ✗${NC}"
fi

if [ $BLOCK_E2E_TEST_EXIT -eq 0 ]; then
    echo -e "Block Dangerous Tool Usages E2E Tests:     ${GREEN}PASSED ✓${NC}"
else
    echo -e "Block Dangerous Tool Usages E2E Tests:     ${RED}FAILED ✗${NC}"
fi

echo ""

if [ $BLOCK_UNIT_TEST_EXIT -eq 0 ] && [ $BLOCK_E2E_TEST_EXIT -eq 0 ]; then
    echo -e "${GREEN}========================================================================${NC}"
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}========================================================================${NC}"
    exit 0
else
    echo -e "${RED}========================================================================${NC}"
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo -e "${RED}========================================================================${NC}"
    echo ""
    echo "Run with --verbose flag for detailed output:"
    echo "  ./test/scripts/hooks/run_all_tests.sh --verbose"
    echo ""
    exit 1
fi
