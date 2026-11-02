// Runs on every page: theme switch, navigation, flash messages, radars.
import { $, $$, flash } from "./lib/dom.js";
import { radar } from "./lib/radar.js";
import { toast } from "./lib/toast.js";

// --- Night edition ---------------------------------------------------------
const root = document.documentElement;
const themeButton = $("[data-theme-toggle]");
const isDark = () =>
  root.dataset.theme === "dark" || (!root.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
const syncThemeLabel = () => {
  const label = $("[data-theme-label]");
  if (label) label.textContent = isDark() ? "Day edition" : "Night edition";
};
themeButton?.addEventListener("click", () => {
  root.dataset.theme = isDark() ? "light" : "dark";
  try { localStorage.setItem("palate-theme", root.dataset.theme); } catch { /* private mode */ }
  syncThemeLabel();
});
syncThemeLabel();

// --- Navigation --------------------------------------------------------------
const navToggle = $("[data-nav-toggle]");
navToggle?.addEventListener("click", () => {
  const open = navToggle.getAttribute("aria-expanded") !== "true";
  navToggle.setAttribute("aria-expanded", open);
  $("#nav-links").classList.toggle("is-open", open);
});

// Reveal the compact logotype once the big masthead title scrolls away.
const bigTitle = $(".masthead__title");
const nav = $("[data-site-nav]");
if (bigTitle && nav) {
  new IntersectionObserver(([entry]) => nav.classList.toggle("is-scrolled", !entry.isIntersecting)).observe(bigTitle);
}

// --- Messages ------------------------------------------------------------------
$$("[data-messages] li").forEach((li) => toast(li.textContent, li.dataset.level.includes("error") ? "error" : "success"));
const carried = flash.take();
if (carried) toast(carried.message, carried.type);

// --- Server-rendered radars and flavour dots ----------------------------------------
$$("[data-radar]").forEach((node) => {
  radar(node, [{ values: JSON.parse(node.dataset.radar) }], {
    labels: node.hasAttribute("data-labels"),
    values: node.hasAttribute("data-values"),
    mini: node.hasAttribute("data-mini"),
  });
});

// --- Count-up numerals ---------------------------------------------------------------
const countUp = (node) => {
  const target = parseFloat(node.dataset.countTo);
  const decimals = (node.dataset.countTo.split(".")[1] || "").length;
  const start = performance.now();
  const tick = (now) => {
    const t = Math.min((now - start) / 1100, 1);
    node.textContent = (target * (1 - Math.pow(1 - t, 3))).toFixed(decimals);
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
};
const counters = new IntersectionObserver((entries) => {
  entries.filter((e) => e.isIntersecting).forEach((e) => { countUp(e.target); counters.unobserve(e.target); });
});
$$("[data-count-to]").forEach((n) => counters.observe(n));
