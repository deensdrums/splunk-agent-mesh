# Decision Record: Judge Demo Runtime (DEMO-001)

**Status:** Decided · **Date:** 2026-06-02 · **Story:** DEMO-001 · **Blocks:**
AUTH-001, DEMO-002 (bootstrap script), DEMO-003 (deterministic demo), DOC-001

This record names the environment a judge is expected to run, answers the Docker
question, and specifies how Splunk Web, the app package, uvicorn, and
credentials are initialized. The actual bootstrap script is DEMO-002; this story
only decides and specifies it.

---

## Decision

Support **two tiers**, with a zero-dependency default:

1. **Tier 1 — Demo mode, no Splunk (the default judge path).** A judge runs the
   sidecar (uvicorn) + the standalone UI and clicks the demo button. Canned
   events and at least one chart render with **no Splunk instance, no LLM key,
   and no tokens**. This is the path that is genuinely realistic "from a clean
   checkout in a few minutes," and it is deterministic, so it can't fail on a
   judge's machine. (Hardened under DEMO-003.)

2. **Tier 2 — Full/live mode against an existing Splunk + a bootstrap script.**
   For a judge who already has (or stands up) a Splunk Enterprise instance, a
   single bootstrap command links the app, starts uvicorn, validates
   prerequisites, and prints the Splunk Web URL. This shows the real value:
   delegated browser-session search through the `agent_mesh_bridge`, live SPL,
   and progressive chart streaming. (Script is DEMO-002.)

**Docker is out of scope** for the judge demo (see below).

Rationale: a hackathon judge needs something that *always works* first (Tier 1),
and a way to see the *real* integration if they have Splunk (Tier 2). Requiring
every judge to stand up Splunk would fail the "realistic from a clean checkout"
bar; shipping only the no-Splunk demo would hide the actual product.

---

## Docker: out of scope (revisit only if judging requires a self-contained image)

A fully containerized Splunk + app + uvicorn path is **not supported** for this
demo. It is a decision we validated and rejected for now, not an oversight:

- **Licensing / image:** the official `splunk/splunk` image needs trial-license
  acceptance and is large; not friction-free to hand to a judge.
- **Custom REST handler fragility:** the `agent_mesh_bridge` endpoint requires
  installing the app *and* having Splunk's bundled Python satisfy
  `restmap.conf: python.required = 3.13` (see Risks). Matching that inside a
  container image adds a sharp version dependency.
- **Bootstrap surface:** app install, token/CORS, sample-data load, and
  multi-container networking (uvicorn ↔ Splunk ↔ browser) multiply the failure
  modes — the opposite of what a 3-minute demo needs.

Revisit if a future judging environment *requires* a single self-contained
image; the Tier-2 init steps below are the spec a container path would automate.

---

## How each tier initializes the pieces

### Tier 1 — Demo mode (no Splunk)

| Piece | How it's initialized |
|---|---|
| App package | Not needed in Splunk. The UI runs **standalone** (webpack demo server); `apiClient` detects non-Splunk-Web runtime and talks to uvicorn directly at `localhost:8765`. |
| uvicorn | Started from `server/` venv. **No** `SPLUNK_TOKEN`, **no** `AGENT_MESH_API_KEY` required — demo mode makes no LLM or Splunk call. |
| Splunk Web | Not used. |
| Credentials | None. Demo run returns canned events + a fixture artifact (DEMO-003 guarantees rows). |

Clean-checkout realism: needs only Node ≥ 22, Yarn, Python ≥ 3.11, and the repo.

### Tier 2 — Full/live mode (existing Splunk + bootstrap)

| Piece | How it's initialized |
|---|---|
| App package | `yarn install && yarn build && yarn workspace @splunk/agent-mesh run link:app`, then **restart Splunk** so it loads the app and the `agent_mesh_bridge` custom REST endpoint. |
| Splunk Web | The judge opens the printed Investigations app URL (e.g. `http://localhost:8000/en-US/app/<app>/...`). Auth is the judge's normal Splunk Web login. |
| uvicorn | Started from `server/` venv with **`AGENT_MESH_API_KEY` only** (env-backed LLM key). **Do not set `SPLUNK_TOKEN`** — see Credential policy. Health-checked at `/api/v1/health`. |
| Search auth | The browser's Splunk session is delegated to uvicorn through the Splunk-Web `__raw` proxy → `agent_mesh_bridge`; searches run as the analyst. No shared admin token on the hot path. |
| Sample data | Load the bundled lookups into indexes (the `| inputlookup … | collect …` block in the README) so live searches return rows. |
| Config (agents/model) | `agents.conf` is read from the repo file (FileConfReader) since no `SPLUNK_TOKEN` is set; the active model is the conf `model` value shown read-only in Settings (ADR-021). |

