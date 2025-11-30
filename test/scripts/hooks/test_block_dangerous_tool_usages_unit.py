#!/usr/bin/env python3
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
"""
Unit tests for block_dangerous_tool_usages.py
Tests the refined path patterns to ensure no false positives.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from io import StringIO

# Add hooks script dir to system path to import the module
hooks_script_dir = Path(__file__).parent.parent.parent.parent / 'plugins' / 'gosu-mcp-core' / 'hooks' 
sys.path.insert(0, str(hooks_script_dir))

from block_dangerous_tool_usages import is_dangerous_rm_command, is_dangerous_git_command

def test_dangerous_rm_patterns():
    """Test that truly dangerous rm commands are detected."""
    dangerous_commands = [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf /home/*",
        "rm -rf ~",
        "rm -rf ~/",
        "rm -rf ~/*",
        "rm -rf $HOME",
        "rm -rf $HOME/*",
        "rm -fr /",  # Flag order variation
        "rm -rf / something",
        "rm -rf /workspace",
        "rm -rf /workspaces",
        "rm -rf /var/lib/docker",
    ]

    print("Testing dangerous rm commands that SHOULD be blocked:")
    for cmd in dangerous_commands:
        result = is_dangerous_rm_command(cmd)
        status = "✓ BLOCKED" if result else "✗ ALLOWED (SHOULD BLOCK)"
        print(f"  {status}: {cmd}")
        assert result == 2, f"Expected '{cmd}' to be detected as dangerous"

def test_potentially_dangerous_rm_patterns():
    """Test that truly dangerous rm commands are detected."""
    dangerous_commands = [
        "rm -rf ..",  # Parent directory without safe context
        "rm -rf ../../",  # Multiple parent traversals
        "rm -rf ./subdir/../other",  # Parent traversal within project
        "rm -rf /workspace/project/build",  # Workspace subtree
        "rm -rf /workspaces/project/build",  # Codespaces subtree
        "rm -rf /workspace/project/*",  # Workspace wildcard requires confirmation
        "rm -rf /workspaces/project/*",  # Codespaces wildcard requires confirmation
        "rm -rf /tmp/*",  # Clearing entire tmp should require confirmation
        "rm -rf /var/log/*",  # Clearing logs should require confirmation
    ]

    print("\nTesting potentially dangerous rm commands that SHOULD be blocked with user confirmation:")
    for cmd in dangerous_commands:
        result = is_dangerous_rm_command(cmd)
        status = "✓ BLOCKED" if result else "✗ ALLOWED (SHOULD BLOCK)"
        print(f"  {status}: {cmd}")
        assert result == 1, f"Expected '{cmd}' to be detected as potentially dangerous"

def test_safe_rm_patterns():
    """Test that safe rm commands are NOT detected as dangerous (no false positives)."""
    safe_commands = [
        "rm -rf ./build",  # Current directory subdirectory
        "rm -rf ./node_modules",
        "rm -rf build/*",  # Relative wildcard scoped to project
        "rm -rf file*.txt",  # Wildcard in filename
        "rm -rf *.log",  # Wildcard at start
        "rm -rf test_*",  # Wildcard in pattern
        "rm -rf /tmp/some-temp-file",  # Under /tmp
        "rm -rf /home/user/project/build",  # Non-critical absolute path
        "rm -rf /opt/app/cache",  # Non-critical absolute path
        "rm file.txt",  # Non-recursive rm
        "rm -f file.txt",  # Force but not recursive
    ]

    print("\nTesting safe rm commands that SHOULD NOT be blocked:")
    for cmd in safe_commands:
        result = is_dangerous_rm_command(cmd)
        status = "✓ ALLOWED" if not result else "✗ BLOCKED (FALSE POSITIVE)"
        print(f"  {status}: {cmd}")
        assert result == 0, f"Expected '{cmd}' to NOT be detected as dangerous (false positive)"

def test_dangerous_git_patterns():
    """Test that dangerous git commands are detected."""
    dangerous_commands = [
        "git reset --hard",
        "git clean -fd",
        "git clean -fdx",
        "git clean -df",
        "git clean -xdf",
        "git clean -f",  # Removes all untracked files
        "git clean -fx",  # Removes all untracked files including ignored
        "git clean -fX",  # Removes only ignored files
        "git push --force",
        "git push -f",
        "git reflog expire --expire=now --all",
    ]

    print("\nTesting dangerous git commands that SHOULD be blocked:")
    for cmd in dangerous_commands:
        result = is_dangerous_git_command(cmd)
        status = "✓ BLOCKED" if result else "✗ ALLOWED (SHOULD BLOCK)"
        print(f"  {status}: {cmd}")
        assert result, f"Expected '{cmd}' to be detected as dangerous"

def test_safe_git_patterns():
    """Test that safe git commands are NOT detected as dangerous."""
    safe_commands = [
        "git status",
        "git add .",
        "git commit -m 'message'",
        "git push",
        "git pull",
        "git log",
        "git diff",
        "git clean -n",  # Dry-run, not dangerous
    ]

    print("\nTesting safe git commands that SHOULD NOT be blocked:")
    for cmd in safe_commands:
        result = is_dangerous_git_command(cmd)
        status = "✓ ALLOWED" if not result else "✗ BLOCKED (FALSE POSITIVE)"
        print(f"  {status}: {cmd}")
        assert not result, f"Expected '{cmd}' to NOT be detected as dangerous (false positive)"

def test_invalid_tool_input_error_message():
    """Test that error message for invalid tool_input doesn't expose internal types."""
    print("\nTesting error message for invalid tool_input format:")

    # Create test input with tool_input as a string instead of dict
    test_input = {
        "tool_name": "Bash",
        "tool_input": "not a dictionary"  # Invalid: should be dict
    }

    # Run the script with this invalid input
    script_path = hooks_script_dir / 'block_dangerous_tool_usages.py'
    result = subprocess.run(
        ['python3', str(script_path), '--and-auto-allow'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )

    # Parse the output
    output = json.loads(result.stdout)
    reason = output.get('hookSpecificOutput', {}).get('permissionDecisionReason', '')

    # Verify the error message doesn't expose type information
    print(f"  Error message: {reason}")
    assert "Invalid tool_input format: expected a dictionary" == reason, \
        f"Expected generic error message, got: {reason}"
    assert "str" not in reason, "Error message should not expose type names"
    assert "list" not in reason, "Error message should not expose type names"
    print("  ✓ Error message is generic and secure")

def test_permission_request_allow():
    """Test PermissionRequest event with allow behavior."""
    print("\nTesting PermissionRequest event with allow behavior:")

    # Create test input for a safe operation with PermissionRequest event
    test_input = {
        "hook_event_name": "PermissionRequest",
        "tool_name": "Bash",
        "tool_input": {"command": "npm test"}
    }

    # Run the script with this input
    script_path = hooks_script_dir / 'block_dangerous_tool_usages.py'
    result = subprocess.run(
        ['python3', str(script_path), '--and-auto-allow'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )

    # Parse the output
    output = json.loads(result.stdout)
    hook_output = output.get('hookSpecificOutput', {})

    # Verify the output format
    print(f"  Output: {json.dumps(output, indent=2)}")
    assert hook_output.get('hookEventName') == 'PermissionRequest', \
        f"Expected hookEventName to be 'PermissionRequest', got: {hook_output.get('hookEventName')}"
    assert 'decision' in hook_output, "Expected 'decision' key in hookSpecificOutput"
    assert hook_output['decision']['behavior'] == 'allow', \
        f"Expected behavior to be 'allow', got: {hook_output['decision']['behavior']}"
    print("  ✓ PermissionRequest allow decision format is correct")

def test_permission_request_deny():
    """Test PermissionRequest event with deny behavior for dangerous command."""
    print("\nTesting PermissionRequest event with deny behavior:")

    # Create test input for a dangerous operation with PermissionRequest event
    test_input = {
        "hook_event_name": "PermissionRequest",
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"}
    }

    # Run the script with this input
    script_path = hooks_script_dir / 'block_dangerous_tool_usages.py'
    result = subprocess.run(
        ['python3', str(script_path)],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )

    # Parse the output
    output = json.loads(result.stdout)
    hook_output = output.get('hookSpecificOutput', {})

    # Verify the output format
    print(f"  Output: {json.dumps(output, indent=2)}")
    assert hook_output.get('hookEventName') == 'PermissionRequest', \
        f"Expected hookEventName to be 'PermissionRequest', got: {hook_output.get('hookEventName')}"
    assert 'decision' in hook_output, "Expected 'decision' key in hookSpecificOutput"
    assert hook_output['decision']['behavior'] == 'deny', \
        f"Expected behavior to be 'deny', got: {hook_output['decision']['behavior']}"
    assert 'message' in hook_output['decision'], "Expected 'message' key in decision for deny"
    assert hook_output['decision']['interrupt'] == True, \
        f"Expected interrupt to be True, got: {hook_output['decision'].get('interrupt')}"
    print("  ✓ PermissionRequest deny decision format is correct")

def test_permission_request_allow_with_updated_input():
    """Test PermissionRequest event with allow behavior and updated input."""
    print("\nTesting PermissionRequest event with updated input:")

    # Note: In current implementation, updatedInput is not used, but we test the structure
    # This test verifies the output format supports updatedInput when implemented
    test_input = {
        "hook_event_name": "PermissionRequest",
        "tool_name": "Bash",
        "tool_input": {"command": "npm test"}
    }

    # Run the script with this input
    script_path = hooks_script_dir / 'block_dangerous_tool_usages.py'
    result = subprocess.run(
        ['python3', str(script_path), '--and-auto-allow'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )

    # Parse the output
    output = json.loads(result.stdout)
    hook_output = output.get('hookSpecificOutput', {})

    # Verify the structure supports updatedInput (even if not present)
    print(f"  Output: {json.dumps(output, indent=2)}")
    assert hook_output.get('hookEventName') == 'PermissionRequest'
    assert hook_output['decision']['behavior'] == 'allow'
    # updatedInput is optional, so we just check the structure is valid JSON
    print("  ✓ PermissionRequest structure supports updatedInput")

def test_hook_event_detection():
    """Test that hook event type is correctly detected from input."""
    print("\nTesting hook event type detection:")

    # Test with hook_event_name field
    test_cases = [
        {
            "input": {
                "hook_event_name": "PermissionRequest",
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"}
            },
            "expected_event": "PermissionRequest",
            "description": "PermissionRequest event"
        },
        {
            "input": {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"}
            },
            "expected_event": "PreToolUse",
            "description": "PreToolUse event"
        },
        {
            "input": {
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"}
            },
            "expected_event": "PreToolUse",
            "description": "Default when no hook_event_name field"
        }
    ]

    script_path = hooks_script_dir / 'block_dangerous_tool_usages.py'

    for i, test_case in enumerate(test_cases):
        result = subprocess.run(
            ['python3', str(script_path), '--and-auto-allow'],
            input=json.dumps(test_case["input"]),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        hook_output = output.get('hookSpecificOutput', {})
        detected_event = hook_output.get('hookEventName')

        print(f"  Test case {i+1} ({test_case['description']}): Expected '{test_case['expected_event']}', got '{detected_event}'")
        assert detected_event == test_case['expected_event'], \
            f"Expected hookEventName to be '{test_case['expected_event']}', got: {detected_event}"

    print("  ✓ Hook event type detection works correctly")

if __name__ == '__main__':
    try:
        test_dangerous_rm_patterns()
        test_potentially_dangerous_rm_patterns()
        test_safe_rm_patterns()
        test_dangerous_git_patterns()
        test_safe_git_patterns()
        test_invalid_tool_input_error_message()
        test_permission_request_allow()
        test_permission_request_deny()
        test_permission_request_allow_with_updated_input()
        test_hook_event_detection()
        print("\n✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
