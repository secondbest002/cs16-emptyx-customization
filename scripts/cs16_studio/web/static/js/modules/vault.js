/**
 * modules/vault.js - CS 1.6 Skin Inventory & Vault Pro
 * Seamless Skin Vault, Knives preservation, and Glove Swapping Mitigation Engine.
 */

import { state, eventBus } from "../core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader } from "../core/api.js";
import { loadActiveModel } from "../app.js";

let vaultItems = [];
let activeCategoryFilter = "all";
let searchQuery = "";
let activeLoadoutTeam = "ct";
let loadoutPresets = [];

export function initVaultModule() {
  const openVaultBtn = document.getElementById("openVaultBtn");
  const saveVaultBtn = document.getElementById("saveVaultBtn");
  const vaultModalCloseBtn = document.getElementById("vaultModalCloseBtn");
  const saveToVaultCloseBtn = document.getElementById("saveToVaultCloseBtn");
  const saveToVaultCancelBtn = document.getElementById("saveToVaultCancelBtn");
  const saveToVaultConfirmBtn = document.getElementById("saveToVaultConfirmBtn");
  const vaultSyncGlovesAllBtn = document.getElementById("vaultSyncGlovesAllBtn");
  const vaultSearchInput = document.getElementById("vaultSearchInput");

  if (openVaultBtn) {
    openVaultBtn.addEventListener("click", () => openVaultModal());
  }

  if (saveVaultBtn) {
    saveVaultBtn.addEventListener("click", () => openSaveToVaultModal());
  }

  if (vaultModalCloseBtn) {
    vaultModalCloseBtn.addEventListener("click", () => closeVaultModal());
  }

  if (saveToVaultCloseBtn) {
    saveToVaultCloseBtn.addEventListener("click", () => closeSaveToVaultModal());
  }

  if (saveToVaultCancelBtn) {
    saveToVaultCancelBtn.addEventListener("click", () => closeSaveToVaultModal());
  }

  if (saveToVaultConfirmBtn) {
    saveToVaultConfirmBtn.addEventListener("click", () => submitSaveToVault());
  }

  if (vaultSyncGlovesAllBtn) {
    vaultSyncGlovesAllBtn.addEventListener("click", () => syncActiveGlovesToVault());
  }

  if (vaultSearchInput) {
    vaultSearchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderVaultCards();
    });
  }

  // Filter Pills
  document.querySelectorAll("[data-vault-filter]").forEach((pill) => {
    pill.addEventListener("click", (e) => {
      document.querySelectorAll("[data-vault-filter]").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      activeCategoryFilter = pill.getAttribute("data-vault-filter") || "all";
      renderVaultCards();
    });
  });

  // Team Loadout Presets UI (Phase 5)
  const ctBtn = document.getElementById("vaultLoadoutCtBtn");
  const tBtn = document.getElementById("vaultLoadoutTBtn");
  const saveLoadoutBtn = document.getElementById("vaultSaveLoadoutBtn");
  const importBtn = document.getElementById("vaultImportBtn");
  const importInput = document.getElementById("vaultImportFileInput");
  const vaultModalEl = document.getElementById("vaultModal");

  if (ctBtn) {
    ctBtn.addEventListener("click", () => {
      ctBtn.classList.add("active");
      if (tBtn) tBtn.classList.remove("active");
      activeLoadoutTeam = "ct";
      loadTeamLoadouts("ct");
    });
  }

  if (tBtn) {
    tBtn.addEventListener("click", () => {
      tBtn.classList.add("active");
      if (ctBtn) ctBtn.classList.remove("active");
      activeLoadoutTeam = "t";
      loadTeamLoadouts("t");
    });
  }

  if (saveLoadoutBtn) {
    saveLoadoutBtn.addEventListener("click", () => saveCurrentTeamLoadout());
  }

  if (importBtn && importInput) {
    importBtn.addEventListener("click", () => importInput.click());
    importInput.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (file) {
        await handleImportSkinFile(file);
        importInput.value = "";
      }
    });
  }

  // Drag-and-drop .cs16skin into vault modal
  if (vaultModalEl) {
    vaultModalEl.addEventListener("dragover", (e) => {
      e.preventDefault();
      vaultModalEl.classList.add("vault-dragover");
    });
    vaultModalEl.addEventListener("dragleave", (e) => {
      if (!e.relatedTarget || !vaultModalEl.contains(e.relatedTarget)) {
        vaultModalEl.classList.remove("vault-dragover");
      }
    });
    vaultModalEl.addEventListener("drop", async (e) => {
      e.preventDefault();
      vaultModalEl.classList.remove("vault-dragover");
      const file = e.dataTransfer?.files?.[0];
      if (file && (file.name.endsWith(".cs16skin") || file.name.endsWith(".zip"))) {
        await handleImportSkinFile(file);
      }
    });
  }

  // Hotkey: Ctrl+Shift+S for Quick Save to Vault
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.code === "KeyS") {
      e.preventDefault();
      openSaveToVaultModal();
    }
  });
}

