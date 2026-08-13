import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const pluginRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bridge = path.join(pluginRoot, "hooks", "capture.py");
const commandBridge = path.join(pluginRoot, "hooks", "command.py");

function capture(kind, payload = {}) {
  const input = {
    ...payload,
    cwd: payload.cwd || process.cwd(),
    session_id: payload.session_id || "pi-session",
  };
  const result = spawnSync("python3", [bridge, "pi", kind], {
    input: JSON.stringify(input),
    encoding: "utf8",
    timeout: 10_000,
  });
  if (result.status !== 0 || !result.stdout.trim()) return null;
  try { return JSON.parse(result.stdout); } catch { return null; }
}

function elephantCommand(rawArgs = "help", ctx = {}) {
  const trimmed = String(rawArgs || "help").trim();
  const separator = trimmed.indexOf(" ");
  const action = separator === -1 ? trimmed : trimmed.slice(0, separator);
  const args = separator === -1 ? "" : trimmed.slice(separator + 1);
  const result = spawnSync("python3", [commandBridge], {
    input: JSON.stringify({
      action,
      arguments: args,
      cwd: ctx?.cwd || process.cwd(),
      harness: "pi",
      session_id: sessionId(ctx),
    }),
    encoding: "utf8",
    timeout: 10_000,
  });
  if (!result.stdout.trim()) return { ok: false, message: result.stderr || "Elephant command failed." };
  try { return JSON.parse(result.stdout); } catch { return { ok: false, message: result.stdout }; }
}

function sessionId(ctx) {
  return String(ctx?.sessionManager?.getSessionFile?.() || `${ctx?.cwd || process.cwd()}:ephemeral`);
}

function messageText(messages = []) {
  const message = [...messages].reverse().find((item) => item?.role === "assistant");
  const content = message?.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.filter((part) => part?.type === "text").map((part) => part.text).join("\n");
  return "";
}

export default function elephantExtension(pi) {
  let recoveredContext = null;
  let currentSession = "pi-session";

  pi.registerCommand("elephant", {
    description: "Save, recover, inspect, and manage Elephant memory",
    handler: async (args, ctx) => {
      const result = elephantCommand(args, ctx);
      if (result.ok && result.command === "resume") {
        pi.sendUserMessage(`${result.message}\n\nContinue the inherited objective now. Inspect the live worktree first and do not repeat completed work.`);
        return;
      }
      ctx?.ui?.notify?.(result.message, result.ok ? "info" : "error");
    },
  });

  pi.registerCommand("resume", {
    description: "Recover the previous coding-agent session",
    handler: async (_args, ctx) => {
      const result = elephantCommand("resume", ctx);
      if (result.ok) {
        pi.sendUserMessage(`${result.message}\n\nContinue the inherited objective now. Inspect the live worktree first and do not repeat completed work.`);
      } else {
        ctx?.ui?.notify?.(result.message, "error");
      }
    },
  });

  pi.on("session_start", async (event, ctx) => {
    currentSession = sessionId(ctx);
    const result = capture("session.started", { session_id: currentSession, cwd: ctx?.cwd });
    recoveredContext = result?.hookSpecificOutput?.additionalContext || null;
    ctx?.ui?.notify?.("Elephant is remembering this session.", "info");
  });

  pi.on("before_agent_start", async (event, ctx) => {
    currentSession = sessionId(ctx);
    capture("user.prompted", {
      session_id: currentSession,
      cwd: ctx?.cwd,
      payload: { prompt: String(event?.prompt || "") },
    });
    if (!recoveredContext) return;
    const context = recoveredContext;
    recoveredContext = null;
    const base = event?.systemPrompt ? `${event.systemPrompt}\n\n` : "";
    return { systemPrompt: `${base}${context}` };
  });

  pi.on("tool_call", async (event, ctx) => {
    capture("tool.started", {
      session_id: currentSession,
      cwd: ctx?.cwd,
      payload: { tool_name: event?.toolName, tool_input: event?.input },
    });
  });

  pi.on("tool_result", async (event, ctx) => {
    capture(event?.isError ? "tool.failed" : "tool.completed", {
      session_id: currentSession,
      cwd: ctx?.cwd,
      payload: { tool_name: event?.toolName, tool_output: event?.content ?? event?.result },
    });
  });

  pi.on("agent_end", async (event, ctx) => {
    capture("model.responded", {
      session_id: currentSession,
      cwd: ctx?.cwd,
      payload: { response: messageText(event?.messages) },
    });
  });

  pi.on("session_before_compact", async (_event, ctx) => {
    capture("context.compacting", { session_id: currentSession, cwd: ctx?.cwd });
  });

  pi.on("session_shutdown", async (_event, ctx) => {
    capture("session.ended", { session_id: currentSession, cwd: ctx?.cwd });
  });
}
