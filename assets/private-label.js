/* Achti: konfigurator Private Label (zapytanie o wycenę).
   Kroki: model -> kolory i ilości -> znakowanie -> logo z podglądem -> dane firmy.
   Podgląd: wykrywanie obrysu czapki, pozycje względem czapki, wtapianie logo w dzianinę
   (mnożenie + odkształcenie po splocie + krzywizna), tekstura haftu, czyszczenie tła logo,
   warianty biały/czarny, pasek podglądów na wszystkich wybranych kolorach. */

const PL_CANVAS_W = 600;
const PL_CANVAS_H = 750;

/* ---------- narzędzia obrazowe ---------- */
const plImg = {
  /* obrys czapki na białym tle (bbox nie-białych pikseli) + mapa jasności w małej skali */
  analyzeHat(img) {
    const w = 120;
    const h = Math.max(1, Math.round((img.height / img.width) * w));
    const c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    const x = c.getContext('2d', { willReadFrequently: true });
    x.drawImage(img, 0, 0, w, h);
    let data;
    try {
      data = x.getImageData(0, 0, w, h).data;
    } catch (e) {
      return { box: { x: 0.1, y: 0.05, w: 0.8, h: 0.9 }, tainted: true };
    }
    let minX = w, minY = h, maxX = -1, maxY = -1;
    for (let j = 0; j < h; j += 1) {
      for (let i = 0; i < w; i += 1) {
        const k = (j * w + i) * 4;
        const a = data[k + 3];
        const lum = (data[k] + data[k + 1] + data[k + 2]) / 3;
        if (a > 40 && lum < 238) {
          if (i < minX) minX = i;
          if (i > maxX) maxX = i;
          if (j < minY) minY = j;
          if (j > maxY) maxY = j;
        }
      }
    }
    if (maxX < 0) return { box: { x: 0.1, y: 0.05, w: 0.8, h: 0.9 }, tainted: false };
    return {
      box: { x: minX / w, y: minY / h, w: (maxX - minX + 1) / w, h: (maxY - minY + 1) / h },
      tainted: false,
    };
  },

  /* usuwa białe tło (zalewanie od krawędzi) z logo bez przezroczystości; zwraca {canvas, cleaned} */
  cleanLogo(img) {
    const maxSide = 900;
    const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    const x = c.getContext('2d', { willReadFrequently: true });
    x.drawImage(img, 0, 0, w, h);
    let id;
    try {
      id = x.getImageData(0, 0, w, h);
    } catch (e) {
      return { canvas: c, cleaned: false };
    }
    const d = id.data;
    let transparent = 0;
    for (let k = 3; k < d.length; k += 4) if (d[k] < 250) transparent += 1;
    if (transparent > d.length / 4 * 0.02) return { canvas: c, cleaned: false }; // już ma przezroczystość
    const isWhite = (k) => d[k] > 235 && d[k + 1] > 235 && d[k + 2] > 235;
    const visited = new Uint8Array(w * h);
    const stack = [];
    const push = (i, j) => {
      if (i < 0 || j < 0 || i >= w || j >= h) return;
      const p = j * w + i;
      if (visited[p]) return;
      visited[p] = 1;
      if (isWhite(p * 4)) stack.push(p);
    };
    for (let i = 0; i < w; i += 1) { push(i, 0); push(i, h - 1); }
    for (let j = 0; j < h; j += 1) { push(0, j); push(w - 1, j); }
    let removed = 0;
    while (stack.length) {
      const p = stack.pop();
      const i = p % w;
      const j = (p - i) / w;
      d[p * 4 + 3] = 0;
      removed += 1;
      push(i + 1, j); push(i - 1, j); push(i, j + 1); push(i, j - 1);
    }
    if (!removed) return { canvas: c, cleaned: false };
    /* wygładzenie krawędzi: półprzezroczystość dla jasnych pikseli przy krawędzi */
    for (let j = 1; j < h - 1; j += 1) {
      for (let i = 1; i < w - 1; i += 1) {
        const p = j * w + i;
        if (d[p * 4 + 3] === 0) continue;
        const n = [p - 1, p + 1, p - w, p + w].filter((q) => d[q * 4 + 3] === 0).length;
        if (n) {
          const lum = (d[p * 4] + d[p * 4 + 1] + d[p * 4 + 2]) / 3;
          d[p * 4 + 3] = Math.round(255 * Math.min(1, (255 - lum) / 120));
        }
      }
    }
    x.putImageData(id, 0, 0);
    return { canvas: c, cleaned: true };
  },

  /* wariant koloru logo: 'white' / 'black' = sylwetka w jednym kolorze, 'original' = bez zmian */
  recolor(srcCanvas, variant) {
    if (variant === 'original') return srcCanvas;
    const c = document.createElement('canvas');
    c.width = srcCanvas.width;
    c.height = srcCanvas.height;
    const x = c.getContext('2d');
    x.drawImage(srcCanvas, 0, 0);
    x.globalCompositeOperation = 'source-in';
    x.fillStyle = variant === 'white' ? '#f6f6f6' : '#141414';
    x.fillRect(0, 0, c.width, c.height);
    return c;
  },

  /* średnia jasność nieprzezroczystych pikseli */
  meanLum(canvas) {
    const x = canvas.getContext('2d', { willReadFrequently: true });
    let d;
    try {
      d = x.getImageData(0, 0, canvas.width, canvas.height).data;
    } catch (e) {
      return 128;
    }
    let sum = 0, n = 0;
    for (let k = 0; k < d.length; k += 16) {
      if (d[k + 3] > 60) { sum += (d[k] * 0.3 + d[k + 1] * 0.59 + d[k + 2] * 0.11); n += 1; }
    }
    return n ? sum / n : 128;
  },

  /* udział nieprzezroczystych pikseli logo o jasności zbliżonej do tła (słaby kontrast) */
  lowContrastRatio(canvas, bgLum, tol) {
    const x = canvas.getContext('2d', { willReadFrequently: true });
    let d;
    try {
      d = x.getImageData(0, 0, canvas.width, canvas.height).data;
    } catch (e) {
      return 0;
    }
    let low = 0, n = 0;
    for (let k = 0; k < d.length; k += 16) {
      if (d[k + 3] > 60) {
        const lum = d[k] * 0.3 + d[k + 1] * 0.59 + d[k + 2] * 0.11;
        if (Math.abs(lum - bgLum) < tol) low += 1;
        n += 1;
      }
    }
    return n ? low / n : 0;
  },

  /* wzór ściegów haftu */
  stitchPattern(ctx) {
    if (plImg._stitch) return plImg._stitch;
    const c = document.createElement('canvas');
    c.width = 6;
    c.height = 6;
    const x = c.getContext('2d');
    x.strokeStyle = 'rgba(0,0,0,0.28)';
    x.lineWidth = 1;
    x.beginPath(); x.moveTo(0, 6); x.lineTo(6, 0); x.stroke();
    x.strokeStyle = 'rgba(255,255,255,0.22)';
    x.beginPath(); x.moveTo(0, 4); x.lineTo(4, 0); x.stroke();
    plImg._stitch = ctx.createPattern(c, 'repeat');
    return plImg._stitch;
  },
};

