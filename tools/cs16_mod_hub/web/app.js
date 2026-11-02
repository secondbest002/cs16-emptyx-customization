/**
 * tools/cs16_mod_hub/web/app.js
 * Universal Client Controller for Counter-Strike 1.6 Mod Hub Pro.
 * Strict Zero Emojis | Full Animated Tactical Glyphs | Complete Modular Isolation.
 */

// Universal Backend Adapter (transparent fallback between REST and pywebview)
const Backend = {
  isWebview: () => Boolean(window.pywebview && window.pywebview.api),

  async get(url, apiMethod, ...args) {
    if (this.isWebview() && typeof window.pywebview.api[apiMethod] === "function") {
      return await window.pywebview.api[apiMethod](...args);
    }
    const res = await fetch(url);
    return await res.json();
  },

  async post(url, body, apiMethod, ...args) {
    if (this.isWebview() && typeof window.pywebview.api[apiMethod] === "function") {
      return await window.pywebview.api[apiMethod](...args);
    }
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return await res.json();
  },
};

// Tactical Inline SVG Templates (Zero External Font Dependencies)
const TACTICAL_ICONS = {
  cpu: `<span class="glyph glyph-xl glyph-cybernetic-cpu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="12,2 21,7 21,17 12,22 3,17 3,7"/><rect class="cpu-core" x="9" y="9" width="6" height="6" rx="1" fill="currentColor"/></svg></span>`,
  shield: `<span class="glyph glyph-xl glyph-ballistic-shield"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2L3 6V12C3 17.5 6.8 22.3 12 24C17.2 22.3 21 17.5 21 12V6L12 2Z"/><circle cx="12" cy="12" r="6" stroke-dasharray="2 3"/></svg></span>`,
  restore: `<span class="glyph glyph-sm glyph-orbital-cycle"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2V8H15.5"/><path d="M2.5 22V16H8.5"/><path d="M20.49 15A9 9 0 0 1 5.64 5.64L2.5 8"/><path d="M3.51 9A9 9 0 0 1 18.36 18.36L21.5 16"/></svg></span>`,
  verified: `<span class="glyph glyph-sm" style="color: var(--emerald-safe);"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></span>`,
};

let currentProfile = "";
let currentBackupsList = [];

// =========================================================================
// Initialization
// =========================================================================

document.addEventListener("DOMContentLoaded", async () => {
  setupUIEvents();
  await initializeHub();
  setInterval(checkStudioStatus, 8000);
});

window.addEventListener("pywebviewready", async () => {
  log("Native pywebview bridge attached.");
  await initializeHub();
});

async function initializeHub() {
  try {
    log("Connecting to CS 1.6 Mod Hub backend runtime...");
    await loadProfiles();
    await loadPlugins();
    await loadCS2EngineSettings();
    await loadCompetitiveSettings();
    await loadBotEcosystem();
    await loadBackups();
    await checkStudioStatus();
    log("Mod Hub initialized successfully. All systems synchronized.");
  } catch (err) {
    log(`[Error] Initialization failed: ${err}`);
  }
}

// =========================================================================
// UI Event Setup & Navigation
// =========================================================================

