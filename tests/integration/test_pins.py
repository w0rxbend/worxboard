# SPDX-License-Identifier: GPL-3.0-or-later
"""Firmware devicetree vs the WS2 PCB vs layout/pins.py (spec §14 WS5, §3, §5, §6.2, §11.2).

Firmware: the committed board files of both targets, plus every built zephyr.dts under build/fw/
(`just fw`). PCB: the committed boards, plus the exported netlists under build/<side>/
(`just pcb-sch-all`). Missing build outputs are skipped; the committed files are always checked.

The chain test walks every switch: socket and diode nets on the PCB -> the RP2040 GPIO on each net
-> the firmware's (row, col) for those GPIOs, with col-offset -> the transform position -> the key
layout.json puts there. It is the check that a key press reaches the right keymap slot.
"""
from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

import fwdt
import pcbdata
from layout import pins

ROOT = Path(__file__).resolve().parents[2]
BOARDS = ROOT / "firmware/zmk/boards/worxbend"
FW_OUT = ROOT / "build/fw"
LAYOUT = json.loads((ROOT / "layout/build/layout.json").read_text())
SIDES = ("left", "right")
TARGETS = ("worxboard", "worxboard2")          # RP2040 rev A, RP2350A experimental
CORE = "worxboard"
ROW = re.compile(r"^ROW\d$")
COL = re.compile(r"^COL\d$")
DIODE_K, DIODE_A = "1", "2"                    # Diode:1N4148W / D_SOD-123 pad numbers
JACK_RES = "1k"                                # series resistors between the jack and UART0 (§6.2)
UNCONNECTED = "unconnected-"


def build_rows() -> list[tuple[str, str]]:
    """(artifact, board) of every build.yaml row."""
    text = (ROOT / "build.yaml").read_text()
    return [(m["artifact"], m["board"]) for m in re.finditer(
        r"board:\s*(?P<board>[\w/]+).*?artifact-name:\s*(?P<artifact>\w+)", text)]


def side_of(board: str) -> str:
    return re.match(r"worxboard2?_(left|right)", board).group(1)


def source_fw(target: str, side: str) -> fwdt.FwPins:
    (dts,) = (BOARDS / target).glob(f"{target}_{side}_*.dts")
    return fwdt.source(dts)


def fw_variants() -> list:
    """Every firmware view: (side, reader, target-or-artifact)."""
    out = [pytest.param(side, "source", t, id=f"source-{t}-{side}") for t in TARGETS for side in SIDES]
    for artifact, board in build_rows():
        dts = FW_OUT / artifact / "zephyr/zephyr.dts"
        built = pytest.mark.skipif(not dts.exists(), reason=f"{artifact} not built (just fw)")
        out.append(pytest.param(side_of(board), "compiled", artifact, id=f"compiled-{artifact}", marks=built))
    return out


def load_fw(reader: str, name: str, side: str) -> fwdt.FwPins:
    if reader == "source":
        return source_fw(name, side)
    return fwdt.compiled(FW_OUT / name / "zephyr/zephyr.dts")


NO_NETLIST = pytest.mark.skipif(not all(pcbdata.netlist_path(s).exists() for s in SIDES),
                                reason="netlists not exported (just pcb-sch-all)")
PCB_KINDS = ("board", "netlist")               # committed boards always; netlists when exported


def pcb_kinds() -> list:
    return [pytest.param(k, marks=NO_NETLIST if k == "netlist" else ()) for k in PCB_KINDS]


def pcb_sources() -> list:
    return [pytest.param(k, s, id=f"{k}-{s}", marks=NO_NETLIST if k == "netlist" else ())
            for k in PCB_KINDS for s in SIDES]


def load_pcb(kind: str, side: str) -> pcbdata.Pcb:
    return pcbdata.netlist(side) if kind == "netlist" else pcbdata.board(side)


def transform_order() -> list[tuple[str, str]]:
    return [(e["side"], e["id"]) for e in LAYOUT["transform_order"]]


