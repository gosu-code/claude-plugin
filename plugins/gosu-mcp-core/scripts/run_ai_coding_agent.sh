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

# Helper script to run Claude Code CLI with all MCP & tools
# Will support other AI coding agent CLI in the future
# Usage:
#   scripts/run_ai_coding_agent.sh [-u agent_user_name] [--yolo] [-r session_id] [--run-every [seconds]] [task_prompt]

set -e

# Function to show usage
show_usage() {
    echo "Usage: $0 [-u agent_user_name] [--yolo] [-r session_id] [--run-every [seconds]] [task_prompt]"
    echo ""
    echo "Options:"
    echo "  -u agent_user_name  Run claude as specified user"
    echo "  --yolo              Enable dangerous permissions mode (skips tool restrictions)"
    echo "  -r session_id       Resume a conversation with session ID (use 'last' for most recent)"
    echo "  --run-every [N]     Run the command every N seconds in a loop (default: 1800 if N not specified)"
    echo ""
    echo "Arguments:"
    echo "  task_prompt        (optional) Main task prompt for the claude agent (default: 'perform assigned tasks')"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 'implement user authentication'"
    echo "  $0 -u agent 'fix bugs in payment module'"
    echo "  $0 --yolo 'perform system modifications'"
    echo "  $0 -u agent --yolo 'dangerous operations'"
    echo "  $0 -r last"
    echo "  $0 -r abc123 'continue with bug fixes'"
    echo "  $0 --run-every 600 'perform assigned tasks'"
    echo "  $0 --run-every 'perform assigned tasks'  # defaults to 1800 seconds"
    exit 1
}

# Initialize variables
AGENT_USER=""
TASK_PROMPT="perform assigned tasks"
YOLO_MODE=false
RESUME_SESSION=""
RUN_INTERVAL=0

# Parse options and arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u)
            AGENT_USER="$2"
            shift 2
            ;;
        --yolo)
            YOLO_MODE=true
            shift
            ;;
        -r)
            RESUME_SESSION="$2"
            shift 2
            ;;
        --run-every)
            # Check if next argument is a number
            if [[ $# -gt 1 ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
                RUN_INTERVAL="$2"
                shift 2
            else
                # Default to 1800 if no number provided
                RUN_INTERVAL=1800
                shift
            fi
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            # All remaining arguments are the task prompt
            TASK_PROMPT="$*"
            break
            ;;
    esac
done

# Set working directory to current directory
WORKING_DIR="."

if [ -n "$AGENT_USER" ]; then
    echo "Running as user: $AGENT_USER"
fi

if [ "$YOLO_MODE" = true ]; then
    echo "YOLO mode enabled: Using --dangerously-skip-permissions"
    echo ""
else
    echo "Checking for installed MCP tools..."
    
    # List MCP tools
    if [ -n "$AGENT_USER" ]; then
        MCP_OUTPUT=$(runuser -u "$AGENT_USER" -- claude mcp list 2>/dev/null || echo "No MCP servers configured.")
    else
        MCP_OUTPUT=$(claude mcp list 2>/dev/null || echo "No MCP servers configured.")
    fi
    
    echo "MCP tools output:"
    echo "$MCP_OUTPUT"
    echo ""
    
    # Extract MCP tool names
    MCP_TOOLS=""
    if [[ "$MCP_OUTPUT" != *"No MCP servers configured."* ]]; then
        echo "Extracting MCP tool names..."
        while IFS= read -r line; do
            if [[ "$line" =~ ^([^:]+): ]]; then
                tool_name="${BASH_REMATCH[1]}"
                if [ -n "$MCP_TOOLS" ]; then
                    MCP_TOOLS="$MCP_TOOLS, mcp__$tool_name"
                else
                    MCP_TOOLS="mcp__$tool_name"
                fi
                echo "  Found: $tool_name"
            fi
        done <<< "$MCP_OUTPUT"
        echo ""
    fi
    
    # Base allowed tools
    BASE_TOOLS="Task, Bash, Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, TodoWrite, WebSearch, BashOutput, KillShell, AskUserQuestion, Skill, SlashCommand, ListMcpResourcesTool, ReadMcpResourceTool"
    
    # Combine base tools with MCP tools
    if [ -n "$MCP_TOOLS" ]; then
        ALLOWED_TOOLS="$BASE_TOOLS, $MCP_TOOLS"
    else
        ALLOWED_TOOLS="$BASE_TOOLS"
    fi
    
    echo "Allowed tools: $ALLOWED_TOOLS"
    echo ""
fi

# Working directory is always current directory
WORKING_DIR="$(pwd)"

# Prepare resume/continue options
RESUME_OPTS=""
if [ -n "$RESUME_SESSION" ]; then
    if [ "$RESUME_SESSION" = "last" ]; then
        RESUME_OPTS="--continue"
    else
        RESUME_OPTS="--resume \"$RESUME_SESSION\""
    fi
fi

# Prepare the claude command
if [ "$YOLO_MODE" = true ]; then
    # YOLO mode: use --dangerously-skip-permissions and skip --allowedTools
    if [ -n "$AGENT_USER" ]; then
        CLAUDE_CMD="runuser -u \"$AGENT_USER\" -- claude --dangerously-skip-permissions $RESUME_OPTS -p \"$TASK_PROMPT\""
    else
        CLAUDE_CMD="claude --dangerously-skip-permissions $RESUME_OPTS -p \"$TASK_PROMPT\""
    fi
else
    # Normal mode: use --allowedTools
    if [ -n "$AGENT_USER" ]; then
        CLAUDE_CMD="runuser -u \"$AGENT_USER\" -- claude --allowedTools \"$ALLOWED_TOOLS\" $RESUME_OPTS -p \"$TASK_PROMPT\""
    else
        CLAUDE_CMD="claude --allowedTools \"$ALLOWED_TOOLS\" $RESUME_OPTS -p \"$TASK_PROMPT\""
    fi
fi

# Function to run the claude command
run_claude() {
    echo "Starting a claude session with command:"
    echo "$CLAUDE_CMD"
    echo ""
    # Execute
    bash -c "$CLAUDE_CMD"
}

# Function to calculate and print next run time
print_next_run_time() {
    local interval=$1
    if command -v gdate &> /dev/null; then
        # macOS with GNU coreutils (brew install coreutils)
        next_run=$(gdate -d "+${interval} seconds" "+%Y-%m-%d %H:%M:%S")
    elif date -v +1d &> /dev/null 2>&1; then
        # macOS BSD date
        next_run=$(date -v+${interval}S "+%Y-%m-%d %H:%M:%S")
    else
        # Linux date
        next_run=$(date -d "+${interval} seconds" "+%Y-%m-%d %H:%M:%S")
    fi
    echo ""
    echo "================================================================"
    echo "Next run scheduled at: $next_run"
    echo "================================================================"
    echo ""
}

# Execute with or without looping
if [ "$RUN_INTERVAL" -gt 0 ]; then
    echo "Loop mode enabled: running every $RUN_INTERVAL seconds"
    echo ""

    while true; do
        run_claude
        print_next_run_time "$RUN_INTERVAL"
        sleep "$RUN_INTERVAL"
    done
else
    # Single run
    run_claude
fi