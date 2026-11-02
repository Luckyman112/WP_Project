// Client-side rendering of a journal entry; mirrors templates/tastings/_entry.html.
import { h } from "./dom.js";
import { radar } from "./radar.js";

export function entryCard(t, index = 0) {
  const radarBox = h("div", { class: "entry__radar", "aria-hidden": "true" });
  radar(radarBox, [{ values: t.profile }], { labels: false, mini: true });

  const foot = [
    h("span", { class: "flavor-dots", "aria-hidden": "true" },
      t.flavor_details.map((f) => h("span", { style: { "--dot": f.color }, title: f.label }))),
  ];
  if (t.match_percent !== undefined) {
    foot.push(h("span", { class: "entry__match" }, `${t.match_percent}% kindred`));
  } else {
    foot.push(h("span", {}, `♥ ${t.like_count} · ✉ ${t.comment_count} · ${t.author.username}`));
  }

  return h("article", { class: `entry cat-${t.category}`, style: { "--i": index % 9 } },
    h("div", { class: "entry__meta" },
      h("span", { class: "cat-label" }, t.category_label),
      h("span", { class: "entry__no" }, `No. ${t.issue_number}`)),
    h("h3", { class: "entry__title" }, h("a", { href: t.url }, t.name)),
    h("span", { class: "entry__score numeral", "aria-label": `Score ${t.score} out of 100` }, t.score),
    h("p", { class: "entry__sub" }, [t.producer || "Unknown producer", t.origin].filter(Boolean).join(" · ")),
    radarBox,
    t.shared_flavors?.length
      ? h("p", { class: "entry__sub" }, `Shares ${t.shared_flavors.map((f) => f.label.toLowerCase()).join(", ")}`)
      : null,
    h("div", { class: "entry__foot" }, foot),
  );
}
