#!/usr/bin/env bash
# Platform smoke tests for install.sh (no Docker/root needed).
# Runs on Linux, macOS, and Windows (Git Bash) and exercises the
# platform-specific branches: detect_os, detect_arch, check_memory,
# port_in_use, configure (domain/timezone), require_root and the
# Git Bash -> Windows path conversion used by run_compose.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

FAILURES=0
ok()   { printf 'ok:   %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; FAILURES=$((FAILURES + 1)); }
section() { printf '\n=== %s ===\n' "$1"; }

section "Syntax"
if bash -n install.sh; then ok "bash -n install.sh"; else fail "bash -n install.sh"; fi

section "CLI --help"
if bash install.sh --help 2>&1 | grep -q "Supported platforms"; then
  ok "--help lists supported platforms"
else
  fail "--help lists supported platforms"
fi

section "Platform detection"
# shellcheck disable=SC1091
source ./install.sh || { echo "cannot source install.sh"; exit 1; }
# install.sh sets -Eeuo pipefail; restore safer options for the test harness.
set +eE
set +u
set +o pipefail

uname_s="$(uname -s)"
case "${uname_s}" in
  Darwin)               EXPECT_PLATFORM="macos" ;;
  Linux)                EXPECT_PLATFORM="linux" ;;
  MINGW*|MSYS*|CYGWIN*) EXPECT_PLATFORM="windows" ;;
  *)                    EXPECT_PLATFORM="unknown" ;;
esac
if [[ "${PLATFORM}" == "${EXPECT_PLATFORM}" ]]; then
  ok "PLATFORM=${PLATFORM}"
else
  fail "PLATFORM=${PLATFORM}, expected ${EXPECT_PLATFORM}"
fi

section "detect_os"
detect_os >/dev/null 2>&1
case "${PLATFORM}" in
  macos)
    [[ "${OS_ID}" == "macos" ]] && ok "OS_ID=macos" || fail "OS_ID=${OS_ID}"
    [[ -n "${OS_NAME}" ]] && ok "OS_NAME=${OS_NAME}" || fail "OS_NAME is empty"
    ;;
  windows)
    [[ "${OS_ID}" == "windows" ]] && ok "OS_ID=windows" || fail "OS_ID=${OS_ID}"
    [[ -n "${OS_NAME}" ]] && ok "OS_NAME=${OS_NAME}" || fail "OS_NAME is empty"
    ;;
  linux)
    [[ "${OS_ID}" =~ ^(ubuntu|debian|rocky|alma|centos|unknown)$ ]] \
      && ok "OS_ID=${OS_ID}" || fail "OS_ID=${OS_ID}"
    ;;
esac

section "detect_arch"
detect_arch >/dev/null 2>&1
if [[ "${ARCH}" =~ ^(amd64|arm64)$ ]]; then
  ok "ARCH=${ARCH}"
else
  fail "ARCH=${ARCH}"
fi

section "detect_channel (lowercase, bash 3.2 portable)"
CHANNEL="GitHub"
REGISTRY=""
detect_channel >/dev/null 2>&1
if [[ "${CHANNEL}" == "github" ]]; then
  ok "channel lowercased to github"
else
  fail "channel='${CHANNEL}', expected github"
fi

section "check_memory"
mem_out="$(check_memory 2>&1 || true)"
mem_gb="$(printf '%s\n' "${mem_out}" | sed -n 's/.*Memory: \([0-9][0-9]*\) GB.*/\1/p')"
if [[ -n "${mem_gb}" ]]; then
  if ((mem_gb >= 1)); then
    ok "memory detected: ${mem_gb} GB"
  else
    fail "memory too low: ${mem_gb} GB"
  fi
elif printf '%s\n' "${mem_out}" | grep -q "skipping the memory check"; then
  ok "memory check skipped on this platform (no wmic)"
else
  fail "check_memory produced no usable result: ${mem_out}"
fi

section "port_in_use"
PY=""
for cand in python3 python; do
  if command -v "${cand}" >/dev/null 2>&1; then PY="${cand}"; break; fi
