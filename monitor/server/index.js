import path from 'node:path';
import express from 'express';
import { config, ROOT } from './config.js';
import { Hub } from './hub.js';
import { auth } from './auth.js';

const app = express();
app.use(express.json());

const hub = new Hub();
hub.start();

// Static app + a local copy of three.js so the tool works with no network.
app.use(express.static(path.join(ROOT, 'public')));
app.use('/vendor/three', express.static(path.join(ROOT, 'node_modules/three/build')));
app.use('/vendor/three-addons', express.static(path.join(ROOT, 'node_modules/three/examples/jsm')));

app.get('/api/state', (_req, res) => {
  res.json(hub.snapshot());
});

// Server-sent events: one-way push is all this needs, and it reconnects on its
// own after a laptop sleeps — which a WebSocket would not do for free.
app.get('/api/stream', (req, res) => {
  res.set({
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
  res.flushHeaders();

  const send = (event, data) => {
    res.write(`event: ${event}\n`);
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  };

  send('snapshot', hub.snapshot());

  const onDelta = (d) => send('delta', d);
  const onGame = (g) => send('game', g);
  const onProvider = (p) => send('provider', p);
  hub.on('delta', onDelta);
  hub.on('game', onGame);
  hub.on('provider', onProvider);

  const keepAlive = setInterval(() => res.write(': ping\n\n'), 25000);

  req.on('close', () => {
    clearInterval(keepAlive);
    hub.off('delta', onDelta);
    hub.off('game', onGame);
    hub.off('provider', onProvider);
  });
});

app.post('/api/action', async (req, res) => {
  const { entityId, actionId } = req.body ?? {};
  if (!entityId || !actionId) {
    return res.status(400).json({ ok: false, message: 'entityId and actionId are required' });
  }
  const result = await hub.execute(entityId, actionId);
  res.status(result.ok ? 200 : 400).json(result);
});

app.post('/api/acknowledge', (req, res) => {
  const { entityId } = req.body ?? {};
  const result = hub.acknowledge(entityId);
  res.status(result.ok ? 200 : 400).json(result);
});

app.get('/api/auth/status', async (_req, res) => {
  res.json(await auth.status());
});

// Kicks off device-code sign-in. Returns immediately with the code so the UI
// can display it; the token lands in the cache when the user completes it.
app.post('/api/auth/login', async (_req, res) => {
  if (!auth.configured) {
    return res.status(400).json({ ok: false, message: 'AZURE_CLIENT_ID is not set' });
  }
  const scopeKey = config.providers.powerAutomate ? 'powerAutomate' : 'graph';
  auth.token(scopeKey).then(
    () => hub.poll(),
    (err) => {
      auth.lastError = err.message;
    },
  );

  // Give MSAL a moment to produce the device code before answering.
  const started = Date.now();
  while (!auth.pendingDeviceCode && Date.now() - started < 5000) {
    await new Promise((r) => setTimeout(r, 100));
  }
  res.json({ ok: true, deviceCode: auth.pendingDeviceCode });
});

app.post('/api/auth/logout', (_req, res) => {
  auth.signOut();
  res.json({ ok: true });
});

app.post('/api/refresh', async (_req, res) => {
  await hub.poll();
  res.json({ ok: true, at: hub.lastPollAt });
});

app.listen(config.port, () => {
  const enabled = Object.entries(config.providers)
    .filter(([, on]) => on)
    .map(([name]) => name)
    .join(', ');
  console.log(`\n  Flow Colony → http://localhost:${config.port}`);
  console.log(`  providers: ${enabled || 'none'} · poll: ${config.pollSeconds}s\n`);
});
