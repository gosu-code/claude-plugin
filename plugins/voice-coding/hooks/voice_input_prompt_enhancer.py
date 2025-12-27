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
A hook script to process and enhance user prompts with additional file finding instructions.
This script intercepts UserPromptSubmit events and augments the prompt with context
about locating relevant files in the codebase based on the user's request.
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, TypedDict


# Constants
MIN_LONG_PROMPT_LENGTH = 200

# Compiled regex patterns for better performance

# Placeholder patterns - detect various placeholder formats
PLACEHOLDER_PATTERNS = [
    re.compile(r"\[place\s*holder\]", re.IGNORECASE),
    re.compile(r"<place\s*holder>", re.IGNORECASE),
    re.compile(r"\{place\s*holder\}", re.IGNORECASE),
    re.compile(r"\(\(place\s*holder\)\)", re.IGNORECASE),
    re.compile(r"\[\[place\s*holder\]\]", re.IGNORECASE),
    re.compile(
        r"\bplace\s*holder\b", re.IGNORECASE
    ),  # Plain "placeholder" or "place holder"
]

# Nameholder patterns - detect various nameholder formats for code symbols
NAMEHOLDER_PATTERNS = [
    re.compile(r"\$\{name\s*holder\}", re.IGNORECASE),  # ${nameholder}
    re.compile(r"\"name\s*holder\"", re.IGNORECASE),  # "nameholder"
    re.compile(r"'name\s*holder'", re.IGNORECASE),  # 'nameholder'
    re.compile(
        r"\bname\s*holder\b", re.IGNORECASE
    ),  # Plain "nameholder" or "name holder"
]

# Ellipsis patterns - indicate incomplete information
ELLIPSIS_PATTERNS = [
    re.compile(r"\.{3,}"),  # Three or more dots: ...
    re.compile(r"…"),  # Unicode ellipsis
    re.compile(r"\betc\.?\b", re.IGNORECASE),  # "etc" or "etc."
    re.compile(r"\band so on\b", re.IGNORECASE),
    re.compile(r"\band so forth\b", re.IGNORECASE),
]

# Trigger patterns - detect file/directory reference triggers (unique patterns not covered above)
TRIGGER_PATTERNS = [
    re.compile(r"\bin this file\b", re.IGNORECASE),
    re.compile(r"\bto this file\b", re.IGNORECASE),
    re.compile(r"\bin this directory\b", re.IGNORECASE),
    re.compile(r"\bto this directory\b", re.IGNORECASE),
]


class ProjectContext(TypedDict):
    """Type definition for project context information."""

    project_files: List[str]
    common_dirs: List[str]
    project_name: str


keyword_categories: Dict[str, Dict[str, Any]] = {
    "test": {
        "keywords": ["test"],
        "directories": ["test", "tests", "__tests__"],
        "suggestion": "Look for {} files in the {} directory",
    },
    "config": {
        "keywords": ["config", "setting"],
        "directories": ["config", "configs", "settings"],
        "suggestion": "Check {} files in the {} directory",
    },
    "component": {
        "keywords": ["component", "ui", "interface"],
        "directories": ["components", "src"],
        "suggestion": "Look for {} in the {} directory",
    },
    "service": {
        "keywords": ["service", "api", "endpoint"],
        "directories": ["services", "app", "apps"],
        "suggestion": "Check {} logic in the {} directory",
    },
    "utility": {
        "keywords": ["util", "helper", "common"],
        "directories": ["utils", "lib"],
        "suggestion": "Look for {} functions in the {} directory",
    },
    "tooling": {
        "keywords": ["script", "tool"],
        "directories": ["scripts", "tools"],
        "suggestion": "Check {} files in the {} directory",
    },
}


def should_enhance_prompt(prompt: str) -> bool:
    """
    Determine if the prompt should be enhanced with file finding instructions.
    Returns True if the prompt contains patterns that indicate the user needs help
    finding files (placeholders, nameholders, ellipsis, or file/directory references).

    Checks four categories of patterns:
    - PLACEHOLDER_PATTERNS: [placeholder], <placeholder>, etc.
    - NAMEHOLDER_PATTERNS: ${nameholder}, "nameholder", etc.
    - ELLIPSIS_PATTERNS: ..., etc, and so on, etc.
    - TRIGGER_PATTERNS: in this file, to this directory, etc.
    """
    # Check all pattern lists for matches
    all_patterns = (
        PLACEHOLDER_PATTERNS
        + NAMEHOLDER_PATTERNS
        + ELLIPSIS_PATTERNS
        + TRIGGER_PATTERNS
    )

    for pattern in all_patterns:
        if pattern.search(prompt):
            return True

    return False


