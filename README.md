<p align="center">
  <img src="assets/elephant.png" width="520" alt="Elephant, the coding agent that never forgets">
</p>

<h1 align="center">Elephant</h1>

<p align="center">
  <em>The model forgets. The elephant doesn't.</em>
</p>

<p align="center">
  <a href="https://github.com/vishesh9131/elephant/stargazers"><img src="https://img.shields.io/github/stars/vishesh9131/elephant?style=flat-square&color=111111&label=stars" alt="GitHub stars"></a>
  <a href="https://github.com/vishesh9131/elephant/releases/latest"><img src="https://img.shields.io/github/v/release/vishesh9131/elephant?style=flat-square&color=111111&label=release" alt="Latest release"></a>
  <a href="https://github.com/vishesh9131/elephant/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/vishesh9131/elephant/ci.yml?branch=main&style=flat-square&color=111111&label=build" alt="Build status"></a>
  <img src="https://img.shields.io/badge/works%20with-20%2B%20agents-111111?style=flat-square" alt="Works with 20+ agents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-111111?style=flat-square" alt="MIT license"></a>
</p>

<p align="center">
  <strong>Claude hits quota. Codex keeps going.</strong><br>
  <sub>Automatic, local-first session continuity across AI coding harnesses.</sub>
</p>

<p align="center">
  <a href="https://vishesh9131.github.io/elephant/"><strong>Visit the Elephant website →</strong></a>
</p>

---

You know the ritual.

Claude has the entire problem in its head. It has read the repo, found the bug,
changed six files, failed one test, and finally understood why.

Then:

```text
You've hit your usage limit.
```

You open another agent. It cheerfully asks what you are working on.

Now **you** are the context window.

Elephant removes that part.

## Without / with Elephant

Without Elephant:

```text
Claude:  You've hit your usage limit.
Codex:   What would you like to work on?
You:     Okay, so first you need to understand this 47-message conversation...
```

With Elephant:

```text
Claude:    You've hit your usage limit.

           [open the same repo in Codex]

Elephant:  Recovered the previous Claude Code session.
           Objective: fix refresh-token rotation.
           State: implementation complete; one integration test still fails.
           Changed: auth/session.py, tests/test_rotation.py

Codex:     I found the failing test. Continuing from there.
```

The dead model does not need to summarize anything. Elephant was already
recording while it was alive.

## How it works

Elephant is a plugin, not another command you babysit.

```text
Every prompt, response, tool call, failure, and file change
                         │
                         ▼
             append-only local journal
                         │
              completed turn / compaction /
              interruption / quota failure
                         │
                         ▼
                recovery capsule
                         │
             open the repo in another agent
                         │
                         ▼
             objective + state + Git evidence
```

It remembers:

- the current objective and last completed state;
- the last prompt and model response;
- modified files and live Git state;
- recent tool/model failures;
- the latest 20 session events;
- a redacted transcript reference when the host exposes one.

Every capture-capable native shell writes the same versioned event format. They
share `~/.elephant/elephant.db`, so Claude's memory is visible to Codex, Hermes,
Pi, OpenCode, Copilot, and every other Elephant adapter.

## Three layers

```text
┌──────────────────────────────────────────────────────────────┐
│ Native shells                                               │
│ Claude · Codex · Hermes · OpenCode · Pi · Copilot · Gemini │
├──────────────────────────────────────────────────────────────┤
│ Elephant kernel                                             │
│ redact · journal · checkpoint · inspect Git · build capsule │
├──────────────────────────────────────────────────────────────┤
│ Continuation                                                │
│ automatic startup injection · Elephant Resume              │
└──────────────────────────────────────────────────────────────┘
```

One memory format. Thin native adapters. No universal fake CLI pretending every
agent exposes the same API.

## Install

Install once in each harness you want to hand work between. Python 3.11+ must
be available as `python3` for the local kernel and lifecycle hooks.

### Claude Code

Send these as two separate prompts inside Claude Code:

```text
/plugin marketplace add vishesh9131/elephant
```

```text
/plugin install elephant@elephant
```

Elephant adds lifecycle capture, the local MCP recovery tools, automatic
startup recovery, and `/elephant:resume`.

### Codex

```bash
codex plugin marketplace add vishesh9131/elephant
```

