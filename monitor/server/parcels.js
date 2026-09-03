import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from './config.js';

// ---------------------------------------------------------------------------
// Parcels: the fixed subdivision of a property hex.
//
// The positions are constant and there are more of them than we currently use.
// That is the whole design. Nine parcels evenly spaced would re-space the moment
// a tenth KPI arrived, moving every object on every property and destroying the
// layout you had learned. Twenty-five fixed positions means a new KPI fills a
// vacant one and NOTHING ELSE MOVES.
// ---------------------------------------------------------------------------

// Single source of truth for hex size; world.js imports it from here so the
// parcel geometry and the plate it sits on can never drift apart.
export const TILE_RADIUS = 9;

const INNER_RADIUS = 4.1;
const OUTER_RADIUS = 6.6;
const RING_COUNT = 12;

function ringPositions(radius, startNumber) {
  return Array.from({ length: RING_COUNT }, (_, i) => {
    // Twelve o'clock first, then clockwise. Rings are aligned rather than
    // interleaved so the parcels form readable radial spokes.
    const angle = -Math.PI / 2 + (i * Math.PI * 2) / RING_COUNT;
    const hour = (i * 12) / RING_COUNT;
    return {
      number: String(startNumber + i).padStart(2, '0'),
      ring: radius === INNER_RADIUS ? 'inner' : 'outer',
      clock: `${hour === 0 ? 12 : hour} o'clock`,
      x: Math.cos(angle) * radius,
      z: Math.sin(angle) * radius,
    };
  });
}

export const PARCEL_POSITIONS = [
  { number: '01', ring: 'centre', clock: 'centre', x: 0, z: 0, landmark: true },
  ...ringPositions(INNER_RADIUS, 2),
  ...ringPositions(OUTER_RADIUS, 14),
];

export const PARCEL_POSITION_BY_NUMBER = new Map(
  PARCEL_POSITIONS.map((p) => [p.number, p]),
);

/** Sanity: every position must sit inside the hex with room for its object. */
export function validateGeometry(objectRadius = 0.8) {
  const apothem = (TILE_RADIUS * Math.sqrt(3)) / 2;
  const problems = [];
  for (const p of PARCEL_POSITIONS) {
    if (Math.hypot(p.x, p.z) + objectRadius > apothem) {
      problems.push(`${p.number} overflows the hex edge`);
    }
  }
  return problems;
}

// ---------------------------------------------------------------------------
// The portfolio file. This is user-editable data, so it is validated loudly:
// a typo here should say what is wrong, not silently draw an empty city.
// ---------------------------------------------------------------------------

const CONFIG_PATH = path.join(ROOT, 'config', 'portfolio.json');

// The real property roster and regional names are business data, so they live
// in data/ (gitignored) and override the tracked template. The repository keeps
// the structure; your portfolio stays on your machine.
const LOCAL_PATH = path.join(ROOT, 'data', 'portfolio.local.json');

export function loadPortfolio() {
  if (!fs.existsSync(CONFIG_PATH)) {
    throw new Error(`Portfolio file not found at ${CONFIG_PATH}`);
  }

  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  } catch (err) {
    throw new Error(`config/portfolio.json is not valid JSON — ${err.message}`);
  }

  if (fs.existsSync(LOCAL_PATH)) {
    try {
      const local = JSON.parse(fs.readFileSync(LOCAL_PATH, 'utf8'));
      if (local.region) raw.region = local.region;
      if (local.neighbourhoods?.length) raw.neighbourhoods = local.neighbourhoods;
      if (local.properties?.length) raw.properties = local.properties;
    } catch (err) {
      throw new Error(`data/portfolio.local.json is not valid JSON — ${err.message}`);
    }
  }

  const errors = [];
  const neighbourhoods = raw.neighbourhoods ?? [];
  const names = new Set(neighbourhoods.map((n) => n.name));

  if (!neighbourhoods.length) errors.push('no neighbourhoods defined');
  if (!(raw.properties ?? []).length) errors.push('no properties defined');

  for (const property of raw.properties ?? []) {
    if (!property.name) errors.push('a property has no name');
    if (!names.has(property.neighbourhood)) {
      errors.push(
        `property "${property.name}" is in neighbourhood "${property.neighbourhood}", which is not defined`,
      );
    }
  }

  const parcels = raw.parcels ?? {};
  for (const number of Object.keys(parcels)) {
    if (!PARCEL_POSITION_BY_NUMBER.has(number)) {
      errors.push(`parcel "${number}" is not a valid position (01–25)`);
    }
    if (parcels[number].assigned && !parcels[number].label) {
      errors.push(`parcel ${number} is marked assigned but has no label`);
    }
  }

  for (const [item, mapping] of Object.entries(raw.lineItems ?? {})) {
    if (!PARCEL_POSITION_BY_NUMBER.has(mapping.parcel)) {
      errors.push(`line item "${item}" maps to parcel "${mapping.parcel}", which is not a position`);
    } else if (!parcels[mapping.parcel]?.assigned) {
      errors.push(`line item "${item}" maps to parcel ${mapping.parcel}, which is not marked assigned`);
    }
  }

  const geometry = validateGeometry();
  errors.push(...geometry);

  if (errors.length) {
    throw new Error(`config/portfolio.json:\n  - ${errors.join('\n  - ')}`);
  }

  return {
    region: raw.region ?? 'Region',
    neighbourhoods,
    properties: raw.properties,
    parcels,
    lineItems: raw.lineItems ?? {},
    townCentre: raw.townCentre ?? null,
    /** Assigned parcels, in position order. */
    assigned: Object.entries(parcels)
      .filter(([, p]) => p.assigned)
      .map(([number, p]) => ({ number, ...p, ...PARCEL_POSITION_BY_NUMBER.get(number) }))
      .sort((a, b) => a.number.localeCompare(b.number)),
    /** Positions with nothing on them yet — drawn as finished, empty lots. */
    vacant: PARCEL_POSITIONS.filter((p) => !parcels[p.number]?.assigned),
  };
}
