# scripts/bootstrap.sh — one-command app install + sidecar

Installs the pre-built Splunk app from `target/app.tgz`, sets up the Python
backend, and starts the uvicorn sidecar.

## Quick start

```bash
./scripts/bootstrap.sh
```

The script will prompt for `SPLUNK_HOME` if it is not already set, extract the
app into `$SPLUNK_HOME/etc/apps/splunk-agent-mesh`, create a Python venv, and
start the backend sidecar on `:8765`. Press **Ctrl-C** to stop.

After the script starts, **restart Splunk** so it loads the app, then open
`http://localhost:8000/en-US/app/splunk-agent-mesh` → Investigations.

## Commands

| Command | What it does |
|---|---|
| `./scripts/bootstrap.sh` | Install app + start uvicorn sidecar. |
| `./scripts/bootstrap.sh check` | Run preflight only and exit (no processes started). |
| `./scripts/bootstrap.sh stop` | Stop whatever a previous run started. |
| `./scripts/bootstrap.sh --help` | Usage. |

## Prerequisites

- **Python ≥ 3.11, curl** — the script creates the backend venv on first run.
- **Splunk** installed locally — the script validates `$SPLUNK_HOME/bin/splunk`.
- **`target/app.tgz`** present in the repo root (pre-bundled or built via
  `yarn build`).

Optional environment variables:

| Variable | Purpose |
|---|---|
| `SPLUNK_HOME` | Path to your Splunk install. Prompted interactively if unset. |
| `AGENT_MESH_API_KEY` | LLM provider key for live investigations. |
| `SPLUNK_HOST` | Splunk REST URL (default `https://localhost:8089`). |

The sidecar runs with `AGENT_MESH_SETTINGS_STORE=dev` and
`AGENT_MESH_CONF_SOURCE=file`, and **`SPLUNK_TOKEN` is explicitly unset** —
searches use your delegated Splunk Web session, not a service token.

## Shutdown and rerun

- **Stop:** press **Ctrl-C** in the foreground session, or run
  `./scripts/bootstrap.sh stop` from another shell.
- **Rerun:** just run the same command again. If a previous run didn't shut down
  cleanly and a port is reported busy, run `./scripts/bootstrap.sh stop` first.

## Logs / troubleshooting

Runtime logs and PID files are written to `.bootstrap/` (gitignored):

- `.bootstrap/uvicorn.log` — backend sidecar

| Symptom | Fix |
|---|---|
| `port 8765 already in use` | `./scripts/bootstrap.sh stop`, or stop the other process. |
| `Splunk not found` | Install Splunk, or set `SPLUNK_HOME` correctly. |
| `app.tgz not found` | Run `yarn build` first, or ensure `target/app.tgz` is present. |
| backend not healthy | Inspect `.bootstrap/uvicorn.log`. |