Open `/plugins`, choose the **Elephant** marketplace, and install Elephant.
Review and trust its local lifecycle hooks when Codex asks, then start a new
session.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add vishesh9131/elephant
copilot plugin install elephant@elephant
```

The same commands work interactively with a `/` prefix. Elephant captures all
nine Copilot CLI plugin lifecycle events and provides the `resume` skill.

### Gemini CLI

```bash
gemini extensions install https://github.com/vishesh9131/elephant --ref=v0.2.0
```

Gemini loads Elephant's project context and `resume` skill. The public repo is
tagged for Gemini's extension gallery crawler.

### Pi

```bash
pi install git:github.com/vishesh9131/elephant@v0.2.0
```

Requires Node.js 22.19+. Pi loads the native JavaScript extension, `/resume`,
and `skill:resume`.

### Hermes Agent

```bash
hermes plugins install vishesh9131/elephant --enable
```

Restart Hermes after installing. Elephant registers native lifecycle hooks, the
`elephant_recover` tool, the `resume` skill, and `/elephant`.

Why `/elephant` instead of `/resume`? Hermes already owns `/resume`. The
elephant remembers names too.

### OpenCode

From a checkout, point your `opencode.json` at Elephant's JavaScript plugin:

```json
{
  "plugin": ["/absolute/path/to/elephant/.opencode/plugins/elephant.mjs"]
}
```

The plugin captures prompts, responses, tool calls, compaction, idle, errors,
and session end. The npm package is prepared but not published yet.

## The rest of the herd

Not every harness exposes lifecycle hooks. Elephant says exactly what each one
can do instead of painting “98% quota used” on a guess.

| Harness | Support | Surface |
|---|---|---|
| Claude Code, Codex, Hermes, OpenCode, Pi | Native continuity | Hooks/extensions capture automatically and inject recovery |
| GitHub Copilot CLI | Native recovery | Marketplace plugin, nine hooks, MCP, and skill |
| Gemini / Antigravity, Qoder, Devin, Grok Build | Native recovery | Extension/plugin manifest plus recovery skill |
| OpenClaw, Swival | Native recovery | Packaged skill collection |
| Cursor | Portable recovery | [`.cursor/rules`](.cursor/rules) + Elephant MCP |
| Windsurf | Portable recovery | [`.windsurf/rules`](.windsurf/rules) + Elephant MCP |
| Cline | Portable recovery | [`.clinerules`](.clinerules) + Elephant MCP |
| Kiro | Portable recovery | [`.kiro/steering`](.kiro/steering) + Elephant MCP |
| CodeWhale, Amp, Jules, compatible hosts | Portable recovery | [`AGENTS.md`](AGENTS.md) |

See the [full platform matrix](docs/platform-native.md) for capability details
and current conformance status.

## What happens near quota?

Mostly, nothing special—and that is the point.

Most coding harnesses do **not** expose an exact subscription percentage.
Elephant never invents one. Quota signals are stored as `exact`, `estimated`,
or `unknown`.

Instead of gambling everything on a mythical “99% used” callback, Elephant:

1. journals continuously;
2. checkpoints after every completed model turn;
3. checkpoints again before compaction and at session end;
4. records native interruption and quota-failure events when the host provides
   them.

If the quota dies without warning, the memory is already on disk.

## Local means local

Elephant has no account, cloud, analytics, telemetry, ad network, or mysterious
“improve the product” upload.

```text
~/.elephant/
├── elephant.db       # append-only events + recovery capsules
└── transcripts/      # optional compressed transcript copies
```

Sensitive keys and common credential formats are redacted before persistence.
Redaction is defense-in-depth, not magic: protect the machine and do not share
the database casually.

Set `ELEPHANT_DATA_DIR` to move the store. Read the [privacy notice](docs/privacy.md)
and [security policy](SECURITY.md).

## Resume explicitly

Automatic recovery happens when a native host starts a new session in a project
that has an Elephant capsule from another session.

When you want to ask directly:

| Host | Command / skill |
|---|---|
| Claude Code | `/elephant:resume` |
| Codex | `$resume` or ask “resume my previous session” |
| Pi | `/resume` or `skill:resume` |
| Hermes | `/elephant` or `plugin:resume` |
| Other skill-capable hosts | `resume` |

Recovery compares the capsule's Git metadata with the live worktree. The files
on disk win. Elephant remembers the past; it does not overwrite the present.

## Tested, not merely listed

The conformance suite proves the same flow across adapters:

```text
capture → checkpoint → switch harness → recover → verify Git state
```

The current release includes:

- real plugin-load checks for Claude Code, OpenCode, Pi, Copilot, and Hermes
  when their binaries are installed, plus remote marketplace discovery in
  Codex;
- live model-turn verification for Copilot CLI and Hermes;
- cross-harness Claude → OpenCode → Pi → portable recovery contracts;
- 11 Python/JavaScript tests for journaling, redaction, MCP, manifests, and
  continuation.

Run everything available on your machine:

```bash
PYTHONPATH=src python3 scripts/conformance.py
python3 -m unittest discover -s tests -v
```

The event protocol is documented in [docs/protocol.md](docs/protocol.md).

## FAQ

**Does Elephant ask the dying model to summarize the session?**

No. A model at quota is about as useful as a fire alarm after the building is
gone. Elephant records continuously and builds the handoff itself.

**Does it copy my session to another company's server?**

No. Harnesses still send prompts to their own configured model providers, but
Elephant's journal stays on your machine.

**Can it really know when I am at 98%?**

Only if the harness exposes that number. Most do not. Elephant would rather be
useful at an honest `unknown` than impressive at a fictional `98%`.

**What if the repo changed after the handoff?**

The live worktree is authoritative. Elephant shows the old capsule as evidence,
compares Git state, and continues from what actually exists.

**Why “Elephant”?**

Because “Cross-Harness Context Persistence Orchestration Kernel” remembered the
architecture and forgot the joke.

## Development

The core is dependency-free Python. Host-specific code stays thin: manifests,
hook maps, skills, and small JavaScript/Python adapters around the shared event
protocol.

To add another harness:

1. declare what its API genuinely exposes;
2. map native events into the Elephant protocol;
3. package the host's native install surface;
4. prove capture → checkpoint → recovery in conformance tests.

Contributions are welcome. Fake support badges are not.

## License

[MIT](LICENSE). Elephants travel better when the gate is open.
