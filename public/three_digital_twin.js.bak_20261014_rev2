/**
 * SmartPark Vision AI - 3D WebGL Digital Twin Engine (Three.js)
 * High-performance spatial simulation of the parking facility.
 * Designed for modular embedding, clean API control, and AI model refinement.
 */

(function (global) {
  'use strict';

  class ParkingDigitalTwin {
    constructor(containerId, options = {}) {
      this.container = document.getElementById(containerId);
      if (!this.container) {
        console.warn(`[SmartPark3D] Conteneur #${containerId} introuvable.`);
        return;
      }

      this.options = Object.assign({
        antialias: true,
        shadows: true,
        autoRotate: false,
        onStallClick: null,
      }, options);

      this.scene = null;
      this.camera = null;
      this.renderer = null;
      this.controls = null;

      // Animatable Objects
      this.barrierArm1 = null;
      this.barrierArm2 = null;
      this.activeCar = null;
      this.stalls = [];
      this.spotlights = [];

      this.isGate1Open = false;
      this.isGate2Open = false;

      this.init();
    }

    init() {
      const width = this.container.clientWidth || 800;
      const height = this.container.clientHeight || 500;

      // 1. Scene Setup
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0x060913);
      this.scene.fog = new THREE.FogExp2(0x060913, 0.018);

      // 2. Camera Setup
      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 500);
      this.camera.position.set(28, 22, 30);

      // 3. Renderer Setup with PBR Tone Mapping
      this.renderer = new THREE.WebGLRenderer({
        antialias: this.options.antialias,
        powerPreference: 'high-performance',
      });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.renderer.shadowMap.enabled = this.options.shadows;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.1;

      // Empty container before mount
      this.container.innerHTML = '';
      this.container.appendChild(this.renderer.domElement);

      // 4. OrbitControls
      if (typeof THREE.OrbitControls !== 'undefined') {
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxPolarAngle = Math.PI / 2.05;
        this.controls.minDistance = 6;
        this.controls.maxDistance = 100;
        this.controls.target.set(0, 0, 0);
      }

      // 5. Lighting Setup
      this.setupLighting();

      // 6. Architecture & Geometry
      this.buildArchitecture();

      // 7. Barriers & Kiosks
      this.buildGatesAndKiosks();

      // 8. 14 Parking Stalls & Cars
      this.buildStalls();

      // 9. Camera Scanning Cones (Wireframe Frustums)
      this.createScannerCone(-3.8, 4.2, -18, 0, 0, -10, 0x10B981, 'CAM-01 ALPR');
      this.createScannerCone(-4.2, 2.5, -13.5, -3.5, 1.2, -13.5, 0x06B6D4, 'CAM-02 Face');
      this.createScannerCone(3.8, 4.2, 18, 0, 0, 10, 0x14B8A6, 'CAM-03 Exit');

      // 10. Start Animation Loop
      this.animate = this.animate.bind(this);
      requestAnimationFrame(this.animate);

      // 11. Handle Resizing
      window.addEventListener('resize', () => this.onResize());
    }

    setupLighting() {
      // Soft Ambient Light
      this.ambientLight = new THREE.AmbientLight(0x94A3B8, 0.4);
      this.scene.add(this.ambientLight);

      // Main Sun / Directional Light with Soft Shadows
      this.sunLight = new THREE.DirectionalLight(0xE2E8F0, 0.85);
      this.sunLight.position.set(25, 45, 20);
      this.sunLight.castShadow = true;
      this.sunLight.shadow.mapSize.width = 1024;
      this.sunLight.shadow.mapSize.height = 1024;
      this.sunLight.shadow.camera.near = 10;
      this.sunLight.shadow.camera.far = 120;
      this.sunLight.shadow.camera.left = -30;
      this.sunLight.shadow.camera.right = 30;
      this.sunLight.shadow.camera.top = 30;
      this.sunLight.shadow.camera.bottom = -30;
      this.sunLight.shadow.bias = -0.0005;
      this.scene.add(this.sunLight);

      // Ceiling Industrial Tube Fixtures (PointLights)
      const lightPositions = [
        [-12, 6, -10], [-12, 6, 0], [-12, 6, 10],
        [12, 6, -10],  [12, 6, 0],  [12, 6, 10],
        [0, 6, -12],   [0, 6, 0],   [0, 6, 12]
      ];

      lightPositions.forEach(pos => {
        const pl = new THREE.PointLight(0xBAE6FD, 0.35, 22, 1.8);
        pl.position.set(...pos);
        this.scene.add(pl);
      });
    }

    buildArchitecture() {
      // 1. Asphalt Ground Plane
      const floorGeo = new THREE.PlaneGeometry(64, 48);
      const floorMat = new THREE.MeshStandardMaterial({
        color: 0x0B1120,
        roughness: 0.88,
        metalness: 0.12,
      });
      const floor = new THREE.Mesh(floorGeo, floorMat);
      floor.rotation.x = -Math.PI / 2;
      floor.receiveShadow = true;
      this.scene.add(floor);

      // 2. High-Tech Precision Grid Lines
      const grid = new THREE.GridHelper(64, 32, 0x1E293B, 0x0F172A);
      grid.position.y = 0.01;
      this.scene.add(grid);

      // 3. Central Driving Aisle (Asphalt Lane)
      const laneGeo = new THREE.PlaneGeometry(9, 48);
      const laneMat = new THREE.MeshStandardMaterial({
        color: 0x080D1A,
        roughness: 0.75,
      });
      const lane = new THREE.Mesh(laneGeo, laneMat);
      lane.rotation.x = -Math.PI / 2;
      lane.position.set(0, 0.015, 0);
      lane.receiveShadow = true;
      this.scene.add(lane);

      // 4. Concrete Structural Columns
      const colGeo = new THREE.BoxGeometry(1.2, 7, 1.2);
      const colMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.6 });
      const columnPositions = [
        [-6, 3.5, -10], [-6, 3.5, 5],
        [6, 3.5, -10],  [6, 3.5, 5]
      ];
      columnPositions.forEach(pos => {
        const col = new THREE.Mesh(colGeo, colMat);
        col.position.set(...pos);
        col.castShadow = true;
        col.receiveShadow = true;
        this.scene.add(col);
      });

      // 5. Ground Inductive Loop Coils (Yellow outline on road)
      const loopGeo = new THREE.PlaneGeometry(4.5, 2.2);
      const loopMat = new THREE.MeshBasicMaterial({ color: 0xEAB308, wireframe: true });
      const loop1 = new THREE.Mesh(loopGeo, loopMat);
      loop1.rotation.x = -Math.PI / 2;
      loop1.position.set(-2, 0.025, -13.5);
      this.scene.add(loop1);

      const loop2 = new THREE.Mesh(loopGeo, loopMat);
      loop2.rotation.x = -Math.PI / 2;
      loop2.position.set(2, 0.025, 13.5);
      this.scene.add(loop2);
    }

    buildGatesAndKiosks() {
      // ---- ENTRY GATE (VOIE 1) ----
      const housingGeo = new THREE.BoxGeometry(0.8, 1.8, 0.8);
      const housingMat = new THREE.MeshStandardMaterial({ color: 0xF59E0B, metalness: 0.6, roughness: 0.3 });
      
      const p1 = new THREE.Mesh(housingGeo, housingMat);
      p1.position.set(-4.2, 0.9, -15);
      p1.castShadow = true;
      this.scene.add(p1);

      // Barrier Arm with Pivot Group
      this.barrierArm1 = new THREE.Group();
      this.barrierArm1.position.set(-4.2, 1.6, -15);

      const armMesh1 = new THREE.Mesh(
        new THREE.BoxGeometry(6.4, 0.14, 0.14),
        new THREE.MeshStandardMaterial({ color: 0xFDE047, roughness: 0.3 })
      );
      armMesh1.position.set(3.2, 0, 0); // Offset so pivot is at end
      armMesh1.castShadow = true;
      this.barrierArm1.add(armMesh1);
      this.scene.add(this.barrierArm1);

      // Kiosk Post & Touchscreen
      const kiosk = new THREE.Mesh(
        new THREE.BoxGeometry(0.6, 1.6, 0.6),
        new THREE.MeshStandardMaterial({ color: 0x0F172A, metalness: 0.8, roughness: 0.2 })
      );
      kiosk.position.set(-4.5, 0.8, -13.5);
      this.scene.add(kiosk);

      const screen = new THREE.Mesh(
        new THREE.PlaneGeometry(0.35, 0.45),
        new THREE.MeshBasicMaterial({ color: 0x06B6D4 })
      );
      screen.position.set(-4.19, 1.25, -13.5);
      screen.rotation.y = Math.PI / 2;
      this.scene.add(screen);

      // ---- EXIT GATE (VOIE 2) ----
      const p2 = new THREE.Mesh(housingGeo, housingMat);
      p2.position.set(4.2, 0.9, 15);
      p2.castShadow = true;
      this.scene.add(p2);

      this.barrierArm2 = new THREE.Group();
      this.barrierArm2.position.set(4.2, 1.6, 15);

      const armMesh2 = new THREE.Mesh(
        new THREE.BoxGeometry(6.4, 0.14, 0.14),
        new THREE.MeshStandardMaterial({ color: 0xFDE047, roughness: 0.3 })
      );
      armMesh2.position.set(-3.2, 0, 0);
      armMesh2.castShadow = true;
      this.barrierArm2.add(armMesh2);
      this.scene.add(this.barrierArm2);
    }

    buildStalls() {
      // 7 Stalls on Left (Zone A & B), 7 Stalls on Right (Zone C & D)
      const stallData = [
        { id: 'A01', x: -14, z: -15, status: 'occupied', color: 0x0284C7 },
        { id: 'A02', x: -14, z: -10, status: 'occupied', color: 0x1E293B },
        { id: 'A03', x: -14, z: -5,  status: 'vacant',   color: null },
        { id: 'A04', x: -14, z: 0,   status: 'reserved', color: null },
        { id: 'B01', x: -14, z: 5,   status: 'occupied', color: 0x0F766E },
        { id: 'B02', x: -14, z: 10,  status: 'vacant',   color: null },
        { id: 'B03', x: -14, z: 15,  status: 'occupied', color: 0x475569 },

        { id: 'C01', x: 14, z: -15, status: 'occupied', color: 0x334155 },
        { id: 'C02', x: 14, z: -10, status: 'vacant',   color: null },
        { id: 'C03', x: 14, z: -5,  status: 'vacant',   color: null },
        { id: 'C04', x: 14, z: 0,   status: 'occupied', color: 0xB91C1C },
        { id: 'D01', x: 14, z: 5,   status: 'vacant',   color: null },
        { id: 'D02', x: 14, z: 10,  status: 'occupied', color: 0x1E293B },
        { id: 'D03', x: 14, z: 15,  status: 'vacant',   color: null },
      ];

      stallData.forEach(item => {
        // Painted Boundary Marking
        const lineGeo = new THREE.EdgesGeometry(new THREE.BoxGeometry(6.4, 0.05, 4.0));
        const lineMat = new THREE.MeshBasicMaterial({ color: 0x475569 });
        const stallOutline = new THREE.LineSegments(lineGeo, lineMat);
        stallOutline.position.set(item.x, 0.03, item.z);
        this.scene.add(stallOutline);

        // Overhead Sensor Beacon
        const beaconGeo = new THREE.SphereGeometry(0.22, 16, 16);
        let beaconColor = 0x10B981; // Green = vacant
        if (item.status === 'occupied') beaconColor = 0xEF4444; // Red = occupied
        else if (item.status === 'reserved') beaconColor = 0x8B5CF6; // Purple = reserved

        const beaconMat = new THREE.MeshBasicMaterial({ color: beaconColor });
        const beacon = new THREE.Mesh(beaconGeo, beaconMat);
        beacon.position.set(item.x, 3.2, item.z);
        this.scene.add(beacon);

        // Procedural 3D Car if occupied
        let carMesh = null;
        if (item.status === 'occupied' && item.color) {
          carMesh = this.createCar(item.x, item.z, item.color);
        }

        this.stalls.push({
          id: item.id,
          x: item.x,
          z: item.z,
          beacon: beacon,
          car: carMesh,
          status: item.status,
        });
      });
    }

    createCar(x, z, colorHex) {
      const car = new THREE.Group();

      // Lower Chassis
      const bodyGeo = new THREE.BoxGeometry(4.4, 0.9, 2.2);
      const bodyMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        roughness: 0.25,
        metalness: 0.75,
      });
      const body = new THREE.Mesh(bodyGeo, bodyMat);
      body.position.y = 0.65;
      body.castShadow = true;
      car.add(body);

      // Cabin / Tinted Glass
      const cabinGeo = new THREE.BoxGeometry(2.4, 0.75, 1.8);
      const cabinMat = new THREE.MeshStandardMaterial({
        color: 0x050811,
        roughness: 0.1,
        metalness: 0.9,
      });
      const cabin = new THREE.Mesh(cabinGeo, cabinMat);
      cabin.position.set(-0.25, 1.45, 0);
      cabin.castShadow = true;
      car.add(cabin);

      // Wheels
      const wheelGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.3, 16);
      const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.8 });
      const offsets = [
        [1.3, 0.35, 1.1], [-1.3, 0.35, 1.1],
        [1.3, 0.35, -1.1], [-1.3, 0.35, -1.1]
      ];
      offsets.forEach(wpos => {
        const wheel = new THREE.Mesh(wheelGeo, wheelMat);
        wheel.rotation.x = Math.PI / 2;
        wheel.position.set(...wpos);
        car.add(wheel);
      });

      // Front Headlights
      const hlMat = new THREE.MeshBasicMaterial({ color: 0xFEF08A });
      const hl1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.18, 0.35), hlMat);
      hl1.position.set(2.2, 0.7, 0.7);
      car.add(hl1);
      const hl2 = hl1.clone();
      hl2.position.set(2.2, 0.7, -0.7);
      car.add(hl2);

      // Algerian Yellow Front License Plate
      const plateMat = new THREE.MeshBasicMaterial({ color: 0xFDE047 });
      const plate = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.16, 0.7), plateMat);
      plate.position.set(2.22, 0.45, 0);
      car.add(plate);

      car.position.set(x, 0, z);
      this.scene.add(car);
      return car;
    }

    createScannerCone(x, y, z, tx, ty, tz, colorHex, label) {
      const coneGeo = new THREE.ConeGeometry(2.4, 6, 4, 1, true);
      const coneMat = new THREE.MeshBasicMaterial({
        color: colorHex,
        wireframe: true,
        transparent: true,
        opacity: 0.22,
      });
      const cone = new THREE.Mesh(coneGeo, coneMat);
      cone.position.set(x, y, z);
      cone.lookAt(tx, ty, tz);
      cone.rotateX(Math.PI / 2);
      this.scene.add(cone);
    }

    // ---- GATE ANIMATION CONTROLS ----
    setGate1(open) {
      this.isGate1Open = open;
      const targetZ = open ? Math.PI / 2.2 : 0;
      this.smoothRotate(this.barrierArm1, targetZ);
    }

    setGate2(open) {
      this.isGate2Open = open;
      const targetZ = open ? -Math.PI / 2.2 : 0;
      this.smoothRotate(this.barrierArm2, targetZ);
    }

    smoothRotate(group, targetAngle) {
      if (!group) return;
      const start = group.rotation.z;
      const diff = targetAngle - start;
      let step = 0;
      const totalSteps = 18;

      const interval = setInterval(() => {
        step++;
        // Easing out cubic
        const progress = step / totalSteps;
        const ease = 1 - Math.pow(1 - progress, 3);
        group.rotation.z = start + diff * ease;

        if (step >= totalSteps) {
          group.rotation.z = targetAngle;
          clearInterval(interval);
        }
      }, 16);
    }

    // ---- CAMERA PRESET VIEWS ----
    setCameraPreset(preset) {
      if (!this.camera || !this.controls) return;
      const duration = 600;

      const presets = {
        isometric: { pos: [28, 22, 30], target: [0, 0, 0] },
        entry:     { pos: [-3, 3.8, -22], target: [-2, 1.2, -14] },
        kiosk:     { pos: [-6.5, 2.2, -13.5], target: [-4.2, 1.25, -13.5] },
        exit:      { pos: [3, 3.8, 10], target: [2, 1.2, 18] },
        top:       { pos: [0, 52, 0.1], target: [0, 0, 0] }
      };

      const p = presets[preset] || presets.isometric;
      this.camera.position.set(...p.pos);
      this.controls.target.set(...p.target);
      this.controls.update();
    }

    setTheme(isDark) {
      if (!this.scene) return;
      if (isDark) {
        this.scene.background.setHex(0x060913);
        if (this.scene.fog) this.scene.fog.color.setHex(0x060913);
        if (this.ambientLight) {
          this.ambientLight.color.setHex(0x94A3B8);
          this.ambientLight.intensity = 0.4;
        }
        if (this.sunLight) {
          this.sunLight.color.setHex(0xE2E8F0);
          this.sunLight.intensity = 0.85;
        }
        if (this.renderer) this.renderer.toneMappingExposure = 1.1;
      } else {
        this.scene.background.setHex(0xD8E2EC);
        if (this.scene.fog) this.scene.fog.color.setHex(0xD8E2EC);
        if (this.ambientLight) {
          this.ambientLight.color.setHex(0xFFFFFF);
          this.ambientLight.intensity = 0.85;
        }
        if (this.sunLight) {
          this.sunLight.color.setHex(0xFFFBEB);
          this.sunLight.intensity = 1.45;
        }
        if (this.renderer) this.renderer.toneMappingExposure = 1.25;
      }
    }

    onResize() {
      if (!this.container || !this.renderer || !this.camera) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    }

    animate() {
      requestAnimationFrame(this.animate);
      if (this.controls) this.controls.update();
      this.renderer.render(this.scene, this.camera);
    }
  }

  // Export globally
  global.ParkingDigitalTwin = ParkingDigitalTwin;

})(window);
