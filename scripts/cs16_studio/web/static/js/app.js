/**
 * app.js - CS 1.6 Asset Studio Pro Next-Gen Modular Orchestrator
 * High-performance, component-based decoupling architecture.
 * Linear / Figma / Spline / CS2 Loadout inspired workspace.
 */

import { state, eventBus } from "./core/state.js";
import { apiGet, apiPost, showToast, showLoader, hideLoader, elements } from "./core/api.js";

import { initSlotsModule } from "./modules/slots.js";
import { initColorStudioModule, setupColorStudioTab } from "./modules/color_studio.js";
import { initViewer3DModule, initOrUpdate3DViewer, resize3DViewport } from "./modules/viewer3d.js";
import { initBakeModule, setupBakeTab } from "./modules/bake.js";
import { initLibraryModule } from "./modules/library.js";
import { initProfilesModule } from "./modules/profiles.js";
import { initProToolsModule, openProToolsModal } from "./modules/pro_tools.js";
import { initChromeStudioModule, refreshChromeStatus } from "./modules/chrome_studio.js";
import { initQoLModule } from "./modules/qol.js";
import { initVaultModule, openSaveToVaultModal, openVaultModal } from "./modules/vault.js";

// Weapon categorization schema for CS2-style Visual Loadout Drawer
const WEAPON_CATEGORIES = {
  pistols: {
    label: "Pistols",
    icon: "weapon",
    weapons: ["usp", "glock18", "deagle", "p228", "elites", "elite", "fiveseven", "tec9"],
  },
  rifles: {
    label: "Rifles & Snipers",
    icon: "rifle",
    weapons: ["ak47", "m4a1", "m4a4", "awp", "scout", "galil", "famas", "sg552", "aug", "g3sg1", "sg550"],
  },
  smgs: {
    label: "SMGs",
    icon: "smg",
    weapons: ["mp5", "p90", "ump45", "mac10", "tmp", "mp7", "bizon", "cz75", "cz75_tmp", "cz75_mac10"],
  },
  heavy: {
    label: "Heavy",
    icon: "heavy",
    weapons: ["m3", "xm1014", "m249", "mag7", "sawedoff", "negev"],
  },
  gear: {
    label: "Equipment & Knives",
    icon: "gear-knife",
    weapons: [
      "knife", "knife_m9", "knife_karambit", "knife_butterfly", "knife_huntsman", "knife_bayonet",
      "c4", "flashbang", "hegrenade", "smokegrenade",
    ],
  },
};

// Base weapon groups with variant definitions for Drawer Sub-Pill Navigation

// Resolves tactical vector glyph based on weapon id and category
function getTacticalWeaponGlyph(weaponId, category) {
  const wid = (weaponId || "").toLowerCase();
  if (category === "gear" || wid.includes("knife")) return "gear-knife";
  if (wid === "awp" || wid === "scout" || wid === "g3sg1" || wid === "sg550") return "sniper";
  if (category === "rifles") return "rifle";
  if (category === "smgs") return "smg";
  if (category === "heavy") return "heavy";
  return "weapon"; // pistols & default tactical handgun
}

const WEAPON_GROUPS_DEF = [
  // Gear / Knives
  {
    groupKey: "knife",
    category: "gear",
    title: "KNIFE",
    variants: [
      { id: "knife", label: "Default" },
      { id: "knife_m9", label: "M9 Bayonet" },
      { id: "knife_karambit", label: "Karambit" },
      { id: "knife_butterfly", label: "Butterfly" },
      { id: "knife_huntsman", label: "Huntsman" },
      { id: "knife_bayonet", label: "Bayonet" },
    ],
  },
  // Rifles
  {
    groupKey: "m4a1",
    category: "rifles",
    title: "M4A1",
    variants: [
      { id: "m4a1", label: "M4A1-S" },
      { id: "m4a4", label: "M4A4" },
    ],
  },
  { groupKey: "ak47", category: "rifles", title: "AK-47", variants: [{ id: "ak47", label: "AK-47" }] },
  { groupKey: "awp", category: "rifles", title: "AWP", variants: [{ id: "awp", label: "AWP" }] },
  { groupKey: "scout", category: "rifles", title: "SCOUT", variants: [{ id: "scout", label: "Scout" }] },
  { groupKey: "galil", category: "rifles", title: "GALIL", variants: [{ id: "galil", label: "Galil" }] },
  { groupKey: "famas", category: "rifles", title: "FAMAS", variants: [{ id: "famas", label: "FAMAS" }] },
  { groupKey: "aug", category: "rifles", title: "AUG", variants: [{ id: "aug", label: "AUG" }] },
  { groupKey: "sg552", category: "rifles", title: "SG 552", variants: [{ id: "sg552", label: "SG 552" }] },
  { groupKey: "g3sg1", category: "rifles", title: "G3SG1", variants: [{ id: "g3sg1", label: "G3SG1" }] },
  { groupKey: "sg550", category: "rifles", title: "SG 550", variants: [{ id: "sg550", label: "SG 550" }] },
  // SMGs
  {
    groupKey: "mp5",
    category: "smgs",
    title: "MP5",
    variants: [
      { id: "mp5", label: "MP5-SD" },
      { id: "mp7", label: "MP7" },
    ],
  },
  {
    groupKey: "p90",
    category: "smgs",
    title: "P90",
    variants: [
      { id: "p90", label: "P90" },
      { id: "bizon", label: "PP-Bizon" },
    ],
  },
  { groupKey: "ump45", category: "smgs", title: "UMP-45", variants: [{ id: "ump45", label: "UMP-45" }] },
  {
    groupKey: "mac10",
    category: "smgs",
    title: "MAC-10",
    variants: [
      { id: "mac10", label: "MAC-10" },
      { id: "cz75", label: "CZ75-Auto" },
      { id: "cz75_mac10", label: "CZ75-Auto" },
    ],
  },
  {
    groupKey: "tmp",
    category: "smgs",
    title: "TMP",
    variants: [
      { id: "tmp", label: "TMP" },
      { id: "cz75", label: "CZ75-Auto" },
      { id: "cz75_tmp", label: "CZ75-Auto" },
    ],
  },
  // Heavy
  {
    groupKey: "xm1014",
    category: "heavy",
    title: "XM1014",
    variants: [
      { id: "xm1014", label: "XM1014" },
      { id: "mag7", label: "MAG-7" },
    ],
  },
  {
    groupKey: "m3",
    category: "heavy",
    title: "M3",
    variants: [
      { id: "m3", label: "M3 90" },
      { id: "sawedoff", label: "Sawed-Off" },
    ],
  },
  {
    groupKey: "m249",
    category: "heavy",
    title: "M249",
    variants: [
      { id: "m249", label: "M249" },
      { id: "negev", label: "Negev" },
    ],
  },
  // Pistols
  { groupKey: "usp", category: "pistols", title: "USP", variants: [{ id: "usp", label: "USP-S" }] },
  { groupKey: "glock18", category: "pistols", title: "GLOCK-18", variants: [{ id: "glock18", label: "Glock-18" }] },
  { groupKey: "deagle", category: "pistols", title: "DESERT EAGLE", variants: [{ id: "deagle", label: "Deagle" }] },
  {
    groupKey: "p228",
    category: "pistols",
    title: "P228",
    variants: [
      { id: "p228", label: "P228" },
      { id: "tec9", label: "Tec-9" },
    ],
  },
  { groupKey: "fiveseven", category: "pistols", title: "FIVE-SEVEN", variants: [{ id: "fiveseven", label: "Five-SeveN" }] },
  {
    groupKey: "elites",
    category: "pistols",
    title: "DUAL ELITES",
    variants: [
      { id: "elites", label: "Dual Elites" },
      { id: "elite", label: "Dual Elites" },
    ],
  },
  // Grenades & C4
  { groupKey: "c4", category: "gear", title: "C4 EXPLOSIVE", variants: [{ id: "c4", label: "C4" }] },
  { groupKey: "hegrenade", category: "gear", title: "HE GRENADE", variants: [{ id: "hegrenade", label: "HE" }] },
  { groupKey: "flashbang", category: "gear", title: "FLASHBANG", variants: [{ id: "flashbang", label: "Flash" }] },
  { groupKey: "smokegrenade", category: "gear", title: "SMOKE GRENADE", variants: [{ id: "smokegrenade", label: "Smoke" }] },
];

function getWeaponCategory(weapon) {
  const w = (weapon || "").toLowerCase().replace(/^v_/, "").replace(/\.mdl$/, "");
  if (w.startsWith("knife") || WEAPON_CATEGORIES.gear.weapons.includes(w)) return "gear";
  if (WEAPON_CATEGORIES.rifles.weapons.includes(w)) return "rifles";
  if (WEAPON_CATEGORIES.smgs.weapons.includes(w)) return "smgs";
  if (WEAPON_CATEGORIES.heavy.weapons.includes(w)) return "heavy";
  return "pistols";
}

// Safe localStorage helpers
function safeStorageGet(key, fallback = null) {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function safeStorageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {}
}

