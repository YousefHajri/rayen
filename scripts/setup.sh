#!/usr/bin/env bash
# RAYEN v0.2 setup — macOS / Linux.  Usage: bash scripts/setup.sh [--with-blender]
set -e
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
$PY -m pip install --upgrade pip
$PY -m pip install -r requirements.txt
if [[ "$1" == "--with-blender" ]]; then
  if $PY -c 'import sys; exit(0 if sys.version_info[:2]==(3,13) else 1)'; then
    $PY -m pip install bpy
  else
    echo "bpy 5.x needs Python 3.13 — install Blender from blender.org instead and run: blender -b -P skills/rayen-render/scripts/render.py -- scene.json -o out"
  fi
fi
$PY scripts/selftest.py
