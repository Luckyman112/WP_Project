// Small DOM helpers. All user content is inserted with textContent, never
// innerHTML, so data from the API cannot inject markup.

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

/**
 * h("a", { href: "/x", class: "link", dataset: { id: 1 } }, "text", childNode)
 */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key === "style" && typeof value === "object") {
      for (const [prop, v] of Object.entries(value)) el.style.setProperty(prop, v);
    } else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

export function debounce(fn, wait = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

const dateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" });
const relativeFormat = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export const formatDate = (iso) => dateFormat.format(new Date(iso));

export function timeAgo(iso) {
  const seconds = Math.round((new Date(iso) - Date.now()) / 1000);
  const units = [["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60]];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return relativeFormat.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

const VERDICTS = [[95, "Transcendent"], [90, "Outstanding"], [85, "Excellent"], [80, "Very good"], [70, "Good"], [0, "Curious"]];
export const verdict = (score) => VERDICTS.find(([threshold]) => score >= threshold)[1];

export const readJSON = (id) => {
  const node = document.getElementById(id);
  return node ? JSON.parse(node.textContent) : null;
};

/** One-shot flash message carried across a page navigation. */
export const flash = {
  set(message, type = "success") {
    try { sessionStorage.setItem("palate-flash", JSON.stringify({ message, type })); } catch { /* storage unavailable */ }
  },
  take() {
    try {
      const raw = sessionStorage.getItem("palate-flash");
      sessionStorage.removeItem("palate-flash");
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  },
};
