// Composer: create or edit a tasting through POST/PUT /api/tastings/.
// Dynamic parts: category-specific fields, flavour wheel, live radar,
// score verdict, character counter, local draft autosave, inline errors.
import { api, endpoints } from "../lib/api.js";
import { $, $$, debounce, flash, h, readJSON, verdict } from "../lib/dom.js";
import { radar } from "../lib/radar.js";
import { toast } from "../lib/toast.js";
import { FlavorWheel } from "../lib/wheel.js";

const form = $("[data-composer]");
const mode = form.dataset.mode;
const families = readJSON("wheel-data");
const schema = readJSON("detail-schema");
const initial = readJSON("initial-data");
const DRAFT_KEY = "palate-draft";
const MAX_FLAVORS = 12;

const detailsBox = $("[data-details]");
const selectedList = $("[data-selected]");
const selectedEmpty = $("[data-selected-empty]");
const status = $("[data-status]");
const errorsBox = $("[data-form-errors]");

let detailValues = {}; // remembers values per category while switching

// --- Category & particulars ---------------------------------------------------------
const category = () => form.category.value;

function renderDetails(values = {}) {
  const fields = schema[category()].map((f) => {
    const id = `d-${f.name}`;
    const control = f.type === "select"
      ? h("select", { class: "input", id, name: f.name },
          h("option", { value: "" }, "—"),
          f.choices.map((c) => h("option", { value: c.value, selected: values[f.name] === c.value }, c.label)))
      : h("input", { class: "input", id, name: f.name, type: f.type, value: values[f.name] ?? "", step: f.name === "abv" ? "0.1" : null, min: f.type === "number" ? 0 : null });
    return h("div", { class: "field", dataset: { field: `details.${f.name}` } },
      h("label", { class: "field__label", for: id }, f.label),
      control,
      h("span", { class: "field__error", dataset: { error: "" } }));
  });
  detailsBox.replaceChildren(...fields);
}

function collectDetails() {
  const out = {};
  for (const f of schema[category()]) {
    const raw = detailsBox.querySelector(`[name="${f.name}"]`)?.value.trim() ?? "";
    if (raw === "") continue;
    out[f.name] = f.type === "number" ? Number(raw) : raw;
  }
  return out;
}

function applyCategoryTone() {
  form.className = form.className.replace(/\bcat-\S+/g, "").trim();
  form.classList.add(`cat-${category()}`);
}

form.addEventListener("change", (e) => {
  if (e.target.name !== "category") return;
  const previous = form.dataset.category;
  if (previous) detailValues[previous] = collectDetails();
  form.dataset.category = category();
  renderDetails(detailValues[category()] ?? {});
  applyCategoryTone();
});

// --- Flavour wheel & selected list --------------------------------------------------------
const wheel = new FlavorWheel($("[data-wheel]"), families, {
  max: MAX_FLAVORS,
  onChange: () => { renderSelected(); saveDraft(); },
});

function renderSelected() {
  const ids = [...wheel.selected];
  selectedEmpty.hidden = ids.length > 0;
  selectedList.replaceChildren(...ids.map((id) => {
    const { note, family } = wheel.describe(id);
    return h("li", {},
      h("button", { type: "button", class: "chip", title: "Remove", onclick: () => wheel.toggle(id) },
        h("span", { class: "chip__dot", style: { "--dot": family.color } }), note.label, " ✕"));
  }));
}

// --- Profile sliders & live radar ------------------------------------------------------------
const sliders = $$("[data-sliders] input[type=range]");
const profile = () => Object.fromEntries(sliders.map((s) => [s.name.split(".")[1], Number(s.value)]));
const liveRadar = radar($("[data-live-radar]"), [{ values: profile() }], { labels: true, values: true });

function syncSlider(slider) {
  slider.nextElementSibling.textContent = slider.value;
  slider.style.setProperty("--fill", `${slider.value * 10}%`);
}
sliders.forEach((s) => {
  syncSlider(s);
  s.addEventListener("input", () => { syncSlider(s); liveRadar.update([{ values: profile() }]); });
});

// --- Score & notes ---------------------------------------------------------------------------
const scoreValue = $("[data-score-value]");
const scoreWord = $("[data-score-word]");
function syncScore() {
  const v = Number(form.score.value);
  scoreValue.textContent = v;
  scoreWord.textContent = verdict(v);
  form.score.style.setProperty("--fill", `${((v - 50) / 50) * 100}%`);
}
form.score.addEventListener("input", syncScore);

