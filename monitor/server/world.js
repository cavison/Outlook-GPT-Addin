import { readJson, writeJson } from './config.js';
import { TILE_RADIUS, PARCEL_POSITIONS, PARCEL_POSITION_BY_NUMBER } from './parcels.js';

// ---------------------------------------------------------------------------
// Hex maths. Flat-top hexes. A district is not one tile but a *region* of one
// or more adjacent tiles, which is both what the reference footage shows and
// the only way a district with 40 flows can render without stacking them.
// ---------------------------------------------------------------------------

export { TILE_RADIUS };
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
export function buildSlots(step = SLOT_STEP, inset = SLOT_INSET) {
  const usable = TILE_RADIUS - inset;
  const span = Math.ceil(usable / step) + 1;
  const slots = [];
  for (let gx = -span; gx <= span; gx++) {
    for (let gz = -span; gz <= span; gz++) {
      // Offset alternate rows: a brick layout looks built, a square grid looks
      // like a spreadsheet.
      const x = gx * step + (gz % 2 === 0 ? 0 : step / 2);
      const z = gz * step * 0.9;
      if (!insideHex(x, z, usable)) continue;
      slots.push({ x, z, d: Math.hypot(x, z) });
    }
  }
  slots.sort((a, b) => a.d - b.d || a.x - b.x || a.z - b.z);
  return slots.map(({ x, z }) => ({ x, z }));
}

// Two grid densities. A district of landmark structures (flows-as-towers,
// properties-as-houses) uses the coarse grid; a district of small repeated
// units — hundreds of them — uses the fine one, so a large fleet reads as a
// field of infrastructure instead of swallowing the map.
export const SLOTS = buildSlots();
export const SLOTS_DENSE = buildSlots(1.2, 1.3);

export const SLOT_GRIDS = { normal: SLOTS, dense: SLOTS_DENSE };

export function slotsFor(density) {
  return SLOT_GRIDS[density] ?? SLOTS;
}

// District plate colours, cycled in order. Status carries meaning through the
// buildings; these only separate regions, so no red/green pairing matters here.
const DISTRICT_COLOURS = [
  0x4f7cff, 0xb44ff5, 0x2fd8c3, 0xff5c9d, 0xffa23a,
  0x6ee7ff, 0x9d6bff, 0x3ddc84, 0xff7a5c, 0x5a8dee,
];

const DEFAULT_LAYOUT = {
  districts: {}, placements: {}, nextDistrictIndex: 0, groupColours: {}, colourCursor: 0,
};

export class WorldLayout {
  constructor() {
    this.state = readJson('world.json', structuredClone(DEFAULT_LAYOUT));
    this.state.districts ??= {};
    this.state.placements ??= {};
    this.state.nextDistrictIndex ??= Object.keys(this.state.districts).length;
    this.state.groupColours ??= {};
    this.state.colourCursor ??= 0;
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

    // A property has no tiles of its own yet: sit it next to its neighbours, so
    // one regional's whole book reads as a single contiguous patch.
    if (district.group) {
      const siblings = Object.values(this.state.districts).filter(
        (d) => d.group === district.group && d.name !== district.name,
      );
      for (const sibling of siblings) {
        for (const tile of sibling.tiles ?? []) {
          for (const [dq, dr] of NEIGHBOURS) {
            const key = `${tile.q + dq},${tile.r + dr}`;
            if (!claimed.has(key)) return { q: tile.q + dq, r: tile.r + dr };
          }
        }
      }
    }

    // No free neighbour (or the district has no tiles yet): walk the spiral.
    const spiral = spiralCoords(claimed.size + 12);
    for (const coord of spiral) {
      if (!claimed.has(`${coord.q},${coord.r}`)) return coord;
    }
    return { q: 0, r: 0 };
  }

  district(name, density = 'normal', group = null) {
    if (!this.state.districts[name]) {
      const index = this.state.nextDistrictIndex++;
      // Properties in the same neighbourhood share a plate colour; the colour
      // identifies the regional's patch, not the individual property.
      // One shared cursor across groups and ungrouped districts, so a
      // neighbourhood can never collide with the Town Centre.
      const nextColour = () =>
        DISTRICT_COLOURS[this.state.colourCursor++ % DISTRICT_COLOURS.length];
      let colour;
      if (group) {
        if (this.state.groupColours[group] === undefined) {
          this.state.groupColours[group] = nextColour();
        }
        colour = this.state.groupColours[group];
      } else {
        colour = nextColour();
      }
      const stub = { name, tiles: [], density, group, colour };
      this.state.districts[name] = stub;
      stub.tiles.push(this.claimCoord(stub));
      this.dirty = true;
    }
    const existing = this.state.districts[name];
    // A district that starts sparse and later fills with small repeated units
    // re-grids itself rather than sprawling across the map.
    if (density === 'dense' && existing.density !== 'dense') {
      existing.density = 'dense';
      this.dirty = true;
    }
    existing.density ??= 'normal';
    if (group && !existing.group) { existing.group = group; this.dirty = true; }
    return existing;
  }

  /** Grow the district until it has room for `count` buildings. */
  ensureCapacity(name, count, density = 'normal', group = null) {
    const district = this.district(name, density, group);
    const perTile = slotsFor(district.density).length;
    while (district.tiles.length * perTile < count) {
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

    // A parcel is a fixed address, not a slot to be handed out. Position 04 is
    // work orders on every property, forever.
    const parcel = entity.encode?.parcel;
    if (parcel) {
      if (!PARCEL_POSITION_BY_NUMBER.has(parcel)) {
        throw new Error(`entity ${entity.id} claims parcel "${parcel}", which is not a position`);
      }
      const placement = { district: entity.district, tile: 0, parcel };
      this.state.placements[entity.id] = placement;
      this.dirty = true;
      return placement;
    }

    const perTile = slotsFor(district.density).length;
    const taken = new Set(
      Object.values(this.state.placements)
        .filter((p) => p.district === entity.district)
        .map((p) => `${p.tile}:${p.slot}`),
    );

    let placement = null;
    outer: for (let tile = 0; tile < district.tiles.length; tile++) {
      for (let slot = 0; slot < perTile; slot++) {
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
      slotGrids: SLOT_GRIDS,
      parcels: PARCEL_POSITIONS,
      districts: Object.values(this.state.districts).map((d) => {
        const tiles = d.tiles.map((t) => ({ ...t, ...axialToWorld(t.q, t.r) }));
        return {
          name: d.name,
          colour: d.colour,
          density: d.density ?? 'normal',
          group: d.group ?? null,
          tiles,
          // Label anchor: the centroid of the region, not of one tile.
          x: tiles.reduce((s, t) => s + t.x, 0) / tiles.length,
          z: tiles.reduce((s, t) => s + t.z, 0) / tiles.length,
        };
      }),
    };
  }
}
