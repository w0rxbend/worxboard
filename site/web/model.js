// worxboard 3D model. Builds both halves from layout.json (PCB outline, switches, keycaps, LEDs, display),
// places the assembled parts of the committed boards (manifest.components) and adds the case STLs when
// the build included them. viewer.js owns the renderer, the camera and the controls.
// Frames: layout.json is the KiCad frame (mm, +y towards the user); the scene is the CAD frame of the
// reference case, (x - OX, -(y - OY)) with Z up. The left half's layout data is already mirrored.
import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";
import { manifest, lay } from "./data.js";

// Anodize colour of the case, with a keycap set that suits it. Render colours, not a fab catalogue.
export const FINISHES = {
  black: { name: "Black", alu: 0x1a1b1e, cap: 0x2b2d32, mod: 0x1d1e22 },
  silver: { name: "Silver", alu: 0xc9cdd3, cap: 0xf1f0ec, mod: 0xb4b9c1 },
  grey: { name: "Space grey", alu: 0x5c6168, cap: 0xe9e7e1, mod: 0x3b3e44 },
  blue: { name: "Blue", alu: 0x24508f, cap: 0xf1f0ec, mod: 0x1c2f52 },
  red: { name: "Red", alu: 0x9c2530, cap: 0xf1f0ec, mod: 0x2b2d32 },
  orange: { name: "Orange", alu: 0xd0601f, cap: 0x2b2d32, mod: 0xf1f0ec },
};
// The four ZMK underglow effects the firmware steps through, in its order.
export const EFFECTS = ["solid", "breathe", "spectrum", "swirl"];
export const SIDES = ["left", "right"];
export const LAYERS = ["bottom", "pcb", "spacer", "top", "switches", "caps"];

// Z stack (spec §10) and part heights, mm
const Z = { pcb: 7.0, pcbTop: 8.6, plateTop: 13.6, swTop: 19.4, capBottom: 20.2, capTop: 27.6 };
const PCB_T = Z.pcbTop - Z.pcb;
const CAP = { gap: 1.0, inset: 2.7, dish: 0.45, bevel: 0.35, rBase: 1.0, rTop: 2.4, corner: 5 };
const SW_LOWER = 14.0, SW_UPPER = 14.0;
const SOCKET = { off: [-0.6, -3.8], size: [11.0, 5.0], h: 1.8 };   // Kailh MX hot-swap, footprint frame
const DISPLAY_T = 2.9, DISPLAY_Z = 13.0;
const J3_H = DISPLAY_Z - Z.pcbTop;   // display socket: up to the module
const LED_BODY = [3.2, 2.8];
const GLOW_SPILL = 7;         // the light pool under a keycap is this much larger than the key cell, mm
const GLOW_GAIN = 1.5;        // HDR gain of a lit pool at full level, above the bloom threshold
const HALO_GAIN = 0.4;        // the halo under a keycap, relative to the pool on the plate
const CASE_MARGIN = 6.2;      // case wall + clearance + leg boss beyond the PCB edge
export const PAIR_GAP = 30;
const SPREAD_TRAVEL = 1100;    // how far the left half slides out of frame for a one-half shot, mm
const EXPLODE = { bottom: 0, pcb: 12, spacer: 24, top: 36, switches: 48, caps: 66 };
const EXPLODE_LEG = 26;
const CREASE = THREE.MathUtils.degToRad(28);

const [OX, OY] = manifest.cad_origin;
const cad = ([x, y]) => [x - OX, -(y - OY)];
const partNames = Object.keys(manifest.parts);
export const hasCase = partNames.some((n) => manifest.parts[n].role === "top");
export const hasRole = (role) => partNames.some((n) => manifest.parts[n].role === role);
export const explodeTravel = EXPLODE.caps;

// pair placement: mirror-symmetric about x = 0, the inner edges PAIR_GAP apart
const innerX = Math.min(...lay.sides.right.outline.vertices.map((v) => cad(v)[0])) - CASE_MARGIN;
export const PAIR_DX = PAIR_GAP / 2 - innerX;

// ---------- materials ----------
export const clip = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const std = (color, metalness, roughness, extra = {}) =>
  new THREE.MeshStandardMaterial({ color, metalness, roughness, ...extra });
