/**
 * modules/viewer3d.js - Interactive 3D WebGL Model Viewport Engine
 * Powered by Three.js & OrbitControls
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

import { state, eventBus } from "../core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader } from "../core/api.js";

const els = {
  get v3dCanvasContainer() { return document.getElementById("viewport3dCanvasContainer"); },
  get v3dPlaceholder() { return document.getElementById("v3dPlaceholder"); },
  get v3dWeaponOnlyBtn() { return document.getElementById("v3dWeaponOnlyBtn"); },
  get v3dGlovesBtn() { return document.getElementById("v3dGlovesBtn"); },
  get v3dHighlightStickersBtn() { return document.getElementById("v3dHighlightStickersBtn"); },
  get v3dFocusWeaponBtn() { return document.getElementById("v3dFocusWeaponBtn"); },
  get v3dResetCamBtn() { return document.getElementById("v3dResetCamBtn"); },
  get v3dFpvBtn() { return document.getElementById("v3dFpvBtn"); },
  get v3dShowcaseBtn() { return document.getElementById("v3dShowcaseBtn"); },
  get v3dAutoRotateBtn() { return document.getElementById("v3dAutoRotateBtn"); },
  get v3dWireframeBtn() { return document.getElementById("v3dWireframeBtn"); },
  get v3dChromeShineBtn() { return document.getElementById("v3dChromeShineBtn"); },
  get v3dSnapshotBtn() { return document.getElementById("v3dSnapshotBtn"); },
  get v3dStats() { return document.getElementById("v3dStats"); },
  get v3dReloadBtn() { return document.getElementById("v3dReloadBtn"); },
  get v3dSoundPreviewBtn() { return document.getElementById("v3dSoundPreviewBtn"); },

  // Tactical CS 1.6 FPV Crosshair
  get v3dFpvCrosshair() { return document.getElementById("v3dFpvCrosshair"); },

  // Floating 3D Slot Repositioning Banner
  get v3dRepositionBanner() { return document.getElementById("v3dRepositionBanner"); },
  get v3dRepositionSlotName() { return document.getElementById("v3dRepositionSlotName"); },
  get v3dRepositionCancelBtn() { return document.getElementById("v3dRepositionCancelBtn"); },

  // POV Drawer & Inspection
  get v3dPovSettingsBtn() { return document.getElementById("v3dPovSettingsBtn"); },
  get v3dInspectBtn() { return document.getElementById("v3dInspectBtn"); },
  get v3dPovDrawer() { return document.getElementById("v3dPovDrawer"); },
  get v3dPovDrawerCloseBtn() { return document.getElementById("v3dPovDrawerCloseBtn"); },

  // Sequence Player HUD Controls
  get hudSeqSelect() { return document.getElementById("hudSeqSelect"); },
  get hudSeqPlayBtn() { return document.getElementById("hudSeqPlayBtn"); },
  get hudSeqScrubber() { return document.getElementById("hudSeqScrubber"); },
  get hudSeqFrameDisplay() { return document.getElementById("hudSeqFrameDisplay"); },
};

let repositionReticleMesh = null;
let currentHoverHit = null;
let pointerDownPos = { x: 0, y: 0, time: 0 };

// ==========================================
// StatTrak 3D Digital LED Projection System
// ==========================================
const STATTRAK_PALETTES = {
  orange: {
    lit: "#ff7700",
    core: "#ffeedd",
    glow: "rgba(255, 119, 0, 0.85)",
    unlit: "rgba(35, 16, 5, 0.85)",
  },
  cyan: {
    lit: "#00d4ff",
    core: "#e6ffff",
    glow: "rgba(0, 212, 255, 0.85)",
    unlit: "rgba(5, 25, 35, 0.85)",
  },
  red: {
    lit: "#ff2244",
    core: "#ffe6e9",
    glow: "rgba(255, 34, 68, 0.85)",
    unlit: "rgba(35, 8, 12, 0.85)",
  },
  green: {
    lit: "#00e676",
    core: "#e6ffed",
    glow: "rgba(0, 230, 118, 0.85)",
    unlit: "rgba(5, 32, 16, 0.85)",
  },
  violet: {
    lit: "#d500f9",
    core: "#fae6ff",
    glow: "rgba(213, 0, 249, 0.85)",
    unlit: "rgba(30, 5, 35, 0.85)",
  },
};

const STATTRAK_SEG_DEFS = {
  a: { x: 14, y: 8, w: 36, h: 10, orient: "h" },
  b: { x: 42, y: 16, w: 10, h: 26, orient: "v" },
  c: { x: 42, y: 50, w: 10, h: 26, orient: "v" },
  d: { x: 14, y: 74, w: 36, h: 10, orient: "h" },
  e: { x: 12, y: 50, w: 10, h: 26, orient: "v" },
  f: { x: 12, y: 16, w: 10, h: 26, orient: "v" },
  g: { x: 14, y: 40, w: 36, h: 10, orient: "h" },
};

const STATTRAK_SEG_MAP = {
  "0": [1, 1, 1, 1, 1, 1, 0],
  "1": [0, 1, 1, 0, 0, 0, 0],
  "2": [1, 1, 0, 1, 1, 0, 1],
  "3": [1, 1, 1, 1, 0, 0, 1],
  "4": [0, 1, 1, 0, 0, 1, 1],
  "5": [1, 0, 1, 1, 0, 1, 1],
  "6": [1, 0, 1, 1, 1, 1, 1],
  "7": [1, 1, 1, 0, 0, 0, 0],
  "8": [1, 1, 1, 1, 1, 1, 1],
  "9": [1, 1, 1, 1, 0, 1, 1],
  " ": [0, 0, 0, 0, 0, 0, 0],
  "-": [0, 0, 0, 0, 0, 0, 1],
};

function drawHexSegment(ctx, gx, gy, gw, gh, orient, inset = 0) {
  const x = gx + inset;
  const y = gy + inset;
  const w = Math.max(gw - inset * 2, 2);
  const h = Math.max(gh - inset * 2, 2);

  ctx.beginPath();
  if (orient === "h") {
    const halfH = Math.floor(h / 2);
    ctx.moveTo(x + halfH, y);
    ctx.lineTo(x + w - halfH, y);
    ctx.lineTo(x + w, y + halfH);
    ctx.lineTo(x + w - halfH, y + h);
    ctx.lineTo(x + halfH, y + h);
    ctx.lineTo(x, y + halfH);
  } else {
    const halfW = Math.floor(w / 2);
    ctx.moveTo(x + halfW, y);
    ctx.lineTo(x + w, y + halfW);
    ctx.lineTo(x + w, y + h - halfW);
    ctx.lineTo(x + halfW, y + h);
    ctx.lineTo(x, y + h - halfW);
    ctx.lineTo(x, y + halfW);
  }
  ctx.closePath();
  ctx.fill();
}

function renderStatTrakCanvas(canvas, digits, colorName) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const w = canvas.width || 384;
  const h = canvas.height || 94;
  const cellW = w / 6.0;

  // Background - Dark textured module glass
  ctx.fillStyle = "#0c0d10";
  ctx.fillRect(0, 0, w, h);

  const pal = STATTRAK_PALETTES[colorName] || STATTRAK_PALETTES.orange;
  const keys = ["a", "b", "c", "d", "e", "f", "g"];
  const cleanDigits = String(digits || "000000").padStart(6, "0").slice(-6);

  for (let i = 0; i < 6; i++) {
    const char = cleanDigits[i];
    const mask = STATTRAK_SEG_MAP[char] || STATTRAK_SEG_MAP["0"];
    const xOff = i * cellW;

    // Subtle cell divider
    if (i > 0) {
      ctx.strokeStyle = "rgba(0, 0, 0, 0.75)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(xOff, 0);
      ctx.lineTo(xOff, h);
      ctx.stroke();
    }

    // 1. Draw faint unlit segments
    ctx.shadowBlur = 0;
    ctx.fillStyle = pal.unlit;
    for (let s = 0; s < 7; s++) {
      if (!mask[s]) {
        const seg = STATTRAK_SEG_DEFS[keys[s]];
        drawHexSegment(ctx, xOff + seg.x, seg.y, seg.w, seg.h, seg.orient, 0);
      }
    }

    // 2. Draw lit segments with outer neon glow
    for (let s = 0; s < 7; s++) {
      if (mask[s]) {
        const seg = STATTRAK_SEG_DEFS[keys[s]];
        ctx.shadowColor = pal.glow;
        ctx.shadowBlur = 8;
        ctx.fillStyle = pal.lit;
        drawHexSegment(ctx, xOff + seg.x, seg.y, seg.w, seg.h, seg.orient, 0);

        // 3. Draw bright inner core
        ctx.shadowBlur = 0;
        ctx.fillStyle = pal.core;
        drawHexSegment(ctx, xOff + seg.x, seg.y, seg.w, seg.h, seg.orient, 2);
      }
    }
  }

  ctx.shadowBlur = 0;
}

function remapStatTrakUVs(positions, uvs) {
  const numTriangles = positions.length / 9;
  if (numTriangles !== 48) {
    return new Float32Array(uvs);
  }

  const newUvs = new Float32Array(uvs);
  const triData = [];
  for (let i = 0; i < numTriangles; i++) {
    const zAvg = (positions[i * 9 + 2] + positions[i * 9 + 5] + positions[i * 9 + 8]) / 3.0;
    triData.push({ index: i, z: zAvg });
  }

  // Sort ascending by Z (slot 0 is leftmost, slot 5 is rightmost)
  triData.sort((a, b) => a.z - b.z);

  // Each slot consists of 8 triangles
  for (let slot = 0; slot < 6; slot++) {
    const startIdx = slot * 8;
    for (let k = 0; k < 8; k++) {
      const triIdx = triData[startIdx + k].index;
      for (let v = 0; v < 3; v++) {
        const uvIdx = triIdx * 6 + v * 2;
        const oldU = uvs[uvIdx];
        newUvs[uvIdx] = (oldU + slot) / 6.0;
      }
    }
  }

  return newUvs;
}

export function updateStatTrak3D(color, number, reset = false) {
  if (!state.viewport3d.initialized) return;

  const currentColor = color || state.pro?.stattrakColor || "orange";
  const currentDigits = number !== undefined && number !== null ? String(number) : (state.pro?.stattrakDigits || "000000");

  if (state.viewport3d.statTrakCanvas && state.viewport3d.statTrakTexture) {
    renderStatTrakCanvas(state.viewport3d.statTrakCanvas, currentDigits, currentColor);
    state.viewport3d.statTrakTexture.needsUpdate = true;
    if (state.viewport3d.renderer && state.viewport3d.scene && state.viewport3d.camera) {
      state.viewport3d.renderer.render(state.viewport3d.scene, state.viewport3d.camera);
    }
  }
}

export function initViewer3DModule() {
  setupToolbarEvents();
  setupRepositionBannerEvents();

  // Listen to model updates to trigger 3D reload
  eventBus.on("model:loaded", () => {
    if (state.viewport3d.initialized) {
      load3DModelGeometry();
    }
  });

  eventBus.on("3d:requestReload", () => {
    load3DModelGeometry();
  });

  // Live color grading synchronization from Tab 3
  eventBus.on("color:textureUpdated", ({ textureIndex, canvas }) => {
    updateTextureMaterialFromCanvas(textureIndex, canvas);
  });

  // Live sticker bake synchronization from Tab 2 (WYSIWYG 3D projection)
  eventBus.on("bake:textureUpdated", ({ textureIndex, canvas }) => {
    updateTextureMaterialFromCanvas(textureIndex, canvas);
  });

  // Slot Repositioning in 3D Viewport (Solusi B)
  eventBus.on("3d:activateMoveSlot", ({ slotName, slotIndex }) => {
    enterSlotRepositionMode(slotName);
  });

  // Slot Pulse Highlight on Card Hover
  eventBus.on("slot:hover", ({ textureName, textureIndex, isHovering }) => {
    handleSlotPulseHover(textureName, textureIndex, isHovering);
  });

  // Weapon inspect animation on 'F' key
  window.addEventListener("keydown", (e) => {
    if (e.key === "f" || e.key === "F") {
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.isContentEditable)) {
        return;
      }
      triggerInspectAnimation();
    }
  });

  // Listen to live POV offset changes
  eventBus.on("3d:setPovOffsets", (offsets) => {
    setPovOffsets(offsets);
  });

  eventBus.on("3d:triggerInspect", () => {
    triggerInspectAnimation();
  });

  // Live texture staging synchronization from dynamic slots
  eventBus.on("slot:textureUpdated", ({ textureIndex, previewUri }) => {
    updateTextureMaterialFromDataUri(textureIndex, previewUri);
  });

  // Live StatTrak LED synchronization from Pro Tools
  eventBus.on("stattrak:preview", ({ color, number, reset }) => {
    updateStatTrak3D(color, number, reset);
  });
  eventBus.on("stattrak:updated", ({ color, number }) => {
    updateStatTrak3D(color, number, false);
  });
}

/**
 * Updates 3D model texture material in real-time from a Data URI across all submodels
 */
