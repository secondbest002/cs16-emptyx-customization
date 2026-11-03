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
};

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

  // Draw alignment guidelines ONLY on the interactive 2D editor canvas
  if (state.bake.stickerImg) {
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(6, 182, 212, 0.75)";
    ctx.lineWidth = 1;

    // Horizontal crosshair
    ctx.beginPath();
    ctx.moveTo(0, state.bake.y);
    ctx.lineTo(bw, state.bake.y);
    ctx.stroke();

    // Vertical crosshair
    ctx.beginPath();
    ctx.moveTo(state.bake.x, 0);
    ctx.lineTo(state.bake.x, bh);
    ctx.stroke();

    // Bullseye
    ctx.beginPath();
    ctx.arc(state.bake.x, state.bake.y, 8, 0, 2 * Math.PI);
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();
  }

  updateCoordUI();

  // Emit real-time WYSIWYG texture update to Three.js 3D Viewport
  const skinIdx = els.bakeTargetSkin ? parseInt(els.bakeTargetSkin.value, 10) : null;
  if (skinIdx !== null && !isNaN(skinIdx) && state.bake.baseImg) {
    eventBus.emit("bake:textureUpdated", { textureIndex: skinIdx, canvas: offscreenBakeCanvas });
  }
}

export function updateCoordUI() {
  const rx = Math.round(state.bake.x || 0);
  const ry = Math.round(state.bake.y || 0);
  if (els.bakeCoordX) els.bakeCoordX.textContent = rx;
  if (els.bakeCoordY) els.bakeCoordY.textContent = ry;
  if (els.bakeSliderX && parseInt(els.bakeSliderX.value, 10) !== rx) els.bakeSliderX.value = rx;
  if (els.bakeInputX && parseInt(els.bakeInputX.value, 10) !== rx) els.bakeInputX.value = rx;
  if (els.bakeSliderY && parseInt(els.bakeSliderY.value, 10) !== ry) els.bakeSliderY.value = ry;
  if (els.bakeInputY && parseInt(els.bakeInputY.value, 10) !== ry) els.bakeInputY.value = ry;
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
      state.bake.isDragging = true;
      canvas.classList.add("grabbing");
      const pos = getCanvasCoords(e);
      state.bake.x = pos.x;
      state.bake.y = pos.y;
      renderBakeCanvas();
    });

    window.addEventListener("mousemove", (e) => {
      if (!state.bake.isDragging) return;
      const pos = getCanvasCoords(e);
      state.bake.x = Math.max(0, Math.min(canvas.width, pos.x));
      state.bake.y = Math.max(0, Math.min(canvas.height, pos.y));
      renderBakeCanvas();
    });

    window.addEventListener("mouseup", () => {
      if (state.bake.isDragging) {
        state.bake.isDragging = false;
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
        applyBakePreset(btn.dataset.preset);
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
      const tier = state.bake.scrape === 0 ? "Mint" : `${state.bake.scrape}% Scraped`;
      if (els.bakeScrapeVal) els.bakeScrapeVal.textContent = `${state.bake.scrape}% (${tier})`;
      renderBakeCanvas();
    });
  }

  if (els.bakeChromeEffect) {
    els.bakeChromeEffect.addEventListener("change", (e) => {
      state.bake.chrome_effect = e.target.value;
      state.bake.fx = e.target.value;
      renderBakeCanvas();
    });
  }

  if (els.bakeApplyBtn) {
    els.bakeApplyBtn.addEventListener("click", async () => {
      await applyBake();
    });
  }

  if (els.bakeResetBtn) {
    els.bakeResetBtn.addEventListener("click", () => {
      resetBake();
    });
  }

  if (els.syncPwModelsBtn) {
    els.syncPwModelsBtn.addEventListener("click", () => {
      triggerSyncPw();
    });
  }

  // Precision Position Sliders and Number Inputs
  if (els.bakeSliderX) {
    els.bakeSliderX.addEventListener("input", (e) => {
      state.bake.x = parseInt(e.target.value, 10);
      updateCoordUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeInputX) {
    els.bakeInputX.addEventListener("input", (e) => {
      const v = parseInt(e.target.value, 10);
      if (!isNaN(v)) {
        state.bake.x = v;
        updateCoordUI();
        renderBakeCanvas();
      }
    });
  }
  if (els.bakeSliderY) {
    els.bakeSliderY.addEventListener("input", (e) => {
      state.bake.y = parseInt(e.target.value, 10);
      updateCoordUI();
      renderBakeCanvas();
    });
  }
  if (els.bakeInputY) {
    els.bakeInputY.addEventListener("input", (e) => {
      const v = parseInt(e.target.value, 10);
      if (!isNaN(v)) {
        state.bake.y = v;
        updateCoordUI();
        renderBakeCanvas();
      }
    });
  }

  // Center Sticker Button
  if (els.bakeCenterBtn) {
    els.bakeCenterBtn.addEventListener("click", () => {
      const bw = els.bakeCanvas ? els.bakeCanvas.width : 512;
      const bh = els.bakeCanvas ? els.bakeCanvas.height : 512;
      state.bake.x = Math.round(bw / 2);
      state.bake.y = Math.round(bh / 2);
      updateCoordUI();
      renderBakeCanvas();
    });
  }

  // Precision Nudge D-Pad
  let nudgeStep = 5;
  const stepOptions = [1, 5, 10, 25];
  let stepIdx = 1; // Default 5px

  if (els.bakeNudgeStepToggle) {
    els.bakeNudgeStepToggle.addEventListener("click", () => {
      stepIdx = (stepIdx + 1) % stepOptions.length;
      nudgeStep = stepOptions[stepIdx];
      els.bakeNudgeStepToggle.textContent = `${nudgeStep}px`;
    });
  }

  const applyNudge = (dx, dy) => {
    const bw = els.bakeCanvas ? els.bakeCanvas.width : 512;
    const bh = els.bakeCanvas ? els.bakeCanvas.height : 512;
    state.bake.x = Math.max(0, Math.min(bw, (state.bake.x || 0) + dx));
    state.bake.y = Math.max(0, Math.min(bh, (state.bake.y || 0) + dy));
    updateCoordUI();
    renderBakeCanvas();
  };

  if (els.bakeNudgeLeft) els.bakeNudgeLeft.addEventListener("click", () => applyNudge(-nudgeStep, 0));
  if (els.bakeNudgeRight) els.bakeNudgeRight.addEventListener("click", () => applyNudge(nudgeStep, 0));
  if (els.bakeNudgeUp) els.bakeNudgeUp.addEventListener("click", () => applyNudge(0, -nudgeStep));
  if (els.bakeNudgeDown) els.bakeNudgeDown.addEventListener("click", () => applyNudge(0, nudgeStep));

  // 3D Surface Dragging Toggle
  state.bake.surfaceDragEnabled = true;
  if (els.bake3dDragToggleBtn) {
    els.bake3dDragToggleBtn.addEventListener("click", () => {
      state.bake.surfaceDragEnabled = !(state.bake.surfaceDragEnabled !== false);
      const isEnabled = state.bake.surfaceDragEnabled;
      els.bake3dDragToggleBtn.classList.toggle("active", isEnabled);
      if (els.bake3dDragToggleLabel) {
        els.bake3dDragToggleLabel.textContent = isEnabled ? "3D Drag: ON" : "3D Drag: OFF";
      }
      showToast(isEnabled ? "3D Surface Dragging enabled! Drag directly on the 3D model." : "3D Surface Dragging paused.", "info");
    });
  }

  // Mode Switcher Buttons (3D / 2D / Split)
  if (els.bakeMode3DBtn) {
    els.bakeMode3DBtn.addEventListener("click", () => {
      if (typeof window.setStageMode === "function") window.setStageMode("3d");
    });
  }
  if (els.bakeMode2DBtn) {
    els.bakeMode2DBtn.addEventListener("click", () => {
      if (typeof window.setStageMode === "function") window.setStageMode("2d");
    });
  }
  if (els.bakeModeSplitBtn) {
    els.bakeModeSplitBtn.addEventListener("click", () => {
      if (typeof window.setStageMode === "function") window.setStageMode("split");
    });
  }
}

export async function triggerSyncPw() {
  const wep = state.currentWeapon;
  const team = state.currentTeam;
  showLoader(`Syncing P & W models for ${wep.toUpperCase()}...`);
  try {
    const res = await apiPost("/api/amxx/sync_pw", {
      weapon: wep,
      team: team,
      auto_backup: true,
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

function applyBakePreset(preset) {
  state.bake.preset = preset;
  const bw = els.bakeCanvas ? els.bakeCanvas.width : 512;
  const bh = els.bakeCanvas ? els.bakeCanvas.height : 512;

  if (preset === "silencer") {
    state.bake.x = Math.round(bw * 0.72);
    state.bake.y = Math.round(bh * 0.35);
  } else if (preset === "slide") {
    state.bake.x = Math.round(bw * 0.45);
    state.bake.y = Math.round(bh * 0.35);
  } else if (preset === "wood") {
    state.bake.x = Math.round(bw * 0.35);
    state.bake.y = Math.round(bh * 0.47);
  } else if (preset === "mag") {
    state.bake.x = Math.round(bw * 0.60);
    state.bake.y = Math.round(bh * 0.70);
  } else if (preset === "stock") {
    state.bake.x = Math.round(bw * 0.18);
    state.bake.y = Math.round(bh * 0.45);
  } else {
    state.bake.x = Math.round(bw * 0.45);
    state.bake.y = Math.round(bh * 0.45);
  }
  renderBakeCanvas();
}

function loadBakeStickerFromFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    loadBakeStickerFromUri(e.target.result, null);
  };
  reader.readAsDataURL(file);
}

export function loadBakeStickerFromUri(dataUri, path = null) {
  state.bake.stickerBase64 = dataUri;
  state.bake.stickerPath = path;
  const img = new Image();
  img.onload = () => {
    state.bake.stickerImg = img;
    renderBakeCanvas();
    eventBus.emit("bake:stickerChanged", { previewUri: dataUri, path: path });
    showToast("Sticker loaded onto canvas! Drag to place.", "info");
  };
  img.src = dataUri;
}

export function resetBake() {
  state.bake.stickerImg = null;
  state.bake.stickerBase64 = null;
  state.bake.stickerPath = null;
  renderBakeCanvas();
  eventBus.emit("bake:stickerChanged", { previewUri: null, path: null });
  showToast("Bake sticker cleared from canvas.", "info");
}

async function applyBake() {
  if (!state.bake.stickerBase64 && !state.bake.stickerPath) {
    showToast("Please choose or upload a sticker first.", "error");
    return;
  }

  const skinIdx = els.bakeTargetSkin ? els.bakeTargetSkin.value : null;
  if (!skinIdx) {
    showToast("No target weapon skin texture selected.", "error");
    return;
  }

  showLoader("Baking sticker onto weapon skin...");
  try {
    const payload = {
      team: state.currentTeam,
      weapon: state.currentWeapon,
      texture_index: parseInt(skinIdx, 10),
      preset: state.bake.preset,
      coords: [Math.round(state.bake.x), Math.round(state.bake.y)],
      scale: state.bake.scale,
      rotation: state.bake.rotation,
      scrape: (state.bake.scrape || 0) / 100.0,
      fx: state.bake.fx || "matte",
      chrome_effect: (els.bakeChromeEffect && els.bakeChromeEffect.value !== "matte") ? els.bakeChromeEffect.value : (state.bake.chrome_effect || null),
    };
    if (state.bake.stickerPath) {
      payload.image_path = state.bake.stickerPath;
    } else {
      payload.image_base64 = state.bake.stickerBase64;
    }

    const res = await apiPost("/api/bake", payload);
    showToast(res.message, "success");

    // Clear sticker from memory to avoid double rendering
    state.bake.stickerImg = null;
    state.bake.stickerBase64 = null;
    state.bake.stickerPath = null;
    renderBakeCanvas();
    eventBus.emit("bake:stickerChanged", { previewUri: null, path: null });

    // Record action for Undo/Redo stack
    const tex = state.modelData ? state.modelData.textures.find((t) => t.index === payload.texture_index) : null;
    const texName = tex ? tex.name : "skin";

    const actionTeam = state.currentTeam;
    const actionWeapon = state.currentWeapon;

    eventBus.emit("history:record", {
      description: `Baked Sticker onto ${texName}`,
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
        await apiPost("/api/bake", payload);
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
