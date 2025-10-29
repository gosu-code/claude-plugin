#!/usr/bin/env bash
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
set -euo pipefail

usage() {
  cat <<'USAGE'
Reply to an existing pull request review comment thread using the GitHub CLI.

Usage:
  scripts/reply-pr-review-comments-thread.sh [options] <owner> <repo> <comment_id>

  <comment_id> may be either the numeric database ID or the GraphQL node ID (e.g. PRRC_*).

Options:
  --body "text"            Inline Markdown body for the reply.
  --body-file path         Read reply body from the given file.
  --stdin                  Read reply body from STDIN.
  --editor                 Open $EDITOR (or $VISUAL) to compose the reply.
  --confirm                Ask for confirmation before posting.
  --dry-run                Show the payload without sending the reply.
  --thread-id id           GraphQL thread node ID (required with --resolve-thread).
  --resolve-thread         Resolve the review thread after posting (requires --thread-id).
  -h, --help               Show this help message.

Examples:
  scripts/reply-pr-review-comments-thread.sh \\
    --body "Thanks for catching that! Updated the pre-flight check." \\
    theunigroup utx 2451122234

  scripts/reply-pr-review-comments-thread.sh \\
    --body-file reply.md --confirm --thread-id PRRT_kwDODds1es5e2SRi --resolve-thread \\
    theunigroup utx 2451122234

Requires:
  - gh (GitHub CLI) authenticated for the target repository
  - jq
USAGE
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required" >&2
  exit 1
fi

check_graphql_errors() {
  local payload=$1
  if jq -e '.errors? // [] | length > 0' >/dev/null 2>&1 <<<"$payload"; then
    echo "error: GraphQL query failed" >&2
    jq '.errors' <<<"$payload" >&2 || true
    exit 1
  fi
}

COMMENT_INFO_QUERY=$(cat <<'GRAPHQL'
query($commentId: ID!) {
  node(id: $commentId) {
    ... on PullRequestReviewComment {
      url
      path
      databaseId
      line
      originalLine
      position
      pullRequest {
        number
        url
      }
    }
  }
}
GRAPHQL
)

BODY_SOURCE=""
BODY_INLINE=""
BODY_FILE=""
READ_STDIN=false
OPEN_EDITOR=false
PROMPT_CONFIRM=false
DRY_RUN=false
THREAD_ID=""
RESOLVE_THREAD=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --body)
      if [ "$#" -lt 2 ]; then
        echo "error: --body requires an argument" >&2
        exit 1
      fi
      if [ -n "$BODY_SOURCE" ]; then
        echo "error: only one of --body, --body-file, or --stdin may be specified" >&2
        exit 1
      fi
      BODY_SOURCE="inline"
      BODY_INLINE=$2
      shift 2
      ;;
    --body-file)
      if [ "$#" -lt 2 ]; then
        echo "error: --body-file requires a path argument" >&2
        exit 1
      fi
      if [ -n "$BODY_SOURCE" ]; then
        echo "error: only one of --body, --body-file, or --stdin may be specified" >&2
        exit 1
      fi
      BODY_SOURCE="file"
      BODY_FILE=$2
      shift 2
      ;;
    --stdin)
      if [ -n "$BODY_SOURCE" ]; then
        echo "error: only one of --body, --body-file, or --stdin may be specified" >&2
        exit 1
      fi
      BODY_SOURCE="stdin"
      READ_STDIN=true
      shift
      ;;
    --editor)
      OPEN_EDITOR=true
      shift
      ;;
    --confirm)
      PROMPT_CONFIRM=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --thread-id)
      if [ "$#" -lt 2 ]; then
        echo "error: --thread-id requires an argument" >&2
        exit 1
      fi
      THREAD_ID=$2
      shift 2
      ;;
    --resolve-thread)
      RESOLVE_THREAD=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "error: unknown option $1" >&2
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -ne 3 ]; then
  usage
  exit 1
fi

OWNER=$1
REPO=$2
COMMENT_INPUT=$3

COMMENT_DB_ID=""
COMMENT_NODE_ID=""

if [[ "$COMMENT_INPUT" =~ ^[0-9]+$ ]]; then
  COMMENT_DB_ID=$COMMENT_INPUT
else
  COMMENT_NODE_ID=$COMMENT_INPUT
fi

if [ "$RESOLVE_THREAD" = "true" ] && [ -z "$THREAD_ID" ]; then
  echo "error: --resolve-thread requires --thread-id" >&2
  exit 1
fi

if [ -z "$BODY_SOURCE" ] && [ -t 0 ] && [ "$OPEN_EDITOR" = "false" ]; then
  echo "error: reply body not provided. Use --body, --body-file, --stdin, or --editor." >&2
  exit 1
fi

if [ -z "$BODY_SOURCE" ] && [ ! -t 0 ]; then
  BODY_SOURCE="stdin"
  READ_STDIN=true
fi

