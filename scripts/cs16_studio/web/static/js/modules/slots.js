/**
 * modules/slots.js - Dynamic Texture Slots & Slot Sticker Scale Tuner
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

import { state, eventBus } from "../core/state.js";
import { apiPost, showToast, showLoader, hideLoader, elements } from "../core/api.js";

// Dynamic modal elements access
const modalEls = {
  get slotTuneModal() { return document.getElementById("slotTuneModal"); },
  get slotTuneModalTitle() { return document.getElementById("slotTuneModalTitle"); },
  get slotTuneDesc() { return document.getElementById("slotTuneDesc"); },
  get slotTuneModalCloseBtn() { return document.getElementById("slotTuneModalCloseBtn"); },
  get slotTunePickLibBtn() { return document.getElementById("slotTunePickLibBtn"); },
  get slotTuneUploadBtn() { return document.getElementById("slotTuneUploadBtn"); },
  get slotTuneFileInput() { return document.getElementById("slotTuneFileInput"); },
  get slotTuneScale() { return document.getElementById("slotTuneScale"); },
  get slotTuneScaleVal() { return document.getElementById("slotTuneScaleVal"); },
  get slotTuneOffsetX() { return document.getElementById("slotTuneOffsetX"); },
  get slotTuneOffsetXVal() { return document.getElementById("slotTuneOffsetXVal"); },
  get slotTuneOffsetY() { return document.getElementById("slotTuneOffsetY"); },
  get slotTuneOffsetYVal() { return document.getElementById("slotTuneOffsetYVal"); },
  get slotTuneRotation() { return document.getElementById("slotTuneRotation"); },
  get slotTuneRotationVal() { return document.getElementById("slotTuneRotationVal"); },
  get slotTuneScrape() { return document.getElementById("slotTuneScrape"); },
  get slotTuneScrapeVal() { return document.getElementById("slotTuneScrapeVal"); },
  get slotTuneModeFit() { return document.getElementById("slotTuneModeFit"); },
  get slotTuneModeStretch() { return document.getElementById("slotTuneModeStretch"); },
  get slotTuneApplyBtn() { return document.getElementById("slotTuneApplyBtn"); },
  get slotTuneResetBtn() { return document.getElementById("slotTuneResetBtn"); },
  get slotTuneCanvas() { return document.getElementById("slotTuneCanvas"); },
  get slotTuneResBadge() { return document.getElementById("slotTuneResBadge"); },
};

/**
 * Initializes the Slots module
 */
export function initSlotsModule() {
  setupFilterPills();
  setupSlotTuneEventListeners();

  // Listen to model loaded event to refresh cards
  eventBus.on("model:loaded", () => {
    renderTextureCards();
  });
}

function setupFilterPills() {
  const pills = document.querySelectorAll(".slot-filters .filter-pill");
  if (!pills || pills.length === 0) return;
  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      pills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.activeFilter = pill.dataset.filter || "all";
      renderTextureCards();
    });
  });
}

/**
 * Renders all texture cards into the dynamic grid based on active filter
 */