const M = {
  alu: std(FINISHES.black.alu, 0.9, 0.46),
  tpu: std(0x18191b, 0, 0.9),
  printed: std(0x2a2b2e, 0, 0.8),
  pcb: std(0x174d35, 0.1, 0.5),
  chip: std(0x16171a, 0.2, 0.5),
  passive: std(0x9c7b52, 0.1, 0.6),
  metal: std(0xb9bec6, 0.9, 0.3),
  socket: std(0xece7dc, 0, 0.7),
  sw: std(0x24262b, 0.05, 0.55),
  stem: std(0xc2272d, 0, 0.5),
  cap: std(FINISHES.black.cap, 0, 0.58),
  capMod: std(FINISHES.black.mod, 0, 0.58),
  display: std(0x0c0d0f, 0.3, 0.3),
  cutFace: new THREE.MeshBasicMaterial({ color: 0xff6a1a, side: THREE.BackSide }),
  edge: new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35 }),
  highlight: std(0xff8a3d, 0.4, 0.5, { emissive: 0x401400 }),
  glow: new THREE.MeshBasicMaterial({
    map: glowTexture(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false,
  }),
  led: new THREE.MeshBasicMaterial({ toneMapped: false }),
};
const clipped = new Set(Object.values(M));
export const highlight = M.highlight;

function glowTexture() {
  const size = 128;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.45, "rgba(255,255,255,0.55)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(c);
}

// ---------- geometry helpers ----------
function mesh(geo, mat) {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = m.receiveShadow = true;
  m.userData.mat = mat;
  return m;
}

/** Make a mesh answer the pointer: `info` is the text the viewer shows for it. */
function describe(m, info, ctx) {
  m.userData.info = info;
  ctx.pickable.push(m);
  return m;
}

/** Box from a KiCad-frame rectangle [x0, y0, x1, y1], between z0 and z1. */
function rectBox(r, z0, z1, mat) {
  const [a, b] = [cad([r[0], r[1]]), cad([r[2], r[3]])];
  const m = mesh(new THREE.BoxGeometry(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]), z1 - z0), mat);
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

/** Rounded rectangle w × h with corner radius r, counter-clockwise, as [x, y] points. */
function roundedRing(w, h, r, z) {
  const pts = [];
  const cx = w / 2 - r, cy = h / 2 - r;
  [[cx, cy], [-cx, cy], [-cx, -cy], [cx, -cy]].forEach(([x, y], quadrant) => {
    for (let i = 0; i <= CAP.corner; i++) {
      const a = (quadrant + i / CAP.corner) * Math.PI / 2;
      pts.push(x + r * Math.cos(a), y + r * Math.sin(a), z);
    }
  });
  return pts;
}

const capGeometries = new Map();
/** Keycap for a w × h cell: tapered sides, a narrow bevel and a dished top; z runs from 0 to the cap height. */
function capGeometry(w, h) {
  const id = `${w}x${h}`;
  if (capGeometries.has(id)) return capGeometries.get(id);
  const H = Z.capTop - Z.capBottom;
  const [tw, th] = [w - 2 * CAP.inset, h - 2 * CAP.inset];
  const rings = [
    roundedRing(w, h, CAP.rBase, 0),
    roundedRing(w - CAP.inset, h - CAP.inset, (CAP.rBase + CAP.rTop) / 2, H / 2),
    roundedRing(tw + CAP.bevel, th + CAP.bevel, CAP.rTop, H - CAP.bevel),
    roundedRing(tw, th, CAP.rTop, H),
    ...[0.93, 0.7, 0.4].map((s) => roundedRing(tw * s, th * s, CAP.rTop * s, H - CAP.dish * (1 - s * s))),
  ];
  const n = rings[0].length / 3;
  const index = [];
  for (let j = 0; j + 1 < rings.length; j++) {
    for (let i = 0; i < n; i++) {
      const a = j * n + i, b = j * n + (i + 1) % n;
      index.push(a, b, b + n, a, b + n, a + n);
    }
  }
  const centre = rings.length * n, last = centre - n;
  for (let i = 0; i < n; i++) index.push(last + i, last + (i + 1) % n, centre);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([...rings.flat(), 0, 0, H - CAP.dish], 3));
  g.setIndex(index);
  g.computeVertexNormals();
  capGeometries.set(id, g);
  return g;
}

