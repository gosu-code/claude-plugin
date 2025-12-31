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
Unit tests for session_hook.py

Tests the session-based hook script that enables per-session temporary hooks
for Claude Code by reading hook configurations from session-specific JSON files.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

# Add hooks script dir to system path to import the module
hooks_script_dir = Path(__file__).parent.parent.parent.parent / 'plugins' / 'gosu-mcp-core' / 'hooks'
sys.path.insert(0, str(hooks_script_dir))

from session_hook import (
    validate_session_id,
    find_session_hooks_file,
    load_hooks_config,
    get_hook_for_event,
    get_matcher_field_for_event,
    matches_hook_entry,
    execute_hook_command,
    execute_json_hook,
    MAX_FILE_SIZE,
    MAX_TIMEOUT,
    DEFAULT_TIMEOUT,
)


class TestValidateSessionId:
    """Tests for validate_session_id function."""

    def test_valid_uuid_lowercase(self):
        """Test that valid lowercase UUIDs are accepted."""
        valid_uuids = [
            "32502be3-59b3-4176-94c4-fd851d460417",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        ]
        for uuid in valid_uuids:
            assert validate_session_id(uuid), f"Expected '{uuid}' to be valid"

    def test_valid_uuid_uppercase(self):
        """Test that valid uppercase UUIDs are accepted."""
        valid_uuids = [
            "32502BE3-59B3-4176-94C4-FD851D460417",
            "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
        ]
        for uuid in valid_uuids:
            assert validate_session_id(uuid), f"Expected '{uuid}' to be valid"

    def test_valid_uuid_mixed_case(self):
        """Test that valid mixed-case UUIDs are accepted."""
        assert validate_session_id("32502Be3-59b3-4176-94C4-fd851D460417")

    def test_invalid_uuid_wrong_length(self):
        """Test that UUIDs with wrong length are rejected."""
        invalid_uuids = [
            "32502be3-59b3-4176-94c4-fd851d46041",   # Too short
            "32502be3-59b3-4176-94c4-fd851d4604177",  # Too long
            "32502be3-59b3-4176-94c4",               # Missing segment
        ]
        for uuid in invalid_uuids:
            assert not validate_session_id(uuid), f"Expected '{uuid}' to be invalid"

    def test_invalid_uuid_wrong_format(self):
        """Test that UUIDs with wrong format are rejected."""
        invalid_uuids = [
            "32502be359b3417694c4fd851d460417",      # No hyphens
            "32502be3_59b3_4176_94c4_fd851d460417",  # Underscores instead of hyphens
            "32502be3-59b3-4176-94c4-fd851d46041g",  # Invalid character 'g'
            "../../../etc/passwd",                   # Path traversal attempt
            "hooks.malicious.json",                  # Filename injection
        ]
        for uuid in invalid_uuids:
            assert not validate_session_id(uuid), f"Expected '{uuid}' to be invalid"

    def test_empty_and_none_values(self):
        """Test that empty and None values are rejected."""
        assert not validate_session_id("")
        assert not validate_session_id(None)
        assert not validate_session_id("   ")

    def test_non_string_values(self):
        """Test that non-string values are rejected."""
        assert not validate_session_id(12345)
        assert not validate_session_id([])
        assert not validate_session_id({})


class TestFindSessionHooksFile:
    """Tests for find_session_hooks_file function."""

    def test_find_local_hooks_file(self):
        """Test finding hooks file in local .claude directory."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create local .claude directory
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text("{}")

            # Change to temp directory and test
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = find_session_hooks_file(session_id)
                assert result is not None
                assert session_id in result
            finally:
                os.chdir(original_cwd)

    def test_find_home_hooks_file(self):
        """Test finding hooks file in home .claude directory."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock home directory
            with mock.patch.object(os.path, 'expanduser', return_value=tmpdir):
                # Create home .claude directory
                claude_dir = Path(tmpdir) / ".claude"
                claude_dir.mkdir()
                hooks_file = claude_dir / f"hooks.{session_id}.json"
                hooks_file.write_text("{}")

                # Change to a different directory (no local hooks)
                with tempfile.TemporaryDirectory() as other_dir:
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(other_dir)
                        result = find_session_hooks_file(session_id)
                        assert result is not None
                        assert session_id in result
                    finally:
                        os.chdir(original_cwd)

    def test_local_takes_priority_over_home(self):
        """Test that local hooks file takes priority over home."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        with tempfile.TemporaryDirectory() as local_dir:
            with tempfile.TemporaryDirectory() as home_dir:
                # Create both local and home .claude directories
                local_claude = Path(local_dir) / ".claude"
                local_claude.mkdir()
                local_hooks = local_claude / f"hooks.{session_id}.json"
                local_hooks.write_text('{"source": "local"}')

                home_claude = Path(home_dir) / ".claude"
                home_claude.mkdir()
                home_hooks = home_claude / f"hooks.{session_id}.json"
                home_hooks.write_text('{"source": "home"}')

                with mock.patch.object(os.path, 'expanduser', return_value=home_dir):
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(local_dir)
                        result = find_session_hooks_file(session_id)
                        assert result is not None
                        # Local should be returned (shorter path, starts with .claude)
                        assert result.startswith(".claude")
                    finally:
                        os.chdir(original_cwd)

    def test_no_hooks_file_found(self):
        """Test when no hooks file exists."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.object(os.path, 'expanduser', return_value=tmpdir):
                original_cwd = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    result = find_session_hooks_file(session_id)
                    assert result is None
                finally:
                    os.chdir(original_cwd)


