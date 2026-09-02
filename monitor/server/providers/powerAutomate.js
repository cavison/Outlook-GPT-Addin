import { makeEntity } from '../model.js';
import { auth } from '../auth.js';
import { config } from '../config.js';

const API = 'https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple';
const API_VERSION = '2016-11-01';

async function call(token, url, init = {}) {
  const res = await fetch(url, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    const err = new Error(`${res.status} ${res.statusText} — ${body.slice(0, 300)}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

/**
 * Collapse a flow's declared state plus its recent run history into one status.
 * Power Automate reports these in two unrelated places, which is exactly the
 * kind of disagreement the normalized model exists to absorb.
 */
function deriveStatus(flow, runs) {
  const state = flow.properties?.state;
  if (state === 'Stopped') return { status: 'paused', detail: 'Trigger turned off' };
  if (state === 'Suspended') {
    return { status: 'blocked', detail: 'Suspended by the service — usually a failed connection' };
  }

  if (!runs.length) return { status: 'unknown', detail: 'No runs in retained history' };

  const [latest] = runs;
  const latestStatus = latest.properties?.status;
  const recentFailures = runs.filter((r) => r.properties?.status === 'Failed').length;

  if (latestStatus === 'Running') {
    return { status: 'running', detail: 'Run in progress' };
  }
  if (latestStatus === 'Failed') {
    const message =
      latest.properties?.error?.message ??
      latest.properties?.code ??
      'Last run failed';
    return { status: 'failed', detail: message };
  }
  if (latestStatus === 'Cancelled') {
    return { status: 'warning', detail: 'Last run cancelled' };
  }
  if (recentFailures >= 2) {
    return {
      status: 'warning',
      detail: `${recentFailures} of the last ${runs.length} runs failed`,
    };
  }
  return { status: 'healthy', detail: 'Last run succeeded' };
}

export class PowerAutomateProvider {
  id = 'powerAutomate';
  label = 'Power Automate';

  constructor() {
    this.environmentId = config.powerAutomate.environmentId || null;
    // flowName -> { triggerName, lastFailedRun } so a re-run knows what to
    // resubmit without a second round trip at click time.
    this.resubmitTargets = new Map();
  }

  async resolveEnvironment(token) {
    if (this.environmentId) return this.environmentId;
    const data = await call(token, `${API}/environments?api-version=${API_VERSION}`);
    const envs = data?.value ?? [];
    const preferred = envs.find((e) => e.properties?.isDefault) ?? envs[0];
    if (!preferred) throw new Error('No Power Automate environments visible to this account');
    this.environmentId = preferred.name;
    return this.environmentId;
  }

  async fetch() {
    const token = await auth.token('powerAutomate', { interactive: false });
    if (!token) return [];

    const env = await this.resolveEnvironment(token);
    const flowsUrl = `${API}/environments/${env}/flows?api-version=${API_VERSION}`;
    const flows = (await call(token, flowsUrl))?.value ?? [];

    const entities = [];
    for (const flow of flows) {
      let runs = [];
      try {
        const runsUrl =
          `${API}/environments/${env}/flows/${flow.name}/runs` +
          `?api-version=${API_VERSION}&$top=8`;
        runs = (await call(token, runsUrl))?.value ?? [];
      } catch (err) {
        // A flow that has never run returns 404 on its run collection. That is
        // information, not an outage — keep going.
        if (err.status !== 404) console.warn(`[powerAutomate] runs for ${flow.name}: ${err.message}`);
      }

      const { status, detail } = deriveStatus(flow, runs);
      const failed = runs.find((r) => r.properties?.status === 'Failed');
      if (failed) {
        this.resubmitTargets.set(flow.name, {
          trigger: failed.properties?.trigger?.name ?? 'manual',
          run: failed.name,
        });
      }

      const runsToday = runs.filter(
        (r) => new Date(r.properties?.startTime ?? 0).toDateString() === new Date().toDateString(),
      ).length;

      entities.push(
        makeEntity({
          id: `pa:${flow.name}`,
          source: 'powerAutomate',
          district: flow.properties?.displayName?.split(/[-–—|:]/)[0]?.trim() || 'Power Automate',
          kind: 'flow',
          name: flow.properties?.displayName ?? flow.name,
          status,
          detail,
          // Busier flows get bigger buildings.
          weight: 0.6 + Math.min(2.2, runs.length * 0.28),
          url: `https://make.powerautomate.com/environments/${env}/flows/${flow.name}/details`,
          metrics: {
            lastRunAt: runs[0]?.properties?.startTime ?? null,
            runsToday,
            failuresToday: runs.filter(
              (r) =>
                r.properties?.status === 'Failed' &&
                new Date(r.properties?.startTime ?? 0).toDateString() ===
                  new Date().toDateString(),
            ).length,
            state: flow.properties?.state ?? null,
            environmentId: env,
            flowName: flow.name,
          },
          actions: [
            {
              id: 'rerun',
              label: 'Resubmit failed run',
              write: true,
              hint: 'Resubmits the most recent failed run with its original trigger payload',
            },
            { id: 'enable', label: 'Turn on', write: true },
            { id: 'disable', label: 'Turn off', write: true, danger: true },
          ],
        }),
      );
    }
    return entities;
  }

  async execute(entityId, actionId) {
    const token = await auth.token('powerAutomate', { interactive: false });
    if (!token) return { ok: false, message: 'Not signed in' };

    const flowName = entityId.replace(/^pa:/, '');
    const env = await this.resolveEnvironment(token);
    const base = `${API}/environments/${env}/flows/${flowName}`;

    try {
      if (actionId === 'enable') {
        await call(token, `${base}/start?api-version=${API_VERSION}`, { method: 'POST' });
        return { ok: true, message: 'Flow turned on' };
      }
      if (actionId === 'disable') {
        await call(token, `${base}/stop?api-version=${API_VERSION}`, { method: 'POST' });
        return { ok: true, message: 'Flow turned off' };
      }
      if (actionId === 'rerun') {
        const target = this.resubmitTargets.get(flowName);
        if (!target) return { ok: false, message: 'No failed run available to resubmit' };
        await call(
          token,
          `${base}/triggers/${target.trigger}/histories/${target.run}/resubmit` +
            `?api-version=${API_VERSION}`,
          { method: 'POST' },
        );
        return { ok: true, message: 'Run resubmitted' };
      }
      return { ok: false, message: `Unsupported action ${actionId}` };
    } catch (err) {
      return { ok: false, message: err.message };
    }
  }
}
