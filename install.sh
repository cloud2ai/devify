#!/usr/bin/env bash
# =============================================================================
# Devify one-command installer
#
# Implements INSTALL_SPEC.md (RFC v1.0):
#   - one-command install via `curl ... | bash`
#   - Docker Compose based; NEVER clones the Git repository
#   - downloads version-consistent release artifacts
#   - preserves user configuration and data; safe to re-run (idempotent)
#   - supports github (ghcr.io / GitHub Releases) and cn (ACR / OSS-CDN) channels
#   - supported platforms: Linux (Ubuntu/Debian/Rocky/Alma/CentOS), macOS,
#     and Windows via Git Bash (all require Docker; Docker Desktop works)
#
# Release artifact layout (must be published by the maintainers per release tag):
#   devify-<version>.tar.gz
#   |-- VERSION                      # e.g. "v1.2.0"
#   |-- docker-compose.yml
#   |-- env.sample
#   |-- docker/
#   |   |-- nginx/{default.conf,certs/}
#   |   |-- mysql/{etc,initdb.d,scripts}/
#   |   `-- haraka/{config,plugins}/
#   `-- (optional extras)
#   devify-<version>.tar.gz.sha256   # optional checksum file
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/cloud2ai/devify/main/install.sh | sudo bash
#   sudo bash install.sh [options]   # see --help
# =============================================================================

set -Eeuo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_NAME="devify"
APP_TITLE="Devify"
GITHUB_REPO="cloud2ai/devify"
GITHUB_API="https://api.github.com/repos/${GITHUB_REPO}"
DEFAULT_INSTALL_DIR="/opt/${APP_NAME}"
DEFAULT_HTTP_PORT=8080
DEFAULT_HTTPS_PORT=10443
DEFAULT_ADMIN_PORT=19443
DEFAULT_SMTP_PORT=25
REGISTRY_GITHUB="ghcr.io/cloud2ai"
REGISTRY_CN="registry.cn-beijing.aliyuncs.com/cloud2ai"
INSTALLER_VERSION="0.2.0"
HEALTH_TIMEOUT=120

# Detect host platform early: macOS and Windows need different defaults and
# preflight behavior (memory detection, daemon.json, root requirement, paths).
case "$(uname -s)" in
  Darwin)                PLATFORM="macos" ;;
  Linux)                 PLATFORM="linux" ;;
  MINGW*|MSYS*|CYGWIN*)  PLATFORM="windows" ;;
  *)                     PLATFORM="unknown" ;;
esac
# Git Bash has no privileged /opt; install under the user's home by default.
if [[ "${PLATFORM}" == "windows" ]]; then
  DEFAULT_INSTALL_DIR="${HOME}/devify"
fi

# ---------------------------------------------------------------------------
# Defaults (overridable via DEVIFY_* environment variables / CLI flags)
# ---------------------------------------------------------------------------
INSTALL_DIR="${DEVIFY_INSTALL_DIR:-${DEFAULT_INSTALL_DIR}}"
INSTALL_DIR_OVERRIDE=0
[[ -n "${DEVIFY_INSTALL_DIR:-}" ]] && INSTALL_DIR_OVERRIDE=1

HTTP_PORT=""
HTTP_PORT_OVERRIDE=0
[[ -n "${DEVIFY_HTTP_PORT:-}" ]] && { HTTP_PORT="${DEVIFY_HTTP_PORT}"; HTTP_PORT_OVERRIDE=1; }

ADMIN_PORT=""
ADMIN_PORT_OVERRIDE=0
[[ -n "${DEVIFY_ADMIN_PORT:-}" ]] && { ADMIN_PORT="${DEVIFY_ADMIN_PORT}"; ADMIN_PORT_OVERRIDE=1; }

SMTP_PORT=""
SMTP_PORT_OVERRIDE=0
[[ -n "${DEVIFY_SMTP_PORT:-}" ]] && { SMTP_PORT="${DEVIFY_SMTP_PORT}"; SMTP_PORT_OVERRIDE=1; }

HTTPS_PORT="${DEVIFY_HTTPS_PORT:-${DEFAULT_HTTPS_PORT}}"
CHANNEL="${DEVIFY_CHANNEL:-}"
VERSION="${DEVIFY_VERSION:-}"
REGISTRY="${DEVIFY_REGISTRY:-}"
DATA_DIR="${DEVIFY_DATA_DIR:-}"
TIMEZONE="${DEVIFY_TIMEZONE:-}"
DOMAIN="${DEVIFY_DOMAIN:-}"
DOMAIN_OVERRIDE=0
[[ -n "${DEVIFY_DOMAIN:-}" ]] && DOMAIN_OVERRIDE=1

HTTPS="${DEVIFY_HTTPS:-false}"
ADMIN_USERNAME="${DEVIFY_ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${DEVIFY_ADMIN_EMAIL:-}"
EMAIL_DOMAIN="${DEVIFY_EMAIL_DOMAIN:-}"
CN_DOWNLOAD_BASE="${DEVIFY_CN_DOWNLOAD_BASE:-}"
ASSUME_YES=0
[[ "${DEVIFY_YES:-}" == "1" ]] && ASSUME_YES=1
INSTALL_DOCKER=0
[[ "${DEVIFY_INSTALL_DOCKER:-}" == "1" ]] && INSTALL_DOCKER=1
DOCKER_MIRROR="${DEVIFY_DOCKER_MIRROR:-}"
FORCE=0
ADVANCED=0

SCHEME="http"
PORT_SUFFIX=""
TMP_DIR=""
LOG_FILE=""
COMPOSE_CMD=()
EXISTING=0
INSTALLED_VERSION=""
ENV_EXISTS=0
ENV_REDIS_PASSWORD=""
ADMIN_PASSWORD=""

# ---------------------------------------------------------------------------
# Colored logging helpers (INSTALL_SPEC §20)
# ---------------------------------------------------------------------------
c_red=$'\033[31m'; c_green=$'\033[32m'; c_yellow=$'\033[33m'
c_blue=$'\033[34m'; c_cyan=$'\033[36m'; c_bold=$'\033[1m'; c_reset=$'\033[0m'
if [[ ! -t 1 || "${NO_COLOR:-}" == "1" || "${TERM:-}" == "dumb" ]]; then
  c_red=""; c_green=""; c_yellow=""; c_blue=""; c_cyan=""; c_bold=""; c_reset=""
fi

log_line() {
  [[ -n "${LOG_FILE}" ]] || return 0
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >>"${LOG_FILE}"
}

log_info()  { printf '%s%s%s\n' "${c_cyan}" "$1" "${c_reset}"; log_line "[INFO]  $1"; }
log_ok()    { printf '%s%s%s\n' "${c_green}" "$1" "${c_reset}"; log_line "[OK]    $1"; }
log_warn()  { printf '%sWARN: %s%s\n' "${c_yellow}" "$1" "${c_reset}"; log_line "[WARN]  $1"; }
log_error() { printf '%sERROR: %s%s\n' "${c_red}" "$1" "${c_reset}" >&2; log_line "[ERROR] $1"; }
log_step()  { printf '\n%s=== %s ===%s\n' "${c_bold}${c_cyan}" "$1" "${c_reset}"; log_line "[STEP]  $1"; }

abort() {
  log_error "$1"
  log_line "install aborted"
  exit 1
}

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: install.sh [options]