export function updateTextureMaterialFromDataUri(textureIndex, dataUri) {
  if (!state.viewport3d.initialized || !dataUri) return;

  if (typeof THREE !== "undefined") {
    const loader = new THREE.TextureLoader();
    loader.load(dataUri, (tex) => {
      tex.magFilter = THREE.LinearFilter;
      tex.minFilter = THREE.LinearFilter;
      tex.generateMipmaps = false;

      // 1. Update all submodel meshes sharing this texture index in the 3D scene
      if (state.viewport3d.meshGroup) {
        state.viewport3d.meshGroup.traverse((child) => {
          if (child.isMesh && child.userData && child.userData.textureIndex === textureIndex) {
            if (child.material) {
              if (child.material.map && typeof child.material.map.dispose === "function") {
                child.material.map.dispose();
              }
              child.material.map = tex;
              if (child.material.uniforms && child.material.uniforms.map) {
                child.material.uniforms.map.value = tex;
              }
              child.material.needsUpdate = true;
            }
          }
        });
      }

      // 2. Also update primary material cache entry
      if (state.viewport3d.materialsByTexIndex && state.viewport3d.materialsByTexIndex[textureIndex]) {
        const mat = state.viewport3d.materialsByTexIndex[textureIndex];
        if (mat.map && typeof mat.map.dispose === "function") {
          mat.map.dispose();
        }
        mat.map = tex;
        if (mat.uniforms && mat.uniforms.map) {
          mat.uniforms.map.value = tex;
        }
        mat.needsUpdate = true;
      }
    });
  }
}

/**
 * Updates 3D model texture material in real-time from a 2D grading canvas across all submodels
 */
export function updateTextureMaterialFromCanvas(textureIndex, canvas) {
  if (!state.viewport3d.initialized || !canvas) return;
  if (canvas.width <= 0 || canvas.height <= 0) return;

  if (typeof THREE !== "undefined") {
    const tex = new THREE.CanvasTexture(canvas);
    tex.magFilter = THREE.LinearFilter;
    tex.minFilter = THREE.LinearFilter;
    tex.generateMipmaps = false;

    // 1. Update all submodel meshes sharing this texture index in the 3D scene
    if (state.viewport3d.meshGroup) {
      state.viewport3d.meshGroup.traverse((child) => {
        if (child.isMesh && child.userData && child.userData.textureIndex === textureIndex) {
          if (child.material) {
            if (child.material.map && typeof child.material.map.dispose === "function") {
              child.material.map.dispose();
            }
            child.material.map = tex;
            if (child.material.uniforms && child.material.uniforms.map) {
              child.material.uniforms.map.value = tex;
            }
            child.material.needsUpdate = true;
          }
        }
      });
    }

    // 2. Also update primary material cache entry
    if (state.viewport3d.materialsByTexIndex && state.viewport3d.materialsByTexIndex[textureIndex]) {
      const mat = state.viewport3d.materialsByTexIndex[textureIndex];
      if (mat.map && typeof mat.map.dispose === "function") {
        mat.map.dispose();
      }
      mat.map = tex;
      if (mat.uniforms && mat.uniforms.map) {
        mat.uniforms.map.value = tex;
      }
      mat.needsUpdate = true;
    }
  }
}

/**
 * Explicitly triggers 3D viewport canvas resize & projection sync
 */
export function resize3DViewport() {
  const container = els.v3dCanvasContainer;
  if (!container || !state.viewport3d.renderer || !state.viewport3d.camera) return;
  const w = container.clientWidth || 800;
  const h = container.clientHeight || 580;
  if (w <= 0 || h <= 0) return;
  state.viewport3d.camera.aspect = w / h;
  state.viewport3d.camera.updateProjectionMatrix();
  state.viewport3d.renderer.setSize(w, h, false);
}



/**
 * Helper to dynamically load script tags if CDN or local bundle was delayed
 */
function loadScriptTag(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => resolve();
    s.onerror = (e) => reject(e);
    document.head.appendChild(s);
  });
}

async function ensureThreeLoaded() {
  if (typeof THREE !== "undefined" && typeof THREE.OrbitControls !== "undefined") {
    return true;
  }
  if (typeof THREE === "undefined") {
    try {
      await loadScriptTag("three.min.js");
    } catch {
      try {
        await loadScriptTag("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js");
      } catch (err) {
        console.warn("Could not load Three.js:", err);
      }
    }
  }
  if (typeof THREE !== "undefined" && typeof THREE.OrbitControls === "undefined") {
    try {
      await loadScriptTag("OrbitControls.js");
    } catch {
      try {
        await loadScriptTag("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js");
      } catch (err) {
        console.warn("Could not load OrbitControls:", err);
      }
    }
  }
  return typeof THREE !== "undefined";
}

/**
 * Initializes or refreshes the 3D viewport canvas when switching tabs
 */
export async function initOrUpdate3DViewer() {
  if (!state.viewport3d.initialized) {
    await init3DScene();
  } else {
    // Resize viewport to match container bounds
    const container = els.v3dCanvasContainer;
    if (container && state.viewport3d.camera && state.viewport3d.renderer) {
      const w = container.clientWidth || 800;
      const h = container.clientHeight || 580;
      state.viewport3d.camera.aspect = w / h;
      state.viewport3d.camera.updateProjectionMatrix();
      state.viewport3d.renderer.setSize(w, h);
    }
  }
  load3DModelGeometry();
}

/**
 * Creates the Three.js scene, camera, renderer, lighting, and controls
 */
