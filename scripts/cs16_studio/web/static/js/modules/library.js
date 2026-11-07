/**
 * modules/library.js - Dedicated Skin Assets & Sticker Assets Libraries
 * CS 1.6 Asset Studio Pro Modular Architecture
 * Clean separation of skins and stickers with zero tag clutter.
 */

import { state, eventBus } from "../core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader } from "../core/api.js";
import { refreshSlotPreview } from "./slots.js";

const els = {
  // Shared Pick Modal
  get libraryModal() { return document.getElementById("libraryModal"); },
  get modalTitle() { return document.getElementById("modalTitle"); },
  get modalCloseBtn() { return document.getElementById("modalCloseBtn"); },
  get modalLibraryGrid() { return document.getElementById("modalLibraryGrid"); },
  get modalLibraryTabs() { return document.getElementById("modalLibraryTabs"); },
  get modalLibrarySearch() { return document.getElementById("modalLibrarySearch"); },
  get modalGloveBilateralWrap() { return document.getElementById("modalGloveBilateralWrap"); },
  get modalGloveBilateralCheck() { return document.getElementById("modalGloveBilateralCheck"); },

  // Skin Assets Library Drawer Elements
  get drawerViewSkinLibrary() { return document.getElementById("drawerViewSkinLibrary"); },
  get skinLibraryGrid() { return document.getElementById("skinLibraryGrid"); },
  get skinSearchInput() { return document.getElementById("skinSearchInput"); },
  get skinCategoryTabs() { return document.getElementById("skinCategoryTabs"); },
  get weaponCategoryFilters() { return document.getElementById("weaponCategoryFilters"); },
  get weaponSubcatFilters() { return document.getElementById("weaponSubcatFilters"); },
  get knifeSubcatFilters() { return document.getElementById("knifeSubcatFilters"); },
  get gloveSubcatFilters() { return document.getElementById("gloveSubcatFilters"); },
  get skinBatchFilesBtn() { return document.getElementById("skinBatchFilesBtn"); },
  get skinBatchFolderBtn() { return document.getElementById("skinBatchFolderBtn"); },
  get skinFileInput() { return document.getElementById("skinFileInput"); },
  get skinFolderInput() { return document.getElementById("skinFolderInput"); },
  get skinDropZone() { return document.getElementById("skinDropZone"); },
  get skinUploadProgress() { return document.getElementById("skinUploadProgress"); },
  get skinUploadProgressText() { return document.getElementById("skinUploadProgressText"); },
  get skinUploadProgressPercent() { return document.getElementById("skinUploadProgressPercent"); },
  get skinUploadProgressBar() { return document.getElementById("skinUploadProgressBar"); },

  // Sticker Assets Library Drawer Elements
  get drawerViewStickerLibrary() { return document.getElementById("drawerViewStickerLibrary"); },
  get stickerLibraryGrid() { return document.getElementById("stickerLibraryGrid"); },
  get stickerSearchInput() { return document.getElementById("stickerSearchInput"); },
  get stickerCatFilters() { return document.getElementById("stickerCatFilters"); },
  get stickerBatchFilesBtn() { return document.getElementById("stickerBatchFilesBtn"); },
  get stickerBatchFolderBtn() { return document.getElementById("stickerBatchFolderBtn"); },
  get stickerFileInput() { return document.getElementById("stickerFileInput"); },
  get stickerFolderInput() { return document.getElementById("stickerFolderInput"); },
  get stickerDropZone() { return document.getElementById("stickerDropZone"); },
  get stickerUploadProgress() { return document.getElementById("stickerUploadProgress"); },
  get stickerUploadProgressText() { return document.getElementById("stickerUploadProgressText"); },
  get stickerUploadProgressPercent() { return document.getElementById("stickerUploadProgressPercent"); },
  get stickerUploadProgressBar() { return document.getElementById("stickerUploadProgressBar"); },
  get stickerRestoreDefaultsBtn() { return document.getElementById("stickerRestoreDefaultsBtn"); },

  // Sticker Edit / Upload Details Modal
  get stickerEditModal() { return document.getElementById("stickerEditModal"); },
  get stickerEditModalTitle() { return document.getElementById("stickerEditModalTitle"); },
  get stickerEditModalCloseBtn() { return document.getElementById("stickerEditModalCloseBtn"); },
  get stickerEditFilename() { return document.getElementById("stickerEditFilename"); },
  get stickerEditNameInput() { return document.getElementById("stickerEditNameInput"); },
  get stickerEditCatInput() { return document.getElementById("stickerEditCatInput"); },
  get stickerUploadAlphaRow() { return document.getElementById("stickerUploadAlphaRow"); },
  get stickerUploadAutoAlpha() { return document.getElementById("stickerUploadAutoAlpha"); },
  get stickerEditSaveBtn() { return document.getElementById("stickerEditSaveBtn"); },
  get stickerEditCancelBtn() { return document.getElementById("stickerEditCancelBtn"); },

  // Skin Edit / Registration Modal
  get skinEditModal() { return document.getElementById("skinEditModal"); },
  get skinEditModalTitle() { return document.getElementById("skinEditModalTitle"); },
  get skinEditModalCloseBtn() { return document.getElementById("skinEditModalCloseBtn"); },
  get skinEditFilename() { return document.getElementById("skinEditFilename"); },
  get skinEditCategorySelect() { return document.getElementById("skinEditCategorySelect"); },
  get skinEditWeaponSelect() { return document.getElementById("skinEditWeaponSelect"); },
  get skinEditNameInput() { return document.getElementById("skinEditNameInput"); },
  get skinEditFilenamePreview() { return document.getElementById("skinEditFilenamePreview"); },
  get skinEditSaveBtn() { return document.getElementById("skinEditSaveBtn"); },
  get skinEditCancelBtn() { return document.getElementById("skinEditCancelBtn"); },
};

export const WEAPONS_BY_CATEGORY = {
  pistols: [
    { id: "usp", label: "USP-S" },
    { id: "glock18", label: "Glock-18" },
    { id: "deagle", label: "Desert Eagle" },
    { id: "p228", label: "P228" },
    { id: "elites", label: "Dual Elites" },
    { id: "fiveseven", label: "Five-SeveN" },
  ],
  rifles: [
    { id: "ak47", label: "AK-47" },
    { id: "m4a1", label: "M4A1-S" },
    { id: "m4a4", label: "M4A4" },
    { id: "awp", label: "AWP" },
    { id: "scout", label: "Scout" },
    { id: "galil", label: "Galil" },
    { id: "famas", label: "FAMAS" },
    { id: "sg552", label: "SG 552" },
    { id: "aug", label: "AUG" },
    { id: "g3sg1", label: "G3SG1" },
    { id: "sg550", label: "SG 550" },
  ],
  smgs: [
    { id: "mp5", label: "MP5" },
    { id: "p90", label: "P90" },
    { id: "ump45", label: "UMP-45" },
    { id: "mac10", label: "MAC-10" },
    { id: "tmp", label: "TMP" },
  ],
  heavy: [
    { id: "m3", label: "M3 Super 90" },
    { id: "xm1014", label: "XM1014" },
    { id: "m249", label: "M249" },
  ],
  knives: [
    { id: "knife", label: "Default Knife" },
    { id: "knife_karambit", label: "Karambit" },
    { id: "knife_butterfly", label: "Butterfly" },
    { id: "knife_m9", label: "M9 Bayonet" },
    { id: "knife_bayonet", label: "Bayonet" },
    { id: "knife_huntsman", label: "Huntsman" },
    { id: "knife_bowie", label: "Bowie" },
    { id: "knife_flip", label: "Flip" },
    { id: "knife_gut", label: "Gut" },
    { id: "knife_falchion", label: "Falchion" },
    { id: "knife_daggers", label: "Shadow Daggers" },
    { id: "knife_skeleton", label: "Skeleton" },
    { id: "knife_nomad", label: "Nomad" },
    { id: "knife_paracord", label: "Paracord" },
    { id: "knife_survival", label: "Survival" },
    { id: "knife_classic", label: "Classic" },
  ],
  gloves: [
    { id: "sport_gloves", label: "Sport Gloves" },
    { id: "specialist_gloves", label: "Specialist" },
    { id: "moto_gloves", label: "Moto Gloves" },
    { id: "hand_wraps", label: "Hand Wraps" },
    { id: "driver_gloves", label: "Driver Gloves" },
    { id: "hydra_gloves", label: "Hydra / Bloodhound" },
    { id: "sleeves", label: "Sleeves / Bare Arms" },
  ],
};

