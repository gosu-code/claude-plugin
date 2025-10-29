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
Fetch all bot-authored review comments for a pull request using the GitHub CLI.

Usage:
  scripts/get_pr_bot_review_comments.sh [--exclude-resolved] [--exclude-outdated] [--include-github-user login1,login2] [--include-diff-hunk] <owner> <repo> <pr_number>

Example:
  scripts/get_pr_bot_review_comments.sh --exclude-resolved --include-diff-hunk --include-github-user 0xgosu theunigroup utx 14147

Requires:
  - gh (GitHub CLI) authenticated for the target repository
  - jq
USAGE
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

EXCLUDE_RESOLVED=false
EXCLUDE_OUTDATED=false
INCLUDE_USERS=()
INCLUDE_DIFF_HUNK=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --exclude-resolved)
      EXCLUDE_RESOLVED=true
      shift
      ;;
    --exclude-outdated)
      EXCLUDE_OUTDATED=true
      shift
      ;;
    --include-github-user)
      if [ "$#" -lt 2 ]; then
        echo "error: --include-github-user requires a comma-separated list" >&2
        exit 1
      fi
      shift
      raw_users=$1
      raw_users=${raw_users// /}
      IFS=',' read -r -a parsed_users <<<"$raw_users"
      for login in "${parsed_users[@]}"; do
        if [ -n "$login" ]; then
          INCLUDE_USERS+=("$login")
        fi
      done
      shift
      ;;
    --include-diff-hunk)
      INCLUDE_DIFF_HUNK=true
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

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required" >&2
  exit 1
fi

OWNER=$1
NAME=$2
NUMBER=$3

THREAD_QUERY_WITH_DIFF=$(cat <<'GRAPHQL'
query($owner: String!, $name: String!, $number: Int!, $threadCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $threadCursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          startLine
          originalLine
          originalStartLine
          comments(first: 100) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              id
              databaseId
              url
              createdAt
              updatedAt
              body
              isMinimized
              minimizedReason
              outdated
              path
              position
              originalPosition
              diffHunk
              author {
                __typename
                login
              }
              commit {
                oid
              }
            }
          }
        }
      }
    }
  }
}
GRAPHQL
)

THREAD_QUERY_NO_DIFF=$(cat <<'GRAPHQL'
query($owner: String!, $name: String!, $number: Int!, $threadCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $threadCursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          startLine
          originalLine
          originalStartLine
          comments(first: 100) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              id
              databaseId
              url
              createdAt
              updatedAt
              body
              isMinimized
              minimizedReason
              outdated
              path
              position
              originalPosition
              author {
                __typename
                login
              }
              commit {
                oid
              }
            }
          }
        }
      }
    }
  }
}
GRAPHQL
)

COMMENT_QUERY_WITH_DIFF=$(cat <<'GRAPHQL'
query($threadId: ID!, $commentCursor: String) {
  node(id: $threadId) {
    ... on PullRequestReviewThread {
      comments(first: 100, after: $commentCursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          databaseId
          url
          createdAt
          updatedAt
          body
          isMinimized
          minimizedReason
          outdated
          path
          position
          originalPosition
          diffHunk
          author {
            __typename
            login
          }
          commit {
            oid
          }
        }
      }
    }
  }
}
GRAPHQL
)

COMMENT_QUERY_NO_DIFF=$(cat <<'GRAPHQL'
query($threadId: ID!, $commentCursor: String) {
  node(id: $threadId) {
    ... on PullRequestReviewThread {
      comments(first: 100, after: $commentCursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          databaseId
          url
          createdAt
          updatedAt
          body
          isMinimized
          minimizedReason
          outdated
          path
          position
          originalPosition
          author {
            __typename
            login
          }
          commit {
            oid
          }
        }
      }
    }
  }
}
GRAPHQL
)

if [ "$INCLUDE_DIFF_HUNK" = "true" ]; then
  THREAD_QUERY=$THREAD_QUERY_WITH_DIFF
  COMMENT_QUERY=$COMMENT_QUERY_WITH_DIFF
else
  THREAD_QUERY=$THREAD_QUERY_NO_DIFF
  COMMENT_QUERY=$COMMENT_QUERY_NO_DIFF
fi

cleanup() {
  rm -f "$TMP_OUTPUT"
}
trap cleanup EXIT

