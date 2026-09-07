/* Achti: konfigurator Private Label (zapytanie o wycenę).
   Kroki: model -> kolory i ilości -> znakowanie -> logo z podglądem -> dane firmy. */
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
      logoImage: null,
      noLogo: false,
      pos: { x: 0.5, y: 0.62, w: 0.22, rot: 0 },
    };
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
      const color = product.colors[Number(btn.dataset.index)];
      this.toggleColor(color);
    };
  }

  toggleColor(color, force) {
    const key = color.title;
    if (this.state.colors.has(key) && force !== true) {
      if (this.state.colors.size === 1) {
        this.state.previewColor = color;
        this.loadHat(color.image);
        return;
      }
      this.state.colors.delete(key);
      if (this.state.previewColor === color) {
        this.state.previewColor = this.state.colors.values().next().value.color;
        this.loadHat(this.state.previewColor.image);
      }
    } else if (!this.state.colors.has(key)) {
      this.state.colors.set(key, { color, qty: this.minQty });
      this.state.previewColor = color;
      this.loadHat(color.image);
    } else {
      this.state.previewColor = color;
      this.loadHat(color.image);
    }
    this.renderQtyList();
    this.refresh();
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
          <button type="button" class="pl-qty-row__swatch" data-preview="${this.esc(key)}" title="${this.t.show_on_preview}">
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
        this.state.previewColor = entry.color;
        this.loadHat(entry.color.image);
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
    const drop = this.$('[data-pl-drop]');

    const handleFile = (file) => {
      if (!file) return;
      this.state.logoName = file.name;
      this.state.noLogo = false;
      if (noLogo) noLogo.checked = false;
      if (file.type === 'image/svg+xml' || file.type.startsWith('image/')) {
        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
          this.state.logoImage = img;
          this.setLogoStatus(this.t.logo_loaded.replace('{{ name }}', file.name), 'ok');
          this.refresh();
        };
        img.onerror = () => {
          this.state.logoImage = null;
          this.setLogoStatus(this.t.logo_no_preview.replace('{{ name }}', file.name), 'warn');
          this.refresh();
        };
        img.src = url;
      } else {
        this.state.logoImage = null;
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
          this.state.logoImage = null;
          this.state.logoName = '';
          if (input) input.value = '';
          this.setLogoStatus(this.t.logo_later, 'ok');
        } else {
          this.setLogoStatus('', '');
        }
        this.refresh();
      });
    }
    if (reset) {
      reset.addEventListener('click', () => {
        const preset = this.placements[this.state.placement] || { x: 0.5, y: 0.62 };
        this.state.pos = { x: preset.x, y: preset.y, w: 0.22, rot: 0 };
        if (size) size.value = 22;
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
    const toRel = (e) => {
      const r = this.canvas.getBoundingClientRect();
      return { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height };
    };
    this.canvas.addEventListener('pointerdown', (e) => {
      if (!this.state.logoImage) return;
      dragging = true;
      this.canvas.setPointerCapture(e.pointerId);
      const p = toRel(e);
      offset = { x: this.state.pos.x - p.x, y: this.state.pos.y - p.y };
      this.canvas.classList.add('is-dragging');
    });
    this.canvas.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const p = toRel(e);
      this.state.pos.x = Math.min(0.97, Math.max(0.03, p.x + offset.x));
      this.state.pos.y = Math.min(0.97, Math.max(0.03, p.y + offset.y));
      this.draw();
    });
    const stop = () => {
      dragging = false;
      this.canvas.classList.remove('is-dragging');
    };
    this.canvas.addEventListener('pointerup', stop);
    this.canvas.addEventListener('pointercancel', stop);
  }

  loadHat(url) {
    if (!this.canvas) return;
    if (!url) {
      this.hat = null;
      this.draw();
      return;
    }
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      this.hat = img;
      this.draw();
    };
    img.onerror = () => {
      const plain = new Image();
      plain.onload = () => {
        this.hat = plain;
        this.draw();
      };
      plain.src = url;
    };
    img.src = url;
  }

  draw() {
    if (!this.ctx) return;
    const { canvas, ctx } = this;
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, W, H);
    if (this.hat) {
      const scale = Math.min(W / this.hat.width, H / this.hat.height);
      const w = this.hat.width * scale;
      const h = this.hat.height * scale;
      ctx.drawImage(this.hat, (W - w) / 2, (H - h) / 2, w, h);
    }
    if (this.state.logoImage) {
      const lw = W * this.state.pos.w;
      const lh = lw * (this.state.logoImage.height / this.state.logoImage.width);
      ctx.save();
      ctx.translate(W * this.state.pos.x, H * this.state.pos.y);
      ctx.rotate((this.state.pos.rot * Math.PI) / 180);
      ctx.globalAlpha = 0.96;
      ctx.drawImage(this.state.logoImage, -lw / 2, -lh / 2, lw, lh);
      ctx.restore();
    }
    const empty = this.$('[data-pl-preview-empty]');
    if (empty) empty.hidden = Boolean(this.hat);
    const hint = this.$('[data-pl-preview-hint]');
    if (hint) {
      if (this.state.logoImage) hint.textContent = this.t.preview_drag;
      else if (this.state.noLogo) hint.textContent = this.t.logo_later;
      else if (this.hat) hint.textContent = this.t.preview_empty;
      else hint.textContent = this.t.preview_pick;
    }
    const back = this.$('[data-pl-back-note]');
    if (back) back.hidden = !(this.placements[this.state.placement] && this.placements[this.state.placement].back);
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

    const rows = [
      [this.t.step_model, hasModel ? `${s.product.title}${s.product.sku ? ` (${s.product.sku})` : ''}` : '—'],
      [this.t.step_colors, colorsText.length ? colorsText.join('; ') : '—'],
      [this.t.qty_total, hasModel ? `${this.totalQty()} ${this.t.pcs}` : '—'],
      [this.t.step_branding, s.branding || '—'],
      [this.t.placement, s.placement || '—'],
      [this.t.logo, s.logoName || (s.noLogo ? this.t.logo_later : '—')],
    ];
    const list = this.$('[data-pl-summary]');
    if (list) {
      list.innerHTML = rows.map(([k, v]) => `<div class="pl-summary__row"><dt>${this.esc(k)}</dt><dd>${this.esc(v)}</dd></div>`).join('');
    }
    this.summaryRows = rows;
    this.writeHidden(false);
    this.draw();
  }

  writeHidden(final) {
    const s = this.state;
    const hidden = this.$('[data-pl-config]');
    if (hidden) {
      const extra = [];
      if (s.logoImage) extra.push(`${this.t.logo_pos}: x ${Math.round(s.pos.x * 100)}%, y ${Math.round(s.pos.y * 100)}%, ${this.t.logo_size} ${Math.round(s.pos.w * 100)}%, ${this.t.logo_rot} ${s.pos.rot}°`);
      const urls = [];
      s.colors.forEach(({ color }) => color.url && urls.push(color.url));
      if (urls.length) extra.push(`URL: ${urls.join(' , ')}`);
      hidden.value = (this.summaryRows || []).map(([k, v]) => `${k}: ${v}`).concat(extra).join('\n');
    }
    if (final) {
      const preview = this.$('[data-pl-preview-field]');
      if (preview) {
        preview.value = '';
        if (this.canvas && s.logoImage) {
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
