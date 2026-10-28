# Firmware (WS1): ZMK module in firmware/zmk, matrix in build.yaml, west workspace in build/fw-ws.
#   just fw                         every build.yaml row -> build/fw/artifacts/<artifact>.uf2
#   just fw worxboard_left_central  only the named rows

fw_image   := "zmkfirmware/zmk-build-arm:stable"
fw_ws      := "build/fw-ws"
fw_scripts := "firmware/zmk/scripts"

_fw_docker := "docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e CCACHE_DIR=/work/build/fw-ccache -v $PWD:/work -w /work/" + fw_ws + " " + fw_image

# Build ZMK firmware for every build.yaml row (or the named artifacts)
fw *artifacts: fw-layouts-check fw-keymap-check fw-west
    {{_fw_docker}} sh -c 'west zephyr-export >/dev/null && python3 /work/{{fw_scripts}}/fw_build.py {{artifacts}}'
    @[ -n "{{artifacts}}" ] || just fw-check

# Create/refresh the west workspace; west update runs only when west.yml changed
fw-west:
    mkdir -p {{fw_ws}}/config build/fw-ccache
    cp firmware/zmk/config/west.yml {{fw_ws}}/config/west.yml
    {{_fw_docker}} sh -c 'set -e; [ -d .west ] || west init -l config; \
        if ! cmp -s config/west.yml .west/west.yml.updated; then \
            west update --fetch-opt=--filter=tree:0 && cp config/west.yml .west/west.yml.updated; fi'

# Regenerate worxboard-layouts.dtsi (physical layout + transform) from layout/build/layout.json
fw-layouts:
    python3 {{fw_scripts}}/gen_layouts.py

# Fail if the committed worxboard-layouts.dtsi is stale
fw-layouts-check:
    python3 {{fw_scripts}}/gen_layouts.py --check

# Keymap: 3 layers x 74 bindings, base layer equals the layout.json legends
fw-keymap-check:
    python3 {{fw_scripts}}/check_keymap.py

# Post-build checks on the right peripheral: no BLE/battery symbols, flash growth within budget
fw-check:
    python3 {{fw_scripts}}/fw_check.py build/fw

# Remove firmware build outputs (keeps the west workspace)
fw-clean:
    rm -rf build/fw
