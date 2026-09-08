import { CELL_STATES, STATE_LABEL } from './portfolio.js';

// Filters sit above the map and drive the map and the roster from one state.
//
// Two views of the same portfolio disagreeing about what is on screen is worse
// than having no filter at all, so there is one filter object and both sides
// read it. Filtering never deletes anything: a hex that does not match is
// pushed down and greyed rather than removed, because the shape of the
// neighbourhood is part of what you are reading and a map with holes in it is a
// different map.

export const HEIGHT_VARIANTS = {
  worst: {
    label: 'Worst KPI',
    hint: 'Each pillar is its own reading. The default, and the honest one.',
  },
  focus: {
    label: 'One KPI',
    hint: 'Only the chosen KPI stands up. Everything else lies flat.',
  },
  flat: {
    label: 'Flat',
    hint: 'Nothing stands up. Colour and the roster carry it — for reading the map as a plan.',
  },
};

export class Filters {
  constructor({ onChange }) {
    this.onChange = onChange;
    this.state = {
      neighbourhood: null,
      band: null,       // 'failing' | 'watch' | 'steady' | 'gap'
      kpi: null,        // a KPI id: show properties where THIS one is a problem
      height: 'worst',
    };
    this.registry = {};
    this.neighbourhoods = [];

    this.bar = document.getElementById('filterbar');
    this.bar.addEventListener('click', (e) => {
      const chip = e.target.closest('[data-filter]');
      if (!chip) return;
      const { filter, value } = chip.dataset;
      if (filter === 'clear') { this.clear(); return; }
      // Clicking the active chip clears it. A filter you cannot get out of by
      // clicking the thing you clicked to get in is a trap.
      this.state[filter] = this.state[filter] === value ? null : value || null;
      // Height is a variant, not a filter: there is no "no height".
      if (filter === 'height' && !this.state.height) this.state.height = 'worst';
      this.render();
      this.onChange(this);
    });
    this.bar.addEventListener('change', (e) => {
      const select = e.target.closest('[data-select]');
      if (!select) return;
      this.state[select.dataset.select] = select.value || null;
      this.render();
      this.onChange(this);
    });
  }

  setRegistry(registry) {
    this.registry = registry ?? {};
    this.render();
  }

  setNeighbourhoods(names) {
    const next = [...names].sort();
    if (next.join('|') === this.neighbourhoods.join('|')) return;
    this.neighbourhoods = next;
    this.render();
  }

  get height() {
    return this.state.height;
  }

  /** The KPI a `focus` height variant should raise, or null. */
  get focusKpi() {
    return this.state.height === 'focus' ? this.state.kpi : null;
  }

  get active() {
    return Boolean(this.state.neighbourhood || this.state.band || this.state.kpi);
  }

  /** A predicate over roster rows. Both the map and the roster use this one. */
  predicate() {
    const { neighbourhood, band, kpi } = this.state;
    if (!neighbourhood && !band && !kpi) return null;

    return (row) => {
      if (neighbourhood && row.neighbourhood !== neighbourhood) return false;
      if (kpi) {
        const cell = row.cellByKpi.get(kpi);
        if (!cell) return false;
        // With a KPI chosen and no band, "show me signage" means show me the
        // properties where signage is a problem — not all 185 of them.
        if (!band && !['fail', 'warn', 'gap'].includes(cell.state)) return false;
        if (band && !matchesBand(cell.state, cell.severity, band)) return false;
        return true;
      }
      if (band) {
        if (band === 'gap') return row.counts.gap > 0;
        if (band === 'failing') return row.hp < 40;
        if (band === 'watch') return row.hp >= 40 && row.hp <= 70;
        if (band === 'steady') return row.hp > 70;
      }
      return true;
    };
  }

  render() {
    const kpis = Object.values(this.registry)
      .filter((k) => k.parcel)
      .sort((a, b) => a.parcel.localeCompare(b.parcel));

    const chip = (filter, value, label, cls = '') =>
      `<button class="fchip ${cls}${this.state[filter] === value ? ' on' : ''}" ` +
      `data-filter="${filter}" data-value="${value}">${label}</button>`;

    const groups = [
      `<div class="fgroup"><span class="flabel">Neighbourhood</span>` +
        `<select data-select="neighbourhood"><option value="">All</option>` +
        this.neighbourhoods
          .map(
            (n) =>
              `<option value="${escapeHtml(n)}"${this.state.neighbourhood === n ? ' selected' : ''}>${escapeHtml(n)}</option>`,
          )
          .join('') +
        `</select></div>`,

      `<div class="fgroup"><span class="flabel">Show</span>` +
        chip('band', 'failing', 'Failing', 'crit') +
        chip('band', 'watch', 'Watch', 'watch') +
        chip('band', 'steady', 'Steady', 'ok') +
        chip('band', 'gap', 'No data', 'gap') +
        `</div>`,

      `<div class="fgroup"><span class="flabel">KPI</span>` +
        `<select data-select="kpi"><option value="">Any</option>` +
        kpis
          .map(
            (k) =>
              `<option value="${escapeHtml(k.id)}"${this.state.kpi === k.id ? ' selected' : ''}>` +
              `${escapeHtml(k.parcel)} · ${escapeHtml(k.label)}</option>`,
          )
          .join('') +
        `</select></div>`,

      `<div class="fgroup"><span class="flabel" title="What pillar height means">Height</span>` +
        Object.entries(HEIGHT_VARIANTS)
          .map(
            ([id, v]) =>
              `<button class="fchip${this.state.height === id ? ' on' : ''}" data-filter="height" ` +
              `data-value="${id}" title="${escapeHtml(v.hint)}">${v.label}</button>`,
          )
          .join('') +
        `</div>`,
    ];

    // "One KPI" with nothing chosen would silently flatten the whole map, so
    // say what is missing rather than looking broken.
    const warn =
      this.state.height === 'focus' && !this.state.kpi
        ? '<span class="fwarn">Pick a KPI above — nothing is raised until you do.</span>'
        : '';

    const clear = this.active
      ? '<button class="fchip clear" data-filter="clear" data-value="">Clear filters</button>'
      : '';

    this.bar.innerHTML = groups.join('') + warn + `<span class="fspacer"></span>` + clear;
  }

  clear() {
    this.state.neighbourhood = null;
    this.state.band = null;
    this.state.kpi = null;
    this.render();
    this.onChange(this);
  }
}

function matchesBand(state, severity, band) {
  if (band === 'gap') return state === 'gap';
  if (band === 'failing') return state === 'fail';
  if (band === 'watch') return state === 'warn';
  if (band === 'steady') return state === 'met';
  return true;
}

export { CELL_STATES, STATE_LABEL };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]),
  );
}
