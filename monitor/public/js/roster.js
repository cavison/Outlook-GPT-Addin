import { buildRoster, money, hpBand, STATE_LABEL } from './portfolio.js';

// The roster: every property as a party sheet.
//
// The map answers "where"; this answers "who", and it is the only view that can
// show a property whose problem is that nothing is happening. A hex with one
// dark parcel is easy to miss from across the city — a card with a violet pip
// in position 10 is not.
//
// Two rules it shares with the hex, on purpose:
//
//   Pips are in PARCEL ORDER, so pip 3 is the same KPI on every card and in the
//   same place it stands on every hex. You learn one layout, not two.
//
//   The card's colour is worst-of; its RANK is the composite. A property is red
//   because of its worst KPI and sorted by how much is wrong, so neither a
//   single catastrophe nor a broad slide can hide behind the other.

const ICONS = {
  coin: '<circle cx="6" cy="6" r="4.2" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M6 3.6v4.8M4.6 5h2.4M5 7h2.4" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>',
  van: '<path d="M1 8V4h6l2.4 2.2V8" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><circle cx="3.4" cy="8.6" r="1.2" fill="none" stroke="currentColor" stroke-width="1.1"/><circle cx="8.6" cy="8.6" r="1.2" fill="none" stroke="currentColor" stroke-width="1.1"/>',
  screen: '<rect x="1" y="2" width="10" height="6.5" rx="1" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M6 8.5v2M4 10.5h4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
  chat: '<path d="M1.5 2h9v6.2h-5L3 10.5V8.2H1.5z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>',
  doc: '<path d="M2.5 1.5h5l2.2 2.2v6.8h-7.2z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M4.3 6h3.4M4.3 8h3.4" stroke="currentColor" stroke-width="1.2"/>',
  mail: '<rect x="1" y="2.5" width="10" height="7" rx="1" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M1.4 3.2 6 6.6l4.6-3.4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
  menu: '<path d="M3 1.5v3.2a1.4 1.4 0 0 0 2.8 0V1.5M4.4 4.7v5.8" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/><path d="M9 1.5c-1 1-1 4 0 4v5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>',
  calendar: '<rect x="1.2" y="2.2" width="9.6" height="8.3" rx="1" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M1.2 4.8h9.6M3.6 1.2v2M8.4 1.2v2" stroke="currentColor" stroke-width="1.2"/>',
  people: '<circle cx="4.2" cy="3.6" r="1.7" fill="none" stroke="currentColor" stroke-width="1.2"/><circle cx="8.6" cy="4.6" r="1.3" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M1.3 10.4c0-1.9 1.3-3 2.9-3s2.9 1.1 2.9 3" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M8 7.6c1.6-.2 2.7.9 2.7 2.8" fill="none" stroke="currentColor" stroke-width="1.2"/>',
  tray: '<path d="M1.2 6.6h9.6a4.8 4.8 0 0 1-9.6 0z" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M6 4.4V2.2M1 10.4h10" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>',
  clipboard: '<rect x="2.2" y="2" width="7.6" height="8.6" rx="1" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M4.6 2V1h2.8v1" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M4.4 5.4h3.2M4.4 7.6h3.2" stroke="currentColor" stroke-width="1.2"/>',
};

const SEGMENTS = 20;

