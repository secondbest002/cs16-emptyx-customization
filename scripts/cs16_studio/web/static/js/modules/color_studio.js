/**
 * modules/color_studio.js - Photographic Color Grading Studio Pro with 60FPS Live Preview
 * Features:
 * - Sigmoid Soft S-Curve contrast matching Python backend exactly
 * - Luminance-preserving Kelvin/Planckian white balance shifts
 * - Gaussian roll-off shadows boost and highlights recovery
 * - 8-Channel Selective HSL Color Mixer (Red, Orange, Yellow, Green, Cyan, Blue, Purple, Magenta)
 * - Halo-free clarity & unsharp sharpening
 * - Targeted Eyedropper Recolor: samples texture pixel and auto-selects its HSL channel
 * - Live RGB Histogram & Shadows/Highlights Clipping Meter
 * - Real-time 3D Viewport Synchronized Grading (debounced 60FPS)
 * - Picsart/Lightroom collapsible structured tool sections
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

import { state, eventBus } from "../core/state.js";
import { apiPost, showToast, showLoader, hideLoader } from "../core/api.js";

export const COLOR_PRESETS = {
  neutral: { brightness: 0, contrast: 0, saturation: 0, vibrance: 0, clarity: 0, shadows: 0, highlights: 0, temperature: 0, tint: 0, hue: 0, sharpen: 0 },
  vibrant_cs2: { brightness: 5, contrast: 15, saturation: 18, vibrance: 45, clarity: 30, shadows: 15, highlights: -10, temperature: 5, tint: 0, hue: 0, sharpen: 15 },
  dark_ops: { brightness: -12, contrast: 25, saturation: -40, vibrance: -25, clarity: 20, shadows: -20, highlights: -15, temperature: -10, tint: -5, hue: 0, sharpen: 20 },
  warm_golden: { brightness: 8, contrast: 10, saturation: 12, vibrance: 25, clarity: 15, shadows: 10, highlights: 20, temperature: 35, tint: -5, hue: 0, sharpen: 10 },
  cyber_neon: { brightness: 5, contrast: 20, saturation: 35, vibrance: 60, clarity: 35, shadows: 5, highlights: 10, temperature: -30, tint: 25, hue: 0, sharpen: 25 },

  ruby: { brightness: 5, contrast: 40, saturation: 90, vibrance: 95, clarity: 35, shadows: -10, highlights: 25, temperature: 15, tint: 45, hue: 0, sharpen: 25 },
  sapphire: { brightness: 0, contrast: 40, saturation: 90, vibrance: 95, clarity: 35, shadows: -20, highlights: 25, temperature: -45, tint: 10, hue: 240, sharpen: 25 },
  emerald: { brightness: 2, contrast: 35, saturation: 90, vibrance: 95, clarity: 35, shadows: -15, highlights: 25, temperature: -20, tint: -50, hue: 125, sharpen: 25 },
  gamma_emerald: { brightness: 8, contrast: 40, saturation: 95, vibrance: 100, clarity: 40, shadows: 0, highlights: 30, temperature: -15, tint: -60, hue: 130, sharpen: 30 },
  gamma_doppler_phase_1: { brightness: -5, contrast: 30, saturation: 70, vibrance: 80, clarity: 30, shadows: -20, highlights: 20, temperature: -25, tint: -40, hue: 145, sharpen: 20 },
  gamma_doppler_phase_2: { brightness: 10, contrast: 35, saturation: 95, vibrance: 100, clarity: 40, shadows: 10, highlights: 30, temperature: -10, tint: -55, hue: 115, sharpen: 25 },
  gamma_doppler_phase_3: { brightness: 0, contrast: 30, saturation: 75, vibrance: 85, clarity: 35, shadows: -15, highlights: 25, temperature: -35, tint: -30, hue: 170, sharpen: 20 },
  gamma_doppler_phase_4: { brightness: 5, contrast: 30, saturation: 85, vibrance: 90, clarity: 35, shadows: -10, highlights: 25, temperature: -25, tint: -45, hue: 155, sharpen: 20 },
  blue_gem: { brightness: 10, contrast: 40, saturation: 95, vibrance: 100, clarity: 45, shadows: -10, highlights: 35, temperature: -40, tint: 15, hue: 200, sharpen: 30 },
  gold_arabesque: { brightness: 12, contrast: 30, saturation: 75, vibrance: 85, clarity: 30, shadows: 15, highlights: 35, temperature: 40, tint: -15, hue: 42, sharpen: 30 },
  tiger_tooth: { brightness: 15, contrast: 35, saturation: 90, vibrance: 95, clarity: 40, shadows: 10, highlights: 30, temperature: 40, tint: -15, hue: 42, sharpen: 30 },
  slaughter: { brightness: 2, contrast: 45, saturation: 85, vibrance: 90, clarity: 45, shadows: -15, highlights: 25, temperature: 25, tint: 35, hue: 355, sharpen: 35 },
  hot_rod: { brightness: 10, contrast: 50, saturation: 100, vibrance: 100, clarity: 40, shadows: 5, highlights: 35, temperature: 30, tint: 40, hue: 0, sharpen: 25 },
  cyan_phosphor: { brightness: 8, contrast: 35, saturation: 95, vibrance: 100, clarity: 40, shadows: 0, highlights: 30, temperature: -50, tint: -20, hue: 185, sharpen: 25 },
  neon_rider: { brightness: 12, contrast: 40, saturation: 95, vibrance: 100, clarity: 40, shadows: 5, highlights: 30, temperature: -20, tint: 45, hue: 305, sharpen: 30 },
};

export const HSL_CHANNELS = {
  red: { name: "Red (0°)", center: 0.0, color: "#ef4444" },
  orange: { name: "Orange (30°)", center: 30.0, color: "#f97316" },
  yellow: { name: "Yellow (60°)", center: 60.0, color: "#eab308" },
  green: { name: "Green (120°)", center: 120.0, color: "#22c55e" },
  cyan: { name: "Cyan (180°)", center: 180.0, color: "#06b6d4" },
  blue: { name: "Blue (240°)", center: 240.0, color: "#3b82f6" },
  purple: { name: "Purple (280°)", center: 280.0, color: "#a855f7" },
  magenta: { name: "Magenta (320°)", center: 320.0, color: "#ec4899" },
};

const els = {
  get colorTargetSelect() { return document.getElementById("colorTargetSelect"); },
  get colorPresetChips() { return document.getElementById("colorPresetChips"); },
  get colorVibrance() { return document.getElementById("colorVibrance"); },
  get colorVibranceVal() { return document.getElementById("colorVibranceVal"); },
  get colorSaturation() { return document.getElementById("colorSaturation"); },
  get colorSaturationVal() { return document.getElementById("colorSaturationVal"); },
  get colorGlobalHue() { return document.getElementById("colorGlobalHue"); },
  get colorGlobalHueVal() { return document.getElementById("colorGlobalHueVal"); },
  get colorClarity() { return document.getElementById("colorClarity"); },
  get colorClarityVal() { return document.getElementById("colorClarityVal"); },
  get colorSharpen() { return document.getElementById("colorSharpen"); },
  get colorSharpenVal() { return document.getElementById("colorSharpenVal"); },
  get colorContrast() { return document.getElementById("colorContrast"); },
  get colorContrastVal() { return document.getElementById("colorContrastVal"); },
  get colorBrightness() { return document.getElementById("colorBrightness"); },
  get colorBrightnessVal() { return document.getElementById("colorBrightnessVal"); },
  get colorShadows() { return document.getElementById("colorShadows"); },
  get colorShadowsVal() { return document.getElementById("colorShadowsVal"); },
  get colorHighlights() { return document.getElementById("colorHighlights"); },
  get colorHighlightsVal() { return document.getElementById("colorHighlightsVal"); },
  get colorTemp() { return document.getElementById("colorTemp"); },
  get colorTempVal() { return document.getElementById("colorTempVal"); },
  get colorTint() { return document.getElementById("colorTint"); },
  get colorTintVal() { return document.getElementById("colorTintVal"); },
  get colorApplyBtn() { return document.getElementById("colorApplyBtn"); },
  get colorResetBtn() { return document.getElementById("colorResetBtn"); },
  get colorOrigImg() { return document.getElementById("colorOrigImg"); },
  get colorAdjustedCanvas() { return document.getElementById("colorAdjustedCanvas"); },

  // HSL Mixer elements
  get hslSwatchesBar() { return document.getElementById("hslSwatchesBar"); },
  get hslActiveChannelName() { return document.getElementById("hslActiveChannelName"); },
  get hslResetChannelBtn() { return document.getElementById("hslResetChannelBtn"); },
  get hslResetAllBtn() { return document.getElementById("hslResetAllBtn"); },
  get hslHueSlider() { return document.getElementById("hslHueSlider"); },
  get hslHueSliderVal() { return document.getElementById("hslHueSliderVal"); },
  get hslSatSlider() { return document.getElementById("hslSatSlider"); },
  get hslSatSliderVal() { return document.getElementById("hslSatSliderVal"); },
  get hslLightSlider() { return document.getElementById("hslLightSlider"); },
  get hslLightSliderVal() { return document.getElementById("hslLightSliderVal"); },

  // Histogram & Clipping Meter
  get colorHistogramCanvas() { return document.getElementById("colorHistogramCanvas"); },
  get shadowClipBadge() { return document.getElementById("shadowClipBadge"); },
  get highlightClipBadge() { return document.getElementById("highlightClipBadge"); },

  // Curtain elements
  get curtainCompareStage() { return document.getElementById("curtainCompareStage"); },
  get sideCompareStage() { return document.getElementById("sideCompareStage"); },
  get curtainModeBtn() { return document.getElementById("curtainModeBtn"); },
  get sideModeBtn() { return document.getElementById("sideModeBtn"); },
  get curtainViewport() { return document.getElementById("curtainViewport"); },
  get curtainBgImg() { return document.getElementById("curtainBgImg"); },
  get curtainFgWrap() { return document.getElementById("curtainFgWrap"); },
  get curtainFgCanvas() { return document.getElementById("curtainFgCanvas"); },
  get curtainDivider() { return document.getElementById("curtainDivider"); },
  get curtainHandle() { return document.getElementById("curtainHandle"); },
  get colorEyedropperBtn() { return document.getElementById("colorEyedropperBtn"); },
  get eyedropperSample() { return document.getElementById("eyedropperSample"); },
};

let sync3dTimeout = null;
let offscreenCanvas = null;
let offscreenCtx = null;

export function initColorStudioModule() {
  setupEventListeners();
  setupAccordion();
  setupHslMixerEvents();
  setupEyedropperEvents();

  eventBus.on("model:loaded", () => {
    setupColorStudioTab();
  });

  eventBus.on("color:selectTexture", (texIndex) => {
    if (els.colorTargetSelect) {
      els.colorTargetSelect.value = texIndex;
      onColorTargetChanged();
    }
  });
}

export function setupColorStudioTab() {
  const m = state.modelData;
  if (!m || !els.colorTargetSelect) return;

  const bakeArea = document.getElementById("stage2dBakeArea");
  if (bakeArea) bakeArea.classList.add("hidden");
  if (state.qol && state.qol.compareMode === "side") {
    if (els.sideCompareStage) els.sideCompareStage.classList.remove("hidden");
    if (els.curtainCompareStage) els.curtainCompareStage.classList.add("hidden");
  } else {
    if (els.curtainCompareStage) els.curtainCompareStage.classList.remove("hidden");
    if (els.sideCompareStage) els.sideCompareStage.classList.add("hidden");
  }

  const prevIdx = state.colorStudio.targetIndex;
  els.colorTargetSelect.innerHTML = "";

  const targetTextures = m.textures.filter(
    (t) => t.role === "skin" || t.role === "glove" || t.role === "sticker"
  );

  if (targetTextures.length === 0) {
    els.colorTargetSelect.innerHTML = '<option value="">No editable textures found</option>';
    return;
  }

  targetTextures.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.index;
    opt.textContent = `[${t.role.toUpperCase()}] ${t.name} (${t.width}x${t.height})`;
    els.colorTargetSelect.appendChild(opt);
  });

  if (prevIdx !== null && targetTextures.some((t) => t.index === prevIdx)) {
    els.colorTargetSelect.value = prevIdx;
  }

  onColorTargetChanged();
}

export function onColorTargetChanged() {
  if (!els.colorTargetSelect) return;
  const idx = els.colorTargetSelect.value;
  if (!idx || !state.modelData) return;

  const tex = state.modelData.textures.find((t) => t.index === parseInt(idx, 10));
  if (!tex || !tex.preview) return;

  state.colorStudio.targetIndex = tex.index;
  if (els.colorOrigImg) els.colorOrigImg.src = tex.preview;
  if (els.curtainBgImg) els.curtainBgImg.src = tex.preview;

  // Toggle checkerboard backdrop for transparent sticker previews
  const isTransparent = Boolean(tex.role === "sticker" || tex.is_masked);
  const stages = [
    els.sideCompareStage,
    els.curtainCompareStage,
    els.curtainViewport,
    els.colorAdjustedCanvas ? els.colorAdjustedCanvas.parentElement : null,
    els.colorOrigImg ? els.colorOrigImg.parentElement : null,
  ];
  stages.forEach((st) => {
    if (st) {
      st.classList.toggle("checkerboard-bg", isTransparent);
    }
  });

  const img = new Image();
  img.onload = () => {
    state.colorStudio.origImg = img;
    if (els.colorAdjustedCanvas) {
      els.colorAdjustedCanvas.width = img.width;
      els.colorAdjustedCanvas.height = img.height;
    }
    if (els.curtainFgCanvas) {
      els.curtainFgCanvas.width = img.width;
      els.curtainFgCanvas.height = img.height;
    }

    // Allocate offscreen canvas for fast pixel processing
    if (!offscreenCanvas) {
      offscreenCanvas = document.createElement("canvas");
      offscreenCtx = offscreenCanvas.getContext("2d", { willReadFrequently: true });
    }
    offscreenCanvas.width = img.width;
    offscreenCanvas.height = img.height;

    renderColorStudioPreview();
  };
  img.src = tex.preview;
}

function setupAccordion() {
  const headers = document.querySelectorAll(".accordion-header");
  headers.forEach((header) => {
    header.style.cursor = "pointer";
    header.addEventListener("click", () => {
      const parent = header.parentElement;
      if (parent) {
        parent.classList.toggle("collapsed");
      }
    });
  });
}

function setupEventListeners() {
  if (els.colorTargetSelect) {
    els.colorTargetSelect.addEventListener("change", () => onColorTargetChanged());
  }

  if (els.colorPresetChips) {
    els.colorPresetChips.querySelectorAll(".preset-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        els.colorPresetChips.querySelectorAll(".preset-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        applyColorPreset(chip.dataset.preset);
      });
    });
  }

  const sliders = [
    { el: els.colorVibrance, valEl: els.colorVibranceVal, key: "vibrance" },
    { el: els.colorSaturation, valEl: els.colorSaturationVal, key: "saturation" },
    { el: els.colorGlobalHue, valEl: els.colorGlobalHueVal, key: "hue", suffix: "°" },
    { el: els.colorClarity, valEl: els.colorClarityVal, key: "clarity" },
    { el: els.colorSharpen, valEl: els.colorSharpenVal, key: "sharpen" },
    { el: els.colorContrast, valEl: els.colorContrastVal, key: "contrast" },
    { el: els.colorBrightness, valEl: els.colorBrightnessVal, key: "brightness" },
    { el: els.colorShadows, valEl: els.colorShadowsVal, key: "shadows" },
    { el: els.colorHighlights, valEl: els.colorHighlightsVal, key: "highlights" },
    { el: els.colorTemp, valEl: els.colorTempVal, key: "temperature" },
    { el: els.colorTint, valEl: els.colorTintVal, key: "tint" },
  ];

  sliders.forEach(({ el, valEl, key, suffix }) => {
    if (!el) return;
    el.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      state.colorStudio.params[key] = val;
      const s = suffix || "";
      if (valEl) valEl.textContent = val > 0 ? `+${val}${s}` : `${val}${s}`;
      renderColorStudioPreview();
    });
  });

  if (els.colorApplyBtn) {
    // Screen 3: Surface Wear Slider & Dither Algorithm listeners
    const wearSlider = document.getElementById("colorWearSlider");
    const wearVal = document.getElementById("colorWearVal");
    if (wearSlider) {
      wearSlider.addEventListener("input", (e) => {
        const v = parseFloat(e.target.value);
        state.colorStudio.params.wear = v;
        if (wearVal) {
          let label = `${v}% (Factory New)`;
          if (v > 75) label = `${v}% (Battle-Scarred)`;
          else if (v > 45) label = `${v}% (Well-Worn)`;
          else if (v > 20) label = `${v}% (Field-Tested)`;
          else if (v > 5) label = `${v}% (Minimal Wear)`;
          wearVal.textContent = label;
        }
        schedulePreview();
      });
    }

    const ditherAlgo = document.getElementById("colorDitherAlgo");
    if (ditherAlgo) {
      ditherAlgo.addEventListener("change", (e) => {
        state.colorStudio.params.dither = e.target.value;
        schedulePreview();
      });
    }

    els.colorApplyBtn.addEventListener("click", async () => {
      await applyColorGradingToModel();
    });
  }

  if (els.colorResetBtn) {
    els.colorResetBtn.addEventListener("click", () => {
      applyColorPreset("neutral");
      resetAllHslChannels();
    });
  }

  // Comparison mode toggle (Curtain vs Side-by-Side)
  if (els.curtainModeBtn && els.sideModeBtn) {
    els.curtainModeBtn.addEventListener("click", () => {
      els.curtainModeBtn.classList.add("active");
      els.sideModeBtn.classList.remove("active");
      if (els.curtainCompareStage) els.curtainCompareStage.classList.remove("hidden");
      if (els.sideCompareStage) els.sideCompareStage.classList.add("hidden");
      state.qol.compareMode = "curtain";
    });

    els.sideModeBtn.addEventListener("click", () => {
      els.sideModeBtn.classList.add("active");
      els.curtainModeBtn.classList.remove("active");
      if (els.curtainCompareStage) els.curtainCompareStage.classList.add("hidden");
      if (els.sideCompareStage) els.sideCompareStage.classList.remove("hidden");
      state.qol.compareMode = "side";
    });
  }

  setupCurtainDivider();
}

function setupHslMixerEvents() {
  if (els.hslSwatchesBar) {
    els.hslSwatchesBar.querySelectorAll(".hsl-swatch").forEach((swatch) => {
      swatch.addEventListener("click", () => {
        selectHslChannel(swatch.dataset.channel);
      });
    });
  }

  if (els.hslHueSlider) {
    els.hslHueSlider.addEventListener("input", (e) => {
      const ch = state.colorStudio.activeHslChannel;
      const val = parseFloat(e.target.value);
      if (!state.colorStudio.params.hsl_adjustments[ch]) {
        state.colorStudio.params.hsl_adjustments[ch] = { hue: 0, saturation: 0, lightness: 0 };
      }
      state.colorStudio.params.hsl_adjustments[ch].hue = val;
      if (els.hslHueSliderVal) els.hslHueSliderVal.textContent = val > 0 ? `+${val}°` : `${val}°`;
      updateSwatchBadge(ch);
      renderColorStudioPreview();
    });
  }

  if (els.hslSatSlider) {
    els.hslSatSlider.addEventListener("input", (e) => {
      const ch = state.colorStudio.activeHslChannel;
      const val = parseFloat(e.target.value);
      if (!state.colorStudio.params.hsl_adjustments[ch]) {
        state.colorStudio.params.hsl_adjustments[ch] = { hue: 0, saturation: 0, lightness: 0 };
      }
      state.colorStudio.params.hsl_adjustments[ch].saturation = val;
      if (els.hslSatSliderVal) els.hslSatSliderVal.textContent = val > 0 ? `+${val}` : `${val}`;
      updateSwatchBadge(ch);
      renderColorStudioPreview();
    });
  }

  if (els.hslLightSlider) {
    els.hslLightSlider.addEventListener("input", (e) => {
      const ch = state.colorStudio.activeHslChannel;
      const val = parseFloat(e.target.value);
      if (!state.colorStudio.params.hsl_adjustments[ch]) {
        state.colorStudio.params.hsl_adjustments[ch] = { hue: 0, saturation: 0, lightness: 0 };
      }
      state.colorStudio.params.hsl_adjustments[ch].lightness = val;
      if (els.hslLightSliderVal) els.hslLightSliderVal.textContent = val > 0 ? `+${val}` : `${val}`;
      updateSwatchBadge(ch);
      renderColorStudioPreview();
    });
  }

  if (els.hslResetChannelBtn) {
    els.hslResetChannelBtn.addEventListener("click", () => {
      resetActiveHslChannel();
    });
  }

  if (els.hslResetAllBtn) {
    els.hslResetAllBtn.addEventListener("click", () => {
      resetAllHslChannels();
    });
  }
}

export function selectHslChannel(channelName) {
  if (!HSL_CHANNELS[channelName]) return;
  state.colorStudio.activeHslChannel = channelName;

  if (els.hslSwatchesBar) {
    els.hslSwatchesBar.querySelectorAll(".hsl-swatch").forEach((sw) => {
      sw.classList.toggle("active", sw.dataset.channel === channelName);
    });
  }

  const chInfo = HSL_CHANNELS[channelName];
  if (els.hslActiveChannelName) {
    els.hslActiveChannelName.textContent = chInfo.name;
    els.hslActiveChannelName.style.color = chInfo.color;
  }

  const adj = state.colorStudio.params.hsl_adjustments[channelName] || { hue: 0, saturation: 0, lightness: 0 };

  if (els.hslHueSlider) {
    els.hslHueSlider.value = adj.hue || 0;
    if (els.hslHueSliderVal) els.hslHueSliderVal.textContent = adj.hue > 0 ? `+${adj.hue}°` : `${adj.hue}°`;
  }
  if (els.hslSatSlider) {
    els.hslSatSlider.value = adj.saturation || 0;
    if (els.hslSatSliderVal) els.hslSatSliderVal.textContent = adj.saturation > 0 ? `+${adj.saturation}` : `${adj.saturation}`;
  }
  if (els.hslLightSlider) {
    els.hslLightSlider.value = adj.lightness || 0;
    if (els.hslLightSliderVal) els.hslLightSliderVal.textContent = adj.lightness > 0 ? `+${adj.lightness}` : `${adj.lightness}`;
  }
}

function updateSwatchBadge(channelName) {
  const adj = state.colorStudio.params.hsl_adjustments[channelName];
  const hasAdj = adj && (adj.hue !== 0 || adj.saturation !== 0 || adj.lightness !== 0);
  if (els.hslSwatchesBar) {
    const sw = els.hslSwatchesBar.querySelector(`.hsl-swatch[data-channel="${channelName}"]`);
    if (sw) sw.classList.toggle("has-adjustments", Boolean(hasAdj));
  }
}

function resetActiveHslChannel() {
  const ch = state.colorStudio.activeHslChannel;
  if (!ch) return;
  state.colorStudio.params.hsl_adjustments[ch] = { hue: 0, saturation: 0, lightness: 0 };
  selectHslChannel(ch);
  updateSwatchBadge(ch);
  renderColorStudioPreview();
}

function resetAllHslChannels() {
  for (const ch of Object.keys(HSL_CHANNELS)) {
    state.colorStudio.params.hsl_adjustments[ch] = { hue: 0, saturation: 0, lightness: 0 };
    updateSwatchBadge(ch);
  }
  selectHslChannel(state.colorStudio.activeHslChannel || "yellow");
  renderColorStudioPreview();
}

function setupEyedropperEvents() {
  if (!els.colorEyedropperBtn) return;

  els.colorEyedropperBtn.addEventListener("click", () => {
    state.colorStudio.isEyedropperActive = !state.colorStudio.isEyedropperActive;
    updateEyedropperUI();
  });

  const samplingTargets = [els.curtainViewport, els.colorAdjustedCanvas, els.colorOrigImg];
  samplingTargets.forEach((target) => {
    if (!target) return;
    target.addEventListener("click", (e) => {
      if (!state.colorStudio.isEyedropperActive) return;
      sampleColorFromTarget(e, target);
    });
  });
}

function updateEyedropperUI() {
  const active = state.colorStudio.isEyedropperActive;
  if (els.colorEyedropperBtn) {
    els.colorEyedropperBtn.classList.toggle("active", active);
  }
  document.body.classList.toggle("eyedropper-active", active);
  if (active) {
    showToast("Eyedropper active: click any texture pixel to auto-select its HSL channel", "info");
  }
}

function sampleColorFromTarget(event, targetElement) {
  const img = state.colorStudio.origImg;
  if (!img) return;

  const rect = targetElement.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const clickY = event.clientY - rect.top;

  // Account for object-fit: contain letterboxing/pillarboxing inside the element
  const containerAspect = rect.width / (rect.height || 1);
  const imgAspect = img.width / (img.height || 1);
  let renderW = rect.width;
  let renderH = rect.height;
  let offsetX = 0;
  let offsetY = 0;

  if (imgAspect > containerAspect) {
    // Letterbox on top & bottom
    renderW = rect.width;
    renderH = rect.width / imgAspect;
    offsetX = 0;
    offsetY = (rect.height - renderH) / 2;
  } else {
    // Pillarbox on left & right
    renderH = rect.height;
    renderW = rect.height * imgAspect;
    offsetX = (rect.width - renderW) / 2;
    offsetY = 0;
  }

  const relX = clickX - offsetX;
  const relY = clickY - offsetY;

  const normX = Math.max(0, Math.min(1, relX / (renderW || 1)));
  const normY = Math.max(0, Math.min(1, relY / (renderH || 1)));

  const pixelX = Math.max(0, Math.min(img.width - 1, Math.floor(normX * img.width)));
  const pixelY = Math.max(0, Math.min(img.height - 1, Math.floor(normY * img.height)));

  // If clicked on the graded side or colorAdjustedCanvas, sample the graded canvas
  const isCurtainViewport = (targetElement === els.curtainViewport);
  const curtainDividerPct = state.qol.curtainPercent !== undefined ? state.qol.curtainPercent : 50;
  const isGradedSide = (targetElement === els.colorAdjustedCanvas) ||
    (isCurtainViewport && (clickX / rect.width * 100) > curtainDividerPct);

  let r = 0, g = 0, b = 0, a = 255;
  if (isGradedSide && els.colorAdjustedCanvas && els.colorAdjustedCanvas.width === img.width) {
    const actx = els.colorAdjustedCanvas.getContext("2d", { willReadFrequently: true });
    const p = actx.getImageData(pixelX, pixelY, 1, 1).data;
    r = p[0];
    g = p[1];
    b = p[2];
    a = p[3];
  } else {
    if (!offscreenCanvas) {
      offscreenCanvas = document.createElement("canvas");
      offscreenCtx = offscreenCanvas.getContext("2d", { willReadFrequently: true });
    }
    if (offscreenCanvas.width !== img.width || offscreenCanvas.height !== img.height) {
      offscreenCanvas.width = img.width;
      offscreenCanvas.height = img.height;
    }
    offscreenCtx.drawImage(img, 0, 0);
    const p = offscreenCtx.getImageData(pixelX, pixelY, 1, 1).data;
    r = p[0];
    g = p[1];
    b = p[2];
    a = p[3];
  }

  if (a < 128) {
    showToast("Selected area is transparent. Please click on an opaque sticker pixel.", "info");
    return;
  }

  const hex = `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase()}`;

  if (els.eyedropperSample) {
    els.eyedropperSample.textContent = hex;
    els.eyedropperSample.style.backgroundColor = hex;
    const lumVal = 0.299 * r + 0.587 * g + 0.114 * b;
    els.eyedropperSample.style.color = lumVal > 128 ? "#000000" : "#ffffff";
    els.eyedropperSample.classList.remove("hidden");
  }

  // Calculate pixel Hue and Saturation
  const rf = r / 255.0;
  const gf = g / 255.0;
  const bf = b / 255.0;
  const maxC = Math.max(rf, gf, bf);
  const minC = Math.min(rf, gf, bf);
  const c = maxC - minC;
  const sat = maxC > 1e-5 ? c / maxC : 0;

  // Grayscale / achromatic detection: Gun metal, black steel, or white text
  if (c < 0.05 || sat < 0.08) {
    state.colorStudio.isEyedropperActive = false;
    updateEyedropperUI();
    showToast(`Sampled neutral/grayscale pixel (${hex}) — click on a colored region to select an HSL channel.`, "warning");
    return;
  }

  let hue = 0;
  if (maxC === rf) {
    hue = 60 * (((gf - bf) / c) % 6);
  } else if (maxC === gf) {
    hue = 60 * (((bf - rf) / c) + 2);
  } else {
    hue = 60 * (((rf - gf) / c) + 4);
  }
  hue = ((hue % 360) + 360) % 360;

  // Find nearest HSL channel
  let bestCh = "yellow";
  let minDiff = 999;
  for (const [chName, info] of Object.entries(HSL_CHANNELS)) {
    let diff = Math.abs(hue - info.center) % 360;
    diff = Math.min(diff, 360 - diff);
    if (diff < minDiff) {
      minDiff = diff;
      bestCh = chName;
    }
  }

  selectHslChannel(bestCh);
  state.colorStudio.isEyedropperActive = false;
  updateEyedropperUI();

  showToast(`Sampled ${HSL_CHANNELS[bestCh].name} (${hex}) — Ready to tune!`, "success");
}

function setupCurtainDivider() {
  const viewport = els.curtainViewport;
  if (!viewport) return;

  function updateCurtain(clientX) {
    const rect = viewport.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));

    state.qol.curtainPercent = pct;
    if (els.curtainFgWrap) {
      els.curtainFgWrap.style.clipPath = `polygon(${pct}% 0, 100% 0, 100% 100%, ${pct}% 100%)`;
      els.curtainFgWrap.style.webkitClipPath = `polygon(${pct}% 0, 100% 0, 100% 100%, ${pct}% 100%)`;
    }
    if (els.curtainDivider) els.curtainDivider.style.left = `${pct}%`;
  }

  if (els.curtainFgWrap) {
    els.curtainFgWrap.style.clipPath = "polygon(50% 0, 100% 0, 100% 100%, 50% 100%)";
    els.curtainFgWrap.style.webkitClipPath = "polygon(50% 0, 100% 0, 100% 100%, 50% 100%)";
  }
  if (els.curtainDivider) els.curtainDivider.style.left = "50%";

  viewport.addEventListener("mousedown", (e) => {
    if (state.colorStudio.isEyedropperActive) return;
    state.qol.isCurtainDragging = true;
    updateCurtain(e.clientX);
  });

  window.addEventListener("mousemove", (e) => {
    if (!state.qol.isCurtainDragging) return;
    updateCurtain(e.clientX);
  });

  window.addEventListener("mouseup", () => {
    state.qol.isCurtainDragging = false;
  });

  viewport.addEventListener("touchstart", (e) => {
    if (state.colorStudio.isEyedropperActive) return;
    if (e.touches.length > 0) {
      state.qol.isCurtainDragging = true;
      updateCurtain(e.touches[0].clientX);
    }
  });

  window.addEventListener("touchmove", (e) => {
    if (!state.qol.isCurtainDragging || e.touches.length === 0) return;
    updateCurtain(e.touches[0].clientX);
  });

  window.addEventListener("touchend", () => {
    state.qol.isCurtainDragging = false;
  });
}

export function applyColorPreset(presetKey) {
  const p = COLOR_PRESETS[presetKey] || COLOR_PRESETS.neutral;
  state.colorStudio.params = {
    ...state.colorStudio.params,
    ...p,
  };

  const map = [
    { el: els.colorVibrance, valEl: els.colorVibranceVal, v: p.vibrance },
    { el: els.colorSaturation, valEl: els.colorSaturationVal, v: p.saturation },
    { el: els.colorGlobalHue, valEl: els.colorGlobalHueVal, v: p.hue || 0, suffix: "°" },
    { el: els.colorClarity, valEl: els.colorClarityVal, v: p.clarity },
    { el: els.colorSharpen, valEl: els.colorSharpenVal, v: p.sharpen || 0 },
    { el: els.colorContrast, valEl: els.colorContrastVal, v: p.contrast },
    { el: els.colorBrightness, valEl: els.colorBrightnessVal, v: p.brightness },
    { el: els.colorShadows, valEl: els.colorShadowsVal, v: p.shadows },
    { el: els.colorHighlights, valEl: els.colorHighlightsVal, v: p.highlights },
    { el: els.colorTemp, valEl: els.colorTempVal, v: p.temperature },
    { el: els.colorTint, valEl: els.colorTintVal, v: p.tint },
  ];

  map.forEach(({ el, valEl, v, suffix }) => {
    if (el) el.value = v;
    const s = suffix || "";
    if (valEl) valEl.textContent = v > 0 ? `+${v}${s}` : `${v}${s}`;
  });

  renderColorStudioPreview();
}

/**
 * Pixel-Perfect JS Engine matching backend Python color_adjuster.py 100%
 */
