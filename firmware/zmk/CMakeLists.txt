# SPDX-License-Identifier: MIT
# worxboard ZMK module sources (zephyr/module.yml -> cmake: firmware/zmk)

if(CONFIG_WORXBOARD_STATUS_SCREEN)
  target_sources(app PRIVATE src/worx_status_screen.c)
endif()
