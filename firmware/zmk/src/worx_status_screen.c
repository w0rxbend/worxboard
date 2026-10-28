/*
 * SPDX-License-Identifier: MIT
 *
 * worxboard right-half status screen (design.md §11.6), 160 x 68 1-bit LS011B7DH03:
 *   worxboard            <- logo label
 *   CAPS  NUM  SCRL      <- host lock LEDs, from zmk_hid_indicators_changed (forwarded by the
 *                           central over the wired split: ZMK_SPLIT_PERIPHERAL_HID_INDICATORS)
 *   wired                <- static: the split link is TRRS, there is no BLE or battery
 * Must not reference zmk_ble_* or battery symbols.
 */

#include <zephyr/kernel.h>
#include <lvgl.h>

#include <dt-bindings/zmk/hid_indicators.h>
#include <zmk/display.h>
#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/hid_indicators_changed.h>

#define LOGO_TEXT "worxboard"
#define LINK_TEXT "wired"
#define LOCK_X0 4     /* px, first lock label */
#define LOCK_PITCH 52 /* px between lock labels: fixed, so text changes never shift the row */

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

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);

    lv_obj_t *logo = label(screen, &lv_font_montserrat_16, LOGO_TEXT);
    lv_obj_align(logo, LV_ALIGN_TOP_MID, 0, 2);

    for (size_t i = 0; i < ARRAY_SIZE(locks); i++) {
        locks[i].obj = label(screen, &lv_font_montserrat_12, locks[i].off);
        lv_obj_align(locks[i].obj, LV_ALIGN_LEFT_MID, LOCK_X0 + i * LOCK_PITCH, 0);
    }

    lv_obj_t *link = label(screen, &lv_font_montserrat_12, LINK_TEXT);
    lv_obj_align(link, LV_ALIGN_BOTTOM_RIGHT, -4, -2);

    worx_lock_row_init();
    return screen;
}
