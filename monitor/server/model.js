// The one shape every provider must produce.
//
// Every API we talk to disagrees about what "failed" means, so normalization
// happens at the edge (inside each provider) and nothing downstream ever sees
// a raw Power Automate or Graph payload.

/** Ordered worst-first. Used for sorting alerts and picking a district's colour. */
export const STATUS = {
  failed: { rank: 0, label: 'Failed', colour: 0xff4d5a, beacon: true, emissive: 1.0 },
  blocked: { rank: 1, label: 'Blocked', colour: 0xff9f3c, beacon: true, emissive: 0.9 },
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
    kind,
    name,
    status,
    detail,
    url,
    // weight drives how tall/large the building is: busier things loom larger.
    weight: Math.max(0.4, Math.min(3, weight)),
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