/* ---------- renderer sceny (czapka + logo) ---------- */
function plRenderScene(target, scene) {
  const { hat, hatBox, logo, pos, effect, tainted } = scene;
  const W = target.width;
  const H = target.height;
  const ctx = target.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, H);
  if (!hat) return null;

  const scale = Math.min(W / hat.width, H / hat.height);
  const dw = hat.width * scale;
  const dh = hat.height * scale;
  const dx = (W - dw) / 2;
  const dy = (H - dh) / 2;
  ctx.drawImage(hat, dx, dy, dw, dh);

  /* obrys czapki w pikselach canvasu */
  const box = { x: dx + hatBox.x * dw, y: dy + hatBox.y * dh, w: hatBox.w * dw, h: hatBox.h * dh };
  if (!logo) return box;

  const lw = box.w * pos.w;
  const lh = lw * (logo.height / logo.width);
  const cx = box.x + pos.x * box.w;
  const cy = box.y + pos.y * box.h;

  /* warstwa logo (płaska, obrócona) */
  const layer = document.createElement('canvas');
  layer.width = W;
  layer.height = H;
  const lx = layer.getContext('2d', { willReadFrequently: true });
  lx.translate(cx, cy);
  lx.rotate((pos.rot * Math.PI) / 180);
  lx.drawImage(logo, -lw / 2, -lh / 2, lw, lh);
  lx.setTransform(1, 0, 0, 1, 0, 0);

  const r = Math.hypot(lw, lh) / 2 + 6;
  const rx0 = Math.max(0, Math.floor(cx - r));
  const ry0 = Math.max(0, Math.floor(cy - r));
  const rx1 = Math.min(W, Math.ceil(cx + r));
  const ry1 = Math.min(H, Math.ceil(cy + r));
  const rw = rx1 - rx0;
  const rh = ry1 - ry0;
  if (rw <= 0 || rh <= 0) return box;

  let warped = layer;
  if (!tainted) {
    try {
      /* jasność zdjęcia pod logo (rozmyta) -> odkształcenie po splocie + krzywizna walca */
      const lum = ctx.getImageData(rx0, ry0, rw, rh).data;
      const src = lx.getImageData(rx0, ry0, rw, rh).data;
      const out = new Uint8ClampedArray(src.length);
      const L = new Float32Array(rw * rh);
      for (let p = 0; p < rw * rh; p += 1) L[p] = lum[p * 4] * 0.3 + lum[p * 4 + 1] * 0.59 + lum[p * 4 + 2] * 0.11;
      /* lekkie rozmycie 3x3 */
      const B = new Float32Array(rw * rh);
      for (let j = 1; j < rh - 1; j += 1) {
        for (let i = 1; i < rw - 1; i += 1) {
          const p = j * rw + i;
          B[p] = (L[p - rw - 1] + L[p - rw] + L[p - rw + 1] + L[p - 1] + L[p] + L[p + 1] + L[p + rw - 1] + L[p + rw] + L[p + rw + 1]) / 9;
        }
      }
      const amp = Math.max(1.2, lw / 120); // siła odkształcenia w px
      const hatCx = box.x + box.w / 2;
      const R = box.w * 0.55; // promień walca (czapka)
      for (let j = 0; j < rh; j += 1) {
        for (let i = 0; i < rw; i += 1) {
          const p = j * rw + i;
          const X = rx0 + i;
          /* krzywizna: piksel widoczny w X pochodzi z płaskiego X' rozciągniętego od środka czapki */
          const u = Math.max(-0.999, Math.min(0.999, (X - hatCx) / R));
          const flatX = hatCx + Math.asin(u) * R;
          const uc = Math.max(-0.999, Math.min(0.999, (cx - hatCx) / R));
          const flatCx = hatCx + Math.asin(uc) * R;
          let sx = cx + (flatX - flatCx) - rx0;
          let sy = j;
          /* odkształcenie po splocie: gradient jasności */
          if (i > 0 && i < rw - 1 && j > 0 && j < rh - 1) {
            sx += ((B[p + 1] - B[p - 1]) / 255) * amp * 2;
            sy += ((B[p + rw] - B[p - rw]) / 255) * amp * 2;
          }
          const si = Math.round(sx);
          const sj = Math.round(sy);
          if (si < 0 || sj < 0 || si >= rw || sj >= rh) continue;
          const q = (sj * rw + si) * 4;
          const o = p * 4;
          const a = src[q + 3];
          if (!a) continue;
          /* cieniowanie dzianiną: mnożenie przez jasność zdjęcia (z podbiciem kontrastu) */
          const shade = Math.min(1.15, Math.max(0.45, 0.35 + (B[p] / 255) * 0.9));
          out[o] = Math.min(255, src[q] * shade);
          out[o + 1] = Math.min(255, src[q + 1] * shade);
          out[o + 2] = Math.min(255, src[q + 2] * shade);
          out[o + 3] = a;
        }
      }
      warped = document.createElement('canvas');
      warped.width = W;
      warped.height = H;
      const wx = warped.getContext('2d');
      wx.putImageData(new ImageData(out, rw, rh), rx0, ry0);
      /* nieostry brzeg wtopiony w dzianinę */
      const soft = document.createElement('canvas');
      soft.width = W;
      soft.height = H;
      const sx2 = soft.getContext('2d');
      sx2.filter = 'blur(0.6px)';
      sx2.drawImage(warped, 0, 0);
      warped = soft;
    } catch (e) {
      warped = layer;
    }
  }

  /* cień nici / grubość */
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.35)';
  ctx.shadowBlur = 2;
  ctx.shadowOffsetX = 0.6;
  ctx.shadowOffsetY = 1;
  ctx.globalAlpha = 0.97;
  ctx.drawImage(warped, 0, 0);
  ctx.restore();

  /* haft: ściegi tylko w obrębie logo */
  if (effect === 'stitch') {
    const mask = document.createElement('canvas');
    mask.width = W;
    mask.height = H;
    const mx = mask.getContext('2d');
    mx.drawImage(warped, 0, 0);
    mx.globalCompositeOperation = 'source-in';
    mx.fillStyle = plImg.stitchPattern(mx);
    mx.fillRect(rx0, ry0, rw, rh);
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.drawImage(mask, 0, 0);
    ctx.restore();
  }
  return box;
}

