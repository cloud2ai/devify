#!/bin/bash
# Basic test script - replaces poetry run pytest

set -e

echo "🚀 Running basic tests"
echo "======================"

# Run pytest directly
python -m pytest "$@"
