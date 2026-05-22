# Claude Code Prompt: Build Sentinel Mesh — Agentic SOC Investigation App for Splunk

You are Claude Code working inside an existing empty Splunk app repo scaffolded with Splunk Create / `@splunk/create`.

Your task is to plan and begin implementing **Sentinel Mesh**, a Security-track Splunk Agentic Ops Hackathon project.

Sentinel Mesh is an agentic SOC investigation copilot for Splunk. It uses a React UI built with Splunk UI Toolkit, a Splunk-side backend service, secure LLM settings, and Splunk searches to investigate alerts, build timelines, map activity to MITRE ATT&CK, identify blast radius, and generate response recommendations.

The project must be designed so future AI coding-agent sessions can continue it safely across multiple refreshes. Preserve decisions, status, TODOs, architecture, and assumptions in repo files.

---

## Important constraints

1. This is a Splunk app created with Splunk Create / `@splunk/create`.
2. Use **Splunk UI Toolkit** React components for the frontend.
3. An empty app already exists with basic elements. Inspect the repo before changing anything.
4. Do not replace the scaffold unless absolutely necessary.
5. The app must eventually run inside Splunk Web.
6. The project should include a backend service that runs on or with the Splunk server.
7. You must decide the best initial backend approach after inspecting the scaffold.
8. The backend must support LLM providers such as:
   - Anthropic Claude
   - OpenRouter
   - Future providers via adapter interface
9. API keys must never be stored in frontend code, localStorage, committed config, or plaintext repo files.
10. Build a secure settings page in the Splunk app for:
    - LLM provider
    - Base URL, if applicable
    - Model name
    - API key
    - Test connection
11. Store API keys using Splunk secure credential storage, preferably Splunk encrypted storage/passwords or a Splunk-supported secure configuration pattern.
12. Keep all implementation steps incremental and well-documented.

---

## Primary goal for this first coding session

Do not attempt to build the entire final product in one pass.

Instead, create a strong foundation:

1. Inspect the existing repo structure.
2. Create persistent project planning artifacts.
3. Decide the backend architecture.
4. Add or stub the initial Splunk UI Toolkit React screens.
5. Add or stub the secure settings workflow.
6. Add or stub the agent orchestration service.
7. Add sample synthetic security data and SPL searches.
8. Add a clear README and continuation notes.
9. Leave the repo in a runnable or at least clearly documented state.

---

## Product name

**Sentinel Mesh**

## Tagline

**From alert to evidence-backed response in minutes.**

## Core user story

A SOC analyst opens the Splunk app, enters a host/user/alert description, and clicks **Start Investigation**.

The app launches an agentic workflow that:

1. Generates or selects SPL searches.
2. Queries Splunk security data.
3. Correlates evidence.
4. Builds an incident timeline.
5. Maps observed behavior to MITRE ATT&CK.
6. Scores severity and confidence.
7. Identifies blast radius.
8. Recommends human-approved response actions.
9. Generates detection logic to improve future coverage.

---

## Target demo scenario

Use this synthetic scenario as the initial demo path:

**Suspicious PowerShell on finance laptop**

Attack chain:

1. User `jsmith` opens a suspicious Office document.
2. `winword.exe` spawns `powershell.exe`.
3. PowerShell runs an encoded command.
4. Host `FIN-LAPTOP-22` contacts rare domain `cdn-update-check.com`.
5. User accesses finance file server `FIN-FILE-01`.
6. Archive `Q2_finance_exports.zip` is created.
7. Large outbound transfer occurs to an unusual external IP.

Expected final investigation result:

- Severity: High
- Confidence: around 85–90%
- Affected user: `jsmith`
- Affected host: `FIN-LAPTOP-22`
- Suspicious domain: `cdn-update-check.com`
- Likely MITRE techniques:
  - PowerShell
  - Obfuscated/encoded command
  - Ingress Tool Transfer
  - Collection/archive staged
  - Possible exfiltration
- Recommended response:
  - Isolate host
  - Disable user session
  - Block domain/IP
  - Hunt across environment
  - Preserve forensic evidence
- Generate a reusable Splunk detection for Office-spawned encoded PowerShell.

---

## Required repo-persistent artifacts

Create or update these files so future Claude Code sessions can resume without losing context:

```text
docs/PROJECT_BRIEF.md
docs/ARCHITECTURE.md
docs/AGENT_DESIGN.md
docs/SECURE_SETTINGS.md
docs/DEMO_STORYBOARD.md
docs/CONTINUATION_LOG.md
docs/DECISIONS.md
docs/TODO.md
docs/PROJECT_BRIEF.md

Include:

Project name
Hackathon track
One-sentence pitch
Problem
Solution
Target users
MVP scope
Non-goals
Final demo experience
docs/ARCHITECTURE.md

Include:

Current repo structure
Frontend structure
Backend/service structure
How React app talks to the backend
How backend talks to Splunk
How backend talks to LLM providers
Secure credential flow
Data flow diagram in Mermaid
Known risks
docs/AGENT_DESIGN.md

Define these agents:

Triage Agent
SPL Hunter Agent
Timeline Agent
Blast Radius Agent
Detection Gap Agent
Response Agent
Executive Brief Agent

For each, include:

Purpose
Inputs
Outputs
Prompt contract
Tool access
Failure behavior
docs/SECURE_SETTINGS.md

Document:

How LLM provider settings are stored
How API keys are stored securely
Which Splunk capabilities may be required
How settings page works
What must never be logged
Redaction requirements
Test connection behavior
docs/DEMO_STORYBOARD.md

Include a 3-minute hackathon demo script:

Problem
Launch investigation
Show agents
Show SPL/evidence
Show timeline
Show response plan
Show generated detection
Closing line
docs/CONTINUATION_LOG.md

This is critical. Every coding session must append:

Date/time
What changed
Commands run
Files touched
Current runnable status
Known broken things
Suggested next steps
docs/DECISIONS.md

Record architecture decisions as ADR-style entries:

Decision
Context
Options considered
Chosen approach
Consequences
docs/TODO.md

Use sections:

Immediate next steps
MVP
Demo polish
Stretch goals
Security hardening
Packaging/release
Initial implementation goals

After creating the planning artifacts, implement or stub the following.

Frontend requirements

Use Splunk UI Toolkit React components where appropriate.

Create or update React pages/components for:

src/pages/InvestigationPage.*
src/pages/SettingsPage.*
src/pages/AboutPage.*
src/components/AgentRunPanel.*
src/components/InvestigationSummary.*
src/components/IncidentTimeline.*
src/components/EntityGraphPlaceholder.*
src/components/EvidenceTable.*
src/components/DetectionRecommendation.*
src/components/ResponsePlan.*
src/services/apiClient.*

The exact paths may differ depending on the existing Splunk Create scaffold. Inspect the repo and adapt paths accordingly. Do not break existing routing.

Investigation page

Should include:

Text input: “Describe what to investigate”
Optional fields:
Host
User
Alert name
Time range
Button: “Start Investigation”
Demo button: “Load Suspicious PowerShell Demo”
Display panels:
Agent progress
Investigation summary
Timeline
Evidence table
MITRE mapping
Response plan
Detection recommendation

For the first implementation, it is acceptable for the page to call a stub backend endpoint returning deterministic demo JSON.

Settings page

Should include:

Provider dropdown:
Anthropic
OpenRouter
Custom OpenAI-compatible
Base URL input
Model input
API key input
Save button
Test Connection button
Clear Credentials button
Redacted display of whether an API key is configured
Warning that the key is stored in Splunk secure storage, not in browser storage

Do not expose the API key after save.

About page

Should explain:

What Sentinel Mesh does
How AI is used
How Splunk data is used
Human approval principle
Demo dataset
Backend/service requirements

Inspect the Splunk app scaffold and choose the best backend approach.

Preferred initial approach:

A Splunk app server-side Python REST handler if the scaffold supports it cleanly.
Otherwise, create a local Python FastAPI service under the repo with clear instructions and a path to later package/integrate it with Splunk.
Whichever approach you choose, document the decision in docs/DECISIONS.md.

The backend must expose or stub these endpoints:

GET  /settings
POST /settings
POST /settings/test
DELETE /settings/credentials
POST /investigations/run
GET  /investigations/{id}
GET  /health

If implementing as Splunk REST handlers, adapt endpoint naming to Splunk conventions and document the actual endpoints.

Settings behavior

The backend should:

Accept provider/model/base URL/API key.
Store non-secret settings in an app-local Splunk conf file if appropriate.
Store API key in Splunk encrypted credential storage if possible.
Never return the API key.
Return only api_key_configured: true/false.
Redact secrets in logs.
Validate inputs.

If secure Splunk credential storage is too much to fully implement in this first pass, create a strongly documented adapter interface and a safe stub that refuses to store plaintext secrets unless explicitly running in local dev mode. Do not silently store plaintext secrets.

Agent orchestration behavior

Create a backend module structure similar to:

server/
  sentinel_mesh/
    __init__.py
    app.py
    config.py
    security.py
    settings_store.py
    splunk_client.py
    llm/
      __init__.py
      base.py
      anthropic_provider.py
      openrouter_provider.py
      openai_compatible_provider.py
    agents/
      __init__.py
      orchestrator.py
      triage_agent.py
      spl_hunter_agent.py
      timeline_agent.py
      blast_radius_agent.py
      detection_gap_agent.py
      response_agent.py
      executive_brief_agent.py
    demo/
      demo_case.py
      synthetic_events.py

Adapt paths if Splunk’s scaffold requires a different layout.

For the first pass, agents may be deterministic/stubbed but must have clean interfaces for future LLM integration.

Agent result schema

The investigation endpoint should return JSON similar to:

{
  "id": "demo-investigation-001",
  "status": "complete",
  "title": "Suspicious PowerShell on FIN-LAPTOP-22",
  "severity": "High",
  "confidence": 0.87,
  "summary": "Word spawned encoded PowerShell, followed by rare domain contact, finance file access, archive creation, and large outbound transfer.",
  "affected_entities": {
    "users": ["jsmith"],
    "hosts": ["FIN-LAPTOP-22", "FIN-FILE-01"],
    "domains": ["cdn-update-check.com"],
    "ips": ["185.199.108.153"],
    "files": ["Q2_finance_exports.zip"]
  },
  "mitre": [
    {
      "technique_id": "T1059.001",
      "name": "PowerShell",
      "confidence": 0.92,
      "evidence": "powershell.exe launched with encoded command"
    }
  ],
  "timeline": [
    {
      "time": "2026-05-18T09:16:22Z",
      "title": "Office spawned PowerShell",
      "description": "winword.exe launched powershell.exe with encoded command",
      "source": "endpoint",
      "severity": "high"
    }
  ],
  "evidence": [
    {
      "source": "endpoint",
      "time": "2026-05-18T09:16:22Z",
      "host": "FIN-LAPTOP-22",
      "user": "jsmith",
      "field": "command_line",
      "value": "powershell -enc ...",
      "interpretation": "Encoded PowerShell launched from Office parent process"
    }
  ],
  "response_plan": [
    {
      "action": "Isolate host",
      "target": "FIN-LAPTOP-22",
      "risk": "May interrupt user productivity",
      "requires_approval": true
    }
  ],
  "detection_recommendation": {
    "title": "Office-spawned encoded PowerShell",
    "spl": "index=endpoint process_name=powershell.exe (command_line=\"*-enc*\" OR command_line=\"*EncodedCommand*\") (parent_process_name=winword.exe OR parent_process_name=excel.exe OR parent_process_name=outlook.exe) | stats count min(_time) as first_seen max(_time) as last_seen by host user parent_process_name command_line",
    "description": "Detects suspicious Office child process behavior commonly associated with phishing payload execution.",
    "severity": "high",
    "mitre": ["T1059.001", "T1027"]
  }
}
Splunk data/search requirements

Add sample files under something like:

splunk/sample_data/endpoint_events.csv
splunk/sample_data/dns_events.csv
splunk/sample_data/auth_events.csv
splunk/sample_data/proxy_events.csv
splunk/sample_data/firewall_events.csv

Include realistic synthetic rows for the demo scenario.

Add example SPL files under:

splunk/spl/
  suspicious_powershell.spl
  rare_domain_after_execution.spl
  finance_file_access.spl
  outbound_transfer.spl
  blast_radius_hunt.spl

Add optional config examples if appropriate:

splunk/config_examples/indexes.conf
splunk/config_examples/props.conf
splunk/config_examples/transforms.conf

Do not assume these configs are installed automatically unless documented.

LLM provider abstraction

Create an interface like:

class LLMProvider:
    def complete(self, messages, model=None, temperature=0.2, max_tokens=2048):
        raise NotImplementedError

    def test_connection(self):
        raise NotImplementedError

Providers:

Anthropic provider
OpenRouter provider
OpenAI-compatible provider

The first pass can stub external calls if dependencies are not installed, but the interface and config flow should be real.

Do not commit real keys.

Use environment variables only for local dev fallback, never as the primary Splunk app settings mechanism.

Security requirements

Implement or document these guardrails:

API keys must not be returned to frontend.
API keys must not be logged.
API keys must not be stored in repo files.
API keys must not be stored in browser localStorage/sessionStorage.
Settings page should show only a redacted configured/not-configured state.
Response actions are recommendations only in MVP.
No automatic destructive action.
All generated SPL should be visible before use.
LLM prompts should include a rule not to fabricate evidence.
Every incident conclusion must be tied to evidence from Splunk or synthetic demo data.
Add .gitignore entries for local secrets and generated files.
UI design requirements

Use a clean SOC-console design:

Main investigation page with cards/panels.
Severity badge.
Confidence score.
Agent progress list.
Timeline.
Evidence table.
Detection recommendation code block.
Response plan checklist.
Settings page with secure credential messaging.

Use Splunk UI Toolkit components where available, such as layout, buttons, inputs, tables, cards/panels, typography, and messages.

If the exact component names differ based on installed packages, inspect package.json and use available Splunk UI packages.

Development approach

Follow this process:

Inspect repo:
List files.
Read package.json.
Identify app structure.
Identify build/test commands.
Identify whether backend/server support already exists.
Create the docs artifacts first.
Make an architecture decision:
Splunk REST handler vs local FastAPI service vs hybrid.
Record it in docs/DECISIONS.md.
Add frontend pages/components.
Add backend stubs.
Add synthetic data and SPL examples.
Add README updates.
Run formatting/tests/build if available.
Append a final status entry to docs/CONTINUATION_LOG.md.
Commands and validation

Before changing files, inspect available scripts.

Try likely commands only if they exist:

npm install
npm run build
npm run test
npm run lint
npm run start
python -m pytest

Do not invent commands that are not in the repo without documenting them.

If a command fails, document:

Command
Error summary
Likely cause
Next fix

Do not hide failures.

README requirements

Update or create README.md with:

Project overview
Hackathon track
Architecture summary
Setup instructions
How to run frontend
How to run backend, if separate
How to configure LLM provider
How credentials are stored
How to load demo data into Splunk
Demo walkthrough
Repo structure
Known limitations
Next steps
Initial acceptance criteria

At the end of this first session, the repo should have:

Persistent docs under docs/
Initial React UI pages/components or stubs
Settings page UI
Backend service or handler stubs
LLM provider abstraction
Demo investigation endpoint or static JSON fallback
Synthetic sample data
Example SPL detections
README updated
Continuation log updated
No committed secrets
A clear path for the next coding-agent refresh
Important implementation preference

Favor simple, working, hackathon-friendly architecture over over-engineering.

However, keep interfaces clean so the project can evolve.

For example:

It is acceptable for the first demo to use deterministic agent outputs.
It is not acceptable to hardcode secrets.
It is acceptable to mock Splunk query results initially.
It is not acceptable to design the app in a way that cannot later query Splunk.
Suggested first architecture decision

You should inspect the repo before deciding, but a likely good initial approach is:

Frontend lives in the existing Splunk Create React app.
Backend agent service starts as a Python service under server/.
The backend has a storage abstraction:
SplunkSecureSettingsStore for real Splunk encrypted storage/passwords.
DevSettingsStore for local development that refuses plaintext secrets unless a clearly named dev-only env var enables it.
Frontend talks to backend through a small API client.
Later, package backend as a Splunk custom REST endpoint or appserver-compatible service if the scaffold supports it.

If you choose this or another approach, document it clearly.

Suggested UI routes

Adapt to existing routing, but aim for:

/
  Investigation
/settings
  Secure LLM settings
/about
  About Sentinel Mesh
Suggested visual layout

Investigation page:

+------------------------------------------------------+
| Sentinel Mesh                                        |
| From alert to evidence-backed response in minutes    |
+------------------------------------------------------+

[Investigation prompt input..........................]
[Host] [User] [Alert] [Time range] [Start Investigation]
[Load Suspicious PowerShell Demo]

+-------------------+ +-----------------------------+
| Agent Run Panel   | | Investigation Summary       |
+-------------------+ +-----------------------------+

+------------------------------------------------------+
| Incident Timeline                                    |
+------------------------------------------------------+

+-------------------------+ +--------------------------+
| Evidence Table          | | MITRE Mapping            |
+-------------------------+ +--------------------------+

+-------------------------+ +--------------------------+
| Response Plan           | | Detection Recommendation |
+-------------------------+ +--------------------------+
Demo investigation content

Use this deterministic demo result if the backend is not connected to Splunk yet:

{
  "id": "demo-investigation-001",
  "status": "complete",
  "title": "Suspicious PowerShell on FIN-LAPTOP-22",
  "severity": "High",
  "confidence": 0.87,
  "summary": "Microsoft Word spawned encoded PowerShell on FIN-LAPTOP-22. The host contacted a rare external domain, accessed a finance file server, created a ZIP archive, and transferred a large amount of data externally.",
  "affected_entities": {
    "users": ["jsmith"],
    "hosts": ["FIN-LAPTOP-22", "FIN-FILE-01"],
    "domains": ["cdn-update-check.com"],
    "ips": ["185.199.108.153"],
    "files": ["Q2_finance_exports.zip"]
  },
  "mitre": [
    {
      "technique_id": "T1059.001",
      "name": "PowerShell",
      "confidence": 0.92,
      "evidence": "powershell.exe launched with encoded command"
    },
    {
      "technique_id": "T1027",
      "name": "Obfuscated Files or Information",
      "confidence": 0.81,
      "evidence": "-EncodedCommand or -enc observed in command line"
    },
    {
      "technique_id": "T1105",
      "name": "Ingress Tool Transfer",
      "confidence": 0.76,
      "evidence": "Host contacted rare external domain after script execution"
    }
  ],
  "timeline": [
    {
      "time": "2026-05-18T09:14:10Z",
      "title": "Suspicious Office document opened",
      "description": "User jsmith opened a document shortly before process execution.",
      "source": "endpoint",
      "severity": "medium"
    },
    {
      "time": "2026-05-18T09:16:22Z",
      "title": "Office spawned encoded PowerShell",
      "description": "winword.exe launched powershell.exe with an encoded command.",
      "source": "endpoint",
      "severity": "high"
    },
    {
      "time": "2026-05-18T09:17:03Z",
      "title": "Rare domain contacted",
      "description": "FIN-LAPTOP-22 resolved cdn-update-check.com.",
      "source": "dns",
      "severity": "high"
    },
    {
      "time": "2026-05-18T09:35:44Z",
      "title": "Finance file server accessed",
      "description": "jsmith authenticated from FIN-LAPTOP-22 to FIN-FILE-01.",
      "source": "auth",
      "severity": "medium"
    },
    {
      "time": "2026-05-18T09:41:10Z",
      "title": "Finance archive created",
      "description": "Q2_finance_exports.zip was created on the endpoint.",
      "source": "endpoint",
      "severity": "high"
    },
    {
      "time": "2026-05-18T09:44:39Z",
      "title": "Large outbound transfer",
      "description": "Approximately 48 MB was sent to an unusual external IP.",
      "source": "proxy",
      "severity": "critical"
    }
  ],
  "evidence": [
    {
      "source": "endpoint",
      "time": "2026-05-18T09:16:22Z",
      "host": "FIN-LAPTOP-22",
      "user": "jsmith",
      "field": "process_chain",
      "value": "winword.exe -> powershell.exe",
      "interpretation": "Office spawning PowerShell is suspicious and often associated with phishing payloads."
    },
    {
      "source": "endpoint",
      "time": "2026-05-18T09:16:22Z",
      "host": "FIN-LAPTOP-22",
      "user": "jsmith",
      "field": "command_line",
      "value": "powershell -enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0...",
      "interpretation": "Encoded PowerShell indicates obfuscation."
    },
    {
      "source": "proxy",
      "time": "2026-05-18T09:44:39Z",
      "host": "FIN-LAPTOP-22",
      "user": "jsmith",
      "field": "bytes_out",
      "value": "48593422",
      "interpretation": "Large outbound transfer after archive creation suggests possible exfiltration."
    }
  ],
  "response_plan": [
    {
      "action": "Isolate host",
      "target": "FIN-LAPTOP-22",
      "risk": "May interrupt user productivity.",
      "requires_approval": true
    },
    {
      "action": "Disable active sessions",
      "target": "jsmith",
      "risk": "May interrupt legitimate access.",
      "requires_approval": true
    },
    {
      "action": "Block domain",
      "target": "cdn-update-check.com",
      "risk": "Low if domain is confirmed malicious or rare.",
      "requires_approval": true
    },
    {
      "action": "Hunt across environment",
      "target": "All hosts",
      "risk": "Read-only search.",
      "requires_approval": false
    }
  ],
  "detection_recommendation": {
    "title": "Office-spawned encoded PowerShell",
    "spl": "index=endpoint process_name=powershell.exe (command_line=\"*-enc*\" OR command_line=\"*EncodedCommand*\") (parent_process_name=winword.exe OR parent_process_name=excel.exe OR parent_process_name=outlook.exe) | stats count min(_time) as first_seen max(_time) as last_seen by host user parent_process_name command_line",
    "description": "Detects suspicious Office child process behavior commonly associated with phishing payload execution.",
    "severity": "high",
    "mitre": ["T1059.001", "T1027"]
  }
}
Final response from you after coding

When done, respond with:

Summary of what you changed.
Files created/modified.
Commands run and results.
Current runnable status.
Known limitations.
Recommended next steps.

Also make sure the same information is appended to docs/CONTINUATION_LOG.md.

Begin by inspecting the repository.