Supported platforms: Linux (Ubuntu/Debian/Rocky/Alma/CentOS), macOS, and
Windows (Git Bash). All platforms require Docker (Docker Desktop works).

Options:
  -d, --dir DIR          Install directory (default: ${DEFAULT_INSTALL_DIR})
  -p, --port PORT        HTTP port (default: ${DEFAULT_HTTP_PORT})
  -c, --channel CH       Distribution channel: github | cn (default: auto-detect)
  -v, --version VER      Release version to install (default: latest)
  -r, --registry REG     Override Docker registry
      --domain HOST      Public hostname / IP
      --data-dir DIR     Data directory (advanced)
      --timezone TZ      Container timezone (advanced)
      --admin-port PORT  Admin HTTPS port (default: ${DEFAULT_ADMIN_PORT})
      --smtp-port PORT   Inbound SMTP port (default: ${DEFAULT_SMTP_PORT})
      --admin-user USER  Initial admin username (default: admin)
      --admin-email EMAIL Initial admin email
      --email-domain D   Inbound email domain (advanced)
      --https            Configure for HTTPS behind a TLS reverse proxy (advanced)
      --cn-base URL      CN channel artifact base URL (advanced)
      --install-docker   Automatically install Docker if missing
      --docker-mirror URL Configure a Docker Hub registry mirror (recommended for cn)
      --advanced         Ask advanced questions interactively
  -y, --yes              Non-interactive: accept defaults, no prompts
      --force            Reinstall/upgrade without confirmation
  -h, --help             Show this help

Environment overrides: DEVIFY_INSTALL_DIR, DEVIFY_HTTP_PORT, DEVIFY_CHANNEL,
DEVIFY_VERSION, DEVIFY_REGISTRY, DEVIFY_DATA_DIR, DEVIFY_TIMEZONE,
DEVIFY_DOMAIN, DEVIFY_HTTPS, DEVIFY_ADMIN_PORT, DEVIFY_SMTP_PORT,
DEVIFY_CN_DOWNLOAD_BASE, DEVIFY_INSTALL_DOCKER=1, DEVIFY_DOCKER_MIRROR,
DEVIFY_YES=1
EOF
}

# ---------------------------------------------------------------------------
# Interaction helpers
# ---------------------------------------------------------------------------
confirm() {
  local prompt="$1" answer=""
  [[ "${ASSUME_YES}" == "1" ]] && return 0
  if [[ ! -t 0 ]]; then
    if [[ -e /dev/tty ]]; then
      printf '%s [y/N] ' "${prompt}" >/dev/tty
      read -r answer </dev/tty || answer="n"
    else
      return 0 # fully non-interactive: proceed with defaults
    fi
  else
    printf '%s [y/N] ' "${prompt}"
    read -r answer || answer="n"
  fi
  answer="$(printf '%s' "${answer}" | tr '[:upper:]' '[:lower:]')"
  [[ "${answer}" == "y" || "${answer}" == "yes" ]]
}

prompt_value() {
  local var_name="$1" label="$2" default="$3" answer=""
  if [[ "${ASSUME_YES}" == "1" || ! -t 0 ]]; then
    printf -v "${var_name}" '%s' "${default}"
    return 0
  fi
  printf '%s [%s]: ' "${label}" "${default}"
  read -r answer || true
  printf -v "${var_name}" '%s' "${answer:-${default}}"
}

# ---------------------------------------------------------------------------
# §2 Preflight checks
# ---------------------------------------------------------------------------
require_root() {
  # Git Bash on Windows has no root/sudo and does not need it: Docker Desktop
  # provides the engine and the default install dir lives under $HOME.
  if [[ "${PLATFORM}" == "windows" ]]; then
    log_info "Running on Windows (Git Bash) without root — Docker Desktop provides the engine"
    return 0
  fi
  if [[ "$(id -u)" -eq 0 ]]; then return 0; fi
  if command -v sudo >/dev/null 2>&1 && [[ -f "$0" && "$0" != "bash" && "$0" != "-bash" ]]; then
    log_warn "not running as root, re-executing with sudo"
    exec sudo -E bash "$0" "$@"
  fi
  abort "install.sh must run as root (or via sudo). e.g. sudo bash install.sh"
}

detect_os() {
  OS_ID="unknown"; OS_NAME="unknown"; SUPPORTED_OS=0
  if [[ "${PLATFORM}" == "macos" ]]; then
    OS_ID="macos"; OS_NAME="macOS $(sw_vers -productVersion 2>/dev/null)"
  elif [[ "${PLATFORM}" == "windows" ]]; then
    OS_ID="windows"; OS_NAME="Windows (Git Bash)"
  elif [[ -r /etc/os-release ]]; then
    OS_ID=$(. /etc/os-release; printf '%s' "${ID:-unknown}")
    OS_NAME=$(. /etc/os-release; printf '%s' "${PRETTY_NAME:-unknown}")
    case "${OS_ID}" in
      ubuntu|debian|rocky|alma|centos) SUPPORTED_OS=1 ;;
    esac
  fi
  log_info "OS: ${OS_NAME} (${OS_ID})"
  if [[ "${SUPPORTED_OS}" == "0" ]]; then
    log_warn "OS '${OS_ID}' is not in the supported list (Ubuntu/Debian/Rocky/Alma/CentOS); continuing only if Docker is already available"
  fi
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64)   ARCH="amd64" ;;
    aarch64|arm64)  ARCH="arm64" ;;
    *) abort "unsupported CPU architecture: $(uname -m) (supported: amd64, arm64)" ;;
  esac
  log_info "Architecture: ${ARCH}"
}

check_memory() {
  local mem_kb=0 mem_gb=0
  case "${PLATFORM}" in
    macos)
      mem_kb="$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 ))"
      ;;
    windows)
      if command -v wmic >/dev/null 2>&1; then
        mem_kb="$(wmic OS get TotalVisibleMemorySize /value 2>/dev/null | sed -n 's/.*=\([0-9][0-9]*\).*/\1/p' | head -n1)"
      else
        log_warn "cannot detect memory on Windows (wmic unavailable); skipping the memory check"
        return 0
      fi
      ;;
    *) mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)" ;;
  esac
  mem_kb="${mem_kb:-0}"
  [[ "${mem_kb}" =~ ^[0-9]+$ ]] || mem_kb=0
  mem_gb=$((mem_kb / 1024 / 1024))
  log_info "Memory: ${mem_gb} GB"
  if ((mem_gb < 1)); then
    abort "available memory is too low (${mem_gb} GB); at least 2 GB required (4 GB recommended)"
  elif ((mem_gb < 4)); then
    log_warn "memory below the 4 GB recommendation (${mem_gb} GB)"
  fi
}

check_disk() {
  local free_kb=0 free_gb=0
  free_kb="$(df -Pk "${INSTALL_DIR}" 2>/dev/null | awk 'NR==2 {print $4}' || echo 0)"
  free_gb=$((free_kb / 1024 / 1024))
  log_info "Disk space on ${INSTALL_DIR}: ${free_gb} GB free"
  if ((free_gb < 5)); then
    abort "insufficient disk space (${free_gb} GB free); at least 5 GB required (20 GB recommended)"
  elif ((free_gb < 20)); then
    log_warn "disk space below the 20 GB recommendation (${free_gb} GB free)"
  fi
}

