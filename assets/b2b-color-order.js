// Zamówienie wielu kolorów naraz (snippets/b2b-color-order.liquid): ilości przy kółkach → jedno /cart/add.js z listą wariantów.
// minimum sztuk jednego koloru: data-min pól (ustawienie motywu b2b_min_per_color; 01.11.2026 = 2, 20.11.2026 = 10)
let MIN_PER_COLOR = 10;

if (!customElements.get('b2b-color-order')) {
  customElements.define(
    'b2b-color-order',
    class B2BColorOrder extends HTMLElement {
      // własny suwak obok tabeli kolorów (Kamil 20.10.2026: ma być zawsze widoczny, także na Macu i telefonie)
      initBar(grid) {
        const bar = this.querySelector('[data-bar]');
        if (!grid || !bar) return;
        const track = bar.querySelector('[data-bar-track]');
        const thumb = bar.querySelector('[data-bar-thumb]');
        const sync = () => {
          const over = grid.scrollHeight - grid.clientHeight;
          bar.hidden = over <= 2;
          this.classList.toggle('has-bar', over > 2);
          if (over <= 2) return;
          const th = track.clientHeight;
          const h = Math.max(32, (th * grid.clientHeight) / grid.scrollHeight);
          thumb.style.height = `${h}px`;
          thumb.style.transform = `translateY(${((th - h) * grid.scrollTop) / over}px)`;
        };
        grid.addEventListener('scroll', sync, { passive: true });
        window.addEventListener('resize', sync);
        requestAnimationFrame(sync);
        const row = () => (grid.querySelector('.b2b-co__item')?.offsetHeight || 56) * 3;
        bar.querySelectorAll('[data-bar-step]').forEach((b) =>
          b.addEventListener('click', () => grid.scrollBy({ top: row() * Number(b.dataset.barStep), behavior: 'smooth' }))
        );
        track.addEventListener('pointerdown', (e) => {
          const th = track.clientHeight;
          const h = thumb.offsetHeight;
          const over = grid.scrollHeight - grid.clientHeight;
          const rect = track.getBoundingClientRect();
          const onThumb = e.target === thumb;
          const startY = e.clientY;
          const startTop = grid.scrollTop;
          if (!onThumb) grid.scrollTop = ((e.clientY - rect.top - h / 2) / (th - h)) * over;
          track.setPointerCapture(e.pointerId);
          const move = (ev) => {
            grid.scrollTop = onThumb ? startTop + ((ev.clientY - startY) / (th - h)) * over
                                     : ((ev.clientY - rect.top - h / 2) / (th - h)) * over;
          };
          const up = () => { track.removeEventListener('pointermove', move); track.removeEventListener('pointerup', up); };
          track.addEventListener('pointermove', move);
          track.addEventListener('pointerup', up);
          e.preventDefault();
        });
      }

      openLightbox(start) {
        const items = [...this.querySelectorAll('.b2b-co__circle[data-full]')];
        if (start < 0 || !items.length) return;
        let i = start;
        const d = this.dataset;
        const box = document.createElement('div');
        box.className = 'b2b-lb' + (this.classList.contains('b2b-co--probka') ? ' b2b-lb--probka' : '');
        box.setAttribute('role', 'dialog');
        box.setAttribute('aria-modal', 'true');
        box.innerHTML = `<button type="button" class="b2b-lb__close" aria-label="${d.lbClose || 'Zamknij'}">×</button>
          <button type="button" class="b2b-lb__nav b2b-lb__nav--prev" aria-label="${d.lbPrev || ''}">‹</button>
          <figure class="b2b-lb__fig"><img class="b2b-lb__img" alt=""><figcaption class="b2b-lb__name"></figcaption></figure>
          <button type="button" class="b2b-lb__nav b2b-lb__nav--next" aria-label="${d.lbNext || ''}">›</button>
          <p class="b2b-lb__count"></p>`;
        const img = box.querySelector('.b2b-lb__img');
        const show = () => {
          const c = items[i];
          img.src = c.dataset.full;
          img.alt = c.dataset.name;
          box.querySelector('.b2b-lb__name').textContent = c.dataset.name;
          box.querySelector('.b2b-lb__count').textContent = `${i + 1} / ${items.length}`;
        };
        const go = (step) => { i = (i + step + items.length) % items.length; show(); };
        const close = () => {
          box.remove();
          document.removeEventListener('keydown', onKey);
          document.documentElement.classList.remove('b2b-lb-open');
          items[i].closest('.b2b-co__item').querySelector('.b2b-co__input')?.focus({ preventScroll: true });
        };
        const onKey = (e) => {
          if (e.key === 'Escape') close();
          else if (e.key === 'ArrowRight') go(1);
          else if (e.key === 'ArrowLeft') go(-1);
        };
        box.addEventListener('click', (e) => {
          if (e.target.closest('.b2b-lb__nav--prev')) go(-1);
          else if (e.target.closest('.b2b-lb__nav--next')) go(1);
          else if (e.target.closest('.b2b-lb__close') || !e.target.closest('.b2b-lb__fig')) close();
        });
        let x0 = null;
        box.addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; }, { passive: true });
        box.addEventListener('touchend', (e) => {
          if (x0 === null) return;
          const dx = e.changedTouches[0].clientX - x0;
          if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
          x0 = null;
        });
        document.addEventListener('keydown', onKey);
        document.documentElement.classList.add('b2b-lb-open');
        document.body.appendChild(box);
        show();
        box.querySelector('.b2b-lb__close').focus();
      }

      connectedCallback() {
        // powiększenie koloru (Adrian 13.10.2026; 05.11.2026 klienci: „jak fotki produktów”): na komputerze podgląd po najechaniu (CSS),
        // kliknięcie/dotknięcie otwiera lightbox z dużym zdjęciem próbki i strzałkami do kolejnych kolorów
        this.addEventListener('click', (e) => {
          const circle = e.target.closest('.b2b-co__circle, .b2b-co__zoom');
          if (!circle) return;
          e.preventDefault(); // bez fokusu na polu ilości (nie wyskakuje klawiatura)
          const c = circle.closest('.b2b-co__item').querySelector('.b2b-co__circle');
          this.openLightbox([...this.querySelectorAll('.b2b-co__circle[data-full]')].indexOf(c));
        });
        // tabela z przewijaniem (Kamil 20.10.2026): podgląd jest position: fixed obok kółka, żeby okienko go nie przycinało
        const placeZoom = (circle) => {
          if (!this.classList.contains('b2b-co--list')) return;
          const zoom = circle.parentElement.querySelector('.b2b-co__zoom');
          if (!zoom) return;
          const r = circle.getBoundingClientRect();
          const w = zoom.offsetWidth || 160;
          const vw = document.documentElement.clientWidth;
          let x = r.right + 12;
          if (x + w > vw - 8) x = Math.max(8, r.left - 12 - w);
          const y = Math.min(Math.max(r.top + r.height / 2, w / 2 + 8), window.innerHeight - w / 2 - 8);
          zoom.style.setProperty('--zx', `${Math.round(x)}px`);
          zoom.style.setProperty('--zy', `${Math.round(y)}px`);
        };
        this.addEventListener('mouseover', (e) => {
          const circle = e.target.closest('.b2b-co__circle');
          if (circle) placeZoom(circle);
        });
        this.addEventListener('click', (e) => {
          const circle = e.target.closest('.b2b-co__circle');
          if (circle) placeZoom(circle);
        }, true);
        const grid = this.querySelector('.b2b-co__grid');
        this.initBar(grid);
        if (grid) grid.addEventListener('scroll', () => this.querySelectorAll('.b2b-co__item.is-zoom').forEach((i) => i.classList.remove('is-zoom')), { passive: true });
        document.addEventListener('click', (e) => {
          if (!e.target.closest('.b2b-co__circle, .b2b-co__zoom'))
            this.querySelectorAll('.b2b-co__item.is-zoom').forEach((i) => i.classList.remove('is-zoom'));
        });
        this.inputs = [...this.querySelectorAll('.b2b-co__input')];
        if (!this.inputs.length) return;
        const i18n = this.querySelector('[data-b2b-co-i18n]');
        this.t = i18n ? JSON.parse(i18n.textContent) : {};
        const minEl = this.querySelector('.b2b-co__input[data-min]');
        if (minEl) MIN_PER_COLOR = parseInt(minEl.dataset.min, 10) || MIN_PER_COLOR;
        this.totalEl = this.querySelector('[data-total]');
        this.addBtn = this.querySelector('[data-add]');
        this.msg = this.querySelector('[data-msg]');

        this.addEventListener('click', (e) => {
          const step = e.target.closest('[data-step]');
          if (!step) return;
          const input = step.parentElement.querySelector('.b2b-co__input');
          const cur = parseInt(input.value, 10) || 0;
          const d = parseInt(step.dataset.step, 10);
          // Adrian: produkcja ma minimum na kolor — z 0 skok na minimum, z minimum w dół na 0
          let v = Math.max(0, cur + d);
          if (d > 0 && v < MIN_PER_COLOR) v = MIN_PER_COLOR;
          if (d < 0 && v < MIN_PER_COLOR) v = 0;
          input.value = v;
          this.update();
        });
        this.addEventListener('input', (e) => {
          if (e.target.classList.contains('b2b-co__input')) this.update();
        });
        this.addEventListener('change', (e) => {
          if (!e.target.classList.contains('b2b-co__input')) return;
          const v = parseInt(e.target.value, 10) || 0;
          if (v > 0 && v < MIN_PER_COLOR) e.target.value = MIN_PER_COLOR;
          this.update();
        });
        this.addEventListener('focusin', (e) => {
          if (e.target.classList.contains('b2b-co__input')) e.target.select();
        });
        this.addBtn.addEventListener('click', () => this.add());
        this.update();
      }

      // 30.10.2026: wartość netto zaznaczonych kolorów + rabat ilościowy liczony od wszystkich sztuk w koszyku (koszyk + to, co dodajemy)
      updateValue(n) {
        const el = this.querySelector('[data-value]');
        if (!el || !this.t.value) return;
        if (!n) { el.hidden = true; return; }
        const cents = this.inputs.reduce((s, i) => s + (parseInt(i.value, 10) || 0) * (Number(i.dataset.price) || 0), 0);
        let fmt;
        try { fmt = new Intl.NumberFormat(this.t.locale || 'pl', { style: 'currency', currency: this.t.currency || 'PLN' }); }
        catch (e) { fmt = { format: (v) => v.toFixed(2) }; }
        const money = (c) => fmt.format(c / 100);
        const total = (Number(this.t.cartCount) || 0) + n;
        const tiers = this.t.tiers || [];
        const tier = tiers.filter((t) => total >= t[0]).pop();
        const next = tiers.find((t) => total < t[0]);
        const lines = [this.t.value.replace('__A__', money(cents))];
        if (tier) lines.push(this.t.discount.replace('__P__', tier[1]).replace('__A__', money(Math.round(cents * (100 - tier[1]) / 100))));
        if (next) lines.push(this.t.next.replace('__N__', next[0] - total).replace('__P__', next[1]));
        el.innerHTML = '';
        lines.forEach((l, i) => { const s = document.createElement('span'); s.textContent = l; if (i) s.className = i === 1 && tier ? 'b2b-co__disc' : 'b2b-co__next'; el.appendChild(s); });
        el.hidden = false;
      }

      items() {
        return this.inputs
          .map((i) => {
            const q = Math.max(0, parseInt(i.value, 10) || 0);
            return { id: Number(i.dataset.variantId), quantity: q > 0 && q < MIN_PER_COLOR ? MIN_PER_COLOR : q };
          })
          .filter((i) => i.quantity > 0);
      }

      update() {
        const items = this.items();
        const n = items.reduce((s, i) => s + i.quantity, 0);
        this.inputs.forEach((i) => i.closest('.b2b-co__item').classList.toggle('is-set', (parseInt(i.value, 10) || 0) > 0));
        this.totalEl.textContent = n
          ? this.t.total.replace('__N__', n).replace('__C__', items.length)
          : this.t.empty;
        this.updateValue(n);
        this.addBtn.disabled = n === 0;
      }

      async add() {
        const items = this.items();
        if (!items.length) return;
        const cart = document.querySelector('cart-notification') || document.querySelector('cart-drawer');
        const body = { items };
        if (cart) {
          body.sections = cart.getSectionsToRender().map((s) => s.id);
          body.sections_url = window.location.pathname;
          cart.setActiveElement && cart.setActiveElement(this.addBtn);
        }
        this.addBtn.disabled = true;
        this.addBtn.classList.add('loading');
        this.msg.hidden = true;
        try {
          const res = await fetch(`${window.routes.cart_add_url}.js`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify(body),
          });
          const data = await res.json();
          if (!res.ok || data.status) throw new Error(data.description || data.message || this.t.error);
          const n = items.reduce((s, i) => s + i.quantity, 0);
          this.inputs.forEach((i) => (i.value = 0));
          this.update();
          this.msg.textContent = this.t.added.replace('__N__', n);
          this.msg.hidden = false;
          if (typeof publish === 'function' && typeof PUB_SUB_EVENTS !== 'undefined') {
            publish(PUB_SUB_EVENTS.cartUpdate, { source: 'b2b-color-order', cartData: data });
          }
          // powiadomienie/szuflada koszyka Trade: pierwszy dodany wiersz + wyrenderowane sekcje
          if (cart && data.items && data.items.length) cart.renderContents({ ...data.items[0], sections: data.sections });
        } catch (e) {
          this.msg.textContent = e.message || this.t.error;
          this.msg.hidden = false;
          this.update();
        } finally {
          this.addBtn.classList.remove('loading');
        }
      }
    }
  );
}