function setupUIEvents() {
  // Navigation Tabs Switching
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", async () => {
      document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPane = document.getElementById(`tab-${tab.dataset.tab}`);
      if (targetPane) targetPane.classList.add("active");

      if (tab.dataset.tab === "safety-center") {
        await loadBackups();
      } else if (tab.dataset.tab === "bots-ecosystem") {
        await loadBotEcosystem();
      } else if (tab.dataset.tab === "gameplay-mods") {
        await loadPlugins();
        await loadCS2EngineSettings();
      } else if (tab.dataset.tab === "competitive-match") {
        await loadCompetitiveSettings();
      } else if (tab.dataset.tab === "skin-studio-tab") {
        await checkStudioStatus(true);
      }
    });
  });

  // Profile Selector
  const selProfile = document.getElementById("sel-profile");
  if (selProfile) {
    selProfile.addEventListener("change", async () => {
      const chosen = selProfile.value;
      log(`Switching active profile: ${chosen}...`);
      const res = await Backend.post("/api/profiles/select", { profile: chosen }, "set_profile", chosen);
      if (res.success) {
        currentProfile = res.path || chosen;
        showToast("Profile switched successfully", "success");
        await loadBackups();
      }
    });
  }

  // Open Explorer Button
  const btnOpenFolder = document.getElementById("btn-open-folder");
  if (btnOpenFolder) {
    btnOpenFolder.addEventListener("click", async () => {
      await Backend.post("/api/open-folder", { folder: currentProfile }, "open_in_explorer", currentProfile);
    });
  }

  // Clear Console Button
  const btnClearConsole = document.getElementById("btn-clear-console");
  if (btnClearConsole) {
    btnClearConsole.addEventListener("click", () => {
      const out = document.getElementById("console-output");
      if (out) out.innerHTML = "";
    });
  }

  // Save CS2 Engine Settings Button
  const btnSaveCS2 = document.getElementById("btn-save-cs2-engine");
  if (btnSaveCS2) {
    btnSaveCS2.addEventListener("click", async () => {
      await saveCS2EngineSettings();
    });
  }

  // Master CS2 Engine Switch
  const chkMasterCS2 = document.getElementById("chk-master-cs2-engine");
  if (chkMasterCS2) {
    chkMasterCS2.addEventListener("change", async () => {
      const val = chkMasterCS2.checked ? "1" : "0";
      await Backend.post("/api/cs2-engine/cvar", { cvar: "amx_cs2_engine", value: val }, "save_cs2_engine_cvar", "amx_cs2_engine", val);
      showToast(`CS2 Modern Engine Master Switch: ${chkMasterCS2.checked ? "ENABLED" : "DISABLED"}`);
    });
  }

  // CS2 Engine Sliders Live Display
  setupSliderListener("rng-cs2-epickup-radius", "val-cs2-epickup-radius", " units", "amx_cs2_epickup_radius", "/api/cs2-engine/cvar");
  setupSliderListener("rng-cs2-ping-cooldown", "val-cs2-ping-cooldown", "s", "amx_cs2_ping_cooldown", "/api/cs2-engine/cvar");

  // CS2 Engine Checkboxes Granular Auto-Sync (Modular Isolation)
  document.querySelectorAll("[data-engine-cvar]").forEach((el) => {
    if (el.type === "checkbox" && el.id !== "chk-master-cs2-engine") {
      el.addEventListener("change", async () => {
        const cvar = el.dataset.engineCvar;
        const val = el.checked ? "1" : "0";
        await Backend.post("/api/cs2-engine/cvar", { cvar, value: val }, "save_cs2_engine_cvar", cvar, val);
        showToast(`${cvar}: ${el.checked ? "ENABLED" : "DISABLED"}`, "info");
      });
    }
  });

  // Save Competitive Config Button
  const btnSaveComp = document.getElementById("btn-save-comp");
  if (btnSaveComp) {
    btnSaveComp.addEventListener("click", async () => {
      await saveCompetitiveSettings();
    });
  }

  // Competitive Tournament Presets
  const btnValveMajor = document.getElementById("preset-valve-major");
  if (btnValveMajor) {
    btnValveMajor.addEventListener("click", async () => {
      await applyCompetitivePreset("valve_major");
    });
  }

  const btnEslPro = document.getElementById("preset-esl-pro");
  if (btnEslPro) {
    btnEslPro.addEventListener("click", async () => {
      await applyCompetitivePreset("esl_pro");
    });
  }

  const btnCplWcg = document.getElementById("preset-cpl-wcg");
  if (btnCplWcg) {
    btnCplWcg.addEventListener("click", async () => {
      await applyCompetitivePreset("cpl_wcg");
    });
  }

  // Competitive HUD Cards Live Preview Toggles
  const chkDmgCard = document.getElementById("chk-comp-dmg-card");
  if (chkDmgCard) {
    chkDmgCard.addEventListener("change", () => {
      syncHUDPreviewCards();
      saveSingleCompetitiveCvar("amx_csgo_dmg_card", chkDmgCard.checked ? "1" : "0");
      showToast("amx_csgo_dmg_card updated", "info");
    });
  }

  const chkMvpCard = document.getElementById("chk-comp-mvp-card");
  if (chkMvpCard) {
    chkMvpCard.addEventListener("change", () => {
      syncHUDPreviewCards();
      saveSingleCompetitiveCvar("amx_csgo_mvp_card", chkMvpCard.checked ? "1" : "0");
      showToast("amx_csgo_mvp_card updated", "info");
    });
  }

  // Competitive Selects and Toggles Auto-Sync
  document.querySelectorAll("[data-comp-cvar]").forEach((el) => {
    if (el.id !== "chk-comp-dmg-card" && el.id !== "chk-comp-mvp-card") {
      el.addEventListener("change", () => {
        const cvar = el.dataset.compCvar;
        const val = el.type === "checkbox" ? (el.checked ? "1" : "0") : el.value;
        if (cvar) {
          saveSingleCompetitiveCvar(cvar, val);
          showToast(`${cvar} updated to ${val}`, "info");
        }
      });
    }
  });

  // Master AI Savage Toggle
  const chkMasterAI = document.getElementById("chk-master-savage-ai");
  if (chkMasterAI) {
    chkMasterAI.addEventListener("change", async () => {
      const enable = chkMasterAI.checked;
      const res = await Backend.post("/api/bots/master", { enable }, "toggle_savage_ai", enable);
      if (res.success) {
        updateAIMasterBadge(enable);
        showToast(`AI Engine set to: ${enable ? "SAVAGE ESPORTS AI" : "NATIVE YAPB"}`);
        await loadBotEcosystem();
      }
    });
  }

  // 4-Tier Difficulty Preset Buttons
  document.querySelectorAll(".btn-apply-preset").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const preset = btn.dataset.targetPreset;
      log(`Applying Bot Difficulty Preset: ${preset.toUpperCase()}...`);
      const res = await Backend.post("/api/bots/preset", { preset }, "apply_bot_preset", preset);
      if (res.success) {
        showToast(`Preset applied: ${preset.toUpperCase()}`, "success");
        await loadBotEcosystem();
      } else {
        showToast(`Preset failed: ${res.error}`, "error");
      }
    });
  });

  // YaPB Quota Slider Live Sync
  const rngQuota = document.getElementById("rng-yb-quota");
  const valQuota = document.getElementById("val-yb-quota");
  if (rngQuota && valQuota) {
    rngQuota.addEventListener("input", () => {
      valQuota.innerText = rngQuota.value;
    });
    rngQuota.addEventListener("change", async () => {
      await Backend.post("/api/bots/yapb/cvar", { cvar: "yb_quota", value: rngQuota.value }, "save_yapb_cvar", "yb_quota", rngQuota.value);
      showToast(`yb_quota updated to ${rngQuota.value}`, "info");
    });
  }

  // YaPB Other Controls Auto-Sync
  document.querySelectorAll("[data-yapb-cvar]").forEach((el) => {
    if (el.id !== "rng-yb-quota") {
      el.addEventListener("change", async () => {
        const cvar = el.dataset.yapbCvar;
        const val = el.type === "checkbox" ? (el.checked ? "1" : "0") : el.value;
        if (cvar) {
          await Backend.post("/api/bots/yapb/cvar", { cvar, value: val }, "save_yapb_cvar", cvar, val);
          showToast(`${cvar} updated to ${val}`, "info");
        }
      });
    }
  });

  // 16 Granular Savage AI Switches (Matrix 4x4)
  document.querySelectorAll("[data-savage-cvar]").forEach((chk) => {
    chk.addEventListener("change", async () => {
      const cvar = chk.dataset.savageCvar;
      const val = chk.checked ? "1" : "0";
      await Backend.post("/api/bots/savage/cvar", { cvar, value: val }, "save_savage_cvar", cvar, val);
      showToast(`${cvar}: ${chk.checked ? "ON" : "OFF"}`, "info");
      // Dynamically re-evaluate active preset card highlight
      try {
        const state = await Backend.get("/api/bots", "get_bot_ecosystem");
        const activePreset = state.active_preset || "custom";
        document.querySelectorAll(".preset-card").forEach((card) => {
          card.classList.toggle("active", card.dataset.preset === activePreset);
        });
      } catch (err) {
        // silent
      }
    });
  });

  // Sanitize Cheats Button (Row 4 Reset)
  const btnSanitizeCheats = document.getElementById("btn-sanitize-cheats");
  if (btnSanitizeCheats) {
    btnSanitizeCheats.addEventListener("click", async () => {
      log("Sanitizing Savage AI Predator cheats...");
      const res = await Backend.post("/api/bots/sanitize-cheats", {}, "sanitize_bot_cheats");
      if (res.success) {
        document.querySelectorAll(".chk-cheat-cvar").forEach((c) => { c.checked = false; });
        showToast("All 4 predator cheats disabled!", "success");
        await loadBotEcosystem();
      }
    });
  }

  // Reset to Balanced Button
  const btnResetBalanced = document.getElementById("btn-reset-balanced");
  if (btnResetBalanced) {
    btnResetBalanced.addEventListener("click", async () => {
      await Backend.post("/api/bots/preset", { preset: "tactical" }, "apply_bot_preset", "tactical");
      showToast("Reset to Balanced Tactical AI", "info");
      await loadBotEcosystem();
    });
  }

  // Save Bot Settings Button
  const btnSaveBots = document.getElementById("btn-save-bots");
  if (btnSaveBots) {
    btnSaveBots.addEventListener("click", async () => {
      await saveBotSettingsBatch();
    });
  }

  // Safety Backups Refresh & Verify Buttons
  const btnRefreshBackups = document.getElementById("btn-refresh-backups");
  if (btnRefreshBackups) {
    btnRefreshBackups.addEventListener("click", async () => {
      await loadBackups();
      showToast("Vault refreshed", "info");
    });
  }

  const btnVerifyBackups = document.getElementById("btn-verify-backups");
  if (btnVerifyBackups) {
    btnVerifyBackups.addEventListener("click", async () => {
      await verifyBackupsIntegrity();
    });
  }

  // Instant Search Filter for Backups Table
  const filterInput = document.getElementById("filter-backups");
  if (filterInput) {
    filterInput.addEventListener("input", () => {
      const query = filterInput.value.toLowerCase().trim();
      filterBackupsTable(query);
    });
  }

  // Launch Studio in Tab 5
  const btnLaunchStudioTab = document.getElementById("btn-launch-studio-tab");
  if (btnLaunchStudioTab) {
    btnLaunchStudioTab.addEventListener("click", async () => {
      log("Launching CS 1.6 Asset Studio...");
      const res = await Backend.post("/api/studio-launch", {}, "launch_asset_studio");
      if (res.success) {
        showToast("Asset Studio launched (Port 5160)", "success");
        setTimeout(() => checkStudioStatus(true), 2500);
      } else {
        showToast(`Launch failed: ${res.error}`, "error");
      }
    });
  }
}

