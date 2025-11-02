# Agent Instructions

# Working with Claude Plugins
- Every plugin MUST be defined in `.claude-plugin/marketplace.json` first.
- Always bump the versions in plugin.json files when making changes to the plugin files (except for README.md).
  - Always bump the patch version regardless of the type of change.
  - Only update the `.claude-plugin/plugin.json` file of the plugin you are modifying.