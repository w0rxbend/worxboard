// worxboard viewer. Builds the PCB, switches, keycaps and display of both halves from layout.json,
// and adds the case STLs when the build included them. Adapted from the w0rxbend/ergodox viewer.
// Frames: layout.json is the KiCad frame (mm, +y towards the user); the scene is the CAD frame of the
// reference case, (x - OX, -(y - OY)) with Z up. The left half's layout data is already mirrored.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";

const FINISHES = {
  black: { name: "Black", color: 0x1e1f23 },
  silver: { name: "Silver", color: 0xc4c8ce },
  grey: { name: "Space grey", color: 0x60656d },
  blue: { name: "Blue", color: 0x2a5ca8 },
  red: { name: "Red", color: 0xa82530 },
  orange: { name: "Orange", color: 0xd8601e },
};
// Z stack (spec §10) and part heights, mm
const Z = { pcb: 7.0, pcbTop: 8.6, plateTop: 13.6, swTop: 19.4, capBottom: 20.2, capTop: 27.6 };
const PCB_T = Z.pcbTop - Z.pcb;
const CAP_GAP = 1.0;          // keycap = key cell minus this
const CAP_TAPER = 0.8;        // top face scale of a keycap
const SW_LOWER = 14.0, SW_UPPER = 15.6;
const SOCKET = { off: [-0.6, -3.8], size: [11.0, 5.0], h: 1.8 };   // Kailh MX hot-swap, footprint frame
const DISPLAY_T = 2.9, DISPLAY_Z = 13.0;
const PART_H = { U1: 0.9, U2: 1.8, SW_BOOT: 1.5, SW_RST: 1.5, J3: DISPLAY_Z - Z.pcbTop };
const CASE_MARGIN = 6.2;      // case wall + clearance + leg boss beyond the PCB edge
const PAIR_GAP = 30;
const EXPLODE = { pcb: 12, spacer: 24, top: 36, switches: 48, caps: 66 };
const EXPLODE_LEG = 26;

const $ = (id) => document.getElementById(id);
const canvas = $("canvas");
const stage = $("stage");

const state = {
  scene: "pair", finish: "black", explode: 0, section: 0, swing: 90,
  caps: true, legends: true, switches: true, pcb: true, top: true, spacer: true, bottom: true,
  legs: true, edges: true, spin: false,
};
for (const kv of location.hash.slice(1).split("&")) {
  const [k, v] = kv.split("=");
  if (k === "scene" && ["pair", "right", "left"].includes(v)) state.scene = v;
  if (k === "finish" && v in FINISHES) state.finish = v;
}

// ---------- renderer, scene, camera ----------
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.setClearColor(0x000000, 0);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(35, 1, 1, 5000);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.autoRotateSpeed = 1.2;

const key = new THREE.DirectionalLight(0xffffff, 1.6);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.bias = -0.0004;
scene.add(key, key.target);
scene.add(new THREE.HemisphereLight(0xdde6ff, 0x20160f, 0.5));
const rim = new THREE.DirectionalLight(0xffb27f, 0.6);
rim.position.set(300, 400, 120);
scene.add(rim);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), new THREE.ShadowMaterial({ opacity: 0.35 }));
ground.receiveShadow = true;
scene.add(ground);

// ---------- materials ----------
const clip = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const std = (color, metalness, roughness, extra = {}) =>
  new THREE.MeshStandardMaterial({ color, metalness, roughness, ...extra });
const M = {
  alu: std(FINISHES[state.finish].color, 0.75, 0.42),
  tpu: std(0x18191b, 0, 0.9),
  printed: std(0xc8692a, 0, 0.75),
  pcb: std(0x1f6f4a, 0.1, 0.55),
  copper: std(0xd4a54a, 0.9, 0.3),
  chip: std(0x16171a, 0.2, 0.5),
  metal: std(0xb9bec6, 0.85, 0.3),
  socket: std(0xece7dc, 0, 0.7),
  sw: std(0x2b2d33, 0.05, 0.6),
  stem: std(0xc2272d, 0, 0.5),
  cap: std(0xe9e6df, 0, 0.62),
  capMod: std(0x9aa1ab, 0, 0.62),
  capAccent: std(0xff6a1a, 0, 0.55),
  display: std(0x111214, 0.3, 0.35),
  cutFace: new THREE.MeshBasicMaterial({ color: 0xff6a1a, side: THREE.BackSide }),
  edge: new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35 }),
  highlight: std(0xff8a3d, 0.4, 0.5, { emissive: 0x401400 }),
};
const clipped = new Set(Object.values(M));

