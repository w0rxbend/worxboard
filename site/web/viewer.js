// worxboard viewer: one WebGL canvas with two drivers. In the story at the top of the page the scroll
// position moves the camera and the model through one shot per chapter; in the "explore" section the
// visitor drives it with orbit controls and the panel. The canvas moves between the two stages, so the
// page keeps a single renderer and a single copy of the model (model.js). Loaded by page.js, which shows
// the static fallback when this module fails.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { lay } from "./data.js";
import { EFFECTS, FINISHES, LAYERS, PAIR_DX, PAIR_GAP, buildModel, clip, explodeTravel, hasCase, hasRole, highlight } from "./model.js";

const $ = (id) => document.getElementById(id);
const canvas = $("canvas");
const stages = { story: $("stage"), explore: $("viewer") };
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const lerp = THREE.MathUtils.lerp;

// ---------- shots: one camera and model pose per story chapter ----------
// at: what the camera looks at; dir: from there to the camera (CAD frame: +x right, +y away, +z up);
// frame: which extent the distance 1 fits; shift: where the subject sits, in viewport fractions from the
// centre (wide screens; a narrow one uses shiftNarrow); glow and dim run 0..1.
const SHOTS = {
  top: { at: "pair", dir: [0, -0.95, 1], frame: "pair", dist: 1.08, shift: [0, 0.15], shiftNarrow: [0, 0.1], spread: 0, explode: 0, legs: 0, swing: 90, glow: 0.75, dim: 0.72 },
  aluminium: { at: "right", dir: [0.95, -1, 0.42], frame: "half", dist: 1.2, shift: [0.17, 0.04], spread: 1, explode: 0, legs: 0, swing: 90, glow: 0, dim: 0 },
  light: { at: "pair", dir: [0.45, -0.85, 0.95], frame: "pair", dist: 1.42, shift: [0.15, 0.02], spread: 0, explode: 0, legs: 0, swing: 90, glow: 1, dim: 1 },
  display: { at: "display", dir: [-0.3, -0.75, 1], frame: "half", dist: 0.42, shift: [0.2, 0], spread: 1, explode: 0, legs: 0, swing: 90, glow: 0.5, dim: 0.55 },
  inside: { at: "exploded", dir: [-0.75, -1, 0.5], frame: "half", dist: 1.36, shift: [0.15, 0.03], spread: 1, explode: 1, legs: 0, swing: 90, glow: 0.45, dim: 0.3 },
  tent: { at: "right", dir: [0.8, -1, 0.3], frame: "half", dist: 1.3, shift: [0.17, 0], spread: 1, explode: 0, legs: 1, swing: 90, glow: 0.6, dim: 0.45 },
};
const SHOT_NARROW_SHIFT = [0, -0.12];   // a narrow screen keeps the subject above the copy
const NARROW = 760;                     // px; matches the stylesheet's breakpoint
const HOLD = 0.3;                       // share of a chapter's scroll, either side of its middle, that holds the shot
const EASE_RATE = 5;                    // 1/s: how fast the pose follows the scroll
// camera presets of the explore stage: direction from the target
const VIEWS = {
  iso: (scene) => [scene === "pair" ? 0 : -0.25, -0.8, 1.25],
  top: () => [0, -0.02, 1],
  front: () => [0, -1, 0.42],
  side: (scene) => [scene === "left" ? -1 : 1, -0.35, 0.3],
};
const LIGHT = {   // [bright studio, dimmed room]
  key: [2.0, 0.3], hemi: [0.5, 0.1], rim: [0.7, 0.4], env: [1.0, 0.28],
};

const state = {
  scene: "pair", finish: "black", view: "iso", explode: 0, section: 0, swing: 90,
  effect: "swirl", hue: 18, glow: 0.6,
  caps: true, legends: true, switches: true, pcb: true, top: true, spacer: true, bottom: true,
  legs: true, edges: false, spin: false,
};
for (const kv of location.hash.slice(1).split("&")) {
  const [k, v] = kv.split("=");
  if (k === "scene" && ["pair", "right", "left"].includes(v)) state.scene = v;
  if (k === "finish" && v in FINISHES) state.finish = v;
  if (k === "view" && v in VIEWS) state.view = v;
}

// ---------- renderer, scene, camera ----------
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, innerWidth < NARROW ? 1.5 : 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);   // black survives tone mapping, so the canvas has no visible edge on the page
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(30, 1, 1, 8000);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.autoRotateSpeed = 1.2;
controls.enabled = false;

