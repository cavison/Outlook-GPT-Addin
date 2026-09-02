import { readJson, writeJson } from './config.js';
import { needsAttention } from './model.js';

// ---------------------------------------------------------------------------
// The scoring rule that matters: XP is paid for CHANGES YOU CAUSED, never for
// uptime. "Flow ran successfully" is the default state of a working system —
// paying for it produces a number that only ever goes up, which everyone stops
// reading by week three. So:
//
//   * an incident that you acted on and that then recovered  -> full credit
//   * an incident that recovered on its own                  -> token credit,
//                                                               labelled as such
//   * an incident still open                                 -> nothing, and it
//                                                               ages visibly
// ---------------------------------------------------------------------------

const XP = {
  acknowledge: 10,
  resolveAttended: 40,
  rapidResponseBonus: 30, // attended within RAPID_MS of the incident opening
  resolveSelfHealed: 5,
  actionExecuted: 15,
  questComplete: 60,
};

const RAPID_MS = 10 * 60 * 1000;
const MAX_EVENTS = 200;

const DEFAULT_STATE = {
  xp: 0,
  streak: 0,
  lastStreakDay: null,
  incidents: {}, // entityId -> open incident
  history: [], // resolved incidents, newest first, capped
  events: [], // ticker feed
  quests: null,
  terraform: 0.5, // 0..1, drives how green/alive the world looks
  totals: { resolved: 0, selfHealed: 0, actions: 0, acknowledged: 0 },
};

