/**
 * modules/chrome_studio.js - Dual-Layer Metallic Specular Chrome Engine & Studio Module
 * CS 1.6 Asset Studio Pro Modular Architecture
 * 100% SVG Vector Glyph System (Zero Unicode Emojis)
 */

import { state, eventBus } from "../core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader } from "../core/api.js";

let orbScene = null;
let orbCamera = null;
let orbRenderer = null;
let orbSphere = null;
let orbMaterial = null;
let orbTexture = null;
let orbAnimFrameId = null;
let orbCanvas2D = null;
let orbCanvasCtx = null;

// Chrome Studio State
export const chromeState = {
  activePreset: "silver",
  intensity: 100,
  tightness: 1.8,
  tint: 0,
  targetParts: [],
  availableSubmodels: [],
  numBodyparts: 0,
  maxBodyparts: 32,
  hasChrome: false,
  canInject: true,
  health: null,
};

const PRESET_DEFAULTS = {
  silver: { intensity: 100, tightness: 1.8, tint: 0, color: "#e2e8f0" },
  gunmetal: { intensity: 90, tightness: 1.6, tint: 215, color: "#64748b" },
  mirror: { intensity: 140, tightness: 2.2, tint: 0, color: "#ffffff" },
  gold: { intensity: 110, tightness: 1.8, tint: 42, color: "#f59e0b" },
  "24k gold": { intensity: 110, tightness: 1.8, tint: 42, color: "#f59e0b" },
  "gold arabesque": { intensity: 115, tightness: 1.8, tint: 40, color: "#fbbf24" },
  sapphire: { intensity: 115, tightness: 1.9, tint: 225, color: "#2563eb" },
  ruby: { intensity: 110, tightness: 1.8, tint: 350, color: "#ef4444" },
  emerald: { intensity: 105, tightness: 1.8, tint: 145, color: "#10b981" },
  "black pearl": { intensity: 120, tightness: 2.0, tint: 270, color: "#6b21a8" },
  "doppler phase 1": { intensity: 115, tightness: 1.9, tint: 280, color: "#8b5cf6" },
  "doppler phase 2": { intensity: 120, tightness: 1.9, tint: 320, color: "#ec4899" },
  "doppler phase 3": { intensity: 115, tightness: 1.9, tint: 195, color: "#0ea5e9" },
  "doppler phase 4": { intensity: 120, tightness: 2.0, tint: 220, color: "#3b82f6" },
  "gamma doppler phase 1": { intensity: 115, tightness: 1.9, tint: 145, color: "#10b981" },
  "gamma doppler phase 2": { intensity: 125, tightness: 2.0, tint: 115, color: "#22c55e" },
  "gamma doppler phase 3": { intensity: 115, tightness: 1.9, tint: 170, color: "#14b8a6" },
  "gamma doppler phase 4": { intensity: 120, tightness: 1.9, tint: 155, color: "#059669" },
  "gamma emerald": { intensity: 130, tightness: 2.1, tint: 130, color: "#00ff88" },
  "blue gem": { intensity: 120, tightness: 2.0, tint: 200, color: "#06b6d4" },
  "case hardened": { intensity: 115, tightness: 1.8, tint: 205, color: "#38bdf8" },
  "case hardened tier 1": { intensity: 125, tightness: 2.0, tint: 210, color: "#0284c7" },
  fade: { intensity: 115, tightness: 1.8, tint: 330, color: "#f43f5e" },
  "full fade": { intensity: 125, tightness: 2.0, tint: 330, color: "#e11d48" },
  "marble fade": { intensity: 120, tightness: 1.9, tint: 200, color: "#a855f7" },
  "marble fade fire & ice": { intensity: 125, tightness: 2.0, tint: 350, color: "#ef4444" },
  "amber fade": { intensity: 110, tightness: 1.8, tint: 35, color: "#d97706" },
  "acid fade": { intensity: 120, tightness: 1.9, tint: 120, color: "#84cc16" },
  "damascus steel": { intensity: 135, tightness: 2.2, tint: 0, color: "#cbd5e1" },
  printstream: { intensity: 130, tightness: 2.1, tint: 280, color: "#f1f5f9" },
  "hyper beast": { intensity: 120, tightness: 1.9, tint: 310, color: "#d946ef" },
  "tiger tooth": { intensity: 120, tightness: 1.9, tint: 42, color: "#eab308" },
  slaughter: { intensity: 115, tightness: 1.8, tint: 355, color: "#dc2626" },
  ultraviolet: { intensity: 110, tightness: 1.8, tint: 275, color: "#7c3aed" },
  "rust coat": { intensity: 75, tightness: 1.4, tint: 25, color: "#9a3412" },
  "hot rod": { intensity: 125, tightness: 2.0, tint: 0, color: "#b91c1c" },
  "cyan phosphor": { intensity: 125, tightness: 2.0, tint: 185, color: "#06b6d4" },
  "neon rider": { intensity: 120, tightness: 1.9, tint: 305, color: "#c026d3" },
  subtle: { intensity: 70, tightness: 1.5, tint: 0, color: "#94a3b8" },
  intense: { intensity: 145, tightness: 2.3, tint: 0, color: "#ffffff" },
};

