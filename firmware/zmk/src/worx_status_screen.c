/*
 * SPDX-License-Identifier: MIT
 *
 * worxboard status screen (design.md §11.6) on the 1-bit 0.91" SSD1306 OLED of both halves. The
 * module is mounted upright, so the screen is laid out portrait, 32 wide x 128 high
 * (worx_display_rotation.c turns it onto the 128 x 32 panel). ZMK's built-in screen is laid out
 * for a landscape 128 x 32 panel and does not fit 32 px wide, so both halves use this one; what
 * they show depends on the split role, so the role-swap builds show the right thing too:
 *
 *     central            peripheral
 *
 *      worx                worx          <- logo
 *      USB                               <- host link: USB symbol; with an x until the host
 *                                           has set up HID
 *      Base                              <- active layer: its display-name, else its number
 *
 *      CAP                 CAP           <- host lock LEDs, from zmk_hid_indicators_changed (the
 *      num                 num              central forwards them to the peripheral over the
 *      scr                 scr              wired split: ZMK_SPLIT_PERIPHERAL_HID_INDICATORS).
 *                                           Lit: upper case in a frame; off: lower case.
 *                         wired          <- static: the split link is TRRS, there is no BLE
 *
 * Must not reference zmk_ble_* or battery symbols.
 */

#include <stdio.h>

#include <zephyr/kernel.h>
#include <lvgl.h>

#include <dt-bindings/zmk/hid_indicators.h>
#include <zmk/display.h>
#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/hid_indicators_changed.h>

#define WORX_CENTRAL (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))

#if WORX_CENTRAL
#include <zmk/events/layer_state_changed.h>
#include <zmk/keymap.h>
#if IS_ENABLED(CONFIG_ZMK_USB)
#include <zmk/events/usb_conn_state_changed.h>
#include <zmk/usb.h>
#endif
#endif

#define SCREEN_W 32   /* px: the portrait width */
#define LOGO_TEXT "worx"
#define LINK_TEXT "wired"
#define LOGO_Y 2      /* px from the top */
#define USB_Y 22      /* px from the top (central) */
#define LAYER_Y 42    /* px from the top (central) */
#define LOCK_Y0_CENTRAL 68
#define LOCK_Y0_PERIPHERAL 36
#define LOCK_PITCH 18 /* px between lock labels */
#define LOCK_FRAME 1  /* px: frame around a lit lock label */
#define LINK_Y (-2)   /* px from the bottom (peripheral) */
#define LAYER_TEXT 8  /* bytes: the label is clipped to SCREEN_W anyway */

struct lock_label {
    zmk_hid_indicators_t bit;
    const char *on;  /* shown when the host LED is lit */
    const char *off; /* shown when it is not */
    lv_obj_t *obj;
};

static struct lock_label locks[] = {
    {HID_INDICATOR_CAPS_LOCK, "CAP", "cap", NULL},
    {HID_INDICATOR_NUM_LOCK, "NUM", "num", NULL},
    {HID_INDICATOR_SCROLL_LOCK, "SCR", "scr", NULL},
};

static lv_style_t lock_style;     /* every lock label */
static lv_style_t lock_lit_style; /* LV_STATE_CHECKED: the host LED is lit */

/* The peripheral has no indicator getter, so remember the last state either half was sent. */
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

#if WORX_CENTRAL

static lv_obj_t *layer_obj;

struct layer_state {
    zmk_keymap_layer_index_t index;
    const char *name;
};

static void layer_update_cb(struct layer_state state) {
    if (layer_obj == NULL) {
        return;
    }
    if (state.name != NULL && state.name[0] != '\0') {
        lv_label_set_text(layer_obj, state.name);
    } else {
        char text[LAYER_TEXT];
        snprintf(text, sizeof(text), "L%u", (unsigned)state.index);
        lv_label_set_text(layer_obj, text);
    }
}

static struct layer_state layer_get_state(const zmk_event_t *eh) {
    zmk_keymap_layer_index_t index = zmk_keymap_highest_layer_active();
    return (struct layer_state){
        .index = index, .name = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(index))};
}

ZMK_DISPLAY_WIDGET_LISTENER(worx_layer, struct layer_state, layer_update_cb, layer_get_state)
ZMK_SUBSCRIPTION(worx_layer, zmk_layer_state_changed);

