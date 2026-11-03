/**
 * modules/profiles.js - Loadout Profile & Preset Manager
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

import { state, eventBus } from "../core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader, elements } from "../core/api.js";

const profileEls = {
  get profileSelect() { return document.getElementById("profileSelect"); },
  get saveProfileBtn() { return document.getElementById("saveProfileBtn"); },
  get drawerNewProfileBtn() { return document.getElementById("drawerNewProfileBtn"); },
  get drawerProfilesList() { return document.getElementById("drawerProfilesList"); },
  get profileModal() { return document.getElementById("profileModal"); },
  get profileModalCloseBtn() { return document.getElementById("profileModalCloseBtn"); },
  get profileNameInput() { return document.getElementById("profileNameInput"); },
  get profileDescInput() { return document.getElementById("profileDescInput"); },
  get profileSaveConfirmBtn() { return document.getElementById("profileSaveConfirmBtn"); },
};

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function initProfilesModule() {
  setupProfileEventListeners();
  fetchProfiles();
}

function setupProfileEventListeners() {
  const openModal = () => {
    if (profileEls.profileModal) {
      if (profileEls.profileNameInput) profileEls.profileNameInput.value = "";
      if (profileEls.profileDescInput) profileEls.profileDescInput.value = "";
      profileEls.profileModal.classList.remove("hidden");
      if (profileEls.profileNameInput) profileEls.profileNameInput.focus();
    }
  };

  if (profileEls.saveProfileBtn) {
    profileEls.saveProfileBtn.addEventListener("click", openModal);
  }

  if (profileEls.drawerNewProfileBtn) {
    profileEls.drawerNewProfileBtn.addEventListener("click", openModal);
  }

  if (profileEls.profileModalCloseBtn) {
    profileEls.profileModalCloseBtn.addEventListener("click", () => {
      if (profileEls.profileModal) profileEls.profileModal.classList.add("hidden");
    });
  }

  if (profileEls.profileSaveConfirmBtn) {
    profileEls.profileSaveConfirmBtn.addEventListener("click", async () => {
      const name = profileEls.profileNameInput ? profileEls.profileNameInput.value.trim() : "";
      if (!name) {
        showToast("Please enter a profile name.", "error");
        return;
      }
      const desc = profileEls.profileDescInput ? profileEls.profileDescInput.value.trim() : "";

      showLoader(`Saving profile "${name}"...`);
      try {
        const res = await apiPost("/api/profiles/save", {
          name,
          team: state.currentTeam,
          description: desc,
        });
        showToast(res.message || "Profile snapshot saved!", "success");
        if (profileEls.profileModal) profileEls.profileModal.classList.add("hidden");
        await fetchProfiles();
      } catch (err) {
        showToast(`Save profile failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  if (profileEls.profileSelect) {
    profileEls.profileSelect.addEventListener("change", async (e) => {
      const profileName = e.target.value;
      if (!profileName) return;

      if (!confirm(`Restore loadout profile "${profileName}"? This will overwrite active model slots.`)) {
        profileEls.profileSelect.value = "";
        return;
      }

      showLoader(`Loading profile "${profileName}"...`);
      try {
        const res = await apiPost("/api/profiles/load", { name: profileName });
        showToast(res.message, "success");
        eventBus.emit("model:reloadRequest");
      } catch (err) {
        showToast(`Load profile failed: ${err.message}`, "error");
      } finally {
        hideLoader();
        profileEls.profileSelect.value = "";
      }
    });
  }
}

export async function fetchProfiles() {
  try {
    const res = await apiGet("/api/profiles");
    const profiles = res.profiles || [];

    // 1. Maintain backward compatibility with select dropdown
    if (profileEls.profileSelect) {
      profileEls.profileSelect.innerHTML = '<option value="">Load Profile...</option>';
      profiles.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.name;
        opt.textContent = `${p.name} (${p.weapon_count} weapons)`;
        profileEls.profileSelect.appendChild(opt);
      });
    }

    // 2. Render rich visual cards in Left Drawer View
    renderDrawerProfiles(profiles);
  } catch (err) {
    console.warn("Profiles load error:", err);
    if (profileEls.drawerProfilesList) {
      profileEls.drawerProfilesList.innerHTML = `
        <div style="text-align: center; color: var(--accent-red); padding: 20px; font-size: 0.82rem;">
          Failed to load profiles.
        </div>
      `;
    }
  }
}

export function renderDrawerProfiles(profiles) {
  if (!profileEls.drawerProfilesList) return;
  profileEls.drawerProfilesList.innerHTML = "";

  if (profiles.length === 0) {
    profileEls.drawerProfilesList.innerHTML = `
      <div style="text-align: center; color: var(--text-dim); padding: 30px 10px;">
        <p style="font-size: 0.85rem; margin-bottom: 12px;">No loadout profiles saved yet.</p>
        <button type="button" class="btn btn-sm btn-secondary create-first-profile-btn">
          <svg class="glyph glyph-xs"><use href="#glyph-save"></use></svg> Create First Snapshot
        </button>
      </div>
    `;

    const createBtn = profileEls.drawerProfilesList.querySelector(".create-first-profile-btn");
    if (createBtn) {
      createBtn.addEventListener("click", () => {
        if (profileEls.profileModal) {
          if (profileEls.profileNameInput) profileEls.profileNameInput.value = "";
          if (profileEls.profileDescInput) profileEls.profileDescInput.value = "";
          profileEls.profileModal.classList.remove("hidden");
          if (profileEls.profileNameInput) profileEls.profileNameInput.focus();
        }
      });
    }
    return;
  }

  profiles.forEach((p) => {
    const card = document.createElement("div");
    card.className = "drawer-profile-card";

    const teamLabel = p.team ? `${p.team.toUpperCase()} Loadout` : "All Weapons";
    const metaDate = p.created_at ? p.created_at.slice(0, 10) : (p.description || "Preset");

    card.innerHTML = `
      <div class="drawer-profile-card-header">
        <span class="drawer-profile-title">${escapeHtml(p.name)}</span>
        <span class="stat-badge" style="font-size: 0.68rem; padding: 1px 6px;">${p.weapon_count || 0} weapons</span>
      </div>
      <div class="drawer-profile-meta">
        <span>${escapeHtml(teamLabel)}</span>
        <span>${escapeHtml(metaDate)}</span>
      </div>
      ${p.description ? `<p style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 8px; line-height: 1.3;">${escapeHtml(p.description)}</p>` : ""}
      <div class="drawer-profile-actions">
        <button type="button" class="btn btn-xs btn-primary profile-load-btn" title="Apply this loadout profile">
          <svg class="glyph glyph-xs"><use href="#glyph-bolt"></use></svg> Apply
        </button>
        <button type="button" class="btn btn-xs btn-danger profile-delete-btn" title="Delete profile">
          <svg class="glyph glyph-xs"><use href="#glyph-trash"></use></svg> Delete
        </button>
      </div>
    `;

    const loadBtn = card.querySelector(".profile-load-btn");
    if (loadBtn) {
      loadBtn.addEventListener("click", async () => {
        if (!confirm(`Apply loadout profile "${p.name}"? This will restore weapon skins and slots.`)) {
          return;
        }

        showLoader(`Applying profile "${p.name}"...`);
        try {
          const res = await apiPost("/api/profiles/load", { name: p.name });
          showToast(res.message || `Profile "${p.name}" applied successfully!`, "success");
          eventBus.emit("model:reloadRequest");
        } catch (err) {
          showToast(`Apply profile failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      });
    }

    const delBtn = card.querySelector(".profile-delete-btn");
    if (delBtn) {
      delBtn.addEventListener("click", async () => {
        if (!confirm(`Delete profile "${p.name}"? This cannot be undone.`)) {
          return;
        }

        showLoader(`Deleting profile "${p.name}"...`);
        try {
          const res = await apiPost("/api/profiles/delete", { name: p.name });
          showToast(res.message || `Profile "${p.name}" deleted.`, "info");
          await fetchProfiles();
        } catch (err) {
          showToast(`Delete failed: ${err.message}`, "error");
        } finally {
          hideLoader();
        }
      });
    }

    profileEls.drawerProfilesList.appendChild(card);
  });
}
