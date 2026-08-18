import { useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  Check,
  Clipboard,
  Code,
  Database,
  GithubLogo,
  LockKey,
  TerminalWindow,
} from "@phosphor-icons/react";

const githubUrl = "https://github.com/vishesh9131/elephant";

const installOptions = [
  {
    id: "claude",
    label: "Claude Code",
    command: "/plugin marketplace add vishesh9131/elephant\n/plugin install elephant@elephant",
    note: "Send these as two separate prompts inside Claude Code.",
  },
  {
    id: "codex",
    label: "Codex",
    command: "codex plugin marketplace add vishesh9131/elephant",
    note: "Then open /plugins, install Elephant, and review its local hooks. Exact can snapshot the active chat immediately.",
  },
  {
    id: "hermes",
    label: "Hermes",
    command: "hermes plugins install vishesh9131/elephant --enable",
    note: "Restart Hermes once so its native lifecycle hooks can load.",
  },
  {
    id: "gemini",
    label: "Gemini CLI",
    command: "gemini extensions install https://github.com/vishesh9131/elephant --ref=v0.4.5",
    note: "Loads Elephant's project context and command skill.",
  },
  {
    id: "pi",
    label: "Pi",
    command: "pi install git:github.com/vishesh9131/elephant@v0.4.5",
    note: "Requires Node.js 22.19 or newer.",
  },
];

const memoryItems = [
  ["Objective", "The goal and current constraints"],
  ["Decisions", "Choices made and why they won"],
  ["Changed files", "Live Git evidence, not a stale summary"],
  ["Failed attempts", "Dead ends the next model should avoid"],
  ["Next action", "The smallest safe step to continue"],
];

const elephantCommands = [
  ["memorize", "Save the freshest recoverable state for this session."],
  ["exact <label>", "Save the active chat under a durable label—even just after install."],
  ["pull <label>", "Load a labeled chat into the current harness."],
  ["resume [memory-id]", "Recover the latest memory, or one selected memory."],
  ["help", "Show the command card."],
  ["status", "Show protection, freshness, source, and transcript coverage."],
  ["history [limit]", "List recent memories for this project."],
  ["peek [memory-id]", "Preview what resume will inject without continuing."],
  ["note <text>", "Record an exact, high-priority user instruction."],
  ["doctor", "Check the database and installed capture capabilities."],
  ["usage", "Show database and transcript disk usage."],
  ["clean [age] [--keep N] [--yes]", "Preview or delete old sessions."],
  ["pin [memory-id]", "Protect a memory's session from cleanup."],
  ["unpin [memory-id]", "Allow a pinned session to be cleaned."],
  ["compact", "Repack the database and reclaim unused space."],
  ["forget <memory-id|session ID|project> --yes", "Delete local Elephant data."],
];

