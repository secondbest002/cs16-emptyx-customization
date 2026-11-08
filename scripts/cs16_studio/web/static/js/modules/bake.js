/**
 * modules/bake.js - Interactive Free-Form Multi-Layer Sticker Staging & Bake Canvas
 * CS 1.6 Asset Studio Pro Modular Architecture (Phase 1 DCC Workflow)
 */

import { state, eventBus } from "../core/state.js";
import { apiPost, showToast, showLoader, hideLoader } from "../core/api.js";
import { getScrapedStickerCanvas, getScrapeConditionName } from "./sticker_scraper_client.js";

const els = {
  get bakeTargetSkin() { return document.getElementById("bakeTargetSkin"); },
  get bakePickLibraryBtn() { return document.getElementById("bakePickLibraryBtn"); },
  get bakeClearLayersBtn() { return document.getElementById("bakeClearLayersBtn"); },
  get bakeLayerCountBadge() { return document.getElementById("bakeLayerCountBadge"); },
  get bakeLayersList() { return document.getElementById("bakeLayersList"); },
  get bakeNoLayersPrompt() { return document.getElementById("bakeNoLayersPrompt"); },
  get bakeActiveLayerBanner() { return document.getElementById("bakeActiveLayerBanner"); },
  get bakeActiveLayerTitle() { return document.getElementById("bakeActiveLayerTitle"); },
  get bakeActiveLayerIndex() { return document.getElementById("bakeActiveLayerIndex"); },
  get bakeDropZone() { return document.getElementById("bakeDropZone"); },
  get bakeFileInput() { return document.getElementById("bakeFileInput"); },
  get bakePresets() { return document.getElementById("bakePresets"); },
  get bakeScale() { return document.getElementById("bakeScale"); },
  get bakeScaleVal() { return document.getElementById("bakeScaleVal"); },
  get bakeRotation() { return document.getElementById("bakeRotation"); },
  get bakeRotationVal() { return document.getElementById("bakeRotationVal"); },
  get bakeCoordX() { return document.getElementById("bakeCoordX"); },
  get bakeCoordY() { return document.getElementById("bakeCoordY"); },
  get bakeScrape() { return document.getElementById("bakeScrape"); },
  get bakeScrapeVal() { return document.getElementById("bakeScrapeVal"); },
  get bakeOpacity() { return document.getElementById("bakeOpacity"); },
  get bakeOpacityVal() { return document.getElementById("bakeOpacityVal"); },
  get bakeChromeEffect() { return document.getElementById("bakeChromeEffect"); },
  get bakeApplyBtn() { return document.getElementById("bakeApplyBtn"); },
  get bakeApplyBtnLabel() { return document.getElementById("bakeApplyBtnLabel"); },
  get bakeResetBtn() { return document.getElementById("bakeResetBtn"); },
  get bakeCanvas() { return document.getElementById("bakeCanvas"); },
  get bakePreviewPlaceholder() { return document.getElementById("bakePreviewPlaceholder"); },
  get syncPwModelsBtn() { return document.getElementById("syncPwModelsBtn"); },

  // Mode switcher & 3D surface dragging controls
  get bakeMode3DBtn() { return document.getElementById("bakeMode3DBtn"); },
  get bakeMode2DBtn() { return document.getElementById("bakeMode2DBtn"); },
  get bakeModeSplitBtn() { return document.getElementById("bakeModeSplitBtn"); },
  get bake3dDragToggleBtn() { return document.getElementById("bake3dDragToggleBtn"); },
  get bake3dDragToggleLabel() { return document.getElementById("bake3dDragToggleLabel"); },

  // Interactive Position Coordinates & Precision Nudge Controls
  get bakeSliderX() { return document.getElementById("bakeSliderX"); },
  get bakeInputX() { return document.getElementById("bakeInputX"); },
  get bakeSliderY() { return document.getElementById("bakeSliderY"); },
  get bakeInputY() { return document.getElementById("bakeInputY"); },
  get bakeCenterBtn() { return document.getElementById("bakeCenterBtn"); },
  get bakeNudgeLeft() { return document.getElementById("bakeNudgeLeft"); },
  get bakeNudgeRight() { return document.getElementById("bakeNudgeRight"); },
  get bakeNudgeUp() { return document.getElementById("bakeNudgeUp"); },
  get bakeNudgeDown() { return document.getElementById("bakeNudgeDown"); },
  get bakeNudgeStepToggle() { return document.getElementById("bakeNudgeStepToggle"); },

  // Screen 3: Rulers, UV Wireframe & Telemetry HUD Elements
  get rulerHCanvas() { return document.getElementById("rulerHCanvas"); },
  get rulerVCanvas() { return document.getElementById("rulerVCanvas"); },
  get uvWireCanvas() { return document.getElementById("uvWireCanvas"); },
  get uvWireframeToggleBtn() { return document.getElementById("uvWireframeToggleBtn"); },
  get uvWireframeLabel() { return document.getElementById("uvWireframeLabel"); },
  get rulersToggleBtn() { return document.getElementById("rulersToggleBtn"); },
  get rulersLabel() { return document.getElementById("rulersLabel"); },
  get rulerWorkspace() { return document.getElementById("rulerWorkspace"); },
  get telemCoords() { return document.getElementById("telemCoords"); },
  get telemUvNorm() { return document.getElementById("telemUvNorm"); },
  get telemScaleVal() { return document.getElementById("telemScaleVal"); },
  get telemRotVal() { return document.getElementById("telemRotVal"); },
  get telemQuantVal() { return document.getElementById("telemQuantVal"); },
  get paletteCellsTrack() { return document.getElementById("paletteCellsTrack"); },
  get paletteHoverReadout() { return document.getElementById("paletteHoverReadout"); },
};

let showUvWireframe = true;
let showRulers = true;
let gizmoDragMode = null; // null | 'move' | 'rotate' | 'scale'
let gizmoInitialScale = 1.0;
let gizmoInitialDist = 0;
let gizmoInitialAngle = 0;
let gizmoInitialRot = 0;
let cursorCoords = { x: 0, y: 0 };
let offscreenBakeCanvas = null;

// Initialize state.bake layers array
if (!state.bake) state.bake = {};
if (!state.bake.layers) state.bake.layers = [];
state.bake.activeLayerId = null;

