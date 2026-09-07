/* Achti: przewijana taśma produktów z przyciskiem Rozwiń/Zwiń (sekcja featured-collection). */
class FcMarquee extends HTMLElement {
  connectedCallback() {
    this.track = this.querySelector('.fc-marquee__track');
    this.toggle = this.querySelector('.fc-marquee__toggle');
    this.viewAll = this.parentElement.querySelector('.fc-marquee__viewall');
    if (!this.track || !this.toggle) return;
    this.reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.originals = Array.from(this.track.children);
    this.toggle.addEventListener('click', () => (this.expanded ? this.collapse() : this.expand()));
    if (this.reduced) {
      this.classList.remove('fc-marquee--running');
      this.classList.add('fc-marquee--static');
    } else {
      this.start();
      this.onResize = () => this.expanded || this.start();
      window.addEventListener('resize', this.onResize);
    }
  }

  start() {
    this.clearClones();
    const speed = Math.max(10, parseFloat(this.dataset.speed) || 40);
    const width = this.originals.reduce((sum, li) => sum + li.getBoundingClientRect().width, 0)
      + this.originals.length * parseFloat(getComputedStyle(this.track).columnGap || 0);
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
    this.track.style.setProperty('--fc-shift', `-${width}px`);
    this.track.style.setProperty('--fc-duration', `${width / speed}s`);
    this.classList.add('fc-marquee--running');
  }

  clearClones() {
    this.track.querySelectorAll('.fc-marquee__clone').forEach((el) => el.remove());
  }

  expand() {
    this.expanded = true;
    this.classList.remove('fc-marquee--running', 'fc-marquee--static');
    this.classList.add('fc-marquee--expanded');
    this.clearClones();
    this.track.style.removeProperty('--fc-shift');
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
