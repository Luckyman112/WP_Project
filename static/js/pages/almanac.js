// The Almanac: statistics computed by a single MongoDB $facet aggregation
// (GET /api/almanac/), re-fetched when the category filter changes.
import { api, endpoints } from "../lib/api.js";
import { columns, hbars } from "../lib/charts.js";
import { $, $$, h } from "../lib/dom.js";
import { radar } from "../lib/radar.js";
import { toast } from "../lib/toast.js";

const CATEGORY_COLORS = { coffee: "#6b4226", tea: "#56693a", chocolate: "#8a4b2f", wine: "#7b1e3a" };
const chart = (name) => $(`[data-chart="${name}"]`);

function totals(t) {
  const items = [
    ["Tastings", t.tastings],
    ["Average score", t.avg_score],
    ["Origins", t.origins],
    ["Contributors", t.authors],
  ];
  $("[data-almanac-totals]").replaceChildren(...items.map(([label, value]) =>
    h("div", { class: "numbers__item" },
      h("span", { class: "numbers__value numeral" }, value),
      h("span", { class: "numbers__label" }, label))));
}

function empty(node) {
  node.replaceChildren(h("p", { class: "muted" }, "Not enough data yet."));
}

async function load(category = "") {
  try {
    const data = await api(endpoints.almanac(category));
    totals(data.totals);

    if (data.by_category.length) {
      columns(chart("categories"), data.by_category.map((c) => ({ label: c.label, value: c.count, color: CATEGORY_COLORS[c.category] })));
    } else empty(chart("categories"));

    columns(chart("scores"), data.score_buckets.map((b) => ({ label: b.label, value: b.count, color: "var(--accent)" })));
    hbars(chart("families"), data.families.map((f) => ({ label: f.label, value: f.count, color: f.color })));

    const ranking = h("ol", { class: "ranking" }, data.top_flavors.map((f) =>
      h("li", {},
        h("a", { href: `/journal/?flavor=${encodeURIComponent(f.id)}` }, f.label),
        h("span", { class: "muted" }, f.family_label),
        h("span", { class: "ranking__count" }, `× ${f.count}`))));
    data.top_flavors.length ? chart("flavors").replaceChildren(ranking) : empty(chart("flavors"));

    const series = data.by_category.map((c) => ({ values: c.profile, color: CATEGORY_COLORS[c.category], label: c.label }));
    if (series.length) {
      const box = chart("profiles");
      // Series count can change with the filter, so redraw instead of animating.
      radar(box, series, { labels: true });
      box.append(h("div", { class: "legend" }, series.map((s) => h("span", { style: { "--series": s.color } }, s.label))));
    } else empty(chart("profiles"));

    hbars(chart("origins"), data.top_origins.map((o) => ({ label: o.origin, value: o.count })), { format: (v) => `${v} entr${v === 1 ? "y" : "ies"}` });
  } catch (error) {
    toast(error.message, "error");
  }
}

$("[data-almanac-filter]").addEventListener("click", (e) => {
  const button = e.target.closest("[data-category]");
  if (!button) return;
  $$("[data-category]", e.currentTarget).forEach((b) => {
    b.classList.toggle("is-active", b === button);
    b.setAttribute("aria-pressed", b === button);
  });
  load(button.dataset.category);
});

load();
