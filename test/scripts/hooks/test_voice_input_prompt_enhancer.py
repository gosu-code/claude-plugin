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
Unit tests for voice_input_prompt_enhancer.py

Tests individual functions and pattern detection logic.
Run with: python3 -m pytest test/scripts/hooks/test_voice_input_prompt_enhancer.py -v
Or: python3 test/scripts/hooks/test_voice_input_prompt_enhancer.py
"""

import sys
import unittest
from pathlib import Path

# Add src directory to path
# Add hooks script dir to system path to import the module
hooks_script_dir = Path(__file__).parent.parent.parent.parent / 'plugins' / 'voice-coding' / 'hooks' 
sys.path.insert(0, str(hooks_script_dir))

from voice_input_prompt_enhancer import (
    should_enhance_prompt,
    count_placeholders,
    count_ellipsis,
    get_project_context,
    generate_file_finding_instructions,
    MIN_LONG_PROMPT_LENGTH,
)


class TestShouldEnhancePrompt(unittest.TestCase):
    """Test the should_enhance_prompt function with various patterns."""

    def test_placeholder_patterns(self):
        """Test that placeholder patterns trigger enhancement."""
        test_cases = [
            ("Update [placeholder] file", "Bracket placeholder"),
            ("Fix <placeholder> component", "Angle bracket placeholder"),
            ("Check {placeholder} config", "Curly brace placeholder"),
            ("Update ((placeholder)) module", "Double paren placeholder"),
            ("Update [[placeholder]] setting", "Double bracket placeholder"),
            ("Update placeholder in code", "Plain placeholder"),
            ("Update place holder in code", "Place holder with space"),
        ]

        for prompt, description in test_cases:
            with self.subTest(description=description):
                self.assertTrue(
                    should_enhance_prompt(prompt),
                    f"Should trigger for: {description}"
                )

    def test_ellipsis_patterns(self):
        """Test that ellipsis patterns trigger enhancement."""
        test_cases = [
            ("Update files in src/...", "Three dots"),
            ("Fix bugs in handlers… controllers", "Unicode ellipsis"),
            ("Add auth, logging, etc", "etc keyword"),
            ("Add auth, logging, etc.", "etc. with period"),
            ("Implement A, B, and so on", "and so on"),
            ("Fix X, Y, and so forth", "and so forth"),
        ]

        for prompt, description in test_cases:
            with self.subTest(description=description):
                self.assertTrue(
                    should_enhance_prompt(prompt),
                    f"Should trigger for: {description}"
                )

    def test_trigger_patterns(self):
        """Test that file/directory reference patterns trigger enhancement."""
        test_cases = [
            ("Update function in this file", "in this file"),
            ("Add import to this file", "to this file"),
            ("Check files in this directory", "in this directory"),
            ("Copy files to this directory", "to this directory"),
            ("Update IN THIS FILE", "case insensitive - in this file"),
            ("Add TO THIS DIRECTORY", "case insensitive - to this directory"),
        ]

        for prompt, description in test_cases:
            with self.subTest(description=description):
                self.assertTrue(
                    should_enhance_prompt(prompt),
                    f"Should trigger for: {description}"
                )

    def test_non_triggering_prompts(self):
        """Test that normal prompts do NOT trigger enhancement."""
        test_cases = [
            ("Update the authentication module", "Normal prompt"),
            ("Add new feature for users", "No triggers"),
            ("Refactor the code", "Simple request"),
            ("Implement user login", "Feature request"),
            ("Fix bug in parser", "Bug fix"),
        ]

        for prompt, description in test_cases:
            with self.subTest(description=description):
                self.assertFalse(
                    should_enhance_prompt(prompt),
                    f"Should NOT trigger for: {description}"
                )


class TestCountPlaceholders(unittest.TestCase):
    """Test the count_placeholders function."""

    def test_single_placeholder(self):
        """Test counting single placeholder patterns."""
        self.assertEqual(count_placeholders("Update [placeholder]"), 1)
        self.assertEqual(count_placeholders("Fix <placeholder>"), 1)
        self.assertEqual(count_placeholders("Check {placeholder}"), 1)
        self.assertEqual(count_placeholders("Update placeholder"), 1)

    def test_multiple_placeholders(self):
        """Test counting multiple placeholders."""
        prompt = "Update [placeholder] and <placeholder> files"
        self.assertEqual(count_placeholders(prompt), 2)

    def test_no_placeholders(self):
        """Test prompts without placeholders."""
        self.assertEqual(count_placeholders("Update the config file"), 0)
        self.assertEqual(count_placeholders("Add new feature"), 0)

    def test_case_insensitive(self):
        """Test that placeholder detection is case insensitive."""
        self.assertEqual(count_placeholders("Update PLACEHOLDER"), 1)
        self.assertEqual(count_placeholders("Update [PlaceHolder]"), 1)

    def test_avoid_double_counting(self):
        """Test that nested/formatted placeholders aren't double counted."""
        # A placeholder inside brackets shouldn't be counted twice
        self.assertEqual(count_placeholders("[placeholder]"), 1)
        self.assertEqual(count_placeholders("<placeholder>"), 1)
        self.assertEqual(count_placeholders("{placeholder}"), 1)

    def test_mixed_placeholder_formats(self):
        """Test counting different placeholder formats together."""
        prompt = "Update [placeholder] and {placeholder} and placeholder"
        # Should count all three
        self.assertEqual(count_placeholders(prompt), 3)

    def test_placeholder_with_adjacent_text(self):
        """Test that placeholders work with adjacent text."""
        # The pattern looks for exact "placeholder" or "place holder", not variations
        self.assertEqual(count_placeholders("[placeholder]text"), 1)
        self.assertEqual(count_placeholders("text[placeholder]"), 1)


