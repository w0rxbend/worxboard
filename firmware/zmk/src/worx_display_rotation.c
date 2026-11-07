/*
 * SPDX-License-Identifier: MIT
 *
 * Portrait output for the 0.91" 128 x 32 SSD1306 OLED on both worxboard halves.
 *
 * The module sits glass up in J3 with its header at the back of the board (low PCB y), the same
 * way on both halves (layout/display.py, docs/verification.md G1). With the usual ZMK 128 x 32
 * settings in worxboard.dtsi (segment-remap, com-invdir), panel pixel (0, 0) is assumed to be
 * the top-left corner of the module seen glass up with its header on the left; seen from the
 * front of the keyboard (header at the top) that view is turned a quarter clockwise, so LVGL
 * lays out a 32 x 128 portrait screen and this flush turns it back (LV_DISPLAY_ROTATION_90):
 * portrait (u, v) -> panel (v, 31 - u). CONFIG_WORXBOARD_DISPLAY_ROTATION_270 turns the screen
 * by 180 degrees, should the module's pixel (0, 0) sit at the other end (not checked on hardware).
 *
 * Zephyr's LVGL glue (modules/lvgl, pinned in firmware/zmk/config/west.yml) does not rotate, so
 * after lvgl_init() this replaces its flush and rounder on the default display: LVGL renders
 * portrait areas, they are turned into a panel-ordered shadow, and the panel rows they touch,
 * widened to whole SSD1306 pages (the driver writes from a page boundary), are handed, full
 * width, to Zephyr's own lvgl_flush_cb_mono(), which converts them to the vertical-tiled format.
 */

#include <string.h>

#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/util.h>

#include <lvgl.h>
#include <lvgl_display.h>

#include "worx_rotate.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define PANEL_NODE DT_CHOSEN(zephyr_display)
#define PANEL_W DT_PROP(PANEL_NODE, width)  /* pixels per row */
#define PANEL_H DT_PROP(PANEL_NODE, height) /* rows */
#define ROW_BYTES (PANEL_W / 8)
#define PAGE 8    /* SSD1306 rows per page (SCREEN_INFO_MONO_VTILED) */
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
BUILD_ASSERT(CONFIG_LV_Z_VDB_SIZE == 100, "bands are staged from a full-screen draw buffer");
BUILD_ASSERT(PANEL_W % 8 == 0, "panel rows must be whole bytes");
BUILD_ASSERT(PANEL_H % PAGE == 0, "panel rows must be whole SSD1306 pages");
BUILD_ASSERT(PANEL_W == 128 && PANEL_H == 32, "worxboard rev A has a 128 x 32 SSD1306 OLED");

/* What LVGL drew, in panel order, LVGL's I1 bit order (MSB = lowest x) */
static uint8_t shadow[PANEL_H * ROW_BYTES];

/*
 * Rows handed to lvgl_flush_cb_mono(). It converts them in place and copies its whole conversion
 * buffer back (lvgl_transform_buffer()), so this is as large as Zephyr's draw buffer at
 * CONFIG_LV_Z_VDB_SIZE 100: 8 + ROUND_UP(W, 8) * ROUND_UP(H, 8) / 8.
 */
static uint8_t stage[PALETTE + ROUND_UP(PANEL_W, 8) * ROUND_UP(PANEL_H, 8) / 8] __aligned(4);

/* 8 on a page-addressed (vertical-tiled) panel such as the SSD1306, else 1 */
static int32_t band_rows = 1;

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
    worx_rot_band(PANEL_H, band_rows, &y_first, &y_last);

    memcpy(stage, px_map, PALETTE);
    memcpy(stage + PALETTE, &shadow[y_first * ROW_BYTES], (y_last - y_first + 1) * ROW_BYTES);

    const lv_area_t rows = {.x1 = 0, .y1 = y_first, .x2 = PANEL_W - 1, .y2 = y_last};
    lvgl_flush_cb_mono(disp, &rows, stage); /* converts, writes, lv_display_flush_ready() */
}

static int worx_display_rotation_init(void) {
    lv_display_t *disp = lv_is_initialized() ? lv_display_get_default() : NULL;

    if (disp == NULL || lv_display_get_color_format(disp) != LV_COLOR_FORMAT_I1) {
        LOG_WRN("worxboard: no 1-bit LVGL display, screen not rotated");
        return 0;
    }

    const struct lvgl_disp_data *data = lv_display_get_user_data(disp);
    band_rows = (data->cap.screen_info & SCREEN_INFO_MONO_VTILED) ? PAGE : 1;

    /* Overwritten by LVGL's first full-screen render before anything is shown */
    memset(shadow, 0x00, sizeof(shadow));

    /* Zephyr's rounder aligns areas in panel terms (x to bytes, y to pages); in portrait those
     * are the wrong axes. LVGL already rounds I1 areas to whole bytes, flush_rotated() takes any
     * area and widens the panel rows it touches to whole pages itself. */
    lv_display_remove_event_cb_with_user_data(disp, lvgl_rounder_cb_mono, disp);
    lv_display_set_flush_cb(disp, flush_rotated);
    lv_display_set_rotation(disp, LV_ROT);
    return 0;
}

SYS_INIT(worx_display_rotation_init, APPLICATION, WORX_ROTATION_INIT_PRIORITY);
