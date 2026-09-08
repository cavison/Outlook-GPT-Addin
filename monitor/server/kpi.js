import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from './config.js';
import { PARCEL_POSITION_BY_NUMBER } from './parcels.js';
import { percentile } from './severity.js';

// ---------------------------------------------------------------------------
// The KPI contract.
//
// Every source — the monthly workbook, a nightly signage agent, a Power
// Automate flow posting to /api/ingest, a hand-edited CSV — produces the same
// thing: a batch of readings for ONE KPI, one row per property. Nothing
// downstream cares where a reading came from.
//
//   { kpi, asOf, source, rows: [{ property, value, ... }] }
//
// Two decisions live here rather than in each connector, because getting them
// wrong in nine different places is how a dashboard starts lying:
//
//   1. What "bad" means for this SHAPE of measurement. Money variance, a
//      ratio of screens online, a count of requests entered and a yes/no
//      submission are four different questions and cannot share one formula.
//      They can and must share one output: severity in 0..1, where 0 is fine.
//
//   2. When a reading has gone stale. A KPI that stopped reporting must not
//      keep showing its last good value forever — that is precisely how a
//      broken feed hides for a month. Past its cadence window a reading is
//      no longer a reading; the parcel goes back to "no data".
// ---------------------------------------------------------------------------

const REGISTRY_PATH = path.join(ROOT, 'config', 'kpis.json');
export const STORE_DIR = path.join(ROOT, 'data', 'measurements');

/** How long a reading stays believable, by cadence, unless the KPI overrides it. */
const STALE_DAYS = { realtime: 1, daily: 3, weekly: 10, monthly: 45, quarterly: 120 };

export const KINDS = ['variance', 'ratio', 'count', 'boolean', 'label'];

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

export function loadRegistry() {
  if (!fs.existsSync(REGISTRY_PATH)) {
    throw new Error(`KPI registry not found at ${REGISTRY_PATH}`);
  }

  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
  } catch (err) {
    throw new Error(`config/kpis.json is not valid JSON — ${err.message}`);
  }

  const errors = [];
  const kpis = {};
  const parcelTaken = new Map();

  for (const [id, spec] of Object.entries(raw.kpis ?? {})) {
    if (!/^[a-z0-9][a-z0-9-]*$/.test(id)) {
      errors.push(`"${id}" is not a valid KPI id (lowercase, digits and hyphens)`);
    }
    if (!KINDS.includes(spec.kind)) {
      errors.push(`${id}: kind "${spec.kind}" is not one of ${KINDS.join(', ')}`);
    }
    if (!spec.label) errors.push(`${id}: no label`);

    // A label KPI is an attribute of the property (its director, say), not a
    // reading, so it has no address on the hex.
    if (spec.kind === 'label') {
      if (spec.parcel) errors.push(`${id}: a label KPI cannot claim a parcel`);
    } else if (!PARCEL_POSITION_BY_NUMBER.has(spec.parcel)) {
      errors.push(`${id}: parcel "${spec.parcel}" is not a position (01–25)`);
    } else if (parcelTaken.has(spec.parcel)) {
      // Two KPIs on one address would silently overwrite each other and the
      // hex would quietly stop meaning what the legend says.
      errors.push(`${id}: parcel ${spec.parcel} is already taken by ${parcelTaken.get(spec.parcel)}`);
    } else {
      parcelTaken.set(spec.parcel, id);
    }

    if (spec.cadence && !STALE_DAYS[spec.cadence]) {
      errors.push(`${id}: cadence "${spec.cadence}" is not one of ${Object.keys(STALE_DAYS).join(', ')}`);
    }
    if (spec.direction && !['at-least', 'at-most'].includes(spec.direction)) {
      errors.push(`${id}: direction must be at-least or at-most`);
    }
    if (spec.kind === 'count' && spec.target == null) {
      errors.push(`${id}: a count KPI needs a target`);
    }

    const cadence = spec.cadence ?? 'monthly';
    kpis[id] = {
      id,
      label: spec.label,
      kind: spec.kind,
      parcel: spec.parcel ?? null,
      cadence,
      staleAfterDays: spec.staleAfterDays ?? STALE_DAYS[cadence] ?? 45,
      ceiling: spec.ceiling ?? 1,
      target: spec.target ?? null,
      direction: spec.direction ?? 'at-least',
      unit: spec.unit ?? null,
      // Roster pip glyph. Falls back to the parcel number, which is never
      // wrong — position IS the identity here.
      icon: spec.icon ?? null,
      priority: Boolean(spec.priority),
      // Adapter hint: which line in the Actuals vs Budget workbook feeds this.
      // Only the importer reads it; every other source names the KPI directly.
      workbookLine: spec.workbookLine ?? null,
      source: spec.source ?? null,
      description: spec.description ?? '',
    };
  }

  if (!Object.keys(kpis).length) errors.push('no KPIs defined');
  if (errors.length) throw new Error(`config/kpis.json:\n  - ${errors.join('\n  - ')}`);

  return kpis;
}