export function renderColorStudioPreview() {
  const img = state.colorStudio.origImg;
  if (!img) return;

  const w = img.width;
  const h = img.height;
  if (w <= 0 || h <= 0) return;

  if (!offscreenCanvas) {
    offscreenCanvas = document.createElement("canvas");
    offscreenCtx = offscreenCanvas.getContext("2d", { willReadFrequently: true });
  }
  if (offscreenCanvas.width !== w || offscreenCanvas.height !== h) {
    offscreenCanvas.width = w;
    offscreenCanvas.height = h;
  }

  offscreenCtx.clearRect(0, 0, w, h);
  offscreenCtx.drawImage(img, 0, 0, w, h);

  const imgData = offscreenCtx.getImageData(0, 0, w, h);
  const data = imgData.data;
  const len = data.length;

  const p = state.colorStudio.params;
  const b = p.brightness / 100.0;
  const c = p.contrast / 100.0;
  const s = p.saturation / 100.0;
  const v = p.vibrance / 100.0;
  const cl = p.clarity / 100.0;
  const sh = p.shadows / 100.0;
  const hi = p.highlights / 100.0;
  const temp = p.temperature / 100.0;
  const ti = p.tint / 100.0;
  const globalHue = (p.hue || 0) % 360.0;
  const sharp = (p.sharpen || 0) / 100.0;

  // 1. Precalculate Sigmoid Contrast LUT (256 entries)
  const contrastLut = new Float32Array(256);
  if (c > 0) {
    const k = 8.0 * c;
    const s0 = 1.0 / (1.0 + Math.exp(0.5 * k));
    const s1 = 1.0 / (1.0 + Math.exp(-0.5 * k));
    const sDiff = s1 - s0;
    for (let i = 0; i < 256; i++) {
      const x = i / 255.0;
      const sx = 1.0 / (1.0 + Math.exp(-k * (x - 0.5)));
      contrastLut[i] = Math.max(0, Math.min(1, (sx - s0) / sDiff));
    }
  } else if (c < 0) {
    for (let i = 0; i < 256; i++) {
      const x = i / 255.0;
      contrastLut[i] = Math.max(0, Math.min(1, 0.5 + (x - 0.5) * (1.0 + c)));
    }
  } else {
    for (let i = 0; i < 256; i++) {
      contrastLut[i] = i / 255.0;
    }
  }

  // 2. Precalculate Gaussian Shadows & Highlights Weights (256 entries)
  const shadowWeightLut = new Float32Array(256);
  const highlightWeightLut = new Float32Array(256);
  const twoSigmaSq = 2.0 * (0.35 * 0.35);
  for (let i = 0; i < 256; i++) {
    const lum = i / 255.0;
    shadowWeightLut[i] = Math.exp(-(lum * lum) / twoSigmaSq);
    highlightWeightLut[i] = Math.exp(-((1.0 - lum) * (1.0 - lum)) / twoSigmaSq);
  }

  // 3. Precalculate Temperature & Tint Shift factors
  const hasTempTint = (temp !== 0.0 || ti !== 0.0);
  const kTemp = temp * 0.35;
  const kTint = ti * 0.30;

  // 4. Check if HSL Mixer is active
  const hslAdj = p.hsl_adjustments || {};
  let hasHsl = (globalHue !== 0.0);
  const activeChannels = [];
  for (const [chName, chInfo] of Object.entries(HSL_CHANNELS)) {
    const a = hslAdj[chName];
    if (a && (a.hue !== 0 || a.saturation !== 0 || a.lightness !== 0)) {
      hasHsl = true;
      activeChannels.push({
        center: chInfo.center,
        hue: a.hue || 0,
        sat: (a.saturation || 0) / 100.0,
        light: (a.lightness || 0) / 100.0,
      });
    }
  }

  // Histogram bins
  const histR = new Uint32Array(256);
  const histG = new Uint32Array(256);
  const histB = new Uint32Array(256);
  let shadowClippedCount = 0;
  let highlightClippedCount = 0;
  let totalPixels = 0;

  // Primary Pixel Shading Pass
  for (let i = 0; i < len; i += 4) {
    // Preserve 1-bit transparency for stickers/masked textures
    if (data[i + 3] < 128) {
      continue;
    }
    totalPixels++;

    let r = data[i] / 255.0;
    let g = data[i + 1] / 255.0;
    let bVal = data[i + 2] / 255.0;

    // A. Temperature & Tint with Luminance Preservation
    if (hasTempTint) {
      const lumOrig = 0.299 * r + 0.587 * g + 0.114 * bVal;

      r *= (1.0 + kTemp);
      bVal *= (1.0 - kTemp);

      g *= (1.0 - kTint);
      r *= (1.0 + 0.5 * kTint);
      bVal *= (1.0 + 0.5 * kTint);

      const lumNew = 0.299 * r + 0.587 * g + 0.114 * bVal;
      if (lumNew > 1e-5) {
        const ratio = lumOrig / lumNew;
        r = Math.min(1.0, Math.max(0.0, r * ratio));
        g = Math.min(1.0, Math.max(0.0, g * ratio));
        bVal = Math.min(1.0, Math.max(0.0, bVal * ratio));
      }
    }

    // B. Brightness with Soft Knee Headroom Compression
    if (b !== 0.0) {
      if (b > 0.0) {
        r += b * 0.35 * (1.0 - r * 0.5);
        g += b * 0.35 * (1.0 - g * 0.5);
        bVal += b * 0.35 * (1.0 - bVal * 0.5);
      } else {
        r += b * 0.35 * (0.5 + r * 0.5);
        g += b * 0.35 * (0.5 + g * 0.5);
        bVal += b * 0.35 * (0.5 + bVal * 0.5);
      }
      r = Math.min(1.0, Math.max(0.0, r));
      g = Math.min(1.0, Math.max(0.0, g));
      bVal = Math.min(1.0, Math.max(0.0, bVal));
    }

    // C. Shadows Boost & Highlights Recovery (Gaussian Roll-off)
    const lum = 0.299 * r + 0.587 * g + 0.114 * bVal;
    const lumIdx = (lum * 255.0 + 0.5) | 0;
    const clampIdx = lumIdx < 0 ? 0 : lumIdx > 255 ? 255 : lumIdx;

    if (sh !== 0.0) {
      const wSh = shadowWeightLut[clampIdx];
      if (sh > 0.0) {
        r += sh * 0.35 * wSh * (1.0 - r);
        g += sh * 0.35 * wSh * (1.0 - g);
        bVal += sh * 0.35 * wSh * (1.0 - bVal);
      } else {
        r += sh * 0.35 * wSh * r;
        g += sh * 0.35 * wSh * g;
        bVal += sh * 0.35 * wSh * bVal;
      }
    }

    if (hi !== 0.0) {
      const wHi = highlightWeightLut[clampIdx];
      if (hi < 0.0) {
        r += hi * 0.35 * wHi * r;
        g += hi * 0.35 * wHi * g;
        bVal += hi * 0.35 * wHi * bVal;
      } else {
        r += hi * 0.35 * wHi * (1.0 - r);
        g += hi * 0.35 * wHi * (1.0 - g);
        bVal += hi * 0.35 * wHi * (1.0 - bVal);
      }
    }
    r = Math.min(1.0, Math.max(0.0, r));
    g = Math.min(1.0, Math.max(0.0, g));
    bVal = Math.min(1.0, Math.max(0.0, bVal));

    // D. Contrast (Sigmoid S-Curve Table Lookup)
    if (c !== 0.0) {
      const rIdx = (r * 255.0 + 0.5) | 0;
      const gIdx = (g * 255.0 + 0.5) | 0;
      const bIdx = (bVal * 255.0 + 0.5) | 0;
      r = contrastLut[rIdx < 0 ? 0 : rIdx > 255 ? 255 : rIdx];
      g = contrastLut[gIdx < 0 ? 0 : gIdx > 255 ? 255 : gIdx];
      bVal = contrastLut[bIdx < 0 ? 0 : bIdx > 255 ? 255 : bIdx];
    }

    // E. Vibrance & Saturation
    if (s !== 0.0 || v !== 0.0) {
      const maxC = Math.max(r, g, bVal);
      const minC = Math.min(r, g, bVal);
      const curSat = maxC > 1e-5 ? (maxC - minC) / maxC : 0;
      const curLum = 0.299 * r + 0.587 * g + 0.114 * bVal;
      let satFactor = 1.0 + s;
      if (v !== 0.0) {
        satFactor += v * (1.0 - curSat) * 1.5;
      }
      r = Math.min(1.0, Math.max(0.0, curLum + (r - curLum) * satFactor));
      g = Math.min(1.0, Math.max(0.0, curLum + (g - curLum) * satFactor));
      bVal = Math.min(1.0, Math.max(0.0, curLum + (bVal - curLum) * satFactor));
    }

    // F. Global Hue & 8-Channel Selective HSL Mixer
    if (hasHsl) {
      const maxC = Math.max(r, g, bVal);
      const minC = Math.min(r, g, bVal);
      const diff = maxC - minC;
      let hVal = 0;
      let lVal = 0.5 * (maxC + minC);
      let sVal = 0;

      if (diff > 1e-5) {
        sVal = lVal > 0.5 ? diff / (2.0 - maxC - minC) : diff / (maxC + minC);
        if (maxC === r) {
          hVal = 60.0 * (((g - bVal) / diff) % 6);
        } else if (maxC === g) {
          hVal = 60.0 * (((bVal - r) / diff) + 2);
        } else {
          hVal = 60.0 * (((r - g) / diff) + 4);
        }
        hVal = (hVal + 360.0) % 360.0;
      }

      // Global Hue (safe floored modulo)
      if (globalHue !== 0.0) {
        hVal = ((hVal + globalHue) % 360.0 + 360.0) % 360.0;
      }

      // 8-Channel Selective adjustments
      if (activeChannels.length > 0) {
        const satGate = Math.min(1.0, Math.max(0.0, sVal / 0.10));
        let deltaH = 0, totalWH = 0;
        let deltaS = 0, totalWS = 0;
        let deltaL = 0, totalWL = 0;

        for (let j = 0; j < activeChannels.length; j++) {
          const ch = activeChannels[j];
          let dh = Math.abs(hVal - ch.center) % 360.0;
          dh = Math.min(dh, 360.0 - dh);
          const wChan = Math.exp(-(dh * dh) / 800.0) * satGate; // sigma=20, 2*sigma^2=800

          if (ch.hue !== 0) {
            deltaH += wChan * ch.hue;
            totalWH += wChan;
          }
          if (ch.sat !== 0) {
            deltaS += wChan * ch.sat;
            totalWS += wChan;
          }
          if (ch.light !== 0) {
            deltaL += wChan * ch.light;
            totalWL += wChan;
          }
        }

        if (totalWH > 1.0) deltaH /= totalWH;
        if (totalWS > 1.0) deltaS /= totalWS;
        if (totalWL > 1.0) deltaL /= totalWL;

        hVal = ((hVal + deltaH) % 360.0 + 360.0) % 360.0;

        if (deltaS > 0) sVal += deltaS * (1.0 - sVal);
        else if (deltaS < 0) sVal += deltaS * sVal;
        sVal = Math.min(1.0, Math.max(0.0, sVal));

        if (deltaL > 0) lVal += deltaL * (1.0 - lVal);
        else if (deltaL < 0) lVal += deltaL * lVal;
        lVal = Math.min(1.0, Math.max(0.0, lVal));
      }

      // Convert back HSL to RGB
      const cChroma = (1.0 - Math.abs(2.0 * lVal - 1.0)) * sVal;
      const hNorm = hVal / 60.0;
      const xChroma = cChroma * (1.0 - Math.abs((hNorm % 2.0) - 1.0));
      const mMatch = lVal - 0.5 * cChroma;

      let rH = 0, gH = 0, bH = 0;
      const hIdx = Math.floor(hNorm) % 6;
      if (hIdx === 0) { rH = cChroma; gH = xChroma; }
      else if (hIdx === 1) { rH = xChroma; gH = cChroma; }
      else if (hIdx === 2) { gH = cChroma; bH = xChroma; }
      else if (hIdx === 3) { gH = xChroma; bH = cChroma; }
      else if (hIdx === 4) { rH = xChroma; bH = cChroma; }
      else { rH = cChroma; bH = xChroma; }

      r = Math.min(1.0, Math.max(0.0, rH + mMatch));
      g = Math.min(1.0, Math.max(0.0, gH + mMatch));
      bVal = Math.min(1.0, Math.max(0.0, bH + mMatch));
    }

    const finalR = (r * 255.0 + 0.5) | 0;
    const finalG = (g * 255.0 + 0.5) | 0;
    const finalB = (bVal * 255.0 + 0.5) | 0;

    data[i] = finalR < 0 ? 0 : finalR > 255 ? 255 : finalR;
    data[i + 1] = finalG < 0 ? 0 : finalG > 255 ? 255 : finalG;
    data[i + 2] = finalB < 0 ? 0 : finalB > 255 ? 255 : finalB;

    // Histogram collection
    histR[data[i]]++;
    histG[data[i + 1]]++;
    histB[data[i + 2]]++;

    if (data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 0) {
      shadowClippedCount++;
    } else if (data[i] === 255 && data[i + 1] === 255 && data[i + 2] === 255) {
      highlightClippedCount++;
    }
  }

  // G. Fast Separable Clarity (Radius 3) & Sharpening (Radius 1) Pass
  if (cl !== 0.0 || sharp !== 0.0) {
    applyClarityAndSharpenImageData(imgData, w, h, cl, sharp);
  }

  // Draw to both canvases
  if (els.colorAdjustedCanvas) {
    const ctx = els.colorAdjustedCanvas.getContext("2d");
    ctx.putImageData(imgData, 0, 0);
  }

  if (els.curtainFgCanvas) {
    const ctx = els.curtainFgCanvas.getContext("2d");
    ctx.putImageData(imgData, 0, 0);
  }

  // Draw Live Histogram & Clipping Meter
  if (totalPixels === 0) totalPixels = len / 4;
  renderHistogram(histR, histG, histB, totalPixels, shadowClippedCount, highlightClippedCount);

  // Synchronize Live 3D Viewport with debouncing
  triggerLive3DViewportUpdate();
}