export function initBakeModule() {
  setupEventListeners();

  eventBus.on("model:loaded", () => {
    setupBakeTab();
  });

  // When a sticker is selected from the library or dropped
  eventBus.on("bake:loadSticker", ({ previewUri, path, name }) => {
    addStickerLayer({ previewUri, path, name });
  });

  eventBus.on("amxx:requestSyncPw", () => {
    triggerSyncPw();
  });

  // Listen to 3D surface dragging coordinates from viewer3d.js
  eventBus.on("bake:coordsChanged", ({ x, y }) => {
    const active = getActiveLayer();
    if (active) {
      active.x = x;
      active.y = y;
      updateActiveLayerUI();
      renderBakeCanvas();
    }
  });

  // Listen to 3D Decal Stamping from viewer3d.js
  eventBus.on("bake:stamp3D", ({ x, y, textureIndex, scale, rotation, scrape }) => {
    handle3DStampPlacement({ x, y, textureIndex, scale, rotation, scrape });
  });

  // Listen to Scrape updates from 3D HUD or Coin Scrape
  eventBus.on("bake:setScrape", ({ scrape, delta }) => {
    const active = getActiveLayer();
    if (!active) return;
    if (delta !== undefined) {
      let nextVal = (active.scrape || 0) + delta;
      if (nextVal > 100) nextVal = 0;
      active.scrape = nextVal;
    } else if (scrape !== undefined) {
      active.scrape = Math.max(0, Math.min(100, parseInt(scrape, 10) || 0));
    }
    updateActiveLayerUI();
    renderBakeCanvas();
    eventBus.emit("bake:scrapeSync", { scrape: active.scrape, name: active.name });
  });
}

export function handle3DStampPlacement({ x, y, textureIndex, scale, rotation, scrape }) {
  const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
  const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;

  if (textureIndex !== undefined && textureIndex !== null && els.bakeTargetSkin) {
    if (String(els.bakeTargetSkin.value) !== String(textureIndex)) {
      els.bakeTargetSkin.value = String(textureIndex);
      loadActiveSkinToCanvas();
    }
  }

  const clampedX = Math.max(0, Math.min(bw, Math.round(x)));
  const clampedY = Math.max(0, Math.min(bh, Math.round(y)));

  const active = getActiveLayer();
  if (active) {
    active.x = clampedX;
    active.y = clampedY;
    if (scale !== undefined && scale !== null) active.scale = scale;
    if (rotation !== undefined && rotation !== null) active.rotation = rotation;
    if (scrape !== undefined && scrape !== null) active.scrape = scrape;

    updateActiveLayerUI();
    renderBakeCanvas();
    showToast(`Stamped "${active.name}" at (${clampedX}, ${clampedY}) in 3D!`, "success");
  } else {
    showToast("Please choose or add a sticker from the Library first to stamp!", "info");
  }
}

export function setupBakeTab() {
  const m = state.modelData;
  if (!m || !els.bakeTargetSkin) return;

  const bakeArea = document.getElementById("stage2dBakeArea");
  const curtainStage = document.getElementById("curtainCompareStage");
  const sideStage = document.getElementById("sideCompareStage");
  if (bakeArea) bakeArea.classList.remove("hidden");
  if (curtainStage) curtainStage.classList.add("hidden");
  if (sideStage) sideStage.classList.add("hidden");

  const prevSelected = els.bakeTargetSkin.value;
  els.bakeTargetSkin.innerHTML = "";
  const skins = m.textures.filter((t) => t.role === "skin");

  if (skins.length === 0) {
    els.bakeTargetSkin.innerHTML = '<option value="">No weapon skin textures found</option>';
    return;
  }

  skins.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.index;
    opt.textContent = `${s.name} (${s.width}x${s.height})`;
    els.bakeTargetSkin.appendChild(opt);
  });

  if (prevSelected && skins.some((s) => s.index === parseInt(prevSelected, 10))) {
    els.bakeTargetSkin.value = prevSelected;
  }

  loadActiveSkinToCanvas();
  renderLayersListUI();
}

export function loadActiveSkinToCanvas() {
  if (!els.bakeTargetSkin) return;
  const skinIdx = els.bakeTargetSkin.value;
  if (!skinIdx || !state.modelData) return;

  const tex = state.modelData.textures.find((t) => t.index === parseInt(skinIdx, 10));
  if (!tex || !tex.preview) return;

  const img = new Image();
  img.onload = () => {
    state.bake.baseImg = img;
    if (els.bakeCanvas) {
      els.bakeCanvas.width = img.width;
      els.bakeCanvas.height = img.height;
      els.bakeCanvas.style.display = "block";
    }
    if (els.bakePreviewPlaceholder) {
      els.bakePreviewPlaceholder.style.display = "none";
    }

    const w = img.width || 512;
    const h = img.height || 512;
    if (els.bakeSliderX) { els.bakeSliderX.min = 0; els.bakeSliderX.max = w; }
    if (els.bakeInputX) { els.bakeInputX.min = 0; els.bakeInputX.max = w; }
    if (els.bakeSliderY) { els.bakeSliderY.min = 0; els.bakeSliderY.max = h; }
    if (els.bakeInputY) { els.bakeInputY.min = 0; els.bakeInputY.max = h; }

    updateActiveLayerUI();
    renderBakeCanvas();
    drawUvWireframe(parseInt(skinIdx, 10), img.width, img.height);
    renderPaletteStrip(tex.palette, tex.is_masked);
  };
  img.src = tex.preview;
}

// ========================================================
// Multi-Layer Sticker Staging Engine
// ========================================================

export function getActiveLayer() {
  if (!state.bake.layers || state.bake.layers.length === 0) return null;
  if (state.bake.activeLayerId) {
    const found = state.bake.layers.find((l) => l.id === state.bake.activeLayerId);
    if (found) return found;
  }
  return state.bake.layers[state.bake.layers.length - 1];
}

