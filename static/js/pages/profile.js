// Contributor page: palate fingerprint (aggregation) + their tastings.
import { api, endpoints } from "../lib/api.js";
import { entryCard } from "../lib/card.js";
import { $ } from "../lib/dom.js";
import { hbars } from "../lib/charts.js";
import { radar } from "../lib/radar.js";
import { toast } from "../lib/toast.js";

const root = $("[data-palate]");
const username = root.dataset.username;
const grid = $("[data-palate-grid]");
const more = $("[data-more]");
let nextUrl = null;

async function loadPalate() {
  try {
    const p = await api(endpoints.palate(username));
    if (!p.count) {
      $("[data-palate-summary]").textContent = "No tastings yet — the palate is a blank page.";
      $("[data-palate-radar]").replaceChildren();
      return;
    }
    const top = p.families[0]?.label.toLowerCase();
    $("[data-palate-summary]").textContent =
      `${p.count} tasting${p.count === 1 ? "" : "s"} across ${p.categories.length} categor${p.categories.length === 1 ? "y" : "ies"}, ` +
      `averaging ${p.avg_score}.${top ? ` Drawn above all to ${top} notes.` : ""}`;
    radar($("[data-palate-radar]"), [{ values: p.profile, label: username }], { labels: true, values: true });
    hbars($("[data-palate-families]"), p.families.map((f) => ({ label: f.label, value: f.count, color: f.color })));
  } catch (error) {
    toast(error.message, "error");
  }
}

async function loadTastings(url = endpoints.tastings(`author=${encodeURIComponent(username)}`)) {
  try {
    const data = await api(url);
    const offset = grid.children.length;
    grid.append(...data.results.map((t, i) => entryCard(t, offset + i)));
    $("[data-palate-count]").textContent = `${data.count} in the journal`;
    nextUrl = data.next;
    more.hidden = !nextUrl;
  } catch (error) {
    toast(error.message, "error");
  }
}

more.addEventListener("click", () => nextUrl && loadTastings(nextUrl));
loadPalate();
loadTastings();