const key = new THREE.DirectionalLight(0xffffff, LIGHT.key[0]);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.bias = -0.0004;
const hemi = new THREE.HemisphereLight(0xdde6ff, 0x20160f, LIGHT.hemi[0]);
const rim = new THREE.DirectionalLight(0xbfd4ff, LIGHT.rim[0]);
rim.position.set(300, 500, 160);
scene.add(key, key.target, hemi, rim);

// the floor: a lit disc that fades to the black background, so the model stands in a pool of light
const floor = new THREE.Mesh(new THREE.CircleGeometry(1, 96),
  new THREE.MeshStandardMaterial({ color: 0x1d1f23, roughness: 0.85, metalness: 0, transparent: true, alphaMap: floorFade() }));
floor.receiveShadow = true;
scene.add(floor);

function floorFade() {
  const size = 256;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "#fff");
  g.addColorStop(0.3, "#666");
  g.addColorStop(0.62, "#111");
  g.addColorStop(0.8, "#000");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(c);
}

// bloom spreads the LED light; tone mapping moves to the output pass
const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }));
const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.8, 0.7, 1.0);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(bloom);
composer.addPass(new OutputPass());
renderer.toneMapping = THREE.ACESFilmicToneMapping;

// ---------- model ----------
const model = await buildModel((p) => { $("loadbar").style.width = `${(p * 100).toFixed(0)}%`; });
scene.add(model.root);
model.setFinish(state.finish);

const REST = { scene: "pair", spread: 0, explode: 0, legs: 0, swing: 90 };
model.setPose(REST);
const pairBox = model.box();
const pairSize = pairBox.getSize(new THREE.Vector3());
const pairCentre = pairBox.getCenter(new THREE.Vector3());
const halfSize = new THREE.Vector3((pairSize.x - PAIR_GAP) / 2, pairSize.y, pairSize.z);
const rightCentre = new THREE.Vector3(pairBox.max.x - halfSize.x / 2, pairCentre.y, pairCentre.z);
const ANCHORS = {
  pair: pairCentre,
  right: rightCentre,
  display: model.displayCentre,
  exploded: rightCentre.clone().setZ(pairCentre.z + explodeTravel / 2),
};
floor.scale.setScalar(pairSize.x * 1.5);
const shadowReach = pairSize.x * 0.75;
Object.assign(key.shadow.camera, { left: -shadowReach, right: shadowReach, top: shadowReach, bottom: -shadowReach, near: 1, far: 4000 });
key.shadow.camera.updateProjectionMatrix();
key.position.copy(pairCentre).add(new THREE.Vector3(-0.4, -0.6, 1).multiplyScalar(pairSize.x * 1.4));
key.target.position.copy(pairCentre);

/** Distance at which a w × d footprint, seen from above, fills the view. */
function fitDistance(w, d) {
  const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  return Math.max(w / 2 / (tanV * camera.aspect), d / 2 / tanV) * 1.12;
}

function setLights(dim) {
  key.intensity = lerp(...LIGHT.key, dim);
  hemi.intensity = lerp(...LIGHT.hemi, dim);
  rim.intensity = lerp(...LIGHT.rim, dim);
  scene.environmentIntensity = lerp(...LIGHT.env, dim);
}

/** Put the floor under the lowest visible solid (the legs, when they point down). */
function settleFloor() {
  const box = model.box();
  floor.position.set(pairCentre.x, pairCentre.y, box.isEmpty() ? 0 : box.min.z - 0.05);
  return box;
}

// ---------- story: the scroll drives the pose ----------
const chapters = [...document.querySelectorAll(".chapter[data-shot]")];
const isNarrow = () => innerWidth < NARROW;

/** The pose the scroll position asks for: the shot of the chapter in view, blended with its neighbour between the holds. */
function scrollPose() {
  const mid = innerHeight / 2;
  const centres = chapters.map((c) => { const r = c.getBoundingClientRect(); return (r.top + r.bottom) / 2; });
  let i = centres.findIndex((c) => c > mid);   // first chapter whose middle is still below the viewport's
  if (i === -1) i = chapters.length;
  const a = SHOTS[chapters[Math.max(i - 1, 0)].dataset.shot];
  const b = SHOTS[chapters[Math.min(i, chapters.length - 1)].dataset.shot];
  const span = i > 0 && i < chapters.length ? (mid - centres[i - 1]) / (centres[i] - centres[i - 1]) : 0;
  const t = THREE.MathUtils.smoothstep(span, HOLD, 1 - HOLD);
  const shift = (s) => (isNarrow() ? s.shiftNarrow ?? SHOT_NARROW_SHIFT : s.shift);
  const dist = (s) => s.dist * (s.frame === "pair" ? fitDistance(pairSize.x, pairSize.y) : fitDistance(halfSize.x, halfSize.y));
  return {
    target: ANCHORS[a.at].clone().lerp(ANCHORS[b.at], t),
    dir: new THREE.Vector3(...a.dir).normalize().lerp(new THREE.Vector3(...b.dir).normalize(), t).normalize(),
    dist: lerp(dist(a), dist(b), t),
    shiftX: lerp(shift(a)[0], shift(b)[0], t), shiftY: lerp(shift(a)[1], shift(b)[1], t),
    spread: lerp(a.spread, b.spread, t), explode: lerp(a.explode, b.explode, t), legs: lerp(a.legs, b.legs, t), swing: lerp(a.swing, b.swing, t),
    glow: lerp(a.glow, b.glow, t), dim: lerp(a.dim, b.dim, t),
  };
}

