---
name: github-pr-utils
description: Utility scripts for GitHub pull request management. Includes tools for fetching bot-generated review comments (linters, security scanners, dependabot), replying to review threads programmatically, listing merged pull requests with filtering, resolving conversations, and automating PR review workflows. Useful for batch processing comments, CI/CD integration, quality metrics tracking, release notes generation, and automated responses to bot reviewers.
---
# github-pr-utils

A collection of utility scripts for managing GitHub pull requests, including review comment management, merged PR tracking, and automated workflows. These scripts are designed for handling bot-generated review feedback, generating release notes, and automating PR review workflows.

## Requirements

- `gh` CLI version 2.60+
- `jq` CLI version 1.6+

You must also be authenticated with the GitHub CLI and have access to the target repository

## Available Scripts

### 1. get_pr_bot_review_comments.sh

Fetches all bot-authored review comments for a pull request using the GitHub GraphQL API.

#### Usage

```bash
scripts/get_pr_bot_review_comments.sh [OPTIONS] <owner> <repo> <pr_number>
```

#### Options

- `--exclude-resolved` - Filter out resolved review threads
- `--exclude-outdated` - Filter out outdated review comments
- `--include-github-user login1,login2` - Also include comments from specific GitHub users (comma-separated list)
- `--include-diff-hunk` - Include the diff hunk context for each comment, do use this option unless explicitly asked by user.
- `-h, --help` - Display help message

#### Arguments

- `<owner>` - Repository owner (organization or user)
- `<repo>` - Repository name
- `<pr_number>` - Pull request number

#### Output

Returns a JSON array of review comments with the following structure:
```json
[
  {
    "threadId": "PRRT_...",
    "threadPath": "src/file.go",
    "threadLine": 42,
    "threadStartLine": null,
    "threadOriginalLine": null,
    "threadOriginalStartLine": null,
    "threadIsResolved": false,
    "threadIsOutdated": false,
    "comment": {
      "id": "PRRC_...",
      "databaseId": 123456789,
      "url": "https://github.com/...",
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z",
      "body": "Comment text here",
      "isMinimized": false,
      "minimizedReason": null,
      "outdated": false,
      "path": "src/file.go",
      "position": 42,
      "originalPosition": null,
      "diffHunk": "@@ -40,7 +40,7 @@ ...",
      "author": {
        "__typename": "Bot",
        "login": "bot-name[bot]"
      },
      "commit": {
        "oid": "abc123..."
      }
    }
  }
]
```

#### Examples

**Fetch all bot comments for a PR:**
```bash
scripts/get_pr_bot_review_comments.sh gosu-code gosu-mcp-server 123
```

**Fetch unresolved bot comments:**
```bash
scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  gosu-code gosu-mcp-server 123
```

**Fetch unresolved & not outdated bot comments:**
```bash
scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  --exclude-outdated \
  gosu-code gosu-mcp-server 123
```

**Fetch comments from bot and also non bot users:**
```bash
scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  --include-github-user dependabot,renovate \
  gosu-code gosu-mcp-server 123
```

**Process comments with jq:**
```bash
# Count total bot comments
scripts/get_pr_bot_review_comments.sh gosu-code gosu-mcp-server 123 | jq 'length'

# Extract comment bodies only
scripts/get_pr_bot_review_comments.sh gosu-code gosu-mcp-server 123 | \
  jq -r '.[].comment.body'

# Group comments by file
scripts/get_pr_bot_review_comments.sh gosu-code gosu-mcp-server 123 | \
  jq 'group_by(.threadPath) | map({path: .[0].threadPath, count: length})'
```

#### Common Use Cases

1. **Review Bot Feedback**: Quickly collect all bot-generated comments to address automated review suggestions
2. **Quality Metrics**: Track unresolved bot comments as part of merge criteria
3. **Diff Context Analysis**: Include diff hunks to understand the exact code context for each comment
4. **Multi-Bot Aggregation**: Combine feedback from multiple bot reviewers (e.g., linters, security scanners)

