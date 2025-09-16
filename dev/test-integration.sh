#!/bin/bash
# Integration test script - runs integration tests only

set -e

echo "🚀 Running integration tests only"
echo "=================================="

# Run integration tests directly
python -m pytest \
    -m "integration" \
    -v \
    "$@"
