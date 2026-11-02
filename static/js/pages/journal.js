// The Journal: live search, filter chips, score range, sorting and
// infinite scroll — all backed by GET /api/tastings/ and mirrored in the URL
// so a filtered view can be bookmarked or shared.
import { api, endpoints } from "../lib/api.js";
import { entryCard } from "../lib/card.js";
import { $, $$, debounce, h, readJSON } from "../lib/dom.js";
import { toast } from "../lib/toast.js";

const form = $("[data-filters]");
const results = $("[data-results]");
const grid = $("[data-grid]");
const countLabel = $("[data-count]");
const emptyState = $("[data-empty]");
const moreButton = $("[data-more]");
const scoreOut = $("[data-score-out]");
const flavorNames = Object.fromEntries((readJSON("wheel-data") ?? []).flatMap((f) => f.notes.map((n) => [n.id, n.label])));

const state = {
  q: "",
  category: new Set(),
  family: "",
  flavor: "",
  min_score: 50,
  sort: "newest",
  liked: false,
};
let nextUrl = null;
let controller = null;
let loading = false;

// --- URL <-> state --------------------------------------------------------------
function readUrl() {
  const p = new URLSearchParams(location.search);
  state.q = p.get("q") ?? "";
  state.category = new Set((p.get("category") ?? "").split(",").filter(Boolean));
  state.family = p.get("family") ?? "";
  state.flavor = p.get("flavor") ?? "";
  state.min_score = Number(p.get("min_score") ?? 50);
  state.sort = p.get("sort") ?? "newest";
  state.liked = p.get("liked") === "1";
}

function toParams() {
  const p = new URLSearchParams();
  if (state.q) p.set("q", state.q);
  if (state.category.size) p.set("category", [...state.category].join(","));
  if (state.family) p.set("family", state.family);
  if (state.flavor) p.set("flavor", state.flavor);
  if (state.min_score > 50) p.set("min_score", state.min_score);
  if (state.sort !== "newest") p.set("sort", state.sort);
  if (state.liked) p.set("liked", "1");
  return p;
}

function syncControls() {
  form.q.value = state.q;
  form.sort.value = state.sort;
  form.min_score.value = state.min_score;
  if (form.liked) form.liked.checked = state.liked;
  $$("[data-category]", form).forEach((b) => b.setAttribute("aria-pressed", state.category.has(b.dataset.category)));
  $$("[data-family]", form).forEach((b) => b.setAttribute("aria-pressed", b.dataset.family === state.family));
  updateScoreOutput();
}

function updateScoreOutput() {
  const v = Number(form.min_score.value);
  scoreOut.textContent = v > 50 ? `${v}+` : "Any";
  form.min_score.style.setProperty("--fill", `${((v - 50) / 50) * 100}%`);
}

// --- Fetching ---------------------------------------------------------------------
async function load({ append = false } = {}) {
  controller?.abort();
  controller = new AbortController();
  loading = true;
  results.classList.add("is-loading");
  const params = toParams();
  if (!append) history.replaceState(null, "", params.toString() ? `?${params}` : location.pathname);

  try {
    const data = await api(append ? nextUrl : endpoints.tastings(params.toString()), { signal: controller.signal });
    nextUrl = data.next;
    const offset = append ? grid.children.length : 0;
    const cards = data.results.map((t, i) => entryCard(t, offset + i));
    if (append) grid.append(...cards);
    else grid.replaceChildren(...cards);
    renderCount(data.count);
    emptyState.hidden = data.count > 0;
    moreButton.hidden = !nextUrl;
  } catch (error) {
    if (error.name !== "AbortError") toast(error.message, "error");
  } finally {
    loading = false;
    results.classList.remove("is-loading");
  }
}

function renderCount(count) {
  const parts = [`${count} ${count === 1 ? "entry" : "entries"}`];
  countLabel.replaceChildren(parts[0]);
  if (state.flavor) {
    countLabel.append(" noting ",
      h("button", { type: "button", class: "chip is-active", onclick: () => { state.flavor = ""; load(); } },
        `${flavorNames[state.flavor] ?? state.flavor} ✕`));
  }
}

const reload = debounce(() => load(), 300);

// --- Events ---------------------------------------------------------------------------
form.addEventListener("submit", (e) => e.preventDefault());
form.q.addEventListener("input", () => { state.q = form.q.value.trim(); reload(); });
form.sort.addEventListener("change", () => { state.sort = form.sort.value; load(); });
form.min_score.addEventListener("input", () => { updateScoreOutput(); state.min_score = Number(form.min_score.value); reload(); });
form.liked?.addEventListener("change", () => { state.liked = form.liked.checked; load(); });

form.addEventListener("click", (e) => {
  const cat = e.target.closest("[data-category]");
  const fam = e.target.closest("[data-family]");
  if (cat) {
    const v = cat.dataset.category;
    state.category.has(v) ? state.category.delete(v) : state.category.add(v);
  } else if (fam) {
    state.family = state.family === fam.dataset.family ? "" : fam.dataset.family;
  } else return;
  syncControls();
  load();
});

form.addEventListener("reset", (e) => {
  e.preventDefault();
  Object.assign(state, { q: "", category: new Set(), family: "", flavor: "", min_score: 50, sort: "newest", liked: false });
  syncControls();
  load();
});

moreButton.addEventListener("click", () => nextUrl && load({ append: true }));

// Infinite scroll: fetch the next page when the sentinel enters the viewport.
new IntersectionObserver(([entry]) => {
  if (entry.isIntersecting && nextUrl && !loading) load({ append: true });
}, { rootMargin: "400px" }).observe($("[data-sentinel]"));

readUrl();
syncControls();
load();