export function addStickerLayer({ previewUri, path = null, name = null }) {
  const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
  const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;

  const layerId = "layer_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
  const layerName = name || (path ? path.split(/[\/\\]/).pop().replace(/\.[^/.]+$/, "") : `Sticker #${state.bake.layers.length + 1}`);

  // Auto-offset subsequent layers slightly so they don't stack directly on top
  const offsetIndex = state.bake.layers.length;
  const initX = Math.round(bw * 0.45) + (offsetIndex % 3) * 20;
  const initY = Math.round(bh * 0.45) + (offsetIndex % 3) * 15;

  showLoader("Loading sticker onto canvas...");
  const img = new Image();
  img.onload = () => {
    hideLoader();
    const newLayer = {
      id: layerId,
      name: layerName,
      img: img,
      previewUri: previewUri,
      path: path,
      x: initX,
      y: initY,
      scale: 1.0,
      rotation: 0.0,
      scrape: 0.0,
      opacity: 1.0,
      chrome_effect: "matte",
      visible: true,
      z_index: state.bake.layers.length,
    };

    state.bake.layers.push(newLayer);
    state.bake.activeLayerId = layerId;

    renderLayersListUI();
    updateActiveLayerUI();
    renderBakeCanvas();
    showToast(`Added "${layerName}" to staging canvas.`, "info");
  };
  img.onerror = () => {
    hideLoader();
    showToast("Failed to load sticker image.", "error");
  };
  img.src = previewUri;
}

export function removeStickerLayer(layerId) {
  const idx = state.bake.layers.findIndex((l) => l.id === layerId);
  if (idx < 0) return;

  const removed = state.bake.layers.splice(idx, 1)[0];
  if (state.bake.activeLayerId === layerId) {
    state.bake.activeLayerId = state.bake.layers.length > 0
      ? state.bake.layers[Math.max(0, idx - 1)].id
      : null;
  }

  // Re-index remaining layers
  state.bake.layers.forEach((l, i) => { l.z_index = i; });

  renderLayersListUI();
  updateActiveLayerUI();
  renderBakeCanvas();
  showToast(`Removed "${removed.name}".`, "info");
}

export function selectStickerLayer(layerId) {
  state.bake.activeLayerId = layerId;
  renderLayersListUI();
  updateActiveLayerUI();
  renderBakeCanvas();
}

export function toggleLayerVisibility(layerId) {
  const layer = state.bake.layers.find((l) => l.id === layerId);
  if (!layer) return;
  layer.visible = !layer.visible;
  renderLayersListUI();
  renderBakeCanvas();
}

export function clearAllLayers() {
  if (state.bake.layers.length === 0) return;
  state.bake.layers = [];
  state.bake.activeLayerId = null;
  renderLayersListUI();
  updateActiveLayerUI();
  renderBakeCanvas();
  showToast("All sticker layers cleared from staging.", "info");
}

export function renderLayersListUI() {
  const list = els.bakeLayersList;
  if (!list) return;

  const count = state.bake.layers.length;
  if (els.bakeLayerCountBadge) {
    els.bakeLayerCountBadge.textContent = `${count} LAYER${count === 1 ? "" : "S"}`;
  }

  if (els.bakeApplyBtnLabel) {
    els.bakeApplyBtnLabel.textContent = count > 1
      ? `BAKE ALL (${count} LAYERS)`
      : count === 1
      ? "BAKE TO SURFACE"
      : "BAKE TO SURFACE";
  }

  list.innerHTML = "";

  if (count === 0) {
    if (els.bakeNoLayersPrompt) {
      list.appendChild(els.bakeNoLayersPrompt);
      els.bakeNoLayersPrompt.style.display = "block";
    }
    if (els.bakeActiveLayerBanner) els.bakeActiveLayerBanner.style.display = "none";
    return;
  }

  if (els.bakeActiveLayerBanner) els.bakeActiveLayerBanner.style.display = "flex";

  const active = getActiveLayer();

  // Render in reverse so top layer is at the top of the UI list
  const displayLayers = [...state.bake.layers].reverse();

  displayLayers.forEach((layer) => {
    const isSelected = active && active.id === layer.id;

    const row = document.createElement("div");
    row.className = `bake-layer-item ${isSelected ? "active" : ""}`;
    row.dataset.layerId = layer.id;

    const thumb = document.createElement("img");
    thumb.className = "bake-layer-thumb";
    thumb.src = layer.previewUri;
    thumb.alt = layer.name;

    const info = document.createElement("div");
    info.className = "bake-layer-info";

    const title = document.createElement("span");
    title.className = "bake-layer-title";
    title.textContent = layer.name;

    const meta = document.createElement("span");
    meta.className = "bake-layer-meta";
    meta.textContent = `X:${Math.round(layer.x)} Y:${Math.round(layer.y)} • ${layer.scale.toFixed(2)}x`;

    info.appendChild(title);
    info.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "bake-layer-actions";

    // Visibility eye toggle
    const visBtn = document.createElement("button");
    visBtn.type = "button";
    visBtn.className = `bake-layer-btn ${layer.visible ? "" : "is-hidden"}`;
    visBtn.title = layer.visible ? "Hide layer" : "Show layer";
    visBtn.innerHTML = `<svg class="glyph glyph-xs"><use href="#glyph-eye"></use></svg>`;
    visBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleLayerVisibility(layer.id);
    });

    // Delete trash button
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "bake-layer-btn btn-delete";
    delBtn.title = "Delete layer";
    delBtn.innerHTML = `<svg class="glyph glyph-xs"><use href="#glyph-trash"></use></svg>`;
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      removeStickerLayer(layer.id);
    });

    actions.appendChild(visBtn);
    actions.appendChild(delBtn);

    row.appendChild(thumb);
    row.appendChild(info);
    row.appendChild(actions);

    row.addEventListener("click", () => {
      selectStickerLayer(layer.id);
    });

    list.appendChild(row);
  });
}