/** Level curve: deliberately slow after level 10 so it doesn't inflate away. */
export function levelFromXp(xp) {
  let level = 1;
  let need = 100;
  let remaining = xp;
  while (remaining >= need) {
    remaining -= need;
    level++;
    need = Math.round(need * 1.35);
  }
  return { level, into: remaining, need, pct: need ? remaining / need : 0 };
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

export class Game {
  constructor() {
    this.state = { ...structuredClone(DEFAULT_STATE), ...readJson('game.json', {}) };
    this.state.incidents ??= {};
    this.state.events ??= [];
    this.state.history ??= [];
    this.state.totals ??= { ...DEFAULT_STATE.totals };
    this.rollQuestsIfNeeded();
  }

  log(kind, text, meta = {}) {
    this.state.events.unshift({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      kind,
      text,
      at: new Date().toISOString(),
      ...meta,
    });
    this.state.events.length = Math.min(this.state.events.length, MAX_EVENTS);
  }

  award(amount, reason) {
    if (!amount) return;
    this.state.xp += amount;
    this.log('xp', reason, { xp: amount });
  }

  // -- incidents ------------------------------------------------------------

  /**
   * Fold a poll's status transitions into incident state.
   * @param {Array} transitions from diffEntities
   */
  applyTransitions(transitions) {
    for (const t of transitions) {
      const wasAttention = needsAttention(t.from);
      const isAttention = needsAttention(t.to);

      if (!wasAttention && isAttention) {
        this.openIncident(t.entity, t.to);
      } else if (wasAttention && !isAttention) {
        this.closeIncident(t.entity, t.to);
      } else if (wasAttention && isAttention) {
        const incident = this.state.incidents[t.entity.id];
        if (incident) incident.status = t.to;
      }
    }
  }

  /**
   * Catch what transitions alone cannot see.
   *
   * Incidents open on a status *change*, so anything already failing at the
   * first poll — or at any restart — would otherwise have no incident record,
   * and could never be acknowledged or scored. This also retires incidents
   * whose entity has vanished from the tenant entirely.
   */
  reconcile(entities) {
    const byId = new Map(entities.map((e) => [e.id, e]));

    for (const entity of entities) {
      if (needsAttention(entity.status) && !this.state.incidents[entity.id]) {
        this.openIncident(entity, entity.status, { silent: true });
      }
    }

    for (const [id, incident] of Object.entries(this.state.incidents)) {
      const entity = byId.get(id);
      if (!entity) {
        // The thing stopped existing — close it out without paying XP for a
        // resolution nobody performed.
        delete this.state.incidents[id];
        this.log('incident', `${incident.name} disappeared from the tenant`);
      } else if (!needsAttention(entity.status)) {
        this.closeIncident(entity, entity.status);
      }
    }
  }

  openIncident(entity, status, { silent = false } = {}) {
    if (this.state.incidents[entity.id]) return;
    this.state.incidents[entity.id] = {
      entityId: entity.id,
      name: entity.name,
      district: entity.district,
      status,
      openedAt: Date.now(),
      attended: false,
      attendedAt: null,
      actions: 0,
    };
    // Pre-existing failures found at startup are adopted quietly — announcing
    // them as if they just happened would cry wolf on every restart.
    this.log('incident', silent ? `${entity.name} is ${status} (found on start-up)` : `${entity.name} → ${status}`, {
      entityId: entity.id,
      district: entity.district,
      severity: status,
    });
  }

  closeIncident(entity, status) {
    const incident = this.state.incidents[entity.id];
    if (!incident) return;
    delete this.state.incidents[entity.id];

    const durationMs = Date.now() - incident.openedAt;
    let gained = 0;
    let note;

    if (incident.attended) {
      gained = XP.resolveAttended;
      note = `Resolved ${entity.name}`;
      if (incident.attendedAt - incident.openedAt <= RAPID_MS) {
        gained += XP.rapidResponseBonus;
        note += ' (rapid response)';
      }
      this.state.totals.resolved++;
      this.bumpQuest('resolve');
    } else {
      gained = XP.resolveSelfHealed;
      note = `${entity.name} recovered on its own — no credit claimed`;
      this.state.totals.selfHealed++;
    }

    this.state.history.unshift({
      ...incident,
      closedAt: Date.now(),
      durationMs,
      resolvedStatus: status,
      attended: incident.attended,
      xp: gained,
    });
    this.state.history.length = Math.min(this.state.history.length, 100);

    this.award(gained, note);
    this.checkStreak();
  }

  /** The user looked at it and took ownership. Marks the incident attended. */
  acknowledge(entityId, name) {
    const incident = this.state.incidents[entityId];
    if (!incident) return { ok: false, reason: 'no open incident' };
    if (incident.attended) return { ok: true, already: true };
    incident.attended = true;
    incident.attendedAt = Date.now();
    this.state.totals.acknowledged++;
    this.award(XP.acknowledge, `Acknowledged ${name ?? incident.name}`);
    this.bumpQuest('acknowledge');
    return { ok: true };
  }

  /** A write action was actually executed against a real system. */
  recordAction(entity, actionLabel) {
    const incident = this.state.incidents[entity.id];
    if (incident) {
      incident.attended = true;
      incident.attendedAt ??= Date.now();
      incident.actions++;
    }
    this.state.totals.actions++;
    this.award(XP.actionExecuted, `${actionLabel} → ${entity.name}`);
    this.bumpQuest('act');
  }

  // -- streak & quests ------------------------------------------------------

  checkStreak() {
    const day = today();
    if (this.state.lastStreakDay === day) return;
    // A streak day is earned by ending with nothing left unattended.
    const unattended = Object.values(this.state.incidents).filter((i) => !i.attended);
    if (unattended.length === 0 && this.state.totals.resolved > 0) {
      this.state.streak++;
      this.state.lastStreakDay = day;
      this.log('streak', `Board cleared — ${this.state.streak} day streak`);
    }
  }

  rollQuestsIfNeeded() {
    const day = today();
    if (this.state.quests?.day === day) return;
    this.state.quests = {
      day,
      items: [
        { id: 'resolve', label: 'Resolve 3 incidents', target: 3, progress: 0, done: false },
        { id: 'act', label: 'Take 2 corrective actions', target: 2, progress: 0, done: false },
        { id: 'acknowledge', label: 'Triage 5 alerts', target: 5, progress: 0, done: false },
      ],
    };
  }

  bumpQuest(id) {
    this.rollQuestsIfNeeded();
    const quest = this.state.quests.items.find((q) => q.id === id);
    if (!quest || quest.done) return;
    quest.progress++;
    if (quest.progress >= quest.target) {
      quest.done = true;
      this.award(XP.questComplete, `Daily quest complete: ${quest.label}`);
    }
  }

  // -- world mood -----------------------------------------------------------

  /**
   * Terraform level: an exponential moving average of system health. It moves
   * slowly on purpose — the world should feel like it recovers over a week of
   * good operations, not flicker every poll.
   */
  updateTerraform(entities) {
    const total = entities.length || 1;
    const attention = entities.filter((e) => needsAttention(e.status)).length;
    const instant = 1 - attention / total;
    this.state.terraform = this.state.terraform * 0.92 + instant * 0.08;
  }

  snapshot() {
    this.rollQuestsIfNeeded();
    const progress = levelFromXp(this.state.xp);
    return {
      xp: this.state.xp,
      ...progress,
      streak: this.state.streak,
      terraform: Number(this.state.terraform.toFixed(4)),
      quests: this.state.quests,
      totals: this.state.totals,
      incidents: Object.values(this.state.incidents).sort((a, b) => a.openedAt - b.openedAt),
      events: this.state.events.slice(0, 40),
    };
  }

  save() {
    writeJson('game.json', this.state);
  }
}