### Credential policy for the demo

- **LLM key:** env var `AGENT_MESH_API_KEY` on the uvicorn process. Settings-page
  save / Splunk Passwords storage is **not** used for the demo.
- **`SPLUNK_TOKEN`: intentionally unset for the sidecar.** AUTH-001 removed its
  former implicit side effects. Tier 2 can opt into individual service-token
  features later with `AGENT_MESH_SETTINGS_STORE=splunk`,
  `AGENT_MESH_CONF_SOURCE=splunk`, or
  `AGENT_MESH_ALLOW_SERVICE_SEARCH_FALLBACK=1`.
- Startup logs the selected credential modes **without printing secrets**.

---

## Bootstrap responsibilities (spec for DEMO-002)

The Tier-2 script (DEMO-002) should, in order:

1. **Preflight:** verify Node/Yarn/Python versions; ports `8000` (Splunk Web),
   `8089` (Splunk REST), `8765` (uvicorn) reachable/free; Splunk reachable;
   `AGENT_MESH_API_KEY` present. Fail early with the specific missing item and
   the fix.
2. **Build + link** the app and prompt for (or detect) the required Splunk
   restart.
3. **Load sample data** (or print the exact SPL if it can't).
4. **Start uvicorn** with `AGENT_MESH_API_KEY` set and `SPLUNK_TOKEN` unset;
   report the `/api/v1/health` result.
5. **Print the exact Splunk Web URL** to open, plus shutdown/rerun instructions.

A Tier-1 variant of the script should start uvicorn + the standalone UI and
print the demo URL, skipping all Splunk steps.

---

## Demo fixture (DEMO-003)

The deterministic demo is a **replayable Log4Shell investigation** — no LLM or
Splunk call.

- **Authoritative source:** `server/agent_mesh/demo/demo_case.py`. This is the
  single source of truth; the former frontend duplicate (`demoData.ts`) was
  removed. The token-less judge is covered by this backend fixture + the
  bootstrap (which always starts uvicorn).
- **Paced replay:** when an investigation runs via `/start` + SSE (what the UI
  does), the events and search artifacts are streamed with pacing — narration,
  a search card going pending → running → done, findings, a handoff, and a
  final answer — so it looks like a live agentic run. The synchronous `/run`
  path returns the same final result instantly.
- **Pacing knob:** `AGENT_MESH_DEMO_STEP_SECONDS` (default `1.1`; tests set `0`).
- **Scenario:** Log4Shell (CVE-2021-44228) exploitation of `web-prod-04` /
  `web-prod-07` with a confirmed outbound LDAP C2 callback. Includes a timechart
  artifact with guaranteed rows.
- **UI labeling:** the console shows a **"Demo data"** badge for demo runs.
- **Smoke tests:** `server/tests/test_demo.py` (no-LLM completion, progressive
  replay with pending→running→done, and a start→completion→artifact run through
  the job store — the same state the SSE endpoint serves).

---

## Risks / prerequisites to validate

- **⚠️ Splunk Python version.** `restmap.conf` declares `python.required =
  3.13`. If the judge's Splunk build ships an older bundled Python, the bridge
  won't load and Tier 2 live mode breaks (Tier 1 is unaffected). The bootstrap
  preflight must check this and, if it's a common mismatch, AUTH-001/DEMO-002
  should decide whether to relax the requirement. **This is the single biggest
  Tier-2 prerequisite to confirm.**
- **App reload requires a Splunk restart** to register the custom REST endpoint;
  the script must make this explicit.
- **CORS:** the backend must allowlist the Splunk Web origin (config default
  already includes `http://localhost:8000`).
- **Model surface:** Settings shows the effective harness model read from
  `agents.conf` as read-only (ADR-021). Judges should edit the conf stanza, not
  provider settings, to change the model used by subsequent runs.

---

## Acceptance criteria — disposition

- ✅ Decision record names the supported path(s) and prerequisites.
- ✅ Docker is explicitly answered: **out of scope** (with rationale + revisit
  condition).
- ✅ The record identifies how Splunk Web, app package, uvicorn, and credentials
  are initialized (per tier, above).
- ✅ Realistic from a clean checkout: Tier 1 needs only Node/Yarn/Python + repo;
  Tier 2 adds an existing Splunk and one bootstrap command.

## Follow-ups this unblocks
- **DEMO-002:** ✅ done — `scripts/bootstrap.sh` (demo/full/check/stop).
- **DEMO-003:** ✅ done — paced Log4Shell replay; see "Demo fixture" above.
- **AUTH-001:** make credential mode explicit; remove the `SPLUNK_TOKEN`
  coupling this record routes around.
- **DOC-001:** fold the Tier-1 command into the README quick start as the
  primary path.