check_graphql_errors() {
  local payload=$1
  if jq -e '.errors? // [] | length > 0' >/dev/null 2>&1 <<<"$payload"; then
    echo "error: GraphQL query failed" >&2
    jq '.errors' <<<"$payload" >&2 || true
    exit 1
  fi
}

TMP_OUTPUT=$(mktemp)

append_comment() {
  local thread_json=$1
  local comment_json=$2

  if [ "$EXCLUDE_RESOLVED" = "true" ]; then
    local resolved
    resolved=$(jq -r '.threadIsResolved // false' <<<"$thread_json")
    if [ "$resolved" = "true" ]; then
      return
    fi
  fi

  if [ "$EXCLUDE_OUTDATED" = "true" ]; then
    local outdated
    outdated=$(jq -r '.threadIsOutdated // false' <<<"$thread_json")
    if [ "$outdated" = "true" ]; then
      return
    fi
  fi

  local author_type
  author_type=$(jq -r '.author.__typename // empty' <<<"$comment_json")

  local author_login
  author_login=$(jq -r '.author.login // empty' <<<"$comment_json")

  local include_author=false
  local author_login_lower
  author_login_lower=$(printf '%s' "$author_login" | tr '[:upper:]' '[:lower:]')
  if [ "${INCLUDE_USERS+set}" ]; then
    for include_login in "${INCLUDE_USERS[@]}"; do
      local include_lower
      include_lower=$(printf '%s' "$include_login" | tr '[:upper:]' '[:lower:]')
      if [ "$author_login_lower" = "$include_lower" ]; then
        include_author=true
        break
      fi
    done
  fi

  if [ "$author_type" = "Bot" ] || [[ "$author_login" == *"[bot]" ]] || [ "$include_author" = "true" ]; then
    jq -n \
      --argjson thread "$thread_json" \
      --argjson comment "$comment_json" \
      '$thread + {comment: $comment}' >>"$TMP_OUTPUT"
  fi
}

thread_cursor=""
while :; do
  thread_cmd=(gh api graphql -F owner="$OWNER" -F name="$NAME" -F number="$NUMBER")
  if [ -n "$thread_cursor" ]; then
    thread_cmd+=(-F threadCursor="$thread_cursor")
  fi
  thread_cmd+=(-f query="$THREAD_QUERY")

  thread_response=$("${thread_cmd[@]}")
  check_graphql_errors "$thread_response"

  while IFS= read -r thread; do
    thread_id=$(jq -r '.id' <<<"$thread")
    thread_info=$(jq -c '{threadId: .id, threadPath: .path, threadLine: .line, threadStartLine: .startLine, threadOriginalLine: .originalLine, threadOriginalStartLine: .originalStartLine, threadIsResolved: .isResolved, threadIsOutdated: .isOutdated}' <<<"$thread")

    while IFS= read -r comment; do
      append_comment "$thread_info" "$comment"
    done < <(jq -c '.comments.nodes[]?' <<<"$thread")

    comments_has_next=$(jq -r '.comments.pageInfo.hasNextPage' <<<"$thread")
    comments_cursor=$(jq -r '.comments.pageInfo.endCursor' <<<"$thread")

    while [ "$comments_has_next" = "true" ] && [ "$comments_cursor" != "null" ] && [ -n "$comments_cursor" ]; do
      comment_response=$(gh api graphql -F threadId="$thread_id" -F commentCursor="$comments_cursor" -f query="$COMMENT_QUERY")
      check_graphql_errors "$comment_response"

      while IFS= read -r comment; do
        append_comment "$thread_info" "$comment"
      done < <(jq -c '.data.node.comments.nodes[]?' <<<"$comment_response")

      comments_has_next=$(jq -r '.data.node.comments.pageInfo.hasNextPage' <<<"$comment_response")
      comments_cursor=$(jq -r '.data.node.comments.pageInfo.endCursor' <<<"$comment_response")
    done
  done < <(jq -c '.data.repository.pullRequest.reviewThreads.nodes[]?' <<<"$thread_response")

  has_next=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage' <<<"$thread_response")
  if [ "$has_next" != "true" ]; then
    break
  fi
  thread_cursor=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor' <<<"$thread_response")
  if [ "$thread_cursor" = "null" ] || [ -z "$thread_cursor" ]; then
    break
  fi
done

jq -s '.' "$TMP_OUTPUT"