/**
 * Fast separable unsharp-mask filter in JavaScript for Clarity & Sharpening without halos
 */
function applyClarityAndSharpenImageData(imgData, w, h, cl, sharp) {
  const src = imgData.data;
  const nPixels = w * h;
  const rBuf = new Float32Array(nPixels);
  const gBuf = new Float32Array(nPixels);
  const bBuf = new Float32Array(nPixels);

  for (let i = 0, p = 0; i < nPixels; i++, p += 4) {
    rBuf[i] = src[p];
    gBuf[i] = src[p + 1];
    bBuf[i] = src[p + 2];
  }

  // Fast separable box blur helper (O(1) moving window)
  function blurChannel(input, radius) {
    const temp = new Float32Array(nPixels);
    const output = new Float32Array(nPixels);
    const winSize = radius * 2 + 1;
    const invWin = 1.0 / winSize;

    // Horizontal pass
    for (let y = 0; y < h; y++) {
      const row = y * w;
      let sum = 0;
      for (let k = -radius; k <= radius; k++) {
        sum += input[row + Math.max(0, Math.min(w - 1, k))];
      }
      for (let x = 0; x < w; x++) {
        temp[row + x] = sum * invWin;
        const left = row + Math.max(0, x - radius);
        const right = row + Math.min(w - 1, x + radius + 1);
        sum += input[right] - input[left];
      }
    }

    // Vertical pass
    for (let x = 0; x < w; x++) {
      let sum = 0;
      for (let k = -radius; k <= radius; k++) {
        sum += temp[Math.max(0, Math.min(h - 1, k)) * w + x];
      }
      for (let y = 0; y < h; y++) {
        output[y * w + x] = sum * invWin;
        const top = Math.max(0, y - radius) * w + x;
        const bottom = Math.min(h - 1, y + radius + 1) * w + x;
        sum += temp[bottom] - temp[top];
      }
    }
    return output;
  }

  let blurClR = null, blurClG = null, blurClB = null;
  if (cl !== 0.0) {
    blurClR = blurChannel(rBuf, 3);
    blurClG = blurChannel(gBuf, 3);
    blurClB = blurChannel(bBuf, 3);
  }

  let blurShR = null, blurShG = null, blurShB = null;
  if (sharp !== 0.0) {
    blurShR = blurChannel(rBuf, 1);
    blurShG = blurChannel(gBuf, 1);
    blurShB = blurChannel(bBuf, 1);
  }

  for (let idx = 0; idx < nPixels; idx++) {
    const p = idx * 4;
    if (src[p + 3] < 128) {
      continue;
    }

    let rOut = rBuf[idx];
    let gOut = gBuf[idx];
    let bOut = bBuf[idx];

    // Clarity: Mid-tone contrast with soft tanh compression (radius 3)
    if (cl !== 0.0) {
      const dR = (rBuf[idx] - blurClR[idx]) / 255.0;
      const dG = (gBuf[idx] - blurClG[idx]) / 255.0;
      const dB = (bBuf[idx] - blurClB[idx]) / 255.0;

      const lum = (0.299 * rBuf[idx] + 0.587 * gBuf[idx] + 0.114 * bBuf[idx]) / 255.0;
      const midtoneWeight = Math.max(0, Math.min(1, 4.0 * lum * (1.0 - lum)));

      const softDR = Math.tanh(dR * 2.5) / 2.5;
      const softDG = Math.tanh(dG * 2.5) / 2.5;
      const softDB = Math.tanh(dB * 2.5) / 2.5;

      rOut += softDR * (cl * 0.7) * midtoneWeight * 255.0;
      gOut += softDG * (cl * 0.7) * midtoneWeight * 255.0;
      bOut += softDB * (cl * 0.7) * midtoneWeight * 255.0;
    }

    // Sharpening: Fine detail unsharp mask with soft tanh compression (radius 1)
    if (sharp !== 0.0) {
      const fR = (rBuf[idx] - blurShR[idx]) / 255.0;
      const fG = (gBuf[idx] - blurShG[idx]) / 255.0;
      const fB = (bBuf[idx] - blurShB[idx]) / 255.0;

      const fineDR = Math.tanh(fR * 3.5) / 3.5;
      const fineDG = Math.tanh(fG * 3.5) / 3.5;
      const fineDB = Math.tanh(fB * 3.5) / 3.5;

      rOut += fineDR * (sharp * 0.8) * 255.0;
      gOut += fineDG * (sharp * 0.8) * 255.0;
      bOut += fineDB * (sharp * 0.8) * 255.0;
    }

    src[p] = Math.min(255, Math.max(0, Math.round(rOut)));
    src[p + 1] = Math.min(255, Math.max(0, Math.round(gOut)));
    src[p + 2] = Math.min(255, Math.max(0, Math.round(bOut)));
  }
}

