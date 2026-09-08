#!/usr/bin/env node
// Build the shareable single-file page.
//
//   node scripts/build-artifact.mjs [--out dist/colony.html] [--stamp "..."]
//
// The artifact is a snapshot: one HTML file, no server, no network beyond a CDN
// script tag. It exists so the map can be handed to someone who does not have
// this repository checked out.
//
// It used to be assembled by hand, which meant nobody could tell what it had
// been built from or reproduce it. Now it comes from the running server's own
// state, and the SCORING is imported from public/js/portfolio.js — the exact
// module the desktop app renders from. Two implementations of "how bad is this
// property" would have drifted apart by the second change.
//
// The output carries real property names, real regionals and real figures, so
// it is written to dist/, which is gitignored. Publishing it is a decision, not
// a side effect of building it.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildRoster } from '../public/js/portfolio.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const args = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i === -1 ? fallback : args[i + 1];
};

const source = flag('from', 'http://localhost:4310/api/state');
const out = path.resolve(flag('out', path.join(ROOT, 'dist', 'colony.html')));

let snapshot;
try {
  snapshot = await (await fetch(source)).json();
} catch (err) {
  console.error(`\n  Could not read ${source} — ${err.message}`);
  console.error('  Start the server first:  npm start\n');
  process.exit(1);
}

if (!snapshot.kpis || !snapshot.entities?.length) {
  console.error('\n  The server returned no KPI registry or no entities. Nothing to build.\n');
  process.exit(1);
}

// -- project the snapshot into the compact shape the page reads ---------------

const entities = new Map(snapshot.entities.map((e) => [e.id, e]));
const { kpis, rows } = buildRoster(entities, snapshot.kpis);

// Hex coordinates come from the server, which packs each regional's book into
// one contiguous patch. Re-deriving the layout in the page would let it and the
// desktop app disagree about where a property sits — and the whole point of a
// map is that a property is always in the same place.
const coordOf = new Map();
for (const d of snapshot.layout.districts) {
  coordOf.set(d.name, d.tiles[0]);
}

const townName = snapshot.layout.districts.find((d) => d.tiles.length > 1 && !d.group)?.name;
const town = townName
  ? snapshot.layout.districts.find((d) => d.name === townName).tiles.map((t) => ({ q: t.q, r: t.r }))
  : [];

const properties = [];
for (const row of rows) {
  const coord = coordOf.get(row.name);
  if (!coord) continue;

  const cells = {};
  for (const cell of row.cells) {
    // A KPI nobody has connected yet gets no object on the map: the parcel's
    // faint site marking is already drawn, so an unbuilt KPI reads as ground
    // held for it. Nine of those across 185 properties would otherwise put
    // 1,665 markers on the map and bury the ones that report.
    if (cell.state === 'wait') continue;
    const m = cell.entity?.metrics ?? {};
    cells[cell.kpi.id] = {
      st: cell.state,
      s: Number(cell.severity.toFixed(4)),
      h: headline(cell),
      d: cell.detail || '',
      ...(m.variance != null ? { v: m.variance } : {}),
    };
  }

  properties.push({
    n: row.name,
    g: row.neighbourhood,
    q: coord.q,
    r: coord.r,
    ...(row.director ? { dir: row.director } : {}),
    hp: row.hp,
    sev: Number(row.severity.toFixed(4)),
    va: Math.round(row.variance),
    gaps: row.counts.gap,
    reporting: row.reporting,
    ...(row.worst && row.worst.severity >= 0.28 ? { worst: row.worst.kpi.label } : {}),
    c: cells,
  });
}

const period = snapshot.entities.find((e) => e.metrics?.period)?.metrics.period ?? '';
const stamp =
  flag('stamp') ??
  `${properties.length} properties · ${kpis.length} KPI slots · built ${new Date().toISOString().slice(0, 10)}`;

const payload = {
  stamp,
  period,
  regions: [...new Set(properties.map((p) => p.g))].sort(),
  kpis: kpis.map((k) => ({
    id: k.id, parcel: k.parcel, label: k.label, icon: k.icon,
    kind: k.kind, priority: k.priority,
  })),
  town,
  properties,
};

// -- assemble -----------------------------------------------------------------

const page = fs.readFileSync(path.join(ROOT, 'artifact', 'page.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'artifact', 'app.js'), 'utf8');

// `</script>` inside the JSON would close the tag early. This is data going into
// a script element, so it has to be escaped for that context, not for HTML.
const json = JSON.stringify(payload).replace(/<\//g, '<\\/');

// The artifact host wraps this in a head that declares UTF-8, but a copy saved
// and opened over file:// has no such header and would decode the property
// names and separators as latin-1. One meta costs nothing and fixes that.
const html = `<meta charset="utf-8">
${page}
<script>window.__CITY__ = ${json};</script>
<script>
${app}
</script>
`;

fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, html);

const kb = Math.round(html.length / 1024);
console.log(`\n  Built ${path.relative(process.cwd(), out)}  (${kb} KB)`);
console.log(`  ${properties.length} properties · ${payload.regions.length} regionals · ${kpis.length} KPI slots`);

const reporting = properties.reduce((s, p) => s + p.reporting, 0);
const gaps = properties.reduce((s, p) => s + p.gaps, 0);
console.log(`  ${reporting} readings · ${gaps} stopped feeds`);
console.log('\n  This file carries real property names and figures. dist/ is gitignored;');
console.log('  publishing it anywhere is a separate, deliberate step.\n');

function headline(cell) {
  if (cell.state === 'gap') return 'no data';
  if (cell.state === 'na') return 'n/a';
  const raw = cell.entity?.encode?.severity?.raw;
  return raw ?? cell.entity?.detail ?? '';
}
