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
hooks_script_dir = Path(__file__).parent.parent.parent.parent / 'plugins' /'gosu-mcp-core' / 'hooks' 
print("\n Script dir:", hooks_script_dir)
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

if __name__ == '__main__':
    try:
        test_dangerous_rm_patterns()
        test_potentially_dangerous_rm_patterns()
        test_safe_rm_patterns()
        test_dangerous_git_patterns()
        test_safe_git_patterns()
        test_invalid_tool_input_error_message()
        print("\n✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
