/*
 * SPDX-License-Identifier: MIT
 *
 * Host test of src/worx_rotate.h (just fw-rotate-check; the firmware workflow's checks job).
 *
 *   cc -std=c11 -Wall -Wextra -Werror -I firmware/zmk/src firmware/zmk/tests/rotate_test.c
 *
 * Panel facts it checks against (docs/verification.md G1; src/worx_display_rotation.c):
 *   - panel x = 0 is the header end of the module; in the nice!view front view (header at the
 *     bottom) x grows upward and y grows to the right;
 *   - on worxboard the header points away from the user, so the user sees that view turned 180°:
 *     x grows down the screen and y grows to the left.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "worx_rotate.h"

#define PW 160
#define PH 68
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
          "top-left -> header end, user's left (y 67): got %d,%d", (int)x, (int)y);
    CHECK(worx_rot_px(WORX_ROT_90, PW, PH, PH - 1, 0, &x, &y) && x == 0 && y == 0,
          "top-right -> header end, y 0: got %d,%d", (int)x, (int)y);
    CHECK(worx_rot_px(WORX_ROT_90, PW, PH, 0, PW - 1, &x, &y) && x == PW - 1 && y == PH - 1,
          "bottom-left -> flex end: got %d,%d", (int)x, (int)y);

    /* stock nice!view (ROT_270): header toward the viewer, at the bottom of the screen */
    CHECK(worx_rot_px(WORX_ROT_270, PW, PH, 0, PW - 1, &x, &y) && x == 0 && y == 0,
          "270 bottom-left -> header end, y 0: got %d,%d", (int)x, (int)y);
    CHECK(worx_rot_px(WORX_ROT_270, PW, PH, 0, 0, &x, &y) && x == PW - 1 && y == 0,
          "270 top-left -> flex end: got %d,%d", (int)x, (int)y);

    /* the two settings are a half turn apart */
    for (int u = 0; u < PH; u++) {
        for (int v = 0; v < PW; v++) {
            int32_t x9, y9, x27, y27;
            worx_rot_px(WORX_ROT_90, PW, PH, u, v, &x9, &y9);
            worx_rot_px(WORX_ROT_270, PW, PH, u, v, &x27, &y27);
            CHECK(x27 == PW - 1 - x9 && y27 == PH - 1 - y9, "not a half turn at %d,%d", u, v);
        }
    }

    /* LVGL rounds I1 areas to whole bytes: u 68..71 exists in an area but not on the panel */
    for (int u = PH; u < PH + 8; u++) {
        CHECK(!worx_rot_px(WORX_ROT_90, PW, PH, u, 0, &x, &y), "u %d must be off the panel", u);
    }
    CHECK(!worx_rot_px(WORX_ROT_90, PW, PH, 0, PW, &x, &y), "v 160 must be off the panel");
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

/* Render a random portrait image in LVGL-shaped chunks (byte-aligned x, widths up to 72, so the
 * last chunk runs past u 67) and compare the shadow with the pixel map. */
static void blit(int rot, unsigned seed) {
    static uint8_t img[PW][9];      /* portrait image, 72 px wide rows (u 68..71 = garbage) */
    static uint8_t shadow[PH * ROW];
    srand(seed);
    for (size_t i = 0; i < sizeof(img); i++) {
        ((uint8_t *)img)[i] = (uint8_t)rand();
    }
    memset(shadow, 0xA5, sizeof(shadow));

    const int xs[][2] = {{0, 24}, {24, 16}, {40, 32}}; /* x1, w: 0..23, 24..39, 40..71 */
    const int ys[][2] = {{0, 100}, {100, 60}};          /* y1, h */
    int lines_min = PH, lines_max = -1;
    for (size_t a = 0; a < 3; a++) {
        for (size_t b = 0; b < 2; b++) {
            const int x1 = xs[a][0], w = xs[a][1], y1 = ys[b][0], h = ys[b][1];
            const uint32_t stride = (uint32_t)(w + 7) / 8;
            static uint8_t chunk[PW * 9];
            memset(chunk, 0, sizeof(chunk));
            for (int j = 0; j < h; j++) {
                for (int i = 0; i < w; i++) {
                    if (bit(&img[0][0], 9, x1 + i, y1 + j)) {
                        chunk[j * stride + i / 8] |= (uint8_t)(0x80 >> (i % 8));
                    }
                }
            }
            int32_t yf, yl;
            worx_rot_blit_i1(rot, PW, PH, x1, y1, w, h, chunk, stride, shadow, &yf, &yl);
            /* lines touched = the panel lines of the on-panel columns x1 .. min(x1 + w, 68) - 1 */
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
            CHECK(bit(shadow, ROW, x, y) == bit(&img[0][0], 9, u, v),
                  "rot %d: pixel %d,%d (panel %d,%d) differs", rot, u, v, (int)x, (int)y);
        }
    }
}

int main(void) {
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
    printf("rotate_test: worx_rotate.h maps the portrait screen onto the panel as specified\n");
    return 0;
}
