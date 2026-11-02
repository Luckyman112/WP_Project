// Interactive sunburst flavour wheel.
// Inner ring: flavour families (click to focus). Outer ring: notes (click to select).
// Notes are keyboard-accessible checkboxes (Tab + Enter/Space).

const NS = "http://www.w3.org/2000/svg";
const SIZE = 520;
const C = SIZE / 2;
const R_INNER = 62;
const R_MID = 138;
const R_OUTER = 252;

const svgEl = (tag, attrs = {}) => {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};

const polar = (r, deg) => {
  const rad = (deg - 90) * (Math.PI / 180);
  return [C + r * Math.cos(rad), C + r * Math.sin(rad)];
};

function sector(r0, r1, a0, a1) {
  const large = a1 - a0 > 180 ? 1 : 0;
  const [x0, y0] = polar(r1, a0);
  const [x1, y1] = polar(r1, a1);
  const [x2, y2] = polar(r0, a1);
  const [x3, y3] = polar(r0, a0);
  return `M${x0},${y0} A${r1},${r1} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 ${large} 0 ${x3},${y3} Z`;
}

function radialText(text, r, deg, className) {
  const [x, y] = polar(r, deg);
  const flip = deg % 360 > 180;
  const rotation = flip ? deg + 90 : deg - 90;
  const node = svgEl("text", {
    x, y,
    class: className,
    "text-anchor": "middle",
    "dominant-baseline": "middle",
    transform: `rotate(${rotation} ${x} ${y})`,
  });
  node.textContent = text;
  return node;
}

export class FlavorWheel {
  constructor(container, families, { selected = [], max = 12, onChange = () => {} } = {}) {
    this.container = container;
    this.families = families;
    this.selected = new Set(selected);
    this.max = max;
    this.onChange = onChange;
    this.notes = new Map();
    this.render();
  }

  render() {
    const svg = svgEl("svg", { viewBox: `0 0 ${SIZE} ${SIZE}`, role: "group", "aria-label": "Flavour wheel" });
    const total = this.families.reduce((n, f) => n + f.notes.length, 0);
    const gap = 0.6;
    let angle = 0;

    for (const family of this.families) {
      const span = (family.notes.length / total) * 360;
      const familyPath = svgEl("path", {
        d: sector(R_INNER, R_MID, angle + gap / 2, angle + span - gap / 2),
        fill: family.color,
        class: "wheel__family",
        "data-family": family.id,
      });
      const title = svgEl("title");
      title.textContent = family.label;
      familyPath.append(title);
      familyPath.addEventListener("click", () => this.focusFamily(family.id));
      svg.append(familyPath, radialText(family.label.split(" ")[0], (R_INNER + R_MID) / 2, angle + span / 2, "wheel__text wheel__text--family"));

      const noteSpan = span / family.notes.length;
      family.notes.forEach((note, i) => {
        const a0 = angle + i * noteSpan;
        const path = svgEl("path", {
          d: sector(R_MID + 3, R_OUTER, a0 + gap / 2, a0 + noteSpan - gap / 2),
          class: "wheel__note",
          style: `--tone: ${family.color}`,
          tabindex: 0,
          role: "checkbox",
          "aria-label": `${note.label} (${family.label})`,
          "data-family": family.id,
        });
        const label = radialText(note.label, (R_MID + R_OUTER) / 2 + 8, a0 + noteSpan / 2, "wheel__text");
        path.addEventListener("click", () => this.toggle(note.id));
        path.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); this.toggle(note.id); }
        });
        path.addEventListener("mouseenter", () => this.showCaption(note.label));
        path.addEventListener("mouseleave", () => this.showCaption());
        svg.append(path, label);
        this.notes.set(note.id, { path, label, note, family });
      });
      angle += span;
    }

    this.center = document.createElement("div");
    this.center.className = "wheel__center";
    this.svg = svg;
    this.container.replaceChildren(svg, this.center);
    this.sync();
  }

  focusFamily(familyId) {
    const same = this.focused === familyId;
    this.focused = same ? null : familyId;
    this.container.classList.toggle("is-focused", !!this.focused);
    this.svg.querySelectorAll("[data-family]").forEach((el) => {
      el.classList.toggle("is-focus", el.dataset.family === this.focused);
    });
  }

  toggle(id) {
    if (this.selected.has(id)) this.selected.delete(id);
    else if (this.selected.size >= this.max) {
      this.showCaption(`Max ${this.max}`);
      this.container.animate([{ transform: "translateX(-4px)" }, { transform: "translateX(4px)" }, { transform: "none" }], { duration: 220 });
      return;
    } else this.selected.add(id);
    this.sync();
    this.onChange([...this.selected]);
  }

  set(ids) {
    this.selected = new Set(ids);
    this.sync();
  }

  sync() {
    for (const [id, { path, label }] of this.notes) {
      const on = this.selected.has(id);
      path.classList.toggle("is-selected", on);
      label.classList.toggle("is-selected", on);
      path.setAttribute("aria-checked", on);
    }
    this.showCaption();
  }

  showCaption(text) {
    const count = document.createElement("span");
    count.className = "wheel__count";
    count.textContent = text ? "" : this.selected.size;
    const caption = document.createElement("span");
    caption.className = "wheel__caption";
    caption.textContent = text ?? (this.selected.size === 1 ? "flavour" : "flavours");
    this.center.replaceChildren(...(text ? [caption] : [count, caption]));
  }

  describe(id) {
    return this.notes.get(id);
  }
}