class TestCountEllipsis(unittest.TestCase):
    """Test the count_ellipsis function."""

    def test_single_ellipsis(self):
        """Test counting single ellipsis patterns."""
        self.assertEqual(count_ellipsis("Update files in src/..."), 1)
        self.assertEqual(count_ellipsis("Fix bugs in handlers…"), 1)
        self.assertEqual(count_ellipsis("Add auth, logging, etc"), 1)
        self.assertEqual(count_ellipsis("Add auth, logging, etc."), 1)
        self.assertEqual(count_ellipsis("Implement A, B, and so on"), 1)
        self.assertEqual(count_ellipsis("Fix X, Y, and so forth"), 1)

    def test_multiple_ellipsis(self):
        """Test counting multiple ellipsis patterns."""
        prompt = "Update files in src/... and test/... etc"
        self.assertEqual(count_ellipsis(prompt), 3)

    def test_no_ellipsis(self):
        """Test prompts without ellipsis."""
        self.assertEqual(count_ellipsis("Update the config file"), 0)
        self.assertEqual(count_ellipsis("Add new feature"), 0)

    def test_four_or_more_dots(self):
        """Test that four or more dots are detected."""
        self.assertEqual(count_ellipsis("Update files...."), 1)
        self.assertEqual(count_ellipsis("Fix bugs....."), 1)

    def test_case_sensitivity(self):
        """Test case sensitivity for 'and so on' and 'and so forth'."""
        self.assertEqual(count_ellipsis("Update A, B, AND SO ON"), 1)
        self.assertEqual(count_ellipsis("Fix X, Y, AND SO FORTH"), 1)

    def test_etc_variations(self):
        """Test different variations of 'etc'."""
        # Pattern \betc\.?\b is now case-insensitive (with re.IGNORECASE)
        self.assertEqual(count_ellipsis("Add auth, etc"), 1)
        self.assertEqual(count_ellipsis("Add auth, etc."), 1)
        # Uppercase ETC should now match (pattern is case-insensitive)
        self.assertEqual(count_ellipsis("Add auth, ETC"), 1)
        self.assertEqual(count_ellipsis("Add auth, ETC."), 1)


class TestGetProjectContext(unittest.TestCase):
    """Test the get_project_context function."""

    def test_valid_directory(self):
        """Test with valid directory."""
        context = get_project_context(str(hooks_script_dir.parent))

        self.assertIn("project_files", context)
        self.assertIn("common_dirs", context)
        self.assertIn("project_name", context)

        self.assertIsInstance(context["project_files"], list)
        self.assertIsInstance(context["common_dirs"], list)
        self.assertEqual(context["project_name"], "voice-coding")

    def test_invalid_directory(self):
        """Test with invalid directory."""
        with self.assertRaises(ValueError):
            get_project_context("/nonexistent/directory/path")

    def test_detects_project_files(self):
        """Test that common project files are detected."""
        context = get_project_context(str(Path(__file__).parent.parent.parent.parent))

        # Should detect at least some project indicators
        # (Makefile, go.mod, etc. exist in this project)
        self.assertGreater(len(context["project_files"]), 0)


