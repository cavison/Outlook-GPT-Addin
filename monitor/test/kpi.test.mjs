// The ingest contract. Every source goes through validateBatch and scoreReading,
// so a mistake here is a mistake on every KPI at once.

import assert from 'node:assert/strict';
import { validateBatch, scoreReading, scaleFor, isStale, parseBool } from '../server/kpi.js';

let passed = 0;
let failed = 0;
function test(name, fn) {
  try { fn(); console.log(`  ok   ${name}`); passed++; }
  catch (err) { console.log(`  FAIL ${name}\n       ${err.message}`); failed++; }
}
function group(name) { console.log(name); }

const REGISTRY = {
  payroll: { id: 'payroll', label: 'Payroll', kind: 'variance', parcel: '02', cadence: 'monthly', staleAfterDays: 45, ceiling: 1 },
  fuel: { id: 'fuel', label: 'Fuel', kind: 'variance', parcel: '05', cadence: 'monthly', staleAfterDays: 45, ceiling: 0.6 },
  signage: { id: 'signage', label: 'Signage', kind: 'ratio', parcel: '10', cadence: 'daily', staleAfterDays: 3, ceiling: 1, target: 1 },
  posts: { id: 'posts', label: 'Posts', kind: 'count', parcel: '11', cadence: 'weekly', staleAfterDays: 10, ceiling: 1, target: 3, direction: 'at-least' },
  overtime: { id: 'overtime', label: 'Overtime', kind: 'count', parcel: '12', cadence: 'weekly', staleAfterDays: 10, ceiling: 1, target: 10, direction: 'at-most' },
  menu: { id: 'menu', label: 'Menu', kind: 'boolean', parcel: '15', cadence: 'monthly', staleAfterDays: 45, ceiling: 1 },
  director: { id: 'director', label: 'Director', kind: 'label', parcel: null, cadence: 'quarterly', staleAfterDays: 120, ceiling: 1 },
};

const NOW = new Date('2026-09-08T12:00:00Z');
const batchOf = (kpi, rows, asOf = NOW.toISOString()) => ({ kpi, asOf, source: 'test', rows });

group('validation');

test('a good batch is accepted and normalised', () => {
  const r = validateBatch(batchOf('signage', [{ property: 'A', value: 3, total: 4 }]), REGISTRY, { now: NOW });
  assert.equal(r.ok, true);
  assert.equal(r.batch.rows[0].value, 3);
  assert.equal(r.batch.rows[0].total, 4);
  assert.ok(r.batch.receivedAt);
});

test('an unregistered KPI is refused', () => {
  const r = validateBatch(batchOf('nope', [{ property: 'A', value: 1 }]), REGISTRY, { now: NOW });
  assert.equal(r.ok, false);
  assert.match(r.errors[0], /unknown kpi/);
});

test('a ratio without a total is refused', () => {
  // Silently treating a missing total as 1 would report every property as
  // catastrophically short of its screens.
  const r = validateBatch(batchOf('signage', [{ property: 'A', value: 3 }]), REGISTRY, { now: NOW });
  assert.equal(r.ok, false);
  assert.match(r.errors[0], /needs a total/);
});

test('a ratio above its total is refused', () => {
  const r = validateBatch(batchOf('signage', [{ property: 'A', value: 9, total: 4 }]), REGISTRY, { now: NOW });
  assert.equal(r.ok, false);
});

test('the same property twice is refused', () => {
  // Last-one-wins would make the map depend on row order.
  const r = validateBatch(
    batchOf('menu', [{ property: 'A', value: 'yes' }, { property: 'A', value: 'no' }]),
    REGISTRY, { now: NOW },
  );
  assert.equal(r.ok, false);
  assert.match(r.errors[0], /twice/);
});

test('a reading from the future is refused', () => {
  const r = validateBatch(
    batchOf('menu', [{ property: 'A', value: 'yes' }], '2027-01-01T00:00:00Z'),
    REGISTRY, { now: NOW },
  );
  assert.equal(r.ok, false);
  assert.match(r.errors[0], /future/);
});

test('not-applicable rows skip value checks', () => {
  const r = validateBatch(
    batchOf('signage', [{ property: 'A', applicable: false, note: 'no screens' }]),
    REGISTRY, { now: NOW },
  );
  assert.equal(r.ok, true);
  assert.equal(r.batch.rows[0].applicable, false);
  assert.equal(r.batch.rows[0].note, 'no screens');
});

test('one bad row rejects the whole batch', () => {
  // Half a batch on the map is worse than none: the half that failed would
  // look like a working feed reporting nothing wrong.
  const r = validateBatch(
    batchOf('menu', [{ property: 'A', value: 'yes' }, { property: 'B', value: 'perhaps' }]),
    REGISTRY, { now: NOW },
  );
  assert.equal(r.ok, false);
});

