/**
 * modules/sticker_scraper_client.js - High-Performance Procedural Sticker Scraping Engine (Client)
 * 100% algorithmic parity with scripts/cs16_studio/sticker_scraper.py
 * Provides 60fps real-time sticker wear, edge peeling, and coin abrasion in the browser.
 */

// Simple deterministic PRNG (Mulberry32) for reproducible scratch and noise patterns
function createRng(seed = 1337) {
  let s = seed >>> 0;
  return function next() {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Scraped canvas cache to ensure 60fps slider scrubbing
const scrapeCache = new Map();
const MAX_CACHE_ENTRIES = 120;

/**
 * Returns descriptive condition tier name for sticker scrape level.
 */
export function getScrapeConditionName(scrapePercent) {
  const s = Math.max(0, Math.min(100, parseFloat(scrapePercent) || 0));
  if (s <= 5) return "Mint / Factory New (0%)";
  if (s <= 25) return "Light Scrape (25%)";
  if (s <= 50) return "Moderate Scrape (50%)";
  if (s <= 75) return "Heavy Scrape (75%)";
  return "Battle-Worn Scrape (100%)";
}

/**
 * Generates edge distance field from an alpha buffer using 3-tier morphological min-filter
 */
function computeEdgeDistance(alphaArr, w, h) {
  const size = w * h;
  const eroded1 = new Uint8Array(size);
  const eroded2 = new Uint8Array(size);
  const eroded3 = new Uint8Array(size);
  const edgeWear = new Float32Array(size);

  // Pass 1: 3x3 min filter on alphaArr -> eroded1
  for (let y = 0; y < h; y++) {
    const yStart = Math.max(0, y - 1);
    const yEnd = Math.min(h - 1, y + 1);
    for (let x = 0; x < w; x++) {
      const xStart = Math.max(0, x - 1);
      const xEnd = Math.min(w - 1, x + 1);
      let minVal = 255;
      for (let ny = yStart; ny <= yEnd; ny++) {
        const rowOff = ny * w;
        for (let nx = xStart; nx <= xEnd; nx++) {
          const v = alphaArr[rowOff + nx];
          if (v < minVal) minVal = v;
        }
      }
      eroded1[y * w + x] = minVal;
    }
  }

  // Pass 2: 3x3 min filter on eroded1 -> eroded2
  for (let y = 0; y < h; y++) {
    const yStart = Math.max(0, y - 1);
    const yEnd = Math.min(h - 1, y + 1);
    for (let x = 0; x < w; x++) {
      const xStart = Math.max(0, x - 1);
      const xEnd = Math.min(w - 1, x + 1);
      let minVal = 255;
      for (let ny = yStart; ny <= yEnd; ny++) {
        const rowOff = ny * w;
        for (let nx = xStart; nx <= xEnd; nx++) {
          const v = eroded1[rowOff + nx];
          if (v < minVal) minVal = v;
        }
      }
      eroded2[y * w + x] = minVal;
    }
  }

  // Pass 3: 3x3 min filter on eroded2 -> eroded3
  for (let y = 0; y < h; y++) {
    const yStart = Math.max(0, y - 1);
    const yEnd = Math.min(h - 1, y + 1);
    for (let x = 0; x < w; x++) {
      const xStart = Math.max(0, x - 1);
      const xEnd = Math.min(w - 1, x + 1);
      let minVal = 255;
      for (let ny = yStart; ny <= yEnd; ny++) {
        const rowOff = ny * w;
        for (let nx = xStart; nx <= xEnd; nx++) {
          const v = eroded2[rowOff + nx];
          if (v < minVal) minVal = v;
        }
      }
      eroded3[y * w + x] = minVal;
    }
  }

  // Edge wear combination: (orig - eroded1)*1.5 + (orig - eroded2)*1.0 + (orig - eroded3)*0.7
  for (let i = 0; i < size; i++) {
    const orig = alphaArr[i];
    const d1 = (orig - eroded1[i]) / 255.0;
    const d2 = (orig - eroded2[i]) / 255.0;
    const d3 = (orig - eroded3[i]) / 255.0;
    const val = d1 * 1.5 + d2 * 1.0 + d3 * 0.7;
    edgeWear[i] = val < 0 ? 0 : val > 1.0 ? 1.0 : val;
  }

  return edgeWear;
}

/**
 * Generates procedural noise & scratch lines matching Python generate_scrape_mask
 */
function generateScrapeMask(w, h, ratio, seed = 1337) {
  const size = w * h;
  const mask = new Float32Array(size);
  if (ratio <= 0.001) return mask;

  const rng = createRng(seed);

  // 1. Multi-scale noise pitting
  const scaleC = Math.max(4, Math.floor(Math.min(w, h) / 8));
  const cw = Math.max(4, Math.floor(w / scaleC));
  const ch = Math.max(4, Math.floor(h / scaleC));
  const coarseGrid = new Float32Array(cw * ch);
  for (let i = 0; i < coarseGrid.length; i++) coarseGrid[i] = rng();

  const scaleM = Math.max(2, Math.floor(Math.min(w, h) / 16));
  const mw = Math.max(4, Math.floor(w / scaleM));
  const mh = Math.max(4, Math.floor(h / scaleM));
  const medGrid = new Float32Array(mw * mh);
  for (let i = 0; i < medGrid.length; i++) medGrid[i] = rng();

  // 2. Offscreen canvas for procedural scratch lines
  const scratchCanvas = document.createElement("canvas");
  scratchCanvas.width = w;
  scratchCanvas.height = h;
  const sCtx = scratchCanvas.getContext("2d");
  sCtx.fillStyle = "#000000";
  sCtx.fillRect(0, 0, w, h);

  const numScratches = Math.floor(ratio * 85);
  sCtx.strokeStyle = "#ffffff";
  sCtx.lineCap = "round";

  for (let i = 0; i < numScratches; i++) {
    const x1 = rng() * w;
    const y1 = rng() * h;
    const maxLen = Math.max(12, Math.min(w, h) * 0.45);
    const len = 8 + rng() * (maxLen - 8);
    const angle = (rng() * 2 - 1) * Math.PI;
    const x2 = x1 + len * Math.cos(angle);
    const y2 = y1 + len * Math.sin(angle);
    const lineWidth = 1 + Math.floor(rng() * 2);
    const alphaVal = 0.7 + rng() * 0.3;

    sCtx.lineWidth = lineWidth;
    sCtx.strokeStyle = `rgba(255, 255, 255, ${alphaVal})`;
    sCtx.beginPath();
    sCtx.moveTo(x1, y1);
    sCtx.lineTo(x2, y2);
    sCtx.stroke();
  }

  const scratchData = sCtx.getImageData(0, 0, w, h).data;

  // 3. Bilinear sample noise grids and combine with scratch lines
  for (let y = 0; y < h; y++) {
    const vC = (y / h) * (ch - 1);
    const yC0 = Math.floor(vC);
    const yC1 = Math.min(ch - 1, yC0 + 1);
    const fvC = vC - yC0;

    const vM = (y / h) * (mh - 1);
    const yM0 = Math.floor(vM);
    const yM1 = Math.min(mh - 1, yM0 + 1);
    const fvM = vM - yM0;

    const rowIdx = y * w;

    for (let x = 0; x < w; x++) {
      const uC = (x / w) * (cw - 1);
      const xC0 = Math.floor(uC);
      const xC1 = Math.min(cw - 1, xC0 + 1);
      const fuC = uC - xC0;

      const nC =
        (coarseGrid[yC0 * cw + xC0] * (1 - fuC) + coarseGrid[yC0 * cw + xC1] * fuC) * (1 - fvC) +
        (coarseGrid[yC1 * cw + xC0] * (1 - fuC) + coarseGrid[yC1 * cw + xC1] * fuC) * fvC;

      const uM = (x / w) * (mw - 1);
      const xM0 = Math.floor(uM);
      const xM1 = Math.min(mw - 1, xM0 + 1);
      const fuM = uM - xM0;

      const nM =
        (medGrid[yM0 * mw + xM0] * (1 - fuM) + medGrid[yM0 * mw + xM1] * fuM) * (1 - fvM) +
        (medGrid[yM1 * mw + xM0] * (1 - fuM) + medGrid[yM1 * mw + xM1] * fuM) * fvM;

      const noiseVal = nC * 0.6 + nM * 0.4;
      const scratchVal = scratchData[(rowIdx + x) * 4] / 255.0;

      const combined = noiseVal * 0.55 + scratchVal * 0.45;
      mask[rowIdx + x] = combined < 0 ? 0 : combined > 1 ? 1 : combined;
    }
  }

  return mask;
}

/**
 * Applies procedural scraping to an Image, Canvas, or ImageBitmap.
 * Returns a HTMLCanvasElement containing the scraped sticker.
 *
 * @param {HTMLImageElement|HTMLCanvasElement} sourceImg
 * @param {number} scrapePercent - Value between 0 and 100 (or 0.0 and 1.0)
 * @param {number} seed - Deterministic PRNG seed (default 1337)
 * @param {string} cacheKey - Optional cache identifier for instant retrieval
 * @returns {HTMLCanvasElement}
 */
export function getScrapedStickerCanvas(sourceImg, scrapePercent = 0, seed = 1337, cacheKey = "") {
  if (!sourceImg) return null;

  const w = sourceImg.width || sourceImg.naturalWidth || 256;
  const h = sourceImg.height || sourceImg.naturalHeight || 256;
  if (w <= 0 || h <= 0) return sourceImg;

  let ratio = parseFloat(scrapePercent) || 0.0;
  if (ratio > 1.0) ratio = ratio / 100.0;
  ratio = Math.max(0.0, Math.min(1.0, ratio));

  // Quick return for pristine mint condition (0%)
  if (ratio <= 0.001) {
    if (sourceImg instanceof HTMLCanvasElement) return sourceImg;
    const mintCanvas = document.createElement("canvas");
    mintCanvas.width = w;
    mintCanvas.height = h;
    const ctx = mintCanvas.getContext("2d");
    ctx.drawImage(sourceImg, 0, 0, w, h);
    return mintCanvas;
  }

  // Check cache
  const normalizedKey = cacheKey ? `${cacheKey}_${Math.round(ratio * 100)}_${seed}` : null;
  if (normalizedKey && scrapeCache.has(normalizedKey)) {
    return scrapeCache.get(normalizedKey);
  }

  // Draw source image onto helper canvas to extract pixel data
  const srcCanvas = document.createElement("canvas");
  srcCanvas.width = w;
  srcCanvas.height = h;
  const srcCtx = srcCanvas.getContext("2d");
  srcCtx.drawImage(sourceImg, 0, 0, w, h);

  const imgData = srcCtx.getImageData(0, 0, w, h);
  const data = imgData.data;
  const size = w * h;

  // Extract alpha channel
  const alphaArr = new Uint8Array(size);
  let maxAlpha = 0;
  for (let i = 0; i < size; i++) {
    const a = data[i * 4 + 3];
    alphaArr[i] = a;
    if (a > maxAlpha) maxAlpha = a;
  }

  if (maxAlpha < 1) {
    return srcCanvas;
  }

  // 1. Compute edge distance erosion
  const edgeWear = computeEdgeDistance(alphaArr, w, h);

  // 2. Generate procedural noise and scratch mask
  const noiseMask = generateScrapeMask(w, h, ratio, seed);

  // 3. Combined erosion field
  // Threshold curve matching sticker_scraper.py
  const threshold = 1.08 - ratio * 0.88;
  const softness = Math.max(0.01, 0.2 - ratio * 0.1);

  // Paper backing color: [225, 225, 220]
  const paperR = 225;
  const paperG = 225;
  const paperB = 220;

  for (let i = 0; i < size; i++) {
    const origAlpha = alphaArr[i];
    if (origAlpha === 0) continue;

    const eField = edgeWear[i] * (0.35 + ratio * 0.65) + noiseMask[i] * (0.65 + ratio * 0.35);

    let wearFactor = (eField - threshold) / softness;
    if (wearFactor < 0) wearFactor = 0;
    else if (wearFactor > 1) wearFactor = 1;

    // New eroded alpha
    const newAlpha = Math.round(origAlpha * (1.0 - wearFactor));
    const pIdx = i * 4;
    data[pIdx + 3] = newAlpha;

    if (newAlpha > 0) {
      const r = data[pIdx];
      const g = data[pIdx + 1];
      const b = data[pIdx + 2];

      // Luminance desaturation
      const lum = 0.299 * r + 0.587 * g + 0.114 * b;
      const desatR = lum * 0.4 + r * 0.6;
      const desatG = lum * 0.4 + g * 0.6;
      const desatB = lum * 0.4 + b * 0.6;

      // Paper backing fringe visible where wearFactor is around 0.3 - 0.8
      let paperFringe = 1.0 - Math.abs(wearFactor - 0.55) / 0.35;
      if (paperFringe < 0) paperFringe = 0;
      else if (paperFringe > 1) paperFringe = 1;

      const f = paperFringe * 0.5;
      data[pIdx] = Math.round(desatR * (1.0 - f) + paperR * f);
      data[pIdx + 1] = Math.round(desatG * (1.0 - f) + paperG * f);
      data[pIdx + 2] = Math.round(desatB * (1.0 - f) + paperB * f);
    }
  }

  // Write back to canvas
  srcCtx.putImageData(imgData, 0, 0);

  // Manage cache size
  if (normalizedKey) {
    if (scrapeCache.size >= MAX_CACHE_ENTRIES) {
      const oldestKey = scrapeCache.keys().next().value;
      scrapeCache.delete(oldestKey);
    }
    scrapeCache.set(normalizedKey, srcCanvas);
  }

  return srcCanvas;
}
