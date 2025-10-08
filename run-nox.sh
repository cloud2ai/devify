#!/bin/bash
#
# Helper script to run nox without color conflicts
#
# Usage:
#   ./run-nox.sh                    # Run default sessions
#   ./run-nox.sh -s unit_tests     # Run specific session
#   ./run-nox.sh --list            # List all sessions
#

# Unset conflicting color environment variables
unset FORCE_COLOR
unset NO_COLOR

# Run nox with all arguments passed to this script
exec nox "$@"