// ---------- data ----------
const [manifest, lay] = await Promise.all(["manifest.json", "layout.json"].map((f) => fetch(f).then((r) => r.json())));
$("version").textContent = manifest.version;
const [OX, OY] = manifest.cad_origin;
const cad = ([x, y]) => [x - OX, -(y - OY)];
const SIDES = ["left", "right"];
const partNames = Object.keys(manifest.parts);
const hasCase = partNames.some((n) => manifest.parts[n].role === "top");

// ---------- case STLs (optional) ----------
const geoms = {}, edges = {};
const progress = Object.fromEntries(partNames.map((n) => [n, 0]));
const updateBar = () => {
  const p = partNames.length ? Object.values(progress).reduce((a, b) => a + b, 0) / partNames.length : 1;
  $("loadbar").style.width = `${(p * 100).toFixed(0)}%`;
};
$("loadtext").textContent = partNames.length ? "loading case models…" : "building from layout.json…";
const stl = new STLLoader();
await Promise.all(partNames.map((n) => new Promise((resolve, reject) => {
  stl.load(manifest.parts[n].file, (g) => {
    g.deleteAttribute("normal");
    geoms[n] = toCreasedNormals(g, THREE.MathUtils.degToRad(28));
    geoms[n].computeBoundingBox();
    edges[n] = new THREE.EdgesGeometry(g, 28);
    progress[n] = 1; updateBar(); resolve();
  }, (e) => { if (e.total) { progress[n] = e.loaded / e.total; updateBar(); } }, reject);
}))).catch((e) => { $("loadtext").textContent = `failed to load models: ${e.message || e}`; throw e; });
updateBar();
$("loader").classList.add("done");

// ---------- geometry helpers ----------
const pickable = [];

function withEdges(mesh, threshold = 30) {
  const g = new THREE.Group();
  const lines = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, threshold), M.edge);
  lines.userData.isEdge = true;
  g.add(mesh, lines);
  return g;
}

function mesh(geo, mat, info) {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = m.receiveShadow = true;
  m.userData.mat = mat;
  if (info) { m.userData.info = info; pickable.push(m); }
  return m;
}

/** Box from a KiCad-frame rectangle [x0, y0, x1, y1], between z0 and z1. */
function rectBox(r, z0, z1, mat, info) {
  const [a, b] = [cad([r[0], r[1]]), cad([r[2], r[3]])];
  const m = mesh(new THREE.BoxGeometry(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]), z1 - z0), mat, info);
  m.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (z0 + z1) / 2);
  return m;
}

function pcbGeometry(side) {
  const s = lay.sides[side];
  const shape = new THREE.Shape(s.outline.vertices.map((v) => new THREE.Vector2(...cad(v))));
  const r = lay.hole.drill / 2;
  for (const h of s.holes) {
    const p = new THREE.Path();
    const [x, y] = cad(h);
    p.absarc(x, y, r, 0, Math.PI * 2, true);
    shape.holes.push(p);
  }
  const g = new THREE.ExtrudeGeometry(shape, { depth: PCB_T, bevelEnabled: false, curveSegments: 24 });
  g.translate(0, 0, Z.pcb);
  return g;
}

/** Keycap top-face size: inset by the same amount on every side. */
const capTop = (w, h) => { const d = (1 - CAP_TAPER) * Math.min(w, h); return [w - d, h - d]; };