class TestGenerateFileFindingInstructions(unittest.TestCase):
    """Test the generate_file_finding_instructions function."""

    def test_placeholder_instructions(self):
        """Test instructions generated for placeholder patterns."""
        context = {
            "project_files": ["go.mod"],
            "common_dirs": ["test"],
            "project_name": "test-project"
        }
        prompt = "Update [placeholder] in the code"
        instructions = generate_file_finding_instructions(prompt, context)

        self.assertIn("placeholder", instructions.lower())
        self.assertIn("Glob tool", instructions)

    def test_ellipsis_instructions(self):
        """Test instructions generated for ellipsis patterns."""
        context = {
            "project_files": ["go.mod"],
            "common_dirs": ["src"],
            "project_name": "test-project"
        }
        prompt = "Update files in src/..."
        instructions = generate_file_finding_instructions(prompt, context)

        self.assertIn("ellipsis pattern", instructions)
        self.assertIn("infer and fill in", instructions.lower())

    def test_long_prompt_note(self):
        """Test that long prompts get voice input note."""
        context = {
            "project_files": [],
            "common_dirs": [],
            "project_name": "test"
        }

        # Create a long prompt
        long_prompt = "Update placeholder " + "x" * MIN_LONG_PROMPT_LENGTH
        instructions = generate_file_finding_instructions(long_prompt, context)

        self.assertIn("Speech To Text", instructions)
        self.assertIn("voice input", instructions.lower())

    def test_short_prompt_no_note(self):
        """Test that short prompts don't get voice input note."""
        context = {
            "project_files": [],
            "common_dirs": [],
            "project_name": "test"
        }

        short_prompt = "Update placeholder"
        instructions = generate_file_finding_instructions(short_prompt, context)

        self.assertNotIn("Speech To Text", instructions)

    def test_keyword_category_test_matching(self):
        """Test that 'test' keyword triggers test directory suggestion."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["test", "src"],
            "project_name": "test-project"
        }
        prompt = "Update test files"
        instructions = generate_file_finding_instructions(prompt, context)

        self.assertIn("test", instructions.lower())
        self.assertIn("test directory", instructions.lower())

    def test_keyword_category_config_matching(self):
        """Test that 'config' keyword triggers config directory suggestion."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["config", "src"],
            "project_name": "test-project"
        }
        prompt = "Update config settings"
        instructions = generate_file_finding_instructions(prompt, context)

        self.assertIn("config", instructions.lower())

    def test_keyword_category_component_matching(self):
        """Test that 'component' keyword triggers components directory suggestion."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["components", "src"],
            "project_name": "test-project"
        }
        prompt = "Update UI component"
        instructions = generate_file_finding_instructions(prompt, context)

        self.assertIn("component", instructions.lower())

    def test_keyword_category_service_matching(self):
        """Test that 'service' or 'api' keywords trigger service directory suggestion."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["services", "src"],
            "project_name": "test-project"
        }

        # Test with 'service' keyword
        prompt_service = "Update user service"
        instructions = generate_file_finding_instructions(prompt_service, context)
        self.assertIn("service", instructions.lower())

        # Test with 'api' keyword
        prompt_api = "Update API endpoint"
        instructions_api = generate_file_finding_instructions(prompt_api, context)
        self.assertIn("api", instructions_api.lower())

    def test_keyword_category_utility_matching(self):
        """Test that 'util' or 'helper' keywords trigger utility directory suggestion."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["utils", "lib"],
            "project_name": "test-project"
        }

        # Test with 'util' keyword
        prompt_util = "Update util functions"
        instructions = generate_file_finding_instructions(prompt_util, context)
        self.assertIn("util", instructions.lower())

        # Test with 'helper' keyword
        prompt_helper = "Update helper methods"
        instructions_helper = generate_file_finding_instructions(prompt_helper, context)
        self.assertIn("helper", instructions_helper.lower())

    def test_keyword_category_tooling_matching(self):
        """Test that 'script' or 'tool' keywords trigger scripts/tools directory suggestion."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["scripts", "tools"],
            "project_name": "test-project"
        }

        # Test with 'script' keyword
        prompt_script = "Update build script"
        instructions = generate_file_finding_instructions(prompt_script, context)
        self.assertIn("script", instructions.lower())

        # Test with 'tool' keyword
        prompt_tool = "Update testing tool"
        instructions_tool = generate_file_finding_instructions(prompt_tool, context)
        self.assertIn("tool", instructions_tool.lower())

    def test_no_matching_directories(self):
        """Test when keywords match but directories don't exist."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": [],  # No matching directories
            "project_name": "test-project"
        }
        prompt = "Update test files"
        instructions = generate_file_finding_instructions(prompt, context)

        # Should still have general search strategies
        self.assertIn("Glob tool", instructions)
        self.assertIn("Grep tool", instructions)

    def test_multiple_keyword_matches(self):
        """Test when prompt contains multiple category keywords."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["test", "services", "utils"],
            "project_name": "test-project"
        }
        prompt = "Update test service and util functions"
        instructions = generate_file_finding_instructions(prompt, context)

        # All matching categories should be included
        self.assertIn("test", instructions.lower())
        self.assertIn("service", instructions.lower())
        self.assertIn("util", instructions.lower())

    def test_placeholder_count_in_instructions(self):
        """Test that placeholder count is correctly reported."""
        context = {
            "project_files": [],
            "common_dirs": [],
            "project_name": "test"
        }
        # Use exact "placeholder" text (not placeholder1, placeholder2, etc.)
        prompt = "Update [placeholder] and <placeholder> and {placeholder}"
        instructions = generate_file_finding_instructions(prompt, context)

        self.assertIn("3 placeholders", instructions)

    def test_ellipsis_count_in_instructions(self):
        """Test that ellipsis count is correctly reported."""
        context = {
            "project_files": [],
            "common_dirs": [],
            "project_name": "test"
        }
        prompt = "Update files in src/... and test/... etc"
        instructions = generate_file_finding_instructions(prompt, context)

        self.assertIn("3 ellipsis pattern", instructions)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_prompt(self):
        """Test with empty prompt."""
        self.assertFalse(should_enhance_prompt(""))

    def test_whitespace_only_prompt(self):
        """Test with whitespace-only prompt."""
        self.assertFalse(should_enhance_prompt("   \t\n  "))

    def test_special_characters_in_prompt(self):
        """Test that special characters don't cause issues."""
        prompt = "Update [placeholder] with @#$%^&*() chars"
        self.assertTrue(should_enhance_prompt(prompt))

    def test_unicode_characters(self):
        """Test with unicode characters."""
        prompt = "Update 文件 with placeholder"
        self.assertTrue(should_enhance_prompt(prompt))

    def test_very_long_placeholder_word(self):
        """Test that placeholder in very long text is detected."""
        long_text = "word " * 1000 + "placeholder " + "word " * 1000
        self.assertTrue(should_enhance_prompt(long_text))

    def test_placeholder_at_boundaries(self):
        """Test placeholder at start/end of prompt."""
        self.assertTrue(should_enhance_prompt("placeholder is here"))
        self.assertTrue(should_enhance_prompt("here is placeholder"))
        self.assertTrue(should_enhance_prompt("placeholder"))

    def test_ellipsis_at_boundaries(self):
        """Test ellipsis at start/end of prompt."""
        self.assertTrue(should_enhance_prompt("... update files"))
        self.assertTrue(should_enhance_prompt("update files ..."))
        self.assertTrue(should_enhance_prompt("..."))

    def test_multiple_dots_not_ellipsis(self):
        """Test that exactly two dots are NOT counted as ellipsis."""
        # Two dots should not trigger (pattern requires 3+)
        self.assertEqual(count_ellipsis("Update files.."), 0)

    def test_etc_as_part_of_word(self):
        """Test that 'etc' as part of another word is handled correctly."""
        # 'etc' should match only as whole word
        prompt = "Update fetching method"  # contains 'etc' in 'fetching'
        # Should not trigger because it's not a word boundary match
        etc_count = count_ellipsis(prompt)
        # The pattern \betc\.?\b should NOT match 'etc' within 'fetching'
        self.assertEqual(etc_count, 0)


