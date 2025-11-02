#!/bin/bash

# Script to list merged pull requests with optional filtering by authors and date range
# Uses GitHub CLI (gh) to retrieve PR data

set -e

# Default values
DEFAULT_DAYS=7
FROM_DATE=""
TO_DATE=""
AUTHORS=""
REPO=""
SHOW_HELP=false
SAVE_TO_FILE=false
OUTPUT_DIR="./out"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

List merged pull requests with optional filtering by authors and date range.

OPTIONS:
    -a, --authors USERS     Comma-separated list of GitHub usernames to filter by
                           Example: -a "user1,user2,user3"

    -f, --from DATE        Start date for PR merge filter (YYYY-MM-DD format)
                           Default: 7 days ago

    -t, --to DATE          End date for PR merge filter (YYYY-MM-DD format)
                           Default: today

    -d, --days DAYS        Number of days to look back (alternative to --from)
                           Default: 7

    -r, --repo REPO        GitHub repository in format "owner/repo"
                           Default: current repository

    -s, --save [DIR]       Save PR details to files (one file per PR)
                           Optional: specify output directory
                           Default: ./out

    -h, --help             Display this help message

EXAMPLES:
    # List all merged PRs from last 7 days (default)
    $0

    # List merged PRs from specific authors
    $0 --authors "john,jane,bob"

    # List merged PRs from last 30 days
    $0 --days 30

    # List merged PRs within a specific date range
    $0 --from "2025-10-01" --to "2025-10-31"

    # Combine filters: specific authors and date range
    $0 --authors "john,jane" --from "2025-10-01" --to "2025-10-31"

    # Query a specific repository
    $0 --repo "owner/repo" --days 30

    # Save PR details to files in ./out directory
    $0 --save

    # Save PR details to custom directory
    $0 --save /path/to/output --days 30

EOF
}

# Function to calculate date N days ago
date_days_ago() {
    local days=$1
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        date -v-${days}d +%Y-%m-%d
    else
        # Linux
        date -d "$days days ago" +%Y-%m-%d
    fi
}