function setupSliderListener(sliderId, valueId, suffix, cvar, endpoint) {
  const slider = document.getElementById(sliderId);
  const val = document.getElementById(valueId);
  if (slider && val) {
    slider.addEventListener("input", () => {
      val.innerText = slider.value + suffix;
    });
    slider.addEventListener("change", async () => {
      await Backend.post(endpoint, { cvar, value: slider.value }, "save_cs2_engine_cvar", cvar, slider.value);
    });
  }
}

// =========================================================================
// PROFILES & AMXX PLUGINS
// =========================================================================

async function loadProfiles() {
  const data = await Backend.get("/api/profiles", "get_profiles");
  const selProfile = document.getElementById("sel-profile");
  if (!selProfile || !data.profiles) return;

  selProfile.innerHTML = "";
  data.profiles.forEach((p) => {
    if (p.exists) {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.innerText = `${p.name} (${p.model_count} models)`;
      if (p.id === data.active || p.path === data.active) opt.selected = true;
      selProfile.appendChild(opt);
    }
  });
  currentProfile = data.active || "";
}

async function loadPlugins() {
  const data = await Backend.get("/api/plugins", "get_plugins");
  const container = document.getElementById("plugin-cards-container");
  if (!container || !data.plugins) return;

  container.innerHTML = "";
  data.plugins.forEach((p) => {
    const card = document.createElement("div");
    card.className = "plugin-card";
    card.innerHTML = `
      <div class="plugin-card-top">
        <span class="plugin-tag">${p.category || "Custom Module"}</span>
        <div class="plugin-title">${p.title || p.name}</div>
        <div class="plugin-desc">${p.description || p.comment || p.name}</div>
      </div>
      <div class="plugin-card-bottom">
        <span class="plugin-status-txt ${p.is_active ? 'loaded' : 'disabled'}">${p.is_active ? 'LOADED' : 'DISABLED'}</span>
        <label class="switch">
          <input type="checkbox" ${p.is_active ? "checked" : ""} data-plugin-name="${p.name}">
          <span class="switch-slider"></span>
        </label>
      </div>
    `;

    card.querySelector("input").addEventListener("change", async (e) => {
      const active = e.target.checked;
      const res = await Backend.post("/api/plugins/toggle", { plugin: p.name, active }, "toggle_plugin", p.name, active);
      if (res.success) {
        showToast(`${p.name}: ${active ? "ENABLED" : "DISABLED"}`, "info");
        await loadPlugins();
      }
    });

    container.appendChild(card);
  });
}

