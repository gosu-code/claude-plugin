# Linear MCP Server Usage

This file describes how to use the Linear MCP Server tools (`mcp__linear`, `mcp__linear__*`) effectively when delegating Linear related requests to the Linear MCP Server tools via the `codex-mcp` skill.

## Available Toolsets

The following sets of tools are available:

<!-- START AUTOMATED TOOLSETS -->
| Toolset       | Description                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| `context`     | **Strongly recommended**: Tools that provide information about the current user and team context |
| `issues`      | Linear issue management and commenting                                      |
| `projects`    | Project management and planning                                             |
| `documents`   | Document and knowledge base access                                          |
| `cycles`      | Work cycle and sprint management                                            |
<!-- END AUTOMATED TOOLSETS -->

## Tools

<!-- START AUTOMATED TOOLS -->
<details>

<tool-name>Context</tool-name>

- **get_user** - Retrieve information about a Linear user
  - `query`: User ID, name, email, or the keyword `me` (string, required)

- **get_team** - Look up a team using identifier, key, or name
  - `query`: Team UUID, key (e.g., `CORE`), or display name (string, required)

- **list_teams** - Page through teams in the workspace
  - `after`: Forward pagination cursor (string, optional)
  - `before`: Reverse pagination cursor (string, optional)
  - `createdAt`: Creation timestamp/duration filter (string, optional)
  - `includeArchived`: Include archived teams when true (boolean, optional)
  - `limit`: Page size (max 250) (number, optional)
  - `orderBy`: Sort key (e.g., `name`) (string, optional)
  - `query`: Text search on team name or key (string, optional)
  - `updatedAt`: Update timestamp/duration filter (string, optional)

- **list_users** - Search Linear users by keyword
  - `query`: Name, email, or other search text. Empty query lists users with default sorting (string, optional)

</details>

<details>

<tool-name>Issues</tool-name>

- **get_issue** - Fetch a Linear issue's current state, fields, relations, and attachments
  - `id`: Unique Linear issue ID (`01H...`) (string, required)

- **get_issue_status** - Resolve metadata for a specific issue status within a given team
  - `team`: Team identifier (UUID or key code such as `ENG`) (string, required)
  - `id`: Explicit status ID; supply when available (string, conditional)
  - `name`: Human-readable status name (e.g., `In Progress`) (string, conditional)

- **list_issues** - Flexible search across workspace issues with rich filters
  - `after`: Pagination cursor (forward) (string, optional)
  - `assignee`: Filter by user ID, name, email, or `me` (string, optional)
  - `before`: Pagination cursor (backward) (string, optional)
  - `createdAt`: Creation time filter (timestamp or duration) (string, optional)
  - `cycle`: Cycle ID or keyword (e.g., `current`) (string, optional)
  - `delegate`: Delegate (agent) identifier filter (string, optional)
  - `includeArchived`: Include archived issues when true (boolean, optional)
  - `label`: Label ID or name filter (string, optional)
  - `limit`: Page size (max 250) (number, optional)
  - `orderBy`: Sort key (commonly `updatedAt`) (string, optional)
  - `parentId`: Restrict to child issues under this parent (string, optional)
  - `project`: Project ID or key filter (string, optional)
  - `query`: Full-text search, supports Linear query DSL (string, optional)
  - `state`: Workflow status name or ID (string, optional)
  - `team`: Team key or ID (string, optional)
  - `updatedAt`: Last update timestamp/duration filter (string, optional)

- **list_issue_labels** - Fetch label definitions across the workspace or a specific team
  - `after`: Pagination cursor for forward traversal (string, optional)
  - `before`: Pagination cursor for reverse traversal (string, optional)
  - `limit`: Number of labels per page (max 250) (number, optional)
  - `name`: Case-insensitive name filter (string, optional)
  - `orderBy`: Sort field (e.g., `createdAt`) (string, optional)
  - `team`: Team key or ID to scope labels (string, optional)

- **list_issue_statuses** - Return the full set of workflow statuses for a team
  - `team`: Team key or ID whose statuses to fetch (string, required)

