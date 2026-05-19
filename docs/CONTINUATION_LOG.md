# Sentinel Mesh — Continuation Log

Every coding session must append an entry to this file so the next agent session can resume without losing context.

---

## Session 1 — 2026-05-18

### What Changed

**Foundation session** — built the full project scaffold from an empty Splunk Create monorepo.

#### Documentation created
- `docs/PROJECT_BRIEF.md` — project overview, MVP scope, demo experience
- `docs/ARCHITECTURE.md` — full architecture with Mermaid data flow diagram
- `docs/AGENT_DESIGN.md` — 7-agent design with purpose/inputs/outputs/prompt contracts
- `docs/SECURE_SETTINGS.md` — credential storage design and security requirements
- `docs/DEMO_STORYBOARD.md` — 3-minute hackathon demo script
- `docs/DECISIONS.md` — 5 ADR-style architecture decisions
- `docs/TODO.md` — full backlog organized by priority
- `docs/CONTINUATION_LOG.md` — this file

#### Frontend (packages/investigations/src/)
- `types.ts` — all shared TypeScript types (InvestigationResult, AgentStep, etc.)
- `Investigations.tsx` — replaced scaffold placeholder with tabbed app root (Investigation / Settings / About)
- `InvestigationsStyles.ts` — updated styled-components for new layout
- `index.ts` — updated exports
- `pages/InvestigationPage.tsx` — full investigation form + result display
- `pages/SettingsPage.tsx` — LLM settings with secure credential messaging
- `pages/AboutPage.tsx` — about/documentation page
- `components/AgentRunPanel.tsx` — agent progress list with status icons
- `components/InvestigationSummary.tsx` — severity badge, confidence, entity list
- `components/IncidentTimeline.tsx` — chronological timeline with color-coded severity dots
- `components/EvidenceTable.tsx` — tabular evidence with source, field, value, interpretation
- `components/EntityGraphPlaceholder.tsx` — entity tag display (graph coming in v2)
- `components/DetectionRecommendation.tsx` — SPL code block with copy button
- `components/ResponsePlan.tsx` — response actions with approval requirements
- `services/apiClient.ts` — HTTP client for all backend calls
- `demo/demoData.ts` — static demo agent steps and full investigation result
- `tests/Investigations.unit.tsx` — updated tests for new component

#### Backend (server/sentinel_mesh/)
- `app.py` — FastAPI app with CORS, all 5 API endpoints
- `config.py` — runtime config from env vars
- `security.py` — key redaction, input validation helpers
- `settings_store.py` — DevSettingsStore + SplunkSecureSettingsStore (stub) abstraction
- `splunk_client.py` — SplunkClient (stub) + DemoSplunkClient (synthetic events)
- `llm/base.py` — LLMProvider interface
- `llm/anthropic_provider.py` — Anthropic Claude adapter
- `llm/openai_compatible_provider.py` — OpenAI-compatible adapter
- `llm/openrouter_provider.py` — OpenRouter adapter (wraps OpenAI-compatible)
- `agents/orchestrator.py` — sequential agent runner
- `agents/triage_agent.py` — entity extraction + severity classification
- `agents/spl_hunter_agent.py` — SPL template generation + search
- `agents/timeline_agent.py` — event correlation into timeline
- `agents/blast_radius_agent.py` — additional entity identification
- `agents/detection_gap_agent.py` — detection rule generation
- `agents/response_agent.py` — response plan generation
- `agents/executive_brief_agent.py` — MITRE mapping + confidence scoring + summary
- `demo/demo_case.py` — static demo investigation result
- `demo/synthetic_events.py` — synthetic event data for each data source
- `requirements.txt` — Python dependencies

#### Splunk Resources
- `packages/ai-investigator/src/main/resources/splunk/lookups/endpoint_events.csv`
- `packages/ai-investigator/src/main/resources/splunk/lookups/dns_events.csv`
- `packages/ai-investigator/src/main/resources/splunk/lookups/auth_events.csv`
- `packages/ai-investigator/src/main/resources/splunk/lookups/proxy_events.csv`
- `packages/ai-investigator/src/main/resources/splunk/lookups/firewall_events.csv`
- `packages/ai-investigator/src/main/resources/splunk/default/data/ui/nav/default.xml` (updated label)

#### Reference SPL and Config
- `splunk/spl/suspicious_powershell.spl`
- `splunk/spl/rare_domain_after_execution.spl`
- `splunk/spl/finance_file_access.spl`
- `splunk/spl/outbound_transfer.spl`
- `splunk/spl/blast_radius_hunt.spl`
- `splunk/config_examples/indexes.conf`
- `splunk/config_examples/props.conf`
- `splunk/config_examples/transforms.conf`

#### Other
- `README.md` — full rewrite with setup, demo, architecture, limitations, next steps
- `.gitignore` — added Sentinel Mesh secret/generated file patterns

