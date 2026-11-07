/*
 * SPDX-License-Identifier: MIT
 *
 * Portrait <-> panel pixel mapping for the worxboard display, a 0.91" 128 x 32 SSD1306 OLED,
 * shared by worx_display_rotation.c and the host test firmware/zmk/tests/rotate_test.c. Plain C,
 * no Zephyr. Written for any W x H panel; the comments use the SSD1306's 128 x 32.
 *
 * Panel frame (what the ssd1306 driver writes): x = 0..127 along a row (SSD1306 column),
 * y = 0..31 (row; 8 rows form one SSD1306 page).
 * Portrait frame (what LVGL lays out after rotation): u = 0..31 to the right, v = 0..127 down.
 *
 *   WORX_ROT_90:  x = v,       y = 31 - u   (LVGL LV_DISPLAY_ROTATION_90)
 *   WORX_ROT_270: x = 127 - v, y = u        (LVGL LV_DISPLAY_ROTATION_270, a half turn from 90)
 *
 * Both agree with LVGL 9.3 lv_display_rotate_area() for a one-pixel area.
 */
#ifndef WORX_ROTATE_H
#define WORX_ROTATE_H

#include <stdbool.h>
#include <stdint.h>

#define WORX_ROT_90 1  /* quarter turns, as lv_display_rotation_t */
#define WORX_ROT_270 3

/* Panel position of portrait pixel (u, v). False if (u, v) is off the panel: LVGL rounds I1
 * areas to whole bytes, so a portrait screen whose width is not a multiple of 8 gets areas past
 * its last column (none on the 32-wide SSD1306 screen; the check stays for other panels). */
static inline bool worx_rot_px(int rot, int32_t panel_w, int32_t panel_h, int32_t u, int32_t v,
                               int32_t *x, int32_t *y) {
    if (u < 0 || v < 0 || u >= panel_h || v >= panel_w) {
        return false;
    }
    if (rot == WORX_ROT_90) {
        *x = v;
        *y = panel_h - 1 - u;
    } else {
        *x = panel_w - 1 - v;
        *y = u;
    }
    return true;
}

/*
 * Copy an LVGL I1 area given in portrait coordinates into a panel-ordered I1 shadow.
 *   src:    the area's pixels without the palette; MSB = leftmost pixel; rows `stride` bytes apart
 *   shadow: panel_h rows of panel_w / 8 bytes, same bit order
 * *y_first / *y_last get the panel lines the area touched (*y_last < *y_first if none).
 */
static inline void worx_rot_blit_i1(int rot, int32_t panel_w, int32_t panel_h, int32_t x1,
                                    int32_t y1, int32_t w, int32_t h, const uint8_t *src,
                                    uint32_t stride, uint8_t *shadow, int32_t *y_first,
                                    int32_t *y_last) {
    const int32_t row_bytes = panel_w / 8;

    *y_first = panel_h;
    *y_last = -1;
    for (int32_t j = 0; j < h; j++) {
        const uint8_t *line = src + (uint32_t)j * stride;
        for (int32_t i = 0; i < w; i++) {
            int32_t x, y;
            if (!worx_rot_px(rot, panel_w, panel_h, x1 + i, y1 + j, &x, &y)) {
                continue;
            }
            uint8_t *dst = &shadow[y * row_bytes + x / 8];
            const uint8_t mask = (uint8_t)(0x80u >> (x % 8));
            if (line[i / 8] & (0x80u >> (i % 8))) {
                *dst |= mask;
            } else {
                *dst &= (uint8_t)~mask;
            }
            if (y < *y_first) {
                *y_first = y;
            }
            if (y > *y_last) {
                *y_last = y;
            }
        }
    }
}

/*
 * Widen the panel rows *y_first..*y_last to whole pages of `page` rows (8 on the SSD1306, whose
 * writes start and end on page boundaries; 1 for a line-addressed panel), clipped to the panel.
 * Leaves an empty range (*y_last < *y_first) as it is.
 */
static inline void worx_rot_band(int32_t panel_h, int32_t page, int32_t *y_first,
                                 int32_t *y_last) {
    if (*y_last < *y_first || page <= 1) {
        return;
    }
    *y_first -= *y_first % page;
    *y_last += page - 1 - *y_last % page;
    if (*y_last > panel_h - 1) {
        *y_last = panel_h - 1;
    }
}

#endif /* WORX_ROTATE_H */
