# SPDX-License-Identifier: MIT
# worxboard ZMK module sources (zephyr/module.yml -> cmake: firmware/zmk)

if(CONFIG_WORXBOARD_STATUS_SCREEN)
  target_sources(app PRIVATE src/worx_status_screen.c)
endif()

if(CONFIG_WORXBOARD_DISPLAY_ROTATION_90 OR CONFIG_WORXBOARD_DISPLAY_ROTATION_270)
  target_sources(app PRIVATE src/worx_display_rotation.c)
endif()
