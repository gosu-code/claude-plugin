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
# End-to-End Tests for block_dangerous_tool_usages.py
#
# This script tests the hook as it would run in production, by feeding JSON
# input via stdin and checking the JSON output.
#
# Usage: ./test_block_dangerous_tool_usages.sh
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
HOOK_SCRIPT_PATH="$PROJECT_ROOT/plugins/gosu-mcp-core/hooks/block_dangerous_tool_usages.py"

# Function to test hook with expected decision
test_hook_decision() {
    local test_name="$1"
    local tool_name="$2"
    local tool_input="$3"
    local expected_decision="$4"
    local expected_reason_pattern="${5:-}"
    local use_auto_allow="${6:-no}"
    local workdir="${7:-}"

    printf "%-60s " "Test: $test_name ..."

    # Create temporary file for stderr
    local stderr_file=$(mktemp)

    # Run the hook with or without --and-auto-allow flag
    local cmd=(python3 "$HOOK_SCRIPT_PATH")
    if [ "$use_auto_allow" = "yes" ]; then
        cmd+=("--and-auto-allow")
    fi

    if [ -n "$workdir" ]; then
        result=$(
            cd "$workdir" && \
            echo "{\"tool_name\": \"$tool_name\", \"tool_input\": $tool_input}" | \
            "${cmd[@]}" 2>"$stderr_file"
        )
    else
        result=$(echo "{\"tool_name\": \"$tool_name\", \"tool_input\": $tool_input}" | \
                 "${cmd[@]}" 2>"$stderr_file")
    fi

    # Verify valid JSON
    if ! echo "$result" | python3 -m json.tool > /dev/null 2>&1; then
        echo -e "${RED}✗ FAIL${NC} (invalid JSON output)"
        # Display stderr if available for debugging
        if [ -s "$stderr_file" ]; then
            echo "  stderr output:"
            cat "$stderr_file" | sed 's/^/    /'
        fi
        rm -f "$stderr_file"
        FAILED=$((FAILED + 1))
        return
    fi

    # Extract decision
    decision=$(echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)

    if [ "$decision" = "$expected_decision" ]; then
        # If expected reason pattern is provided, check it
        if [ -n "$expected_reason_pattern" ]; then
            reason=$(echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data['hookSpecificOutput'].get('permissionDecisionReason', ''))" 2>/dev/null)
            if echo "$reason" | grep -q "$expected_reason_pattern"; then
                echo -e "${GREEN}✓ PASS${NC} (decision: $decision)"
                PASSED=$((PASSED + 1))
            else
                echo -e "${RED}✗ FAIL${NC} (decision correct but reason mismatch)"
                echo "    Expected pattern: $expected_reason_pattern"
                echo "    Actual reason: $reason"
                # Display stderr if available for debugging
                if [ -s "$stderr_file" ]; then
                    echo "  stderr output:"
                    cat "$stderr_file" | sed 's/^/    /'
                fi
                FAILED=$((FAILED + 1))
            fi
        else
            echo -e "${GREEN}✓ PASS${NC} (decision: $decision)"
            PASSED=$((PASSED + 1))
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (expected: $expected_decision, got: $decision)"
        # Display stderr if available for debugging
        if [ -s "$stderr_file" ]; then
            echo "  stderr output:"
            cat "$stderr_file" | sed 's/^/    /'
        fi
        FAILED=$((FAILED + 1))
    fi

    # Clean up temporary stderr file
    rm -f "$stderr_file"
}

# Function to test default mode (exit code 0, no output for safe operations)
test_hook_no_output() {
    local test_name="$1"
    local tool_name="$2"
    local tool_input="$3"
    local workdir="${4:-}"

    printf "%-60s " "Test: $test_name ..."

    # Run the hook without --and-auto-allow flag
    set +e
    local cmd=(python3 "$HOOK_SCRIPT_PATH")
    if [ -n "$workdir" ]; then
        result=$(
            cd "$workdir" && \
            echo "{\"tool_name\": \"$tool_name\", \"tool_input\": $tool_input}" | \
            "${cmd[@]}" 2>/dev/null
        )
    else
        result=$(echo "{\"tool_name\": \"$tool_name\", \"tool_input\": $tool_input}" | \
                 "${cmd[@]}" 2>/dev/null)
    fi
    exit_code=$?
    set -e

    # Should have exit code 0 and no output
    if [ $exit_code -eq 0 ] && [ -z "$result" ]; then
        echo -e "${GREEN}✓ PASS${NC} (exit 0, no output)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (expected: exit 0 with no output, got: exit $exit_code)"
        FAILED=$((FAILED + 1))
    fi
}