### Commands Run

- No build commands run (dependencies not installed in this environment).
- File creation only.

### Current Runnable Status

**NOT YET BUILT** — dependencies not installed, build not run.

Expected build status after `yarn install && yarn build`:
- TypeScript compilation: likely 1-3 minor issues (import types, TextArea event handler signatures)
- Runtime: should render the tabbed app in Splunk Web once built and deployed

Expected backend status after `pip install -r requirements.txt`:
- FastAPI app should start cleanly
- Demo endpoint: `POST /api/v1/investigations/run` with `{"demo": true}` should return DEMO_RESULT
- Real investigation: works if `SENTINEL_MESH_API_KEY` and `SENTINEL_MESH_DEV_MODE=1` are set

### Known Broken Things

1. **TypeScript**: `TextArea` and `Text` component event handler types may need adjustment. Splunk UI Toolkit event signatures vary between `@splunk/react-ui` versions. Run `yarn build` to find exact errors.
2. **TabLayout**: The `TabLayout` component's `onChange` event signature may differ in the installed version of `@splunk/react-ui`. If it fails, replace with a simple `<button>` tab implementation.
3. **ColumnLayout**: Check that `ColumnLayout.Row` and `ColumnLayout.Column` are the correct sub-component names for the installed version.
4. **SplunkSecureSettingsStore**: Stub — not functional. Uses DevSettingsStore by default.
5. **Real Splunk searches**: Not connected. DemoSplunkClient used for demo mode.

### Suggested Next Steps for Session 2

1. Run `cd server && pip install fastapi uvicorn pydantic httpx python-dotenv && uvicorn sentinel_mesh.app:app --reload`
2. Smoke test: `curl -X POST http://localhost:8000/api/v1/investigations/run -d '{"description":"test","demo":true}' -H 'Content-Type: application/json'`
3. Link and deploy to local Splunk: `yarn workspace @splunk/ai-investigator run link:app`
4. Wire SplunkSecureSettingsStore to real Splunk Passwords API
5. Test the Settings page round-trip (save → test connection)

---

## Session 1 (continued) — 2026-05-18

### What Changed

TypeScript compilation errors fixed after running `yarn install && yarn build`:

**Root causes:**
1. `variables.fontSizeMedium` does not exist in `@splunk/themes` — replaced with `fontSizeLarge` across all 9 affected files
2. `TabLayout.onChange` passes `activePanelId?: string` (optional) — fixed handler to guard for undefined; also removed conflicting `defaultActivePanelId` (can't use both controlled and uncontrolled props)
3. `Text` and `TextArea` use Splunk's own `onChange` signature (first arg is a union event type) — changed all handlers to `(_e: unknown, { value }: { value: string }) =>`
4. `Select.onChange` passes `value: string | number | boolean` — updated handler to `String(value)`
5. `variables.spacingMedium` etc. are `VariableInterpolation` functions, not strings — cannot be used in `style={{}}` inline objects; converted affected sections to styled-components

**Files modified:**
- `src/components/AgentRunPanel.tsx`
- `src/components/DetectionRecommendation.tsx`
- `src/components/EntityGraphPlaceholder.tsx`
- `src/components/EvidenceTable.tsx`
- `src/components/IncidentTimeline.tsx`
- `src/components/InvestigationSummary.tsx`
- `src/components/ResponsePlan.tsx`
- `src/Investigations.tsx`
- `src/pages/AboutPage.tsx`
- `src/pages/InvestigationPage.tsx`
- `src/pages/SettingsPage.tsx`

### Commands Run

```
yarn install && yarn build    # installed deps, fixed 22 TS errors
yarn workspace @splunk/investigations run types:build   # 0 errors
yarn build    # both packages compile cleanly
```

### Current Runnable Status

**FRONTEND BUILDS CLEAN** — `yarn build` exits 0 with only webpack size warnings (bundle is 6.38 MB, normal for Splunk UI Toolkit). TypeScript: 0 errors.

**BACKEND** — not yet run in this environment. Expected to start cleanly.

### Known Broken Things

1. **Backend not started** — run `uvicorn sentinel_mesh.app:app --reload` from `server/`
2. **SplunkSecureSettingsStore** still a stub
3. **Real Splunk searches** not connected
4. **`TextArea` no placeholder** — Splunk's TextArea doesn't support `placeholder`; removed from InvestigationPage. Consider adding a helper text label instead.

### Suggested Next Steps for Session 3

1. Start backend: `cd server && pip install fastapi uvicorn pydantic httpx python-dotenv && uvicorn sentinel_mesh.app:app --reload`
2. Smoke test demo endpoint
3. Deploy to Splunk: `yarn workspace @splunk/ai-investigator run link:app`
4. Wire SplunkSecureSettingsStore to Splunk Passwords API
5. Test full Settings → Test Connection → Run Investigation round-trip
