#!/usr/bin/env bash
#
# Splunk Agent Mesh — one-command bootstrap + preflight for judges (DEMO-002).
#
# Modes (see docs/DEMO_RUNTIME.md for the runtime decision):
#   demo  (default)  Tier 1: uvicorn + standalone UI, no Splunk, no LLM key.
#   full             Tier 2: existing Splunk + delegated search + live LLM.
#   check            Run preflight only and exit.
#   stop             Stop anything a previous run started.
#
# Usage:
#   ./scripts/bootstrap.sh [demo|full|check|stop] [--help]
#
# The script starts processes in the background, health-checks them, prints the
# URL to open, then blocks until Ctrl-C (which cleanly stops what it started).
set -euo pipefail

# ---- constants -------------------------------------------------------------
UVICORN_PORT=8765
UI_PORT=8080
SPLUNK_WEB_PORT=8000
SPLUNK_REST_URL="${SPLUNK_HOST:-https://localhost:8089}"
MIN_NODE_MAJOR=22
SPLUNK_APP_ID="${AGENT_MESH_SPLUNK_APP_ID:-splunk-agent-mesh}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$REPO_ROOT/.bootstrap"
VENV="$REPO_ROOT/server/.venv"

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
# die "<what went wrong>" "<how to fix it>"
die()  { fail "$1"; [ $# -ge 2 ] && printf '       %s\n' "→ $2"; exit 1; }

# ---- small utilities -------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

port_in_use() {  # 0 if something is LISTENing on $1
    if have lsof; then lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
    else nc -z localhost "$1" >/dev/null 2>&1; fi
}

http_code() {  # echo HTTP status (or 000 on connection failure)
    curl -sk -m 5 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

node_major() { node -v 2>/dev/null | sed 's/^v\([0-9][0-9]*\).*/\1/'; }

# ---- preflight -------------------------------------------------------------
preflight_common() {
    info "Preflight: tooling"
    have node  || die "node not found" "Install Node >= ${MIN_NODE_MAJOR}"
    [ "$(node_major)" -ge "$MIN_NODE_MAJOR" ] \
        || die "node $(node -v) is too old" "Need Node >= ${MIN_NODE_MAJOR}"
    ok "node $(node -v)"
    have yarn || die "yarn not found" "Install Yarn (npm i -g yarn)"
    ok "yarn $(yarn -v)"
    have python3 || die "python3 not found" "Install Python >= 3.11"
    python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' \
        || die "python3 $(python3 -V) is too old" "Need Python >= 3.11"
    ok "$(python3 -V)"
    have curl || die "curl not found" "Install curl (used for health checks)"

    info "Preflight: ports"
    if port_in_use "$UVICORN_PORT"; then
        die "port ${UVICORN_PORT} (uvicorn) is already in use" \
            "Stop the other process, or run: ./scripts/bootstrap.sh stop"
    fi
    ok "port ${UVICORN_PORT} free (uvicorn)"
}

preflight_demo() {
    if port_in_use "$UI_PORT"; then
        die "port ${UI_PORT} (demo UI) is already in use" \
            "Stop the other process, or run: ./scripts/bootstrap.sh stop"
    fi
    ok "port ${UI_PORT} free (demo UI)"
}

preflight_full() {
    info "Preflight: full-mode prerequisites"
    [ -n "${AGENT_MESH_API_KEY:-}" ] \
        || die "AGENT_MESH_API_KEY is not set" \
               "export AGENT_MESH_API_KEY=<your-llm-key> before running 'full'"
    ok "AGENT_MESH_API_KEY present"
    [ -n "${SPLUNK_HOME:-}" ] \
        || die "SPLUNK_HOME is not set (needed to link the app)" \
               "export SPLUNK_HOME=/path/to/your/splunk"
    ok "SPLUNK_HOME=${SPLUNK_HOME}"
    local code
    code="$(http_code "${SPLUNK_REST_URL}/services/server/info")"
    if [ "$code" = "000" ]; then
        die "Splunk REST not reachable at ${SPLUNK_REST_URL}" \
            "Start Splunk, or set SPLUNK_HOST=https://<host>:8089"
    fi
    ok "Splunk REST reachable at ${SPLUNK_REST_URL} (HTTP ${code})"
    if [ -n "${SPLUNK_TOKEN:-}" ]; then
        warn "SPLUNK_TOKEN is set; it is intentionally NOT used by the sidecar."
        warn "Searches use your delegated Splunk Web session. (See docs/DEMO_RUNTIME.md.)"
    fi
}

# ---- dependency setup ------------------------------------------------------
ensure_node_deps() {
    if [ ! -d "$REPO_ROOT/node_modules" ]; then
        info "Installing JS dependencies (yarn install)…"
        (cd "$REPO_ROOT" && yarn install) || die "yarn install failed" "Check the output above"
    fi
    ok "JS dependencies present"
}

ensure_venv() {
    if [ ! -x "$VENV/bin/uvicorn" ]; then
        info "Creating Python venv + installing backend deps…"
        python3 -m venv "$VENV" || die "venv creation failed" "Check your Python install"
        "$VENV/bin/pip" install -q -r "$REPO_ROOT/server/requirements.txt" \
            || die "pip install failed" "Check server/requirements.txt and the output above"
    fi
    ok "backend venv ready ($VENV)"
}

ensure_llm_sdk() {  # full mode: the active provider's SDK must be importable
    if ! "$VENV/bin/python" -c 'import anthropic' >/dev/null 2>&1; then
        info "Installing the Anthropic SDK for live LLM calls…"
        "$VENV/bin/pip" install -q anthropic \
            || die "anthropic install failed" "pip install anthropic into $VENV"
    fi
    ok "LLM SDK present (anthropic)"
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

start_uvicorn() {  # $1 = mode (demo|full)
    info "Starting backend (uvicorn :${UVICORN_PORT})…"
    # POC-safe modes + no SPLUNK_TOKEN coupling (AUTH-001 / docs/DEMO_RUNTIME.md).
    # In demo mode no LLM key is needed; in full mode AGENT_MESH_API_KEY is passed through.
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

demo_smoke() {
    info "Smoke check: deterministic demo run"
    local body
    body="$(curl -sk -m 15 -X POST "http://localhost:${UVICORN_PORT}/api/v1/investigations/run" \
        -H 'Content-Type: application/json' -d '{"description":"bootstrap smoke","demo":true}' 2>/dev/null || true)"
    if printf '%s' "$body" | grep -q '"agent_order"'; then
        ok "demo investigation returned events"
    else
        warn "demo smoke did not return the expected payload (UI demo button should still work)"
    fi
}

start_ui() {
    info "Starting standalone UI (:${UI_PORT})… first build can take ~30-60s"
    ( cd "$REPO_ROOT" && yarn workspace @splunk/agent-mesh-ui run start:demo \
        >"$RUN_DIR/ui.log" 2>&1 ) &
    echo $! >"$RUN_DIR/ui.pid"
    CHILD_PIDS+=("$!")
    local i
    for i in $(seq 1 120); do
        if port_in_use "$UI_PORT"; then
            ok "UI dev server listening (:${UI_PORT})"
            return 0
        fi
        sleep 1
    done
    fail "UI dev server did not come up"
    tail -n 20 "$RUN_DIR/ui.log" 2>/dev/null | sed 's/^/       /'
    die "standalone UI failed to start" "Inspect $RUN_DIR/ui.log"
}

link_app() {
    info "Building + linking the Splunk app…"
    (cd "$REPO_ROOT" && yarn build) || die "yarn build failed" "Check the output above"
    (cd "$REPO_ROOT" && yarn workspace @splunk/agent-mesh run link:app) \
        || die "app link failed" "Ensure SPLUNK_HOME is writable"
    ok "app built and linked into \$SPLUNK_HOME/etc/apps"
    warn "Restart Splunk so it loads the app + agent_mesh_bridge REST endpoint."
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

block_until_interrupt() {  # $1 = human URL line
    cat <<EOF

${C_GRN}Ready.${C_RESET} $1

  Logs:     $RUN_DIR/uvicorn.log  $( [ -f "$RUN_DIR/ui.pid" ] && echo "$RUN_DIR/ui.log" )
  Stop:     press Ctrl-C  (or in another shell: ./scripts/bootstrap.sh stop)
  Re-run:   ./scripts/bootstrap.sh ${MODE}

EOF
    # Wait on children; cleanup runs via trap on Ctrl-C.
    wait
}

# ---- commands --------------------------------------------------------------
cmd_check() {
    preflight_common
    preflight_demo || true
    info "Preflight (demo) passed. For full mode also: AGENT_MESH_API_KEY, SPLUNK_HOME, reachable Splunk."
}

cmd_demo() {
    preflight_common
    preflight_demo
    ensure_node_deps
    ensure_venv
    trap cleanup INT TERM EXIT
    start_uvicorn demo
    demo_smoke
    start_ui
    block_until_interrupt "Open ${C_BLU}http://localhost:${UI_PORT}${C_RESET} and click \"Run Demo Investigation\"."
}

cmd_full() {
    preflight_common
    preflight_full
    ensure_node_deps
    ensure_venv
    ensure_llm_sdk
    link_app
    print_sample_data_hint
    trap cleanup INT TERM EXIT
    start_uvicorn full
    block_until_interrupt "Open Splunk Web at ${C_BLU}http://localhost:${SPLUNK_WEB_PORT}/en-US/app/${SPLUNK_APP_ID}${C_RESET} → Investigations."
}

cmd_stop() {
    if ! ls "$RUN_DIR"/*.pid >/dev/null 2>&1; then
        info "Nothing to stop (no PID files in $RUN_DIR)."
        return 0
    fi
    cleanup
}

usage() {
    sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# ---- main ------------------------------------------------------------------
MODE="${1:-demo}"
case "$MODE" in
    demo)  cmd_demo ;;
    full)  cmd_full ;;
    check) cmd_check ;;
    stop)  cmd_stop ;;
    -h|--help|help) usage ;;
    *) usage; die "unknown mode: $MODE" "Use one of: demo, full, check, stop" ;;
esac
