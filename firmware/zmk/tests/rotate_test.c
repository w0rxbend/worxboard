/*
 * SPDX-License-Identifier: MIT
 *
 * Host test of src/worx_rotate.h (just fw-rotate-check; the firmware workflow's checks job).
 *
 *   cc -std=c11 -Wall -Wextra -Werror -I firmware/zmk/src firmware/zmk/tests/rotate_test.c
 *
 * Panel facts it checks against (docs/verification.md G1; src/worx_display_rotation.c), for the
 * 0.91" 128 x 32 SSD1306 OLED with the worxboard.dtsi settings (assumed, not yet seen on hardware):
 *   - seen glass up with the header on the left, panel x grows to the right from the header end
 *     and y grows down;
 *   - on worxboard the header points away from the user, so the user sees that view turned a
 *     quarter clockwise: x grows down the screen and y grows to the left;
 *   - the driver writes whole 8-row pages, so flushed bands are widened to page boundaries.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "worx_rotate.h"

#define PW 128
#define PH 32
#define PAGE 8
#define IMG_W 40 /* portrait image row, px: u 32..39 are off the panel */
#define IMG_B (IMG_W / 8)
#define ROW (PW / 8)

static int failures;

#define CHECK(cond, ...)                                                                           \
    do {                                                                                           \
        if (!(cond)) {                                                                             \
            failures++;                                                                            \
            printf("FAIL %s:%d: ", __FILE__, __LINE__);                                            \
            printf(__VA_ARGS__);                                                                   \
            printf("\n");                                                                          \
        }                                                                                          \
    } while (0)

/* LVGL 9.3 lv_display_rotate_area() for a one-pixel area at (u, v) (src/display/lv_display.c,
 * hor_res = PW, ver_res = PH): the mapping LVGL itself documents for each rotation. */
static void lvgl_rotate_px(int rot, int u, int v, int *x, int *y) {
    if (rot == WORX_ROT_90) {
        *y = PH - u - 1;
        *x = v;
    } else {
        *x = PW - v - 1;
        *y = u;
    }
}

static int bit(const uint8_t *buf, int stride, int x, int y) {
    return (buf[y * stride + x / 8] >> (7 - x % 8)) & 1;
}

static void corners(void) {
    int32_t x, y;

    /* worxboard (ROT_90): what the user sees as the top of the screen is the header end */
    CHECK(worx_rot_px(WORX_ROT_90, PW, PH, 0, 0, &x, &y) && x == 0 && y == PH - 1,
          "top-left -> header end, user's left (y 31): got %d,%d", (int)x, (int)y);
    CHECK(worx_rot_px(WORX_ROT_90, PW, PH, PH - 1, 0, &x, &y) && x == 0 && y == 0,
          "top-right -> header end, y 0: got %d,%d", (int)x, (int)y);
    CHECK(worx_rot_px(WORX_ROT_90, PW, PH, 0, PW - 1, &x, &y) && x == PW - 1 && y == PH - 1,
          "bottom-left -> far end: got %d,%d", (int)x, (int)y);

    /* ROT_270, the half-turn fallback: the header end is at the bottom of the screen */
    CHECK(worx_rot_px(WORX_ROT_270, PW, PH, 0, PW - 1, &x, &y) && x == 0 && y == 0,
          "270 bottom-left -> header end, y 0: got %d,%d", (int)x, (int)y);
    CHECK(worx_rot_px(WORX_ROT_270, PW, PH, 0, 0, &x, &y) && x == PW - 1 && y == 0,
          "270 top-left -> far end: got %d,%d", (int)x, (int)y);

    /* the two settings are a half turn apart */
    for (int u = 0; u < PH; u++) {
        for (int v = 0; v < PW; v++) {
            int32_t x9, y9, x27, y27;
            worx_rot_px(WORX_ROT_90, PW, PH, u, v, &x9, &y9);
            worx_rot_px(WORX_ROT_270, PW, PH, u, v, &x27, &y27);
            CHECK(x27 == PW - 1 - x9 && y27 == PH - 1 - y9, "not a half turn at %d,%d", u, v);
        }
    }

    /* u 32..39 (an area rounded past the screen) and v 128 are off the panel */
    for (int u = PH; u < PH + 8; u++) {
        CHECK(!worx_rot_px(WORX_ROT_90, PW, PH, u, 0, &x, &y), "u %d must be off the panel", u);
    }
    CHECK(!worx_rot_px(WORX_ROT_90, PW, PH, 0, PW, &x, &y), "v 128 must be off the panel");
}

static void matches_lvgl_and_is_a_bijection(int rot) {
    static int hits[PH][PW];
    memset(hits, 0, sizeof(hits));
    for (int u = 0; u < PH; u++) {
        for (int v = 0; v < PW; v++) {
            int32_t x, y;
            int lx, ly;
            CHECK(worx_rot_px(rot, PW, PH, u, v, &x, &y), "%d,%d off the panel", u, v);
            lvgl_rotate_px(rot, u, v, &lx, &ly);
            CHECK(x == lx && y == ly, "rot %d at %d,%d: %d,%d, LVGL %d,%d", rot, u, v, (int)x,
                  (int)y, lx, ly);
            hits[y][x]++;
        }
    }
    for (int y = 0; y < PH; y++) {
        for (int x = 0; x < PW; x++) {
            CHECK(hits[y][x] == 1, "rot %d: panel %d,%d hit %d times", rot, x, y, hits[y][x]);
        }
    }
}