let pose = null;   // the eased story pose; null until the first story frame
function easePose(goal, dt) {
  if (!pose || reducedMotion.matches) return goal;
  const k = 1 - Math.exp(-dt * EASE_RATE);
  const out = {};
  for (const [name, v] of Object.entries(goal)) {
    out[name] = v.isVector3 ? pose[name].clone().lerp(v, k) : lerp(pose[name], v, k);
  }
  out.dir.normalize();
  return out;
}

const tags = [...document.querySelectorAll("#tags [data-layer]")];
const tagPoint = new THREE.Vector3();
/** Pin each layer's label beside that layer of the exploded right half. */
function placeTags(opacity) {
  $("tags").style.opacity = opacity;
  if (opacity <= 0) return;
  const right = model.halves.get("right");
  const w = canvas.clientWidth, h = canvas.clientHeight;
  for (const tag of tags) {
    const layer = right.userData[tag.dataset.layer];
    // the half's own frame: its outer edge is the pair's, less the half's place in the pair
    tagPoint.set(pairBox.max.x - PAIR_DX + 6, pairCentre.y, Number(tag.dataset.z)).applyMatrix4(layer.matrixWorld).project(camera);
    tag.style.transform = `translate(${((tagPoint.x + 1) / 2 * w).toFixed(1)}px, ${((1 - tagPoint.y) / 2 * h).toFixed(1)}px) translateY(-50%)`;
  }
}

function storyFrame(dt, time) {
  pose = easePose(scrollPose(), dt);
  model.setPose({ scene: "pair", spread: pose.spread, explode: pose.explode, legs: pose.legs, swing: pose.swing });
  settleFloor();
  setLights(pose.dim);
  showGlow(pose.glow, time);
  const w = canvas.clientWidth, h = canvas.clientHeight;
  camera.near = pose.dist / 50; camera.far = pose.dist * 20;
  camera.setViewOffset(w, h, -pose.shiftX * w, -pose.shiftY * h, w, h);
  camera.position.copy(pose.target).addScaledVector(pose.dir, pose.dist);
  camera.lookAt(pose.target);
  camera.updateMatrixWorld();
  placeTags(THREE.MathUtils.smoothstep(pose.explode, 0.6, 0.95));
}

// ---------- LEDs ----------
let glowHueShown = -1;
function showGlow(level, time) {
  const hue = model.setGlow(state.effect, state.hue, level, reducedMotion.matches ? 0 : time);
  // the page takes its accent from the light the keyboard shows
  if (Math.abs(hue - glowHueShown) > 2) {
    glowHueShown = hue;
    document.documentElement.style.setProperty("--glow", `hsl(${hue.toFixed(0)} 95% 62%)`);
  }
}

// ---------- explore: the visitor drives ----------
let exploreBox = new THREE.Box3();

function applyExplore() {
  model.setPose({ scene: state.scene, spread: 0, explode: state.explode, legs: 1, swing: state.swing });
  model.setVisible(state);
  model.setSection(state.section > 0);
  exploreBox = settleFloor();
  if (state.section > 0 && !exploreBox.isEmpty()) {
    const y = exploreBox.min.y + state.section * (exploreBox.max.y - exploreBox.min.y);
    clip.constant = -y;
    $("sectionVal").textContent = `y ${y.toFixed(1)}`;
  } else $("sectionVal").textContent = "off";
  $("explodeVal").textContent = state.explode ? `${Math.round(state.explode * explodeTravel)} mm` : "0";
  $("swingVal").textContent = `${state.swing}°`;
  $("glowVal").textContent = state.glow ? `${Math.round(state.glow * 100)} %` : "off";
  controls.autoRotate = state.spin && !reducedMotion.matches;
  setLights(state.glow * 0.6);
  hud();
}