// Master Next-Gen Initializer
export async function initApp() {
  try { setupNavigation(); } catch (err) { console.error("setupNavigation error:", err); }
  try { setupTeamToggle(); } catch (err) { console.error("setupTeamToggle error:", err); }
  try { setupWeaponDropdown(); } catch (err) { console.error("setupWeaponDropdown error:", err); }
  try { setupStudioLayout(); } catch (err) { console.error("setupStudioLayout error:", err); }

  // Initialize individual component modules with isolated fault domains
  try { initSlotsModule(); } catch (err) { console.error("initSlotsModule error:", err); }
  try { initColorStudioModule(); } catch (err) { console.error("initColorStudioModule error:", err); }
  try { initViewer3DModule(); } catch (err) { console.error("initViewer3DModule error:", err); }
  try { initBakeModule(); } catch (err) { console.error("initBakeModule error:", err); }
  try { initLibraryModule(); } catch (err) { console.error("initLibraryModule error:", err); }
  try { initProfilesModule();
  initPwSyncPromptModal(); } catch (err) { console.error("initProfilesModule error:", err); }
  try { initProToolsModule(); } catch (err) { console.error("initProToolsModule error:", err); }
  try { initChromeStudioModule(); } catch (err) { console.error("initChromeStudioModule error:", err); }
  try { initQoLModule(); } catch (err) { console.error("initQoLModule error:", err); }
  try { initVaultModule(); } catch (err) { console.error("initVaultModule error:", err); }
  try {
    updateEngineTelemetry();
    setInterval(updateEngineTelemetry, 8000);
    window.addEventListener("focus", updateEngineTelemetry);
    updateTripletTelemetry();
  } catch (err) {
    console.error("updateEngineTelemetry error:", err);
  }

  // Global event bus listeners
  eventBus.on("model:reloadRequest", () => {
    loadActiveModel();
  });

  eventBus.on("weapon:changed", ({ weapon, team }) => {
    state.currentWeapon = weapon;
    if (team) state.currentTeam = team;
    loadActiveModel();
    updateActiveDrawerWeaponCard();
    updateTripletTelemetry(weapon, team || state.currentTeam);
  });

  eventBus.on("team:toggle", (team) => {
    state.currentTeam = team;
    updateTeamButtonsUI();
    populateWeaponSelect();
  });

  eventBus.on("triplet:changed", (payload) => {
    loadActiveModel(payload?.type);
  });

  // Discover and load initial model list
  try {
    await fetchAvailableModels();
  } catch (err) {
    console.error("fetchAvailableModels error:", err);
  }

  // Initialize 3D Hero Viewport immediately
  try {
    initOrUpdate3DViewer();
  } catch (err) {
    console.error("initOrUpdate3DViewer error:", err);
  }
}

// Dual-trigger execution: fires immediately if document is already ready, or on DOMContentLoaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}

// Expose global debug & automation hooks
if (typeof window !== "undefined") {
  window.initApp = initApp;
  window.loadWeapons = fetchAvailableModels;
  window.loadModel = (wep, team) => {
    if (wep) state.currentWeapon = wep;
    if (team) state.currentTeam = team;
    return loadActiveModel();
  };
}