#if IS_ENABLED(CONFIG_ZMK_USB)

static lv_obj_t *usb_obj;

struct usb_state {
    enum zmk_usb_conn_state conn;
};

static void usb_update_cb(struct usb_state state) {
    if (usb_obj != NULL) {
        lv_label_set_text(usb_obj, state.conn == ZMK_USB_CONN_HID ? LV_SYMBOL_USB
                                                                  : LV_SYMBOL_USB LV_SYMBOL_CLOSE);
    }
}

static struct usb_state usb_get_state(const zmk_event_t *eh) {
    return (struct usb_state){.conn = zmk_usb_get_conn_state()};
}

ZMK_DISPLAY_WIDGET_LISTENER(worx_usb, struct usb_state, usb_update_cb, usb_get_state)
ZMK_SUBSCRIPTION(worx_usb, zmk_usb_conn_state_changed);

#endif /* CONFIG_ZMK_USB */
#endif /* WORX_CENTRAL */

static lv_obj_t *label(lv_obj_t *parent, const lv_font_t *font, const char *text, int32_t y,
                       lv_align_t align) {
    lv_obj_t *obj = lv_label_create(parent);
    lv_obj_set_style_text_font(obj, font, LV_PART_MAIN);
    lv_obj_set_style_text_align(obj, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
    lv_obj_set_width(obj, SCREEN_W);
    lv_label_set_long_mode(obj, LV_LABEL_LONG_CLIP);
    lv_label_set_text(obj, text);
    lv_obj_align(obj, align, 0, y);
    return obj;
}

static void init_lock_styles(lv_color_t ink) {
    lv_style_init(&lock_style);
    lv_style_set_text_font(&lock_style, &lv_font_montserrat_10);
    lv_style_set_text_align(&lock_style, LV_TEXT_ALIGN_CENTER);
    lv_style_set_width(&lock_style, SCREEN_W);
    lv_style_set_pad_ver(&lock_style, 1);
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
     * sets its own opaque paper and ink (light paper, dark ink, as ZMK's mono theme; the SSD1306
     * node's inversion-on shows that as lit text on black). Without an opaque paper the text has
     * the colour of the uncleared buffer and does not show. */
    const bool invert = IS_ENABLED(CONFIG_ZMK_DISPLAY_INVERT);
    const lv_color_t ink = invert ? lv_color_white() : lv_color_black();
    const lv_color_t paper = invert ? lv_color_black() : lv_color_white();

    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, paper, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_text_color(screen, ink, LV_PART_MAIN);
    lv_obj_set_style_pad_all(screen, 0, LV_PART_MAIN);

    label(screen, &lv_font_montserrat_12, LOGO_TEXT, LOGO_Y, LV_ALIGN_TOP_MID);

    int32_t lock_y0 = LOCK_Y0_PERIPHERAL;
#if WORX_CENTRAL
    lock_y0 = LOCK_Y0_CENTRAL;
#if IS_ENABLED(CONFIG_ZMK_USB)
    usb_obj = label(screen, &lv_font_montserrat_12, LV_SYMBOL_USB, USB_Y, LV_ALIGN_TOP_MID);
    worx_usb_init();
#endif
    layer_obj = label(screen, &lv_font_montserrat_10, "", LAYER_Y, LV_ALIGN_TOP_MID);
    worx_layer_init();
#else
    label(screen, &lv_font_montserrat_10, LINK_TEXT, LINK_Y, LV_ALIGN_BOTTOM_MID);
#endif

    init_lock_styles(ink);
    for (size_t i = 0; i < ARRAY_SIZE(locks); i++) {
        locks[i].obj = lv_label_create(screen);
        lv_obj_add_style(locks[i].obj, &lock_style, LV_PART_MAIN);
        lv_obj_add_style(locks[i].obj, &lock_lit_style, LV_PART_MAIN | LV_STATE_CHECKED);
        lv_label_set_text(locks[i].obj, locks[i].off);
        lv_obj_align(locks[i].obj, LV_ALIGN_TOP_MID, 0, lock_y0 + (int32_t)i * LOCK_PITCH);
    }

    worx_lock_row_init();
    return screen;
}