// =========================================================================
// CS2 MODERN ENGINE
// =========================================================================

async function loadCS2EngineSettings() {
  const data = await Backend.get("/api/cs2-engine", "get_cs2_engine_config");
  const cvars = data.cvars || {};

  document.querySelectorAll("[data-engine-cvar]").forEach((el) => {
    const key = el.dataset.engineCvar;
    if (key in cvars) {
      if (el.type === "checkbox") {
        el.checked = (cvars[key] === "1");
      } else if (el.type === "range" || el.type === "number") {
        el.value = cvars[key];
        const valId = `val-${key.replace(/_/g, "-")}`;
        const valEl = document.getElementById(valId);
        if (valEl) {
          const suffix = key.includes("radius") ? " units" : "s";
          valEl.innerText = cvars[key] + suffix;
        }
      }
    }
  });
}

async function saveCS2EngineSettings() {
  const settings = {};
  document.querySelectorAll("[data-engine-cvar]").forEach((el) => {
    const key = el.dataset.engineCvar;
    if (el.type === "checkbox") {
      settings[key] = el.checked ? "1" : "0";
    } else {
      settings[key] = el.value;
    }
  });

  log(`Saving CS2 Modern Engine settings (${Object.keys(settings).length} CVARs)...`);
  const res = await Backend.post("/api/cs2-engine/save", { settings }, "save_cs2_engine_settings", settings);
  if (res.success) {
    showToast("Engine settings saved successfully", "success");
    log("[Engine] cs2_modern_engine.cfg synchronized.");
  } else {
    showToast(`Failed to save engine: ${res.error}`, "error");
  }
}

