#!/usr/bin/env bash
# Run pytest inside the running devify-api-dev container.

set -euo pipefail

CONTAINER_NAME="${DEVIFY_API_CONTAINER:-devify-api-dev}"
PROJECT_DIR="${DEVIFY_PROJECT_DIR:-/opt/devify}"

normalize_path() {
    case "$1" in
        devify/*)
            printf '%s\n' "${1#devify/}"
            ;;
        *)
            printf '%s\n' "$1"
            ;;
    esac
}

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: docker is not installed or not on PATH."
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    echo "Error: container '$CONTAINER_NAME' is not running."
    echo "Start the dev stack first, then rerun this script."
    exit 1
fi

ARGS=()
for arg in "$@"; do
    if [[ "$arg" == -* ]]; then
        ARGS+=("$arg")
    else
        ARGS+=("$(normalize_path "$arg")")
    fi
done

exec docker exec -w "$PROJECT_DIR" "$CONTAINER_NAME" pytest "${ARGS[@]}"
