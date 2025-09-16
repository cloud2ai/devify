#!/bin/bash
# HTML coverage report script - replaces poetry run pytest --cov --cov-report=html

set -e

echo "🚀 Running tests with HTML coverage report"
echo "==========================================="

# Run pytest with HTML coverage directly
python -m pytest \
    --cov=devify \
    --cov-report=html \
    --cov-report=term-missing \
    "$@"

echo ""
echo "✅ HTML coverage report generated:"
echo "   - HTML: htmlcov/index.html"
echo "   - Open with: xdg-open htmlcov/index.html"