export function openSaveToVaultModal() {
  const modal = document.getElementById("saveToVaultModal");
  if (!modal) return;

  const wName = (state.currentWeapon || "usp").toUpperCase();
  const input = document.getElementById("vaultSkinNameInput");
  const weaponTag = document.getElementById("vaultSaveWeaponTag");
  const thumbImg = document.getElementById("vaultSaveThumbPreview");

  if (weaponTag) weaponTag.textContent = wName;
  if (input) {
    input.value = `${wName} | Custom Finish`;
    setTimeout(() => {
      input.focus();
      input.select();
    }, 100);
  }

  // Capture current 3D canvas snapshot
  try {
    const canvas = document.querySelector("#viewport3dCanvasContainer canvas");
    if (canvas && thumbImg) {
      thumbImg.src = canvas.toDataURL("image/png");
      thumbImg.style.display = "block";
    }
  } catch (err) {
    if (thumbImg) thumbImg.style.display = "none";
  }

  // Reset checkboxes
  const pwCheck = document.getElementById("vaultSyncPwCheck");
  const gloveCheck = document.getElementById("vaultAutoGloveCheck");
  const amxxCheck = document.getElementById("vaultAmxxCheck");
  const equipCheck = document.getElementById("vaultEquipNowCheck");

  if (pwCheck) pwCheck.checked = true;
  if (gloveCheck) gloveCheck.checked = true;
  if (amxxCheck) amxxCheck.checked = false; // default false per user preference
  if (equipCheck) equipCheck.checked = false;

  modal.classList.remove("hidden");
}

export function closeSaveToVaultModal() {
  const modal = document.getElementById("saveToVaultModal");
  if (modal) modal.classList.add("hidden");
}

