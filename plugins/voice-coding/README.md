# voice-coding

Enhances voice coding sessions with intelligent prompt processing for natural speech-to-code workflows in Claude Code.

## Overview

The voice-coding plugin improves the voice coding experience by automatically processing and enhancing user prompts submitted through voice input. It detects incomplete or placeholder-heavy prompts and augments them with context-aware instructions, making it easier to use natural speech patterns when coding with Claude.

## Features

- **Automatic Prompt Enhancement**: Intelligently augments voice input prompts with file-finding context
- **Placeholder Detection**: Identifies various placeholder formats in speech-to-text output
- **Ellipsis Handling**: Recognizes incomplete statements and provides appropriate context
- **Smart Thresholds**: Only activates for prompts that meet length and complexity criteria
- **Non-Intrusive**: Seamlessly integrates without disrupting normal Claude Code workflows

## Installation

1. Install the plugin:
```
/plugin install voice-coding@gosu-code
```

2. Restart Claude Code

The plugin activates automatically - no additional configuration required.

## Prerequisites

- **Claude Code**: Compatible version with plugin support
- **Voice Input**: Any voice-to-text system that works with Claude Code

## How It Works

The voice-coding plugin operates through a hook that intercepts user prompts before they reach Claude. When activated, it:

1. **Analyzes the Prompt**: Checks prompt length and content for patterns indicating voice input
2. **Detects Patterns**: Identifies placeholders, ellipsis, and incomplete references
3. **Enhances Context**: Adds instructions to help Claude locate files and understand intent
4. **Passes Through**: Sends enhanced prompt to Claude for processing

### Activation Criteria

The enhancer activates when a prompt:
- Contains 200+ characters (indicates substantial voice input)
- Includes placeholders or ellipsis patterns
- Shows patterns typical of speech-to-text conversion

### Detected Patterns

**Placeholder Formats:**
- `[placeholder]`
- `<placeholder>`
- `{placeholder}`
- `((placeholder))`
- `[[placeholder]]`
- Plain text: "placeholder" or "place holder"

**Ellipsis Patterns:**
- Three dots: `...`
- Multiple periods: `....`
- Spaced dots: `. . .`
- Text indicators: "dot dot dot", "and so on", "etcetera"

## Usage Examples

### Example 1: Natural File References

**Voice Input:**
```
Update the authentication module to use JWT tokens instead of placeholder session cookies
```

**Enhanced by Plugin:**
The plugin detects "placeholder" and adds context about finding the authentication module files in the codebase.

**Result:**
Claude understands to search for authentication-related files and makes the JWT token implementation changes accordingly.

### Example 2: Incomplete Specifications

**Voice Input:**
```
Refactor the user service class to follow the repository pattern.
It should have methods for create, read, update, and so on...
```

**Enhanced by Plugin:**
The plugin detects "and so on" (ellipsis pattern) and provides context that helps Claude understand the full CRUD pattern is intended.

**Result:**
Claude implements complete CRUD operations, not just the explicitly mentioned ones.

### Example 3: Vague File References

**Voice Input:**
```
Review the configuration file and check if the database connection settings
are using placeholder values that need to be replaced with actual production values
```

**Enhanced by Plugin:**
The plugin adds instructions to help Claude locate configuration files (config.yml, .env, settings files, etc.).

**Result:**
Claude efficiently finds and reviews all relevant configuration files without needing explicit paths.

## Components

### Hooks

#### voice_input_prompt_enhancer

The main hook that processes user prompts submitted via the UserPromptSubmit event.

**Trigger:** UserPromptSubmit event (fires when user submits a prompt)

**Process:**
1. Receives prompt from Claude Code
2. Analyzes prompt for voice input patterns
3. Enhances prompt with file-finding context if patterns detected
4. Returns enhanced prompt or original if no enhancement needed

**Configuration:**
- Timeout: 10 seconds
- Runs before prompt reaches Claude's main processing

## Benefits

### For Voice Coding

- **Natural Speech Patterns**: Speak naturally without worrying about exact syntax
- **Reduced Friction**: Less need to spell out file paths and technical details
- **Context Awareness**: Claude better understands your intent from conversational input
- **Error Recovery**: Handles speech-to-text errors and placeholders gracefully

### For Development Workflow

- **Faster Input**: Code while walking, thinking, or multitasking
- **Accessibility**: Improved support for hands-free coding scenarios
- **Reduced Cognitive Load**: Focus on logic rather than precise phrasing
- **Seamless Integration**: Works with existing Claude Code features

## Best Practices

### Speaking to Claude

**Do:**
- Use natural, conversational language
- Reference files by description (e.g., "the authentication module")
- Use "placeholder" to indicate example values
- Say "and so on" or "etc" for lists that continue predictably

**Don't:**
- Worry about perfect pronunciation of file paths
- Spell out every technical detail
- Pause for long periods (may break speech recognition)
- Use overly complex sentence structures

### Effective Voice Prompts

**Good Examples:**
```
"Review the user authentication code and check for placeholder API keys"
"Update the database schema file... the users table... to add email verification"
"Refactor the payment processing module to handle errors properly and so on"
```

**Less Effective:**
```
"Do something" (too vague)
"src slash app slash auth dot py line 42" (too precise, defeats purpose)
Short single-word commands (plugin won't activate)
```

## Troubleshooting

### Enhancement Not Triggering

**Problem:** Prompts aren't being enhanced

**Solutions:**
1. Ensure prompt is 200+ characters (minimum threshold)
2. Include terms like "placeholder", "etc", or "..." to trigger detection
3. Verify plugin is installed: check installed plugins list
4. Restart Claude Code if recently installed

### Over-Enhancement

**Problem:** Normal prompts getting unnecessary enhancements

**Solutions:**
1. Avoid using "placeholder" in prompts when you mean something specific
2. Be more specific instead of using ellipsis ("...")
3. This is rare due to length threshold - shorter prompts won't trigger enhancement

### Speech Recognition Issues

**Problem:** Speech-to-text produces poor results

**Solutions:**
1. Improve microphone quality and positioning
2. Reduce background noise
3. Speak clearly with moderate pace
4. Use system's speech recognition settings to train voice model
5. Note: This plugin enhances prompts but doesn't affect speech recognition itself

### Hook Timeout

**Problem:** Hook times out during processing

**Solutions:**
1. This is rare as processing is fast
2. Check system performance and available resources
3. Report issue if timeout occurs consistently

## Technical Details

### Hook Configuration

The voice_input_prompt_enhancer hook is configured in `hooks.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/voice_input_prompt_enhancer.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Processing Logic

1. **Pattern Matching**: Uses compiled regex patterns for efficient detection
2. **Length Threshold**: Only processes prompts with 200+ characters
3. **Context Addition**: Augments prompt with file-finding instructions
4. **Passthrough**: Returns enhanced or original prompt to Claude

### Performance

- **Fast Processing**: Sub-second enhancement in most cases
- **Low Overhead**: Minimal impact on prompt submission time
- **Compiled Patterns**: Regex patterns compiled once for efficiency
- **Graceful Fallback**: Original prompt used if enhancement fails

## Integration with Other Plugins

### Works Well With

- **gosu-mcp-core**: Enhanced prompts work seamlessly with specialized agents
- **codex-mcp**: Voice input can trigger appropriate Codex delegation
- Other Claude Code plugins that process user prompts

### No Conflicts

The voice-coding plugin operates at the prompt submission stage and doesn't interfere with other plugin functionality.

## License

Licensed under AGPL-3.0. See the LICENSE file for details.
