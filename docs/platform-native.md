# Platform-native architecture

Elephant follows Ponytail's distribution pattern: one repository, one shared
core, and thin native packages rather than a universal user-facing CLI.

## Capability tiers

| Tier | Meaning |
|---|---|
| Native continuity | The host exposes lifecycle hooks or an extension API. Elephant captures automatically and can inject recovery context. |
| Native recovery | The host can install Elephant's skill/tool package and recover a capsule, but exposes fewer reliable capture events. |
| Portable recovery | The host reads a rule/context file. It can consume Elephant memory when its MCP tool is configured, but cannot independently promise quota-aware capture. |

## Harness matrix

| Harness | Package surface | Tier | Current behavior |
|---|---|---|---|
| Claude Code | `.claude-plugin`, hooks, MCP, skill, marketplace | Native continuity | Captures prompts/tools/responses, archives transcripts, checkpoints stops/compaction/failure/end, injects recovery on start |
| Codex | `.codex-plugin`, hooks, MCP, skill, marketplace | Native continuity | Captures lifecycle/tool events, checkpoints completed turns/compaction/end, injects recovery on start |
| Hermes Agent | `plugin.yaml`, `register(ctx)` hooks/tool/command/skill | Native continuity | Live model turn on Hermes 0.20.0 verified start, prompt, request, response, and end events; recovery command is `/elephant` |
| OpenCode | JavaScript plugin + skills | Native continuity | Live-loaded on OpenCode 1.4.6; contract covers startup injection, prompts, tools, compaction, failures, idle, and end |
| Pi | JavaScript extension + skills | Native continuity | Live-loaded on Pi 0.84.1; Pi's RPC runtime reports the `resume` command and `skill:resume` from Elephant |
| GitHub Copilot CLI | marketplace plugin, hooks, skills | Native recovery | Live model turn on Copilot CLI 1.0.79 verified start, prompt, response, and end hooks; all nine documented hooks are contract-tested |
| Qoder | plugin manifest, skills, rules, hook template | Native recovery | Skills/rules plus capture when native hooks are enabled |
| Devin CLI | plugin manifest + skills | Native recovery | Provides the recovery skill; host telemetry adapter is the next conformance target |
| Grok Build | marketplace + skills | Native recovery | Provides the recovery skill; no fake lifecycle injection where Grok cannot support it |
| Gemini / Antigravity | extension + `AGENTS.md` context + skills | Native recovery | Loads the recovery behavior; native event capture awaits a stable compatible hook surface |
| OpenClaw / Swival | packaged skill collection | Native recovery | Can recover sessions captured in another harness through the bundled skill fallback |
| Cursor | `.cursor/rules` | Portable recovery | Uses Elephant MCP when configured; rule-only mode cannot capture quotas |
| Windsurf | `.windsurf/rules` | Portable recovery | Same limitation as Cursor |
| Cline | `.clinerules` | Portable recovery | Same limitation as Cursor |
| Kiro | `.kiro/steering` | Portable recovery | Same limitation as Cursor |
| CodeWhale, Amp, Jules and other compatible hosts | `AGENTS.md` | Portable recovery | Instruction-level discovery; no claim of native lifecycle telemetry |

## Adapter rule

Every native shell emits the same versioned Elephant events. Harness-specific
transcripts and hook payloads are inputs, never the interchange format. The
portable recovery capsule is the compatibility boundary.

All shells share `~/.elephant/elephant.db` and `~/.elephant/transcripts/` by
default. A harness-private plugin cache must never become the memory location,
or another harness would be unable to see it. `ELEPHANT_DATA_DIR` can override
the shared location for tests or managed deployments.

Adding a new harness therefore requires only:

1. a capability manifest stating what the host truly exposes;
2. a thin event adapter or extension;
3. a native install package;
4. a conformance test proving capture → checkpoint → recovery.

Run `PYTHONPATH=src python scripts/conformance.py`. Hosts with a non-interactive
validator receive a real plugin-load check; the others run the same callbacks
through a fake host API plus their native manifest/command schema. The report
says `SKIP` or `CONTRACT` instead of pretending an unavailable binary was
live-tested.