async function submitSaveToVault() {
  const nameInput = document.getElementById("vaultSkinNameInput");
  const name = nameInput ? nameInput.value.trim() : "";
  if (!name) {
    showToast("Please enter a skin name.", "warning");
    return;
  }

  const pwCheck = document.getElementById("vaultSyncPwCheck");
  const amxxCheck = document.getElementById("vaultAmxxCheck");
  const equipCheck = document.getElementById("vaultEquipNowCheck");

  let thumb_b64 = null;
  try {
    const canvas = document.querySelector("#viewport3dCanvasContainer canvas");
    if (canvas) {
      thumb_b64 = canvas.toDataURL("image/png");
    }
  } catch (e) {}

  showLoader(`Saving "${name}" to Skin Vault...`);
  try {
    const res = await apiPost("/api/inventory/save", {
      name: name,
      weapon: state.currentWeapon,
      team: state.currentTeam,
      path: state.modelData?.model_path,
      sync_pw: pwCheck ? pwCheck.checked : true,
      register_amxx: amxxCheck ? amxxCheck.checked : false,
      equip_now: equipCheck ? equipCheck.checked : false,
      thumb_b64: thumb_b64,
    });

    if (res.success) {
      showToast(`Skin "${name}" saved to Inventory Vault!`, "success");
      closeSaveToVaultModal();
      // If equipped immediately, reload model
      if (equipCheck && equipCheck.checked) {
        await loadActiveModel();
      }
      // If vault open, refresh
      const vaultModal = document.getElementById("vaultModal");
      if (vaultModal && !vaultModal.classList.contains("hidden")) {
        await loadVaultItems();
      }
    } else {
      showToast(res.error || "Failed to save skin.", "error");
    }
  } catch (err) {
    showToast(`Save Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

export async function openVaultModal() {
  const modal = document.getElementById("vaultModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  await Promise.all([
    loadVaultItems(),
    loadTeamLoadouts(activeLoadoutTeam),
  ]);
}

export function closeVaultModal() {
  const modal = document.getElementById("vaultModal");
  if (modal) modal.classList.add("hidden");
}

async function loadVaultItems() {
  const grid = document.getElementById("vaultGrid");
  if (grid) {
    grid.innerHTML = '<div class="vault-loading"><div class="spinner"></div><p>Loading Inventory Vault...</p></div>';
  }

  try {
    const res = await apiGet("/api/inventory");
    vaultItems = res.items || [];
    renderVaultCards();
  } catch (err) {
    if (grid) {
      grid.innerHTML = `<div class="vault-empty"><p class="text-crimson">Failed to load inventory: ${err.message}</p></div>`;
    }
  }
}

function renderVaultCards() {
  const grid = document.getElementById("vaultGrid");
  const countBadge = document.getElementById("vaultTotalCountBadge");
  if (!grid) return;

  // Filter items
  let filtered = vaultItems.filter((item) => {
    // Category filter
    if (activeCategoryFilter !== "all") {
      if (activeCategoryFilter === "knives" && !item.is_knife) return false;
      if (activeCategoryFilter === "rifles" && !["ak47", "m4a1", "m4a4", "awp", "scout", "galil", "famas", "sg552", "aug", "g3sg1", "sg550"].includes(item.weapon)) return false;
      if (activeCategoryFilter === "pistols" && !["usp", "glock18", "deagle", "p228", "elite", "elites", "fiveseven", "tec9"].includes(item.weapon)) return false;
      if (activeCategoryFilter === "smgs" && !["mp5", "p90", "ump45", "mac10", "tmp", "mp7", "bizon", "cz75"].includes(item.weapon)) return false;
      if (activeCategoryFilter === "heavy" && !["m3", "xm1014", "m249", "mag7", "sawedoff", "negev"].includes(item.weapon)) return false;
    }

    // Search query
    if (searchQuery) {
      const matchName = item.name.toLowerCase().includes(searchQuery);
      const matchWeapon = item.weapon.toLowerCase().includes(searchQuery);
      const matchCategory = (item.category || "").toLowerCase().includes(searchQuery);
      if (!matchName && !matchWeapon && !matchCategory) return false;
    }

    return true;
  });

  if (countBadge) {
    countBadge.textContent = `${vaultItems.length} SKINS`;
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="vault-empty">
        <svg class="glyph glyph-lg text-muted"><use href="#glyph-box"></use></svg>
        <h4>No skins found in this category</h4>
        <p>Customize any weapon or knife in Asset Studio and click <strong>"Save to Vault"</strong> to build your CS 1.6 inventory!</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map((item) => {
    const isEquippedCt = item.is_equipped_ct;
    const isEquippedT = item.is_equipped_t;
    const isKnife = item.is_knife;
    const thumbSrc = item.thumbnail || "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100' fill='%23333'><rect width='100' height='100'/></svg>";
    const stickers = item.metadata?.stickers || [];
    const gloveSlots = item.metadata?.glove_slots || [];

    return `
      <div class="vault-card ${isEquippedCt || isEquippedT ? 'is-active-card' : ''}" data-item-id="${item.id}">
        <!-- Thumbnail Wrap -->
        <div class="vault-card-thumb-wrap">
          <img src="${thumbSrc}" alt="${item.name}" class="vault-card-thumb" loading="lazy" />
          
          <!-- Badges Cluster -->
          <div class="vault-card-badge-row">
            ${isEquippedCt ? '<span class="vault-badge badge-ct" title="Equipped for Counter-Terrorists">CT EQUIPPED</span>' : ''}
            ${isEquippedT ? '<span class="vault-badge badge-t" title="Equipped for Terrorists">T EQUIPPED</span>' : ''}
            ${item.amxx_registered ? '<span class="vault-badge badge-amxx" title="Registered in in-game CS 1.6 /skins menu">IN-GAME /SKINS</span>' : ''}
          </div>

          <span class="vault-category-pill">${isKnife ? (item.knife_variant ? item.knife_variant.toUpperCase() : 'KNIFE') : item.weapon.toUpperCase()}</span>
        </div>

        <!-- Info Header -->
        <div class="vault-card-info">
          <div class="vault-card-title-row">
            <h4 class="vault-card-name" title="${item.name}">${item.name}</h4>
          </div>
          <div class="vault-card-meta">
            <span>${item.weapon.toUpperCase()}</span>
            ${stickers.length > 0 ? `<span class="vault-sticker-count"><svg class="glyph glyph-xs"><use href="#glyph-target"></use></svg> ${stickers.length} Stickers</span>` : ''}
            ${item.metadata?.has_stattrak ? '<span class="vault-stattrak-badge">StatTrak™</span>' : ''}
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="vault-card-actions">
          <button type="button" class="btn btn-xs ${isEquippedCt ? 'btn-emerald active-eq' : 'btn-secondary'} btn-equip-ct" data-action="equip-ct" title="Equip to Counter-Terrorist Loadout">
            <svg class="glyph glyph-xs"><use href="#glyph-check"></use></svg>
            <span>CT</span>
          </button>
          <button type="button" class="btn btn-xs ${isEquippedT ? 'btn-emerald active-eq' : 'btn-secondary'} btn-equip-t" data-action="equip-t" title="Equip to Terrorist Loadout">
            <svg class="glyph glyph-xs"><use href="#glyph-check"></use></svg>
            <span>T</span>
          </button>
          <button type="button" class="btn btn-xs btn-icon btn-sync-glove" data-action="sync-glove" title="Synchronize current active gloves to this skin (Mitigate glove clash)">
            <svg class="glyph glyph-xs text-cyan"><use href="#glyph-glove"></use></svg>
          </button>
          <button type="button" class="btn btn-xs btn-icon btn-export" data-action="export" title="Export portable .cs16skin bundle">
            <svg class="glyph glyph-xs text-amber"><use href="#glyph-download"></use></svg>
          </button>
          <button type="button" class="btn btn-xs btn-icon btn-inspect" data-action="inspect" title="Inspect model in 3D Viewport">
            <svg class="glyph glyph-xs"><use href="#glyph-eye"></use></svg>
          </button>
          <button type="button" class="btn btn-xs btn-icon btn-toggle-amxx ${item.amxx_registered ? 'active-amxx' : ''}" data-action="toggle-amxx" title="${item.amxx_registered ? 'Remove from in-game /skins menu' : 'Add to in-game /skins menu'}">
            <svg class="glyph glyph-xs ${item.amxx_registered ? 'text-emerald' : 'text-muted'}"><use href="#glyph-tag"></use></svg>
          </button>
          <button type="button" class="btn btn-xs btn-icon btn-delete" data-action="delete" title="Delete from Inventory Vault">
            <svg class="glyph glyph-xs text-crimson"><use href="#glyph-trash"></use></svg>
          </button>
        </div>
      </div>
    `;
  }).join("");

  // Attach card event listeners
  grid.querySelectorAll(".vault-card").forEach((card) => {
    const id = card.getAttribute("data-item-id");
    const item = vaultItems.find((it) => it.id === id);
    if (!item) return;

    // Equip CT
    card.querySelector('[data-action="equip-ct"]')?.addEventListener("click", () => equipVaultItem(id, "ct"));
    // Equip T
    card.querySelector('[data-action="equip-t"]')?.addEventListener("click", () => equipVaultItem(id, "t"));
    // Sync Gloves
    card.querySelector('[data-action="sync-glove"]')?.addEventListener("click", () => syncItemGloves(id));
    // Export .cs16skin
    card.querySelector('[data-action="export"]')?.addEventListener("click", () => {
      window.location.href = `/api/vault/export_skin?id=${encodeURIComponent(id)}`;
      showToast(`Exporting .cs16skin bundle for "${item.name}"...`, "info");
    });
    // Inspect 3D
    card.querySelector('[data-action="inspect"]')?.addEventListener("click", () => inspectVaultItem(item));
    // Toggle AMXX
    card.querySelector('[data-action="toggle-amxx"]')?.addEventListener("click", () => toggleAmxxItem(id, !item.amxx_registered));
    // Delete
    card.querySelector('[data-action="delete"]')?.addEventListener("click", () => deleteVaultItem(id, item.name));
  });
}

async function equipVaultItem(itemId, team = "ct") {
  showLoader(`Equipping to ${team.toUpperCase()} Loadout with Glove Sync...`);
  try {
    const res = await apiPost("/api/inventory/equip", {
      id: itemId,
      team: team,
      sync_active_glove: true,
    });

    if (res.success) {
      showToast(res.message || `Equipped for ${team.toUpperCase()}!`, "success");
      // Reload inventory data
      await loadVaultItems();
      // Reload active model if team matches
      if (state.currentTeam === team) {
        await loadActiveModel();
      }
    } else {
      showToast(res.error || "Failed to equip item.", "error");
    }
  } catch (err) {
    showToast(`Equip Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function syncItemGloves(itemId) {
  showLoader("Synchronizing gloves to skin...");
  try {
    const res = await apiPost("/api/inventory/sync_gloves", {
      target_items: [itemId],
      donor_weapon: state.currentWeapon,
      team: state.currentTeam,
    });

    if (res.success) {
      showToast("Gloves successfully updated on skin!", "success");
      await loadVaultItems();
    } else {
      showToast(res.error || "Glove sync failed.", "error");
    }
  } catch (err) {
    showToast(`Sync Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function syncActiveGlovesToVault() {
  if (!confirm(`Synchronize active loadout gloves (${state.currentTeam.toUpperCase()}) across ALL skins in your Inventory Vault?\n\nThis will update hands on all saved viewmodels without touching weapon paint, stickers, or StatTrak.`)) {
    return;
  }

  showLoader("Batch synchronizing gloves across entire vault...");
  try {
    const res = await apiPost("/api/inventory/sync_gloves", {
      donor_weapon: state.currentWeapon,
      team: state.currentTeam,
    });

    if (res.success) {
      showToast(res.message || `Synchronized gloves on ${res.updated_count} skins!`, "success");
      await loadVaultItems();
    } else {
      showToast(res.error || "Batch glove sync failed.", "error");
    }
  } catch (err) {
    showToast(`Batch Sync Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function inspectVaultItem(item) {
  closeVaultModal();
  state.currentWeapon = item.weapon;
  state.currentTeam = item.team || state.currentTeam;
  await loadActiveModel();
  showToast(`Inspecting "${item.name}" in 3D Viewport.`, "info");
}

async function toggleAmxxItem(itemId, enable) {
  showLoader(`${enable ? 'Adding to' : 'Removing from'} in-game menu...`);
  try {
    const res = await apiPost("/api/inventory/toggle_amxx", {
      id: itemId,
      enable: enable,
    });

    if (res.success) {
      showToast(res.message, "success");
      await loadVaultItems();
    } else {
      showToast(res.error || "Toggle failed.", "error");
    }
  } catch (err) {
    showToast(`AMXX Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function deleteVaultItem(itemId, name) {
  if (!confirm(`Are you sure you want to delete "${name}" from your Skin Inventory Vault?\n\nThis cannot be undone.`)) {
    return;
  }

  showLoader(`Deleting "${name}"...`);
  try {
    const res = await apiPost("/api/inventory/delete", { id: itemId });
    if (res.success) {
      showToast(res.message || `Deleted "${name}".`, "info");
      await loadVaultItems();
    } else {
      showToast(res.error || "Failed to delete item.", "error");
    }
  } catch (err) {
    showToast(`Delete Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}


// =============================================================================
// TEAM LOADOUTS & PORTABLE BUNDLES ENGINE (Phase 5)
// =============================================================================

export async function loadTeamLoadouts(team = "ct") {
  const container = document.getElementById("vaultLoadoutsList");
  if (!container) return;

  try {
    const res = await apiGet(`/api/vault/loadouts?team=${encodeURIComponent(team)}`);
    loadoutPresets = res.loadouts || [];
    renderTeamLoadouts(loadoutPresets, team);
  } catch (err) {
    container.innerHTML = `<span class="text-crimson" style="font-size: 0.8rem;">Failed to load loadouts: ${err.message}</span>`;
  }
}

function renderTeamLoadouts(presets, team) {
  const container = document.getElementById("vaultLoadoutsList");
  if (!container) return;

  if (!presets || presets.length === 0) {
    container.innerHTML = `<span class="text-muted" style="font-size: 0.8rem;">No saved ${team.toUpperCase()} presets. Click <strong>"Save Current Loadout"</strong> to create one.</span>`;
    return;
  }

  container.innerHTML = presets.map((p) => {
    return `
      <div class="loadout-chip" style="display: inline-flex; align-items: center; gap: 6px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 3px 8px; font-size: 0.8rem;">
        <span style="font-weight: 600; color: #f8fafc;">${p.name}</span>
        <span style="font-size: 0.72rem; color: var(--accent-cyan);">(${p.weapon_count || Object.keys(p.slots || {}).length} weapons)</span>
        <button type="button" class="btn btn-xs btn-emerald" data-loadout-apply="${p.id}" style="padding: 1px 6px; font-size: 0.7rem; height: 20px;" title="Equip this full loadout">
          <svg class="glyph glyph-xs"><use href="#glyph-check"></use></svg>
          <span>Equip</span>
        </button>
        <button type="button" class="btn btn-xs btn-icon" data-loadout-delete="${p.id}" style="padding: 1px 4px; height: 20px;" title="Delete preset">
          <svg class="glyph glyph-xs text-crimson"><use href="#glyph-trash"></use></svg>
        </button>
      </div>
    `;
  }).join("");

  // Attach handlers
  container.querySelectorAll("[data-loadout-apply]").forEach((btn) => {
    const pid = btn.getAttribute("data-loadout-apply");
    btn.addEventListener("click", () => applyTeamLoadout(pid));
  });

  container.querySelectorAll("[data-loadout-delete]").forEach((btn) => {
    const pid = btn.getAttribute("data-loadout-delete");
    btn.addEventListener("click", () => deleteTeamLoadout(pid));
  });
}

async function saveCurrentTeamLoadout() {
  const defaultName = `${activeLoadoutTeam.toUpperCase()} Theme Loadout`;
  const name = prompt(`Enter a name for this ${activeLoadoutTeam.toUpperCase()} loadout preset:`, defaultName);
  if (!name || !name.trim()) return;

  showLoader(`Saving ${activeLoadoutTeam.toUpperCase()} loadout preset...`);
  try {
    const res = await apiPost("/api/vault/loadout_save", {
      team: activeLoadoutTeam,
      name: name.trim(),
    });
    if (res.success) {
      showToast(res.message || "Saved loadout preset!", "success");
      await loadTeamLoadouts(activeLoadoutTeam);
    } else {
      showToast(res.error || "Failed to save loadout.", "error");
    }
  } catch (err) {
    showToast(`Loadout Save Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function applyTeamLoadout(presetId) {
  showLoader("Applying full team loadout with glove sync...");
  try {
    const res = await apiPost("/api/vault/loadout_apply", {
      preset_id: presetId,
    });
    if (res.success) {
      showToast(res.message || "Loadout equipped!", "success");
      await Promise.all([
        loadVaultItems(),
        loadTeamLoadouts(activeLoadoutTeam),
      ]);
      await loadActiveModel();
    } else {
      showToast(res.error || "Failed to apply loadout.", "error");
    }
  } catch (err) {
    showToast(`Loadout Apply Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function deleteTeamLoadout(presetId) {
  if (!confirm("Are you sure you want to delete this loadout preset?")) return;

  try {
    const res = await apiPost("/api/vault/loadout_delete", { preset_id: presetId });
    if (res.success) {
      showToast(res.message || "Deleted loadout preset.", "info");
      await loadTeamLoadouts(activeLoadoutTeam);
    } else {
      showToast(res.error || "Failed to delete loadout.", "error");
    }
  } catch (err) {
    showToast(`Delete Error: ${err.message}`, "error");
  }
}

async function handleImportSkinFile(file) {
  showLoader(`Importing bundle "${file.name}"...`);
  try {
    const reader = new FileReader();
    const b64Promise = new Promise((resolve, reject) => {
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    const b64 = await b64Promise;
    const res = await apiPost("/api/vault/import_skin", {
      bundle_b64: b64,
      team: state.currentTeam,
      register_amxx: false,
      equip_now: false,
    });

    if (res.success) {
      showToast(res.message || `Imported "${res.name}" into Vault!`, "success");
      await loadVaultItems();
    } else {
      showToast(res.error || "Import failed.", "error");
    }
  } catch (err) {
    showToast(`Import Error: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}
