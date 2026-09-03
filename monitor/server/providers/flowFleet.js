import { makeEntity } from '../model.js';
import { config } from '../config.js';

// The flow checker, as a scale model.
//
// The point this provider exists to prove: a tenant with hundreds of flows must
// not turn the map into a wall of buildings. Every flow gets its own unit, but a
// unit is a small relay in a field — so a fleet grows sideways as texture, and
// only the ones in trouble claim any visual weight.
//
// It also encodes the distinction the real checker turns on, which Power
// Automate itself cannot tell you: a flow's *expected* state.

const SOLUTIONS = [
  'Invoice Ops', 'Client Intake', 'Field Service', 'Finance Sync',
  'Vendor Portal', 'HR Onboarding', 'Reporting', 'Notifications',
];

const VERBS = ['Sync', 'Notify', 'Route', 'Archive', 'Validate', 'Escalate', 'Reconcile', 'Dispatch'];
const NOUNS = ['Invoice', 'Contact', 'Work Order', 'Approval', 'Document', 'Payment', 'Ticket', 'Timesheet'];

/**
 * Deterministic pseudo-random so the demo fleet is the same on every restart —
 * a fleet that reshuffles each poll would make the scale demo unreadable.
 */
function rand(seed) {
  let h = 2166136261 ^ seed;
  h = Math.imul(h ^ (h >>> 13), 16777619);
  return ((h >>> 0) % 100000) / 100000;
}

export class FlowFleetProvider {
  id = 'flowFleet';
  label = 'Flow checker';

  constructor(size = config.flowFleet.size) {
    this.rows = Array.from({ length: size }, (_, i) => {
      const solution = SOLUTIONS[i % SOLUTIONS.length];
      const name = `${VERBS[Math.floor(rand(i * 7) * VERBS.length)]} ${
        NOUNS[Math.floor(rand(i * 13) * NOUNS.length)]
      } ${String(i + 1).padStart(3, '0')}`;

      // The registry entry: what this flow is SUPPOSED to do. Power Automate
      // knows none of this — it is the judgement the checker adds.
      const expectedOn = rand(i * 3) > 0.08; // a few are meant to be off
      const cadenceHours = [1, 24, 24, 24, 168][Math.floor(rand(i * 5) * 5)];

      return {
        id: `fleet:${i}`,
        name,
        solution,
        expectedOn,
        cadenceHours,
        actuallyOn: expectedOn ? rand(i * 11) > 0.05 : false,
        hoursSinceRun: Math.floor(rand(i * 17) * cadenceHours * 1.6),
        lastError: null,
      };
    });
  }

  /**
   * The four states the checker distinguishes. This is the whole reason the
   * daily audit exists: only the first is visible in Power Automate's own UI.
   */
  assess(row) {
    if (row.expectedOn && !row.actuallyOn) {
      return {
        status: 'blocked',
        detail: 'Should be running — trigger is switched off',
      };
    }
    if (!row.expectedOn) {
      return { status: 'paused', detail: 'Off by design — not under watch' };
    }
    if (row.lastError) {
      return { status: 'failed', detail: row.lastError };
    }
    if (row.hoursSinceRun > row.cadenceHours * 1.5) {
      // On, no errors, and quietly not firing. The silent killer.
      return {
        status: 'warning',
        detail: `On, but no run in ${row.hoursSinceRun}h (expects every ${row.cadenceHours}h)`,
      };
    }
    return {
      status: 'healthy',
      detail: `Last run ${row.hoursSinceRun}h ago · every ${row.cadenceHours}h`,
    };
  }

  tick() {
    for (const row of this.rows) {
      row.hoursSinceRun += Math.random() < 0.3 ? 1 : 0;
      if (row.actuallyOn && Math.random() < 0.35) row.hoursSinceRun = 0;
      // Occasionally somebody turns one off, which is the event the whole
      // checker exists to catch.
      if (row.expectedOn && row.actuallyOn && Math.random() < 0.002) row.actuallyOn = false;
      if (row.expectedOn && !row.actuallyOn && Math.random() < 0.02) {
        row.actuallyOn = true;
        row.hoursSinceRun = 0;
      }
      if (Math.random() < 0.004) row.lastError = 'Connection reference expired — reauthorisation required';
      else if (row.lastError && Math.random() < 0.05) row.lastError = null;
    }
  }

  async fetch() {
    this.tick();
    return this.rows.map((row) => {
      const { status, detail } = this.assess(row);
      return makeEntity({
        id: row.id,
        source: 'flowFleet',
        district: 'Flow Checker',
        kind: 'flow',
        name: row.name,
        status,
        detail,
        url: null,
        metrics: {
          solution: row.solution,
          expectedState: row.expectedOn ? 'Started' : 'Stopped',
          actualState: row.actuallyOn ? 'Started' : 'Stopped',
          cadenceHours: row.cadenceHours,
          hoursSinceRun: row.hoursSinceRun,
        },
        encode: {
          // A relay: small, repeated, unlit when it should be lit.
          form: 'relay',
        },
        actions: row.expectedOn && !row.actuallyOn
          ? [{ id: 'enable', label: 'Turn back on', write: true, hint: 'Restarts the trigger' }]
          : [],
      });
    });
  }

  async execute(entityId, actionId) {
    const row = this.rows.find((r) => r.id === entityId);
    if (!row) return { ok: false, message: 'Unknown flow' };
    if (actionId !== 'enable') return { ok: false, message: `Unsupported action ${actionId}` };
    row.actuallyOn = true;
    row.hoursSinceRun = 0;
    return { ok: true, message: `${row.name} turned back on` };
  }
}
