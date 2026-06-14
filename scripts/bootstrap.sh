#!/usr/bin/env bash
#
# Splunk Agent Mesh — one-command bootstrap.
#
# Installs the pre-built Splunk app from target/app.tgz, creates a Python
# venv for the backend sidecar, and starts uvicorn.
#
# Commands:
#   (default)  Install app + start uvicorn sidecar.
#   check      Run preflight only and exit.
#   stop       Stop anything a previous run started.
#
# Usage:
#   ./scripts/bootstrap.sh [check|stop] [--help]
set -euo pipefail

# ---- constants -------------------------------------------------------------
UVICORN_PORT=8765
SPLUNK_WEB_PORT=8000
SPLUNK_REST_URL="${SPLUNK_HOST:-https://localhost:8089}"
SPLUNK_APP_ID="splunk-agent-mesh"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$REPO_ROOT/.bootstrap"
VENV="$REPO_ROOT/server/.venv"
APP_TGZ="$REPO_ROOT/target/app.tgz"

# ---- output helpers --------------------------------------------------------
if [ -t 1 ]; then
    C_RESET="$(printf '\033[0m')"; C_RED="$(printf '\033[31m')"
    C_GRN="$(printf '\033[32m')"; C_YEL="$(printf '\033[33m')"; C_BLU="$(printf '\033[34m')"
else
    C_RESET=""; C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""