/* Render a random portrait image in LVGL-shaped chunks (byte-aligned x; the last chunk runs past
 * u 31, which the blit must drop) and compare the shadow with the pixel map. */
static void blit(int rot, unsigned seed) {
    static uint8_t img[PW][IMG_B];  /* portrait image, IMG_W px wide rows (u 32..39 = garbage) */
    static uint8_t shadow[PH * ROW];
    srand(seed);
    for (size_t i = 0; i < sizeof(img); i++) {
        ((uint8_t *)img)[i] = (uint8_t)rand();
    }
    memset(shadow, 0xA5, sizeof(shadow));

    const int xs[][2] = {{0, 8}, {8, 8}, {16, 24}}; /* x1, w: 0..7, 8..15, 16..39 */
    const int ys[][2] = {{0, 100}, {100, 28}};       /* y1, h */
    int lines_min = PH, lines_max = -1;
    for (size_t a = 0; a < 3; a++) {
        for (size_t b = 0; b < 2; b++) {
            const int x1 = xs[a][0], w = xs[a][1], y1 = ys[b][0], h = ys[b][1];
            const uint32_t stride = (uint32_t)(w + 7) / 8;
            static uint8_t chunk[PW * IMG_B];
            memset(chunk, 0, sizeof(chunk));
            for (int j = 0; j < h; j++) {
                for (int i = 0; i < w; i++) {
                    if (bit(&img[0][0], IMG_B, x1 + i, y1 + j)) {
                        chunk[j * stride + i / 8] |= (uint8_t)(0x80 >> (i % 8));
                    }
                }
            }
            int32_t yf, yl;
            worx_rot_blit_i1(rot, PW, PH, x1, y1, w, h, chunk, stride, shadow, &yf, &yl);
            /* rows touched = the panel rows of the on-panel columns x1 .. min(x1 + w, 32) - 1 */
            const int last = (x1 + w < PH ? x1 + w : PH) - 1;
            int32_t ya, yb, dummy;
            worx_rot_px(rot, PW, PH, x1, y1, &dummy, &ya);
            worx_rot_px(rot, PW, PH, last, y1, &dummy, &yb);
            CHECK(yf == (ya < yb ? ya : yb) && yl == (ya < yb ? yb : ya),
                  "rot %d chunk %d,%d: lines %d..%d, want %d..%d", rot, x1, y1, (int)yf, (int)yl,
                  (int)(ya < yb ? ya : yb), (int)(ya < yb ? yb : ya));
            lines_min = yf < lines_min ? yf : lines_min;
            lines_max = yl > lines_max ? yl : lines_max;
        }
    }
    CHECK(lines_min == 0 && lines_max == PH - 1, "rot %d: lines %d..%d", rot, lines_min, lines_max);

    for (int u = 0; u < PH; u++) {
        for (int v = 0; v < PW; v++) {
            int32_t x, y;
            worx_rot_px(rot, PW, PH, u, v, &x, &y);
            CHECK(bit(shadow, ROW, x, y) == bit(&img[0][0], IMG_B, u, v),
                  "rot %d: pixel %d,%d (panel %d,%d) differs", rot, u, v, (int)x, (int)y);
        }
    }
}

/* worx_rot_band() widens touched rows to whole SSD1306 pages and never leaves the panel */
static void bands(void) {
    for (int a = 0; a < PH; a++) {
        for (int b = a; b < PH; b++) {
            int32_t yf = a, yl = b;
            worx_rot_band(PH, PAGE, &yf, &yl);
            CHECK(yf % PAGE == 0 && (yl + 1) % PAGE == 0, "rows %d..%d -> %d..%d not whole pages", a,
                  b, (int)yf, (int)yl);
            CHECK(yf <= a && yl >= b && yf > a - PAGE && yl < b + PAGE && yl < PH,
                  "rows %d..%d -> %d..%d not the covering pages", a, b, (int)yf, (int)yl);
            int32_t lf = a, ll = b;
            worx_rot_band(PH, 1, &lf, &ll);
            CHECK(lf == a && ll == b, "page 1 must leave rows %d..%d as they are", a, b);
        }
    }
    int32_t ef = PH, el = -1;
    worx_rot_band(PH, PAGE, &ef, &el);
    CHECK(ef == PH && el == -1, "an empty range must stay empty");
}

int main(void) {
    bands();
    corners();
    matches_lvgl_and_is_a_bijection(WORX_ROT_90);
    matches_lvgl_and_is_a_bijection(WORX_ROT_270);
    for (unsigned seed = 1; seed <= 4; seed++) {
        blit(WORX_ROT_90, seed);
        blit(WORX_ROT_270, seed);
    }
    if (failures) {
        printf("rotate_test: %d failure(s)\n", failures);
        return 1;
    }
    printf("rotate_test: worx_rotate.h maps the portrait screen onto the panel as specified, in whole pages\n");
    return 0;
}