BODY_CONTENT=""
case "$BODY_SOURCE" in
  inline)
    BODY_CONTENT=$BODY_INLINE
    ;;
  file)
    if [ ! -f "$BODY_FILE" ]; then
      echo "error: file not found: $BODY_FILE" >&2
      exit 1
    fi
    BODY_CONTENT=$(cat "$BODY_FILE")
    ;;
  stdin)
    BODY_CONTENT=$(cat)
    ;;
  "")
    BODY_CONTENT=""
    ;;
esac

TMP_EDITOR_FILE=""
TMP_BODY_FILE=""
cleanup() {
  if [ -n "$TMP_EDITOR_FILE" ] && [ -f "$TMP_EDITOR_FILE" ]; then
    rm -f "$TMP_EDITOR_FILE"
  fi
  if [ -n "$TMP_BODY_FILE" ] && [ -f "$TMP_BODY_FILE" ]; then
    rm -f "$TMP_BODY_FILE"
  fi
}
trap cleanup EXIT

if [ "$OPEN_EDITOR" = "true" ]; then
  TMP_EDITOR_FILE=$(mktemp)
  if [ -n "$BODY_CONTENT" ]; then
    printf '%s' "$BODY_CONTENT" >"$TMP_EDITOR_FILE"
  fi
  EDITOR_CMD=${VISUAL:-${EDITOR:-vi}}
  "$EDITOR_CMD" "$TMP_EDITOR_FILE"
  BODY_CONTENT=$(cat "$TMP_EDITOR_FILE")
fi

if ! [[ "$BODY_CONTENT" =~ [^[:space:]] ]]; then
  echo "error: reply body cannot be empty" >&2
  exit 1
fi

TMP_BODY_FILE=$(mktemp)
printf '%s' "$BODY_CONTENT" >"$TMP_BODY_FILE"

COMMENT_REST_RESPONSE=""
COMMENT_HTML_URL=""
if [ -n "$COMMENT_DB_ID" ]; then
  COMMENT_REST_RESPONSE=$(gh api \
    --header "Accept: application/vnd.github+json" \
    "repos/$OWNER/$REPO/pulls/comments/$COMMENT_DB_ID")
  COMMENT_NODE_ID=$(jq -r '.node_id // empty' <<<"$COMMENT_REST_RESPONSE")
  COMMENT_HTML_URL=$(jq -r '.html_url // empty' <<<"$COMMENT_REST_RESPONSE")
  if [ -z "$COMMENT_NODE_ID" ] || [ "$COMMENT_NODE_ID" = "null" ]; then
    echo "error: unable to determine GraphQL node id for comment $COMMENT_DB_ID" >&2
    exit 1
  fi
else
  COMMENT_HTML_URL=""
fi

if [ -z "$COMMENT_NODE_ID" ] || [ "$COMMENT_NODE_ID" = "null" ]; then
  echo "error: GraphQL node id for comment is required" >&2
  exit 1
fi

comment_info_response=$(gh api graphql -f commentId="$COMMENT_NODE_ID" -f query="$COMMENT_INFO_QUERY")
check_graphql_errors "$comment_info_response"

comment_database_id=$(jq -r '.data.node.databaseId // empty' <<<"$comment_info_response")
if [ -z "$COMMENT_DB_ID" ] || [ "$COMMENT_DB_ID" = "null" ]; then
  COMMENT_DB_ID=$comment_database_id
fi
if [ -z "$COMMENT_DB_ID" ] || [ "$COMMENT_DB_ID" = "null" ]; then
  echo "error: unable to determine numeric comment id" >&2
  exit 1
fi

comment_path=$(jq -r '.data.node.path // empty' <<<"$comment_info_response")
comment_line=$(jq -r '.data.node.line // empty' <<<"$comment_info_response")
if [ -z "$comment_line" ] || [ "$comment_line" = "null" ]; then
  comment_line=$(jq -r '.data.node.originalLine // empty' <<<"$comment_info_response")
fi
if [ -z "$comment_line" ] || [ "$comment_line" = "null" ]; then
  comment_line=$(jq -r '.data.node.position // empty' <<<"$comment_info_response")
fi
comment_line_suffix=""
if [ -n "$comment_line" ] && [ "$comment_line" != "null" ]; then
  comment_line_suffix=" line $comment_line"
fi
comment_pr_number=$(jq -r '.data.node.pullRequest.number // empty' <<<"$comment_info_response")
comment_pr_url=$(jq -r '.data.node.pullRequest.url // empty' <<<"$comment_info_response")
comment_url=$(jq -r '.data.node.url // empty' <<<"$comment_info_response")
if [ -z "$comment_url" ] || [ "$comment_url" = "null" ]; then
  comment_url=$COMMENT_HTML_URL
fi

if [ "$RESOLVE_THREAD" = "true" ] && [ -z "$THREAD_ID" ]; then
  echo "error: --resolve-thread requires --thread-id" >&2
  exit 1
fi

if [ "$DRY_RUN" = "true" ]; then
  cat <<EOF