check_tools() {
  local tool
  for tool in curl tar gzip openssl; do
    command -v "${tool}" >/dev/null 2>&1 || abort "required tool not found: ${tool}"
  done
  log_ok "Required tools present (curl, tar, gzip, openssl)"
}

# ---------------------------------------------------------------------------
# §2/§9 Channel detection & network connectivity
# ---------------------------------------------------------------------------
detect_channel() {
  if [[ -z "${CHANNEL}" ]]; then
    log_info "Detecting install channel..."
    if curl -fsSI --max-time 8 -o /dev/null https://github.com >/dev/null 2>&1; then
      CHANNEL="github"
    else
      CHANNEL="cn"
    fi
    log_info "Auto-detected channel: ${CHANNEL}"
  fi
  CHANNEL="$(printf '%s' "${CHANNEL}" | tr '[:upper:]' '[:lower:]')"
  case "${CHANNEL}" in
    github|cn) ;;
    *) abort "invalid channel '${CHANNEL}' (supported: github, cn)" ;;
  esac
  if [[ -z "${REGISTRY}" ]]; then
    if [[ "${CHANNEL}" == "github" ]]; then REGISTRY="${REGISTRY_GITHUB}"; else REGISTRY="${REGISTRY_CN}"; fi
  fi
  log_info "Channel: ${CHANNEL} | Registry: ${REGISTRY}"
}

check_network() {
  log_info "Checking network connectivity (channel: ${CHANNEL})..."
  local url=""
  if [[ "${CHANNEL}" == "github" || -z "${CN_DOWNLOAD_BASE}" ]]; then
    url="https://github.com/${GITHUB_REPO}"
    curl -fsSI --max-time 10 -o /dev/null "${url}" \
      || abort "no connectivity to ${url}; check the network or select a different channel (--channel cn)"
  else
    url="${CN_DOWNLOAD_BASE}"
    curl -fsSI --max-time 10 -o /dev/null "${url}" \
      || abort "no connectivity to CN distribution base ${url}"
  fi
  log_ok "network OK (${url})"
}

# ---------------------------------------------------------------------------
# §2/§3/§10 Docker & Docker Compose
# ---------------------------------------------------------------------------
check_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    log_warn "Docker is not installed"
    install_docker
    return 0
  fi
  DOCKER_VERSION="$(docker --version 2>/dev/null | sed -n 's/^Docker version \([0-9][0-9.]*\).*/\1/p')"
  log_info "Docker: ${DOCKER_VERSION:-unknown}"
  if [[ -n "${DOCKER_VERSION}" ]]; then
    local major=0 minor=0
    major="${DOCKER_VERSION%%.*}"
    minor="${DOCKER_VERSION#*.}"; minor="${minor%%.*}"
    if ((major < 20 || (major == 20 && minor < 10))); then
      log_warn "Docker ${DOCKER_VERSION} is older than 20.10; upgrade recommended"
    fi
  fi
  docker info >/dev/null 2>&1 \
    || abort "docker daemon is not running; start it (Docker Desktop on ${OS_NAME}) and re-run the installer"
  log_ok "Docker daemon is running"
  configure_docker_mirror
}

configure_docker_mirror() {
  [[ -n "${DOCKER_MIRROR}" ]] || return 0
  log_info "Configuring Docker Hub mirror: ${DOCKER_MIRROR}"
  if [[ "${PLATFORM}" != "linux" ]]; then
    log_warn "Docker Desktop on ${OS_NAME} does not read /etc/docker/daemon.json; configure the mirror in Docker Desktop settings (registry-mirrors) manually"
    return 0
  fi
  mkdir -p /etc/docker
  if [[ -f /etc/docker/daemon.json ]]; then
    if command -v python3 >/dev/null 2>&1; then
      python3 -c 'import json, sys
p = "/etc/docker/daemon.json"
d = json.load(open(p))
m = d.setdefault("registry-mirrors", [])
for x in sys.argv[1:]:
    if x not in m:
        m.append(x)
json.dump(d, open(p, "w"), indent=2)' "${DOCKER_MIRROR}"
    else
      log_warn "daemon.json exists but python3 is unavailable; mirror config not merged"
      return 0
    fi
  else
    printf '{\n  "registry-mirrors": ["%s"]\n}\n' "${DOCKER_MIRROR}" >/etc/docker/daemon.json
  fi
  systemctl restart docker >/dev/null 2>&1 || service docker restart >/dev/null 2>&1 || true
  sleep 3
  docker info >/dev/null 2>&1 || log_warn "docker daemon did not come back after mirror configuration"
  log_ok "Docker Hub mirror configured"
}

install_docker() {
  if [[ "${INSTALL_DOCKER}" != "1" ]]; then
    if [[ "${ASSUME_YES}" == "1" || ! -t 0 ]]; then
      abort "Docker is required but not installed; re-run with --install-docker to install it automatically"
    fi
    confirm "Docker is missing. Install Docker automatically?" \
      || abort "Docker is required; install it manually and re-run the installer"
  fi
  if [[ "${SUPPORTED_OS}" != "1" ]]; then
    install_docker_desktop
    return 0
  fi
  log_info "Installing Docker..."
  local script_urls=() url="" ok=0
  if [[ "${CHANNEL}" == "cn" ]]; then
    script_urls=("https://get.daocloud.io/docker" "https://get.docker.com")
  else
    script_urls=("https://get.docker.com" "https://get.daocloud.io/docker")
  fi
  for url in "${script_urls[@]}"; do
    log_info "trying Docker install script: ${url}"
    if curl -fsSL --max-time 60 "${url}" | sh; then
      ok=1
      break
    fi
    log_warn "Docker install script failed: ${url}"
  done
  if [[ "${ok}" != "1" ]]; then
    log_warn "Docker install scripts unreachable; falling back to distribution packages"
    install_docker_distro
  fi
  systemctl enable --now docker >/dev/null 2>&1 || true
  command -v docker >/dev/null 2>&1 || abort "Docker installation completed but 'docker' is not on PATH"
  log_ok "Docker installed: $(docker --version)"
  configure_docker_mirror
}

install_docker_desktop() {
  case "${PLATFORM}" in
    macos)
      if command -v brew >/dev/null 2>&1; then
        log_info "Installing Docker Desktop via Homebrew..."
        brew install --cask docker \
          || abort "Homebrew install failed; install Docker Desktop manually from https://www.docker.com/products/docker-desktop/ and re-run the installer"
        log_warn "Docker Desktop installed via Homebrew — open Docker.app once to finish setup, then re-run the installer"
      else
        log_warn "Homebrew is not installed; install it from https://brew.sh or use the official installer"
        abort "install Docker Desktop manually from https://www.docker.com/products/docker-desktop/ and re-run the installer"
      fi
      ;;
    windows)
      if command -v winget >/dev/null 2>&1; then
        log_info "Installing Docker Desktop via winget..."
        winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements || true
      fi
      abort "install Docker Desktop manually from https://www.docker.com/products/docker-desktop/ and re-run the installer"
      ;;
    *)
      abort "cannot auto-install Docker on unsupported OS '${OS_ID}'; install Docker manually and re-run"
      ;;
  esac
}

