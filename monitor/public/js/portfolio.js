// One property, assembled.
//
// The server sends entities — one per parcel — because that is what the map
// draws. The roster, the filters and the height variants all want the opposite
// shape: one row per property, with every KPI on it, in a fixed order. This
// module is the only place that transposition happens, so the roster and the
// map can never disagree about how a property is doing.

/** Pip and filter states, worst first. The order is the sort order. */
export const CELL_STATES = ['fail', 'warn', 'gap', 'met', 'na', 'wait'];

export const STATE_LABEL = {
  fail: 'Failing',
  warn: 'Slipping',
  gap: 'No data — feed stopped',
  met: 'Met',
  na: 'Not applicable',
  wait: 'Not connected yet',
};

/**
 * Which pip a parcel gets.
 *
 * `gap` and `wait` are deliberately different: one is a feed that broke and is
 * work to do, the other is a KPI nobody has wired up yet and is a plan. Reading
 * them as one thing would either cry wolf about nine unbuilt KPIs or bury a
 * real outage among them.
 */
function cellState(entity) {
  if (!entity) return 'wait';
  if (entity.status === 'unknown') return 'gap';
  if (entity.status === 'paused' || entity.encode?.form === 'lot') return 'na';
  const severity = entity.encode?.severity?.value ?? 0;
  if (severity >= 0.5) return 'fail';
  if (severity >= 0.28) return 'warn';
  return 'met';
}

/**
 * Build the roster rows.
 *
 * @param {Map<string, object>} entities   every entity, by id
 * @param {object} registry                the KPI registry from the server
 */
export function buildRoster(entities, registry) {
  // Parcel order, so pip 3 is the same KPI on every card — the same rule the
  // hex itself obeys. Sorting by label would reshuffle the cards the day
  // someone renames a KPI.
  const kpis = Object.values(registry)
    .filter((k) => k.parcel)
    .sort((a, b) => a.parcel.localeCompare(b.parcel));

  const byProperty = new Map();
  for (const e of entities.values()) {
    if (e.source !== 'estate') continue;
    const row = byProperty.get(e.district) ?? { parcels: new Map(), landmark: null };
    if (e.encode?.parcel === '01') row.landmark = e;
    else if (e.metrics?.kpi) row.parcels.set(e.metrics.kpi, e);
    byProperty.set(e.district, row);
  }

  const rows = [];
  for (const [name, raw] of byProperty) {
    if (!raw.landmark) continue; // a property with no landmark is mid-poll
    const m = raw.landmark.metrics ?? {};

    const cells = kpis.map((kpi) => {
      const entity = raw.parcels.get(kpi.id) ?? null;
      const state = cellState(entity);
      return {
        kpi,
        entity,
        state,
        severity: entity?.encode?.severity?.value ?? 0,
        detail: entity?.detail ?? (state === 'wait' ? (kpi.source ?? 'not connected') : ''),
      };
    });

    const scored = cells.filter((c) => ['fail', 'warn', 'met'].includes(c.state));

    rows.push({
      name,
      neighbourhood: raw.landmark.group ?? 'Unassigned',
      director: m.director ?? null,
      landmarkId: raw.landmark.id,
      status: raw.landmark.status,
      detail: raw.landmark.detail,
      cells,
      cellByKpi: new Map(cells.map((c) => [c.kpi.id, c])),
      // Worst-of drives the colour, exactly as it drives the landmark's.
      severity: scored.length ? Math.max(...scored.map((c) => c.severity)) : 0,
      hp: healthPoints(scored),
      variance: cells
        .filter((c) => c.kpi.kind === 'variance' && c.entity?.metrics?.variance != null)
        .reduce((sum, c) => sum + c.entity.metrics.variance, 0),
      counts: countStates(cells),
      reporting: scored.length,
      worst: scored.length
        ? scored.reduce((a, b) => (b.severity > a.severity ? b : a))
        : null,
    });
  }

  return { kpis, rows };
}

/**
 * 0–100, high is good, in the shape a party sheet uses.
 *
 * A mean rather than worst-of, because this is the number the roster SORTS on
 * and worst-of cannot tell a property failing one line from a property failing
 * four equally badly. The colour still comes from worst-of, so nothing hides:
 * the card is red because of its worst KPI and ranked by how much is wrong.
 *
 * Priority KPIs count double. Payroll and the operating line are the two that
 * actually move the business, and letting four automotive parcels outvote them
 * would rank the roster by petrol.
 *
 * Only reporting KPIs count. A broken feed is shown as its own pip and its own
 * tally instead of being quietly folded into the score, because "we don't know"
 * is not the same as "it's bad" and averaging it in would make both invisible.
 */
function healthPoints(scored) {
  if (!scored.length) return 100;
  let weight = 0;
  let load = 0;
  for (const c of scored) {
    const w = c.kpi.priority ? 2 : 1;
    weight += w;
    load += c.severity * w;
  }
  return Math.round(100 - (load / weight) * 100);
}

function countStates(cells) {
  const out = Object.fromEntries(CELL_STATES.map((s) => [s, 0]));
  for (const c of cells) out[c.state]++;
  return out;
}

export function money(value) {
  const sign = value < 0 ? '−' : '+';
  return `${sign}$${Math.abs(Math.round(value)).toLocaleString('en-US')}`;
}

export function hpBand(hp) {
  return hp > 70 ? '' : hp >= 40 ? 'm-amber' : 'm-red';
}