test('booleans accept the words people actually type', () => {
  for (const yes of ['yes', 'Y', 'true', 1, 'done', 'On File', true]) assert.equal(parseBool(yes), true, String(yes));
  for (const no of ['no', 'N', 'false', 0, 'missing', 'Not Done', false]) assert.equal(parseBool(no), false, String(no));
  assert.equal(parseBool('perhaps'), null);
});

group('scoring');

test('a favourable variance is flat', () => {
  const s = scoreReading({ value: 4200 }, REGISTRY.payroll, { scale: 6666 });
  assert.equal(s.severity, 0);
  assert.match(s.headline, /under/);
});

test('an unfavourable variance scales against its own line', () => {
  const s = scoreReading({ value: -3333 }, REGISTRY.payroll, { scale: 6666 });
  assert.ok(Math.abs(s.severity - 0.5) < 1e-9);
});

test('a ceiling caps a secondary line below full height', () => {
  // Without this, a few hundred dollars of fuel out-shouts a five-figure
  // payroll overrun, because fuel's own scale is tiny.
  const s = scoreReading({ value: -99999 }, REGISTRY.fuel, { scale: 1452 });
  assert.equal(s.severity, 0.6);
});

test('the variance scale is the 90th percentile of unfavourable readings', () => {
  const rows = [
    ...Array.from({ length: 9 }, (_, i) => ({ property: `p${i}`, value: -(i + 1) * 1000 })),
    { property: 'big', value: -500000 },   // an outlier must not set the scale
    { property: 'good', value: 50000 },    // favourable rows do not either
  ];
  const scale = scaleFor({ rows });
  assert.ok(scale > 8000 && scale < 20000, `scale was ${scale}`);
});

test('a scale floor stops a rounding difference reaching full height', () => {
  assert.equal(scaleFor({ rows: [{ property: 'a', value: -1 }] }), 250);
});

test('no unfavourable readings means no scale at all', () => {
  assert.equal(scaleFor({ rows: [{ property: 'a', value: 100 }] }), null);
});

test('a ratio is the shortfall against target', () => {
  assert.equal(scoreReading({ value: 4, total: 4 }, REGISTRY.signage).severity, 0);
  assert.equal(scoreReading({ value: 2, total: 4 }, REGISTRY.signage).severity, 0.5);
  assert.equal(scoreReading({ value: 0, total: 4 }, REGISTRY.signage).severity, 1);
});

test('nothing installed is not applicable, not a failure', () => {
  const s = scoreReading({ value: 0, total: 0 }, REGISTRY.signage);
  assert.equal(s.notApplicable, true);
  assert.equal(s.severity, 0);
});

test('an at-least count misses downward', () => {
  assert.equal(scoreReading({ value: 3 }, REGISTRY.posts).severity, 0);
  assert.equal(scoreReading({ value: 9 }, REGISTRY.posts).severity, 0);
  assert.equal(scoreReading({ value: 0 }, REGISTRY.posts).severity, 1);
});

test('an at-most count misses upward', () => {
  assert.equal(scoreReading({ value: 10 }, REGISTRY.overtime).severity, 0);
  assert.equal(scoreReading({ value: 5 }, REGISTRY.overtime).severity, 0);
  assert.equal(scoreReading({ value: 15 }, REGISTRY.overtime).severity, 0.5);
});

test('a row target overrides the KPI default', () => {
  assert.equal(scoreReading({ value: 3, target: 6 }, REGISTRY.posts).severity, 0.5);
});

test('a boolean is all or nothing', () => {
  assert.equal(scoreReading({ value: true }, REGISTRY.menu).severity, 0);
  assert.equal(scoreReading({ value: false }, REGISTRY.menu).severity, 1);
});

group('staleness');

test('a fresh reading is believed', () => {
  assert.equal(isStale({ asOf: '2026-09-07T00:00:00Z' }, REGISTRY.signage, NOW), false);
});

test('a reading past its cadence window is not', () => {
  // A daily feed that last spoke a week ago has stopped, and its last value
  // must not keep showing green.
  assert.equal(isStale({ asOf: '2026-09-01T00:00:00Z' }, REGISTRY.signage, NOW), true);
});

test('cadence decides the window, so monthly figures survive a month', () => {
  assert.equal(isStale({ asOf: '2026-07-31T00:00:00Z' }, REGISTRY.payroll, NOW), false);
  assert.equal(isStale({ asOf: '2026-06-30T00:00:00Z' }, REGISTRY.payroll, NOW), true);
});

test('an unreadable date is treated as stale', () => {
  assert.equal(isStale({ asOf: 'sometime' }, REGISTRY.payroll, NOW), true);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