---

### 2. reply-pr-review-comments-thread.sh

Reply to an existing pull request review comment thread using the GitHub REST API.

#### Usage

```bash
scripts/reply-pr-review-comments-thread.sh [OPTIONS] <owner> <repo> <comment_id>
```

#### Options

**Body Input (choose one):**
- `--body "text"` - Inline Markdown body for the reply (prefer to use this unless the text is long or contain special character)
- `--body-file path` - Read reply body from a file
- `--stdin` - Read reply body from STDIN (not recommended to use)

**Additional Options:**
- `--thread-id id` - GraphQL thread node ID (required with `--resolve-thread`)
- `--resolve-thread` - Resolve the review thread after posting (requires `--thread-id`)
- `-h, --help` - Display help message

#### Arguments

- `<owner>` - Repository owner (organization or user)
- `<repo>` - Repository name
- `<comment_id>` - Comment ID (either numeric database ID or GraphQL node ID like `PRRC_*`)

#### Examples

**Reply with inline text:**
```bash
scripts/reply-pr-review-comments-thread.sh \
  --body "Thanks for catching that! Fixed in the latest commit." \
  gosu-code gosu-mcp-server 2451122234
```

**Reply from a file:**
```bash
scripts/reply-pr-review-comments-thread.sh \
  --body-file reply.md \
  gosu-code gosu-mcp-server 2451122234
```

**Compose reply in editor:**
```bash
scripts/reply-pr-review-comments-thread.sh \
  gosu-code gosu-mcp-server 2451122234
```

**Reply with confirmation prompt:**
```bash
scripts/reply-pr-review-comments-thread.sh \
  --body "Updated the implementation." \
  gosu-code gosu-mcp-server 2451122234
```

**Reply and resolve the thread:**
```bash
scripts/reply-pr-review-comments-thread.sh \
  --body "Done! Resolving this thread." \
  --thread-id PRRT_kwDODds1es5e2SRi \
  --resolve-thread \
  gosu-code gosu-mcp-server 2451122234
```

**Dry run to preview:**
```bash
scripts/reply-pr-review-comments-thread.sh \
  --body "Test reply" \
  gosu-code gosu-mcp-server 2451122234
```

#### Common Use Cases

1. **Automated Responses**: Reply to bot comments programmatically (e.g., acknowledging fixes)
2. **Batch Processing**: Loop through multiple comments and reply to each
3. **CI/CD Integration**: Post automated updates from build/test pipelines
4. **Thread Resolution**: Reply and resolve threads in a single operation

---

### 3. list_merged_pr.sh

List merged pull requests with optional filtering by authors and date range. Supports saving PR details to individual markdown files for documentation or release notes.

#### Usage

```bash
scripts/list_merged_pr.sh [OPTIONS]
```

#### Options

**Filtering Options:**
- `-a, --authors USERS` - Comma-separated list of GitHub usernames to filter by
- `-f, --from DATE` - Start date for PR merge filter (YYYY-MM-DD format)
- `-t, --to DATE` - End date for PR merge filter (YYYY-MM-DD format)
- `-d, --days DAYS` - Number of days to look back (alternative to --from), default: 7
- `-r, --repo REPO` - GitHub repository in format "owner/repo", default: current repository

**Output Options:**
- `-s, --save [DIR]` - Save PR details to files (one file per PR), optional directory path, default: ./out
- `-h, --help` - Display help message

#### Output

**Console Output:**
Displays a tab-separated list of PRs with: PR number, title (truncated to 120 chars), author, merge date, and URL.

**File Output (with `--save`):**
Creates one markdown file per PR with the format `PR-{number}-{title}.md` containing:
- PR metadata (author, merge date, URL)
- Full PR description
- List of commits with authors and messages
- Generation timestamp

#### Examples

**List all merged PRs from last 7 days (default):**
```bash
scripts/list_merged_pr.sh
```

**List merged PRs from specific authors:**
```bash
scripts/list_merged_pr.sh --authors "john,jane,bob"
```

