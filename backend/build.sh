#!/usr/bin/env bash
set -o errexit

echo "=== Python version ==="
python --version

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

echo "=== Build complete ==="
