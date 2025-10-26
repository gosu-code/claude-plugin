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

# Script to run Claude Code CLI with MCP tools in a background session via tmux
# Will support other AI coding agent CLI in the future
# Usage:
#   scripts/run_ai_coding_agent.sh [-u agent_user_name] [--yolo] [-r session_id] [task_prompt]

set -e

# Function to show usage
show_usage() {
    echo "Usage: $0 [-u agent_user_name] [--yolo] [-r session_id] [task_prompt]"
    echo ""
    echo "Options:"
    echo "  -u agent_user_name  Run claude as specified user"
    echo "  --yolo              Enable dangerous permissions mode (skips tool restrictions)"
    echo "  -r session_id       Resume a conversation with session ID (use 'last' for most recent)"
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
    exit 1
}

# Initialize variables
AGENT_USER=""
TASK_PROMPT="perform assigned tasks"
YOLO_MODE=false
RESUME_SESSION=""

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
    BASE_TOOLS="Task, Bash, Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, TodoWrite, WebSearch, BashOutput, KillShell, SlashCommand, ListMcpResourcesTool, ReadMcpResourceTool"
    
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

# Generate unique session name based on timestamp
SESSION_NAME="claude-agent-$(date +%s)"

# Create tmux socket directory
TMUX_SOCKET_DIR="/tmp/tmux-0"
mkdir -p "$TMUX_SOCKET_DIR"

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
        CLAUDE_CMD="runuser -u \"$AGENT_USER\" -- claude --dangerously-skip-permissions $RESUME_OPTS -p \"$TASK_PROMPT\" >& agent-$SESSION_NAME.log"
    else
        CLAUDE_CMD="claude --dangerously-skip-permissions $RESUME_OPTS -p \"$TASK_PROMPT\" >& agent-$SESSION_NAME.log"
    fi
else
    # Normal mode: use --allowedTools
    if [ -n "$AGENT_USER" ]; then
        CLAUDE_CMD="runuser -u \"$AGENT_USER\" -- claude --allowedTools \"$ALLOWED_TOOLS\" $RESUME_OPTS -p \"$TASK_PROMPT\" >& agent-$SESSION_NAME.log"
    else
        CLAUDE_CMD="claude --allowedTools \"$ALLOWED_TOOLS\" $RESUME_OPTS -p \"$TASK_PROMPT\" >& agent-$SESSION_NAME.log"
    fi
fi

# Start new session in current directory
echo "Starting tmux session with command:"
echo "$CLAUDE_CMD"
echo ""

tmux -S "$TMUX_SOCKET_DIR/ai-coding-agent" new -d -s "$SESSION_NAME" "$CLAUDE_CMD"

echo "Agent session '$SESSION_NAME' started successfully!"
echo ""
echo "To attach to the session:"
echo "  tmux -S $TMUX_SOCKET_DIR/ai-coding-agent attach -t $SESSION_NAME"
echo ""
echo "To check session status:"
echo "  tmux -S $TMUX_SOCKET_DIR/ai-coding-agent list-sessions"
echo ""
echo "To view output (when finish):"
echo "  cat $WORKING_DIR/agent-$SESSION_NAME.log"