const commandScenarios = [
  {
    id: "exact",
    command: "exact <label>",
    eyebrow: "INSTALLED MID-SESSION",
    title: "Save the chat you are already inside.",
    setup: "You are 47 messages into a Codex task when you install Elephant. There is no earlier Elephant memory yet.",
    syntax: "@Elephant exact auth-refresh",
    steps: [
      ["1", "Choose a label", "Use 1–64 letters, numbers, dots, underscores, or hyphens."],
      ["2", "Elephant finds this chat", "It matches the active transcript to this exact project folder."],
      ["3", "A snapshot is pinned", "The newest 256 KiB is redacted, compressed, labeled, and protected."],
    ],
    result: [
      "🐘 Exact memory saved as `auth-refresh`.",
      "Source: codex",
      "Transcript coverage: snapshot",
      "Protected through quota failure and session cleanup.",
    ],
    tip: "The label is a name you invent—not a session ID.",
  },
  {
    id: "pull",
    command: "pull <label>",
    eyebrow: "SWITCHING HARNESSES",
    title: "Bring the labeled chat into Claude Code.",
    setup: "You saved `auth-refresh` in Codex and opened the same repository in Claude Code.",
    syntax: "/elephant:pull auth-refresh",
    steps: [
      ["1", "Open the same project", "Labels are scoped to the repository so unrelated chats never leak in."],
      ["2", "Pull the label", "Elephant feeds the redacted transcript and recovery capsule to Claude."],
      ["3", "Review the handoff", "Claude names the old harness and summarizes where the work stopped."],
    ],
    result: [
      "🐘 Elephant restored where you left off in codex.",
      "Label: auth-refresh",
      "Summary: Fix token rotation — implementation ready for tests",
      "Transcript coverage: snapshot",
    ],
    tip: "Pull restores context; you decide when the new harness starts working.",
  },
  {
    id: "resume",
    command: "resume [memory-id]",
    eyebrow: "QUOTA ENDED",
    title: "Continue from the freshest checkpoint.",
    setup: "Claude Code stopped unexpectedly, but Elephant had already journaled the work.",
    syntax: "@Elephant resume",
    steps: [
      ["1", "Ask for the latest", "Leave out the memory ID to recover the freshest memory for this project."],
      ["2", "Compare live files", "The new harness checks the capsule against the current Git worktree."],
      ["3", "Continue once", "Completed work is not repeated; the next safe action becomes the starting point."],
    ],
    result: [
      "🐘 Memory restored.",
      "From: claude-code / session-7f2c",
      "State: implementation complete",
      "Next: run the refresh-token integration test",
    ],
    tip: "Use a memory ID only when you want an older, specific checkpoint.",
  },
  {
    id: "clean",
    command: "clean [age] [--keep N]",
    eyebrow: "STORAGE HYGIENE",
    title: "Preview old memories before deleting anything.",
    setup: "Elephant has months of local sessions and you want to reclaim space safely.",
    syntax: "/elephant:clean 30d --keep 10",
    steps: [
      ["1", "Run a preview", "Without `--yes`, Elephant only reports what would be removed."],
      ["2", "Check protected work", "The newest sessions and every pinned session stay untouched."],
      ["3", "Confirm explicitly", "Repeat with `--yes` only after the preview looks correct."],
    ],
    result: [
      "🐘 Cleanup preview.",
      "Eligible sessions: 6",
      "Pinned sessions skipped: 2",
      "Add --yes to apply this exact cleanup plan.",
    ],
    tip: "Elephant never adds `--yes` for you.",
  },
  {
    id: "memorize",
    command: "memorize",
    eyebrow: "MANUAL CHECKPOINT",
    title: "Save the freshest recoverable state now.",
    setup: "You reached a stable milestone and want a checkpoint before attempting a risky refactor.",
    syntax: "/elephant:memorize",
    steps: [
      ["1", "Ask for a checkpoint", "No label or memory ID is required."],
      ["2", "Elephant gathers evidence", "The objective, recent events, changed files, failures, and transcript coverage are captured."],
      ["3", "Keep the memory ID", "Use the returned ID later when you need this specific point instead of the latest one."],
    ],
    result: [
      "🐘 Memorized.",
      "Source: claude-code · Events: 84",
      "Modified files: 3 · Transcript coverage: observed",
      "Memory ID: mem_7f2c",
    ],
    tip: "Automatic journaling continues; memorize simply forces a fresh checkpoint.",
  },
  {
    id: "help",
    command: "help",
    eyebrow: "COMMAND DISCOVERY",
    title: "See every command supported by this install.",
    setup: "You remember Elephant can recover work, but not the exact command or syntax for your harness.",
    syntax: "@Elephant help",
    steps: [
      ["1", "Invoke help", "Use the Elephant mention or native command prefix in your current harness."],
      ["2", "Scan the command card", "Each available command appears with its accepted arguments."],
      ["3", "Use the native prefix", "Claude, Codex, Hermes, and Pi display the syntax appropriate for that host."],
    ],
    result: [
      "Elephant commands",
      "memorize · exact <label> · pull <label> · resume",
      "status · history · peek · note · doctor · usage",
      "clean · pin · unpin · compact · forget",
    ],
    tip: "Help reads the version you installed, so it is the authoritative command list.",
  },
  {
    id: "status",
    command: "status",
    eyebrow: "PROTECTION CHECK",
    title: "Confirm that the current project is recoverable.",
    setup: "You are about to close the harness and want confidence that Elephant has a fresh memory.",
    syntax: "@Elephant status",
    steps: [
      ["1", "Check protection", "Protected means at least one recovery capsule exists for this project."],
      ["2", "Check freshness", "Fresh tells you whether the newest capsule reflects recent activity."],
      ["3", "Read coverage honestly", "Snapshot, observed, and unavailable are reported without pretending they mean complete."],
    ],
    result: [
      "🐘 Elephant status",
      "Protected: yes · Capsule fresh: yes",
      "Latest source: codex",
      "Transcript coverage: snapshot",
    ],
    tip: "Status reports evidence; it never invents an exact quota percentage.",
  },
  {
    id: "history",
    command: "history [limit]",
    eyebrow: "FIND AN OLDER MEMORY",
    title: "List recent checkpoints for this project.",
    setup: "The latest memory is not the point you want, so you need to identify an earlier checkpoint.",
    syntax: "$elephant history 5",
    steps: [
      ["1", "Choose a list length", "Leave the number out for the default ten memories."],
      ["2", "Compare timestamps", "Each row shows its source harness, objective, creation time, and memory ID."],
      ["3", "Copy the right ID", "Use it with peek, resume, pin, unpin, or forget."],
    ],
    result: [
      "🐘 Recent Elephant memories",
      "1. codex · 10:17 · Fix token rotation · mem_7f2c",
      "2. claude-code · 09:42 · Reproduce expiry bug · mem_61aa",
      "3. codex · 09:18 · Add regression test · mem_2d90",
    ],
    tip: "History is scoped to the current project, not every repository on your machine.",
  },
  {
    id: "peek",
    command: "peek [memory-id]",
    eyebrow: "PREVIEW BEFORE RESUME",
    title: "Inspect a memory without continuing it.",
    setup: "You found two possible checkpoints and want to verify one before injecting it into the active harness.",
    syntax: "/elephant:peek mem_61aa",
    steps: [
      ["1", "Select a memory", "Provide an ID, or omit it to preview the freshest capsule."],
      ["2", "Read the evidence", "Elephant shows the objective, state, files, and recent failures."],
      ["3", "Choose deliberately", "Resume only when the preview matches the work you intend to continue."],
    ],
    result: [
      "🐘 Memory preview",
      "Objective: Reproduce refresh-token expiry bug",
      "Modified files: auth/session.py, tests/test_rotation.py",
      "Failures: test expected 401 but received 200",
    ],
    tip: "Peek is read-only; it does not tell the harness to start working.",
  },
  {
    id: "note",
    command: "note <text>",
    eyebrow: "PRESERVE A DECISION",
    title: "Attach an instruction that must survive handoff.",
    setup: "You made a constraint explicit: the database schema must not change during this fix.",
    syntax: "/elephant:note \"Do not change the database schema\"",
    steps: [
      ["1", "State the instruction exactly", "Write the constraint in the words the next harness should see."],
      ["2", "Elephant checkpoints it", "The note is stored as high-priority evidence on the current memory."],
      ["3", "Recover it later", "Resume and pull surface the preserved instruction with the rest of the work."],
    ],
    result: [
      "🐘 Noted exactly: Do not change the database schema",
      "Memory ID: mem_83bc",
    ],
    tip: "Use note for decisions and constraints, not for replacing the conversation transcript.",
  },
  {
    id: "doctor",
    command: "doctor",
    eyebrow: "DIAGNOSE THE INSTALL",
    title: "Check whether Elephant can capture and recover.",
    setup: "A command did not behave as expected and you want a quick health report before troubleshooting further.",
    syntax: "@Elephant doctor",
    steps: [
      ["1", "Run the health check", "Elephant inspects its local database, data directory, and adapter readiness."],
      ["2", "Read each signal", "Healthy, writable, and recoverable memory are reported separately."],
      ["3", "Act on the failing line", "The report distinguishes storage trouble from a project that simply has no memory yet."],
    ],
    result: [
      "🐘 Elephant doctor",
      "Healthy: yes · Database: ok",
      "Writable: yes",
      "Recoverable memory: yes",
    ],
    tip: "Doctor checks Elephant itself; status checks the current project's protection.",
  },
  {
    id: "usage",
    command: "usage",
    eyebrow: "MEASURE LOCAL STORAGE",
    title: "See exactly how much disk space Elephant uses.",
    setup: "You have used Elephant across several projects and want to inspect storage before cleaning anything.",
    syntax: "@Elephant usage",
    steps: [
      ["1", "Measure the store", "Elephant separates database bytes from compressed transcript bytes."],
      ["2", "Compare scopes", "The report shows this project's sessions alongside totals for all projects."],
      ["3", "Choose maintenance", "Clean previews removable sessions; compact reclaims unused database pages afterward."],
    ],
    result: [
      "🐘 Elephant storage",
      "Total on disk: 18.6 MiB · Database: 4.2 MiB",
      "Transcripts: 14.4 MiB",
      "This project: 12 sessions, 31 memories, 2 pinned",
    ],
    tip: "Usage never deletes data—it only measures it.",
  },
  {
    id: "pin",
    command: "pin [memory-id]",
    eyebrow: "PROTECT IMPORTANT WORK",
    title: "Exclude a session from automatic cleanup.",
    setup: "A successful migration session is valuable long-term, even though it will eventually become old.",
    syntax: "/elephant:pin mem_7f2c",
    steps: [
      ["1", "Choose the memory", "Provide its ID, or omit it to select the latest capsule."],
      ["2", "Elephant resolves the session", "Protection applies to the complete source session, not just one capsule."],
      ["3", "Clean safely", "Future cleanup previews and deletions skip that pinned session."],
    ],
    result: [
      "🐘 Pinned session session-7f2c.",
      "Cleanup will leave it alone.",
    ],
    tip: "An exact label is pinned automatically; pin is useful for ordinary memories.",
  },
  {
    id: "unpin",
    command: "unpin [memory-id]",
    eyebrow: "REMOVE PROTECTION",
    title: "Allow an old session to be cleaned again.",
    setup: "The migration is finished and backed up, so its old Elephant session no longer needs permanent protection.",
    syntax: "/elephant:unpin mem_7f2c",
    steps: [
      ["1", "Select the protected memory", "Elephant resolves its source session from the memory ID."],
      ["2", "Remove the pin", "No transcript or capsule is deleted by this command."],
      ["3", "Preview cleanup later", "The session becomes eligible only when it also meets the age and retention rules."],
    ],
    result: [
      "🐘 Unpinned: session session-7f2c.",
    ],
    tip: "Unpin changes cleanup eligibility; it does not erase the memory.",
  },
  {
    id: "compact",
    command: "compact",
    eyebrow: "RECLAIM DATABASE SPACE",
    title: "Repack SQLite after old memories are removed.",
    setup: "You completed a confirmed cleanup and want the database file to release its unused pages.",
    syntax: "@Elephant compact",
    steps: [
      ["1", "Clean first if needed", "Compact does not decide which sessions should be deleted."],
      ["2", "Repack the database", "SQLite rewrites its internal pages without changing the remaining memories."],
      ["3", "Review the savings", "Elephant reports the size before, after, and reclaimed."],
    ],
    result: [
      "🐘 Database compacted.",
      "Before: 9.8 MiB; after: 4.2 MiB; reclaimed: 5.6 MiB.",
    ],
    tip: "Compact is safe for retained memories, but it only helps after unused pages exist.",
  },
  {
    id: "forget",
    command: "forget <target> --yes",
    eyebrow: "PERMANENT DELETION",
    title: "Delete one memory, one session, or this project.",
    setup: "A test session contains context you intentionally no longer want stored locally.",
    syntax: "/elephant:forget mem_test91",
    steps: [
      ["1", "Start without confirmation", "Elephant warns that deletion is permanent and changes nothing."],
      ["2", "Verify the target", "Choose a memory ID, a named session, or `project` for the current repository."],
      ["3", "Repeat with --yes", "Only your explicit confirmation allows the deletion to run."],
    ],
    result: [
      "Elephant will permanently delete local memory.",
      "Repeat with --yes to confirm.",
    ],
    tip: "Always read the target twice; forgotten local memory cannot be recovered by Elephant.",
  },
];