class PrivateLabelConfigurator extends HTMLElement {
  connectedCallback() {
    const dataEl = this.querySelector('[data-pl-data]');
    if (!dataEl) return;
    try {
      this.products = JSON.parse(dataEl.textContent || '[]');
    } catch (e) {
      this.products = [];
    }
    this.t = JSON.parse(this.dataset.strings || '{}');
    this.placements = JSON.parse(this.dataset.placements || '{}');
    this.minQty = Number(this.dataset.minQty) || 50;
    this.state = {
      product: null,
      previewColor: null,
      colors: new Map(),
      branding: null,
      brandingDesc: '',
      placement: null,
      logoName: '',
      logoSource: null, // canvas z oczyszczonym logo
      logoVariant: 'original',
      noLogo: false,
      pos: { x: 0.5, y: 0.58, w: 0.34, rot: 0 },
    };
    this.hatCache = new Map(); // url -> {img, box, tainted}
    this.$ = (sel) => this.querySelector(sel);
    this.$$ = (sel) => Array.from(this.querySelectorAll(sel));

    this.modelGrid = this.$('[data-pl-models]');
    this.colorList = this.$('[data-pl-colors]');
    this.qtyList = this.$('[data-pl-qty-list]');
    this.canvas = this.$('[data-pl-canvas]');
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.form = this.$('form');

    this.renderModels();
    this.bindBranding();
    this.bindLogo();
    this.bindForm();
    this.bindNav();
    this.refresh();
  }

