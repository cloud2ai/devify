#!/bin/bash
# Coverage test script - replaces poetry run pytest --cov

set -e

echo "🚀 Running tests with coverage"
echo "==============================="

# Run pytest with coverage directly
python -m pytest \
    --cov=devify \
    --cov-report=term-missing \
    --cov-report=xml \
    "$@"

echo ""
echo "✅ Coverage report generated:"
echo "   - XML: coverage.xml"
echo "   - Terminal: See above output"