function Brand({ compact = false }) {
  return (
    <a className={`brand ${compact ? "brand--compact" : ""}`} href="#top" aria-label="Elephant home">
      <span className="brand__mark" aria-hidden="true">
        <img src="./elephant.png" alt="" />
      </span>
      <span>Elephant</span>
    </a>
  );
}

function AppButton({ href, children, secondary = false, className = "" }) {
  return (
    <a className={`button ${secondary ? "button--secondary" : ""} ${className}`} href={href}>
      {children}
    </a>
  );
}

export function App() {
  const [activeInstall, setActiveInstall] = useState(installOptions[0]);
  const [activeScenario, setActiveScenario] = useState(commandScenarios[0]);
  const [copied, setCopied] = useState(false);

  async function copyInstall() {
    try {
      await navigator.clipboard.writeText(activeInstall.command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      const textArea = document.createElement("textarea");
      textArea.value = activeInstall.command;
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      textArea.remove();
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    }
  }

  return (
    <main id="top">
      <header className="site-header page-shell">
        <Brand />
        <nav className="site-nav" aria-label="Primary navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#command-lab">Try commands</a>
          <a href="#harnesses">Harnesses</a>
          <a href="#privacy">Privacy</a>
          <a href="#install">Install</a>
        </nav>
        <a className="github-chip" href={githubUrl} target="_blank" rel="noreferrer">
          <GithubLogo size={17} weight="fill" aria-hidden="true" />
          <span>GitHub</span>
        </a>
      </header>

      <section className="hero page-shell" aria-labelledby="hero-heading">
        <div className="hero__copy">
          <div className="eyebrow"><span className="signal signal--orange" /> OPEN-SOURCE CONTINUITY PLUGIN</div>
          <h1 id="hero-heading">Quota ends.<br />Work doesn’t.</h1>
          <p>
            Elephant remembers your coding session before the model disappears,
            then carries the work into Codex, Hermes, or whichever harness comes next.
          </p>
          <div className="hero__actions">
            <AppButton href="#install">Install Elephant <ArrowDown size={16} weight="bold" /></AppButton>
            <AppButton href={githubUrl} secondary>
              <GithubLogo size={17} weight="fill" /> View on GitHub
            </AppButton>
          </div>
          <div className="hero__meta" aria-label="Project metadata">
            <span>V0.4.5</span><span>MIT LICENSE</span><span>LOCAL-FIRST</span>
          </div>
        </div>
        <div className="hero__art" aria-label="Elephant illustration">
          <img src="./elephant.png" alt="A hand-drawn elephant with its trunk raised" />
        </div>
      </section>

      <section className="pulse-panel page-shell" aria-labelledby="pulse-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">THE MOMENT ELEPHANT EARNS ITS NAME</p>
            <h2 id="pulse-title">One session. Two harnesses. Zero context lost.</h2>
          </div>
          <div className="pulse-legend" aria-label="Chart legend">
            <span><i className="legend-line legend-line--orange" />Claude Code</span>
            <span><i className="legend-line legend-line--violet" />Codex</span>
          </div>
        </div>

        <div className="pulse-visual">
          <img className="pulse-image" src="./quota-pulse.png" alt="An orange quota signal becoming a violet continuation signal" />
          <div className="pulse-label pulse-label--source">
            <strong>Claude Code</strong>
            <span>Building…</span>
            <b>LIMIT</b>
            <small>quota exhausted</small>
          </div>
          <div className="checkpoint">
            <span className="checkpoint__label">Elephant checkpoint</span>
            <span className="checkpoint__mark"><img src="./elephant.png" alt="" /></span>
            <small>memory is already safe</small>
          </div>
          <div className="pulse-label pulse-label--target">
            <strong>Codex</strong>
            <span>Continuing…</span>
            <b>12%</b>
            <small>fresh quota, same work</small>
          </div>
        </div>

        <div className="pulse-timeline" aria-hidden="true">
          <span><i />Session start<small>09:41</small></span>
          <span><i />Checkpoint<small>10:17</small></span>
          <span><i />Resumed<small>10:19</small></span>
        </div>
      </section>

      <section className="harness-strip page-shell" id="harnesses" aria-label="Supported coding harnesses">
        <p>Works with the coding harnesses you already use.</p>
        <div>
          <span>Claude Code</span><i />
          <span>Codex</span><i />
          <span>Hermes</span><i />
          <span>Gemini CLI</span><i />
          <span>OpenCode</span><i />
          <span>Pi</span><i />
          <span>Copilot</span><i />
          <span>and more</span>
        </div>
      </section>

      <section className="story page-shell" id="how-it-works">
        <div className="story__intro">
          <p className="section-kicker">HOW IT WORKS</p>
          <h2>Capture once.<br />Continue anywhere.</h2>
          <p>Elephant never waits for a mythical 99% quota callback. It journals continuously, so a sudden limit is boring—not catastrophic.</p>
        </div>
        <ol className="steps">
          <li><span>1</span><div><h3>Capture</h3><p>Every completed turn, edit, tool result and failure is recorded by a native adapter.</p></div></li>
          <li><span>2</span><div><h3>Checkpoint</h3><p>The kernel builds a redacted recovery capsule and reconciles it with live Git state.</p></div></li>
          <li><span>3</span><div><h3>Continue</h3><p>Open the same repo elsewhere. Elephant injects the last objective, evidence and next action.</p></div></li>
        </ol>
      </section>

      <section className="memory-panel page-shell" aria-labelledby="memory-title">
        <div className="memory-list">
          <p className="section-kicker">PORTABLE · COMPRESSED · YOURS</p>
          <h2 id="memory-title">What gets<br />carried over.</h2>
          <ul>
            {memoryItems.map(([title, copy]) => (
              <li key={title}><Check size={17} weight="bold" /><span><strong>{title}</strong><small>{copy}</small></span></li>
            ))}
          </ul>
        </div>
        <div className="capsule-window" aria-label="Example Elephant recovery capsule">
          <div className="capsule-window__bar"><span>recovery-capsule.json</span><span>portable · versioned · yours</span></div>
          <pre>{`{
  "source": "claude-code",
  "target": "codex",
  "objective": "Fix refresh-token rotation",
  "state": "Implementation complete",
  "changed_files": [
    "auth/session.py",
    "tests/test_rotation.py"
  ],
  "failed_attempts": 1,
  "next_action": "Run the integration test"
}`}</pre>
        </div>
      </section>

      <section className="command-lab page-shell" id="command-lab" aria-labelledby="command-lab-title">
        <div className="command-lab__heading">
          <div>
            <p className="section-kicker">LEARN BY DOING</p>
            <h2 id="command-lab-title">Pick a moment.<br />See what Elephant does.</h2>
          </div>
          <p>Every walkthrough starts with a real situation, shows exactly what to type, and explains the response line by line.</p>
        </div>

        <div className="scenario-picker" role="tablist" aria-label="Choose an Elephant command scenario">
          {commandScenarios.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              role="tab"
              aria-selected={activeScenario.id === scenario.id}
              className={activeScenario.id === scenario.id ? "is-active" : ""}
              onClick={() => setActiveScenario(scenario)}
            >
              <span>{scenario.eyebrow}</span>
              <code>{scenario.command}</code>
            </button>
          ))}
        </div>

        <div className="scenario-stage">
          <div className="scenario-story">
            <p className="scenario-story__eyebrow"><span className="signal signal--orange" /> {activeScenario.eyebrow}</p>
            <h3>{activeScenario.title}</h3>
            <p className="scenario-story__setup">{activeScenario.setup}</p>
            <ol className="scenario-steps">
              {activeScenario.steps.map(([number, title, copy]) => (
                <li key={number}>
                  <span>{number}</span>
                  <div><strong>{title}</strong><p>{copy}</p></div>
                </li>
              ))}
            </ol>
          </div>

          <div className="scenario-terminal" aria-live="polite">
            <div className="scenario-terminal__bar">
              <span><i /><i /><i /></span>
              <small>interactive example · no command is actually run</small>
            </div>
            <div className="scenario-terminal__body">
              <p className="terminal-context">YOU TYPE</p>
              <pre className="terminal-command"><span>›</span> {activeScenario.syntax}</pre>
              <p className="terminal-context">ELEPHANT REPLIES</p>
              <pre className="terminal-result">{activeScenario.result.join("\n")}</pre>
              <div className="terminal-tip"><strong>Remember</strong><span>{activeScenario.tip}</span></div>
            </div>
          </div>
        </div>
        <p className="command-lab__demo-note">All 16 commands include a real situation, exact syntax, expected response, and the safety detail that matters.</p>
      </section>

      <section className="commands page-shell" id="commands" aria-labelledby="commands-title">
        <div className="commands__intro">
          <p className="section-kicker">THE WHOLE TOOLBOX</p>
          <h2 id="commands-title">Every command.<br />Nothing hidden.</h2>
          <p>Use the same action in any supported harness. Only the prefix changes.</p>
          <div className="command-prefixes" aria-label="Command syntax by harness">
            <code>/elephant:command</code>
            <code>$elephant command</code>
            <code>@Elephant command</code>
          </div>
        </div>
        <dl className="command-list">
          {elephantCommands.map(([command, description]) => (
            <div key={command} className="command-list__item">
              <dt><code>{command}</code></dt>
              <dd>{description}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="privacy page-shell" id="privacy" aria-labelledby="privacy-title">
        <div>
          <p className="section-kicker">LOCAL-FIRST BY DESIGN</p>
          <h2 id="privacy-title">Private by design.<br />Local by default.</h2>
        </div>
        <div className="privacy-facts">
          <article><LockKey size={27} weight="thin" /><h3>100% local</h3><p>Everything is stored in ~/.elephant on your machine.</p></article>
          <article><Database size={27} weight="thin" /><h3>You own it</h3><p>Inspect, export, back up, move, or delete it whenever you want.</p></article>
          <article><Code size={27} weight="thin" /><h3>Open source</h3><p>Auditable adapters and a documented, versioned protocol.</p></article>
        </div>
      </section>

      <section className="install page-shell" id="install" aria-labelledby="install-title">
        <div className="install__heading">
          <p className="section-kicker">GET STARTED</p>
          <h2 id="install-title">Install once.<br />Then forget about it.</h2>
          <p>Python 3.10+ powers the local kernel. Elephant takes it from there.</p>
        </div>
        <div className="install-console">
          <div className="install-tabs" role="tablist" aria-label="Choose a harness">
            {installOptions.map((option) => (
              <button
                key={option.id}
                type="button"
                role="tab"
                aria-selected={activeInstall.id === option.id}
                className={activeInstall.id === option.id ? "is-active" : ""}
                onClick={() => { setActiveInstall(option); setCopied(false); }}
              >{option.label}</button>
            ))}
          </div>
          <div className="command-box">
            <TerminalWindow size={20} weight="thin" aria-hidden="true" />
            <pre>{activeInstall.command}</pre>
            <button className="copy-button" type="button" onClick={copyInstall} aria-live="polite">
              {copied ? <Check size={16} weight="bold" /> : <Clipboard size={16} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <p className="install-note">{activeInstall.note}</p>
        </div>
      </section>

      <section className="closing page-shell">
        <div>
          <p className="section-kicker">KEEP THE THREAD</p>
          <h2>Different harness.<br />Same momentum.</h2>
        </div>
        <div>
          <p>Quotas are temporary. The work is not. Elephant keeps the full thread moving when one model has to hand it off to another.</p>
          <AppButton href={githubUrl}>View on GitHub <ArrowRight size={16} weight="bold" /></AppButton>
        </div>
      </section>

      <footer className="site-footer page-shell">
        <Brand compact />
        <p>MIT License <span>·</span> No telemetry <span>·</span> Made for long coding sessions</p>
        <a href={githubUrl} target="_blank" rel="noreferrer"><GithubLogo size={17} weight="fill" /> github.com/vishesh9131/elephant</a>
      </footer>
    </main>
  );
}