function capGeometry(w, h) {
  const g = new THREE.BoxGeometry(w, h, Z.capTop - Z.capBottom);
  const [tw, th] = capTop(w, h);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    if (pos.getZ(i) > 0) { pos.setX(i, pos.getX(i) * tw / w); pos.setY(i, pos.getY(i) * th / h); }
  }
  g.computeVertexNormals();
  return g;
}

function textTexture(text, w, h, { bg = null, fg = "#2a2c31", font = "JetBrains Mono, monospace", weight = 600 } = {}) {
  const px = 64;
  const c = document.createElement("canvas");
  c.width = Math.round(w * px / 10); c.height = Math.round(h * px / 10);
  const ctx = c.getContext("2d");
  if (bg) { ctx.fillStyle = bg; ctx.fillRect(0, 0, c.width, c.height); }
  ctx.fillStyle = fg;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  let size = c.height * 0.34;
  ctx.font = `${weight} ${size}px ${font}`;
  while (ctx.measureText(text).width > c.width * 0.86 && size > 6) { size -= 1; ctx.font = `${weight} ${size}px ${font}`; }
  ctx.fillText(text, c.width / 2, c.height / 2);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

const MOD_LEGEND = /^(LSFT|RSFT|BSPC|DEL|ENT|TAB|SPC|LGUI|LALT|HYPER|MEH|HOME|END|PGUP|PGDN|LEFT|RGHT|UP|DOWN|\\)|_T\(|^LT|^TG|^TT|^LA/;

function keyGroup(side, k, groups) {
  const [x, y] = cad([k.x, k.y]);
  const pitch = lay.pitch;
  const info = `${side} ${k.id}  ${k.legend}\nZMK RC(${k.rc[0]},${k.rc[1]})  ·  ROW${k.row} / COL${k.col}\n` +
    `x ${k.x.toFixed(2)}  y ${k.y.toFixed(2)}  rot ${k.rot}°  ·  ${k.w}×${k.h}u`;
  const at = (g) => { g.position.set(x, y, 0); g.rotation.z = THREE.MathUtils.degToRad(k.rot); return g; };

  // switch: lower body through the plate, upper housing and stem above it
  const sw = new THREE.Group();
  const lower = mesh(new THREE.BoxGeometry(SW_LOWER, SW_LOWER, Z.plateTop - Z.pcbTop), M.sw);
  lower.position.z = (Z.pcbTop + Z.plateTop) / 2;
  const upper = mesh(new THREE.BoxGeometry(SW_UPPER * 0.9, SW_UPPER * 0.9, Z.swTop - Z.plateTop), M.sw, info);
  upper.position.z = (Z.plateTop + Z.swTop) / 2;
  const stem = mesh(new THREE.BoxGeometry(4, 4, 1.2), M.stem);
  stem.position.z = Z.swTop + 0.6;
  sw.add(lower, upper, stem);
  groups.switches.add(at(sw));

  // keycap with a legend decal on its top face
  const w = k.w * pitch - CAP_GAP, h = k.h * pitch - CAP_GAP;
  const cap = new THREE.Group();
  const mat = k.id === "C6R1" ? M.capAccent : MOD_LEGEND.test(k.legend) ? M.capMod : M.cap;
  const body = mesh(capGeometry(w, h), mat, info);
  body.position.z = (Z.capBottom + Z.capTop) / 2;
  const [tw, th] = capTop(w, h);
  const decal = new THREE.Mesh(new THREE.PlaneGeometry(tw, th),
    new THREE.MeshBasicMaterial({ map: textTexture(k.legend, tw, th, { fg: mat === M.capAccent ? "#1a0d04" : "#25272c" }), transparent: true }));
  decal.position.z = Z.capTop + 0.02;
  decal.userData.isLegend = true;
  clipped.add(decal.material);
  cap.add(body, decal);
  groups.caps.add(at(cap));

  // hot-swap socket on the bottom side (mirrored footprint on the left)
  const mx = side === "left" ? -1 : 1;
  const sock = mesh(new THREE.BoxGeometry(...SOCKET.size, SOCKET.h), M.socket, `${side} hot-swap socket ${k.id}\nKailh CPG151101S11, bottom side`);
  sock.position.set(mx * SOCKET.off[0], -SOCKET.off[1], Z.pcb - SOCKET.h / 2);
  groups.pcb.add(at(new THREE.Group().add(sock)));
}

function displayGroup(side) {
  const d = lay.sides[side].display;
  const g = new THREE.Group();
  const info = `${side} display\nSharp LS011B7DH03 (nice!view), 160 × 68\nPIO1 SPI: SCK GP2, MOSI GP3, CS GP5`;
  g.add(rectBox(d.module, DISPLAY_Z, DISPLAY_Z + DISPLAY_T, M.display, info));
  // the active area under the window, drawn as the status screen would look
  const [a, b] = [cad(d.window.slice(0, 2)), cad(d.window.slice(2))];
  const ww = Math.abs(b[0] - a[0]), wh = Math.abs(b[1] - a[1]);
  const text = side === "left" ? "LAYER 0" : "worxboard";
  const tex = textTexture(text, wh, ww, { bg: "#c9d3cc", fg: "#1b1e1c", font: "Space Grotesk, sans-serif", weight: 700 });
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(wh, ww), new THREE.MeshBasicMaterial({ map: tex }));
  screen.rotation.z = Math.PI / 2;     // the module is mounted vertically
  screen.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, DISPLAY_Z + DISPLAY_T + 0.02);
  clipped.add(screen.material);
  g.add(screen);
  return g;
}