class TestMixedPatterns(unittest.TestCase):
    """Test scenarios with multiple patterns combined."""

    def test_placeholder_and_ellipsis(self):
        """Test prompt with both placeholder and ellipsis."""
        prompt = "Update [placeholder] files in src/..."
        self.assertTrue(should_enhance_prompt(prompt))
        self.assertEqual(count_placeholders(prompt), 1)
        self.assertEqual(count_ellipsis(prompt), 1)

    def test_placeholder_and_trigger(self):
        """Test prompt with placeholder and file reference."""
        prompt = "Update [placeholder] in this file"
        self.assertTrue(should_enhance_prompt(prompt))

    def test_ellipsis_and_trigger(self):
        """Test prompt with ellipsis and directory reference."""
        prompt = "Update files in src/... in this directory"
        self.assertTrue(should_enhance_prompt(prompt))

    def test_all_patterns_combined(self):
        """Test prompt with all pattern types."""
        prompt = "Update [placeholder] files in src/... and etc in this directory"
        self.assertTrue(should_enhance_prompt(prompt))
        self.assertEqual(count_placeholders(prompt), 1)
        # Should count both '...' and 'etc'
        self.assertGreaterEqual(count_ellipsis(prompt), 2)

    def test_multiple_placeholders_and_ellipsis(self):
        """Test with multiple instances of different patterns."""
        # Use exact "placeholder" text (not placeholder1, placeholder2)
        prompt = "Update [placeholder] and <placeholder> in src/... and test/... etc"
        self.assertTrue(should_enhance_prompt(prompt))
        self.assertEqual(count_placeholders(prompt), 2)
        self.assertEqual(count_ellipsis(prompt), 3)  # ... + ... + etc

    def test_mixed_instructions_generation(self):
        """Test instruction generation with mixed patterns."""
        context = {
            "project_files": ["package.json"],
            "common_dirs": ["test", "src"],
            "project_name": "test-project"
        }
        prompt = "Update test [placeholder] files in src/... etc"
        instructions = generate_file_finding_instructions(prompt, context)

        # Should include all relevant suggestions
        self.assertIn("placeholder", instructions.lower())
        self.assertIn("ellipsis", instructions.lower())
        self.assertIn("test", instructions.lower())

    def test_complex_real_world_scenario(self):
        """Test a complex real-world voice input scenario."""
        context = {
            "project_files": ["package.json", "go.mod"],
            "common_dirs": ["test", "src", "services", "utils"],
            "project_name": "my-app"
        }
        # Simulate voice input with multiple triggers
        prompt = (
            "Update the test files in [placeholder] directory and also "
            "the service handlers in src/services/... and util functions etc "
            "and make sure to update in this file as well"
        )
        instructions = generate_file_finding_instructions(prompt, context)

        # Should detect all patterns
        self.assertIn("1 placeholders", instructions)  # [placeholder]
        self.assertIn("2 ellipsis pattern", instructions)  # ... and etc
        self.assertIn("test", instructions.lower())
        self.assertIn("service", instructions.lower())
        self.assertIn("util", instructions.lower())
        self.assertIn("Glob tool", instructions)


