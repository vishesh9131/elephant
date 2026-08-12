# Elephant continuity

When the user asks Elephant to resume previous work, call the
`elephant_recover` MCP tool for the current workspace if it is available.
Compare its Git state with the live worktree and continue without repeating
completed work. Never invent a previous session and never ask the user to run a
terminal command for Elephant.
