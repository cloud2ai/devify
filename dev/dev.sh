#!/bin/bash
# Main development tool script - provides tox-like functionality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    echo "🛠️  Devify Development Tools"
    echo "============================"
    echo ""
    echo "Available commands:"
    echo ""
    echo "  test            Run basic tests"
    echo "  test-cov        Run tests with coverage"
    echo "  test-html       Run tests with HTML coverage report"
    echo "  test-fast       Run fast tests (exclude slow)"
    echo "  test-unit       Run unit tests only"
    echo "  test-integration Run integration tests only"
    echo ""
    echo "Usage examples:"
    echo "  ./dev/dev.sh test"
    echo "  ./dev/dev.sh test-cov"
    echo "  ./dev/dev.sh test-html"
    echo "  ./dev/dev.sh test -- -v  # Pass extra args to pytest"
    echo ""
    echo "🚀 Simple shell scripts to replace Poetry commands!"
}

case "${1:-help}" in
    test)
        shift
        exec "$SCRIPT_DIR/test.sh" "$@"
        ;;
    test-cov)
        shift
        exec "$SCRIPT_DIR/test-cov.sh" "$@"
        ;;
    test-html)
        shift
        exec "$SCRIPT_DIR/test-html.sh" "$@"
        ;;
    test-fast)
        shift
        exec "$SCRIPT_DIR/test-fast.sh" "$@"
        ;;
    test-unit)
        shift
        exec "$SCRIPT_DIR/test-unit.sh" "$@"
        ;;
    test-integration)
        shift
        exec "$SCRIPT_DIR/test-integration.sh" "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