done
if [[ -n "${PY}" ]]; then
  PORT=18765
  SERVER_LOG="${TMPDIR:-/tmp}/devify-test-socket-$$.log"
  (
    sleep 2
    exec "${PY}" -c \
      'import socket, sys, time; sock = socket.socket(); sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); sock.bind(("127.0.0.1", int(sys.argv[1]))); sock.listen(1); time.sleep(30)' \
      "${PORT}"
  ) >"${SERVER_LOG}" 2>&1 &
  SRV_PID=$!
  port_ready=0
  port_attempt=0
  while ((port_attempt < 20)); do
    if port_in_use "${PORT}"; then
      port_ready=1
      break
    fi
    port_attempt=$((port_attempt + 1))
    sleep 0.5
  done
  if ((port_ready)); then
    ok "detects listening port ${PORT}"
  else
    fail "missed listening port ${PORT}"
    if kill -0 "${SRV_PID}" 2>/dev/null; then
      printf 'diagnostic: socket server process %s is still running\n' "${SRV_PID}"
    else
      printf 'diagnostic: socket server process %s exited before the port check\n' "${SRV_PID}"
    fi
    if command -v lsof >/dev/null 2>&1; then
      printf 'diagnostic: lsof path: %s\n' "$(command -v lsof)"
      lsof -nP -iTCP -sTCP:LISTEN 2>&1 | grep -F ":${PORT}" || true
    else
      printf 'diagnostic: lsof is unavailable\n'
    fi
    if [[ -s "${SERVER_LOG}" ]]; then
      sed 's/^/diagnostic: server: /' "${SERVER_LOG}"
    fi
  fi
  if port_in_use "$((PORT + 1))"; then
    fail "false positive on free port $((PORT + 1))"
  else
    ok "free port $((PORT + 1)) not flagged"
  fi
  kill "${SRV_PID}" 2>/dev/null || true
  wait "${SRV_PID}" 2>/dev/null || true
  rm -f "${SERVER_LOG}"
else
  ok "python not available; skipping live-port check"
fi

section "configure (domain/timezone)"
res="$(
  ASSUME_YES=1
  INSTALL_DIR="${TMPDIR:-/tmp}/devify-test-$$"
  DOMAIN=""
  TIMEZONE=""
  ADMIN_EMAIL=""
  EMAIL_DOMAIN=""
  configure >/dev/null 2>&1
  printf '%s\n%s\n' "${DOMAIN}" "${TIMEZONE}"
)"
test_domain="$(printf '%s\n' "${res}" | sed -n '1p')"
test_timezone="$(printf '%s\n' "${res}" | sed -n '2p')"
[[ -n "${test_domain}" ]] && ok "domain=${test_domain}" || fail "domain is empty"
[[ -n "${test_timezone}" ]] && ok "timezone=${test_timezone}" || fail "timezone is empty"

section "require_root"
if [[ "${PLATFORM}" == "windows" ]]; then
  if require_root >/dev/null 2>&1; then
    ok "require_root runs without root on Windows"
  else
    fail "require_root failed on Windows"
  fi
else
  ok "require_root skipped (root/sudo re-exec is host-specific, not run in CI)"
fi

section "run_compose (Windows path conversion)"
if [[ "${PLATFORM}" == "windows" ]]; then
  COMPOSE_CMD=(echo)
  LOG_FILE="${TMPDIR:-/tmp}/devify-test-install.log"
  : >"${LOG_FILE}"
  INSTALL_DIR="${HOME}/devify"
  DATA_DIR="${INSTALL_DIR}"
  out="$(run_compose ps 2>/dev/null)"
  if [[ "${out}" =~ --project-directory\ [A-Za-z]:[\\/] ]]; then
    ok "MSYS path converted for Docker CLI: ${out}"
  else
    fail "path not converted: ${out}"
  fi
else
  ok "run_compose conversion covered by CI on windows-latest"
fi

printf '\n'
if ((FAILURES > 0)); then
  printf '%d test(s) failed\n' "${FAILURES}"
  exit 1
fi
printf 'All platform smoke tests passed\n'
