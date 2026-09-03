import fs from 'node:fs';
import path from 'node:path';
import { makeEntity } from '../model.js';
import { loadPortfolio } from '../parcels.js';
import { ROOT } from '../config.js';
import { severityFor, statusFor, rollUp, formatMoney } from '../severity.js';

// The portfolio, driven by the monthly Actuals vs Budget import.
//
// One hex per property, one pillar per budget line item at its fixed parcel
// address, and a centre landmark carrying the property's worst line. Height is
// severity, so a property that came in under budget everywhere reads as flat
// ground and a property in trouble is visible from across the map.
//
// Without an import it falls back to fenced plots — an address with no feed,
// which must never be mistaken for an address with nothing wrong.

const DATA_PATH = path.join(ROOT, 'data', 'financials.json');

export class EstateProvider {
  id = 'estate';
  label = 'Portfolio';

  constructor() {
    this.portfolio = loadPortfolio();
    this.financials = this.loadFinancials();
  }

  loadFinancials() {
    if (!fs.existsSync(DATA_PATH)) return null;
    try {
      const data = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));
      if (!Array.isArray(data.rows) || !data.rows.length) return null;
      return data;
    } catch (err) {
      console.warn(`[estate] could not read data/financials.json — ${err.message}`);
      return null;
    }
  }

  /** Rows grouped by property, keyed by the line item's configured parcel. */
  indexRows() {
    const { lineItems = {} } = this.portfolio;
    const byProperty = new Map();

    for (const row of this.financials.rows) {
      const mapping = lineItems[row.item];
      if (!mapping) continue; // a line item nobody has put on the map yet
      if (!byProperty.has(row.property)) byProperty.set(row.property, []);
      byProperty.get(row.property).push({ ...row, mapping });
    }
    return byProperty;
  }

  async fetch() {
    const entities = [];
    const { properties, assigned, townCentre } = this.portfolio;

    // Town Centre first so it claims the origin hex.
    if (townCentre) {
      for (const building of townCentre.buildings ?? []) {
        entities.push(
          makeEntity({
            id: `town:${building.id}`,
            source: 'estate',
            district: townCentre.name,
            kind: 'civic',
            name: building.label,
            status: 'unknown',
            detail: 'Awaiting data — no connector yet',
            encode: { parcel: building.parcel, form: 'plot' },
            actions: [],
          }),
        );
      }
    }

    if (!this.financials) {
      for (const property of properties) {
        for (const parcel of assigned) {
          entities.push(
            makeEntity({
              id: `estate:${property.name}:${parcel.number}`,
              source: 'estate',
              district: property.name,
              group: property.neighbourhood,
              kind: 'parcel',
              name: parcel.label,
              status: 'unknown',
              detail: 'No import yet — run scripts/import-financials.mjs',
              metrics: { parcel: parcel.number },
              encode: { parcel: parcel.number, form: 'plot' },
              actions: [],
            }),
          );
        }
      }
      return entities;
    }

    const { scales } = this.financials;
    const byProperty = this.indexRows();
    const period = this.financials.source;

    for (const property of properties) {
      const rows = byProperty.get(property.name) ?? [];
      const severities = [];

      for (const row of rows) {
        const ceiling = row.mapping.ceiling ?? 1;
        const severity = severityFor(row.variance, scales[row.item], { ceiling });
        severities.push({ severity, row });

        const over = row.variance < 0;
        entities.push(
          makeEntity({
            id: `estate:${property.name}:${row.mapping.parcel}`,
            source: 'estate',
            district: property.name,
            group: property.neighbourhood,
            kind: 'parcel',
            name: row.mapping.label ?? row.item,
            status: statusFor(severity),
            detail: over
              ? `${formatMoney(Math.abs(row.variance))} over budget — actual ${formatMoney(row.actual)} vs budget ${formatMoney(row.budget)}`
              : `${formatMoney(row.variance)} under budget — actual ${formatMoney(row.actual)} vs budget ${formatMoney(row.budget)}`,
            metrics: {
              lineItem: row.item,
              ytdActual: row.actual,
              ytdBudget: row.budget,
              variance: row.variance,
              variancePct: row.budget ? Number((row.variance / row.budget).toFixed(4)) : null,
              severityPct: Math.round(severity * 100),
              parcel: row.mapping.parcel,
              regional: property.neighbourhood,
              period,
            },
            encode: {
              parcel: row.mapping.parcel,
              form: 'pillar',
              severity: {
                value: severity,
                label: 'Unfavourable variance',
                raw: over ? `${formatMoney(Math.abs(row.variance))} over` : 'under budget',
              },
            },
            actions: [],
          }),
        );
      }

      // The centre landmark: the property itself, carrying its worst line.
      const overall = rollUp(severities.map((s) => s.severity));
      const worst = severities.sort((a, b) => b.severity - a.severity)[0];
      entities.push(
        makeEntity({
          id: `estate:${property.name}:01`,
          source: 'estate',
          district: property.name,
          group: property.neighbourhood,
          kind: 'property',
          name: property.name,
          status: statusFor(overall),
          detail: rows.length
            ? overall < 0.28
              ? `On plan across ${rows.length} budget lines`
              : `Worst line: ${worst.row.mapping.label ?? worst.row.item} — ${formatMoney(Math.abs(worst.row.variance))} over`
            : 'No budget lines matched for this property',
          metrics: {
            regional: property.neighbourhood,
            linesTracked: rows.length,
            worstLine: worst?.row.item ?? null,
            totalUnfavourable: rows
              .filter((r) => r.variance < 0)
              .reduce((sum, r) => sum + Math.abs(r.variance), 0),
            severityPct: Math.round(overall * 100),
            period,
          },
          encode: {
            parcel: '01',
            form: 'pillar-landmark',
            severity: { value: overall, label: 'Worst budget line', raw: null },
          },
          actions: [],
        }),
      );
    }

    return entities;
  }

  async execute() {
    return { ok: false, message: 'Budget figures are read-only' };
  }
}
