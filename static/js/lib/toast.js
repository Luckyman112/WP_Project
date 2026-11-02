import { h } from "./dom.js";

const ICONS = { success: "✓", error: "!", info: "§" };

export function toast(message, type = "info", timeout = 4200) {
  const region = document.querySelector("[data-toasts]");
  if (!region) return;

  const close = () => {
    node.classList.add("is-leaving");
    node.addEventListener("animationend", () => node.remove(), { once: true });
  };
  const node = h(
    "div",
    { class: `toast toast--${type}`, role: type === "error" ? "alert" : "status" },
    h("span", { "aria-hidden": "true" }, ICONS[type] ?? ICONS.info),
    h("span", {}, message),
    h("button", { type: "button", "aria-label": "Dismiss", onclick: close }, "✕"),
  );
  region.append(node);
  if (timeout) setTimeout(close, timeout);
}