# ---- firmware vs layout/pins.py -------------------------------------------------------------------

@pytest.mark.parametrize("side, reader, name", fw_variants())
def test_firmware_pins_match_pins_py(side, reader, name):
    fw = load_fw(reader, name, side)
    by_net = [pins.gpio(f"COL{i}") for i in range(len(pins.COL_GPIOS))]      # COL0 outer .. COL6 inner
    cols, by_net = (pins.COL_GPIOS, by_net) if side == "left" else (pins.RIGHT_COL_GPIOS, by_net[::-1])
    assert [g.pin for g in fw.rows] == list(pins.ROW_GPIOS) == [pins.gpio(f"ROW{i}") for i in range(6)]
    assert all(g.flags == fwdt.PULL_DOWN for g in fw.rows), "rows: active high with pull-down (col2row)"
    assert [g.pin for g in fw.cols] == list(cols) == by_net
    assert all(g.flags == 0 for g in fw.cols), "columns: plain active-high outputs"
    assert fw.col_offset == (0 if side == "left" else len(pins.COL_GPIOS))
    assert fw.uart == {"TX": pins.UART_TX, "RX": pins.UART_RX}
    assert fw.uart == {"TX": pins.gpio("UART_TX"), "RX": pins.gpio("UART_RX")}
    assert fw.uart_input == {pins.UART_RX}
    spi = {k: g.pin for k, g in fw.spi.items() if k != "miso"}
    assert spi == {"clk": pins.DISP_SCK, "mosi": pins.DISP_MOSI, "cs": pins.DISP_CS}
    assert spi == {"clk": pins.gpio("DISP_SCK"), "mosi": pins.gpio("DISP_MOSI"), "cs": pins.gpio("DISP_CS")}
    assert fw.spi["cs"].flags & fwdt.ACTIVE_LOW == 0, "the LS011B7DH03 chip select is active high"
    assert fw.pio1 == {pins.DISP_SCK, pins.DISP_MOSI}


def check_pio_spi_pins(fw: fwdt.FwPins) -> None:
    """The PIO SPI muxes clk, mosi and miso to PIO1 on its first transfer, after the UART and kscan
    have claimed theirs: none of them may be a UART, row or column pin. miso is never driven, so it
    must reuse MOSI (as ZMK's pico-spi-pio examples do) or be a spare pin with no net."""
    taken = {pins.UART_TX: "UART_TX", pins.UART_RX: "UART_RX"} | \
        {g: f"ROW{i}" for i, g in enumerate(pins.ROW_GPIOS)} | {g: f"COL{i}" for i, g in enumerate(pins.COL_GPIOS)}
    for role in ("clk", "mosi", "miso"):
        pin = fw.spi[role].pin
        assert pin not in taken, f"PIO SPI {role} on GP{pin} takes {taken[pin]} away"
    spare = {int(p.name[4:].split("/")[0]) for p in pins.PINS if p.net is None}
    assert fw.spi["miso"].pin in {fw.spi["mosi"].pin} | spare


@pytest.mark.parametrize("side, reader, name", fw_variants())
def test_display_spi_keeps_off_uart_and_matrix(side, reader, name):
    check_pio_spi_pins(load_fw(reader, name, side))


@pytest.mark.parametrize("miso", [None, pins.UART_RX, pins.ROW_GPIOS[0], pins.COL_GPIOS[-1], pins.DISP_CS])
def test_display_spi_check_rejects(miso):
    """No miso-gpios (the driver then takes GP0, UART TX) or a miso on a used pin must fail."""
    fw = source_fw(CORE, "left")
    spi = {k: v for k, v in fw.spi.items() if k != "miso"}
    text = fwdt.COMMENT.sub("", fwdt._flatten(next((BOARDS / CORE).glob("worxboard_left_*.dts"))))
    text = re.sub(r"miso-gpios\s*=[^;]*;", "" if miso is None else f"miso-gpios = <&gpio0 {miso} 0>;", text)
    bad = fwdt.parse(text)
    assert {k: v for k, v in bad.spi.items() if k != "miso"} == spi
    with pytest.raises(AssertionError):
        check_pio_spi_pins(bad)


