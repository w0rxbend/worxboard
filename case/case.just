# Case and plates (WS3): build123d CNC case (port of the reference ergodox_case.py), spec §10

case_py      := "env PYTHONHASHSEED=0 uv run --group case python"   # fixed hash seed: reproducible DXF object order
case_tools   := "uv run --group case --with trimesh==5.2.0 --with networkx==3.5 --with matplotlib==3.10.7 --with pillow==12.0.0 python"
case_exports := "case/exports"
case_renders := "case/renders"

# STEP / STL of both halves, legs, fit-check DXFs and plates/*.dxf; fails on any case check
model:
    {{case_py}} case/worxboard_case.py {{case_exports}} plates

# Interference with the PCB STEP (build/<side>/worxboard-<side>.step), or the layout zones until it exists
fitcheck:
    {{case_py}} case/check_fit.py {{case_exports}}

# Regenerate the PNG previews in case/renders (needs model)
renders:
    @mkdir -p {{case_renders}}
    {{case_tools}} case/tools/zrender.py {{case_renders}}/pair_top_iso.png 1200 -50 0 \
        {{case_exports}}/worxboard_left_top.stl:-115,0,0 {{case_exports}}/worxboard_right_top.stl:115,0,0
    {{case_tools}} case/tools/zrender.py {{case_renders}}/right_top_underside.png 1000 140 15 {{case_exports}}/worxboard_right_top.stl
    {{case_tools}} case/tools/zrender.py {{case_renders}}/right_bottom_tray.png 1000 -45 15 {{case_exports}}/worxboard_right_bottom.stl
    {{case_tools}} case/tools/zrender.py {{case_renders}}/right_back_usb.png 1000 -75 180 {{case_exports}}/worxboard_right_top.stl \
        {{case_exports}}/worxboard_right_bottom.stl::0.69,0.72,0.77
    {{case_tools}} case/tools/zrender.py {{case_renders}}/right_with_legs.png 1100 -60 -60 \
        {{case_exports}}/worxboard_right_assembly_with_legs.stl
    {{case_tools}} case/tools/zrender.py {{case_renders}}/leg.png 800 35 30 {{case_exports}}/worxboard_leg.stl {{case_exports}}/worxboard_leg_cap.stl
    {{case_tools}} case/tools/zrender.py {{case_renders}}/leg_cap_tree.png 700 -55 20 {{case_exports}}/worxboard_leg_cap_tree.stl
    {{case_tools}} case/tools/zrender.py {{case_renders}}/spacer.png 1000 -50 35 {{case_exports}}/worxboard_right_spacer.stl
    {{case_tools}} case/tools/section.py {{case_exports}} {{case_renders}}/section.png
    {{case_tools}} case/tools/leg_section.py {{case_exports}} {{case_renders}}/leg_section.png
    {{case_tools}} case/overlay.py {{case_renders}}/overlay.png right

# Order package in case/exports/order (needs model): jlccnc/ (STEP + PDF drawings, hole table, notes),
# jlc3dp/ (printed parts, notes), hardware.csv; plus the stand-alone plate DXFs
order:
    rm -rf {{case_exports}}/order
    {{case_tools}} case/drawings.py {{case_exports}} {{case_exports}}/order
    cp case/production/README.md {{case_exports}}/order/README.md
    cp case/production/jlccnc/ORDER_NOTES.md {{case_exports}}/order/jlccnc/ORDER_NOTES.md
    cp case/production/jlc3dp/ORDER_NOTES.md {{case_exports}}/order/jlc3dp/ORDER_NOTES.md
    mkdir -p {{case_exports}}/order/plates && cp plates/*.dxf {{case_exports}}/order/plates/

# Copy the generated order files into the committed case/production (needs model + order)
production:
    {{case_tools}} case/production.py sync {{case_exports}}/order case/production

# Fail if case/production differs from a fresh order package (needs model + order)
production-check:
    {{case_tools}} case/production.py check {{case_exports}}/order case/production
