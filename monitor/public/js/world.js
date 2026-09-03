import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { MapControls } from './controls.js';
import {
  createBuilding, createBeacon, statusMaterial, NEUTRAL_SHELL, NEUTRAL_SIGNAL, UNLIT,
} from './buildings.js';
import {
  statusColour, metricColour, ATTENTION, STATUS_GLYPH, statusRank, hash01,
} from './palette.js';

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
    sun.shadow.mapSize.set(1024, 1024);
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
    this.slotGrids = layout.slotGrids ?? { normal: layout.slots };
    this.parcels = layout.parcels ?? [];
    this.parcelByNumber = new Map(this.parcels.map((p) => [p.number, p]));
    for (const d of layout.districts) {
      const existing = this.districts.get(d.name);
      if (existing) this._refreshDistrict(existing, d);
      else {
        this.districts.set(d.name, this._createDistrict(d));
        this._lotsDirty = true;
      }
    }
    if (this._lotsDirty) {
      this._lotsDirty = false;
      this._rebuildLots();
      this._rebuildGroupLabels();
    }
  }

  /**
   * One label per neighbourhood, shown when zoomed out.
   *
   * At portfolio zoom 187 property names cover the entire map — the labels stop
   * being annotation and become the view. Far out you want to know whose patch
   * you are looking at; the property name only matters once you are close
   * enough to act on it.
   */
  _rebuildGroupLabels() {
    this.groupLabels ??= new Map();
    const centroids = new Map();

    for (const d of this.districts.values()) {
      if (!d.neighbourhood) continue;
      const row = centroids.get(d.neighbourhood) ?? { x: 0, z: 0, n: 0, colour: d.colour };
      row.x += d.x;
      row.z += d.z;
      row.n++;
      centroids.set(d.neighbourhood, row);
    }

    for (const [name, row] of centroids) {
      let label = this.groupLabels.get(name);
      if (!label) {
        label = document.createElement('div');
        label.className = 'district-label group-label';
        label.textContent = name;
        label.style.setProperty('--district', `#${row.colour.toString(16).padStart(6, '0')}`);
        document.getElementById('labels').appendChild(label);
        this.groupLabels.set(name, label);
      }
      label.dataset.x = row.x / row.n;
      label.dataset.z = row.z / row.n;
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

    return {
      group, label, colour: d.colour, x: d.x, z: d.z,
      tiles: d.tiles, density: d.density ?? 'normal',
      // Named `neighbourhood`, not `group` — `group` is already the THREE.Group.
      neighbourhood: d.group ?? null,
    };
  }

  /**
   * Every parcel position on every hex, as ONE instanced mesh.
   *
   * These are decorative site markings, and drawn individually they were 4,675
   * separate draw calls — by far the largest single cost in the scene, for the
   * least important thing in it.
   */
  _rebuildLots() {
    if (!this.parcels?.length) return;
    const tiles = [];
    for (const d of this.districts.values()) {
      for (const tile of d.tiles) tiles.push(tile);
    }
    const count = tiles.length * this.parcels.length;
    if (!count) return;

    if (this.lots) {
      this.scene.remove(this.lots);
      this.lots.geometry.dispose();
      this.lots.material.dispose();
    }

    const geo = new THREE.CircleGeometry(0.62, 12);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshBasicMaterial({
      color: 0x9fb6d8, transparent: true, opacity: 0.13, depthWrite: false,
    });
    this.lots = new THREE.InstancedMesh(geo, mat, count);
    this.lots.frustumCulled = false;

    const dummy = new THREE.Object3D();
    let i = 0;
    for (const tile of tiles) {
      for (const parcel of this.parcels) {
        dummy.position.set(tile.x + parcel.x, 0.17, tile.z + parcel.z);
        dummy.updateMatrix();
        this.lots.setMatrixAt(i++, dummy.matrix);
      }
    }
    this.lots.instanceMatrix.needsUpdate = true;
    this.scene.add(this.lots);
  }

  /** Rebuild a district's plates when it grows a new tile. */
  _refreshDistrict(existing, d) {
    const density = d.density ?? 'normal';
    if (existing.tiles.length === d.tiles.length && existing.density === density) return;
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
    // A parcel is a fixed address within the hex; a slot is handed out on
    // arrival. Parcels win.
    if (placement.parcel) {
      const parcel = this.parcelByNumber.get(placement.parcel);
      if (parcel) return { x: tile.x + parcel.x, z: tile.z + parcel.z };
    }
    const grid = this.slotGrids[d.density] ?? this.slots;
    const slot = grid[placement.slot] ?? { x: 0, z: 0 };
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
    // Relays sit on the fine grid, so they are drawn smaller than landmarks.
    const formName = entity.encode?.form ?? entity.kind;
    group.userData.baseScale =
      formName === 'relay' ? BUILDING_SCALE * 0.62
      : formName === 'plot' ? 0.55
      : formName === 'pillar' ? 1.0
      : formName === 'pillar-landmark' ? 1.0
      : formName === 'plot-landmark' ? 1.0
      : BUILDING_SCALE;
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
      const unlit = group.userData.unlitStatuses?.has(entity.status);
      const mat = unlit ? UNLIT : statusMaterial(entity.status);
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
    // "Not running" is drawn as darkness, not as another colour — for a relay
    // field that is literally what the failure is.
    const unlit = record.group.userData.unlitStatuses?.has(entity.status);
    const mat = unlit ? UNLIT : statusMaterial(entity.status);
    for (const signal of record.group.userData.signals ?? []) signal.material = mat;

    // Beacons are clustered per district, not per entity. One badge saying
    // "4 issues here" is a signpost; forty badges are wallpaper, and they hide
    // the pillar heights that carry the actual meaning.
    this._beaconsDirty = true;

    // Flash on any status change so a transition is visible even if you were
    // looking at another part of the map.
    if (record.entity && record.entity.status !== entity.status) {
      record.group.userData.flashAt = performance.now();
    }
  }

  /**
   * One beacon per district, coloured by its worst status and labelled with how
   * many things are wrong. Far out it tells you WHERE; you zoom in to see what.
   */
  _syncClusterBeacons() {
    this._beaconsDirty = false;
    this.clusterBeacons ??= new Map();

    const worst = new Map();
    for (const record of this.entities.values()) {
      if (!ATTENTION.has(record.entity.status)) continue;
      const key = record.entity.district;
      const row = worst.get(key) ?? { count: 0, status: 'warning', top: 0 };
      row.count++;
      if (statusRank(record.entity.status) < statusRank(row.status)) {
        row.status = record.entity.status;
      }
      row.top = Math.max(row.top, record.group.userData.height * (record.group.userData.baseScale ?? 1));
      worst.set(key, row);
    }

    for (const [name, beacon] of this.clusterBeacons) {
      if (!worst.has(name)) {
        this.scene.remove(beacon);
        this.clusterBeacons.delete(name);
      }
    }

    for (const [name, row] of worst) {
      const district = this.districts.get(name);
      if (!district) continue;
      const signature = `${row.status}:${row.count}`;
      let beacon = this.clusterBeacons.get(name);

      if (!beacon || beacon.userData.signature !== signature) {
        if (beacon) this.scene.remove(beacon);
        beacon = createBeacon(statusColour(row.status), String(row.count));
        beacon.userData.signature = signature;
        this.scene.add(beacon);
        this.clusterBeacons.set(name, beacon);
      }
      beacon.position.set(district.x, row.top + 3.4, district.z);
      beacon.userData.baseY = row.top + 3.4;
    }
  }

  remove(id) {
    const record = this.entities.get(id);
    if (!record) return;
    this.scene.remove(record.group);
    if (record.beacon) this.scene.remove(record.beacon);
    this.pickables = this.pickables.filter((p) => p !== record.group);
    this.entities.delete(id);
    this._beaconsDirty = true;
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

    // Below this the map is a place you are working in; above it, an overview.
    const CLOSE_ENOUGH_FOR_NAMES = 95;
    const showProperties = this.controls.distance < CLOSE_ENOUGH_FOR_NAMES;

    const place = (el, x, y, z) => {
      v.set(x, y, z).project(this.camera);
      if (v.z >= 1) {
        el.style.display = 'none';
        return;
      }
      el.style.display = 'block';
      el.style.transform =
        `translate(-50%,-50%) translate(${((v.x + 1) / 2) * rect.width}px,` +
        `${((-v.y + 1) / 2) * rect.height}px)`;
    };

    for (const d of this.districts.values()) {
      if (!showProperties) {
        d.label.style.display = 'none';
        continue;
      }
      place(d.label, d.x, 4.5, d.z);
    }

    for (const label of this.groupLabels?.values() ?? []) {
      if (showProperties) {
        label.style.display = 'none';
        continue;
      }
      place(label, Number(label.dataset.x), 10, Number(label.dataset.z));
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

    }

    if (this._beaconsDirty) this._syncClusterBeacons();

    for (const beacon of this.clusterBeacons?.values() ?? []) {
      const { halo, plate } = beacon.userData.parts;
      beacon.position.y = beacon.userData.baseY + Math.sin(elapsed * 2.2 + beacon.position.x) * 0.3;
      plate.quaternion.copy(this.camera.quaternion);
      halo.quaternion.copy(this.camera.quaternion);
      const s = 1 + Math.sin(elapsed * 3) * 0.1;
      halo.scale.setScalar(s);
      halo.material.opacity = 0.2 + 0.28 * (0.5 + 0.5 * Math.sin(elapsed * 3));
    }

    this._updateLabels();
    this.composer.render();
  };
}
