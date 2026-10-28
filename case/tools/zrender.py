# SPDX-License-Identifier: GPL-3.0-or-later
"""Tiny z-buffer renderer: zrender.py out.png W elev azim stl[:dx,dy,dz[:r,g,b]] ..."""
import sys, numpy as np, trimesh
from PIL import Image
def rot(elev, azim):
    a, e = np.radians(azim), np.radians(elev)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return Rx @ Rz
def main():
    out, W, elev, azim = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    meshes = []
    for spec in sys.argv[5:]:
        parts = spec.split(":")
        m = trimesh.load(parts[0])
        if len(parts) > 1 and parts[1]:
            m.apply_translation([float(v) for v in parts[1].split(",")])
        col = np.array([float(v) for v in parts[2].split(",")]) if len(parts) > 2 else np.array([.78, .8, .84])
        meshes.append((m, col))
    R = rot(elev, azim)
    allv = np.vstack([R @ m.vertices.T for m, _ in meshes] and [(R @ m.vertices.T).T for m, _ in meshes])
    mn, mx = allv.min(0), allv.max(0)
    s = (W - 20) / max(mx[0] - mn[0], mx[1] - mn[1])
    H = int((mx[1] - mn[1]) * s) + 20
    zb = np.full((H, W), -1e9); img = np.ones((H, W, 3))
    light = np.array([-0.3, 0.4, 0.85]); light /= np.linalg.norm(light)
    for m, col in meshes:
        v = (R @ m.vertices.T).T
        p = np.c_[(v[:, 0] - mn[0]) * s + 10, (mx[1] - v[:, 1]) * s + 10, v[:, 2]]
        n = (R @ m.face_normals.T).T
        for f, nn in zip(m.faces, n):
            if nn[2] <= 0: continue
            t = p[f]
            x0, x1 = int(max(t[:, 0].min(), 0)), int(min(t[:, 0].max() + 1, W - 1))
            y0, y1 = int(max(t[:, 1].min(), 0)), int(min(t[:, 1].max() + 1, H - 1))
            if x1 < x0 or y1 < y0: continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-12: continue
            l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
            l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            z = l1 * az + l2 * bz + l3 * cz
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (z > sub)
            sub[upd] = z[upd]
            sh = 0.3 + 0.7 * max(nn @ light, 0)
            sh *= 0.8 + 0.2 * np.clip((t[:, 2].mean() - mn[2]) / max(mx[2] - mn[2], 1e-6), 0, 1)
            img[y0:y1 + 1, x0:x1 + 1][upd] = col * sh
    Image.fromarray((img * 255).astype(np.uint8)).save(out)
main()
