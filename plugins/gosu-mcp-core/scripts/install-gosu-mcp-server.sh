#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Setup colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Starting Gosu MCP Server Automated Installation...${NC}"

# Phase 1: Verify GH Status
if [ -z "$GH_TOKEN" ] && ! gh auth status &>/dev/null; then
    echo -e "${RED}Error: You must authenticate with GitHub CLI first or set GH_TOKEN environment variable before installing this mcp server.${NC}"
    echo -e "${RED}Please run: gh auth login${NC}"
    exit 1
fi

if [ -n "$GH_TOKEN" ]; then
    echo -e "${GREEN}GitHub token provided via GH_TOKEN environment variable.${NC}"
else
    echo -e "${GREEN}GitHub CLI authentication verified.${NC}"
fi

# Phase 2: Install Native Binary
TEMP_DIR=$(mktemp -d)
# Clean up temp dir on exit
trap 'rm -rf "$TEMP_DIR"' EXIT

ZIP_FILE="$TEMP_DIR/gosu-mcp-server-native-binaries.zip"
# Use the raw URL to download the actual zip file, not the GitHub web page
DOWNLOAD_URL="https://github.com/gosu-code/claude-plugin/raw/main/plugins/gosu-mcp-core/artifacts/gosu-mcp-server-native-binaries.zip"

echo "Downloading latest artifact from GitHub..."
curl -L -s -o "$ZIP_FILE" "$DOWNLOAD_URL"

# Detect platform
OS_NAME=$(uname -s)
ARCH_NAME=$(uname -m)

case "$OS_NAME" in
    Darwin) PLATFORM_OS="darwin" ;;
    Linux) PLATFORM_OS="linux" ;;
    *) echo -e "${RED}Unsupported OS: $OS_NAME${NC}"; exit 1 ;;
esac

case "$ARCH_NAME" in
    x86_64|amd64) PLATFORM_ARCH="amd64" ;;
    arm64|aarch64) PLATFORM_ARCH="arm64" ;;
    *) echo -e "${RED}Unsupported architecture: $ARCH_NAME${NC}"; exit 1 ;;
esac

BINARY_NAME="gosu-mcp-server-${PLATFORM_OS}-${PLATFORM_ARCH}"
echo "Detected platform: ${PLATFORM_OS}-${PLATFORM_ARCH}. Selecting binary: $BINARY_NAME"

# Ensure ~/.gosu exists
mkdir -p ~/.gosu

echo "Extracting archive..."
unzip -q -o -j "$ZIP_FILE" -d ~/.gosu

# Check if the required binary was extracted
if [ ! -f ~/.gosu/"$BINARY_NAME" ]; then
    echo -e "${RED}Error: Required binary $BINARY_NAME not found in the extracted archive.${NC}"
    exit 1
fi

echo "Installing binary..."
cp ~/.gosu/"$BINARY_NAME" ~/.gosu/gosu-mcp-server
chmod +x ~/.gosu/gosu-mcp-server

# Verify the installed binary is executable
if [ ! -x ~/.gosu/gosu-mcp-server ]; then
    echo -e "${RED}Error: Installed binary is not executable.${NC}"
    exit 1
fi

# Clean up the extracted platform-specific binaries
rm -f ~/.gosu/gosu-mcp-server-darwin-amd64 ~/.gosu/gosu-mcp-server-darwin-arm64 ~/.gosu/gosu-mcp-server-linux-amd64 ~/.gosu/gosu-mcp-server-linux-arm64
echo -e "${GREEN}Binary installed successfully to ~/.gosu/gosu-mcp-server.${NC}"

# Phase 3: Configure Claude MCP
echo "Configuring Claude MCP..."

# Get GitHub token
if [ -z "$GH_TOKEN" ]; then
    GH_TOKEN=$(gh auth token 2>/dev/null || true)
fi

if [ -z "$GH_TOKEN" ]; then
    echo -e "${RED}Error: Could not retrieve GitHub token. Set GH_TOKEN environment variable or run 'gh auth login'.${NC}"
    exit 1
fi

# We use set +e temporarily because 'claude mcp add' might return a non-zero exit code if it already exists or fails
set +e
ADD_OUTPUT=$(claude mcp add gosu --scope user --env GITHUB_PERSONAL_ACCESS_TOKEN="$GH_TOKEN" -- ~/.gosu/gosu-mcp-server stdio 2>&1)
ADD_STATUS=$?
set -e

# If it says it already exists, remove and re-add
if echo "$ADD_OUTPUT" | grep -q "already exists"; then
    echo "Existing Gosu MCP configuration found. Updating..."
    claude mcp remove gosu --scope user &>/dev/null || true
    
    set +e
    ADD_OUTPUT=$(claude mcp add gosu --scope user --env GITHUB_PERSONAL_ACCESS_TOKEN="$GH_TOKEN" -- ~/.gosu/gosu-mcp-server stdio 2>&1)
    ADD_STATUS=$?
    set -e
fi

if [ $ADD_STATUS -ne 0 ]; then
    echo -e "${RED}Error: Failed to add Claude MCP server. Output:${NC}"
    echo "$ADD_OUTPUT"
    echo -e "\nTroubleshooting suggestions:"
    echo "- Verify 'gh auth login' has completed successfully"
    echo "- Confirm '~/.gosu/gosu-mcp-server' exists and is executable"
    exit 1
fi

# Verify installation with claude mcp list
set +e
LIST_OUTPUT=$(claude mcp list 2>&1)
set -e

if ! echo "$LIST_OUTPUT" | grep -q "gosu"; then
    echo -e "${RED}Warning: 'gosu' not found in 'claude mcp list' output. It may have failed to register properly.${NC}"
    echo "Output from 'claude mcp list':"
    echo "$LIST_OUTPUT"
    exit 1
fi

echo -e "${GREEN}Gosu MCP server installed and configured successfully.${NC}"
echo "Please restart any running claude instance for changes to take effect."
