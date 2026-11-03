/**
 * core/api.js - HTTP API Client & UI Feedback Helpers
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

// Dynamic getters for root DOM elements to guarantee live access regardless of execution order
export const elements = {
  get loader() { return document.getElementById("loader"); },
  get loaderText() { return document.getElementById("loaderText"); },
  get toastContainer() { return document.getElementById("toastContainer"); },
  get teamToggle() { return document.getElementById("teamToggle"); },
  get weaponSelect() { return document.getElementById("weaponSelect"); },
  get profileSelect() { return document.getElementById("profileSelect"); },
  get saveProfileBtn() { return document.getElementById("saveProfileBtn"); },
  get restoreBtn() { return document.getElementById("restoreBtn"); },
  get openProToolsBtn() { return document.getElementById("openProToolsBtn"); },
  get modelName() { return document.getElementById("modelName"); },
  get modelPath() { return document.getElementById("modelPath"); },
  get textureCount() { return document.getElementById("textureCount"); },
  get stickerCount() { return document.getElementById("stickerCount"); },
  get backupStatus() { return document.getElementById("backupStatus"); },
  get textureGrid() { return document.getElementById("textureGrid"); },
  get navTabs() { return document.querySelectorAll(".nav-tab"); },
  get tabPanes() { return document.querySelectorAll(".tab-pane"); },
  get filterPills() { return document.querySelectorAll(".filter-pill"); },

  // QoL Header Buttons
  get quickSearchBtn() { return document.getElementById("quickSearchBtn"); },
  get undoBtn() { return document.getElementById("undoBtn"); },
  get redoBtn() { return document.getElementById("redoBtn"); },
  get exportModpackBtn() { return document.getElementById("exportModpackBtn"); },
};

/**
 * Standardized HTTP GET wrapper with error JSON parsing
 */
export async function apiGet(endpoint) {
  try {
    const res = await fetch(endpoint);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`[API GET] Failed: ${endpoint}`, err);
    throw err;
  }
}

/**
 * Standardized HTTP POST wrapper
 */
export async function apiPost(endpoint, data) {
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`[API POST] Failed: ${endpoint}`, err);
    throw err;
  }
}

/**
 * Modern floating toast notification
 */
export function showToast(message, type = "info") {
  const container = elements.toastContainer || document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/**
 * Loading overlay spinner
 */
export function showLoader(text = "Processing...") {
  const loader = elements.loader || document.getElementById("loader");
  const loaderText = elements.loaderText || document.getElementById("loaderText");
  if (loaderText) loaderText.textContent = text;
  if (loader) loader.classList.remove("hidden");
}

export function hideLoader() {
  const loader = elements.loader || document.getElementById("loader");
  if (loader) loader.classList.add("hidden");
}
