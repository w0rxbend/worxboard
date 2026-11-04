/*
 * SPDX-License-Identifier: MIT
 *
 * Portrait output for the nice!view-class display on both worxboard halves.
 *
 * The module sits LCD up in J3 with its header at the back of the board (low PCB y) and its flex
 * toward the user, the same way on both halves (layout/display.py, docs/verification.md G1). The
 * panel is 160 x 68 with its lines running along the module, and pixel x = 0 is at the header end:
 * ZMK's nice_view widgets, drawn for the nice!view's own upright view (header at the bottom),
 * put their top canvas at x 92..159 and turn it a quarter clockwise (LV_DISPLAY_ROTATION_270),
 * and nicekeyboards.com shows that screen upright with the header at the bottom. Seen from the
 * front of the keyboard the module is turned 180° from that view, so LVGL lays out a 68 x 160
 * portrait screen and this flush turns it a quarter the other way (LV_DISPLAY_ROTATION_90):
 * portrait (u, v) -> panel (v, 67 - u). CONFIG_WORXBOARD_DISPLAY_ROTATION_270 selects the stock
 * nice!view orientation instead.
 *
 * Zephyr's LVGL glue (modules/lvgl, pinned in firmware/zmk/config/west.yml) does not rotate, so
 * after lvgl_init() this replaces its flush and rounder on the default display: LVGL renders
 * portrait areas, they are turned into a panel-ordered shadow, and the panel lines they touch are
 * handed, full width, to Zephyr's own lvgl_flush_cb_mono() (the ls0xx driver writes whole lines only).
 */

#include <string.h>

#include <zephyr/devicetree.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/util.h>

#include <lvgl.h>
#include <lvgl_display.h>

#include "worx_rotate.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define PANEL_NODE DT_CHOSEN(zephyr_display)
#define PANEL_W DT_PROP(PANEL_NODE, width)  /* pixels per line */
#define PANEL_H DT_PROP(PANEL_NODE, height) /* lines */
#define ROW_BYTES (PANEL_W / 8)
#define PALETTE 8 /* LVGL puts the I1 palette (2 x ARGB8888) in front of the pixels */

#if IS_ENABLED(CONFIG_WORXBOARD_DISPLAY_ROTATION_270)
#define ROT WORX_ROT_270
#define LV_ROT LV_DISPLAY_ROTATION_270
#else
#define ROT WORX_ROT_90
#define LV_ROT LV_DISPLAY_ROTATION_90
#endif

/* After Zephyr's lvgl_init(), before ZMK's main() builds the status screen */
#define WORX_ROTATION_INIT_PRIORITY 91

BUILD_ASSERT(IS_ENABLED(CONFIG_LV_Z_AUTO_INIT), "LVGL must be set up by SYS_INIT");
BUILD_ASSERT(WORX_ROTATION_INIT_PRIORITY > CONFIG_LV_Z_INIT_PRIORITY, "must run after lvgl_init");
BUILD_ASSERT(PANEL_W % 8 == 0, "panel lines must be whole bytes");
BUILD_ASSERT(PANEL_W == 160 && PANEL_H == 68, "worx_rotate.h is written for the LS011B7DH03");

/* What LVGL drew, in panel order, LVGL's I1 bit order (MSB = lowest x) */
static uint8_t shadow[PANEL_H * ROW_BYTES];

/*
 * Lines handed to lvgl_flush_cb_mono(). It converts them in place and copies its whole conversion
 * buffer back (lvgl_transform_buffer()), so this is as large as Zephyr's largest draw buffer:
 * 8 + ROUND_UP(W, 8) * ROUND_UP(H, 8) / 8 at CONFIG_LV_Z_VDB_SIZE 100.
 */
static uint8_t stage[PALETTE + ROUND_UP(PANEL_W, 8) * ROUND_UP(PANEL_H, 8) / 8] __aligned(4);

static void flush_rotated(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map) {
    const int32_t w = lv_area_get_width(area);
    const int32_t h = lv_area_get_height(area);
    const uint32_t stride = lv_draw_buf_width_to_stride(w, LV_COLOR_FORMAT_I1);
    int32_t y_first, y_last;

    worx_rot_blit_i1(ROT, PANEL_W, PANEL_H, area->x1, area->y1, w, h, px_map + PALETTE, stride,
                     shadow, &y_first, &y_last);
    if (y_last < y_first) {
        lv_display_flush_ready(disp);
        return;
    }

    memcpy(stage, px_map, PALETTE);
    memcpy(stage + PALETTE, &shadow[y_first * ROW_BYTES], (y_last - y_first + 1) * ROW_BYTES);

    const lv_area_t lines = {.x1 = 0, .y1 = y_first, .x2 = PANEL_W - 1, .y2 = y_last};
    lvgl_flush_cb_mono(disp, &lines, stage); /* converts, writes, lv_display_flush_ready() */
}

static int worx_display_rotation_init(void) {
    lv_display_t *disp = lv_is_initialized() ? lv_display_get_default() : NULL;

    if (disp == NULL || lv_display_get_color_format(disp) != LV_COLOR_FORMAT_I1) {
        LOG_WRN("worxboard: no 1-bit LVGL display, screen not rotated");
        return 0;
    }

    /* ls0xx_init() clears the panel to white, which is I1 1 */
    memset(shadow, 0xFF, sizeof(shadow));

    /* Zephyr's rounder widens areas to x 0..159, the panel line; in portrait that is v, not u.
     * LVGL already rounds I1 areas to whole bytes, and flush_rotated() takes any area. */
    lv_display_remove_event_cb_with_user_data(disp, lvgl_rounder_cb_mono, disp);
    lv_display_set_flush_cb(disp, flush_rotated);
    lv_display_set_rotation(disp, LV_ROT);
    return 0;
}

SYS_INIT(worx_display_rotation_init, APPLICATION, WORX_ROTATION_INIT_PRIORITY);
