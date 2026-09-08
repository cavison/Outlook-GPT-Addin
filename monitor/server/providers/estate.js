import { makeEntity } from '../model.js';
import { loadPortfolio } from '../parcels.js';
import { statusFor, rollUp } from '../severity.js';
import { loadRegistry, readStore, scaleFor, isStale, scoreReading } from '../kpi.js';

// The portfolio: one hex per property, one pillar per KPI at its fixed parcel
// address, and a centre landmark standing for the property itself.
//
// Nothing in here knows where a reading came from. The workbook importer, a
// nightly signage agent and a Power Automate flow posting to /api/ingest all
// write the same batch format into data/measurements, and this provider turns
// whatever it finds there into buildings. Adding a KPI is a registry entry plus
// a feed — no code.
//
// Height is severity, so a property with nothing wrong reads as flat ground and
// a property in trouble is visible from across the map. The centre landmark is
// the one exception: constant height everywhere, so it acts as a ruler.
//
// Four kinds of empty, and they must never look alike:
//
//   healthy pillar   reported, and fine
//   paved lot        not applicable at this property — a real answer
//   marked-out plot  registered but never connected. Nothing is emitted: the
//                    parcel's faint site marking is already drawn on every hex,
//                    so an unbuilt KPI reads as ground held for it. Nine
//                    unconnected KPIs across 185 properties would otherwise put
//                    1,665 fenced plots on the map and bury the six that report.
//   fenced plot      WAS reporting and stopped, or the batch skipped this
//                    property. This is the one that matters: a feed that
//                    quietly died is exactly the failure this map exists to
//                    catch, and it must not be able to hide behind a green tile.

export class EstateProvider {
  id = 'estate';
  label = 'Portfolio';

  constructor() {
    this.portfolio = loadPortfolio();
    this.registry = loadRegistry();
  }

  /** The registry, for the client's legend, roster and filters. */
  describeKpis() {
    return this.registry;
  }