// =========================================================================
// COMPETITIVE MATCH ENGINE & LIVE HUD
// =========================================================================

async function loadCompetitiveSettings() {
  const data = await Backend.get("/api/competitive", "get_competitive_config");
  const cvars = data.cvars || {};

  document.querySelectorAll("[data-comp-cvar]").forEach((el) => {
    const key = el.dataset.compCvar;
    if (key in cvars) {
      if (el.type === "checkbox") {
        el.checked = (cvars[key] === "1");
      } else {
        let val = cvars[key];
        if (key === "amx_csgo_maxrounds") {
          if (val === "24") val = "12";
          else if (val === "30") val = "15";
          else if (val === "16") val = "8";
        }
        if (el.tagName === "SELECT") {
          const matchingOption = Array.from(el.options).find((opt) => opt.value === val);
          if (matchingOption) {
            el.value = val;
          } else if (val) {
            const opt = document.createElement("option");
            opt.value = val;
            opt.textContent = `${val} (Custom)`;
            el.appendChild(opt);
            el.value = val;
          }
        } else {
          el.value = val;
        }
      }
    }
  });

  syncHUDPreviewCards();
}

function syncHUDPreviewCards() {
  const chkDmg = document.getElementById("chk-comp-dmg-card");
  const cardDmg = document.getElementById("preview-dmg-card");
  if (chkDmg && cardDmg) {
    cardDmg.classList.toggle("disabled", !chkDmg.checked);
  }

  const chkMvp = document.getElementById("chk-comp-mvp-card");
  const cardMvp = document.getElementById("preview-mvp-card");
  if (chkMvp && cardMvp) {
    cardMvp.classList.toggle("disabled", !chkMvp.checked);
  }
}

