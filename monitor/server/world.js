import { readJson, writeJson } from './config.js';

// ---------------------------------------------------------------------------
// Hex maths. Flat-top hexes. A district is not one tile but a *region* of one
// or more adjacent tiles, which is both what the reference footage shows and
// the only way a district with 40 flows can render without stacking them.
// ---------------------------------------------------------------------------

export const TILE_RADIUS = 9;
const SQRT3 = Math.sqrt(3);
const APOTHEM = (TILE_RADIUS * SQRT3) / 2;
const TILE_GAP = 0.55;
const SLOT_STEP = 2.8;
const SLOT_INSET = 2.0; // keep buildings clear of the plate edge

export function axialToWorld(q, r) {
  const spacing = TILE_RADIUS + TILE_GAP / 2;
  return {
    x: spacing * 1.5 * q,
    z: spacing * SQRT3 * (r + q / 2),
  };
}

const NEIGHBOURS = [
  [1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1],
];

/** Rings of axial coordinates spiralling out from the origin. */
export function spiralCoords(count) {
  const out = [{ q: 0, r: 0 }];
  let ring = 1;
  while (out.length < count) {
    let q = -ring;
    let r = ring;
    for (let side = 0; side < 6 && out.length < count; side++) {
      for (let step = 0; step < ring && out.length < count; step++) {
        out.push({ q, r });
        q += NEIGHBOURS[side][0];
        r += NEIGHBOURS[side][1];
      }
    }
    ring++;
  }
  return out.slice(0, count);
}

function insideHex(x, z, radius) {
  const ax = Math.abs(x);
  const az = Math.abs(z);
  if (az > (radius * SQRT3) / 2) return false;
  return SQRT3 * ax + az <= SQRT3 * radius;
}

/**
 * Building slots inside one tile, ordered centre-outward so a tile fills from
 * its core. Deterministic: slot N is always the same spot, which is what keeps
 * the city recognisable day to day.
 */
export function buildSlots() {
  const usable = TILE_RADIUS - SLOT_INSET;
  const slots = [];
  for (let gx = -8; gx <= 8; gx++) {
    for (let gz = -8; gz <= 8; gz++) {
      // Offset alternate rows: a brick layout looks built, a square grid looks
      // like a spreadsheet.
      const x = gx * SLOT_STEP + (gz % 2 === 0 ? 0 : SLOT_STEP / 2);
      const z = gz * SLOT_STEP * 0.9;
      if (!insideHex(x, z, usable)) continue;
      slots.push({ x, z, d: Math.hypot(x, z) });
    }
  }
  slots.sort((a, b) => a.d - b.d || a.x - b.x || a.z - b.z);
  return slots.map(({ x, z }) => ({ x, z }));
}

export const SLOTS = buildSlots();

// District plate colours, cycled in order. Status carries meaning through the
// buildings; these only separate regions, so no red/green pairing matters here.
const DISTRICT_COLOURS = [
  0x4f7cff, 0xb44ff5, 0x2fd8c3, 0xff5c9d, 0xffa23a,
  0x6ee7ff, 0x9d6bff, 0x3ddc84, 0xff7a5c, 0x5a8dee,
];

const DEFAULT_LAYOUT = { districts: {}, placements: {}, nextDistrictIndex: 0 };

export class WorldLayout {
  constructor() {
    this.state = readJson('world.json', structuredClone(DEFAULT_LAYOUT));
    this.state.districts ??= {};
    this.state.placements ??= {};
    this.state.nextDistrictIndex ??= Object.keys(this.state.districts).length;
    this.dirty = false;
  }

  /** Every axial coordinate already claimed by any district. */
  claimedCoords() {
    const set = new Set();
    for (const d of Object.values(this.state.districts)) {
      for (const t of d.tiles ?? []) set.add(`${t.q},${t.r}`);
    }
    return set;
  }

  /**
   * Take the next free coordinate, preferring one adjacent to the district's
   * existing tiles so a region stays contiguous instead of scattering shards
   * across the map.
   */
  claimCoord(district) {
    const claimed = this.claimedCoords();

    for (const tile of district.tiles ?? []) {
      for (const [dq, dr] of NEIGHBOURS) {
        const key = `${tile.q + dq},${tile.r + dr}`;
        if (!claimed.has(key)) return { q: tile.q + dq, r: tile.r + dr };
      }
    }

    // No free neighbour (or the district has no tiles yet): walk the spiral.
    const spiral = spiralCoords(claimed.size + 12);
    for (const coord of spiral) {
      if (!claimed.has(`${coord.q},${coord.r}`)) return coord;
    }
    return { q: 0, r: 0 };
  }

  district(name) {
    if (!this.state.districts[name]) {
      const index = this.state.nextDistrictIndex++;
      const stub = { name, tiles: [], colour: DISTRICT_COLOURS[index % DISTRICT_COLOURS.length] };
      this.state.districts[name] = stub;
      stub.tiles.push(this.claimCoord(stub));
      this.dirty = true;
    }
    return this.state.districts[name];
  }

  /** Grow the district until it has room for `count` buildings. */
  ensureCapacity(name, count) {
    const district = this.district(name);
    while (district.tiles.length * SLOTS.length < count) {
      district.tiles.push(this.claimCoord(district));
      this.dirty = true;
    }
    return district;
  }

  /** Assign (or recall) a tile+slot for an entity within its district. */
  place(entity) {
    const existing = this.state.placements[entity.id];
    if (existing && existing.district === entity.district) return existing;

    const district = this.district(entity.district);
    const taken = new Set(
      Object.values(this.state.placements)
        .filter((p) => p.district === entity.district)
        .map((p) => `${p.tile}:${p.slot}`),
    );

    let placement = null;
    outer: for (let tile = 0; tile < district.tiles.length; tile++) {
      for (let slot = 0; slot < SLOTS.length; slot++) {
        if (!taken.has(`${tile}:${slot}`)) {
          placement = { district: entity.district, tile, slot };
          break outer;
        }
      }
    }

    if (!placement) {
      // Every tile is full — grow the region and take the first slot of the
      // new tile.
      district.tiles.push(this.claimCoord(district));
      placement = { district: entity.district, tile: district.tiles.length - 1, slot: 0 };
      this.dirty = true;
    }

    this.state.placements[entity.id] = placement;
    this.dirty = true;
    return placement;
  }

  /** Drop placements for entities that no longer exist, freeing their slots. */
  prune(liveIds) {
    for (const id of Object.keys(this.state.placements)) {
      if (!liveIds.has(id)) {
        delete this.state.placements[id];
        this.dirty = true;
      }
    }
  }

  save() {
    if (!this.dirty) return;
    writeJson('world.json', this.state);
    this.dirty = false;
  }

  /** Everything the client needs to draw the ground plan. */
  describe() {
    return {
      tileRadius: TILE_RADIUS,
      apothem: APOTHEM,
      slots: SLOTS,
      districts: Object.values(this.state.districts).map((d) => {
        const tiles = d.tiles.map((t) => ({ ...t, ...axialToWorld(t.q, t.r) }));
        return {
          name: d.name,
          colour: d.colour,
          tiles,
          // Label anchor: the centroid of the region, not of one tile.
          x: tiles.reduce((s, t) => s + t.x, 0) / tiles.length,
          z: tiles.reduce((s, t) => s + t.z, 0) / tiles.length,
        };
      }),
    };
  }
}