class TestLoadHooksConfig:
    """Tests for load_hooks_config function."""

    def test_load_valid_hooks_config(self):
        """Test loading a valid hooks configuration file."""
        config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo hello"}]}
                ]
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            try:
                result = load_hooks_config(f.name)
                assert result == config
            finally:
                os.unlink(f.name)

    def test_load_empty_config(self):
        """Test loading an empty configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{}")
            f.flush()
            try:
                result = load_hooks_config(f.name)
                assert result == {}
            finally:
                os.unlink(f.name)

    def test_load_invalid_json(self):
        """Test loading a file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json")
            f.flush()
            try:
                try:
                    load_hooks_config(f.name)
                    assert False, "Expected JSONDecodeError"
                except json.JSONDecodeError:
                    pass  # Expected
            finally:
                os.unlink(f.name)

    def test_load_oversized_file(self):
        """Test loading a file that exceeds maximum size."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            # Write a file larger than MAX_FILE_SIZE
            large_content = '{"data": "' + 'x' * (MAX_FILE_SIZE + 100) + '"}'
            f.write(large_content)
            f.flush()
            try:
                try:
                    load_hooks_config(f.name)
                    assert False, "Expected IOError for oversized file"
                except IOError as e:
                    assert "exceeds maximum size" in str(e)
            finally:
                os.unlink(f.name)


class TestGetMatcherFieldForEvent:
    """Tests for get_matcher_field_for_event function."""

    def test_precompact_uses_trigger(self):
        """Test that PreCompact matches against trigger field."""
        assert get_matcher_field_for_event("PreCompact") == "trigger"

    def test_sessionstart_uses_source(self):
        """Test that SessionStart matches against source field."""
        assert get_matcher_field_for_event("SessionStart") == "source"

    def test_other_events_return_none(self):
        """Test that events without matcher support return None."""
        assert get_matcher_field_for_event("PreToolUse") is None
        assert get_matcher_field_for_event("Stop") is None
        assert get_matcher_field_for_event("Unknown") is None


class TestMatchesHookEntry:
    """Tests for matches_hook_entry function."""

    def test_no_matcher_matches_everything(self):
        """Test that hooks without matcher field match everything."""
        entry = {"hooks": [{"type": "command", "command": "echo"}]}
        assert matches_hook_entry(entry, "SessionStart", {"source": "startup"})
        assert matches_hook_entry(entry, "SessionStart", {"source": "resume"})
        assert matches_hook_entry(entry, "PreCompact", {"trigger": "manual"})

    def test_sessionstart_matcher_startup(self):
        """Test SessionStart matcher with startup source."""
        entry = {"matcher": "startup", "hooks": []}
        assert matches_hook_entry(entry, "SessionStart", {"source": "startup"})
        assert not matches_hook_entry(entry, "SessionStart", {"source": "resume"})
        assert not matches_hook_entry(entry, "SessionStart", {"source": "clear"})

    def test_sessionstart_matcher_resume(self):
        """Test SessionStart matcher with resume source."""
        entry = {"matcher": "resume", "hooks": []}
        assert matches_hook_entry(entry, "SessionStart", {"source": "resume"})
        assert not matches_hook_entry(entry, "SessionStart", {"source": "startup"})

    def test_sessionstart_matcher_clear(self):
        """Test SessionStart matcher with clear source."""
        entry = {"matcher": "clear", "hooks": []}
        assert matches_hook_entry(entry, "SessionStart", {"source": "clear"})
        assert not matches_hook_entry(entry, "SessionStart", {"source": "startup"})

    def test_sessionstart_matcher_compact(self):
        """Test SessionStart matcher with compact source."""
        entry = {"matcher": "compact", "hooks": []}
        assert matches_hook_entry(entry, "SessionStart", {"source": "compact"})
        assert not matches_hook_entry(entry, "SessionStart", {"source": "startup"})

    def test_precompact_matcher_manual(self):
        """Test PreCompact matcher with manual trigger."""
        entry = {"matcher": "manual", "hooks": []}
        assert matches_hook_entry(entry, "PreCompact", {"trigger": "manual"})
        assert not matches_hook_entry(entry, "PreCompact", {"trigger": "auto"})

    def test_precompact_matcher_auto(self):
        """Test PreCompact matcher with auto trigger."""
        entry = {"matcher": "auto", "hooks": []}
        assert matches_hook_entry(entry, "PreCompact", {"trigger": "auto"})
        assert not matches_hook_entry(entry, "PreCompact", {"trigger": "manual"})

    def test_matcher_case_insensitive(self):
        """Test that matcher comparison is case-insensitive."""
        entry = {"matcher": "STARTUP", "hooks": []}
        assert matches_hook_entry(entry, "SessionStart", {"source": "startup"})
        assert matches_hook_entry(entry, "SessionStart", {"source": "STARTUP"})
        assert matches_hook_entry(entry, "SessionStart", {"source": "Startup"})

    def test_event_without_matcher_support(self):
        """Test that events without matcher support ignore matcher field."""
        entry = {"matcher": "anything", "hooks": []}
        # Events without matcher support should still match
        assert matches_hook_entry(entry, "PreToolUse", {"tool_name": "Read"})
        assert matches_hook_entry(entry, "Stop", {})


class TestGetHookForEvent:
    """Tests for get_hook_for_event function."""

    def test_find_command_hook(self):
        """Test finding a command hook for an event."""
        config = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {"type": "command", "command": "echo hello", "timeout": 30}
                        ]
                    }
                ]
            }
        }
        result = get_hook_for_event(config, "SessionStart")
        assert result is not None
        assert result["type"] == "command"
        assert result["command"] == "echo hello"
        assert result["timeout"] == 30

    def test_skip_prompt_hook(self):
        """Test that prompt hooks are skipped."""
        config = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {"type": "prompt", "prompt": "some prompt"},
                            {"type": "command", "command": "echo hello"}
                        ]
                    }
                ]
            }
        }
        result = get_hook_for_event(config, "SessionStart")
        assert result is not None
        assert result["type"] == "command"
        assert result["command"] == "echo hello"

    def test_find_first_command_in_multiple_matchers(self):
        """Test finding first command across multiple matchers."""
        config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Read",
                        "hooks": [{"type": "command", "command": "echo read"}]
                    },
                    {
                        "matcher": "Write",
                        "hooks": [{"type": "command", "command": "echo write"}]
                    }
                ]
            }
        }
        result = get_hook_for_event(config, "PreToolUse")
        assert result is not None
        assert result["command"] == "echo read"

    def test_no_hook_for_event(self):
        """Test when no hook exists for the event."""
        config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo hello"}]}
                ]
            }
        }
        result = get_hook_for_event(config, "Stop")
        assert result is None

    def test_empty_hooks_config(self):
        """Test with empty hooks configuration."""
        assert get_hook_for_event({}, "SessionStart") is None
        assert get_hook_for_event({"hooks": {}}, "SessionStart") is None

    def test_empty_hooks_array(self):
        """Test with empty hooks array."""
        config = {"hooks": {"SessionStart": []}}
        assert get_hook_for_event(config, "SessionStart") is None

    def test_invalid_hooks_structure(self):
        """Test with invalid hooks structure."""
        # hooks is not a dict
        assert get_hook_for_event({"hooks": []}, "SessionStart") is None
        # event hooks is not a list
        assert get_hook_for_event({"hooks": {"SessionStart": "invalid"}}, "SessionStart") is None

    def test_find_json_hook(self):
        """Test finding a json type hook for an event."""
        config = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {"type": "json", "json": {"key": "value"}, "exitcode": 0}
                        ]
                    }
                ]
            }
        }
        result = get_hook_for_event(config, "SessionStart")
        assert result is not None
        assert result["type"] == "json"
        assert result["json"] == {"key": "value"}
        assert result["exitcode"] == 0

    def test_find_json_hook_minimal(self):
        """Test finding a json hook with only type field."""
        config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "json"}]}
                ]
            }
        }
        result = get_hook_for_event(config, "SessionStart")
        assert result is not None
        assert result["type"] == "json"

    def test_json_hook_takes_priority_over_later_command(self):
        """Test that first json hook is returned before later command hooks."""
        config = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {"type": "json", "json": {"first": True}},
                            {"type": "command", "command": "echo later"}
                        ]
                    }
                ]
            }
        }
        result = get_hook_for_event(config, "SessionStart")
        assert result is not None
        assert result["type"] == "json"
        assert result["json"] == {"first": True}

    def test_matcher_filters_sessionstart(self):
        """Test that SessionStart hooks are filtered by source matcher."""
        config = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [{"type": "json", "json": {"for": "startup"}}]
                    },
                    {
                        "matcher": "resume",
                        "hooks": [{"type": "json", "json": {"for": "resume"}}]
                    }
                ]
            }
        }
        # Test startup source
        result = get_hook_for_event(config, "SessionStart", {"source": "startup"})
        assert result is not None
        assert result["json"] == {"for": "startup"}

        # Test resume source
        result = get_hook_for_event(config, "SessionStart", {"source": "resume"})
        assert result is not None
        assert result["json"] == {"for": "resume"}

        # Test unmatched source
        result = get_hook_for_event(config, "SessionStart", {"source": "clear"})
        assert result is None

    def test_matcher_filters_precompact(self):
        """Test that PreCompact hooks are filtered by trigger matcher."""
        config = {
            "hooks": {
                "PreCompact": [
                    {
                        "matcher": "manual",
                        "hooks": [{"type": "json", "json": {"for": "manual"}}]
                    },
                    {
                        "matcher": "auto",
                        "hooks": [{"type": "json", "json": {"for": "auto"}}]
                    }
                ]
            }
        }
        # Test manual trigger
        result = get_hook_for_event(config, "PreCompact", {"trigger": "manual"})
        assert result is not None
        assert result["json"] == {"for": "manual"}

        # Test auto trigger
        result = get_hook_for_event(config, "PreCompact", {"trigger": "auto"})
        assert result is not None
        assert result["json"] == {"for": "auto"}

    def test_no_matcher_matches_any_input(self):
        """Test that hooks without matcher match any input."""
        config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "json", "json": {"matches": "all"}}]}
                ]
            }
        }
        # Should match any source
        result = get_hook_for_event(config, "SessionStart", {"source": "startup"})
        assert result is not None
        result = get_hook_for_event(config, "SessionStart", {"source": "resume"})
        assert result is not None

    def test_first_matching_hook_is_returned(self):
        """Test that the first matching hook is returned."""
        config = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [{"type": "json", "json": {"order": 1}}]
                    },
                    {
                        "hooks": [{"type": "json", "json": {"order": 2}}]  # No matcher - matches all
                    }
                ]
            }
        }
        # startup should match the first entry
        result = get_hook_for_event(config, "SessionStart", {"source": "startup"})
        assert result["json"] == {"order": 1}

        # resume should match the second entry (no matcher)
        result = get_hook_for_event(config, "SessionStart", {"source": "resume"})
        assert result["json"] == {"order": 2}


class TestExecuteHookCommand:
    """Tests for execute_hook_command function."""

    def test_execute_simple_command(self):
        """Test executing a simple echo command."""
        stdout, stderr, exit_code = execute_hook_command("echo hello", "{}", timeout=5)
        assert stdout.strip() == "hello"
        assert exit_code == 0

    def test_execute_command_with_stdin(self):
        """Test that command receives JSON input via stdin."""
        input_json = '{"session_id": "test-123"}'
        stdout, stderr, exit_code = execute_hook_command("cat", input_json, timeout=5)
        assert stdout == input_json
        assert exit_code == 0

    def test_execute_command_with_error(self):
        """Test executing a command that fails."""
        stdout, stderr, exit_code = execute_hook_command("exit 42", "{}", timeout=5)
        assert exit_code == 42

    def test_execute_command_timeout(self):
        """Test that command times out correctly."""
        stdout, stderr, exit_code = execute_hook_command("sleep 10", "{}", timeout=1)
        assert exit_code == 1
        assert "timed out" in stderr.lower()

    def test_execute_nonexistent_command(self):
        """Test executing a command that doesn't exist."""
        stdout, stderr, exit_code = execute_hook_command(
            "nonexistent_command_xyz_123", "{}", timeout=5
        )
        assert exit_code != 0