install_docker_distro() {
  case "${OS_ID}" in
    ubuntu|debian)
      apt-get update -y
      apt-get install -y docker.io docker-compose-v2 2>/dev/null \
        || apt-get install -y docker.io docker-compose-plugin
      ;;
    rocky|alma|centos)
      dnf install -y docker docker-compose-plugin 2>/dev/null \
        || yum install -y docker docker-compose-plugin 2>/dev/null || true
      ;;
    *) abort "cannot auto-install Docker on unsupported OS '${OS_ID}'" ;;
  esac
}

check_compose() {
  COMPOSE_CMD=()
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
  else
    log_warn "Docker Compose v2 plugin not found; installing..."
    install_compose_plugin
    COMPOSE_CMD=(docker compose)
  fi
  "${COMPOSE_CMD[@]}" version >/dev/null 2>&1 || abort "Docker Compose is not usable"
  log_ok "Compose: $("${COMPOSE_CMD[@]}" version | head -n 1)"
}

install_compose_plugin() {
  if [[ "${PLATFORM}" != "linux" ]]; then
    abort "Docker Compose plugin not found; Docker Desktop includes it — update Docker Desktop or install Compose manually"
  fi
  case "${OS_ID}" in
    ubuntu|debian)
      apt-get update -y >/dev/null
      apt-get install -y docker-compose-v2 2>/dev/null || apt-get install -y docker-compose-plugin
      ;;
    rocky|alma|centos)
      dnf install -y docker-compose-plugin 2>/dev/null || yum install -y docker-compose-plugin
      ;;
    *) abort "unsupported OS for Compose plugin installation: ${OS_ID}" ;;
  esac
}

# ---------------------------------------------------------------------------
# §4 Interactive configuration
# ---------------------------------------------------------------------------
configure() {
  if [[ "${INSTALL_DIR_OVERRIDE}" != "1" && "${ASSUME_YES}" != "1" && -t 0 ]]; then
    prompt_value INSTALL_DIR "Install directory" "${INSTALL_DIR}"
  fi
  INSTALL_DIR="${INSTALL_DIR%/}"
  [[ -z "${DATA_DIR}" ]] && DATA_DIR="${INSTALL_DIR}"
  DATA_DIR="${DATA_DIR%/}"

  if [[ -z "${DOMAIN}" ]]; then
    if [[ "${PLATFORM}" == "macos" ]]; then
      DOMAIN="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
    elif [[ "${PLATFORM}" == "windows" ]]; then
      DOMAIN="$(ipconfig 2>/dev/null | awk '/IPv4/ {print $NF; exit}' || true)"
    else
      DOMAIN="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
    fi
    [[ -z "${DOMAIN}" ]] && DOMAIN="$(hostname -f 2>/dev/null || hostname)"
    [[ -z "${DOMAIN}" ]] && DOMAIN="127.0.0.1"
  fi
  [[ "${DOMAIN}" =~ ^[A-Za-z0-9._:-]+$ ]] || abort "invalid domain/host: ${DOMAIN}"

  if [[ -z "${TIMEZONE}" ]]; then
    if [[ "${PLATFORM}" == "macos" ]]; then
      TIMEZONE="$(readlink /etc/localtime 2>/dev/null | sed 's|.*/zoneinfo/||')"
    else
      TIMEZONE="$(cat /etc/timezone 2>/dev/null || true)"
    fi
    [[ -z "${TIMEZONE}" ]] && TIMEZONE="UTC"
  fi
  if [[ -z "${ADMIN_EMAIL}" ]]; then ADMIN_EMAIL="admin@${DOMAIN}"; fi
  if [[ -z "${EMAIL_DOMAIN}" ]]; then EMAIL_DOMAIN="devify.local"; fi

  if [[ "${HTTPS}" == "true" ]]; then SCHEME="https"; else SCHEME="http"; fi

  if [[ "${ADVANCED}" == "1" && "${ASSUME_YES}" != "1" && -t 0 ]]; then
    if confirm "Enable HTTPS configuration (requires a TLS-terminating reverse proxy)?"; then HTTPS="true"; SCHEME="https"; fi
    prompt_value TIMEZONE "Timezone" "${TIMEZONE}"
    prompt_value EMAIL_DOMAIN "Inbound email domain" "${EMAIL_DOMAIN}"
    prompt_value DATA_DIR "Data directory" "${DATA_DIR}"
  fi
}

# ---------------------------------------------------------------------------
# §2/§4/§19 Port conflict detection
# ---------------------------------------------------------------------------
port_in_use() {
  local port="$1"
  case "${PLATFORM}" in
    macos)
      if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
        return $?
      fi
      ;;
    windows)
      netstat -ano 2>/dev/null | awk -v p=":${port}$" '$1 ~ /^TCP/ && $4 == "LISTENING" && $2 ~ p { found=1 } END { exit !found }'
      return $?
      ;;
  esac
  if command -v ss >/dev/null 2>&1; then
    ss -ltnH 2>/dev/null | awk -v p=":${port}$" '$4 ~ p { found=1 } END { exit !found }'
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | awk -v p=":${port}$" '$4 ~ p { found=1 } END { exit !found }'
  else
    return 1
  fi
}

next_free_port() {
  local port="$1"
  while port_in_use "${port}"; do port=$((port + 1)); done
  printf '%s' "${port}"
}

