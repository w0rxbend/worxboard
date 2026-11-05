// worxboard page content: version, stats, downloads, gallery, docs and navigation, from manifest.json and
// layout.json. Kept apart from viewer.js (three.js, WebGL) so the page still fills in without them.
import { manifest, lay } from "./data.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const blob = (p) => `${manifest.repo}/blob/main/${p}`;
const SIDES = ["left", "right"];

// ---------- version and stats ----------
$("version").textContent = manifest.version;
$("footVersion").textContent = `build ${manifest.version}`;
const ob = lay.sides.right.outline.vertices;
const ext = (i) => Math.max(...ob.map((v) => v[i])) - Math.min(...ob.map((v) => v[i]));
$("sizeStat").textContent = `${ext(0).toFixed(1)} × ${ext(1).toFixed(1)}`;
$("keyStat").textContent = SIDES.reduce((a, s) => a + lay.sides[s].keys.length, 0);
const alu = ["right_top", "right_bottom"].map((n) => manifest.parts[n]?.mass_g);
if (alu.every((g) => typeof g === "number")) $("massStat").textContent = `≈ ${Math.round(alu[0] + alu[1])} g`;

// ---------- downloads under the viewer ----------
const downloads = Object.entries(manifest.parts).map(([n, p]) =>
  `<a class="part" href="${esc(p.file)}" download title="Download ${esc(n)}.stl"><b>${esc(p.label)}</b>` +
  `<span>${p.size.join(" × ")} mm</span><span>${p.mass_g ? `${p.mass_g} g · 6061` : p.material === "tpu" ? "TPU, 3D-printed" : `${p.volume_cm3} cm³ · print`} · STL ↓</span></a>`);
downloads.push(`<a class="part" href="layout.json" download><b>layout.json</b><span>schema ${esc(lay.schema)} · every key, hole, zone</span><span>the single source of truth ↓</span></a>`);
$("partlist").innerHTML = downloads.join("");

// ---------- gallery: filters and a lightbox ----------
const GROUPS = { pcb: "PCB", case: "Case", layout: "Layout", proof: "Placement proofs", other: "Other" };
const shots = manifest.gallery.map((s, i) => ({ ...s, i, group: s.group in GROUPS ? s.group : "other" }));
$("shots").innerHTML = shots.map((s) =>
  `<figure data-group="${s.group}"${s.wide ? ' class="wide"' : ""}>` +
  `<button type="button" data-i="${s.i}" aria-label="Enlarge: ${esc(s.caption)}"><img loading="lazy" src="${esc(s.file)}" alt="${esc(s.caption)}"></button>` +
  `<figcaption><span class="tag">${GROUPS[s.group]}</span>${esc(s.caption)}</figcaption></figure>`).join("");

const counts = shots.reduce((c, s) => ({ ...c, [s.group]: (c[s.group] || 0) + 1 }), {});
const filters = [["all", "All", shots.length], ...Object.keys(GROUPS).filter((g) => counts[g]).map((g) => [g, GROUPS[g], counts[g]])];
$("filters").innerHTML = filters.map(([g, label, n]) =>
  `<button type="button" data-filter="${g}" aria-pressed="${g === "all"}">${label}<span>${n}</span></button>`).join("");
let filter = "all";
$("filters").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-filter]");
  if (!b) return;
  filter = b.dataset.filter;
  for (const x of $("filters").children) x.setAttribute("aria-pressed", String(x === b));
  for (const f of $("shots").children) f.hidden = filter !== "all" && f.dataset.group !== filter;
});

const lb = $("lightbox");
let current = 0;
const visible = () => shots.filter((s) => filter === "all" || s.group === filter);
function show(i) {
  current = i;
  const s = shots[i];
  $("lbImg").src = s.file;
  $("lbImg").alt = s.caption;
  $("lbCap").textContent = s.caption;
}
function step(d) {
  const v = visible();
  const k = v.findIndex((s) => s.i === current);
  show(v[(k + d + v.length) % v.length].i);
}
$("shots").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-i]");
  if (!b) return;
  show(Number(b.dataset.i));
  if (typeof lb.showModal === "function") lb.showModal();
  else window.open(shots[current].file, "_blank", "noopener");
});
$("lbClose").addEventListener("click", () => lb.close());
$("lbPrev").addEventListener("click", () => step(-1));
$("lbNext").addEventListener("click", () => step(1));
lb.addEventListener("click", (e) => { if (e.target === lb || e.target.tagName === "FIGURE") lb.close(); });
lb.addEventListener("keydown", (e) => {
  if (e.key === "ArrowLeft") step(-1);
  if (e.key === "ArrowRight") step(1);
});

// ---------- documentation links ----------
const DOCS = [
  ["docs/buildguide_en.md", "Build guide", "Check, flash, plug in the displays, assemble"],
  ["docs/ordering-jlcpcb.md", "Ordering PCBs", "The JLCPCB turnkey order, step by step"],
  ["docs/shopping-list.md", "Shopping list", "The four orders and every off-board part"],
  ["docs/bom.md", "Bill of materials", "JLC parts, fees, gates (generated)"],
  ["docs/electrical.md", "Electrical design", "Power path, TRRS, USB-C, MCU, display"],
  ["docs/pinout.md", "Pinout", "GPIO map, TRRS, J3, part positions (generated)"],
  ["docs/matrix.md", "Key matrix", "6×7 per half, sockets, ZMK 6×14 transform (generated)"],
  ["docs/firmware.md", "Firmware", "ZMK builds, flashing, keymap, displays"],
  ["docs/case.md", "Case and plates", "build123d case, Z stack, files"],
  ["docs/legs.md", "Tent legs", "Mounts, positions, the custom leg"],
  ["docs/design.md", "Design spec", "The frozen rev A specification"],
  ["docs/deviations.md", "Deviations", "What changed from the spec, and why"],
  ["docs/verification.md", "Verification", "Integration results, CI, gates G1–G3"],
  ["docs/sources.md", "Sources", "Prior art and attribution"],
];
$("doclinks").innerHTML = DOCS.map(([p, t, d]) => `<a href="${blob(p)}">${t}<span>${d}</span></a>`).join("");

// ---------- copy the build commands ----------
$("copyCode").addEventListener("click", async (e) => {
  const text = $("codeBlock").textContent.split("\n").map((l) => l.replace(/^\$ /, "").replace(/\s+#.*$/, "")).join("\n");
  try {
    await navigator.clipboard.writeText(text);
    e.target.textContent = "copied";
  } catch {
    e.target.textContent = "copy failed";
  }
  setTimeout(() => { e.target.textContent = "copy"; }, 1600);
});

// ---------- highlight the section in view ----------
const links = new Map([...$("navlinks").querySelectorAll("a")].map((a) => [a.getAttribute("href").slice(1), a]));
const spy = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    for (const a of links.values()) a.classList.remove("on");
    links.get(e.target.id)?.classList.add("on");
  }
}, { rootMargin: "-40% 0px -55% 0px" });
for (const id of links.keys()) { const s = document.getElementById(id); if (s) spy.observe(s); }