def get_project_context(cwd: str) -> ProjectContext:
    """
    Extract project context from the current working directory.
    Returns information about the project structure that might help with file finding.
    """
    cwd_path = Path(cwd)

    # Validate that cwd exists
    if not cwd_path.exists() or not cwd_path.is_dir():
        raise ValueError(f"Invalid working directory: {cwd}")

    # Common project indicators
    project_files = [
        "package.json",
        "requirements.txt",
        "Gemfile",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "composer.json",
        "Makefile",
        "CMakeLists.txt",
        ".gitignore",
    ]

    found_files = []
    for file in project_files:
        if (cwd_path / file).exists():
            found_files.append(file)

    # Common directory structures, constructed from keyword_categories
    common_dirs = set()
    for config in keyword_categories.values():
        common_dirs.update(config["directories"])

    found_dirs = []
    for dir_name in common_dirs:
        if (cwd_path / dir_name).exists():
            found_dirs.append(dir_name)

    return ProjectContext(
        project_files=found_files,
        common_dirs=found_dirs,
        project_name=cwd_path.name,
    )


def count_placeholders(prompt: str) -> int:
    """
    Count the number of placeholders in the prompt using compiled regex patterns.
    Supports various placeholder formats: [placeholder], <placeholder>, {placeholder}, etc.

    Note: Counts unique placeholder instances, removing text matched by specific
    patterns (brackets, braces) before checking for plain "placeholder" word.
    """
    prompt_lower = prompt.lower()

    # First, remove all formatted placeholders to avoid double-counting
    # when we check for plain "placeholder" word
    cleaned_prompt = prompt_lower
    for pattern in PLACEHOLDER_PATTERNS[
        :-1
    ]:  # All except the last (plain word) pattern
        cleaned_prompt = pattern.sub("", cleaned_prompt)

    # Count formatted placeholders
    total_count = 0
    for pattern in PLACEHOLDER_PATTERNS[:-1]:
        total_count += len(pattern.findall(prompt_lower))

    # Count plain "placeholder" words only in the cleaned text
    plain_pattern = PLACEHOLDER_PATTERNS[-1]
    total_count += len(plain_pattern.findall(cleaned_prompt))

    return total_count


def count_nameholders(prompt: str) -> int:
    """
    Count the number of nameholder tokens in the prompt.
    Uses same logic as count_placeholders to avoid double-counting.
    Supports various nameholder formats: ${nameholder}, "nameholder", 'nameholder', etc.
    """
    nameholder_count = 0
    cleaned_prompt = prompt

    # Remove formatted nameholders first (patterns 0-2: ${nameholder}, "nameholder", 'nameholder')
    for pattern in NAMEHOLDER_PATTERNS[:3]:
        cleaned_prompt = pattern.sub("", cleaned_prompt)
        nameholder_count += len(pattern.findall(prompt))

    # Count plain "nameholder" only in cleaned text
    plain_pattern = NAMEHOLDER_PATTERNS[3]
    nameholder_count += len(plain_pattern.findall(cleaned_prompt))

    return nameholder_count


def count_ellipsis(prompt: str) -> int:
    """
    Count the number of ellipsis patterns in the prompt.
    Detects: ..., …, etc, and so on, and so forth
    """
    total_count = 0
    for pattern in ELLIPSIS_PATTERNS:
        total_count += len(pattern.findall(prompt))
    return total_count


