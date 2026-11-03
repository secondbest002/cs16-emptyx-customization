/**
 * core/state.js - Reactive global application state & event bus
 * CS 1.6 Asset Studio Pro Modular Architecture
 */

// Event Bus implementation for decoupled component communication
class EventBus {
  constructor() {
    this.events = {};
  }

  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (!this.events[event]) return;
    this.events[event] = this.events[event].filter((cb) => cb !== callback);
  }

  emit(event, data) {
    if (!this.events[event]) return;
    this.events[event].forEach((callback) => {
      try {
        callback(data);
      } catch (err) {
        console.error(`[EventBus] Error in listener for "${event}":`, err);
      }
    });
  }
}

export const eventBus = new EventBus();

// Global Application State
export const state = {
  currentTeam: "ct",
  currentWeapon: "usp",
  availableModels: { ct: [], t: [], all: [] },
  amxxCatalog: null,
  activeLoadout: { ct: {}, t: {} },
  modelData: null,
  activeFilter: "all",
  pendingSlotUpdates: {}, // index -> { file, base64, previewUri, mode, scale }

  // WYSIWYG Bake State
  bake: {
    stickerBase64: null,
    stickerPath: null,
    preset: "center",
    scale: 1.0,
    rotation: 0,
    scrape: 0,
    fx: "matte",
    x: 200,
    y: 180,
    isDragging: false,
    baseImg: null,
    stickerImg: null,
  },

  // Color Studio State
  colorStudio: {
    targetIndex: null,
    origImg: null,
    params: {
      brightness: 0,
      contrast: 0,
      saturation: 0,
      vibrance: 0,
      clarity: 0,
      shadows: 0,
      highlights: 0,
      temperature: 0,
      tint: 0,
      hue: 0,
      sharpen: 0,
      hsl_adjustments: {
        red: { hue: 0, saturation: 0, lightness: 0 },
        orange: { hue: 0, saturation: 0, lightness: 0 },
        yellow: { hue: 0, saturation: 0, lightness: 0 },
        green: { hue: 0, saturation: 0, lightness: 0 },
        cyan: { hue: 0, saturation: 0, lightness: 0 },
        blue: { hue: 0, saturation: 0, lightness: 0 },
        purple: { hue: 0, saturation: 0, lightness: 0 },
        magenta: { hue: 0, saturation: 0, lightness: 0 },
      },
    },
    activeHslChannel: "yellow",
    isEyedropperActive: false,
  },

  // Slot Sticker Scale & Fine-Tuner Modal State
  slotTune: {
    texture: null,
    stickerImg: null,
    stickerDataUri: null,
    scale: 1.0,
    offsetX: 0,
    offsetY: 0,
    rotation: 0,
    mode: "fit",
    scrape: 0,
  },

  // 3D Viewport State
  viewport3d: {
    initialized: false,
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    meshGroup: null,
    materialsByTexIndex: {},
    isWireframe: false,
    autoRotate: false,
    chromeShine: false,
    weaponOnly: false,
    showGloves: true,
    highlightStickers: false,
    repositionMode: false,
    repositionSlot: null,
    pulsingMesh: null,
    snapshotTransparent: true,
    currentBounds: null,
    currentWeaponBounds: null,
    animFrameId: null,
    currentMode: "orbit", // 'orbit', 'fpv', 'showcase'
    povConfig: { offset_x: 0.0, offset_y: 0.0, offset_z: 0.0, sway: 1.0 },
    inspectActive: false,
    inspectStartTime: 0,
  },

  // Library State
  libraryItems: [],
  libraryStickers: [],
  librarySkins: [],
  activeLibraryCat: "all",
  librarySearch: "",
  targetModalSlot: null,
  modalTargetDestination: "slot", // "slot", "bake", "slotTune"

  // Pro Tools State
  pro: {
    activeTab: "stattrak",
    stattrakColor: "orange",
    wearFloat: 0.35,
  },

  // QoL Features State
  qol: {
    undoStack: [],
    redoStack: [],
    curtainPercent: 50,
    isCurtainDragging: false,
    compareMode: "curtain", // 'curtain' or 'side'
    sampledColor: null,
    quickSearchTerm: "",
    selectedQuickIndex: 0,
  },
};