export function updateActiveLayerUI() {
  const active = getActiveLayer();
  const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
  const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;

  if (!active) {
    if (els.bakeActiveLayerTitle) els.bakeActiveLayerTitle.textContent = "None";
    if (els.bakeActiveLayerIndex) els.bakeActiveLayerIndex.textContent = "-";
    if (els.bakeCoordX) els.bakeCoordX.textContent = "-";
    if (els.bakeCoordY) els.bakeCoordY.textContent = "-";
    return;
  }

  const idx = state.bake.layers.findIndex((l) => l.id === active.id) + 1;
  if (els.bakeActiveLayerTitle) els.bakeActiveLayerTitle.textContent = active.name;
  if (els.bakeActiveLayerIndex) els.bakeActiveLayerIndex.textContent = `#${idx}`;

  const rx = Math.round(active.x);
  const ry = Math.round(active.y);
  if (els.bakeCoordX) els.bakeCoordX.textContent = rx;
  if (els.bakeCoordY) els.bakeCoordY.textContent = ry;
  if (els.bakeSliderX) els.bakeSliderX.value = rx;
  if (els.bakeInputX) els.bakeInputX.value = rx;
  if (els.bakeSliderY) els.bakeSliderY.value = ry;
  if (els.bakeInputY) els.bakeInputY.value = ry;

  if (els.bakeScale) els.bakeScale.value = active.scale;
  if (els.bakeScaleVal) els.bakeScaleVal.textContent = `${active.scale.toFixed(2)}x`;

  if (els.bakeRotation) els.bakeRotation.value = active.rotation;
  if (els.bakeRotationVal) els.bakeRotationVal.textContent = `${active.rotation}°`;

  if (els.bakeScrape) els.bakeScrape.value = active.scrape;
  if (els.bakeScrapeVal) {
    els.bakeScrapeVal.textContent = getScrapeConditionName(active.scrape);
  }

  if (els.bakeOpacity) els.bakeOpacity.value = Math.round((active.opacity ?? 1.0) * 100);
  if (els.bakeOpacityVal) els.bakeOpacityVal.textContent = `${Math.round((active.opacity ?? 1.0) * 100)}%`;

  if (els.bakeChromeEffect) els.bakeChromeEffect.value = active.chrome_effect || "matte";

  eventBus.emit("bake:activeLayerChanged", { layer: active });

  // Telemetry HUD
  if (els.telemCoords) els.telemCoords.textContent = `X: ${rx}, Y: ${ry}`;
  if (els.telemUvNorm) els.telemUvNorm.textContent = `(u: ${(rx / bw).toFixed(3)}, v: ${(ry / bh).toFixed(3)})`;
  if (els.telemScaleVal) els.telemScaleVal.textContent = `${active.scale.toFixed(2)}x`;
  if (els.telemRotVal) els.telemRotVal.textContent = `${active.rotation.toFixed(1)}°`;
}

// ========================================================
// 2D Canvas & Offscreen Compositing Engine
// ========================================================

export function renderBakeCanvas() {
  const canvas = els.bakeCanvas;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const bw = canvas.width;
  const bh = canvas.height;

  if (!offscreenBakeCanvas) {
    offscreenBakeCanvas = document.createElement("canvas");
  }
  if (offscreenBakeCanvas.width !== bw || offscreenBakeCanvas.height !== bh) {
    offscreenBakeCanvas.width = bw;
    offscreenBakeCanvas.height = bh;
  }
  const offCtx = offscreenBakeCanvas.getContext("2d");
  offCtx.clearRect(0, 0, bw, bh);

  // 1. Draw base weapon skin texture
  if (state.bake.baseImg) {
    offCtx.drawImage(state.bake.baseImg, 0, 0, bw, bh);
  }

  // 2. Composite all visible sticker layers in z_index order
  const sortedLayers = [...state.bake.layers].sort((a, b) => a.z_index - b.z_index);

  sortedLayers.forEach((layer) => {
    if (!layer.visible || !layer.img) return;

    const scrapeVal = layer.scrape || 0;
    const sImg = scrapeVal > 0
      ? getScrapedStickerCanvas(layer.img, scrapeVal, 1337, layer.id || layer.name)
      : layer.img;

    const baseDim = Math.round(bw * 0.25 * layer.scale);
    const aspect = sImg.width / Math.max(1, sImg.height);
    const sw = aspect >= 1.0 ? baseDim : Math.round(baseDim * aspect);
    const sh = aspect >= 1.0 ? Math.round(baseDim / aspect) : baseDim;

    offCtx.save();
    offCtx.translate(layer.x, layer.y);
    if (layer.rotation !== 0) {
      offCtx.rotate((layer.rotation * Math.PI) / 180);
    }
    offCtx.globalAlpha = layer.opacity ?? 1.0;
    offCtx.drawImage(sImg, -sw / 2, -sh / 2, sw, sh);

    // Chrome/Foil sheen overlay simulation
    const effect = layer.chrome_effect;
    if (effect && effect !== "matte" && effect !== "none") {
      offCtx.save();
      offCtx.globalCompositeOperation = "color-dodge";
      offCtx.globalAlpha = (layer.opacity ?? 1.0) * 0.35;
      const grad = offCtx.createLinearGradient(-sw / 2, -sh / 2, sw / 2, sh / 2);
      if (effect === "gold") {
        grad.addColorStop(0, "#ffe066");
        grad.addColorStop(0.5, "#d97706");
        grad.addColorStop(1, "#fef08a");
      } else if (effect === "sapphire") {
        grad.addColorStop(0, "#38bdf8");
        grad.addColorStop(0.5, "#1d4ed8");
        grad.addColorStop(1, "#93c5fd");
      } else if (effect === "ruby") {
        grad.addColorStop(0, "#f87171");
        grad.addColorStop(0.5, "#b91c1c");
        grad.addColorStop(1, "#fca5a5");
      } else if (effect === "emerald") {
        grad.addColorStop(0, "#34d399");
        grad.addColorStop(0.5, "#047857");
        grad.addColorStop(1, "#a7f3d0");
      } else {
        grad.addColorStop(0, "#ffffff");
        grad.addColorStop(0.5, "#94a3b8");
        grad.addColorStop(1, "#f8fafc");
      }
      offCtx.fillStyle = grad;
      offCtx.fillRect(-sw / 2, -sh / 2, sw, sh);
      offCtx.restore();
    }

    offCtx.restore();
  });

  // 3. Blit clean composite onto display canvas
  ctx.clearRect(0, 0, bw, bh);
  ctx.drawImage(offscreenBakeCanvas, 0, 0);

  // 4. Interactive Quad Gizmo on ACTIVE layer
  const active = getActiveLayer();
  if (active && active.visible && active.img) {
    const sImg = active.img;
    const baseDim = Math.round(bw * 0.25 * active.scale);
    const aspect = sImg.width / Math.max(1, sImg.height);
    const sw = aspect >= 1.0 ? baseDim : Math.round(baseDim * aspect);
    const sh = aspect >= 1.0 ? Math.round(baseDim / aspect) : baseDim;
    const rad = ((active.rotation || 0) * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);

    function toWorld(lx, ly) {
      return {
        x: active.x + (lx * cos - ly * sin),
        y: active.y + (lx * sin + ly * cos),
      };
    }

    const cTL = toWorld(-sw / 2, -sh / 2);
    const cTR = toWorld(sw / 2, -sh / 2);
    const cBR = toWorld(sw / 2, sh / 2);
    const cBL = toWorld(-sw / 2, sh / 2);
    const rotArmBase = toWorld(0, -sh / 2);
    const rotHandle = toWorld(0, -sh / 2 - 22);

    ctx.save();

    // Alignment Crosshairs
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, active.y); ctx.lineTo(bw, active.y);
    ctx.moveTo(active.x, 0); ctx.lineTo(active.x, bh);
    ctx.stroke();

    // Bounding Box Quad
    ctx.setLineDash([5, 3]);
    ctx.strokeStyle = "#00d4ff";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cTL.x, cTL.y);
    ctx.lineTo(cTR.x, cTR.y);
    ctx.lineTo(cBR.x, cBR.y);
    ctx.lineTo(cBL.x, cBL.y);
    ctx.closePath();
    ctx.stroke();

    // Rotation Arm & Handle
    ctx.setLineDash([]);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(rotArmBase.x, rotArmBase.y);
    ctx.lineTo(rotHandle.x, rotHandle.y);
    ctx.stroke();

    ctx.fillStyle = "#00d4ff";
    ctx.beginPath();
    ctx.arc(rotHandle.x, rotHandle.y, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 4 Corner Scale Anchor Pips
    const corners = [cTL, cTR, cBR, cBL];
    corners.forEach((c) => {
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(c.x - 4, c.y - 4, 8, 8);
      ctx.strokeStyle = "#00d4ff";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(c.x - 4, c.y - 4, 8, 8);
    });

    // Center Pivot Bullseye
    ctx.beginPath();
    ctx.arc(active.x, active.y, 4, 0, 2 * Math.PI);
    ctx.fillStyle = "#f59e0b";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.restore();
  }

  drawRulers(bw, bh);

  // Emit real-time texture update to Three.js 3D Viewport
  const skinIdx = els.bakeTargetSkin ? parseInt(els.bakeTargetSkin.value, 10) : null;
  if (skinIdx !== null && !isNaN(skinIdx) && state.bake.baseImg) {
    eventBus.emit("bake:textureUpdated", { textureIndex: skinIdx, canvas: offscreenBakeCanvas });
  }
}