export function initChromeStudioModule() {
  setupPillSwitcher();
  setupPresetGallery();
  setupParametricSliders();
  setupActionButtons();
  setupSelectionButtons();

  eventBus.on("model:loaded", () => {
    refreshChromeStatus();
  });

  eventBus.on("chrome:tabActivated", () => {
    if (!orbRenderer) {
      initOrbVisualizer();
    }
    refreshChromeStatus();
  });
}

/**
 * Initializes the sleek Sliding Segmented Pill Switcher
 */
function setupPillSwitcher() {
  const buttons = document.querySelectorAll(".pill-switch-btn");
  const subpanes = document.querySelectorAll(".finishes-subpane");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetSub = btn.dataset.subpane;
      buttons.forEach((b) => {
        b.classList.remove("active", "bg-cyber-cyan", "text-obsidian-950", "font-bold", "shadow-sm");
        b.classList.add("text-slate-400");
      });
      subpanes.forEach((p) => {
        p.classList.remove("active");
        p.classList.add("hidden");
      });

      btn.classList.add("active", "bg-cyber-cyan", "text-obsidian-950", "font-bold", "shadow-sm");
      btn.classList.remove("text-slate-400");
      const pascalSub = targetSub.charAt(0).toUpperCase() + targetSub.slice(1);
      const targetPane = document.getElementById(`subpane${pascalSub}`) ||
                         document.getElementById(`subpane${targetSub}`) ||
                         (targetSub.toLowerCase() === "stattrak" ? document.getElementById("subpaneStatTrak") : null);
      if (targetPane) {
        targetPane.classList.add("active");
        targetPane.classList.remove("hidden");
      }

      if (targetSub === "chrome") {
        if (!orbRenderer) {
          initOrbVisualizer();
        }
      }
    });
  });
}

/**
 * Preset finish gallery chip selectors
 */
function setupPresetGallery() {
  const chips = document.querySelectorAll(".preset-chip-btn");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");

      const preset = chip.dataset.preset;
      chromeState.activePreset = preset;

      const label = document.getElementById("chromeActivePresetLabel");
      if (label) {
        label.textContent = chip.querySelector("span:last-child")?.textContent || preset;
      }

      // Apply preset defaults
      const defs = PRESET_DEFAULTS[preset];
      if (defs) {
        chromeState.intensity = defs.intensity;
        chromeState.tightness = defs.tightness;
        chromeState.tint = defs.tint;

        syncSliderUI();
      }

      updateOrbTexture();
    });
  });
}

function syncSliderUI() {
  const intSlider = document.getElementById("chromeIntensitySlider");
  const intVal = document.getElementById("chromeIntensityVal");
  if (intSlider && intVal) {
    intSlider.value = chromeState.intensity;
    intVal.textContent = `${chromeState.intensity}%`;
  }

  const tightSlider = document.getElementById("chromeTightnessSlider");
  const tightVal = document.getElementById("chromeTightnessVal");
  if (tightSlider && tightVal) {
    tightSlider.value = chromeState.tightness;
    tightVal.textContent = Number(chromeState.tightness).toFixed(1);
  }

  const tintSlider = document.getElementById("chromeTintSlider");
  const tintVal = document.getElementById("chromeTintVal");
  if (tintSlider && tintVal) {
    tintSlider.value = chromeState.tint;
    tintVal.textContent = `${chromeState.tint}°`;
  }
}

/**
 * Real-time parametric slider events
 */