function hud() {
  if (exploreBox.isEmpty()) { $("hud").textContent = "nothing visible"; return; }
  const s = exploreBox.getSize(new THREE.Vector3());
  const shown = [...model.halves.values()].filter((h) => h.visible).length;
  $("hud").textContent =
    `${s.x.toFixed(1)} × ${s.y.toFixed(1)} × ${s.z.toFixed(1)} mm\n` +
    `${shown * lay.sides.left.keys.length} keys, ${hasCase ? `${FINISHES[state.finish].name.toLowerCase()} case` : "case not in this build"}`;
}

/** Width of the explore stage the panel leaves free, px. */
const freeWidth = () => (canvas.clientWidth > NARROW ? $("panel").offsetLeft : canvas.clientWidth);

/** Point the camera at everything visible, from the chosen preset. */
function frameExplore() {
  if (exploreBox.isEmpty()) return;
  const size = exploreBox.getSize(new THREE.Vector3());
  const centre = exploreBox.getCenter(new THREE.Vector3());
  const dist = fitDistance(size.x * canvas.clientWidth / freeWidth(), size.y + size.z);
  controls.target.copy(centre);
  camera.position.copy(centre).addScaledVector(new THREE.Vector3(...VIEWS[state.view](state.scene)).normalize(), dist);
  camera.near = dist / 100; camera.far = dist * 20;
  controls.update();
}

// picking: hover a part to read what it is
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let picked = null, pickQueued = false;
const isShown = (o) => { for (; o; o = o.parent) if (!o.visible) return false; return true; };
function pick(ev) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(model.pickable.filter(isShown), false)
    .find((h) => state.section === 0 || clip.distanceToPoint(h.point) >= 0);
  return hit ? { mesh: hit.object, x: ev.clientX - r.left, y: ev.clientY - r.top } : null;
}
function setPicked(hit) {
  if (picked) picked.material = picked.userData.mat;
  picked = hit?.mesh || null;
  const tip = $("tooltip");
  if (!picked) { tip.classList.remove("on"); return; }
  picked.material = highlight;
  tip.textContent = picked.userData.info;
  tip.style.left = `${hit.x}px`; tip.style.top = `${hit.y}px`;
  tip.classList.add("on");
}
canvas.addEventListener("pointermove", (ev) => {
  if (mode !== "explore" || ev.buttons || pickQueued) return;
  pickQueued = true;
  requestAnimationFrame(() => { pickQueued = false; setPicked(pick(ev)); });
});
canvas.addEventListener("pointerleave", () => { setPicked(null); controls.enableZoom = false; });
// the wheel scrolls the page until the visitor takes hold of the model
canvas.addEventListener("pointerdown", () => { controls.enableZoom = true; });
controls.enableZoom = false;

// ---------- controls ----------
function swatches(container, onPick) {
  for (const [id, f] of Object.entries(FINISHES)) {
    const b = document.createElement("button");
    b.type = "button";
    b.style.setProperty("--swatch", `#${f.alu.toString(16).padStart(6, "0")}`);
    b.title = f.name;
    b.setAttribute("aria-label", `${f.name} finish`);
    b.dataset.finish = id;
    b.addEventListener("click", () => onPick(id));
    container.append(b);
  }
}
function effectButtons(container, onPick) {
  for (const effect of EFFECTS) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = effect[0].toUpperCase() + effect.slice(1);
    b.dataset.effect = effect;
    b.addEventListener("click", () => onPick(effect));
    container.append(b);
  }
}
const setFinish = (id) => { state.finish = id; model.setFinish(id); syncUI(); if (mode === "explore") { hud(); saveHash(); } };
const setEffect = (effect) => { state.effect = effect; syncUI(); };
for (const el of document.querySelectorAll("[data-swatches]")) swatches(el, setFinish);
for (const el of document.querySelectorAll("[data-effects]")) effectButtons(el, setEffect);

const press = (el, on) => { el.classList.toggle("on", on); el.setAttribute("aria-pressed", String(on)); };
function syncUI() {
  for (const b of document.querySelectorAll("[data-finish]")) press(b, b.dataset.finish === state.finish);
  for (const b of document.querySelectorAll("[data-effect]")) press(b, b.dataset.effect === state.effect);
  for (const b of document.querySelectorAll("[data-scene]")) press(b, b.dataset.scene === state.scene);
  for (const b of document.querySelectorAll("[data-view]")) press(b, b.dataset.view === state.view);
  for (const el of document.querySelectorAll("[data-finish-name]")) el.textContent = FINISHES[state.finish].name;
  $("section").value = state.section;
}
const saveHash = () => history.replaceState(null, "",
  `#scene=${state.scene}&finish=${state.finish}${state.view === "iso" ? "" : `&view=${state.view}`}`);

