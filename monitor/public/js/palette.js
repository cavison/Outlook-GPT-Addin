// Single source of truth for status colour, shared by the 3D scene and the HUD
// so a red building and a red list row are always the same red.

// Validated with the dataviz palette validator (dark surface, all pairs):
// worst CVD ΔE 9.4, worst normal-vision ΔE 17.2, all ≥3:1 contrast.
//
// `blocked` is violet rather than the obvious orange: against `warning` yellow
// an orange scored ΔE 12.4 on normal vision — below the 15 floor — so two
// different severities were near-indistinguishable at a glance.
export const STATUS_COLOUR = {
  failed: 0xff4d5a,
  blocked: 0xb57bff,
  warning: 0xffd23f,
  running: 0x4fc3f7,
  healthy: 0x5be7a9,
  paused: 0x8892a6,
  unknown: 0x6b7280,
};

// Secondary encoding: severity must never be carried by colour alone, so each
// attention state gets its own beacon glyph too.
export const STATUS_GLYPH = {
  failed: '✕',
  blocked: '‖',
  warning: '!',
};

export const STATUS_LABEL = {
  failed: 'Failed',
  blocked: 'Blocked',
  warning: 'Degraded',
  running: 'Running',
  healthy: 'Healthy',
  paused: 'Paused',
  unknown: 'Unknown',
};

export const ATTENTION = new Set(['failed', 'blocked', 'warning']);

/** Worst first — matches the server's ordering. */
const RANK = { failed: 0, blocked: 1, warning: 2, running: 3, healthy: 4, paused: 5, unknown: 6 };
export function statusRank(status) {
  return RANK[status] ?? RANK.unknown;
}

export const hex = (n) => `#${n.toString(16).padStart(6, '0')}`;

export function statusColour(status) {
  return STATUS_COLOUR[status] ?? STATUS_COLOUR.unknown;
}

// Diverging ramp for signed domain metrics (over/under, ahead/behind, +/-).
// Two opposed hues with a NEUTRAL GREY midpoint — a hue at the midpoint would
// imply "nothing" is itself a value. Deliberately blue↔red, which is distinct
// from the status language above; the two never appear at the same time,
// because the view mode switches between them.
export const DIVERGING = {
  low: 0x3987e5, // under / below plan
  mid: 0x9aa0a6, // exactly at the midpoint
  high: 0xe34948, // over / above plan
};

/** Mix two 0xRRGGBB colours in sRGB. Good enough for a lit 3D surface. */
function mixHex(a, b, t) {
  const ar = (a >> 16) & 255, ag = (a >> 8) & 255, ab = a & 255;
  const br = (b >> 16) & 255, bg = (b >> 8) & 255, bb = b & 255;
  return (
    ((Math.round(ar + (br - ar) * t) << 16) |
      (Math.round(ag + (bg - ag) * t) << 8) |
      Math.round(ab + (bb - ab) * t)) >>> 0
  );
}

/**
 * Colour for a declared metric. Diverging metrics are normalized around their
 * midpoint so that "on plan" always lands on grey regardless of the domain.
 */
export function metricColour(metric) {
  const [lo, hi] = metric.domain;
  if (metric.mode === 'sequential') {
    const t = Math.max(0, Math.min(1, (metric.value - lo) / (hi - lo || 1)));
    return mixHex(0xcde2fb, 0x104281, t);
  }
  const mid = metric.midpoint ?? 0;
  const reach = Math.max(Math.abs(hi - mid), Math.abs(mid - lo)) || 1;
  const t = Math.max(-1, Math.min(1, (metric.value - mid) / reach));
  return t >= 0
    ? mixHex(DIVERGING.mid, DIVERGING.high, t)
    : mixHex(DIVERGING.mid, DIVERGING.low, -t);
}

/** Stable pseudo-random in [0,1) from a string — keeps building variation fixed
 *  across reloads so the city stays recognisable. */
export function hash01(str, salt = 0) {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}
