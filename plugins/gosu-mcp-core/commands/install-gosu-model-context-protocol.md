---
allowed-tools: Bash(gh auth:*), Bash(claude mcp:*), Bash(uname:*), Bash(test:*), Bash(mkdir:*), Bash(cp:*), Bash(chmod:*), Bash(ls:*), Bash(unzip:*), Bash(rm:*)
argument-hint: [--help|--update]
description: Install and configure the Gosu MCP server
model: claude-haiku-4-5
---
Install and configure the gosu MCP server using the bundled native binaries and GitHub CLI authentication. Usage: `/install-gosu-model-context-protocol`
User prompt: $ARGUMENTS
When $ARGUMENTS contains `--help`, `-h`, or `--usage`, print the usage instructions and stop. Do not proceed further.

1.  **COMMAND Arguments Analysis**:
  - When `--update` is present, treat the command as a reinstall/refresh of the Gosu MCP server binary and Claude MCP registration.
  - When no arguments are provided, execute the full install and verification flow.

2.  **COMMAND Execution Process**:
  - Use the Claude plugin installation directory `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core` as the source of truth for bundled install assets.
  - The expected bundled archive path is `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/artifacts/gosu-mcp-server-native-binaries.zip`.
  - The installed server path must be `~/.gosu/gosu-mcp-server`.

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
  
  **Phase 2: Install Native Binary**
  - Verify that the plugin directory exists: `test -d ~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core`
  - Verify that the bundled archive exists: `test -f ~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/artifacts/gosu-mcp-server-native-binaries.zip`
  - If either path is missing, stop and explain that the gosu-mcp-core plugin installation is incomplete and should be reinstalled.
  - Detect the user platform:
    - Run `uname -s` and map `Darwin` -> `darwin`, `Linux` -> `linux`
    - Run `uname -m` and map `x86_64` or `amd64` -> `amd64`, `arm64` or `aarch64` -> `arm64`
    - If the OS or architecture is unsupported, stop and report the detected values
  - Ensure the target directory exists: `mkdir -p ~/.gosu`
  - Create a temporary extraction directory inside `~/.gosu`, such as `~/.gosu/tmp-gosu-mcp-server-install`
  - Remove any previous temporary extraction directory before reusing it: `rm -rf ~/.gosu/tmp-gosu-mcp-server-install`
  - Unzip the bundled archive into that directory: `unzip -o ~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/artifacts/gosu-mcp-server-native-binaries.zip -d ~/.gosu/tmp-gosu-mcp-server-install`
  - Select the binary matching the detected platform from this extracted layout:
    - `gosu-mcp-server-native-binaries/gosu-mcp-server-darwin-amd64`
    - `gosu-mcp-server-native-binaries/gosu-mcp-server-darwin-arm64`
    - `gosu-mcp-server-native-binaries/gosu-mcp-server-linux-amd64`
    - `gosu-mcp-server-native-binaries/gosu-mcp-server-linux-arm64`
  - Copy the selected binary to `~/.gosu/gosu-mcp-server`
  - Apply executable permissions: `chmod +x ~/.gosu/gosu-mcp-server`
  - Verify the installed binary exists and is executable with `test -x ~/.gosu/gosu-mcp-server`
  - Remove the temporary extraction directory after a successful copy
  - If unzip, copy, or chmod fails, display the exact error output and stop

  **Phase 3: Configure Claude MCP**
  - Execute the MCP registration command: `claude mcp add gosu --scope user --env GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token) -- ~/.gosu/gosu-mcp-server stdio`
  - Capture the command output and analyze the response
  - Treat both of these as success:
    - A new server registration message for `gosu`
    - "MCP server gosu already exists in local config"
  - After a successful add/update attempt, verify with `claude mcp list` to confirm `gosu` is listed among installed MCP servers
    - A healthy entry should reference `~/.gosu/gosu-mcp-server stdio` and show a connected status
    - If `gosu` is listed with a failed status, report the failure output and remind the user to confirm the binary at `~/.gosu/gosu-mcp-server` is executable
  - When a successful MCP connection is confirmed:
    - Display: "Gosu MCP server installed and configured successfully. Please /exit and start `claude` again for changes to take effect."
  - If `claude mcp add` fails, display the full error message and provide focused troubleshooting suggestions:
    - "Verify `gh auth login` has completed successfully"
    - "Confirm `~/.gosu/gosu-mcp-server` exists and is executable"
    - "Re-run `/install-gosu-model-context-protocol --update` to refresh the installed binary"

3.  **COMMAND Output Directory**:
  - This command installs the Gosu MCP server binary to `~/.gosu/gosu-mcp-server`
  - It uses the bundled archive from `~/.claude/plugins/marketplaces/gosu-code/plugins/gosu-mcp-core/artifacts/gosu-mcp-server-native-binaries.zip`
  - No additional project files are produced

4.  **Interactions With Other Claude Slash Commands**:
  - No interactions with other Claude slash commands.

5.  **Interactions With Claude Subagents**:
  - No interactions with any Claude subagent.