export async function init3DScene() {
  const container = els.v3dCanvasContainer;
  if (!container) return;

  const threeReady = await ensureThreeLoaded();
  if (!threeReady || typeof THREE === "undefined") {
    console.error("Three.js library is not available.");
    if (els.v3dPlaceholder) {
      els.v3dPlaceholder.innerHTML = `
        <div style="text-align: center; padding: 24px; color: var(--accent-red);">
          <p style="font-weight: 700; font-size: 1.1rem; margin-bottom: 8px;">Three.js Engine Not Loaded</p>
          <p style="color: var(--text-muted); font-size: 0.9rem;">Please check your connection to load the Three.js library or verify local script files.</p>
        </div>
      `;
    }
    return;
  }

  const width = container.clientWidth || 800;
  const height = container.clientHeight || 580;

  // 1. Scene
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x080c14);

  // Tactical subtle grid floor for GoldSrc scale reference
  const gridHelper = new THREE.GridHelper(100, 20, 0x1e293b, 0x0f172a);
  gridHelper.position.y = -18;
  scene.add(gridHelper);

  // 2. Camera
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(0, 15, 45);

  // 3. Renderer with antialiasing, transparency & preserveDrawingBuffer for high-res snapshots
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputEncoding = THREE.sRGBEncoding;
  } catch (webglErr) {
    console.error("WebGL initialization failed:", webglErr);
    if (els.v3dPlaceholder) {
      els.v3dPlaceholder.style.display = "flex";
      els.v3dPlaceholder.innerHTML = `
        <div style="text-align: center; padding: 24px; color: var(--accent-red);">
          <p style="font-weight: 700; font-size: 1.1rem; margin-bottom: 8px;">WebGL Not Supported or Disabled</p>
          <p style="color: var(--text-muted); font-size: 0.9rem;">Could not create a WebGL context in your browser. Please ensure hardware acceleration is enabled.</p>
        </div>
      `;
    }
    return;
  }

  // Remove existing canvas if any
  const oldCanvas = container.querySelector("canvas");
  if (oldCanvas) oldCanvas.remove();
  container.appendChild(renderer.domElement);

  // 4. OrbitControls
  let controls = null;
  if (typeof THREE.OrbitControls !== "undefined") {
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 5;
    controls.maxDistance = 250;
  }

  // 5. Lighting Setup (Classic CS:GO Viewmodel Studio Lighting)
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
  scene.add(ambientLight);

  const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
  mainLight.position.set(30, 40, 50);
  scene.add(mainLight);

  const rimLight = new THREE.DirectionalLight(0x06b6d4, 0.7);
  rimLight.position.set(-30, -20, -30);
  scene.add(rimLight);

  const keyLight = new THREE.DirectionalLight(0xf59e0b, 0.5);
  keyLight.position.set(20, -10, -20);
  scene.add(keyLight);

  // 6. Mesh Group
  const meshGroup = new THREE.Group();
  scene.add(meshGroup);

  // 7. Holographic Reticle Cursor for 3D Slot Repositioning
  repositionReticleMesh = createGhostDecalCursor();
  scene.add(repositionReticleMesh);

  // 8. Dynamic FPV Bullet Trajectory Raycast & Impact Reticle
  const trajPositions = new Float32Array(6);
  const trajGeom = new THREE.BufferGeometry();
  trajGeom.setAttribute("position", new THREE.BufferAttribute(trajPositions, 3));
  const trajMat = new THREE.LineBasicMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
  });
  const trajLine = new THREE.Line(trajGeom, trajMat);
  trajLine.visible = false;
  scene.add(trajLine);
  state.viewport3d.trajectoryLine = trajLine;

  const reticleGeom = new THREE.RingGeometry(0.3, 0.45, 16);
  const reticleMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.75,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
  });
  const reticleMesh = new THREE.Mesh(reticleGeom, reticleMat);
  reticleMesh.visible = false;
  scene.add(reticleMesh);
  state.viewport3d.trajectoryHitReticle = reticleMesh;

  // Setup Raycasting and Slot Repositioning Interactions
  setupRaycastAndRepositionInteractions(renderer.domElement, camera, meshGroup);

  state.viewport3d.scene = scene;
  state.viewport3d.camera = camera;
  state.viewport3d.renderer = renderer;
  state.viewport3d.controls = controls;
  state.viewport3d.meshGroup = meshGroup;
  state.viewport3d.initialized = true;

  // Responsive resize system using native ResizeObserver to prevent canvas stretching during panel toggles & transitions
  const updateViewportSize = (explicitW, explicitH) => {
    if (!container || !state.viewport3d.renderer || !state.viewport3d.camera) return;
    const w = explicitW || container.clientWidth || 800;
    const h = explicitH || container.clientHeight || 580;
    if (w <= 0 || h <= 0) return;
    state.viewport3d.camera.aspect = w / h;
    if (state.viewport3d.currentMode === "fpv") {
      state.viewport3d.camera.fov = 68.0;
    }
    state.viewport3d.camera.updateProjectionMatrix();
    state.viewport3d.renderer.setSize(w, h, false);
  };

  if (window.ResizeObserver) {
    if (state.viewport3d.resizeObserver) {
      state.viewport3d.resizeObserver.disconnect();
    }
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        let w = 0;
        let h = 0;
        if (entry.target === container && entry.contentRect && entry.contentRect.width > 0 && entry.contentRect.height > 0) {
          w = Math.floor(entry.contentRect.width);
          h = Math.floor(entry.contentRect.height);
        } else {
          w = container.clientWidth;
          h = container.clientHeight;
        }
        if (w > 0 && h > 0) {
          updateViewportSize(w, h);
        }
      }
    });
    ro.observe(container);
    const stageArea = document.getElementById("stageViewportArea");
    if (stageArea && stageArea !== container) {
      ro.observe(stageArea);
    }
    state.viewport3d.resizeObserver = ro;
  }

  window.addEventListener("resize", () => {
    updateViewportSize();
  });

  // 60fps Animation Loop with Slot Pulse Glow
  function animate() {
    state.viewport3d.animFrameId = requestAnimationFrame(animate);
    if (controls) {
      if (state.viewport3d.autoRotate) {
        meshGroup.rotation.y += 0.008;
      }
      controls.update();
    }

    // Animation time update for sticker shaders & slot highlights
    const curTime = performance.now() * 0.001;
    if (meshGroup) {
      meshGroup.children.forEach((mesh) => {
        if (mesh.userData && mesh.userData.isSticker && mesh.material && mesh.material.uniforms) {
          if (mesh.material.uniforms.uTime) {
            mesh.material.uniforms.uTime.value = curTime;
          }
        }
      });
    }

    // Modern Slot Pulse Glow: Emissive cyan pulsing when user hovers slot card in Tab 1
    if (state.viewport3d.pulsingMesh && state.viewport3d.pulsingMesh.material) {
      const pulse = 0.5 + 0.5 * Math.sin(Date.now() * 0.009);
      const mat = state.viewport3d.pulsingMesh.material;
      if (mat.uniforms && mat.uniforms.uHighlight) {
        mat.uniforms.uHighlight.value = 1.0;
      } else if (mat.emissive) {
        mat.emissive.setHex(0x00f0ff);
        mat.emissiveIntensity = 0.35 + 0.65 * pulse;
        mat.needsUpdate = true;
      }
    }

    // Directive 6: Sequence Player playback & bone articulation (runs in both Orbit & FPV)
    if (state.viewport3d.activeSequence && state.viewport3d.isPlayingSequence) {
      const seq = state.viewport3d.activeSequence;
      if (seq && seq.bone_matrices && seq.bone_matrices.length > 0) {
        const now = performance.now();
        const dt = (now - (state.viewport3d.lastSeqTime || now)) / 1000;
        state.viewport3d.lastSeqTime = now;
        state.viewport3d.sequenceFrame = (state.viewport3d.sequenceFrame || 0) + dt * (seq.fps || 30.0);
        if (state.viewport3d.sequenceFrame >= seq.frame_count) {
          if (state.viewport3d.inspectActive) {
            state.viewport3d.inspectActive = false;
            state.viewport3d.isPlayingSequence = false;
            if (els.hudSeqPlayBtn) els.hudSeqPlayBtn.textContent = "Play";
            meshGroup.children.forEach((mesh) => {
              mesh.matrix.identity();
              mesh.matrixAutoUpdate = true;
            });
          } else {
            state.viewport3d.sequenceFrame = 0; // loop normal playback
          }
        }
        const fIdx = Math.max(0, Math.min(Math.floor(state.viewport3d.sequenceFrame), seq.frame_count - 1));
        applySequenceBoneFrame(seq, fIdx);
        if (els.hudSeqScrubber && seq.frame_count > 1) {
          els.hudSeqScrubber.value = String((fIdx / (seq.frame_count - 1)) * 100);
        }
        updateSequenceFrameDisplay(fIdx, seq.frame_count);
      }
    }

    // First-Person POV Stance Offset, Breathing Idle Sway & Weapon Inspect
    if (state.viewport3d.currentMode === "fpv") {
      const pov = state.viewport3d.povConfig || { offset_x: 0, offset_y: 0, offset_z: 0, sway: 1.0 };
      const t = Date.now() * 0.001;
      const swayScale = (pov.sway !== undefined) ? pov.sway : 1.0;
      const swayX = Math.cos(t * 0.75) * 0.02 * swayScale;
      const swayY = Math.sin(t * 1.5) * 0.05 * swayScale;

      const wep = (state.currentWeapon || "").toLowerCase();
      const isDualElites = wep.includes("elite");
      const isPistol = /usp|glock|deagle|p228|fiveseven/i.test(wep);
      const isRifle = /ak47|m4a1|galil|famas|aug|sg552/i.test(wep);

      // Default category offsets (CS2 Harmonized Standards, all pistols reference USP/Glock)
      const defaultX = isDualElites ? 0.0 : (isPistol ? 1.0 : (isRifle ? 2.2 : 1.8));
      const defaultY = isPistol ? 1.2 : (isRifle ? 1.4 : 1.3);
      const defaultZ = isPistol ? -1.2 : (isRifle ? -1.4 : -1.3);

      const effX = isDualElites ? 0.0 : (pov.offset_x !== undefined && pov.offset_x !== 0 ? pov.offset_x : defaultX);
      const effY = (pov.offset_y !== undefined && pov.offset_y !== 0) ? pov.offset_y : defaultY;
      const effZ = (pov.offset_z !== undefined && pov.offset_z !== 0) ? pov.offset_z : defaultZ;

      // Weapon inspect animation tilt curve
      let inspRotY = 0;
      let inspRotZ = 0;
      if (state.viewport3d.inspectActive) {
        const elapsed = (Date.now() - state.viewport3d.inspectStartTime) / 1000;
        const dur = 2.5;
        if (elapsed < dur) {
          const progress = elapsed / dur;
          const curve = Math.sin(progress * Math.PI);
          inspRotY = curve * 0.45;
          inspRotZ = curve * 0.35;
        } else {
          state.viewport3d.inspectActive = false;
        }
      }

      meshGroup.position.set(effX + swayX, effZ + swayY, -effY);
      meshGroup.rotation.set(0, inspRotY, inspRotZ);
    }

    // Dynamic FPV Bullet Trajectory Raycast & Tactical Crosshair
    const isFpvMode = state.viewport3d.currentMode === "fpv";
    if (els.v3dFpvCrosshair) {
      const showCross = isFpvMode && (state.viewport3d.showCrosshair !== false);
      els.v3dFpvCrosshair.classList.toggle("hidden", !showCross);
    }

    if (state.viewport3d.trajectoryLine) {
      const showTraj = isFpvMode && (state.viewport3d.showTrajectory !== false);
      state.viewport3d.trajectoryLine.visible = showTraj;
      if (state.viewport3d.trajectoryHitReticle) {
        state.viewport3d.trajectoryHitReticle.visible = showTraj;
      }

      if (showTraj) {
        const muzzlePos = new THREE.Vector3(
          meshGroup.position.x + 0.15,
          meshGroup.position.y + 0.22,
          meshGroup.position.z - 11.5
        );
        const targetPos = new THREE.Vector3(0, 0, -85.0);

        const posAttr = state.viewport3d.trajectoryLine.geometry.attributes.position;
        posAttr.setXYZ(0, muzzlePos.x, muzzlePos.y, muzzlePos.z);
        posAttr.setXYZ(1, targetPos.x, targetPos.y, targetPos.z);
        posAttr.needsUpdate = true;

        if (state.viewport3d.trajectoryHitReticle) {
          state.viewport3d.trajectoryHitReticle.position.copy(targetPos);
        }
      }
    }

renderer.render(scene, camera);
  }
  animate();
}

/**
 * Loads model geometry and materials from backend endpoint /api/model_3d
 */