const LEGEND_NAMES = {
  DEL: "Del", BSPC: "Bksp", SPC: "Space", ENT: "Enter", TAB: "Tab", LSFT: "Shift", RSFT: "Shift", LGUI: "Gui",
  LALT: "Alt", "LA(LSFT)": "Alt", HYPER: "Hyper", MEH: "Meh", HOME: "Home", END: "End", PGUP: "PgUp", PGDN: "PgDn",
  LEFT: "←", RGHT: "→", UP: "↑", DOWN: "↓", APP: "App", ESC: "Esc",
};
/** What a keycap would print for a keymap entry: the tap key of a hold-tap, "Fn" for a layer key. */
function capLegend(legend) {
  if (/^T[GT]\(\d\)$/.test(legend)) return "Fn";
  const tap = legend.match(/^(?:\w+_T\(|LT\(\d,)(.+)\)$/)?.[1] ?? legend;
  return LEGEND_NAMES[tap] ?? tap;
}
const isModifier = (legend) => capLegend(legend).length > 1;

const legendTextures = new Map();
/** White text on a transparent w × h mm texture; the decal material tints it. */
function legendTexture(text, w, h) {
  const id = `${text}|${w}|${h}`;
  if (legendTextures.has(id)) return legendTextures.get(id);
  const px = 12;   // texture pixels per mm
  const c = document.createElement("canvas");
  c.width = Math.round(w * px); c.height = Math.round(h * px);
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  let size = (text.length > 1 ? 3.0 : 4.6) * px;
  const font = () => { ctx.font = `600 ${size}px Archivo, system-ui, sans-serif`; };
  for (font(); ctx.measureText(text).width > c.width * 0.86 && size > 6; font()) size -= 1;
  ctx.fillText(text, c.width / 2, c.height / 2);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  legendTextures.set(id, t);
  return t;
}

/** Placeholder status screen, portrait as the module is mounted: 68 × 160 display pixels, drawn at 2×. */
function screenTexture(lines) {
  const c = document.createElement("canvas");
  c.width = 136; c.height = 320;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#bcc5b9";
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.fillStyle = "#15171a";
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  lines.forEach(([text, size, y]) => {
    ctx.font = `700 ${size}px Archivo, system-ui, sans-serif`;
    ctx.fillText(text, c.width / 2, y);
  });
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.NearestFilter;
  return t;
}
const SCREENS = {
  left: [["USB", 26, 40], ["0", 120, 150], ["BASE", 30, 262]],
  right: [["CAPS", 30, 70], ["NUM", 30, 160], ["SCRL", 30, 250]],
};

// ---------- one half ----------
function keyGroup(side, k, groups, ctx) {
  const [x, y] = cad([k.x, k.y]);
  const info = `${side} ${k.id}  ${k.legend}\nZMK RC(${k.rc[0]},${k.rc[1]})  ·  ROW${k.row} / COL${k.col}\n` +
    `x ${k.x.toFixed(2)}  y ${k.y.toFixed(2)}  rot ${k.rot}°  ·  ${k.w}×${k.h}u`;
  const at = (g) => { g.position.set(x, y, 0); g.rotation.z = THREE.MathUtils.degToRad(k.rot); return g; };

  // switch: lower body through the plate, upper housing and stem above it
  const sw = new THREE.Group();
  const lower = mesh(new THREE.BoxGeometry(SW_LOWER, SW_LOWER, Z.plateTop - Z.pcbTop), M.sw);
  lower.position.z = (Z.pcbTop + Z.plateTop) / 2;
  const upper = describe(mesh(new THREE.BoxGeometry(SW_UPPER, SW_UPPER, Z.swTop - Z.plateTop), M.sw), info, ctx);
  upper.position.z = (Z.plateTop + Z.swTop) / 2;
  const stem = mesh(new THREE.BoxGeometry(4, 4, 1.2), M.stem);
  stem.position.z = Z.swTop + 0.6;
  sw.add(lower, upper, stem);
  groups.switches.add(at(sw));

  // keycap with a legend decal on its top face
  const w = k.w * lay.pitch - CAP.gap, h = k.h * lay.pitch - CAP.gap;
  const onMod = isModifier(k.legend);
  const body = describe(mesh(capGeometry(w, h), onMod ? M.capMod : M.cap), info, ctx);
  body.position.z = Z.capBottom;
  const [tw, th] = [w - 2 * CAP.inset, h - 2 * CAP.inset];
  const decal = new THREE.Mesh(new THREE.PlaneGeometry(tw, th),
    new THREE.MeshBasicMaterial({ map: legendTexture(capLegend(k.legend), tw, th), transparent: true, depthWrite: false }));
  decal.position.z = Z.capTop + 0.02;
  clipped.add(decal.material);
  ctx.legends.push({ decal, onMod });
  groups.caps.add(at(new THREE.Group().add(body, decal)));

  // hot-swap socket on the bottom side (mirrored footprint on the left)
  const mx = side === "left" ? -1 : 1;
  const sock = describe(mesh(new THREE.BoxGeometry(...SOCKET.size, SOCKET.h), M.socket),
    `${side} hot-swap socket ${k.id}\nMX hot-swap socket CPG151101S11-16, bottom side`, ctx);
  sock.position.set(mx * SOCKET.off[0], -SOCKET.off[1], Z.pcb - SOCKET.h / 2);
  groups.pcb.add(at(new THREE.Group().add(sock)));
}

/** One instanced quad per entry of `items` ({x, y, rot, w, h} in the KiCad frame), flat at height z. */
function instancedQuads(items, z, mat) {
  const inst = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), mat, items.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 0, 1);
  items.forEach((it, i) => {
    const [x, y] = cad([it.x, it.y]);
    q.setFromAxisAngle(up, THREE.MathUtils.degToRad(it.rot));
    inst.setMatrixAt(i, m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(it.w, it.h, 1)));
    inst.setColorAt(i, new THREE.Color(0));
  });
  return inst;
}