function setupParametricSliders() {
  const intSlider = document.getElementById("chromeIntensitySlider");
  const intVal = document.getElementById("chromeIntensityVal");
  if (intSlider) {
    intSlider.addEventListener("input", (e) => {
      chromeState.intensity = parseFloat(e.target.value) || 100;
      if (intVal) intVal.textContent = `${chromeState.intensity}%`;
      updateOrbTexture();
    });
  }

  const tightSlider = document.getElementById("chromeTightnessSlider");
  const tightVal = document.getElementById("chromeTightnessVal");
  if (tightSlider) {
    tightSlider.addEventListener("input", (e) => {
      chromeState.tightness = parseFloat(e.target.value) || 1.8;
      if (tightVal) tightVal.textContent = Number(chromeState.tightness).toFixed(1);
      updateOrbTexture();
    });
  }

  const tintSlider = document.getElementById("chromeTintSlider");
  const tintVal = document.getElementById("chromeTintVal");
  if (tintSlider) {
    tintSlider.addEventListener("input", (e) => {
      chromeState.tint = parseFloat(e.target.value) || 0;
      if (tintVal) tintVal.textContent = `${chromeState.tint}°`;
      updateOrbTexture();
    });
  }
}

function setupSelectionButtons() {
  const selectAllBtn = document.getElementById("chromeSelectAllPartsBtn");
  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", () => {
      document.querySelectorAll(".chrome-comp-check").forEach((chk) => {
        chk.checked = true;
      });
      collectTargetParts();
    });
  }

  const clearBtn = document.getElementById("chromeClearPartsBtn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      document.querySelectorAll(".chrome-comp-check").forEach((chk) => {
        chk.checked = false;
      });
      collectTargetParts();
    });
  }
}

function collectTargetParts() {
  const checked = [];
  document.querySelectorAll(".chrome-comp-check:checked").forEach((chk) => {
    checked.push(chk.value);
  });
  chromeState.targetParts = checked;
}

/**
 * Action Buttons: Inject Chrome & Revert to Matte
 */
function setupActionButtons() {
  const injectBtn = document.getElementById("chromeInjectBtn");
  if (injectBtn) {
    injectBtn.addEventListener("click", async () => {
      await injectChrome();
    });
  }

  const removeBtn = document.getElementById("chromeRemoveBtn");
  if (removeBtn) {
    removeBtn.addEventListener("click", async () => {
      await removeChrome();
    });
  }
}

/**
 * Fetches status from backend /api/chrome/status and renders the UI
 */
export async function refreshChromeStatus() {
  const weapon = state.currentWeapon;
  const team = state.currentTeam;
  if (!weapon) return;

  try {
    const res = await apiGet(`/api/chrome/status?team=${team}&weapon=${weapon}`);
    if (!res.success) return;

    chromeState.hasChrome = res.has_chrome;
    chromeState.numBodyparts = res.num_bodyparts;
    chromeState.maxBodyparts = res.max_bodyparts || 32;
    chromeState.canInject = res.can_inject;
    chromeState.availableSubmodels = res.detected_submodels || [];
    chromeState.health = res.health;

    if (res.active_preset) {
      chromeState.activePreset = res.active_preset.toLowerCase();
      const chip = document.querySelector(`.preset-chip-btn[data-preset="${chromeState.activePreset}"]`);
      if (chip) {
        document.querySelectorAll(".preset-chip-btn").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        const label = document.getElementById("chromeActivePresetLabel");
        if (label) label.textContent = chip.querySelector("span:last-child")?.textContent || chromeState.activePreset;
      }
    }

    renderSafetyBudgetGauge();
    renderComponentCheckchips();
  } catch (err) {
    console.warn("Could not fetch chrome status:", err);
  }
}