// ---------------------------------------------------------------------------
// Batch validation. Shared by the CLI, the HTTP endpoint and the reader, so a
// bad batch is rejected the same way however it arrives.
// ---------------------------------------------------------------------------

/**
 * Check and tidy one batch against the registry.
 * @returns {{ ok: boolean, errors: string[], batch?: object }}
 */
export function validateBatch(batch, registry, { now = new Date() } = {}) {
  const errors = [];
  if (!batch || typeof batch !== 'object') return { ok: false, errors: ['batch is not an object'] };

  const spec = registry[batch.kpi];
  if (!spec) {
    errors.push(
      `unknown kpi "${batch.kpi}" — add it to config/kpis.json first ` +
        `(known: ${Object.keys(registry).join(', ')})`,
    );
    return { ok: false, errors };
  }

  const asOf = batch.asOf ? new Date(batch.asOf) : now;
  if (Number.isNaN(asOf.getTime())) errors.push(`asOf "${batch.asOf}" is not a date`);
  // A reading from the future is almost always a timezone or format mistake,
  // and it would keep a stale feed looking fresh indefinitely.
  if (asOf.getTime() > now.getTime() + 36 * 3600 * 1000) {
    errors.push(`asOf ${asOf.toISOString()} is in the future`);
  }

  if (!Array.isArray(batch.rows) || !batch.rows.length) {
    errors.push('rows must be a non-empty array');
    return { ok: false, errors };
  }

  const seen = new Set();
  const rows = [];
  batch.rows.forEach((row, i) => {
    const where = `row ${i + 1}`;
    const property = String(row.property ?? '').trim();
    if (!property) { errors.push(`${where}: no property`); return; }
    if (seen.has(property)) { errors.push(`${where}: "${property}" appears twice`); return; }
    seen.add(property);

    const out = { property };
    if (row.applicable === false) {
      // "We don't do this here" is a real answer and must not be scored as a
      // failure — but it must also not be silently indistinguishable from a
      // feed that died.
      out.applicable = false;
      if (row.note) out.note = String(row.note);
      rows.push(out);
      return;
    }

    const problem = validateValue(row, spec, where);
    if (problem) { errors.push(problem); return; }

    Object.assign(out, coerceValue(row, spec));
    if (row.note) out.note = String(row.note);
    if (row.url) out.url = String(row.url);
    rows.push(out);
  });

  if (errors.length) return { ok: false, errors };

  return {
    ok: true,
    errors: [],
    batch: {
      kpi: batch.kpi,
      asOf: asOf.toISOString(),
      source: String(batch.source ?? 'unknown'),
      receivedAt: now.toISOString(),
      rows,
    },
  };
}

function validateValue(row, spec, where) {
  switch (spec.kind) {
    case 'variance':
      if (!Number.isFinite(Number(row.value))) return `${where}: value must be a number`;
      return null;
    case 'ratio':
      if (!Number.isFinite(Number(row.value))) return `${where}: value must be a number`;
      if (row.total == null || !Number.isFinite(Number(row.total))) {
        return `${where}: a ratio needs a total (e.g. screens installed)`;
      }
      if (Number(row.total) < 0) return `${where}: total cannot be negative`;
      if (Number(row.value) > Number(row.total)) {
        return `${where}: value ${row.value} exceeds total ${row.total}`;
      }
      return null;
    case 'count':
      if (!Number.isFinite(Number(row.value))) return `${where}: value must be a number`;
      return null;
    case 'boolean':
      if (parseBool(row.value) === null) {
        return `${where}: value must be true/false (yes/no, 1/0 and done/missing also work)`;
      }
      return null;
    case 'label':
      if (row.value == null || String(row.value).trim() === '') return `${where}: value is empty`;
      return null;
    default:
      return `${where}: unsupported kind ${spec.kind}`;
  }
}

function coerceValue(row, spec) {
  switch (spec.kind) {
    case 'variance':
      return {
        value: Number(row.value),
        ...(row.budget != null ? { budget: Number(row.budget) } : {}),
        ...(row.actual != null ? { actual: Number(row.actual) } : {}),
      };
    case 'ratio':
      return { value: Number(row.value), total: Number(row.total) };
    case 'count':
      return { value: Number(row.value), ...(row.target != null ? { target: Number(row.target) } : {}) };
    case 'boolean':
      return { value: parseBool(row.value) };
    default:
      return { value: String(row.value).trim() };
  }
}