/**
 * The lit LEDs of one half: a pool of light on the plate under each keycap, a fainter halo around the
 * switch just below the keycap (what shows between the caps from the side) and the LED body on the PCB.
 */
function ledGroups(side, groups, ctx) {
  const s = lay.sides[side];
  const cells = s.keys.map((k) => ({ ...k, w: k.w * lay.pitch + GLOW_SPILL, h: k.h * lay.pitch + GLOW_SPILL }));
  const pools = instancedQuads(cells, Z.plateTop + 0.25, M.glow);
  const halos = instancedQuads(cells, Z.capBottom - 0.6, M.glow);
  const bodies = instancedQuads(s.leds.map((l) => ({ ...l, w: LED_BODY[0], h: LED_BODY[1] })), Z.pcbTop + 0.06, M.led);
  groups.top.add(pools);
  groups.switches.add(halos);
  groups.pcb.add(bodies);
  // swirl phase: the position across the whole pair, 0 at the far left and 1 at the far right
  const sign = side === "left" ? -1 : 1;
  const phases = s.keys.map((k) => 0.5 + (sign * PAIR_DX + cad([k.x, k.y])[0]) / (4 * PAIR_DX));
  ctx.leds.push({ lit: [[pools, 1], [halos, HALO_GAIN], [bodies, 1]], phases });
}

function displayGroup(side, ctx) {
  const d = lay.sides[side].display;
  const g = new THREE.Group();
  const info = `${side} display\nSharp LS011B7DH03 (nice!view), 160 × 68\nPIO1 SPI: SCK GP2, MOSI GP3, CS GP5`;
  g.add(describe(rectBox(d.module, DISPLAY_Z, DISPLAY_Z + DISPLAY_T, M.display), info, ctx));
  // the active area under the window, drawn as a status screen would look
  const [a, b] = [cad(d.window.slice(0, 2)), cad(d.window.slice(2))];
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])),
    new THREE.MeshBasicMaterial({ map: screenTexture(SCREENS[side]) }));
  screen.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, DISPLAY_Z + DISPLAY_T + 0.02);
  clipped.add(screen.material);
  g.add(screen);
  return g;
}