@pytest.mark.parametrize("side, reader, name", fw_variants())
def test_firmware_transform_is_layout_order(side, reader, name):
    fw = load_fw(reader, name, side)
    assert fw.transform == tuple(tuple(e["rc"]) for e in LAYOUT["transform_order"])


@pytest.mark.parametrize("side, reader, name", [p for p in fw_variants() if p.values[1] == "compiled"])
def test_compiled_dts_equals_board_files(side, reader, name):
    """The build applied the board files as written: no snippet or shield moved a pin."""
    assert load_fw(reader, name, side) == source_fw(CORE, side)


@pytest.mark.parametrize("side", SIDES)
def test_rp2350_target_shares_the_pinout(side):
    assert source_fw("worxboard2", side) == source_fw(CORE, side)


# ---- PCB vs layout/pins.py ------------------------------------------------------------------------

@pytest.mark.parametrize("kind, side", pcb_sources())
def test_pcb_gpio_nets_match_pins_py(kind, side):
    pcb = load_pcb(kind, side)
    pad_of = {g: pad for pad, g in pcb.gpio_pads.items()}
    for p in pins.PINS:
        m = pcbdata.GPIO_NAME.match(p.name)
        if not m:
            continue
        net = pcb.parts[pcbdata.MCU].pads.get(pad_of[int(m.group(1))], "")
        if p.net is None:
            assert net == "" or net.startswith(UNCONNECTED), f"{p.name} should be unconnected, is on {net}"
        else:
            assert net == p.net, f"{pcb.source}: {p.name} on {net}, pins.py says {p.net}"


@pytest.mark.parametrize("side", SIDES)
def test_netlist_names_match_the_board_pad_map(side):
    """The board reader's assumptions: RP2040 pads by pins.py QFN number, diode pad 1 = cathode."""
    if not pcbdata.netlist_path(side).exists():
        pytest.skip("netlist not exported (just pcb-sch-all)")
    nl = pcbdata.netlist(side)
    assert nl.gpio_pads == pcbdata.QFN_GPIO
    for _, diode in nl.matrix().values():
        assert (diode.names[DIODE_K], diode.names[DIODE_A]) == ("K", "A")


@pytest.mark.parametrize("side", SIDES)
def test_netlist_equals_committed_board(side):
    if not pcbdata.netlist_path(side).exists():
        pytest.skip("netlist not exported (just pcb-sch-all)")
    nl, brd = pcbdata.netlist(side), pcbdata.board(side)
    refs = {r for r in nl.parts if not r.startswith("#")}
    assert refs <= set(brd.parts), f"parts missing on the board: {sorted(refs - set(brd.parts))}"
    for ref in sorted(refs):
        assert brd.parts[ref].pads == nl.parts[ref].pads, f"{side} {ref}: board pads differ from the netlist"


# ---- PCB -> firmware chains ------------------------------------------------------------------------

def check_switch_chain(pcb: pcbdata.Pcb, fw: fwdt.FwPins) -> None:
    """Socket/diode nets -> RP2040 GPIOs -> firmware (row, col) + col-offset -> transform -> the key."""
    side = pcb.side
    keys = {k["id"]: k for k in LAYOUT["sides"][side]["keys"]}
    matrix = pcb.matrix()
    assert set(matrix) == set(keys), "one socket and one diode per layout key"
    rows, cols, order = [g.pin for g in fw.rows], [g.pin for g in fw.cols], transform_order()
    for kid, (sock, diode) in sorted(matrix.items()):
        row_net, switch = diode.pads[DIODE_K], diode.pads[DIODE_A]
        (col_net,) = [n for n in sock.pads.values() if COL.match(n)]
        assert ROW.match(row_net), f"{kid}: diode cathode on {row_net}, not a row (col2row)"
        assert set(sock.pads.values()) == {col_net, switch}, f"{kid}: socket is not in series with its diode"
        rc = (rows.index(pcb.gpio(row_net)), cols.index(pcb.gpio(col_net)) + fw.col_offset)
        assert rc == tuple(keys[kid]["rc"]), f"{pcb.source} {kid}: firmware scans it as RC{rc}"
        assert order[fw.transform.index(rc)] == (side, kid), f"{kid}: RC{rc} is another key's keymap slot"