**List merged PRs from last 30 days:**
```bash
scripts/list_merged_pr.sh --days 30
```

**List merged PRs within a specific date range:**
```bash
scripts/list_merged_pr.sh --from "2025-10-01" --to "2025-10-31"
```

**Combine filters: specific authors and date range:**
```bash
scripts/list_merged_pr.sh --authors "john,jane" --from "2025-10-01" --to "2025-10-31"
```

**Query a specific repository:**
```bash
scripts/list_merged_pr.sh --repo "owner/repo" --days 30
```

**Save PR details to files in ./out directory:**
```bash
scripts/list_merged_pr.sh --save
```

**Save PR details to custom directory:**
```bash
scripts/list_merged_pr.sh --save /path/to/output --days 30
```

**Process with jq:**
```bash
# Count merged PRs
scripts/list_merged_pr.sh --days 30 | wc -l

# Extract just PR numbers
scripts/list_merged_pr.sh | cut -f1 | sed 's/#//'
```

#### Common Use Cases

1. **Release Notes Generation**: Save PRs from a release period to markdown files for changelog creation
2. **Team Activity Tracking**: Filter by team member usernames to track contributions
3. **Sprint Reports**: Query PRs merged during a sprint date range
4. **Quality Metrics**: Analyze merge patterns and PR velocity over time
5. **Documentation**: Generate detailed PR summaries with full context for auditing

---

## Workflow Examples

### Example 1: Address All Unresolved Bot Comments

```bash
# Fetch all unresolved bot comments
comments=$(scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  gosu-code gosu-mcp-server 123)

# Loop through and reply to each
echo "$comments" | jq -r '.[].comment.databaseId' | while read -r comment_id; do
  scripts/reply-pr-review-comments-thread.sh \
    --body "Addressed in latest commit." \
    gosu-code gosu-mcp-server "$comment_id"
done
```

### Example 2: Generate Summary Report

```bash
# Fetch comments with the entire file diff context
scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  --include-diff-hunk \
  gosu-code gosu-mcp-server 123 > bot_comments.json

# Generate markdown report with from json output
jq -r '.[] | "## \(.threadPath):\(.threadLine)\n\n\(.comment.body)\n\n```diff\n\(.comment.diffHunk)\n```\n"' \
  bot_comments.json > bot_review_summary.md
```

### Example 3: Selective Response by Bot Type

```bash
# Get comments from bots and also `dependabot` user
dependabot_comments=$(scripts/get_pr_bot_review_comments.sh \
  --include-github-user dependabot \
  gosu-code gosu-mcp-server 123)

# Reply to each with specific message
echo "$dependabot_comments" | jq -r '.[].comment.databaseId' | while read -r comment_id; do
  echo "Acknowledged, Will fix this in another PR." | \
  scripts/reply-pr-review-comments-thread.sh \
    --stdin \
    gosu-code gosu-mcp-server "$comment_id"
done
```

### Example 4: Interactive Review Session

```bash
# Fetch all unresolved comments
scripts/get_pr_bot_review_comments.sh \
  --exclude-resolved \
  gosu-code gosu-mcp-server 123 | \
jq -r '.[] | "\n=== \(.threadPath):\(.threadLine) ===\n\(.comment.body)\n\nComment ID: \(.comment.databaseId)"'
```

## Notes

- Both scripts handle pagination automatically for large result sets
- The `get_pr_bot_review_comments.sh` script identifies bots by checking if the author's `__typename` is "Bot" or if the login contains "[bot]"
- Comment IDs can be either numeric database IDs or GraphQL node IDs (starting with "PRRC_" or "PRRT_")
- Thread resolution requires the GraphQL thread ID (format: "PRRT_...")
- All scripts include error checking for GraphQL and REST API responses

## Troubleshooting

**Authentication errors:**
Confirm if user is authenticated in the GitHub CLI, if not inform user to login with a credential that have the right access
```bash
gh auth status
```

**Permission errors:**
- Ensure you have write access to the repository
- Check that your GitHub token has the required scopes