function pcbGroup(side, ctx) {
  const g = new THREE.Group();
  const s = lay.sides[side];
  g.add(describe(mesh(pcbGeometry(side), M.pcb), `worxboard-${side} PCB\n4-layer, 1.6 mm, ENIG\n${s.keys.length} keys`, ctx));
  g.add(describe(rectBox(manifest.bodies[side].J3, Z.pcbTop, Z.pcbTop + J3_H, M.chip), "J3  display socket, 5.0 mm (fitted by the fab)", ctx));
  // assembled parts at their footprint pose: box = [cx, cy, w, l, h] in the footprint frame
  for (const c of manifest.components[side]) {
    const [cx, cy, w, l, h] = c.box;
    const top = c.side === "top";
    const body = describe(mesh(new THREE.BoxGeometry(w, l, h), M[c.mat]), `${side} ${c.ref}  ${c.value}\n${c.part}, ${c.side} side`, ctx);
    body.position.set(cx, -cy, top ? Z.pcbTop + h / 2 : Z.pcb - h / 2);
    const at = new THREE.Group().add(body);
    const [x, y] = cad(c.at);
    at.position.set(x, y, 0);
    at.rotation.z = THREE.MathUtils.degToRad(c.at[2]);
    g.add(at);
  }
  for (const j of s.jacks) {
    const label = j.ref === "J1" ? "J1 USB-C (HRO TYPE-C-31-M-12)" : "J2 TRRS jack (PJ-320D)\nDO NOT HOT-PLUG";
    g.add(describe(rectBox(j.body, Z.pcbTop, Z.pcbTop + j.height, M.metal), label, ctx));
  }
  g.add(displayGroup(side, ctx));
  return g;
}

function casePart(name, mat, stl, ctx) {
  const p = manifest.parts[name];
  const info = `${p.label}\n${p.size.join(" × ")} mm` + (p.mass_g ? `  ·  ${p.mass_g} g` : `  ·  ${p.volume_cm3} cm³`);
  const cut = new THREE.Mesh(stl[name].solid, M.cutFace);
  const lines = new THREE.LineSegments(stl[name].edges, M.edge);
  ctx.cutFaces.push(cut);
  ctx.edges.push(lines);
  return new THREE.Group().add(describe(mesh(stl[name].solid, mat), info, ctx), cut, lines);
}

function legAssembly(stl, ctx) {
  const g = new THREE.Group();
  g.add(casePart("leg", M.alu, stl, ctx));
  if (stl.leg_cap) { const c = casePart("leg_cap", M.tpu, stl, ctx); ctx.legCaps.push(c); g.add(c); }
  return g;
}

function half(side, stl, ctx) {
  const groups = Object.fromEntries([...LAYERS, "legs"].map((n) => [n, new THREE.Group()]));
  groups.pcb.add(pcbGroup(side, ctx));
  for (const k of lay.sides[side].keys) keyGroup(side, k, groups, ctx);
  ledGroups(side, groups, ctx);
  const add = (layer, mat) => { if (stl[`${side}_${layer}`]) groups[layer].add(casePart(`${side}_${layer}`, mat, stl, ctx)); };
  add("bottom", M.alu);
  add("spacer", M.printed);
  add("top", M.alu);
  if (stl.leg) {
    const mirror = new THREE.Matrix4().makeScale(side === "left" ? -1 : 1, 1, 1);
    for (const arr of manifest.legs) {
      const mount = new THREE.Group();
      mount.matrixAutoUpdate = false;
      mount.matrix.multiplyMatrices(mirror, new THREE.Matrix4().fromArray(arr).transpose());
      const swing = legAssembly(stl, ctx);
      ctx.swings.push(swing);
      mount.add(swing);
      groups.legs.add(mount);
    }
    groups.top.add(groups.legs);
  }
  const g = new THREE.Group();
  for (const layer of LAYERS) g.add(groups[layer]);
  g.userData = groups;
  return g;
}

/** Load the case STLs of this build (none is an accepted state: the boards then show without a case). */
async function loadCase(onProgress) {
  const loaded = Object.fromEntries(partNames.map((n) => [n, 0]));
  const report = () => onProgress(partNames.length ? Object.values(loaded).reduce((a, b) => a + b, 0) / partNames.length : 1);
  const loader = new STLLoader();
  const stl = {};
  await Promise.all(partNames.map((n) => new Promise((resolve, reject) => {
    loader.load(manifest.parts[n].file, (g) => {
      g.deleteAttribute("normal");
      stl[n] = { solid: toCreasedNormals(g, CREASE), edges: new THREE.EdgesGeometry(g, 28) };
      loaded[n] = 1; report(); resolve();
    }, (e) => { if (e.total) { loaded[n] = e.loaded / e.total; report(); } }, reject);
  })));
  report();
  return stl;
}

/**
 * Build both halves once and keep them for the page's lifetime: changing the view only moves and hides
 * groups, so no geometry or texture is allocated after this returns.
 */
