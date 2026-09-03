// The one shape every provider must produce.
//
// Every API we talk to disagrees about what "failed" means, so normalization
// happens at the edge (inside each provider) and nothing downstream ever sees
// a raw Power Automate or Graph payload.

/** Ordered worst-first. Used for sorting alerts and picking a district's colour. */
export const STATUS = {
  failed: { rank: 0, label: 'Failed', colour: 0xff4d5a, beacon: true, emissive: 1.0 },
  blocked: { rank: 1, label: 'Blocked', colour: 0xb57bff, beacon: true, emissive: 0.9 },
  warning: { rank: 2, label: 'Degraded', colour: 0xffd23f, beacon: true, emissive: 0.7 },
  running: { rank: 3, label: 'Running', colour: 0x4fc3f7, beacon: false, emissive: 0.9 },
  healthy: { rank: 4, label: 'Healthy', colour: 0x5be7a9, beacon: false, emissive: 0.35 },
  paused: { rank: 5, label: 'Paused', colour: 0x8892a6, beacon: false, emissive: 0.12 },
  unknown: { rank: 6, label: 'Unknown', colour: 0x6b7280, beacon: false, emissive: 0.12 },
};

export const STATUSES = Object.keys(STATUS);

export function statusRank(status) {
  return (STATUS[status] ?? STATUS.unknown).rank;
}

export function needsAttention(status) {
  return Boolean((STATUS[status] ?? STATUS.unknown).beacon);
}

/**
 * Build a normalized entity. Providers call this rather than hand-rolling
 * objects, so a missing field fails loudly here instead of silently rendering
 * a building with no name.
 *
 * @param {object} raw
 * @returns {object} entity
 */
export function makeEntity(raw) {
  const {
    id,
    source,
    district,
    kind = 'flow',
    name,
    status = 'unknown',
    detail = '',
    metrics = {},
    url = null,
    actions = [],
    weight = 1,
    encode = null,
    group = null,
  } = raw;

  if (!id) throw new Error('entity requires an id');
  if (!source) throw new Error(`entity ${id} requires a source`);
  if (!district) throw new Error(`entity ${id} requires a district`);
  if (!name) throw new Error(`entity ${id} requires a name`);
  if (!STATUS[status]) throw new Error(`entity ${id} has unknown status "${status}"`);

  return {
    id,
    source,
    district,
    // The cluster a district belongs to — a neighbourhood, for properties.
    group,
    kind,
    name,
    status,
    detail,
    url,
    // weight drives how tall the building is when no explicit encoding is
    // given: busier things loom larger.
    weight: Math.max(0.4, Math.min(3, weight)),
    encode: normalizeEncoding(encode, id),
    metrics: {
      lastRunAt: metrics.lastRunAt ?? null,
      durationMs: metrics.durationMs ?? null,
      runsToday: metrics.runsToday ?? null,
      failuresToday: metrics.failuresToday ?? null,
      successRate: metrics.successRate ?? null,
      ...metrics,
    },
    actions: actions.map((a) => ({
      id: a.id,
      label: a.label,
      // `write: true` actions mutate something in your tenant and always get a
      // confirmation step in the UI. A stray click must never fire a flow.
      write: Boolean(a.write),
      danger: Boolean(a.danger),
      hint: a.hint ?? '',
    })),
    updatedAt: new Date().toISOString(),
  };
}

/**
 * How a provider declares what its data *means* visually.
 *
 * This is what makes the city a general instrument rather than a flow monitor:
 * a district of houses sized by budget variance and a district of towers sized
 * by run volume are the same machinery with different encodings.
 *
 * Two rules are enforced here rather than left to each provider:
 *
 * 1. **Magnitude rides height only, never footprint.** Scaling a building in
 *    all three axes makes a 2x value look 8x — 3D volume is badly misjudged.
 *    Height is a length from a common baseline, which is the one channel people
 *    read accurately.
 * 2. **A signed metric is a separate channel from status.** Colour in the world
 *    means health; a diverging metric gets its own view mode so two colour
 *    languages are never on screen at once.
 */
function normalizeEncoding(encode, id) {
  if (!encode) return null;

  const out = { form: encode.form ?? null, parcel: encode.parcel ?? null };

  // Severity: 0 = fine, 1 = as bad as this KPI gets.
  //
  // This is what lets one hex mix payroll dollars, open work orders and
  // occupancy percent and still be readable — each provider normalises its own
  // metric against its own thresholds, and height then means the same thing
  // everywhere: how bad. A flat property is a healthy one.
  //
  // The cost is deliberate: normalising throws away raw magnitude, so $30k over
  // and four open work orders can stand the same height. The number itself
  // lives in the detail card; the skyline only answers "who needs me".
  if (encode.severity) {
    const { value, label, raw } = encode.severity;
    if (typeof value !== 'number' || Number.isNaN(value)) {
      throw new Error(`entity ${id} encode.severity.value must be a number`);
    }
    out.severity = {
      value: Math.max(0, Math.min(1, value)),
      label: label ?? 'Severity',
      raw: raw ?? null,
    };
  }

  if (encode.height) {
    const { value, label, unit = '', domain } = encode.height;
    if (typeof value !== 'number' || Number.isNaN(value)) {
      throw new Error(`entity ${id} encode.height.value must be a number`);
    }
    if (!Array.isArray(domain) || domain.length !== 2 || domain[0] === domain[1]) {
      throw new Error(`entity ${id} encode.height.domain must be [min, max] with min !== max`);
    }
    out.height = { value, label: label ?? 'Magnitude', unit, domain };
  }

  if (encode.metric) {
    const { value, label, unit = '', domain, mode = 'diverging', midpoint = 0 } = encode.metric;
    if (typeof value !== 'number' || Number.isNaN(value)) {
      throw new Error(`entity ${id} encode.metric.value must be a number`);
    }
    if (!Array.isArray(domain) || domain.length !== 2) {
      throw new Error(`entity ${id} encode.metric.domain must be [min, max]`);
    }
    if (!['diverging', 'sequential'].includes(mode)) {
      throw new Error(`entity ${id} encode.metric.mode must be diverging or sequential`);
    }
    out.metric = { value, label: label ?? 'Metric', unit, domain, mode, midpoint };
  }

  return out.height || out.metric || out.form || out.parcel || out.severity ? out : null;
}

/**
 * Diff two entity maps. Returns only what actually changed, because pushing a
 * full snapshot every poll would make the client re-render the whole city and
 * lose the "something just happened" signal that the beacons depend on.
 */
export function diffEntities(prev, next) {
  const added = [];
  const changed = [];
  const removed = [];
  const transitions = [];

  for (const [id, entity] of next) {
    const before = prev.get(id);
    if (!before) {
      added.push(entity);
      continue;
    }
    if (before.status !== entity.status) {
      transitions.push({ id, from: before.status, to: entity.status, entity });
      changed.push(entity);
    } else if (
      before.detail !== entity.detail ||
      before.name !== entity.name ||
      before.metrics.lastRunAt !== entity.metrics.lastRunAt
    ) {
      changed.push(entity);
    }
  }

  for (const [id, entity] of prev) {
    if (!next.has(id)) removed.push(entity);
  }

  return { added, changed, removed, transitions };
}
