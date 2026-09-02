import { makeEntity } from '../model.js';

// A simulated tenant. It exists so the city is alive on first run — you can
// judge the design, the beacons and the scoring before spending a week waiting
// on an app registration. It churns on a real state machine rather than random
// colours, so "watch it for five minutes" is a meaningful test.

const SEED = [
  { d: 'Invoice Ops', n: 'Invoice Intake — Email', k: 'flow', w: 2.6 },
  { d: 'Invoice Ops', n: 'PO Match & Route', k: 'flow', w: 2.1 },
  { d: 'Invoice Ops', n: 'Vendor Onboarding Approval', k: 'approval', w: 1.4 },
  { d: 'Invoice Ops', n: 'Exception Queue Sweep', k: 'flow', w: 1.1 },
  { d: 'Invoice Ops', n: 'Nightly Ledger Export', k: 'job', w: 1.8 },
  { d: 'Invoice Ops', n: 'Duplicate Detector', k: 'flow', w: 0.9 },

  { d: 'Client Intake', n: 'New Client Form → CRM', k: 'flow', w: 2.3 },
  { d: 'Client Intake', n: 'Welcome Sequence', k: 'flow', w: 1.2 },
  { d: 'Client Intake', n: 'Document Request Chase', k: 'flow', w: 1.0 },
  { d: 'Client Intake', n: 'Intake SLA Watchdog', k: 'watchdog', w: 1.6 },
  { d: 'Client Intake', n: 'Signature Callback', k: 'webhook', w: 1.3 },

  { d: 'Outlook Add-in', n: 'Rewriter API Health', k: 'endpoint', w: 2.4 },
  { d: 'Outlook Add-in', n: 'Manifest Validation', k: 'job', w: 0.8 },
  { d: 'Outlook Add-in', n: 'Token Refresh Loop', k: 'endpoint', w: 1.5 },
  { d: 'Outlook Add-in', n: 'Usage Telemetry Sink', k: 'flow', w: 1.1 },

  { d: 'Reporting', n: 'Weekly Ops Digest', k: 'flow', w: 1.4 },
  { d: 'Reporting', n: 'Dataverse Sync', k: 'job', w: 2.2 },
  { d: 'Reporting', n: 'KPI Refresh', k: 'job', w: 1.7 },
  { d: 'Reporting', n: 'Stale Record Sweeper', k: 'flow', w: 0.9 },

  { d: 'M365 Signals', n: 'Shared Mailbox — Support', k: 'mailbox', w: 2.5 },
  { d: 'M365 Signals', n: 'Shared Mailbox — Billing', k: 'mailbox', w: 1.9 },
  { d: 'M365 Signals', n: 'Graph Subscription Renewal', k: 'subscription', w: 1.6 },
  { d: 'M365 Signals', n: 'Calendar Conflict Watch', k: 'calendar', w: 1.0 },
  { d: 'M365 Signals', n: 'Inbox Rule Drift', k: 'watchdog', w: 0.8 },
];

const FAIL_REASONS = [
  'Action "Send an email (V2)" failed: 429 TooManyRequests',
  'Connection reference expired — reauthorisation required',
  'Timeout waiting on HTTP response after 120s',
  'Trigger condition evaluated null: "approverEmail"',
  'Dataverse write rejected: duplicate alternate key',
];

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

export class MockProvider {
  id = 'mock';
  label = 'Simulated tenant';

  constructor() {
    this.rows = SEED.map((s, i) => ({
      id: `mock:${i}`,
      district: s.d,
      name: s.n,
      kind: s.k,
      weight: s.w,
      status: Math.random() < 0.12 ? 'warning' : 'healthy',
      detail: '',
      reason: null,
      runsToday: Math.floor(Math.random() * 400),
      failuresToday: 0,
      lastRunAt: Date.now() - Math.floor(Math.random() * 9e5),
    }));
  }

  /** One step of the simulation. Transitions are weighted so failures are
   *  uncommon but not rare enough to be boring to watch. */
  tick() {
    for (const row of this.rows) {
      const roll = Math.random();
      switch (row.status) {
        case 'healthy':
          if (roll < 0.035) row.status = 'running';
          else if (roll < 0.05) { row.status = 'warning'; row.reason = 'Success rate dipped below 95%'; }
          else if (roll < 0.058) { row.status = 'failed'; row.reason = pick(FAIL_REASONS); row.failuresToday++; }
          break;
        case 'running':
          if (roll < 0.55) { row.status = 'healthy'; row.lastRunAt = Date.now(); row.runsToday++; }
          else if (roll < 0.62) { row.status = 'failed'; row.reason = pick(FAIL_REASONS); row.failuresToday++; }
          break;
        case 'warning':
          if (roll < 0.18) row.status = 'healthy';
          else if (roll < 0.26) { row.status = 'failed'; row.reason = pick(FAIL_REASONS); row.failuresToday++; }
          break;
        case 'failed':
          // Failures mostly persist until someone does something — that is the
          // whole point of the monitor.
          if (roll < 0.04) row.status = 'healthy';
          else if (roll < 0.09) row.status = 'blocked';
          break;
        case 'blocked':
          if (roll < 0.03) row.status = 'failed';
          break;
        default:
          break;
      }
    }
  }

  async fetch() {
    this.tick();
    return this.rows.map((row) => {
      const mins = Math.max(0, Math.round((Date.now() - row.lastRunAt) / 60000));
      const detail =
        row.status === 'failed' || row.status === 'blocked' || row.status === 'warning'
          ? row.reason ?? 'Needs attention'
          : `Last run ${mins}m ago · ${row.runsToday} runs today`;

      return makeEntity({
        id: row.id,
        source: 'mock',
        district: row.district,
        kind: row.kind,
        name: row.name,
        status: row.status,
        detail,
        weight: row.weight,
        url: null,
        metrics: {
          lastRunAt: new Date(row.lastRunAt).toISOString(),
          runsToday: row.runsToday,
          failuresToday: row.failuresToday,
          successRate: row.runsToday
            ? Number((1 - row.failuresToday / Math.max(1, row.runsToday)).toFixed(3))
            : null,
        },
        actions: [
          { id: 'rerun', label: 'Re-run now', write: true, hint: 'Resubmits the most recent failed run' },
          { id: 'disable', label: 'Turn off', write: true, danger: true, hint: 'Stops the trigger' },
          { id: 'enable', label: 'Turn on', write: true },
        ],
      });
    });
  }

  async execute(entityId, actionId) {
    const row = this.rows.find((r) => r.id === entityId);
    if (!row) return { ok: false, message: 'Unknown entity' };

    switch (actionId) {
      case 'rerun':
        row.status = 'running';
        row.reason = null;
        row.lastRunAt = Date.now();
        return { ok: true, message: `Re-run queued for ${row.name}` };
      case 'disable':
        row.status = 'paused';
        return { ok: true, message: `${row.name} turned off` };
      case 'enable':
        row.status = 'healthy';
        row.reason = null;
        return { ok: true, message: `${row.name} turned on` };
      default:
        return { ok: false, message: `Unsupported action ${actionId}` };
    }
  }
}