validate_port() {
  [[ "$1" =~ ^[0-9]+$ ]] && ((10#$1 >= 1 && 10#$1 <= 65535))
}

resolve_ports() {
  [[ -n "${HTTP_PORT}" ]] || HTTP_PORT="${DEFAULT_HTTP_PORT}"
  [[ -n "${ADMIN_PORT}" ]] || ADMIN_PORT="${DEFAULT_ADMIN_PORT}"
  [[ -n "${SMTP_PORT}" ]] || SMTP_PORT="${DEFAULT_SMTP_PORT}"

  validate_port "${HTTP_PORT}" || abort "invalid HTTP port: ${HTTP_PORT}"
  if port_in_use "${HTTP_PORT}"; then
    if [[ "${ASSUME_YES}" != "1" && -t 0 ]]; then
      while port_in_use "${HTTP_PORT}"; do
        prompt_value HTTP_PORT "Port ${HTTP_PORT} is in use; enter a free port" "$((HTTP_PORT + 1))"
        validate_port "${HTTP_PORT}" || HTTP_PORT="$((HTTP_PORT + 1))"
      done
    else
      local alt
      alt="$(next_free_port "$((HTTP_PORT + 1))")"
      log_warn "port ${HTTP_PORT} is in use; using ${alt} instead"
      HTTP_PORT="${alt}"
    fi
  fi

  if port_in_use "${HTTPS_PORT}"; then
    HTTPS_PORT="$(next_free_port "$((HTTPS_PORT + 1))")"
    log_warn "HTTPS port in use; using ${HTTPS_PORT} instead"
  fi
  if port_in_use "${ADMIN_PORT}"; then
    ADMIN_PORT="$(next_free_port "$((ADMIN_PORT + 1))")"
    log_warn "admin port in use; using ${ADMIN_PORT} instead"
  fi
  if port_in_use "${SMTP_PORT}"; then
    SMTP_PORT="$(next_free_port "$((SMTP_PORT + 1))")"
    log_warn "SMTP port in use; using ${SMTP_PORT} instead"
  fi

  PORT_SUFFIX=""
  if [[ "${SCHEME}" == "https" ]]; then
    [[ "${HTTP_PORT}" != "443" ]] && PORT_SUFFIX=":${HTTP_PORT}"
  else
    [[ "${HTTP_PORT}" != "80" ]] && PORT_SUFFIX=":${HTTP_PORT}"
  fi
  log_info "Ports: HTTP=${HTTP_PORT} HTTPS=${HTTPS_PORT} Admin=${ADMIN_PORT} SMTP=${SMTP_PORT}"
}

# ---------------------------------------------------------------------------
# §7/§19 Existing installation detection
# ---------------------------------------------------------------------------
detect_existing() {
  EXISTING=0; INSTALLED_VERSION=""
  [[ -f "${INSTALL_DIR}/docker-compose.yml" ]] || return 0
  EXISTING=1
  log_warn "Existing installation detected at ${INSTALL_DIR}"
  if [[ -f "${INSTALL_DIR}/install-info.env" ]]; then
    INSTALLED_VERSION="$(grep -E '^DEVIFY_VERSION=' "${INSTALL_DIR}/install-info.env" | tail -n1 | cut -d= -f2- || true)"
    [[ -n "${INSTALLED_VERSION}" ]] && log_info "Installed version: ${INSTALLED_VERSION}"
    [[ "${HTTP_PORT_OVERRIDE}" == "0" ]] && HTTP_PORT="$(grep -E '^DEVIFY_HTTP_PORT=' "${INSTALL_DIR}/install-info.env" | tail -n1 | cut -d= -f2- || true)"
    [[ "${ADMIN_PORT_OVERRIDE}" == "0" ]] && ADMIN_PORT="$(grep -E '^DEVIFY_ADMIN_PORT=' "${INSTALL_DIR}/install-info.env" | tail -n1 | cut -d= -f2- || true)"
    [[ "${SMTP_PORT_OVERRIDE}" == "0" ]] && SMTP_PORT="$(grep -E '^DEVIFY_SMTP_PORT=' "${INSTALL_DIR}/install-info.env" | tail -n1 | cut -d= -f2- || true)"
    [[ "${DOMAIN_OVERRIDE}" == "0" ]] && DOMAIN="$(grep -E '^DEVIFY_DOMAIN=' "${INSTALL_DIR}/install-info.env" | tail -n1 | cut -d= -f2- || true)"
    [[ "${DOMAIN_OVERRIDE}" == "0" && -n "${DOMAIN}" ]] && DOMAIN_OVERRIDE=1
  fi
}

# ---------------------------------------------------------------------------
# §8 Release version resolution & artifact download
# ---------------------------------------------------------------------------
resolve_version() {
  if [[ -z "${VERSION}" ]]; then
    if [[ "${EXISTING}" == "1" && -n "${INSTALLED_VERSION}" ]]; then
      VERSION="${INSTALLED_VERSION#v}"
      log_info "Reusing installed version v${VERSION} (rerun)"
    else
      log_info "Resolving latest release version..."
      local api=""
      api="$(curl -fsSL --max-time 20 "${GITHUB_API}/releases/latest" 2>/dev/null \
        | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1 || true)"
      if [[ -z "${api}" && "${CHANNEL}" == "cn" && -n "${CN_DOWNLOAD_BASE}" ]]; then
        api="$(curl -fsSL --max-time 20 "${CN_DOWNLOAD_BASE}/latest" 2>/dev/null | tr -d '[:space:]' | head -c 64 || true)"
      fi
      [[ -z "${api}" ]] && abort "could not resolve the latest release version (no GitHub release / CN base configured); pass --version explicitly"
      VERSION="${api#v}"
      log_info "Latest release: v${VERSION}"
    fi
  fi
  VERSION="${VERSION#v}"
  TAG="v${VERSION}"
  IMAGE_TAG="${VERSION}"
  if [[ "${INSTALLER_VERSION}" != "${VERSION}" ]]; then
    log_warn "installer v${INSTALLER_VERSION} is installing release v${VERSION}"
  fi
}

artifact_url() {
  if [[ "${CHANNEL}" == "cn" && -n "${CN_DOWNLOAD_BASE}" ]]; then
    printf '%s/devify-%s.tar.gz' "${CN_DOWNLOAD_BASE%/}" "${VERSION}"
  else
    if [[ "${CHANNEL}" == "cn" ]]; then
      log_warn "CN distribution base not configured (set --cn-base or DEVIFY_CN_DOWNLOAD_BASE); falling back to GitHub Releases"
    fi
    printf 'https://github.com/%s/releases/download/%s/devify-%s.tar.gz' "${GITHUB_REPO}" "${TAG}" "${VERSION}"
  fi
}

download_artifact() {
  log_step "Downloading release artifact"
  TMP_DIR="$(mktemp -d)"
  mkdir -p "${TMP_DIR}/extract"
  local url="" expected="" actual=""
  url="$(artifact_url)"
  log_info "Downloading ${url}"
  curl -fL --retry 3 --retry-delay 2 --max-time 300 -o "${TMP_DIR}/artifact.tar.gz" "${url}" \
    || abort "failed to download release artifact; check the version/channel and network"

  if curl -fsSL --max-time 20 -o "${TMP_DIR}/artifact.sha256" "${url}.sha256" >/dev/null 2>&1; then
    expected="$(awk '{print $1}' "${TMP_DIR}/artifact.sha256" | tr -d '[:space:]' || true)"
    if command -v sha256sum >/dev/null 2>&1; then
      actual="$(sha256sum "${TMP_DIR}/artifact.tar.gz" | awk '{print $1}')"
    else
      actual="$(shasum -a 256 "${TMP_DIR}/artifact.tar.gz" | awk '{print $1}')"
    fi
    [[ -n "${expected}" && "${expected}" == "${actual}" ]] \
      || abort "release artifact checksum verification failed"
    log_ok "Checksum verified"
  else
    log_warn "no checksum file available; skipping verification"
  fi

  tar -xzf "${TMP_DIR}/artifact.tar.gz" -C "${TMP_DIR}/extract" \
    || abort "failed to extract release artifact"

  local artifact_version=""
  artifact_version="$(cat "${TMP_DIR}/extract/VERSION" 2>/dev/null | tr -d '[:space:]' || true)"
  if [[ -z "${artifact_version}" ]]; then
    abort "release artifact is missing the VERSION file; artifact layout is invalid"
  fi
  if [[ "${artifact_version#v}" != "${VERSION}" ]]; then
    abort "release artifact version mismatch: requested ${TAG}, artifact contains ${artifact_version} (installer and release version must stay consistent)"
  fi
  log_ok "Artifact v${VERSION} downloaded and verified"
}

install_artifact_files() {
  log_step "Installing release files"
  cp -f "${TMP_DIR}/extract/docker-compose.yml" "${INSTALL_DIR}/docker-compose.yml"
  [[ -f "${TMP_DIR}/extract/env.sample" ]] && cp -f "${TMP_DIR}/extract/env.sample" "${INSTALL_DIR}/env.sample"
  if [[ -d "${TMP_DIR}/extract/docker" ]]; then
    # tar-pipe copy preserves files already present in the target (e.g. user certs)
    (cd "${TMP_DIR}/extract" && tar -cf - docker 2>/dev/null) | (cd "${INSTALL_DIR}" && tar -xf -)
  fi
  find "${INSTALL_DIR}/docker/nginx/certs" -type f ! -name '*.crt' ! -name '*.key' -delete 2>/dev/null || true
  chmod 600 "${INSTALL_DIR}/docker/nginx/certs"/* 2>/dev/null || true
  log_ok "Release files installed"
}

# ---------------------------------------------------------------------------
# §5/§6 Configuration generation (secrets are never prompted for)
# ---------------------------------------------------------------------------
gen_secret()   { openssl rand -base64 48 | tr -d '\n'; }
gen_password() { openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20; }

ensure_env_key() {
  local file="$1" key="$2" value="$3"
  if ! grep -qE "^${key}=" "${file}"; then
    printf '%s=%s\n' "${key}" "${value}" >>"${file}"
    log_info "Added missing ${key} to .env"
  fi
}

generate_env() {
  log_step "Generating configuration"
  local env_file="${INSTALL_DIR}/.env"
  if [[ -f "${env_file}" ]]; then
    ENV_EXISTS=1
    log_warn ".env exists — preserving it (the installer never overwrites .env)"
    ensure_env_key "${env_file}" "REDIS_PASSWORD" "$(gen_password)"
    ensure_env_key "${env_file}" "JWT_SECRET" "$(gen_secret)"
    ensure_env_key "${env_file}" "TZ" "${TIMEZONE}"
    ENV_REDIS_PASSWORD="$(grep -E '^REDIS_PASSWORD=' "${env_file}" | tail -n1 | cut -d= -f2- | tr -d "'" || true)"
    ADMIN_PASSWORD="$(grep -E '^DJANGO_SUPERUSER_PASSWORD=' "${env_file}" | tail -n1 | cut -d= -f2- | tr -d "'" || true)"
    [[ -z "${ENV_REDIS_PASSWORD}" ]] && abort ".env exists but REDIS_PASSWORD could not be read"
    EMAIL_DOMAIN="$(grep -E '^AUTO_ASSIGN_EMAIL_DOMAIN=' "${env_file}" | tail -n1 | cut -d= -f2- | tr -d "'" || true)"
    [[ -z "${EMAIL_DOMAIN}" ]] && EMAIL_DOMAIN="devify.local"
    return 0
  fi

  local secret_key jwt_secret db_password root_password redis_password admin_password
  secret_key="$(gen_secret)"
  jwt_secret="$(gen_secret)"
  db_password="$(gen_password)"
  root_password="$(gen_password)"
  redis_password="$(gen_password)"
  admin_password="$(gen_password)"
  ADMIN_PASSWORD="${admin_password}"
  ENV_REDIS_PASSWORD="${redis_password}"

  cat >"${env_file}" <<EOF
# ============================================================================
# Devify runtime configuration — generated by install.sh v${INSTALLER_VERSION}
# on $(date -u '+%Y-%m-%d %H:%M:%S UTC'). Do not commit this file.
# ============================================================================

# --- Core ---
SECRET_KEY='${secret_key}'
JWT_SECRET='${jwt_secret}'
DJANGO_DEBUG=false
ALLOWED_HOSTS=${DOMAIN},localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS='${SCHEME}://${DOMAIN}${PORT_SUFFIX}'
CORS_ALLOW_ALL_ORIGINS=false
CORS_ALLOWED_ORIGINS='${SCHEME}://${DOMAIN}${PORT_SUFFIX}'
DJANGO_LOG_LEVEL=INFO
DJANGO_SUPERUSER_USERNAME=${ADMIN_USERNAME}
DJANGO_SUPERUSER_EMAIL=${ADMIN_EMAIL}
DJANGO_SUPERUSER_PASSWORD='${admin_password}'

# --- Ports ---
NGINX_HTTP_PORT=${HTTP_PORT}
NGINX_HTTPS_PORT=${HTTPS_PORT}
NGINX_ADMIN_PORT=${ADMIN_PORT}
ATTACHMENT_BASE_URL=${SCHEME}://${DOMAIN}${PORT_SUFFIX}
SITE_DOMAIN=${DOMAIN}${PORT_SUFFIX}
SITE_NAME=${APP_TITLE}
FRONTEND_URL=${SCHEME}://${DOMAIN}${PORT_SUFFIX}
VITE_API_BASE_URL=${SCHEME}://${DOMAIN}${PORT_SUFFIX}
ACCOUNT_DEFAULT_HTTP_PROTOCOL=${SCHEME}

# --- Database (MariaDB/MySQL) ---
DB_ENGINE=mysql
MYSQL_USER=${APP_NAME}
MYSQL_PASSWORD='${db_password}'
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=${APP_NAME}
MYSQL_ROOT_PASSWORD='${root_password}'

# --- Redis / Celery ---
REDIS_PASSWORD='${redis_password}'
CELERY_BROKER_URL=redis://:${redis_password}@redis:6379/0
CELERY_RESULT_BACKEND=redis://:${redis_password}@redis:6379/0
CELERY_LOG_LEVEL=INFO
CELERY_CONCURRENCY=1
CELERY_MAX_TASKS_PER_CHILD=1000
CELERY_MAX_MEMORY_PER_CHILD=256000
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CACHE_BACKEND=redis

# --- Email ---
EMAIL_ATTACHMENT_DIR=/opt/email_attachments
AUTO_ASSIGN_EMAIL_DOMAIN=${EMAIL_DOMAIN}
HARAKA_EMAIL_BASE_DIR=/opt/haraka/emails
HARAKA_SMTP_PORT=${SMTP_PORT}
DEFAULT_LANGUAGE=en-US
DEFAULT_SCENE=chat
THREADLINE_CONFIG_PATH=/opt/devify/conf/threadline

# SMTP is intentionally left on the console backend; configure real SMTP
# credentials here before relying on outbound notifications.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=noreply@${EMAIL_DOMAIN}

# --- Container ---
TZ=${TIMEZONE}
EOF
  chmod 600 "${env_file}"
  log_ok ".env generated with random secrets (chmod 600)"
}

# ---------------------------------------------------------------------------
# Compose / nginx / haraka patching per channel & install parameters
# ---------------------------------------------------------------------------
sed_inplace() {
  local file="$1"; shift
  sed -i.bak "$@" "${file}" && rm -f "${file}.bak"
}

patch_compose() {
  log_step "Patching compose files (channel: ${CHANNEL})"
  local compose="${INSTALL_DIR}/docker-compose.yml"
  local nginx_conf="${INSTALL_DIR}/docker/nginx/default.conf"
  local haraka_ini="${INSTALL_DIR}/docker/haraka/config/redis.ini"
  local host_list="${INSTALL_DIR}/docker/haraka/config/host_list.prod"

  # registry: cn ACR image refs -> channel registry
  sed_inplace "${compose}" -E "s|(image:[[:space:]]*)registry\.cn-beijing\.aliyuncs\.com/cloud2ai|\1${REGISTRY}|g"
  # pin version-consistent image tags
  sed_inplace "${compose}" -E "s|(image:[[:space:]]*[^ ]+/${APP_NAME}(-ui)?):latest|\1:${IMAGE_TAG}|g"
  # redis authentication
  sed_inplace "${compose}" 's|command: redis-server|command: redis-server --requirepass ${REDIS_PASSWORD}|'
  sed_inplace "${compose}" 's|"redis-cli", "ping"|"redis-cli", "-a", "${REDIS_PASSWORD}", "ping"|'

  if [[ -f "${nginx_conf}" ]]; then
    sed_inplace "${nginx_conf}" "s|server_name app\.aimychats\.com;|server_name ${DOMAIN};|g"
    sed_inplace "${nginx_conf}" "s|app\.aimychats\.com\.crt|devify.crt|g; s|app\.aimychats\.com\.key|devify.key|g"
  fi
  if [[ -f "${haraka_ini}" ]]; then
    sed_inplace "${haraka_ini}" "s|^# password=.*|password=${ENV_REDIS_PASSWORD}|"
  fi
  if [[ -f "${host_list}" && -n "${EMAIL_DOMAIN}" && "${EMAIL_DOMAIN}" != "devify.local" ]]; then
    sed_inplace "${host_list}" "s|^aimychats\.com$|${EMAIL_DOMAIN}|"
  fi
  log_ok "Compose files patched"
}

# ---------------------------------------------------------------------------
# TLS certificates (self-signed for the admin panel / haraka STARTTLS)
# ---------------------------------------------------------------------------
generate_certs() {
  log_step "Ensuring TLS certificates"
  local certs_dir="${INSTALL_DIR}/docker/nginx/certs"
  mkdir -p "${certs_dir}" "${DATA_DIR}/data/certs/haraka"

  if [[ ! -f "${certs_dir}/devify.crt" || ! -f "${certs_dir}/devify.key" ]]; then
    log_info "Generating self-signed certificate for ${DOMAIN} (replace with a real certificate for production)"
    openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
      -keyout "${certs_dir}/devify.key" -out "${certs_dir}/devify.crt" \
      -subj "/CN=${DOMAIN}" -addext "subjectAltName=DNS:${DOMAIN},IP:${DOMAIN}" 2>/dev/null \
      || openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
           -keyout "${certs_dir}/devify.key" -out "${certs_dir}/devify.crt" \
           -subj "/CN=${DOMAIN}"
    chmod 600 "${certs_dir}/devify.key"
  fi

  if [[ ! -f "${DATA_DIR}/data/certs/haraka/cert.pem" || ! -f "${DATA_DIR}/data/certs/haraka/key.pem" ]]; then
    openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
      -keyout "${DATA_DIR}/data/certs/haraka/key.pem" -out "${DATA_DIR}/data/certs/haraka/cert.pem" \
      -subj "/CN=haraka" -addext "subjectAltName=DNS:haraka" 2>/dev/null \
      || openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
           -keyout "${DATA_DIR}/data/certs/haraka/key.pem" -out "${DATA_DIR}/data/certs/haraka/cert.pem" \
           -subj "/CN=haraka"
    chmod 600 "${DATA_DIR}/data/certs/haraka/key.pem"
  fi
  log_ok "TLS certificates ready"
}

# ---------------------------------------------------------------------------
# §5 Directory layout
# ---------------------------------------------------------------------------
create_dirs() {
  log_step "Creating directories"
  mkdir -p "${INSTALL_DIR}"/{config,data,logs,backup,scripts}
  mkdir -p "${DATA_DIR}"/{cache,data}
  mkdir -p "${DATA_DIR}"/data/{django/staticfiles,mysql/data,redis,email_attachments}
  mkdir -p "${DATA_DIR}"/data/logs/{api,worker,scheduler,mysql,redis,nginx,haraka}
  mkdir -p "${DATA_DIR}"/data/haraka/{emails,email_attachments,debug,logs}
  mkdir -p "${DATA_DIR}"/data/certs/haraka
  mkdir -p "${INSTALL_DIR}/docker/nginx/certs"
  printf '%s\n' "# Reserved for user-managed configuration" >"${INSTALL_DIR}/config/README.md"
  log_ok "Directories created under ${INSTALL_DIR} (data: ${DATA_DIR})"
}

# ---------------------------------------------------------------------------
# Docker Compose lifecycle
# ---------------------------------------------------------------------------
run_compose() {
  export DEVIFY_ENV_FILE="${INSTALL_DIR}/.env"
  export DEVIFY_RUNTIME_ROOT="${DATA_DIR}"
  export DEVIFY_NGINX_CERTS_DIR="${INSTALL_DIR}/docker/nginx/certs"
  local project_dir="${INSTALL_DIR}"
  if [[ "${PLATFORM}" == "windows" ]] && command -v cygpath >/dev/null 2>&1; then
    # Git Bash passes MSYS paths; the native Docker CLI needs Windows paths.
    project_dir="$(cygpath -w "${INSTALL_DIR}")"
    DEVIFY_ENV_FILE="$(cygpath -w "${DEVIFY_ENV_FILE}")"
    DEVIFY_RUNTIME_ROOT="$(cygpath -w "${DEVIFY_RUNTIME_ROOT}")"
    DEVIFY_NGINX_CERTS_DIR="$(cygpath -w "${DEVIFY_NGINX_CERTS_DIR}")"
  fi
  "${COMPOSE_CMD[@]}" --project-directory "${project_dir}" -f "${project_dir}/docker-compose.yml" "$@" \
    2>&1 | tee -a "${LOG_FILE}"
}

pull_images() {
  log_step "Pulling container images (registry: ${REGISTRY})"
  run_compose config --quiet || abort "invalid docker-compose configuration; see ${LOG_FILE}"
  local attempt=1 max_attempts=3
  until run_compose pull; do
    if ((attempt >= max_attempts)); then
      abort "docker compose pull failed after ${max_attempts} attempts; check network access to the registry (see ${LOG_FILE})"
    fi
    log_warn "docker compose pull failed (attempt ${attempt}/${max_attempts}); retrying in 10s"
    sleep 10
    attempt=$((attempt + 1))
  done
  log_ok "Images pulled"
}

start_stack() {
  log_step "Starting Docker Compose stack"
  local attempt=1 max_attempts=6
  until run_compose up -d --no-build --remove-orphans; do
    if ((attempt >= max_attempts)); then
      log_error "docker compose up failed after ${max_attempts} attempts"
      log_error "container status:"
      run_compose ps || true
      log_error "recent container logs:"
      run_compose logs --tail=100 --no-color || true
      abort "docker compose up failed; see ${LOG_FILE} and the container logs above"
    fi
    log_warn "docker compose up failed (attempt ${attempt}/${max_attempts}); retrying in 30s (dependencies may still be converging)"
    sleep 30
    attempt=$((attempt + 1))
  done
  log_ok "Stack started"
}

# ---------------------------------------------------------------------------
# §11 Health check
# ---------------------------------------------------------------------------
health_check() {
  log_step "Waiting for health endpoint (timeout: ${HEALTH_TIMEOUT}s)"
  local deadline=$((SECONDS + HEALTH_TIMEOUT))
  local url="http://127.0.0.1:${HTTP_PORT}/health"
  until curl -fsS --max-time 5 "${url}" >/dev/null 2>&1; do
    if ((SECONDS >= deadline)); then
      log_error "health check timed out after ${HEALTH_TIMEOUT}s"
      log_error "container status:"
      run_compose ps || true
      log_error "recent container logs:"
      run_compose logs --tail=100 --no-color || true
      abort "health check failed — see ${LOG_FILE} and the container logs above"
    fi
    sleep 5
  done
  log_ok "Health check passed: ${url}"
}

# ---------------------------------------------------------------------------
# §7/§13 Installation metadata & summary
# ---------------------------------------------------------------------------
write_install_info() {
  local info="${INSTALL_DIR}/install-info.env"
  {
    printf '# Devify installation metadata — generated by install.sh v%s\n' "${INSTALLER_VERSION}"
    printf 'DEVIFY_VERSION=%s\n' "${VERSION}"
    printf 'DEVIFY_INSTALL_TIME=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf 'DEVIFY_INSTALL_CHANNEL=%s\n' "${CHANNEL}"
    printf 'DEVIFY_INSTALL_DIR=%s\n' "${INSTALL_DIR}"
    printf 'DEVIFY_DATA_DIR=%s\n' "${DATA_DIR}"
    printf 'DEVIFY_URL=%s\n' "${SCHEME}://${DOMAIN}${PORT_SUFFIX}"
    printf 'DEVIFY_USERNAME=%s\n' "${ADMIN_USERNAME}"
    printf 'DEVIFY_INITIAL_PASSWORD=%s\n' "${ADMIN_PASSWORD}"
    printf 'DEVIFY_REGISTRY=%s\n' "${REGISTRY}"
    printf 'DEVIFY_HTTP_PORT=%s\n' "${HTTP_PORT}"
    printf 'DEVIFY_HTTPS_PORT=%s\n' "${HTTPS_PORT}"
    printf 'DEVIFY_ADMIN_PORT=%s\n' "${ADMIN_PORT}"
    printf 'DEVIFY_SMTP_PORT=%s\n' "${SMTP_PORT}"
    printf 'DEVIFY_TIMEZONE=%s\n' "${TIMEZONE}"
    printf 'DEVIFY_DOMAIN=%s\n' "${DOMAIN}"
    printf 'DEVIFY_HTTPS=%s\n' "${HTTPS}"
    printf 'DEVIFY_INSTALLER_VERSION=%s\n' "${INSTALLER_VERSION}"
  } >"${info}"
  chmod 600 "${info}"
  log_ok "Installation metadata saved (${info}, chmod 600)"
}

show_summary() {
  log_step "Installation summary"
  log_info "  Platform:     ${OS_NAME} (${PLATFORM})"
  log_info "  Version:      v${VERSION}"
  log_info "  Channel:      ${CHANNEL} (registry: ${REGISTRY})"
  log_info "  Install dir:  ${INSTALL_DIR}"
  log_info "  Data dir:     ${DATA_DIR}"
  log_info "  URL:          ${SCHEME}://${DOMAIN}${PORT_SUFFIX}"
  log_info "  HTTP port:    ${HTTP_PORT}"
  if [[ "${EXISTING}" == "1" ]]; then
    log_info "  Mode:         rerun/upgrade (existing installation, .env preserved)"
  fi
}

final_summary() {
  log_step "Installation complete"
  log_ok "Devify v${VERSION} installed at ${INSTALL_DIR}"
  log_info "URL:              ${SCHEME}://${DOMAIN}${PORT_SUFFIX}"
  log_info "Admin panel:      https://${DOMAIN}:${ADMIN_PORT}/devify-admin (self-signed certificate)"
  log_info "Username:         ${ADMIN_USERNAME}"
  log_info "Initial password: ${ADMIN_PASSWORD}"
  log_info "Install dir:      ${INSTALL_DIR}"
  log_info "Data dir:         ${DATA_DIR}"
  log_info "Config file:      ${INSTALL_DIR}/.env"
  log_info "Install info:     ${INSTALL_DIR}/install-info.env"
  log_info "Install log:      ${LOG_FILE}"
  log_warn "SMTP is not configured (console backend); edit ${INSTALL_DIR}/.env to enable outbound notifications"
  if [[ "${HTTPS}" != "true" ]]; then
    log_warn "HTTPS is not enabled; put a TLS-terminating reverse proxy in front for production"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  local arg=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help) usage; exit 0 ;;
      -d|--dir) INSTALL_DIR="${2:?--dir requires an argument}"; INSTALL_DIR_OVERRIDE=1; shift 2 ;;
      -p|--port) HTTP_PORT="${2:?--port requires an argument}"; HTTP_PORT_OVERRIDE=1; shift 2 ;;
      -c|--channel) CHANNEL="$2"; shift 2 ;;
      -v|--version) VERSION="$2"; shift 2 ;;
      -r|--registry) REGISTRY="$2"; shift 2 ;;
      --domain) DOMAIN="$2"; DOMAIN_OVERRIDE=1; shift 2 ;;
      --data-dir) DATA_DIR="$2"; shift 2 ;;
      --timezone) TIMEZONE="$2"; shift 2 ;;
      --admin-port) ADMIN_PORT="$2"; ADMIN_PORT_OVERRIDE=1; shift 2 ;;
      --smtp-port) SMTP_PORT="$2"; SMTP_PORT_OVERRIDE=1; shift 2 ;;
      --admin-user) ADMIN_USERNAME="$2"; shift 2 ;;
      --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
      --email-domain) EMAIL_DOMAIN="$2"; shift 2 ;;
      --https) HTTPS="true"; shift ;;
      --cn-base) CN_DOWNLOAD_BASE="$2"; shift 2 ;;
      --install-docker) INSTALL_DOCKER=1; shift ;;
      --docker-mirror) DOCKER_MIRROR="$2"; shift 2 ;;
      --advanced) ADVANCED=1; shift ;;
      -y|--yes) ASSUME_YES=1; shift ;;
      --force) FORCE=1; shift ;;
      --) shift; break ;;
      *) log_error "unknown option: $1"; usage; exit 1 ;;
    esac
  done

  trap 'log_line "=== install failed at line ${LINENO} (exit $?) ==="' ERR
  trap '[[ -n "${TMP_DIR}" ]] && rm -rf "${TMP_DIR}"' EXIT

  # §2 Preflight
  require_root "$@"

  mkdir -p "${INSTALL_DIR}/logs"
  LOG_FILE="${INSTALL_DIR}/logs/install.log"
  log_line "=== install.sh v${INSTALLER_VERSION} started ($(date -u '+%Y-%m-%dT%H:%M:%SZ')) ==="
  log_line "argv: $*"

  detect_os
  detect_arch
  check_memory
  check_disk
  check_tools

  # §7 existing installation
  detect_existing

  # §2/§9 channel + network + docker
  detect_channel
  check_network
  check_docker
  check_compose

  # §4 interactive configuration + §3 confirmation
  configure
  resolve_version
  resolve_ports
  show_summary
  if [[ "${EXISTING}" == "1" && -n "${INSTALLED_VERSION}" && "${INSTALLED_VERSION#v}" != "${VERSION}" && "${FORCE}" != "1" ]]; then
    log_warn "upgrade: installed v${INSTALLED_VERSION#v} -> v${VERSION}"
  fi
  confirm "Proceed?" || abort "installation cancelled"

  # §5/§6/§8/§9/§10
  create_dirs
  download_artifact
  install_artifact_files
  generate_env
  patch_compose
  generate_certs
  pull_images
  start_stack
  health_check
  write_install_info
  final_summary
}

if [[ "${BASH_SOURCE[0]:-}" == "$0" || -z "${BASH_SOURCE[0]:-}" ]]; then
  main "$@"
fi
