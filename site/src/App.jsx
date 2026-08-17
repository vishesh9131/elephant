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
    note: "Then open /plugins and install Elephant from the marketplace.",
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
    command: "gemini extensions install https://github.com/vishesh9131/elephant --ref=v0.4.2",
    note: "Loads Elephant's project context and command skill.",
  },
  {
    id: "pi",
    label: "Pi",
    command: "pi install git:github.com/vishesh9131/elephant@v0.4.2",
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
  ["exact <label>", "Save the full redacted chat under a durable label."],
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
          <a href="#commands">Commands</a>
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
            <span>V0.4.2</span><span>MIT LICENSE</span><span>LOCAL-FIRST</span>
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
