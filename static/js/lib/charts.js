// Minimal SVG / HTML charts in the journal's style (no chart library).
import { h } from "./dom.js";

const NS = "http://www.w3.org/2000/svg";
const svgEl = (tag, attrs = {}) => {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};

/** Vertical column chart. items: [{label, value, color?}] */
export function columns(container, items, { height = 220, format = (v) => v } = {}) {
  const width = 480;
  const top = 24;
  const bottom = 30;
  const max = Math.max(1, ...items.map((i) => i.value));
  const slot = width / Math.max(items.length, 1);
  const barWidth = Math.min(64, slot * 0.6);

  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart", role: "img" });
  svg.setAttribute("aria-label", items.map((i) => `${i.label}: ${format(i.value)}`).join(", "));

  items.forEach((item, idx) => {
    const barHeight = ((height - top - bottom) * item.value) / max;
    const x = idx * slot + (slot - barWidth) / 2;
    const y = height - bottom - barHeight;
    const bar = svgEl("rect", {
      x, y, width: barWidth, height: barHeight,
      class: "chart__bar",
      style: `--bar: ${item.color ?? "var(--ink)"}; animation-delay: ${idx * 60}ms`,
    });
    const value = svgEl("text", { x: x + barWidth / 2, y: y - 7, "text-anchor": "middle", class: "chart__value" });
    value.textContent = format(item.value);
    const label = svgEl("text", { x: x + barWidth / 2, y: height - 10, "text-anchor": "middle", class: "chart__label" });
    label.textContent = item.label;
    svg.append(bar, value, label);
  });
  svg.append(svgEl("line", { x1: 0, x2: width, y1: height - bottom, y2: height - bottom, class: "chart__axis" }));
  container.replaceChildren(svg);
}

/** Ranked horizontal bars as an accessible HTML list. */
export function hbars(container, items, { format = (v) => v } = {}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  const rows = items.map((item, idx) =>
    h("li", {},
      h("span", {}, item.label),
      h("span", { class: "hbars__track" },
        h("span", {
          class: "hbars__fill",
          style: { "--w": `${(item.value / max) * 100}%`, "--bar": item.color ?? "var(--ink)", "animation-delay": `${idx * 60}ms` },
        })),
      h("span", { class: "hbars__value" }, format(item.value)),
    ));
  if (container.matches("ul, ol")) container.replaceChildren(...rows);
  else container.replaceChildren(h("ul", { class: "hbars" }, rows));
}