  get logo() {
    if (!this.state.logoSource) return null;
    if (!this._logoCache || this._logoCache.variant !== this.state.logoVariant || this._logoCache.src !== this.state.logoSource) {
      this._logoCache = { variant: this.state.logoVariant, src: this.state.logoSource, canvas: plImg.recolor(this.state.logoSource, this.state.logoVariant) };
    }
    return this._logoCache.canvas;
  }

  get effect() {
    const b = (this.state.branding || '').toLowerCase();
    return b.includes('haft') || b.includes('embroid') || b.includes('stick') || b.includes('brod') ? 'stitch' : 'print';
  }

  /* ---------- nawigacja / stan kroków ---------- */
  bindNav() {
    this.$$('[data-pl-goto]').forEach((btn) =>
      btn.addEventListener('click', () => {
        const step = this.$(`[data-pl-step="${btn.dataset.plGoto}"]`);
        if (step && !step.hidden) step.scrollIntoView({ block: 'start', behavior: 'smooth' });
      })
    );
  }

  unlock(name) {
    const step = this.$(`[data-pl-step="${name}"]`);
    if (step && step.hidden) step.hidden = false;
    return step;
  }

  setDone(name, done) {
    const step = this.$(`[data-pl-step="${name}"]`);
    if (step) step.classList.toggle('pl-step--done', Boolean(done));
  }

  totalQty() {
    let sum = 0;
    this.state.colors.forEach((c) => (sum += Number(c.qty) || 0));
    return sum;
  }

  /* ---------- krok 1: model ---------- */
  renderModels() {
    if (!this.modelGrid) return;
    this.modelGrid.innerHTML = this.products
      .map(
        (p, i) => `
      <button type="button" class="pl-tile" data-index="${i}" aria-pressed="false">
        <span class="pl-tile__media">${p.image ? `<img src="${p.image}" alt="" width="300" height="375" loading="lazy">` : ''}</span>
        <span class="pl-tile__title">${this.esc(p.title)}</span>
        <span class="pl-tile__meta">${this.esc(p.sku || '')}${p.colors.length > 1 ? ` · ${this.t.colors_count.replace('{{ count }}', p.colors.length)}` : ''}</span>
      </button>`
      )
      .join('');
    this.modelGrid.addEventListener('click', (e) => {
      const tile = e.target.closest('.pl-tile');
      if (!tile) return;
      this.selectModel(this.products[Number(tile.dataset.index)], tile);
    });
  }

  selectModel(product, tile) {
    if (this.state.product === product) return;
    this.state.product = product;
    this.state.colors = new Map();
    this.$$('.pl-tile').forEach((t) => t.setAttribute('aria-pressed', String(t === tile)));
    this.renderColors(product);
    this.toggleColor(product.colors[0], true);
    this.setDone('model', true);
    const next = this.unlock('colors');
    if (next) next.scrollIntoView({ block: 'start', behavior: 'smooth' });
    this.refresh();
  }

  /* ---------- krok 2: kolory i ilości ---------- */
  renderColors(product) {
    this.colorList.innerHTML = product.colors
      .map(
        (c, i) => `
      <li class="model-colors__item">
        <button type="button" class="model-colors__circle pl-color" data-index="${i}" title="${this.esc(c.title)}" aria-pressed="false">
          ${c.image ? `<img src="${c.image}" alt="${this.esc(c.title)}" width="80" height="80" loading="lazy">` : ''}
        </button>
      </li>`
      )
      .join('');
    this.colorList.onclick = (e) => {
      const btn = e.target.closest('.pl-color');
      if (!btn) return;
      this.toggleColor(product.colors[Number(btn.dataset.index)]);
    };
  }

  toggleColor(color, force) {
    const key = color.title;
    if (this.state.colors.has(key) && force !== true) {
      if (this.state.colors.size === 1) {
        this.setPreviewColor(color);
        return;
      }
      this.state.colors.delete(key);
      if (this.state.previewColor === color) this.setPreviewColor(this.state.colors.values().next().value.color);
    } else if (!this.state.colors.has(key)) {
      this.state.colors.set(key, { color, qty: this.minQty });
      this.setPreviewColor(color);
    } else {
      this.setPreviewColor(color);
    }
    this.renderQtyList();
    this.refresh();
  }

  setPreviewColor(color) {
    this.state.previewColor = color;
    this.loadHat(color.image).then(() => this.draw());
  }

