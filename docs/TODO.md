# Splunk Agent Mesh — TODO

## Immediate (next session)

- [ ] **Validate LLM provider adapters end-to-end** — install `anthropic` and
  `openai` SDKs, run `POST /api/v1/settings/test` against each provider with a
  real key. This is the biggest unblocker for a live demo.
- [ ] **Implement `SplunkSecureSettingsStore`** — three calls against
  `/services/storage/passwords`. Same auth machinery as `SplunkRestConfReader`.
- [ ] **Validate `SplunkRestConfReader` against a live Splunk** — ensure
  `agents.conf` is reachable via REST after the app is deployed.
- [ ] **Smoke-test the demo in Splunk Web** — confirm the input card +
  AgentTabsPanel render correctly and the demo button populates all 7 tabs.

## Skills (the next big feature)

- [ ] Define a `Skill` interface: name, description, JSON-schema input/output,
  invoke method.
- [ ] Built-in skills: `splunk_search` (calls `SplunkClient.search`),
  `web_search` (optional), `mitre_lookup` (resolves technique ids to canonical
  names).
- [ ] `agents.conf`: honor the `skills =` field — the runtime grants the agent
  access to the listed skills via tool use.
- [ ] LLM-side: switch to tool-use API for providers that support it (Anthropic
  `tools`, OpenAI function calling).
- [ ] Rich rendering: code-block renderers for `spl`, `splunk-chart`,
  `splunk-table`. Wire into `MarkdownView.codeBlockRenderers`.

## Cross-agent context (v2)

- [ ] Stanza field `depends_on = <agent_id, ...>` so dependent agents see prior
  outputs.
- [ ] Orchestrator builds a DAG and runs independent agents in parallel.

## Streaming (v2)

- [ ] Server-Sent Events or WebSocket endpoint streaming per-agent status and
  partial markdown as it lands.
- [ ] Frontend: per-tab progressive rendering of streaming markdown.

## Real Splunk integration

- [ ] Implement `SplunkClient.search(spl, time_range)` against
  `/services/search/jobs` with session-key auth.
- [ ] Load sample CSV data into Splunk as lookups (`| inputlookup ... |
  collect index=...`).
- [ ] Per-request session-token forwarding from the browser, instead of a
  single backend admin token.

## Polish

- [ ] Animate tab status badges (pulsing for `running`).
- [ ] Persist active tab in URL hash for deep-linking.
- [ ] Settings page: list configured agents (read-only) so admins can verify
  what's wired up.
- [ ] "Export markdown" button per agent tab.
- [ ] "Export full investigation" button (concatenated markdown).

## Tests

- [ ] `ConfReader` unit tests — file parser, default merge, line continuation,
  enabled/disabled handling.
- [ ] `LLMAgent` unit tests with a mock LLM provider.
- [ ] Frontend behavior tests: `AgentTabsPanel` renders descriptors, switches
  tabs on click, surfaces error state.
- [ ] `MarkdownView` test for the code-block renderer registry.

## Security hardening

- [ ] Validate Splunk session token on every backend request.
- [ ] Rate limit `/investigations/run`.
- [ ] Audit log: which user ran which investigation, when, against which agents.
- [ ] Backend timeouts on LLM calls (per-agent).

## Packaging

- [ ] Package the Python backend as a Splunk Custom REST Handler so it runs
  inside Splunk.
- [ ] Build a `.tar.gz` Splunk app via `yarn link:app` + Splunk packaging.
- [ ] CI: GitHub Actions for `yarn build`, Python imports, basic smoke tests.