function pcbGroup(side) {
  const g = new THREE.Group();
  const s = lay.sides[side];
  const board = mesh(pcbGeometry(side), M.pcb, `worxboard-${side} PCB\n2-layer, 1.6 mm, ENIG\n${s.keys.length} keys`);
  g.add(withEdges(board, 20));
  const bodies = manifest.bodies[side];
  const labels = { U1: "RP2040", U2: "W25Q128 flash", SW_BOOT: "BOOT button", SW_RST: "RESET button", J3: "J3 display header" };
  for (const [ref, label] of Object.entries(labels)) {
    g.add(rectBox(bodies[ref], Z.pcbTop, Z.pcbTop + PART_H[ref], ref.startsWith("SW") ? M.metal : M.chip, `${ref}  ${label}`));
  }
  for (const j of s.jacks) {
    const label = j.ref === "J1" ? "J1 USB-C (HRO TYPE-C-31-M-12)" : "J2 TRRS jack (PJ-320D)\nDO NOT HOT-PLUG";
    g.add(rectBox(j.body, Z.pcbTop, Z.pcbTop + j.height, M.metal, label));
  }
  g.add(displayGroup(side));
  return g;
}

function casePart(name, mat) {
  const m = mesh(geoms[name], mat, null);
  const p = manifest.parts[name];
  m.userData.info = `${p.label}\n${p.size.join(" × ")} mm` + (p.mass_g ? `  ·  ${p.mass_g} g` : `  ·  ${p.volume_cm3} cm³`);
  pickable.push(m);
  const cap = new THREE.Mesh(geoms[name], M.cutFace);
  const lines = new THREE.LineSegments(edges[name], M.edge);
  lines.userData.isEdge = true;
  return new THREE.Group().add(m, cap, lines);
}

function legAssembly() {
  const g = new THREE.Group();
  if (geoms.leg) g.add(casePart("leg", M.alu));
  if (geoms.leg_cap) { const c = casePart("leg_cap", M.tpu); c.userData.isCap = true; g.add(c); }
  return g;
}

