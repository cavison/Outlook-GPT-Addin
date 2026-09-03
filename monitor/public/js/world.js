import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { MapControls } from './controls.js';
import {
  createBuilding, createBeacon, statusMaterial, NEUTRAL_SHELL, NEUTRAL_SIGNAL,
} from './buildings.js';
import { statusColour, metricColour, ATTENTION, STATUS_GLYPH, hash01 } from './palette.js';

// Buildings are authored at unit scale; this sizes them against the plate.
// Tuned so a handful of structures reads as a settlement rather than as specks.
const BUILDING_SCALE = 1.35;

/** Flat-top hex plate. Cylinder vertices land 30° off, hence the rotation. */
function hexMesh(radius, height, material) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, 6), material);
  m.rotation.y = Math.PI / 6;
  return m;
}

/** Faint grid on the district floor — the plate should read as engineered. */
function gridTexture() {
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  // Deliberately near-black: under a bright sun and ACES tone mapping, anything
  // lighter washes out to flat grey and the pale buildings stop reading against
  // it. The deck should be dark so the status glows carry the image.
  ctx.fillStyle = '#0c1424';
  ctx.fillRect(0, 0, size, size);
  ctx.strokeStyle = 'rgba(130,180,255,0.30)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= size; i += 16) {
    ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, size); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(size, i); ctx.stroke();
  }
  // Every fourth line brighter, so the grid has a readable rhythm when zoomed out.
  ctx.strokeStyle = 'rgba(150,200,255,0.5)';
  for (let i = 0; i <= size; i += 64) {
    ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, size); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(size, i); ctx.stroke();
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(6, 6);
  return tex;
}

function skyTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 8;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, '#7fb4e8');
  grad.addColorStop(0.55, '#bcdcf5');
  grad.addColorStop(1, '#dff0e4');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 8, 256);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export class World {
  constructor(canvas) {
    this.canvas = canvas;
    this.entities = new Map(); // id -> { entity, group, beacon, placement }
    this.districts = new Map(); // name -> { group, label, plateEdge }
    this.pickables = [];
    this.selectedId = null;
    this.hoveredId = null;
    this.terraform = 0.5;
    // 'health' paints by status; 'metric' paints by each provider's declared
    // diverging metric. Only ever one at a time — two colour languages on one
    // screen means neither can be trusted.
    this.viewMode = 'health';
    this.onSelect = () => {};
    this.onHover = () => {};

    this._initScene();
    this._initGround();
    this._initPicking();
    this._loop();
  }

  // -- setup ----------------------------------------------------------------

  _initScene() {
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;

    this.scene = new THREE.Scene();
    this.scene.background = skyTexture();
    this.scene.fog = new THREE.Fog(0xcfe6f2, 220, 620);

    this.camera = new THREE.PerspectiveCamera(45, 1, 0.5, 2000);
    this.controls = new MapControls(this.camera, this.canvas);

    const hemi = new THREE.HemisphereLight(0xdfefff, 0x4a7a44, 1.5);
    this.scene.add(hemi);

    const sun = new THREE.DirectionalLight(0xfff2d8, 2.1);
    sun.position.set(70, 120, 50);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    const s = 160;
    Object.assign(sun.shadow.camera, { left: -s, right: s, top: s, bottom: -s, near: 1, far: 420 });
    sun.shadow.bias = -0.0008;
    this.scene.add(sun);
    this.sun = sun;

    // Bloom is what makes the status domes and beacons glow rather than just be
    // brightly coloured. Kept low-threshold and tight so it lifts emissives
    // without washing out the whole city.
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.62, 0.6, 0.72);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());

    this.clock = new THREE.Clock();
    addEventListener('resize', () => this.resize());
    this.resize();
  }

  _initGround() {
    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(700, 64),
      new THREE.MeshStandardMaterial({ color: 0x63a84f, roughness: 1 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.02;
    ground.receiveShadow = true;
    this.scene.add(ground);

    // Vegetation density tracks the terraform level — the Planet Crafter beat.
    // A neglected board is a barren one; a well-run week visibly greens up.
    const MAX_TREES = 420;
    const trunkGeo = new THREE.CylinderGeometry(0.16, 0.22, 1.1, 5);
    const leafGeo = new THREE.IcosahedronGeometry(1.05, 0);
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x6b4a2f, roughness: 0.9 });
    const leafMat = new THREE.MeshStandardMaterial({ color: 0x2f8f4e, roughness: 0.85 });

    this.trunks = new THREE.InstancedMesh(trunkGeo, trunkMat, MAX_TREES);
    this.leaves = new THREE.InstancedMesh(leafGeo, leafMat, MAX_TREES);
    this.trunks.castShadow = this.leaves.castShadow = true;
    this.trunks.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.leaves.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

    this.treeSpots = [];
    for (let i = 0; i < MAX_TREES; i++) {
      // Ring distribution keeps trees off the city core without a collision test.
      const angle = hash01(`tree${i}`, 1) * Math.PI * 2;
      const radius = 58 + hash01(`tree${i}`, 2) * 520;
      this.treeSpots.push({
        x: Math.cos(angle) * radius,
        z: Math.sin(angle) * radius,
        s: 0.7 + hash01(`tree${i}`, 3) * 1.5,
      });
    }
    this.scene.add(this.trunks, this.leaves);
    this._layoutTrees();
  }

  _layoutTrees() {
    const count = Math.round(60 + this.terraform * 360);
    const dummy = new THREE.Object3D();
    for (let i = 0; i < this.treeSpots.length; i++) {
      const spot = this.treeSpots[i];
      const on = i < count;
      const scale = on ? spot.s : 0.0001;
      dummy.position.set(spot.x, 0.55 * scale, spot.z);
      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      this.trunks.setMatrixAt(i, dummy.matrix);
      dummy.position.set(spot.x, 1.25 * scale, spot.z);
      dummy.scale.setScalar(scale * 0.9);
      dummy.updateMatrix();
      this.leaves.setMatrixAt(i, dummy.matrix);
    }
    this.trunks.count = this.leaves.count = this.treeSpots.length;
    this.trunks.instanceMatrix.needsUpdate = true;
    this.leaves.instanceMatrix.needsUpdate = true;
  }

  _initPicking() {
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    let downAt = null;

    this.canvas.addEventListener('pointerdown', (e) => {
      downAt = { x: e.clientX, y: e.clientY };
    });

    this.canvas.addEventListener('pointerup', (e) => {
      // A click is only a click if the camera did not move — otherwise every
      // drag across the map would open a card.
      if (!downAt || Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 5) return;
      const hit = this._pick(e);
      this.select(hit?.id ?? null);
      this.onSelect(hit?.id ?? null);
    });

    this.canvas.addEventListener('pointermove', (e) => {
      const hit = this._pick(e);
      const id = hit?.id ?? null;
      if (id !== this.hoveredId) {
        this.hoveredId = id;
        this.canvas.style.cursor = id ? 'pointer' : 'grab';
        this.onHover(id);
      }
    });
  }

  _pick(event) {
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.pickables, true);
    for (const hit of hits) {
      let node = hit.object;
      while (node && !node.userData.entityId) node = node.parent;
      if (node) return { id: node.userData.entityId, node };
    }
    return null;
  }

  resize() {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
    this.composer.setSize(w, h);
  }

  // -- districts ------------------------------------------------------------

  setLayout(layout) {
    this.tileRadius = layout.tileRadius;
    this.slots = layout.slots;
    for (const d of layout.districts) {
      const existing = this.districts.get(d.name);
      if (existing) this._refreshDistrict(existing, d);
      else this.districts.set(d.name, this._createDistrict(d));
    }
  }

  _createDistrict(d) {
    const group = new THREE.Group();

    // Shared per-district materials: one grid texture and one edge colour for
    // the whole region, so a multi-tile district reads as a single place.
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x141c30, roughness: 0.95 });
    const floorMat = new THREE.MeshStandardMaterial({
      map: gridTexture(),
      roughness: 0.9,
      metalness: 0.05,
    });
    const edgeMat = new THREE.MeshBasicMaterial({
      color: d.colour,
      transparent: true,
      opacity: 0.9,
    });

    for (const tile of d.tiles) {
      const base = hexMesh(this.tileRadius, 2.4, baseMat);
      base.position.set(tile.x, -1.2, tile.z);
      base.receiveShadow = true;
      group.add(base);

      const floor = hexMesh(this.tileRadius * 0.985, 0.3, floorMat);
      floor.position.set(tile.x, 0, tile.z);
      floor.receiveShadow = true;
      group.add(floor);

      // The glowing plate edge that separates regions in the reference.
      const edge = hexMesh(this.tileRadius * 1.015, 0.55, edgeMat);
      edge.position.set(tile.x, -0.2, tile.z);
      group.add(edge);
    }

    this.scene.add(group);

    const label = document.createElement('div');
    label.className = 'district-label';
    label.textContent = d.name;
    label.style.setProperty('--district', `#${d.colour.toString(16).padStart(6, '0')}`);
    document.getElementById('labels').appendChild(label);

    return { group, label, colour: d.colour, x: d.x, z: d.z, tiles: d.tiles };
  }

  /** Rebuild a district's plates when it grows a new tile. */
  _refreshDistrict(existing, d) {
    if (existing.tiles.length === d.tiles.length) return;
    this.scene.remove(existing.group);
    existing.label.remove();
    this.districts.set(d.name, this._createDistrict(d));
  }

  districtPosition(name) {
    const d = this.districts.get(name);
    return d ? { x: d.x, z: d.z } : { x: 0, z: 0 };
  }

  /** World position of a placement (which tile, which slot within it). */
  slotPosition(districtName, placement) {
    const d = this.districts.get(districtName);
    if (!d) return null;
    const tile = d.tiles[placement.tile ?? 0] ?? d.tiles[0];
    const slot = this.slots[placement.slot] ?? { x: 0, z: 0 };
    return { x: tile.x + slot.x, z: tile.z + slot.z };
  }

  // -- entities -------------------------------------------------------------

  upsert(entity, placement) {
    const existing = this.entities.get(entity.id);
    if (existing) {
      this._applyStatus(existing, entity);
      existing.entity = entity;
      this._applyViewMode(existing); // the metric may have moved
      return;
    }

    const position = this.slotPosition(entity.district, placement);
    if (!position) return; // layout arrives first; a later poll will place it

    const group = createBuilding(entity);
    group.position.set(position.x, 0.12, position.z);
    group.userData.entityId = entity.id;
    // Buildings are drawn at unit scale then sized here, so one constant tunes
    // how dense the skyline reads against the plate.
    group.userData.baseScale = BUILDING_SCALE;
    // Grow-in animation: new work visibly gets built.
    group.scale.setScalar(0.01);
    group.userData.spawnAt = performance.now();
    this.scene.add(group);
    this.pickables.push(group);

    const record = { entity, group, beacon: null, district: entity.district };
    this.entities.set(entity.id, record);
    this._applyStatus(record, entity);
    this._applyViewMode(record);
  }

  /**
   * Repaint one building's shell for the current view mode. In health mode the
   * shell is neutral and status does the talking; in metric mode the shell
   * carries the diverging value and status retreats to the beacons.
   */
  _applyViewMode(record) {
    const { group, entity } = record;
    const metric = entity.encode?.metric;
    const bodies = group.userData.bodies ?? [];
    const originals = group.userData.shellMaterials ?? [];

    if (this.viewMode === 'metric') {
      // In metric view the map answers exactly one question. Status retreats to
      // the beacons — which carry a glyph, not just a colour — so nothing on the
      // ground competes with the ramp.
      for (const signal of group.userData.signals ?? []) signal.material = NEUTRAL_SIGNAL;

      if (metric) {
        group.userData.metricMaterial ??= new THREE.MeshStandardMaterial({
          roughness: 0.6,
          metalness: 0.05,
        });
        group.userData.metricMaterial.color.setHex(metricColour(metric));
        for (const body of bodies) body.material = group.userData.metricMaterial;
      } else {
        // Declared no metric, so it does not participate in this view.
        for (const body of bodies) body.material = NEUTRAL_SHELL;
      }
    } else {
      const mat = statusMaterial(entity.status);
      for (const signal of group.userData.signals ?? []) signal.material = mat;
      bodies.forEach((body, i) => {
        if (originals[i]) body.material = originals[i];
      });
    }
  }

  setViewMode(mode) {
    if (mode === this.viewMode) return;
    this.viewMode = mode;
    for (const record of this.entities.values()) this._applyViewMode(record);
  }

  _applyStatus(record, entity) {
    const mat = statusMaterial(entity.status);
    for (const signal of record.group.userData.signals ?? []) signal.material = mat;

    const wants = ATTENTION.has(entity.status);
    // A beacon's glyph changes with severity, so the three attention states are
    // distinguishable without relying on colour.
    if (wants && record.beacon && record.beacon.userData.glyph !== STATUS_GLYPH[entity.status]) {
      this.scene.remove(record.beacon);
      record.beacon = null;
    }
    if (wants && !record.beacon) {
      const beacon = createBeacon(statusColour(entity.status), STATUS_GLYPH[entity.status]);
      beacon.userData.glyph = STATUS_GLYPH[entity.status];
      beacon.position.set(
        record.group.position.x,
        record.group.userData.height * BUILDING_SCALE + 2.0,
        record.group.position.z,
      );
      this.scene.add(beacon);
      record.beacon = beacon;
    } else if (wants && record.beacon) {
      const colour = new THREE.Color(statusColour(entity.status));
      for (const part of Object.values(record.beacon.userData.parts)) part.material.color = colour;
    } else if (!wants && record.beacon) {
      this.scene.remove(record.beacon);
      record.beacon = null;
    }

    // Flash on any status change so a transition is visible even if you were
    // looking at another part of the map.
    if (record.entity && record.entity.status !== entity.status) {
      record.group.userData.flashAt = performance.now();
    }
  }

  remove(id) {
    const record = this.entities.get(id);
    if (!record) return;
    this.scene.remove(record.group);
    if (record.beacon) this.scene.remove(record.beacon);
    this.pickables = this.pickables.filter((p) => p !== record.group);
    this.entities.delete(id);
  }

  select(id) {
    this.selectedId = id;
    if (!id) return;
    const record = this.entities.get(id);
    if (record) this.controls.focus(record.group.position.x, record.group.position.z, 40);
  }

  focusDistrict(name) {
    const p = this.districtPosition(name);
    this.controls.focus(p.x, p.z, 58);
  }

  setTerraform(value) {
    if (Math.abs(value - this.terraform) < 0.01) return;
    this.terraform = value;
    this._layoutTrees();
    // Sky and ground warm up as the board gets healthier.
    const health = THREE.MathUtils.clamp(value, 0, 1);
    this.scene.fog.color.setHSL(0.55 - health * 0.06, 0.35 + health * 0.2, 0.72 + health * 0.06);
    this.renderer.toneMappingExposure = 0.92 + health * 0.22;
  }

  // -- frame ----------------------------------------------------------------

  _updateLabels() {
    const rect = this.canvas.getBoundingClientRect();
    const v = new THREE.Vector3();
    for (const d of this.districts.values()) {
      v.set(d.x, 4.5, d.z).project(this.camera);
      const visible = v.z < 1;
      d.label.style.display = visible ? 'block' : 'none';
      if (!visible) continue;
      d.label.style.transform =
        `translate(-50%,-50%) translate(${((v.x + 1) / 2) * rect.width}px,` +
        `${((-v.y + 1) / 2) * rect.height}px)`;
    }
  }

  _loop = () => {
    requestAnimationFrame(this._loop);
    const t = performance.now();
    const elapsed = this.clock.getElapsedTime();

    this.controls.update();

    // One shared pulse drives every attention material, so all the alarms in
    // the city breathe together — a scattered flicker reads as noise.
    const pulse = 0.5 + 0.5 * Math.sin(elapsed * 4);
    for (const status of ['failed', 'blocked', 'warning']) {
      statusMaterial(status).emissiveIntensity = 0.4 + pulse * 0.85;
    }
    statusMaterial('running').emissiveIntensity = 0.5 + 0.4 * Math.sin(elapsed * 8);

    for (const record of this.entities.values()) {
      // Grow-in
      const base = record.group.userData.baseScale ?? 1;
      if (record.group.userData.spawnAt) {
        const p = Math.min(1, (t - record.group.userData.spawnAt) / 700);
        const eased = 1 - Math.pow(1 - p, 3);
        record.group.scale.setScalar(eased * base);
        if (p >= 1) {
          delete record.group.userData.spawnAt;
          record.group.scale.setScalar(base);
        }
      }
      // Status-change flash — a one-off hop, added on top of the resting height.
      let flash = 0;
      if (record.group.userData.flashAt) {
        const p = (t - record.group.userData.flashAt) / 900;
        if (p >= 1) delete record.group.userData.flashAt;
        else flash = Math.sin(p * Math.PI) * 0.9;
      }

      // Selection lift, eased so the selected building rises out of the block.
      const selected = record.entity.id === this.selectedId;
      record.group.userData.lift ??= 0;
      record.group.userData.lift += ((selected ? 0.9 : 0) - record.group.userData.lift) * 0.15;
      record.group.position.y = 0.12 + flash + record.group.userData.lift;

      if (record.beacon) {
        const b = record.beacon;
        b.position.y =
          record.group.userData.height * BUILDING_SCALE +
          2.0 +
          record.group.userData.lift +
          Math.sin(elapsed * 2.2 + record.group.position.x) * 0.28;
        const { halo, plate } = b.userData.parts;
        // Billboard only the flat parts; the light shaft must stay vertical.
        plate.quaternion.copy(this.camera.quaternion);
        halo.quaternion.copy(this.camera.quaternion);
        const s = 1 + Math.sin(elapsed * 3) * 0.12;
        halo.scale.setScalar(s);
        halo.material.opacity = 0.2 + 0.28 * (0.5 + 0.5 * Math.sin(elapsed * 3));
        plate.material.opacity = 0.75 + 0.25 * (0.5 + 0.5 * Math.sin(elapsed * 3));
      }
    }

    this._updateLabels();
    this.composer.render();
  };
}
