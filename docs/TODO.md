# Splunk Agent Mesh — TODO

## Done

- [x] **Validate LLM provider adapters end-to-end** — Anthropic provider is live and tested.
- [x] **Validate `SplunkRestConfReader` against live Splunk** — agents.conf reads correctly via REST.
- [x] **Skills: `splunk_search`** — agents emit fenced SPL blocks, orchestrator extracts and executes them, results rendered as artifacts.
- [x] **Cross-agent context (`depends_on`)** — orchestrator builds DAG, passes prior outputs to dependent agents.
- [x] **SSE streaming** — progressive per-agent rendering via Server-Sent Events.
- [x] **Async job API** — `/start`, `/status`, `/stream`, `/cancel` endpoints.
- [x] **`SplunkClient`** — live search execution against Splunk search jobs API.
- [x] **Visualization inference** — agent-driven hints via fence tag suffixes (`spl_column`, `spl_table`, etc.) with data-shape fallback.
- [x] **`@splunk/visualizations`** — Column, Line, Pie chart rendering for search artifacts.
- [x] **InvestigationReport** — report-style layout replacing legacy tab panel.

## Immediate

- [ ] **Smoke-test all viz types with real data** — confirm Column, Line, Pie, Bar, Table, Single all render correctly for their respective SPL patterns.
- [ ] **Remove `AgentTabsPanel`** — dead code, superseded by `InvestigationReport`.
- [ ] **Demo storyboard alignment** — update `DEMO_STORYBOARD.md` to match current UI (report layout, not tabs).

## Polish

- [ ] Animate agent status in report (pulsing spinner while running).
- [ ] "Export full investigation" button (concatenated markdown + artifact summaries).
- [ ] Settings page: list configured agents (read-only) so admins can verify the mesh.
- [ ] Persist investigation results to Splunk KV Store for history.

## Security hardening

- [ ] Validate Splunk session token on every backend request (per-request auth).
- [ ] Rate limit `/investigations/start`.
- [ ] Backend timeouts on LLM calls (per-agent).
- [ ] Per-request session-token forwarding from browser instead of single backend admin token.

## Future features

- [ ] **Parallel agent execution** — agents at the same DAG depth could run concurrently.
- [ ] **Additional skills**: `web_search`, `mitre_lookup` (resolves technique IDs to canonical names).
- [ ] **Multiple meshes** — app supports more than one mesh, selectable from the UI.
- [ ] **`SplunkSecureSettingsStore`** — wire to Splunk Passwords API for production credential storage.

## Packaging

- [ ] Package the Python backend as a Splunk Custom REST Handler.
- [ ] Build a `.tar.gz` Splunk app via `yarn link:app` + Splunk packaging.
- [ ] CI: GitHub Actions for `yarn build`, Python imports, basic smoke tests.

## Tests

- [ ] `ConfReader` unit tests — file parser, default merge, line continuation.
- [ ] `splunk_search.extract_spl_blocks` unit tests — viz hint parsing, bare fences, content validation.
- [ ] `LLMAgent` unit tests with a mock LLM provider.
- [ ] Frontend component tests for `InvestigationReport` and `ArtifactRenderer`.
