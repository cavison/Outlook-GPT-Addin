import { EventEmitter } from 'node:events';
import { config } from './config.js';
import { diffEntities, needsAttention, statusRank } from './model.js';
import { buildProviders } from './providers/index.js';
import { WorldLayout } from './world.js';
import { loadPortfolio } from './parcels.js';
import { Game } from './game.js';

/**
 * Owns the poll loop and the single source of truth for world state.
 * Emits:
 *   'delta'    — what changed on the last poll
 *   'game'     — score/quests/incidents after scoring
 *   'provider' — per-provider health, so a dead connector is visible
 */
export class Hub extends EventEmitter {
  constructor() {
    super();
    this.providers = buildProviders();
    this.layout = new WorldLayout();
    try {
      this.townCentre = loadPortfolio().townCentre?.name ?? 'Town Centre';
    } catch {
      this.townCentre = 'Town Centre';
    }
    this.game = new Game();
    this.entities = new Map();
    this.providerHealth = new Map();
    this.timer = null;
    this.polling = false;
    this.lastPollAt = null;
  }

  start() {
    this.poll();
    this.timer = setInterval(() => this.poll(), config.pollSeconds * 1000);
  }

  stop() {
    if (this.timer) clearInterval(this.timer);
  }

  async poll() {
    if (this.polling) return; // a slow tenant must not stack overlapping polls
    this.polling = true;
    try {
      const next = new Map();

      for (const provider of this.providers) {
        try {
          const rows = await provider.fetch();
          for (const entity of rows) next.set(entity.id, entity);
          this.providerHealth.set(provider.id, {
            id: provider.id,
            label: provider.label,
            ok: true,
            count: rows.length,
            checkedAt: new Date().toISOString(),
            error: null,
          });
        } catch (err) {
          // Keep the previous entities for a failed provider rather than
          // deleting its whole district — a transient 429 should not demolish
          // half the city.
          for (const [id, entity] of this.entities) {
            if (entity.source === provider.id) next.set(id, entity);
          }
          this.providerHealth.set(provider.id, {
            id: provider.id,
            label: provider.label,
            ok: false,
            count: 0,
            checkedAt: new Date().toISOString(),
            error: err.message,
          });
          console.warn(`[hub] provider ${provider.id} failed: ${err.message}`);
        }
      }

      const delta = diffEntities(this.entities, next);
      this.entities = next;

      // Placement before broadcast, so the client never receives an entity it
      // cannot position. Districts are grown to fit first — otherwise the last
      // arrivals in a big district would have nowhere to stand.
      const perDistrict = new Map();
      for (const entity of this.entities.values()) {
        const row = perDistrict.get(entity.district) ?? { count: 0, compact: 0, group: null };
        row.group ??= entity.group ?? null;
        // Parcels have fixed addresses inside one hex, so they never drive a
        // property to claim more tiles.
        if (!entity.encode?.parcel) row.count++;
        // A district built from small repeated units gets the fine grid, so a
        // fleet of hundreds reads as infrastructure rather than sprawl.
        if (entity.encode?.form === 'relay') row.compact++;
        perDistrict.set(entity.district, row);
      }
      // Plan first: keeping each regional's book clear of every other's is a
      // whole-map constraint, so it cannot be solved district by district.
      const planned = [...perDistrict].map(([name, row]) => ({ name, group: row.group }));
      if (!perDistrict.has(this.townCentre)) planned.push({ name: this.townCentre, group: null });
      this.layout.planFor(planned, this.townCentre);

      for (const [name, row] of perDistrict) {
        const density = row.compact > row.count / 2 ? 'dense' : 'normal';
        this.layout.ensureCapacity(name, row.count, density, row.group);
      }
      for (const entity of this.entities.values()) this.layout.place(entity);
      this.layout.prune(new Set(this.entities.keys()));
      this.layout.save();

      const entityList = [...this.entities.values()];
      this.game.applyTransitions(delta.transitions);
      // Transitions first (they carry the from → to story), then reconcile to
      // adopt anything already broken and retire anything that vanished.
      this.game.reconcile(entityList);
      this.game.updateTerraform(entityList);
      this.game.checkStreak();
      this.game.save();

      this.lastPollAt = new Date().toISOString();

      if (delta.added.length || delta.changed.length || delta.removed.length) {
        this.emit('delta', {
          ...delta,
          layout: this.layout.describe(),
          at: this.lastPollAt,
        });
      }
      this.emit('game', this.game.snapshot());
      this.emit('provider', [...this.providerHealth.values()]);
    } finally {
      this.polling = false;
    }
  }

  /** Full state for a newly connected client. */
  snapshot() {
    const entities = [...this.entities.values()];
    return {
      entities,
      layout: this.layout.describe(),
      placements: Object.fromEntries(
        entities.map((e) => [e.id, this.layout.place(e)]),
      ),
      game: this.game.snapshot(),
      providers: [...this.providerHealth.values()],
      alerts: entities
        .filter((e) => needsAttention(e.status))
        .sort((a, b) => statusRank(a.status) - statusRank(b.status)),
      config: {
        pollSeconds: config.pollSeconds,
        allowWriteActions: config.allowWriteActions,
        requireConfirmForWrites: config.requireConfirmForWrites,
      },
      lastPollAt: this.lastPollAt,
    };
  }

  entity(id) {
    return this.entities.get(id) ?? null;
  }

  /** Run a provider action, then score it. */
  async execute(entityId, actionId) {
    const entity = this.entities.get(entityId);
    if (!entity) return { ok: false, message: 'Unknown entity' };

    const action = entity.actions.find((a) => a.id === actionId);
    if (!action) return { ok: false, message: 'Unknown action' };
    if (action.write && !config.allowWriteActions) {
      return { ok: false, message: 'Write actions are disabled (ALLOW_WRITE_ACTIONS=false)' };
    }

    const provider = this.providers.find((p) => p.id === entity.source);
    if (!provider) return { ok: false, message: 'Provider unavailable' };

    const result = await provider.execute(entityId, actionId);
    if (result.ok) {
      this.game.recordAction(entity, action.label);
      this.game.save();
      this.emit('game', this.game.snapshot());
      // Reflect the change immediately rather than waiting out the poll gap.
      setTimeout(() => this.poll(), 1200);
    }
    return result;
  }

  acknowledge(entityId) {
    const entity = this.entities.get(entityId);
    if (!entity) return { ok: false, message: 'Unknown entity' };
    const result = this.game.acknowledge(entityId, entity.name);
    this.game.save();
    this.emit('game', this.game.snapshot());
    return result;
  }
}
