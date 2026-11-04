"""Internal-corner check of the machined case parts against JLCCNC's CNC Machining Design Guideline
(deviation CASE-8).

Reads the exported STEPs (case/exports) of both tops, both bottoms and the leg, finds every vertical
internal corner (a concave Z-axis cylinder face that is not a full hole, a sharp concave vertical edge,
or a chord vertex of a polygonised arc), finds the face the cutter reaches it from by casting rays up and
down from the cavity beside it, and fails unless its radius is at least worxboard_case.corner_r() of that
depth. Exempt, and listed: the switch and stabiliser cut-outs (R0.5, a 1 mm end mill, through the
1.5 mm plate at the bottom of the open key well; ORDER_NOTES), the engraved side mark, and side
operations (corners closed above and below: the USB-C recess).

    python case/corner_check.py case/exports
"""
import math
import os
import sys
from collections import defaultdict

from build123d import Edge, Face, Sketch, Vector, import_step
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.collections import (
    IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as EdgeFaceMap)
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Line
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import worxboard_case as E  # noqa: E402

SHARP_TURN = 30.0    # an edge turning more than this is a corner; less, a vertex of a polygonised arc


def _cutouts(side: str):
    """Switch and stabiliser cut-outs (part frame, shapely), grown 0.1 to catch their corner faces."""
    s = Sketch()
    for kx, ky, w, h, rot in E.KEYS(side):
        s += E.switch_cut(kx, ky, rot)
    for kx, ky, w, h, rot, sd in E.stab_keys(side):
        s += E.stab_cuts(kx, ky, rot, sd)
    polys = [Polygon([(q.X, q.Y) for e in f.outer_wire().edges()
                      for q in (e.position_at(t / 8) for t in range(8))]) for f in s.faces()]
    return unary_union(polys).buffer(0.1)


# STEP stem: (face a cutter from above enters by, side whose switch cut-outs are exempt, engraving depth);
# a cutter from below enters by the part's lowest face (the tops' parting face)
PARTS = {
    "right_top": (E.Z_TOP, "right", None),
    "left_top": (E.Z_TOP, "left", None),
    "right_bottom": (E.Z_SPLIT, None, E.ENGRAVE_DEPTH),
    "left_bottom": (E.Z_SPLIT, None, E.ENGRAVE_DEPTH),
    "leg": (E.LEG_HUB_L, None, None),
}


def corners(part):
    """Yield (kind, radius, z0, z1, x, y, probe point in the cavity beside it) for every vertical
    internal corner of the part."""
    for f in part.faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        cyl = a.Cylinder()
        if abs(abs(cyl.Axis().Direction().Z()) - 1) > 1e-6:
            continue
        r, loc = cyl.Radius(), cyl.Axis().Location()
        c = f.center()
        to_axis = Vector(loc.X() - c.X, loc.Y() - c.Y, 0)
        if f.normal_at(c).dot(to_axis) <= 0:          # convex: a boss, not a corner
            continue
        if math.degrees(a.LastUParameter() - a.FirstUParameter()) > 359:
            continue                                  # a hole
        bb = f.bounding_box()
        probe = c + to_axis * (min(0.3, r / 2) / max(to_axis.length, 1e-9))
        yield "fillet", r, bb.min.Z, bb.max.Z, c.X, c.Y, probe
    m = EdgeFaceMap()
    TopExp.MapShapesAndAncestors_s(part.wrapped, TopAbs_EDGE, TopAbs_FACE, m)
    for i in range(1, m.Extent() + 1):
        e = TopoDS.Edge(m.FindKey(i))
        ca = BRepAdaptor_Curve(e)
        if ca.GetType() != GeomAbs_Line or abs(abs(ca.Line().Direction().Z()) - 1) > 1e-6:
            continue
        fl = m.FindFromIndex(i)
        if fl.Size() != 2:
            continue
        fs = [Face(TopoDS.Face(s)) for s in fl]
        edge = Edge(e)
        p = edge.position_at(0.5)
        n1, n2 = fs[0].normal_at(p), fs[1].normal_at(p)
        if abs(n1.dot(n2)) > 0.999:
            continue
        if not (part.is_inside(p + (n1 - n2) * 0.02) and part.is_inside(p + (n2 - n1) * 0.02)):
            continue                                  # convex edge
        turn = math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        bb = edge.bounding_box()
        probe = p + (n1 + n2).normalized() * 0.05
        if turn >= SHARP_TURN:
            yield "sharp", 0.0, bb.min.Z, bb.max.Z, p.X, p.Y, probe
        else:   # vertex of a polygonised arc: its radius from the longer chord. Only an arc's end vertex,
                # next to a partial chord, reads high; its inner vertices read the arc's own radius.
            w = max(math.hypot(f.bounding_box().size.X, f.bounding_box().size.Y) for f in fs)
            yield "arc", w / (2 * math.sin(math.radians(turn) / 2)), bb.min.Z, bb.max.Z, p.X, p.Y, probe


def check(path: str, up_face: float, side: str | None, engrave: float | None) -> list[str]:
    part = import_step(path)
    bb = part.bounding_box()
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(part.wrapped, 1e-6)

    def open_to(q, up: bool) -> bool:
        inter.Perform(gp_Lin(gp_Pnt(q.X, q.Y, q.Z), gp_Dir(0, 0, 1 if up else -1)), 1e-4, 1e3)
        return inter.NbPnt() == 0

    cut = _cutouts(side) if side else None
    rows = defaultdict(int)
    bad = []
    for kind, r, z0, z1, x, y, q in corners(part):
        up = open_to(Vector(q.X, q.Y, z1 - 0.05), True)
        dn = open_to(Vector(q.X, q.Y, z0 + 0.05), False)
        depths = ([max(z1, up_face) - z0] if up else []) + ([z1 - bb.min.Z] if dn else [])
        if not depths:
            why = "side operation"
        elif engrave is not None and z1 <= engrave + 1e-6:
            why = "engraving"
        elif cut is not None and r >= E.SWITCH_CUT_R - 1e-6 and cut.contains(Point(x, y)) \
                and abs(z0 - E.Z_PLATE_BOT) < 0.02 and abs(z1 - E.Z_PLATE_TOP) < 0.02:
            why = "switch / stabiliser cut-out"
        else:
            depth = min(depths)
            need = E.corner_r(depth)
            why = "ok"
            if r < need - 1e-3:
                bad.append(f"{kind} at ({x:.2f},{y:.2f}) Z {z0:.2f}-{z1:.2f}: "
                           f"R{r:.2f} < R{need} for {depth:.1f} deep")
                why = "BELOW THE RULE"
        rows[(why, kind)] += 1
    name = os.path.basename(path)
    summary = ", ".join(f"{n} {kind} {why}" for (why, kind), n in sorted(rows.items()))
    print(f"  {name}: {summary}")
    return [f"{name}: {b}" for b in bad]


def main(exports: str):
    print("Internal corners vs JLCCNC (R = depth/10 + 0.5, tool table past 10 mm, R0.5 to 3 mm):")
    bad = []
    for stem, (up_face, side, engrave) in PARTS.items():
        bad += check(os.path.join(exports, f"worxboard_{stem}.step"), up_face, side, engrave)
    if bad:
        print("\n".join("  " + b for b in bad))
        sys.exit(f"corner check failed: {len(bad)} internal corner(s) below JLCCNC's minimum radius")
    print("corner check passed: every internal corner meets JLCCNC's rule (exemptions listed above)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(E.ROOT, "case", "exports"))
