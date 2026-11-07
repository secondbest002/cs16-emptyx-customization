/**
 * modules/bake.js - Interactive WYSIWYG Bake Sticker Canvas
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

import { state, eventBus } from "../core/state.js";
import { apiPost, showToast, showLoader, hideLoader } from "../core/api.js";

const els = {
  get bakeTargetSkin() { return document.getElementById("bakeTargetSkin"); },
  get bakePickLibraryBtn() { return document.getElementById("bakePickLibraryBtn"); },
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
  get bakeChromeEffect() { return document.getElementById("bakeChromeEffect"); },
  get bakeApplyBtn() { return document.getElementById("bakeApplyBtn"); },
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

export function initBakeModule() {
  setupEventListeners();

  eventBus.on("model:loaded", () => {
    setupBakeTab();
  });

  eventBus.on("bake:loadSticker", ({ previewUri, path }) => {
    loadBakeStickerFromUri(previewUri, path);
  });

  eventBus.on("amxx:requestSyncPw", () => {
    triggerSyncPw();
  });

  // Listen to 3D surface dragging coordinates from viewer3d.js
  eventBus.on("bake:coordsChanged", ({ x, y }) => {
    state.bake.x = x;
    state.bake.y = y;
    updateCoordUI();
    renderBakeCanvas();
  });
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

    if (!state.bake.x || !state.bake.y) {
      state.bake.x = Math.round(img.width * 0.45);
      state.bake.y = Math.round(img.height * 0.45);
    }
    const w = img.width || 512;
    const h = img.height || 512;
    if (els.bakeSliderX) { els.bakeSliderX.min = 0; els.bakeSliderX.max = w; }
    if (els.bakeInputX) { els.bakeInputX.min = 0; els.bakeInputX.max = w; }
    if (els.bakeSliderY) { els.bakeSliderY.min = 0; els.bakeSliderY.max = h; }
    if (els.bakeInputY) { els.bakeInputY.min = 0; els.bakeInputY.max = h; }
    updateCoordUI();
    renderBakeCanvas();
    drawUvWireframe(parseInt(skinIdx, 10), img.width, img.height);
    renderPaletteStrip(tex.palette, tex.is_masked);
  };
  img.src = tex.preview;
}

let offscreenBakeCanvas = null;

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

  // Draw weapon body skin base onto offscreen canvas
  if (state.bake.baseImg) {
    offCtx.drawImage(state.bake.baseImg, 0, 0, bw, bh);
  }

  // Draw sticker overlay if loaded onto offscreen canvas
  if (state.bake.stickerImg) {
    const sImg = state.bake.stickerImg;
    const baseDim = Math.round(bw * 0.25 * state.bake.scale);
    const aspect = sImg.width / Math.max(1, sImg.height);
    const sw = aspect >= 1.0 ? baseDim : Math.round(baseDim * aspect);
    const sh = aspect >= 1.0 ? Math.round(baseDim / aspect) : baseDim;

    offCtx.save();
    offCtx.translate(state.bake.x, state.bake.y);
    if (state.bake.rotation !== 0) {
      offCtx.rotate((state.bake.rotation * Math.PI) / 180);
    }
    offCtx.drawImage(sImg, -sw / 2, -sh / 2, sw, sh);

    // Directive 1: Real-time foil/chrome sheen rendering on sticker
    const effect = state.bake.chrome_effect || (els.bakeChromeEffect ? els.bakeChromeEffect.value : "matte");
    if (effect && effect !== "matte" && effect !== "none") {
      offCtx.save();
      offCtx.globalCompositeOperation = "color-dodge";
      offCtx.globalAlpha = 0.35;
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
  }

  // Render clean composite onto 2D canvas
  ctx.clearRect(0, 0, bw, bh);
  ctx.drawImage(offscreenBakeCanvas, 0, 0);

  // Screen 3: Interactive Quad Gizmo with Rotation Handle & Scale Anchors
  if (state.bake.stickerImg) {
    const sImg = state.bake.stickerImg;
    const baseDim = Math.round(bw * 0.25 * state.bake.scale);
    const aspect = sImg.width / Math.max(1, sImg.height);
    const sw = aspect >= 1.0 ? baseDim : Math.round(baseDim * aspect);
    const sh = aspect >= 1.0 ? Math.round(baseDim / aspect) : baseDim;
    const rad = ((state.bake.rotation || 0) * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);

    function toWorld(lx, ly) {
      return {
        x: state.bake.x + (lx * cos - ly * sin),
        y: state.bake.y + (lx * sin + ly * cos),
      };
    }

    const cTL = toWorld(-sw / 2, -sh / 2);
    const cTR = toWorld(sw / 2, -sh / 2);
    const cBR = toWorld(sw / 2, sh / 2);
    const cBL = toWorld(-sw / 2, sh / 2);
    const rotArmBase = toWorld(0, -sh / 2);
    const rotHandle = toWorld(0, -sh / 2 - 22);

    ctx.save();

    // 1. Alignment Crosshair Guides
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, state.bake.y); ctx.lineTo(bw, state.bake.y);
    ctx.moveTo(state.bake.x, 0); ctx.lineTo(state.bake.x, bh);
    ctx.stroke();

    // 2. High-precision Bounding Box Quad
    ctx.setLineDash([5, 3]);
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cTL.x, cTL.y);
    ctx.lineTo(cTR.x, cTR.y);
    ctx.lineTo(cBR.x, cBR.y);
    ctx.lineTo(cBL.x, cBL.y);
    ctx.closePath();
    ctx.stroke();

    // 3. Rotation Arm & Handle
    ctx.setLineDash([]);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(rotArmBase.x, rotArmBase.y);
    ctx.lineTo(rotHandle.x, rotHandle.y);
    ctx.stroke();

    ctx.fillStyle = "#38bdf8";
    ctx.beginPath();
    ctx.arc(rotHandle.x, rotHandle.y, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 4. 4 Corner Scale Anchor Pips (Squares)
    const corners = [cTL, cTR, cBR, cBL];
    corners.forEach((c) => {
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(c.x - 4, c.y - 4, 8, 8);
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(c.x - 4, c.y - 4, 8, 8);
    });

    // 5. Center Pivot Amber Bullseye
    ctx.beginPath();
    ctx.arc(state.bake.x, state.bake.y, 4, 0, 2 * Math.PI);
    ctx.fillStyle = "#f59e0b";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.restore();
  }

  updateCoordUI();
  drawRulers(bw, bh);

  // Emit real-time WYSIWYG texture update to Three.js 3D Viewport
  const skinIdx = els.bakeTargetSkin ? parseInt(els.bakeTargetSkin.value, 10) : null;
  if (skinIdx !== null && !isNaN(skinIdx) && state.bake.baseImg) {
    eventBus.emit("bake:textureUpdated", { textureIndex: skinIdx, canvas: offscreenBakeCanvas });
  }
}

// Draws the 2D Coordinate Rulers
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

  // Draw cursor guide on H ruler
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

  // Draw cursor guide on V ruler
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

// Draws the 3D Mesh Polygon UV Wireframe Overlay
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

// Renders the Floyd-Steinberg 256-Color Palette Strip
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

export function updateCoordUI() {
  const rx = Math.round(state.bake.x || 0);
  const ry = Math.round(state.bake.y || 0);
  const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
  const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;

  if (els.bakeCoordX) els.bakeCoordX.textContent = rx;
  if (els.bakeCoordY) els.bakeCoordY.textContent = ry;
  if (els.bakeSliderX && parseInt(els.bakeSliderX.value, 10) !== rx) els.bakeSliderX.value = rx;
  if (els.bakeInputX && parseInt(els.bakeInputX.value, 10) !== rx) els.bakeInputX.value = rx;
  if (els.bakeSliderY && parseInt(els.bakeSliderY.value, 10) !== ry) els.bakeSliderY.value = ry;
  if (els.bakeInputY && parseInt(els.bakeInputY.value, 10) !== ry) els.bakeInputY.value = ry;

  // Screen 3: Telemetry HUD readout bar
  if (els.telemCoords) els.telemCoords.textContent = `X: ${rx}, Y: ${ry}`;
  if (els.telemUvNorm) els.telemUvNorm.textContent = `(u: ${(rx / bw).toFixed(3)}, v: ${(ry / bh).toFixed(3)})`;
  if (els.telemScaleVal) els.telemScaleVal.textContent = `${(state.bake.scale || 1.0).toFixed(2)}x`;
  if (els.telemRotVal) els.telemRotVal.textContent = `${(state.bake.rotation || 0).toFixed(1)}°`;
}

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
      if (!state.bake.stickerImg) return;

      const bw = canvas.width;
      const sImg = state.bake.stickerImg;
      const baseDim = Math.round(bw * 0.25 * state.bake.scale);
      const aspect = sImg.width / Math.max(1, sImg.height);
      const sw = aspect >= 1.0 ? baseDim : Math.round(baseDim * aspect);
      const sh = aspect >= 1.0 ? Math.round(baseDim / aspect) : baseDim;
      const rad = ((state.bake.rotation || 0) * Math.PI) / 180;
      const cos = Math.cos(rad);
      const sin = Math.sin(rad);

      function toWorld(lx, ly) {
        return {
          x: state.bake.x + (lx * cos - ly * sin),
          y: state.bake.y + (lx * sin + ly * cos),
        };
      }

      const rotHandle = toWorld(0, -sh / 2 - 22);
      const distRot = Math.hypot(pos.x - rotHandle.x, pos.y - rotHandle.y);

      if (distRot <= 12) {
        // Rotation Drag
        gizmoDragMode = "rotate";
        gizmoInitialAngle = Math.atan2(pos.y - state.bake.y, pos.x - state.bake.x);
        gizmoInitialRot = state.bake.rotation || 0;
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
        gizmoInitialDist = Math.hypot(pos.x - state.bake.x, pos.y - state.bake.y);
        gizmoInitialScale = state.bake.scale || 1.0;
        state.bake.isDragging = true;
        canvas.classList.add("grabbing");
        return;
      }

      // Default: Move Drag
      gizmoDragMode = "move";
      state.bake.isDragging = true;
      canvas.classList.add("grabbing");
      state.bake.x = pos.x;
      state.bake.y = pos.y;
      renderBakeCanvas();
    });

    window.addEventListener("mousemove", (e) => {
      const pos = getCanvasCoords(e);
      cursorCoords = pos;
      drawRulers(canvas.width, canvas.height);

      if (!state.bake.isDragging) return;

      if (gizmoDragMode === "rotate") {
        const curAngle = Math.atan2(pos.y - state.bake.y, pos.x - state.bake.x);
        const deltaDeg = ((curAngle - gizmoInitialAngle) * 180) / Math.PI;
        let finalDeg = Math.round((gizmoInitialRot + deltaDeg) % 360);
        if (finalDeg < 0) finalDeg += 360;
        state.bake.rotation = finalDeg;
        if (els.bakeRotation) els.bakeRotation.value = finalDeg;
        if (els.bakeRotationVal) els.bakeRotationVal.textContent = `${finalDeg}°`;
        renderBakeCanvas();
      } else if (gizmoDragMode === "scale") {
        const curDist = Math.hypot(pos.x - state.bake.x, pos.y - state.bake.y);
        const scaleFactor = curDist / Math.max(10, gizmoInitialDist);
        let newScale = Math.max(0.2, Math.min(2.5, gizmoInitialScale * scaleFactor));
        state.bake.scale = parseFloat(newScale.toFixed(2));
        if (els.bakeScale) els.bakeScale.value = state.bake.scale;
        if (els.bakeScaleVal) els.bakeScaleVal.textContent = `${state.bake.scale.toFixed(2)}x`;
        renderBakeCanvas();
      } else if (gizmoDragMode === "move") {
        state.bake.x = Math.max(0, Math.min(canvas.width, pos.x));
        state.bake.y = Math.max(0, Math.min(canvas.height, pos.y));
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
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.05 : -0.05;
      state.bake.scale = Math.max(0.2, Math.min(2.5, state.bake.scale + delta));
      if (els.bakeScale) els.bakeScale.value = state.bake.scale;
      if (els.bakeScaleVal) els.bakeScaleVal.textContent = `${state.bake.scale.toFixed(2)}x`;
      renderBakeCanvas();
    });
  }

  // UV Wireframe Toggle Event
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

  // Rulers Toggle Event
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
      state.bake.scale = parseFloat(e.target.value);
      if (els.bakeScaleVal) els.bakeScaleVal.textContent = `${state.bake.scale.toFixed(2)}x`;
      renderBakeCanvas();
    });
  }

  if (els.bakeRotation) {
    els.bakeRotation.addEventListener("input", (e) => {
      state.bake.rotation = parseInt(e.target.value, 10);
      if (els.bakeRotationVal) els.bakeRotationVal.textContent = `${state.bake.rotation}°`;
      renderBakeCanvas();
    });
  }

  if (els.bakeScrape) {
    els.bakeScrape.addEventListener("input", (e) => {
      state.bake.scrape = parseInt(e.target.value, 10);
      if (els.bakeScrapeVal) {
        const val = state.bake.scrape;
        let label = "Mint (0%)";
        if (val > 75) label = `Battle-Scarred (${val}%)`;
        else if (val > 45) label = `Well-Worn (${val}%)`;
        else if (val > 20) label = `Field-Tested (${val}%)`;
        else if (val > 0) label = `Light Wear (${val}%)`;
        els.bakeScrapeVal.textContent = label;
      }
      renderBakeCanvas();
    });
  }

  if (els.bakeChromeEffect) {
    els.bakeChromeEffect.addEventListener("change", (e) => {
      state.bake.chrome_effect = e.target.value;
      renderBakeCanvas();
    });
  }

  if (els.bakeSliderX) {
    els.bakeSliderX.addEventListener("input", (e) => {
      state.bake.x = parseInt(e.target.value, 10);
      renderBakeCanvas();
    });
  }
  if (els.bakeInputX) {
    els.bakeInputX.addEventListener("change", (e) => {
      state.bake.x = parseInt(e.target.value, 10);
      renderBakeCanvas();
    });
  }
  if (els.bakeSliderY) {
    els.bakeSliderY.addEventListener("input", (e) => {
      state.bake.y = parseInt(e.target.value, 10);
      renderBakeCanvas();
    });
  }
  if (els.bakeInputY) {
    els.bakeInputY.addEventListener("change", (e) => {
      state.bake.y = parseInt(e.target.value, 10);
      renderBakeCanvas();
    });
  }

  if (els.bakeCenterBtn) {
    els.bakeCenterBtn.addEventListener("click", () => {
      const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
      const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;
      state.bake.x = Math.round(bw / 2);
      state.bake.y = Math.round(bh / 2);
      renderBakeCanvas();
    });
  }

  const getNudgeStep = () => (state.bake.nudgeStep || 5);
  if (els.bakeNudgeLeft) {
    els.bakeNudgeLeft.addEventListener("click", () => {
      state.bake.x = Math.max(0, state.bake.x - getNudgeStep());
      renderBakeCanvas();
    });
  }
  if (els.bakeNudgeRight) {
    els.bakeNudgeRight.addEventListener("click", () => {
      const bw = (els.bakeCanvas && els.bakeCanvas.width) || 512;
      state.bake.x = Math.min(bw, state.bake.x + getNudgeStep());
      renderBakeCanvas();
    });
  }
  if (els.bakeNudgeUp) {
    els.bakeNudgeUp.addEventListener("click", () => {
      state.bake.y = Math.max(0, state.bake.y - getNudgeStep());
      renderBakeCanvas();
    });
  }
  if (els.bakeNudgeDown) {
    els.bakeNudgeDown.addEventListener("click", () => {
      const bh = (els.bakeCanvas && els.bakeCanvas.height) || 512;
      state.bake.y = Math.min(bh, state.bake.y + getNudgeStep());
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
    els.bakeResetBtn.addEventListener("click", () => resetBake());
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