export class Roster {
  /**
   * @param {object} hooks
   *   onSelect(entityId)   a card was clicked — select the property
   *   onHover(name|null)   a card is under the cursor — highlight its hex
   */
  constructor({ onSelect, onHover }) {
    this.onSelect = onSelect;
    this.onHover = onHover;
    this.registry = {};
    this.entities = new Map();
    this.rows = [];
    this.kpis = [];
    this.filter = null;
    this.sort = 'hp';
    this.group = true;
    this.query = '';
    this.selectedProperty = null;

    this.host = document.getElementById('roster-list');
    this.head = document.getElementById('roster-head');

    // Delegated: the list is rebuilt on every poll, and a handler bound to a
    // row would be pointing at a detached node most of the time.
    this.host.addEventListener('click', (e) => {
      const card = e.target.closest('.rcard');
      if (card) this.onSelect(card.dataset.id);
    });
    this.host.addEventListener('mouseover', (e) => {
      const card = e.target.closest('.rcard');
      this._focus(card ? card.dataset.name : null);
    });
    this.host.addEventListener('mouseleave', () => this._focus(null));

    document.getElementById('roster-sort').addEventListener('change', (e) => {
      this.sort = e.target.value;
      this.render();
    });
    const groupBtn = document.getElementById('roster-group');
    groupBtn.addEventListener('click', () => {
      this.group = !this.group;
      groupBtn.setAttribute('aria-pressed', String(this.group));
      this.render();
    });

    let debounce;
    document.getElementById('roster-q').addEventListener('input', (e) => {
      clearTimeout(debounce);
      debounce = setTimeout(() => { this.query = e.target.value; this.render(); }, 110);
    });
  }

  setRegistry(registry) {
    this.registry = registry ?? {};
  }

  setEntities(entities) {
    this.entities = entities;
    const built = buildRoster(entities, this.registry);
    this.rows = built.rows;
    this.kpis = built.kpis;
    this.render();
  }

  /** A predicate from the filter bar. Null means everything. */
  setFilter(filter) {
    this.filter = filter;
    this.render();
  }

  setSelected(propertyName) {
    if (this.selectedProperty === propertyName) return;
    this.selectedProperty = propertyName;
    for (const card of this.host.querySelectorAll('.rcard')) {
      card.classList.toggle('on', card.dataset.name === propertyName);
    }
  }

  _focus(name) {
    this.host.classList.toggle('focused', Boolean(name));
    for (const card of this.host.querySelectorAll('.rcard')) {
      card.classList.toggle('active', card.dataset.name === name);
    }
    this.onHover?.(name);
  }

  visibleRows() {
    const q = this.query.trim().toLowerCase();
    return this.rows.filter((r) => {
      if (this.filter && !this.filter(r)) return false;
      if (!q) return true;
      return (
        r.name.toLowerCase().includes(q) ||
        r.neighbourhood.toLowerCase().includes(q) ||
        (r.director ?? '').toLowerCase().includes(q)
      );
    });
  }

  render() {
    if (!this.rows.length) {
      this.host.innerHTML = '<p class="empty">Waiting for the first poll.</p>';
      this.head.innerHTML = '';
      return;
    }

    const rows = this.visibleRows();
    this._renderTally(rows);
    this._renderLegend();

    if (!rows.length) {
      this.host.innerHTML = '<p class="empty">No property matches these filters.</p>';
      return;
    }

    const compare = {
      hp: (a, b) => a.hp - b.hp || a.name.localeCompare(b.name),
      name: (a, b) => a.name.localeCompare(b.name),
      leader: (a, b) => a.neighbourhood.localeCompare(b.neighbourhood) || a.hp - b.hp,
      variance: (a, b) => a.variance - b.variance,
      gaps: (a, b) => b.counts.gap - a.counts.gap || a.hp - b.hp,
    }[this.sort];

    const sorted = [...rows].sort(compare);

    if (!this.group) {
      this.host.innerHTML = sorted.map((r) => this._card(r)).join('');
      this.setSelected(this.selectedProperty);
      return;
    }

    const groups = new Map();
    for (const r of sorted) {
      if (!groups.has(r.neighbourhood)) groups.set(r.neighbourhood, []);
      groups.get(r.neighbourhood).push(r);
    }

    // Unassigned last, always — it is a data-quality bucket, not a real book,
    // and it should never lead the list.
    const order = [...groups.keys()].sort((a, b) => {
      if (a === 'Unassigned') return 1;
      if (b === 'Unassigned') return -1;
      if (this.sort === 'hp' || this.sort === 'variance' || this.sort === 'gaps') {
        return mean(groups.get(a)) - mean(groups.get(b));
      }
      return a.localeCompare(b);
    });

    this.host.innerHTML = order
      .map((k) => this._groupHead(k, groups.get(k)) + groups.get(k).map((r) => this._card(r)).join(''))
      .join('');
    this.setSelected(this.selectedProperty);
  }