export function parseBool(v) {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'number') return v !== 0;
  const s = String(v ?? '').trim().toLowerCase();
  if (['true', 'yes', 'y', '1', 'done', 'complete', 'completed', 'on file', 'ok'].includes(s)) return true;
  if (['false', 'no', 'n', '0', 'missing', 'incomplete', 'not done', 'none', ''].includes(s)) return false;
  return null;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export function batchPath(kpiId) {
  return path.join(STORE_DIR, `${kpiId}.json`);
}

export function writeBatch(batch) {
  fs.mkdirSync(STORE_DIR, { recursive: true });
  fs.writeFileSync(batchPath(batch.kpi), `${JSON.stringify(batch, null, 2)}\n`);
  return batchPath(batch.kpi);
}

/** Every stored batch, keyed by KPI id. Unreadable files warn and are skipped. */
export function readStore(registry) {
  const out = new Map();
  if (!fs.existsSync(STORE_DIR)) return out;

  for (const id of Object.keys(registry)) {
    const file = batchPath(id);
    if (!fs.existsSync(file)) continue;
    try {
      const batch = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (Array.isArray(batch.rows)) out.set(id, batch);
    } catch (err) {
      console.warn(`[kpi] could not read ${path.basename(file)} — ${err.message}`);
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

/**
 * The scale for a variance KPI: the 90th percentile of its own unfavourable
 * readings. See severity.js for why percent-of-budget and raw dollars both
 * fail on this data. Derived per batch so a KPI pushed by an API gets the same
 * treatment as one imported from the workbook, with nothing to configure.
 */
export function scaleFor(batch) {
  const magnitudes = batch.rows
    .filter((r) => r.applicable !== false && Number.isFinite(r.value) && r.value < 0)
    .map((r) => Math.abs(r.value));
  if (!magnitudes.length) return null;
  return Math.max(percentile(magnitudes, 0.9), 250);
}

/** True when a batch is older than its KPI's cadence allows. */
export function isStale(batch, spec, now = new Date()) {
  const asOf = new Date(batch.asOf);
  if (Number.isNaN(asOf.getTime())) return true;
  return now.getTime() - asOf.getTime() > spec.staleAfterDays * 86400_000;
}

/**
 * Score one reading.
 *
 * Returns `{ severity, headline, detail }` — severity in 0..1 where 0 is fine,
 * and two strings the UI can show without knowing what kind of KPI this is.
 */
export function scoreReading(row, spec, { scale = null } = {}) {
  const ceiling = spec.ceiling ?? 1;
  const clamp = (v) => Math.max(0, Math.min(ceiling, v * ceiling));

  switch (spec.kind) {
    case 'variance': {
      const v = row.value;
      const over = v < 0;
      const severity = over && scale ? clamp(Math.abs(v) / scale) : 0;
      return {
        severity,
        headline: over ? `${money(Math.abs(v))} over` : `${money(v)} under`,
        detail:
          row.actual != null && row.budget != null
            ? `actual ${money(row.actual)} vs budget ${money(row.budget)}`
            : over
              ? 'over budget'
              : 'under budget',
      };
    }
    case 'ratio': {
      const target = spec.target ?? 1;
      if (!row.total) {
        // Nothing installed to report on. Not a failure, and not a gap either.
        return { severity: 0, headline: 'none installed', detail: '', notApplicable: true };
      }
      const share = row.value / row.total;
      const shortfall = Math.max(0, target - share) / (target || 1);
      return {
        severity: clamp(shortfall),
        headline: `${row.value} of ${row.total}`,
        detail: `${Math.round(share * 100)}% — target ${Math.round(target * 100)}%`,
      };
    }
    case 'count': {
      const target = row.target ?? spec.target ?? 0;
      const miss =
        spec.direction === 'at-most'
          ? Math.max(0, row.value - target)
          : Math.max(0, target - row.value);
      const severity = clamp(miss / Math.max(1, Math.abs(target)));
      const unit = spec.unit ? ` ${spec.unit}` : '';
      return {
        severity,
        headline: `${row.value}${unit}`,
        detail:
          spec.direction === 'at-most'
            ? `target no more than ${target}`
            : `target ${target}`,
      };
    }
    case 'boolean': {
      return {
        severity: row.value ? 0 : ceiling,
        headline: row.value ? 'done' : 'not done',
        detail: '',
      };
    }
    default:
      return { severity: 0, headline: String(row.value), detail: '' };
  }
}

function money(value) {
  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(Math.round(value)).toLocaleString('en-US')}`;
}