def generate_prompt_enhancing_instructions(
    prompt: str, project_context: ProjectContext
) -> str:
    """
    Generate enhanced instructions for finding relevant files and symbols based on the prompt.
    """
    base_instruction = "**The user prompt requires enhancement before you can proceed. Follow the below instructions for prompt enhancement:**\n"

    # Define keyword categories and their associated directories/suggestions

    prompt_lower = prompt.lower()
    suggestions = []

    # Process each category
    for category, config in keyword_categories.items():
        # Check if prompt contains at least one keyword from this category
        matched_keywords = [kw for kw in config["keywords"] if kw in prompt_lower]
        if matched_keywords:
            # Check if project has at least one matching directory
            matching_dirs = [
                dir_name
                for dir_name in config["directories"]
                if dir_name in project_context["common_dirs"]
            ]
            if matching_dirs:
                # Use the first matched keyword and directory for string replacement
                keyword = matched_keywords[0]
                directory = matching_dirs[0]
                formatted_suggestion = config["suggestion"].format(keyword, directory)
                suggestions.append(formatted_suggestion)

    # Handle placeholder-specific suggestions
    if any(term in prompt_lower for term in ["placeholder", "place holder"]):
        suggestions.append(
            "Identify all placeholder in the prompt eg. [placeholder], <placeholder>, {placeholder}, ((placeholder)), [[placeholder]], etc. Use the related keywords (before/after the placeholder) to search for relevant files."
        )

        # Count number of placeholders in the prompt using compiled patterns
        placeholder_count = count_placeholders(prompt)
        suggestions.append(
            f"There are {placeholder_count} placeholder(s) in the prompt. All must be replaced with relevant file/directory paths or ARN/URL/URI (e.g., database url, s3 url, http uri)."
        )

    # Handle nameholder-specific suggestions
    if any(term in prompt_lower for term in ["nameholder", "name holder"]):
        suggestions.append(
            "Identify all nameholder in the prompt eg. ${nameholder}, \"nameholder\", 'nameholder', etc. Use the related keywords (before/after the nameholder) to search for relevant code symbols."
        )

        # Count number of nameholders in the prompt using compiled patterns
        nameholder_count = count_nameholders(prompt)
        suggestions.append(
            f"There are {nameholder_count} nameholder(s) in the prompt. All must be replaced with the name of a symbol within this project repo (e.g., variable, constant, function, method, class, interface, type, etc.)."
        )

    # Handle ellipsis-specific suggestions (... or etc or and so on)
    ellipsis_count = count_ellipsis(prompt)
    if ellipsis_count > 0:
        suggestions.append(
            f"The prompt contains {ellipsis_count} ellipsis pattern(s) ('...', '…', 'etc', 'and so on'). These indicate incomplete information or examples."
        )
        suggestions.append(
            "You must infer and fill in the missing/implied information based on context. Look for patterns before/after the ellipsis to understand what's being referenced."
        )
        suggestions.append(
            "Example: 'Update files in src/components/... to use new API' → Search for ALL files in src/components/ directory, not just literal '...' files."
        )

    # Add general search guidance
    general_guidance = [
        "Use the Glob tool to search for files by pattern (e.g., '**/*.ts', '**/*.go', '**/*.py')",
        "Use the Grep tool to search for specific class, function, interface names (e.g., 'class SymbolName', 'func SymbolName', 'def symbol_name', 'type InterfaceName interface')",
        "Use the LSP tool (gopls, pyright, tsserver) that match the programming language of this repo to search for symbol definitions",
        "Check the project structure first with 'ls' or 'tree' commands if available",
    ]

    instruction = base_instruction
    if suggestions:
        instruction += "Based on project structure, consider:\n"
        for suggestion in suggestions:
            instruction += f"- {suggestion}\n"
        instruction += "\nGeneral search strategies:\n"
        for guidance in general_guidance:
            instruction += f"- {guidance}\n"
    else:
        instruction += "General search strategies:\n"
        for guidance in general_guidance:
            instruction += f"- {guidance}\n"

    # Check if prompt is a long one (possibly from voice input)
    if len(prompt) > MIN_LONG_PROMPT_LENGTH:
        instruction += "\nNote: The prompt may be a long transcripts of user voice input using Speech To Text. Identify the main intent and ignore misspellings, out of context or filler words."
    return instruction


def main() -> None:
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Validate input data
        if not isinstance(input_data, dict):
            print("Invalid input: expected JSON object", file=sys.stderr)
            sys.exit(1)

        # Extract relevant fields with validation
        prompt = input_data.get("prompt", "")
        if not prompt or not isinstance(prompt, str):
            print("Invalid or missing 'prompt' field", file=sys.stderr)
            sys.exit(1)

        cwd = input_data.get("cwd", os.getcwd())
        if not isinstance(cwd, str):
            print("Invalid 'cwd' field", file=sys.stderr)
            sys.exit(1)

        # Check if prompt should be enhanced
        if not should_enhance_prompt(prompt):
            # Allow the prompt to proceed without enhancement
            sys.exit(0)

        # Get project context and generate prompt enhancing instructions
        project_context = get_project_context(cwd)
        file_instructions = generate_prompt_enhancing_instructions(
            prompt, project_context
        )

        # Output the additional context using the hook-specific format
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": file_instructions,
            }
        }

        print(json.dumps(output))
        sys.exit(0)

    except json.JSONDecodeError as e:
        # On JSON decode error, exit with error code
        print(f"JSON decode error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Handle any other errors and exit with error code
        print(f"Error processing prompt: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