// Setup next-generation workspace layout (Rail, Drawer, Hero Stage, Inspector Dock)
function setupStudioLayout() {
  const drawer = document.getElementById("left-drawer") || document.getElementById("studioDrawer");
  const railBtnLoadout = document.getElementById("railBtnLoadout");
  const railBtnSkinLibrary = document.getElementById("railBtnSkinLibrary");
  const railBtnStickerLibrary = document.getElementById("railBtnStickerLibrary");
  const railBtnProfiles = document.getElementById("railBtnProfiles");
  const railBtnToggleDrawer = document.getElementById("railBtnToggleDrawer");

  const drawerViewWeapons = document.getElementById("drawerViewWeapons");
  const drawerViewSkinLibrary = document.getElementById("drawerViewSkinLibrary");
  const drawerViewStickerLibrary = document.getElementById("drawerViewStickerLibrary");
  const drawerViewProfiles = document.getElementById("drawerViewProfiles");

  const drawerSearch = document.getElementById("drawerWeaponSearch");

  // Auto-migration cleanup: remove stale dock height and initialize dock width
  try {
    localStorage.removeItem("cs16_dock_height");
  } catch {}
  const savedDockWidth = safeStorageGet("cs16_dock_width", "440");
  document.documentElement.style.setProperty("--dock-width", `${savedDockWidth}px`);

  // Auto-collapse drawer on smaller mobile/tablet screens (<= 960px)
  if (drawer && window.innerWidth <= 960) {
    drawer.classList.add("collapsed");
    [railBtnLoadout, railBtnSkinLibrary, railBtnStickerLibrary, railBtnProfiles].forEach((b) => b && b.classList.remove("active"));
  }

  // Active Model Pill click trigger for Command Palette
  const modelActivePill = document.getElementById("modelActivePill");
  if (modelActivePill) {
    const triggerCommandPalette = () => {
      const quickSearchBtn = document.getElementById("quickSearchBtn");
      if (quickSearchBtn) quickSearchBtn.click();
    };
    modelActivePill.addEventListener("click", triggerCommandPalette);
    modelActivePill.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        triggerCommandPalette();
      }
    });
  }

  // Last active drawer tab tracking
  let currentActiveBtn = railBtnLoadout;
  let currentActiveView = drawerViewWeapons;

  // Rail View Switching (VS Code pattern: click active icon to toggle/collapse drawer)
  function switchDrawerView(activeBtn, targetView) {
    const isDrawerOpen = drawer && !drawer.classList.contains("collapsed");
    const isAlreadyActive = activeBtn && activeBtn.classList.contains("active");

    // If drawer is currently OPEN and user clicks the ALREADY ACTIVE rail icon, collapse the drawer!
    if (isDrawerOpen && isAlreadyActive) {
      if (drawer) drawer.classList.add("collapsed");
      const splitterBottom = document.getElementById("splitterBottom");
      if (splitterBottom) splitterBottom.classList.add("hidden-splitter");
      [railBtnLoadout, railBtnSkinLibrary, railBtnStickerLibrary, railBtnProfiles].forEach((b) => b && b.classList.remove("active"));
      window.dispatchEvent(new Event("resize"));
      resize3DViewport();
      setTimeout(() => resize3DViewport(), 260);
      return;
    }

    [railBtnLoadout, railBtnSkinLibrary, railBtnStickerLibrary, railBtnProfiles].forEach((b) => b && b.classList.remove("active"));
    [drawerViewWeapons, drawerViewSkinLibrary, drawerViewStickerLibrary, drawerViewProfiles].forEach((v) => v && v.classList.remove("active"));

    if (activeBtn) activeBtn.classList.add("active");
    if (targetView) targetView.classList.add("active");

    currentActiveBtn = activeBtn;
    currentActiveView = targetView;

    // Expand drawer if it was collapsed
    if (drawer && drawer.classList.contains("collapsed")) {
      drawer.classList.remove("collapsed");
      const splitterBottom = document.getElementById("splitterBottom");
      if (splitterBottom) splitterBottom.classList.remove("hidden-splitter");
      window.dispatchEvent(new Event("resize"));
      resize3DViewport();
      setTimeout(() => resize3DViewport(), 260);
    }
  }

  if (railBtnLoadout) railBtnLoadout.addEventListener("click", () => switchDrawerView(railBtnLoadout, drawerViewWeapons));
  if (railBtnSkinLibrary) railBtnSkinLibrary.addEventListener("click", () => switchDrawerView(railBtnSkinLibrary, drawerViewSkinLibrary));
  if (railBtnStickerLibrary) railBtnStickerLibrary.addEventListener("click", () => switchDrawerView(railBtnStickerLibrary, drawerViewStickerLibrary));
  if (railBtnProfiles) railBtnProfiles.addEventListener("click", () => switchDrawerView(railBtnProfiles, drawerViewProfiles));

  // Drawer Toggle (Collapse / Expand via Ctrl+B or bottom toggle button)
  function toggleDrawer() {
    if (!drawer) return;
    const isNowCollapsed = drawer.classList.toggle("collapsed");
    const splitterBottom = document.getElementById("splitterBottom");
    if (splitterBottom) splitterBottom.classList.toggle("hidden-splitter", isNowCollapsed);
    if (isNowCollapsed) {
      [railBtnLoadout, railBtnSkinLibrary, railBtnStickerLibrary, railBtnProfiles].forEach((b) => b && b.classList.remove("active"));
    } else {
      [railBtnLoadout, railBtnSkinLibrary, railBtnStickerLibrary, railBtnProfiles].forEach((b) => b && b.classList.remove("active"));
      [drawerViewWeapons, drawerViewSkinLibrary, drawerViewStickerLibrary, drawerViewProfiles].forEach((v) => v && v.classList.remove("active"));

      const btnToRestore = currentActiveBtn || railBtnLoadout;
      const viewToRestore = currentActiveView || drawerViewWeapons;
      if (btnToRestore) btnToRestore.classList.add("active");
      if (viewToRestore) viewToRestore.classList.add("active");
    }
    window.dispatchEvent(new Event("resize"));
    resize3DViewport();
    setTimeout(() => resize3DViewport(), 260);
  }

  if (railBtnToggleDrawer) railBtnToggleDrawer.addEventListener("click", () => toggleDrawer());

  // Right Inspector Dock Toggle (Collapse / Expand)
  function toggleDock() {
    const dock = document.getElementById("studioInspectorDock");
    const splitterRight = document.getElementById("splitterRight");
    if (!dock) return;
    const isCollapsed = dock.classList.toggle("collapsed");
    if (splitterRight) splitterRight.classList.toggle("hidden-dock", isCollapsed);
    window.dispatchEvent(new Event("resize"));
    resize3DViewport();
    setTimeout(() => resize3DViewport(), 260);
  }

  const toggleDockBtn = document.getElementById("toggleDockBtn");
  if (toggleDockBtn) {
    toggleDockBtn.addEventListener("click", () => toggleDock());
  }

  // Zen Viewport Mode (Toggle full 3D focus)
  function toggleZenMode() {
    const container = document.querySelector(".studio-workspace-container");
    const stageZenBtn = document.getElementById("stageZenBtn");
    if (!container) return;
    const isZen = container.classList.toggle("zen-mode");
    if (stageZenBtn) stageZenBtn.classList.toggle("zen-active", isZen);
    window.dispatchEvent(new Event("resize"));
    resize3DViewport();
    setTimeout(() => resize3DViewport(), 260);
  }

  const stageZenBtn = document.getElementById("stageZenBtn");
  if (stageZenBtn) {
    stageZenBtn.addEventListener("click", () => toggleZenMode());
  }

  // Stage Mode Switcher (3D Viewport / 2D Precision Canvas / Split View)
  function setStageMode(mode) {
    const v3d = document.getElementById("viewport3dCanvasContainer");
    const s2d = document.getElementById("stage2dContainer");
    const btn3d = document.getElementById("stageMode3DBtn");
    const btn2d = document.getElementById("stageMode2DBtn");
    const btnSplit = document.getElementById("stageModeSplitBtn");
    const bakeBtn3d = document.getElementById("bakeMode3DBtn");
    const bakeBtn2d = document.getElementById("bakeMode2DBtn");
    const bakeBtnSplit = document.getElementById("bakeModeSplitBtn");

    if (mode === "3d") {
      if (v3d) v3d.classList.remove("hidden");
      if (s2d) s2d.classList.add("hidden");
      if (btn3d) btn3d.classList.add("active");
      if (btn2d) btn2d.classList.remove("active");
      if (btnSplit) btnSplit.classList.remove("active");
      if (bakeBtn3d) bakeBtn3d.classList.add("active");
      if (bakeBtn2d) bakeBtn2d.classList.remove("active");
      if (bakeBtnSplit) bakeBtnSplit.classList.remove("active");
    } else if (mode === "2d") {
      if (v3d) v3d.classList.add("hidden");
      if (s2d) s2d.classList.remove("hidden");
      if (btn3d) btn3d.classList.remove("active");
      if (btn2d) btn2d.classList.add("active");
      if (btnSplit) btnSplit.classList.remove("active");
      if (bakeBtn3d) bakeBtn3d.classList.remove("active");
      if (bakeBtn2d) bakeBtn2d.classList.add("active");
      if (bakeBtnSplit) bakeBtnSplit.classList.remove("active");
      const bakeArea = document.getElementById("stage2dBakeArea");
      if (bakeArea) bakeArea.classList.remove("hidden");
    } else if (mode === "split") {
      if (v3d) v3d.classList.remove("hidden");
      if (s2d) s2d.classList.remove("hidden");
      if (btn3d) btn3d.classList.remove("active");
      if (btn2d) btn2d.classList.remove("active");
      if (btnSplit) btnSplit.classList.add("active");
      if (bakeBtn3d) bakeBtn3d.classList.remove("active");
      if (bakeBtn2d) bakeBtn2d.classList.remove("active");
      if (bakeBtnSplit) bakeBtnSplit.classList.add("active");
      const bakeArea = document.getElementById("stage2dBakeArea");
      if (bakeArea) bakeArea.classList.remove("hidden");
    }

    window.dispatchEvent(new Event("resize"));
    resize3DViewport();
    setTimeout(() => resize3DViewport(), 160);
  }
  window.setStageMode = setStageMode;

  const stageMode3DBtn = document.getElementById("stageMode3DBtn");
  const stageMode2DBtn = document.getElementById("stageMode2DBtn");
  const stageModeSplitBtn = document.getElementById("stageModeSplitBtn");

  if (stageMode3DBtn) stageMode3DBtn.addEventListener("click", () => setStageMode("3d"));
  if (stageMode2DBtn) stageMode2DBtn.addEventListener("click", () => setStageMode("2d"));
  if (stageModeSplitBtn) stageModeSplitBtn.addEventListener("click", () => setStageMode("split"));

  // Hotkeys: Ctrl+B (Drawer), Ctrl+J (Dock), F11 (Zen Mode)
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === "b" || e.key === "B")) {
      e.preventDefault();
      toggleDrawer();
    } else if ((e.ctrlKey || e.metaKey) && (e.key === "j" || e.key === "J")) {
      e.preventDefault();
      toggleDock();
    } else if (e.key === "F11") {
      e.preventDefault();
      toggleZenMode();
    }
  });

  // Setup Draggable Splitters (Horizontal resize of vertical panels)
  setupSplitters();

  // Setup Left Drawer Collapsible Categories
  setupCategoryCollapsing();

  // Setup 3D Viewport HUD Capsule Minimize / Dimming
  setupHudCapsule();

  // Real-time weapon filter search in drawer with auto-expansion
  if (drawerSearch) {
    drawerSearch.addEventListener("input", (e) => {
      const q = (e.target.value || "").trim().toLowerCase();
      document.querySelectorAll(".drawer-weapon-card").forEach((card) => {
        const w = (card.dataset.weapon || "").toLowerCase();
        const text = card.textContent.toLowerCase();
        const match = !q || w.includes(q) || text.includes(q);
        card.style.display = match ? "flex" : "none";
      });

      // Auto-expand categories with matching weapons when searching
      if (q) {
        document.querySelectorAll(".weapon-category-section").forEach((sec) => {
          const visible = Array.from(sec.querySelectorAll(".drawer-weapon-card")).some(
            (c) => c.style.display !== "none"
          );
          if (visible) sec.classList.remove("collapsed");
        });
      }
    });

    drawerSearch.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        drawerSearch.value = "";
        drawerSearch.dispatchEvent(new Event("input"));
        drawerSearch.blur();
      }
    });
  }

  // Hero Stage Mode Switcher (3D Viewport / 2D Precision Canvas / Split View)
  const mode3DBtn = document.getElementById("stageMode3DBtn");
  const mode2DBtn = document.getElementById("stageMode2DBtn");
  const modeSplitBtn = document.getElementById("stageModeSplitBtn");

  const container3D = document.getElementById("viewport3dCanvasContainer");
  const container2D = document.getElementById("stage2dContainer");
  const footer3dHints = document.getElementById("stageFooter3dHints");
  const footer2dHints = document.getElementById("stageFooter2dHints");

  function setStageMode(mode) {
    [mode3DBtn, mode2DBtn, modeSplitBtn].forEach((b) => b && b.classList.remove("active"));

    if (mode === "3d") {
      if (mode3DBtn) mode3DBtn.classList.add("active");
      if (container3D) {
        container3D.style.display = "block";
        container3D.style.flex = "1";
      }
      if (container2D) {
        container2D.classList.add("hidden");
        container2D.style.flex = "0";
      }
      if (footer3dHints) footer3dHints.classList.remove("hidden");
      if (footer2dHints) footer2dHints.classList.add("hidden");
    } else if (mode === "2d") {
      if (mode2DBtn) mode2DBtn.classList.add("active");
      if (container3D) {
        container3D.style.display = "none";
        container3D.style.flex = "0";
      }
      if (container2D) {
        container2D.classList.remove("hidden");
        container2D.style.flex = "1";
      }
      if (footer3dHints) footer3dHints.classList.add("hidden");
      if (footer2dHints) footer2dHints.classList.remove("hidden");
    } else if (mode === "split") {
      if (modeSplitBtn) modeSplitBtn.classList.add("active");
      if (container3D) {
        container3D.style.display = "block";
        container3D.style.flex = "1";
      }
      if (container2D) {
        container2D.classList.remove("hidden");
        container2D.style.flex = "1";
      }
      if (footer3dHints) footer3dHints.classList.remove("hidden");
      if (footer2dHints) footer2dHints.classList.remove("hidden");
    }

    // Trigger Three.js aspect ratio update
    setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 50);
  }

  if (mode3DBtn) mode3DBtn.addEventListener("click", () => setStageMode("3d"));
  if (mode2DBtn) mode2DBtn.addEventListener("click", () => setStageMode("2d"));
  if (modeSplitBtn) modeSplitBtn.addEventListener("click", () => setStageMode("split"));

  // Topbar "Pro Tools" fallback button (if present) switches Inspector Dock to Gloves/Pro tab
  const openProToolsBtn = document.getElementById("openProToolsBtn");
  if (openProToolsBtn) {
    openProToolsBtn.addEventListener("click", () => {
      const dockTabGloves = document.getElementById("dockTabGloves");
      if (dockTabGloves) dockTabGloves.click();
    });
  }

  // Topbar In-Game Equip Button
  const equipInGameBtn = document.getElementById("equipInGameBtn");
  if (equipInGameBtn) {
    equipInGameBtn.addEventListener("click", async () => {
      const wep = state.currentWeapon;
      const team = state.currentTeam;
      if (!wep) return;
      showLoader(`Equipping ${wep.toUpperCase()} in-game...`);
      try {
        const res = await apiPost("/api/amxx/loadout/equip", { team, weapon: wep });
        if (!res.success) throw new Error(res.error || "Failed to equip");
        if (!state.activeLoadout) state.activeLoadout = { ct: {}, t: {} };
        if (!state.activeLoadout[team]) state.activeLoadout[team] = {};
        if (res.slot) {
          state.activeLoadout[team][res.slot] = res.model_path || wep;
        }
        showToast(res.message || `Equipped ${wep.toUpperCase()} for ${team.toUpperCase()}!`, "success");
        updateInGameEquipButton();
        updateActiveDrawerWeaponCard();
      } catch (err) {
        showToast(`Equip failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
    });
  }

  // Topbar P/W Sync Trigger Button
  const syncPwTopbarBtn = document.getElementById("syncPwTopbarBtn");
  if (syncPwTopbarBtn) {
    syncPwTopbarBtn.addEventListener("click", () => {
      eventBus.emit("amxx:requestSyncPw");
    });
  }

  // Dock Footer Quick Save Snapshot Button
  const dockQuickSaveBtn = document.getElementById("dockQuickSaveBtn");
  if (dockQuickSaveBtn) {
    dockQuickSaveBtn.addEventListener("click", () => {
      const saveProfileBtn = document.getElementById("saveProfileBtn") || document.getElementById("drawerNewProfileBtn");
      if (saveProfileBtn) {
        saveProfileBtn.click();
      } else {
        showToast("Profile snapshot saved", "success");
      }
    });
  }

  // Topbar 3-Dots Collapsible More Menu
  setupTopbarMoreMenu();

  // Floating Quick Jump Rail (Right Edge Slide-Out)
  setupQuickJumpRail();
}

// Topbar 3-Dots Collapsible More Menu (Undo, Redo, Sync, Save Profile, Restore)
function setupTopbarMoreMenu() {
  const topbarMoreBtn = document.getElementById("topbarMoreBtn");
  const topbarMoreMenu = document.getElementById("topbarMoreMenu");
  if (!topbarMoreBtn || !topbarMoreMenu) return;

  topbarMoreBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const isClosed = topbarMoreMenu.classList.contains("hidden");
    topbarMoreMenu.classList.toggle("hidden", !isClosed);
    topbarMoreBtn.setAttribute("aria-expanded", isClosed ? "true" : "false");
  });

  document.addEventListener("click", (e) => {
    if (!topbarMoreMenu.classList.contains("hidden") && !topbarMoreMenu.contains(e.target)) {
      topbarMoreMenu.classList.add("hidden");
      topbarMoreBtn.setAttribute("aria-expanded", "false");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !topbarMoreMenu.classList.contains("hidden")) {
      topbarMoreMenu.classList.add("hidden");
      topbarMoreBtn.setAttribute("aria-expanded", "false");
    }
  });

  topbarMoreMenu.querySelectorAll(".menu-item-btn").forEach((item) => {
    item.addEventListener("click", () => {
      topbarMoreMenu.classList.add("hidden");
      topbarMoreBtn.setAttribute("aria-expanded", "false");
    });
  });
}

// Floating Quick Jump Rail Controller (Zero-Modal Instant Dock Nav)
function setupQuickJumpRail() {
  const rail = document.getElementById("floatingQuickJumpRail");
  const handle = document.getElementById("quickJumpHandle");
  const dock = document.getElementById("studioInspectorDock");
  const splitterRight = document.getElementById("splitterRight");

  if (handle && rail) {
    handle.addEventListener("click", (e) => {
      e.stopPropagation();
      rail.classList.toggle("is-open");
    });

    // Close floating rail if clicking outside
    document.addEventListener("click", (e) => {
      if (rail.classList.contains("is-open") && !rail.contains(e.target)) {
        rail.classList.remove("is-open");
      }
    });
  }

  const jumpButtons = document.querySelectorAll(".quick-jump-btn");
  jumpButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      if (!target) return;

      // Expand dock if collapsed
      if (dock && dock.classList.contains("collapsed")) {
        dock.classList.remove("collapsed");
        if (splitterRight) splitterRight.classList.remove("hidden-dock");
        window.dispatchEvent(new Event("resize"));
        resize3DViewport();
      }

      // Activate corresponding dock tab
      const dockTab = document.querySelector(`.dock-tab[data-tab="${target}"]`) ||
                      document.getElementById(`dockTab${target.charAt(0).toUpperCase() + target.slice(1)}`);
      if (dockTab) {
        dockTab.click();
      }

      // Update active state on jump rail
      jumpButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Scroll dock body to top
      const dockBody = document.querySelector(".studio-dock-body");
      if (dockBody) {
        dockBody.scrollTo({ top: 0, behavior: "smooth" });
      }

      // Auto-collapse rail on compact screens
      if (rail && window.innerWidth < 1280) {
        rail.classList.remove("is-open");
      }
    });
  });
}

// Navigation Handling across dock tab panes
function setupNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  const panes = document.querySelectorAll(".tab-pane");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      panes.forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");
      const tabName = tab.dataset.tab;
      const targetId = `tab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`;
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      // Synchronize Quick Jump Rail active state
      document.querySelectorAll(".quick-jump-btn").forEach((qBtn) => {
        qBtn.classList.toggle("active", qBtn.dataset.target === tabName);
      });

      // Synchronize Inspector Active Tab Title Badge
      const titleMap = {
        slots: "SLOTS & ASSETS",
        bake: "BAKE CANVAS",
        color: "COLOR LAB",
        finishes: "FINISHES & FX",
        gloves: "GLOVE SUITE"
      };
      const titleEl = document.getElementById("inspectorActiveTabTitle");
      if (titleEl && titleMap[tabName]) {
        titleEl.textContent = titleMap[tabName];
      }

      // Tab specific activation hooks
      if (tabName === "color") {
        setupColorStudioTab();
      } else if (tabName === "viewport3d") {
        initOrUpdate3DViewer();
      } else if (tabName === "bake") {
        setupBakeTab();
      } else if (tabName === "gloves") {
        openProToolsModal();
      } else if (tabName === "finishes" || tabName === "pro") {
        openProToolsModal();
        eventBus.emit("chrome:tabActivated");
      }
    });
  });
}

function setupTeamToggle() {
  if (!elements.teamToggle) return;
  elements.teamToggle.querySelectorAll(".team-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.currentTeam = btn.dataset.team;
      updateTeamButtonsUI();
      populateWeaponSelect();
    });
  });
}

function updateTeamButtonsUI() {
  if (!elements.teamToggle) return;
  elements.teamToggle.querySelectorAll(".team-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.team === state.currentTeam);
  });
  const teamSubtitle = document.getElementById("drawerTeamSubtitle");
  if (teamSubtitle) {
    teamSubtitle.textContent = state.currentTeam === "ct" ? "CT Arsenal" : "T Arsenal";
  }
  updateInGameEquipButton();
}

function setupWeaponDropdown() {
  if (elements.weaponSelect) {
    elements.weaponSelect.addEventListener("change", (e) => {
      state.currentWeapon = e.target.value;
      loadActiveModel();
      updateActiveDrawerWeaponCard();
    });
  }

  if (elements.restoreBtn) {
    elements.restoreBtn.addEventListener("click", () => {
      openRestoreScopeModal();
    });
  }

  // Restore Scope Modal Event Listeners
  const closeRestoreBtn = document.getElementById("closeRestoreModalBtn");
  const cancelRestoreBtn = document.getElementById("cancelRestoreBtn");
  const confirmRestoreBtn = document.getElementById("confirmRestoreBtn");
  const restoreModal = document.getElementById("restoreScopeModal");

  if (closeRestoreBtn) closeRestoreBtn.addEventListener("click", closeRestoreScopeModal);
  if (cancelRestoreBtn) cancelRestoreBtn.addEventListener("click", closeRestoreScopeModal);
  if (confirmRestoreBtn) confirmRestoreBtn.addEventListener("click", executeRestoreScope);
  if (restoreModal) {
    restoreModal.addEventListener("click", (e) => {
      if (e.target === restoreModal) closeRestoreScopeModal();
    });
  }
}

// Checks if a weapon is equipped in the active CS:GO AMXX loadout
export function isWeaponEquippedInGame(team, weapon) {
  if (!state.activeLoadout || !state.activeLoadout[team] || !weapon) return false;
  const loadout = state.activeLoadout[team];
  const wClean = weapon.toLowerCase().replace(/^v_/, "").replace(/\.mdl$/, "");

  const slotMap = {
    knife: "KNIFE", knife_m9: "KNIFE", knife_karambit: "KNIFE", knife_butterfly: "KNIFE", knife_huntsman: "KNIFE", knife_bayonet: "KNIFE",
    m4a1: "M4A1", m4a4: "M4A1", ak47: "AK47", awp: "AWP", scout: "SCOUT", galil: "GALIL", famas: "FAMAS", sg552: "SG552", aug: "AUG", g3sg1: "G3SG1", sg550: "SG550",
    mp5: "MP5NAVY", mp7: "MP5NAVY", p90: "P90", bizon: "P90", ump45: "UMP45", mac10: "MAC10", cz75_mac10: "MAC10", tmp: "TMP", cz75_tmp: "TMP", cz75: (team === "t" ? "MAC10" : "TMP"),
    xm1014: "XM1014", mag7: "XM1014", m3: "M3", sawedoff: "M3", m249: "M249", negev: "M249",
    usp: "USP", glock18: "GLOCK18", deagle: "DEAGLE", p228: "P228", tec9: "P228", elite: "ELITE", elites: "ELITE", fiveseven: "FIVESEVEN",
  };

  const slot = slotMap[wClean] || wClean.toUpperCase();
  const activeVal = (loadout[slot] || "").toLowerCase();
  if (!activeVal) return false;

  return (
    activeVal === wClean ||
    activeVal.endsWith(`v_${wClean}.mdl`) ||
    activeVal.includes(`/${wClean}.`) ||
    activeVal.includes(`v_${wClean}`)
  );
}

// Synchronizes the real-time engine telemetry status pill (Screen 1 Master Workstation)
export async function updateEngineTelemetry() {
  const pill = document.getElementById("engineTelemetryPill");
  const dot = document.getElementById("engineTelemetryDot");
  const label = document.getElementById("engineTelemetryLabel");
  if (!pill || !dot || !label) return;

  try {
    const data = await apiGet("/api/engine/status");
    if (data && data.is_game_running) {
      pill.classList.remove("standalone-dcc");
      pill.classList.add("game-running");
      dot.className = "telemetry-pip pulse-dot-green";
      label.textContent = "ACTIVE IN-GAME (hl.exe)";
      pill.title = "Counter-Strike 1.6 engine (hl.exe) is currently running and synchronized";
    } else {
      pill.classList.remove("game-running");
      pill.classList.add("standalone-dcc");
      dot.className = "telemetry-pip pulse-dot-cyan";
      label.textContent = "STANDALONE DCC";
      pill.title = "GoldSrc IDST v10 DCC Workstation (hl.exe idle)";
    }
  } catch (err) {
    // Graceful fallback
  }
}

// Synchronizes the topbar Equip In-Game button state
export function updateInGameEquipButton() {
  const equipBtn = document.getElementById("equipInGameBtn");
  const equipLabel = document.getElementById("equipInGameLabel");
  if (!equipBtn || !equipLabel) return;

  const isEquipped = isWeaponEquippedInGame(state.currentTeam, state.currentWeapon);
  equipBtn.classList.toggle("active-equipped", isEquipped);
  if (isEquipped) {
    equipLabel.textContent = "ACTIVE IN-GAME";
    equipBtn.title = "This weapon variant is currently active in your CS:GO AMXX loadout";
  } else {
    equipLabel.textContent = "Equip In-Game";
    equipBtn.title = "Equip this weapon variant in active in-game CS:GO AMXX loadout";
  }
}

async function fetchAvailableModels() {
  showLoader("Discovering weapon models & AMXX inventory...");
  try {
    let modelData = null;
    try {
      modelData = await apiGet("/api/models");
    } catch {
      modelData = await apiGet("/api/weapons");
    }
    const [catalogData, loadoutData] = await Promise.all([
      apiGet("/api/amxx/catalog").catch(() => null),
      apiGet("/api/amxx/loadout").catch(() => null),
    ]);
    state.availableModels = (modelData && modelData.models) || {};
    if (catalogData && (catalogData.catalog || catalogData.inventory)) {
      state.amxxCatalog = catalogData.catalog || catalogData.inventory || catalogData;
    }
    if (loadoutData && loadoutData.loadout) {
      state.activeLoadout = loadoutData.loadout;
    } else if (catalogData && catalogData.active_loadout) {
      state.activeLoadout = catalogData.active_loadout;
    }
    populateWeaponSelect();
  } catch (err) {
    showToast(`Failed to discover models: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

function populateWeaponSelect() {
  const models = state.availableModels[state.currentTeam] || [];
  if (!elements.weaponSelect) return;
  elements.weaponSelect.innerHTML = "";

  if (models.length === 0) {
    elements.weaponSelect.innerHTML = '<option value="">No models found</option>';
    populateVisualLoadoutDrawer([]);
    return;
  }

  const seenWeapons = new Set();
  models.forEach((m) => {
    if (!seenWeapons.has(m.weapon)) {
      seenWeapons.add(m.weapon);
      const opt = document.createElement("option");
      opt.value = m.weapon;
      opt.textContent = m.weapon.toUpperCase();
      if (m.weapon.toLowerCase() === state.currentWeapon.toLowerCase()) {
        opt.selected = true;
      }
      elements.weaponSelect.appendChild(opt);
    }
  });

  if (!seenWeapons.has(state.currentWeapon.toLowerCase()) && models.length > 0) {
    state.currentWeapon = models[0].weapon;
    elements.weaponSelect.value = state.currentWeapon;
  }

  try {
    populateVisualLoadoutDrawer(models);
  } catch (err) {
    console.error("Error in populateVisualLoadoutDrawer:", err);
  }
  loadActiveModel();
}

// Populates categorized weapons into the Visual Loadout Drawer with sub-pills for variants
function populateVisualLoadoutDrawer(models) {
  const grids = {
    pistols: document.getElementById("catGridPistols"),
    rifles: document.getElementById("catGridRifles"),
    smgs: document.getElementById("catGridSmgs"),
    heavy: document.getElementById("catGridHeavy"),
    gear: document.getElementById("catGridGear"),
  };

  const counts = { pistols: 0, rifles: 0, smgs: 0, heavy: 0, gear: 0 };

  Object.values(grids).forEach((g) => {
    if (g) g.innerHTML = "";
  });

  const availableByWeapon = new Map();
  models.forEach((m) => {
    const w = (m.weapon || "").toLowerCase();
    if (w) availableByWeapon.set(w, m);
  });

  const allModelsMap = new Map();
  (state.availableModels?.all || []).forEach((m) => {
    const w = (m.weapon || "").toLowerCase();
    if (w) allModelsMap.set(w, m);
  });

  const handledWeapons = new Set();
  const currentWeaponLower = (state.currentWeapon || "").toLowerCase();

  // 1. Render predefined groups (with sub-pills when multiple variants exist)
  WEAPON_GROUPS_DEF.forEach((def) => {
    const matchingVariants = def.variants.filter((v) => {
      const vid = v.id.toLowerCase();
      if (availableByWeapon.has(vid)) return true;
      if (allModelsMap.has(vid)) {
        availableByWeapon.set(vid, allModelsMap.get(vid));
        return true;
      }
      return false;
    });
    if (matchingVariants.length === 0 && !availableByWeapon.has(def.groupKey.toLowerCase()) && !allModelsMap.has(def.groupKey.toLowerCase())) {
      return;
    }

    matchingVariants.forEach((v) => handledWeapons.add(v.id.toLowerCase()));
    handledWeapons.add(def.groupKey.toLowerCase());

    const targetCat = def.category;
    counts[targetCat]++;
    const targetGrid = grids[targetCat];
    if (!targetGrid) return;

    // Determine if any variant is currently active in state.currentWeapon
    const isCurrentGroup = matchingVariants.some((v) => v.id.toLowerCase() === currentWeaponLower) ||
                           def.groupKey.toLowerCase() === currentWeaponLower;

    // Check in-game equipped status
    const isEquippedInGame = matchingVariants.some((v) => isWeaponEquippedInGame(state.currentTeam, v.id));

    // Check backup status
    const hasBackup = matchingVariants.some((v) => {
      const m = availableByWeapon.get(v.id.toLowerCase());
      return m && m.has_orig_backup;
    });

    const card = document.createElement("div");
    card.className = "drawer-weapon-card";
    card.dataset.weapon = def.groupKey;
    if (isCurrentGroup) {
      card.classList.add("active");
    }

    const iconType = getTacticalWeaponGlyph(def.groupKey, targetCat);

    let statusClass = "clean";
    let statusText = "CLEAN";
    if (isEquippedInGame) {
      statusClass = "active-ingame";
      statusText = "ACTIVE";
    } else if (hasBackup) {
      statusClass = "modified";
      statusText = "MOD";
    }

    // Main row of card
    const mainRow = document.createElement("div");
    mainRow.className = "card-main-row";
    mainRow.innerHTML = `
      <div class="card-left">
        <svg class="glyph glyph-xs"><use href="#glyph-${iconType}"></use></svg>
        <span class="weapon-title">${def.title}</span>
      </div>
      <div class="card-right">
        <span class="weapon-status-pill ${statusClass}">${statusText}</span>
      </div>
    `;
    card.appendChild(mainRow);

    // Sub-pills for variants (if 2 or more variants exist)
    if (matchingVariants.length > 1) {
      const subpillsWrap = document.createElement("div");
      subpillsWrap.className = "weapon-subpills";

      matchingVariants.forEach((v) => {
        const isSubActive = v.id.toLowerCase() === currentWeaponLower;
        const subBtn = document.createElement("button");
        subBtn.type = "button";
        subBtn.className = `subpill-btn ${isSubActive ? "active" : ""}`;
        subBtn.dataset.variant = v.id;
        subBtn.textContent = v.label;

        subBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          state.currentWeapon = v.id;
          if (elements.weaponSelect) {
            let opt = Array.from(elements.weaponSelect.options).find(
              (o) => o.value.toLowerCase() === v.id.toLowerCase()
            );
            if (!opt) {
              opt = document.createElement("option");
              opt.value = v.id;
              opt.textContent = v.label.toUpperCase();
              elements.weaponSelect.appendChild(opt);
            }
            elements.weaponSelect.value = v.id;
          }
          loadActiveModel();
          updateActiveDrawerWeaponCard();
          updateInGameEquipButton();
        });

        subpillsWrap.appendChild(subBtn);
      });

      card.appendChild(subpillsWrap);
    }

    // Clicking anywhere on card
    card.addEventListener("click", () => {
      const currentWepLower = (state.currentWeapon || "").toLowerCase();
      const alreadyInGroup = matchingVariants.some((v) => v.id.toLowerCase() === currentWepLower) ||
                             def.groupKey.toLowerCase() === currentWepLower;
      if (alreadyInGroup) return;

      // Prefer equipped variant if available, otherwise first variant or group key
      const equippedVar = matchingVariants.find((v) => isWeaponEquippedInGame(state.currentTeam, v.id));
      const targetWep = equippedVar ? equippedVar.id : (matchingVariants[0]?.id || def.groupKey);

      state.currentWeapon = targetWep;
      if (elements.weaponSelect) elements.weaponSelect.value = targetWep;
      loadActiveModel();
      updateActiveDrawerWeaponCard();
      updateInGameEquipButton();
    });

    targetGrid.appendChild(card);
  });

  // 2. Render any remaining individual models not covered by predefined groups
  models.forEach((m) => {
    const w = (m.weapon || "").toLowerCase();
    if (!w || handledWeapons.has(w)) return;
    handledWeapons.add(w);

    const targetCat = getWeaponCategory(w);
    counts[targetCat]++;
    const targetGrid = grids[targetCat];
    if (!targetGrid) return;

    const card = document.createElement("div");
    card.className = "drawer-weapon-card";
    card.dataset.weapon = w;
    const isCurrent = w === currentWeaponLower;
    if (isCurrent) card.classList.add("active");

    const isEquipped = isWeaponEquippedInGame(state.currentTeam, w);
    let statusClass = m.has_orig_backup ? "modified" : "clean";
    let statusText = m.has_orig_backup ? "MOD" : "CLEAN";
    if (isEquipped) {
      statusClass = "active-ingame";
      statusText = "ACTIVE";
    }

    const iconType = getTacticalWeaponGlyph(w, targetCat);
    card.innerHTML = `
      <div class="card-main-row">
        <div class="card-left">
          <svg class="glyph glyph-xs"><use href="#glyph-${iconType}"></use></svg>
          <span class="weapon-title">${w.toUpperCase()}</span>
        </div>
        <div class="card-right">
          <span class="weapon-status-pill ${statusClass}">${statusText}</span>
        </div>
      </div>
    `;

    card.addEventListener("click", () => {
      state.currentWeapon = w;
      if (elements.weaponSelect) elements.weaponSelect.value = w;
      loadActiveModel();
      updateActiveDrawerWeaponCard();
      updateInGameEquipButton();
    });

    targetGrid.appendChild(card);
  });

  // Update category count badges
  const bPistols = document.getElementById("catBadgePistols");
  if (bPistols) bPistols.textContent = counts.pistols;
  const bRifles = document.getElementById("catBadgeRifles");
  if (bRifles) bRifles.textContent = counts.rifles;
  const bSmgs = document.getElementById("catBadgeSmgs");
  if (bSmgs) bSmgs.textContent = counts.smgs;
  const bHeavy = document.getElementById("catBadgeHeavy");
  if (bHeavy) bHeavy.textContent = counts.heavy;
  const bGear = document.getElementById("catBadgeGear");
  if (bGear) bGear.textContent = counts.gear;
}

// Setup Draggable Splitters (Bottom Shelf vertical resizer + Inspector Dock horizontal resizer)
function setupSplitters() {
  const splitterBottom = document.getElementById("splitterBottom");
  const splitterLeft = document.getElementById("splitterLeft");
  const splitterRight = document.getElementById("splitterRight");
  const root = document.documentElement;

  // Restore saved dimensions
  const savedShelfHeight = safeStorageGet("cs16_shelf_height", "260");
  if (savedShelfHeight) {
    root.style.setProperty("--bottom-shelf-height", `${savedShelfHeight}px`);
  }
  const savedDrawerWidth = safeStorageGet("cs16_drawer_width");
  if (savedDrawerWidth) {
    root.style.setProperty("--drawer-width", `${savedDrawerWidth}px`);
  }
  const savedDockWidth = safeStorageGet("cs16_dock_width");
  if (savedDockWidth) {
    root.style.setProperty("--dock-width", `${savedDockWidth}px`);
  }

  // Bottom Shelf horizontal splitter (vertical drag resizing)
  if (splitterBottom) {
    splitterBottom.addEventListener("mousedown", (e) => {
      e.preventDefault();
      document.body.classList.add("is-resizing");
      splitterBottom.classList.add("is-dragging");

      function onMouseMove(ev) {
        const stageArea = document.querySelector(".studio-hero-stage");
        const stageRect = stageArea ? stageArea.getBoundingClientRect() : { bottom: window.innerHeight };
        const footerEl = document.getElementById("stageFooter");
        const footerHeight = footerEl ? footerEl.offsetHeight : 28;
        const newHeight = Math.max(140, Math.min(520, stageRect.bottom - ev.clientY - footerHeight));
        root.style.setProperty("--bottom-shelf-height", `${newHeight}px`);
        resize3DViewport();
      }

      function onMouseUp(ev) {
        document.body.classList.remove("is-resizing");
        splitterBottom.classList.remove("is-dragging");
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        const stageArea = document.querySelector(".studio-hero-stage");
        const stageRect = stageArea ? stageArea.getBoundingClientRect() : { bottom: window.innerHeight };
        const footerEl = document.getElementById("stageFooter");
        const footerHeight = footerEl ? footerEl.offsetHeight : 28;
        const finalHeight = Math.max(140, Math.min(520, stageRect.bottom - ev.clientY - footerHeight));
        safeStorageSet("cs16_shelf_height", finalHeight);
        window.dispatchEvent(new Event("resize"));
        resize3DViewport();
      }

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    });

    splitterBottom.addEventListener("dblclick", () => {
      root.style.setProperty("--bottom-shelf-height", "260px");
      safeStorageSet("cs16_shelf_height", 260);
      window.dispatchEvent(new Event("resize"));
      resize3DViewport();
    });
  }

  // Left splitter drag (fallback compatibility)
  if (splitterLeft) {
    splitterLeft.addEventListener("mousedown", (e) => {
      e.preventDefault();
      document.body.classList.add("is-resizing");
      splitterLeft.classList.add("is-dragging");

      function onMouseMove(ev) {
        // 52px is activity rail width
        const newWidth = Math.max(200, Math.min(460, ev.clientX - 52));
        root.style.setProperty("--drawer-width", `${newWidth}px`);
      }

      function onMouseUp(ev) {
        document.body.classList.remove("is-resizing");
        splitterLeft.classList.remove("is-dragging");
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        const finalWidth = Math.max(200, Math.min(460, ev.clientX - 52));
        safeStorageSet("cs16_drawer_width", finalWidth);
        window.dispatchEvent(new Event("resize"));
        resize3DViewport();
      }

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    });

    splitterLeft.addEventListener("dblclick", () => {
      root.style.setProperty("--drawer-width", "290px");
      safeStorageSet("cs16_drawer_width", 290);
      window.dispatchEvent(new Event("resize"));
      resize3DViewport();
    });
  }

  // Right vertical inspector dock splitter drag
  if (splitterRight) {
    splitterRight.addEventListener("mousedown", (e) => {
      e.preventDefault();
      document.body.classList.add("is-resizing");
      splitterRight.classList.add("is-dragging");

      function onMouseMove(ev) {
        const newWidth = Math.max(300, Math.min(520, window.innerWidth - ev.clientX));
        root.style.setProperty("--dock-width", `${newWidth}px`);
      }

      function onMouseUp(ev) {
        document.body.classList.remove("is-resizing");
        splitterRight.classList.remove("is-dragging");
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        const finalWidth = Math.max(300, Math.min(520, window.innerWidth - ev.clientX));
        safeStorageSet("cs16_dock_width", finalWidth);
        window.dispatchEvent(new Event("resize"));
        resize3DViewport();
      }

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    });

    splitterRight.addEventListener("dblclick", () => {
      root.style.setProperty("--dock-width", "360px");
      safeStorageSet("cs16_dock_width", 360);
      window.dispatchEvent(new Event("resize"));
      resize3DViewport();
    });
  }
}

// Setup Collapsible Weapon Categories with Memory
function setupCategoryCollapsing() {
  const sections = document.querySelectorAll(".weapon-category-section");
  let savedCollapsed = [];
  try {
    savedCollapsed = JSON.parse(safeStorageGet("cs16_collapsed_categories", "[]"));
  } catch {
    savedCollapsed = [];
  }

  sections.forEach((sec) => {
    const cat = sec.dataset.category;
    if (savedCollapsed.includes(cat)) {
      sec.classList.add("collapsed");
    }

    const header = sec.querySelector(".category-header");
    if (header) {
      header.addEventListener("click", () => {
        sec.classList.toggle("collapsed");
        const currentCollapsed = Array.from(document.querySelectorAll(".weapon-category-section.collapsed")).map(
          (s) => s.dataset.category
        );
        safeStorageSet("cs16_collapsed_categories", JSON.stringify(currentCollapsed));
      });
      header.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          header.click();
        }
      });
    }
  });
}