export async function load3DModelGeometry(targetTripletType = null) {
  if (!state.viewport3d.initialized) return;

  if (targetTripletType) {
    state.viewport3d.tripletType = targetTripletType;
  }
  const currentTriplet = state.viewport3d.tripletType || "v";

  if (els.v3dPlaceholder) {
    els.v3dPlaceholder.style.display = "flex";
    const tLabel = currentTriplet === "p" ? "Player Model (p_*.mdl)" : currentTriplet === "w" ? "World Model (w_*.mdl)" : "Viewmodel (v_*.mdl)";
    els.v3dPlaceholder.innerHTML = `<div class="spinner"></div><p>Loading 3D ${tLabel} Geometry...</p>`;
  }

  try {
    const reqWeapon = state.currentWeapon;
    const reqTeam = state.currentTeam;
    const res = await apiGet(`/api/model_3d?team=${reqTeam}&weapon=${reqWeapon}&type=${currentTriplet}`);
    if (reqWeapon !== state.currentWeapon || reqTeam !== state.currentTeam) {
      // Discard stale response from fast-switching weapons
      return;
    }
    if (!res.success) {
      if (currentTriplet !== "v") {
        showToast(res.error || `Could not load ${currentTriplet.toUpperCase()}-Model. Switching to Viewmodel.`, "warning");
        setTripletMeshView("v");
        return;
      }
      throw new Error(res.error || "Failed to load 3D data");
    }

    const group = state.viewport3d.meshGroup;

    // Dispose old base meshes, geometries, and GPU textures to prevent memory leaks
    for (let i = group.children.length - 1; i >= 0; i--) {
      const obj = group.children[i];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (obj.material.map) obj.material.map.dispose();
        obj.material.dispose();
      }
      group.remove(obj);
    }

    if (state.viewport3d.statTrakTexture) {
      if (typeof state.viewport3d.statTrakTexture.dispose === "function") {
        state.viewport3d.statTrakTexture.dispose();
      }
      state.viewport3d.statTrakTexture = null;
    }
    state.viewport3d.statTrakCanvas = null;

    state.viewport3d.pulsingMesh = null;
    state.viewport3d.materialsByTexIndex = {};


    const hasChromeLayer = (res.meshes || []).some((m) => m.is_chrome && m.is_additive);
    if (hasChromeLayer) {
      state.viewport3d.chromeShine = true;
    }
    updateToolbarButtonStates();

    let totalVerts = 0;
    const textureLoader = new THREE.TextureLoader();
    const materialCache = {};

    // Build mesh for each submodel texture layer
    (res.meshes || []).forEach((m) => {
      if (!m.positions || m.positions.length === 0) return;

      const isHandle = /handle/i.test(m.texture_name || "") && !/glove|sport|sleeve/i.test(m.texture_name || "");
      const isGlove = !isHandle && (m.role === "glove" || /sport|glove|sleeve|arm|finger/i.test(m.texture_name || "") || (/hand/i.test(m.texture_name || "") && !/handle/i.test(m.texture_name || "")));
      const isSticker = (m.role === "sticker" || /sticker|decal/i.test(m.texture_name || "")) && !/scope/i.test(m.texture_name || "");
      const isStatDigit = Boolean(m.role === "stattrak" || /stat_digit|stattrak_digit/i.test(m.texture_name || "") || (m.texture_name && m.texture_name.toLowerCase().includes("digit") && m.texture_name.toLowerCase().includes("stat")));

      let meshUvs = m.uvs;
      if (isStatDigit && m.positions && m.positions.length === 432) {
        meshUvs = remapStatTrakUVs(m.positions, m.uvs);
      }

      const geom = new THREE.BufferGeometry();
      geom.setAttribute("position", new THREE.Float32BufferAttribute(m.positions, 3));
      geom.setAttribute("uv", new THREE.Float32BufferAttribute(meshUvs, 2));
      geom.computeVertexNormals();

      totalVerts += m.vertex_count;

      let mat = null;
      if (isStatDigit) {
        let stCanvas = state.viewport3d.statTrakCanvas;
        if (!stCanvas) {
          stCanvas = document.createElement("canvas");
          stCanvas.width = 384;
          stCanvas.height = 94;
          state.viewport3d.statTrakCanvas = stCanvas;
        }

        const currentDigits = state.pro?.stattrakDigits || (document.getElementById("stNumberInput")?.value?.trim()) || "000000";
        const currentColor = state.pro?.stattrakColor || "orange";
        renderStatTrakCanvas(stCanvas, currentDigits, currentColor);

        const stTex = new THREE.CanvasTexture(stCanvas);
        stTex.magFilter = THREE.LinearFilter;
        stTex.minFilter = THREE.LinearFilter;
        stTex.generateMipmaps = false;
        state.viewport3d.statTrakTexture = stTex;

        mat = new THREE.MeshStandardMaterial({
          map: stTex,
          roughness: 0.25,
          metalness: 0.1,
          emissiveMap: stTex,
          emissive: new THREE.Color(0xffffff),
          emissiveIntensity: 0.85,
          side: THREE.DoubleSide,
          wireframe: state.viewport3d.isWireframe,
        });
      } else {
        // Share material across all submodel meshes with identical texture layer configuration
        const matKey = `${m.texture_index}_${Boolean(m.is_chrome && m.is_additive)}_${Boolean(isSticker)}`;
        mat = materialCache[matKey];

        if (!mat) {
        // Find texture preview from active modelData
        const availableTextures = (res.textures && res.textures.length > 0) ? res.textures : (state.modelData ? state.modelData.textures : []);
        const texEntry = availableTextures.find((t) => t.index === m.texture_index || t.name === m.texture_name);
        const previewUri = texEntry ? texEntry.preview : null;

        if (previewUri) {
        const texture = textureLoader.load(previewUri);
        texture.magFilter = THREE.LinearFilter;
        // Universal LinearFilter for non-power-of-two (NPOT) GoldSrc textures
        texture.minFilter = THREE.LinearFilter;
        texture.generateMipmaps = false;

        if (m.is_chrome && m.is_additive) {
          texture.wrapS = THREE.ClampToEdgeWrapping;
          texture.wrapT = THREE.ClampToEdgeWrapping;

          mat = new THREE.ShaderMaterial({
            uniforms: {
              tChrome: { value: texture },
              uIntensity: { value: state.viewport3d.chromeShine ? 1.0 : 0.0 },
            },
            vertexShader: `
              varying vec2 vChromeUV;
              void main() {
                vec3 vNorm = normalize(normalMatrix * normal);
                // Exact GoldSrc R_StudioChrome spherical reflection mapping
                vChromeUV = vec2(vNorm.x * 0.5 + 0.5, -vNorm.y * 0.5 + 0.5);
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
              }
            `,
            fragmentShader: `
              uniform sampler2D tChrome;
              uniform float uIntensity;
              varying vec2 vChromeUV;
              void main() {
                vec4 col = texture2D(tChrome, vChromeUV);
                gl_FragColor = vec4(col.rgb * uIntensity, 1.0);
              }
            `,
            blending: THREE.AdditiveBlending,
            depthWrite: false,         // glDepthMask(GL_FALSE) in GoldSrc
            depthTest: true,
            polygonOffset: true,      // Eliminates Z-fighting on co-planar dual-layer meshes
            polygonOffsetFactor: -1.0,
            polygonOffsetUnits: -1.0,
            transparent: true,
            side: THREE.DoubleSide,
            wireframe: state.viewport3d.isWireframe,
          });
        } else if (isSticker) {
          // Item 1: Foil & Holographic shader for stickers (masked to diffuse.a > 0.5)
          // Strictly check explicit texture/staged metadata - NEVER scan raw Base64 data strings
          const stagedItem = state.pendingSlotUpdates && state.pendingSlotUpdates[m.texture_index]?.item;
          const isHolo = /holo/i.test(m.texture_name || "") || (stagedItem && /holo/i.test(stagedItem.category || stagedItem.name || ""));
          const isFoil = /foil/i.test(m.texture_name || "") || (stagedItem && /foil/i.test(stagedItem.category || stagedItem.name || ""));
          let effectType = 0; // matte default
          if (isHolo) effectType = 2; // holographic
          else if (isFoil || state.viewport3d.chromeShine) effectType = 1; // foil

          mat = new THREE.ShaderMaterial({
            uniforms: {
              map: { value: texture },
              uTime: { value: 0.0 },
              uEffectType: { value: effectType },
              uHighlight: { value: state.viewport3d.highlightStickers ? 1.0 : 0.0 },
            },
            vertexShader: `
              varying vec2 vUv;
              varying vec3 vNormal;
              varying vec3 vViewPosition;
              void main() {
                vUv = uv;
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                vViewPosition = -mvPosition.xyz;
                vNormal = normalize(normalMatrix * normal);
                gl_Position = projectionMatrix * mvPosition;
              }
            `,
            fragmentShader: `
              uniform sampler2D map;
              uniform float uTime;
              uniform int uEffectType;
              uniform float uHighlight;
              varying vec2 vUv;
              varying vec3 vNormal;
              varying vec3 vViewPosition;

              vec3 spectralRainbow(float t) {
                return vec3(
                  0.5 + 0.5 * sin(6.28318 * (t + 0.0)),
                  0.5 + 0.5 * sin(6.28318 * (t + 0.33)),
                  0.5 + 0.5 * sin(6.28318 * (t + 0.67))
                );
              }

              void main() {
                vec4 diffuse = texture2D(map, vUv);

                // Highlight Mode: Bright neon cyan outline & emissive glow
                if (uHighlight > 0.0) {
                  float pulse = 0.7 + 0.3 * sin(uTime * 4.0);
                  vec3 neonCyan = vec3(0.0, 0.9, 1.0);

                  if (diffuse.a < 0.5) {
                    // Empty slot visualization: crisp neon border + corner brackets + subtle tint
                    float edgeDistX = min(vUv.x, 1.0 - vUv.x);
                    float edgeDistY = min(vUv.y, 1.0 - vUv.y);
                    float minEdge = min(edgeDistX, edgeDistY);

                    // Outer neon border
                    if (minEdge < 0.045) {
                      gl_FragColor = vec4(neonCyan * 1.6, 0.9 * pulse);
                      return;
                    }
                    // Corner bracket accents
                    if ((vUv.x < 0.16 || vUv.x > 0.84) && (vUv.y < 0.16 || vUv.y > 0.84) && minEdge < 0.09) {
                      gl_FragColor = vec4(neonCyan * 1.8, 0.95 * pulse);
                      return;
                    }
                    // Translucent inner quad fill so user locates empty slots effortlessly
                    gl_FragColor = vec4(neonCyan * 0.15, 0.22 * pulse);
                    return;
                  }

                  // Pop existing sticker with glowing cyan rim accent
                  vec3 norm = normalize(vNormal);
                  vec3 viewDir = normalize(vViewPosition);
                  float NdotV = clamp(dot(norm, viewDir), 0.0, 1.0);
                  float rim = pow(1.0 - NdotV, 2.0);

                  vec3 col = diffuse.rgb;
                  col = mix(col, neonCyan, 0.25 * pulse);
                  col += neonCyan * (rim * 0.8 + 0.35) * pulse;
                  gl_FragColor = vec4(col, diffuse.a);
                  return;
                }

                // Normal Mode (Highlight OFF)
                if (diffuse.a < 0.5) {
                  discard;
                }

                vec3 norm = normalize(vNormal);
                vec3 viewDir = normalize(vViewPosition);
                float NdotV = clamp(dot(norm, viewDir), 0.0, 1.0);
                float fresnel = pow(1.0 - NdotV, 2.5);

                vec3 col = diffuse.rgb;

                if (uEffectType == 1) {
                  // Foil: metallic specular reflection highlight
                  vec3 lightDir = normalize(vec3(0.5, 0.8, 0.7));
                  vec3 halfVec = normalize(lightDir + viewDir);
                  float spec = pow(max(dot(norm, halfVec), 0.0), 32.0);
                  vec3 foilShine = vec3(1.0, 0.95, 0.8) * spec * 1.5;
                  col += foilShine;
                } else if (uEffectType == 2) {
                  // Holographic: dynamic view-angle Fresnel spectral rainbow iridescence
                  float spectralShift = (1.0 - NdotV) * 2.0 + uTime * 0.15 + (vUv.x + vUv.y) * 0.5;
                  vec3 rainbowCol = spectralRainbow(spectralShift);
                  col = mix(col, col * rainbowCol * 1.8 + rainbowCol * 0.4, fresnel * 0.85);
                }

                gl_FragColor = vec4(col, diffuse.a);
              }
            `,
            transparent: true,
            depthWrite: true,
            depthTest: true,
            polygonOffset: true,
            polygonOffsetFactor: -1.0,
            polygonOffsetUnits: -1.0,
            side: THREE.DoubleSide,
            wireframe: state.viewport3d.isWireframe,
          });
          mat.map = texture;
        } else {
          const isChromeActive = Boolean(m.is_chrome || state.viewport3d.chromeShine);
          mat = new THREE.MeshStandardMaterial({
            map: texture,
            transparent: m.is_masked,
            alphaTest: m.is_masked ? 0.5 : 0.0,
            roughness: isChromeActive ? 0.08 : 0.45,
            metalness: isChromeActive ? 0.92 : 0.15,
            side: THREE.DoubleSide,
            wireframe: state.viewport3d.isWireframe,
          });
        }
      } else {
        mat = new THREE.MeshStandardMaterial({
          color: 0x94a3b8,
          wireframe: state.viewport3d.isWireframe,
        });
      }

      materialCache[matKey] = mat;
    }
    }

    state.viewport3d.materialsByTexIndex[m.texture_index] = mat;

    const mesh = new THREE.Mesh(geom, mat);
      if (m.is_chrome && m.is_additive) {
        mesh.renderOrder = 10;
      }
      mesh.userData = {
        textureIndex: m.texture_index,
        textureName: m.texture_name,
        role: m.role || (isStatDigit ? "stattrak" : isGlove ? "glove" : isSticker ? "sticker" : "skin"),
        slotIdentifier: m.slot_identifier,
        boneId: m.bone_id,
        isGlove: isGlove,
        isSticker: isSticker,
        isStatDigit: isStatDigit,
        isMasked: Boolean(m.is_masked),
        originalEmissive: mat.emissive ? mat.emissive.getHex() : 0x000000,
      };
      group.add(mesh);
    });

    // Update real-time GoldSrc polygon triangle budget telemetry
    const trisBadge = document.getElementById("trisCountBadge");
    const totalTris = Math.floor(totalVerts / 3);
    // trisBadge declared above
    const trisVal = document.getElementById("trisCountVal");
    // trisBadge declared above
    // trisVal reused from line 1165
    if (trisVal) {
      trisVal.textContent = `${totalTris.toLocaleString()} TRIS`;
    }
    if (trisBadge) {
      trisBadge.title = `Total Model Polygons: ${totalTris.toLocaleString()} tris (GoldSrc budget: 2,048 tris)`;
      trisBadge.classList.toggle("budget-warning", totalTris > 2048);
    }

    // Update last loaded weapon and team to decide whether to re-center & reset camera
    const isSameWeapon = (state.viewport3d.lastLoadedWeapon === reqWeapon && state.viewport3d.lastLoadedTeam === reqTeam);
    state.viewport3d.lastLoadedWeapon = reqWeapon;
    state.viewport3d.lastLoadedTeam = reqTeam;

    state.viewport3d.currentBounds = res.bounds;
    state.viewport3d.currentWeaponBounds = res.weapon_bounds || res.bounds;

    const wb = res.weapon_bounds || res.bounds;
    if (wb && wb.center) {
      const c = wb.center;
      group.position.set(-c[0], -c[1], -c[2]);

      // Focus camera proportional to weapon dimensions
      if ((!isSameWeapon || state.viewport3d.tripletChanged) && state.viewport3d.currentMode === "orbit") {
        state.viewport3d.tripletChanged = false;
        const r = wb.radius || 20;
        state.viewport3d.camera.position.set(r * 1.15, r * 0.65, r * 1.85);
        if (state.viewport3d.controls) {
          state.viewport3d.controls.target.set(0, 0, 0);
          state.viewport3d.controls.update();
        }
      }
    }

    // Apply visibility and highlight states immediately
    applyMeshVisibility();
    applyStickerHighlight();

    const totalTriangles = res.total_triangles || Math.round(totalVerts / 3);
    if (els.v3dStats) {
      els.v3dStats.textContent = `Meshes: ${res.mesh_count} • Vertices: ${totalVerts} • Triangles: ${totalTriangles}`;
    }

    // trisVal reused from line 1165
    // trisBadge declared above
    if (trisVal) {
      trisVal.textContent = `${totalTriangles.toLocaleString()} Tris`;
      if (trisBadge) {
        if (totalTriangles > 2048) {
          trisBadge.classList.add("stat-warn");
          trisBadge.title = `High-Poly Mesh: ${totalTriangles.toLocaleString()} triangles (GoldSrc budget: 2,048 recommended)`;
        } else {
          trisBadge.classList.remove("stat-warn");
          trisBadge.title = `GoldSrc Standard: ${totalTriangles.toLocaleString()} triangles (Optimal budget)`;
        }
      }
    }
    if (els.v3dPlaceholder) {
      els.v3dPlaceholder.style.display = "none";
    }
  } catch (err) {
    console.error("3D Load Error:", err);
    if (els.v3dPlaceholder) {
      els.v3dPlaceholder.style.display = "flex";
      els.v3dPlaceholder.innerHTML = `<span style="color: var(--accent-red); padding: 20px; text-align: center;">3D Viewport Notice: ${err.message}</span>`;
    }
  }
}

