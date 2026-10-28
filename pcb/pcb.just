# PCB (WS2): headless KiCad pipeline of spec §9, one container run per stage group.
#   just pcb-deps            pinned container Python deps -> pcb/.tools/site313
#   just pcb-sch left        stages 1-6: footprints, schematic, ERC, netlist, netcmp
#   just pcb-sch-all         both sides, then require the committed schematics to be current

pcb_image := "kicad/kicad:10.0.7"
pcb_site  := "pcb/.tools/site313"

_pcb_docker := "docker run --rm --network none -u $(id -u):$(id -g) -e HOME=/tmp -v $PWD:/w -w /w -e PYTHONPATH=/w:/w/" + pcb_site + " " + pcb_image

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