  renderQtyList() {
    this.$$('.pl-color').forEach((b) => {
      b.setAttribute('aria-pressed', String(this.state.colors.has(b.title)));
      b.classList.toggle('pl-color--preview', this.state.previewColor && b.title === this.state.previewColor.title);
    });
    const rows = [];
    this.state.colors.forEach(({ color, qty }, key) => {
      rows.push(`
        <div class="pl-qty-row${this.state.previewColor === color ? ' pl-qty-row--preview' : ''}" data-key="${this.esc(key)}">
          <button type="button" class="pl-qty-row__swatch" data-preview="${this.esc(key)}" title="${this.esc(this.t.show_on_preview)}">
            ${color.image ? `<img src="${color.image}" alt="" width="48" height="48">` : ''}
          </button>
          <span class="pl-qty-row__name">${this.esc(color.title)}<small>${this.esc(color.sku || '')}</small></span>
          <label class="pl-qty-row__qty">
            <span class="visually-hidden">${this.esc(this.t.qty)}</span>
            <input type="number" min="1" step="1" value="${qty}" data-qty="${this.esc(key)}" inputmode="numeric">
          </label>
          <button type="button" class="pl-qty-row__remove" data-remove="${this.esc(key)}" aria-label="${this.esc(this.t.remove)}">&times;</button>
        </div>`);
    });
    this.qtyList.innerHTML = rows.join('');
    this.qtyList.querySelectorAll('[data-qty]').forEach((input) =>
      input.addEventListener('input', () => {
        const entry = this.state.colors.get(input.dataset.qty);
        if (entry) entry.qty = Math.max(0, parseInt(input.value, 10) || 0);
        this.refresh();
      })
    );
    this.qtyList.querySelectorAll('[data-remove]').forEach((btn) =>
      btn.addEventListener('click', () => {
        const entry = this.state.colors.get(btn.dataset.remove);
        if (entry) this.toggleColor(entry.color);
      })
    );
    this.qtyList.querySelectorAll('[data-preview]').forEach((btn) =>
      btn.addEventListener('click', () => {
        const entry = this.state.colors.get(btn.dataset.preview);
        if (!entry) return;
        this.setPreviewColor(entry.color);
        this.renderQtyList();
      })
    );
    const total = this.$('[data-pl-total]');
    if (total) total.textContent = this.totalQty();
  }

  /* ---------- krok 3: znakowanie ---------- */
  bindBranding() {
    this.$$('[data-pl-branding]').forEach((btn) =>
      btn.addEventListener('click', () => {
        this.state.branding = btn.dataset.plBranding;
        this.state.brandingDesc = btn.dataset.plDesc || '';
        this.$$('[data-pl-branding]').forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
        const desc = this.$('[data-pl-branding-desc]');
        if (desc) desc.textContent = this.state.brandingDesc;
        this.refresh();
      })
    );
    this.$$('[data-pl-placement]').forEach((btn) =>
      btn.addEventListener('click', () => {
        this.state.placement = btn.dataset.plPlacement;
        this.$$('[data-pl-placement]').forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
        const preset = this.placements[this.state.placement];
        if (preset) this.state.pos = { ...this.state.pos, x: preset.x, y: preset.y };
        this.refresh();
      })
    );
  }

  /* ---------- krok 4: logo + podgląd ---------- */
  bindLogo() {
    const input = this.$('[data-pl-logo]');
    const size = this.$('[data-pl-size]');
    const rot = this.$('[data-pl-rot]');
    const noLogo = this.$('[data-pl-nologo]');
    const reset = this.$('[data-pl-reset]');
    const download = this.$('[data-pl-download]');
    const downloadAll = this.$('[data-pl-download-all]');
    const drop = this.$('[data-pl-drop]');

    const handleFile = (file) => {
      if (!file) return;
      this.state.logoName = file.name;
      this.state.noLogo = false;
      if (noLogo) noLogo.checked = false;
      if (file.type.startsWith('image/')) {
        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
          const res = plImg.cleanLogo(img);
          this.state.logoSource = res.canvas;
          this.state.logoVariant = 'original';
          this.$$('[data-pl-variant]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.plVariant === 'original')));
          const status = this.t.logo_loaded.replace('{{ name }}', file.name) + (res.cleaned ? ` ${this.t.logo_cleaned}` : '');
          this.setLogoStatus(status, 'ok');
          const variants = this.$('[data-pl-variants]');
          if (variants) variants.hidden = false;
          this.refresh();
        };
        img.onerror = () => {
          this.state.logoSource = null;
          this.setLogoStatus(this.t.logo_no_preview.replace('{{ name }}', file.name), 'warn');
          this.refresh();
        };
        img.src = url;
      } else {
        this.state.logoSource = null;
        this.setLogoStatus(this.t.logo_no_preview.replace('{{ name }}', file.name), 'warn');
        this.refresh();
      }
    };

    if (input) input.addEventListener('change', () => handleFile(input.files && input.files[0]));
    if (drop) {
      ['dragenter', 'dragover'].forEach((ev) =>
        drop.addEventListener(ev, (e) => {
          e.preventDefault();
          drop.classList.add('is-over');
        })
      );
      ['dragleave', 'drop'].forEach((ev) =>
        drop.addEventListener(ev, (e) => {
          e.preventDefault();
          drop.classList.remove('is-over');
        })
      );
      drop.addEventListener('drop', (e) => handleFile(e.dataTransfer.files && e.dataTransfer.files[0]));
    }
    this.$$('[data-pl-variant]').forEach((btn) =>
      btn.addEventListener('click', () => {
        this.state.logoVariant = btn.dataset.plVariant;
        this.$$('[data-pl-variant]').forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
        this.refresh();
      })
    );
    if (size) {
      size.addEventListener('input', () => {
        this.state.pos.w = Number(size.value) / 100;
        this.draw();
      });
    }
    if (rot) {
      rot.addEventListener('input', () => {
        this.state.pos.rot = Number(rot.value);
        this.draw();
      });
    }
    if (noLogo) {
      noLogo.addEventListener('change', () => {
        this.state.noLogo = noLogo.checked;
        if (noLogo.checked) {
          this.state.logoSource = null;
          this.state.logoName = '';
          if (input) input.value = '';
          const variants = this.$('[data-pl-variants]');
          if (variants) variants.hidden = true;
          this.setLogoStatus(this.t.logo_later, 'ok');
        } else {
          this.setLogoStatus('', '');
        }
        this.refresh();
      });
    }
    if (reset) {
      reset.addEventListener('click', () => {
        const preset = this.placements[this.state.placement] || { x: 0.5, y: 0.58 };
        this.state.pos = { x: preset.x, y: preset.y, w: 0.34, rot: 0 };
        if (size) size.value = 34;
        if (rot) rot.value = 0;
        this.draw();
      });
    }
    if (download) {
      download.addEventListener('click', (e) => {
        if (!this.canvas) return;
        try {
          download.href = this.canvas.toDataURL('image/png');
          const name = [this.state.product && this.state.product.sku, this.state.branding].filter(Boolean).join('-') || 'podglad';
          download.download = `achti-private-label-${name}.png`;
        } catch (err) {
          e.preventDefault();
          this.setLogoStatus(this.t.download_blocked, 'warn');
        }
      });
    }
    if (downloadAll) {
      downloadAll.addEventListener('click', (e) => {
        const sheet = this.buildSheet();
        if (!sheet) {
          e.preventDefault();
          return;
        }
        try {
          downloadAll.href = sheet.toDataURL('image/png');
          downloadAll.download = `achti-private-label-${(this.state.product && this.state.product.sku) || 'model'}-kolory.png`;
        } catch (err) {
          e.preventDefault();
          this.setLogoStatus(this.t.download_blocked, 'warn');
        }
      });
    }
    this.bindDrag();
  }

