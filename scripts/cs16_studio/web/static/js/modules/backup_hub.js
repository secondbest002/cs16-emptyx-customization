/**
 * modules/backup_hub.js - Visual Backup & Rollback Hub
 * CS 1.6 Asset Studio Pro - Phase 2 Quality Improvement
 *
 * Features:
 * 1. Side-by-side visual diff card: Current Active Model vs Selected Restore Point
 * 2. Dedicated Snapshot & Legacy Backup listing with 128x128 pixel-perfect thumbnails
 * 3. 1-Click Rollback to any specific restore point (.orig.mdl, .bak, intermediate snapshots)
 * 4. 1-Click Loose Backup Consolidation into isolated dedicated backup/ folders
 */

import { state, eventBus } from "../core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader, elements } from "../core/api.js";

const hubEls = {
  get modal() { return document.getElementById("backupHubModal"); },
  get closeBtn() { return document.getElementById("backupHubCloseBtn"); },
  get cancelBtn() { return document.getElementById("backupHubCancelBtn"); },
  get restoreBtn() { return document.getElementById("backupHubRestoreBtn"); },
  get migrateBtn() { return document.getElementById("backupHubMigrateBtn"); },
  get openHubBtn() { return document.getElementById("backupHubBtn"); },
  get openFromScopeBtn() { return document.getElementById("openBackupHubFromScopeBtn"); },

  // Diff Header & Titles
  get modelTitle() { return document.getElementById("backupHubModelTitle"); },

  // Current Working Model Diff Card
  get currentName() { return document.getElementById("backupHubCurrentName"); },
  get currentThumb() { return document.getElementById("backupHubCurrentThumb"); },
  get currentThumbPlaceholder() { return document.getElementById("backupHubCurrentThumbPlaceholder"); },
  get currentSize() { return document.getElementById("backupHubCurrentSize"); },
  get currentTexCount() { return document.getElementById("backupHubCurrentTexCount"); },
  get currentDate() { return document.getElementById("backupHubCurrentDate"); },

  // Selected Restore Point Diff Card
  get selectedName() { return document.getElementById("backupHubSelectedName"); },
  get selectedBadge() { return document.getElementById("backupHubSelectedBadge"); },
  get selectedThumb() { return document.getElementById("backupHubSelectedThumb"); },
  get selectedThumbPlaceholder() { return document.getElementById("backupHubSelectedThumbPlaceholder"); },
  get selectedSize() { return document.getElementById("backupHubSelectedSize"); },
  get selectedTexCount() { return document.getElementById("backupHubSelectedTexCount"); },
  get selectedDate() { return document.getElementById("backupHubSelectedDate"); },

  // List & Status
  get countBadge() { return document.getElementById("backupHubCountBadge"); },
  get listContainer() { return document.getElementById("backupHubList"); },
  get statusMsg() { return document.getElementById("backupHubStatusMsg"); },
};

let currentBackupsData = null;
let selectedBackupItem = null;

