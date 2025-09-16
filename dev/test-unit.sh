#!/bin/bash
# Unit test script - runs unit tests only

set -e

echo "🚀 Running unit tests only"
echo "=========================="

# Run unit tests directly
python -m pytest \
    -m "unit" \
    -v \
    "$@"
