#!/usr/bin/env node
// Import a monthly Actuals vs Budget workbook into the map.
//
//   node scripts/import-financials.mjs <file.xlsx> [--sheet DashboardData]
//
// Reads the tidy tab (Regional LED / Property / Budget Line Item / YTD Actual /
// YTD Budget / Variance F/(U)) and writes two files, both into data/, which is
// gitignored:
//
//   financials.json      the figures, plus a severity scale per line item
//   portfolio.local.json the property roster and regional names
//
// Property-level figures, the property list and named regionals are all
// business data and none of it belongs in a repository. config/portfolio.json
// stays a neutral template holding only the parcel structure.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import xlsx from 'xlsx';
import { buildScales } from '../server/severity.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith('--'));
const sheetArg = args.indexOf('--sheet');
const sheetName = sheetArg !== -1 ? args[sheetArg + 1] : null;

if (!file) {
  console.error('Usage: node scripts/import-financials.mjs <file.xlsx> [--sheet DashboardData]');
  process.exit(1);
}
if (!fs.existsSync(file)) {
  console.error(`No such file: ${file}`);
  process.exit(1);
}

const COLUMNS = {
  regional: ['regional led', 'regional', 'led'],
  property: ['property', 'community'],
  item: ['budget line item', 'line item', 'account'],
  actual: ['ytd actual', 'actual'],
  budget: ['ytd budget', 'budget'],
  variance: ['variance f/(u)', 'variance', 'variance f/u'],
};

const norm = (v) => String(v ?? '').trim().toLowerCase();

/** Find the header row rather than assuming it — these exports carry a title block. */
function locateHeader(grid) {
  for (let r = 0; r < Math.min(grid.length, 40); r++) {
    const cells = grid[r].map(norm);
    const hasProperty = cells.some((c) => COLUMNS.property.includes(c));
    const hasItem = cells.some((c) => COLUMNS.item.includes(c));
    if (hasProperty && hasItem) return r;
  }
  return -1;
}

function mapColumns(headerCells) {
  const index = {};
  headerCells.forEach((cell, i) => {
    const c = norm(cell);
    for (const [key, names] of Object.entries(COLUMNS)) {
      if (index[key] === undefined && names.includes(c)) index[key] = i;
    }
  });
  return index;
}

const book = xlsx.readFile(file, { cellDates: false });
const sheet =
  book.Sheets[sheetName ?? ''] ??
  book.Sheets[book.SheetNames.find((n) => norm(n).replace(/\s+/g, '') === 'dashboarddata')] ??
  null;

if (!sheet) {
  console.error(
    `Could not find the data sheet. Sheets present: ${book.SheetNames.join(', ')}\n` +
      'Pass one with --sheet "<name>".',
  );
  process.exit(1);
}

const grid = xlsx.utils.sheet_to_json(sheet, { header: 1, blankrows: false, defval: null });
const headerRow = locateHeader(grid);
if (headerRow === -1) {
  console.error('Could not find a header row containing Property and Budget Line Item.');
  process.exit(1);
}

const index = mapColumns(grid[headerRow]);
const missing = ['property', 'item', 'variance'].filter((k) => index[k] === undefined);
if (missing.length) {
  console.error(`Header is missing required column(s): ${missing.join(', ')}`);
  console.error(`Found: ${grid[headerRow].filter(Boolean).join(' | ')}`);
  process.exit(1);
}

const num = (v) => {
  if (typeof v === 'number') return v;
  const parsed = Number(String(v ?? '').replace(/[$,\s]/g, '').replace(/^\((.*)\)$/, '-$1'));
  return Number.isFinite(parsed) ? parsed : 0;
};

const rows = [];
for (let r = headerRow + 1; r < grid.length; r++) {
  const line = grid[r];
  const property = line[index.property];
  const item = line[index.item];
  if (!property || !item) continue;
  rows.push({
    regional: String(line[index.regional] ?? 'Unassigned').trim() || 'Unassigned',
    property: String(property).trim(),
    item: String(item).trim(),
    actual: num(line[index.actual]),
    budget: num(line[index.budget]),
    variance: num(line[index.variance]),
  });
}