function formatBytes(bytes) {
  if (bytes === undefined || bytes === null || isNaN(bytes)) return "--";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(2)} MB`;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function initBackupHubModule() {
  if (hubEls.openHubBtn) {
    hubEls.openHubBtn.addEventListener("click", () => openBackupHubModal());
  }

  if (hubEls.openFromScopeBtn) {
    hubEls.openFromScopeBtn.addEventListener("click", () => {
      // Close restoreScopeModal if open
      const scopeModal = document.getElementById("restoreScopeModal");
      if (scopeModal) scopeModal.classList.add("hidden");
      openBackupHubModal();
    });
  }

  if (hubEls.closeBtn) {
    hubEls.closeBtn.addEventListener("click", closeBackupHubModal);
  }

  if (hubEls.cancelBtn) {
    hubEls.cancelBtn.addEventListener("click", closeBackupHubModal);
  }

  if (hubEls.modal) {
    hubEls.modal.addEventListener("click", (e) => {
      if (e.target === hubEls.modal) closeBackupHubModal();
    });
  }

  if (hubEls.restoreBtn) {
    hubEls.restoreBtn.addEventListener("click", executeRestoreSelected);
  }

  if (hubEls.migrateBtn) {
    hubEls.migrateBtn.addEventListener("click", executeMigrateLooseBackups);
  }
}

export async function openBackupHubModal() {
  if (!hubEls.modal) return;
  hubEls.modal.classList.remove("hidden");

  // Reset selected card
  selectedBackupItem = null;
  if (hubEls.restoreBtn) hubEls.restoreBtn.disabled = true;
  if (hubEls.selectedName) hubEls.selectedName.textContent = "None Selected";
  if (hubEls.selectedBadge) {
    hubEls.selectedBadge.textContent = "SELECT A RESTORE POINT";
    hubEls.selectedBadge.className = "diff-badge restore-badge";
  }
  if (hubEls.selectedThumb) {
    hubEls.selectedThumb.src = "";
    hubEls.selectedThumb.classList.add("hidden");
  }
  if (hubEls.selectedThumbPlaceholder) {
    hubEls.selectedThumbPlaceholder.classList.remove("hidden");
    hubEls.selectedThumbPlaceholder.textContent = "Select a backup below";
  }
  if (hubEls.selectedSize) hubEls.selectedSize.textContent = "--";
  if (hubEls.selectedTexCount) hubEls.selectedTexCount.textContent = "--";
  if (hubEls.selectedDate) hubEls.selectedDate.textContent = "--";
  if (hubEls.statusMsg) hubEls.statusMsg.textContent = "Select a restore point to compare visual differences.";

  await loadBackupHubData();
}

export function closeBackupHubModal() {
  if (hubEls.modal) hubEls.modal.classList.add("hidden");
}

export async function loadBackupHubData() {
  const weapon = state.currentWeapon || "usp";
  const team = state.currentTeam || "ct";
  const customPath = state.modelData?.model_path;

  if (hubEls.modelTitle) {
    hubEls.modelTitle.textContent = state.modelData?.model_name || `v_${weapon}.mdl`;
  }

  if (hubEls.listContainer) {
    hubEls.listContainer.innerHTML = `
      <div style="text-align: center; padding: 24px; color: var(--text-dim);">
        <div class="spinner" style="margin: 0 auto 10px; width: 24px; height: 24px;"></div>
        Scanning backup history & generating thumbnails...
      </div>
    `;
  }

  try {
    const params = new URLSearchParams({ weapon, team });
    if (customPath) params.set("path", customPath);

    const data = await apiGet(`/api/model/backups?${params.toString()}`);
    currentBackupsData = data;

    // 1. Update Current Active Model Card
    const cur = data.current || {};
    if (hubEls.currentName) hubEls.currentName.textContent = data.model_name || `v_${weapon}.mdl`;
    if (hubEls.currentSize) hubEls.currentSize.textContent = formatBytes(cur.size);
    if (hubEls.currentTexCount) hubEls.currentTexCount.textContent = cur.texture_count || "--";
    if (hubEls.currentDate) hubEls.currentDate.textContent = cur.formatted_date || "--";

    if (cur.thumbnail && hubEls.currentThumb) {
      hubEls.currentThumb.src = cur.thumbnail;
      hubEls.currentThumb.classList.remove("hidden");
      if (hubEls.currentThumbPlaceholder) hubEls.currentThumbPlaceholder.classList.add("hidden");
    } else {
      if (hubEls.currentThumb) hubEls.currentThumb.classList.add("hidden");
      if (hubEls.currentThumbPlaceholder) {
        hubEls.currentThumbPlaceholder.classList.remove("hidden");
        hubEls.currentThumbPlaceholder.textContent = "No Texture Thumbnail";
      }
    }

    // 2. Render Backups List
    renderBackupList(data.backups || []);

  } catch (err) {
    if (hubEls.listContainer) {
      hubEls.listContainer.innerHTML = `
        <div style="text-align: center; padding: 20px; color: #ef4444;">
          Failed to load backups: ${escapeHtml(err.message)}
        </div>
      `;
    }
  }
}

function renderBackupList(backups) {
  if (hubEls.countBadge) {
    hubEls.countBadge.textContent = String(backups.length);
  }

  if (!hubEls.listContainer) return;
  hubEls.listContainer.innerHTML = "";

  if (backups.length === 0) {
    hubEls.listContainer.innerHTML = `
      <div style="text-align: center; padding: 24px; color: var(--text-dim); background: rgba(0,0,0,0.2); border-radius: 8px;">
        <svg class="glyph glyph-md" style="color: var(--text-dim); margin-bottom: 6px;"><use href="#glyph-clock"></use></svg>
        <p style="margin: 0; font-size: 0.85rem;">No restore points found for this weapon.</p>
        <p style="margin: 4px 0 0; font-size: 0.75rem; color: #64748b;">
          Backups are automatically created whenever you bake stickers, adjust colors, or transfer gloves.
        </p>
      </div>
    `;
    return;
  }

  backups.forEach((b, idx) => {
    const itemEl = document.createElement("div");
    itemEl.className = "backup-point-item";
    itemEl.dataset.id = b.id;

    const badgeClass = b.type === "orig" ? "restore-badge" : (b.is_dedicated ? "restore-badge" : "restore-badge legacy");
    const badgeLabel = b.type === "orig" ? "GOLDEN ORIGINAL" : (b.is_dedicated ? "SNAPSHOT" : "LOOSE LEGACY");

    itemEl.innerHTML = `
      <div class="point-item-left">
        ${b.thumbnail 
          ? `<img src="${b.thumbnail}" alt="${escapeHtml(b.filename)}" class="point-item-thumb" />` 
          : `<div class="point-item-thumb" style="display: flex; align-items: center; justify-content: center; font-size: 0.65rem; color: #64748b;">RAW</div>`
        }
        <div class="point-item-info">
          <div class="point-item-title-row">
            <span class="point-item-filename font-mono">${escapeHtml(b.filename)}</span>
            <span class="diff-badge ${badgeClass}">${badgeLabel}</span>
          </div>
          <div class="point-item-meta">
            <span>${escapeHtml(b.formatted_date || b.modified_at || "Unknown Date")}</span>
            <span>&bull;</span>
            <span>${formatBytes(b.size)}</span>
            <span>&bull;</span>
            <span>${b.texture_count || 0} textures</span>
            ${!b.is_dedicated ? '<span style="color: #f59e0b;">(In Model Root)</span>' : ''}
          </div>
        </div>
      </div>
      <div class="point-item-right">
        <button type="button" class="btn btn-secondary btn-xs select-backup-btn">
          <span>Compare & Select</span>
        </button>
      </div>
    `;

    itemEl.addEventListener("click", () => selectBackup(b, itemEl));
    hubEls.listContainer.appendChild(itemEl);

    // Auto-select first item (preferred: Golden Original or latest backup)
    if (idx === 0 && !selectedBackupItem) {
      selectBackup(b, itemEl);
    }
  });
}

function selectBackup(b, itemEl) {
  selectedBackupItem = b;

  // Update item selection styles
  if (hubEls.listContainer) {
    hubEls.listContainer.querySelectorAll(".backup-point-item").forEach((el) => {
      el.classList.toggle("selected", el === itemEl);
    });
  }

  // Update Right-side Selected Card
  if (hubEls.selectedName) hubEls.selectedName.textContent = b.filename;
  if (hubEls.selectedSize) hubEls.selectedSize.textContent = formatBytes(b.size);
  if (hubEls.selectedTexCount) hubEls.selectedTexCount.textContent = b.texture_count || "--";
  if (hubEls.selectedDate) hubEls.selectedDate.textContent = b.formatted_date || b.modified_at || "--";

  if (hubEls.selectedBadge) {
    if (b.type === "orig") {
      hubEls.selectedBadge.textContent = "GOLDEN ORIGINAL (.orig.mdl)";
      hubEls.selectedBadge.className = "diff-badge restore-badge";
    } else if (b.is_dedicated) {
      hubEls.selectedBadge.textContent = "DEDICATED SNAPSHOT (.bak)";
      hubEls.selectedBadge.className = "diff-badge restore-badge";
    } else {
      hubEls.selectedBadge.textContent = "LEGACY LOOSE (.bak)";
      hubEls.selectedBadge.className = "diff-badge restore-badge legacy";
    }
  }

  if (b.thumbnail && hubEls.selectedThumb) {
    hubEls.selectedThumb.src = b.thumbnail;
    hubEls.selectedThumb.classList.remove("hidden");
    if (hubEls.selectedThumbPlaceholder) hubEls.selectedThumbPlaceholder.classList.add("hidden");
  } else {
    if (hubEls.selectedThumb) hubEls.selectedThumb.classList.add("hidden");
    if (hubEls.selectedThumbPlaceholder) {
      hubEls.selectedThumbPlaceholder.classList.remove("hidden");
      hubEls.selectedThumbPlaceholder.textContent = "No Texture Thumbnail";
    }
  }

  if (hubEls.restoreBtn) {
    hubEls.restoreBtn.disabled = false;
  }

  if (hubEls.statusMsg) {
    hubEls.statusMsg.innerHTML = `Ready to rollback to <strong style="color: var(--text-bright); font-family: monospace;">${escapeHtml(b.filename)}</strong> (${formatBytes(b.size)}).`;
  }
}

async function executeRestoreSelected() {
  if (!selectedBackupItem) {
    showToast("Please select a restore point first.", "warning");
    return;
  }

  const b = selectedBackupItem;
  const weapon = state.currentWeapon || "usp";
  const team = state.currentTeam || "ct";
  const customPath = state.modelData?.model_path;

  const confirmMsg = `Rollback active model to "${b.filename}"?\n\nThis will safely restore textures and geometry from this restore point.`;
  if (!confirm(confirmMsg)) return;

  showLoader(`Rolling back to ${b.filename}...`);
  try {
    const payload = {
      weapon,
      team,
      backup_target: b.filename,
      path: customPath,
    };

    const res = await apiPost("/api/model/restore_backup", payload);
    showToast(res.message || `Successfully restored from ${b.filename}!`, "success");

    // Trigger reload across Studio
    eventBus.emit("model:reloadRequest");
    eventBus.emit("model:restored", { team, weapon, backup: b.filename });

    // Refresh hub data to update active model card
    await loadBackupHubData();

  } catch (err) {
    showToast(`Rollback failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function executeMigrateLooseBackups() {
  showLoader("Consolidating loose backups into dedicated backup/ folders...");
  try {
    const res = await apiPost("/api/tools/migrate_backups", {});
    const count = res.moved_count || 0;
    if (count > 0) {
      showToast(`Consolidated ${count} loose backup file(s) into dedicated backup/ folders!`, "success");
    } else {
      showToast("All backups are already organized into dedicated backup/ folders.", "info");
    }
    await loadBackupHubData();
  } catch (err) {
    showToast(`Backup consolidation failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}