export function setTripletMeshView(tripletType) {
  state.viewport3d.tripletType = tripletType;
  ["v", "p", "w"].forEach((t) => {
    const btn = document.getElementById(`tripletBtn${t.toUpperCase()}`);
    if (btn) {
      if (t === tripletType) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  });
  state.viewport3d.tripletChanged = true;
  load3DModelGeometry(tripletType);
  eventBus.emit("triplet:changed", {
    type: tripletType,
    weapon: state.currentWeapon,
    team: state.currentTeam,
  });
}

function setupToolbarEvents() {
  // Stage Triplet Switcher (V-Model / P-Model / W-Model)
  ["v", "p", "w"].forEach((type) => {
    const btn = document.getElementById(`tripletBtn${type.toUpperCase()}`);
    btn?.addEventListener("click", () => {
      setTripletMeshView(type);
    });
  });

  if (els.v3dWeaponOnlyBtn) {
    els.v3dWeaponOnlyBtn.addEventListener("click", () => {
      toggleWeaponOnly();
    });
  }

  if (els.v3dGlovesBtn) {
    els.v3dGlovesBtn.addEventListener("click", () => {
      toggleGloves();
    });
  }

  if (els.v3dHighlightStickersBtn) {
    els.v3dHighlightStickersBtn.addEventListener("click", () => {
      toggleHighlightStickers();
    });
  }

  if (els.v3dFocusWeaponBtn) {
    els.v3dFocusWeaponBtn.addEventListener("click", () => {
      focusCameraToWeapon();
    });
  }

  if (els.v3dResetCamBtn) {
    els.v3dResetCamBtn.addEventListener("click", () => {
      resetCameraView();
    });
  }

  // QoL 4: First-Person Player Eye View Simulation
  if (els.v3dFpvBtn) {
    els.v3dFpvBtn.addEventListener("click", () => {
      setFirstPersonView();
    });
  }

  // QoL 4: 360° Showcase Presentation Orbit
  if (els.v3dShowcaseBtn) {
    els.v3dShowcaseBtn.addEventListener("click", () => {
      toggleShowcaseMode();
    });
  }

  if (els.v3dAutoRotateBtn) {
    els.v3dAutoRotateBtn.addEventListener("click", () => {
      state.viewport3d.autoRotate = !state.viewport3d.autoRotate;
      updateToolbarButtonStates();
    });
  }

  if (els.v3dWireframeBtn) {
    els.v3dWireframeBtn.addEventListener("click", () => {
      state.viewport3d.isWireframe = !state.viewport3d.isWireframe;
      els.v3dWireframeBtn.classList.toggle("btn-primary", state.viewport3d.isWireframe);
      els.v3dWireframeBtn.classList.toggle("active", state.viewport3d.isWireframe);
      Object.values(state.viewport3d.materialsByTexIndex).forEach((mat) => {
        mat.wireframe = state.viewport3d.isWireframe;
      });
    });
  }

  if (els.v3dChromeShineBtn) {
    els.v3dChromeShineBtn.addEventListener("click", () => {
      state.viewport3d.chromeShine = !state.viewport3d.chromeShine;
      updateToolbarButtonStates();
      Object.values(state.viewport3d.materialsByTexIndex).forEach((mat) => {
        if (mat instanceof THREE.ShaderMaterial && mat.uniforms) {
          if (mat.uniforms.uIntensity) {
            mat.uniforms.uIntensity.value = state.viewport3d.chromeShine ? 1.0 : 0.0;
          }
          if (mat.uniforms.uEffectType && mat.uniforms.uEffectType.value !== 2) {
            mat.uniforms.uEffectType.value = state.viewport3d.chromeShine ? 1 : 0;
          }
        } else if (mat.roughness !== undefined && mat.metalness !== undefined) {
          mat.roughness = state.viewport3d.chromeShine ? 0.08 : 0.45;
          mat.metalness = state.viewport3d.chromeShine ? 0.92 : 0.15;
        }
      });

      // Solusi 3: Synchronize 3D virtual decals with Chrome Shine toggle
      if (state.viewport3d.bakedDecalsGroup) {
        state.viewport3d.bakedDecalsGroup.children.forEach((decal) => {
          if (decal.material) {
            const decalFx = decal.userData?.fx || "matte";
            const isChrome = decalFx === "chrome" || decalFx === "foil" || state.viewport3d.chromeShine;
            if (isChrome) {
              decal.material.roughness = 0.08;
              decal.material.metalness = 0.92;
            } else if (decalFx === "matte") {
              decal.material.roughness = 0.35;
              decal.material.metalness = 0.15;
            } else if (decalFx === "glow") {
              decal.material.roughness = 0.35;
              decal.material.metalness = 0.15;
              if (decal.material.emissive) {
                decal.material.emissive.setHex(0x00f0ff);
                decal.material.emissiveIntensity = 0.8;
              }
            }
            decal.material.needsUpdate = true;
          }
        });
      }
    });
  }

  if (els.v3dReloadBtn) {
    els.v3dReloadBtn.addEventListener("click", () => {
      load3DModelGeometry();
      showToast("3D Model Geometry hot-reloaded.", "info");
    });
  }

  if (els.v3dSnapshotBtn) {
    els.v3dSnapshotBtn.addEventListener("click", (e) => {
      takeHighResSnapshot({ transparent: !e.shiftKey });
    });
  }

  if (els.v3dSoundPreviewBtn) {
    els.v3dSoundPreviewBtn.addEventListener("click", () => {
      const wep = state.currentWeapon;
      if (!wep) {
        showToast("No active weapon selected.", "warning");
        return;
      }
      const audioUrl = `/api/amxx/sound?weapon=${encodeURIComponent(wep)}`;
      const audio = new Audio(audioUrl);
      audio.play().then(() => {
        showToast(`Playing sound preview for ${wep.toUpperCase()}`, "info");
      }).catch((err) => {
        console.warn("Audio preview failed or not found:", err);
        showToast(`No audio preview found for ${wep.toUpperCase()}`, "warning");
      });
    });
  }

  if (els.v3dPovSettingsBtn) {
    els.v3dPovSettingsBtn.addEventListener("click", () => {
      togglePovDrawer();
    });
  }

  if (els.v3dInspectBtn) {
    els.v3dInspectBtn.addEventListener("click", () => {
      triggerInspectAnimation();
    });
  }

  if (els.v3dPovDrawerCloseBtn) {
    els.v3dPovDrawerCloseBtn.addEventListener("click", () => {
      closePovDrawer();
    });
  }

  // HUD Collapse Toggle and 'H' Keyboard Shortcut
  const hudCollapseBtn = document.getElementById("hudCollapseToggleBtn");
  const floatingHud = document.getElementById("floatingHudCapsule");
  if (hudCollapseBtn && floatingHud) {
    hudCollapseBtn.addEventListener("click", () => {
      floatingHud.classList.toggle("collapsed");
      const isCol = floatingHud.classList.contains("collapsed");
      const label = hudCollapseBtn.querySelector(".hud-toggle-label");
      if (label) label.textContent = isCol ? "Show HUD" : "Hide HUD";
    });
  }

  window.addEventListener("keydown", (e) => {
    if (e.key === "h" || e.key === "H") {
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.isContentEditable)) {
        return;
      }
      if (hudCollapseBtn) hudCollapseBtn.click();
    }
  });

  // Sequence Player HUD Controls (Directive 6)
  if (els.hudSeqSelect) {
    els.hudSeqSelect.addEventListener("change", async () => {
      const idx = parseInt(els.hudSeqSelect.value, 10);
      if (state.viewport3d.sequences && state.viewport3d.sequences[idx]) {
        const targetSeq = state.viewport3d.sequences[idx];
        if (!targetSeq.bone_matrices || targetSeq.bone_matrices.length === 0) {
          try {
            const res = await apiGet(`/api/model_sequence?weapon=${encodeURIComponent(state.currentWeapon)}&team=${encodeURIComponent(state.currentTeam)}&sequence=${targetSeq.index}`);
            if (res && res.success && res.bone_matrices) {
              targetSeq.bone_matrices = res.bone_matrices;
              targetSeq.fps = res.fps || targetSeq.fps;
              targetSeq.frame_count = res.frame_count || targetSeq.frame_count;
            }
          } catch (err) {
            console.warn("Could not fetch sequence bone matrices:", err);
          }
        }
        state.viewport3d.activeSequence = targetSeq;
        state.viewport3d.sequenceFrame = 0;
        state.viewport3d.isPlayingSequence = true;
        state.viewport3d.lastSeqTime = performance.now();
        if (els.hudSeqPlayBtn) els.hudSeqPlayBtn.textContent = "Pause";
        updateSequenceFrameDisplay(0, state.viewport3d.activeSequence.frame_count);
      }
    });
  }

  if (els.hudSeqPlayBtn) {
    els.hudSeqPlayBtn.addEventListener("click", () => {
      state.viewport3d.isPlayingSequence = !state.viewport3d.isPlayingSequence;
      state.viewport3d.lastSeqTime = performance.now();
      els.hudSeqPlayBtn.textContent = state.viewport3d.isPlayingSequence ? "Pause" : "Play";
    });
  }

  if (els.hudSeqScrubber) {
    els.hudSeqScrubber.addEventListener("input", () => {
      state.viewport3d.isPlayingSequence = false;
      if (els.hudSeqPlayBtn) els.hudSeqPlayBtn.textContent = "Play";
      const seq = state.viewport3d.activeSequence;
      if (seq && seq.frame_count > 0) {
        const pct = parseFloat(els.hudSeqScrubber.value) / 100.0;
        const targetFrame = Math.round(pct * (seq.frame_count - 1));
        state.viewport3d.sequenceFrame = targetFrame;
        applySequenceBoneFrame(seq, targetFrame);
        updateSequenceFrameDisplay(targetFrame, seq.frame_count);
      }
    });
  }
}