export async function buildModel(onProgress) {
  // the legends and screens are drawn to canvases, which need the face loaded first; a miss falls back to system-ui
  const [stl] = await Promise.all([loadCase(onProgress), document.fonts.load("600 16px Archivo").catch(() => [])]);
  const ctx = { pickable: [], legends: [], leds: [], swings: [], legCaps: [], edges: [], cutFaces: [] };
  const halves = new Map(SIDES.map((side) => [side, half(side, stl, ctx)]));
  const root = new THREE.Group().add(...halves.values());
  const display = lay.sides.right.display.window_centre;
  return {
    root, halves, pickable: ctx.pickable,
    /** Centre of the right half's screen with the pair in place. */
    displayCentre: new THREE.Vector3(PAIR_DX + cad(display)[0], cad(display)[1], DISPLAY_Z + DISPLAY_T),

    setFinish(id) {
      const f = FINISHES[id];
      M.alu.color.setHex(f.alu);
      M.cap.color.setHex(f.cap);
      M.capMod.color.setHex(f.mod);
      const ink = (hex) => (new THREE.Color(hex).getHSL({}).l > 0.5 ? 0x24262b : 0xe9ebee);
      for (const { decal, onMod } of ctx.legends) decal.material.color.setHex(ink(onMod ? f.mod : f.cap));
    },

    /**
     * scene: "pair" or one side; spread 0..1 slides the left half out of a pair; explode 0..1;
     * legs 0..1 grows the tent legs out of their mounts; swing in degrees.
     */
    setPose({ scene, spread, explode, legs, swing }) {
      for (const [side, h] of halves) {
        const sign = side === "left" ? -1 : 1;
        h.visible = scene === "pair" || scene === side;
        h.position.x = scene === "pair" ? sign * PAIR_DX - (side === "left" ? spread * SPREAD_TRAVEL : 0) : 0;
        for (const layer of LAYERS) h.userData[layer].position.z = explode * EXPLODE[layer];
      }
      const angle = THREE.MathUtils.degToRad(swing);
      for (const s of ctx.swings) { s.rotation.z = angle; s.scale.setScalar(Math.max(legs, 1e-3)); }
      for (const c of ctx.legCaps) c.position.y = explode * EXPLODE_LEG;
    },

    /** flags: one boolean per layer, plus legs, legends and edges. */
    setVisible(flags) {
      for (const h of halves.values()) {
        for (const layer of LAYERS) h.userData[layer].visible = flags[layer];
        h.userData.legs.visible = flags.legs;
      }
      for (const { decal } of ctx.legends) decal.visible = flags.legends;
      for (const e of ctx.edges) e.visible = flags.edges;
    },

    /** Clip everything behind the plane y = clip.constant; the cut faces only exist while clipping. */
    setSection(on) {
      for (const m of clipped) { m.clippingPlanes = on ? [clip] : []; m.needsUpdate = true; }
      for (const c of ctx.cutFaces) c.visible = on;
    },

    /** Light the LEDs: level 0..1, hue in degrees, time in seconds. Returns the hue shown at the centre. */
    setGlow(effect, hue, level, time) {
      const c = new THREE.Color();
      const pulse = effect === "breathe" ? 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(time * 1.6)) : 1;
      const base = effect === "spectrum" || effect === "swirl" ? hue + time * 30 : hue;
      for (const { lit, phases } of ctx.leds) {
        for (const [quads, gain] of lit) {
          phases.forEach((phase, i) => {
            const h = effect === "swirl" ? base + (phase - 0.5) * 300 : base;
            quads.setColorAt(i, c.setHSL(((h % 360) + 360) % 360 / 360, 1, 0.5).multiplyScalar(level * pulse * GLOW_GAIN * gain));
          });
          quads.instanceColor.needsUpdate = true;
          quads.visible = level > 0;
        }
      }
      return ((base % 360) + 360) % 360;
    },

    /** World-space box of the visible solids; `only` limits it to some layers of every visible half. */
    box(only) {
      const box = new THREE.Box3();
      root.updateMatrixWorld(true);
      for (const h of halves.values()) {
        if (!h.visible) continue;
        for (const layer of only ?? LAYERS) {
          h.userData[layer].traverseVisible((o) => { if (o.isMesh && o.userData.mat) box.expandByObject(o); });
        }
      }
      return box;
    },
  };
}