###############################################################################
# Test Suite
###############################################################################

echo "========================================================================"
echo "End-to-End Tests for block_dangerous_tool_usages.py"
echo "========================================================================"
echo ""

# Verify script exists
if [ ! -f "$HOOK_SCRIPT_PATH" ]; then
    echo -e "${RED}ERROR: Script not found at $HOOK_SCRIPT_PATH${NC}"
    exit 1
fi

###############################################################################
echo "--- Dangerous rm Command Tests (Should DENY) ---"
###############################################################################

test_hook_decision \
    "rm -rf /" \
    "Bash" \
    '{"command": "rm -rf /"}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm -rf *" \
    "Bash" \
    '{"command": "rm -rf *"}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm -fr directory" \
    "Bash" \
    '{"command": "rm -fr directory"}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm -r -f folder" \
    "Bash" \
    '{"command": "rm -r -f folder"}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm --recursive --force" \
    "Bash" \
    '{"command": "rm --recursive --force /tmp/test"}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm -Rf directory" \
    "Bash" \
    '{"command": "rm -Rf directory"}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm -rf ~/" \
    "Bash" \
    '{"command": "rm -rf ~/"}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm -rf .." \
    "Bash" \
    '{"command": "rm -rf .."}' \
    "ask" \
    "Potentially Dangerous rm command"

test_hook_decision \
    "rm -rf . (current dir)" \
    "Bash" \
    '{"command": "rm -rf ."}' \
    "deny" \
    "Dangerous rm command"

test_hook_decision \
    "rm -rf with \$HOME" \
    "Bash" \
    '{"command": "rm -rf $HOME/temp"}' \
    "deny" \
    "Dangerous rm command"

echo ""

###############################################################################
echo "--- Dangerous git Command Tests (Should DENY) ---"
###############################################################################

