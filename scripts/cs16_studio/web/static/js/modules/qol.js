/**
 * modules/qol.js - Quality-of-Life (QoL) Enhancements Suite:
 * 1. Multi-Step Undo / Redo History Stack (Ctrl+Z / Ctrl+Y)
 * 2. Split-Screen Curtain Comparison Controls
 * 3. Quick Weapon Switcher Spotlight Modal (Ctrl+K or /)
 * 4. Color Eyedropper Tool
 * 5. 1-Click Export Mod Pack (.zip)
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

import { state, eventBus } from "../core/state.js";
import { apiPost, showToast, showLoader, hideLoader, elements } from "../core/api.js";

const qolEls = {
  get undoBtn() { return document.getElementById("undoBtn"); },
  get redoBtn() { return document.getElementById("redoBtn"); },
  get quickSearchBtn() { return document.getElementById("quickSearchBtn"); },
  get quickSwitcherModal() { return document.getElementById("quickSwitcherModal"); },
  get quickSwitcherInput() { return document.getElementById("quickSwitcherInput"); },
  get quickSwitcherResults() { return document.getElementById("quickSwitcherResults"); },
  get colorEyedropperBtn() { return document.getElementById("colorEyedropperBtn"); },
  get eyedropperSample() { return document.getElementById("eyedropperSample"); },
  get exportModpackBtn() { return document.getElementById("exportModpackBtn"); },
  get exportModpackModal() { return document.getElementById("exportModpackModal"); },
  get exportModalCloseBtn() { return document.getElementById("exportModalCloseBtn"); },
  get exportPackName() { return document.getElementById("exportPackName"); },
  get exportTeamAll() { return document.getElementById("exportTeamAll"); },
  get exportTeamCT() { return document.getElementById("exportTeamCT"); },
  get exportTeamT() { return document.getElementById("exportTeamT"); },
  get exportOnlyModified() { return document.getElementById("exportOnlyModified"); },
  get exportConfirmBtn() { return document.getElementById("exportConfirmBtn"); },
  get exportStatusArea() { return document.getElementById("exportStatusArea"); },
};

export function initQoLModule() {
  setupUndoRedo();
  setupQuickSwitcher();
  setupEyedropper();
  setupModpackExport();
}

// ==========================================
// QoL 1: MULTI-STEP UNDO / REDO HISTORY STACK
// ==========================================

function setupUndoRedo() {
  // Listen for history records from other modules
  eventBus.on("history:record", (entry) => {
    state.qol.undoStack.push(entry);
    if (state.qol.undoStack.length > 50) {
      state.qol.undoStack.shift();
    }
    state.qol.redoStack = []; // Clear redo stack on new action
    updateUndoRedoUI();
  });

  if (qolEls.undoBtn) {
    qolEls.undoBtn.addEventListener("click", () => performUndo());
  }

  if (qolEls.redoBtn) {
    qolEls.redoBtn.addEventListener("click", () => performRedo());
  }

  // Keyboard shortcut listener for Ctrl+Z and Ctrl+Y / Ctrl+Shift+Z
  window.addEventListener("keydown", (e) => {
    // Avoid triggering when user is typing in text inputs or textareas
    const tag = e.target.tagName.toLowerCase();
    if (tag === "input" || tag === "textarea" || e.target.isContentEditable) return;

    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === "z") {
      e.preventDefault();
      performUndo();
    } else if (
      ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") ||
      ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "z")
    ) {
      e.preventDefault();
      performRedo();
    }
  });

  updateUndoRedoUI();
}

function updateUndoRedoUI() {
  const canUndo = state.qol.undoStack.length > 0;
  const canRedo = state.qol.redoStack.length > 0;

  if (qolEls.undoBtn) {
    qolEls.undoBtn.disabled = !canUndo;
    if (canUndo) {
      const top = state.qol.undoStack[state.qol.undoStack.length - 1];
      qolEls.undoBtn.title = `Undo: ${top.description} (Ctrl+Z)`;
    } else {
      qolEls.undoBtn.title = "Nothing to undo (Ctrl+Z)";
    }
  }

  if (qolEls.redoBtn) {
    qolEls.redoBtn.disabled = !canRedo;
    if (canRedo) {
      const top = state.qol.redoStack[state.qol.redoStack.length - 1];
      qolEls.redoBtn.title = `Redo: ${top.description} (Ctrl+Y)`;
    } else {
      qolEls.redoBtn.title = "Nothing to redo (Ctrl+Y)";
    }
  }
}

async function performUndo() {
  if (state.qol.undoStack.length === 0) return;

  const action = state.qol.undoStack.pop();
  showLoader(`Undoing: ${action.description}...`);
  try {
    await action.undo();
    state.qol.redoStack.push(action);
    showToast(`Undone: ${action.description}`, "info");
    updateUndoRedoUI();

    if (action.weapon && (action.weapon.toLowerCase() !== state.currentWeapon.toLowerCase() || (action.team && action.team !== state.currentTeam))) {
      state.currentWeapon = action.weapon;
      if (action.team) state.currentTeam = action.team;
      if (elements.weaponSelect) elements.weaponSelect.value = state.currentWeapon;
    }
    eventBus.emit("model:reloadRequest");
  } catch (err) {
    showToast(`Undo failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function performRedo() {
  if (state.qol.redoStack.length === 0) return;

  const action = state.qol.redoStack.pop();
  showLoader(`Redoing: ${action.description}...`);
  try {
    await action.redo();
    state.qol.undoStack.push(action);
    showToast(`Redone: ${action.description}`, "info");
    updateUndoRedoUI();

    if (action.weapon && (action.weapon.toLowerCase() !== state.currentWeapon.toLowerCase() || (action.team && action.team !== state.currentTeam))) {
      state.currentWeapon = action.weapon;
      if (action.team) state.currentTeam = action.team;
      if (elements.weaponSelect) elements.weaponSelect.value = state.currentWeapon;
    }
    eventBus.emit("model:reloadRequest");
  } catch (err) {
    showToast(`Redo failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

// ==========================================
// QoL 3: QUICK WEAPON SWITCHER (Ctrl+K or /)
// ==========================================

function setupQuickSwitcher() {
  if (qolEls.quickSearchBtn) {
    qolEls.quickSearchBtn.addEventListener("click", () => openQuickSwitcher());
  }

  // Keyboard shortcut listener: Ctrl+K, Cmd+K, or pressing '/' outside inputs
  window.addEventListener("keydown", (e) => {
    const tag = e.target.tagName.toLowerCase();

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      openQuickSwitcher();
      return;
    }

    if (e.key === "/" && tag !== "input" && tag !== "textarea") {
      e.preventDefault();
      openQuickSwitcher();
      return;
    }

    if (e.key === "Escape" && qolEls.quickSwitcherModal && !qolEls.quickSwitcherModal.classList.contains("hidden")) {
      closeQuickSwitcher();
      return;
    }
  });

  if (qolEls.quickSwitcherModal) {
    qolEls.quickSwitcherModal.addEventListener("click", (e) => {
      if (e.target === qolEls.quickSwitcherModal) closeQuickSwitcher();
    });
  }

  if (qolEls.quickSwitcherInput) {
    qolEls.quickSwitcherInput.addEventListener("input", (e) => {
      state.qol.quickSearchTerm = e.target.value.toLowerCase().trim();
      state.qol.selectedQuickIndex = 0;
      renderQuickSwitcherResults();
    });

    qolEls.quickSwitcherInput.addEventListener("keydown", (e) => {
      handleQuickSwitcherKeyNav(e);
    });
  }
}

function openQuickSwitcher() {
  if (!qolEls.quickSwitcherModal) return;
  qolEls.quickSwitcherModal.classList.remove("hidden");
  if (qolEls.quickSwitcherInput) {
    qolEls.quickSwitcherInput.value = "";
    state.qol.quickSearchTerm = "";
    state.qol.selectedQuickIndex = 0;
    qolEls.quickSwitcherInput.focus();
  }
  renderQuickSwitcherResults();
}

function closeQuickSwitcher() {
  if (qolEls.quickSwitcherModal) {
    qolEls.quickSwitcherModal.classList.add("hidden");
  }
}

function getFilteredWeapons() {
  const currentTeamModels = state.availableModels[state.currentTeam] || [];
  const term = state.qol.quickSearchTerm;

  const seen = new Set();
  const list = [];

  currentTeamModels.forEach((m) => {
    if (!seen.has(m.weapon)) {
      seen.add(m.weapon);
      list.push(m);
    }
  });

  if (!term) return list;

  return list.filter((m) => {
    return m.weapon.toLowerCase().includes(term) || (m.name && m.name.toLowerCase().includes(term));
  });
}

function renderQuickSwitcherResults() {
  if (!qolEls.quickSwitcherResults) return;
  const filtered = getFilteredWeapons();
  qolEls.quickSwitcherResults.innerHTML = "";

  if (filtered.length === 0) {
    qolEls.quickSwitcherResults.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--text-dim);">
        No weapons matching "${state.qol.quickSearchTerm}".
      </div>
    `;
    return;
  }

  filtered.forEach((m, idx) => {
    const item = document.createElement("div");
    item.className = `quick-switcher-item ${idx === state.qol.selectedQuickIndex ? "selected" : ""}`;
    item.dataset.index = idx;
    item.dataset.weapon = m.weapon;

    const isActive = m.weapon.toLowerCase() === state.currentWeapon.toLowerCase();

    item.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="display: flex; align-items: center;"><svg class="glyph glyph-sm"><use href="#glyph-weapon"></use></svg></span>
        <span class="weapon-name">${m.weapon.toUpperCase()}</span>
        ${isActive ? '<span class="stat-badge" style="background: rgba(59,130,246,0.3); border-color: var(--accent-blue);">Active</span>' : ""}
      </div>
      <div class="weapon-meta">
        <span class="role-badge ${m.has_orig_backup ? 'skin' : 'other'}">${m.has_orig_backup ? 'Modified' : 'Original'}</span>
        <span class="stat-badge">${state.currentTeam.toUpperCase()}</span>
      </div>
    `;

    item.addEventListener("click", () => {
      selectWeaponFromQuickSwitcher(m.weapon);
    });

    item.addEventListener("mouseenter", () => {
      state.qol.selectedQuickIndex = idx;
      updateQuickSwitcherSelection();
    });

    qolEls.quickSwitcherResults.appendChild(item);
  });
}

function updateQuickSwitcherSelection() {
  if (!qolEls.quickSwitcherResults) return;
  const items = qolEls.quickSwitcherResults.querySelectorAll(".quick-switcher-item");
  items.forEach((item, idx) => {
    item.classList.toggle("selected", idx === state.qol.selectedQuickIndex);
    if (idx === state.qol.selectedQuickIndex) {
      item.scrollIntoView({ block: "nearest" });
    }
  });
}

function handleQuickSwitcherKeyNav(e) {
  const filtered = getFilteredWeapons();
  if (filtered.length === 0) return;

  if (e.key === "ArrowDown") {
    e.preventDefault();
    state.qol.selectedQuickIndex = (state.qol.selectedQuickIndex + 1) % filtered.length;
    updateQuickSwitcherSelection();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    state.qol.selectedQuickIndex = (state.qol.selectedQuickIndex - 1 + filtered.length) % filtered.length;
    updateQuickSwitcherSelection();
  } else if (e.key === "Enter") {
    e.preventDefault();
    const chosen = filtered[state.qol.selectedQuickIndex];
    if (chosen) {
      selectWeaponFromQuickSwitcher(chosen.weapon);
    }
  } else if (e.key === "Tab") {
    e.preventDefault();
    // Toggle CT <-> T team
    state.currentTeam = state.currentTeam === "ct" ? "t" : "ct";
    eventBus.emit("team:toggle", state.currentTeam);
    renderQuickSwitcherResults();
  }
}

function selectWeaponFromQuickSwitcher(weapon) {
  closeQuickSwitcher();
  if (weapon.toLowerCase() === state.currentWeapon.toLowerCase()) return;
  state.currentWeapon = weapon;
  if (elements.weaponSelect) elements.weaponSelect.value = weapon;
  eventBus.emit("weapon:changed", { weapon, team: state.currentTeam });
  showToast(`Switched to ${weapon.toUpperCase()} in 0.1s!`, "info");
}

// ==========================================
// QoL 5: COLOR EYEDROPPER TOOL
// ==========================================

function setupEyedropper() {
  if (!qolEls.colorEyedropperBtn) return;

  qolEls.colorEyedropperBtn.addEventListener("click", async () => {
    // 1. Try Native EyeDropper API (Chromium / Edge / modern browsers)
    if (window.EyeDropper) {
      try {
        const eyeDropper = new window.EyeDropper();
        const result = await eyeDropper.open();
        applySampledColor(result.sRGBHex);
        return;
      } catch (err) {
        // User canceled eyedropper or unsupported
        if (err.name === "AbortError") return;
      }
    }

    // 2. Fallback: Sample center pixel from active Color Studio Canvas
    const canvas = document.getElementById("colorAdjustedCanvas") || document.getElementById("curtainFgCanvas");
    if (canvas) {
      const ctx = canvas.getContext("2d");
      const cx = Math.floor(canvas.width / 2);
      const cy = Math.floor(canvas.height / 2);
      const pixel = ctx.getImageData(cx, cy, 1, 1).data;
      const hex = `#${((1 << 24) + (pixel[0] << 16) + (pixel[1] << 8) + pixel[2]).toString(16).slice(1)}`;
      applySampledColor(hex);
    } else {
      showToast("Color canvas not ready for sampling.", "error");
    }
  });
}

function applySampledColor(hex) {
  state.qol.sampledColor = hex;

  if (qolEls.eyedropperSample) {
    qolEls.eyedropperSample.textContent = hex.toUpperCase();
    qolEls.eyedropperSample.style.borderColor = hex;
    qolEls.eyedropperSample.style.color = hex;
    qolEls.eyedropperSample.classList.remove("hidden");
  }

  // Copy hex to clipboard
  if (navigator.clipboard) {
    navigator.clipboard.writeText(hex).catch(() => {});
  }

  // Broadcast sampled color for StatTrak LED or tint matching
  eventBus.emit("color:eyedropperSampled", hex);

  showToast(`Sampled color ${hex.toUpperCase()}! Copied to clipboard.`, "success");
}

// ==========================================
// QoL 6: 1-CLICK EXPORT MOD PACK (.ZIP)
// ==========================================

function setupModpackExport() {
  let exportTeam = "all";

  if (qolEls.exportModpackBtn) {
    qolEls.exportModpackBtn.addEventListener("click", () => {
      if (qolEls.exportModpackModal) qolEls.exportModpackModal.classList.remove("hidden");
      if (qolEls.exportStatusArea) qolEls.exportStatusArea.classList.add("hidden");
    });
  }

  if (qolEls.exportModalCloseBtn) {
    qolEls.exportModalCloseBtn.addEventListener("click", () => {
      if (qolEls.exportModpackModal) qolEls.exportModpackModal.classList.add("hidden");
    });
  }

  // Team scope buttons
  const teamBtns = [
    { btn: qolEls.exportTeamAll, val: "all" },
    { btn: qolEls.exportTeamCT, val: "ct" },
    { btn: qolEls.exportTeamT, val: "t" },
  ];

  teamBtns.forEach(({ btn, val }) => {
    if (!btn) return;
    btn.addEventListener("click", () => {
      teamBtns.forEach((b) => b.btn && b.btn.classList.remove("active"));
      btn.classList.add("active");
      exportTeam = val;
    });
  });

  if (qolEls.exportConfirmBtn) {
    qolEls.exportConfirmBtn.addEventListener("click", async () => {
      const packName = qolEls.exportPackName ? qolEls.exportPackName.value.trim() || "CS16_Custom_ModPack" : "CS16_Custom_ModPack";
      const onlyModified = qolEls.exportOnlyModified ? qolEls.exportOnlyModified.checked : false;

      showLoader("Bundling custom models into modpack ZIP...");
      try {
        const includeAmxx = document.getElementById("exportIncludeAmxx")?.checked ?? false;
        const includePw = document.getElementById("exportIncludePw")?.checked ?? false;
        const includeSounds = document.getElementById("exportIncludeSounds")?.checked ?? false;

        const payload = {
          team: exportTeam,
          include_only_modified: onlyModified,
          include_amxx_configs: includeAmxx,
          include_pw_models: includePw,
          include_sounds: includeSounds,
          pack_name: packName,
        };

        const res = await apiPost("/api/export_modpack", payload);
        if (!res.success) throw new Error(res.error || "Export failed");

        // Trigger automatic browser download via Data URI
        const downloadLink = document.createElement("a");
        downloadLink.href = res.zip_base64;
        downloadLink.download = res.filename || `${packName}.zip`;
        document.body.appendChild(downloadLink);
        downloadLink.click();
        downloadLink.remove();

        showToast(res.message, "success");

        if (qolEls.exportStatusArea) {
          qolEls.exportStatusArea.innerHTML = `
            <p style="font-weight: 700; color: var(--accent-green); margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
              <svg class="glyph glyph-sm" style="color: var(--accent-green);"><use href="#glyph-check-circle"></use></svg> Successfully Generated ${res.model_count} Models!
            </p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 10px;">
              Your ZIP archive has started downloading automatically.
            </p>
            <a href="${res.zip_base64}" download="${res.filename}" class="btn btn-secondary btn-sm" style="display: inline-block;">
              Click here if download did not start
            </a>
          `;
          qolEls.exportStatusArea.classList.remove("hidden");
        }
      } catch (err) {
        showToast(`Export modpack failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }
}