const notesCounter = $("[data-notes-counter]");
const syncNotes = () => { notesCounter.textContent = `${form.notes.value.length} / 4000`; };
form.notes.addEventListener("input", syncNotes);

// --- Payload, filling, drafts ------------------------------------------------------------------
function payload() {
  return {
    category: category(),
    name: form.name.value.trim(),
    producer: form.producer.value.trim(),
    origin: form.origin.value.trim(),
    score: Number(form.score.value),
    notes: form.notes.value.trim(),
    flavors: [...wheel.selected],
    profile: profile(),
    details: collectDetails(),
    is_public: form.is_public.checked,
  };
}

function fill(data) {
  const radio = form.querySelector(`[name=category][value="${data.category}"]`);
  if (radio) radio.checked = true;
  form.dataset.category = category();
  for (const key of ["name", "producer", "origin", "notes"]) form[key].value = data[key] ?? "";
  form.score.value = data.score ?? 85;
  form.is_public.checked = data.is_public ?? true;
  sliders.forEach((s) => { s.value = data.profile?.[s.name.split(".")[1]] ?? 5; syncSlider(s); });
  wheel.set(data.flavors ?? []);
  renderDetails(data.details ?? {});
  renderSelected();
  applyCategoryTone();
  syncScore();
  syncNotes();
  liveRadar.update([{ values: profile() }]);
}

const saveDraft = debounce(() => {
  if (mode !== "create") return;
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(payload()));
    status.textContent = `Draft saved · ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  } catch { /* storage unavailable: drafts are a convenience only */ }
}, 600);

function readDraft() {
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY)); } catch { return null; }
}
const clearDraft = () => { try { localStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ } };

form.addEventListener("input", saveDraft);

// --- Validation & submit ----------------------------------------------------------------------
function clearErrors() {
  errorsBox.hidden = true;
  errorsBox.replaceChildren();
  $$("[data-field]", form).forEach((f) => {
    f.classList.remove("has-error");
    const slot = $("[data-error]", f);
    if (slot) slot.textContent = "";
  });
}

function showError(path, message) {
  const field = form.querySelector(`[data-field="${path}"]`);
  const slot = field && $("[data-error]", field);
  if (slot) {
    field.classList.add("has-error");
    slot.textContent = message;
    return true;
  }
  return false;
}

function showErrors(data) {
  const loose = [];
  const walk = (obj, prefix = "") => {
    for (const [key, value] of Object.entries(obj)) {
      const path = prefix ? `${prefix}.${key}` : key;
      if (Array.isArray(value)) {
        if (!showError(path, value.join(" "))) loose.push(`${path}: ${value.join(" ")}`);
      } else if (value && typeof value === "object") walk(value, path);
      else if (!showError(path, String(value))) loose.push(String(value));
    }
  };
  walk(data);
  if (loose.length) {
    errorsBox.replaceChildren(h("ul", {}, loose.map((m) => h("li", {}, m))));
    errorsBox.hidden = false;
  }
  form.querySelector(".has-error, [data-form-errors]:not([hidden])")?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function validate(data) {
  const errors = {};
  if (!data.name) errors.name = ["Give the tasting a name."];
  if (data.name.length > 120) errors.name = ["Keep the name under 120 characters."];
  if (data.notes.length > 4000) errors.notes = ["Notes are limited to 4000 characters."];
  if (!data.flavors.length) errors.flavors = ["Pick at least one flavour on the wheel."];
  return errors;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearErrors();
  const data = payload();
  const clientErrors = validate(data);
  if (Object.keys(clientErrors).length) {
    showErrors(clientErrors);
    return;
  }

  const button = $("[data-submit]");
  button.classList.add("is-loading");
  try {
    const saved = mode === "edit"
      ? await api(endpoints.tasting(form.dataset.id), { method: "PUT", body: data })
      : await api(endpoints.tastings(), { method: "POST", body: data });
    clearDraft();
    flash.set(mode === "edit" ? "Changes saved." : "Tasting published.");
    location.href = saved.url;
  } catch (error) {
    if (error.status === 400) showErrors(error.data);
    else toast(error.message, "error");
  } finally {
    button.classList.remove("is-loading");
  }
});

// --- Boot -----------------------------------------------------------------------------------
if (initial) {
  fill(initial);
} else {
  form.dataset.category = category();
  renderDetails();
  applyCategoryTone();
  syncScore();
  renderSelected();
  const draft = readDraft();
  if (draft && (draft.name || draft.flavors?.length)) {
    fill(draft);
    toast("Restored your unsaved draft.", "info");
  }
}