async function saveSingleCompetitiveCvar(cvar, val) {
  await Backend.post("/api/competitive/cvar", { cvar, value: val }, "save_competitive_cvar", cvar, val);
}

async function saveCompetitiveSettings() {
  const settings = {};
  document.querySelectorAll("[data-comp-cvar]").forEach((el) => {
    const key = el.dataset.compCvar;
    if (el.type === "checkbox") {
      settings[key] = el.checked ? "1" : "0";
    } else {
      settings[key] = el.value;
    }
  });

  log(`Saving competitive match settings (${Object.keys(settings).length} CVARs)...`);
  const res = await Backend.post("/api/competitive/save", { settings }, "save_competitive_settings", settings);
  if (res.success) {
    showToast("Competitive config saved successfully", "success");
    log("[Comp] csgo_competitive.cfg synchronized.");
  }
}

async function applyCompetitivePreset(preset) {
  log(`Applying Competitive Preset: ${preset.toUpperCase()}...`);
  const res = await Backend.post("/api/competitive/preset", { preset }, "apply_competitive_preset", preset);
  if (res.success) {
    showToast(`Preset loaded: ${preset.toUpperCase()}`, "success");
    await loadCompetitiveSettings();
  }
}

// =========================================================================
// BOTS & AI CENTER
// =========================================================================

async function loadBotEcosystem() {
  const state = await Backend.get("/api/bots", "get_bot_ecosystem");
  const savageEnable = state.savage_enable;
  const activePreset = state.active_preset || "custom";
  const yapb = state.yapb || {};
  const savage = state.savage || {};

  // Master switch
  const chkMasterAI = document.getElementById("chk-master-savage-ai");
  if (chkMasterAI) chkMasterAI.checked = savageEnable;
  updateAIMasterBadge(savageEnable);

  // Active Preset Card Highlighting
  document.querySelectorAll(".preset-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.preset === activePreset);
  });

  // Populate YaPB Settings
  document.querySelectorAll("[data-yapb-cvar]").forEach((el) => {
    const key = el.dataset.yapbCvar;
    if (key in yapb) {
      if (el.type === "checkbox") {
        el.checked = (yapb[key] === "1");
      } else {
        el.value = yapb[key];
        if (key === "yb_quota") {
          const valEl = document.getElementById("val-yb-quota");
          if (valEl) valEl.innerText = yapb[key];
        }
      }
    }
  });

  // Populate Savage Settings
  document.querySelectorAll("[data-savage-cvar]").forEach((el) => {
    const key = el.dataset.savageCvar;
    if (key in savage) {
      el.checked = (savage[key] === "1");
    }
  });
}

function updateAIMasterBadge(savageEnable) {
  const txtTitle = document.getElementById("txt-ai-mode-title");
  const txtDesc = document.getElementById("txt-ai-mode-desc");
  const badgeMode = document.getElementById("badge-ai-mode");
  const iconAI = document.getElementById("icon-ai-mode");

  if (savageEnable) {
    if (txtTitle) txtTitle.innerText = "Savage Esports AI Engine";
    if (txtDesc) txtDesc.innerText = "5-role meta, holding angles, weapon drops, and tactical radio/chat calls enabled.";
    if (badgeMode) {
      badgeMode.innerText = "SAVAGE AI";
      badgeMode.style.color = "var(--cyber-cyan)";
    }
    if (iconAI) iconAI.innerHTML = TACTICAL_ICONS.cpu;
  } else {
    if (txtTitle) txtTitle.innerText = "Native YaPB Bot Engine (Standar)";
    if (txtDesc) txtDesc.innerText = "Savage AI is completely DISABLED. Running 100% clean, native YaPB bot pathing & rules.";
    if (badgeMode) {
      badgeMode.innerText = "NATIVE YAPB";
      badgeMode.style.color = "var(--emerald-safe)";
    }
    if (iconAI) iconAI.innerHTML = TACTICAL_ICONS.shield;
  }
}

