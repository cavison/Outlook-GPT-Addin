import * as THREE from 'three';
import { statusColour, hash01 } from './palette.js';

// Procedural buildings from primitives. No asset pipeline, no model licensing,
// and every flow gets a silhouette that stays the same across restarts because
// the variation is seeded from the entity id.

const SHELL = new THREE.MeshStandardMaterial({ color: 0xdfe7f5, roughness: 0.55, metalness: 0.1 });
const SHELL_DARK = new THREE.MeshStandardMaterial({ color: 0x93a6c6, roughness: 0.6, metalness: 0.2 });
const ACCENT = new THREE.MeshStandardMaterial({ color: 0xe23b4e, roughness: 0.5 });
const TRIM = new THREE.MeshStandardMaterial({ color: 0x4a5f86, roughness: 0.5 });

// Geometry is shared across every building; only transforms and the status
// material differ. Keeps a few hundred buildings cheap.
const GEO = {
  pad: new THREE.CylinderGeometry(1.05, 1.15, 0.18, 12),
  drum: new THREE.CylinderGeometry(0.62, 0.7, 1, 12),
  box: new THREE.BoxGeometry(1.1, 1, 1.1),
  dome: new THREE.SphereGeometry(0.62, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2),
  sphere: new THREE.SphereGeometry(0.42, 14, 10),
  mast: new THREE.CylinderGeometry(0.055, 0.055, 1, 6),
  ring: new THREE.TorusGeometry(0.72, 0.06, 8, 24),
  dish: new THREE.SphereGeometry(0.55, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2.6),
  fin: new THREE.BoxGeometry(0.12, 0.5, 0.62),
  crate: new THREE.BoxGeometry(0.26, 0.26, 0.26),
  // Cone with 4 sides = a pitched roof once rotated 45°.
  roof: new THREE.ConeGeometry(0.92, 0.62, 4),
  relayPad: new THREE.CylinderGeometry(0.24, 0.28, 0.1, 6),
  pillar: new THREE.BoxGeometry(0.72, 1, 0.72),
  pillarCap: new THREE.BoxGeometry(0.86, 0.12, 0.86),
  lamp: new THREE.SphereGeometry(0.17, 8, 6),
  chimney: new THREE.BoxGeometry(0.2, 0.5, 0.2),
};

// Worn by everything that is not participating in the active metric view, so a
// metric map never has stray status colour competing with its ramp.
export const NEUTRAL_SHELL = new THREE.MeshStandardMaterial({
  color: 0x9aa3b4,
  roughness: 0.75,
  metalness: 0.05,
});
// A dead lamp. Deliberately darker than the deck it stands on, so an unlit unit
// reads as a hole in the field rather than merely a duller light.
export const UNLIT = new THREE.MeshStandardMaterial({
  color: 0x2a3242,
  roughness: 0.9,
  metalness: 0,
});

export const NEUTRAL_SIGNAL = new THREE.MeshStandardMaterial({
  color: 0x76809a,
  roughness: 0.7,
  metalness: 0.05,
});

/** One emissive material per status, shared and animated centrally. */
const statusMaterials = new Map();
export function statusMaterial(status) {
  if (!statusMaterials.has(status)) {
    const colour = statusColour(status);
    statusMaterials.set(
      status,
      new THREE.MeshStandardMaterial({
        color: colour,
        emissive: colour,
        emissiveIntensity: 0.45,
        roughness: 0.3,
        metalness: 0.1,
      }),
    );
  }
  return statusMaterials.get(status);
}

export function allStatusMaterials() {
  return statusMaterials;
}