  setLogoStatus(text, kind) {
    const el = this.$('[data-pl-logo-status]');
    if (!el) return;
    el.textContent = text;
    el.dataset.kind = kind || '';
  }

  bindDrag() {
    if (!this.canvas) return;
    let dragging = false;
    let offset = { x: 0, y: 0 };
    const toHat = (e) => {
      const r = this.canvas.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * this.canvas.width;
      const py = ((e.clientY - r.top) / r.height) * this.canvas.height;
      const box = this.hatBoxPx || { x: 0, y: 0, w: this.canvas.width, h: this.canvas.height };
      return { x: (px - box.x) / box.w, y: (py - box.y) / box.h };
    };
    this.canvas.addEventListener('pointerdown', (e) => {
      if (!this.logo) return;
      dragging = true;
      this.canvas.setPointerCapture(e.pointerId);
      const p = toHat(e);
      offset = { x: this.state.pos.x - p.x, y: this.state.pos.y - p.y };
      this.canvas.classList.add('is-dragging');
    });
    this.canvas.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const p = toHat(e);
      this.state.pos.x = Math.min(1.05, Math.max(-0.05, p.x + offset.x));
      this.state.pos.y = Math.min(1.05, Math.max(-0.05, p.y + offset.y));
      this.draw();
    });
    const stop = () => {
      if (dragging) this.scheduleStrip();
      dragging = false;
      this.canvas.classList.remove('is-dragging');
    };
    this.canvas.addEventListener('pointerup', stop);
    this.canvas.addEventListener('pointercancel', stop);
  }

  /* ładowanie zdjęcia czapki z cache + analiza obrysu */
  loadHat(url) {
    if (!url) return Promise.resolve(null);
    if (this.hatCache.has(url)) return Promise.resolve(this.hatCache.get(url));
    return new Promise((resolve) => {
      const done = (img) => {
        const a = plImg.analyzeHat(img);
        const entry = { img, box: a.box, tainted: a.tainted };
        this.hatCache.set(url, entry);
        resolve(entry);
      };
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => done(img);
      img.onerror = () => {
        const plain = new Image();
        plain.onload = () => done(plain);
        plain.onerror = () => resolve(null);
        plain.src = url;
      };
      img.src = url;
    });
  }

  currentScene(entry) {
    return {
      hat: entry ? entry.img : null,
      hatBox: entry ? entry.box : { x: 0, y: 0, w: 1, h: 1 },
      tainted: entry ? entry.tainted : true,
      logo: this.logo,
      pos: this.state.pos,
      effect: this.effect,
    };
  }

  draw() {
    if (!this.ctx) return;
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = requestAnimationFrame(() => {
      this._raf = null;
      const url = this.state.previewColor && this.state.previewColor.image;
      const entry = url ? this.hatCache.get(url) : null;
      this.hatBoxPx = plRenderScene(this.canvas, this.currentScene(entry));
      const empty = this.$('[data-pl-preview-empty]');
      if (empty) empty.hidden = Boolean(entry);
      const hint = this.$('[data-pl-preview-hint]');
      if (hint) {
        if (this.logo) hint.textContent = this.t.preview_drag;
        else if (this.state.noLogo) hint.textContent = this.t.logo_later;
        else if (entry) hint.textContent = this.t.preview_empty;
        else hint.textContent = this.t.preview_pick;
      }
      const back = this.$('[data-pl-back-note]');
      if (back) back.hidden = !(this.placements[this.state.placement] && this.placements[this.state.placement].back);
      this.checkContrast(entry);
    });
  }

  /* ostrzeżenie o słabym kontraście logo z czapką */
  checkContrast(entry) {
    const warn = this.$('[data-pl-contrast]');
    if (!warn) return;
    if (!entry || !this.logo || entry.tainted) {
      warn.hidden = true;
      return;
    }
    const logoLum = plImg.meanLum(this.logo);
    /* jasność czapki pod logo */
    const box = this.hatBoxPx;
    let hatLum = 128;
    try {
      const cx = box.x + this.state.pos.x * box.w;
      const cy = box.y + this.state.pos.y * box.h;
      const s = Math.max(8, box.w * this.state.pos.w * 0.5);
      const tmp = document.createElement('canvas');
      tmp.width = PL_CANVAS_W;
      tmp.height = PL_CANVAS_H;
      plRenderScene(tmp, { ...this.currentScene(entry), logo: null });
      const d = tmp.getContext('2d', { willReadFrequently: true }).getImageData(Math.max(0, cx - s / 2), Math.max(0, cy - s / 2), Math.max(1, Math.round(s)), Math.max(1, Math.round(s))).data;
      let sum = 0, n = 0;
      for (let k = 0; k < d.length; k += 16) { sum += d[k] * 0.3 + d[k + 1] * 0.59 + d[k + 2] * 0.11; n += 1; }
      hatLum = n ? sum / n : 128;
    } catch (e) {
      warn.hidden = true;
      return;
    }
    const ratio = plImg.lowContrastRatio(this.logo, hatLum, 70);
    warn.hidden = !(ratio > 0.4 || Math.abs(logoLum - hatLum) < 40);
  }

  /* pasek podglądów na wszystkich wybranych kolorach */
  scheduleStrip() {
    clearTimeout(this._stripTimer);
    this._stripTimer = setTimeout(() => this.renderStrip(), 250);
  }

  async renderStrip() {
    const strip = this.$('[data-pl-strip]');
    const list = this.$('[data-pl-strip-list]');
    const all = this.$('[data-pl-download-all]');
    if (!strip || !list) return;
    const colors = Array.from(this.state.colors.values()).map((c) => c.color);
    if (!this.logo || colors.length < 2) {
      strip.hidden = true;
      if (all) all.hidden = true;
      return;
    }
    strip.hidden = false;
    if (all) all.hidden = false;
    const token = (this._stripToken = (this._stripToken || 0) + 1);
    const items = await Promise.all(colors.map(async (color) => ({ color, entry: await this.loadHat(color.image) })));
    if (token !== this._stripToken) return;
    list.innerHTML = '';
    this._sheet = [];
    items.forEach(({ color, entry }) => {
      const c = document.createElement('canvas');
      c.width = 300;
      c.height = 375;
      plRenderScene(c, this.currentScene(entry));
      const item = document.createElement('div');
      item.className = 'pl-strip__item';
      item.appendChild(c);
      const label = document.createElement('span');
      label.textContent = color.sku || color.title;
      item.appendChild(label);
      list.appendChild(item);
      this._sheet.push({ canvas: c, label: color.sku || color.title });
    });
  }

  buildSheet() {
    if (!this._sheet || !this._sheet.length) return null;
    const cols = Math.min(4, this._sheet.length);
    const rows = Math.ceil(this._sheet.length / cols);
    const cw = 300, ch = 375, pad = 16, lh = 28;
    const sheet = document.createElement('canvas');
    sheet.width = cols * cw + (cols + 1) * pad;
    sheet.height = rows * (ch + lh) + (rows + 1) * pad;
    const x = sheet.getContext('2d');
    x.fillStyle = '#ffffff';
    x.fillRect(0, 0, sheet.width, sheet.height);
    x.fillStyle = '#262626';
    x.font = '600 16px Jost, Arial, sans-serif';
    x.textAlign = 'center';
    this._sheet.forEach((it, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const ox = pad + col * (cw + pad);
      const oy = pad + row * (ch + lh + pad);
      x.drawImage(it.canvas, ox, oy);
      x.fillText(it.label, ox + cw / 2, oy + ch + 20);
    });
    return sheet;
  }

  /* ---------- krok 5: dane i wysyłka ---------- */
  bindForm() {
    if (!this.form) return;
    this.form.addEventListener('submit', (e) => {
      const missing = [];
      if (!this.state.product) missing.push(this.t.err_model);
      if (this.totalQty() < this.minQty) missing.push(this.t.err_qty.replace('{{ count }}', this.minQty));
      if (!this.state.branding) missing.push(this.t.err_branding);
      if (!this.state.placement) missing.push(this.t.err_placement);
      if (!this.state.logoName && !this.state.noLogo) missing.push(this.t.err_logo);
      const box = this.$('[data-pl-errors]');
      if (missing.length) {
        e.preventDefault();
        box.hidden = false;
        box.innerHTML = `<p>${this.esc(this.t.err_intro)}</p><ul>${missing.map((m) => `<li>${this.esc(m)}</li>`).join('')}</ul>`;
        box.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return;
      }
      box.hidden = true;
      this.writeHidden(true);
    });
    ['input', 'change'].forEach((ev) => this.form.addEventListener(ev, () => this.refresh()));
  }

  /* ---------- odświeżenie: kroki, podsumowanie, pola ukryte ---------- */
  refresh() {
    const s = this.state;
    const hasModel = Boolean(s.product);
    const qtyOk = hasModel && this.totalQty() >= this.minQty;
    const brandingOk = Boolean(s.branding && s.placement);
    const logoOk = Boolean(s.logoName || s.noLogo);

    this.setDone('model', hasModel);
    this.setDone('colors', qtyOk);
    this.setDone('branding', brandingOk);
    this.setDone('logo', logoOk);
    if (hasModel) ['colors', 'branding', 'logo', 'details'].forEach((n) => this.unlock(n));

    const qtyWarn = this.$('[data-pl-qty-warn]');
    if (qtyWarn) qtyWarn.hidden = !hasModel || qtyOk;

    const progress = this.$('[data-pl-progress]');
    if (progress) {
      const done = [hasModel, qtyOk, brandingOk, logoOk].filter(Boolean).length;
      progress.textContent = this.t.progress.replace('{{ done }}', done).replace('{{ total }}', 4);
      progress.style.setProperty('--pl-progress', `${(done / 4) * 100}%`);
    }

    const colorsText = [];
    s.colors.forEach(({ color, qty }) => colorsText.push(`${color.title}${color.sku ? ` (${color.sku})` : ''}: ${qty} ${this.t.pcs}`));
    const variantLabel = { original: this.t.variant_original, white: this.t.variant_white, black: this.t.variant_black };
    const rows = [
      [this.t.step_model, hasModel ? `${s.product.title}${s.product.sku ? ` (${s.product.sku})` : ''}` : '—'],
      [this.t.step_colors, colorsText.length ? colorsText.join('; ') : '—'],
      [this.t.qty_total, hasModel ? `${this.totalQty()} ${this.t.pcs}` : '—'],
      [this.t.step_branding, s.branding || '—'],
      [this.t.placement, s.placement || '—'],
      [this.t.logo, s.logoName ? `${s.logoName}${s.logoVariant !== 'original' ? ` (${this.t.variant_label}: ${s.logoVariant})` : ''}` : s.noLogo ? this.t.logo_later : '—'],
    ];
    const list = this.$('[data-pl-summary]');
    if (list) list.innerHTML = rows.map(([k, v]) => `<div class="pl-summary__row"><dt>${this.esc(k)}</dt><dd>${this.esc(v)}</dd></div>`).join('');
    this.summaryRows = rows;
    this.writeHidden(false);
    this.draw();
    this.scheduleStrip();
  }

  writeHidden(final) {
    const s = this.state;
    const hidden = this.$('[data-pl-config]');
    if (hidden) {
      const extra = [];
      if (this.logo) extra.push(`${this.t.logo_pos}: x ${Math.round(s.pos.x * 100)}% / y ${Math.round(s.pos.y * 100)}% czapki, ${this.t.logo_size} ${Math.round(s.pos.w * 100)}% szerokości czapki, ${this.t.logo_rot} ${s.pos.rot}°`);
      const urls = [];
      s.colors.forEach(({ color }) => color.url && urls.push(color.url));
      if (urls.length) extra.push(`URL: ${urls.join(' , ')}`);
      hidden.value = (this.summaryRows || []).map(([k, v]) => `${k}: ${v}`).concat(extra).join('\n');
    }
    if (final) {
      const preview = this.$('[data-pl-preview-field]');
      if (preview) {
        preview.value = '';
        if (this.canvas && this.logo) {
          try {
            const small = document.createElement('canvas');
            small.width = 360;
            small.height = 450;
            small.getContext('2d').drawImage(this.canvas, 0, 0, small.width, small.height);
            preview.value = small.toDataURL('image/jpeg', 0.6);
          } catch (err) {
            preview.value = '';
          }
        }
      }
    }
  }

  esc(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
}
if (!customElements.get('private-label-configurator')) customElements.define('private-label-configurator', PrivateLabelConfigurator);
