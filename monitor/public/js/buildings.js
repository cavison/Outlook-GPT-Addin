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
};

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
export function createBuilding(entity) {
  const group = new THREE.Group();
  const r1 = hash01(entity.id, 1);
  const r2 = hash01(entity.id, 2);
  const r3 = hash01(entity.id, 3);

  const height = 0.75 + entity.weight * 0.55 + r1 * 0.4;
  const mat = statusMaterial(entity.status);
  const signals = [];

  group.add(mesh(GEO.pad, SHELL_DARK, { y: 0.09, ry: r1 * Math.PI }));

  switch (entity.kind) {
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
  group.userData.height = 0.18 + height + 0.9;
  return group;
}

/**
 * The floating marker from the reference video: a rounded plate with an icon,
 * a light shaft down to the building, and a pulsing ground ring. This is the
 * whole reason to render a city instead of a table — an unmissable "here".
 */
/** Rounded-square badge with an exclamation mark, drawn once and reused. */
let badgeTexture = null;
function getBadgeTexture() {
  if (badgeTexture) return badgeTexture;
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
  ctx.fillText('!', size / 2, size / 2 + 3);

  badgeTexture = new THREE.CanvasTexture(canvas);
  return badgeTexture;
}

export function createBeacon(colour) {
  const group = new THREE.Group();

  const glow = new THREE.MeshBasicMaterial({
    color: colour,
    map: getBadgeTexture(),
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
