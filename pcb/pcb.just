# PCB (WS2): headless KiCad pipeline of spec §9, one container run per stage group.
#   just pcb-deps            pinned container Python deps -> pcb/.tools/site313
#   just pcb-sch left        stages 1-6: footprints, schematic, ERC, netlist, netcmp
#   just pcb-sch-all         both sides, then require the committed schematics to be current
#   just pcb-place left      stages 7-9: placement, locked critical routes, DSN
#   just pcb-route left      Freerouting (container B)
#   just pcb-finish left     stages 10-12: SES import, completion router, pours, DRC gate, checks
#   just pcb-drc left        stages 11-12 only, on the committed board (DRC gate, checks)
#   just pcb-fab left        stages 13-14: JLCPCB gerbers/BOM/CPL, renders, Edge DXF, STEP
#   just pcb-render-check left   after pcb-fab: the committed renders are current (pixel compare)
#   just pcb-production left     stage P: JLC order package (panel, gerbers/BOM/CPL) -> pcb/production/left
#   just pcb-production-check left   stage P, then the committed package must be byte-identical
#   just pcb-cpl-images          docs/images/cpl-*.svg: JLC footprints from the CPL over the KiCad pads
#   just pcb-stock left [5]      live JLC stock for the committed package (network)
#   just pcb left | pcb-all  everything for one / both sides

pcb_image := "kicad/kicad:10.0.7"
pcb_full  := "kicad/kicad:10.0.7-full"   # stock 3D models: STEP and renders only
pcb_site  := "pcb/.tools/site313"
fr_image  := "eclipse-temurin:25-jre"

# PYTHONHASHSEED=0 + seeded KIIDs (place.seed_kiids): the same inputs give byte-identical boards
_pcb_run    := "docker run --rm --network none -u $(id -u):$(id -g) -e HOME=/tmp -e PYTHONHASHSEED=0 -v $PWD:/w -w /w -e PYTHONPATH=/w:/w/" + pcb_site
_pcb_docker := _pcb_run + " " + pcb_image

# Install the container Python deps (spec §9.1) once
pcb-deps:
    @[ -d {{pcb_site}}/kicad_sch_api ] || uv pip install --python-version 3.13 --target {{pcb_site}} \
        kikit==1.8.1 kicad-sch-api==0.5.6 shapely==2.2.0

# Container A, schematic stages 1-6 for one side
pcb-sch side: pcb-deps
    {{_pcb_docker}} bash pcb/scripts/stage_a.sh {{side}}

# Stages 1-6 for both sides; fail if the generated library or schematics differ from git
pcb-sch-all: (pcb-sch "left") (pcb-sch "right")
    git diff --exit-code -- pcb/lib pcb/left/*.kicad_sch pcb/right/*.kicad_sch

# Stages 7-9 (container A, layout half): place, critical routes, DSN
pcb-place side: pcb-deps
    {{_pcb_docker}} bash -c "bash tools/kicad_env.sh && python3 pcb/scripts/place.py {{side}} && python3 pcb/scripts/route_critical.py {{side}} && python3 pcb/scripts/export_dsn.py {{side}}"

# Container B: Freerouting autoroute (spec §9.2); fallback -mp 60 when nets stay unrouted
pcb-route side passes="30":
    bash tools/fetch_freerouting.sh
    docker run --rm --network none --read-only --tmpfs /tmp -e HOME=/tmp -u $(id -u):$(id -g) \
        -v $PWD/pcb/.tools:/fr:ro -v $PWD/build/{{side}}:/w -w /w {{fr_image}} \
        java -Duser.home=/tmp -Djava.awt.headless=true -jar /fr/freerouting-2.5.0.jar \
        -de {{side}}.dsn -do {{side}}.ses --router.autorouter.max_passes={{passes}} --gui.enabled=false \
        --router.automatic_neckdown=false --router.copper_to_edge_clearance_um=500 > build/{{side}}/freerouting.log 2>&1
    @grep -E "unrouted|completed" build/{{side}}/freerouting.log | tail -2

# Container C: SES import, stitching, zone fill, DRC gate, scripted checks
pcb-finish side:
    {{_pcb_docker}} bash pcb/scripts/stage_c.sh {{side}}

# Stages 11-12 on the committed board: DRC gate (parity, 0 unconnected) and scripted checks
pcb-drc side: pcb-deps
    {{_pcb_docker}} bash -c "bash tools/kicad_env.sh && mkdir -p build/{{side}} && kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations --format json -o build/{{side}}/drc.json pcb/{{side}}/worxboard-{{side}}.kicad_pcb && python3 pcb/scripts/checks.py {{side}}"

# Container D, stages 13-14: build/<side>/{jlc/,edge.dxf,worxboard-<side>.step}, docs/images/pcb-<side>-*.png
pcb-fab side: pcb-deps
    {{_pcb_run}} {{pcb_full}} bash pcb/scripts/stage_d.sh {{side}}

# After pcb-fab: docs/images/pcb-<side>-*.png equal the committed ones up to the raytracer's run-to-run
# noise (a few pixels by a level or two, deviations BOARD-12)
pcb-render-check side: pcb-deps
    mkdir -p build/{{side}}/committed
    for v in top bottom; do git show HEAD:docs/images/pcb-{{side}}-$v.png > build/{{side}}/committed/pcb-{{side}}-$v.png; done
    {{_pcb_docker}} python3 pcb/scripts/render_check.py {{side}}

# Stage P: the JLC turnkey order package (KiKit panel + DRC, panel and bare-board gerbers/BOM/CPL,
# cpl_check, jlc_check) from the committed board -> build/<side>/production
pcb-package side: pcb-deps
    {{_pcb_docker}} bash pcb/scripts/stage_p.sh {{side}}

# Stage P, then make it the committed order package pcb/production/<side>/
pcb-production side: (pcb-package side)
    rm -rf pcb/production/{{side}}
    mkdir -p pcb/production
    cp -r build/{{side}}/production pcb/production/{{side}}

# Stage P, then require the committed order package to equal the rebuilt one byte for byte
pcb-production-check side: (pcb-package side)
    diff -r build/{{side}}/production pcb/production/{{side}}

# CPL overlay drawings docs/images/cpl-*.svg: JLC's footprints placed from the committed bare-board
# CPLs of both halves over the KiCad pads (cpl_check.py --svg)
pcb-cpl-images: pcb-deps
    {{_pcb_docker}} bash -c "bash tools/kicad_env.sh && python3 pcb/scripts/cpl_check.py --quiet --svg docs/images \
        pcb/left/worxboard-left.kicad_pcb pcb/production/left/bare-board/bom.csv pcb/production/left/bare-board/cpl.csv \
        pcb/right/worxboard-right.kicad_pcb pcb/production/right/bare-board/bom.csv pcb/production/right/bare-board/cpl.csv"

# Live JLC stock for the committed package (network; run it on the day you order)
pcb-stock side boards="5":
    uv run python pcb/scripts/jlc_check.py check {{side}} pcb/production/{{side}} --stock {{boards}}

# All stages for one side (spec §9.2): schematic, layout, autoroute, finish + DRC + checks, fab outputs
pcb side: (pcb-sch side) (pcb-place side) (pcb-route side) (pcb-finish side) (pcb-fab side)

# Both sides
pcb-all: (pcb "left") (pcb "right")
