/*
 * SPDX-License-Identifier: MIT
 *
 * worxboard right-half status screen (design.md §11.6) on the 1-bit LS011B7DH03. The module is
 * mounted upright, so the screen is laid out portrait, 68 wide x 160 high (worx_display_rotation.c
 * turns it onto the 160 x 68 panel):
 *
 *     worx         <- logo, two lines
 *     board
 *
 *    [CAPS]        <- host lock LEDs, from zmk_hid_indicators_changed (forwarded by the central
 *     num             over the wired split: ZMK_SPLIT_PERIPHERAL_HID_INDICATORS). Lit: upper
 *     scrl            case in a frame; off: lower case.
 *
 *     wired        <- static: the split link is TRRS, there is no BLE or battery
 *
 * Must not reference zmk_ble_* or battery symbols.
 */

#include <zephyr/kernel.h>
#include <lvgl.h>

#include <dt-bindings/zmk/hid_indicators.h>
#include <zmk/display.h>
#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/hid_indicators_changed.h>

#define LOGO_TEXT "worx\nboard"
#define LINK_TEXT "wired"
#define LOGO_Y 4      /* px from the top */
#define LOCK_Y0 52    /* px from the top to the first lock label */
#define LOCK_PITCH 28 /* px between lock labels */
#define LOCK_W 60     /* px: fixed, so text changes never move the column */
#define LOCK_FRAME 2  /* px: frame around a lit lock label */
#define LINK_Y (-4)   /* px from the bottom */

struct lock_label {
    zmk_hid_indicators_t bit;
    const char *on;  /* shown when the host LED is lit */
    const char *off; /* shown when it is not */
    lv_obj_t *obj;
};

static struct lock_label locks[] = {
    {HID_INDICATOR_CAPS_LOCK, "CAPS", "caps", NULL},
    {HID_INDICATOR_NUM_LOCK, "NUM", "num", NULL},
    {HID_INDICATOR_SCROLL_LOCK, "SCRL", "scrl", NULL},
};

static lv_style_t lock_style;     /* every lock label */
static lv_style_t lock_lit_style; /* LV_STATE_CHECKED: the host LED is lit */

/* The peripheral has no indicator getter, so remember the last forwarded state. */
static zmk_hid_indicators_t last_indicators;

struct lock_state {
    zmk_hid_indicators_t indicators;
};

static void lock_row_update_cb(struct lock_state state) {
    for (size_t i = 0; i < ARRAY_SIZE(locks); i++) {
        if (locks[i].obj != NULL) {
            bool lit = (state.indicators & locks[i].bit) != 0;
            lv_label_set_text(locks[i].obj, lit ? locks[i].on : locks[i].off);
            lv_obj_set_state(locks[i].obj, LV_STATE_CHECKED, lit);
        }
    }
}

static struct lock_state lock_row_get_state(const zmk_event_t *eh) {
    const struct zmk_hid_indicators_changed *ev = eh ? as_zmk_hid_indicators_changed(eh) : NULL;
    if (ev != NULL) {
        last_indicators = ev->indicators;
    }
    return (struct lock_state){.indicators = last_indicators};
}

ZMK_DISPLAY_WIDGET_LISTENER(worx_lock_row, struct lock_state, lock_row_update_cb,
                            lock_row_get_state)
ZMK_SUBSCRIPTION(worx_lock_row, zmk_hid_indicators_changed);

static lv_obj_t *label(lv_obj_t *parent, const lv_font_t *font, const char *text) {
    lv_obj_t *obj = lv_label_create(parent);
    lv_obj_set_style_text_font(obj, font, LV_PART_MAIN);
    lv_label_set_text(obj, text);
    return obj;
}

static void init_lock_styles(lv_color_t ink) {
    lv_style_init(&lock_style);
    lv_style_set_text_font(&lock_style, &lv_font_montserrat_16);
    lv_style_set_text_align(&lock_style, LV_TEXT_ALIGN_CENTER);
    lv_style_set_width(&lock_style, LOCK_W);
    lv_style_set_pad_ver(&lock_style, 2);
    lv_style_set_border_width(&lock_style, LOCK_FRAME); /* always there, so lit text never moves */
    lv_style_set_border_color(&lock_style, ink);
    lv_style_set_border_opa(&lock_style, LV_OPA_TRANSP);

    /* A frame, not inverse video: at 1 bit the anti-aliased glyph edges fall to the paper side
     * of the threshold, so ink-on-paper text would come out thin and broken. */
    lv_style_init(&lock_lit_style);
    lv_style_set_border_opa(&lock_lit_style, LV_OPA_COVER);
}

lv_obj_t *zmk_display_status_screen(void) {
    /* ZMK gives a custom screen no theme, and LVGL never clears an I1 draw buffer, so the screen
     * sets its own paper and ink, as the mono theme of the left's built-in screen does (light
     * paper, dark ink; swapped by ZMK_DISPLAY_INVERT). Without an opaque paper the text has the
     * colour of the uncleared buffer and does not show. */
    const bool invert = IS_ENABLED(CONFIG_ZMK_DISPLAY_INVERT);
    const lv_color_t ink = invert ? lv_color_white() : lv_color_black();
    const lv_color_t paper = invert ? lv_color_black() : lv_color_white();

    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, paper, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_text_color(screen, ink, LV_PART_MAIN);

    lv_obj_t *logo = label(screen, &lv_font_montserrat_16, LOGO_TEXT);
    lv_obj_set_style_text_align(logo, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
    lv_obj_align(logo, LV_ALIGN_TOP_MID, 0, LOGO_Y);

    init_lock_styles(ink);
    for (size_t i = 0; i < ARRAY_SIZE(locks); i++) {
        locks[i].obj = lv_label_create(screen);
        lv_obj_add_style(locks[i].obj, &lock_style, LV_PART_MAIN);
        lv_obj_add_style(locks[i].obj, &lock_lit_style, LV_PART_MAIN | LV_STATE_CHECKED);
        lv_label_set_text(locks[i].obj, locks[i].off);
        lv_obj_align(locks[i].obj, LV_ALIGN_TOP_MID, 0, LOCK_Y0 + i * LOCK_PITCH);
    }

    lv_obj_t *link = label(screen, &lv_font_montserrat_12, LINK_TEXT);
    lv_obj_align(link, LV_ALIGN_BOTTOM_MID, 0, LINK_Y);

    worx_lock_row_init();
    return screen;
}