// Coordinate Rulers
export function drawRulers(bw, bh) {
  if (!showRulers) return;
  const hCanvas = els.rulerHCanvas;
  const vCanvas = els.rulerVCanvas;
  if (!hCanvas || !vCanvas) return;

  if (hCanvas.width !== bw) hCanvas.width = bw;
  if (vCanvas.height !== bh) vCanvas.height = bh;

  const hCtx = hCanvas.getContext("2d");
  const vCtx = vCanvas.getContext("2d");

  // Horizontal Ruler
  hCtx.fillStyle = "#0b0f19";
  hCtx.fillRect(0, 0, bw, 20);
  hCtx.strokeStyle = "rgba(56, 189, 248, 0.4)";
  hCtx.fillStyle = "#94a3b8";
  hCtx.font = "8px monospace";
  hCtx.textAlign = "center";

  for (let x = 0; x <= bw; x += 16) {
    hCtx.beginPath();
    if (x % 64 === 0) {
      hCtx.moveTo(x, 8);
      hCtx.lineTo(x, 20);
      hCtx.stroke();
      if (x > 0 && x < bw) hCtx.fillText(String(x), x, 7);
    } else if (x % 32 === 0) {
      hCtx.moveTo(x, 13);
      hCtx.lineTo(x, 20);
      hCtx.stroke();
    } else {
      hCtx.moveTo(x, 16);
      hCtx.lineTo(x, 20);
      hCtx.stroke();
    }
  }

  if (cursorCoords.x >= 0 && cursorCoords.x <= bw) {
    hCtx.strokeStyle = "#38bdf8";
    hCtx.lineWidth = 2;
    hCtx.beginPath();
    hCtx.moveTo(cursorCoords.x, 0);
    hCtx.lineTo(cursorCoords.x, 20);
    hCtx.stroke();
    hCtx.lineWidth = 1;
  }

  // Vertical Ruler
  vCtx.fillStyle = "#0b0f19";
  vCtx.fillRect(0, 0, 20, bh);
  vCtx.strokeStyle = "rgba(56, 189, 248, 0.4)";
  vCtx.fillStyle = "#94a3b8";
  vCtx.font = "8px monospace";
  vCtx.textAlign = "left";

  for (let y = 0; y <= bh; y += 16) {
    vCtx.beginPath();
    if (y % 64 === 0) {
      vCtx.moveTo(8, y);
      vCtx.lineTo(20, y);
      vCtx.stroke();
      if (y > 0 && y < bh) vCtx.fillText(String(y), 1, y - 2);
    } else if (y % 32 === 0) {
      vCtx.moveTo(13, y);
      vCtx.lineTo(20, y);
      vCtx.stroke();
    } else {
      vCtx.moveTo(16, y);
      vCtx.lineTo(20, y);
      vCtx.stroke();
    }
  }

  if (cursorCoords.y >= 0 && cursorCoords.y <= bh) {
    vCtx.strokeStyle = "#38bdf8";
    vCtx.lineWidth = 2;
    vCtx.beginPath();
    vCtx.moveTo(0, cursorCoords.y);
    vCtx.lineTo(20, cursorCoords.y);
    vCtx.stroke();
    vCtx.lineWidth = 1;
  }
}

// 3D Mesh Polygon UV Wireframe Overlay
export function drawUvWireframe(skinIdx, bw, bh) {
  const canvas = els.uvWireCanvas;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (canvas.width !== bw) canvas.width = bw;
  if (canvas.height !== bh) canvas.height = bh;

  ctx.clearRect(0, 0, bw, bh);
  if (!showUvWireframe) return;

  const model3d = state.viewport3d?.model3dData;
  if (!model3d || !model3d.meshes) return;

  const targetMesh = model3d.meshes.find((m) => m.texture_index === skinIdx);
  if (!targetMesh || !targetMesh.uvs || targetMesh.uvs.length === 0) return;

  const uvs = targetMesh.uvs;
  ctx.save();
  ctx.strokeStyle = "rgba(56, 189, 248, 0.35)";
  ctx.lineWidth = 0.75;

  ctx.beginPath();
  for (let i = 0; i < uvs.length; i += 6) {
    const x0 = uvs[i] * bw;
    const y0 = uvs[i + 1] * bh;
    const x1 = uvs[i + 2] * bw;
    const y1 = uvs[i + 3] * bh;
    const x2 = uvs[i + 4] * bw;
    const y2 = uvs[i + 5] * bh;

    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineTo(x0, y0);
  }
  ctx.stroke();
  ctx.restore();
}

