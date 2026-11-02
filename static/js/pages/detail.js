// Tasting article: savour (like), letters (comments), kindred tastes, delete.
import { api, endpoints } from "../lib/api.js";
import { entryCard } from "../lib/card.js";
import { $, $$, flash, h, timeAgo } from "../lib/dom.js";
import { toast } from "../lib/toast.js";

// --- Savour (optimistic like toggle) ------------------------------------------------
const likeButton = $("[data-like]");
likeButton?.addEventListener("click", async () => {
  if (likeButton.dataset.login) {
    location.href = likeButton.dataset.login;
    return;
  }
  const counter = $("[data-like-count]", likeButton);
  const wasLiked = likeButton.getAttribute("aria-pressed") === "true";
  const previous = Number(counter.textContent);

  likeButton.setAttribute("aria-pressed", !wasLiked);
  counter.textContent = previous + (wasLiked ? -1 : 1);
  try {
    const data = await api(endpoints.like(likeButton.dataset.id), { method: wasLiked ? "DELETE" : "POST" });
    counter.textContent = data.like_count;
  } catch (error) {
    likeButton.setAttribute("aria-pressed", wasLiked);
    counter.textContent = previous;
    toast(error.message, "error");
  }
});

// --- Letters (comments) ------------------------------------------------------------
const letters = $("[data-letters]");
const list = $("[data-letter-list]");
const letterCount = $("[data-letter-count]");
const letterForm = $("[data-letter-form]");

function letterItem(c) {
  const del = c.can_delete
    ? h("button", { type: "button", class: "letters__delete", onclick: () => removeLetter(c, item) }, "delete")
    : null;
  const item = h("li", { class: "letters__item" },
    h("div", { class: "letters__head" },
      h("a", { href: c.author_url }, c.author),
      h("span", {}, h("time", { datetime: c.created_at, title: new Date(c.created_at).toLocaleString() }, timeAgo(c.created_at)), del ? " · " : "", del)),
    h("p", {}, c.text));
  return item;
}

function updateLetterCount() {
  const n = list.children.length;
  letterCount.textContent = `${n} letter${n === 1 ? "" : "s"}`;
}

async function loadLetters() {
  try {
    const items = await api(endpoints.comments(letters.dataset.id));
    list.replaceChildren(...items.map(letterItem));
    updateLetterCount();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function removeLetter(c, node) {
  try {
    await api(endpoints.comment(letters.dataset.id, c.id), { method: "DELETE" });
    node.remove();
    updateLetterCount();
    toast("Letter deleted.", "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

if (letterForm) {
  const textarea = letterForm.text;
  const counter = $("[data-counter]", letterForm);
  textarea.addEventListener("input", () => {
    const n = textarea.value.length;
    counter.textContent = `${n} / 1000`;
    counter.classList.toggle("is-over", n > 1000);
  });

  letterForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = textarea.value.trim();
    if (!text) {
      textarea.focus();
      toast("Write something first.", "error");
      return;
    }
    const button = $("button[type=submit]", letterForm);
    button.classList.add("is-loading");
    try {
      const comment = await api(endpoints.comments(letters.dataset.id), { method: "POST", body: { text } });
      list.append(letterItem(comment));
      updateLetterCount();
      letterForm.reset();
      counter.textContent = "0 / 1000";
      toast("Letter sent.", "success");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      button.classList.remove("is-loading");
    }
  });
}

loadLetters();

// --- Kindred tastes ------------------------------------------------------------------
const kindred = $("[data-kindred]");
const kindredGrid = $("[data-kindred-grid]");

async function loadKindred(cross) {
  kindredGrid.setAttribute("aria-busy", "true");
  try {
    const items = await api(endpoints.similar(kindred.dataset.id, cross));
    kindredGrid.replaceChildren(
      ...(items.length ? items.map(entryCard) : [h("p", { class: "muted" }, "No kindred tastes yet.")]),
    );
  } catch (error) {
    toast(error.message, "error");
  } finally {
    kindredGrid.removeAttribute("aria-busy");
  }
}

$$("[data-cross]", kindred).forEach((button) =>
  button.addEventListener("click", () => {
    $$("[data-cross]", kindred).forEach((b) => {
      b.classList.toggle("is-active", b === button);
      b.setAttribute("aria-pressed", b === button);
    });
    loadKindred(button.dataset.cross === "1");
  }));

loadKindred(false);

// --- Delete with confirmation dialog -------------------------------------------------------
const deleteButton = $("[data-delete]");
const dialog = $("[data-delete-dialog]");
deleteButton?.addEventListener("click", () => dialog.showModal());
dialog?.addEventListener("close", async () => {
  if (dialog.returnValue !== "confirm") return;
  try {
    await api(endpoints.tasting(deleteButton.dataset.id), { method: "DELETE" });
    flash.set("Tasting deleted.");
    location.href = "/journal/";
  } catch (error) {
    toast(error.message, "error");
  }
});