# Function to get today's date
today() {
    date +%Y-%m-%d
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--authors)
            AUTHORS="$2"
            shift 2
            ;;
        -f|--from)
            FROM_DATE="$2"
            shift 2
            ;;
        -t|--to)
            TO_DATE="$2"
            shift 2
            ;;
        -d|--days)
            DEFAULT_DAYS="$2"
            shift 2
            ;;
        -r|--repo)
            REPO="$2"
            shift 2
            ;;
        -s|--save)
            SAVE_TO_FILE=true
            # Check if next argument is a directory path (not starting with -)
            if [[ $# -gt 1 && ! "$2" =~ ^- ]]; then
                OUTPUT_DIR="$2"
                shift 2
            else
                shift
            fi
            ;;
        -h|--help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    show_help
    exit 0
fi

# Set default dates if not provided
if [ -z "$FROM_DATE" ]; then
    FROM_DATE=$(date_days_ago $DEFAULT_DAYS)
fi

if [ -z "$TO_DATE" ]; then
    TO_DATE=$(today)
fi

# Validate date format
validate_date() {
    local date=$1
    if ! [[ $date =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo -e "${RED}Error: Invalid date format: $date${NC}"
        echo -e "${YELLOW}Expected format: YYYY-MM-DD${NC}"
        exit 1
    fi
}

validate_date "$FROM_DATE"
validate_date "$TO_DATE"

# Build search query
SEARCH_QUERY="is:pr is:merged merged:$FROM_DATE..$TO_DATE"

# Add author filters if provided
if [ -n "$AUTHORS" ]; then
    IFS=',' read -ra AUTHOR_ARRAY <<< "$AUTHORS"
    for author in "${AUTHOR_ARRAY[@]}"; do
        # Trim whitespace
        author=$(echo "$author" | xargs)
        SEARCH_QUERY="$SEARCH_QUERY author:$author"
    done
fi

# Display filter information
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Merged Pull Requests${NC}"
echo -e "${BLUE}========================================${NC}"
if [ -n "$REPO" ]; then
    echo -e "${GREEN}Repository:${NC} $REPO"
else
    echo -e "${GREEN}Repository:${NC} Current"
fi
echo -e "${GREEN}Date Range:${NC} $FROM_DATE to $TO_DATE"
if [ -n "$AUTHORS" ]; then
    echo -e "${GREEN}Authors:${NC} $AUTHORS"
else
    echo -e "${GREEN}Authors:${NC} All"
fi
echo -e "${BLUE}========================================${NC}"
echo ""

# Execute gh pr list command
echo -e "${YELLOW}Fetching merged pull requests...${NC}"
echo ""

# Build gh command with optional -R flag
GH_CMD="gh pr list"
if [ -n "$REPO" ]; then
    GH_CMD="$GH_CMD -R $REPO"
fi

# Run the gh command and capture output
PR_DATA=$($GH_CMD \
    --state merged \
    --search "$SEARCH_QUERY" \
    --limit 1000 \
    --json number,title,author,mergedAt,url)

# Display PRs in table format
echo "$PR_DATA" | jq -r '.[] | "#" + (.number | tostring) + "\t" + (.title | .[0:120]) + "\t" + .author.login + "\t" + (.mergedAt | .[0:10]) + "\t" + .url'

# Check if command succeeded
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to retrieve pull requests${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Successfully retrieved merged pull requests${NC}"

# Save PR details to files if --save option is enabled
if [ "$SAVE_TO_FILE" = true ]; then
    echo ""
    echo -e "${YELLOW}Saving PR details to files...${NC}"

    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"

    # Get the number of PRs
    PR_COUNT=$(echo "$PR_DATA" | jq '. | length')

    if [ "$PR_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}No PRs to save.${NC}"
    else
        # Process each PR
        echo "$PR_DATA" | jq -c '.[]' | while read -r pr; do
            PR_NUMBER=$(echo "$pr" | jq -r '.number')
            PR_TITLE=$(echo "$pr" | jq -r '.title')
            PR_AUTHOR=$(echo "$pr" | jq -r '.author.login')
            PR_MERGED_AT=$(echo "$pr" | jq -r '.mergedAt | .[0:10]')
            PR_URL=$(echo "$pr" | jq -r '.url')

            # Fetch full PR details including body and commits
            echo -e "${BLUE}  Fetching details for PR #${PR_NUMBER}...${NC}"

            # Build gh pr view command
            GH_VIEW_CMD="gh pr view $PR_NUMBER"
            if [ -n "$REPO" ]; then
                GH_VIEW_CMD="$GH_VIEW_CMD -R $REPO"
            fi

            # Get full PR body
            PR_BODY=$($GH_VIEW_CMD --json body --jq '.body')

            # Get list of commits with author and message
            COMMITS=$($GH_VIEW_CMD --json commits --jq '.commits[] | "- " + .authors[0].login + ": " + .messageHeadline')

            # Create filename (sanitize title for filesystem)
            SAFE_TITLE=$(echo "$PR_TITLE" | tr '/' '-' | tr ' ' '_' | tr -cd '[:alnum:]_-' | cut -c1-100)
            FILENAME="${OUTPUT_DIR}/PR-${PR_NUMBER}-${SAFE_TITLE}.md"

            # Write PR details to file
            cat > "$FILENAME" << PREOF
# PR #${PR_NUMBER}: ${PR_TITLE}

**Author:** ${PR_AUTHOR}
**Merged At:** ${PR_MERGED_AT}
**URL:** ${PR_URL}

---

## Description

${PR_BODY}

---

## Commits

${COMMITS}

---

*Generated by list_merged_pr.sh on $(date)*
PREOF

            echo -e "${GREEN}  ✓ Saved to: ${FILENAME}${NC}"
        done

        echo ""
        echo -e "${GREEN}✓ Saved ${PR_COUNT} PR(s) to ${OUTPUT_DIR}/${NC}"
    fi
fi