// Setup 3D Viewport HUD Capsule Minimize / Dimming
// Setup 3D Viewport HUD Capsule Minimize / Dimming
function setupHudCapsule() {
  const hud = document.getElementById("floatingHudCapsule");
  const hudExpanded = document.getElementById("hud-expanded");
  const hudMinimized = document.getElementById("hud-minimized");
  const toggleBtn = document.getElementById("hudCollapseToggleBtn");
  const viewport3d = document.getElementById("viewport3dCanvasContainer");

  function toggleHud() {
    if (hudExpanded && hudMinimized) {
      const isExpandedHidden = hudExpanded.classList.contains("hidden");
      if (isExpandedHidden) {
        hudExpanded.classList.remove("hidden");
        hudMinimized.classList.add("hidden");
      } else {
        hudExpanded.classList.add("hidden");
        hudMinimized.classList.remove("hidden");
      }
    } else if (hud) {
      hud.classList.toggle("collapsed");
    }
    const label = toggleBtn ? toggleBtn.querySelector(".hud-toggle-label") : null;
    if (label) {
      label.textContent = (hudExpanded && hudExpanded.classList.contains("hidden")) ? "Expand HUD" : "Minimize HUD";
    }
  }

  window.toggleHudCollapse = toggleHud;

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => toggleHud());
  }

  if (hudMinimized) {
    hudMinimized.addEventListener("click", () => toggleHud());
  }

  // Global drawer helper
  window.toggleLeftDrawer = function() {
    const drawer = document.getElementById("left-drawer") || document.getElementById("studioDrawer");
    if (!drawer) return;
    drawer.classList.toggle("collapsed");
    window.dispatchEvent(new Event("resize"));
    resize3DViewport();
    setTimeout(() => resize3DViewport(), 260);
  };

  window.switchInspectorTab = function(tabName) {
    if (tabName === "fx") tabName = "finishes";
    const tabBtn = document.getElementById(`dockTab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`) ||
                   document.querySelector(`.dock-tab[data-tab="${tabName}"]`);
    if (tabBtn) tabBtn.click();
  };

  // Keyboard shortcut 'H'
  window.addEventListener("keydown", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;
    if (e.key === "h" || e.key === "H") {
      toggleHud();
    }
  });

  // Auto-dim HUD on 3D canvas interaction
  if (viewport3d && hud) {
    viewport3d.addEventListener("pointerdown", (e) => {
      if (e.target.closest("#floatingHudCapsule")) return;
      hud.classList.add("is-dimmed");
    });
    window.addEventListener("pointerup", () => {
      hud.classList.remove("is-dimmed");
    });
  }
}