class TestProjectContextEdgeCases(unittest.TestCase):
    """Test edge cases for project context analysis."""

    def test_empty_project_directory(self):
        """Test with a directory that has no project files."""
        import tempfile
        import shutil

        # Create a temporary empty directory
        temp_dir = tempfile.mkdtemp()
        try:
            context = get_project_context(temp_dir)
            self.assertEqual(len(context["project_files"]), 0)
            self.assertEqual(len(context["common_dirs"]), 0)
            self.assertIsInstance(context["project_name"], str)
        finally:
            shutil.rmtree(temp_dir)

    def test_nonexistent_directory_raises_error(self):
        """Test that nonexistent directory raises ValueError."""
        with self.assertRaises(ValueError) as context:
            get_project_context("/this/path/should/not/exist/123456789")
        self.assertIn("Invalid working directory", str(context.exception))

    def test_file_path_instead_of_directory(self):
        """Test that passing a file path raises ValueError."""
        # Use a known file
        file_path = str(Path(__file__).parent.parent.parent.parent / "Makefile")
        if Path(file_path).exists():
            with self.assertRaises(ValueError):
                get_project_context(file_path)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    # Run tests
    print("=" * 70)
    print("Running Unit Tests for voice_input_prompt_enhancer.py")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ All unit tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
