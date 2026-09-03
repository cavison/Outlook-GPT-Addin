// Where each hex goes.
//
// The incremental approach this replaces grew every neighbourhood from whatever
// coordinate happened to be free, which packed tightly but let two regionals'
// books end up touching. You cannot see where one book stops and the next
// starts if they share an edge.
//
// So the layout is planned globally instead:
//
//   * the Town Centre holds the middle, as a compact block of blank hexes
//   * each regional grows outward from its own bearing around that centre
//   * NO hex may touch a hex belonging to a different regional
//
// That last rule is what produces the gap: an unclaimed ring of hexes falls out
// of the constraint rather than being drawn in, so it is exactly one hex wide
// wherever two books come closest.

const NEIGHBOURS = [
  [1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1],
];

const key = (q, r) => `${q},${r}`;

/** Axial distance in hex steps. */
export function hexDistance(a, b) {
  return (Math.abs(a.q - b.q) + Math.abs(a.q + a.r - b.q - b.r) + Math.abs(a.r - b.r)) / 2;
}

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

/** Flat-top axial to world, matching the renderer's spacing. */
function toWorld(q, r, spacing) {
  return { x: spacing * 1.5 * q, z: spacing * Math.sqrt(3) * (r + q / 2) };
}

const bearing = (coord, spacing) => {
  const w = toWorld(coord.q, coord.r, spacing);
  return Math.atan2(w.z, w.x);
};

/** Smallest absolute angle between two bearings. */
function angleGap(a, b) {
  let d = Math.abs(a - b) % (Math.PI * 2);
  return d > Math.PI ? Math.PI * 2 - d : d;
}

/**
 * Plan the whole map.
 *
 * @param {Array<{name: string, group: string|null}>} districts
 * @param {object} options
 * @returns {{ town: Array, byDistrict: Map<string, {q,r}> }}
 */
export function planLayout(districts, { townTiles = 10, spacing = 9.275, townDistrict = null } = {}) {
  const owner = new Map();               // "q,r" -> region name, or '__town__'
  const byDistrict = new Map();

  // 1. The Town Centre takes the middle as one compact block.
  const town = spiralCoords(townTiles);
  for (const c of town) owner.set(key(c.q, c.r), '__town__');

  // 2. Group the properties by regional, biggest book first so the crowded
  //    ones choose their ground before the small ones fill in around them.
  const regions = new Map();
  for (const d of districts) {
    if (!d.group) continue;
    if (!regions.has(d.group)) regions.set(d.group, []);
    regions.get(d.group).push(d.name);
  }
  const ordered = [...regions.entries()].sort((a, b) => b[1].length - a[1].length);

  // 3. A bearing per regional, evenly spread, so books radiate rather than
  //    stacking on one side.
  const bearings = new Map();
  ordered.forEach(([region], i) => {
    bearings.set(region, (i * Math.PI * 2) / ordered.length);
  });

  const touchesOtherRegion = (coord, region) => {
    for (const [dq, dr] of NEIGHBOURS) {
      const o = owner.get(key(coord.q + dq, coord.r + dr));
      if (o && o !== region && o !== '__town__') return true;
    }
    return false;
  };

  // A generous search field — the separation gaps mean the map needs far more
  // coordinates than it has properties.
  const field = spiralCoords(districts.length * 9 + 400);

  for (const [region, names] of ordered) {
    const want = names.length;
    const placed = [];
    const aim = bearings.get(region);

    // Seed: the free hex closest to this regional's bearing, just outside the
    // Town Centre, that is not already rubbing against another book.
    let seed = null;
    let best = Infinity;
    for (const c of field) {
      if (owner.has(key(c.q, c.r))) continue;
      const dist = hexDistance({ q: 0, r: 0 }, c);
      if (dist < 2) continue;
      if (touchesOtherRegion(c, region)) continue;
      // Prefer close to the centre and on-bearing; the angle dominates so the
      // books do not all crowd the same arc.
      const score = angleGap(bearing(c, spacing), aim) * 12 + dist;
      if (score < best) { best = score; seed = c; }
    }
    if (!seed) continue;

    owner.set(key(seed.q, seed.r), region);
    placed.push(seed);

    // Grow: always take the legal hex that keeps the book most compact.
    while (placed.length < want) {
      let pick = null;
      let pickScore = Infinity;
      const seen = new Set();

      for (const t of placed) {
        for (const [dq, dr] of NEIGHBOURS) {
          const c = { q: t.q + dq, r: t.r + dr };
          const k = key(c.q, c.r);
          if (seen.has(k) || owner.has(k)) continue;
          seen.add(k);
          if (touchesOtherRegion(c, region)) continue;
          // Compactness: distance to the book's centre of mass.
          const cx = placed.reduce((s, p) => s + p.q, 0) / placed.length;
          const cy = placed.reduce((s, p) => s + p.r, 0) / placed.length;
          const score = Math.hypot(c.q - cx, c.r - cy);
          if (score < pickScore) { pickScore = score; pick = c; }
        }
      }

      if (!pick) break; // boxed in; the remaining properties fall through below
      owner.set(key(pick.q, pick.r), region);
      placed.push(pick);
    }

    names.forEach((name, i) => {
      if (placed[i]) byDistrict.set(name, placed[i]);
    });

    // Anything that could not be placed under the separation rule still needs a
    // hex — better a slightly tighter map than a property that vanishes.
    for (let i = placed.length; i < names.length; i++) {
      const spot = field.find((c) => !owner.has(key(c.q, c.r)));
      if (!spot) break;
      owner.set(key(spot.q, spot.r), region);
      byDistrict.set(names[i], spot);
    }
  }

  // 4. The Town Centre gets the whole middle block. Any other district without
  //    a regional (a shared utility district, say) gets its own ground clear of
  //    the books rather than being wedged between them.
  for (const d of districts) {
    if (d.group) continue;
    if (townDistrict && d.name === townDistrict) { byDistrict.set(d.name, town[0]); continue; }
    const spot = field.find((c) => {
      if (owner.has(key(c.q, c.r))) return false;
      for (const [dq, dr] of NEIGHBOURS) {
        const o = owner.get(key(c.q + dq, c.r + dr));
        if (o && o !== '__town__') return false;
      }
      return true;
    });
    if (spot) { owner.set(key(spot.q, spot.r), '__other__'); byDistrict.set(d.name, spot); }
  }

  return { town, byDistrict, owner };
}

/** How well the plan separated the books — used by the tests. */
export function auditPlan(districts, plan) {
  const byRegion = new Map();
  for (const d of districts) {
    if (!d.group) continue;
    const c = plan.byDistrict.get(d.name);
    if (!c) continue;
    if (!byRegion.has(d.group)) byRegion.set(d.group, []);
    byRegion.get(d.group).push(c);
  }

  const report = [];
  for (const [region, coords] of byRegion) {
    const own = new Set(coords.map((c) => key(c.q, c.r)));
    let touchingOwn = 0;
    let touchingOther = 0;
    for (const c of coords) {
      let ownNeighbour = false;
      for (const [dq, dr] of NEIGHBOURS) {
        const k = key(c.q + dq, c.r + dr);
        if (own.has(k)) ownNeighbour = true;
        else {
          const o = plan.owner.get(k);
          if (o && o !== region && o !== '__town__') touchingOther++;
        }
      }
      if (ownNeighbour) touchingOwn++;
    }
    report.push({
      region,
      count: coords.length,
      contiguity: coords.length ? touchingOwn / coords.length : 0,
      adjacentToOtherRegions: touchingOther,
    });
  }
  return report;
}
