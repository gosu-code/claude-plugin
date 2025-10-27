# Github MCP Server Usage

This file describes how to use the GitHub MCP Server tools (`mcp__github`, `mcp__github__*`, `github` MCP) effectively when delegate GitHub related requests to the GitHub MCP Server tools via the Codex MCP skill.

## Available Toolsets

The following sets of tools are available:

<!-- START AUTOMATED TOOLSETS -->
| Toolset       | Description                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| `context`     | **Strongly recommended**: Tools that provide information about the current user and operating context |
| `issues`      | GitHub Issues related tools                                                 |
| `pull_requests` | GitHub Pull Request related tools                                         |
| `repos`       | GitHub Repository related tools                                             |
| `users`       | GitHub User related tools                                                   |
<!-- END AUTOMATED TOOLSETS -->

## Tools

<!-- START AUTOMATED TOOLS -->
<details>

<tool-name>Context</tool-name>

- **get_me** - Get my user profile
  - No parameters required

- **get_team_members** - Get team members
  - `org`: Organization login (owner) that contains the team. (string, required)
  - `team_slug`: Team slug (string, required)

- **get_teams** - Get teams
  - `user`: Username to get teams for. If not provided, uses the authenticated user. (string, optional)

</details>

<details>

<tool-name>Issues</tool-name>

- **add_issue_comment** - Add comment to issue
  - `body`: Comment content (string, required)
  - `issue_number`: Issue number to comment on (number, required)
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)

- **assign_copilot_to_issue** - Assign Copilot to issue
  - `issueNumber`: Issue number (number, required)
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)

- **get_label** - Get a specific label from a repository.
  - `name`: Label name. (string, required)
  - `owner`: Repository owner (username or organization name) (string, required)
  - `repo`: Repository name (string, required)

- **issue_read** - Get issue details
  - `issue_number`: The number of the issue (number, required)
  - `method`: The read operation to perform on a single issue. 
Options are: 
1. get - Get details of a specific issue.
2. get_comments - Get issue comments.
3. get_sub_issues - Get sub-issues of the issue.
4. get_labels - Get labels assigned to the issue.
 (string, required)
  - `owner`: The owner of the repository (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: The name of the repository (string, required)

- **issue_write** - Create or update issue.
  - `assignees`: Usernames to assign to this issue (string[], optional)
  - `body`: Issue body content (string, optional)
  - `duplicate_of`: Issue number that this issue is a duplicate of. Only used when state_reason is 'duplicate'. (number, optional)
  - `issue_number`: Issue number to update (number, optional)
  - `labels`: Labels to apply to this issue (string[], optional)
  - `method`: Write operation to perform on a single issue.
Options are: 
- 'create' - creates a new issue. 
- 'update' - updates an existing issue.
 (string, required)
  - `milestone`: Milestone number (number, optional)
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)
  - `state`: New state (string, optional)
  - `state_reason`: Reason for the state change. Ignored unless state is changed. (string, optional)
  - `title`: Issue title (string, optional)
  - `type`: Type of this issue (string, optional)

- **list_issue_types** - List available issue types
  - `owner`: The organization owner of the repository (string, required)

- **list_issues** - List issues
  - `after`: Cursor for pagination. Use the endCursor from the previous page's PageInfo for GraphQL APIs. (string, optional)
  - `direction`: Order direction. If provided, the 'orderBy' also needs to be provided. (string, optional)
  - `labels`: Filter by labels (string[], optional)
  - `orderBy`: Order issues by field. If provided, the 'direction' also needs to be provided. (string, optional)
  - `owner`: Repository owner (string, required)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: Repository name (string, required)
  - `since`: Filter by date (ISO 8601 timestamp) (string, optional)
  - `state`: Filter by state, by default both open and closed issues are returned when not provided (string, optional)

- **search_issues** - Search issues
  - `order`: Sort order (string, optional)
  - `owner`: Optional repository owner. If provided with repo, only issues for this repository are listed. (string, optional)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `query`: Search query using GitHub issues search syntax (string, required)
  - `repo`: Optional repository name. If provided with owner, only issues for this repository are listed. (string, optional)
  - `sort`: Sort field by number of matches of categories, defaults to best match (string, optional)

- **sub_issue_write** - Change sub-issue
  - `after_id`: The ID of the sub-issue to be prioritized after (either after_id OR before_id should be specified) (number, optional)
  - `before_id`: The ID of the sub-issue to be prioritized before (either after_id OR before_id should be specified) (number, optional)
  - `issue_number`: The number of the parent issue (number, required)
  - `method`: The action to perform on a single sub-issue
Options are:
- 'add' - add a sub-issue to a parent issue in a GitHub repository.
- 'remove' - remove a sub-issue from a parent issue in a GitHub repository.
- 'reprioritize' - change the order of sub-issues within a parent issue in a GitHub repository. Use either 'after_id' or 'before_id' to specify the new position.
				 (string, required)
  - `owner`: Repository owner (string, required)
  - `replace_parent`: When true, replaces the sub-issue's current parent issue. Use with 'add' method only. (boolean, optional)
  - `repo`: Repository name (string, required)
  - `sub_issue_id`: The ID of the sub-issue to add. ID is not the same as issue number (number, required)