function renderSafetyBudgetGauge() {
  const countLabel = document.getElementById("chromeBodypartCountLabel");
  const fill = document.getElementById("chromeBodypartBudgetFill");
  const statusTag = document.getElementById("chromeBudgetStatusTag");
  const healthLabel = document.getElementById("chromeHealthLabel");
  const vertsLabel = document.getElementById("chromeVertsBudgetLabel");

  const used = chromeState.numBodyparts;
  const max = chromeState.maxBodyparts || 32;
  const pct = Math.min(100, Math.round((used / max) * 100));

  if (countLabel) {
    countLabel.textContent = `${used} / ${max} Used`;
  }

  if (fill) {
    fill.style.width = `${pct}%`;
    fill.className = "budget-fill";
    if (used <= 24) {
      fill.classList.add("safe");
    } else if (used < 32) {
      fill.classList.add("warning");
    } else {
      fill.classList.add("danger");
    }
  }

  if (statusTag) {
    statusTag.className = "budget-status-tag";
    if (used <= 24) {
      statusTag.classList.add("safe");
      statusTag.textContent = "Safe";
    } else if (used < 32) {
      statusTag.classList.add("warning");
      statusTag.textContent = "Tight Budget";
    } else {
      statusTag.classList.add("danger");
      statusTag.textContent = "Limit Reached";
    }
  }

  if (healthLabel && chromeState.health) {
    const h = chromeState.health;
    healthLabel.textContent = `${h.status} (${h.score || 100}/100)`;
    healthLabel.className = h.healthy ? "budget-subvalue text-emerald" : "budget-subvalue text-red";
  }

  if (vertsLabel && chromeState.health) {
    const maxV = chromeState.health.max_verts_submodel || 0;
    vertsLabel.textContent = `${maxV} / 2048 ${maxV <= 2048 ? "(Safe)" : "(Exceeded)"}`;
    vertsLabel.className = maxV <= 2048 ? "budget-subvalue" : "budget-subvalue text-red";
  }
}

function getFriendlySubmodelName(weaponKey, rawName, bodypartName) {
  const lower = (rawName || "").toLowerCase().trim();
  const bpLower = (bodypartName || "").toLowerCase().trim();

  const map = {
    ref_01: "Upper Slide / Sights",
    ref_02: "Lower Frame / Receiver",
    ref_03: "Barrel & Action",
    ref_04: "Magazine / Clip",
    ref_05: "Silencer Suppressor",
  };

  if (map[lower]) {
    return map[lower];
  }

  if (lower.includes("slide")) return "Upper Slide";
  if (lower.includes("silencer") || lower.includes("suppressor")) return "Silencer Suppressor";
  if (lower.includes("receiver") || lower.includes("body")) return "Receiver Body";
  if (lower.includes("barrel")) return "Barrel Assembly";
  if (lower.includes("clip") || lower.includes("mag")) return "Magazine Clip";
  if (lower.includes("scope") || lower.includes("sight")) return "Scope / Sights";
  if (lower.includes("blade")) return "Knife Blade";
  if (lower.includes("handle") || lower.includes("grip")) return "Grip Frame";

  if (rawName && rawName !== "unnamed") {
    return rawName.charAt(0).toUpperCase() + rawName.slice(1);
  }
  return bpLower.charAt(0).toUpperCase() + bpLower.slice(1);
}

function renderComponentCheckchips() {
  const container = document.getElementById("chromeComponentsList");
  if (!container) return;
  container.innerHTML = "";

  const submodels = chromeState.availableSubmodels;
  if (!submodels || submodels.length === 0) {
    container.innerHTML = '<span style="font-size: 0.72rem; color: var(--text-muted); padding: 4px;">No separable components found.</span>';
    return;
  }

  submodels.forEach((sm, idx) => {
    const label = document.createElement("label");
    label.className = "weapon-check-card";
    const friendlyName = getFriendlySubmodelName(state.currentWeapon, sm.name, sm.bodypart);
    label.title = `${friendlyName} [${sm.name}] (${sm.numverts} vertices) in ${sm.bodypart}`;

    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.className = "chrome-comp-check";
    chk.value = sm.name;
    chk.checked = true;

    chk.addEventListener("change", () => {
      label.classList.toggle("is-checked", chk.checked);
      collectTargetParts();
    });

    const span = document.createElement("span");
    span.textContent = `${friendlyName} (${sm.numverts}v)`;

    label.appendChild(chk);
    label.appendChild(span);
    label.classList.add("is-checked");
    container.appendChild(label);
  });

  collectTargetParts();
}

/**
 * Applies dual-layer chrome injection via POST /api/chrome/inject
 */
