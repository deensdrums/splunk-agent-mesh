# Sentinel Mesh — TODO

## Immediate Next Steps (Session 2)

- [ ] Run `yarn install` and `yarn build` to verify frontend compiles
- [ ] Run `cd server && pip install -r requirements.txt && uvicorn sentinel_mesh.app:app --reload` to verify backend starts
- [ ] Verify demo mode returns correct JSON from `/api/v1/investigations/run` with `demo: true`
- [ ] Add `react-dom` peer dep to `investigations` package (needed for standalone testing)
- [ ] Wire frontend API client base URL to be configurable via Splunk app conf or env var
- [ ] Add unit tests for `AgentRunPanel`, `IncidentTimeline`, `EvidenceTable`

## MVP

- [ ] Real SPL Hunter Agent: generate and run actual Splunk searches
- [ ] Connect `splunk_client.py` to a real Splunk instance (session key auth)
- [ ] LLM integration: wire Anthropic provider to TriageAgent and ExecutiveBriefAgent
- [ ] Settings save/load from backend: test full round-trip (save → test connection → run investigation)
- [ ] Splunk Passwords API integration in `SplunkSecureSettingsStore`
- [ ] Load sample CSV data into Splunk as lookups for demo
- [ ] Add polling/progress endpoint so frontend can show real-time agent progress
- [ ] MITRE ATT&CK mapping display: add technique links to attack.mitre.org
- [ ] Entity graph: implement real graph visualization (replace placeholder)

## Demo Polish

- [ ] Animate agent steps with realistic timing (simulate 2-3 sec per agent)
- [ ] Add Sentinel Mesh logo/branding to header
- [ ] Add severity color coding (red=critical, orange=high, yellow=medium, green=low)
- [ ] Add confidence bar visualization
- [ ] Make response plan items checkable (mark as completed)
- [ ] Add "Copy SPL" button to detection recommendation
- [ ] Add "Export PDF" or "Export JSON" for investigation result
- [ ] Dark mode support via @splunk/themes

## Stretch Goals

- [ ] Real-time streaming agent output (SSE or WebSocket)
- [ ] Investigation history: list and re-open past investigations
- [ ] Entity graph: interactive D3 or Cytoscape graph of affected entities
- [ ] Multi-investigation comparison view
- [ ] Direct Splunk alert action integration: trigger investigation from Notable Event
- [ ] Slack/Teams notification of investigation complete
- [ ] Analyst feedback loop: thumbs up/down on agent conclusions

## Security Hardening

- [ ] Add Splunk session token validation to backend routes
- [ ] Rate limit `/investigations/run` endpoint
- [ ] Audit log: record who ran which investigation, when
- [ ] Validate all SPL before execution (block dangerous commands: `delete`, `rest`)
- [ ] Add content security policy headers to Mako templates
- [ ] Penetration test settings endpoint for injection

## Packaging / Release

- [ ] Package Python backend as Splunk Custom REST Handler in `appserver/`
- [ ] Bundle backend dependencies into app via `pip install --target`
- [ ] Create Splunk app package (`.tar.gz`) via `yarn link:app` + Splunk packaging tools
- [ ] Write `app.manifest` for Splunkbase submission
- [ ] Add CI/CD: GitHub Actions for lint, test, build
- [ ] Write install guide for Splunk Cloud (admin steps)