function mesh(geo, mat, { x = 0, y = 0, z = 0, sx = 1, sy = 1, sz = 1, ry = 0, rx = 0 } = {}) {
  const m = new THREE.Mesh(geo, mat);
  m.position.set(x, y, z);
  m.scale.set(sx, sy, sz);
  m.rotation.y = ry;
  m.rotation.x = rx;
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

/**
 * Build one structure. `signal` is the mesh whose emissive colour carries
 * status — the renderer swaps its material on every status change, so the
 * archetypes below only have to nominate which part glows.
 */
/** Height range in world units. A common baseline plus a bounded range is what
 *  makes two buildings comparable at a glance. */
const MIN_HEIGHT = 0.55;
const MAX_HEIGHT = 3.4;

// Pillars: a flat plinth at zero, capped so one catastrophic KPI cannot make a
// spike that hides the rest of the city behind it.
const PILLAR_MIN = 0.12;
const PILLAR_MAX = 6.0;

/**
 * Resolve a building's height.
 *
 * When a provider declares `encode.height`, magnitude is mapped onto height and
 * height ALONE — the footprint never changes. Scaling all three axes would make
 * a 2x value look 8x, and volume is the channel people misjudge worst.
 */
export function heightFor(entity) {
  // Severity wins: for a portfolio overview, height means "how bad", and a
  // property with nothing wrong should read as flat ground.
  const severity = entity.encode?.severity;
  if (severity) return PILLAR_MIN + severity.value * (PILLAR_MAX - PILLAR_MIN);

  const spec = entity.encode?.height;
  if (!spec) return 0.75 + entity.weight * 0.55 + hash01(entity.id, 1) * 0.4;

  const [lo, hi] = spec.domain;
  const t = Math.max(0, Math.min(1, (spec.value - lo) / (hi - lo)));
  // Square root so the tallest value does not dwarf everything else into
  // unreadable stubs; still monotonic, so bigger always means bigger.
  return MIN_HEIGHT + Math.sqrt(t) * (MAX_HEIGHT - MIN_HEIGHT);
}

export function createBuilding(entity) {
  const group = new THREE.Group();
  const r1 = hash01(entity.id, 1);
  const r2 = hash01(entity.id, 2);
  const r3 = hash01(entity.id, 3);

  const height = heightFor(entity);
  const mat = statusMaterial(entity.status);
  const signals = [];
  // Parts that carry a domain metric in the diverging view. Kept separate from
  // `signals` so status and metric never fight over the same surface.
  const bodies = [];

  const form = entity.encode?.form ?? entity.kind;
  // Relays stand on a fine grid and bring their own footing; the landmark pad
  // would be wider than their whole slot.
  if (form !== 'relay' && form !== 'pillar') {
    group.add(mesh(GEO.pad, SHELL_DARK, { y: 0.09, ry: r1 * Math.PI }));
  }

  switch (form) {
    case 'pillar': {
      // Deliberately plain. Detail comes later and only where it earns its
      // place; right now the only job is that a bad KPI is visibly tall and a
      // good one is visibly flat.
      // Its own small plinth: the landmark pad is wider than a parcel spacing.
      group.add(mesh(GEO.pad, SHELL_DARK, { y: 0.04, sx: 0.62, sz: 0.62, sy: 0.45 }));
      const column = mesh(GEO.pillar, mat, { y: 0.02 + height / 2, sy: height });
      group.add(column);
      signals.push(column);
      bodies.push(column);

      // A cap only once the pillar has risen enough to have a top worth seeing.
      if (height > 0.9) {
        group.add(mesh(GEO.pillarCap, SHELL_DARK, { y: 0.02 + height + 0.06 }));
      }
      break;
    }
    case 'plot':
    case 'plot-landmark': {
      // A parcel with an address but no feed yet: a fenced construction plot.
      // Deliberately NOT a neutral empty space — "no data" must never look like
      // "nothing wrong", because that is how a KPI stops reporting and nobody
      // notices for a month.
      const big = form === 'plot-landmark';
      const r = big ? 1.45 : 1.0;

      const base = mesh(GEO.pad, SHELL_DARK, { y: 0.06, sx: r, sz: r, sy: 0.5 });
      group.add(base);
      bodies.push(base);

      // Corner posts, tape strung between them.
      for (let i = 0; i < 4; i++) {
        const a = (i / 4) * Math.PI * 2 + Math.PI / 4;
        group.add(mesh(GEO.mast, TRIM, {
          x: Math.cos(a) * r * 0.8,
          z: Math.sin(a) * r * 0.8,
          y: 0.34,
          sy: 0.5,
          sx: 0.6,
          sz: 0.6,
        }));
      }

      // The marker post. Its colour is the entity's status, so the moment a
      // connector starts feeding this parcel the plot lights up.
      const marker = mesh(GEO.crate, mat, {
        y: 0.62,
        sx: big ? 2.2 : 1.5,
        sy: big ? 2.2 : 1.5,
        sz: 0.35,
      });
      group.add(marker);
      signals.push(marker);
      break;
    }
    case 'relay': {
      // A small lamp on a post. Hundreds of these read as a lit field of
      // infrastructure; the eye picks out a DARK one instantly, which is
      // exactly the failure we care about — a flow that should be running and
      // isn't. Absence of light is a better encoding for "not running" than any
      // colour could be, because it is literally what it means.
      group.add(mesh(GEO.relayPad, SHELL_DARK, { y: 0.05 }));
      group.add(mesh(GEO.mast, TRIM, { y: 0.32, sy: 0.55, sx: 0.7, sz: 0.7 }));
      const lamp = mesh(GEO.lamp, mat, { y: 0.62 });
      group.add(lamp);
      signals.push(lamp);
      // Statuses that mean "not running" go dark rather than glowing.
      group.userData.unlitStatuses = new Set(['blocked', 'paused', 'unknown']);
      break;
    }
    case 'house': {
      // A house: fixed footprint, storeys stacked upward. Height is the whole
      // message, so the silhouette must make height easy to compare.
      const body = mesh(GEO.box, SHELL, {
        y: 0.18 + height / 2,
        sy: height,
        sx: 0.92,
        sz: 0.92,
      });
      group.add(body);
      bodies.push(body);

      const roof = mesh(GEO.roof, SHELL_DARK, {
        y: 0.18 + height + 0.28,
        ry: Math.PI / 4,
        sx: 1.12,
        sz: 1.12,
      });
      group.add(roof);
      bodies.push(roof);

      group.add(mesh(GEO.chimney, SHELL_DARK, { x: 0.3, y: 0.18 + height + 0.5, z: 0.22 }));

      // Status rides a lit band at the eaves — small, and never the thing that
      // encodes the money.
      const band = mesh(GEO.crate, mat, {
        y: 0.18 + height - 0.06,
        sx: 3.7,
        sy: 0.22,
        sz: 3.7,
      });
      group.add(band);
      signals.push(band);
      break;
    }
    case 'mailbox':
    case 'approval': {
      // Wide low block with a lit strip along the roof.
      const body = mesh(GEO.box, SHELL, { y: 0.18 + height / 2, sy: height, sx: 1.15, sz: 0.95 });
      group.add(body);
      const strip = mesh(GEO.crate, mat, { y: 0.18 + height + 0.06, sx: 3.4, sy: 0.28, sz: 0.9 });
      group.add(strip);
      signals.push(strip);
      group.add(mesh(GEO.crate, ACCENT, { x: 0.62, y: 0.36, z: 0.5, sy: 0.7 }));
      break;
    }
    case 'job':
    case 'subscription': {
      // Silo/tank with a banded ring.
      const drum = mesh(GEO.drum, SHELL, { y: 0.18 + height / 2, sy: height, sx: 1.05, sz: 1.05 });
      group.add(drum);
      const ring = mesh(GEO.ring, mat, { y: 0.18 + height * 0.62, rx: Math.PI / 2, sx: 0.95, sy: 0.95 });
      group.add(ring);
      signals.push(ring);
      const cap = mesh(GEO.dome, SHELL_DARK, { y: 0.18 + height, sx: 1.02, sz: 1.02, sy: 0.7 });
      group.add(cap);
      break;
    }
    case 'endpoint': {
      // Dish on a mast — reads as "talks to something outside".
      group.add(mesh(GEO.drum, SHELL, { y: 0.18 + height * 0.3, sy: height * 0.6, sx: 0.8, sz: 0.8 }));
      group.add(mesh(GEO.mast, TRIM, { y: 0.18 + height * 0.75, sy: height * 0.9 }));
      const dish = mesh(GEO.dish, mat, {
        y: 0.18 + height * 1.15,
        rx: -0.9 + r2 * 0.4,
        ry: r3 * Math.PI * 2,
      });
      group.add(dish);
      signals.push(dish);
      break;
    }
    case 'watchdog': {
      // Slim tower with a beacon sphere — a thing whose job is to look at things.
      group.add(mesh(GEO.drum, SHELL, { y: 0.18 + height * 0.5, sy: height, sx: 0.62, sz: 0.62 }));
      group.add(mesh(GEO.fin, TRIM, { x: 0.42, y: 0.18 + height * 0.5, ry: r2 * Math.PI }));
      const orb = mesh(GEO.sphere, mat, { y: 0.18 + height + 0.28 });
      group.add(orb);
      signals.push(orb);
      break;
    }
    case 'calendar':
    case 'webhook': {
      group.add(mesh(GEO.box, SHELL, { y: 0.18 + height / 2, sy: height, sx: 0.85, sz: 0.85 }));
      const ring = mesh(GEO.ring, mat, { y: 0.18 + height + 0.1, sx: 0.8, sy: 0.8 });
      group.add(ring);
      signals.push(ring);
      group.add(mesh(GEO.mast, TRIM, { y: 0.18 + height + 0.45, sy: 0.7 }));
      break;
    }
    default: {
      // 'flow' — the domed tower that dominates the skyline.
      const body = mesh(GEO.drum, SHELL, { y: 0.18 + height / 2, sy: height, sx: 1, sz: 1 });
      group.add(body);
      const dome = mesh(GEO.dome, mat, { y: 0.18 + height, sx: 1.05, sz: 1.05, sy: 0.9 });
      group.add(dome);
      signals.push(dome);
      if (r2 > 0.55) {
        group.add(mesh(GEO.mast, TRIM, { x: 0.5, y: 0.18 + height + 0.3, sy: 0.8 }));
        group.add(mesh(GEO.crate, ACCENT, { x: 0.5, y: 0.18 + height + 0.72, sx: 0.5, sy: 0.5, sz: 0.5 }));
      }
      if (r3 > 0.4) {
        group.add(mesh(GEO.crate, ACCENT, { x: -0.55, y: 0.3, z: 0.45 }));
        group.add(mesh(GEO.crate, SHELL_DARK, { x: -0.55, y: 0.3, z: 0.15 }));
      }
      break;
    }
  }

  group.rotation.y = r1 * Math.PI * 2;
  group.userData.signals = signals;

  // Every shell surface can carry a domain metric in the diverging view. These
  // are collected rather than listed per-archetype so a new building shape gets
  // metric shading for free.
  if (!bodies.length) {
    group.traverse((o) => {
      if (o.isMesh && (o.material === SHELL || o.material === SHELL_DARK)) bodies.push(o);
    });
  }
  group.userData.bodies = bodies;
  group.userData.shellMaterials = bodies.map((b) => b.material);
  group.userData.height = 0.18 + height + 0.9;
  return group;
}

/**
 * The floating marker from the reference video: a rounded plate with an icon,
 * a light shaft down to the building, and a pulsing ground ring. This is the
 * whole reason to render a city instead of a table — an unmissable "here".
 */
/** Rounded-square badge, one per glyph, drawn once and cached. */
const badgeTextures = new Map();
function getBadgeTexture(glyph = '!') {
  if (badgeTextures.has(glyph)) return badgeTextures.get(glyph);
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');

  const r = 26;
  const pad = 14;
  ctx.beginPath();
  ctx.moveTo(pad + r, pad);
  ctx.arcTo(size - pad, pad, size - pad, size - pad, r);
  ctx.arcTo(size - pad, size - pad, pad, size - pad, r);
  ctx.arcTo(pad, size - pad, pad, pad, r);
  ctx.arcTo(pad, pad, size - pad, pad, r);
  ctx.closePath();
  ctx.fillStyle = '#ffffff';
  ctx.fill();

  // Knock the glyph out of the badge so the beacon colour shows through it.
  ctx.globalCompositeOperation = 'destination-out';
  ctx.font = 'bold 68px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(glyph, size / 2, size / 2 + 3);

  const tex = new THREE.CanvasTexture(canvas);
  badgeTextures.set(glyph, tex);
  return tex;
}

export function createBeacon(colour, glyph = '!') {
  const group = new THREE.Group();

  const glow = new THREE.MeshBasicMaterial({
    color: colour,
    map: getBadgeTexture(glyph),
    transparent: true,
    opacity: 0.95,
    depthWrite: false,
    depthTest: false, // a beacon must never be hidden behind a taller building
  });

  const plate = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 1.25), glow);
  plate.renderOrder = 10;
  plate.userData.billboard = true;
  group.add(plate);

  const halo = new THREE.Mesh(
    new THREE.RingGeometry(0.8, 1.05, 28),
    new THREE.MeshBasicMaterial({
      color: colour,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
      depthWrite: false,
      depthTest: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  halo.renderOrder = 9;
  halo.userData.billboard = true;
  group.add(halo);

  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(0.14, 0.3, 3, 10, 1, true),
    new THREE.MeshBasicMaterial({
      color: colour,
      transparent: true,
      opacity: 0.16,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  shaft.position.y = -1.9;
  group.add(shaft);

  group.userData.parts = { plate, halo, shaft };
  return group;
}

export function disposeGroup(group) {
  group.traverse((obj) => {
    if (obj.isMesh) {
      if (obj.geometry && !Object.values(GEO).includes(obj.geometry)) obj.geometry.dispose();
      if (obj.material && obj.material.dispose && !statusMaterials.has(obj.material)) {
        // Shared status/shell materials are reused; only one-off beacon
        // materials are safe to dispose here.
        if (obj.material.userData?.disposable) obj.material.dispose();
      }
    }
  });
}