test_hook_decision \
    "git reset --hard" \
    "Bash" \
    '{"command": "git reset --hard HEAD~1"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -fdx" \
    "Bash" \
    '{"command": "git clean -fdx"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -xdf" \
    "Bash" \
    '{"command": "git clean -xdf"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -dfx" \
    "Bash" \
    '{"command": "git clean -dfx"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -fxd" \
    "Bash" \
    '{"command": "git clean -fxd"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -dxf" \
    "Bash" \
    '{"command": "git clean -dxf"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -xfd" \
    "Bash" \
    '{"command": "git clean -xfd"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -fd" \
    "Bash" \
    '{"command": "git clean -fd"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -df" \
    "Bash" \
    '{"command": "git clean -df"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git clean -f (dangerous: removes all untracked files)" \
    "Bash" \
    '{"command": "git clean -f"}' \
    "deny" \
    "Dangerous git command detected and prevented." \
    "yes"

test_hook_decision \
    "git clean -fx (dangerous: removes all untracked + ignored files)" \
    "Bash" \
    '{"command": "git clean -fx"}' \
    "deny" \
    "Dangerous git command detected and prevented." \
    "yes"

test_hook_decision \
    "git clean -fX (dangerous: removes only ignored files)" \
    "Bash" \
    '{"command": "git clean -fX"}' \
    "deny" \
    "Dangerous git command detected and prevented." \
    "yes"

test_hook_decision \
    "git push --force" \
    "Bash" \
    '{"command": "git push --force origin main"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git push -f" \
    "Bash" \
    '{"command": "git push -f"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git branch -D" \
    "Bash" \
    '{"command": "git branch -D feature-branch"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git branch -d" \
    "Bash" \
    '{"command": "git branch -d old-branch"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git tag -d" \
    "Bash" \
    '{"command": "git tag -d v1.0.0"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git remote remove" \
    "Bash" \
    '{"command": "git remote remove origin"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git filter-branch" \
    "Bash" \
    '{"command": "git filter-branch --tree-filter"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git reflog expire" \
    "Bash" \
    '{"command": "git reflog expire --expire=now --all"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git update-ref -d" \
    "Bash" \
    '{"command": "git update-ref -d refs/heads/main"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "git checkout --orphan" \
    "Bash" \
    '{"command": "git checkout --orphan new-branch"}' \
    "deny" \
    "Dangerous git command"

echo ""

###############################################################################
echo "--- .env File Access Tests (Should ASK) ---"
###############################################################################

test_hook_decision \
    "Read .env file" \
    "Read" \
    '{"file_path": "/path/to/.env"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "Edit .env file" \
    "Edit" \
    '{"file_path": "/workspaces/project/.env", "old_string": "foo", "new_string": "bar"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "Write .env file" \
    "Write" \
    '{"file_path": "/home/user/.env", "content": "API_KEY=secret"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "Bash cat .env" \
    "Bash" \
    '{"command": "cat .env"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "Bash echo to .env" \
    "Bash" \
    '{"command": "echo API_KEY=secret > .env"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "Bash touch .env" \
    "Bash" \
    '{"command": "touch .env"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "Bash cp .env" \
    "Bash" \
    '{"command": "cp .env .env.backup"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "Bash mv to .env" \
    "Bash" \
    '{"command": "mv temp .env"}' \
    "ask" \
    "sensitive data"

echo ""

###############################################################################
echo "--- Safe Operations Tests (Should ALLOW) ---"
###############################################################################

test_hook_decision \
    "Read normal file" \
    "Read" \
    '{"file_path": "/path/to/config.json"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "Read .env.example" \
    "Read" \
    '{"file_path": "/workspaces/project/.env.example"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "Read default.env" \
    "Read" \
    '{"file_path": "/config/default.env"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "Read default.production.env" \
    "Read" \
    '{"file_path": "/config/default.production.env"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "git status" \
    "Bash" \
    '{"command": "git status"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "git diff" \
    "Bash" \
    '{"command": "git diff"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "git log" \
    "Bash" \
    '{"command": "git log --oneline"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "git add" \
    "Bash" \
    '{"command": "git add ."}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "git commit" \
    "Bash" \
    '{"command": "git commit -m \"Update files\""}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "git push (no force)" \
    "Bash" \
    '{"command": "git push origin main"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "rm non-recursive" \
    "Bash" \
    '{"command": "rm /tmp/tempfile.txt"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "rm -r single dir (no force)" \
    "Bash" \
    '{"command": "rm -r /tmp/safe-dir"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "docker run --rm" \
    "Bash" \
    '{"command": "docker run --rm -it ubuntu bash"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "ls command" \
    "Bash" \
    '{"command": "ls -la /tmp"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "mkdir command" \
    "Bash" \
    '{"command": "mkdir -p /tmp/new-dir"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "cat normal file" \
    "Bash" \
    '{"command": "cat /etc/hosts"}' \
    "allow" \
    "" \
    "yes"

echo ""

###############################################################################
echo "--- Config-based Auto-Allow Tests ---"
###############################################################################

config_dir=$(mktemp -d)
mkdir -p "$config_dir/.gosu"
cat > "$config_dir/.gosu/settings.json" <<'EOF'
{"autoAllowNonDangerousToolUsage": true}
EOF

test_hook_decision \
    "Config enables auto-allow without flag" \
    "Bash" \
    '{"command": "git status"}' \
    "allow" \
    "" \
    "no" \
    "$config_dir"

rm -rf "$config_dir"

config_dir=$(mktemp -d)
mkdir -p "$config_dir/.gosu"
cat > "$config_dir/.gosu/settings.json" <<'EOF'
{"autoAllowNonDangerousToolUsage": false}
EOF

test_hook_no_output \
    "Config disabled auto-allow keeps default behavior" \
    "Bash" \
    '{"command": "git status"}' \
    "$config_dir"

rm -rf "$config_dir"

echo ""

###############################################################################
echo "--- Edge Case Tests ---"
###############################################################################

test_hook_decision \
    "Case insensitive rm -RF" \
    "Bash" \
    '{"command": "RM -RF /tmp/test"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "Case insensitive GIT RESET --HARD" \
    "Bash" \
    '{"command": "GIT RESET --HARD"}' \
    "deny" \
    "Dangerous git command"

test_hook_decision \
    "Extra spaces in rm -rf" \
    "Bash" \
    '{"command": "rm   -rf   /tmp"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "MultiEdit tool with .env" \
    "MultiEdit" \
    '{"file_path": "/app/.env"}' \
    "ask" \
    "sensitive data"

test_hook_decision \
    "File with 'env' in name but not .env" \
    "Read" \
    '{"file_path": "/config/environment.js"}' \
    "allow" \
    "" \
    "yes"

test_hook_decision \
    "File with .env substring" \
    "Read" \
    '{"file_path": "/config/development.conf"}' \
    "allow" \
    "" \
    "yes"

echo ""

###############################################################################
echo "--- Default Mode Tests (No Flag, Exit 0, No Output) ---"
###############################################################################

test_hook_no_output \
    "Default: Read normal file" \
    "Read" \
    '{"file_path": "/path/to/config.json"}'

test_hook_no_output \
    "Default: git status" \
    "Bash" \
    '{"command": "git status"}'

test_hook_no_output \
    "Default: ls command" \
    "Bash" \
    '{"command": "ls -la /tmp"}'

test_hook_no_output \
    "Default: mkdir command" \
    "Bash" \
    '{"command": "mkdir -p /tmp/new-dir"}'

test_hook_no_output \
    "Default: safe file with 'env' in name" \
    "Read" \
    '{"file_path": "/config/environment.js"}'

echo ""

###############################################################################
echo "--- Invalid Input Tests ---"
###############################################################################

printf "%-60s " "Test: Invalid JSON input ..."
set +e  # Temporarily disable exit on error
stderr=$(echo "invalid json" | python3 "$HOOK_SCRIPT_PATH" 2>&1)
result=$(echo "invalid json" | python3 "$HOOK_SCRIPT_PATH" 2>/dev/null)
set -e  # Re-enable exit on error

# Should output deny decision for invalid JSON
decision=$(echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data['hookSpecificOutput']['permissionDecision'])" 2>/dev/null || echo "")
if [ "$decision" = "deny" ]; then
    echo -e "${GREEN}✓ PASS${NC} (denied invalid JSON)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (should deny invalid JSON)"
    FAILED=$((FAILED + 1))
fi

printf "%-60s " "Test: Missing tool_name field ..."
result=$(echo '{"tool_input": {"command": "ls"}}' | python3 "$HOOK_SCRIPT_PATH" --and-auto-allow 2>/dev/null)
decision=$(echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
if [ "$decision" = "allow" ]; then
    echo -e "${GREEN}✓ PASS${NC} (allowed when tool_name missing)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (should allow when tool_name missing)"
    FAILED=$((FAILED + 1))
fi

printf "%-60s " "Test: Invalid tool_input type (string) ..."
result=$(echo '{"tool_name": "Bash", "tool_input": "not a dict"}' | python3 "$HOOK_SCRIPT_PATH" 2>/dev/null)
decision=$(echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
if [ "$decision" = "deny" ]; then
    echo -e "${GREEN}✓ PASS${NC} (denied invalid tool_input type)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (should deny invalid tool_input type)"
    FAILED=$((FAILED + 1))
fi

printf "%-60s " "Test: Invalid tool_input type (list) ..."
result=$(echo '{"tool_name": "Bash", "tool_input": ["not", "a", "dict"]}' | python3 "$HOOK_SCRIPT_PATH" 2>/dev/null)
decision=$(echo "$result" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data['hookSpecificOutput']['permissionDecision'])" 2>/dev/null)
if [ "$decision" = "deny" ]; then
    echo -e "${GREEN}✓ PASS${NC} (denied invalid tool_input type)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (should deny invalid tool_input type)"
    FAILED=$((FAILED + 1))
fi

echo ""

###############################################################################
# Summary
###############################################################################

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