export function updateSequenceFrameDisplay(currentFrame, totalFrames) {
  if (els.hudSeqFrameDisplay) {
    els.hudSeqFrameDisplay.textContent = `${currentFrame + 1}/${totalFrames}`;
  }
}

export function applySequenceBoneFrame(seq, frameIdx) {
  if (!seq || !seq.bone_matrices || seq.bone_matrices.length === 0) return;
  const group = state.viewport3d.meshGroup;
  if (!group) return;
  const clampedIdx = Math.max(0, Math.min(frameIdx, seq.bone_matrices.length - 1));
  const frameBones = seq.bone_matrices[clampedIdx];
  if (!frameBones) return;

  group.children.forEach((mesh) => {
    const bId = mesh.userData?.boneId ?? 0;
    if (frameBones[bId]) {
      mesh.matrixAutoUpdate = false;
      mesh.matrix.fromArray(frameBones[bId]);
    }
  });
}

/**
 * Toggles weapon-only inspection mode (hides hands and sleeves)
 */
function toggleWeaponOnly() {
  state.viewport3d.weaponOnly = !state.viewport3d.weaponOnly;
  state.viewport3d.showGloves = !state.viewport3d.weaponOnly;

  applyMeshVisibility();
  if (state.viewport3d.weaponOnly) {
    if (state.viewport3d.currentMode === "orbit") {
      focusCameraToWeapon();
    }
  }
  showToast(state.viewport3d.weaponOnly ? "Weapon Only mode active (gloves/arms hidden)." : "Gloves & arms visible.", "info");
}

/**
 * Toggles gloves and sleeves visibility
 */
function toggleGloves() {
  state.viewport3d.showGloves = !state.viewport3d.showGloves;
  state.viewport3d.weaponOnly = !state.viewport3d.showGloves;

  applyMeshVisibility();
  if (!state.viewport3d.showGloves) {
    if (state.viewport3d.currentMode === "orbit") {
      focusCameraToWeapon();
    }
  }
  showToast(state.viewport3d.showGloves ? "Gloves & arms visible." : "Gloves & arms hidden.", "info");
}

/**
 * Toggles highlight on sticker meshes
 */
function toggleHighlightStickers() {
  state.viewport3d.highlightStickers = !state.viewport3d.highlightStickers;
  applyStickerHighlight();
  showToast(state.viewport3d.highlightStickers ? "Sticker slots highlighted with neon accent." : "Sticker highlight disabled.", "info");
}

/**
 * Applies mesh visibility according to state.viewport3d.showGloves
 */
function applyMeshVisibility() {
  const group = state.viewport3d.meshGroup;
  if (!group) return;

  const showGloves = state.viewport3d.showGloves !== false;
  group.children.forEach((mesh) => {
    if (mesh.userData && mesh.userData.isGlove) {
      mesh.visible = showGloves;
    }
  });

  updateToolbarButtonStates();
}

/**
 * Highlights sticker slots and decals with accent color
 */
function applyStickerHighlight() {
  const group = state.viewport3d.meshGroup;
  const highlightVal = state.viewport3d.highlightStickers ? 1.0 : 0.0;

  if (group) {
    group.children.forEach((mesh) => {
      if (mesh.userData && mesh.userData.isSticker && mesh.material) {
        if (mesh.material.uniforms && mesh.material.uniforms.uHighlight) {
          mesh.material.uniforms.uHighlight.value = highlightVal;
        } else if (mesh.material.emissive) {
          mesh.material.emissive.setHex(highlightVal > 0 ? 0x00e5ff : (mesh.userData.originalEmissive || 0x000000));
          mesh.material.emissiveIntensity = highlightVal > 0 ? 0.85 : 0.0;
        }
      }
    });
  }

  // Also highlight virtual baked decals group
  if (state.viewport3d.bakedDecalsGroup) {
    state.viewport3d.bakedDecalsGroup.children.forEach((decal) => {
      if (decal.material && decal.material.emissive) {
        decal.material.emissive.setHex(highlightVal > 0 ? 0x00e5ff : 0x000000);
        decal.material.emissiveIntensity = highlightVal > 0 ? 0.85 : 0.0;
      }
    });
  }

  updateToolbarButtonStates();
}

/**
 * Focus camera directly on weapon mesh bounds
 */
function focusCameraToWeapon() {
  if (!state.viewport3d.camera || !state.viewport3d.controls) return;
  state.viewport3d.currentMode = "orbit";
  state.viewport3d.controls.enabled = true;
  const wb = state.viewport3d.currentWeaponBounds || state.viewport3d.currentBounds;
  const r = (wb && wb.radius) ? wb.radius : 20;

  state.viewport3d.controls.target.set(0, 0, 0);
  state.viewport3d.camera.position.set(r * 1.15, r * 0.65, r * 1.85);
  state.viewport3d.controls.update();

  if (state.viewport3d.meshGroup) {
    state.viewport3d.meshGroup.rotation.set(0, 0, 0);
  }
  state.viewport3d.autoRotate = false;
  if (els.v3dAutoRotateBtn) {
    els.v3dAutoRotateBtn.innerHTML = '<svg class="glyph glyph-xs"><use href="#glyph-rotate"></use></svg> Auto-Rotate: OFF';
    els.v3dAutoRotateBtn.classList.remove("btn-primary");
  }
  if (els.v3dFpvBtn) els.v3dFpvBtn.classList.remove("btn-primary");
  if (els.v3dShowcaseBtn) els.v3dShowcaseBtn.classList.remove("btn-primary");
  showToast("Camera focused on weapon mesh.", "info");
}

/**
 * Synchronizes UI button styling with current state
 */
function updateToolbarButtonStates() {
  if (els.v3dWeaponOnlyBtn) {
    const isWpnOnly = Boolean(state.viewport3d.weaponOnly);
    els.v3dWeaponOnlyBtn.classList.toggle("btn-primary", isWpnOnly);
    els.v3dWeaponOnlyBtn.classList.toggle("active", isWpnOnly);
    els.v3dWeaponOnlyBtn.title = isWpnOnly ? "Weapon Only: ON (gloves hidden)" : "Weapon Only: OFF (click to hide gloves)";
    if (!els.v3dWeaponOnlyBtn.classList.contains("icon-only")) {
      els.v3dWeaponOnlyBtn.innerHTML = isWpnOnly ? '<svg class="glyph glyph-xs"><use href="#glyph-weapon"></use></svg> Weapon Only: ON' : '<svg class="glyph glyph-xs"><use href="#glyph-weapon"></use></svg> Weapon Only';
    }
  }
  if (els.v3dGlovesBtn) {
    const showGloves = state.viewport3d.showGloves !== false;
    els.v3dGlovesBtn.classList.toggle("btn-primary", showGloves);
    els.v3dGlovesBtn.classList.toggle("active", showGloves);
    els.v3dGlovesBtn.title = showGloves ? "Gloves & Sleeves: ON" : "Gloves & Sleeves: OFF";
    if (!els.v3dGlovesBtn.classList.contains("icon-only")) {
      els.v3dGlovesBtn.innerHTML = showGloves ? '<svg class="glyph glyph-xs"><use href="#glyph-glove"></use></svg> Gloves: ON' : '<svg class="glyph glyph-xs"><use href="#glyph-glove"></use></svg> Gloves: OFF';
    }
  }
  if (els.v3dHighlightStickersBtn) {
    const isHighlight = Boolean(state.viewport3d.highlightStickers);
    els.v3dHighlightStickersBtn.classList.toggle("btn-primary", isHighlight);
    els.v3dHighlightStickersBtn.classList.toggle("active", isHighlight);
    els.v3dHighlightStickersBtn.title = isHighlight ? "Sticker Highlight: ON" : "Highlight Sticker Slots";
    if (!els.v3dHighlightStickersBtn.classList.contains("icon-only")) {
      els.v3dHighlightStickersBtn.innerHTML = isHighlight ? '<svg class="glyph glyph-xs"><use href="#glyph-target"></use></svg> Highlight: ON' : '<svg class="glyph glyph-xs"><use href="#glyph-target"></use></svg> Highlight Stickers';
    }
  }
  if (els.v3dChromeShineBtn) {
    const isChrome = Boolean(state.viewport3d.chromeShine);
    els.v3dChromeShineBtn.classList.toggle("btn-primary", isChrome);
    els.v3dChromeShineBtn.classList.toggle("active", isChrome);
    els.v3dChromeShineBtn.title = isChrome ? "Metallic Chrome Shine: ON" : "Toggle Metallic Chrome Reflection";
    if (!els.v3dChromeShineBtn.classList.contains("icon-only")) {
      els.v3dChromeShineBtn.innerHTML = `<svg class="glyph glyph-xs"><use href="#glyph-sparkle"></use></svg> <span>Chrome Shine: ${isChrome ? 'ON' : 'OFF'}</span>`;
    }
  }
  if (els.v3dAutoRotateBtn) {
    const isRot = Boolean(state.viewport3d.autoRotate);
    els.v3dAutoRotateBtn.classList.toggle("btn-primary", isRot);
    els.v3dAutoRotateBtn.classList.toggle("active", isRot);
    els.v3dAutoRotateBtn.title = isRot ? "Auto-Rotate Orbit: ON" : "Toggle Auto-Rotate Orbit";
    if (!els.v3dAutoRotateBtn.classList.contains("icon-only")) {
      els.v3dAutoRotateBtn.innerHTML = `<svg class="glyph glyph-xs"><use href="#glyph-rotate"></use></svg> Auto-Rotate: ${isRot ? 'ON' : 'OFF'}`;
    }
  }
}

function resetCameraView() {
  if (!state.viewport3d.camera) return;
  state.viewport3d.currentMode = "orbit";
  if (els.v3dFpvCrosshair) els.v3dFpvCrosshair.classList.add("hidden");
  if (state.viewport3d.trajectoryLine) state.viewport3d.trajectoryLine.visible = false;
  if (state.viewport3d.trajectoryHitReticle) state.viewport3d.trajectoryHitReticle.visible = false;
  if (state.viewport3d.controls) {
    state.viewport3d.controls.enabled = true;
  }
  state.viewport3d.camera.fov = 45;
  state.viewport3d.camera.updateProjectionMatrix();

  const wb = state.viewport3d.currentWeaponBounds || state.viewport3d.currentBounds;
  const r = (wb && wb.radius) ? wb.radius : 20;
  state.viewport3d.camera.position.set(r * 1.15, r * 0.65, r * 1.85);
  if (state.viewport3d.controls) {
    state.viewport3d.controls.target.set(0, 0, 0);
    state.viewport3d.controls.update();
  }
  if (state.viewport3d.meshGroup) {
    if (wb && wb.center) {
      const c = wb.center;
      state.viewport3d.meshGroup.position.set(-c[0], -c[1], -c[2]);
    } else {
      state.viewport3d.meshGroup.position.set(0, 0, 0);
    }
    state.viewport3d.meshGroup.rotation.set(0, 0, 0);
  }
  state.viewport3d.autoRotate = false;
  if (els.v3dAutoRotateBtn) {
    els.v3dAutoRotateBtn.classList.remove("btn-primary");
    els.v3dAutoRotateBtn.classList.remove("active");
    els.v3dAutoRotateBtn.title = "Toggle automatic turntable rotation";
    if (!els.v3dAutoRotateBtn.classList.contains("icon-only")) {
      els.v3dAutoRotateBtn.innerHTML = '<svg class="glyph glyph-xs"><use href="#glyph-rotate"></use></svg> Auto-Rotate: OFF';
    }
  }
  if (els.v3dFpvBtn) els.v3dFpvBtn.classList.remove("btn-primary");
  if (els.v3dShowcaseBtn) els.v3dShowcaseBtn.classList.remove("btn-primary");
  showToast("Camera view reset to weapon orbit.", "info");
}

