import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import openCodePlugin from '../.opencode/plugins/elephant.mjs';
import piExtension from '../pi-extension/index.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const bridge = path.join(root, 'hooks', 'capture.py');
const temporary = mkdtempSync(path.join(tmpdir(), 'elephant-conformance-'));
const workspace = path.join(temporary, 'workspace');
mkdirSync(workspace);
process.env.ELEPHANT_DATA_DIR = path.join(temporary, 'data');

function capture(harness, kind, payload) {
  const result = spawnSync('python3', [bridge, harness, kind], {
    input: JSON.stringify({ cwd: workspace, ...payload }),
    encoding: 'utf8',
    env: process.env,
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim() ? JSON.parse(result.stdout) : null;
}

try {
  capture('claude-code', 'SessionStart', { session_id: 'claude-old' });
  capture('claude-code', 'UserPromptSubmit', {
    session_id: 'claude-old',
    prompt: 'Finish the portable handoff adapters',
  });
  capture('claude-code', 'Stop', {
    session_id: 'claude-old',
    last_assistant_message: 'The shared kernel is ready.',
  });

  const openCode = await openCodePlugin({ directory: workspace });
  const config = {};
  await openCode.config(config);
  assert(config.skills.paths.some((item) => item.endsWith('/skills')));
  await openCode.event({
    event: {
      type: 'session.created',
      properties: { sessionID: 'opencode-new', info: { id: 'opencode-new', directory: workspace } },
    },
  });
  const system = { system: ['OpenCode system'] };
  await openCode['experimental.chat.system.transform']({ sessionID: 'opencode-new' }, system);
  assert.match(system.system[0], /Finish the portable handoff adapters/);
  await openCode['chat.message'](
    { sessionID: 'opencode-new' },
    { parts: [{ type: 'text', text: 'Verify the OpenCode adapter' }] },
  );
  await openCode['tool.execute.before'](
    { sessionID: 'opencode-new', tool: 'write', callID: 'call-1' },
    { args: { file_path: 'adapter.py' } },
  );
  await openCode['tool.execute.after'](
    { sessionID: 'opencode-new', tool: 'write', callID: 'call-1', args: { file_path: 'adapter.py' } },
    { title: 'write', output: 'ok', metadata: {} },
  );
  await openCode['experimental.session.compacting']({ sessionID: 'opencode-new' }, { context: [] });
  await openCode.event({ event: { type: 'session.idle', properties: { sessionID: 'opencode-new' } } });
  await openCode.event({ event: { type: 'session.compacted', properties: { sessionID: 'opencode-new' } } });
  await openCode.event({
    event: {
      type: 'session.error',
      properties: { sessionID: 'opencode-new', error: { name: 'APIError', data: { message: 'retryable test failure' } } },
    },
  });
  await openCode.event({
    event: {
      type: 'session.deleted',
      properties: { sessionID: 'opencode-new', info: { id: 'opencode-new', directory: workspace } },
    },
  });

  const handlers = new Map();
  const commands = new Map();
  piExtension({
    on: (name, handler) => handlers.set(name, handler),
    registerCommand: (name, command) => commands.set(name, command),
  });
  assert(commands.has('elephant'));
  assert(commands.has('resume'));
  const notices = [];
  const piContext = {
    cwd: workspace,
    sessionManager: { getSessionFile: () => path.join(workspace, 'pi-new.jsonl') },
    ui: { notify: (message) => notices.push(message) },
  };
  await handlers.get('session_start')({}, piContext);
  const before = await handlers.get('before_agent_start')(
    { prompt: 'Verify the Pi adapter', systemPrompt: 'Pi system' },
    piContext,
  );
  assert.match(before.systemPrompt, /Verify the OpenCode adapter/);
  assert.match(before.systemPrompt, /adapter\.py/);
  await handlers.get('tool_call')({ toolName: 'write', input: { path: 'pi.py' } }, piContext);
  await handlers.get('tool_result')({ toolName: 'write', content: 'ok', isError: false }, piContext);
  await handlers.get('agent_end')(
    { messages: [{ role: 'assistant', content: [{ type: 'text', text: 'Pi adapter verified.' }] }] },
    piContext,
  );
  await handlers.get('session_before_compact')({}, piContext);
  await handlers.get('session_shutdown')({}, piContext);
  assert(notices.length > 0);

  const recovered = capture('generic', 'session.started', { session_id: 'secondary-new' });
  assert.match(recovered.hookSpecificOutput.additionalContext, /Verify the Pi adapter/);
  assert.match(recovered.hookSpecificOutput.additionalContext, /Pi adapter verified/);
  console.log('OpenCode → Pi → secondary recovery: pass');
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