</details>

<details>

<tool-name>Pull Requests</tool-name>

- **add_comment_to_pending_review** - Add review comment to the requester's latest pending pull request review
  - `body`: The text of the review comment (string, required)
  - `line`: The line of the blob in the pull request diff that the comment applies to. For multi-line comments, the last line of the range (number, optional)
  - `owner`: Repository owner (string, required)
  - `path`: The relative path to the file that necessitates a comment (string, required)
  - `pullNumber`: Pull request number (number, required)
  - `repo`: Repository name (string, required)
  - `side`: The side of the diff to comment on. LEFT indicates the previous state, RIGHT indicates the new state (string, optional)
  - `startLine`: For multi-line comments, the first line of the range that the comment applies to (number, optional)
  - `startSide`: For multi-line comments, the starting side of the diff that the comment applies to. LEFT indicates the previous state, RIGHT indicates the new state (string, optional)
  - `subjectType`: The level at which the comment is targeted (string, required)

- **create_pull_request** - Open new pull request
  - `base`: Branch to merge into (string, required)
  - `body`: PR description (string, optional)
  - `draft`: Create as draft PR (boolean, optional)
  - `head`: Branch containing changes (string, required)
  - `maintainer_can_modify`: Allow maintainer edits (boolean, optional)
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)
  - `title`: PR title (string, required)

- **list_pull_requests** - List pull requests
  - `base`: Filter by base branch (string, optional)
  - `direction`: Sort direction (string, optional)
  - `head`: Filter by head user/org and branch (string, optional)
  - `owner`: Repository owner (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: Repository name (string, required)
  - `sort`: Sort by (string, optional)
  - `state`: Filter by state (string, optional)

- **merge_pull_request** - Merge pull request
  - `commit_message`: Extra detail for merge commit (string, optional)
  - `commit_title`: Title for merge commit (string, optional)
  - `merge_method`: Merge method (string, optional)
  - `owner`: Repository owner (string, required)
  - `pullNumber`: Pull request number (number, required)
  - `repo`: Repository name (string, required)

- **pull_request_read** - Get details for a single pull request
  - `method`: Action to specify what pull request data needs to be retrieved from GitHub. 
Possible options: 
 1. get - Get details of a specific pull request.
 2. get_diff - Get the diff of a pull request.
 3. get_status - Get status of a head commit in a pull request. This reflects status of builds and checks.
 4. get_files - Get the list of files changed in a pull request. Use with pagination parameters to control the number of results returned.
 5. get_review_comments - Get the review comments on a pull request. They are comments made on a portion of the unified diff during a pull request review. Use with pagination parameters to control the number of results returned.
 6. get_reviews - Get the reviews on a pull request. When asked for review comments, use get_review_comments method.
 7. get_comments - Get comments on a pull request. Use this if user doesn't specifically want review comments. Use with pagination parameters to control the number of results returned.
 (string, required)
  - `owner`: Repository owner (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `pullNumber`: Pull request number (number, required)
  - `repo`: Repository name (string, required)

- **pull_request_review_write** - Write operations (create, submit, delete) on pull request reviews.
  - `body`: Review comment text (string, optional)
  - `commitID`: SHA of commit to review (string, optional)
  - `event`: Review action to perform. (string, optional)
  - `method`: The write operation to perform on pull request review. (string, required)
  - `owner`: Repository owner (string, required)
  - `pullNumber`: Pull request number (number, required)
  - `repo`: Repository name (string, required)

- **request_copilot_review** - Request Copilot review
  - `owner`: Repository owner (string, required)
  - `pullNumber`: Pull request number (number, required)
  - `repo`: Repository name (string, required)

- **search_pull_requests** - Search pull requests
  - `order`: Sort order (string, optional)
  - `owner`: Optional repository owner. If provided with repo, only pull requests for this repository are listed. (string, optional)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `query`: Search query using GitHub pull request search syntax (string, required)
  - `repo`: Optional repository name. If provided with owner, only pull requests for this repository are listed. (string, optional)
  - `sort`: Sort field by number of matches of categories, defaults to best match (string, optional)

- **update_pull_request** - Edit pull request
  - `base`: New base branch name (string, optional)
  - `body`: New description (string, optional)
  - `draft`: Mark pull request as draft (true) or ready for review (false) (boolean, optional)
  - `maintainer_can_modify`: Allow maintainer edits (boolean, optional)
  - `owner`: Repository owner (string, required)
  - `pullNumber`: Pull request number to update (number, required)
  - `repo`: Repository name (string, required)
  - `reviewers`: GitHub usernames to request reviews from (string[], optional)
  - `state`: New state (string, optional)
  - `title`: New title (string, optional)

- **update_pull_request_branch** - Update pull request branch
  - `expectedHeadSha`: The expected SHA of the pull request's HEAD ref (string, optional)
  - `owner`: Repository owner (string, required)
  - `pullNumber`: Pull request number (number, required)
  - `repo`: Repository name (string, required)

</details>

<details>

<tool-name>Repositories</tool-name>

- **create_branch** - Create branch
  - `branch`: Name for new branch (string, required)
  - `from_branch`: Source branch (defaults to repo default) (string, optional)
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)

- **create_or_update_file** - Create or update file
  - `branch`: Branch to create/update the file in (string, required)
  - `content`: Content of the file (string, required)
  - `message`: Commit message (string, required)
  - `owner`: Repository owner (username or organization) (string, required)
  - `path`: Path where to create/update the file (string, required)
  - `repo`: Repository name (string, required)
  - `sha`: Required if updating an existing file. The blob SHA of the file being replaced. (string, optional)

- **create_repository** - Create repository
  - `autoInit`: Initialize with README (boolean, optional)
  - `description`: Repository description (string, optional)
  - `name`: Repository name (string, required)
  - `organization`: Organization to create the repository in (omit to create in your personal account) (string, optional)
  - `private`: Whether repo should be private (boolean, optional)

- **delete_file** - Delete file
  - `branch`: Branch to delete the file from (string, required)
  - `message`: Commit message (string, required)
  - `owner`: Repository owner (username or organization) (string, required)
  - `path`: Path to the file to delete (string, required)
  - `repo`: Repository name (string, required)

- **fork_repository** - Fork repository
  - `organization`: Organization to fork to (string, optional)
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)