def check_trrs_crossover(pcbs: dict[str, pcbdata.Pcb], fw: dict[str, fwdt.FwPins]) -> None:
    """Straight TRRS cable: each contact joins a TX on one half to the RX on the other (§6.2)."""
    gpio = {}
    for side, pcb in pcbs.items():
        jack = pcb.parts["J2"].pads
        assert (jack["R2"], jack["S"]) == ("VLINK", "GND"), f"{side}: Ring2 = VLINK, Sleeve = GND"
        for contact in ("T", "R1"):
            (uart_net,) = pcb.through(jack[contact], JACK_RES)
            gpio[side, contact] = pcb.gpio(uart_net)
    for contact in ("T", "R1"):
        role = {g: r for r, g in fw["left"].uart.items()}[gpio["left", contact]]
        other = {"TX": "RX", "RX": "TX"}[role]
        assert gpio["right", contact] == fw["right"].uart[other], \
            f"{contact}: left {role} meets right GP{gpio['right', contact]}, not its {other}"


@pytest.mark.parametrize("kind, side", pcb_sources())
def test_every_switch_reaches_its_keymap_slot(kind, side):
    check_switch_chain(load_pcb(kind, side), source_fw(CORE, side))


@pytest.mark.parametrize("kind", pcb_kinds())
def test_trrs_link_crosses_tx_and_rx(kind):
    check_trrs_crossover({s: load_pcb(kind, s) for s in SIDES}, {s: source_fw(CORE, s) for s in SIDES})


@pytest.mark.parametrize("kind, side", pcb_sources())
def test_display_header_matches_firmware_spi(kind, side):
    pcb, fw = load_pcb(kind, side), source_fw(CORE, side)
    header = pcb.parts["J3"].pads
    want = {"MOSI": fw.spi["mosi"].pin, "SCK": fw.spi["clk"].pin, "CS": fw.spi["cs"].pin}
    for n, name in enumerate(LAYOUT["display_part"]["header_pin_order"], start=1):
        net = header[str(n)]
        if name in want:
            assert pcb.gpio(net) == want[name], f"J3 pin {n} ({name}) on {net}"
        else:
            assert net == {"VCC": "3V3", "GND": "GND"}[name], f"J3 pin {n} ({name}) on {net}"


# ---- the checks catch the mistakes they exist for ---------------------------------------------------

@pytest.mark.parametrize("mistake", [
    pytest.param(lambda fw: replace(fw, cols=fw.cols[::-1]), id="right col-gpios not reversed"),
    pytest.param(lambda fw: replace(fw, col_offset=0), id="right col-offset missing"),
    pytest.param(lambda fw: replace(fw, rows=fw.rows[1:] + fw.rows[:1]), id="rows rotated"),
])
def test_switch_chain_rejects(mistake):
    with pytest.raises(AssertionError):
        check_switch_chain(pcbdata.board("right"), mistake(source_fw(CORE, "right")))


def test_trrs_crossover_rejects_uncrossed_firmware():
    fw = {s: source_fw(CORE, s) for s in SIDES}
    fw["right"] = replace(fw["right"], uart={"TX": fw["right"].uart["RX"], "RX": fw["right"].uart["TX"]})
    with pytest.raises(AssertionError):
        check_trrs_crossover({s: pcbdata.board(s) for s in SIDES}, fw)