Dry run: would POST reply to comment $COMMENT_INPUT (node: $COMMENT_NODE_ID) on $OWNER/$REPO
PR        : ${comment_pr_number:-unknown}
Parent    : ${comment_url:-<unknown>}
Location  : ${comment_path:-<unknown>}${comment_line_suffix:-}
Thread ID : ${THREAD_ID:-<not provided>}
Body:
---
$BODY_CONTENT
---
EOF
  exit 0
fi

if [ "$PROMPT_CONFIRM" = "true" ]; then
  printf 'Reply target: %s/%s (comment %s | node %s)\n' "$OWNER" "$REPO" "$COMMENT_INPUT" "$COMMENT_NODE_ID"
  if [ -n "$comment_pr_number" ] && [ "$comment_pr_number" != "null" ]; then
    if [ -n "$comment_pr_url" ] && [ "$comment_pr_url" != "null" ]; then
      printf 'Pull Request: #%s (%s)\n' "$comment_pr_number" "$comment_pr_url"
    else
      printf 'Pull Request: #%s\n' "$comment_pr_number"
    fi
  fi
  if [ -n "$comment_url" ] && [ "$comment_url" != "null" ]; then
    printf 'Parent comment: %s\n' "$comment_url"
  fi
  if [ -n "$comment_path" ] && [ "$comment_path" != "null" ]; then
    printf 'Location: %s' "$comment_path"
    if [ -n "$comment_line" ] && [ "$comment_line" != "null" ]; then
      printf ' line %s' "$comment_line"
    fi
    printf '\n'
  fi
  if [ -n "$THREAD_ID" ]; then
    printf 'Thread ID: %s\n' "$THREAD_ID"
  fi
  echo "Reply body:"
  echo "-----------"
  printf '%s\n' "$BODY_CONTENT"
  echo "-----------"
  read -r -p "Post reply? [y/N] " confirmation
  case "$confirmation" in
    y|Y|yes|YES)
      ;;
    *)
      echo "aborted"
      exit 0
      ;;
  esac
fi

if [ -z "$comment_pr_number" ] || [ "$comment_pr_number" = "null" ]; then
  echo "error: unable to determine pull request number for comment" >&2
  exit 1
fi

reply_response=$(gh api \
  --header "Accept: application/vnd.github+json" \
  "repos/$OWNER/$REPO/pulls/$comment_pr_number/comments" \
  -F in_reply_to="$COMMENT_DB_ID" \
  -F body=@"$TMP_BODY_FILE")

reply_html_url=$(jq -r '.html_url // empty' <<<"$reply_response")
reply_node_id=$(jq -r '.node_id // empty' <<<"$reply_response")
reply_db_id=$(jq -r '.id // empty' <<<"$reply_response")
reply_path=$(jq -r '.path // empty' <<<"$reply_response")
reply_line=$(jq -r 'if (.line != null) then (.line|tostring) elif (.original_line != null) then (.original_line|tostring) elif (.original_position != null) then (.original_position|tostring) else "" end' <<<"$reply_response")
reply_author=$(jq -r '.user.login // empty' <<<"$reply_response")
reply_pr_number=$comment_pr_number
reply_pr_url=$comment_pr_url

printf 'Reply posted: %s (node: %s, db: %s)\n' "${reply_html_url:-<no url>}" "${reply_node_id:-unknown}" "${reply_db_id:-unknown}"
if [ -n "$reply_author" ] && [ "$reply_author" != "null" ]; then
  printf 'Author: %s\n' "$reply_author"
fi
if [ -n "$reply_pr_number" ] && [ "$reply_pr_number" != "null" ]; then
  if [ -n "$reply_pr_url" ] && [ "$reply_pr_url" != "null" ]; then
    printf 'Pull Request: #%s (%s)\n' "$reply_pr_number" "$reply_pr_url"
  else
    printf 'Pull Request: #%s\n' "$reply_pr_number"
  fi
fi
if [ -n "$reply_path" ] && [ "$reply_path" != "null" ]; then
  printf 'Thread location: %s' "$reply_path"
  if [ -n "$reply_line" ] && [ "$reply_line" != "null" ]; then
    printf ' : line %s' "$reply_line"
  fi
  printf '\n'
fi

if [ "$RESOLVE_THREAD" = "true" ]; then
  RESOLVE_MUTATION=$(cat <<'GRAPHQL'
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}
GRAPHQL
)

  resolve_response=$(gh api graphql -f threadId="$THREAD_ID" -f query="$RESOLVE_MUTATION")
  if jq -e '.errors? // [] | length > 0' >/dev/null 2>&1 <<<"$resolve_response"; then
    echo "warning: reply posted, but failed to resolve thread" >&2
    jq '.errors' <<<"$resolve_response" >&2 || true
    exit 1
  fi

  is_resolved=$(jq -r '.data.resolveReviewThread.thread.isResolved // false' <<<"$resolve_response")
  if [ "$is_resolved" = "true" ]; then
    echo "Thread resolved."
  else
    echo "warning: reply posted, but thread did not report as resolved" >&2
  fi
fi