function half(side) {
  const groups = Object.fromEntries(["bottom", "pcb", "spacer", "top", "switches", "caps", "legs"].map((n) => [n, new THREE.Group()]));
  groups.pcb.add(pcbGroup(side));
  for (const k of lay.sides[side].keys) keyGroup(side, k, groups);
  const part = (role) => manifest.parts[`${side}_${role}`] && geoms[`${side}_${role}`];
  if (part("bottom")) groups.bottom.add(casePart(`${side}_bottom`, M.alu));
  if (part("spacer")) groups.spacer.add(casePart(`${side}_spacer`, M.printed));
  if (part("top")) groups.top.add(casePart(`${side}_top`, M.alu));
  if (geoms.leg) {
    const mirror = new THREE.Matrix4().makeScale(side === "left" ? -1 : 1, 1, 1);
    for (const arr of manifest.legs) {
      const mount = new THREE.Group();
      mount.matrixAutoUpdate = false;
      mount.matrix.multiplyMatrices(mirror, new THREE.Matrix4().fromArray(arr).transpose());
      const swing = legAssembly();
      swing.userData.swing = true;
      mount.add(swing);
      groups.legs.add(mount);
    }
    groups.top.add(groups.legs);
  }
  const g = new THREE.Group();
  for (const [n, sub] of Object.entries(groups)) if (n !== "legs") g.add(sub);
  g.userData = groups;
  return g;
}

// pair placement: mirror-symmetric about x = 0, the inner edges PAIR_GAP apart
const innerX = Math.min(...lay.sides.right.outline.vertices.map((v) => cad(v)[0])) - CASE_MARGIN;
const PAIR_DX = PAIR_GAP / 2 - innerX;

let root = new THREE.Group();
let halves = [];

function build() {
  scene.remove(root);
  root = new THREE.Group();
  pickable.length = 0;
  halves = [];
  const sides = state.scene === "pair" ? SIDES : [state.scene];
  for (const side of sides) {
    const h = half(side);
    if (state.scene === "pair") h.position.x = side === "right" ? PAIR_DX : -PAIR_DX;
    halves.push(h);
    root.add(h);
  }
  scene.add(root);
  apply();
  frame();
}

// ---------- state -> scene ----------
function apply() {
  M.alu.color.setHex(FINISHES[state.finish].color);
  for (const m of clipped) { m.clippingPlanes = state.section > 0 ? [clip] : []; m.needsUpdate = true; }
  for (const h of halves) {
    const g = h.userData;
    for (const [n, dz] of Object.entries(EXPLODE)) g[n].position.z = state.explode * dz;
    g.caps.visible = state.caps;
    g.switches.visible = state.switches;
    g.pcb.visible = state.pcb;
    g.top.visible = state.top;
    g.spacer.visible = state.spacer;
    g.bottom.visible = state.bottom;
    g.legs.visible = state.legs;
  }
  root.traverse((o) => {
    if (o.userData.swing) o.rotation.z = THREE.MathUtils.degToRad(state.swing);
    if (o.userData.isEdge) o.visible = state.edges;
    if (o.userData.isLegend) o.visible = state.legends;
    if (o.userData.isCap) o.position.y = state.explode * EXPLODE_LEG;
  });
  root.updateMatrixWorld(true);
  const box = visibleBox();
  ground.position.z = box.isEmpty() ? 0 : box.min.z - 0.05;
  if (state.section > 0 && !box.isEmpty()) {
    const y = box.min.y + state.section * (box.max.y - box.min.y);
    clip.constant = -y;
    $("sectionVal").textContent = `y ${y.toFixed(1)}`;
  } else $("sectionVal").textContent = "off";
  $("explodeVal").textContent = state.explode ? `${Math.round(state.explode * EXPLODE.caps)} mm` : "0";
  $("swingVal").textContent = `${state.swing}°`;
  controls.autoRotate = state.spin;
  hud(box);
  location.replace(`#scene=${state.scene}&finish=${state.finish}`);
}

function visibleBox() {
  const box = new THREE.Box3();
  root.traverseVisible((o) => { if (o.isMesh && o.userData.mat) box.expandByObject(o); });
  return box;
}

function hud(box) {
  if (box.isEmpty()) { $("hud").textContent = "nothing visible"; return; }
  const s = box.getSize(new THREE.Vector3());
  const nkeys = halves.length * lay.sides.left.keys.length;
  $("hud").textContent =
    `extent  ${s.x.toFixed(1)} × ${s.y.toFixed(1)} × ${s.z.toFixed(1)} mm\n` +
    `keys    ${nkeys}  ·  ${hasCase ? `case: ${FINISHES[state.finish].name.toLowerCase()}` : "case: not built yet"}\n` +
    `version ${manifest.version}`;
}

