---
allowed-tools: Bash(gh auth:*), Bash(claude mcp:*), Bash(docker run:*)
argument-hint: [--help]
description: Install and configure the Gosu MCP server
model: claude-haiku-4-5
---
Install and configure the gosu MCP server using GitHub CLI authentication. Usage: `/install-gosu-model-context-protocol`
User prompt: $ARGUMENTS
When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions and stop. Do not proceed further.

1.  **COMMAND Arguments Analysis**:
  - This command takes no arguments. The installation process is fully automated.

2.  **COMMAND Execution Process**:
  **Phase 1: Verify GH Status**
  - Verify if user has already authenticated to GitHub CLI by running `gh auth status`
  - If authentication status shows "not logged in" or any authentication error, stop execution immediately
    - Display clear instructions to the user: "You must authenticate with GitHub CLI first before install this mcp server. Please run: `gh auth login`"
    - Do not proceed to installation phase
  - If authentication status is valid with message similiar to below text, proceed to installation phase:
    ```
    ✓ Logged in to github.com account GithubUserName (/path/to/.config/gh/hosts.yml)
    - Active account: true
    - Git operations protocol: ssh
    - Token: gho_*********************************
    ```
  
  **Phase 2: Install MCP Server**
  - Execute the MCP server installation command: `claude mcp add gosu --scope user --env GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token) -- docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN -v '${PWD:-.}:/server/cwd' 0xgosu/gosu-mcp-server`
  - Capture the command output and analyze the response
  - Check if the output contains one of the following success messages:
    - "MCP server gosu already exists in local config" (server already installed)
    - "Added stdio MCP server gosu with command: docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN 0xgosu/gosu-mcp-server to local config" (new installation successful)
  - If either success message is found, verify with a follow-up command: `claude mcp list` to confirm "gosu" is listed among installed MCP servers
    - A message "gosu: docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN 0xgosu/gosu-mcp-server - ✓ Connected" confirms successful connection
    - If "gosu" is listed with a failed status, try to run the docker command manually to diagnose connection issues: `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN $(gh auth token) -v $PWD:/server/cwd' 0xgosu/gosu-mcp-server`
    - Try remove "-v '${PWD:-.}:/server/cwd'" from the docker command if volume mounting issues are suspected
    - Show any error messages from the manual run to help user troubleshoot
  - When a successful MCP connection is confirmed, 
    - Display a final success message to the user: "Gosu MCP server installed and configured successfully. Please /exit and start `claude` again for changes to take effect."
    - Then stop execution
  - If neither success message is present, or any errors occur during installation, analyze the error output to provide potential resolution steps based on common error patterns
    - Must display the full error message to help user troubleshoot
    - Show suggestions to resolve common issues, such as:
      - "Ensure Docker is installed and running"
      - "Check your internet connection"
      - "Verify your GitHub token has necessary permissions"

3.  **COMMAND Output Directory**:
  - This command does not produce output files. All configuration is handled by the Claude MCP system.

4.  **Interactions With Other Claude Slash Commands**:
  - No interactions with other Claude slash commands.

5.  **Interactions With Claude Subagents**:
  - No interactions with any Claude subagent.