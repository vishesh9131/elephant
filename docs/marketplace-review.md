# Marketplace review cases

## Positive cases

1. **Claude to Codex:** capture a completed Claude Code turn, open the same Git
   worktree in Codex, and recover the objective, state, and next action.
2. **Codex to Claude:** capture a Codex tool failure and completed follow-up,
   then recover both in Claude Code without repeating the successful work.
3. **Compaction:** trigger a supported host's pre-compaction event and verify a
   recovery capsule exists before compaction finishes.
4. **Explicit recovery:** ask “resume my previous coding session” and verify the
   `resume` skill uses the latest capsule for the current project.
5. **Git drift:** change the worktree after a capsule is written and verify the
   recovery flow treats the live worktree as authoritative.

## Negative cases

1. **No capsule:** ask to resume in an unseen project; Elephant must say no
   recorded session exists and must not invent one.
2. **Secret disclosure:** include a synthetic API token in a captured payload;
   recovery must return a redacted value.
3. **False quota precision:** provide no exact host quota signal; Elephant must
   label quota knowledge unknown rather than claim “98% used.”

All cases use local synthetic repositories and require no private account data.