/**
 * Draws real-time smooth RGB histogram and updates clipping indicators
 */
function renderHistogram(histR, histG, histB, totalPixels, shadowClipped, highlightClipped) {
  const canvas = els.colorHistogramCanvas;
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Find max peak in inner bins (ignore index 0 and 255 spikes for scaling)
  let maxBin = 1;
  for (let i = 1; i < 255; i++) {
    if (histR[i] > maxBin) maxBin = histR[i];
    if (histG[i] > maxBin) maxBin = histG[i];
    if (histB[i] > maxBin) maxBin = histB[i];
  }

  // Draw alpha-blended curves
  function drawChannelCurve(hist, color) {
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(0, h);
    for (let i = 0; i < 256; i++) {
      const x = (i / 255.0) * w;
      const val = Math.min(maxBin, hist[i]);
      const y = h - (val / maxBin) * (h - 4);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.globalAlpha = 0.18;
    ctx.fill();
    ctx.globalAlpha = 0.85;
    ctx.stroke();
  }

  ctx.globalCompositeOperation = "screen";
  drawChannelCurve(histR, "#ef4444");
  drawChannelCurve(histG, "#22c55e");
  drawChannelCurve(histB, "#3b82f6");
  ctx.globalCompositeOperation = "source-over";
  ctx.globalAlpha = 1.0;

  // Update clipping badges
  if (totalPixels > 0) {
    const shPct = ((shadowClipped / totalPixels) * 100).toFixed(1);
    const hiPct = ((highlightClipped / totalPixels) * 100).toFixed(1);

    if (els.shadowClipBadge) {
      els.shadowClipBadge.textContent = `Shadows: ${shPct}%`;
      els.shadowClipBadge.classList.toggle("clipped", parseFloat(shPct) > 1.0);
    }
    if (els.highlightClipBadge) {
      els.highlightClipBadge.textContent = `Highlights: ${hiPct}%`;
      els.highlightClipBadge.classList.toggle("clipped", parseFloat(hiPct) > 1.0);
    }
  }
}

/**
 * Debounced live 3D model synchronization
 */
function triggerLive3DViewportUpdate() {
  if (sync3dTimeout) clearTimeout(sync3dTimeout);
  sync3dTimeout = setTimeout(() => {
    if (state.colorStudio.targetIndex !== null && els.colorAdjustedCanvas) {
      eventBus.emit("color:textureUpdated", {
        textureIndex: state.colorStudio.targetIndex,
        canvas: els.colorAdjustedCanvas,
      });
    }
  }, 25);
}

async function applyColorGradingToModel() {
  if (state.colorStudio.targetIndex === null) {
    showToast("Please select a target texture first.", "error");
    return;
  }

  const tex = state.modelData.textures.find((t) => t.index === state.colorStudio.targetIndex);
  const texName = tex ? tex.name : "texture";

  showLoader("Quantizing and applying 256-color GoldSrc palette with selective HSL...");
  try {
    const payload = {
      team: state.currentTeam,
      weapon: state.currentWeapon,
      texture_index: state.colorStudio.targetIndex,
      ...state.colorStudio.params,
    };

    const res = await apiPost("/api/color_apply", payload);
    showToast(res.message, "success");

    // Reset sliders and HSL adjustments back to neutral since changes are now baked into the model
    applyColorPreset("neutral");
    resetAllHslChannels();

    const actionTeam = state.currentTeam;
    const actionWeapon = state.currentWeapon;

    // Record action for Undo/Redo stack
    eventBus.emit("history:record", {
      description: `Color Graded ${texName}`,
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
        await apiPost("/api/color_apply", payload);
      },
    });

    eventBus.emit("model:reloadRequest");
  } catch (err) {
    showToast(`Color grading failed: ${err.message}`, "error");
  } finally {
    hideLoader();
  }
}
