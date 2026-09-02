import * as THREE from 'three';

/**
 * Compact orbit/pan/zoom controller.
 *
 * Written rather than imported so the camera feel can be tuned for a city you
 * lean over: rotation is clamped above the horizon (you never end up under the
 * ground plane) and panning moves along the ground rather than the view plane,
 * which is what makes dragging across a map feel right.
 */
export class MapControls {
  constructor(camera, dom) {
    this.camera = camera;
    this.dom = dom;

    this.target = new THREE.Vector3(0, 0, 0);
    this.distance = 62;
    this.minDistance = 18;
    this.maxDistance = 320;
    this.azimuth = -Math.PI / 4;
    this.polar = 0.95; // radians from vertical

    this.minPolar = 0.18;
    this.maxPolar = 1.42;

    this.velocity = { azimuth: 0, polar: 0 };
    this.panVelocity = new THREE.Vector3();
    this.zoomVelocity = 0;
    this.damping = 0.86;

    this.pointers = new Map();
    this.mode = null;
    this.last = { x: 0, y: 0 };
    this.pinchDistance = 0;

    this._bind();
    this.update(true);
  }

  _bind() {
    const dom = this.dom;
    dom.style.touchAction = 'none';

    dom.addEventListener('pointerdown', (e) => {
      dom.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (this.pointers.size === 1) {
        this.mode = e.button === 2 || e.shiftKey ? 'pan' : 'orbit';
        this.last = { x: e.clientX, y: e.clientY };
      } else if (this.pointers.size === 2) {
        this.mode = 'pinch';
        this.pinchDistance = this._pinchSpan();
      }
    });

    dom.addEventListener('pointermove', (e) => {
      if (!this.pointers.has(e.pointerId)) return;
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

      if (this.mode === 'pinch' && this.pointers.size === 2) {
        const span = this._pinchSpan();
        this.zoomVelocity += (this.pinchDistance - span) * 0.02;
        this.pinchDistance = span;
        return;
      }

      const dx = e.clientX - this.last.x;
      const dy = e.clientY - this.last.y;
      this.last = { x: e.clientX, y: e.clientY };

      if (this.mode === 'orbit') {
        this.velocity.azimuth -= dx * 0.005;
        this.velocity.polar -= dy * 0.005;
      } else if (this.mode === 'pan') {
        this._pan(dx, dy);
      }
    });

    const release = (e) => {
      this.pointers.delete(e.pointerId);
      if (this.pointers.size === 0) this.mode = null;
      else if (this.pointers.size === 1) this.mode = 'orbit';
    };
    dom.addEventListener('pointerup', release);
    dom.addEventListener('pointercancel', release);
    dom.addEventListener('contextmenu', (e) => e.preventDefault());

    dom.addEventListener(
      'wheel',
      (e) => {
        e.preventDefault();
        this.zoomVelocity += e.deltaY * 0.06;
      },
      { passive: false },
    );

    // Keyboard nudge — useful on a wall display with no mouse in reach.
    window.addEventListener('keydown', (e) => {
      if (e.target.matches('input, textarea')) return;
      const step = 6;
      if (e.key === 'ArrowLeft') this._pan(step, 0);
      if (e.key === 'ArrowRight') this._pan(-step, 0);
      if (e.key === 'ArrowUp') this._pan(0, step);
      if (e.key === 'ArrowDown') this._pan(0, -step);
    });
  }

  _pinchSpan() {
    const [a, b] = [...this.pointers.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  /** Pan along the ground plane, scaled by zoom so it feels constant on screen. */
  _pan(dx, dy) {
    const scale = this.distance * 0.0016;
    const forward = new THREE.Vector3(Math.sin(this.azimuth), 0, Math.cos(this.azimuth));
    const right = new THREE.Vector3(forward.z, 0, -forward.x);
    this.panVelocity.addScaledVector(right, dx * scale);
    this.panVelocity.addScaledVector(forward, dy * scale);
  }

  /** Ease the camera toward a point — used when jumping to an alert. */
  focus(x, z, distance = 46) {
    this.targetOverride = { x, z, distance };
  }

  update(immediate = false) {
    if (this.targetOverride) {
      const t = immediate ? 1 : 0.09;
      this.target.x += (this.targetOverride.x - this.target.x) * t;
      this.target.z += (this.targetOverride.z - this.target.z) * t;
      this.distance += (this.targetOverride.distance - this.distance) * t;
      if (Math.abs(this.targetOverride.x - this.target.x) < 0.4) this.targetOverride = null;
    }

    this.azimuth += this.velocity.azimuth;
    this.polar = THREE.MathUtils.clamp(
      this.polar + this.velocity.polar,
      this.minPolar,
      this.maxPolar,
    );
    this.target.add(this.panVelocity);
    this.distance = THREE.MathUtils.clamp(
      this.distance + this.zoomVelocity,
      this.minDistance,
      this.maxDistance,
    );

    this.velocity.azimuth *= this.damping;
    this.velocity.polar *= this.damping;
    this.panVelocity.multiplyScalar(this.damping);
    this.zoomVelocity *= this.damping;

    const sinPolar = Math.sin(this.polar);
    this.camera.position.set(
      this.target.x + this.distance * sinPolar * Math.sin(this.azimuth),
      this.target.y + this.distance * Math.cos(this.polar),
      this.target.z + this.distance * sinPolar * Math.cos(this.azimuth),
    );
    this.camera.lookAt(this.target);
  }
}