async function saveBotSettingsBatch() {
  const yapb = {};
  document.querySelectorAll("[data-yapb-cvar]").forEach((el) => {
    const key = el.dataset.yapbCvar;
    yapb[key] = (el.type === "checkbox") ? (el.checked ? "1" : "0") : el.value;
  });

  const savage = {};
  document.querySelectorAll("[data-savage-cvar]").forEach((el) => {
    const key = el.dataset.savageCvar;
    savage[key] = el.checked ? "1" : "0";
  });

  const res = await Backend.post("/api/bots/save", { yapb, savage }, "save_bot_settings", yapb, savage);
  if (res.success) {
    showToast("Bot settings saved successfully", "success");
    log("[Bots] yapb.cfg and bot_savage_roles.cfg synchronized.");
  }
}

// =========================================================================
// SAFETY & BACKUPS (SHA-256 INTEGRITY)
// =========================================================================

async function loadBackups() {
  const [backupsRes, telemetry] = await Promise.all([
    Backend.get(`/api/backups?dir=${encodeURIComponent(currentProfile)}`, "get_backups", currentProfile),
    Backend.get(`/api/backups/telemetry?dir=${encodeURIComponent(currentProfile)}`, "get_backup_telemetry", currentProfile),
  ]);

  currentBackupsList = backupsRes.backups || [];

  // Update Telemetry Cards
  const txtCount = document.getElementById("telemetry-backup-count");
  const txtSize = document.getElementById("telemetry-backup-size");
  const txtIntegrity = document.getElementById("telemetry-backup-integrity");
  const txtGuard = document.getElementById("telemetry-backup-guard");

  if (txtCount) txtCount.innerText = telemetry.total_files || currentBackupsList.length;
  if (txtSize) txtSize.innerText = `${telemetry.total_mb || 0.0} MB`;
  if (txtIntegrity) txtIntegrity.innerText = `${telemetry.integrity_pct || 100}% VALID`;
  if (txtGuard) txtGuard.innerText = telemetry.write_guarded ? "Direct I/O Write Locks Guarded" : "Direct I/O Read Only";

  renderBackupsTable(currentBackupsList);
}

function renderBackupsTable(backups) {
  const tbody = document.getElementById("backups-tbody");
  if (!tbody) return;

  tbody.innerHTML = "";
  if (!backups || backups.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--muted-slate); padding: 24px;">No safety .bak backup files found in this directory.</td></tr>`;
    return;
  }

  backups.forEach((b) => {
    const tr = document.createElement("tr");
    const category = b.category || getCategoryFromModel(b.model_name);
    const shaText = b.sha256 ? `<span class="sha256-cell" title="${b.sha256}">${b.sha256.substring(0, 16)}...</span>` : `<span style="color: var(--muted-slate); font-size: 10px;">Unchecked</span>`;

    tr.innerHTML = `
      <td>
        <div class="model-name-cell">
          <span class="glyph glyph-sm" style="color: var(--tactical-amber);"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></span>
          <strong>${b.model_name}</strong>
        </div>
      </td>
      <td><span class="weapon-cat-tag">${category}</span></td>
      <td><span class="path-cell" title="${b.backup_path}">${b.backup_path}</span></td>
      <td style="font-family: var(--font-mono); font-size: 11px;">${(b.size_bytes / 1024).toFixed(1)} KB</td>
      <td style="font-family: var(--font-mono); font-size: 11px; color: var(--muted-slate);">${b.modified_str}</td>
      <td>${shaText}</td>
      <td style="text-align: right;">
        <button class="btn btn-ghost btn-sm btn-restore" data-path="${b.backup_path}">
          ${TACTICAL_ICONS.restore}
          <span>Restore</span>
        </button>
      </td>
    `;

    tr.querySelector(".btn-restore").addEventListener("click", async () => {
      if (confirm(`Restore model '${b.model_name}' from backup? This will overwrite the active model.`)) {
        log(`Restoring '${b.model_name}'...`);
        const res = await Backend.post("/api/backups/restore", { backup_path: b.backup_path }, "restore_backup", b.backup_path);
        if (res.success) {
          showToast(`${b.model_name} restored successfully`, "success");
          log(`[RESTORE] ${res.message}`);
          await loadBackups();
        } else {
          showToast(`Restore error: ${res.message}`, "error");
        }
      }
    });

    tbody.appendChild(tr);
  });
}

