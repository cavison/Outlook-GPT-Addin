import { World } from './world.js';
import { Hud } from './hud.js';
import { Roster } from './roster.js';
import { Filters } from './filters.js';
import { STATUS_LABEL, ATTENTION } from './palette.js';

const world = new World(document.getElementById('scene'));
// Exposed for diagnostics: profiling the render passes from the console.
window.__world = world;
const entities = new Map();
const placements = new Map();
let registry = {};

const hud = new Hud({
  onSelect: (id, fromCard = false) => {
    hud.select(id, true);
    world.select(id);
    if (!fromCard && id) world.select(id);
  },
  onAction: async (entityId, actionId) => {
    const res = await post('/api/action', { entityId, actionId });
    hud.toast(res.message ?? (res.ok ? 'Done' : 'Failed'), res.ok ? 'good' : 'bad');
  },
  onAcknowledge: async (entityId) => {
    const res = await post('/api/acknowledge', { entityId });
    if (res.ok) hud.toast('Acknowledged — you own this one now', 'good');
    else hud.toast(res.message ?? 'Could not acknowledge', 'bad');
  },
  onViewMode: (mode) => {
    world.setViewMode(mode);
    hud.setViewMode(mode);
  },
  onRefresh: async () => {
    hud.setPollStatus('refreshing…');
    await post('/api/refresh', {});
  },
  onSignIn: async () => {
    const res = await post('/api/auth/login', {});
    if (res.deviceCode) hud.showDeviceCode(res.deviceCode);
    else hud.toast(res.message ?? 'Sign-in could not start', 'bad');
    pollAuth();
  },
});

const roster = new Roster({
  onSelect: (id) => {
    hud.select(id, true);
    world.select(id);
  },
  // Pointing at a card pins that property's label on the map. Without it,
  // finding a name from the roster means hunting 185 identical hexes.
  onHover: (name) => world.highlight(name),
});

// One filter state drives the map and the roster. Two views of one portfolio
// disagreeing about what is on screen is worse than having no filter at all.
const filters = new Filters({
  onChange: (f) => {
    const predicate = f.predicate();
    roster.setFilter(predicate);
    world.setFilter(predicate ? new Set(roster.visibleRows().map((r) => r.name)) : null);
    world.setHeightVariant(f.height, f.focusKpi);
  },
});

for (const tab of document.querySelectorAll('.tab')) {
  tab.addEventListener('click', () => {
    for (const other of document.querySelectorAll('.tab')) {
      const on = other === tab;
      other.classList.toggle('active', on);
      other.setAttribute('aria-selected', String(on));
      document.getElementById(`pane-${other.dataset.tab}`).classList.toggle('hidden', !on);
    }
  });
}

world.onSelect = (id) => {
  hud.select(id, true);
  const entity = entities.get(id);
  if (entity) roster.setSelected(entity.district);
};

async function post(url, body) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return await res.json();
  } catch (err) {
    return { ok: false, message: err.message };
  }
}

function applySnapshot(snapshot) {
  entities.clear();
  for (const e of snapshot.entities) entities.set(e.id, e);
  for (const [id, p] of Object.entries(snapshot.placements ?? {})) placements.set(id, p);

  world.setLayout(snapshot.layout);
  for (const e of snapshot.entities) {
    const placement = placements.get(e.id);
    if (placement) world.upsert(e, placement);
  }
  world.setTerraform(snapshot.game.terraform);

  hud.setConfig(snapshot.config ?? {});
  hud.setEntities(entities);
  hud.setProviders(snapshot.providers ?? []);
  hud.setGame(snapshot.game);

  if (snapshot.kpis) {
    registry = snapshot.kpis;
    roster.setRegistry(registry);
    filters.setRegistry(registry);
  }
  refreshRoster();
  markPoll(snapshot.lastPollAt);
}

/** Rebuild the roster, then re-apply the filter so the map agrees with it. */
function refreshRoster() {
  roster.setEntities(entities);
  filters.setNeighbourhoods(new Set(roster.rows.map((r) => r.neighbourhood)));
  const predicate = filters.predicate();
  roster.setFilter(predicate);
  world.setFilter(predicate ? new Set(roster.visibleRows().map((r) => r.name)) : null);
  world.setHeightVariant(filters.height, filters.focusKpi);
}

function applyDelta(delta) {
  if (delta.layout) world.setLayout(delta.layout);

  for (const e of [...delta.added, ...delta.changed]) {
    entities.set(e.id, e);
    // A brand new entity may not have a cached placement yet; ask the server
    // for the authoritative map rather than guessing a slot.
    const placement = placements.get(e.id);
    if (placement) world.upsert(e, placement);
    else refreshPlacements();
  }
  for (const e of delta.removed) {
    entities.delete(e.id);
    placements.delete(e.id);
    world.remove(e.id);
  }

  // Announce only the transitions that newly demand attention. Recoveries are
  // good news and get a quieter treatment.
  for (const t of delta.transitions ?? []) {
    if (ATTENTION.has(t.to) && !ATTENTION.has(t.from)) {
      hud.toast(`${t.entity.name} → ${STATUS_LABEL[t.to] ?? t.to}`, 'bad');
    } else if (!ATTENTION.has(t.to) && ATTENTION.has(t.from)) {
      hud.toast(`${t.entity.name} recovered`, 'good');
    }
  }

  hud.setEntities(entities);
  hud.renderAlerts();
  hud.renderDetail();
  refreshRoster();
  markPoll(delta.at);
}

let refreshingPlacements = false;
async function refreshPlacements() {
  if (refreshingPlacements) return;
  refreshingPlacements = true;
  try {
    const snapshot = await (await fetch('/api/state')).json();
    applySnapshot(snapshot);
  } finally {
    refreshingPlacements = false;
  }
}

let lastPollAt = null;
function markPoll(at) {
  if (at) lastPollAt = new Date(at);
}
setInterval(() => {
  if (!lastPollAt) return;
  const secs = Math.round((Date.now() - lastPollAt) / 1000);
  hud.setPollStatus(`updated ${secs}s ago`);
}, 1000);

// -- live stream -------------------------------------------------------------

function connect() {
  const source = new EventSource('/api/stream');

  source.addEventListener('snapshot', (e) => applySnapshot(JSON.parse(e.data)));
  source.addEventListener('delta', (e) => applyDelta(JSON.parse(e.data)));
  source.addEventListener('game', (e) => {
    const game = JSON.parse(e.data);
    hud.setGame(game);
    world.setTerraform(game.terraform);
  });
  source.addEventListener('provider', (e) => hud.setProviders(JSON.parse(e.data)));

  source.onerror = () => {
    hud.setPollStatus('reconnecting…');
    // EventSource retries on its own; this only surfaces the state.
  };
}

async function pollAuth() {
  const status = await (await fetch('/api/auth/status')).json();
  hud.showSignIn(status);
  if (status.pendingDeviceCode) hud.showDeviceCode(status.pendingDeviceCode);
  if (status.configured && !status.signedIn) setTimeout(pollAuth, 4000);
}

connect();
pollAuth();
