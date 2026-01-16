#!/bin/bash

# Cloudflare Pages Build Script
# This script prepares the web application for deployment.
# It gathers all assets into a 'dist' directory and fixes paths.

echo "Building Open EGM-4 Web..."

# 1. Clean and Create dist directory
rm -rf dist
mkdir -p dist

# 2. Copy Web Assets
# Copy content of 'web' to root of 'dist'
cp -r web/* dist/

# 3. Copy Source Code
# Copy 'src' directory into 'dist/src'
cp -r src dist/src
cp README.md dist/

# 4. Patch pyscript.toml
# In development (repo view), pyscript.toml points to "../src"
# In production (dist view), 'src' is inside the root, not parent.
# We need to change "../src" to "./src" (which actually means keys in [files])

# Using sed to simple replacement of "../" with "./" in the [files] section would be risky globally,
# but safe enough if we target specific lines or just the files section keys.
# Let's replace '"../' with '"./' 

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed requires empty string for -i
    sed -i '' 's|"\.\./|"\./|g' dist/pyscript.toml
else
    # Linux (Cloudflare)
    sed -i 's|"\.\./|"\./|g' dist/pyscript.toml
fi

echo "Build complete. Output directory: dist"