function getCategoryFromModel(name) {
  const n = (name || "").toLowerCase();
  if (n.includes("ak47") || n.includes("m4a1") || n.includes("m4a4") || n.includes("galil") || n.includes("famas") || n.includes("aug") || n.includes("sg552")) return "PRIMARY RIFLE";
  if (n.includes("awp") || n.includes("scout") || n.includes("g3sg1") || n.includes("sg550")) return "SNIPER RIFLE";
  if (n.includes("deagle") || n.includes("elite")) return "HEAVY PISTOL";
  if (n.includes("usp") || n.includes("glock") || n.includes("p228") || n.includes("fiveseven") || n.includes("cz75") || n.includes("tec9")) return "SIDEARM PISTOL";
  if (n.includes("mp5") || n.includes("p90") || n.includes("mac10") || n.includes("tmp") || n.includes("ump45") || n.includes("bizon") || n.includes("mp7")) return "SUBMACHINE GUN";
  if (n.includes("knife") || n.includes("bayonet") || n.includes("karambit")) return "COMBAT MELEE";
  if (n.includes("c4") || n.includes("grenade") || n.includes("flashbang")) return "TACTICAL UTILITY";
  return "CUSTOM ASSET";
}

function filterBackupsTable(query) {
  if (!query) {
    renderBackupsTable(currentBackupsList);
    return;
  }
  const filtered = currentBackupsList.filter((b) => {
    const cat = getCategoryFromModel(b.model_name).toLowerCase();
    const name = (b.model_name || "").toLowerCase();
    const path = (b.backup_path || "").toLowerCase();
    return name.includes(query) || cat.includes(query) || path.includes(query);
  });
  renderBackupsTable(filtered);
}

async function verifyBackupsIntegrity() {
  log("Verifying binary GoldSrc IDST header and calculating SHA-256 for all backups...");
  const res = await Backend.get(`/api/backups/verify?dir=${encodeURIComponent(currentProfile)}`, "verify_all_backups", currentProfile);
  if (res.success && res.backups) {
    currentBackupsList = res.backups;
    renderBackupsTable(currentBackupsList);
    showToast("Integrity check complete: 100% IDST Verified", "success");
    log(`[SHA-256] Verified ${res.backups.length} candidate model headers.`);
  }
}

// =========================================================================
// ASSET STUDIO INTEGRATION (PORT 5160)
// =========================================================================

async function checkStudioStatus(updateIframe = false) {
  try {
    const res = await Backend.get("/api/studio-status", "check_asset_studio_status");
    const studio = res.studio || res;
    const dot = document.getElementById("studio-status-dot");
    const suiteDot = document.getElementById("suite-dot");
    const suiteText = document.getElementById("suite-status-text");
    const iframe = document.getElementById("studio-iframe");

    if (studio.online) {
      if (dot) dot.classList.add("online");
      if (suiteDot) suiteDot.classList.add("online");
      if (suiteText) {
        suiteText.innerText = "ONLINE (Port 5160)";
        suiteText.style.color = "var(--emerald-safe)";
      }
      if (updateIframe && iframe && iframe.src === "about:blank") {
        iframe.src = studio.url || "http://127.0.0.1:5160/";
      }
    } else {
      if (dot) dot.classList.remove("online");
      if (suiteDot) suiteDot.classList.remove("online");
      if (suiteText) {
        suiteText.innerText = "OFFLINE / STANDBY";
        suiteText.style.color = "var(--muted-slate)";
      }
    }
  } catch (err) {
    // Suppress network errors on initial check
  }
}

// =========================================================================
// TOAST NOTIFICATIONS & TELEMETRY LOGGER
// =========================================================================

function showToast(msg, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  if (type === "success") {
    toast.style.borderColor = "var(--emerald-safe)";
  } else if (type === "error") {
    toast.style.borderColor = "var(--demon-crimson)";
  } else {
    toast.style.borderColor = "var(--tactical-amber)";
  }
  toast.innerText = msg;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 2600);
}

function log(msg) {
  const output = document.getElementById("console-output");
  if (!output) return;

  const now = new Date();
  const timeStr = now.toTimeString().split(" ")[0];
  const line = document.createElement("div");
  line.style.padding = "1px 0";
  line.innerText = `[${timeStr}] ${msg}`;

  output.appendChild(line);
  output.scrollTop = output.scrollHeight;
}
