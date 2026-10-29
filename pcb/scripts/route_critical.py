# SPDX-License-Identifier: GPL-3.0-or-later
"""Lay the locked critical routes of one half (spec §9 stage 8).

    python3 pcb/scripts/route_critical.py <side>     (edits pcb/<side>/worxboard-<side>.kicad_pcb)

- QFN-56: Freerouting fans the U1 signal pins out itself at FAN_W (export_dsn.py puts those
  nets in a 0.15 mm class). Here: the joins inside the pad ring (MOAT, between the pad inner
  ends and the exposed pad): 3V3 pins 42/43/44/33/22 and 1/10, 1V1 pins 45/50, TESTEN onto the
  GND pad; 48/49 and 43/44 bridged at the pads; a 3 x 3 via array in the exposed pad; three
  3V3 exits necked to 0.15 mm between the pads, then 0.5 mm.
- USB pair U1 -> R3/R4 -> U4 (pass-through) -> J1, with the receptacle's A/B ties, and the
  J1 escape vias the pair encloses on the right half. A B.Cu track keepout runs under the pair.
- Key matrix: switch -> diode links, rows (F.Cu) and columns (B.Cu), vias at the thumb pads.

Geometry is written in the U1 frame (place.U1_ROT) where it is the same on both halves; the
J1 end is laid per side.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pcbnew  # noqa: E402

from design import POWER_NETS  # noqa: E402
from place import U1_ROT, U4_L_S, USB_NETS, layout_side, mm, pt, rotate, seed_kiids, usb_diagonal  # noqa: E402

FAN_W = 0.15                 # QFN stubs and inner joins
PAIR_W = 0.25
POWER_W = 0.5
PAD_END = 3.875              # QFN pad outer end from the centre
MOAT = 2.3                   # inner joins: between the pad inner ends (3.0) and the exposed pad (1.6)
EP_VIAS = (-1.0, 0.0, 1.0)
PAIR_PITCH = 0.45
USB_CHAMFER = 0.35           # 45 deg corner where the pair leaves the pads
USB_BUMP = 1.2               # D- detour depth (~0.7 mm extra length)
# U1 corner fan-out: (side normal, 45 deg heading, pins from the corner inward), U1 frame
FAN_GROUPS = [
    ((-1, 0), (-1, -1), ["1", "2", "3", "4", "5", "6", "7"]),
    ((0, -1), (-1, -1), ["56", "55", "54", "53", "52", "51", "50"]),
    ((-1, 0), (-1, 1), ["14", "13", "12", "11", "9", "8"]),
    ((0, 1), (-1, 1), ["15", "16", "17", "18"]),
    ((0, 1), (1, 1), ["28", "27", "26", "25", "24", "23", "21"]),
    ((1, 0), (1, 1), ["29", "30", "31", "32", "34", "35", "36", "37", "38"]),
]
FAN_R0 = 0.25                # first bend this far past the pad end
FAN_STAGGER = 0.3            # each next pin bends this much further out
FAN_STAGGER_POWER = 0.6      # after the 3V3 exit (pin 1, 0.5 mm wide)
FAN_RUN = 1.2                # diagonal length
FAN_VIA_PINS = ("17", "29", "30", "31")   # COL0, COL4..COL6: fan end -> via, under U1 on B.Cu
FAN_STAGGER_VIA = 0.45       # beside a via end: (0.4 + 0.45) / sqrt 2 clears via + track
FAN_VIA_STEP = 0.9           # each next via end this much further along its run
KEEPOUT_GROW = 0.6           # B.Cu keepout half-width beyond the pair
U4_KEEPOUT_GAP = 0.3         # left half: the keepout stops this far past U4's row jogs

# Key matrix, key frame (mm from the switch centre, as seen from the top; B.Cu socket pads at
# (-7.085, -2.54) COL and (5.842, -5.08) MX, diode at (0, 5) with the cathode west)
MX_X = 7.0                   # socket pad 2 -> diode anode link (B.Cu), east of the peg hole
ROW_Y = 6.6                  # row line (F.Cu) and row vias, below the diode
COL_X = -8.885               # column line (B.Cu) and column vias, west of the socket
MATRIX_W = 0.25
CLEAR = 0.2
HOLE_CLEAR = 0.25            # copper to a drilled hole
DETOUR_DEPTHS = [0.5 * i for i in range(2, 13)]   # sideways step around a hole keepout
DETOUR_HALF = 3.6            # half-length of the straight part beside the hole
JOG_TRIES = [0.0] + [s * 0.5 * i for i in range(1, 15) for s in (1, -1)]

TESTEN = "19"


class Router:
    def __init__(self, board: pcbnew.BOARD, side: str):
        self.board, self.side = board, side
        self.u1 = board.FindFootprintByReference("U1")
        self.rot = U1_ROT[side]
        c = self.u1.GetPosition()
        self.cx, self.cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
        self.tracks = 0

    # U1 frame <-> board
    def g(self, lx: float, ly: float) -> tuple[float, float]:
        dx, dy = rotate(lx, ly, self.rot)
        return self.cx + dx, self.cy + dy

    def local(self, x: float, y: float) -> tuple[float, float]:
        return rotate(x - self.cx, y - self.cy, -self.rot)

    def pad(self, ref: str, num: str) -> pcbnew.PAD:
        fp = self.board.FindFootprintByReference(ref)
        pads = [p for p in fp.Pads() if p.GetNumber() == num]
        if not pads:
            raise SystemExit(f"{ref} has no pad {num}")
        return pads[0]

    def pad_xy(self, ref: str, num: str) -> tuple[float, float]:
        p = self.pad(ref, num).GetPosition()
        return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)

    def net(self, ref: str, num: str) -> pcbnew.NETINFO_ITEM:
        return self.pad(ref, num).GetNet()

    def track(self, net, pts, width: float, layer=pcbnew.F_Cu) -> None:
        for a, b in zip(pts, pts[1:]):
            if math.dist(a, b) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(pt(*a))
            t.SetEnd(pt(*b))
            t.SetWidth(mm(width))
            t.SetLayer(layer)
            t.SetNet(net)
            t.SetLocked(True)
            self.board.Add(t)
            self.tracks += 1

    def ltrack(self, net, lpts, width: float, layer=pcbnew.F_Cu) -> None:
        self.track(net, [self.g(*p) for p in lpts], width, layer)

    def via(self, net, xy) -> None:
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pt(*xy))
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(net)
        v.SetLocked(True)
        self.board.Add(v)

    # --- QFN ------------------------------------------------------------------------------
    def u1_pads(self) -> dict[str, tuple[float, float]]:
        out = {}
        for p in self.u1.Pads():
            if p.GetNetname() and not p.GetNetname().startswith("unconnected-"):
                out[p.GetNumber()] = self.local(*(pcbnew.ToMM(v) for v in (p.GetPosition().x, p.GetPosition().y)))
        return out

    def qfn_inner(self) -> None:
        """Joins inside the pad ring (between the pad inner ends and the exposed pad)."""
        pads = self.u1_pads()
        gnd, v33, v11 = self.net("U1", "57"), self.net("U1", "42"), self.net("U1", "45")
        lx, ly = pads[TESTEN]                                 # TESTEN straight onto the GND pad
        self.ltrack(self.net("U1", TESTEN), [(lx, ly), (lx, 1.2)], FAN_W)
        # 3V3: 44-43 across the gap, 43-42 across the corner, 48-49 across the gap
        (x43, y43), (x42, y42) = pads["43"], pads["42"]
        self.ltrack(v33, [pads["44"], pads["43"]], FAN_W)
        self.ltrack(v33, [(x43, y43), (x43, -3.1), (3.1, y42), (x42, y42)], FAN_W)
        self.ltrack(v33, [pads["49"], pads["48"]], FAN_W)
        # 3V3 moat east + south (42, 33, 22) and west (1, 10); 1V1 moat north (45, 50)
        (x22, _), (_, y33), (_, y1), (_, y10) = pads["22"], pads["33"], pads["1"], pads["10"]
        self.ltrack(v33, [pads["42"], (MOAT, y42), (MOAT, MOAT), (x22, MOAT), pads["22"]], FAN_W)
        self.ltrack(v33, [pads["33"], (MOAT, y33)], FAN_W)
        self.ltrack(v33, [pads["1"], (-MOAT, y1), (-MOAT, y10), pads["10"]], FAN_W)
        (x50, _), (x45, _) = pads["50"], pads["45"]
        self.ltrack(v11, [pads["50"], (x50, -MOAT), (x45, -MOAT), pads["45"]], FAN_W)
        for vx in EP_VIAS:
            for vy in EP_VIAS:
                self.via(gnd, self.g(vx, vy))

    def power_escapes(self) -> None:
        """3V3 leaves the pad ring east (pin 42) and north (48/49), necked to 0.15 between the
        pads, then 0.5; the west exit (pin 1) leads the north-west fan."""
        pads = self.u1_pads()
        v33 = self.net("U1", "42")
        x42, y42 = pads["42"]
        self.ltrack(v33, [(x42, y42), (PAD_END + 0.45, y42)], FAN_W)
        self.ltrack(v33, [(PAD_END + 0.45, y42), (PAD_END + 1.45, y42)], POWER_W)
        xm = (pads["48"][0] + pads["49"][0]) / 2
        self.ltrack(v33, [(xm, pads["48"][1]), (xm, -PAD_END - 0.25)], FAN_W)
        self.ltrack(v33, [(xm, -PAD_END - 0.25), (xm, -PAD_END - 1.15)], POWER_W)

    def fanout(self) -> None:
        """45 deg corner fan-out of the U1 signal pins (FAN_GROUPS): each half-side bends toward
        a corner, the pin nearest the corner first and each next one FAN_STAGGER further out,
        so neighbouring diagonals stay (0.4 + FAN_STAGGER) / sqrt 2 apart. The ends are staggered
        along the run so the router can reach each from the front and the leading side."""
        pads = self.u1_pads()
        for normal, heading, pins in FAN_GROUPS:
            r = PAD_END + FAN_R0
            vias_done = 0
            for i, num in enumerate(pins):
                lx, ly = pads[num]
                lat = lx if normal[0] == 0 else ly
                def at(rad: float, t: float):
                    return (rad * normal[0], t) if normal[0] else (t, rad * normal[1])
                turn = at(r, lat)
                run = FAN_RUN + FAN_VIA_STEP * vias_done if num in FAN_VIA_PINS else FAN_RUN
                end = (turn[0] + heading[0] * run / math.sqrt(2), turn[1] + heading[1] * run / math.sqrt(2))
                net = self.net("U1", num)
                if num == "1":                     # 3V3: wide once clear of the pads, more room after
                    mid = (turn[0] + heading[0] * 0.4, turn[1] + heading[1] * 0.4)
                    self.ltrack(net, [(lx, ly), turn, mid], FAN_W)
                    self.ltrack(net, [mid, end], POWER_W)
                else:
                    self.ltrack(net, [(lx, ly), turn, end], FAN_W)
                if num in FAN_VIA_PINS:            # columns drop to B.Cu to cross under U1
                    self.via(net, self.g(*end))
                    vias_done += 1
                nxt = pins[i + 1] if i + 1 < len(pins) else None
                wide = num == "1" or num in FAN_VIA_PINS or nxt in FAN_VIA_PINS
                r += FAN_STAGGER_POWER if num == "1" else FAN_STAGGER_VIA if wide else FAN_STAGGER
        # XIN straight down into the crystal
        y1 = self.local(*self.pad_xy("Y1", "1"))
        lx, ly = pads["20"]
        self.ltrack(self.net("U1", "20"), [(lx, ly), (lx, y1[1] - 1.5), (y1[0], y1[1] - 1.5 + abs(y1[0] - lx)), y1], FAN_W)

    @staticmethod
    def fanout_nets(board: pcbnew.BOARD) -> list[str]:
        """U1 signal nets: Freerouting routes them at FAN_W (export_dsn.py)."""
        u1 = board.FindFootprintByReference("U1")
        skip = set(POWER_NETS) | set(USB_NETS)
        return sorted({p.GetNetname() for p in u1.Pads()
                       if p.GetNetname() and not p.GetNetname().startswith("unconnected-")} - skip)

    # --- USB ------------------------------------------------------------------------------
    def usb(self) -> list[list[tuple[float, float]]]:
        """Lay the pair; return its centre-line(s) for the keepout."""
        pads = self.u1_pads()
        dp, dm = self.net("U1", "47"), self.net("U1", "46")
        (xp, yp), (xm, ym) = pads["47"], pads["46"]
        # U1 frame: north out of the pads (DP outer), east into R3 / R4
        r3, r4 = (self.local(*self.pad_xy(r, "2")) for r in ("R3", "R4"))
        yP, yM = -PAD_END - 0.975, -PAD_END - 0.525
        x_wide = 2.6                                          # 0.15 -> 0.25 past the corner pins
        # out of the pads with 45 deg chamfers (D- bends first, clear of pad 45)
        c = USB_CHAMFER
        self.ltrack(dp, [(xp, yp), (xp, yP + c), (xp + c, yP), (x_wide, yP)], FAN_W)
        self.ltrack(dm, [(xm, ym), (xm, yM + c), (xm + c, yM), (x_wide, yM)], FAN_W)
        ry = r3[1]
        self.ltrack(dp, [(x_wide, yP), (r3[0] - 0.6 - abs(ry - yP), yP), (r3[0] - 0.6, ry), r3], PAIR_W)
        # D- is the inner line of every bend: a 45 deg bump toward the pads evens the lengths
        b0, d = x_wide + 0.3, USB_BUMP
        ry = r4[1]
        self.ltrack(dm, [(x_wide, yM), (b0, yM), (b0 + d, yM + d), (b0 + d + 0.5, yM + d),
                         (b0 + d + 0.5 + abs(yM + d - ry), ry), r4], PAIR_W)
        self.u4_vias()
        start = [self.g(xp, yP), self.g(r3[0], (yP + yM) / 2)]
        if self.side == "right":
            return [start, *self.usb_right(dp, dm)]
        return [start, *self.usb_left(dp, dm)]

    def u4_vias(self) -> None:
        """U4 GND (pin 2) and VBUS (pin 5) leave between the pass-through rows to vias."""
        u4 = self.board.FindFootprintByReference("U4").GetPosition()
        c = (pcbnew.ToMM(u4.x), pcbnew.ToMM(u4.y))
        for num, width in (("2", POWER_W), ("5", POWER_W)):
            p = self.pad_xy("U4", num)
            d = math.dist(p, c)
            v = (p[0] + (p[0] - c[0]) / d * 1.15, p[1] + (p[1] - c[1]) / d * 1.15)
            self.track(self.net("U4", num), [p, v], width)
            self.via(self.net("U4", num), v)

    def usb_right(self, dp, dm) -> list[list[tuple[float, float]]]:
        """Right half: R3/R4 -> U4 rows (rot 0) -> shallow U under the J1 pad row -> rear pads."""
        r3o, r4o = (self.pad_xy(r, "1") for r in ("R3", "R4"))
        u4 = {n: self.pad_xy("U4", n) for n in ("1", "6", "3", "4")}
        for net, r_out, u_in in ((dp, r3o, u4["1"]), (dm, r4o, u4["3"])):
            ry, uy = r_out[1], u_in[1]
            self.track(net, [r_out, (r_out[0] + 0.5, ry), (r_out[0] + 0.5 + abs(uy - ry), uy), u_in], PAIR_W)
        self.track(dp, [u4["1"], u4["6"]], PAIR_W)
        self.track(dm, [u4["3"], u4["4"]], PAIR_W)
        p6, p4 = u4["6"], u4["4"]
        b6, a7 = self.pad_xy("J1", "B6"), self.pad_xy("J1", "A7")
        rear = b6[1] + 0.725                                  # pad rear end
        x_dm, x_dp = p4[0] + 1.9, p4[0] + 2.35
        y_dp, y_dm = rear + 1.53, rear + 1.98
        self.track(dp, [p6, (x_dp - 0.6, p6[1]), (x_dp, p6[1] + 0.6), (x_dp, y_dp), (b6[0], y_dp), b6], PAIR_W)
        self.track(dm, [p4, (x_dm, p4[1]), (x_dm, y_dm), (a7[0], y_dm), a7], PAIR_W)
        self.j1_ties(dp, dm)
        self.j1_escapes(rear)
        return [[self.g(*self.local(*r3o)), ((p6[0] + p4[0]) / 2, (p6[1] + p4[1]) / 2)]]

    def usb_left(self, dp, dm) -> list[list[tuple[float, float]]]:
        """Left half: R3/R4 -> straight run with U4 on it (rotated) -> J1 rear pads."""
        j1 = self.board.FindFootprintByReference("J1").GetPosition()
        a, b = usb_diagonal(self.side, (pcbnew.ToMM(j1.x), pcbnew.ToMM(j1.y)))
        n = math.dist(a, b)
        u = ((b[0] - a[0]) / n, (b[1] - a[1]) / n)
        left = (u[1], -u[0])                                  # y down: left-hand normal

        def P(s: float, off: float) -> tuple[float, float]:
            return a[0] + s * u[0] + off * left[0], a[1] + s * u[1] + off * left[1]
        s4 = U4_L_S
        hp, row = PAIR_PITCH / 2, 0.95
        jog = row - hp
        lines = (("DP", dp, "R3", +1, "1", "6", "B6"), ("DM", dm, "R4", -1, "3", "4", "A7"))
        for _, net, rref, sign, u_in, u_out, jpad in lines:
            r_out = self.pad_xy(rref, "1")
            pin_in, pin_out, pad = self.pad_xy("U4", u_in), self.pad_xy("U4", u_out), self.pad_xy("J1", jpad)
            col = pad[0]
            s_c = (col - a[0] - sign * hp * left[0]) / u[0]
            pts = [r_out, (r_out[0] - 0.5, r_out[1]), P(0, sign * hp),
                   P(s4 - 2.6 - jog, sign * hp), P(s4 - 2.6, sign * row), pin_in, pin_out,
                   P(s4 + 2.6, sign * row), P(s4 + 2.6 + jog, sign * hp), P(s_c, sign * hp), pad]
            self.track(net, pts, PAIR_W)
        self.j1_ties(dp, dm)
        # no keepout across U4: its pins 2 / 5 sit between the split rows, and the VBUS via
        # can only leave on B.Cu (docs/deviations.md WS2b-7)
        end = (b[0] - a[0]) / u[0] if abs(u[0]) > 1e-9 else n
        gap = 2.6 + jog + U4_KEEPOUT_GAP
        return [[P(0, 0), P(s4 - gap, 0)], [P(s4 + gap, 0), P(end, 0)]]

    def j1_ties(self, dp, dm) -> None:
        """A6/B6 (DP) tied in front of the pad row, A7/B7 (DM) behind it."""
        b6, a6, a7, b7 = (self.pad_xy("J1", n) for n in ("B6", "A6", "A7", "B7"))
        tie_rear, tie_front = b6[1] + 0.725 + 0.68, b6[1] - 1.295
        self.track(dm, [a7, (a7[0], tie_rear), (b7[0], tie_rear), b7], PAIR_W)
        self.track(dp, [b6, (b6[0], tie_front), (a6[0], tie_front), a6], PAIR_W)

    def j1_escapes(self, rear: float) -> None:
        gnd_pad, vbus, cc2 = self.pad_xy("J1", "B12"), self.pad_xy("J1", "B9"), self.pad_xy("J1", "B5")
        sh = min((self.pad_xy_all("J1", "SH")), key=lambda p: math.dist(p, gnd_pad) + abs(p[1] - gnd_pad[1]) * 2)
        self.track(self.net("J1", "B12"), [gnd_pad, (gnd_pad[0], sh[1] + 0.6), (sh[0], sh[1] + 0.6)], POWER_W)
        v = (vbus[0], rear + 0.7)
        self.track(self.net("J1", "B9"), [vbus, v], POWER_W)
        self.via(self.net("J1", "B9"), v)
        c = (cc2[0] + 0.25, rear + 0.73)
        self.track(self.net("J1", "B5"), [cc2, (cc2[0], rear + 0.3), c], PAIR_W)
        self.via(self.net("J1", "B5"), c)

    def pad_xy_all(self, ref: str, num: str) -> list[tuple[float, float]]:
        fp = self.board.FindFootprintByReference(ref)
        return [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in fp.Pads() if p.GetNumber() == num]

    # --- matrix ---------------------------------------------------------------------------
    def matrix(self, keys: list[dict]) -> None:
        """Switch -> diode links for every key; rows (F.Cu) and columns (B.Cu) of the main
        block as straight lines with 45 deg jogs; vias at the 25 deg thumb keys' row and column
        pads so Freerouting only meets round items there."""
        fps = {f.GetField("Key").GetText() + ":" + f.GetReference()[:1]: f
               for f in self.board.GetFootprints() if f.HasField("Key")}
        self.obst = {pcbnew.F_Cu: self.obstacles(pcbnew.F_Cu), pcbnew.B_Cu: self.obstacles(pcbnew.B_Cu)}
        rows, cols = {}, {}
        for k in keys:
            sk, d = fps[k["id"] + ":S"], fps[k["id"] + ":D"]
            frame = KeyFrame(k)
            p1, p2 = (frame.local(*self.pad_xy(sk.GetReference(), n)) for n in ("1", "2"))
            dk, da = (frame.local(*self.pad_xy(d.GetReference(), n)) for n in ("1", "2"))
            mx = self.net(sk.GetReference(), "2")
            self.track(mx, [frame.g(*q) for q in (p2, (MX_X, p2[1]), (MX_X, da[1]), da)], MATRIX_W, pcbnew.B_Cu)
            row, col = self.net(d.GetReference(), "1"), self.net(sk.GetReference(), "1")
            rv, cv = frame.g(dk[0], ROW_Y), frame.g(COL_X, p1[1])
            if k["rot"] != 0:                          # thumbs: first via spot clear of holes
                rv = self.via_spot(row, [frame.g(dk[0] + dx, ROW_Y) for dx in (0, -1.0, 1.0, -2.0)])
                cv = self.via_spot(col, [frame.g(COL_X, p1[1] + dy) for dy in (0, 1.2, -1.2, 2.4, -2.4)])
            self.track(row, [frame.g(*dk), rv], MATRIX_W, pcbnew.B_Cu)
            self.via(row, rv)
            self.track(col, [frame.g(*p1), cv], MATRIX_W, pcbnew.B_Cu)
            self.via(col, cv)
            if k["rot"] == 0:
                rows.setdefault(k["row"], []).append((k, rv, row))
                cols.setdefault(k["col"], []).append((k, cv, col))
        for members in rows.values():
            members.sort(key=lambda m: m[1][0])
            for (ka, a, net), (kb, b, _) in zip(members, members[1:]):
                self.track(net, self.jogged(a, b, (ka["x"] + kb["x"]) / 2, 0, pcbnew.F_Cu, net), MATRIX_W, pcbnew.F_Cu)
        for members in cols.values():
            members.sort(key=lambda m: m[1][1])
            for (ka, a, net), (kb, b, _) in zip(members, members[1:]):
                self.track(net, self.jogged(a, b, (ka["y"] + kb["y"]) / 2, 1, pcbnew.B_Cu, net), MATRIX_W, pcbnew.B_Cu)

    def via_spot(self, net, spots: list[tuple[float, float]]) -> tuple[float, float]:
        from shapely.geometry import Point
        code = net.GetNetCode()
        for p in spots:
            disc = Point(p).buffer(0.3)
            if not any(g.intersects(disc) for layer in self.obst for g, c in self.obst[layer] if c != code):
                return p
        raise SystemExit(f"{net.GetNetname()}: no clear via spot near {spots[0]}")

    def obstacles(self, layer) -> list:
        """(geometry, net code) of every pad and hole on `layer` (holes: all layers)."""
        from shapely.geometry import Point, box
        out = []
        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                if pad.HasHole() and pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    r = pcbnew.ToMM(pad.GetDrillSize().x) / 2
                    out.append((Point(*self.xy(pad.GetPosition())).buffer(r + HOLE_CLEAR), -1))
                elif pad.IsOnLayer(layer):
                    bb = pad.GetBoundingBox()
                    (x0, y0), (x1, y1) = self.xy(bb.GetOrigin()), self.xy(bb.GetEnd())
                    out.append((box(x0, y0, x1, y1).buffer(CLEAR), pad.GetNetCode()))
        for z in self.board.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.IsOnLayer(layer):
                from shapely.geometry import Polygon
                o = z.Outline().Outline(0)
                out.append((Polygon([self.xy(o.CPoint(i)) for i in range(o.PointCount())]), -1))
        return out

    @staticmethod
    def xy(v) -> tuple[float, float]:
        return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)

    def jogged(self, a, b, mid: float, axis: int, layer, net) -> list[tuple[float, float]]:
        """a -> b along `axis` (0 = x, 1 = y) with one 45 deg jog near `mid`, clear of pads of
        other nets and of holes; the jog slides along the run until it fits."""
        from shapely.geometry import LineString
        da = abs(b[1 - axis] - a[1 - axis])
        code = net.GetNetCode()

        def clear(pts) -> bool:
            line = LineString(pts).buffer(MATRIX_W / 2)
            return not any(g.intersects(line) for g, c in self.obst[layer] if c != code)

        def P(along: float, across: float) -> tuple[float, float]:
            return (along, across) if axis == 0 else (across, along)
        a0, a1, b1 = a[axis], a[1 - axis], b[1 - axis]
        for off in JOG_TRIES:
            m = mid + off
            pts = [a, P(m - da / 2, a1), P(m + da / 2, b1), b]
            if clear(pts):
                return pts
        # a straight run blocked by a hole keepout: step around it with a 45 deg trapezoid
        if da < 1e-6:
            n = int(abs(b[axis] - a0))
            sign = 1 if b[axis] > a0 else -1
            for depth in DETOUR_DEPTHS:
                for side in (1, -1):
                    for c in range(2, n - 1):
                        cx = a0 + sign * c
                        h = depth + DETOUR_HALF
                        pts = [a, P(cx - sign * h, a1), P(cx - sign * (h - depth), a1 + side * depth),
                               P(cx + sign * (h - depth), a1 + side * depth), P(cx + sign * h, a1), b]
                        if clear(pts):
                            return pts
        raise SystemExit(f"{net.GetNetname()}: no clear route between {a} and {b}")

    def keepout(self, lines: list[list[tuple[float, float]]]) -> None:
        """B.Cu track keepout under the pair (fills still allowed)."""
        from shapely.geometry import LineString
        from shapely.ops import unary_union
        geom = unary_union([LineString(l).buffer(PAIR_PITCH / 2 + KEEPOUT_GROW, cap_style=2, join_style=2)
                            for l in lines if len(l) > 1])
        for poly in getattr(geom, "geoms", [geom]):
            z = pcbnew.ZONE(self.board)
            z.SetIsRuleArea(True)
            z.SetLayer(pcbnew.B_Cu)
            z.SetDoNotAllowTracks(True)
            z.SetDoNotAllowVias(False)
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowZoneFills(False)
            z.SetDoNotAllowFootprints(False)
            z.SetZoneName("USB_KEEPOUT")
            o = z.Outline()
            o.NewOutline()
            for x, y in list(poly.exterior.coords)[:-1]:
                o.Append(mm(x), mm(y))
            self.board.Add(z)


class KeyFrame:
    """Switch frame: KiCad screen rotation about the key centre."""
    def __init__(self, k: dict):
        self.x, self.y, self.rot = k["x"], k["y"], k["rot"]

    def g(self, lx: float, ly: float) -> tuple[float, float]:
        dx, dy = rotate(lx, ly, self.rot)
        return self.x + dx, self.y + dy

    def local(self, x: float, y: float) -> tuple[float, float]:
        return rotate(x - self.x, y - self.y, -self.rot)


def offset(pts: list[tuple[float, float]], d: float) -> list[tuple[float, float]]:
    """Polyline offset by d to the left of travel (y down: left normal = (dy, -dx)), mitred."""
    def normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        return dy / n, -dx / n
    segs = [normal(a, b) for a, b in zip(pts, pts[1:])]
    out = []
    for i, (x, y) in enumerate(pts):
        ns = segs[max(i - 1, 0):i + 1]
        mx, my = sum(n[0] for n in ns), sum(n[1] for n in ns)
        m = math.hypot(mx, my)
        mx, my = mx / m, my / m
        k = d / (mx * ns[0][0] + my * ns[0][1])
        out.append((x + mx * k, y + my * k))
    return out


def clear_locked(board: pcbnew.BOARD) -> None:
    """Re-running replaces the critical routes (and nothing else)."""
    for t in list(board.GetTracks()):
        if t.IsLocked():
            board.Delete(t)
    for z in list(board.Zones()):
        if z.GetZoneName() == "USB_KEEPOUT":
            board.Delete(z)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("left", "right"):
        print(__doc__)
        return 2
    side = argv[1]
    path = ROOT / "pcb" / side / f"worxboard-{side}.kicad_pcb"
    seed_kiids(side, b"route_critical", path.read_bytes())
    board = pcbnew.LoadBoard(str(path))
    clear_locked(board)
    r = Router(board, side)
    r.qfn_inner()
    r.power_escapes()
    r.fanout()
    r.keepout(r.usb())
    r.matrix(layout_side(side)["keys"])
    board.Save(str(path))
    print(f"{side}: {r.tracks} locked track segments")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