let pendingSkinUploadBase64 = null;
let pendingUploadBase64 = null;
let pendingUploadMode = "sticker"; // "sticker" or "skin"

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function initLibraryModule() {
  state.skinItems = state.skinItems || [];
  state.stickerItems = state.stickerItems || [];
  state.activeSkinTab = "all";
  state.activeKnifeType = "all";
  state.activeStickerCat = "all";
  state.skinSearch = "";
  state.stickerSearch = "";

  setupEventListeners();

  eventBus.on("library:openForSlot", (tex) => {
    openLibraryModalForSlot(tex);
  });

  eventBus.on("library:openGeneral", (destination) => {
    state.modalTargetDestination = destination;
    if (els.modalTitle) {
      els.modalTitle.textContent =
        destination === "bake" ? "Choose Sticker for Bake Surface" : "Choose Sticker for Slot Fine-Tuner";
    }
    openLibraryModalGeneral();
  });

  eventBus.on("model:loaded", () => {
    renderSkinLibraryGrid();
  });

  fetchLibraryData();
}

function setupEventListeners() {
  if (els.modalCloseBtn) {
    els.modalCloseBtn.addEventListener("click", () => {
      if (els.libraryModal) els.libraryModal.classList.add("hidden");
    });
  }

  // Picker Modal Tabs (Stickers / Skins / Gloves)
  if (els.modalLibraryTabs) {
    els.modalLibraryTabs.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        els.modalLibraryTabs.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activePickerTab = pill.dataset.pickerTab || "stickers";
        renderModalLibraryGrid();
      });
    });
  }

  // Picker Modal Search
  if (els.modalLibrarySearch) {
    els.modalLibrarySearch.addEventListener("input", (e) => {
      state.pickerSearch = e.target.value.toLowerCase().trim();
      renderModalLibraryGrid();
    });
  }

  // --- SKIN LIBRARY CONTROLS ---
  state.activeSkinTab = state.activeSkinTab || "all";
  state.activeWeaponCategory = state.activeWeaponCategory || "all";
  state.activeWeaponType = state.activeWeaponType || "all";
  state.activeKnifeType = state.activeKnifeType || "all";
  state.activeGloveType = state.activeGloveType || "all";

  if (els.skinCategoryTabs) {
    els.skinCategoryTabs.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        els.skinCategoryTabs.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activeSkinTab = pill.dataset.tab || "all";

        if (state.activeSkinTab === "weapons") {
          if (els.weaponCategoryFilters) els.weaponCategoryFilters.classList.remove("hidden");
          if (state.activeWeaponCategory && state.activeWeaponCategory !== "all") {
            if (els.weaponSubcatFilters) els.weaponSubcatFilters.classList.remove("hidden");
          } else {
            if (els.weaponSubcatFilters) els.weaponSubcatFilters.classList.add("hidden");
          }
          if (els.knifeSubcatFilters) els.knifeSubcatFilters.classList.add("hidden");
          if (els.gloveSubcatFilters) els.gloveSubcatFilters.classList.add("hidden");
        } else if (state.activeSkinTab === "knives") {
          if (els.knifeSubcatFilters) els.knifeSubcatFilters.classList.remove("hidden");
          if (els.weaponCategoryFilters) els.weaponCategoryFilters.classList.add("hidden");
          if (els.weaponSubcatFilters) els.weaponSubcatFilters.classList.add("hidden");
          if (els.gloveSubcatFilters) els.gloveSubcatFilters.classList.add("hidden");
        } else if (state.activeSkinTab === "gloves") {
          if (els.gloveSubcatFilters) els.gloveSubcatFilters.classList.remove("hidden");
          if (els.weaponCategoryFilters) els.weaponCategoryFilters.classList.add("hidden");
          if (els.weaponSubcatFilters) els.weaponSubcatFilters.classList.add("hidden");
          if (els.knifeSubcatFilters) els.knifeSubcatFilters.classList.add("hidden");
        } else {
          // 'all'
          if (els.weaponCategoryFilters) els.weaponCategoryFilters.classList.add("hidden");
          if (els.weaponSubcatFilters) els.weaponSubcatFilters.classList.add("hidden");
          if (els.knifeSubcatFilters) els.knifeSubcatFilters.classList.add("hidden");
          if (els.gloveSubcatFilters) els.gloveSubcatFilters.classList.add("hidden");
        }
        renderSkinLibraryGrid();
      });
    });
  }

  if (els.weaponCategoryFilters) {
    els.weaponCategoryFilters.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        els.weaponCategoryFilters.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activeWeaponCategory = pill.dataset.weaponCat || "all";
        state.activeWeaponType = "all";
        renderWeaponSubcatFilters(state.activeWeaponCategory);
        renderSkinLibraryGrid();
      });
    });
  }

  if (els.knifeSubcatFilters) {
    els.knifeSubcatFilters.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        els.knifeSubcatFilters.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activeKnifeType = pill.dataset.knifeType || "all";
        renderSkinLibraryGrid();
      });
    });
  }

  if (els.gloveSubcatFilters) {
    els.gloveSubcatFilters.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        els.gloveSubcatFilters.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activeGloveType = pill.dataset.gloveType || "all";
        renderSkinLibraryGrid();
      });
    });
  }

  if (els.skinSearchInput) {
    els.skinSearchInput.addEventListener("input", (e) => {
      state.skinSearch = e.target.value.toLowerCase().trim();
      renderSkinLibraryGrid();
    });
  }

  if (els.skinBatchFilesBtn) {
    els.skinBatchFilesBtn.addEventListener("click", () => {
      if (els.skinFileInput) els.skinFileInput.click();
    });
  }

  if (els.skinBatchFolderBtn) {
    els.skinBatchFolderBtn.addEventListener("click", () => {
      if (els.skinFolderInput) els.skinFolderInput.click();
    });
  }

  if (els.skinFileInput) {
    els.skinFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleSkinFiles(e.target.files);
        e.target.value = "";
      }
    });
  }

  if (els.skinFolderInput) {
    els.skinFolderInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleSkinFiles(e.target.files);
        e.target.value = "";
      }
    });
  }

  if (els.skinDropZone) {
    els.skinDropZone.addEventListener("click", () => {
      if (els.skinFileInput) els.skinFileInput.click();
    });
    setupDragDrop(els.skinDropZone, handleSkinFiles);
  }

  if (els.drawerViewSkinLibrary) {
    els.drawerViewSkinLibrary.addEventListener("dragover", (e) => e.preventDefault());
    els.drawerViewSkinLibrary.addEventListener("drop", (e) => {
      if (e.target.closest("#skinDropZone")) return;
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleSkinFiles(e.dataTransfer.files);
      }
    });
  }

  // --- STICKER LIBRARY CONTROLS ---
  if (els.stickerCatFilters) {
    els.stickerCatFilters.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        els.stickerCatFilters.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.activeStickerCat = pill.dataset.cat || "all";
        renderStickerLibraryGrid();
      });
    });
  }

  if (els.stickerSearchInput) {
    els.stickerSearchInput.addEventListener("input", (e) => {
      state.stickerSearch = e.target.value.toLowerCase().trim();
      renderStickerLibraryGrid();
    });
  }

  if (els.stickerBatchFilesBtn) {
    els.stickerBatchFilesBtn.addEventListener("click", () => {
      if (els.stickerFileInput) els.stickerFileInput.click();
    });
  }

  if (els.stickerBatchFolderBtn) {
    els.stickerBatchFolderBtn.addEventListener("click", () => {
      if (els.stickerFolderInput) els.stickerFolderInput.click();
    });
  }

  if (els.stickerRestoreDefaultsBtn) {
    els.stickerRestoreDefaultsBtn.addEventListener("click", async () => {
      if (!confirm("Restore default tournament stickers? Existing custom stickers will not be touched.")) return;
      showLoader("Restoring default tournament stickers...");
      try {
        const res = await apiPost("/api/library/stickers/restore_defaults", {});
        showToast(res.message || "Default tournament stickers restored!", "success");
        await fetchLibraryData();
      } catch (err) {
        showToast(`Restore failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  if (els.stickerFileInput) {
    els.stickerFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        if (e.target.files.length === 1) {
          handleSingleStickerFile(e.target.files[0]);
        } else {
          handleStickerBatchFiles(e.target.files);
        }
        e.target.value = "";
      }
    });
  }

  if (els.stickerFolderInput) {
    els.stickerFolderInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleStickerBatchFiles(e.target.files);
        e.target.value = "";
      }
    });
  }

  if (els.stickerDropZone) {
    els.stickerDropZone.addEventListener("click", () => {
      if (els.stickerFileInput) els.stickerFileInput.click();
    });
    setupDragDrop(els.stickerDropZone, (files) => {
      if (files.length === 1) {
        handleSingleStickerFile(files[0]);
      } else {
        handleStickerBatchFiles(files);
      }
    });
  }

  if (els.drawerViewStickerLibrary) {
    els.drawerViewStickerLibrary.addEventListener("dragover", (e) => e.preventDefault());
    els.drawerViewStickerLibrary.addEventListener("drop", (e) => {
      if (e.target.closest("#stickerDropZone")) return;
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        if (e.dataTransfer.files.length === 1) {
          handleSingleStickerFile(e.dataTransfer.files[0]);
        } else {
          handleStickerBatchFiles(e.dataTransfer.files);
        }
      }
    });
  }

  // --- STICKER EDIT MODAL CONTROLS ---
  if (els.stickerEditModalCloseBtn) {
    els.stickerEditModalCloseBtn.addEventListener("click", closeStickerModal);
  }
  if (els.stickerEditCancelBtn) {
    els.stickerEditCancelBtn.addEventListener("click", closeStickerModal);
  }

  if (els.stickerEditSaveBtn) {
    els.stickerEditSaveBtn.addEventListener("click", async () => {
      const name = els.stickerEditNameInput ? els.stickerEditNameInput.value.trim() : "";
      if (!name) {
        showToast("Please enter a name.", "error");
        return;
      }
      const category = els.stickerEditCatInput ? els.stickerEditCatInput.value.trim() || "Custom / User" : "Custom / User";

      if (pendingUploadBase64) {
        const autoAlpha = Boolean(els.stickerUploadAutoAlpha && els.stickerUploadAutoAlpha.checked);
        showLoader(`Uploading custom sticker "${name}"...`);
        try {
          const res = await apiPost("/api/library/stickers/upload", {
            name,
            category,
            image_base64: pendingUploadBase64,
            auto_alpha: autoAlpha,
          });
          showToast(res.message || "Custom sticker uploaded!", "success");
          closeStickerModal();
          await fetchLibraryData();
        } catch (err) {
          showToast(`Upload failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      } else {
        const filename = els.stickerEditFilename ? els.stickerEditFilename.value : "";
        if (!filename) {
          showToast("Missing sticker filename.", "error");
          return;
        }
        showLoader(`Updating "${name}"...`);
        try {
          const res = await apiPost("/api/library/stickers/edit", {
            filename,
            name,
            category,
          });
          showToast(res.message || "Sticker updated!", "success");
          closeStickerModal();
          await fetchLibraryData();
        } catch (err) {
          showToast(`Update failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      }
    });
  }

  // --- SKIN EDIT / REGISTRATION MODAL CONTROLS ---
  if (els.skinEditCategorySelect) {
    els.skinEditCategorySelect.addEventListener("change", (e) => {
      populateSkinWeaponSelect(e.target.value);
    });
  }

  if (els.skinEditWeaponSelect) {
    els.skinEditWeaponSelect.addEventListener("change", () => {
      updateSkinFilenamePreview();
    });
  }

  if (els.skinEditNameInput) {
    els.skinEditNameInput.addEventListener("input", () => {
      updateSkinFilenamePreview();
    });
  }

  if (els.skinEditModalCloseBtn) {
    els.skinEditModalCloseBtn.addEventListener("click", closeSkinModal);
  }
  if (els.skinEditCancelBtn) {
    els.skinEditCancelBtn.addEventListener("click", closeSkinModal);
  }

  if (els.skinEditSaveBtn) {
    els.skinEditSaveBtn.addEventListener("click", async () => {
      const skinName = els.skinEditNameInput ? els.skinEditNameInput.value.trim() : "";
      if (!skinName) {
        showToast("Please enter a skin name.", "error");
        return;
      }
      const category = els.skinEditCategorySelect ? els.skinEditCategorySelect.value : "pistols";
      const weapon = els.skinEditWeaponSelect ? els.skinEditWeaponSelect.value : "usp";
      const wepOpt = els.skinEditWeaponSelect ? els.skinEditWeaponSelect.selectedOptions[0] : null;
      const wepLabel = wepOpt ? wepOpt.textContent : weapon.toUpperCase();

      if (pendingSkinUploadBase64) {
        showLoader(`Registering skin "${skinName}" for ${wepLabel}...`);
        try {
          const res = await apiPost("/api/library/skins/upload", {
            name: `${wepLabel} ${skinName}`,
            skin_name: skinName,
            weapon: weapon,
            weapon_category: category,
            category: category.charAt(0).toUpperCase() + category.slice(1),
            image_base64: pendingSkinUploadBase64,
          });
          showToast(res.message || `Registered "${wepLabel} ${skinName}" into Skin Library!`, "success");
          closeSkinModal();
          await fetchLibraryData();
        } catch (err) {
          showToast(`Registration failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      } else {
        const filename = els.skinEditFilename ? els.skinEditFilename.value : "";
        if (!filename) {
          showToast("Missing skin filename.", "error");
          return;
        }
        showLoader(`Updating "${skinName}"...`);
        try {
          const res = await apiPost("/api/library/skins/edit", {
            filename,
            name: `${wepLabel} ${skinName}`,
            skin_name: skinName,
            weapon: weapon,
            weapon_category: category,
          });
          showToast(res.message || "Skin details updated!", "success");
          closeSkinModal();
          await fetchLibraryData();
        } catch (err) {
          showToast(`Update failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      }
    });
  }
}

function setupDragDrop(dropZone, callback) {
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove("drag-over");
  });
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      callback(e.dataTransfer.files);
    }
  });
}

function readFileAsDataUri(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = () => resolve("");
    reader.readAsDataURL(file);
  });
}

// Single sticker upload with details modal
function handleSingleStickerFile(file) {
  if (!file) return;
  const validTypes = ["image/png", "image/jpeg", "image/bmp", "image/webp"];
  if (!validTypes.includes(file.type) && !/\.(png|jpe?g|bmp|webp)$/i.test(file.name)) {
    showToast("Unsupported image format. Use PNG, JPG, BMP, or WEBP.", "error");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    pendingUploadBase64 = e.target.result;
    openStickerModalForUpload(file.name);
  };
  reader.readAsDataURL(file);
}

// Batch sticker uploads
async function handleStickerBatchFiles(fileList) {
  if (!fileList || fileList.length === 0) return;
  const files = Array.from(fileList).filter((f) => /\.(png|jpe?g|bmp|webp)$/i.test(f.name));
  if (files.length === 0) {
    showToast("No supported sticker images found (PNG, JPG, BMP, WEBP).", "error");
    return;
  }

  if (els.stickerUploadProgress) {
    els.stickerUploadProgress.classList.remove("hidden");
  }

  let totalUploaded = 0;
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const dataUri = await readFileAsDataUri(file);
    const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");

    const pct = Math.round(((i + 1) / files.length) * 100);
    if (els.stickerUploadProgressText) els.stickerUploadProgressText.textContent = `Ingesting sticker ${i + 1} / ${files.length}...`;
    if (els.stickerUploadProgressPercent) els.stickerUploadProgressPercent.textContent = `${pct}%`;
    if (els.stickerUploadProgressBar) els.stickerUploadProgressBar.style.width = `${pct}%`;

    try {
      const res = await apiPost("/api/library/stickers/upload", {
        name: cleanName,
        category: "Custom / User",
        image_base64: dataUri,
        auto_alpha: true,
      });
      if (res && res.success) totalUploaded++;
    } catch (err) {
      console.warn("Sticker batch item failed:", err);
    }
  }

  if (els.stickerUploadProgress) {
    els.stickerUploadProgress.classList.add("hidden");
  }
  showToast(`Successfully ingested ${totalUploaded} custom sticker(s)!`, "success");
  await fetchLibraryData();
}

// Handle skin file(s) ingestion
function handleSkinFiles(fileList) {
  if (!fileList || fileList.length === 0) return;
  const files = Array.from(fileList).filter((f) => /\.(png|jpe?g|bmp|webp)$/i.test(f.name));
  if (files.length === 0) {
    showToast("No supported skin images found (PNG, JPG, BMP, WEBP).", "error");
    return;
  }

  if (files.length === 1) {
    handleSingleSkinFile(files[0]);
  } else {
    handleSkinBatchFiles(files);
  }
}

function handleSingleSkinFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    pendingSkinUploadBase64 = e.target.result;
    openSkinModalForUpload(file.name);
  };
  reader.readAsDataURL(file);
}

function inferWeaponCategoryAndName(filename) {
  const stem = filename.replace(/\.[^/.]+$/, "").toLowerCase();

  // 1. Search in all categories
  for (const [cat, weps] of Object.entries(WEAPONS_BY_CATEGORY)) {
    for (const w of weps) {
      if (stem.startsWith(w.id + "_") || stem === w.id) {
        const rem = stem.slice(w.id.length).replace(/^[_\-]+/, "");
        const skinName = rem ? rem.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Custom";
        return { category: cat, weapon: w.id, skinName };
      }
    }
  }

  // 2. Fallback to active weapon
  const curWep = (state.currentWeapon || "usp").toLowerCase();
  let defaultCat = "pistols";
  for (const [cat, weps] of Object.entries(WEAPONS_BY_CATEGORY)) {
    if (weps.some((w) => w.id === curWep)) {
      defaultCat = cat;
      break;
    }
  }

  const cleanName = filename.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return { category: defaultCat, weapon: curWep, skinName: cleanName };
}

function openSkinModalForUpload(originalFilename) {
  if (!els.skinEditModal) return;
  const inferred = inferWeaponCategoryAndName(originalFilename);

  if (els.skinEditModalTitle) {
    els.skinEditModalTitle.innerHTML = '<svg class="glyph glyph-md"><use href="#glyph-palette"></use></svg> Register Skin to Library';
  }
  if (els.skinEditFilename) els.skinEditFilename.value = "";
  if (els.skinEditCategorySelect) els.skinEditCategorySelect.value = inferred.category;
  populateSkinWeaponSelect(inferred.category, inferred.weapon);
  if (els.skinEditNameInput) els.skinEditNameInput.value = inferred.skinName;
  updateSkinFilenamePreview();

  els.skinEditModal.classList.remove("hidden");
  if (els.skinEditNameInput) els.skinEditNameInput.focus();
}

function openSkinModalForEdit(item) {
  if (!els.skinEditModal) return;
  pendingSkinUploadBase64 = null;

  if (els.skinEditModalTitle) {
    els.skinEditModalTitle.innerHTML = '<svg class="glyph glyph-md"><use href="#glyph-tune"></use></svg> Edit Skin Details';
  }
  if (els.skinEditFilename) els.skinEditFilename.value = item.filename || "";

  let cat = item.weapon_category || "pistols";
  if (!WEAPONS_BY_CATEGORY[cat]) {
    cat = item.knife_type ? "knives" : /glove|arm/i.test(item.category || "") ? "gloves" : "pistols";
  }

  let wep = item.weapon || "usp";
  if (!wep && item.knife_type) {
    wep = "knife_" + item.knife_type.toLowerCase().replace(/ /g, "_");
  }

  if (els.skinEditCategorySelect) els.skinEditCategorySelect.value = cat;
  populateSkinWeaponSelect(cat, wep);
  if (els.skinEditNameInput) els.skinEditNameInput.value = item.skin_name || item.name || "";
  updateSkinFilenamePreview();

  els.skinEditModal.classList.remove("hidden");
  if (els.skinEditNameInput) els.skinEditNameInput.focus();
}

function closeSkinModal() {
  if (els.skinEditModal) els.skinEditModal.classList.add("hidden");
  pendingSkinUploadBase64 = null;
  if (els.skinEditFilename) els.skinEditFilename.value = "";
  if (els.skinEditNameInput) els.skinEditNameInput.value = "";
}

function populateSkinWeaponSelect(category, selectedWeapon = "") {
  if (!els.skinEditWeaponSelect) return;
  els.skinEditWeaponSelect.innerHTML = "";
  const list = WEAPONS_BY_CATEGORY[category] || WEAPONS_BY_CATEGORY.pistols;
  list.forEach((w) => {
    const opt = document.createElement("option");
    opt.value = w.id;
    opt.textContent = w.label;
    if (w.id === selectedWeapon) opt.selected = true;
    els.skinEditWeaponSelect.appendChild(opt);
  });
  updateSkinFilenamePreview();
}

function updateSkinFilenamePreview() {
  if (!els.skinEditFilenamePreview) return;
  const wep = els.skinEditWeaponSelect ? els.skinEditWeaponSelect.value : "weapon";
  const name = els.skinEditNameInput ? els.skinEditNameInput.value.trim() : "";
  const cleanName = (name || "skin").toLowerCase().replace(/[^a-z0-9_\-]/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "");
  els.skinEditFilenamePreview.textContent = `${wep}_${cleanName || "skin"}.png`;
}

// Batch skin uploads with heuristic metadata detection
async function handleSkinBatchFiles(fileList) {
  if (!fileList || fileList.length === 0) return;
  const files = Array.from(fileList).filter((f) => /\.(png|jpe?g|bmp|webp)$/i.test(f.name));
  if (files.length === 0) {
    showToast("No supported skin images found (PNG, JPG, BMP, WEBP).", "error");
    return;
  }

  if (els.skinUploadProgress) {
    els.skinUploadProgress.classList.remove("hidden");
  }

  let totalUploaded = 0;
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const dataUri = await readFileAsDataUri(file);
    const inferred = inferWeaponCategoryAndName(file.name);

    const pct = Math.round(((i + 1) / files.length) * 100);
    if (els.skinUploadProgressText) els.skinUploadProgressText.textContent = `Ingesting skin ${i + 1} / ${files.length}...`;
    if (els.skinUploadProgressPercent) els.skinUploadProgressPercent.textContent = `${pct}%`;
    if (els.skinUploadProgressBar) els.skinUploadProgressBar.style.width = `${pct}%`;

    try {
      const res = await apiPost("/api/library/skins/upload", {
        name: `${inferred.weapon.toUpperCase()} ${inferred.skinName}`,
        skin_name: inferred.skinName,
        weapon: inferred.weapon,
        weapon_category: inferred.category,
        category: inferred.category.charAt(0).toUpperCase() + inferred.category.slice(1),
        image_base64: dataUri,
      });
      if (res && res.success) totalUploaded++;
    } catch (err) {
      console.warn("Skin batch item failed:", err);
    }
  }

  if (els.skinUploadProgress) {
    els.skinUploadProgress.classList.add("hidden");
  }
  showToast(`Successfully ingested ${totalUploaded} weapon skin(s) with auto-registered metadata!`, "success");
  await fetchLibraryData();
}

function openStickerModalForUpload(originalFilename) {
  if (!els.stickerEditModal) return;
  const cleanName = originalFilename.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");

  if (els.stickerEditModalTitle) {
    els.stickerEditModalTitle.innerHTML = '<svg class="glyph glyph-md"><use href="#glyph-sparkle"></use></svg> Upload Custom Sticker';
  }
  if (els.stickerEditFilename) els.stickerEditFilename.value = "";
  if (els.stickerEditNameInput) els.stickerEditNameInput.value = cleanName;
  if (els.stickerEditCatInput) els.stickerEditCatInput.value = "Custom / User";
  if (els.stickerUploadAlphaRow) els.stickerUploadAlphaRow.style.display = "block";
  if (els.stickerUploadAutoAlpha) els.stickerUploadAutoAlpha.checked = true;

  els.stickerEditModal.classList.remove("hidden");
  if (els.stickerEditNameInput) els.stickerEditNameInput.focus();
}

function openStickerModalForEdit(item) {
  if (!els.stickerEditModal) return;
  pendingUploadBase64 = null;

  if (els.stickerEditModalTitle) {
    els.stickerEditModalTitle.innerHTML = '<svg class="glyph glyph-md"><use href="#glyph-tune"></use></svg> Edit Sticker Details';
  }
  if (els.stickerEditFilename) els.stickerEditFilename.value = item.filename || "";
  if (els.stickerEditNameInput) els.stickerEditNameInput.value = item.name || "";
  if (els.stickerEditCatInput) els.stickerEditCatInput.value = item.category || "Custom / User";
  if (els.stickerUploadAlphaRow) els.stickerUploadAlphaRow.style.display = "none";

  els.stickerEditModal.classList.remove("hidden");
  if (els.stickerEditNameInput) els.stickerEditNameInput.focus();
}

function closeStickerModal() {
  if (els.stickerEditModal) els.stickerEditModal.classList.add("hidden");
  pendingUploadBase64 = null;
  if (els.stickerEditFilename) els.stickerEditFilename.value = "";
  if (els.stickerEditNameInput) els.stickerEditNameInput.value = "";
}

export async function fetchLibraryData() {
  try {
    const [stickersRes, skinsRes] = await Promise.all([
      apiGet("/api/library/stickers"),
      apiGet("/api/library/skins"),
    ]);

    state.stickerItems = (stickersRes.stickers || []).map((s) => ({ ...s, asset_type: "stickers" }));
    state.skinItems = (skinsRes.skins || []).map((sk) => ({ ...sk, asset_type: "weapons" }));
    state.libraryItems = [...state.stickerItems, ...state.skinItems];

    renderSkinLibraryGrid();
    renderStickerLibraryGrid();
  } catch (err) {
    console.warn("Failed to load asset libraries:", err);
  }
}

/**
 * Render Tier 2 Specific Weapon Filters for selected category
 */
export function renderWeaponSubcatFilters(category) {
  if (!els.weaponSubcatFilters) return;
  els.weaponSubcatFilters.innerHTML = "";

  if (!category || category === "all" || !WEAPONS_BY_CATEGORY[category]) {
    els.weaponSubcatFilters.classList.add("hidden");
    return;
  }

  els.weaponSubcatFilters.classList.remove("hidden");
  const catNames = {
    pistols: "Pistols",
    rifles: "Rifles & Snipers",
    smgs: "SMGs",
    heavy: "Heavy Weapons",
  };
  const label = catNames[category] || category;

  // 1. "All <Category>" pill
  const allBtn = document.createElement("button");
  allBtn.type = "button";
  allBtn.className = "filter-pill" + (state.activeWeaponType === "all" ? " active" : "");
  allBtn.dataset.weaponType = "all";
  allBtn.textContent = `All ${label}`;
  allBtn.addEventListener("click", () => {
    els.weaponSubcatFilters.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
    allBtn.classList.add("active");
    state.activeWeaponType = "all";
    renderSkinLibraryGrid();
  });
  els.weaponSubcatFilters.appendChild(allBtn);

  // 2. Specific weapons in category
  const list = WEAPONS_BY_CATEGORY[category] || [];
  list.forEach((w) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "filter-pill" + (state.activeWeaponType === w.id ? " active" : "");
    btn.dataset.weaponType = w.id;
    btn.textContent = w.label;
    btn.addEventListener("click", () => {
      els.weaponSubcatFilters.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      state.activeWeaponType = w.id;
      renderSkinLibraryGrid();
    });
    els.weaponSubcatFilters.appendChild(btn);
  });
}

/**
 * Render Skin Assets Library Grid (zero tags)
 */
export function renderSkinLibraryGrid() {
  if (!els.skinLibraryGrid) return;
  els.skinLibraryGrid.innerHTML = "";

  const filtered = (state.skinItems || []).filter((item) => {
    const itemName = (item.name || "").toLowerCase();
    const itemCat = (item.category || "").toLowerCase();
    const itemWep = (item.weapon || "").toLowerCase();
    const isKnife = Boolean(item.knife_type) || itemName.includes("knife") || itemWep.includes("knife");
    const isGlove = /glove|arm|sleeve/i.test(itemName) || /glove|arm|sleeve/i.test(itemCat) || /glove|arm|sleeve/i.test(itemWep);
    const isWeapon = !isKnife && !isGlove;

    // 1. Primary Tab filter
    if (state.activeSkinTab === "knives" && !isKnife) return false;
    if (state.activeSkinTab === "gloves" && !isGlove) return false;
    if (state.activeSkinTab === "weapons" && !isWeapon) return false;

    // 2. Weapons Sub-filters (Tier 1 Category & Tier 2 Weapon ID)
    if (state.activeSkinTab === "weapons") {
      if (state.activeWeaponCategory && state.activeWeaponCategory !== "all") {
        const catWeps = (WEAPONS_BY_CATEGORY[state.activeWeaponCategory] || []).map((w) => w.id);
        const matchesCat = item.weapon_category === state.activeWeaponCategory || catWeps.includes(item.weapon);
        if (!matchesCat) return false;
      }
      if (state.activeWeaponType && state.activeWeaponType !== "all") {
        const targetWep = state.activeWeaponType.toLowerCase();
        const matchesWep = item.weapon === targetWep ||
                           itemName.includes(targetWep) ||
                           (item.filename || "").toLowerCase().startsWith(targetWep + "_");
        if (!matchesWep) return false;
      }
    }

    // 3. Knife archetype
    if (state.activeSkinTab === "knives" && state.activeKnifeType && state.activeKnifeType !== "all") {
      if (item.knife_type !== state.activeKnifeType) return false;
    }

    // 4. Glove archetype
    if (state.activeSkinTab === "gloves" && state.activeGloveType && state.activeGloveType !== "all") {
      const gType = state.activeGloveType.toLowerCase();
      const combined = `${itemName} ${itemCat} ${itemWep}`;
      if (gType === "sport" && !combined.includes("sport")) return false;
      if (gType === "specialist" && !combined.includes("specialist")) return false;
      if (gType === "moto" && !combined.includes("moto")) return false;
      if (gType === "handwrap" && !combined.includes("handwrap") && !combined.includes("hand wrap")) return false;
      if (gType === "driver" && !combined.includes("driver")) return false;
      if (gType === "hydra" && !combined.includes("hydra")) return false;
      if (gType === "bloodhound" && !combined.includes("bloodhound")) return false;
      if (gType === "sleeve" && !combined.includes("sleeve") && !combined.includes("arm")) return false;
    }

    // 5. Search query
    if (state.skinSearch) {
      const q = state.skinSearch;
      const nameMatch = itemName.includes(q);
      const skinNameMatch = (item.skin_name || "").toLowerCase().includes(q);
      const wepMatch = itemWep.includes(q);
      const catMatch = itemCat.includes(q);
      const knifeMatch = (item.knife_type || "").toLowerCase().includes(q);
      if (!nameMatch && !skinNameMatch && !wepMatch && !catMatch && !knifeMatch) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    els.skinLibraryGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">
        No skin assets found matching your criteria.
      </div>
    `;
    return;
  }

  filtered.forEach((item) => {
    const card = document.createElement("div");
    card.className = "library-card";
    const previewUri = item.preview || item.thumbnail || "";

    let cardActionsTopHtml = "";
    if (item.is_custom) {
      cardActionsTopHtml = `
        <div class="library-card-actions-top">
          <button type="button" class="library-action-icon-btn btn-edit-skin" title="Edit skin details">
            <svg class="glyph glyph-xs"><use href="#glyph-tune"></use></svg>
          </button>
          <button type="button" class="library-action-icon-btn btn-del" title="Delete skin">
            <svg class="glyph glyph-xs"><use href="#glyph-trash"></use></svg>
          </button>
        </div>
      `;
    }

    const curWep = (state.currentWeapon || "usp").toLowerCase();
    const itemWep = (item.weapon || "").toLowerCase();
    const isGlove = /glove|arm|sleeve/i.test(item.name || "") || /glove|arm|sleeve/i.test(item.category || "");
    const isDifferentWeapon = Boolean(itemWep) && itemWep !== curWep && !isGlove && !item.knife_type;

    let applyBtnText = "Apply Skin";
    let applyBtnIcon = "#glyph-bolt";
    if (isDifferentWeapon) {
      applyBtnText = `Switch to ${itemWep.toUpperCase()} & Apply`;
      applyBtnIcon = "#glyph-restore";
    } else if (isGlove) {
      applyBtnText = "Apply Gloves";
      applyBtnIcon = "#glyph-glove";
    }

    card.innerHTML = `
      ${cardActionsTopHtml}
      <div class="library-thumb-wrap">
        <img src="${previewUri}" alt="${escapeHtml(item.name)}">
      </div>
      <div class="library-card-info">
        <span class="library-card-title">${escapeHtml(item.skin_name || item.name)}</span>
        <span class="library-card-cat">${escapeHtml((item.weapon ? item.weapon.toUpperCase() + " • " : "") + (item.knife_type || item.category || "Custom Weapon Skin"))}</span>
      </div>
      <div class="library-quick-actions">
        <button type="button" class="action-pill apply-skin-btn" title="Stage preview on 3D model">
          <svg class="glyph glyph-xs"><use href="${applyBtnIcon}"></use></svg> ${escapeHtml(applyBtnText)}
        </button>
      </div>
    `;

    if (item.is_custom) {
      const editBtn = card.querySelector(".btn-edit-skin");
      if (editBtn) {
        editBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          openSkinModalForEdit(item);
        });
      }

      const delBtn = card.querySelector(".btn-del");
      if (delBtn) {
        delBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (!confirm(`Delete custom skin "${item.name}"?`)) return;
          showLoader(`Deleting skin "${item.name}"...`);
          try {
            const res = await apiPost("/api/library/skins/delete", { filename: item.filename });
            showToast(res.message || "Skin deleted.", "success");
            await fetchLibraryData();
          } catch (err) {
            showToast(`Delete failed: ${err.message}`, "error");
          } finally {
            hideLoader();
          }
        });
      }
    }

    const applyBtn = card.querySelector(".apply-skin-btn");
    if (applyBtn) {
      applyBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        try {
          // 1. If skin belongs to a different weapon model, switch weapon first
          if (isDifferentWeapon) {
            showLoader(`Switching to ${itemWep.toUpperCase()}...`);
            if (typeof window.loadModel === "function") {
              await window.loadModel(itemWep, state.currentTeam);
            } else {
              state.currentWeapon = itemWep;
              const res = await apiGet(`/api/model?team=${state.currentTeam}&weapon=${itemWep}`);
              state.modelData = res;
              state.pendingSlotUpdates = {};
              eventBus.emit("model:loaded", res);
            }
            hideLoader();
          }

          if (!state.modelData || !state.modelData.textures || state.modelData.textures.length === 0) {
            showToast("No active model loaded to apply skin.", "error");
            return;
          }

          const uri = item.preview || item.thumbnail || "";
          if (!uri && !item.path) {
            showToast("No texture data available for this skin.", "error");
            return;
          }

          if (isGlove) {
            openApplyGlovesPromptModal(item);
            return;
          } else {
            // Weapon Skin
            const skinSlots = state.modelData.textures.filter((t) => t.role === "skin");
            let targetSlot = skinSlots[0] || state.modelData.textures[0];

            if (skinSlots.length > 1) {
              const lowerItem = (item.name || "").toLowerCase();
              const matched = skinSlots.find((s) => lowerItem.includes(s.name.replace(/\.[^.]+$/, "").toLowerCase()));
              if (matched) targetSlot = matched;
            }

            state.pendingSlotUpdates[targetSlot.index] = {
              image_path: item.path,
              base64: uri,
              previewUri: uri,
              mode: targetSlot.is_masked ? "fit" : "stretch",
              scale: 1.0,
            };
            refreshSlotPreview(targetSlot);
            eventBus.emit("slot:textureUpdated", {
              textureIndex: targetSlot.index,
              previewUri: uri,
            });

            showToast(`Staged "${item.name}" on ${targetSlot.name}. Click 'Inject Texture' to commit.`, "success");
          }

          // Switch to "Slots & Assets" inspector tab so user sees staged slot and 'Inject Texture' button
          const slotsNavTab = document.querySelector('.nav-tab[data-tab="slots"]');
          if (slotsNavTab) slotsNavTab.click();

        } catch (err) {
          showToast(`Apply failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      });
    }

    card.style.cursor = "pointer";
    card.addEventListener("click", (e) => {
      if (e.target.closest("button") || e.target.closest(".library-action-icon-btn")) return;
      if (applyBtn) applyBtn.click();
    });

    els.skinLibraryGrid.appendChild(card);
  });
}

/**
 * Mirror an image base64 data URI horizontally via canvas
 */
function mirrorImageBase64(srcUri) {
  return new Promise((resolve) => {
    if (!srcUri) return resolve("");
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const c = document.createElement("canvas");
        c.width = img.width;
        c.height = img.height;
        const ctx = c.getContext("2d");
        ctx.translate(c.width, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(img, 0, 0);
        resolve(c.toDataURL("image/png"));
      } catch (e) {
        console.warn("mirrorImageBase64 error:", e);
        resolve(srcUri);
      }
    };
    img.onerror = () => resolve(srcUri);
    img.src = srcUri;
  });
}

/**
 * Opens the interactive Apply Gloves destination prompt modal
 */
function openApplyGlovesPromptModal(item) {
  const modal = document.getElementById("applyGlovesModal");
  if (!modal) return;

  const closeBtn = document.getElementById("applyGlovesCloseBtn");
  const thumb = document.getElementById("applyGloveThumb");
  const nameEl = document.getElementById("applyGloveName");
  const catEl = document.getElementById("applyGloveCategory");
  const metaEl = document.getElementById("applyGloveMeta");
  const activeWepLabel = document.getElementById("applyGloveActiveWepLabel");
  const slotsList = document.getElementById("applyGloveSlotsList");
  const mirrorCheck = document.getElementById("applyGloveMirrorCheck");
  const sleeveNotice = document.getElementById("applyGloveSleeveNotice");
  const sleeveNameList = document.getElementById("applyGloveSleeveNameList");
  const previewActiveBtn = document.getElementById("applyGlovePreviewActiveBtn");
  const commitActiveBtn = document.getElementById("applyGloveCommitActiveBtn");
  const sendToBatchBtn = document.getElementById("applyGloveSendToBatchBtn");
  const batchAllBtn = document.getElementById("applyGloveBatchAllBtn");

  const uri = item.preview || item.thumbnail || "";
  const gloveName = item.skin_name || item.name || "Glove";
  const curWep = (state.currentWeapon || "usp").toUpperCase();

  if (thumb) thumb.src = uri;
  if (nameEl) nameEl.textContent = gloveName;
  if (catEl) catEl.textContent = item.category || "Gloves";
  if (metaEl) metaEl.textContent = item.path ? item.path.split(/[/\\]/).pop() : "Texture Ready";
  if (activeWepLabel) activeWepLabel.textContent = `v_${curWep.toLowerCase()}.mdl (${curWep})`;

  // Detect active model glove slots (STRICTLY role === 'glove', never sleeve)
  const allTextures = (state.modelData && state.modelData.textures) || [];
  const gloveSlots = allTextures.filter((t) => t.role === "glove" && t.role !== "sleeve" && !t.name.toLowerCase().includes("sleeve"));
  const sleeveSlots = allTextures.filter((t) => t.role === "sleeve" || t.name.toLowerCase().includes("sleeve"));

  if (slotsList) {
    slotsList.innerHTML = "";
    if (gloveSlots.length === 0) {
      slotsList.innerHTML = `<div style="font-size: 0.8rem; color: #ef4444; padding: 6px;">No glove texture slots detected in current model (v_${curWep.toLowerCase()}.mdl).</div>`;
      if (previewActiveBtn) previewActiveBtn.disabled = true;
      if (commitActiveBtn) commitActiveBtn.disabled = true;
    } else {
      if (previewActiveBtn) previewActiveBtn.disabled = false;
      if (commitActiveBtn) commitActiveBtn.disabled = false;
      gloveSlots.forEach((slot) => {
        const lower = slot.name.toLowerCase();
        const isRight = lower.includes("right") || lower.includes("_r") || lower.includes("hand_r");
        const handLabel = isRight ? "Right Hand" : "Left Hand";

        const row = document.createElement("label");
        row.className = "checkbox-label";
        row.style.cssText = "display: flex; align-items: center; gap: 8px; font-size: 0.84rem; padding: 5px 8px; background: rgba(0,0,0,0.25); border-radius: 4px; border: 1px solid var(--border-subtle); cursor: pointer;";
        row.innerHTML = `
          <input type="checkbox" class="glove-slot-checkbox" data-index="${slot.index}" data-is-right="${isRight}" checked style="cursor: pointer;">
          <span style="font-family: monospace; color: var(--accent-cyan); font-weight: 600;">${escapeHtml(slot.name)}</span>
          <span style="color: var(--text-dim); font-size: 0.76rem; margin-left: auto;">${slot.width}x${slot.height} • <strong style="color: ${isRight ? '#ec4899' : '#06b6d4'};">${handLabel}</strong></span>
        `;
        slotsList.appendChild(row);
      });
    }
  }

  // Update Sleeve Safe Notice
  if (sleeveNotice && sleeveNameList) {
    if (sleeveSlots.length > 0) {
      sleeveNotice.style.display = "flex";
      sleeveNameList.textContent = sleeveSlots.map((s) => s.name).join(", ");
    } else {
      sleeveNotice.style.display = "none";
    }
  }

  const closeModal = () => {
    modal.classList.add("hidden");
  };

  if (closeBtn) closeBtn.onclick = closeModal;

  // 1. Preview in 3D Action
  if (previewActiveBtn) {
    previewActiveBtn.onclick = async () => {
      const checkedBoxes = Array.from(modal.querySelectorAll(".glove-slot-checkbox:checked"));
      if (checkedBoxes.length === 0) {
        showToast("Please select at least one glove slot to preview.", "error");
        return;
      }
      showLoader("Staging glove preview...");
      try {
        const doMirror = Boolean(mirrorCheck && mirrorCheck.checked);
        let mirroredUri = null;

        for (const cb of checkedBoxes) {
          const idx = parseInt(cb.dataset.index, 10);
          const isRight = cb.dataset.isRight === "true";
          const slot = gloveSlots.find((s) => s.index === idx);
          if (!slot) continue;

          let targetUri = uri;
          if (isRight && doMirror) {
            if (!mirroredUri) mirroredUri = await mirrorImageBase64(uri);
            targetUri = mirroredUri;
          }

          state.pendingSlotUpdates[slot.index] = {
            image_path: item.path,
            base64: targetUri,
            previewUri: targetUri,
            mode: "stretch",
            scale: 1.0,
          };
          refreshSlotPreview(slot);
          eventBus.emit("slot:textureUpdated", {
            textureIndex: slot.index,
            previewUri: targetUri,
          });
        }
        showToast(`Staged "${gloveName}" on active model gloves! (Sleeves untouched)`, "success");
        closeModal();
      } catch (err) {
        showToast(`Preview failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    };
  }

  // 2. Commit & Inject to Active Model Action
  if (commitActiveBtn) {
    commitActiveBtn.onclick = async () => {
      const checkedBoxes = Array.from(modal.querySelectorAll(".glove-slot-checkbox:checked"));
      if (checkedBoxes.length === 0) {
        showToast("Please select at least one glove slot to inject.", "error");
        return;
      }
      showLoader(`Injecting gloves into ${curWep}...`);
      try {
        const doMirror = Boolean(mirrorCheck && mirrorCheck.checked);
        let mirroredUri = null;

        for (const cb of checkedBoxes) {
          const idx = parseInt(cb.dataset.index, 10);
          const isRight = cb.dataset.isRight === "true";
          const slot = gloveSlots.find((s) => s.index === idx);
          if (!slot) continue;

          let targetUri = uri;
          if (isRight && doMirror) {
            if (!mirroredUri) mirroredUri = await mirrorImageBase64(uri);
            targetUri = mirroredUri;
          }

          const res = await apiPost("/api/inject", {
            weapon: state.currentWeapon,
            team: state.currentTeam,
            texture_index: slot.index,
            texture_name: slot.name,
            image_base64: targetUri,
            image_path: (isRight && doMirror) ? null : item.path,
            mode: "stretch",
          });
          if (!res.success) {
            throw new Error(res.error || `Failed on slot ${slot.name}`);
          }
        }
        showToast(`Successfully injected "${gloveName}" into ${curWep}! Sleeves untouched.`, "success");
        closeModal();
        eventBus.emit("model:reloadRequest");
      } catch (err) {
        showToast(`Injection failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    };
  }

  // 3. Send to Batch Glove Injector Action
  if (sendToBatchBtn) {
    sendToBatchBtn.onclick = () => {
      const doMirror = Boolean(mirrorCheck && mirrorCheck.checked);
      eventBus.emit("gloves:loadIntoBatch", { dataUrl: uri, mirror: doMirror });

      // Switch dock tab to Gloves
      const dockTabGloves = document.getElementById("dockTabGloves");
      if (dockTabGloves) dockTabGloves.click();

      // Ensure Right Dock is expanded
      const dock = document.getElementById("studioInspectorDock");
      if (dock && dock.classList.contains("collapsed")) {
        const toggleDockBtn = document.getElementById("toggleDockBtn");
        if (toggleDockBtn) toggleDockBtn.click();
      }

      showToast(`Loaded "${gloveName}" into Batch Glove Injector.`, "success");
      closeModal();
    };
  }

  // 4. 1-Click Inject All Weapons Action
  if (batchAllBtn) {
    batchAllBtn.onclick = async () => {
      if (!confirm(`Inject "${gloveName}" across ALL weapon models in your loadout (CT & T)?`)) {
        return;
      }
      showLoader(`Batch injecting "${gloveName}" across all weapons...`);
      try {
        const res = await apiPost("/api/gloves/batch_inject_images", {
          left_image_base64: uri,
          left_image_path: item.path,
          mirror_left: true,
          team: "all",
        });
        if (!res.success) {
          throw new Error(res.error || "Batch injection failed.");
        }
        const count = res.total_models || (res.updated_models && res.updated_models.length) || "all";
        showToast(`Successfully injected "${gloveName}" across ${count} models!`, "success");
        closeModal();
        eventBus.emit("model:reloadRequest");
      } catch (err) {
        showToast(`Batch injection failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    };
  }

  modal.classList.remove("hidden");
}

/**
 * Render Sticker Assets Library Grid (zero tags)
 */
export function renderStickerLibraryGrid() {
  if (!els.stickerLibraryGrid) return;
  els.stickerLibraryGrid.innerHTML = "";

  const filtered = (state.stickerItems || []).filter((item) => {
    // 1. Style filter
    if (state.activeStickerCat && state.activeStickerCat !== "all") {
      if (item.category !== state.activeStickerCat) return false;
    }
    // 2. Search query
    if (state.stickerSearch) {
      const q = state.stickerSearch;
      const nameMatch = (item.name || "").toLowerCase().includes(q);
      const catMatch = (item.category || "").toLowerCase().includes(q);
      if (!nameMatch && !catMatch) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    els.stickerLibraryGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">
        No stickers found matching your criteria.
      </div>
    `;
    return;
  }

  filtered.forEach((item) => {
    const card = document.createElement("div");
    card.className = "library-card";
    const previewUri = item.preview || item.thumbnail || "";

    const actionsTopHtml = `
      <div class="library-card-actions-top">
        <button type="button" class="library-action-icon-btn btn-edit" title="Edit sticker details">
          <svg class="glyph glyph-xs"><use href="#glyph-tune"></use></svg>
        </button>
        <button type="button" class="library-action-icon-btn btn-del" title="Delete sticker">
          <svg class="glyph glyph-xs"><use href="#glyph-trash"></use></svg>
        </button>
      </div>
    `;

    card.innerHTML = `
      ${actionsTopHtml}
      <div class="library-thumb-wrap">
        <img src="${previewUri}" alt="${escapeHtml(item.name)}">
      </div>
      <div class="library-card-info">
        <span class="library-card-title">${escapeHtml(item.name)}</span>
        <span class="library-card-cat">${escapeHtml(item.category || "Tournament Sticker")}</span>
      </div>
      <div class="library-quick-actions">
        <button type="button" class="action-pill apply-slot-1-btn"><svg class="glyph glyph-xs"><use href="#glyph-bolt"></use></svg> Slot 1</button>
        <button type="button" class="action-pill apply-bake-btn"><svg class="glyph glyph-xs"><use href="#glyph-target"></use></svg> Bake</button>
      </div>
    `;

    const editBtn = card.querySelector(".btn-edit");
    if (editBtn) {
      editBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        openStickerModalForEdit(item);
      });
    }

    const delBtn = card.querySelector(".btn-del");
    if (delBtn) {
      delBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Delete sticker "${item.name}"? This cannot be undone.`)) return;
        showLoader(`Deleting sticker "${item.name}"...`);
        try {
          const res = await apiPost("/api/library/stickers/delete", { filename: item.filename });
          showToast(res.message || "Sticker deleted.", "success");
          await fetchLibraryData();
        } catch (err) {
          showToast(`Delete failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      });
    }

    const slot1Btn = card.querySelector(".apply-slot-1-btn");
    if (slot1Btn) {
      slot1Btn.addEventListener("click", () => {
        applyLibraryItemToSlot(item, 1);
      });
    }

    const bakeBtn = card.querySelector(".apply-bake-btn");
    if (bakeBtn) {
      bakeBtn.addEventListener("click", () => {
        eventBus.emit("bake:loadSticker", { previewUri: item.preview || item.thumbnail, path: item.path, name: item.name });
        const bakeTab = document.querySelector('.nav-tab[data-tab="bake"]');
        if (bakeTab) bakeTab.click();
      });
    }

    els.stickerLibraryGrid.appendChild(card);
  });
}

function openLibraryModalForSlot(tex) {
  state.targetModalSlot = tex;
  state.modalTargetDestination = "slot";

  // Context-aware defaults based on slot role
  if (tex.role === "skin") {
    state.activePickerTab = "skins";
    if (els.modalTitle) {
      els.modalTitle.textContent = `Choose Skin for Slot: ${tex.name} (${(state.currentWeapon || "weapon").toUpperCase()})`;
    }
    if (els.modalGloveBilateralWrap) els.modalGloveBilateralWrap.style.display = "none";
  } else if (tex.role === "glove") {
    state.activePickerTab = "gloves";
    if (els.modalTitle) {
      els.modalTitle.textContent = `Choose Glove / Sleeve for Slot: ${tex.name}`;
    }
    if (els.modalGloveBilateralWrap) els.modalGloveBilateralWrap.style.display = "flex";
  } else {
    state.activePickerTab = "stickers";
    if (els.modalTitle) {
      els.modalTitle.textContent = `Choose Sticker for Slot: ${tex.name}`;
    }
    if (els.modalGloveBilateralWrap) els.modalGloveBilateralWrap.style.display = "none";
  }

  // Update tabs in modal header
  if (els.modalLibraryTabs) {
    els.modalLibraryTabs.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.classList.toggle("active", pill.dataset.pickerTab === state.activePickerTab);
    });
  }

  if (els.modalLibrarySearch) {
    els.modalLibrarySearch.value = "";
    state.pickerSearch = "";
  }

  // Fetch glove presets if needed
  if (state.activePickerTab === "gloves" && (!state.glovePresets || state.glovePresets.length === 0)) {
    apiGet("/api/gloves/presets")
      .then((res) => {
        if (res && res.presets) state.glovePresets = res.presets;
        renderModalLibraryGrid();
      })
      .catch(() => renderModalLibraryGrid());
  } else {
    renderModalLibraryGrid();
  }

  if (els.libraryModal) els.libraryModal.classList.remove("hidden");
}

export function openLibraryModalGeneral() {
  state.activePickerTab = "stickers";
  if (els.modalGloveBilateralWrap) els.modalGloveBilateralWrap.style.display = "none";
  if (els.modalLibraryTabs) {
    els.modalLibraryTabs.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.classList.toggle("active", pill.dataset.pickerTab === "stickers");
    });
  }
  if (els.modalLibrarySearch) {
    els.modalLibrarySearch.value = "";
    state.pickerSearch = "";
  }
  renderModalLibraryGrid();
  if (els.libraryModal) els.libraryModal.classList.remove("hidden");
}

export function renderModalLibraryGrid() {
  if (!els.modalLibraryGrid || !els.libraryModal) return;
  els.modalLibraryGrid.innerHTML = "";

  const tab = state.activePickerTab || "stickers";
  const query = (state.pickerSearch || "").toLowerCase();
  let items = [];

  if (tab === "stickers") {
    items = (state.stickerItems || []).filter((item) => {
      if (!query) return true;
      return (item.name || "").toLowerCase().includes(query) || (item.category || "").toLowerCase().includes(query);
    });
  } else if (tab === "skins") {
    items = (state.skinItems || []).filter((item) => {
      if (!query) return true;
      return (item.name || "").toLowerCase().includes(query) ||
             (item.skin_name || "").toLowerCase().includes(query) ||
             (item.weapon || "").toLowerCase().includes(query) ||
             (item.category || "").toLowerCase().includes(query) ||
             (item.knife_type || "").toLowerCase().includes(query);
    });
    // Sort skins matching active weapon to the front
    const curWep = (state.currentWeapon || "").toLowerCase();
    items.sort((a, b) => {
      const aMatch = (a.weapon || "").toLowerCase() === curWep || (a.name || "").toLowerCase().includes(curWep);
      const bMatch = (b.weapon || "").toLowerCase() === curWep || (b.name || "").toLowerCase().includes(curWep);
      if (aMatch && !bMatch) return -1;
      if (!aMatch && bMatch) return 1;
      return 0;
    });
  } else if (tab === "gloves") {
    // 1. Glove Presets
    const presetItems = (state.glovePresets || []).map((p) => ({
      name: p.name,
      category: "Glove Preset",
      preview: p.right_thumb || p.left_thumb || p.right_image || p.left_image || "",
      is_preset: true,
      preset_data: p,
    }));
    // 2. Glove / Arm textures in skin library
    const skinGloveItems = (state.skinItems || []).filter((sk) => {
      const n = (sk.name || "").toLowerCase();
      const c = (sk.category || "").toLowerCase();
      return /glove|arm|sport|sleeve/i.test(n) || /glove|arm/i.test(c);
    });
    items = [...presetItems, ...skinGloveItems].filter((item) => {
      if (!query) return true;
      return (item.name || "").toLowerCase().includes(query) || (item.category || "").toLowerCase().includes(query);
    });
  }

  if (items.length === 0) {
    els.modalLibraryGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim); font-size: 0.85rem;">
        No ${tab} found matching "${escapeHtml(state.pickerSearch)}".
      </div>
    `;
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "library-card";
    card.style.padding = "10px";
    const previewUri = item.preview || item.thumbnail || "";
    card.innerHTML = `
      <div class="library-thumb-wrap" style="height: 100px;">
        <img src="${previewUri}" alt="${escapeHtml(item.name)}">
      </div>
      <div class="library-card-info">
        <span class="library-card-title" style="font-size: 0.85rem;">${escapeHtml(item.name)}</span>
        <span class="library-card-cat" style="font-size: 0.7rem;">${escapeHtml(item.category || "")}</span>
      </div>
    `;

    card.style.cursor = "pointer";
    card.addEventListener("click", () => {
      els.libraryModal.classList.add("hidden");

      if (state.modalTargetDestination === "bake") {
        eventBus.emit("bake:loadSticker", { previewUri: item.preview || item.thumbnail, path: item.path, name: item.name });
      } else if (state.modalTargetDestination === "slotTune") {
        state.slotTune.stickerDataUri = item.preview || item.thumbnail;
        const img = new Image();
        img.onload = () => {
          state.slotTune.stickerImg = img;
          const canvas = document.getElementById("slotTuneCanvas");
          if (canvas) {
            import("./slots.js").then((m) => m.renderSlotTuneCanvas());
          }
        };
        img.src = item.preview || item.thumbnail;
      } else if (state.modalTargetDestination === "slot" && state.targetModalSlot) {
        const isGloveSlot = state.targetModalSlot.role === "glove";
        const isBilateral = Boolean(els.modalGloveBilateralCheck && els.modalGloveBilateralCheck.checked);

        if (isGloveSlot && isBilateral && state.modelData && state.modelData.textures) {
          const gloveSlots = state.modelData.textures.filter((t) => t.role === "glove");
          if (item.is_preset && item.preset_data) {
            // Apply preset left/right images to respective glove slots
            gloveSlots.forEach((gSlot) => {
              const lower = gSlot.name.toLowerCase();
              const isLeft = lower.includes("left") || lower.includes("_l");
              const imgUri = isLeft ? (item.preset_data.left_image || item.preset_data.right_image) : (item.preset_data.right_image || item.preset_data.left_image);
              if (imgUri) {
                state.pendingSlotUpdates[gSlot.index] = {
                  base64: imgUri,
                  previewUri: imgUri,
                  mode: "stretch",
                  scale: 1.0,
                };
                refreshSlotPreview(gSlot);
              }
            });
            showToast(`Preset "${item.name}" staged across gloves. Click 'Inject Texture' to commit.`, "success");
          } else {
            // Single glove texture to all glove slots
            gloveSlots.forEach((gSlot) => {
              state.pendingSlotUpdates[gSlot.index] = {
                image_path: item.path,
                base64: item.preview || item.thumbnail,
                previewUri: item.preview || item.thumbnail,
                mode: "stretch",
                scale: 1.0,
              };
              refreshSlotPreview(gSlot);
            });
            showToast(`Staged "${item.name}" across left and right gloves. Click 'Inject Texture' to commit.`, "success");
          }
        } else {
          // Normal single slot staging (weapon skin, single glove, or sticker)
          state.pendingSlotUpdates[state.targetModalSlot.index] = {
            image_path: item.path,
            base64: item.preview || item.thumbnail,
            previewUri: item.preview || item.thumbnail,
            mode: state.targetModalSlot.is_masked ? "fit" : "stretch",
            scale: 1.0,
          };
          refreshSlotPreview(state.targetModalSlot);
          showToast(`Staged "${item.name}" for ${state.targetModalSlot.name}. Click 'Inject Texture' to commit.`, "success");
        }
      }
    });

    els.modalLibraryGrid.appendChild(card);
  });
}

function applyLibraryItemToSlot(item, slotNumber) {
  if (!state.modelData) return;
  const stickers = state.modelData.textures.filter((t) => t.role === "sticker");
  if (stickers.length === 0) {
    showToast("No sticker slots in active model.", "error");
    return;
  }

  const target = stickers[Math.min(slotNumber - 1, stickers.length - 1)];
  const uri = item.preview || item.thumbnail || "";
  state.pendingSlotUpdates[target.index] = {
    image_path: item.path,
    base64: uri,
    previewUri: uri,
    mode: "fit",
    scale: 1.0,
  };
  refreshSlotPreview(target);

  const slotsTab = document.querySelector('.nav-tab[data-tab="slots"]');
  if (slotsTab) slotsTab.click();
  showToast(`Sticker staged for slot ${target.name}. Click 'Inject Texture' to commit.`, "info");
}
