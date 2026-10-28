# SPDX-License-Identifier: MIT
# EXPERIMENTAL: RP2350A firmware target only (design.md §13); no rev A hardware.
board_runner_args(uf2 "--board-id=RP2350")
include(${ZEPHYR_BASE}/boards/common/uf2.board.cmake)
