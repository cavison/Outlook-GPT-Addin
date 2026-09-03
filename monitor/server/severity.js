// Turning budget variance into pillar height.
//
// This is the judgement-heavy part of the whole app, so the reasoning is here
// rather than buried in a provider.
//
// The source convention: Variance F/(U) = Budget - Actual.
//   positive -> favourable, came in under budget -> GOOD -> flat
//   negative -> unfavourable, overspent          -> BAD  -> tall
//
// Two obvious scalings were tried against the real July YTD data and both fail:
//
//   Percent of budget. Automotive Gas & Oil reaches 5,122% of budget on a median
//   unfavourable variance of $373. A property $500 over on gas would tower over
//   one $11,777 over on payroll. Worse, 158 of 186 properties have no Automotive
//   Lease budget at all, so the ratio is undefined for most of the portfolio.
//
//   Raw dollars on one shared scale. Payroll swamps everything; gas and oil
//   would never leave the ground even when a property is wildly over on it.
//
// What works is scaling each line item against ITS OWN spread: severity answers
// "how bad is this, for this kind of expense". The reference point is the 90th
// percentile of unfavourable variance for that line item, so the scale is set by
// the data rather than by a number someone made up, and it survives the outliers
// that would wreck a max-based scale.

/** Percentile of a numeric array, nearest-rank. */
export function percentile(values, q) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))));
  return sorted[index];
}

/**
 * One scale per line item, derived from the unfavourable variances present.
 * @param {Array<{item: string, variance: number}>} rows
 */
export function buildScales(rows, { quantile = 0.9 } = {}) {
  const byItem = new Map();
  for (const row of rows) {
    if (row.variance >= 0) continue; // favourable rows do not set the scale
    if (!byItem.has(row.item)) byItem.set(row.item, []);
    byItem.get(row.item).push(Math.abs(row.variance));
  }

  const scales = {};
  for (const [item, magnitudes] of byItem) {
    // A floor keeps a line item where nobody overspent from turning a $1
    // rounding difference into a full-height pillar.
    scales[item] = Math.max(percentile(magnitudes, quantile), 250);
  }
  return scales;
}

/**
 * Severity in 0..1 for one row.
 *
 * `ceiling` lets a line item be capped below full height. The automotive lines
 * are real but secondary, and without a cap their small scales let a few hundred
 * dollars of petrol out-shout a five-figure payroll overrun.
 */
export function severityFor(variance, scale, { ceiling = 1 } = {}) {
  if (!Number.isFinite(variance) || variance >= 0) return 0;
  if (!Number.isFinite(scale) || scale <= 0) return 0;
  const raw = Math.abs(variance) / scale;
  return Math.max(0, Math.min(ceiling, raw * ceiling));
}

/** Thresholds are a business judgement, so they live in one place. */
export function statusFor(severity) {
  if (severity >= 0.75) return 'failed';
  if (severity >= 0.5) return 'blocked';
  if (severity >= 0.28) return 'warning';
  return 'healthy';
}

/**
 * The centre landmark: the property itself.
 *
 * Worst-of rather than an average, because averaging hides a single
 * catastrophic line behind five healthy ones — and the landmark exists to make
 * a troubled property visible from across the map.
 */
export function rollUp(severities) {
  if (!severities.length) return 0;
  return Math.max(...severities);
}

export function formatMoney(value) {
  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(Math.round(value)).toLocaleString('en-US')}`;
}