function frame() {
  const box = visibleBox();
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const vfov = THREE.MathUtils.degToRad(camera.fov / 2);
  const hfov = Math.atan(Math.tan(vfov) * camera.aspect);
  const dist = sphere.radius / Math.sin(Math.min(vfov, hfov)) * (camera.aspect > 1 ? 0.8 : 0.95);
  const dir = new THREE.Vector3(state.scene === "pair" ? 0 : -0.25, -0.8, 1.25).normalize();
  controls.target.copy(sphere.center);
  camera.position.copy(sphere.center).addScaledVector(dir, dist);
  camera.near = dist / 100; camera.far = dist * 20;
  camera.updateProjectionMatrix();
  const r = sphere.radius;
  Object.assign(key.shadow.camera, { left: -r * 1.6, right: r * 1.6, top: r * 1.6, bottom: -r * 1.6, near: 1, far: 4000 });
  key.shadow.camera.updateProjectionMatrix();
  key.position.copy(sphere.center).add(new THREE.Vector3(-0.4, -0.6, 1).multiplyScalar(r * 3));
  key.target.position.copy(sphere.center);
  controls.update();
}

// ---------- picking ----------
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let picked = null, pending = null;
const isShown = (o) => { for (; o; o = o.parent) if (!o.visible) return false; return true; };
function pick(ev) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hits = ray.intersectObjects(pickable.filter(isShown), false)
    .filter((h) => state.section === 0 || clip.distanceToPoint(h.point) >= 0);
  return hits[0] ? { mesh: hits[0].object, x: ev.clientX - r.left, y: ev.clientY - r.top } : null;
}
function setPicked(hit) {
  if (picked) picked.material = picked.userData.mat;
  picked = hit?.mesh || null;
  const tip = $("tooltip");
  if (!picked) { tip.classList.remove("on"); return; }
  picked.material = M.highlight;
  tip.textContent = picked.userData.info;
  tip.style.left = `${hit.x}px`; tip.style.top = `${hit.y}px`;
  tip.classList.add("on");
}
canvas.addEventListener("pointermove", (ev) => {
  if (ev.buttons) return;
  if (!pending) pending = requestAnimationFrame(() => { pending = null; setPicked(pick(ev)); });
});
canvas.addEventListener("pointerleave", () => setPicked(null));

// ---------- UI ----------
for (const [id, f] of Object.entries(FINISHES)) {
  const b = document.createElement("button");
  b.style.background = `#${f.color.toString(16).padStart(6, "0")}`;
  b.title = f.name;
  b.dataset.finish = id;
  b.addEventListener("click", () => { state.finish = id; syncUI(); apply(); });
  $("finishes").append(b);
}
for (const b of $("scenes").querySelectorAll("button")) {
  b.addEventListener("click", () => { state.scene = b.dataset.scene; state.section = 0; syncUI(); build(); });
}
const bindRange = (id, k) => $(id).addEventListener("input", (e) => { state[k] = Number(e.target.value); apply(); });
bindRange("explode", "explode");
bindRange("section", "section");
bindRange("swing", "swing");
const TOGGLES = { tCaps: "caps", tLegends: "legends", tSwitches: "switches", tPcb: "pcb", tTop: "top",
  tSpacer: "spacer", tBottom: "bottom", tLegs: "legs", tEdges: "edges", tSpin: "spin" };
