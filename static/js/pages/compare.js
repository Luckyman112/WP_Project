// Side by side: overlay two tastings' radars and diff their profiles.
import { api, endpoints } from "../lib/api.js";
import { $, h, verdict } from "../lib/dom.js";
import { AXES, radar } from "../lib/radar.js";
import { toast } from "../lib/toast.js";

const form = $("[data-compare-form]");
const stage = $("[data-compare-stage]");
const empty = $("[data-compare-empty]");
const COLORS = { a: "var(--accent)", b: "var(--ink)" };
let chart = null;

function side(key, t) {
  return h("div", { class: `cat-${t.category}` },
    h("span", { class: "cat-label" }, t.category_label),
    h("h2", {}, h("a", { href: t.url }, t.name)),
    h("p", { class: "muted" }, [t.producer, t.origin].filter(Boolean).join(" · ")),
    h("p", {}, h("span", { class: "numeral", style: { "font-size": "3rem", color: "var(--cat)" } }, t.score), " ", h("em", {}, verdict(t.score))),
    h("div", { class: "legend" }, h("span", { style: { "--series": COLORS[key] } }, key === "a" ? "First" : "Second")),
    h("ul", { class: "flavor-list", style: { "margin-top": "1rem" } },
      t.flavor_details.map((f) => h("li", { class: "chip" }, h("span", { class: "chip__dot", style: { "--dot": f.color } }), f.label))));
}

function diffRow(axis, a, b) {
  const delta = a - b;
  const width = Math.abs(delta) * 5;
  return h("li", {},
    h("span", { class: "kicker" }, axis),
    h("span", { class: "diff-bar" },
      h("span", { style: { "--series": delta >= 0 ? COLORS.a : COLORS.b, left: delta >= 0 ? "50%" : `${50 - width}%`, width: `${width}%` } })),
    h("span", { class: "mono" }, delta > 0 ? `+${delta}` : String(delta)));
}

async function render() {
  const a = form.a.value;
  const b = form.b.value;
  const params = new URLSearchParams();
  if (a) params.set("a", a);
  if (b) params.set("b", b);
  history.replaceState(null, "", params.toString() ? `?${params}` : location.pathname);

  if (!a || !b) {
    stage.hidden = true;
    empty.hidden = false;
    return;
  }
  try {
    const [ta, tb] = await Promise.all([api(endpoints.tasting(a)), api(endpoints.tasting(b))]);
    stage.hidden = false;
    empty.hidden = true;
    $('[data-side="a"]').replaceChildren(side("a", ta));
    $('[data-side="b"]').replaceChildren(side("b", tb));

    const series = [
      { values: ta.profile, color: COLORS.a, label: ta.name },
      { values: tb.profile, color: COLORS.b, label: tb.name },
    ];
    if (chart) chart.update(series);
    else chart = radar($("[data-compare-radar]"), series, { labels: true });

    $("[data-compare-legend]").replaceChildren(
      h("span", { style: { "--series": COLORS.a } }, ta.name),
      h("span", { style: { "--series": COLORS.b } }, tb.name));
    $("[data-compare-diff]").replaceChildren(...AXES.map((axis) => diffRow(axis, ta.profile[axis], tb.profile[axis])));

    const shared = ta.flavor_details.filter((f) => tb.flavors.includes(f.id));
    const union = new Set([...ta.flavors, ...tb.flavors]).size || 1;
    const distance = AXES.reduce((sum, axis) => sum + Math.abs(ta.profile[axis] - tb.profile[axis]), 0);
    const kinship = Math.round(((shared.length / union) * 0.6 + (1 - distance / 60) * 0.4) * 100);
    $("[data-compare-shared]").replaceChildren(
      h("span", { class: "kicker" }, "Kinship"),
      h("p", { class: "numeral", style: { "font-size": "4rem", margin: 0 } }, `${kinship}%`),
      h("p", { class: "muted" }, shared.length
        ? `Both note ${shared.map((f) => f.label.toLowerCase()).join(", ")}.`
        : "No flavours in common — a study in contrast."));
  } catch (error) {
    toast(error.message, "error");
  }
}

form.addEventListener("change", render);
render();