  _renderTally(rows) {
    const crit = rows.filter((r) => r.hp < 40).length;
    const watch = rows.filter((r) => r.hp >= 40 && r.hp <= 70).length;
    const gaps = rows.reduce((s, r) => s + r.counts.gap, 0);
    const variance = rows.reduce((s, r) => s + r.variance, 0);

    this.head.innerHTML =
      `<span class="rchip crit"><i></i>Critical <b>${crit}</b></span>` +
      `<span class="rchip watch"><i></i>Watch <b>${watch}</b></span>` +
      `<span class="rchip ok"><i></i>Steady <b>${rows.length - crit - watch}</b></span>` +
      (gaps ? `<span class="rchip gap" title="Parcels whose feed stopped reporting"><i></i>No data <b>${gaps}</b></span>` : '') +
      `<span class="rchip" title="Sum of every tracked budget line">Variance <b class="${variance < 0 ? 'bad' : 'good'}">${money(variance)}</b></span>`;
  }

  _renderLegend() {
    const el = document.getElementById('roster-legend');
    if (!el || el.dataset.built === String(this.kpis.length)) return;
    el.dataset.built = String(this.kpis.length);
    el.innerHTML = this.kpis
      .map((k) => `<div><span class="pip">${glyph(k)}</span>${k.parcel} · ${escapeHtml(k.label)}</div>`)
      .join('');
  }

  _groupHead(name, list) {
    const avg = Math.round(mean(list));
    const band = hpBand(avg);
    return (
      `<div class="ghead${name === 'Unassigned' ? ' unassigned' : ''}">` +
      `<span class="nm">${escapeHtml(name)}</span>` +
      `<span class="ct">${list.length} ${list.length === 1 ? 'property' : 'properties'}</span>` +
      `<span class="avg ${band}"><em>avg</em><span class="segs">${segments(avg)}</span>` +
      `<span class="hpnum">${avg}</span></span></div>`
    );
  }

  _card(r) {
    const band = hpBand(r.hp);
    const sub = r.director
      ? `${escapeHtml(r.director)}${this.group ? '' : ` · ${escapeHtml(r.neighbourhood)}`}`
      : `<span class="faint">${this.group ? 'no director on file' : escapeHtml(r.neighbourhood)}</span>`;

    return (
      `<article class="rcard ${band}" data-id="${escapeHtml(r.landmarkId)}" data-name="${escapeHtml(r.name)}" tabindex="0">` +
      `<div class="rid"><span class="prop">${escapeHtml(r.name)}</span>` +
      `<span class="dir">${sub}</span></div>` +
      `<div class="hpnum">${r.hp}</div>` +
      `<div class="segs">${segments(r.hp)}</div>` +
      `<div class="var ${r.variance < 0 ? 'over' : ''}">${r.variance ? money(r.variance) : '—'}</div>` +
      `<div class="pips">${r.cells.map((c) => pip(c)).join('')}</div>` +
      `</article>`
    );
  }
}

function mean(list) {
  return list.reduce((s, r) => s + r.hp, 0) / list.length;
}

function segments(hp) {
  const on = Math.round((hp / 100) * SEGMENTS);
  return Array.from({ length: SEGMENTS }, (_, i) => `<span class="seg${i < on ? ' on' : ''}"></span>`).join('');
}

function glyph(kpi) {
  const path = ICONS[kpi.icon];
  // The parcel number is the fallback and it is not a poor one: on this map
  // position IS the KPI's identity.
  return path
    ? `<svg viewBox="0 0 12 12" aria-hidden="true">${path}</svg>`
    : `<b>${escapeHtml(kpi.parcel)}</b>`;
}

function pip(cell) {
  const title = `${cell.kpi.parcel} · ${cell.kpi.label} — ${STATE_LABEL[cell.state]}${
    cell.detail ? `\n${cell.detail}` : ''
  }`;
  const inner = cell.state === 'na' || cell.state === 'wait' ? '' : glyph(cell.kpi);
  return `<span class="pip ${cell.state}" title="${escapeHtml(title)}">${inner}</span>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]),
  );
}