- **create_issue** - Open a new Linear issue scoped to a particular team
  - `team`: Team key, name, or ID that owns the issue (string, required)
  - `title`: Issue title rendered in Linear (string, required)
  - `assignee`: Assign to a user by ID, name, email, or `me` (string, optional)
  - `cycle`: Cycle name or ID such as `current` (string, optional)
  - `delegate`: Agent or teammate responsible for follow-up (string, optional)
  - `description`: Markdown body content (string, optional)
  - `dueDate`: ISO-8601 due date (string, optional)
  - `labels`: Array of label names or IDs (array of strings, optional)
  - `links`: Related resource links, each with `title` and `url` (array of objects, optional)
  - `parentId`: Parent issue ID when creating a sub-issue (string, optional)
  - `priority`: Priority level 0–4; avoid setting unless requested (number, optional)
  - `project`: Project name or ID to associate (string, optional)
  - `state`: Workflow state ID or name (string, optional)

- **create_issue_label** - Define a new label for issues at workspace or team scope
  - `name`: Label display name (string, required)
  - `color`: Hex color code (string, optional)
  - `description`: Help text describing the label (string, optional)
  - `isGroup`: Mark as a label group that cannot be applied directly (boolean, optional)
  - `parentId`: Parent label ID when nesting labels (string, optional)
  - `teamId`: Team ID if creating a team-scoped label (string, optional)

- **update_issue** - Modify fields on an existing Linear issue
  - `id`: Issue ID to mutate (string, required)
  - `assignee`: Update assignee by ID, name, email, or `me` (string, optional)
  - `cycle`: Adjust cycle membership (string, optional)
  - `delegate`: Change the delegated agent or teammate (string, optional)
  - `description`: Replace issue description markdown (string, optional)
  - `dueDate`: Update due date (string, optional)
  - `estimate`: Set or change effort estimate (number, optional)
  - `labels`: Complete replacement list of label names or IDs (array of strings, optional)
  - `links`: Replace linked resources array (array of objects, optional)
  - `parentId`: Reassign parent issue (string, optional)
  - `priority`: Priority level 0–4; avoid changing unless requested (number, optional)
  - `project`: Associate with a different project (string, optional)
  - `state`: New workflow state ID or name (string, optional)
  - `title`: Update the issue title (string, optional)

- **create_comment** - Create a Markdown comment on a Linear issue and optionally nest it under an existing comment
  - `body`: Markdown payload rendered inside the Linear issue thread (string, required)
  - `issueId`: Linear issue identifier receiving the comment (string, required)
  - `parentId`: Comment ID to reply to; omit to post a top-level comment (string, optional)

- **list_comments** - Enumerate every comment on a chosen issue, ordered chronologically
  - `issueId`: Linear issue whose comments are requested (string, required)

</details>

<details>

<tool-name>Projects</tool-name>

- **get_project** - Return a single Linear project by fuzzy query string
  - `query`: Project ID, name fragment, or key (string, required)

- **list_projects** - Search or page through projects with flexible filters
  - `after`: Forward pagination cursor (string, optional)
  - `before`: Reverse pagination cursor (string, optional)
  - `createdAt`: Creation timestamp/duration filter (string, optional)
  - `includeArchived`: Include archived projects when true (boolean, optional)
  - `initiative`: Initiative ID constraint (string, optional)
  - `limit`: Page size (max 250) (number, optional)
  - `member`: Restrict to projects with this member (string, optional)
  - `orderBy`: Sort key (e.g., `createdAt`) (string, optional)
  - `query`: Text search on project name (string, optional)
  - `state`: Project state (e.g., `In Progress`) (string, optional)
  - `team`: Team ID or key filter (string, optional)
  - `updatedAt`: Update timestamp/duration filter (string, optional)

- **list_project_labels** - Enumerate labels scoped to projects (distinct from issue labels)
  - `after`: Forward pagination cursor (string, optional)
  - `before`: Reverse pagination cursor (string, optional)
  - `limit`: Results per page (max 250) (number, optional)
  - `name`: Case-insensitive name match (string, optional)
  - `orderBy`: Sort order field (string, optional)