if (!rows.length) {
  console.error('Header found, but no data rows below it.');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Merges: properties the workbook reports separately that belong on one hex.
// ---------------------------------------------------------------------------
const mergePath = path.join(ROOT, 'data', 'merges.json');
let applied = [];
if (fs.existsSync(mergePath)) {
  let spec;
  try {
    spec = JSON.parse(fs.readFileSync(mergePath, 'utf8'));
  } catch (err) {
    console.error(`data/merges.json is not valid JSON — ${err.message}`);
    process.exit(1);
  }

  const present = new Set(rows.map((r) => r.property));
  const problems = [];
  for (const m of spec.merges ?? []) {
    if (!present.has(m.from)) problems.push(`"${m.from}" (from) is not in the workbook`);
    if (!present.has(m.into)) problems.push(`"${m.into}" (into) is not in the workbook`);
  }
  if (problems.length) {
    // A merge that silently does nothing leaves two half-properties on the map
    // and no way to notice, so an unmatched name stops the import.
    console.error('\n  Merge targets not found:');
    for (const p of problems) console.error(`    - ${p}`);
    console.error('\n  Names must match the workbook exactly. Nothing was written.\n');
    process.exit(1);
  }

  const into = new Map((spec.merges ?? []).map((m) => [m.from, m.into]));
  if (into.size) {
    const regionalOf = new Map();
    for (const r of rows) if (!into.has(r.property)) regionalOf.set(r.property, r.regional);

    const merged = new Map();
    for (const r of rows) {
      const target = into.get(r.property) ?? r.property;
      const key = `${target}\u0000${r.item}`;
      const existing = merged.get(key);
      if (!existing) {
        merged.set(key, { ...r, property: target, regional: regionalOf.get(target) ?? r.regional });
      } else {
        // Variance is budget - actual, so it sums as cleanly as its parts do.
        existing.actual += r.actual;
        existing.budget += r.budget;
        existing.variance += r.variance;
      }
    }
    applied = [...into].map(([from, target]) => ({ from, into: target }));
    rows.length = 0;
    rows.push(...merged.values());
  }
}

// Sanity-check the sign convention rather than trusting it: variance should be
// budget - actual. If a future export flips it, every pillar would be upside
// down and nothing else would complain.
let checked = 0;
let mismatched = 0;
for (const row of rows) {
  if (!row.actual && !row.budget) continue;
  checked++;
  if (Math.abs(row.budget - row.actual - row.variance) > 1) mismatched++;
}
const flipped = checked > 0 && mismatched / checked > 0.5;
if (flipped) {
  console.warn(
    `\n  WARNING: variance does not look like (budget - actual) in ${mismatched}/${checked} rows.`,
  );
  console.warn('  Check the sign convention before trusting the map.\n');
}

const scales = buildScales(rows);
const properties = [...new Set(rows.map((r) => r.property))].sort();
const regionals = [...new Set(rows.map((r) => r.regional))].sort();

const payload = {
  importedAt: new Date().toISOString(),
  source: path.basename(file),
  rowCount: rows.length,
  scales,
  rows,
};

fs.mkdirSync(path.join(ROOT, 'data'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'data', 'financials.json'), JSON.stringify(payload, null, 2));

// The roster goes to data/, not into the tracked config: real property names
// and named regionals are business data and do not belong in a repository.
const localPath = path.join(ROOT, 'data', 'portfolio.local.json');
fs.writeFileSync(
  localPath,
  `${JSON.stringify(
    {
      region: `${path.basename(file, path.extname(file))}`,
      neighbourhoods: regionals.map((name) => ({ name, manager: name })),
      properties: properties.map((name) => ({
        name,
        neighbourhood: rows.find((r) => r.property === name).regional,
      })),
    },
    null,
    2,
  )}\n`,
);

console.log(`\n  Imported ${rows.length} rows from ${path.basename(file)}`);
for (const m of applied) console.log(`  Merged "${m.from}" into "${m.into}"`);
console.log(`  ${properties.length} properties · ${regionals.length} regionals`);
console.log('\n  Severity scale per line item (90th percentile of unfavourable variance):');
for (const [item, scale] of Object.entries(scales).sort((a, b) => b[1] - a[1])) {
  console.log(`    $${String(Math.round(scale)).padStart(7)}   ${item}`);
}
console.log('\n  Wrote data/financials.json and data/portfolio.local.json');
console.log('  Both are gitignored — figures, property names and regionals stay off GitHub.\n');