fi
info() { printf '%s\n' "${C_BLU}==>${C_RESET} $*"; }
ok()   { printf '%s\n' "  ${C_GRN}ok${C_RESET}   $*"; }
warn() { printf '%s\n' "  ${C_YEL}warn${C_RESET} $*"; }
fail() { printf '%s\n' "  ${C_RED}FAIL${C_RESET} $*"; }
die()  { fail "$1"; [ $# -ge 2 ] && printf '       %s\n' "→ $2"; exit 1; }

# ---- small utilities -------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

port_in_use() {
    if have lsof; then lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
    else nc -z localhost "$1" >/dev/null 2>&1; fi
}

http_code() {
    curl -sk -m 5 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

# ---- resolve SPLUNK_HOME ---------------------------------------------------
resolve_splunk_home() {
    if [ -n "${SPLUNK_HOME:-}" ]; then
        ok "SPLUNK_HOME=${SPLUNK_HOME} (from environment)"
        return
    fi
    if [ -t 0 ]; then
        printf '  %s?%s  SPLUNK_HOME is not set. Enter path [/opt/splunk]: ' "$C_YEL" "$C_RESET"
        read -r user_input
        SPLUNK_HOME="${user_input:-/opt/splunk}"
        export SPLUNK_HOME
    else
        die "SPLUNK_HOME is not set" "export SPLUNK_HOME=/path/to/splunk"
    fi
}

# ---- preflight -------------------------------------------------------------
preflight() {
    info "Preflight: tooling"
    have python3 || die "python3 not found" "Install Python >= 3.11"
    python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' \
        || die "python3 $(python3 -V) is too old" "Need Python >= 3.11"
    ok "$(python3 -V)"
    have curl || die "curl not found" "Install curl (used for health checks)"

    info "Preflight: Splunk"
    resolve_splunk_home
    [ -x "$SPLUNK_HOME/bin/splunk" ] \
        || die "Splunk not found at ${SPLUNK_HOME}" \
               "Install Splunk, or set SPLUNK_HOME to the correct path"
    ok "Splunk found at ${SPLUNK_HOME}"

    info "Preflight: app package"
    [ -f "$APP_TGZ" ] \
        || die "app.tgz not found at ${APP_TGZ}" \
               "Run 'yarn build' to generate it, or ensure target/app.tgz is present"
    ok "app.tgz found"

    info "Preflight: ports"
    if port_in_use "$UVICORN_PORT"; then
        die "port ${UVICORN_PORT} (uvicorn) is already in use" \
            "Stop the other process, or run: ./scripts/bootstrap.sh stop"
    fi
    ok "port ${UVICORN_PORT} free (uvicorn)"

    if [ -n "${SPLUNK_TOKEN:-}" ]; then
        warn "SPLUNK_TOKEN is set; it is intentionally NOT passed to the sidecar."
        warn "Searches use your delegated Splunk Web session."
    fi
}

# ---- install app -----------------------------------------------------------
install_app() {
    info "Installing Splunk app to ${SPLUNK_HOME}/etc/apps/${SPLUNK_APP_ID}…"
    tar xzf "$APP_TGZ" -C "$SPLUNK_HOME/etc/apps/" \
        || die "Failed to extract app.tgz" "Check permissions on ${SPLUNK_HOME}/etc/apps/"
    ok "app installed to ${SPLUNK_HOME}/etc/apps/${SPLUNK_APP_ID}"

    info "Restarting Splunk…"
    "$SPLUNK_HOME/bin/splunk" restart \
        || die "Splunk restart failed" "Try manually: ${SPLUNK_HOME}/bin/splunk restart"
    ok "Splunk restarted"
}

# ---- dependency setup ------------------------------------------------------
ensure_venv() {
    if [ ! -x "$VENV/bin/uvicorn" ]; then
        info "Creating Python venv + installing backend deps…"
        python3 -m venv "$VENV" || die "venv creation failed" "Check your Python install"
        "$VENV/bin/pip" install -q -r "$REPO_ROOT/server/requirements.txt" \
            || die "pip install failed" "Check server/requirements.txt and the output above"
    fi
    ok "backend venv ready ($VENV)"
}

# ---- process management ----------------------------------------------------
mkdir -p "$RUN_DIR"
CHILD_PIDS=()

cleanup() {
    trap - INT TERM EXIT
    info "Shutting down…"
    for pidfile in "$RUN_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        local pid; pid="$(cat "$pidfile" 2>/dev/null || true)"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile"
    done
    ok "stopped"
}

start_uvicorn() {
    info "Starting backend (uvicorn :${UVICORN_PORT})…"
    ( cd "$REPO_ROOT/server" && \
      env -u SPLUNK_TOKEN \
          AGENT_MESH_SETTINGS_STORE=dev \
          AGENT_MESH_CONF_SOURCE=file \
          "$VENV/bin/uvicorn" agent_mesh.app:app --port "$UVICORN_PORT" \
          >"$RUN_DIR/uvicorn.log" 2>&1 ) &
    echo $! >"$RUN_DIR/uvicorn.pid"
    CHILD_PIDS+=("$!")

    local url="http://localhost:${UVICORN_PORT}/api/v1/health"
    local i
    for i in $(seq 1 30); do
        if [ "$(http_code "$url")" = "200" ]; then
            ok "backend healthy ($url)"
            return 0
        fi
        sleep 1
    done
    fail "backend did not become healthy"
    printf '       --- last 20 lines of %s ---\n' "$RUN_DIR/uvicorn.log"
    tail -n 20 "$RUN_DIR/uvicorn.log" 2>/dev/null | sed 's/^/       /'
    die "uvicorn failed to start" "Inspect $RUN_DIR/uvicorn.log"
}

print_sample_data_hint() {
    cat <<EOF
  Load sample data (run once in Splunk Search, if not already loaded):
    | inputlookup endpoint_events.csv | collect index=endpoint
    | inputlookup dns_events.csv      | collect index=dns
    | inputlookup auth_events.csv     | collect index=auth
    | inputlookup proxy_events.csv    | collect index=proxy
    | inputlookup firewall_events.csv | collect index=firewall
EOF
}

block_until_interrupt() {
    cat <<EOF

${C_GRN}Ready.${C_RESET} $1

  Logs:     $RUN_DIR/uvicorn.log
  Stop:     press Ctrl-C  (or in another shell: ./scripts/bootstrap.sh stop)
  Re-run:   ./scripts/bootstrap.sh

EOF
    wait
}

# ---- commands --------------------------------------------------------------
confirm_proceed() {
    warn "This script will install the Splunk app and restart Splunk."
    if [ -t 0 ]; then
        printf '  %s?%s  Continue? [y/N]: ' "$C_YEL" "$C_RESET"
        read -r answer
        case "$answer" in
            [yY]) ;;
            *) info "Aborted."; exit 0 ;;
        esac
    else
        die "Non-interactive mode — pass confirmation via environment or run interactively"
    fi
}

prompt_api_key() {
    if [ -n "${AGENT_MESH_API_KEY:-}" ]; then
        ok "AGENT_MESH_API_KEY set (from environment)"
        return
    fi
    info "LLM configuration (Anthropic)"
    printf '  %s?%s  Enter your Anthropic API key (press Enter to skip): ' "$C_YEL" "$C_RESET"
    read -r api_key
    if [ -n "$api_key" ]; then
        export AGENT_MESH_API_KEY="$api_key"
        ok "AGENT_MESH_API_KEY set"
    else
        warn "No API key provided — live investigations will not be available."
    fi
}

cmd_start() {
    confirm_proceed
    preflight
    install_app
    print_sample_data_hint
    prompt_api_key
    ensure_venv
    trap cleanup INT TERM EXIT
    start_uvicorn
    block_until_interrupt "Open Splunk Web at ${C_BLU}http://localhost:${SPLUNK_WEB_PORT}/en-US/app/${SPLUNK_APP_ID}${C_RESET} → Investigations."
}

cmd_check() {
    preflight
    info "Preflight passed."
}

cmd_stop() {
    if ! ls "$RUN_DIR"/*.pid >/dev/null 2>&1; then
        info "Nothing to stop (no PID files in $RUN_DIR)."
        return 0
    fi
    cleanup
}

usage() {
    sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# ---- main ------------------------------------------------------------------
MODE="${1:-start}"
case "$MODE" in
    start)  cmd_start ;;
    check)  cmd_check ;;
    stop)   cmd_stop ;;
    -h|--help|help) usage ;;
    *) usage; die "unknown command: $MODE" "Use one of: start, check, stop" ;;
esac
