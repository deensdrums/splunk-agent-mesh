# scripts/bootstrap.sh — one-command demo bootstrap

A single command that preflights prerequisites, starts the app, health-checks
it, and prints the URL to open. See `docs/DEMO_RUNTIME.md` for the runtime
decision this implements (DEMO-002).

## TL;DR (judges)

From a clean checkout, on macOS/Linux:

```bash
./scripts/bootstrap.sh
```

That runs **demo mode**: it starts the backend and a standalone UI, then prints
`http://localhost:8080`. Open it and click **"Run Demo Investigation"** — no Splunk, no LLM key, no
tokens required. Press **Ctrl-C** to stop.

## Modes

| Command | What it does |
|---|---|
| `./scripts/bootstrap.sh` or `… demo` | **Tier 1.** uvicorn (`:8765`) + standalone UI (`:8080`). No Splunk, no key. The deterministic demo. |
| `./scripts/bootstrap.sh full` | **Tier 2.** Builds + links the Splunk app, starts uvicorn for live LLM + delegated Splunk search, prints the Splunk Web URL. Requires an existing Splunk and an LLM key. |
| `./scripts/bootstrap.sh check` | Run preflight only and exit (no processes started). |
| `./scripts/bootstrap.sh stop` | Stop whatever a previous run started. |
| `./scripts/bootstrap.sh --help` | Usage. |

## Prerequisites

Both modes: **Node ≥ 22, Yarn, Python ≥ 3.11, curl.** The script creates the
backend venv and installs JS deps on first run if needed.

`full` mode additionally requires:
- `AGENT_MESH_API_KEY` exported (the LLM provider key).
- `SPLUNK_HOME` exported (to link the app).
- A reachable Splunk REST endpoint (`SPLUNK_HOST`, default
  `https://localhost:8089`).
- After linking, **restart Splunk** so it loads the app + the `agent_mesh_bridge`
  REST endpoint, and load the sample data (the script prints the SPL).

The sidecar runs with `AGENT_MESH_SETTINGS_STORE=dev` and
`AGENT_MESH_CONF_SOURCE=file`, and **`SPLUNK_TOKEN` is explicitly unset** for the
backend process — searches use your delegated Splunk Web session, not a service
token (see `docs/DEMO_RUNTIME.md`).

## Shutdown and rerun

- **Stop:** press **Ctrl-C** in the foreground session, or run
  `./scripts/bootstrap.sh stop` from another shell.
- **Rerun:** just run the same command again. If a previous run didn't shut down
  cleanly and a port is reported busy, run `./scripts/bootstrap.sh stop` first.

## Logs / troubleshooting

Runtime logs and PID files are written to `.bootstrap/` (gitignored):

- `.bootstrap/uvicorn.log` — backend
- `.bootstrap/ui.log` — standalone UI (demo mode)

Preflight failures name the missing prerequisite and the fix. Common ones:

| Symptom | Fix |
|---|---|
| `port 8765/8080 already in use` | `./scripts/bootstrap.sh stop`, or stop the other process. |
| `AGENT_MESH_API_KEY is not set` (full) | `export AGENT_MESH_API_KEY=<key>` before `full`. |
| `Splunk REST not reachable` (full) | Start Splunk, or set `SPLUNK_HOST=https://<host>:8089`. |
| backend not healthy | Inspect `.bootstrap/uvicorn.log`. |
