/* Achti: przewijana taśma produktów z przyciskiem Rozwiń/Zwiń (sekcja featured-collection).
   Taśma jedzie sama (requestAnimationFrame), zatrzymuje się po najechaniu i daje się przeciągać palcem (telefon)
   albo myszką (komputer); po puszczeniu jedzie dalej od miejsca, w którym ją zostawiono. */
class FcMarquee extends HTMLElement {
  connectedCallback() {
    this.track = this.querySelector('.fc-marquee__track');
    this.toggle = this.querySelector('.fc-marquee__toggle');
    this.viewAll = this.parentElement.querySelector('.fc-marquee__viewall');
    if (!this.track || !this.toggle) return;
    this.reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.originals = Array.from(this.track.children);
    this.pos = 0;
    this.loop = 0;
    this.toggle.addEventListener('click', () => (this.expanded ? this.collapse() : this.expand()));
    this.bindDrag();
    if (this.reduced) {
      this.classList.remove('fc-marquee--running');
      this.classList.add('fc-marquee--static');
    } else {
      this.start();
      this.onResize = () => this.expanded || this.start();
      window.addEventListener('resize', this.onResize);
    }
  }

  disconnectedCallback() {
    this.running = false;
    if (this.onResize) window.removeEventListener('resize', this.onResize);
  }

  start() {
    this.clearClones();
    this.speed = Math.max(10, parseFloat(this.dataset.speed) || 40); // px na sekundę
    const gap = parseFloat(getComputedStyle(this.track).columnGap || 0);
    const width = this.originals.reduce((sum, li) => sum + li.getBoundingClientRect().width, 0) + this.originals.length * gap;
    if (!width) return;
    let copies = 1;
    while (width * copies < window.innerWidth * 2) copies += 1;
    for (let i = 0; i < copies; i += 1) {
      this.originals.forEach((li) => {
        const clone = li.cloneNode(true);
        clone.setAttribute('aria-hidden', 'true');
        clone.classList.add('fc-marquee__clone');
        clone.removeAttribute('id');
        clone.querySelectorAll('[id]').forEach((el) => el.removeAttribute('id'));
        clone.querySelectorAll('a, button, input').forEach((el) => el.setAttribute('tabindex', '-1'));
        this.track.appendChild(clone);
      });
    }
    this.loop = width;
    this.wrap();
    this.classList.add('fc-marquee--running');
    this.apply();
    if (!this.running) {
      this.running = true;
      this.last = null;
      requestAnimationFrame((ts) => this.tick(ts));
    }
  }

  tick(ts) {
    if (!this.running) return;
    if (this.last != null && !this.dragging && !this.hovered && !this.expanded && this.loop) {
      const dt = Math.min(ts - this.last, 100) / 1000; // po powrocie do karty nie przeskakuj
      this.pos -= this.speed * dt;
      this.wrap();
      this.apply();
    }
    this.last = ts;
    requestAnimationFrame((t) => this.tick(t));
  }

  wrap() {
    if (!this.loop) return;
    while (this.pos <= -this.loop) this.pos += this.loop;
    while (this.pos > 0) this.pos -= this.loop;
  }

  apply() {
    this.track.style.transform = `translate3d(${this.pos}px, 0, 0)`;
  }

  bindDrag() {
    this.addEventListener('mouseenter', () => (this.hovered = true));
    this.addEventListener('mouseleave', () => (this.hovered = false));
    this.addEventListener('focusin', () => (this.hovered = true));
    this.addEventListener('focusout', () => (this.hovered = false));
    this.track.querySelectorAll('img').forEach((img) => (img.draggable = false));
    this.track.addEventListener('pointerdown', (e) => {
      if (this.expanded || this.reduced || (e.pointerType === 'mouse' && e.button !== 0)) return;
      this.dragging = true;
      this.moved = false;
      this.dragStartX = e.clientX;
      this.dragStartPos = this.pos;
      this.dragPointer = e.pointerId;
      this.classList.add('fc-marquee--dragging');
      try { this.track.setPointerCapture(e.pointerId); } catch (err) { /* stare przeglądarki */ }
    });
    this.track.addEventListener('pointermove', (e) => {
      if (!this.dragging || e.pointerId !== this.dragPointer) return;
      const dx = e.clientX - this.dragStartX;
      if (Math.abs(dx) > 6) this.moved = true;
      this.pos = this.dragStartPos + dx;
      this.wrap();
      this.apply();
    });
    const end = (e) => {
      if (!this.dragging || e.pointerId !== this.dragPointer) return;
      this.dragging = false;
      this.classList.remove('fc-marquee--dragging');
      try { this.track.releasePointerCapture(e.pointerId); } catch (err) { /* ignoruj */ }
      if (this.moved) {
        // przeciągnięcie nie może otworzyć produktu — zjedz najbliższy klik
        const swallow = (ev) => { ev.preventDefault(); ev.stopPropagation(); };
        this.track.addEventListener('click', swallow, { capture: true, once: true });
        setTimeout(() => this.track.removeEventListener('click', swallow, { capture: true }), 300);
      }
    };
    this.track.addEventListener('pointerup', end);
    this.track.addEventListener('pointercancel', end);
  }

  clearClones() {
    this.track.querySelectorAll('.fc-marquee__clone').forEach((el) => el.remove());
    this.track.querySelectorAll('img').forEach((img) => (img.draggable = false));
  }

  expand() {
    this.expanded = true;
    this.classList.remove('fc-marquee--running', 'fc-marquee--static', 'fc-marquee--dragging');
    this.classList.add('fc-marquee--expanded');
    this.clearClones();
    this.track.style.removeProperty('transform');
    this.toggle.textContent = this.toggle.dataset.labelCollapse;
    this.toggle.setAttribute('aria-expanded', 'true');
    if (this.viewAll) this.viewAll.hidden = false;
  }

  collapse() {
    this.expanded = false;
    this.classList.remove('fc-marquee--expanded');
    this.toggle.textContent = this.toggle.dataset.labelExpand;
    this.toggle.setAttribute('aria-expanded', 'false');
    if (this.viewAll) this.viewAll.hidden = true;
    if (this.reduced) this.classList.add('fc-marquee--static');
    else this.start();
    this.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
}
if (!customElements.get('fc-marquee')) customElements.define('fc-marquee', FcMarquee);
