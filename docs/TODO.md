# Splunk Agent Mesh — TODO

## Done

- [x] **Config-driven agents** — `agents.conf` stanzas, `SplunkRestConfReader` +
  `FileConfReader`.
- [x] **LLM provider adapters** — Anthropic live; OpenRouter + OpenAI-compatible
  share the `complete()` interface.
- [x] **Live `SplunkClient`** — dispatch / poll / preview / final against the
  search jobs API.
- [x] **Structured event contract** — `agents/events.py` schema + validator,
  corrective retry, tolerant code-fence stripping.
- [x] **Harness-driven agentic loop** — one action per turn, handoff to the
  reporting sub-agent, finalize-turn + synthetic-final guard.
- [x] **Single visible Threat Hunter + Reporting sub-agent** — `agent_role`
  split; five legacy personas retained but disabled.
- [x] **Progressive search streaming** — preview rows + artifact `_revision`
  re-emission over SSE.
- [x] **Delegated Splunk auth** — `agent_mesh_bridge` REST endpoint, per-request
  session validation, signed SSE stream tokens, browser-side row fetching.
- [x] **Console UI** — staggered event reveal, stick-to-bottom auto-follow,
  status bar, inline charts, thinking indicator.
- [x] **Tests** — backend (`test_events.py`, `test_progressive_search.py`);
  frontend (`InvestigationReport`, `InvestigationPage`, `splunkSearchResults`,
  `useStaggeredReveal`).

## Immediate

- [ ] **Remove `AgentTabsPanel`** and unused `legacy/` components if not being
  revived.
- [ ] **Smoke-test all viz types** with real data (Column, Line, Pie, Bar,
  Table, Single).

## Security / hardening

- [x] Validate the delegated Splunk session before live investigations.
- [x] Forward Splunk Web session tokens through the authenticated REST bridge.
- [ ] Rate-limit `/investigations/start`.
- [ ] Per-agent LLM call timeouts.
- [ ] Seed the SSE stream-token secret from the environment (survive restarts /
  support multiple workers).
- [ ] Persist investigation/job state outside process memory.

## Future features

- [ ] **Discovery tools** for the Threat Hunter (index / sourcetype / field
  summaries) so it explores instead of guessing.
- [ ] **Search-optimizer sub-agent** that refines SPL + viz hint before
  execution.
- [ ] **Re-enable specialized personas** as additional primary agents where they
  add value.
- [ ] **`SplunkSecureSettingsStore`** wired to the Passwords API for production.
- [ ] **Multiple meshes** selectable from the UI.

## Packaging

- [ ] Package the Python backend for deployment alongside the Splunk app.
- [ ] Build a `.tar.gz` Splunk app via `yarn link:app` + Splunk packaging.
- [ ] CI: `yarn build`, `pytest`, `yarn test`, lint.

## Docs

- [ ] Keep `docs/legacy/HISTORY.md` appended as major architecture shifts land.
