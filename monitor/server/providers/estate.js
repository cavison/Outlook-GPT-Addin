import { makeEntity } from '../model.js';
import { loadPortfolio } from '../parcels.js';
import { config } from '../config.js';

// Phase 01: the shell.
//
// Every property, every assigned parcel, no data yet. This exists so the frame
// is real before any connector is — the hexes, the neighbourhood clusters and
// the fixed parcel addresses are the part that must not change later.
//
// It also makes the three-kinds-of-empty distinction concrete from day one:
//
//   assigned + no feed  -> "awaiting data", a fenced plot. NOT fine. Needs work.
//   unassigned position -> a finished empty lot. Deliberate, needs nothing.
//   assigned + feed ok  -> the real object (arrives with each connector).
//
// The dangerous case is the first one looking like the second, which is how a
// KPI silently stops reporting and nobody notices for a month.

/** Deterministic 0..1 from a string, so the demo skyline is stable across
 *  restarts rather than reshuffling on every poll. */
function seeded(str, salt = 0) {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

/**
 * Severity to status. Thresholds live here rather than in the renderer, because
 * "what counts as bad" is a business judgement per KPI, not a drawing decision.
 */
function statusFor(severity) {
  if (severity >= 0.75) return 'failed';
  if (severity >= 0.5) return 'blocked';
  if (severity >= 0.28) return 'warning';
  return 'healthy';
}

export class EstateProvider {
  id = 'estate';
  label = 'Portfolio';

  constructor() {
    this.portfolio = loadPortfolio();
    this.demo = config.estateDemo;
  }

  /**
   * Stand-in severities until real connectors land. Most parcels sit near zero
   * so a healthy property reads as almost flat ground, and a few properties are
   * deliberately in trouble so the skyline has something to say.
   */
  demoSeverity(propertyName, parcelNumber) {
    const propertyTrouble = seeded(propertyName, 11);
    const base = seeded(`${propertyName}:${parcelNumber}`, 7);
    // Most properties are fine; roughly a quarter are having a bad month.
    if (propertyTrouble > 0.74) return Math.min(1, base * 1.15);
    if (propertyTrouble > 0.55) return base * 0.55;
    return base * 0.22;
  }

  async fetch() {
    const entities = [];
    const { properties, assigned, townCentre } = this.portfolio;

    // Town Centre first so it claims the origin hex and the properties grow
    // outward around it.
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

    for (const property of properties) {
      for (const parcel of assigned) {
        if (!this.demo) {
          // No connector: a fenced plot, explicitly NOT a healthy-looking blank.
          entities.push(
            makeEntity({
              id: `estate:${property.name}:${parcel.number}`,
              source: 'estate',
              district: property.name,
              group: property.neighbourhood,
              kind: 'parcel',
              name: parcel.label,
              status: 'unknown',
              detail: 'Awaiting data — no connector yet',
              metrics: { parcel: parcel.number, position: parcel.clock },
              encode: { parcel: parcel.number, form: 'plot' },
              actions: [],
            }),
          );
          continue;
        }

        const severity = this.demoSeverity(property.name, parcel.number);
        const status = statusFor(severity);
        entities.push(
          makeEntity({
            id: `estate:${property.name}:${parcel.number}`,
            source: 'estate',
            district: property.name,
            group: property.neighbourhood,
            kind: 'parcel',
            name: parcel.label,
            status,
            detail:
              severity < 0.28
                ? `${parcel.label} — on plan`
                : `${parcel.label} — ${Math.round(severity * 100)}% of the way to the red line`,
            metrics: {
              parcel: parcel.number,
              position: parcel.clock,
              neighbourhood: property.neighbourhood,
              severityPct: Math.round(severity * 100),
              simulated: true,
            },
            encode: {
              parcel: parcel.number,
              form: 'pillar',
              severity: {
                value: severity,
                label: 'Severity',
                raw: `${Math.round(severity * 100)}% (simulated)`,
              },
            },
            actions: [],
          }),
        );
      }
    }

    return entities;
  }

  async execute() {
    return { ok: false, message: 'The shell has no data and nothing to act on yet' };
  }
}