class TestExecuteJsonHook:
    """Tests for execute_json_hook function."""

    def test_execute_json_hook_with_data(self):
        """Test executing a json hook with JSON data."""
        hook = {"type": "json", "json": {"key": "value", "nested": {"a": 1}}, "exitcode": 0}
        stdout, stderr, exit_code = execute_json_hook(hook)
        assert exit_code == 0
        assert stderr == ""
        parsed = json.loads(stdout)
        assert parsed == {"key": "value", "nested": {"a": 1}}

    def test_execute_json_hook_empty_json(self):
        """Test executing a json hook with empty JSON (default)."""
        hook = {"type": "json"}
        stdout, stderr, exit_code = execute_json_hook(hook)
        assert exit_code == 0
        assert stderr == ""
        assert json.loads(stdout) == {}

    def test_execute_json_hook_custom_exitcode(self):
        """Test executing a json hook with custom exit code."""
        hook = {"type": "json", "json": {"status": "error"}, "exitcode": 42}
        stdout, stderr, exit_code = execute_json_hook(hook)
        assert exit_code == 42
        assert json.loads(stdout) == {"status": "error"}

    def test_execute_json_hook_zero_exitcode_explicit(self):
        """Test executing a json hook with explicit zero exit code."""
        hook = {"type": "json", "exitcode": 0}
        stdout, stderr, exit_code = execute_json_hook(hook)
        assert exit_code == 0
        assert json.loads(stdout) == {}

    def test_execute_json_hook_invalid_json_type(self):
        """Test that non-dict json field returns error."""
        hook = {"type": "json", "json": "not a dict"}
        stdout, stderr, exit_code = execute_json_hook(hook)
        assert exit_code == 1
        assert "must be an object" in stderr
        assert stdout == ""

    def test_execute_json_hook_string_exitcode(self):
        """Test that string exitcode is converted to int."""
        hook = {"type": "json", "exitcode": "5"}
        stdout, stderr, exit_code = execute_json_hook(hook)
        assert exit_code == 5

    def test_execute_json_hook_invalid_exitcode(self):
        """Test that invalid exitcode defaults to 0."""
        hook = {"type": "json", "exitcode": "not_a_number"}
        stdout, stderr, exit_code = execute_json_hook(hook)
        assert exit_code == 0