// Floyd-Steinberg 256-Color Palette Strip
export function renderPaletteStrip(paletteArray, isMasked = false) {
  const track = els.paletteCellsTrack;
  if (!track) return;
  track.innerHTML = "";

  if (!paletteArray || paletteArray.length === 0) {
    track.innerHTML = '<span style="color:#64748b; font-size:10px; margin:auto;">No indexed palette loaded</span>';
    return;
  }

  paletteArray.forEach((hex, idx) => {
    const cell = document.createElement("div");
    cell.className = "palette-swatch-cell";
    cell.style.background = hex;
    if (idx === 255 && isMasked) cell.classList.add("mask-cell");

    cell.addEventListener("mouseenter", () => {
      if (els.paletteHoverReadout) {
        const r = parseInt(hex.slice(1, 3), 16) || 0;
        const g = parseInt(hex.slice(3, 5), 16) || 0;
        const b = parseInt(hex.slice(5, 7), 16) || 0;
        const maskLabel = (idx === 255 && isMasked) ? " • [BLUE KEY MASK]" : "";
        els.paletteHoverReadout.textContent = `Index #${idx}: ${hex.toUpperCase()} (R: ${r}, G: ${g}, B: ${b})${maskLabel}`;
      }
    });

    track.appendChild(cell);
  });
}

// Preset positioning for active layer
function applyPreset(preset) {
  const active = getActiveLayer();
  if (!active) {
    showToast("Please add or select a sticker layer first.", "warning");
    return;
  }

  const bw = els.bakeCanvas ? els.bakeCanvas.width : 512;
  const bh = els.bakeCanvas ? els.bakeCanvas.height : 512;

  if (preset === "silencer") {
    active.x = Math.round(bw * 0.72);
    active.y = Math.round(bh * 0.35);
  } else if (preset === "slide") {
    active.x = Math.round(bw * 0.45);
    active.y = Math.round(bh * 0.35);
  } else if (preset === "wood") {
    active.x = Math.round(bw * 0.35);
    active.y = Math.round(bh * 0.47);
  } else if (preset === "mag") {
    active.x = Math.round(bw * 0.60);
    active.y = Math.round(bh * 0.70);
  } else if (preset === "stock") {
    active.x = Math.round(bw * 0.18);
    active.y = Math.round(bh * 0.45);
  } else {
    active.x = Math.round(bw * 0.45);
    active.y = Math.round(bh * 0.45);
  }

  updateActiveLayerUI();
  renderBakeCanvas();
}

function loadBakeStickerFromFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    addStickerLayer({ previewUri: e.target.result, path: null, name: file.name.replace(/\.[^/.]+$/, "") });
  };
  reader.readAsDataURL(file);
}

export function setBakeViewportMode(mode) {
  const stageModeSwitcher = document.getElementById("stageModeSwitcher");
  if (!stageModeSwitcher) return;
  const btn = stageModeSwitcher.querySelector(`[data-mode="${mode}"]`);
  if (btn) btn.click();
}