export function renderTextureCards() {
  const grid = elements.textureGrid || document.getElementById("textureGrid");
  const m = state.modelData;
  if (!grid || !m) return;

  grid.innerHTML = "";

  const filtered = m.textures.filter((t) => {
    if (state.activeFilter === "all") return true;
    return t.role === state.activeFilter;
  });

  const countBadge = document.getElementById("slotsCountBadge");
  if (countBadge) {
    countBadge.textContent = `${filtered.length} LOADED`;
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">
        No textures found for filter "${state.activeFilter}".
      </div>
    `;
    return;
  }

  filtered.forEach((tex) => {
    const card = createTextureCard(tex);
    grid.appendChild(card);
  });
}

function createTextureCard(tex) {
  const card = document.createElement("div");
  card.className = "texture-card";
  card.dataset.index = tex.index;

  const pending = state.pendingSlotUpdates[tex.index];
  const isMasked = tex.is_masked;
  const isChrome = Boolean(tex.flags & 0x0002);
  const defaultMode = isMasked ? "fit" : "stretch";
  const activeMode = pending ? pending.mode : defaultMode;

  // Contextual titles and target descriptions
  const formattedIndex = String(tex.index).padStart(2, "0");
  let title = "Texture Slot";
  let targetDesc = "Weapon Model Mesh";
  if (tex.role === "skin") {
    title = "Main Weapon Skin";
    targetDesc = "Mesh Receiver / Handguard / Stock";
  } else if (tex.role === "sticker") {
    title = `Sticker Slot #${tex.index}`;
    targetDesc = "Decal Surface Quad Placement";
  } else if (tex.role === "glove") {
    title = "Glove / Hand Texture";
    targetDesc = "First-Person Player Rig Surface";
  } else if (tex.role === "sleeve") {
    title = "Sleeve / Arm Texture";
    targetDesc = "First-Person Sleeve Mesh Rig";
  } else if (tex.role === "stattrak") {
    title = "StatTrak Digital Module";
    targetDesc = "Kill Counter LED Display Panel";
  }

  card.innerHTML = `
    <!-- Card Header -->
    <div class="card-header">
      <div class="slot-header-left">
        <div class="slot-idx-badge">#${formattedIndex}</div>
        <div class="slot-title-wrap">
          <span class="slot-title-text">${title} <span class="slot-filename">(${tex.name})</span></span>
          <span class="slot-target-desc">Target: ${targetDesc}</span>
        </div>
      </div>
      <div class="slot-header-right">
        <span class="status-pill status-synced">
          <span class="pulse-dot-green"></span> SYNCED
        </span>
        ${isChrome ? `<span class="badge-chrome" title="GoldSrc Specular Chrome Overlay"><svg class="glyph glyph-xs"><use href="#glyph-sparkle"></use></svg> 0x0002 CHROME</span>` : ""}
      </div>
    </div>

    <!-- Dual-Canvas Comparison View -->
    <div class="card-body">
      <div class="dual-canvas-grid">
        <!-- Left: Active in Model -->
        <div class="canvas-half active-half">
          <div class="canvas-half-header">
            <span class="label-with-dot">
              <span class="dot-green"></span> ACTIVE IN MODEL
            </span>
            <span class="canvas-dim">${tex.width}x${tex.height}</span>
          </div>
          <div class="checkerboard-pattern canvas-stage-box">
            <img src="${tex.preview}" alt="${tex.name}" id="curImg_${tex.index}" class="canvas-preview-img">
            <span class="canvas-badge-bottom-right">256c Indexed</span>
          </div>
        </div>

        <!-- Right: New Preview / Buffer -->
        <div class="canvas-half preview-half">
          <div class="canvas-half-header">
            <span class="label-with-dot">
              <span class="dot-cyan"></span> NEW PREVIEW
            </span>
            <span class="canvas-status-tag ${pending ? 'ready' : ''}">${pending ? 'READY' : 'STAGED'}</span>
          </div>
          <div class="checkerboard-pattern canvas-stage-box">
            <img src="${pending ? pending.previewUri : tex.preview}" alt="New Preview" id="newImg_${tex.index}" class="canvas-preview-img" style="${pending ? '' : 'opacity: 0.45; filter: grayscale(70%);'}">
            <span class="canvas-badge-bottom-right buffer-tag">Stage Buffer</span>
          </div>
          <div class="canvas-half-footer">
            <span>Fit: ${activeMode === 'fit' ? 'Smart UV' : 'Stretch UV'}</span>
            <span style="color: var(--accent-amber);">Quantized 8-bit</span>
          </div>
        </div>
      </div>

      <!-- File Ingestion Drop Zone -->
      <div class="drop-zone" id="dropZone_${tex.index}">
        <input type="file" accept="image/*" class="file-input" id="fileInput_${tex.index}">
        <div class="drop-prompt">
          <svg class="glyph glyph-sm text-cyan"><use href="#glyph-upload"></use></svg>
          <span class="drop-text-primary">Drop 8/24-bit BMP or PNG to Replace</span>
        </div>
        <span class="drop-hint-sub">Auto Floyd-Steinberg 256c color reduction for GoldSrc</span>
      </div>

      <!-- Mode Switcher & Quick Tool Buttons -->
      <div class="slot-tools-strip">
        <div class="team-toggle mode-toggle-group">
          <button type="button" class="team-btn mode-btn ${activeMode === 'fit' ? 'active' : ''}" data-idx="${tex.index}" data-mode="fit">Smart Fit</button>
          <button type="button" class="team-btn mode-btn ${activeMode === 'stretch' ? 'active' : ''}" data-idx="${tex.index}" data-mode="stretch">Stretch UV</button>
        </div>

        <div class="slot-quick-btns">
          <button type="button" class="btn-tool quick-lib-btn" id="quickLibBtn_${tex.index}" title="Choose asset from library for this slot">
            <svg class="glyph glyph-xs text-cyan"><use href="#${tex.role === 'skin' ? 'glyph-palette' : tex.role === 'glove' ? 'glyph-glove' : 'glyph-sparkle'}"></use></svg>
            <span>${tex.role === 'skin' ? 'Pick Skin' : tex.role === 'glove' ? 'Pick Glove' : tex.role === 'stattrak' ? 'Customize LED' : 'Pick Sticker'}</span>
          </button>

          ${tex.role === 'sticker' ? `
            <button type="button" class="btn-tool fine-tune-slot-btn" id="fineTuneBtn_${tex.index}" title="Adjust sticker scale, rotation, and offset inside this slot">
              <svg class="glyph glyph-xs text-purple"><use href="#glyph-tune"></use></svg>
              <span>Tune</span>
            </button>
            <button type="button" class="btn-tool move-slot-3d-btn" id="moveSlot3dBtn_${tex.index}" data-slot="${tex.name}" title="Reposition this decal quad by clicking on 3D mesh surface">
              <svg class="glyph glyph-xs text-cyan"><use href="#glyph-pin"></use></svg>
              <span>Move (3D)</span>
            </button>
            <button type="button" class="btn-tool grade-color-btn" id="gradeColorBtn_${tex.index}" title="Open Color Studio for this sticker slot">
              <svg class="glyph glyph-xs text-emerald"><use href="#glyph-palette"></use></svg>
              <span>Color Lab</span>
            </button>
          ` : `
            <button type="button" class="btn-tool grade-color-btn" id="gradeColorBtn_${tex.index}" title="Open Color Studio for this texture">
              <svg class="glyph glyph-xs text-emerald"><use href="#glyph-palette"></use></svg>
              <span>Color Lab</span>
            </button>
          `}
        </div>
      </div>

      <!-- Standout Amber Injection & Revert Action Bar -->
      <div class="slot-action-row">
        <button type="button" class="btn-revert revert-btn" id="revertBtn_${tex.index}" title="Revert slot to original model state">
          <svg class="glyph glyph-xs"><use href="#glyph-restore"></use></svg>
          <span>Revert</span>
        </button>
        <button type="button" class="btn-inject inject-btn" id="injectBtn_${tex.index}" ${pending ? "" : "disabled"} title="Inject and compile texture into active GoldSrc model">
          <svg class="glyph glyph-xs"><use href="#glyph-bolt"></use></svg>
          <span>INJECT TEXTURE</span>
        </button>
      </div>
    </div>
  `;

  setupCardEvents(card, tex);
  return card;
}