function updateActiveDrawerWeaponCard() {
  const currentWep = (state.currentWeapon || "").toLowerCase();

  document.querySelectorAll(".drawer-weapon-card").forEach((card) => {
    const cardWep = (card.dataset.weapon || "").toLowerCase();
    const subpills = Array.from(card.querySelectorAll(".subpill-btn"));

    let isCardActive = false;
    if (subpills.length > 0) {
      subpills.forEach((sp) => {
        const isMatch = (sp.dataset.variant || "").toLowerCase() === currentWep;
        sp.classList.toggle("active", isMatch);
        if (isMatch) isCardActive = true;
      });
    } else {
      isCardActive = cardWep === currentWep;
    }

    card.classList.toggle("active", isCardActive);

    // Update status pill
    const pill = card.querySelector(".weapon-status-pill");
    if (pill) {
      let isEquipped = false;
      if (subpills.length > 0) {
        isEquipped = subpills.some((sp) => isWeaponEquippedInGame(state.currentTeam, sp.dataset.variant));
      } else {
        isEquipped = isWeaponEquippedInGame(state.currentTeam, cardWep);
      }

      if (isEquipped) {
        pill.className = "weapon-status-pill active-ingame";
        pill.textContent = "ACTIVE";
      } else if (isCardActive && state.modelData?.has_orig_backup) {
        pill.className = "weapon-status-pill modified";
        pill.textContent = "MOD";
      } else {
        pill.className = "weapon-status-pill clean";
        pill.textContent = "CLEAN";
      }
    }
  });

  updateInGameEquipButton();
}

