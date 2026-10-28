# Docs and microsite (WS4)

site_out := "_site"
lychee   := "lycheeverse/lychee:0.24.2"
docs_md  := "README.md docs/*.md"

# Regenerate docs/pinout.md and docs/matrix.md from layout/build/layout.json
docs-gen:
    uv run python site/gen_docs.py

# Docs acceptance: generated docs up to date, then every local link and anchor resolves
docs-check:
    uv run python site/gen_docs.py --check
    just docs-links --offline

# Link check with lychee in Docker (pass --offline to skip external URLs)
docs-links *args:
    docker run --rm -u $(id -u):$(id -g) -v "$PWD":/w -w /w {{lychee}} \
        --no-progress --include-fragments --root-dir /w {{args}} {{docs_md}}

# Build the GitHub Pages microsite into _site/ (adds case STLs and renders when they exist)
site:
    uv run python site/build_site.py {{site_out}} {{quote(version)}}

# Build the site and serve it on http://localhost:8000
site-serve: site
    cd {{site_out}} && python3 -m http.server 8000