export async function triggerSyncPw() {
  const wep = state.currentWeapon;
  const team = state.currentTeam;
  if (!wep) return;

  showLoader(`Syncing P & W models for ${wep.toUpperCase()}...`);
  try {
    const res = await apiPost("/api/amxx/sync_pw", {
      weapon: wep,
      team: team,
      auto_backup: true,
      include_stickers: true,
    });
    if (res.success) {
      showToast(res.message || `Synchronized P/W models for ${wep.toUpperCase()}`, "success");
      eventBus.emit("amxx:pwSynced", { weapon: wep, team: team, result: res });
    } else {
      showToast(res.error || "P/W Synchronization failed", "error");
    }
  } catch (err) {
    showToast(`P/W Sync error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

// Master Single-Pass Multi-Sticker Bake Apply
async function applyBake() {
  if (!state.bake.layers || state.bake.layers.length === 0) {
    showToast("Please add at least one sticker layer to staging.", "warning");
    return;
  }

  const skinIdx = els.bakeTargetSkin ? els.bakeTargetSkin.value : null;
  if (!skinIdx) {
    showToast("No target weapon skin texture selected.", "error");
    return;
  }

  const activeLayers = state.bake.layers.filter((l) => l.visible);
  if (activeLayers.length === 0) {
    showToast("All sticker layers are currently hidden.", "warning");
    return;
  }

  showLoader(`Baking ${activeLayers.length} sticker layer(s) into weapon surface...`);
  try {
    const payload = {
      team: state.currentTeam,
      weapon: state.currentWeapon,
      texture_index: parseInt(skinIdx, 10),
      layers: activeLayers.map((l, idx) => ({
        id: l.id,
        name: l.name,
        image_base64: l.previewUri,
        image_path: l.path || null,
        x: Math.round(l.x),
        y: Math.round(l.y),
        scale: l.scale,
        rotation: l.rotation,
        scrape: (l.scrape || 0) / 100.0,
        opacity: l.opacity ?? 1.0,
        chrome_effect: l.chrome_effect,
        visible: true,
        z_index: idx,
      })),
      sync_pw: false,
    };

    const res = await apiPost("/api/bake_layers_commit", payload);
    if (!res.success) {
      throw new Error(res.error || "Bake commit failed");
    }

    showToast(res.message || "Successfully baked stickers onto weapon surface!", "success");

    // Clear staging layers
    state.bake.layers = [];
    state.bake.activeLayerId = null;
    renderLayersListUI();
    updateActiveLayerUI();
    renderBakeCanvas();

    // Record action for Undo/Redo stack
    const tex = state.modelData ? state.modelData.textures.find((t) => t.index === payload.texture_index) : null;
    const texName = tex ? tex.name : "skin";

    const actionTeam = state.currentTeam;
    const actionWeapon = state.currentWeapon;

    eventBus.emit("history:record", {
      description: `Baked ${payload.layers.length} Stickers onto ${texName}`,
      team: actionTeam,
      weapon: actionWeapon,
      undo: async () => {
        await apiPost("/api/revert", {
          team: actionTeam,
          weapon: actionWeapon,
          texture_index: payload.texture_index,
          texture_name: texName,
        });
      },
      redo: async () => {
        await apiPost("/api/bake_layers_commit", payload);
      },
    });

    eventBus.emit("model:reloadRequest");
    eventBus.emit("3d:requestReload");
  } catch (err) {
    showToast(`Bake failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

// ========================================================
// DOM Event Listeners & Gizmo Dragging
// ========================================================

function setupEventListeners() {
  const canvas = els.bakeCanvas;
  if (canvas) {
    function getCanvasCoords(e) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / (rect.width || 1);
      const scaleY = canvas.height / (rect.height || 1);
      return {
        x: Math.round((e.clientX - rect.left) * scaleX),
        y: Math.round((e.clientY - rect.top) * scaleY),
      };
    }

    canvas.addEventListener("mousedown", (e) => {
      const pos = getCanvasCoords(e);
      const active = getActiveLayer();
      if (!active || !active.img) return;

      const bw = canvas.width;
      const sImg = active.img;
      const baseDim = Math.round(bw * 0.25 * active.scale);
      const aspect = sImg.width / Math.max(1, sImg.height);
      const sw = aspect >= 1.0 ? baseDim : Math.round(baseDim * aspect);
      const sh = aspect >= 1.0 ? Math.round(baseDim / aspect) : baseDim;
      const rad = ((active.rotation || 0) * Math.PI) / 180;
      const cos = Math.cos(rad);
      const sin = Math.sin(rad);

      function toWorld(lx, ly) {
        return {
          x: active.x + (lx * cos - ly * sin),
          y: active.y + (lx * sin + ly * cos),
        };
      }

      const rotHandle = toWorld(0, -sh / 2 - 22);
      const distRot = Math.hypot(pos.x - rotHandle.x, pos.y - rotHandle.y);

      if (distRot <= 12) {
        gizmoDragMode = "rotate";
        gizmoInitialAngle = Math.atan2(pos.y - active.y, pos.x - active.x);
        gizmoInitialRot = active.rotation || 0;
        state.bake.isDragging = true;
        canvas.classList.add("grabbing");
        return;
      }

      // Check 4 Corner Scale handles
      const corners = [
        toWorld(-sw / 2, -sh / 2),
        toWorld(sw / 2, -sh / 2),
        toWorld(sw / 2, sh / 2),
        toWorld(-sw / 2, sh / 2),
      ];
      const isCornerHit = corners.some((c) => Math.hypot(pos.x - c.x, pos.y - c.y) <= 10);
      if (isCornerHit) {
        gizmoDragMode = "scale";
        gizmoInitialDist = Math.hypot(pos.x - active.x, pos.y - active.y);
        gizmoInitialScale = active.scale || 1.0;
        state.bake.isDragging = true;
        canvas.classList.add("grabbing");
        return;
      }

      // Hit-test other visible layers to switch selection
      const otherLayers = [...state.bake.layers].reverse();
      for (const layer of otherLayers) {
        if (!layer.visible || !layer.img) continue;
        const lBaseDim = Math.round(bw * 0.25 * layer.scale);
        const lAspect = layer.img.width / Math.max(1, layer.img.height);
        const lsw = lAspect >= 1.0 ? lBaseDim : Math.round(lBaseDim * lAspect);
        const lsh = lAspect >= 1.0 ? Math.round(lBaseDim / lAspect) : lBaseDim;

        if (Math.abs(pos.x - layer.x) <= lsw / 2 && Math.abs(pos.y - layer.y) <= lsh / 2) {
          if (layer.id !== active.id) {
            selectStickerLayer(layer.id);
          }
          break;
        }
      }

      // Default: Move Drag
      gizmoDragMode = "move";
      state.bake.isDragging = true;
      canvas.classList.add("grabbing");
      const curActive = getActiveLayer();
      if (curActive) {
        curActive.x = pos.x;
        curActive.y = pos.y;
        updateActiveLayerUI();
        renderBakeCanvas();
      }
    });

    window.addEventListener("mousemove", (e) => {
      const pos = getCanvasCoords(e);
      cursorCoords = pos;
      drawRulers(canvas.width, canvas.height);

      if (!state.bake.isDragging) return;
      const active = getActiveLayer();
      if (!active) return;

      if (gizmoDragMode === "rotate") {
        const curAngle = Math.atan2(pos.y - active.y, pos.x - active.x);
        const deltaDeg = ((curAngle - gizmoInitialAngle) * 180) / Math.PI;
        let finalDeg = Math.round((gizmoInitialRot + deltaDeg) % 360);
        if (finalDeg < 0) finalDeg += 360;
        active.rotation = finalDeg;
        updateActiveLayerUI();
        renderBakeCanvas();
      } else if (gizmoDragMode === "scale") {
        const curDist = Math.hypot(pos.x - active.x, pos.y - active.y);
        const scaleFactor = curDist / Math.max(10, gizmoInitialDist);
        let newScale = Math.max(0.2, Math.min(2.5, gizmoInitialScale * scaleFactor));
        active.scale = parseFloat(newScale.toFixed(2));
        updateActiveLayerUI();
        renderBakeCanvas();
      } else if (gizmoDragMode === "move") {
        active.x = Math.max(0, Math.min(canvas.width, pos.x));
        active.y = Math.max(0, Math.min(canvas.height, pos.y));
        updateActiveLayerUI();
        renderBakeCanvas();
      }
    });

    window.addEventListener("mouseup", () => {
      if (state.bake.isDragging) {
        state.bake.isDragging = false;
        gizmoDragMode = null;
        canvas.classList.remove("grabbing");
      }
    });

    canvas.addEventListener("wheel", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.05 : -0.05;
      active.scale = Math.max(0.2, Math.min(2.5, active.scale + delta));
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }

  // UV Wireframe Toggle
  if (els.uvWireframeToggleBtn) {
    els.uvWireframeToggleBtn.addEventListener("click", () => {
      showUvWireframe = !showUvWireframe;
      els.uvWireframeToggleBtn.classList.toggle("active", showUvWireframe);
      if (els.uvWireframeLabel) {
        els.uvWireframeLabel.textContent = showUvWireframe ? "UV Wire: ON" : "UV Wire: OFF";
      }
      const skinIdx = els.bakeTargetSkin ? parseInt(els.bakeTargetSkin.value, 10) : 0;
      const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
      const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;
      drawUvWireframe(skinIdx, bw, bh);
    });
  }

  // Rulers Toggle
  if (els.rulersToggleBtn) {
    els.rulersToggleBtn.addEventListener("click", () => {
      showRulers = !showRulers;
      els.rulersToggleBtn.classList.toggle("active", showRulers);
      if (els.rulersLabel) {
        els.rulersLabel.textContent = showRulers ? "Rulers: ON" : "Rulers: OFF";
      }
      if (els.rulerWorkspace) {
        els.rulerWorkspace.style.gridTemplateColumns = showRulers ? "20px 1fr" : "0px 1fr";
        els.rulerWorkspace.style.gridTemplateRows = showRulers ? "20px 1fr" : "0px 1fr";
      }
      const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
      const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;
      drawRulers(bw, bh);
    });
  }

  if (els.bakeTargetSkin) {
    els.bakeTargetSkin.addEventListener("change", () => loadActiveSkinToCanvas());
  }

  if (els.bakeDropZone) {
    els.bakeDropZone.addEventListener("click", () => els.bakeFileInput && els.bakeFileInput.click());
  }

  if (els.bakeFileInput) {
    els.bakeFileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) loadBakeStickerFromFile(e.target.files[0]);
    });
  }

  if (els.bakePickLibraryBtn) {
    els.bakePickLibraryBtn.addEventListener("click", () => {
      eventBus.emit("library:openGeneral", "bake");
    });
  }

  if (els.bakeClearLayersBtn) {
    els.bakeClearLayersBtn.addEventListener("click", () => clearAllLayers());
  }

  if (els.bakePresets) {
    els.bakePresets.querySelectorAll(".preset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        els.bakePresets.querySelectorAll(".preset-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        applyPreset(btn.dataset.preset);
      });
    });
  }

  if (els.bakeScale) {
    els.bakeScale.addEventListener("input", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.scale = parseFloat(e.target.value);
      if (els.bakeScaleVal) els.bakeScaleVal.textContent = `${active.scale.toFixed(2)}x`;
      renderBakeCanvas();
    });
  }

  if (els.bakeRotation) {
    els.bakeRotation.addEventListener("input", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.rotation = parseInt(e.target.value, 10);
      if (els.bakeRotationVal) els.bakeRotationVal.textContent = `${active.rotation}°`;
      renderBakeCanvas();
    });
  }

  if (els.bakeScrape) {
    els.bakeScrape.addEventListener("input", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.scrape = parseInt(e.target.value, 10);
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }

  if (els.bakeOpacity) {
    els.bakeOpacity.addEventListener("input", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.opacity = parseInt(e.target.value, 10) / 100.0;
      if (els.bakeOpacityVal) els.bakeOpacityVal.textContent = `${Math.round(active.opacity * 100)}%`;
      renderBakeCanvas();
    });
  }

  if (els.bakeChromeEffect) {
    els.bakeChromeEffect.addEventListener("change", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.chrome_effect = e.target.value;
      renderBakeCanvas();
    });
  }

  if (els.bakeSliderX) {
    els.bakeSliderX.addEventListener("input", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.x = parseInt(e.target.value, 10);
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeInputX) {
    els.bakeInputX.addEventListener("change", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.x = parseInt(e.target.value, 10);
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeSliderY) {
    els.bakeSliderY.addEventListener("input", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.y = parseInt(e.target.value, 10);
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeInputY) {
    els.bakeInputY.addEventListener("change", (e) => {
      const active = getActiveLayer();
      if (!active) return;
      active.y = parseInt(e.target.value, 10);
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }

  if (els.bakeCenterBtn) {
    els.bakeCenterBtn.addEventListener("click", () => {
      const active = getActiveLayer();
      if (!active) return;
      const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
      const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;
      active.x = Math.round(bw / 2);
      active.y = Math.round(bh / 2);
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }

  const getNudgeStep = () => (state.bake.nudgeStep || 5);
  if (els.bakeNudgeLeft) {
    els.bakeNudgeLeft.addEventListener("click", () => {
      const active = getActiveLayer();
      if (!active) return;
      active.x = Math.max(0, active.x - getNudgeStep());
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeNudgeRight) {
    els.bakeNudgeRight.addEventListener("click", () => {
      const active = getActiveLayer();
      if (!active) return;
      const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
      active.x = Math.min(bw, active.x + getNudgeStep());
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeNudgeUp) {
    els.bakeNudgeUp.addEventListener("click", () => {
      const active = getActiveLayer();
      if (!active) return;
      active.y = Math.max(0, active.y - getNudgeStep());
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeNudgeDown) {
    els.bakeNudgeDown.addEventListener("click", () => {
      const active = getActiveLayer();
      if (!active) return;
      const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;
      active.y = Math.min(bh, active.y + getNudgeStep());
      updateActiveLayerUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeNudgeStepToggle) {
    els.bakeNudgeStepToggle.addEventListener("click", () => {
      state.bake.nudgeStep = state.bake.nudgeStep === 1 ? 5 : (state.bake.nudgeStep === 5 ? 10 : 1);
      els.bakeNudgeStepToggle.textContent = `${state.bake.nudgeStep}px`;
    });
  }

  if (els.bakeApplyBtn) {
    els.bakeApplyBtn.addEventListener("click", () => applyBake());
  }

  if (els.bakeResetBtn) {
    els.bakeResetBtn.addEventListener("click", () => clearAllLayers());
  }

  if (els.syncPwModelsBtn) {
    els.syncPwModelsBtn.addEventListener("click", () => triggerSyncPw());
  }

  if (els.bakeMode3DBtn) {
    els.bakeMode3DBtn.addEventListener("click", () => setBakeViewportMode("3d"));
  }
  if (els.bakeMode2DBtn) {
    els.bakeMode2DBtn.addEventListener("click", () => setBakeViewportMode("2d"));
  }
  if (els.bakeModeSplitBtn) {
    els.bakeModeSplitBtn.addEventListener("click", () => setBakeViewportMode("split"));
  }

  if (els.bake3dDragToggleBtn) {
    els.bake3dDragToggleBtn.addEventListener("click", () => {
      state.bake.allow3dDrag = !state.bake.allow3dDrag;
      els.bake3dDragToggleBtn.classList.toggle("active", state.bake.allow3dDrag);
      if (els.bake3dDragToggleLabel) {
        els.bake3dDragToggleLabel.textContent = `Drag: ${state.bake.allow3dDrag ? "ON" : "OFF"}`;
      }
      showToast(`3D surface sticker dragging: ${state.bake.allow3dDrag ? "ENABLED" : "DISABLED"}`);
    });
  }
}
