// Single source of truth for status colour, shared by the 3D scene and the HUD
// so a red building and a red list row are always the same red.

export const STATUS_COLOUR = {
  failed: 0xff4d5a,
  blocked: 0xff9f3c,
  warning: 0xffd23f,
  running: 0x4fc3f7,
  healthy: 0x5be7a9,
  paused: 0x8892a6,
  unknown: 0x6b7280,
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

export const hex = (n) => `#${n.toString(16).padStart(6, '0')}`;

export function statusColour(status) {
  return STATUS_COLOUR[status] ?? STATUS_COLOUR.unknown;
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