class TestMainIntegration:
    """Integration tests for the main function using subprocess."""

    def get_script_path(self):
        """Get the path to the session_hook.py script."""
        return str(hooks_script_dir / "session_hook.py")

    def test_no_session_id(self):
        """Test with missing session_id."""
        input_data = {"hook_event_name": "SessionStart"}
        result = subprocess.run(
            [sys.executable, self.get_script_path()],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "{}"

    def test_invalid_session_id(self):
        """Test with invalid session_id format."""
        input_data = {
            "session_id": "../../../etc/passwd",
            "hook_event_name": "SessionStart"
        }
        result = subprocess.run(
            [sys.executable, self.get_script_path()],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "{}"

    def test_no_session_hooks_file(self):
        """Test when no session hooks file exists."""
        input_data = {
            "session_id": "32502be3-59b3-4176-94c4-fd851d460417",
            "hook_event_name": "SessionStart"
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "{}"

    def test_execute_session_hook(self):
        """Test executing a session hook command."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        hooks_config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo session-hook-output"}]}
                ]
            }
        }
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SessionStart"
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .claude directory and hooks file
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text(json.dumps(hooks_config))

            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert "session-hook-output" in result.stdout

    def test_no_hook_for_event(self):
        """Test when hooks file exists but no hook for the event."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        hooks_config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo hello"}]}
                ]
            }
        }
        input_data = {
            "session_id": session_id,
            "hook_event_name": "Stop"  # Different event
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text(json.dumps(hooks_config))

            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "{}"

    def test_invalid_json_input(self):
        """Test with invalid JSON input."""
        result = subprocess.run(
            [sys.executable, self.get_script_path()],
            input="not valid json",
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 1
        assert "Failed to parse JSON" in result.stderr

    def test_malformed_hooks_file(self):
        """Test with malformed hooks configuration file."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SessionStart"
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text("invalid json content")

            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 1
            assert "Error loading session hooks file" in result.stderr

    def test_execute_json_hook_integration(self):
        """Test executing a json type hook via subprocess."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        hooks_config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "json", "json": {"result": "success", "count": 42}}]}
                ]
            }
        }
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SessionStart"
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text(json.dumps(hooks_config))

            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            output = json.loads(result.stdout)
            assert output == {"result": "success", "count": 42}

    def test_execute_json_hook_with_exitcode(self):
        """Test executing a json hook with custom exit code."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        hooks_config = {
            "hooks": {
                "Stop": [
                    {"hooks": [{"type": "json", "json": {"error": "something failed"}, "exitcode": 5}]}
                ]
            }
        }
        input_data = {
            "session_id": session_id,
            "hook_event_name": "Stop"
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text(json.dumps(hooks_config))

            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 5
            output = json.loads(result.stdout)
            assert output == {"error": "something failed"}

    def test_execute_json_hook_empty_json(self):
        """Test executing a json hook with default empty JSON."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        hooks_config = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "json"}]}
                ]
            }
        }
        input_data = {
            "session_id": session_id,
            "hook_event_name": "SessionStart"
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text(json.dumps(hooks_config))

            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert json.loads(result.stdout) == {}

    def test_matcher_filters_sessionstart_integration(self):
        """Test SessionStart matcher filtering via subprocess."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        hooks_config = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [{"type": "json", "json": {"matched": "startup"}}]
                    },
                    {
                        "matcher": "resume",
                        "hooks": [{"type": "json", "json": {"matched": "resume"}}]
                    }
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text(json.dumps(hooks_config))

            # Test with startup source
            input_data = {
                "session_id": session_id,
                "hook_event_name": "SessionStart",
                "source": "startup"
            }
            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert json.loads(result.stdout) == {"matched": "startup"}

            # Test with resume source
            input_data["source"] = "resume"
            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert json.loads(result.stdout) == {"matched": "resume"}

            # Test with unmatched source
            input_data["source"] = "clear"
            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "{}"

    def test_matcher_filters_precompact_integration(self):
        """Test PreCompact matcher filtering via subprocess."""
        session_id = "32502be3-59b3-4176-94c4-fd851d460417"
        hooks_config = {
            "hooks": {
                "PreCompact": [
                    {
                        "matcher": "manual",
                        "hooks": [{"type": "json", "json": {"trigger_type": "manual"}}]
                    },
                    {
                        "matcher": "auto",
                        "hooks": [{"type": "json", "json": {"trigger_type": "auto"}}]
                    }
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            hooks_file = claude_dir / f"hooks.{session_id}.json"
            hooks_file.write_text(json.dumps(hooks_config))

            # Test with manual trigger
            input_data = {
                "session_id": session_id,
                "hook_event_name": "PreCompact",
                "trigger": "manual"
            }
            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert json.loads(result.stdout) == {"trigger_type": "manual"}

            # Test with auto trigger
            input_data["trigger"] = "auto"
            result = subprocess.run(
                [sys.executable, self.get_script_path()],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0
            assert json.loads(result.stdout) == {"trigger_type": "auto"}


def run_all_tests():
    """Run all tests and report results."""
    import traceback

    test_classes = [
        TestValidateSessionId,
        TestFindSessionHooksFile,
        TestLoadHooksConfig,
        TestGetMatcherFieldForEvent,
        TestMatchesHookEntry,
        TestGetHookForEvent,
        TestExecuteHookCommand,
        TestExecuteJsonHook,
        TestMainIntegration,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_class in test_classes:
        print(f"\n{'=' * 60}")
        print(f"Running {test_class.__name__}")
        print('=' * 60)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    print(f"  {method_name}...", end=" ")
                    getattr(instance, method_name)()
                    print("✓ PASSED")
                    passed += 1
                except AssertionError as e:
                    print(f"✗ FAILED: {e}")
                    errors.append((f"{test_class.__name__}.{method_name}", str(e)))
                    failed += 1
                except Exception as e:
                    print(f"✗ ERROR: {e}")
                    errors.append((f"{test_class.__name__}.{method_name}", traceback.format_exc()))
                    failed += 1

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print('=' * 60)

    if errors:
        print("\nFailures and Errors:")
        for name, error in errors:
            print(f"\n  {name}:")
            print(f"    {error}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