function setupCardEvents(card, tex) {
  const fileInput = card.querySelector(`#fileInput_${tex.index}`);
  const dropZone = card.querySelector(`#dropZone_${tex.index}`);
  const injectBtn = card.querySelector(`#injectBtn_${tex.index}`);
  const revertBtn = card.querySelector(`#revertBtn_${tex.index}`);
  const quickLibBtn = card.querySelector(`#quickLibBtn_${tex.index}`);
  const fineTuneBtn = card.querySelector(`#fineTuneBtn_${tex.index}`);
  const gradeColorBtn = card.querySelector(`#gradeColorBtn_${tex.index}`);
  const chromeBtn = card.querySelector(`#chromeBtn_${tex.index}`);
  const modeBtns = card.querySelectorAll(".mode-btn");

  // 3D Viewport Slot Pulse Highlight on card hover
  card.addEventListener("mouseenter", () => {
    eventBus.emit("slot:hover", { textureName: tex.name, textureIndex: tex.index, isHovering: true });
  });
  card.addEventListener("mouseleave", () => {
    eventBus.emit("slot:hover", { textureName: tex.name, textureIndex: tex.index, isHovering: false });
  });

  // Drag & drop
  if (dropZone) {
    ["dragenter", "dragover"].forEach((ename) => {
      dropZone.addEventListener(ename, (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((ename) => {
      dropZone.addEventListener(ename, (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) handleSlotFile(tex, files[0]);
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) handleSlotFile(tex, e.target.files[0]);
    });
  }

  // Mode toggles
  if (modeBtns) {
    modeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        modeBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const mode = btn.dataset.mode;
        if (state.pendingSlotUpdates[tex.index]) {
          state.pendingSlotUpdates[tex.index].mode = mode;
          refreshSlotPreview(tex);
        }
      });
    });
  }

  // Pick from Library
  if (quickLibBtn) {
    quickLibBtn.addEventListener("click", () => {
      eventBus.emit("library:openForSlot", tex);
    });
  }

  // Fine-Tune Button
  if (fineTuneBtn) {
    fineTuneBtn.addEventListener("click", () => {
      openSlotTuneModal(tex);
    });
  }

  // Move in 3D Button
  const moveSlot3dBtn = card.querySelector(".move-slot-3d-btn");
  if (moveSlot3dBtn) {
    moveSlot3dBtn.addEventListener("click", () => {
      const stageBtn = document.getElementById("stageMode3DBtn") || document.querySelector('.nav-tab[data-tab="viewport3d"]');
      if (stageBtn) stageBtn.click();
      eventBus.emit("3d:activateMoveSlot", { slotName: tex.name, slotIndex: tex.index });
    });
  }

  // Grade Color Button
  if (gradeColorBtn) {
    gradeColorBtn.addEventListener("click", () => {
      eventBus.emit("color:selectTexture", tex.index);
      const colorTab = document.getElementById("dockTabColor") || document.querySelector('.nav-tab[data-tab="color"]');
      if (colorTab) colorTab.click();
    });
  }

  // Chrome Specular Studio Shortcut (if present)
  if (chromeBtn) {
    chromeBtn.addEventListener("click", () => {
      const finishesTab = document.getElementById("dockTabFinishes");
      if (finishesTab) finishesTab.click();
      const pillBtn = document.querySelector('.pill-switch-btn[data-subpane="chrome"]');
      if (pillBtn) pillBtn.click();
    });
  }

  // Inject Texture
  if (injectBtn) {
    injectBtn.addEventListener("click", async () => {
      await injectPendingSlot(tex);
    });
  }

  // Revert Slot
  if (revertBtn) {
    revertBtn.addEventListener("click", async () => {
      await revertSlot(tex);
    });
  }
}

