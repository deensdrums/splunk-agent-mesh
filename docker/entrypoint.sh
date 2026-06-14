#!/bin/bash
# Splunk Agent Mesh — Docker entrypoint
# Wraps the official Splunk entrypoint to also start uvicorn and load demo data.
set -e

APP_TGZ="/tmp/app.tgz"
INDEXES_CONF="/tmp/indexes.conf"
AGENT_MESH_DIR="/opt/agent-mesh"
SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"

# --- Phase 1: Start uvicorn in the background ---
echo "[agent-mesh] Starting uvicorn on port 8765..."
cd "$AGENT_MESH_DIR/server"
"$AGENT_MESH_DIR/.venv/bin/uvicorn" agent_mesh.app:app \
    --host 0.0.0.0 \
    --port 8765 \
    --log-level info &

# --- Phase 2: Background job to install app and load demo data ---
(
    set +e
    echo "[agent-mesh] Waiting for Splunk to become ready..."
    until curl -sk -o /dev/null -w '%{http_code}' \
        https://localhost:8089/services/server/info 2>/dev/null | grep -qE "200|401"; do
        sleep 5
    done

    # Install the app if not already present
    if [ ! -d "$SPLUNK_HOME/etc/apps/splunk-agent-mesh/default" ]; then
        echo "[agent-mesh] Installing app..."
        sudo tar xzf "$APP_TGZ" -C "$SPLUNK_HOME/etc/apps/"
        sudo chown -R splunk:splunk "$SPLUNK_HOME/etc/apps/splunk-agent-mesh"

        # Add demo indexes
        sudo mkdir -p "$SPLUNK_HOME/etc/apps/splunk-agent-mesh/local"
        sudo cp "$INDEXES_CONF" "$SPLUNK_HOME/etc/apps/splunk-agent-mesh/local/indexes.conf"
        sudo chown -R splunk:splunk "$SPLUNK_HOME/etc/apps/splunk-agent-mesh/local"

        echo "[agent-mesh] Restarting Splunk to load app..."
        sudo "$SPLUNK_HOME/bin/splunk" restart

        echo "[agent-mesh] Waiting for Splunk to come back..."
        sleep 5
        until curl -sk -o /dev/null -w '%{http_code}' \
            https://localhost:8089/services/server/info 2>/dev/null | grep -qE "200|401"; do
            sleep 5
        done
    fi

    # Load demo data
    sleep 5
    echo "[agent-mesh] Loading demo data into indexes..."
    for pair in \
        "endpoint_events.csv:endpoint" \
        "dns_events.csv:dns" \
        "auth_events.csv:auth" \
        "proxy_events.csv:proxy" \
        "firewall_events.csv:firewall"; do

        csv="${pair%%:*}"
        idx="${pair##*:}"
        echo "[agent-mesh]   $csv -> index=$idx"
        "$SPLUNK_HOME/bin/splunk" search \
            "| inputlookup $csv | collect index=$idx" \
            -auth "admin:${SPLUNK_PASSWORD}" 2>/dev/null || \
            echo "[agent-mesh]   WARNING: failed to load $csv"
    done

    echo ""
    echo "============================================"
    echo "  Splunk Agent Mesh is ready!"
    echo "============================================"
    echo ""
    echo "  Splunk Web:  http://localhost:8000"
    echo "  Login:       admin / <your SPLUNK_PASSWORD>"
    echo ""
    echo "  App:         http://localhost:8000/en-US/app/splunk-agent-mesh/Investigations"
    echo ""
    echo "  Next step:   Click the gear icon and enter"
    echo "               your Anthropic API key."
    echo ""
    echo "  Demo mode:   Works without an API key."
    echo ""
    echo "============================================"
) &

# --- Phase 3: Hand off to the Splunk entrypoint (foreground) ---
exec /sbin/entrypoint.sh start-service
