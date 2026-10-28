# SPDX-License-Identifier: GPL-3.0-or-later
"""The frozen GPIO contract (spec §3)."""
from layout import pins as P

SPEC_NETS = {  # GPIO -> (net, QFN pin)
    0: ("UART_TX", 2), 1: ("UART_RX", 3), 2: ("DISP_SCK", 4), 3: ("DISP_MOSI", 5),
    4: ("DISP_DC", 6), 5: ("DISP_CS", 7), 6: ("DISP_RST", 8), 7: ("DISP_BL", 9),
    **{8 + i: (f"ROW{i}", 11 + i) for i in range(6)},
    **{14 + i: (f"COL{i}", q) for i, q in enumerate((17, 18, 27, 28, 29, 30, 31))},
    21: ("TRRS_DET", 32), 26: ("VBUS_SENSE", 38),
}


def test_gpio_nets_match_spec():
    for g, (net, qfn) in SPEC_NETS.items():
        assert P.gpio(net) == g
        assert P.BY_NET[net].qfn == qfn


def test_matrix_and_uart_gpios():
    assert P.ROW_GPIOS == (8, 9, 10, 11, 12, 13)
    assert P.COL_GPIOS == (14, 15, 16, 17, 18, 19, 20)
    assert P.RIGHT_COL_GPIOS == (20, 19, 18, 17, 16, 15, 14)
    assert (P.UART_TX, P.UART_RX, P.UART_BAUD) == (0, 1, 115200)
    assert (P.DISP_SCK, P.DISP_MOSI, P.DISP_CS) == (2, 3, 5)


def test_pins_unique():
    assert len({p.name for p in P.PINS}) == len(P.PINS)
    assert len({p.qfn for p in P.PINS}) == len(P.PINS)


def test_trrs_crossover():
    left, right = P.TRRS["left"], P.TRRS["right"]
    assert (left["TRRS_A"], left["TRRS_B"]) == ("UART_TX", "UART_RX")
    assert (right["TRRS_A"], right["TRRS_B"]) == ("UART_RX", "UART_TX")
    for side in (left, right):
        assert (side["T"], side["R1"], side["R2"], side["S"]) == ("TRRS_A", "TRRS_B", "VLINK", "GND")