async function injectChrome() {
  const weapon = state.currentWeapon;
  const team = state.currentTeam;
  if (!weapon) return;

  const syncPw = Boolean(document.getElementById("chromeSyncPwCheck")?.checked);
  collectTargetParts();

  showLoader(`Injecting ${chromeState.activePreset.toUpperCase()} Chrome into ${weapon.toUpperCase()}...`);
  try {
    const payload = {
      team,
      weapon,
      preset: chromeState.activePreset,
      intensity: chromeState.intensity,
      tightness: chromeState.tightness,
      tint: chromeState.tint,
      sync_pw: syncPw,
    };

    if (chromeState.targetParts && chromeState.targetParts.length > 0) {
      payload.target_parts = chromeState.targetParts;
    }

    const res = await apiPost("/api/chrome/inject", payload);
    if (!res.success) throw new Error(res.error || "Chrome injection failed");

    showToast(res.message || "Dual-layer metallic chrome injected successfully!", "success");
    eventBus.emit("model:reloadRequest");
    await refreshChromeStatus();
  } catch (err) {
    showToast(`Injection failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

/**
 * Reverts to clean matte via POST /api/chrome/remove
 */
async function removeChrome() {
  const weapon = state.currentWeapon;
  const team = state.currentTeam;
  if (!weapon) return;

  const syncPw = Boolean(document.getElementById("chromeSyncPwCheck")?.checked);

  showLoader(`Reverting ${weapon.toUpperCase()} to clean matte...`);
  try {
    const res = await apiPost("/api/chrome/remove", {
      team,
      weapon,
      sync_pw: syncPw,
    });
    if (!res.success) throw new Error(res.error || "Removal failed");

    showToast(res.message || "Chrome overlay safely stripped.", "success");
    eventBus.emit("model:reloadRequest");
    await refreshChromeStatus();
  } catch (err) {
    showToast(`Reversion failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

/**
 * Live 60 FPS 3D Chrome Orb Visualizer (Three.js mini rotating sphere)
 */
function initOrbVisualizer() {
  const canvas = document.getElementById("chromeOrbCanvas");
  if (!canvas || typeof THREE === "undefined") return;

  const w = canvas.clientWidth || 120;
  const h = canvas.clientHeight || 120;

  orbScene = new THREE.Scene();
  orbCamera = new THREE.PerspectiveCamera(40, 1.0, 0.1, 100);
  orbCamera.position.set(0, 0, 3.2);

  try {
    orbRenderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    orbRenderer.setSize(w, h, false);
    orbRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  } catch (e) {
    console.warn("Could not create WebGLRenderer for Orb canvas:", e);
    return;
  }

  // Create client-side procedural 64x64 texture canvas
  orbCanvas2D = document.createElement("canvas");
  orbCanvas2D.width = 64;
  orbCanvas2D.height = 64;
  orbCanvasCtx = orbCanvas2D.getContext("2d");

  renderProceduralReflectionToCanvas();

  orbTexture = new THREE.CanvasTexture(orbCanvas2D);
  orbTexture.magFilter = THREE.LinearFilter;
  orbTexture.minFilter = THREE.LinearFilter;
  orbTexture.wrapS = THREE.ClampToEdgeWrapping;
  orbTexture.wrapT = THREE.ClampToEdgeWrapping;

  // Additive Spherical Shader Material mirroring GoldSrc R_StudioChrome
  orbMaterial = new THREE.ShaderMaterial({
    uniforms: {
      tChrome: { value: orbTexture },
      uIntensity: { value: 1.0 },
    },
    vertexShader: `
      varying vec2 vChromeUV;
      varying vec3 vViewNormal;
      void main() {
        vec3 vNorm = normalize(normalMatrix * normal);
        vChromeUV = vec2(vNorm.x * 0.5 + 0.5, -vNorm.y * 0.5 + 0.5);
        vViewNormal = vNorm;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D tChrome;
      uniform float uIntensity;
      varying vec2 vChromeUV;
      varying vec3 vViewNormal;
      void main() {
        vec4 col = texture2D(tChrome, vChromeUV);
        // Base dark metal sphere with specular chrome reflection highlight
        vec3 baseMetal = vec3(0.08, 0.10, 0.14) * max(0.0, vViewNormal.z);
        gl_FragColor = vec4(baseMetal + col.rgb * uIntensity, 1.0);
      }
    `,
  });

  const geom = new THREE.SphereGeometry(1.0, 32, 32);
  orbSphere = new THREE.Mesh(geom, orbMaterial);
  orbScene.add(orbSphere);

  // 60 FPS Turntable Rotation Loop
  function animateOrb() {
    orbAnimFrameId = requestAnimationFrame(animateOrb);
    if (orbSphere) {
      orbSphere.rotation.y += 0.015;
      orbSphere.rotation.x = Math.sin(Date.now() * 0.001) * 0.15;
    }
    if (orbRenderer && orbScene && orbCamera) {
      orbRenderer.render(orbScene, orbCamera);
    }
  }

  animateOrb();
}

/**
 * Updates the 64x64 reflection texture dynamically
 */
export function updateOrbTexture() {
  if (!orbCanvasCtx || !orbTexture) return;
  renderProceduralReflectionToCanvas();
  orbTexture.needsUpdate = true;
}

/**
 * Renders procedural 64x64 reflection map on 2D canvas in microseconds
 */
function renderProceduralReflectionToCanvas() {
  if (!orbCanvasCtx) return;
  const w = 64;
  const h = 64;
  const imgData = orbCanvasCtx.createImageData(w, h);
  const data = imgData.data;

  const cx = 31.5;
  const cy = 31.5;
  const rCut = 12.10;
  const preset = chromeState.activePreset.toLowerCase();
  const intensityScale = chromeState.intensity / 100.0;
  const p = Math.max(0.4, chromeState.tightness);
  const tintDeg = (chromeState.tint || 0) % 360;

  const peakMap = {
    silver: 174,
    gunmetal: 135,
    mirror: 245,
    "24k gold": 180,
    gold: 174,
    sapphire: 190,
    ruby: 185,
    emerald: 180,
    "blue gem": 195,
  };

  const basePeak = peakMap[preset] || 174;
  const peak = Math.min(255, Math.max(10, basePeak * intensityScale));

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = (y * w + x) * 4;
      const dist = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);

      if (dist > rCut) {
        data[idx] = 0;
        data[idx + 1] = 0;
        data[idx + 2] = 0;
        data[idx + 3] = 0;
        continue;
      }

      const cosineBase = 0.5 * (1.0 + Math.cos((Math.PI * dist) / rCut));
      const val = Math.min(255, Math.max(1, Math.round(peak * Math.pow(cosineBase, p))));

      let r = val;
      let g = val;
      let b = val;

      if (preset === "gold" || preset === "24k gold") {
        r = val;
        g = Math.round(val * 0.82);
        b = Math.round(val * 0.35);
      } else if (preset === "gunmetal") {
        r = Math.round(val * 0.72);
        g = Math.round(val * 0.78);
        b = Math.round(val * 0.88);
      } else if (preset === "sapphire") {
        r = Math.round(val * 0.22);
        g = Math.round(val * 0.55);
        b = val;
      } else if (preset === "ruby") {
        r = val;
        g = Math.round(val * 0.15);
        b = Math.round(val * 0.28);
      } else if (preset === "emerald") {
        r = Math.round(val * 0.20);
        g = val;
        b = Math.round(val * 0.40);
      } else if (preset === "blue gem") {
        if (val < 90) {
          r = Math.round(val * 0.70);
          g = Math.round(val * 0.20);
          b = Math.round(val * 0.95);
        } else if (val < 175) {
          const ratio = (val - 90) / 85.0;
          r = Math.round(val * (0.70 - 0.50 * ratio));
          g = Math.round(val * (0.20 + 0.60 * ratio));
          b = val;
        } else {
          r = val;
          g = Math.round(val * 0.85);
          b = Math.round(val * 0.35);
        }
      }

      // Hue tint rotation
      if (tintDeg !== 0) {
        const [h0, s0, v0] = rgbToHsv(r, g, b);
        const newH = (h0 + tintDeg / 360.0) % 1.0;
        const [nr, ng, nb] = hsvToRgb(newH, s0, v0);
        r = nr;
        g = ng;
        b = nb;
      }

      data[idx] = r;
      data[idx + 1] = g;
      data[idx + 2] = b;
      data[idx + 3] = 255;
    }
  }

  orbCanvasCtx.putImageData(imgData, 0, 0);
}

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  const d = max - min;
  const s = max === 0 ? 0 : d / max;
  const v = max;

  if (max !== min) {
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return [h, s, v];
}

function hsvToRgb(h, s, v) {
  let r = 0, g = 0, b = 0;
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);

  switch (i % 6) {
    case 0: r = v; g = t; b = p; break;
    case 1: r = q; g = v; b = p; break;
    case 2: r = p; g = v; b = t; break;
    case 3: r = p; g = q; b = v; break;
    case 4: r = t; g = p; b = v; break;
    case 5: r = v; g = p; b = q; break;
  }

  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}