- **get_commit** - Get commit details
  - `include_diff`: Whether to include file diffs and stats in the response. Default is true. (boolean, optional)
  - `owner`: Repository owner (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: Repository name (string, required)
  - `sha`: Commit SHA, branch name, or tag name (string, required)

- **get_file_contents** - Get file or directory contents
  - `owner`: Repository owner (username or organization) (string, required)
  - `path`: Path to file/directory (directories must end with a slash '/') (string, optional)
  - `ref`: Accepts optional git refs such as `refs/tags/{tag}`, `refs/heads/{branch}` or `refs/pull/{pr_number}/head` (string, optional)
  - `repo`: Repository name (string, required)
  - `sha`: Accepts optional commit SHA. If specified, it will be used instead of ref (string, optional)

- **get_latest_release** - Get latest release
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)

- **get_release_by_tag** - Get a release by tag name
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)
  - `tag`: Tag name (e.g., 'v1.0.0') (string, required)

- **get_tag** - Get tag details
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)
  - `tag`: Tag name (string, required)

- **list_branches** - List branches
  - `owner`: Repository owner (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: Repository name (string, required)

- **list_commits** - List commits
  - `author`: Author username or email address to filter commits by (string, optional)
  - `owner`: Repository owner (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: Repository name (string, required)
  - `sha`: Commit SHA, branch or tag name to list commits of. If not provided, uses the default branch of the repository. If a commit SHA is provided, will list commits up to that SHA. (string, optional)

- **list_releases** - List releases
  - `owner`: Repository owner (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: Repository name (string, required)

- **list_tags** - List tags
  - `owner`: Repository owner (string, required)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `repo`: Repository name (string, required)

- **push_files** - Push files to repository
  - `branch`: Branch to push to (string, required)
  - `files`: Array of file objects to push, each object with path (string) and content (string) (object[], required)
  - `message`: Commit message (string, required)
  - `owner`: Repository owner (string, required)
  - `repo`: Repository name (string, required)

- **search_code** - Search code
  - `order`: Sort order for results (string, optional)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `query`: Search query using GitHub's powerful code search syntax. Examples: 'content:Skill language:Java org:github', 'NOT is:archived language:Python OR language:go', 'repo:github/github-mcp-server'. Supports exact matching, language filters, path filters, and more. (string, required)
  - `sort`: Sort field ('indexed' only) (string, optional)

- **search_repositories** - Search repositories
  - `minimal_output`: Return minimal repository information (default: true). When false, returns full GitHub API repository objects. (boolean, optional)
  - `order`: Sort order (string, optional)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `query`: Repository search query. Examples: 'machine learning in:name stars:>1000 language:python', 'topic:react', 'user:facebook'. Supports advanced search syntax for precise filtering. (string, required)
  - `sort`: Sort repositories by field, defaults to best match (string, optional)

</details>

<details>

<tool-name>Users</tool-name>

- **search_users** - Search users
  - `order`: Sort order (string, optional)
  - `page`: Page number for pagination (min 1) (number, optional)
  - `perPage`: Results per page for pagination (min 1, max 100) (number, optional)
  - `query`: User search query. Examples: 'john smith', 'location:seattle', 'followers:>100'. Search is automatically scoped to type:user. (string, required)
  - `sort`: Sort users by number of followers or repositories, or when the person joined GitHub. (string, optional)

</details>
<!-- END AUTOMATED TOOLS -->
