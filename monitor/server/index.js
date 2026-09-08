import path from 'node:path';
import express from 'express';
import { config, ROOT } from './config.js';
import { Hub } from './hub.js';
import { auth } from './auth.js';
import { loadRegistry, validateBatch, writeBatch } from './kpi.js';

const app = express();
// A monthly batch for 200 properties is comfortably under this; the default
// 100kb is not.
app.use(express.json({ limit: '4mb' }));

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

// ---------------------------------------------------------------------------
// Ingest. The door a Power Automate flow, a scheduled agent or a script pushes
// readings through. Same normalizer and same validation as the CLI, so nothing
// can reach the map by a route that skips the checks.
//
// The server binds to localhost, so this is not exposed to your network. If you
// ever put it behind a tunnel so a cloud flow can reach it, put a shared secret
// in INGEST_TOKEN first — an unauthenticated writer could otherwise quietly
// turn every KPI green.
// ---------------------------------------------------------------------------
app.get('/api/kpis', (_req, res) => {
  try {
    res.json({ ok: true, kpis: loadRegistry() });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
});

app.post('/api/ingest', async (req, res) => {
  if (config.ingestToken && req.get('x-ingest-token') !== config.ingestToken) {
    return res.status(401).json({ ok: false, message: 'bad or missing x-ingest-token' });
  }

  let registry;
  try {
    registry = loadRegistry();
  } catch (err) {
    return res.status(500).json({ ok: false, message: err.message });
  }

  // Accept one batch or several, so a flow that gathers three KPIs in one run
  // does not have to make three calls and half-succeed.
  const batches = Array.isArray(req.body) ? req.body : [req.body];
  const checked = batches.map((b) => validateBatch(b, registry));
  const bad = checked.filter((c) => !c.ok);
  if (bad.length) {
    // All or nothing: a partly-applied push would leave the map in a state
    // nobody asked for and nobody can see.
    return res.status(400).json({
      ok: false,
      message: `${bad.length} of ${batches.length} batch(es) rejected — nothing was written`,
      errors: bad.flatMap((c) => c.errors).slice(0, 50),
    });
  }

  const written = checked.map((c) => {
    writeBatch(c.batch);
    return { kpi: c.batch.kpi, rows: c.batch.rows.length, asOf: c.batch.asOf };
  });

  await hub.poll(); // show it now rather than at the next tick
  res.json({ ok: true, written });
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
