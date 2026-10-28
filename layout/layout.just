# Layout (WS0): the single source of truth for pcb/, case/, firmware/ and site/

# Regenerate layout/build/layout.json, docs/images/layout.svg and build/kle.json
layout:
    uv run python -m layout.export

# Layout acceptance: tests, then regenerate and require no diff in the committed outputs
layout-check:
    uv run pytest layout
    just layout
    git diff --exit-code -- layout/build/layout.json docs/images/layout.svg
    test -z "$(git status --porcelain -- layout/build docs/images/layout.svg)"
