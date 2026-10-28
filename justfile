# worxboard - build recipes. Each stream owns its own *.just file.
#   just --list            all recipes
#   just setup             create .venv with every Python group (uv)
#   just all               layout-check -> fw -> pcb-all -> model -> site

import 'layout/layout.just'
import 'firmware/firmware.just'
import 'pcb/pcb.just'
import 'case/case.just'
import 'site/site.just'

version := `git describe --tags --always --dirty 2>/dev/null || echo dev`

# List recipes
default:
    @just --list --unsorted

# Create .venv (Python 3.12) with the layout, case and dev groups
setup:
    uv sync --all-groups

# Full pipeline from a clean clone (each stage is defined by its stream)
all:
    just layout-check
    just fw
    just pcb-all
    just model
    just site

# Remove Python caches and build outputs
clean:
    find . -name __pycache__ -type d -prune -exec rm -rf {} +
    rm -rf build