  async fetch() {
    const now = new Date();
    const { properties } = this.portfolio;
    const store = readStore(this.registry);

    // Per-KPI preparation, done once rather than per property: the variance
    // scale is a property of the whole column, not of one reading.
    const prepared = new Map();
    for (const [id, spec] of Object.entries(this.registry)) {
      const batch = store.get(id) ?? null;
      const stale = batch ? isStale(batch, spec, now) : false;
      prepared.set(id, {
        spec,
        batch,
        stale,
        scale: batch && spec.kind === 'variance' ? scaleFor(batch) : null,
        rows: new Map((batch?.rows ?? []).map((r) => [r.property, r])),
      });
    }

    const entities = [];

    for (const property of properties) {
      const severities = [];
      const attributes = {};
      const brokenFeeds = [];
      const awaitingFeeds = [];

      // Attributes first — the landmark carries them, so the roster can show a
      // director's name without a second round trip.
      for (const [id, prep] of prepared) {
        if (prep.spec.kind !== 'label') continue;
        const row = prep.rows.get(property.name);
        if (row && !prep.stale && row.applicable !== false) attributes[id] = row.value;
      }

      for (const [id, prep] of prepared) {
        const { spec, batch, stale } = prep;
        if (!spec.parcel) continue;

        const base = {
          id: `estate:${property.name}:${spec.parcel}`,
          source: 'estate',
          district: property.name,
          group: property.neighbourhood,
          name: spec.label,
        };

        const row = prep.rows.get(property.name);

        // --- registered, never connected ------------------------------------
        // Ground held for it, nothing built. The parcel's site marking is
        // already on the hex, so emitting an object here would only add noise.
        if (!batch) {
          awaitingFeeds.push(id);
          continue;
        }

        // --- was reporting, isn't now ---------------------------------------
        if (stale || !row) {
          brokenFeeds.push(id);
          entities.push(
            makeEntity({
              ...base,
              kind: 'parcel',
              status: 'unknown',
              detail: noDataReason(batch, stale, spec),
              metrics: {
                kpi: id,
                parcel: spec.parcel,
                kind: spec.kind,
                cadence: spec.cadence,
                regional: property.neighbourhood,
                asOf: batch.asOf,
                feed: stale ? 'stale' : 'missing-row',
              },
              encode: { parcel: spec.parcel, form: 'plot' },
              actions: [],
            }),
          );
          continue;
        }

        const scored = row.applicable === false
          ? { severity: 0, headline: 'not applicable', detail: row.note ?? '', notApplicable: true }
          : scoreReading(row, spec, { scale: prep.scale });

        // --- not applicable -------------------------------------------------
        if (scored.notApplicable) {
          entities.push(
            makeEntity({
              ...base,
              kind: 'parcel',
              status: 'paused',
              detail: row.note ?? `${spec.label} does not apply at this property`,
              metrics: {
                kpi: id,
                parcel: spec.parcel,
                kind: spec.kind,
                applicable: false,
                regional: property.neighbourhood,
                asOf: batch.asOf,
              },
              encode: { parcel: spec.parcel, form: 'lot' },
              actions: [],
            }),
          );
          continue;
        }

        // --- a reading ------------------------------------------------------
        severities.push({ severity: scored.severity, kpi: id, spec, scored, row });

        entities.push(
          makeEntity({
            ...base,
            kind: 'parcel',
            status: statusFor(scored.severity),
            detail: [scored.headline, scored.detail].filter(Boolean).join(' — '),
            metrics: {
              kpi: id,
              parcel: spec.parcel,
              kind: spec.kind,
              cadence: spec.cadence,
              value: row.value,
              ...(row.total != null ? { total: row.total } : {}),
              ...(row.budget != null ? { ytdBudget: row.budget } : {}),
              ...(row.actual != null ? { ytdActual: row.actual } : {}),
              ...(spec.kind === 'variance' ? { variance: row.value } : {}),
              target: row.target ?? spec.target ?? null,
              severityPct: Math.round(scored.severity * 100),
              regional: property.neighbourhood,
              asOf: batch.asOf,
              period: batch.source,
              ...(row.note ? { note: row.note } : {}),
            },
            url: row.url ?? null,
            encode: {
              parcel: spec.parcel,
              form: 'pillar',
              severity: {
                value: scored.severity,
                label: spec.label,
                raw: scored.headline,
              },
            },
            actions: [],
          }),
        );
      }

      // --- the centre landmark ---------------------------------------------
      const overall = rollUp(severities.map((s) => s.severity));
      const worst = [...severities].sort((a, b) => b.severity - a.severity)[0];
      const reporting = severities.length;

      entities.push(
        makeEntity({
          id: `estate:${property.name}:01`,
          source: 'estate',
          district: property.name,
          group: property.neighbourhood,
          kind: 'property',
          name: property.name,
          status: reporting ? statusFor(overall) : 'unknown',
          detail: !reporting
            ? 'No KPI is reporting for this property'
            : overall < 0.28
              ? `On plan across ${reporting} reporting KPI${reporting === 1 ? '' : 's'}`
              : `Worst: ${worst.spec.label} — ${worst.scored.headline}`,
          metrics: {
            regional: property.neighbourhood,
            ...attributes,
            kpisReporting: reporting,
            // Two different problems, kept apart. A broken feed is work; a
            // KPI nobody has connected yet is a plan.
            kpisBroken: brokenFeeds.length,
            brokenFeeds,
            kpisAwaiting: awaitingFeeds.length,
            awaitingFeeds,
            worstKpi: worst?.kpi ?? null,
            severityPct: Math.round(overall * 100),
            // The roster ranks on this. Worst-of decides the colour, but a
            // property failing four KPIs deserves to outrank one failing a
            // single line equally badly, and worst-of alone cannot say that.
            loadPct: Math.round(
              (severities.reduce((sum, s) => sum + s.severity, 0) / Math.max(1, reporting)) * 100,
            ),
            failing: severities.filter((s) => s.severity >= 0.28).length,
          },
          encode: {
            parcel: '01',
            form: 'pillar-landmark',
            // Constant height: the landmark is the property, not one of its
            // numbers. The roll-up still sets its colour and sorts the roster.
            severity: {
              value: overall,
              label: 'Worst KPI',
              raw: worst ? worst.spec.label : null,
              height: 'fixed',
            },
          },
          actions: [],
        }),
      );
    }

    return entities;
  }

  async execute() {
    return { ok: false, message: 'KPI readings are read-only — fix the source, not the map' };
  }
}

function noDataReason(batch, stale, spec) {
  if (stale) {
    const days = Math.round((Date.now() - new Date(batch.asOf)) / 86400_000);
    return `Feed stale — last reading ${days} day${days === 1 ? '' : 's'} ago, ${spec.cadence} expected`;
  }
  return 'This property was not in the last batch';
}