for (const [id, k] of Object.entries(TOGGLES)) {
  $(id).addEventListener("change", (e) => { state[k] = e.target.checked; apply(); });
}
// without case models the case controls do nothing
const caseCtl = { tTop: "top", tSpacer: "spacer", tBottom: "bottom", tLegs: "leg" };
for (const [id, role] of Object.entries(caseCtl)) {
  const present = partNames.some((n) => manifest.parts[n].role === role);
  $(id).disabled = !present;
  $(id).parentElement.classList.toggle("off", !present);
  $(id).parentElement.title = present ? "" : "not in this build: run `just model` before `just site`";
}
$("swingGroup").style.opacity = geoms.leg ? 1 : 0.4;
$("resetView").addEventListener("click", frame);
$("snap").addEventListener("click", () => {
  renderer.render(scene, camera);
  const a = document.createElement("a");
  a.href = renderer.domElement.toDataURL("image/png");
  a.download = `worxboard-${state.scene}.png`;
  a.click();
});
function syncUI() {
  for (const b of $("scenes").querySelectorAll("button")) b.classList.toggle("on", b.dataset.scene === state.scene);
  for (const b of $("finishes").querySelectorAll("button")) b.classList.toggle("on", b.dataset.finish === state.finish);
  $("section").value = state.section;
}

// ---------- page content from the manifest ----------
const blob = (p) => `${manifest.repo}/blob/main/${p}`;
const downloads = partNames.map((n) => {
  const p = manifest.parts[n];
  return `<a class="part" href="${p.file}" download title="Download ${n}.stl"><b>${p.label}</b>` +
    `<span>${p.size.join(" × ")} mm</span><span>${p.mass_g ? `${p.mass_g} g · 6061` : p.material === "tpu" ? "TPU, 3D-printed" : `${p.volume_cm3} cm³ · print`} · STL ↓</span></a>`;
});
downloads.push(`<a class="part" href="layout.json" download><b>layout.json</b><span>schema ${lay.schema} · every key, hole, zone</span><span>the single source of truth ↓</span></a>`);
$("partlist").innerHTML = downloads.join("");

const ob = lay.sides.right.outline.vertices;
const ext = (i) => Math.max(...ob.map((v) => v[i])) - Math.min(...ob.map((v) => v[i]));
$("sizeStat").textContent = `${ext(0).toFixed(1)} × ${ext(1).toFixed(1)}`;
$("keyStat").textContent = SIDES.reduce((a, s) => a + lay.sides[s].keys.length, 0);

$("shots").innerHTML = manifest.gallery.map((s) =>
  `<figure${s.wide ? ' class="wide"' : ""}><img loading="lazy" src="${s.file}" alt="${s.caption}"><figcaption>${s.caption}</figcaption></figure>`).join("");

const DOCS = [
  ["docs/buildguide_en.md", "Build guide", "Check, flash, solder J3, assemble"],
  ["docs/bom.md", "Bill of materials", "JLC parts with [G3] flags, builder parts, gates"],
  ["docs/electrical.md", "Electrical design", "Power path, TRRS, USB-C, MCU, display"],
  ["docs/pinout.md", "Pinout", "GPIO map, TRRS contacts, J3 (generated)"],
  ["docs/matrix.md", "Key matrix", "6×7 per half, ZMK 6×14 transform (generated)"],
  ["docs/firmware.md", "Firmware", "ZMK builds, flashing, keymap, displays"],
  ["docs/ordering-jlcpcb.md", "Ordering PCBs", "JLCPCB settings for both sides"],
  ["docs/case.md", "Case and plates", "build123d case, Z stack, files"],
  ["docs/legs.md", "Tent legs", "Mounts, positions, the custom leg"],
  ["docs/design.md", "Design spec", "The frozen rev A specification"],
  ["docs/sources.md", "Sources", "Prior art and attribution"],
];
$("doclinks").innerHTML = DOCS.map(([p, t, d]) => `<a href="${blob(p)}">${t}<span>${d}</span></a>`).join("");

// ---------- loop ----------
function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.floor(w * renderer.getPixelRatio()) || canvas.height !== Math.floor(h * renderer.getPixelRatio())) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    const panel = w > 760 ? $("panel").offsetWidth + 14 : 0;
    camera.setViewOffset(w, h, panel / 2, 0, w, h);
    camera.updateProjectionMatrix();
  }
}
new ResizeObserver(resize).observe(stage);
syncUI();
resize();
build();
renderer.setAnimationLoop(() => {
  resize();
  controls.update();
  renderer.render(scene, camera);
});