export function setFirstPersonView() {
  if (!state.viewport3d.camera || !state.viewport3d.controls) return;
  state.viewport3d.currentMode = "fpv";
  state.viewport3d.controls.enabled = false;

  // Auto-restore gloves & sleeves in First-Person POV view
  if (state.viewport3d.weaponOnly) {
    state.viewport3d.weaponOnly = false;
    state.viewport3d.showGloves = true;
    applyMeshVisibility();
    updateToolbarButtonStates();
  }

  // CS2 locked viewmodel vertical FOV standard (68.0 deg)
  state.viewport3d.camera.fov = 68.0;
  state.viewport3d.camera.position.set(0, 0, 0);
  state.viewport3d.camera.updateProjectionMatrix();

  state.viewport3d.controls.target.set(0, 0, -100);
  state.viewport3d.controls.update();

  state.viewport3d.autoRotate = false;
  if (els.v3dAutoRotateBtn) {
    els.v3dAutoRotateBtn.innerHTML = '<svg class="glyph glyph-xs"><use href="#glyph-rotate"></use></svg> Auto-Rotate: OFF';
    els.v3dAutoRotateBtn.classList.remove("btn-primary");
  }
  if (els.v3dFpvBtn) els.v3dFpvBtn.classList.add("btn-primary");
  if (els.v3dShowcaseBtn) els.v3dShowcaseBtn.classList.remove("btn-primary");

  showToast("Switched to True First-Person Eye View (FPV, CS2 68 deg Vertical FOV).", "info");
}

export async function triggerInspectAnimation() {
  state.viewport3d.inspectActive = true;
  state.viewport3d.inspectStartTime = performance.now();
  let seq = state.viewport3d.inspectSequence;
  if (!seq && state.viewport3d.sequences) {
    seq = state.viewport3d.sequences.find((s) => s.label && s.label.includes("inspect"));
  }
  if (seq && (!seq.bone_matrices || seq.bone_matrices.length === 0)) {
    try {
      const res = await apiGet(`/api/model_sequence?weapon=${encodeURIComponent(state.currentWeapon)}&team=${encodeURIComponent(state.currentTeam)}&sequence=${seq.index}`);
      if (res && res.success && res.bone_matrices) {
        seq.bone_matrices = res.bone_matrices;
        seq.fps = res.fps || seq.fps;
        seq.frame_count = res.frame_count || seq.frame_count;
        state.viewport3d.inspectSequence = seq;
      }
    } catch (err) {
      console.warn("Could not fetch inspect sequence bone matrices:", err);
    }
  }
  if (seq && seq.bone_matrices && seq.bone_matrices.length > 0) {
    state.viewport3d.activeSequence = seq;
    state.viewport3d.isPlayingSequence = true;
    state.viewport3d.sequenceFrame = 0;
    state.viewport3d.lastSeqTime = performance.now();
    if (els.hudSeqPlayBtn) els.hudSeqPlayBtn.textContent = "Pause";
    if (els.hudSeqSelect && state.viewport3d.sequences) {
      const sIdx = state.viewport3d.sequences.findIndex((s) => s.index === seq.index);
      if (sIdx >= 0) els.hudSeqSelect.value = String(sIdx);
    }
  }
  const label = seq && seq.label ? ` (${seq.label})` : "";
  showToast(`Inspecting weapon${label}...`, "info");
}

export function setPovOffsets(offsets) {
  state.viewport3d.povConfig = { ...(state.viewport3d.povConfig || {}), ...offsets };
}

function togglePovDrawer() {
  if (!els.v3dPovDrawer) return;
  const isHidden = els.v3dPovDrawer.classList.toggle("hidden");
  if (!isHidden && state.viewport3d.currentMode !== "fpv") {
    setFirstPersonView();
  }
}

function closePovDrawer() {
  if (els.v3dPovDrawer) {
    els.v3dPovDrawer.classList.add("hidden");
  }
}

function toggleShowcaseMode() {
  if (!state.viewport3d.camera || !state.viewport3d.controls) return;

  if (state.viewport3d.currentMode === "showcase" && state.viewport3d.autoRotate) {
    resetCameraView();
    return;
  }

  state.viewport3d.currentMode = "showcase";
  if (els.v3dFpvCrosshair) els.v3dFpvCrosshair.classList.add("hidden");
  if (state.viewport3d.trajectoryLine) state.viewport3d.trajectoryLine.visible = false;
  if (state.viewport3d.trajectoryHitReticle) state.viewport3d.trajectoryHitReticle.visible = false;

  // Optimal 3/4 showcase presentation angle based on weapon bounds
  const wb = state.viewport3d.currentWeaponBounds || state.viewport3d.currentBounds;
  const r = (wb && wb.radius) ? wb.radius : 20;
  state.viewport3d.camera.position.set(r * 1.1, r * 0.7, r * 1.9);
  state.viewport3d.controls.target.set(0, 0, 0);
  state.viewport3d.controls.update();

  state.viewport3d.autoRotate = true;
  if (els.v3dAutoRotateBtn) {
    els.v3dAutoRotateBtn.innerHTML = '<svg class="glyph glyph-xs"><use href="#glyph-rotate"></use></svg> Auto-Rotate: ON';
    els.v3dAutoRotateBtn.classList.add("btn-primary");
  }
  if (els.v3dShowcaseBtn) els.v3dShowcaseBtn.classList.add("btn-primary");
  if (els.v3dFpvBtn) els.v3dFpvBtn.classList.remove("btn-primary");

  showToast("Showcase Orbit Mode activated (360° Presentation).", "info");
}

/**
 * Creates the holographic ghost decal targeting cursor in Three.js
 */
function createGhostDecalCursor() {
  const group = new THREE.Group();

  // 1. Center plane for sticker projection
  const planeGeom = new THREE.PlaneGeometry(1, 1);
  const planeMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    transparent: true,
    opacity: 0.85,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const planeMesh = new THREE.Mesh(planeGeom, planeMat);
  planeMesh.name = "ghostPlane";
  group.add(planeMesh);

  // 2. Outer holographic reticle ring
  const ringGeom = new THREE.RingGeometry(0.48, 0.52, 40);
  const ringMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    transparent: true,
    opacity: 0.9,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const ringMesh = new THREE.Mesh(ringGeom, ringMat);
  ringMesh.position.z = 0.002;
  group.add(ringMesh);

  group.visible = false;
  return group;
}

/**
 * Sets up pointer raycasting and click detection for in-place 3D Slot Repositioning
 * and interactive 3D Surface Sticker Dragging (Bake Mode)
 */
function setupRaycastAndRepositionInteractions(domElement, camera, meshGroup) {
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let isBakeSurfaceDragging = false;

  function isBakeModeEligible() {
    const tabBake = document.getElementById("tabBake");
    const isBakeTabActive = tabBake && tabBake.classList.contains("active");
    const isDragEnabled = state.bake && state.bake.surfaceDragEnabled !== false;
    return isBakeTabActive && isDragEnabled;
  }

  domElement.addEventListener("pointermove", (e) => {
    // 1. In-place Slot Repositioning Hover
    if (state.viewport3d.repositionMode && meshGroup) {
      const rect = domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);

      // Only raycast on valid weapon meshes (ignore gloves and sleeves)
      const validMeshes = meshGroup.children.filter(
        (m) => m.isMesh && m.visible && !m.userData.isGlove && m.userData.role !== "glove" && m.userData.role !== "sleeve"
      );

      const intersects = raycaster.intersectObjects(validMeshes, false);
      if (intersects.length > 0 && intersects[0].uv) {
        currentHoverHit = intersects[0];
        updateGhostTransform(currentHoverHit);
      } else {
        currentHoverHit = null;
        if (repositionReticleMesh) repositionReticleMesh.visible = false;
      }
      return;
    }

    // 2. Interactive 3D Surface Dragging for Bake Sticker
    if (isBakeSurfaceDragging && meshGroup) {
      const rect = domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);

      const validMeshes = meshGroup.children.filter(
        (m) => m.isMesh && m.visible && !m.userData.isGlove && m.userData.role !== "glove" && m.userData.role !== "sleeve"
      );

      const intersects = raycaster.intersectObjects(validMeshes, false);
      if (intersects.length > 0 && intersects[0].uv) {
        const hit = intersects[0];
        const texW = state.bake.baseImg?.width || 512;
        const texH = state.bake.baseImg?.height || 512;
        const x = Math.round(hit.uv.x * texW);
        const y = Math.round((1.0 - hit.uv.y) * texH);

        state.bake.x = x;
        state.bake.y = y;
        eventBus.emit("bake:coordsChanged", { x, y });
      }
      return;
    }

    // 3. Hover Cursor Feedback when Bake Sticker is ready to drag
    const hasBakeStickers = (state.bake?.layers && state.bake.layers.length > 0) || Boolean(state.bake?.stickerImg);
    if (isBakeModeEligible() && hasBakeStickers && meshGroup && !state.viewport3d.repositionMode) {
      const rect = domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const validMeshes = meshGroup.children.filter(
        (m) => m.isMesh && m.visible && !m.userData.isGlove && m.userData.role !== "glove" && m.userData.role !== "sleeve"
      );
      const intersects = raycaster.intersectObjects(validMeshes, false);
      domElement.style.cursor = (intersects.length > 0 && intersects[0].uv) ? "crosshair" : "";
    }
  });

  domElement.addEventListener("pointerleave", () => {
    currentHoverHit = null;
    if (repositionReticleMesh) repositionReticleMesh.visible = false;
    if (!isBakeSurfaceDragging) {
      domElement.style.cursor = "";
    }
  });

  domElement.addEventListener("pointerdown", (e) => {
    if (e.button === 0) {
      pointerDownPos = { x: e.clientX, y: e.clientY, time: Date.now() };

      // Check if user is starting a 3D Surface Bake Drag
      if (!state.viewport3d.repositionMode && isBakeModeEligible() && meshGroup) {
        const rect = domElement.getBoundingClientRect();
        mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const validMeshes = meshGroup.children.filter(
          (m) => m.isMesh && m.visible && !m.userData.isGlove && m.userData.role !== "glove" && m.userData.role !== "sleeve"
        );
        const intersects = raycaster.intersectObjects(validMeshes, false);

        if (intersects.length > 0 && intersects[0].uv) {
          const hasSticker = (state.bake?.layers && state.bake.layers.length > 0) || Boolean(state.bake?.stickerImg);
          if (!hasSticker) {
            showToast("Choose or add a sticker layer first to drag on the 3D weapon surface!", "info");
          } else {
            isBakeSurfaceDragging = true;
            if (state.viewport3d.controls) {
              state.viewport3d.controls.enabled = false;
            }
            domElement.style.cursor = "grabbing";

            const hit = intersects[0];
            const texW = state.bake.baseImg?.width || 512;
            const texH = state.bake.baseImg?.height || 512;
            const x = Math.round(hit.uv.x * texW);
            const y = Math.round((1.0 - hit.uv.y) * texH);

            state.bake.x = x;
            state.bake.y = y;
            eventBus.emit("bake:coordsChanged", { x, y });
          }
        }
      }
    }
  });

  window.addEventListener("pointerup", (e) => {
    // Release 3D surface dragging
    if (isBakeSurfaceDragging) {
      isBakeSurfaceDragging = false;
      if (state.viewport3d.controls) {
        state.viewport3d.controls.enabled = true;
      }
      domElement.style.cursor = "";
    }

    if (e.button === 0 && state.viewport3d.repositionMode) {
      const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
      const elapsed = Date.now() - pointerDownPos.time;
      if (dist < 6 && elapsed < 450) {
        const rect = domElement.getBoundingClientRect();
        mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        const validMeshes = meshGroup.children.filter(
          (m) => m.isMesh && m.visible && !m.userData.isGlove && m.userData.role !== "glove" && m.userData.role !== "sleeve"
        );
        const intersects = raycaster.intersectObjects(validMeshes, false);
        const hit = intersects.find((h) => h.uv) || currentHoverHit;
        if (hit && hit.uv) {
          executeSlotReposition(hit);
        }
      }
    }
  });

  // Pressing Escape cancels slot repositioning
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state.viewport3d.repositionMode) {
      exitSlotRepositionMode();
      showToast("Slot repositioning cancelled.", "info");
    }
  });
}