function handleSlotFile(tex, file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUri = e.target.result;
    state.pendingSlotUpdates[tex.index] = {
      file,
      base64: dataUri,
      previewUri: dataUri,
      mode: tex.is_masked ? "fit" : "stretch",
      scale: 1.0,
    };
    refreshSlotPreview(tex);
  };
  reader.readAsDataURL(file);
}

export async function refreshSlotPreview(tex) {
  const pending = state.pendingSlotUpdates[tex.index];
  if (!pending) return;

  try {
    const res = await apiPost("/api/preview", {
      image_base64: pending.base64,
      width: tex.width,
      height: tex.height,
      is_masked: tex.is_masked,
      mode: pending.mode,
      scale: pending.scale,
    });

    pending.previewUri = res.preview;
    const newImg = document.getElementById(`newImg_${tex.index}`);
    if (newImg) {
      newImg.src = res.preview;
      newImg.style.opacity = "1";
      newImg.style.filter = "none";
    }

    const injectBtn = document.getElementById(`injectBtn_${tex.index}`);
    if (injectBtn) injectBtn.disabled = false;

    // Real-time 3D Viewport synchronization
    eventBus.emit("slot:textureUpdated", { textureIndex: tex.index, previewUri: res.preview });
  } catch (err) {
    showToast(`Preview failed: ${err.message}`, "error");
  }
}

