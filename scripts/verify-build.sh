#!/bin/bash
# Build Verification Script for Peacock Engine V3 Frontend
# Ensures the React UI builds correctly and outputs to app/static/

set -e

echo "[verify-build] Starting frontend build verification..."

cd "$(dirname "$0")/.."

# Step 1: Ensure ui/ directory exists
if [ ! -d "ui" ]; then
    echo "[verify-build] ERROR: ui/ directory not found"
    exit 1
fi

# Step 2: Build the frontend
echo "[verify-build] Running npm install && npm run build in ui/..."
cd ui
npm install
npm run build
cd ..

# Step 3: Verify app/static/index.html exists
if [ ! -f "app/static/index.html" ]; then
    echo "[verify-build] ERROR: app/static/index.html is missing after build"
    exit 1
fi

echo "[verify-build] app/static/index.html exists"

# Step 4: Verify key asset files referenced in index.html exist
JS_FILE=$(grep -oP 'src="/assets/[^"]+\.js"' app/static/index.html | head -1 | sed 's/src="//;s/"//')
CSS_FILE=$(grep -oP 'href="/assets/[^"]+\.css"' app/static/index.html | head -1 | sed 's/href="//;s/"//')

if [ -n "$JS_FILE" ]; then
    JS_PATH="app/static$JS_FILE"
    if [ ! -f "$JS_PATH" ]; then
        echo "[verify-build] ERROR: JS asset missing: $JS_PATH"
        exit 1
    fi
    echo "[verify-build] JS asset exists: $JS_PATH"
fi

if [ -n "$CSS_FILE" ]; then
    CSS_PATH="app/static$CSS_FILE"
    if [ ! -f "$CSS_PATH" ]; then
        echo "[verify-build] ERROR: CSS asset missing: $CSS_PATH"
        exit 1
    fi
    echo "[verify-build] CSS asset exists: $CSS_PATH"
fi

# Step 5: Verify index.html references are consistent
INDEX_HASH=$(grep -oP 'index-[A-Za-z0-9]+\.js' app/static/index.html | head -1)
ACTUAL_JS=$(ls app/static/assets/index-*.js 2>/dev/null | head -1 | xargs basename)

if [ "$INDEX_HASH" != "$ACTUAL_JS" ]; then
    echo "[verify-build] ERROR: index.html references $INDEX_HASH but found $ACTUAL_JS"
    exit 1
fi

echo "[verify-build] Asset references are consistent"

echo "[verify-build] ✅ All checks passed. Frontend build is healthy."
