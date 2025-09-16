#!/bin/bash
# Fast test script - excludes slow tests

set -e

echo "🚀 Running fast tests (excluding slow tests)"
echo "============================================="

# Run fast tests directly
python -m pytest \
    -m "not slow" \
    -v \
    "$@"
