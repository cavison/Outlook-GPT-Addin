(function () {
  'use strict';
  const DATA = window.__CITY__;

  // ---- palette (validated set, shared with the desktop app) ----------------
  const COL = { failed: 0xff4d5a, blocked: 0xb57bff, warning: 0xffd23f, healthy: 0x5be7a9 };
  const hex = (n) => '#' + n.toString(16).padStart(6, '0');
  const statusOf = (s) => (s >= 0.75 ? 'failed' : s >= 0.5 ? 'blocked' : s >= 0.28 ? 'warning' : 'healthy');
  const LABEL = { failed: 'Failed', blocked: 'Blocked', warning: 'Degraded', healthy: 'On plan' };
  const money = (v) => (v < 0 ? '\u2212' : '+') + '$' + Math.abs(Math.round(v)).toLocaleString('en-US');

  // ---- hex + parcel geometry (ported from the server) ----------------------
  const R = 9, GAP = 0.55, S3 = Math.sqrt(3), SP = R + GAP / 2;
  const axial = (q, r) => ({ x: SP * 1.5 * q, z: SP * S3 * (r + q / 2) });
  const NB = [[1,0],[1,-1],[0,-1],[-1,0],[-1,1],[0,1]];

  function ring(radius, start, n) {
    return Array.from({ length: n }, (_, i) => {
      const a = -Math.PI / 2 + (i * Math.PI * 2) / n;
      return { num: String(start + i).padStart(2, '0'),
               x: Math.cos(a) * radius, z: Math.sin(a) * radius };
    });
  }
  const PARCELS = [{ num: '01', x: 0, z: 0, landmark: true }]
    .concat(ring(4.1, 2, 12)).concat(ring(6.6, 14, 12));
  const PARCEL_AT = new Map(PARCELS.map((p) => [p.num, p]));

  // Hex coordinates come from the server, which packs each regional's book into
  // one contiguous patch. Re-deriving the layout here would let the page and the
  // desktop app disagree about where a property sits — and the whole point of a
  // map is that a property is always in the same place.
  for (const p of DATA.properties) Object.assign(p, axial(p.q, p.r));

  let townTiles = [];
  const REGION_COLOUR = [0x4f7cff, 0xb44ff5, 0x2fd8c3, 0xff5c9d, 0xffa23a, 0x6ee7ff];
  const regionColour = new Map(DATA.regions.map((r, i) => [r, REGION_COLOUR[i % REGION_COLOUR.length]]));

  // ---- scene ---------------------------------------------------------------
  const canvas = document.getElementById('scene');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.02;

  const scene = new THREE.Scene();
  // Aerial perspective, pushed well back: 185 hexes span far enough that a
  // near plane of 260 fogged most of the portfolio into a pale wash.
  scene.fog = new THREE.Fog(0xcfe6f2, 430, 1500);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.5, 3000);

  (function sky() {
    const c = document.createElement('canvas');
    c.width = 8; c.height = 256;
    const g = c.getContext('2d').createLinearGradient(0, 0, 0, 256);
    g.addColorStop(0, '#7fb4e8'); g.addColorStop(.55, '#bcdcf5'); g.addColorStop(1, '#dff0e4');
    const ctx = c.getContext('2d'); ctx.fillStyle = g; ctx.fillRect(0, 0, 8, 256);
    const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding;
    scene.background = t;
  })();

  scene.add(new THREE.HemisphereLight(0xdfefff, 0x4a7a44, 1.45));
  const sun = new THREE.DirectionalLight(0xfff2d8, 2.0);
  sun.position.set(90, 150, 70);
  scene.add(sun);

  const ground = new THREE.Mesh(new THREE.CircleGeometry(900, 48),
    new THREE.MeshStandardMaterial({ color: 0x63a84f, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.02;
  scene.add(ground);

  // ---- deck plates ---------------------------------------------------------
  function gridTex() {
    const s = 256, c = document.createElement('canvas');
    c.width = c.height = s;
    const x = c.getContext('2d');
    x.fillStyle = '#0c1424'; x.fillRect(0, 0, s, s);
    x.strokeStyle = 'rgba(130,180,255,.28)'; x.lineWidth = 1;
    for (let i = 0; i <= s; i += 16) { x.beginPath(); x.moveTo(i,0); x.lineTo(i,s); x.stroke();
      x.beginPath(); x.moveTo(0,i); x.lineTo(s,i); x.stroke(); }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(5, 5);
    return t;
  }
  const deckMat = new THREE.MeshStandardMaterial({ map: gridTex(), roughness: .9 });
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x141c30, roughness: .95 });

  const hexGeo = new THREE.CylinderGeometry(R * 0.985, R * 0.985, 0.3, 6);
  const baseGeo = new THREE.CylinderGeometry(R, R, 2.2, 6);
  const edgeGeo = new THREE.CylinderGeometry(R * 1.015, R * 1.015, 0.5, 6);

  const townCount = (DATA.town || []).length || 1;
  const decks = new THREE.InstancedMesh(hexGeo, deckMat, DATA.properties.length + townCount);
  const bases = new THREE.InstancedMesh(baseGeo, baseMat, DATA.properties.length + townCount);
  const dummy = new THREE.Object3D();
  const edgesByRegion = new Map();

  function placeHex(i, x, z) {
    dummy.rotation.set(0, Math.PI / 6, 0);
    dummy.position.set(x, 0, z); dummy.updateMatrix(); decks.setMatrixAt(i, dummy.matrix);
    dummy.position.set(x, -1.1, z); dummy.updateMatrix(); bases.setMatrixAt(i, dummy.matrix);
  }
  DATA.properties.forEach((p, i) => {
    placeHex(i, p.x, p.z);
    if (!edgesByRegion.has(p.g)) edgesByRegion.set(p.g, []);
    edgesByRegion.get(p.g).push(p);
  });
  // The Town Centre: blank ground held in the middle, where the books converge.
  townTiles = (DATA.town || [{ q: 0, r: 0 }]).map((t) => axial(t.q, t.r));
  townTiles.forEach((t, i) => placeHex(DATA.properties.length + i, t.x, t.z));
  decks.instanceMatrix.needsUpdate = bases.instanceMatrix.needsUpdate = true;
  scene.add(decks, bases);

  // one edge mesh per region, so a regional's patch reads as one colour
  const edgeMatByRegion = new Map();
  for (const [region, props] of edgesByRegion) {
    const mat = new THREE.MeshBasicMaterial({ color: regionColour.get(region), transparent: true, opacity: .85 });
    edgeMatByRegion.set(region, mat);
    const im = new THREE.InstancedMesh(edgeGeo, mat, props.length);
    props.forEach((p, i) => {
      dummy.rotation.set(0, Math.PI / 6, 0);
      dummy.position.set(p.x, -0.18, p.z); dummy.updateMatrix(); im.setMatrixAt(i, dummy.matrix);
    });
    im.instanceMatrix.needsUpdate = true;
    scene.add(im);
  }

  // vacant parcel markings, all as one mesh
  (function lots() {
    const g = new THREE.CircleGeometry(0.6, 10); g.rotateX(-Math.PI / 2);
    const im = new THREE.InstancedMesh(g,
      new THREE.MeshBasicMaterial({ color: 0x9fb6d8, transparent: true, opacity: .12, depthWrite: false }),
      (DATA.properties.length + townTiles.length) * PARCELS.length);
    let i = 0;
    const tiles = DATA.properties.map((p) => ({ x: p.x, z: p.z })).concat(townTiles);
    for (const t of tiles) for (const pc of PARCELS) {
      dummy.rotation.set(0, 0, 0);
      dummy.position.set(t.x + pc.x, 0.17, t.z + pc.z);
      dummy.updateMatrix(); im.setMatrixAt(i++, dummy.matrix);
    }
    im.instanceMatrix.needsUpdate = true; im.frustumCulled = false;
    scene.add(im);
  })();

  // ---- pillars -------------------------------------------------------------
  //
  // One pillar per KPI at its fixed parcel address, plus the centre landmark.
  //
  // The landmark stands for the property, not for a number, so it is the same
  // height on every hex — a fixed ruler every other pillar is read against. It
  // used to rise with the property's worst line, which read as a second failing
  // KPI and made a hex with one bad pillar look like a hex with two.
  //
  // Instanced by bucket rather than one mesh per pillar: 185 hexes times 15
  // parcels is 2,775 objects, and at that count draw calls, not geometry, are
  // what costs. Rebuilding every matrix when a filter moves is cheap by
  // comparison — a few thousand writes once per click.

  const PMIN = 0.12, PMAX = 6.0, LANDMARK_H = 1.35;
  const pillarGeo = new THREE.BoxGeometry(0.72, 1, 0.72);
  const plinthGeo = new THREE.CylinderGeometry(0.42, 0.46, 0.1, 8);

  const BUCKETS = {
    failed: 0xff4d5a, blocked: 0xb57bff, warning: 0xffd23f, healthy: 0x5be7a9,
    // Achromatic and bright: there is no reading to colour, and grey on a dark
    // deck disappears. A feed that stopped is the failure this map exists to
    // catch, so it must not be the quietest thing on it.
    nodata: 0xd7dde8,
    // Filtered out. Pale and matte — a dark grey building would read as a hole
    // punched in the map rather than as a quiet one.
    dimmed: 0x707d92,
  };
  const bucketMat = {};
  for (const k in BUCKETS) {
    bucketMat[k] = new THREE.MeshStandardMaterial({
      color: BUCKETS[k],
      emissive: BUCKETS[k],
      emissiveIntensity: k === 'dimmed' ? 0 : 0.38,
      roughness: k === 'dimmed' ? 0.95 : 0.35,
    });
  }

  // Every drawable cell, flattened once. `st` is the pip state the build script
  // baked in, so the page never re-derives what "failing" means.
  const cells = [];
  for (const p of DATA.properties) {
    const pc0 = PARCEL_AT.get('01');
    cells.push({
      p, kpi: null, parcel: '01', landmark: true, st: 'landmark',
      s: p.sev, x: p.x + pc0.x, z: p.z + pc0.z,
    });
    for (const k of DATA.kpis) {
      const cell = p.c[k.id];
      if (!cell) continue;                 // never connected: ground held, nothing built
      const pc = PARCEL_AT.get(k.parcel);
      if (!pc) continue;
      cells.push({
        p, kpi: k, parcel: k.parcel, landmark: false,
        st: cell.st, s: cell.s || 0, cell,
        x: p.x + pc.x, z: p.z + pc.z,
      });
    }
  }

  const meshes = {};
  for (const k in BUCKETS) {
    const im = new THREE.InstancedMesh(pillarGeo, bucketMat[k], Math.max(1, cells.length));
    im.count = 0; im.frustumCulled = false;
    meshes[k] = im; scene.add(im);
  }
  const plinths = new THREE.InstancedMesh(plinthGeo,
    new THREE.MeshStandardMaterial({ color: 0x93a6c6, roughness: 0.6 }), cells.length);
  plinths.count = 0; plinths.frustumCulled = false; scene.add(plinths);

  let visibleSet = null;       // null = no filter
  let heightVariant = 'worst';
  let focusKpi = null;
  const picks = [];

  function bucketFor(cell) {
    if (visibleSet && !visibleSet.has(cell.p.n)) return 'dimmed';
    if (cell.landmark) return statusOf(cell.s);
    if (cell.st === 'gap') return 'nodata';
    if (cell.st === 'na') return 'dimmed';
    return statusOf(cell.s);
  }

  function heightFor(cell) {
    // The landmark keeps its constant height in every variant. A ruler that
    // changed with the variant would not be one.
    if (cell.landmark) return LANDMARK_H;
    if (cell.st === 'na') return 0;                 // a paved lot: nothing stands up
    if (cell.st === 'gap') return 0.85;             // a marker post, not a reading
    if (heightVariant === 'flat') return PMIN;
    if (heightVariant === 'focus') {
      return focusKpi && cell.kpi && cell.kpi.id === focusKpi ? PMIN + cell.s * (PMAX - PMIN) : PMIN;
    }
    return PMIN + cell.s * (PMAX - PMIN);
  }

  function rebuild() {
    for (const k in meshes) meshes[k].count = 0;
    plinths.count = 0;
    picks.length = 0;

    for (const cell of cells) {
      const h = heightFor(cell);
      const wide = cell.landmark ? 1.9 : 1;
      const bucket = bucketFor(cell);

      dummy.rotation.set(0, 0, 0);
      dummy.position.set(cell.x, 0.06, cell.z);
      dummy.scale.set(wide, 1, wide);
      dummy.updateMatrix();
      plinths.setMatrixAt(plinths.count++, dummy.matrix);

      if (h > 0) {
        const im = meshes[bucket];
        dummy.position.set(cell.x, 0.02 + h / 2, cell.z);
        dummy.scale.set(wide, h, wide);
        dummy.updateMatrix();
        im.setMatrixAt(im.count++, dummy.matrix);
      }
      picks.push({ x: cell.x, z: cell.z, cell });
    }

    for (const k in meshes) meshes[k].instanceMatrix.needsUpdate = true;
    plinths.instanceMatrix.needsUpdate = true;
    dummy.scale.set(1, 1, 1);
  }

  function setVisibleSet(set) {
    visibleSet = set;
    rebuild();
    for (const [region, mat] of edgeMatByRegion) {
      const anyShown = !set || DATA.properties.some((p) => p.g === region && set.has(p.n));
      mat.opacity = anyShown ? 0.85 : 0.12;
    }
  }
  function setHeightVariant(variant, kpi) {
    heightVariant = variant; focusKpi = kpi || null;
    rebuild();
  }

  // ---- camera controls -----------------------------------------------------
  const ctrl = {
    target: new THREE.Vector3(0, 0, 0), dist: 230, az: -Math.PI / 4, pol: 0.92,
    vAz: 0, vPol: 0, vZoom: 0, pan: new THREE.Vector3(), goal: null,
  };
  let pointers = new Map(), mode = null, last = { x: 0, y: 0 }, pinch = 0;

  canvas.addEventListener('pointerdown', (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) { mode = e.button === 2 || e.shiftKey ? 'pan' : 'orbit'; last = { x: e.clientX, y: e.clientY }; }
    else if (pointers.size === 2) { mode = 'pinch'; pinch = span(); }
  });
  function span() { const [a, b] = [...pointers.values()]; return Math.hypot(a.x - b.x, a.y - b.y); }
  canvas.addEventListener('pointermove', (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (mode === 'pinch' && pointers.size === 2) { const s = span(); ctrl.vZoom += (pinch - s) * .05; pinch = s; return; }
    const dx = e.clientX - last.x, dy = e.clientY - last.y;
    last = { x: e.clientX, y: e.clientY };
    if (mode === 'orbit') { ctrl.vAz -= dx * .005; ctrl.vPol -= dy * .005; }
    else if (mode === 'pan') panBy(dx, dy);
  });
  const release = (e) => { pointers.delete(e.pointerId); mode = pointers.size ? 'orbit' : null; };
  canvas.addEventListener('pointerup', release);
  canvas.addEventListener('pointercancel', release);
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('wheel', (e) => { e.preventDefault(); ctrl.vZoom += e.deltaY * .12; }, { passive: false });

  function panBy(dx, dy) {
    const k = ctrl.dist * .0016;
    const f = new THREE.Vector3(Math.sin(ctrl.az), 0, Math.cos(ctrl.az));
    ctrl.pan.addScaledVector(new THREE.Vector3(f.z, 0, -f.x), dx * k).addScaledVector(f, dy * k);
  }
  function flyTo(x, z, dist) { ctrl.goal = { x: x, z: z, dist: dist }; }

  function updateCamera() {
    if (ctrl.goal) {
      ctrl.target.x += (ctrl.goal.x - ctrl.target.x) * .1;
      ctrl.target.z += (ctrl.goal.z - ctrl.target.z) * .1;
      ctrl.dist += (ctrl.goal.dist - ctrl.dist) * .1;
      if (Math.abs(ctrl.goal.x - ctrl.target.x) < .5 && Math.abs(ctrl.goal.dist - ctrl.dist) < .5) ctrl.goal = null;
    }
    ctrl.az += ctrl.vAz;
    ctrl.pol = Math.max(.16, Math.min(1.4, ctrl.pol + ctrl.vPol));
    ctrl.target.add(ctrl.pan);
    ctrl.dist = Math.max(22, Math.min(520, ctrl.dist + ctrl.vZoom));
    ctrl.vAz *= .86; ctrl.vPol *= .86; ctrl.vZoom *= .86; ctrl.pan.multiplyScalar(.86);
    const sp = Math.sin(ctrl.pol);
    camera.position.set(
      ctrl.target.x + ctrl.dist * sp * Math.sin(ctrl.az),
      ctrl.dist * Math.cos(ctrl.pol),
      ctrl.target.z + ctrl.dist * sp * Math.cos(ctrl.az));
    camera.lookAt(ctrl.target);
  }

  // ---- picking: nearest pillar to the ray on the ground plane ---------------
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  let downPt = null;

  /**
   * What is under the cursor.
   *
   * Two answers, because they are two different questions. Land on a pillar and
   * you want that KPI; land anywhere else on the plate and you just want to know
   * which property this is — which is the whole point when you are zoomed out
   * past the labels.
   */
  function probe(clientX, clientY) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = new THREE.Vector3();
    if (!ray.ray.intersectPlane(plane, hit)) return null;

    // Inner-ring parcels sit 2.15 apart, so keep the pillar radius under half
    // that or a click lands on a neighbour.
    let best = null, bestD = Infinity;
    for (const pick of picks) {
      const d = Math.hypot(pick.x - hit.x, pick.z - hit.z);
      const reach = pick.cell.landmark ? 1.6 : 1.05;
      if (d < reach && d < bestD) { best = pick; bestD = d; }
    }
    if (best) return { kind: 'pillar', cell: best.cell, property: best.cell.p };

    let prop = null, dist = 8.2;
    for (const p of DATA.properties) {
      const d = Math.hypot(p.x - hit.x, p.z - hit.z);
      if (d < dist) { dist = d; prop = p; }
    }
    if (prop) return { kind: 'hex', property: prop };

    for (const t of townTiles) {
      if (Math.hypot(t.x - hit.x, t.z - hit.z) < 8.2) return { kind: 'town' };
    }
    return null;
  }

  canvas.addEventListener('pointerdown', (e) => { downPt = { x: e.clientX, y: e.clientY }; });
  canvas.addEventListener('pointerup', (e) => {
    if (!downPt || Math.hypot(e.clientX - downPt.x, e.clientY - downPt.y) > 5) return;
    const found = probe(e.clientX, e.clientY);
    if (!found) { select(null); return; }
    select(found.property, found.kind === 'pillar' && found.cell.kpi ? found.cell.kpi.id : null);
  });

  // ---- hover ---------------------------------------------------------------
  const tip = document.getElementById('tip');
  let hoverRaf = 0, hoverEvent = null;

  canvas.addEventListener('pointerleave', () => { tip.style.display = 'none'; });
  canvas.addEventListener('pointermove', (e) => {
    hoverEvent = e;
    if (hoverRaf) return;
    // One probe per frame at most; pointermove fires far faster than that.
    hoverRaf = requestAnimationFrame(() => {
      hoverRaf = 0;
      if (mode) { tip.style.display = 'none'; return; }   // dragging the camera
      const found = probe(hoverEvent.clientX, hoverEvent.clientY);
      if (!found) { tip.style.display = 'none'; canvas.style.cursor = 'grab'; return; }
      canvas.style.cursor = 'pointer';
      showTip(found, hoverEvent.clientX, hoverEvent.clientY);
    });
  });

  function showTip(found, cx, cy) {
    if (found.kind === 'town') {
      tip.innerHTML = '<div class="t">Town Centre</div>' +
        '<div class="r">Held for shared items</div>' +
        '<div class="m">ten blank hexes &middot; nothing assigned yet</div>';
      tip.style.setProperty('--tc', '#5aa2ff');
    } else {
      const p = found.property;
      let html = '<div class="t">' + p.n + '</div><div class="r">' + p.g +
        (p.dir ? ' &middot; ' + p.dir : '') + '</div>';
      let colour = hex(COL[statusOf(p.sev)]);

      if (found.kind === 'pillar' && !found.cell.landmark) {
        const c = found.cell;
        colour = c.st === 'gap' ? '#d7dde8'
          : c.st === 'na' ? '#8892a6' : hex(COL[statusOf(c.s)]);
        html += '<div class="v">' + c.kpi.label + ': ' + (c.cell.h || '—') + '</div>';
        if (c.cell.d) html += '<div class="m">' + c.cell.d + '</div>';
      } else {
        html += '<div class="v">HP ' + p.hp + ' &middot; ' +
          (p.worst ? 'worst: ' + p.worst : 'nothing over') + '</div>';
        html += '<div class="m">' + p.reporting + ' reporting' +
          (p.gaps ? ' &middot; ' + p.gaps + ' feed' + (p.gaps === 1 ? '' : 's') + ' stopped' : '') +
          ' &middot; click for the breakdown</div>';
      }
      tip.innerHTML = html;
      tip.style.setProperty('--tc', colour);
    }
    tip.style.display = 'block';
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(innerWidth - w - 10, cx + 16) + 'px';
    tip.style.top = Math.max(10, Math.min(innerHeight - h - 10, cy - h - 14)) + 'px';
  }

  // ---- labels --------------------------------------------------------------
  const labelHost = document.getElementById('labels');
  const propLabels = DATA.properties.map((p) => {
    const el = document.createElement('div');
    el.className = 'lab'; el.textContent = p.n;
    el.style.setProperty('--c', hex(regionColour.get(p.g)));
    labelHost.appendChild(el);
    return { el: el, p: p };
  });
  let townLabelEl = null;
  (function townLabel() {
    if (!townTiles.length) return;
    const el = document.createElement('div');
    el.className = 'lab reg';
    el.textContent = 'Town Centre';
    el.style.setProperty('--c', '#5aa2ff');
    labelHost.appendChild(el);
    townLabelEl = {
      el: el,
      x: townTiles.reduce((s2, t) => s2 + t.x, 0) / townTiles.length,
      z: townTiles.reduce((s2, t) => s2 + t.z, 0) / townTiles.length,
    };
  })();

  const regionLabels = DATA.regions.map((name) => {
    const props = DATA.properties.filter((p) => p.g === name);
    const el = document.createElement('div');
    el.className = 'lab reg'; el.textContent = name;
    el.style.setProperty('--c', hex(regionColour.get(name)));
    labelHost.appendChild(el);
    return { el: el, name: name,
             x: props.reduce((s, p) => s + p.x, 0) / props.length,
             z: props.reduce((s, p) => s + p.z, 0) / props.length };
  });

  const v3 = new THREE.Vector3();
  function place(el, x, y, z, rect) {
    v3.set(x, y, z).project(camera);
    if (v3.z >= 1) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.style.transform = 'translate(-50%,-50%) translate(' +
      ((v3.x + 1) / 2) * rect.width + 'px,' + ((-v3.y + 1) / 2) * rect.height + 'px)';
  }
  function updateLabels() {
    const rect = canvas.getBoundingClientRect();
    // Close in, names help. From the whole portfolio they cover the map, so the
    // region a patch belongs to is the only label worth drawing.
    const near = ctrl.dist < 110;
    const reach = 24;
    for (const l of propLabels) {
      // A property you are pointing at on the roster keeps its name wherever it
      // is — that is the whole reason to hover it from across the portfolio.
      const pinned = hovered === l.p.n || (selected && selected === l.p);
      const show = pinned || (near && Math.hypot(l.p.x - ctrl.target.x, l.p.z - ctrl.target.z) < reach);
      l.el.classList.toggle('dim', Boolean(visibleSet && !visibleSet.has(l.p.n)));
      show ? place(l.el, l.p.x, 5, l.p.z, rect) : (l.el.style.display = 'none');
    }
    for (const l of regionLabels) near ? (l.el.style.display = 'none') : place(l.el, l.x, 12, l.z, rect);
    if (townLabelEl) place(townLabelEl.el, townLabelEl.x, 8, townLabelEl.z, rect);
  }

  // ---- HUD -------------------------------------------------------------------
  // The roster, the filters and the height variants. Same rules as the desktop
  // app, and for the same reasons — see public/js/roster.js and filters.js. The
  // scoring itself is NOT recomputed here: hp, severity and pip state are baked
  // into the payload by the build script, which imports the same module the
  // desktop app uses. Two implementations of "how bad is this property" would
  // have drifted apart by the second change.

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

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
  const glyph = (k) => (ICONS[k.icon]
    ? '<svg viewBox="0 0 12 12" aria-hidden="true">' + ICONS[k.icon] + '</svg>'
    : '<b>' + esc(k.parcel) + '</b>');

  const STATE_LABEL = {
    met: 'Met', warn: 'Slipping', fail: 'Failing',
    gap: 'No data — feed stopped', na: 'Not applicable', wait: 'Not connected yet',
  };
  const band = (hp) => (hp > 70 ? '' : hp >= 40 ? 'm-amber' : 'm-red');
  const SEGMENTS = 20;
  const segs = (hp) => {
    const on = Math.round((hp / 100) * SEGMENTS);
    let out = '';
    for (let i = 0; i < SEGMENTS; i++) out += '<span class="seg' + (i < on ? ' on' : '') + '"></span>';
    return out;
  };

  // "Needs you" counts properties with at least one KPI slipping, failing or
  // dark — NOT properties with a low composite. A property that is fine on
  // average but has one line 90% over still needs someone, and a headline that
  // averaged it away would be the first thing in this app to lie.
  const needsSomeone = (p) =>
    p.gaps > 0 || DATA.kpis.some((k) => {
      const c = p.c[k.id];
      return c && (c.st === 'fail' || c.st === 'warn');
    });
  $('s-props').textContent = DATA.properties.length;
  $('s-bad').textContent = DATA.properties.filter(needsSomeone).length;
  $('s-flat').textContent = DATA.properties.filter((p) => !needsSomeone(p)).length;
  $('stamp').textContent = DATA.stamp;

  const state = { region: null, band: null, kpi: null, height: 'worst', sort: 'hp', group: true, q: '' };
  let selected = null, focusedParcel = null, hovered = null;

  // ---- filters ---------------------------------------------------------------
  // One filter state drives the map and the roster. Two views of one portfolio
  // disagreeing about what is on screen is worse than having no filter at all.

  const VARIANTS = [
    ['worst', 'Worst KPI', 'Each pillar is its own reading. The default, and the honest one.'],
    ['focus', 'One KPI', 'Only the chosen KPI stands up. Everything else lies flat.'],
    ['flat', 'Flat', 'Nothing stands up. Colour and the roster carry it.'],
  ];

  function renderFilters() {
    const chip = (f, v, label, cls) =>
      '<button class="fchip ' + (cls || '') + (state[f] === v ? ' on' : '') +
      '" data-f="' + f + '" data-v="' + v + '">' + label + '</button>';

    let html = '<div class="fgroup"><span class="flabel">Neighbourhood</span>' +
      '<select data-s="region"><option value="">All</option>' +
      DATA.regions.map((r) => '<option value="' + esc(r) + '"' +
        (state.region === r ? ' selected' : '') + '>' + esc(r) + '</option>').join('') +
      '</select></div>';

    html += '<div class="fgroup"><span class="flabel">Show</span>' +
      chip('band', 'failing', 'Failing', 'crit') + chip('band', 'watch', 'Watch', 'watch') +
      chip('band', 'steady', 'Steady', 'ok') + chip('band', 'gap', 'No data', 'gap') + '</div>';

    html += '<div class="fgroup"><span class="flabel">KPI</span>' +
      '<select data-s="kpi"><option value="">Any</option>' +
      DATA.kpis.map((k) => '<option value="' + esc(k.id) + '"' +
        (state.kpi === k.id ? ' selected' : '') + '>' + esc(k.parcel) + ' · ' + esc(k.label) +
        '</option>').join('') + '</select></div>';

    html += '<div class="fgroup"><span class="flabel">Height</span>' +
      VARIANTS.map(([id, label, hint]) =>
        '<button class="fchip' + (state.height === id ? ' on' : '') + '" data-f="height" data-v="' +
        id + '" title="' + esc(hint) + '">' + label + '</button>').join('') + '</div>';

    // "One KPI" with nothing chosen would silently flatten the whole map, so say
    // what is missing rather than looking broken.
    if (state.height === 'focus' && !state.kpi) {
      html += '<span class="fwarn">Pick a KPI above — nothing is raised until you do.</span>';
    }
    html += '<span class="fspacer"></span>';
    if (state.region || state.band || state.kpi) {
      html += '<button class="fchip clear" data-f="clear" data-v="">Clear filters</button>';
    }
    $('filterbar').innerHTML = html;
  }

  $('filterbar').addEventListener('click', (e) => {
    const b = e.target.closest('[data-f]');
    if (!b) return;
    if (b.dataset.f === 'clear') { state.region = state.band = state.kpi = null; }
    else {
      // Clicking the active chip clears it. A filter you cannot get out of by
      // clicking the thing you clicked to get in is a trap.
      state[b.dataset.f] = state[b.dataset.f] === b.dataset.v ? null : b.dataset.v;
      if (b.dataset.f === 'height' && !state.height) state.height = 'worst';
    }
    apply();
  });
  $('filterbar').addEventListener('change', (e) => {
    const s = e.target.closest('[data-s]');
    if (!s) return;
    state[s.dataset.s] = s.value || null;
    apply();
  });

  function matches(p) {
    if (state.region && p.g !== state.region) return false;
    if (state.kpi) {
      const cell = p.c[state.kpi];
      const st = cell ? cell.st : 'wait';
      if (!state.band) return st === 'fail' || st === 'warn' || st === 'gap';
      return bandOfState(st) === state.band;
    }
    if (state.band === 'gap') return p.gaps > 0;
    if (state.band === 'failing') return p.hp < 40;
    if (state.band === 'watch') return p.hp >= 40 && p.hp <= 70;
    if (state.band === 'steady') return p.hp > 70;
    return true;
  }
  function bandOfState(st) {
    return st === 'fail' ? 'failing' : st === 'warn' ? 'watch' : st === 'gap' ? 'gap'
      : st === 'met' ? 'steady' : null;
  }

  // ---- roster ----------------------------------------------------------------

  function visible() {
    const q = state.q.trim().toLowerCase();
    return DATA.properties.filter((p) => {
      if (!matches(p)) return false;
      if (!q) return true;
      return p.n.toLowerCase().includes(q) || p.g.toLowerCase().includes(q) ||
        (p.dir || '').toLowerCase().includes(q);
    });
  }

  function pip(p, k) {
    const cell = p.c[k.id];
    const st = cell ? cell.st : 'wait';
    const title = k.parcel + ' · ' + k.label + ' — ' + STATE_LABEL[st] +
      (cell && cell.d ? '\n' + cell.d : '');
    const inner = st === 'na' || st === 'wait' ? '' : glyph(k);
    return '<span class="pip ' + st + '" title="' + esc(title) + '">' + inner + '</span>';
  }

  function cardHTML(p) {
    const sub = p.dir
      ? esc(p.dir) + (state.group ? '' : ' · ' + esc(p.g))
      : '<span class="faint">' + (state.group ? 'no director on file' : esc(p.g)) + '</span>';
    return '<article class="rcard ' + band(p.hp) + (selected === p ? ' on' : '') +
      '" data-n="' + esc(p.n) + '">' +
      '<div class="rid"><span class="prop">' + esc(p.n) + '</span><span class="dir">' + sub + '</span></div>' +
      '<div class="hpnum">' + p.hp + '</div>' +
      '<div class="segs">' + segs(p.hp) + '</div>' +
      '<div class="var' + (p.va < 0 ? ' over' : '') + '">' + (p.va ? money(p.va) : '—') + '</div>' +
      '<div class="pips">' + DATA.kpis.map((k) => pip(p, k)).join('') + '</div></article>';
  }

  function groupHead(name, list) {
    const avg = Math.round(list.reduce((s, p) => s + p.hp, 0) / list.length);
    return '<div class="ghead' + (name === 'Unassigned' ? ' un' : '') + '">' +
      '<span class="nm">' + esc(name) + '</span><span class="ct">' + list.length + ' ' +
      (list.length === 1 ? 'property' : 'properties') + '</span>' +
      '<span class="avg ' + band(avg) + '"><em>avg</em><span class="segs">' + segs(avg) +
      '</span><span class="hpnum">' + avg + '</span></span></div>';
  }

  function renderRoster() {
    const rows = visible();

    const crit = rows.filter((p) => p.hp < 40).length;
    const watch = rows.filter((p) => p.hp >= 40 && p.hp <= 70).length;
    const gaps = rows.reduce((s, p) => s + p.gaps, 0);
    const va = rows.reduce((s, p) => s + p.va, 0);
    $('r-tally').innerHTML =
      '<span class="rchip crit"><i></i>Critical <b>' + crit + '</b></span>' +
      '<span class="rchip watch"><i></i>Watch <b>' + watch + '</b></span>' +
      '<span class="rchip ok"><i></i>Steady <b>' + (rows.length - crit - watch) + '</b></span>' +
      (gaps ? '<span class="rchip gap" title="Parcels whose feed stopped reporting"><i></i>No data <b>' + gaps + '</b></span>' : '') +
      '<span class="rchip">Variance <b class="' + (va < 0 ? 'bad' : 'good') + '">' + money(va) + '</b></span>';

    if (!$('r-legend').dataset.built) {
      $('r-legend').dataset.built = '1';
      $('r-legend').innerHTML = DATA.kpis.map((k) =>
        '<div><span class="pip">' + glyph(k) + '</span>' + esc(k.parcel) + ' · ' + esc(k.label) + '</div>').join('');
    }

    const list = $('r-list');
    if (!rows.length) { list.innerHTML = '<p class="empty">No property matches these filters.</p>'; return; }

    const cmp = {
      hp: (a, b) => a.hp - b.hp || a.n.localeCompare(b.n),
      name: (a, b) => a.n.localeCompare(b.n),
      leader: (a, b) => a.g.localeCompare(b.g) || a.hp - b.hp,
      variance: (a, b) => a.va - b.va,
      gaps: (a, b) => b.gaps - a.gaps || a.hp - b.hp,
    }[state.sort];
    const sorted = rows.slice().sort(cmp);

    if (!state.group) { list.innerHTML = sorted.map(cardHTML).join(''); return; }

    const groups = new Map();
    for (const p of sorted) {
      if (!groups.has(p.g)) groups.set(p.g, []);
      groups.get(p.g).push(p);
    }
    // Unassigned last, always — it is a data-quality bucket, not a real book.
    const order = [...groups.keys()].sort((a, b) => {
      if (a === 'Unassigned') return 1;
      if (b === 'Unassigned') return -1;
      if (state.sort === 'name' || state.sort === 'leader') return a.localeCompare(b);
      const av = groups.get(a).reduce((s, p) => s + p.hp, 0) / groups.get(a).length;
      const bv = groups.get(b).reduce((s, p) => s + p.hp, 0) / groups.get(b).length;
      return av - bv;
    });
    list.innerHTML = order.map((k) => groupHead(k, groups.get(k)) + groups.get(k).map(cardHTML).join('')).join('');
  }

  $('r-sort').addEventListener('change', (e) => { state.sort = e.target.value; renderRoster(); });
  const groupBtn = $('r-group');
  groupBtn.addEventListener('click', () => {
    state.group = !state.group;
    groupBtn.setAttribute('aria-pressed', String(state.group));
    renderRoster();
  });
  let qTimer;
  $('r-q').addEventListener('input', (e) => {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => { state.q = e.target.value; apply(); }, 110);
  });

  // Delegated: the list is rebuilt whenever a filter moves, so a handler bound
  // to a row would be pointing at a detached node most of the time.
  $('r-list').addEventListener('click', (e) => {
    const card = e.target.closest('.rcard');
    if (!card) return;
    select(DATA.properties.find((p) => p.n === card.dataset.n));
  });
  $('r-list').addEventListener('mouseover', (e) => {
    const card = e.target.closest('.rcard');
    setHover(card ? card.dataset.n : null);
  });
  $('r-list').addEventListener('mouseleave', () => setHover(null));

  function setHover(name) {
    if (hovered === name) return;
    hovered = name;
    // Pointing at a card pins that property's label on the map. Without it,
    // finding a name from the roster means hunting 185 identical hexes.
    $('r-list').classList.toggle('focused', Boolean(name));
    for (const card of $('r-list').querySelectorAll('.rcard')) {
      card.classList.toggle('active', card.dataset.n === name);
    }
  }

  // ---- detail card -----------------------------------------------------------

  function select(p, parcel) {
    selected = p || null;
    focusedParcel = parcel || null;
    const card = $('card');
    // The card and the legend want the same corner. Once you have opened a
    // property the legend has done its job, so it stands aside rather than
    // being scrolled behind.
    $('legend').style.display = p ? 'none' : 'flex';
    if (!p) { card.style.display = 'none'; renderRoster(); return; }
    flyTo(p.x, p.z, 62);
    card.style.display = 'flex';

    const st = statusOf(p.sev);
    const cells = DATA.kpis.map((k) => ({ k: k, cell: p.c[k.id] || null }));
    const rank = { fail: 0, gap: 1, warn: 2, met: 3, na: 4, wait: 5 };
    cells.sort((a, b) => {
      const sa = a.cell ? a.cell.st : 'wait', sb = b.cell ? b.cell.st : 'wait';
      return rank[sa] - rank[sb] || a.k.parcel.localeCompare(b.k.parcel);
    });

    $('c-body').innerHTML =
      '<div class="ch"><button class="close" id="c-close" aria-label="Close">×</button>' +
      '<div class="kind">' + esc(p.g) + (p.dir ? ' · ' + esc(p.dir) : '') + '</div>' +
      '<h3>' + esc(p.n) + '</h3>' +
      '<span class="chip" style="background:' + hex(COL[st]) + '22;color:' + hex(COL[st]) + '">' +
      LABEL[st] + ' · HP ' + p.hp + '</span></div>' +
      '<div class="bars">' + cells.map((row) => {
        const k = row.k, c = row.cell;
        const s = c ? c.st : 'wait';
        const quiet = s === 'na' || s === 'wait';
        const colour = s === 'gap' ? '#d7dde8' : hex(COL[statusOf(c ? c.s : 0)]);
        return '<div class="bar' + (k.id === focusedParcel ? ' hit' : '') + (quiet ? ' quiet' : '') + '">' +
          '<span class="bn"><span class="pip ' + s + '">' +
          (quiet ? '' : glyph(k)) + '</span>' + esc(k.label) + '</span>' +
          '<span class="bv" style="color:' + (quiet ? 'var(--muted)' : colour) + '">' +
          esc(c ? c.h : 'no feed') + '</span>' +
          (quiet ? '' : '<span class="track"><span class="fill" style="width:' +
            Math.max(2, (c.s || 0) * 100) + '%;background:' + colour + '"></span></span>') +
          '</div>';
      }).join('') + '</div>';

    $('c-close').addEventListener('click', () => select(null));
    renderRoster();
  }

  // ---- apply -----------------------------------------------------------------
  // One place where a state change reaches the map, so the two can never end up
  // showing different portfolios.

  function apply() {
    renderFilters();
    renderRoster();
    const shown = new Set(visible().map((p) => p.n));
    const filtering = Boolean(state.region || state.band || state.kpi || state.q.trim());
    setVisibleSet(filtering ? shown : null);
    setHeightVariant(state.height, state.height === 'focus' ? state.kpi : null);
  }

  apply();

  // ---- frame ---------------------------------------------------------------
  function resize() {
    const w = canvas.clientWidth || innerWidth, h = canvas.clientHeight || innerHeight;
    camera.aspect = w / h; camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }
  addEventListener('resize', resize);
  resize();

  const clock = new THREE.Clock();
  (function frame() {
    requestAnimationFrame(frame);
    const t = clock.getElapsedTime();
    // One shared pulse, so every alarm in the city breathes together — a
    // scattered flicker reads as noise.
    const pulse = .38 + (.5 + .5 * Math.sin(t * 3.2)) * .5;
    bucketMat.failed.emissiveIntensity = pulse;
    bucketMat.blocked.emissiveIntensity = .34 + pulse * .35;
    bucketMat.nodata.emissiveIntensity = .28 + pulse * .3;
    updateCamera();
    updateLabels();
    renderer.render(scene, camera);
  })();
})();
