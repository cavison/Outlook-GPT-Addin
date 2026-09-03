import {
  STATUS_LABEL, STATUS_GLYPH, statusColour, metricColour, hex, ATTENTION, DIVERGING,
} from './palette.js';

const $ = (id) => document.getElementById(id);

function relative(ms) {
  if (ms == null) return '—';
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h}h`;
  return `${Math.round(h / 24)}d`;
}

function clockTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export class Hud {
  constructor({ onSelect, onAction, onAcknowledge, onRefresh, onSignIn, onViewMode }) {
    this.viewMode = 'health';
    this.onSelect = onSelect;
    this.onAction = onAction;
    this.onAcknowledge = onAcknowledge;
    this.state = { entities: new Map(), game: null, config: {} };
    this.selectedId = null;
    this.pendingConfirm = null;

    // Delegated once, so rows can be re-rendered without losing their handler
    // (and without a click landing on a node that was just replaced).
    $('alert-list').addEventListener('click', (e) => {
      const row = e.target.closest('.alert');
      if (row) this.onSelect(row.dataset.id);
    });

    for (const btn of document.querySelectorAll('.mode')) {
      btn.addEventListener('click', () => onViewMode(btn.dataset.mode));
    }

    $('refresh').addEventListener('click', onRefresh);
    $('detail-close').addEventListener('click', () => this.select(null, true));
    $('signin-start').addEventListener('click', onSignIn);
    $('signin-dismiss').addEventListener('click', () => $('signin').classList.add('hidden'));

    // Keep incident ages ticking without waiting for a poll.
    setInterval(() => this.renderAlerts(), 1000);
  }

  setEntities(entities) {
    this.state.entities = entities;
    this.renderLegend();
  }

  setViewMode(mode) {
    this.viewMode = mode;
    for (const btn of document.querySelectorAll('.mode')) {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    }
    this.renderLegend();
  }

  /**
   * A map where height means different things in different districts is
   * unreadable without this. The legend is generated from the encodings the
   * providers actually declared, so it can never drift from what is drawn.
   */
  renderLegend() {
    const entities = [...this.state.entities.values()];
    if (!entities.length) return;

    // One entry per (district, encoding) pair actually present.
    const byDistrict = new Map();
    for (const e of entities) {
      if (!e.encode?.height && !e.encode?.metric) continue;
      if (!byDistrict.has(e.district)) byDistrict.set(e.district, e.encode);
    }

    const groups = [];

    const heightGeneric = entities.some((e) => !e.encode?.height);
    if (heightGeneric) {
      groups.push(`
        <div class="legend-group">
          <div class="legend-title">Building height</div>
          <div class="legend-sub">Activity volume</div>
          <div class="height-key"><i style="height:30%"></i><i style="height:55%"></i><i style="height:80%"></i><i style="height:100%"></i></div>
        </div>`);
    }

    for (const [district, encode] of byDistrict) {
      const parts = [`<div class="legend-title">${escapeHtml(district)}</div>`];
      if (encode.height) {
        parts.push(`<div class="legend-sub">Height — ${escapeHtml(encode.height.label)}</div>`);
        parts.push('<div class="height-key"><i style="height:30%"></i><i style="height:55%"></i><i style="height:80%"></i><i style="height:100%"></i></div>');
      }
      if (encode.metric && this.viewMode === 'metric') {
        const [lo, hi] = encode.metric.domain;
        parts.push(`<div class="legend-sub">Colour — ${escapeHtml(encode.metric.label)}</div>`);
        parts.push(
          `<div class="ramp" style="background:linear-gradient(90deg,${hex(DIVERGING.low)},${hex(DIVERGING.mid)},${hex(DIVERGING.high)})"></div>` +
          `<div class="ramp-labels"><span>${formatSigned(lo, encode.metric.unit)}</span>` +
          `<span>on plan</span><span>${formatSigned(hi, encode.metric.unit)}</span></div>`,
        );
      }
      groups.push(`<div class="legend-group">${parts.join('')}</div>`);
    }

    if (this.viewMode !== 'metric') {
      groups.push(`
        <div class="legend-group">
          <div class="legend-title">Status colour</div>
          ${['failed', 'blocked', 'warning', 'running', 'healthy', 'paused']
            .map((s) => {
              const c = hex(statusColour(s));
              const glyph = STATUS_GLYPH[s];
              return `<div class="legend-row">${
                glyph
                  ? `<span class="glyph" style="background:${c}">${glyph}</span>`
                  : `<span class="swatch" style="background:${c}"></span>`
              }<span>${STATUS_LABEL[s]}</span></div>`;
            })
            .join('')}
        </div>`);
    }

    $('legend-body').innerHTML = groups.join('');
  }

  setConfig(config) {
    this.state.config = config;
  }

  setGame(game) {
    this.state.game = game;
    this.renderGame();
    this.renderAlerts();
  }

  setProviders(providers) {
    $('providers').innerHTML = providers
      .map(
        (p) =>
          `<span class="provider-dot ${p.ok ? '' : 'bad'}" title="${
            p.error ? String(p.error).replace(/"/g, "'") : `${p.count} items`
          }"><i></i>${p.label}</span>`,
      )
      .join('');
  }

  setPollStatus(text) {
    $('poll').textContent = text;
  }

  // -- score ---------------------------------------------------------------

  renderGame() {
    const g = this.state.game;
    if (!g) return;
    $('level-chip').textContent = g.level;
    $('xp-fill').style.width = `${Math.round(g.pct * 100)}%`;
    $('xp-text').textContent = `${g.into} / ${g.need} XP · ${g.xp} total`;
    $('streak').textContent = g.streak;
    $('terraform').textContent = `${Math.round(g.terraform * 100)}%`;

    $('quest-list').innerHTML = (g.quests?.items ?? [])
      .map(
        (q) => `
        <div class="quest ${q.done ? 'done' : ''}">
          <span class="tick">${q.done ? '✓' : ''}</span>
          <span class="label">${q.label}</span>
          <span class="prog">${Math.min(q.progress, q.target)}/${q.target}</span>
        </div>`,
      )
      .join('');

    $('feed').innerHTML = g.events
      .slice(0, 18)
      .map(
        (e) => `
        <div class="feed-item ${e.kind}">
          <span class="when">${clockTime(e.at)}</span>
          <span class="what">${escapeHtml(e.text)}</span>
          ${e.xp ? `<span class="xp">+${e.xp}</span>` : ''}
        </div>`,
      )
      .join('');
  }

  // -- alert queue ---------------------------------------------------------

  renderAlerts() {
    const incidents = new Map(
      (this.state.game?.incidents ?? []).map((i) => [i.entityId, i]),
    );
    const rows = [...this.state.entities.values()]
      .filter((e) => ATTENTION.has(e.status))
      .sort((a, b) => {
        const ia = incidents.get(a.id)?.openedAt ?? Infinity;
        const ib = incidents.get(b.id)?.openedAt ?? Infinity;
        return ia - ib; // oldest unresolved first — age is the thing that matters
      });

    const count = $('alert-count');
    count.textContent = rows.length;
    count.classList.toggle('hot', rows.length > 0);

    const list = $('alert-list');
    if (!rows.length) {
      if (this.alertSignature !== 'empty') {
        list.innerHTML = '<p class="empty">Nothing needs you. The colony is quiet.</p>';
        this.alertSignature = 'empty';
      }
      return;
    }

    // Ages tick every second, but replacing the whole list that often meant a
    // click could land on a node that had just been detached. Rebuild only when
    // the rows themselves change; otherwise update the ages in place.
    const signature = rows
      .map((e) => `${e.id}:${e.status}:${e.detail}:${incidents.get(e.id)?.attended ? 1 : 0}`)
      .join('|') + `:${this.selectedId}`;

    if (signature !== this.alertSignature) {
      this.alertSignature = signature;
      list.innerHTML = rows
        .map((e) => {
          const incident = incidents.get(e.id);
          return `
          <div class="alert ${e.id === this.selectedId ? 'selected' : ''}" data-id="${e.id}">
            <span class="bar" style="background:${hex(statusColour(e.status))}"></span>
            <span>
              <span class="name">${escapeHtml(e.name)}</span>
              <span class="sub">${escapeHtml(e.district)} · ${escapeHtml(e.detail)}</span>
            </span>
            <span class="age ${incident?.attended ? 'attended' : ''}"
                  title="${incident?.attended ? 'Acknowledged' : 'Not yet triaged'}"></span>
          </div>`;
        })
        .join('');
    }

    for (const row of list.querySelectorAll('.alert')) {
      const incident = incidents.get(row.dataset.id);
      const age = incident ? relative(Date.now() - incident.openedAt) : '—';
      const text = `${incident?.attended ? '✓ ' : ''}${age}`;
      const cell = row.querySelector('.age');
      if (cell.textContent !== text) cell.textContent = text;
    }
  }

  // -- detail card ---------------------------------------------------------

  select(id, silent = false) {
    this.selectedId = id;
    this.pendingConfirm = null;
    this.renderDetail();
    this.renderAlerts();
    if (!silent && id) this.onSelect(id, true);
  }

  renderDetail() {
    const panel = $('detail');
    const entity = this.selectedId ? this.state.entities.get(this.selectedId) : null;
    if (!entity) {
      panel.classList.add('hidden');
      return;
    }
    panel.classList.remove('hidden');

    const colour = hex(statusColour(entity.status));
    const incident = (this.state.game?.incidents ?? []).find((i) => i.entityId === entity.id);
    const problem = ATTENTION.has(entity.status);
    const m = entity.metrics ?? {};

    // Which numbers matter depends on what the thing IS. A property has no
    // "runs today", and showing four em-dashes is worse than showing nothing.
    const metrics = entity.encode?.height || entity.encode?.metric
      ? [
          ...(m.budget != null ? [['Budget', formatSigned(m.budget, '$').replace('+', '')]] : []),
          ...(m.actual != null ? [['Actual', formatSigned(m.actual, '$').replace('+', '')]] : []),
          ...(m.variance != null ? [['Variance', formatSigned(m.variance, '$')]] : []),
          ...(m.variancePct != null ? [['Variance %', `${(m.variancePct * 100).toFixed(1)}%`]] : []),
          ...(m.phase ? [['Phase', m.phase]] : []),
          ...(m.stalledDays ? [['Stalled', `${m.stalledDays} days`]] : []),
        ]
      : [
          ['Last run', m.lastRunAt ? relative(Date.now() - new Date(m.lastRunAt)) + ' ago' : '—'],
          ['Runs today', m.runsToday ?? '—'],
          ['Failures today', m.failuresToday ?? '—'],
          ['Success rate', m.successRate != null ? `${Math.round(m.successRate * 100)}%` : '—'],
        ];

    const writesAllowed = this.state.config.allowWriteActions !== false;

    $('detail-body').innerHTML = `
      <div class="detail-head">
        <div class="kind">${escapeHtml(entity.district)} · ${escapeHtml(entity.kind)}</div>
        <h3>${escapeHtml(entity.name)}</h3>
        <span class="chip" style="background:${colour}22;color:${colour}">
          <i></i>${STATUS_LABEL[entity.status] ?? entity.status}
        </span>
        ${
          incident
            ? `<span class="chip" style="background:#ffffff12;color:#96a3bd">
                 open ${relative(Date.now() - incident.openedAt)}${incident.attended ? ' · triaged' : ''}
               </span>`
            : ''
        }
      </div>
      <div class="detail-detail ${problem ? 'problem' : ''}">${escapeHtml(entity.detail || '—')}</div>
      <dl class="metrics">
        ${metrics
          .map(([k, v]) => `<div class="metric"><dt>${k}</dt><dd>${escapeHtml(String(v))}</dd></div>`)
          .join('')}
      </dl>
      ${this.pendingConfirm ? this.confirmHtml(entity) : ''}
      <div class="actions">
        ${
          incident && !incident.attended
            ? '<button class="primary" data-ack="1">Acknowledge (+10 XP)</button>'
            : ''
        }
        ${
          entity.url
            ? `<a href="${entity.url}" target="_blank" rel="noopener">
                 <button class="ghost">Open in ${entity.source === 'graph' ? 'Outlook' : 'Power Automate'}</button>
               </a>`
            : ''
        }
        ${entity.actions
          .map(
            (a) =>
              `<button class="${a.danger ? 'danger' : 'ghost'}" data-action="${a.id}"
                       ${a.write && !writesAllowed ? 'disabled title="Write actions disabled"' : ''}>
                 ${escapeHtml(a.label)}
               </button>`,
          )
          .join('')}
        ${
          entity.actions.some((a) => a.write) && writesAllowed
            ? '<span class="hint">Write actions run against your real tenant.</span>'
            : ''
        }
      </div>`;

    const body = $('detail-body');
    body.querySelector('[data-ack]')?.addEventListener('click', () => this.onAcknowledge(entity.id));
    for (const btn of body.querySelectorAll('[data-action]')) {
      btn.addEventListener('click', () => this.requestAction(entity, btn.dataset.action));
    }
    body.querySelector('[data-confirm-yes]')?.addEventListener('click', () => {
      const pending = this.pendingConfirm;
      this.pendingConfirm = null;
      this.renderDetail();
      this.onAction(entity.id, pending.actionId);
    });
    body.querySelector('[data-confirm-no]')?.addEventListener('click', () => {
      this.pendingConfirm = null;
      this.renderDetail();
    });
  }

  confirmHtml(entity) {
    const action = entity.actions.find((a) => a.id === this.pendingConfirm.actionId);
    return `
      <div class="confirm">
        <p><strong>${escapeHtml(action.label)}</strong> on <strong>${escapeHtml(entity.name)}</strong>.
        ${escapeHtml(action.hint || 'This changes something in your tenant.')}</p>
        <div class="row">
          <button class="${action.danger ? 'danger' : 'primary'}" data-confirm-yes>Yes, do it</button>
          <button class="ghost" data-confirm-no>Cancel</button>
        </div>
      </div>`;
  }

  /** Write actions always route through a confirm step — one stray click must
   *  never be able to fire or stop a production flow. */
  requestAction(entity, actionId) {
    const action = entity.actions.find((a) => a.id === actionId);
    if (!action) return;
    const needsConfirm = action.write && this.state.config.requireConfirmForWrites !== false;
    if (needsConfirm) {
      this.pendingConfirm = { actionId };
      this.renderDetail();
    } else {
      this.onAction(entity.id, actionId);
    }
  }

  toast(message, kind = '') {
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.textContent = message;
    $('toasts').appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  showSignIn(status) {
    if (!status.configured || status.signedIn) {
      $('signin').classList.add('hidden');
      return;
    }
    $('signin').classList.remove('hidden');
  }

  showDeviceCode(code) {
    if (!code) return;
    const el = $('device-code');
    el.classList.remove('hidden');
    el.innerHTML = `
      Go to <strong>${code.verificationUri}</strong> and enter:
      <code>${code.userCode}</code>
      Leave this open — the colony connects itself once you finish.`;
  }
}

function formatSigned(value, unit) {
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  const n = Math.abs(value);
  const short = n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : `${Math.round(n)}`;
  return unit === '$' ? `${sign}$${short}` : `${sign}${short}${unit}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]),
  );
}