async function injectPendingSlot(tex) {
  const pending = state.pendingSlotUpdates[tex.index];
  if (!pending) return;

  showLoader(`Injecting texture into ${tex.name}...`);
  try {
    const payload = {
      team: state.currentTeam,
      weapon: state.currentWeapon,
      texture_index: tex.index,
      texture_name: tex.name,
      mode: pending.mode,
      scale: pending.scale,
    };

    if (pending.image_path) {
      payload.image_path = pending.image_path;
    } else {
      payload.image_base64 = pending.base64;
    }

    const res = await apiPost("/api/inject", payload);
    showToast(res.message, "success");

    const actionTeam = state.currentTeam;
    const actionWeapon = state.currentWeapon;

    // Push action to undo stack
    eventBus.emit("history:record", {
      description: `Injected into ${tex.name}`,
      team: actionTeam,
      weapon: actionWeapon,
      undo: async () => {
        await apiPost("/api/revert", {
          team: actionTeam,
          weapon: actionWeapon,
          texture_index: tex.index,
          texture_name: tex.name,
        });
      },
      redo: async () => {
        await apiPost("/api/inject", payload);
      },
    });

    const curImg = document.getElementById(`curImg_${tex.index}`);
    if (curImg) curImg.src = res.preview;

    delete state.pendingSlotUpdates[tex.index];
    const injectBtn = document.getElementById(`injectBtn_${tex.index}`);
    if (injectBtn) injectBtn.disabled = true;

    eventBus.emit("model:reloadRequest");

    // Check if injected slot is a weapon skin (p/w sync candidate)
    if (tex.role === "skin") {
      eventBus.emit("pw:promptSync", {
        weapon: actionWeapon,
        team: actionTeam,
        textureName: tex.name,
      });
    }
  } catch (err) {
    showToast(`Injection failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function revertSlot(tex) {
  if (!confirm(`Revert "${tex.name}" back to its previous snapshot?`)) {
    return;
  }

  showLoader(`Reverting ${tex.name}...`);
  try {
    const res = await apiPost("/api/revert", {
      team: state.currentTeam,
      weapon: state.currentWeapon,
      texture_index: tex.index,
      texture_name: tex.name,
    });

    showToast(res.message, "success");
    eventBus.emit("model:reloadRequest");
  } catch (err) {
    showToast(`Revert failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function toggleChromeShimmer(tex) {
  const actionTeam = state.currentTeam;
  const actionWeapon = state.currentWeapon;
  const prevChrome = Boolean(tex.flags & 0x0002);

  showLoader(`Toggling Chrome Reflection on ${tex.name}...`);
  try {
    const res = await apiPost("/api/toggle_chrome", {
      team: actionTeam,
      weapon: actionWeapon,
      texture_index: tex.index,
    });
    showToast(res.message, "success");

    eventBus.emit("history:record", {
      description: `Toggle Chrome on ${tex.name}`,
      team: actionTeam,
      weapon: actionWeapon,
      undo: async () => {
        await apiPost("/api/toggle_chrome", {
          team: actionTeam,
          weapon: actionWeapon,
          texture_index: tex.index,
          enable: prevChrome,
        });
      },
      redo: async () => {
        await apiPost("/api/toggle_chrome", {
          team: actionTeam,
          weapon: actionWeapon,
          texture_index: tex.index,
          enable: !prevChrome,
        });
      },
    });

    eventBus.emit("model:reloadRequest");
  } catch (err) {
    showToast(`Chrome toggle failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

// ==========================================
// SLOT TUNER MODAL
// ==========================================

export function openSlotTuneModal(tex) {
  state.slotTune.texture = tex;
  state.slotTune.scale = 1.0;
  state.slotTune.offsetX = 0;
  state.slotTune.offsetY = 0;
  state.slotTune.rotation = 0;
  state.slotTune.mode = "fit";

  modalEls.slotTuneModalTitle.textContent = `Sticker Slot Fine-Tuner: "${tex.name}"`;
  modalEls.slotTuneDesc.textContent = `Adjust sticker placement inside the native ${tex.width}x${tex.height} slot resolution.`;
  modalEls.slotTuneResBadge.textContent = `${tex.width}x${tex.height} px`;

  // Reset sliders
  modalEls.slotTuneScale.value = 1.0;
  modalEls.slotTuneScaleVal.textContent = "1.00x";
  modalEls.slotTuneOffsetX.value = 0;
  modalEls.slotTuneOffsetXVal.textContent = "0px";
  modalEls.slotTuneOffsetY.value = 0;
  modalEls.slotTuneOffsetYVal.textContent = "0px";
  modalEls.slotTuneRotation.value = 0;
  modalEls.slotTuneRotationVal.textContent = "0°";
  state.slotTune.scrape = 0;
  if (modalEls.slotTuneScrape) modalEls.slotTuneScrape.value = 0;
  if (modalEls.slotTuneScrapeVal) modalEls.slotTuneScrapeVal.textContent = "0% (Mint)";

  modalEls.slotTuneCanvas.width = tex.width;
  modalEls.slotTuneCanvas.height = tex.height;

  const img = new Image();
  img.onload = () => {
    state.slotTune.stickerImg = img;
    state.slotTune.stickerDataUri = tex.preview;
    renderSlotTuneCanvas();
  };
  img.src = tex.preview;

  modalEls.slotTuneModal.classList.remove("hidden");
}

function setupSlotTuneEventListeners() {
  if (modalEls.slotTuneModalCloseBtn) {
    modalEls.slotTuneModalCloseBtn.addEventListener("click", () => {
      if (modalEls.slotTuneModal) modalEls.slotTuneModal.classList.add("hidden");
    });
  }

  if (modalEls.slotTuneUploadBtn) {
    modalEls.slotTuneUploadBtn.addEventListener("click", () => {
      if (modalEls.slotTuneFileInput) modalEls.slotTuneFileInput.click();
    });
  }

  if (modalEls.slotTuneFileInput) {
    modalEls.slotTuneFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (re) => {
          const dataUri = re.target.result;
          state.slotTune.stickerDataUri = dataUri;
          const img = new Image();
          img.onload = () => {
            state.slotTune.stickerImg = img;
            renderSlotTuneCanvas();
          };
          img.src = dataUri;
        };
        reader.readAsDataURL(file);
      }
    });
  }

  if (modalEls.slotTunePickLibBtn) {
    modalEls.slotTunePickLibBtn.addEventListener("click", () => {
      eventBus.emit("library:openGeneral", "slotTune");
    });
  }

  if (modalEls.slotTuneScale) {
    modalEls.slotTuneScale.addEventListener("input", (e) => {
      state.slotTune.scale = parseFloat(e.target.value);
      if (modalEls.slotTuneScaleVal) modalEls.slotTuneScaleVal.textContent = `${state.slotTune.scale.toFixed(2)}x`;
      renderSlotTuneCanvas();
    });
  }

  if (modalEls.slotTuneOffsetX) {
    modalEls.slotTuneOffsetX.addEventListener("input", (e) => {
      state.slotTune.offsetX = parseInt(e.target.value, 10);
      if (modalEls.slotTuneOffsetXVal) modalEls.slotTuneOffsetXVal.textContent = `${state.slotTune.offsetX}px`;
      renderSlotTuneCanvas();
    });
  }

  if (modalEls.slotTuneOffsetY) {
    modalEls.slotTuneOffsetY.addEventListener("input", (e) => {
      state.slotTune.offsetY = parseInt(e.target.value, 10);
      if (modalEls.slotTuneOffsetYVal) modalEls.slotTuneOffsetYVal.textContent = `${state.slotTune.offsetY}px`;
      renderSlotTuneCanvas();
    });
  }

  if (modalEls.slotTuneRotation) {
    modalEls.slotTuneRotation.addEventListener("input", (e) => {
      state.slotTune.rotation = parseInt(e.target.value, 10);
      if (modalEls.slotTuneRotationVal) modalEls.slotTuneRotationVal.textContent = `${state.slotTune.rotation}°`;
      renderSlotTuneCanvas();
    });
  }

  if (modalEls.slotTuneScrape) {
    modalEls.slotTuneScrape.addEventListener("input", (e) => {
      state.slotTune.scrape = parseInt(e.target.value, 10);
      const tier = state.slotTune.scrape === 0 ? "Mint" : `${state.slotTune.scrape}% Scraped`;
      if (modalEls.slotTuneScrapeVal) modalEls.slotTuneScrapeVal.textContent = `${state.slotTune.scrape}% (${tier})`;
    });
  }

  if (modalEls.slotTuneModeFit) {
    modalEls.slotTuneModeFit.addEventListener("click", () => {
      if (modalEls.slotTuneModeFit) modalEls.slotTuneModeFit.classList.add("active");
      if (modalEls.slotTuneModeStretch) modalEls.slotTuneModeStretch.classList.remove("active");
      state.slotTune.mode = "fit";
      renderSlotTuneCanvas();
    });
  }

  if (modalEls.slotTuneModeStretch) {
    modalEls.slotTuneModeStretch.addEventListener("click", () => {
      if (modalEls.slotTuneModeStretch) modalEls.slotTuneModeStretch.classList.add("active");
      if (modalEls.slotTuneModeFit) modalEls.slotTuneModeFit.classList.remove("active");
      state.slotTune.mode = "stretch";
      renderSlotTuneCanvas();
    });
  }

  if (modalEls.slotTuneResetBtn) {
    modalEls.slotTuneResetBtn.addEventListener("click", () => {
      state.slotTune.scale = 1.0;
      state.slotTune.offsetX = 0;
      state.slotTune.offsetY = 0;
      state.slotTune.rotation = 0;
      state.slotTune.scrape = 0;
      if (modalEls.slotTuneScale) modalEls.slotTuneScale.value = 1.0;
      if (modalEls.slotTuneScaleVal) modalEls.slotTuneScaleVal.textContent = "1.00x";
      if (modalEls.slotTuneOffsetX) modalEls.slotTuneOffsetX.value = 0;
      if (modalEls.slotTuneOffsetXVal) modalEls.slotTuneOffsetXVal.textContent = "0px";
      if (modalEls.slotTuneOffsetY) modalEls.slotTuneOffsetY.value = 0;
      if (modalEls.slotTuneOffsetYVal) modalEls.slotTuneOffsetYVal.textContent = "0px";
      if (modalEls.slotTuneRotation) modalEls.slotTuneRotation.value = 0;
      if (modalEls.slotTuneRotationVal) modalEls.slotTuneRotationVal.textContent = "0°";
      if (modalEls.slotTuneScrape) modalEls.slotTuneScrape.value = 0;
      if (modalEls.slotTuneScrapeVal) modalEls.slotTuneScrapeVal.textContent = "0% (Mint)";
      renderSlotTuneCanvas();
    });
  }

  if (modalEls.slotTuneApplyBtn) {
    modalEls.slotTuneApplyBtn.addEventListener("click", async () => {
      await applySlotTuneToModel();
    });
  }
}

export function renderSlotTuneCanvas() {
  const canvas = modalEls.slotTuneCanvas;
  const sImg = state.slotTune.stickerImg;
  if (!canvas || !sImg) return;

  const ctx = canvas.getContext("2d");
  const tw = canvas.width;
  const th = canvas.height;

  ctx.clearRect(0, 0, tw, th);

  let sw, sh;
  if (state.slotTune.mode === "stretch") {
    sw = Math.max(4, Math.round(tw * state.slotTune.scale));
    sh = Math.max(4, Math.round(th * state.slotTune.scale));
  } else {
    const fitScale = Math.min(tw / sImg.width, th / sImg.height);
    const appliedScale = fitScale * state.slotTune.scale;
    sw = Math.max(4, Math.round(sImg.width * appliedScale));
    sh = Math.max(4, Math.round(sImg.height * appliedScale));
  }

  const cx = tw / 2 + state.slotTune.offsetX;
  const cy = th / 2 + state.slotTune.offsetY;

  ctx.save();
  ctx.translate(cx, cy);
  if (state.slotTune.rotation !== 0) {
    ctx.rotate((state.slotTune.rotation * Math.PI) / 180);
  }
  ctx.drawImage(sImg, -sw / 2, -sh / 2, sw, sh);

  ctx.strokeStyle = "rgba(6, 182, 212, 0.6)";
  ctx.lineWidth = 1;
  ctx.strokeRect(-sw / 2, -sh / 2, sw, sh);
  ctx.restore();
}

async function applySlotTuneToModel() {
  const tex = state.slotTune.texture;
  if (!tex || !state.slotTune.stickerDataUri) return;

  showLoader(`Quantizing and injecting tuned sticker into slot ${tex.name}...`);
  try {
    const payload = {
      team: state.currentTeam,
      weapon: state.currentWeapon,
      texture_index: tex.index,
      image_base64: state.slotTune.stickerDataUri,
      scale: state.slotTune.scale,
      offset_x: state.slotTune.offsetX,
      offset_y: state.slotTune.offsetY,
      rotation: state.slotTune.rotation,
      mode: state.slotTune.mode,
      scrape: (state.slotTune.scrape || 0) / 100.0,
    };

    const res = await apiPost("/api/slot_tune_apply", payload);
    showToast(res.message, "success");

    const actionTeam = state.currentTeam;
    const actionWeapon = state.currentWeapon;

    eventBus.emit("history:record", {
      description: `Tuned Sticker on ${tex.name}`,
      team: actionTeam,
      weapon: actionWeapon,
      undo: async () => {
        await apiPost("/api/revert", {
          team: actionTeam,
          weapon: actionWeapon,
          texture_index: tex.index,
          texture_name: tex.name,
        });
      },
      redo: async () => {
        await apiPost("/api/slot_tune_apply", payload);
      },
    });

    modalEls.slotTuneModal.classList.add("hidden");
    eventBus.emit("model:reloadRequest");
  } catch (err) {
    showToast(`Slot tune failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}
