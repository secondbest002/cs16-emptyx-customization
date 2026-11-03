/**
 * modules/pro_tools.js - Pro Tools Suite (StatTrak, Glove Studio & Batch Injector, Wear Simulator)
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

import { state, eventBus } from "../core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader, elements } from "../core/api.js";

const proEls = {
  get openProToolsBtn() { return document.getElementById("openProToolsBtn"); },
  get proToolsModal() { return document.getElementById("proToolsModal"); },
  get proToolsModalCloseBtn() { return document.getElementById("proToolsModalCloseBtn"); },
  get proTabBtns() { return document.querySelectorAll(".pro-tab-btn"); },
  get proPanes() { return document.querySelectorAll(".pro-pane"); },

  // StatTrak
  get stColorButtons() { return document.getElementById("stColorButtons"); },
  get stNumberInput() { return document.getElementById("stNumberInput"); },
  get stApplyBtn() { return document.getElementById("stApplyBtn"); },
  get stResetBtn() { return document.getElementById("stResetBtn"); },
  get stTargetTextureSelect() { return document.getElementById("stTargetTextureSelect"); },
  get stTargetTextureGroup() { return document.getElementById("stTargetTextureGroup"); },
  get stLiveLedPreview() { return document.getElementById("stLiveLedPreview"); },
  get stPreviewDigits() { return document.getElementById("stPreviewDigits"); },

  // Glove Studio - Mode Switcher & 3D Sleeve Transplant
  get gloveModeImageBtn() { return document.getElementById("gloveModeImageBtn"); },
  get gloveModeTransferBtn() { return document.getElementById("gloveModeTransferBtn"); },
  get gloveModeSleeveBtn() { return document.getElementById("gloveModeSleeveBtn"); },
  get gloveModeImageSection() { return document.getElementById("gloveModeImageSection"); },
  get gloveModeTransferSection() { return document.getElementById("gloveModeTransferSection"); },
  get gloveModeSleeveSection() { return document.getElementById("gloveModeSleeveSection"); },

  // 3D Sleeve Transplant Elements
  get sleeveTargetArmBadge() { return document.getElementById("sleeveTargetArmBadge"); },
  get sleevePresetSelect() { return document.getElementById("sleevePresetSelect"); },
  get sleeveCustomDonorGroup() { return document.getElementById("sleeveCustomDonorGroup"); },
  get sleeveCustomDonorInput() { return document.getElementById("sleeveCustomDonorInput"); },
  get sleeveScaleRatioBadge() { return document.getElementById("sleeveScaleRatioBadge"); },
  get sleeveScaleRatioDesc() { return document.getElementById("sleeveScaleRatioDesc"); },
  get sleeveAutoBackupCheck() { return document.getElementById("sleeveAutoBackupCheck"); },
  get sleeveTransplantBtn() { return document.getElementById("sleeveTransplantBtn"); },

  // POV Drawer Elements
  get povPresetChips() { return document.getElementById("povPresetChips"); },
  get povDualElitesNotice() { return document.getElementById("povDualElitesNotice"); },
  get povSliderX() { return document.getElementById("povSliderX"); },
  get povSliderY() { return document.getElementById("povSliderY"); },
  get povSliderZ() { return document.getElementById("povSliderZ"); },
  get povSliderSway() { return document.getElementById("povSliderSway"); },
  get povValX() { return document.getElementById("povValX"); },
  get povValY() { return document.getElementById("povValY"); },
  get povValZ() { return document.getElementById("povValZ"); },
  get povValSway() { return document.getElementById("povValSway"); },
  get povApplyGameBtn() { return document.getElementById("povApplyGameBtn"); },
  get povResetBtn() { return document.getElementById("povResetBtn"); },

  // Glove Batch Injector - Dropzones & Previews
  get gloveDropzoneLeft() { return document.getElementById("gloveDropzoneLeft"); },
  get gloveFileInputLeft() { return document.getElementById("gloveFileInputLeft"); },
  get gloveEmptyLeft() { return document.getElementById("gloveEmptyLeft"); },
  get glovePreviewContainerLeft() { return document.getElementById("glovePreviewContainerLeft"); },
  get glovePreviewImgLeft() { return document.getElementById("glovePreviewImgLeft"); },
  get gloveClearLeftBtn() { return document.getElementById("gloveClearLeftBtn"); },
  get gloveMetaLeft() { return document.getElementById("gloveMetaLeft"); },

  get gloveDropzoneRight() { return document.getElementById("gloveDropzoneRight"); },
  get gloveFileInputRight() { return document.getElementById("gloveFileInputRight"); },
  get gloveEmptyRight() { return document.getElementById("gloveEmptyRight"); },
  get glovePreviewContainerRight() { return document.getElementById("glovePreviewContainerRight"); },
  get glovePreviewImgRight() { return document.getElementById("glovePreviewImgRight"); },
  get gloveClearRightBtn() { return document.getElementById("gloveClearRightBtn"); },
  get gloveMetaRight() { return document.getElementById("gloveMetaRight"); },

  // Glove Batch Injector - Controls & Scopes
  get gloveMirrorCheck() { return document.getElementById("gloveMirrorCheck"); },
  get gloveTeamScopeSelect() { return document.getElementById("gloveTeamScopeSelect"); },
  get gloveToggleCustomScopeBtn() { return document.getElementById("gloveToggleCustomScopeBtn"); },
  get gloveCustomScopeSection() { return document.getElementById("gloveCustomScopeSection"); },
  get gloveScopeSelectAllBtn() { return document.getElementById("gloveScopeSelectAllBtn"); },
  get gloveScopeClearBtn() { return document.getElementById("gloveScopeClearBtn"); },
  get gloveBatchWeaponsList() { return document.getElementById("gloveBatchWeaponsList"); },
  get gloveBatchInjectBtn() { return document.getElementById("gloveBatchInjectBtn"); },

  // Glove Presets
  get glovePresetNameInput() { return document.getElementById("glovePresetNameInput"); },
  get glovePresetSaveBtn() { return document.getElementById("glovePresetSaveBtn"); },
  get glovePresetsContainer() { return document.getElementById("glovePresetsContainer"); },
  get glovePresetsCountBadge() { return document.getElementById("glovePresetsCountBadge"); },

  // Glove Transfer (Mode B)
  get gloveSourceSelect() { return document.getElementById("gloveSourceSelect"); },
  get gloveSelectAllBtn() { return document.getElementById("gloveSelectAllBtn"); },
  get gloveClearBtn() { return document.getElementById("gloveClearBtn"); },
  get gloveWeaponsList() { return document.getElementById("gloveWeaponsList"); },
  get gloveSyncSleeves() { return document.getElementById("gloveSyncSleeves"); },
  get gloveTransferApplyBtn() { return document.getElementById("gloveTransferApplyBtn"); },

  // Wear Simulator
  get wearTargetSkin() { return document.getElementById("wearTargetSkin"); },
  get wearFloatSlider() { return document.getElementById("wearFloatSlider"); },
  get wearFloatVal() { return document.getElementById("wearFloatVal"); },
  get wearTierBadge() { return document.getElementById("wearTierBadge"); },
  get wearApplyBtn() { return document.getElementById("wearApplyBtn"); },
};

// Internal Glove Injector State
const gloveBatchState = {
  leftBase64: null,
  rightBase64: null,
  leftImgObj: null,
  rightImgObj: null,
  isAutoMirrored: false,
};

export function initProToolsModule() {
  setupProToolsEventListeners();
  setupGloveInjectorEvents();
  setupSleeveTransplantEvents();
  setupPovDrawerEvents();
  updateLiveLedPreview();

  // Listen to batch glove image loading request from library modal
  eventBus.on("gloves:loadIntoBatch", ({ dataUrl, mirror = true }) => {
    if (!dataUrl) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      if (proEls.gloveMirrorCheck) {
        proEls.gloveMirrorCheck.checked = mirror;
      }
      updateGloveDropzone("left", dataUrl, img, false);
      if (mirror) {
        applyAutoMirrorFromLeft(img);
      }
    };
    img.src = dataUrl;
  });

  // Sync glove, pro tools, sleeve, and POV stance options whenever active model is loaded/reloaded
  eventBus.on("model:loaded", () => {
    openProToolsModal(false);
    populateStatTrakDropdown();
    updateLiveLedPreview();
    inspectActiveWeaponSleeve();
    checkDualElitesNotice();
  });
}

export function updateLiveLedPreview() {
  const color = state.pro?.stattrakColor || "orange";
  if (proEls.stLiveLedPreview) {
    proEls.stLiveLedPreview.dataset.color = color;
  }
  let digits = "000000";
  if (proEls.stNumberInput && proEls.stNumberInput.value.trim()) {
    const raw = proEls.stNumberInput.value.trim();
    if (/^\d+$/.test(raw)) {
      digits = raw.padStart(6, "0").slice(-6);
    } else {
      digits = raw.slice(0, 6);
    }
  }
  if (proEls.stPreviewDigits) {
    proEls.stPreviewDigits.textContent = digits;
  }
  if (!state.pro) state.pro = {};
  state.pro.stattrakDigits = digits;

  // Real-time dynamic sync to 3D WebGL viewport
  eventBus.emit("stattrak:preview", { color, number: digits });
}

export function populateStatTrakDropdown() {
  const m = state.modelData;
  if (!m || !m.textures) return;
  if (proEls.stTargetTextureSelect) {
    proEls.stTargetTextureSelect.innerHTML = "";
    const stTextures = m.textures.filter((t) =>
      t.role === "stattrak" ||
      (t.name && (t.name.toLowerCase().includes("stat") || t.name.toLowerCase().includes("digit")))
    );
    if (stTextures.length > 0) {
      if (proEls.stTargetTextureGroup) proEls.stTargetTextureGroup.style.display = "";
      let bestIdx = null;
      stTextures.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.index;
        opt.textContent = `${t.name} (${t.width}x${t.height})`;
        if (t.name.toLowerCase().includes("digit") && bestIdx === null) {
          bestIdx = t.index;
        }
        proEls.stTargetTextureSelect.appendChild(opt);
      });
      if (bestIdx !== null) {
        proEls.stTargetTextureSelect.value = bestIdx;
      }
    } else {
      if (proEls.stTargetTextureGroup) proEls.stTargetTextureGroup.style.display = "none";
    }
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function mirrorImageCanvas(img) {
  const c = document.createElement("canvas");
  c.width = img.naturalWidth || img.width;
  c.height = img.naturalHeight || img.height;
  const ctx = c.getContext("2d");
  ctx.translate(c.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(img, 0, 0);
  return c.toDataURL("image/png");
}

function updateGloveDropzone(side, dataUrl, imgObj, isAutoMirrored = false) {
  const isLeft = side === "left";
  const preview = isLeft ? proEls.glovePreviewImgLeft : proEls.glovePreviewImgRight;
  const container = isLeft ? proEls.glovePreviewContainerLeft : proEls.glovePreviewContainerRight;
  const empty = isLeft ? proEls.gloveEmptyLeft : proEls.gloveEmptyRight;
  const meta = isLeft ? proEls.gloveMetaLeft : proEls.gloveMetaRight;

  if (preview) preview.src = dataUrl;
  if (container) container.classList.remove("hidden");
  if (empty) empty.classList.add("hidden");

  const w = imgObj ? (imgObj.naturalWidth || imgObj.width) : 0;
  const h = imgObj ? (imgObj.naturalHeight || imgObj.height) : 0;

  if (meta) {
    meta.textContent = isAutoMirrored ? `Mirrored (${w}x${h})` : `${w}x${h}`;
    meta.classList.add("loaded");
  }

  if (isLeft) {
    gloveBatchState.leftBase64 = dataUrl;
    gloveBatchState.leftImgObj = imgObj;
    // If mirror is checked, update right preview
    if (proEls.gloveMirrorCheck && proEls.gloveMirrorCheck.checked && imgObj) {
      applyAutoMirrorFromLeft(imgObj);
    }
  } else {
    gloveBatchState.rightBase64 = dataUrl;
    gloveBatchState.rightImgObj = imgObj;
    gloveBatchState.isAutoMirrored = isAutoMirrored;
  }
}

function clearGloveDropzone(side) {
  const isLeft = side === "left";
  const preview = isLeft ? proEls.glovePreviewImgLeft : proEls.glovePreviewImgRight;
  const container = isLeft ? proEls.glovePreviewContainerLeft : proEls.glovePreviewContainerRight;
  const empty = isLeft ? proEls.gloveEmptyLeft : proEls.gloveEmptyRight;
  const meta = isLeft ? proEls.gloveMetaLeft : proEls.gloveMetaRight;
  const input = isLeft ? proEls.gloveFileInputLeft : proEls.gloveFileInputRight;

  if (preview) preview.src = "";
  if (container) container.classList.add("hidden");
  if (empty) empty.classList.remove("hidden");
  if (meta) {
    meta.textContent = "Not Loaded";
    meta.classList.remove("loaded");
  }
  if (input) input.value = "";

  if (isLeft) {
    gloveBatchState.leftBase64 = null;
    gloveBatchState.leftImgObj = null;
    if (gloveBatchState.isAutoMirrored) {
      clearGloveDropzone("right");
    }
  } else {
    gloveBatchState.rightBase64 = null;
    gloveBatchState.rightImgObj = null;
    gloveBatchState.isAutoMirrored = false;
  }
}

function applyAutoMirrorFromLeft(leftImg) {
  try {
    const mirroredDataUri = mirrorImageCanvas(leftImg);
    const mImg = new Image();
    mImg.onload = () => {
      updateGloveDropzone("right", mirroredDataUri, mImg, true);
    };
    mImg.src = mirroredDataUri;
  } catch (err) {
    console.error("Failed to mirror image:", err);
  }
}

function handleGloveFile(file, side) {
  if (!file.type.startsWith("image/") && !file.name.match(/\.(png|jpe?g|bmp|webp)$/i)) {
    showToast("Please select a valid image file (PNG, BMP, JPG, WEBP).", "error");
    return;
  }
  const reader = new FileReader();
  reader.onload = (ev) => {
    const dataUrl = ev.target.result;
    const img = new Image();
    img.onload = () => {
      if (side === "right" && proEls.gloveMirrorCheck && proEls.gloveMirrorCheck.checked) {
        proEls.gloveMirrorCheck.checked = false;
        gloveBatchState.isAutoMirrored = false;
      }
      updateGloveDropzone(side, dataUrl, img, false);
      showToast(`${side === "left" ? "Left" : "Right"} glove loaded (${img.width}x${img.height})`, "success");
    };
    img.src = dataUrl;
  };
  reader.readAsDataURL(file);
}

function setupGloveDropzoneEvents() {
  ["left", "right"].forEach((side) => {
    const isLeft = side === "left";
    const dropzone = isLeft ? proEls.gloveDropzoneLeft : proEls.gloveDropzoneRight;
    const fileInput = isLeft ? proEls.gloveFileInputLeft : proEls.gloveFileInputRight;
    const clearBtn = isLeft ? proEls.gloveClearLeftBtn : proEls.gloveClearRightBtn;

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener("click", (e) => {
      if (e.target.closest(".glove-clear-btn")) return;
      fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) handleGloveFile(file, side);
    });

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) handleGloveFile(file, side);
    });

    if (clearBtn) {
      clearBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        clearGloveDropzone(side);
      });
    }
  });

  // Auto-Mirror toggle
  if (proEls.gloveMirrorCheck) {
    proEls.gloveMirrorCheck.addEventListener("change", (e) => {
      if (e.target.checked) {
        if (gloveBatchState.leftImgObj) {
          applyAutoMirrorFromLeft(gloveBatchState.leftImgObj);
        } else {
          showToast("Upload Left Hand Glove to preview auto-mirroring.", "info");
        }
      } else {
        if (gloveBatchState.isAutoMirrored) {
          clearGloveDropzone("right");
        }
      }
    });
  }

  // Submode Tabs (Mode A vs Mode B vs Mode C)
  if (proEls.gloveModeImageBtn) {
    proEls.gloveModeImageBtn.addEventListener("click", () => {
      proEls.gloveModeImageBtn.classList.add("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
      proEls.gloveModeImageBtn.classList.remove("bg-obsidian-850", "border-white/10", "text-slate-400");
      if (proEls.gloveModeTransferBtn) {
        proEls.gloveModeTransferBtn.classList.remove("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
        proEls.gloveModeTransferBtn.classList.add("bg-obsidian-850", "border-white/10", "text-slate-400");
      }
      if (proEls.gloveModeSleeveBtn) {
        proEls.gloveModeSleeveBtn.classList.remove("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
        proEls.gloveModeSleeveBtn.classList.add("bg-obsidian-850", "border-white/10", "text-slate-400");
      }
      if (proEls.gloveModeImageSection) {
        proEls.gloveModeImageSection.classList.remove("hidden");
        proEls.gloveModeImageSection.classList.add("active");
      }
      if (proEls.gloveModeTransferSection) {
        proEls.gloveModeTransferSection.classList.add("hidden");
        proEls.gloveModeTransferSection.classList.remove("active");
      }
      if (proEls.gloveModeSleeveSection) {
        proEls.gloveModeSleeveSection.classList.add("hidden");
        proEls.gloveModeSleeveSection.classList.remove("active");
      }
    });
  }

  if (proEls.gloveModeTransferBtn) {
    proEls.gloveModeTransferBtn.addEventListener("click", () => {
      proEls.gloveModeTransferBtn.classList.add("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
      proEls.gloveModeTransferBtn.classList.remove("bg-obsidian-850", "border-white/10", "text-slate-400");
      if (proEls.gloveModeImageBtn) {
        proEls.gloveModeImageBtn.classList.remove("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
        proEls.gloveModeImageBtn.classList.add("bg-obsidian-850", "border-white/10", "text-slate-400");
      }
      if (proEls.gloveModeSleeveBtn) {
        proEls.gloveModeSleeveBtn.classList.remove("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
        proEls.gloveModeSleeveBtn.classList.add("bg-obsidian-850", "border-white/10", "text-slate-400");
      }
      if (proEls.gloveModeTransferSection) {
        proEls.gloveModeTransferSection.classList.remove("hidden");
        proEls.gloveModeTransferSection.classList.add("active");
      }
      if (proEls.gloveModeImageSection) {
        proEls.gloveModeImageSection.classList.add("hidden");
        proEls.gloveModeImageSection.classList.remove("active");
      }
      if (proEls.gloveModeSleeveSection) {
        proEls.gloveModeSleeveSection.classList.add("hidden");
        proEls.gloveModeSleeveSection.classList.remove("active");
      }
    });
  }

  if (proEls.gloveModeSleeveBtn) {
    proEls.gloveModeSleeveBtn.addEventListener("click", () => {
      proEls.gloveModeSleeveBtn.classList.add("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
      proEls.gloveModeSleeveBtn.classList.remove("bg-obsidian-850", "border-white/10", "text-slate-400");
      if (proEls.gloveModeImageBtn) {
        proEls.gloveModeImageBtn.classList.remove("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
        proEls.gloveModeImageBtn.classList.add("bg-obsidian-850", "border-white/10", "text-slate-400");
      }
      if (proEls.gloveModeTransferBtn) {
        proEls.gloveModeTransferBtn.classList.remove("active", "bg-cyber-cyan/20", "border-cyber-cyan", "text-white");
        proEls.gloveModeTransferBtn.classList.add("bg-obsidian-850", "border-white/10", "text-slate-400");
      }
      if (proEls.gloveModeSleeveSection) {
        proEls.gloveModeSleeveSection.classList.remove("hidden");
        proEls.gloveModeSleeveSection.classList.add("active");
      }
      if (proEls.gloveModeImageSection) {
        proEls.gloveModeImageSection.classList.add("hidden");
        proEls.gloveModeImageSection.classList.remove("active");
      }
      if (proEls.gloveModeTransferSection) {
        proEls.gloveModeTransferSection.classList.add("hidden");
        proEls.gloveModeTransferSection.classList.remove("active");
      }
      inspectActiveWeaponSleeve();
    });
  }

  // Custom Weapons Scope Toggle
  if (proEls.gloveToggleCustomScopeBtn && proEls.gloveCustomScopeSection) {
    proEls.gloveToggleCustomScopeBtn.addEventListener("click", () => {
      const isHidden = proEls.gloveCustomScopeSection.classList.toggle("hidden");
      proEls.gloveToggleCustomScopeBtn.classList.toggle("active", !isHidden);
      proEls.gloveToggleCustomScopeBtn.setAttribute("aria-expanded", String(!isHidden));
    });
  }

  if (proEls.gloveScopeSelectAllBtn && proEls.gloveBatchWeaponsList) {
    proEls.gloveScopeSelectAllBtn.addEventListener("click", () => {
      proEls.gloveBatchWeaponsList.querySelectorAll("input").forEach((c) => {
        c.checked = true;
        c.closest(".weapon-check-card")?.classList.add("is-checked");
      });
    });
  }

  if (proEls.gloveScopeClearBtn && proEls.gloveBatchWeaponsList) {
    proEls.gloveScopeClearBtn.addEventListener("click", () => {
      proEls.gloveBatchWeaponsList.querySelectorAll("input").forEach((c) => {
        c.checked = false;
        c.closest(".weapon-check-card")?.classList.remove("is-checked");
      });
    });
  }

  // Update batch weapons list when target team scope changes
  if (proEls.gloveTeamScopeSelect) {
    proEls.gloveTeamScopeSelect.addEventListener("change", (e) => {
      updateGloveBatchWeaponsList(e.target.value);
    });
  }

  // Batch Image Inject Action
  if (proEls.gloveBatchInjectBtn) {
    proEls.gloveBatchInjectBtn.addEventListener("click", async () => {
      const leftB64 = gloveBatchState.leftBase64;
      const rightB64 = gloveBatchState.rightBase64;
      const mirror = proEls.gloveMirrorCheck ? proEls.gloveMirrorCheck.checked : false;

      if (!leftB64 && !rightB64) {
        showToast("Please select or drop at least one glove image (left or right).", "error");
        return;
      }

      const team = proEls.gloveTeamScopeSelect ? proEls.gloveTeamScopeSelect.value : "all";
      let weapons = ["all"];
      if (
        proEls.gloveCustomScopeSection &&
        !proEls.gloveCustomScopeSection.classList.contains("hidden") &&
        proEls.gloveBatchWeaponsList
      ) {
        const checked = proEls.gloveBatchWeaponsList.querySelectorAll("input:checked");
        if (checked.length === 0) {
          showToast("Please select at least one weapon from the scope list, or close custom scope to inject to all models.", "warning");
          return;
        }
        weapons = Array.from(checked).map((c) => c.value);
      }

      showLoader(`Injecting gloves into ${team.toUpperCase()} loadout models...`);
      try {
        const res = await apiPost("/api/gloves/batch_inject_images", {
          left_image_base64: leftB64,
          right_image_base64: rightB64,
          mirror_left: mirror,
          team: team,
          weapons: weapons,
        });

        showToast(res.message || "Glove batch injection completed successfully!", "success");
        eventBus.emit("model:reloadRequest");
      } catch (err) {
        showToast(`Glove batch injection failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Preset Save
  if (proEls.glovePresetSaveBtn) {
    proEls.glovePresetSaveBtn.addEventListener("click", async () => {
      const name = proEls.glovePresetNameInput ? proEls.glovePresetNameInput.value.trim() : "";
      if (!name) {
        showToast("Please enter a name for the glove preset.", "error");
        return;
      }
      if (!gloveBatchState.leftBase64 && !gloveBatchState.rightBase64) {
        showToast("Please load at least one glove image to save as preset.", "error");
        return;
      }

      showLoader("Saving glove preset...");
      try {
        const res = await apiPost("/api/gloves/presets/save", {
          name: name,
          left_image_base64: gloveBatchState.leftBase64,
          right_image_base64: gloveBatchState.rightBase64,
          mirror_left: proEls.gloveMirrorCheck ? proEls.gloveMirrorCheck.checked : false,
        });

        showToast(res.message || `Preset '${name}' saved successfully.`, "success");
        if (proEls.glovePresetNameInput) proEls.glovePresetNameInput.value = "";
        loadGlovePresets();
      } catch (err) {
        showToast(`Failed to save preset: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }
}

async function loadGlovePresets() {
  if (!proEls.glovePresetsContainer) return;
  try {
    const res = await apiGet("/api/gloves/presets");
    const presets = res.presets || [];
    if (proEls.glovePresetsCountBadge) {
      proEls.glovePresetsCountBadge.textContent = `${presets.length} Preset${presets.length === 1 ? "" : "s"}`;
    }

    if (presets.length === 0) {
      proEls.glovePresetsContainer.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 8px; font-size: 0.8rem;">
          No saved glove presets yet. Save your favorite glove pairs above!
        </div>
      `;
      return;
    }

    proEls.glovePresetsContainer.innerHTML = "";
    presets.forEach((p) => {
      const item = document.createElement("div");
      item.className = "glove-preset-item";
      const thumbsHtml = `
        <div class="glove-preset-thumbs">
          ${p.left_thumb ? `<img src="${p.left_thumb}" class="glove-preset-thumb-img" title="Left Glove">` : ""}
          ${p.right_thumb ? `<img src="${p.right_thumb}" class="glove-preset-thumb-img" title="Right Glove">` : ""}
        </div>
      `;
      const dateStr = p.created_at ? new Date(p.created_at).toLocaleDateString() : "";
      item.innerHTML = `
        <div class="glove-preset-left">
          ${thumbsHtml}
          <div class="glove-preset-info">
            <span class="glove-preset-name">${escapeHtml(p.name)}</span>
            <span class="glove-preset-date">${dateStr}</span>
          </div>
        </div>
        <div class="glove-preset-actions">
          <button type="button" class="btn btn-sm btn-primary apply-preset-btn" data-preset="${escapeHtml(p.name)}" title="Apply this preset to loadout">
            Apply
          </button>
          <button type="button" class="btn btn-sm btn-danger delete-preset-btn" data-preset="${escapeHtml(p.name)}" title="Delete preset" style="padding: 2px 6px;">
            &times;
          </button>
        </div>
      `;

      // Apply button
      item.querySelector(".apply-preset-btn").addEventListener("click", async () => {
        const team = proEls.gloveTeamScopeSelect ? proEls.gloveTeamScopeSelect.value : "all";
        showLoader(`Applying preset '${p.name}' to ${team.toUpperCase()} loadout...`);
        try {
          const applyRes = await apiPost("/api/gloves/presets/apply", {
            name: p.name,
            team: team,
            weapons: ["all"],
          });
          showToast(applyRes.message || `Preset '${p.name}' applied!`, "success");
          eventBus.emit("model:reloadRequest");
        } catch (err) {
          showToast(`Failed to apply preset: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      });

      // Delete button
      item.querySelector(".delete-preset-btn").addEventListener("click", async () => {
        if (!confirm(`Delete glove preset '${p.name}'?`)) return;
        try {
          await apiPost("/api/gloves/presets/delete", { name: p.name });
          showToast(`Preset '${p.name}' deleted.`, "info");
          loadGlovePresets();
        } catch (err) {
          showToast(`Failed to delete preset: ${err.message}`, "error");
        }
      });

      proEls.glovePresetsContainer.appendChild(item);
    });
  } catch (err) {
    console.error("Failed to load glove presets:", err);
  }
}

function setupProToolsEventListeners() {
  if (proEls.openProToolsBtn) {
    proEls.openProToolsBtn.addEventListener("click", () => openProToolsModal(true));
  }

  if (proEls.proToolsModalCloseBtn) {
    proEls.proToolsModalCloseBtn.addEventListener("click", () => {
      if (proEls.proToolsModal) proEls.proToolsModal.classList.add("hidden");
    });
  }

  // Tabs switching (StatTrak, Gloves, Wear)
  proEls.proTabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      proEls.proTabBtns.forEach((b) => b.classList.remove("active"));
      proEls.proPanes.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const pro = btn.dataset.pro;
      const pane = document.getElementById(`proPane${pro.charAt(0).toUpperCase() + pro.slice(1)}`);
      if (pane) pane.classList.add("active");
    });
  });

  // StatTrak Colors
  if (proEls.stColorButtons) {
    proEls.stColorButtons.querySelectorAll(".color-opt-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        proEls.stColorButtons.querySelectorAll(".color-opt-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.pro.stattrakColor = btn.dataset.color;
        updateLiveLedPreview();
      });
    });
  }

  // StatTrak Live Number Input
  if (proEls.stNumberInput) {
    proEls.stNumberInput.addEventListener("input", () => {
      updateLiveLedPreview();
    });
  }

  // Apply StatTrak
  if (proEls.stApplyBtn) {
    proEls.stApplyBtn.addEventListener("click", async () => {
      showLoader("Updating StatTrak LED digit display...");
      try {
        const selectedTexIdx = proEls.stTargetTextureSelect && proEls.stTargetTextureSelect.value
          ? parseInt(proEls.stTargetTextureSelect.value, 10)
          : null;

        const payload = {
          team: state.currentTeam,
          weapon: state.currentWeapon,
          color: state.pro.stattrakColor,
          number: proEls.stNumberInput ? proEls.stNumberInput.value.trim() || null : null,
        };
        if (selectedTexIdx !== null && !isNaN(selectedTexIdx)) {
          payload.texture_index = selectedTexIdx;
        }

        const res = await apiPost("/api/stattrak_apply", payload);
        showToast(res.message, "success");
        if (proEls.proToolsModal) proEls.proToolsModal.classList.add("hidden");

        const actionTeam = state.currentTeam;
        const actionWeapon = state.currentWeapon;
        const targetTexName = res.texture_name || "stat_digit.bmp";
        const targetTexIdx = res.texture_index !== undefined ? res.texture_index : selectedTexIdx;

        eventBus.emit("history:record", {
          description: `Customized StatTrak LED (${state.pro.stattrakColor.toUpperCase()})`,
          team: actionTeam,
          weapon: actionWeapon,
          undo: async () => {
            await apiPost("/api/revert", {
              team: actionTeam,
              weapon: actionWeapon,
              texture_name: targetTexName,
              texture_index: targetTexIdx,
            });
          },
          redo: async () => {
            await apiPost("/api/stattrak_apply", payload);
          },
        });

        eventBus.emit("model:reloadRequest");
        eventBus.emit("3d:requestReload");
        eventBus.emit("stattrak:updated", {
          color: state.pro.stattrakColor,
          number: state.pro.stattrakDigits || "000000",
        });
      } catch (err) {
        showToast(`StatTrak customization failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Reset StatTrak to Original
  if (proEls.stResetBtn) {
    proEls.stResetBtn.addEventListener("click", async () => {
      showLoader("Restoring original StatTrak LED texture...");
      try {
        const payload = {
          team: state.currentTeam,
          weapon: state.currentWeapon,
          texture_name: "stat_digit.bmp",
        };
        const res = await apiPost("/api/stattrak_reset", payload);
        showToast(res.message || "StatTrak restored to original", "success");
        if (proEls.stNumberInput) proEls.stNumberInput.value = "";
        updateLiveLedPreview();
        eventBus.emit("model:reloadRequest");
        eventBus.emit("3d:requestReload");
        eventBus.emit("stattrak:preview", {
          color: state.pro.stattrakColor || "orange",
          number: "000000",
          reset: true,
        });
      } catch (err) {
        showToast(`StatTrak reset failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Glove Transfer (Mode B) Controls
  if (proEls.gloveSelectAllBtn) {
    proEls.gloveSelectAllBtn.addEventListener("click", () => {
      if (proEls.gloveWeaponsList) {
        proEls.gloveWeaponsList.querySelectorAll("input").forEach((chk) => {
          chk.checked = true;
          chk.closest(".weapon-check-card")?.classList.add("is-checked");
        });
      }
    });
  }

  if (proEls.gloveClearBtn) {
    proEls.gloveClearBtn.addEventListener("click", () => {
      if (proEls.gloveWeaponsList) {
        proEls.gloveWeaponsList.querySelectorAll("input").forEach((chk) => {
          chk.checked = false;
          chk.closest(".weapon-check-card")?.classList.remove("is-checked");
        });
      }
    });
  }

  if (proEls.gloveTransferApplyBtn) {
    proEls.gloveTransferApplyBtn.addEventListener("click", async () => {
      const srcWeapon = proEls.gloveSourceSelect ? proEls.gloveSourceSelect.value : "";
      const chks = proEls.gloveWeaponsList ? proEls.gloveWeaponsList.querySelectorAll("input:checked") : [];
      const targets = Array.from(chks).map((c) => c.value);

      if (targets.length === 0) {
        showToast("Please select at least one target weapon.", "error");
        return;
      }

      showLoader(`Transferring gloves from ${srcWeapon.toUpperCase()} to ${targets.length} weapons...`);
      try {
        const res = await apiPost("/api/glove_transfer", {
          source_weapon: srcWeapon,
          target_weapons: targets,
          team: state.currentTeam,
          sync_sleeves: proEls.gloveSyncSleeves ? proEls.gloveSyncSleeves.checked : true,
        });
        showToast("Glove transfer completed successfully!", "success");
        if (proEls.proToolsModal) proEls.proToolsModal.classList.add("hidden");
        eventBus.emit("model:reloadRequest");
      } catch (err) {
        showToast(`Glove transfer failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Wear Simulator Controls
  if (proEls.wearFloatSlider) {
    proEls.wearFloatSlider.addEventListener("input", (e) => {
      const f = parseFloat(e.target.value);
      state.pro.wearFloat = f;
      if (proEls.wearFloatVal) proEls.wearFloatVal.textContent = f.toFixed(3);

      let tier = "Factory New (FN)";
      let bg = "#10b981";
      if (f >= 0.45) {
        tier = "Battle-Scarred (BS)";
        bg = "#ef4444";
      } else if (f >= 0.38) {
        tier = "Well-Worn (WW)";
        bg = "#f59e0b";
      } else if (f >= 0.15) {
        tier = "Field-Tested (FT)";
        bg = "#8b5cf6";
      } else if (f >= 0.07) {
        tier = "Minimal Wear (MW)";
        bg = "#06b6d4";
      }
      if (proEls.wearTierBadge) {
        proEls.wearTierBadge.textContent = tier;
        proEls.wearTierBadge.style.backgroundColor = bg;
      }
    });
  }

  if (proEls.wearApplyBtn) {
    proEls.wearApplyBtn.addEventListener("click", async () => {
      const skinIdx = proEls.wearTargetSkin ? proEls.wearTargetSkin.value : null;
      showLoader("Applying procedural edge wear & scratches...");
      try {
        const payload = {
          team: state.currentTeam,
          weapon: state.currentWeapon,
          texture_index: parseInt(skinIdx, 10),
          wear_float: state.pro.wearFloat,
        };

        const res = await apiPost("/api/wear_apply", payload);
        showToast(res.message, "success");
        if (proEls.proToolsModal) proEls.proToolsModal.classList.add("hidden");

        const actionTeam = state.currentTeam;
        const actionWeapon = state.currentWeapon;
        const texName = res.texture_name || `Slot ${skinIdx}`;

        eventBus.emit("history:record", {
          description: `Applied Wear Float (${state.pro.wearFloat.toFixed(2)}) to ${texName}`,
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
            await apiPost("/api/wear_apply", payload);
          },
        });

        eventBus.emit("model:reloadRequest");
      } catch (err) {
        showToast(`Wear simulation failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }
}

function setupGloveInjectorEvents() {
  setupGloveDropzoneEvents();
}

function updateGloveBatchWeaponsList(selectedTeam = "all") {
  if (!proEls.gloveBatchWeaponsList) return;
  proEls.gloveBatchWeaponsList.innerHTML = "";

  let candidateModels = [];
  if (selectedTeam === "all") {
    const ctList = (state.availableModels && state.availableModels.ct) || [];
    const tList = (state.availableModels && state.availableModels.t) || [];
    candidateModels = [...ctList, ...tList];
  } else {
    candidateModels = (state.availableModels && state.availableModels[selectedTeam]) || [];
  }

  if (candidateModels.length === 0) {
    proEls.gloveBatchWeaponsList.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 12px; font-size: 0.8rem;">No weapon models found.</div>';
    return;
  }

  const seen = new Set();
  candidateModels.forEach((mod) => {
    const weaponName = (mod.weapon || "").trim();
    if (!weaponName) return;
    const wKey = weaponName.toLowerCase();
    if (!seen.has(wKey)) {
      seen.add(wKey);
      const chkBatch = document.createElement("label");
      chkBatch.className = "weapon-check-card";
      chkBatch.title = weaponName.toUpperCase();
      chkBatch.innerHTML = `
        <input type="checkbox" value="${weaponName}">
        <span>${weaponName.toUpperCase()}</span>
      `;
      const input = chkBatch.querySelector("input");
      input.addEventListener("change", () => {
        chkBatch.classList.toggle("is-checked", input.checked);
      });
      proEls.gloveBatchWeaponsList.appendChild(chkBatch);
    }
  });
}

export function openProToolsModal(showModal = false) {
  const m = state.modelData;
  if (!m) return;

  const models = (state.availableModels && state.availableModels[state.currentTeam]) || [];
  if (proEls.gloveSourceSelect) proEls.gloveSourceSelect.innerHTML = "";
  if (proEls.gloveWeaponsList) proEls.gloveWeaponsList.innerHTML = "";

  if (models.length === 0 && proEls.gloveWeaponsList) {
    proEls.gloveWeaponsList.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 12px; font-size: 0.8rem;">No target models available.</div>';
  }

  const seen = new Set();
  models.forEach((mod) => {
    const weaponName = (mod.weapon || "").trim();
    if (!weaponName) return;
    const wKey = weaponName.toLowerCase();
    if (!seen.has(wKey)) {
      seen.add(wKey);
      const opt = document.createElement("option");
      opt.value = weaponName;
      opt.textContent = weaponName.toUpperCase();
      if (weaponName.toLowerCase() === state.currentWeapon.toLowerCase()) opt.selected = true;
      if (proEls.gloveSourceSelect) proEls.gloveSourceSelect.appendChild(opt);

      // Checkbox for target (Mode B)
      const chkWrap = document.createElement("label");
      chkWrap.className = "weapon-check-card";
      chkWrap.title = weaponName.toUpperCase();
      chkWrap.innerHTML = `
        <input type="checkbox" value="${weaponName}">
        <span>${weaponName.toUpperCase()}</span>
      `;
      const chkInput = chkWrap.querySelector("input");
      chkInput.addEventListener("change", () => {
        chkWrap.classList.toggle("is-checked", chkInput.checked);
      });
      if (proEls.gloveWeaponsList) proEls.gloveWeaponsList.appendChild(chkWrap);
    }
  });

  // Populate Target Weapons Checklist for Batch Injector based on chosen scope
  const currentScope = proEls.gloveTeamScopeSelect ? proEls.gloveTeamScopeSelect.value : "all";
  updateGloveBatchWeaponsList(currentScope);

  if (proEls.wearTargetSkin) {
    proEls.wearTargetSkin.innerHTML = "";
    const skins = m.textures.filter((t) => t.role === "skin");
    skins.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.index;
      opt.textContent = `${s.name} (${s.width}x${s.height})`;
      proEls.wearTargetSkin.appendChild(opt);
    });
  }

  // Populate StatTrak Target Texture Selector
  populateStatTrakDropdown();
  updateLiveLedPreview();

  // Load saved glove presets
  loadGlovePresets();

  if (showModal && proEls.proToolsModal) {
    proEls.proToolsModal.style.display = "";
    proEls.proToolsModal.classList.remove("hidden");
  }
}

// =====================================================================
// 3D Sleeve Transplant & First-Person POV Stance Engine
// =====================================================================

export async function inspectActiveWeaponSleeve() {
  const wep = state.currentWeapon || "usp";
  const team = state.currentTeam || "ct";
  const donorPreset = proEls.sleevePresetSelect ? proEls.sleevePresetSelect.value : "sas_navy";
  const customDonor = proEls.sleeveCustomDonorInput ? proEls.sleeveCustomDonorInput.value.trim() : "";

  try {
    let url = `/api/sleeve/inspect?weapon=${encodeURIComponent(wep)}&team=${encodeURIComponent(team)}&donor_preset=${encodeURIComponent(donorPreset)}`;
    if (donorPreset === "custom" && customDonor) {
      url += `&donor_path=${encodeURIComponent(customDonor)}`;
    }
    const res = await apiGet(url);
    if (!res.success) return;

    if (proEls.sleeveTargetArmBadge && res.target) {
      const armType = res.target.arm_type || "bare_arm";
      proEls.sleeveTargetArmBadge.className = "arm-type-badge";
      if (armType === "bare_arm") {
        proEls.sleeveTargetArmBadge.classList.add("badge-bare");
        proEls.sleeveTargetArmBadge.textContent = "Bare Arm Rig";
      } else if (armType === "jacket_sleeve") {
        proEls.sleeveTargetArmBadge.classList.add("badge-jacket");
        proEls.sleeveTargetArmBadge.textContent = "CT Loose Jacket";
      } else {
        proEls.sleeveTargetArmBadge.classList.add("badge-gloves");
        proEls.sleeveTargetArmBadge.textContent = "Gloves Only";
      }
    }

    if (proEls.sleeveScaleRatioBadge) {
      proEls.sleeveScaleRatioBadge.textContent = `${Number(res.scale_ratio).toFixed(4)}x`;
    }
    if (proEls.sleeveScaleRatioDesc) {
      proEls.sleeveScaleRatioDesc.textContent = res.scale_description || "Auto-calculated bone ratio";
    }
  } catch (err) {
    console.warn("Sleeve inspect failed:", err);
  }
}

export function checkDualElitesNotice() {
  const wep = (state.currentWeapon || "").toLowerCase();
  const isDualElites = wep.includes("elite");
  if (proEls.povDualElitesNotice) {
    proEls.povDualElitesNotice.classList.toggle("hidden", !isDualElites);
  }
  if (isDualElites) {
    if (proEls.povSliderX) proEls.povSliderX.value = "0.0";
    if (proEls.povValX) proEls.povValX.textContent = "0.0";
    eventBus.emit("3d:setPovOffsets", { offset_x: 0.0 });
  }
}

function setupSleeveTransplantEvents() {
  if (proEls.sleevePresetSelect) {
    proEls.sleevePresetSelect.addEventListener("change", (e) => {
      const isCustom = e.target.value === "custom";
      if (proEls.sleeveCustomDonorGroup) {
        proEls.sleeveCustomDonorGroup.classList.toggle("hidden", !isCustom);
      }
      inspectActiveWeaponSleeve();
    });
  }

  if (proEls.sleeveCustomDonorInput) {
    proEls.sleeveCustomDonorInput.addEventListener("change", () => {
      inspectActiveWeaponSleeve();
    });
  }

  if (proEls.sleeveTransplantBtn) {
    proEls.sleeveTransplantBtn.addEventListener("click", async () => {
      const wep = state.currentWeapon || "usp";
      const team = state.currentTeam || "ct";
      const donorPreset = proEls.sleevePresetSelect ? proEls.sleevePresetSelect.value : "sas_navy";
      const customDonor = proEls.sleeveCustomDonorInput ? proEls.sleeveCustomDonorInput.value.trim() : null;
      const autoBackup = proEls.sleeveAutoBackupCheck ? proEls.sleeveAutoBackupCheck.checked : true;

      showLoader(`Transplanting 3D sleeves into ${wep.toUpperCase()}...`);
      try {
        const payload = {
          weapon: wep,
          team: team,
          donor_preset: donorPreset,
          auto_backup: autoBackup,
        };
        if (donorPreset === "custom" && customDonor) {
          payload.donor_path = customDonor;
        }
        const res = await apiPost("/api/sleeve/inject", payload);
        if (res.success) {
          showToast(res.message || "3D sleeve transplant completed!", "success");
          eventBus.emit("model:reloadRequest");
          eventBus.emit("3d:requestReload");
          inspectActiveWeaponSleeve();
        } else {
          showToast(`Sleeve transplant failed: ${res.error || "Unknown error"}`, "error");
        }
      } catch (err) {
        showToast(`Sleeve transplant failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }
}

const POV_PRESET_MAP = {
  cs2_classic: { offset_x: 2.5, offset_y: 1.5, offset_z: -1.5, sway: 1.5 },
  csgo_desktop: { offset_x: 1.0, offset_y: 1.0, offset_z: -1.0, sway: 1.0 },
  couch: { offset_x: 0.0, offset_y: 2.0, offset_z: -2.0, sway: 1.2 },
  quake_centered: { offset_x: 0.0, offset_y: 1.8, offset_z: -1.0, sway: 0.0 },
  vanilla_16: { offset_x: 0.0, offset_y: 0.0, offset_z: 0.0, sway: 0.0 },
};

function updatePovSlidersFromState(cfg) {
  const wep = (state.currentWeapon || "").toLowerCase();
  const isDualElites = wep.includes("elite");

  if (proEls.povDualElitesNotice) {
    proEls.povDualElitesNotice.classList.toggle("hidden", !isDualElites);
  }

  const ox = isDualElites ? 0.0 : (cfg.offset_x ?? 0.0);
  const oy = cfg.offset_y ?? 0.0;
  const oz = cfg.offset_z ?? 0.0;
  const sway = cfg.sway ?? 1.0;

  if (proEls.povSliderX) proEls.povSliderX.value = ox;
  if (proEls.povSliderY) proEls.povSliderY.value = oy;
  if (proEls.povSliderZ) proEls.povSliderZ.value = oz;
  if (proEls.povSliderSway) proEls.povSliderSway.value = sway;

  if (proEls.povValX) proEls.povValX.textContent = Number(ox).toFixed(1);
  if (proEls.povValY) proEls.povValY.textContent = Number(oy).toFixed(1);
  if (proEls.povValZ) proEls.povValZ.textContent = Number(oz).toFixed(1);
  if (proEls.povValSway) proEls.povValSway.textContent = Number(sway).toFixed(1);

  eventBus.emit("3d:setPovOffsets", { offset_x: ox, offset_y: oy, offset_z: oz, sway: sway });
}

function setupPovDrawerEvents() {
  // Preset chips
  if (proEls.povPresetChips) {
    proEls.povPresetChips.querySelectorAll(".pov-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        proEls.povPresetChips.querySelectorAll(".pov-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        const presetName = chip.dataset.preset;
        const presetCfg = POV_PRESET_MAP[presetName] || POV_PRESET_MAP.cs2_classic;
        updatePovSlidersFromState(presetCfg);
      });
    });
  }

  // Sliders input events
  const onSliderChange = () => {
    const wep = (state.currentWeapon || "").toLowerCase();
    const isDualElites = wep.includes("elite");

    let ox = parseFloat(proEls.povSliderX?.value || 0.0);
    if (isDualElites) ox = 0.0;
    const oy = parseFloat(proEls.povSliderY?.value || 0.0);
    const oz = parseFloat(proEls.povSliderZ?.value || 0.0);
    const sway = parseFloat(proEls.povSliderSway?.value || 1.0);

    if (proEls.povValX) proEls.povValX.textContent = ox.toFixed(1);
    if (proEls.povValY) proEls.povValY.textContent = oy.toFixed(1);
    if (proEls.povValZ) proEls.povValZ.textContent = oz.toFixed(1);
    if (proEls.povValSway) proEls.povValSway.textContent = sway.toFixed(1);

    eventBus.emit("3d:setPovOffsets", { offset_x: ox, offset_y: oy, offset_z: oz, sway: sway });
  };

  if (proEls.povSliderX) proEls.povSliderX.addEventListener("input", onSliderChange);
  if (proEls.povSliderY) proEls.povSliderY.addEventListener("input", onSliderChange);
  if (proEls.povSliderZ) proEls.povSliderZ.addEventListener("input", onSliderChange);
  if (proEls.povSliderSway) proEls.povSliderSway.addEventListener("input", onSliderChange);

  // Apply to game
  if (proEls.povApplyGameBtn) {
    proEls.povApplyGameBtn.addEventListener("click", async () => {
      const wep = state.currentWeapon || "usp";
      const isDualElites = wep.toLowerCase().includes("elite");
      let ox = parseFloat(proEls.povSliderX?.value || 0.0);
      if (isDualElites) ox = 0.0;
      const oy = parseFloat(proEls.povSliderY?.value || 0.0);
      const oz = parseFloat(proEls.povSliderZ?.value || 0.0);

      showLoader("Writing modern_pov.cfg and updating userconfig.cfg...");
      try {
        const res = await apiPost("/api/pov/apply", {
          weapon: wep,
          config: {
            offset_x: ox,
            offset_y: oy,
            offset_z: oz,
          },
        });
        if (res.success) {
          showToast(res.message || "POV configuration applied to game!", "success");
        } else {
          showToast(`Failed to apply POV: ${res.error || "Unknown error"}`, "error");
        }
      } catch (err) {
        showToast(`Failed to apply POV: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Reset vanilla
  if (proEls.povResetBtn) {
    proEls.povResetBtn.addEventListener("click", async () => {
      showLoader("Resetting modern_pov.cfg to vanilla default...");
      try {
        const res = await apiPost("/api/pov/reset", {});
        if (res.success) {
          showToast(res.message || "POV reset to vanilla default.", "success");
          if (proEls.povPresetChips) {
            proEls.povPresetChips.querySelectorAll(".pov-chip").forEach((c) => {
              c.classList.toggle("active", c.dataset.preset === "vanilla_16");
            });
          }
          updatePovSlidersFromState(POV_PRESET_MAP.vanilla_16);
        } else {
          showToast(`Failed to reset POV: ${res.error || "Unknown error"}`, "error");
        }
      } catch (err) {
        showToast(`Failed to reset POV: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }
}