- **create_project** - Initialize a new Linear project with optional metadata
  - `team`: Team name or ID that owns the project (string, required)
  - `name`: Project title (string, required)
  - `description`: Markdown project description (string, optional)
  - `labels`: Labels to apply by name or ID (array of strings, optional)
  - `lead`: Project lead user identifier (string, optional)
  - `priority`: Priority 0–4; omit unless the user specifies (number, optional)
  - `startDate`: ISO-8601 start date (string, optional)
  - `state`: Project state name or ID (string, optional)
  - `summary`: Short plaintext summary (string, optional)
  - `targetDate`: ISO-8601 target completion date (string, optional)

- **update_project** - Modify an existing project and its metadata
  - `id`: Project ID to update (string, required)
  - `name`: New project title (string, optional)
  - `description`: Markdown description replacement (string, optional)
  - `labels`: Complete replacement list of labels by name or ID (array of strings, optional)
  - `lead`: Update project lead (string, optional)
  - `priority`: Priority 0–4; only set when explicitly requested (number, optional)
  - `startDate`: Adjust start date (string, optional)
  - `state`: New project state name or ID (string, optional)
  - `summary`: Update plaintext summary (string, optional)
  - `targetDate`: Adjust target completion date (string, optional)

</details>

<details>

<tool-name>Documents</tool-name>

- **get_document** - Retrieve the full contents and metadata of a Linear document by ID or slug
  - `id`: Document UUID or human-readable slug (e.g., `roadmap/2024`) (string, required)

- **list_documents** - Query documents workspace-wide with pagination and filtering
  - `after`: Cursor for the next page of results (string, optional)
  - `before`: Cursor for the previous page (string, optional)
  - `createdAt`: ISO timestamp/duration filter on creation time (string, optional)
  - `creatorId`: Restrict to documents authored by a specific user (string, optional)
  - `includeArchived`: Include archived documents when true (boolean, optional)
  - `initiativeId`: Filter to documents linked to a Linear initiative (string, optional)
  - `limit`: Page size (max 250) (number, optional)
  - `orderBy`: Sorting directive, e.g., `createdAt` (string, optional)
  - `projectId`: Restrict to documents tied to a project (string, optional)
  - `query`: Full-text search expression (string, optional)
  - `updatedAt`: ISO timestamp/duration filter on update time (string, optional)

- **search_documentation** - Run full-text searches against Linear's built-in documentation
  - `query`: Search string or keywords (string, required)
  - `page`: 1-based page selector for additional result sets (number, optional)

</details>

<details>

<tool-name>Cycles</tool-name>

- **list_cycles** - List Linear cycles belonging to a specific team
  - `teamId`: Team UUID owning the cycles (string, required)
  - `type`: Filter to `current`, `previous`, `next`, or `all` (default) (string, optional)

</details>
<!-- END AUTOMATED TOOLS -->

## Usage Notes

- All tools run through the MCP call interface. Provide arguments as JSON-compatible objects.
- String identifiers such as `issueId`, `teamId`, or `projectId` are Linear UUIDs unless noted otherwise. Named queries accept the same strings you would use in the Linear UI search box.
- Timestamp filters accept ISO-8601 values (`2024-03-01T00:00:00Z`) or ISO-8601 durations (e.g., `-P7D` for "last seven days"), matching Linear's GraphQL conventions.
- `limit` parameters default to Linear's API defaults (usually 50). Tune them to manage pagination breadth.
- List-style tools expose `after`/`before` identifiers for cursor-based pagination. Supply them exactly as returned in previous responses.
- Unless otherwise called out, tools return the same shapes as Linear's GraphQL API. Inspect responses in a dev session to discover all available fields.

## Implementation Tips

- Capture IDs from list responses and cache them when orchestrating multi-step flows; many tools expect those IDs directly.
- Respect Linear rate limits by batching calls and favoring targeted filters over broad `limit` values.
- When surfacing results to users, preserve pagination cursors so they can continue browsing with subsequent tool invocations.
- Response includes custom fields, assignee, labels, parent/child links, and SLAs when getting issue details.
- Combine with `list_comments` to collect conversational context when investigating issues.
- Supports any Markdown that Linear accepts (mentions, inline code, etc.) when creating comments.
- Combine multiple filters in `list_issues` to mimic advanced Linear search views.
- Returns team metadata including members, key, and workflow configuration.
- Returns rich fields such as title, content markdown, owner, and timestamps for documents.
- Use pagination cursors to iterate through large backlogs efficiently.
