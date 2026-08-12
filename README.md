# Elephant

**Your coding session remembers you—even when the model forgets.**

Elephant is a plugin, not a command you babysit. Install it once in a supported
coding harness. It quietly records the session while the agent works, creates a
recovery capsule after every completed turn and before destructive context
boundaries, then restores that capsule when another harness opens the project.

## The experience

1. Work normally in Claude Code, Codex, Hermes, OpenCode, Pi, or another
   supported host.
2. The agent hits a quota, compacts context, crashes, or you simply switch tools.
3. Open the same project in another harness.
4. Elephant injects the previous objective and state automatically. Run
   **Elephant Resume** whenever you want the explicit handoff view.

The outgoing model never needs to answer after its quota dies. Native plugin
hooks have already written an append-only local journal. When a harness exposes
its transcript file, Elephant stores a compressed, redacted copy and makes it
available page-by-page through the recovery tool.

## Install

### Claude Code

```text
/plugin marketplace add vishesh9131/elephant
/plugin install elephant@elephant
```

### Codex

```text
codex plugin marketplace add vishesh9131/elephant
```

Then open `/plugins`, choose the **Elephant** marketplace, and install Elephant.

### GitHub Copilot CLI

```text
copilot plugin marketplace add vishesh9131/elephant
copilot plugin install elephant@elephant
```

### Gemini CLI

```text
gemini extensions install https://github.com/vishesh9131/elephant --ref=v0.2.0
```

### Pi

```text
pi install git:github.com/vishesh9131/elephant@v0.2.0
```

### Hermes Agent

```text
hermes plugins install vishesh9131/elephant --enable
```

The native packages contribute automatically:

- lifecycle hooks for capture and checkpointing;
- an Elephant MCP server with recovery, status, checkpoint, and transcript tools;
- the `/elephant:resume` skill;
- automatic prior-session context on session start.

Codex uses the same repository's `.codex-plugin` package. Hermes uses its native
`plugin.yaml` + Python `register(ctx)` interface. OpenCode and Pi load their
bundled JavaScript extensions. Copilot CLI, Devin, Grok, Gemini/Antigravity,
Qoder, OpenClaw, Cursor, Windsurf, Cline, Kiro, CodeWhale, Swival, Amp, Jules,
and other `AGENTS.md`-aware hosts use the platform-native package or portability
layer included in this repository.

See [platform support](docs/platform-native.md) for the exact capability tier of
each host. “Supported” does not falsely imply that every host exposes quota or
lifecycle telemetry.

## Privacy

Elephant is local-first. It writes redacted session events and recovery capsules
to `~/.elephant/` and does not include telemetry or a hosted service. Read the
[privacy notice](docs/privacy.md), [terms](docs/terms.md), or open a
[support issue](https://github.com/vishesh9131/elephant/issues).

## Three layers

1. **Native shells** — manifests, hooks, MCP, skills, and extensions shaped for
   each harness.
2. **Elephant kernel** — redaction, append-only SQLite journal, transcript
   archive, Git state, and portable recovery capsules.
3. **Continuation** — automatic startup injection plus **Elephant Resume** for an
   explicit handoff.

## Honest quota behavior

Most harnesses do not expose an exact subscription percentage. Elephant labels
signals as `exact`, `estimated`, or `unknown`; it never invents “98% used.” The
real safety mechanism is continuous capture plus a checkpoint after every
completed model turn. Native compaction, session-end, and hard quota-failure
events create additional checkpoints.

## Development

The Python runtime uses only the standard library and is bundled inside the
plugin. End users do not install or operate an `elephant` CLI. Maintainers can
run the portability contracts and every locally available live-host check with:

```bash
PYTHONPATH=src python scripts/conformance.py
```

The event compatibility contract is documented in
[docs/protocol.md](docs/protocol.md).
