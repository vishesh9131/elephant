// Native OpenCode adapter for Elephant. The Python process is an internal
// plugin runtime; the user never operates it directly.

import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const pluginRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const bridge = path.join(pluginRoot, 'hooks', 'capture.py');

function capture(kind, payload = {}, cwd = process.cwd()) {
  const input = {
    ...payload,
    cwd: payload.cwd || cwd,
    session_id: payload.session_id || payload.sessionID || 'opencode-session',
  };
  const result = spawnSync('python3', [bridge, 'opencode', kind], {
    input: JSON.stringify(input),
    encoding: 'utf8',
    timeout: 10_000,
  });
  if (result.status !== 0 || !result.stdout.trim()) return null;
  try { return JSON.parse(result.stdout); } catch { return null; }
}

export default async ({ directory } = {}) => {
  const cwd = directory || process.cwd();
  const recovery = new Map();
  const rememberStart = (sessionID, payload = {}) => {
    if (recovery.has(sessionID)) return;
    const result = capture('session.started', { ...payload, session_id: sessionID }, cwd);
    recovery.set(sessionID, result?.hookSpecificOutput?.additionalContext || null);
  };
  return {
    config: async (config) => {
      config.skills ||= {};
      config.skills.paths ||= [];
      const skills = path.join(pluginRoot, 'skills');
      if (!config.skills.paths.includes(skills)) config.skills.paths.push(skills);
    },

    'experimental.chat.system.transform': async (input, output) => {
      const sessionID = String(input?.sessionID || input?.session_id || 'opencode-session');
      rememberStart(sessionID);
      const context = recovery.get(sessionID);
      recovery.set(sessionID, null);
      if (!context) return;
      if (output.system.length) output.system[output.system.length - 1] += `\n\n${context}`;
      else output.system.push(context);
    },

    'chat.message': async (input, output) => {
      const prompt = (output?.parts || [])
        .filter((part) => part?.type === 'text')
        .map((part) => part.text)
        .join('\n');
      capture('user.prompted', {
        session_id: input?.sessionID,
        payload: { prompt },
      }, cwd);
    },

    'tool.execute.before': async (input, output) => {
      capture('tool.started', {
        session_id: input?.sessionID,
        payload: { tool_name: input?.tool, tool_input: output?.args },
      }, cwd);
    },

    'tool.execute.after': async (input, output) => {
      capture('tool.completed', {
        session_id: input?.sessionID,
        payload: { tool_name: input?.tool, tool_input: input?.args, tool_output: output },
      }, cwd);
    },

    'experimental.session.compacting': async (input) => {
      capture('context.compacting', { session_id: input?.sessionID }, cwd);
    },

    event: async ({ event } = {}) => {
      const type = event?.type;
      const properties = event?.properties || {};
      const sessionID = properties.sessionID || properties.info?.id;
      if (type === 'session.created') {
        rememberStart(String(sessionID || 'opencode-session'), {
          cwd: properties.info?.directory || cwd,
          payload: properties,
        });
      } else if (type === 'session.idle') {
        capture('model.responded', { session_id: sessionID, payload: properties }, cwd);
      } else if (type === 'session.compacted') {
        capture('context.usage', { session_id: sessionID, payload: properties }, cwd);
      } else if (type === 'session.error') {
        capture('model.failed', { session_id: sessionID, payload: properties }, cwd);
      } else if (type === 'session.deleted') {
        capture('session.ended', { session_id: sessionID, payload: properties }, cwd);
      }
    },
  };
};
