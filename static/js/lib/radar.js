// Hand-drawn SVG radar chart for the six-axis sensory profile.
// Supports several overlaid series and animates between values.

export const AXES = ["sweetness", "acidity", "bitterness", "body", "finish", "intensity"];
const NS = "http://www.w3.org/2000/svg";
const MAX = 10;

const svgEl = (tag, attrs = {}) => {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};

/**
 * @param {HTMLElement} container
 * @param {{values: Object, color?: string, label?: string}[]} series
 * @param {{labels?: boolean, values?: boolean, mini?: boolean}} options
 */
export function radar(container, series, { labels = true, values = false, mini = false } = {}) {
  const size = 300;
  const pad = labels ? 46 : 6;
  const c = size / 2;
  const r = c - pad;
  const angle = (i) => (-90 + (360 / AXES.length) * i) * (Math.PI / 180);
  const point = (i, v) => [c + Math.cos(angle(i)) * r * (v / MAX), c + Math.sin(angle(i)) * r * (v / MAX)];

  const svg = svgEl("svg", { viewBox: `0 0 ${size} ${size}`, class: `radar${mini ? " radar--mini" : ""}`, role: "img" });

  for (let ring = 2; ring <= MAX; ring += 2) {
    const pts = AXES.map((_, i) => point(i, ring).join(",")).join(" ");
    svg.append(svgEl("polygon", { points: pts, class: "radar__grid" }));
  }
  AXES.forEach((axis, i) => {
    const [x, y] = point(i, MAX);
    svg.append(svgEl("line", { x1: c, y1: c, x2: x, y2: y, class: "radar__spoke" }));
    if (labels) {
      const [lx, ly] = point(i, MAX + 2.6);
      const text = svgEl("text", { x: lx, y: ly, "text-anchor": "middle", "dominant-baseline": "middle", class: "radar__label" });
      text.textContent = axis;
      svg.append(text);
    }
  });

  const layers = series.map((s) => {
    const group = svgEl("g", { style: `--series: ${s.color ?? "var(--cat, var(--accent))"}` });
    const area = svgEl("polygon", { class: "radar__area" });
    const dots = AXES.map(() => svgEl("circle", { r: 3.5, class: "radar__point" }));
    const numbers = values ? AXES.map(() => svgEl("text", { class: "radar__value", "text-anchor": "middle" })) : [];
    group.append(area, ...dots, ...numbers);
    svg.append(group);
    return { area, dots, numbers, current: Object.fromEntries(AXES.map((a) => [a, 0])) };
  });

  const draw = (layer, vals) => {
    const pts = AXES.map((a, i) => point(i, vals[a]));
    layer.area.setAttribute("points", pts.map((p) => p.join(",")).join(" "));
    layer.dots.forEach((dot, i) => { dot.setAttribute("cx", pts[i][0]); dot.setAttribute("cy", pts[i][1]); });
    layer.numbers.forEach((num, i) => {
      const [x, y] = point(i, Math.max(vals[AXES[i]], 0) + 1.3);
      num.setAttribute("x", x);
      num.setAttribute("y", y);
      num.textContent = Math.round(vals[AXES[i]]);
    });
  };

  const animate = (layer, target) => {
    const from = { ...layer.current };
    const start = performance.now();
    const duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 420;
    const step = (now) => {
      const t = duration ? Math.min((now - start) / duration, 1) : 1;
      const ease = 1 - Math.pow(1 - t, 3);
      const vals = Object.fromEntries(AXES.map((a) => [a, from[a] + ((target[a] ?? 0) - from[a]) * ease]));
      draw(layer, vals);
      if (t < 1) requestAnimationFrame(step);
      else layer.current = { ...target };
    };
    requestAnimationFrame(step);
  };

  const update = (nextSeries) => {
    nextSeries.forEach((s, i) => layers[i] && animate(layers[i], s.values ?? {}));
    const description = nextSeries
      .map((s) => `${s.label ?? "Profile"}: ${AXES.map((a) => `${a} ${s.values?.[a] ?? 0}`).join(", ")}`)
      .join("; ");
    svg.setAttribute("aria-label", description);
  };

  container.replaceChildren(svg);
  update(series);
  return { update };
}