export async function loadActiveModel(typeOverride = null) {
  showLoader(`Loading ${state.currentWeapon.toUpperCase()} (${state.currentTeam.toUpperCase()})...`);
  try {
    if (typeOverride && state.viewport3d) {
      state.viewport3d.tripletType = typeOverride;
    }
    const tripletType = typeOverride || state.viewport3d?.tripletType || "v";
    const data = await apiGet(`/api/model?team=${state.currentTeam}&weapon=${state.currentWeapon}&type=${tripletType}`);
    state.modelData = data;
    state.pendingSlotUpdates = {};

    renderModelDetails();
    checkModelHealth();
    updateActiveDrawerWeaponCard();
    updateInGameEquipButton();
    eventBus.emit("model:loaded", data);
  } catch (err) {
    showToast(`Error loading model: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

async function checkModelHealth() {
  const badge = document.getElementById("modelHealthBadge");
  if (!badge) return;
  try {
    const health = await apiGet(`/api/model/health?team=${state.currentTeam}&weapon=${state.currentWeapon}`);
    if (health.healthy) {
      badge.className = "health-badge healthy";
      badge.innerHTML = `<svg class="glyph glyph-xs"><use href="#glyph-shield"></use></svg> <span class="badge-text">Model: 100% Clean</span>`;
      badge.title = `0 byte drift (${health.file_size} bytes) • Max submodel verts: ${health.max_verts_submodel}/2048 • GoldSrc IDST v10 intact`;
    } else {
      badge.className = "health-badge warning";
      badge.innerHTML = `<svg class="glyph glyph-xs"><use href="#glyph-alert"></use></svg> <span class="badge-text">Model: ${health.issues?.length || 1} Glitches</span>`;
      badge.title = (health.issues || []).join("\n");
    }
  } catch (err) {
    badge.className = "health-badge warning";
    badge.innerHTML = `<svg class="glyph glyph-xs"><use href="#glyph-alert"></use></svg> <span class="badge-text">Health Check Failed</span>`;
  }
}

function renderModelDetails() {
  const m = state.modelData;
  if (!m) return;

  if (elements.modelName) elements.modelName.textContent = m.model_name;
  if (elements.modelPath) elements.modelPath.textContent = m.model_path;

  const tb = document.getElementById("telemetryBreadcrumb");
  if (tb && m.weapon_key) {
    const teamStr = (state.currentTeam || "ct").toUpperCase();
    tb.textContent = `CS 1.6 / ${teamStr} / ${m.weapon_key.toUpperCase()}`;
  }

  const total = m.textures.length;
  const stickers = m.textures.filter((t) => t.role === "sticker").length;

  if (elements.textureCount) elements.textureCount.textContent = `${total} Textures`;
  if (elements.stickerCount) elements.stickerCount.textContent = `${stickers} Sticker Slot${stickers === 1 ? "" : "s"}`;

  if (elements.backupStatus) {
    if (m.has_orig_backup) {
      elements.backupStatus.textContent = "Original Backup (.orig)";
      elements.backupStatus.style.borderColor = "var(--accent-green)";
      elements.backupStatus.style.color = "var(--accent-green)";
    } else {
      elements.backupStatus.textContent = "Ready for First Edit";
      elements.backupStatus.style.borderColor = "var(--border)";
      elements.backupStatus.style.color = "var(--text-muted)";
    }
  }
}

export function openRestoreScopeModal() {
  const m = state.modelData;
  if (!m) return;

  const modal = document.getElementById("restoreScopeModal");
  if (!modal) return;

  const nameEl = document.getElementById("restoreModalWeaponName");
  if (nameEl) {
    nameEl.textContent = `${state.currentWeapon.toUpperCase()} (${state.currentTeam.toUpperCase()})`;
  }

  // Populate dynamic status for scopes based on m.triplet
  const triplet = m.triplet || {};
  const vInfo = triplet.v || {};
  const pInfo = triplet.p || {};
  const wInfo = triplet.w || {};

  const statusAll = document.getElementById("restoreStatusAll");
  const statusV = document.getElementById("restoreStatusV");
  const statusPW = document.getElementById("restoreStatusPW");

  if (statusAll) {
    const avail = [];
    if (vInfo.has_backup) avail.push(`V (${vInfo.backup_type})`);
    if (pInfo.has_backup) avail.push(`P (${pInfo.backup_type})`);
    if (wInfo.has_backup) avail.push(`W (${wInfo.backup_type})`);
    statusAll.innerHTML = avail.length > 0
      ? `<span style="color: var(--accent-green); font-weight: 500;">● Backups ready: ${avail.join(", ")}</span>`
      : `<span style="color: var(--text-dim);">No backups detected yet for this weapon</span>`;
  }

  if (statusV) {
    statusV.innerHTML = vInfo.has_backup
      ? `<span style="color: var(--accent-green); font-weight: 500;">● Viewmodel backup ready (${vInfo.backup_type})</span>`
      : `<span style="color: var(--text-dim);">No viewmodel backup detected</span>`;
  }

  if (statusPW) {
    const pwAvail = [];
    if (pInfo.has_backup) pwAvail.push(`Player (${pInfo.backup_type})`);
    if (wInfo.has_backup) pwAvail.push(`World (${wInfo.backup_type})`);
    statusPW.innerHTML = pwAvail.length > 0
      ? `<span style="color: var(--accent-green); font-weight: 500;">● ${pwAvail.join(" & ")} backup ready</span>`
      : `<span style="color: var(--text-dim);">No P or W backups detected</span>`;
  }

  modal.classList.remove("hidden");
}

export function closeRestoreScopeModal() {
  const modal = document.getElementById("restoreScopeModal");
  if (modal) modal.classList.add("hidden");
}

async function executeRestoreScope() {
  const modal = document.getElementById("restoreScopeModal");
  const selectedScopeInput = modal ? modal.querySelector('input[name="restoreScope"]:checked') : null;
  const scope = selectedScopeInput ? selectedScopeInput.value : "all";

  closeRestoreScopeModal();
  showLoader(`Restoring weapon models (${scope.toUpperCase()})...`);
  try {
    const res = await apiPost("/api/restore", {
      team: state.currentTeam,
      weapon: state.currentWeapon,
      path: state.modelData ? state.modelData.model_path : undefined,
      scope: scope,
    });

    showToast(res.message, "success");
    eventBus.emit("model:restored", { team: state.currentTeam, weapon: state.currentWeapon, scope });
    await loadActiveModel();
  } catch (err) {
    showToast(`Restore failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}

export function setStageMode(mode) {
  if (typeof window.setStageMode === "function") {
    window.setStageMode(mode);
  }
}


// =========================================================================

// =========================================================================
// TRIPLET SYNC TELEMETRY CONTROLLER (FASE 3)
// =========================================================================
export async function updateTripletTelemetry(weapon = state.currentWeapon, team = state.currentTeam) {
  if (!weapon) return;
  try {
    const res = await apiGet(`/api/triplets/status?weapon=${weapon}&team=${team}`);
    if (!res.success) return;

    // Viewmodel
    const vName = document.getElementById("tripletNameV");
    const vStatus = document.getElementById("tripletStatusV");
    if (vName) vName.textContent = res.v_model.name || `v_${weapon}.mdl`;
    if (vStatus) {
      vStatus.textContent = res.v_model.status;
      vStatus.className = `chip-status status-${res.v_model.status.toLowerCase()}`;
    }

    // Player Model
    const pName = document.getElementById("tripletNameP");
    const pStatus = document.getElementById("tripletStatusP");
    const pBtn = document.getElementById("tripletBtnP");
    if (pName) pName.textContent = res.p_model.name || `p_${weapon}.mdl`;
    if (pStatus) {
      pStatus.textContent = res.p_model.status;
      pStatus.className = `chip-status status-${res.p_model.status.toLowerCase()}`;
    }
    if (pBtn) {
      pBtn.style.opacity = res.p_model.exists ? "1" : "0.5";
      pBtn.title = res.p_model.exists
        ? `View Third-Person Player Model (${res.p_model.name})`
        : `Player model (${res.p_model.name}) not found. Click Sync P/W to generate.`;
    }

    // World Model
    const wName = document.getElementById("tripletNameW");
    const wStatus = document.getElementById("tripletStatusW");
    const wBtn = document.getElementById("tripletBtnW");
    if (wName) wName.textContent = res.w_model.name || `w_${weapon}.mdl`;
    if (wStatus) {
      wStatus.textContent = res.w_model.status;
      wStatus.className = `chip-status status-${res.w_model.status.toLowerCase()}`;
    }
    if (wBtn) {
      wBtn.style.opacity = res.w_model.exists ? "1" : "0.5";
      wBtn.title = res.w_model.exists
        ? `View Ground Dropped World Model (${res.w_model.name})`
        : `World model (${res.w_model.name}) not found. Click Sync P/W to generate.`;
    }

    // Update backup status badge
    const backupBadge = document.getElementById("backupStatus");
    if (backupBadge) {
      const anyBak = res.v_model.has_backup || res.p_model.has_backup || res.w_model.has_backup;
      backupBadge.textContent = anyBak ? "Backup Active (.orig)" : "No Backup";
      backupBadge.classList.toggle("stat-warn", !anyBak);
    }
  } catch (err) {
    console.debug("updateTripletTelemetry error:", err);
  }
}

// =========================================================================
// INTERACTIVE P/W MODEL SYNC PROMPT MODAL CONTROLLER (SCREEN 2 MOCKUP FIDELITY)
// =========================================================================
function initPwSyncPromptModal() {
  const modal = document.getElementById("pwSyncPromptModal");
  if (!modal) return;

  const closeBtn = document.getElementById("pwPromptCloseBtn");
  const vOnlyBtn = document.getElementById("pwPromptVOnlyBtn");
  const syncBtn = document.getElementById("pwPromptSyncBtn");
  const vModelLabel = document.getElementById("pwPromptVModelName");
  const pModelLabel = document.getElementById("pwPromptPName");
  const wModelLabel = document.getElementById("pwPromptWName");
  const flowSourceTag = document.getElementById("flowModelSourceTag");
  const rememberCheck = document.getElementById("pwPromptRememberCheck");
  const choiceSync = document.getElementById("pwChoiceCardSync");
  const choiceVOnly = document.getElementById("pwChoiceCardVOnly");

  // Granular targets & animated progress
  const targetCheckP = document.getElementById("pwCheckTargetP");
  const targetCheckW = document.getElementById("pwCheckTargetW");
  const targetCheckAutoBackup = document.getElementById("pwCheckAutoBackup");
  const progressWrap = document.getElementById("pwSyncProgressWrap");
  const stepLabel = document.getElementById("pwSyncStepLabel");
  const pctLabel = document.getElementById("pwSyncPctLabel");
  const progressFill = document.getElementById("pwSyncProgressFill");

  // Topbar and inspector trigger buttons
  const quickSyncBtn = document.getElementById("tripletQuickSyncBtn");
  const dockSyncBtn = document.getElementById("dockSyncPwBtn");

  const triggerManualPrompt = () => {
    openModalForWeapon(state.currentWeapon, state.currentTeam);
  };
  quickSyncBtn?.addEventListener("click", triggerManualPrompt);
  dockSyncBtn?.addEventListener("click", triggerManualPrompt);

  // Preference cycle button
  const pwPrefBtn = document.getElementById("pwPrefToggleBtn");
  const pwPrefLabel = document.getElementById("pwPrefToggleLabel");

  function updatePwPrefLabel() {
    const pref = localStorage.getItem("cs16_pw_sync_pref") || "always_ask";
    state.pwSyncPreference = pref;
    if (pwPrefLabel) {
      if (pref === "always_sync") pwPrefLabel.textContent = "P/W Sync: Auto Sync";
      else if (pref === "never_sync") pwPrefLabel.textContent = "P/W Sync: V-Only (Never)";
      else pwPrefLabel.textContent = "P/W Sync: Always Ask";
    }
  }
  updatePwPrefLabel();

  pwPrefBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    const cur = localStorage.getItem("cs16_pw_sync_pref") || "always_ask";
    let next = "always_sync";
    if (cur === "always_ask") next = "always_sync";
    else if (cur === "always_sync") next = "never_sync";
    else next = "always_ask";

    localStorage.setItem("cs16_pw_sync_pref", next);
    state.pwSyncPreference = next;
    updatePwPrefLabel();
    showToast(`P/W Sync mode changed to: ${next.replace('_', ' ').toUpperCase()}`, "info");
  });

  let currentPending = null;
  let selectedMode = "sync"; // 'sync' | 'v_only'
  let isSyncing = false;

  function closeModal() {
    modal.classList.add("hidden");
    currentPending = null;
    isSyncing = false;
    if (progressWrap) progressWrap.classList.add("hidden");
    if (syncBtn) {
      syncBtn.disabled = false;
      syncBtn.innerHTML = '<svg class="glyph glyph-xs"><use href="#glyph-sync"></use></svg><span>Sync P/W Models Now</span>';
    }
    if (vOnlyBtn) vOnlyBtn.disabled = false;
  }

  function setChoice(mode) {
    selectedMode = mode;
    if (mode === "sync") {
      choiceSync?.classList.add("selected");
      choiceVOnly?.classList.remove("selected");
      if (syncBtn) {
        syncBtn.className = "btn btn-primary";
        syncBtn.innerHTML = '<svg class="glyph glyph-xs"><use href="#glyph-sync"></use></svg><span>Sync P/W Models Now</span>';
      }
    } else {
      choiceSync?.classList.remove("selected");
      choiceVOnly?.classList.add("selected");
      if (syncBtn) {
        syncBtn.className = "btn btn-secondary";
        syncBtn.innerHTML = '<span>Keep Viewmodel Only</span>';
      }
    }
  }

  choiceSync?.addEventListener("click", () => setChoice("sync"));
  choiceVOnly?.addEventListener("click", () => setChoice("v_only"));
  closeBtn?.addEventListener("click", () => {
    if (!isSyncing) closeModal();
  });

  vOnlyBtn?.addEventListener("click", () => {
    if (isSyncing) return;
    if (rememberCheck?.checked) {
      localStorage.setItem("cs16_pw_sync_pref", "never_sync");
      state.pwSyncPreference = "never_sync";
    }
    closeModal();
    showToast("Kept Viewmodel only (v_*.mdl). P/W models untouched.", "info");
  });

  function openModalForWeapon(weapon, team) {
    currentPending = { weapon, team };
    const wep = (weapon || "usp").toLowerCase();
    if (vModelLabel) vModelLabel.textContent = `v_${wep}.mdl`;
    if (pModelLabel) pModelLabel.textContent = `p_${wep}.mdl`;
    if (wModelLabel) wModelLabel.textContent = `w_${wep}.mdl`;
    if (flowSourceTag) flowSourceTag.textContent = `v_${wep}.mdl`;

    setChoice("sync");
    if (rememberCheck) rememberCheck.checked = false;
    if (progressWrap) progressWrap.classList.add("hidden");
    if (syncBtn) syncBtn.disabled = false;
    if (vOnlyBtn) vOnlyBtn.disabled = false;
    modal.classList.remove("hidden");
  }

  syncBtn?.addEventListener("click", async () => {
    if (!currentPending || isSyncing) {
      closeModal();
      return;
    }

    const { weapon, team } = currentPending;
    const shouldRemember = Boolean(rememberCheck?.checked);

    if (selectedMode === "v_only") {
      if (shouldRemember) {
        localStorage.setItem("cs16_pw_sync_pref", "never_sync");
        state.pwSyncPreference = "never_sync";
      }
      closeModal();
      showToast("Kept Viewmodel only (v_*.mdl). P/W models untouched.", "info");
      return;
    }

    const syncP = Boolean(targetCheckP?.checked ?? true);
    const syncW = Boolean(targetCheckW?.checked ?? true);
    const autoBak = Boolean(targetCheckAutoBackup?.checked ?? true);

    if (!syncP && !syncW) {
      showToast("Please check at least one target model (Player or World).", "warning");
      return;
    }

    if (shouldRemember) {
      localStorage.setItem("cs16_pw_sync_pref", "always_sync");
      state.pwSyncPreference = "always_sync";
    }

    isSyncing = true;
    if (syncBtn) {
      syncBtn.disabled = true;
      syncBtn.innerHTML = '<div class="spinner-sm"></div><span>Synchronizing...</span>';
    }
    if (vOnlyBtn) vOnlyBtn.disabled = true;

    // Show and animate compilation progress bar
    if (progressWrap) progressWrap.classList.remove("hidden");
    const setProg = (pct, label) => {
      if (progressFill) progressFill.style.width = `${pct}%`;
      if (pctLabel) pctLabel.textContent = `${pct}%`;
      if (stepLabel) stepLabel.textContent = label;
    };

    setProg(20, "Creating safe .orig.mdl backup snapshot...");
    await new Promise((r) => setTimeout(r, 260));

    setProg(50, "Extracting viewmodel UV textures & Floyd-Steinberg quantizing...");
    await new Promise((r) => setTimeout(r, 280));

    try {
      setProg(75, `Compiling StudioModel headers for ${[syncP ? 'p_' + weapon : '', syncW ? 'w_' + weapon : ''].filter(Boolean).join(', ')}...`);
      const res = await apiPost("/api/amxx/sync_pw", {
        weapon: weapon,
        team: team,
        auto_backup: autoBak,
        sync_p: syncP,
        sync_w: syncW,
      });

      setProg(100, "Synchronization Complete! Triplet verified.");
      await new Promise((r) => setTimeout(r, 350));

      closeModal();
      const pStatus = res.p_injected ? "✓ p_*.mdl" : "- p_*.mdl skipped";
      const wStatus = res.w_injected ? "✓ w_*.mdl" : "- w_*.mdl skipped";
      showToast(`P/W Synchronized: ${pStatus}, ${wStatus}`, "success");
      updateTripletTelemetry(weapon, team);
      eventBus.emit("amxx:pwSynced", { weapon, team, result: res });
    } catch (err) {
      showToast(`P/W Sync failed: ${err.message}`, "error");
      closeModal();
    }
  });

  // Listen for pw:promptSync event from slots.js or other modules
  eventBus.on("pw:promptSync", async (data) => {
    const pref = state.pwSyncPreference || localStorage.getItem("cs16_pw_sync_pref") || "always_ask";

    if (pref === "always_sync") {
      showLoader(`Auto-syncing P & W models for ${data.weapon.toUpperCase()}...`);
      try {
        const res = await apiPost("/api/amxx/sync_pw", {
          weapon: data.weapon,
          team: data.team,
          auto_backup: true,
          sync_p: true,
          sync_w: true,
        });
        showToast(`Auto-synced P & W models for ${data.weapon.toUpperCase()}`, "success");
        updateTripletTelemetry(data.weapon, data.team);
        eventBus.emit("amxx:pwSynced", { weapon: data.weapon, team: data.team, result: res });
      } catch (err) {
        showToast(`Auto P/W Sync failed: ${err.message}`, "error");
      } finally {
        hideLoader();
      }
      return;
    }

    if (pref === "never_sync") {
      return;
    }

    // Default: Show interactive Titanium prompt modal
    openModalForWeapon(data.weapon, data.team);
  });
}