/**
 * Resolves the surface normal in true World coordinate space, transforming
 * the local face normal by the object's matrixWorld if rotated or transformed.
 */
function getHitWorldNormal(hit) {
  const normal = hit && hit.face && hit.face.normal ? hit.face.normal.clone() : new THREE.Vector3(0, 0, 1);
  if (hit && hit.object) {
    if (typeof hit.object.updateMatrixWorld === "function") {
      hit.object.updateMatrixWorld();
    }
    if (hit.object.matrixWorld) {
      normal.transformDirection(hit.object.matrixWorld);
    }
  }
  return normal.normalize();
}

/**
 * Updates holographic reticle cursor position and normal orientation
 */
function updateGhostTransform(hit) {
  if (!repositionReticleMesh || !hit || !hit.point || !hit.face) return;

  const worldNormal = getHitWorldNormal(hit);

  // Offset slightly along surface normal to eliminate z-fighting
  const offset = worldNormal.clone().multiplyScalar(0.06);
  repositionReticleMesh.position.copy(hit.point.clone().add(offset));

  // Align with polygon normal in world coordinates
  repositionReticleMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), worldNormal);

  // Scale reticle proportional to weapon radius
  const wb = state.viewport3d.currentWeaponBounds || state.viewport3d.currentBounds;
  const radius = wb && wb.radius ? wb.radius : 15;
  const baseDim = radius * 0.28;
  repositionReticleMesh.scale.set(baseDim, baseDim, 1);

  repositionReticleMesh.visible = true;
}

/**
 * Executes Safe In-Place Slot Repositioning (Solusi B) to the clicked surface coordinates
 */
async function executeSlotReposition(hit) {
  if (!hit || !hit.point || !state.viewport3d.repositionSlot) return;

  const targetSlot = state.viewport3d.repositionSlot;
  const group = state.viewport3d.meshGroup;
  let modelPoint = hit.point.clone();
  let modelNormal = getHitWorldNormal(hit);

  if (group) {
    if (typeof group.updateMatrixWorld === "function") {
      group.updateMatrixWorld(true);
    }
    modelPoint = group.worldToLocal(hit.point.clone());
    const invMat = new THREE.Matrix4().copy(group.matrixWorld).invert();
    modelNormal = modelNormal.clone().transformDirection(invMat).normalize();
  }

  const posArr = [modelPoint.x, modelPoint.y, modelPoint.z];
  const normalArr = [modelNormal.x, modelNormal.y, modelNormal.z];
  const boneId = hit.object?.userData?.boneId;
  const actionTeam = state.currentTeam;
  const actionWeapon = state.currentWeapon;

  showLoader(`Moving slot '${targetSlot}' to new surface position...`);
  try {
    const payload = {
      team: actionTeam,
      weapon: actionWeapon,
      slot: targetSlot,
      pos: posArr,
      normal: normalArr,
      scale: 1.0,
      rotation: 0.0,
      bone_id: boneId,
    };

    const res = await apiPost("/api/slot/reposition", payload);
    if (!res.success) throw new Error(res.error || "Slot repositioning failed");

    showToast(res.message || `Slot '${targetSlot}' repositioned successfully!`, "success");
    exitSlotRepositionMode();

    // Reload model metadata and 3D geometry immediately
    eventBus.emit("model:reloadRequest");
    await load3DModelGeometry();

    // Undo record
    let snapId = res.snapshot_id;
    eventBus.emit("history:record", {
      description: `Repositioned Slot ${targetSlot}`,
      team: actionTeam,
      weapon: actionWeapon,
      undo: async () => {
        showLoader("Undoing slot reposition...");
        try {
          await apiPost("/api/slot/undo", { team: actionTeam, weapon: actionWeapon, snapshot_id: snapId });
          eventBus.emit("model:reloadRequest");
          await load3DModelGeometry();
          showToast("Slot reposition undone.", "info");
        } finally {
          hideLoader();
        }
      },
      redo: async () => {
        showLoader("Redoing slot reposition...");
        try {
          const redoRes = await apiPost("/api/slot/reposition", payload);
          if (redoRes && redoRes.snapshot_id) {
            snapId = redoRes.snapshot_id;
          }
          eventBus.emit("model:reloadRequest");
          await load3DModelGeometry();
        } finally {
          hideLoader();
        }
      },
    });
  } catch (err) {
    showToast(`Slot repositioning failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

/**
 * Activates clean 3D Target-Pick mode for repositioning a specific sticker slot
 */
export function enterSlotRepositionMode(slotName) {
  state.viewport3d.repositionMode = true;
  state.viewport3d.repositionSlot = slotName;

  if (els.v3dCanvasContainer) {
    els.v3dCanvasContainer.classList.add("reposition-active");
  }
  if (els.v3dRepositionSlotName) {
    els.v3dRepositionSlotName.textContent = slotName;
  }
  if (els.v3dRepositionBanner) {
    els.v3dRepositionBanner.classList.remove("hidden");
  }

  // Adjust OrbitControls: Left Click places slot, Right Click rotates
  if (state.viewport3d.controls && typeof THREE !== "undefined") {
    state.viewport3d.controls.mouseButtons = {
      LEFT: THREE.MOUSE.NONE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.ROTATE,
    };
  }

  showToast(`Mode Move Slot active: Click anywhere on weapon surface to reposition ${slotName}!`, "info");
}

/**
 * Exits 3D Target-Pick reposition mode and restores default camera controls
 */
export function exitSlotRepositionMode() {
  state.viewport3d.repositionMode = false;
  state.viewport3d.repositionSlot = null;

  if (els.v3dCanvasContainer) {
    els.v3dCanvasContainer.classList.remove("reposition-active");
  }
  if (els.v3dRepositionBanner) {
    els.v3dRepositionBanner.classList.add("hidden");
  }
  if (repositionReticleMesh) {
    repositionReticleMesh.visible = false;
  }
  currentHoverHit = null;

  // Restore OrbitControls
  if (state.viewport3d.controls && typeof THREE !== "undefined") {
    state.viewport3d.controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.PAN,
    };
  }
}

function setupRepositionBannerEvents() {
  if (els.v3dRepositionCancelBtn) {
    els.v3dRepositionCancelBtn.addEventListener("click", () => {
      exitSlotRepositionMode();
      showToast("Slot repositioning cancelled.", "info");
    });
  }
}

/**
 * Slot Pulse Highlight: Emissive cyan pulsing when user hovers a slot card in Tab 1
 */
function handleSlotPulseHover(textureName, textureIndex, isHovering) {
  if (!state.viewport3d.initialized || !state.viewport3d.meshGroup) return;

  if (isHovering) {
    const mesh = state.viewport3d.meshGroup.children.find(
      (m) =>
        m.isMesh &&
        (m.userData.textureName === textureName ||
          m.userData.textureIndex === textureIndex ||
          (m.userData.slotIdentifier && m.userData.slotIdentifier.toLowerCase() === (textureName || "").toLowerCase()))
    );
    if (mesh && mesh.material) {
      if (mesh.userData.savedEmissive === undefined) {
        mesh.userData.savedEmissive = mesh.material.emissive ? mesh.material.emissive.getHex() : 0x000000;
        mesh.userData.savedEmissiveIntensity = mesh.material.emissiveIntensity !== undefined ? mesh.material.emissiveIntensity : 0.0;
      }
      state.viewport3d.pulsingMesh = mesh;
    }
  } else {
    if (state.viewport3d.pulsingMesh && state.viewport3d.pulsingMesh.material) {
      const pm = state.viewport3d.pulsingMesh;
      if (pm.material.uniforms && pm.material.uniforms.uHighlight) {
        pm.material.uniforms.uHighlight.value = state.viewport3d.highlightStickers ? 1.0 : 0.0;
      } else if (pm.material.emissive) {
        pm.material.emissive.setHex(pm.userData.savedEmissive !== undefined ? pm.userData.savedEmissive : 0x000000);
        pm.material.emissiveIntensity = pm.userData.savedEmissiveIntensity !== undefined ? pm.userData.savedEmissiveIntensity : 0.0;
        pm.material.needsUpdate = true;
      }
      pm.userData.savedEmissive = undefined;
      pm.userData.savedEmissiveIntensity = undefined;
    }
    state.viewport3d.pulsingMesh = null;
  }
}

/**
 * High-Res Snapshot Studio: Renders current 3D view at 4K UHD (3840x2160) with transparent background
 * using an offscreen canvas export without grid floor obstruction.
 */
export async function takeHighResSnapshot(options = {}) {
  const {
    width = 3840,
    height = 2160,
    transparent = state.viewport3d.snapshotTransparent !== false,
  } = options;

  const { scene, camera, renderer } = state.viewport3d;
  if (!scene || !camera || !renderer) {
    showToast("3D Viewport is not initialized yet.", "error");
    return;
  }

  const container = els.v3dCanvasContainer;
  const origW = container ? container.clientWidth : 800;
  const origH = container ? container.clientHeight : 580;
  const origAspect = camera.aspect;
  const origBg = scene.background;

  // Temporarily hide ground grid helper and reticle so studio snapshot is pristine
  const gridHelper = scene.children.find((c) => c.type === "GridHelper" || c.isGridHelper);
  const origGridVis = gridHelper ? gridHelper.visible : true;
  if (gridHelper) gridHelper.visible = false;
  if (repositionReticleMesh) repositionReticleMesh.visible = false;

  showLoader(`Rendering 4K studio snapshot (${width}x${height})...`);
  try {
    if (transparent) {
      scene.background = null;
    }

    // Prepare offscreen canvas for high-resolution 4K render output
    const offscreenCanvas = document.createElement("canvas");
    offscreenCanvas.width = width;
    offscreenCanvas.height = height;
    const offscreenCtx = offscreenCanvas.getContext("2d");

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    renderer.render(scene, camera);

    // Blit WebGL buffer onto offscreen canvas for browser PNG blob generation
    offscreenCtx.drawImage(renderer.domElement, 0, 0, width, height);
    const dataUrl = offscreenCanvas.toDataURL("image/png");

    const link = document.createElement("a");
    const weaponName = (state.currentWeapon || "weapon").toLowerCase();
    link.download = `v_${weaponName}_snapshot_4k.png`;
    link.href = dataUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast(`4K High-Res Snapshot exported (v_${weaponName}_snapshot_4k.png)!`, "success");
  } catch (err) {
    console.error("High-Res Snapshot failed:", err);
    showToast(`Failed to capture snapshot: ${err.message}`, "error");
  } finally {
    // Restore original size, background, and helper visibilities
    scene.background = origBg;
    if (gridHelper) gridHelper.visible = origGridVis;
    camera.aspect = origAspect;
    camera.updateProjectionMatrix();
    renderer.setSize(origW, origH, false);
    renderer.render(scene, camera);
    hideLoader();

    if (state.viewport3d.repositionMode && currentHoverHit) {
      updateGhostTransform(currentHoverHit);
    }
  }
}
