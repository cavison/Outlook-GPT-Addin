import { makeEntity } from '../model.js';

// A worked example of a NON-flow domain on the same map: properties, where the
// house you see is sized by how far its budget has drifted.
//
// This exists to be copied. It is the shortest demonstration that the city is a
// general instrument: swap these rows for a query against your real system and
// nothing else in the app changes.

const PROPERTIES = [
  { id: 'p1', name: '412 Marlowe Ave', budget: 480_000, actual: 511_400, phase: 'Framing', stalledDays: 0 },
  { id: 'p2', name: '87 Ridgeway Ct', budget: 320_000, actual: 318_900, phase: 'Finishes', stalledDays: 0 },
  { id: 'p3', name: 'Halstead Mill — Unit B', budget: 1_250_000, actual: 1_402_000, phase: 'MEP rough-in', stalledDays: 12 },
  { id: 'p4', name: '9 Corbin Lane', budget: 275_000, actual: 249_100, phase: 'Closeout', stalledDays: 0 },
  { id: 'p5', name: 'Westgate Retail Pad', budget: 890_000, actual: 902_600, phase: 'Sitework', stalledDays: 0 },
  { id: 'p6', name: '1130 Ferris St', budget: 410_000, actual: 388_400, phase: 'Framing', stalledDays: 0 },
  { id: 'p7', name: 'Ashcroft Row — Phase 2', budget: 2_100_000, actual: 2_486_000, phase: 'Permitting', stalledDays: 31 },
  { id: 'p8', name: '55 Quarry Rd', budget: 198_000, actual: 201_300, phase: 'Punch list', stalledDays: 0 },
];

/**
 * Operational status is about whether the property needs a human — not about
 * whether it is over budget. Money is a separate question, and conflating the
 * two is how a dashboard starts lying: a project can be well over budget and
 * perfectly on track, or dead stalled and exactly on budget.
 */
function statusOf(property, variancePct) {
  if (property.stalledDays >= 21) return { status: 'blocked', detail: `Stalled ${property.stalledDays} days in ${property.phase}` };
  if (property.stalledDays > 0) return { status: 'warning', detail: `No movement for ${property.stalledDays} days` };
  if (variancePct > 0.1) return { status: 'failed', detail: `${(variancePct * 100).toFixed(1)}% over budget in ${property.phase}` };
  if (variancePct > 0.03) return { status: 'warning', detail: `Trending ${(variancePct * 100).toFixed(1)}% over in ${property.phase}` };
  return { status: 'healthy', detail: `${property.phase} · on plan` };
}

const money = (n) =>
  `${n < 0 ? '-' : ''}$${Math.abs(Math.round(n)).toLocaleString('en-US')}`;

export class PortfolioProvider {
  id = 'portfolio';
  label = 'Portfolio';

  constructor() {
    this.rows = PROPERTIES.map((p) => ({ ...p }));
  }

  tick() {
    // Costs creep and stalls lengthen — enough movement to see the world react.
    for (const row of this.rows) {
      if (Math.random() < 0.25) row.actual += Math.round((Math.random() - 0.35) * row.budget * 0.01);
      if (row.stalledDays > 0 && Math.random() < 0.3) row.stalledDays++;
      if (row.stalledDays === 0 && Math.random() < 0.03) row.stalledDays = 1;
    }
  }

  async fetch() {
    this.tick();

    // A shared domain across the district, so height is comparable between
    // houses. Per-entity domains would make the tallest house on every tile
    // look identical regardless of value.
    const variances = this.rows.map((r) => Math.abs(r.actual - r.budget));
    const maxVariance = Math.max(1, ...variances);
    const signed = this.rows.map((r) => r.actual - r.budget);
    const bound = Math.max(1, ...signed.map(Math.abs));

    return this.rows.map((row) => {
      const variance = row.actual - row.budget;
      const variancePct = variance / row.budget;
      const { status, detail } = statusOf(row, variancePct);

      return makeEntity({
        id: `prop:${row.id}`,
        source: 'portfolio',
        district: 'Properties',
        kind: 'property',
        name: row.name,
        status,
        detail,
        url: null,
        metrics: {
          budget: row.budget,
          actual: row.actual,
          variance,
          variancePct: Number(variancePct.toFixed(4)),
          phase: row.phase,
          stalledDays: row.stalledDays,
        },
        encode: {
          form: 'house',
          // Height = how far off plan, in absolute dollars. Footprint stays
          // fixed so the comparison is a length, not a volume.
          height: {
            value: Math.abs(variance),
            label: 'Budget variance',
            unit: '$',
            domain: [0, maxVariance],
          },
          // Signed variance for the diverging view: under plan vs over plan,
          // with "exactly on budget" sitting at the neutral midpoint.
          metric: {
            value: variance,
            label: 'Over / under budget',
            unit: '$',
            domain: [-bound, bound],
            mode: 'diverging',
            midpoint: 0,
          },
        },
        actions: [],
      });
    });
  }

  async execute() {
    return { ok: false, message: 'Portfolio rows are read-only in this build' };
  }
}

export const formatMoney = money;