for (const b of document.querySelectorAll("[data-scene]")) {
  b.addEventListener("click", () => {
    state.scene = b.dataset.scene; state.section = 0;
    setPicked(null); syncUI(); applyExplore(); frameExplore(); saveHash();
  });
}
for (const b of document.querySelectorAll("[data-view]")) {
  b.addEventListener("click", () => { state.view = b.dataset.view; syncUI(); frameExplore(); saveHash(); });
}
// a manual orbit leaves the preset: the buttons go dark until a preset or Reset view is chosen again
controls.addEventListener("start", () => { for (const b of document.querySelectorAll("[data-view]")) press(b, false); });
for (const id of ["explode", "section", "swing", "glow", "hue"]) {
  $(id).value = state[id];
  $(id).addEventListener("input", (e) => { state[id] = Number(e.target.value); applyExplore(); });
}
const TOGGLES = { tCaps: "caps", tLegends: "legends", tSwitches: "switches", tPcb: "pcb", tTop: "top",
  tSpacer: "spacer", tBottom: "bottom", tLegs: "legs", tEdges: "edges", tSpin: "spin" };
for (const [id, k] of Object.entries(TOGGLES)) {
  $(id).checked = state[k];
  $(id).addEventListener("change", (e) => { state[k] = e.target.checked; applyExplore(); });
}
// without case models the case controls do nothing
for (const [id, role] of Object.entries({ tTop: "top", tSpacer: "spacer", tBottom: "bottom", tLegs: "leg" })) {
  const present = hasRole(role);
  $(id).disabled = !present;
  $(id).parentElement.classList.toggle("off", !present);
  $(id).parentElement.title = present ? "" : "not in this build: run `just model` before `just site`";
}
$("swing").disabled = !hasRole("leg");
$("resetView").addEventListener("click", () => { state.view = "iso"; syncUI(); frameExplore(); });
const fs = $("fullscreen");
fs.hidden = !stages.explore.requestFullscreen;
fs.addEventListener("click", () => (document.fullscreenElement ? document.exitFullscreen() : stages.explore.requestFullscreen()));
document.addEventListener("fullscreenchange", () => {
  const label = document.fullscreenElement === stages.explore ? "Exit full screen" : "Full screen";
  fs.title = label;
  fs.setAttribute("aria-label", label);
});
$("snap").addEventListener("click", () => {
  composer.render();
  const a = document.createElement("a");
  a.href = canvas.toDataURL("image/png");
  a.download = `worxboard-${state.scene}.png`;
  a.click();
});

// ---------- which driver has the canvas ----------
let mode = "idle";
const storyTrack = $("story");

function wantedMode() {
  if (document.fullscreenElement === stages.explore) return "explore";
  if (storyTrack.getBoundingClientRect().bottom > 0) return "story";
  const r = stages.explore.getBoundingClientRect();
  return r.top < innerHeight && r.bottom > 0 ? "explore" : "idle";
}

function enter(next) {
  mode = next;
  controls.enabled = next === "explore";
  setPicked(null);
  if (next === "idle") return;
  stages[next].prepend(canvas);
  resize(true);
  if (next === "story") {
    pose = null;
    model.setVisible({ ...Object.fromEntries(LAYERS.map((l) => [l, true])), legs: true, legends: true, edges: false });
    model.setSection(false);
    return;
  }
  placeTags(0);
  applyExplore();
  frameExplore();
}

function resize(force) {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  const size = renderer.getSize(new THREE.Vector2());
  if (!force && size.x === w && size.y === h) return;
  renderer.setSize(w, h, false);
  composer.setPixelRatio(renderer.getPixelRatio());
  composer.setSize(w, h);
  camera.aspect = w / h;
  if (mode === "explore") {
    // the panel covers the right of a wide stage: centre the model in what is left
    camera.setViewOffset(w, h, (w - freeWidth()) / 2, 0, w, h);
  }
  camera.updateProjectionMatrix();
}

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const next = wantedMode();
  if (next !== mode) enter(next);
  const dt = Math.min(clock.getDelta(), 0.1);
  if (mode === "idle") return;   // off screen: the rest of the page scrolls without a busy GPU
  resize(false);
  if (mode === "story") storyFrame(dt, clock.elapsedTime);
  else { controls.update(); showGlow(state.glow, clock.elapsedTime); }
  composer.render();
});

syncUI();
document.documentElement.dataset.viewer = "ready";
