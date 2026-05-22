# Splunk Agent Mesh — Project Brief

## Project Name
Splunk Agent Mesh

## Hackathon Track
Security — Splunk Agentic Ops Hackathon

## One-Sentence Pitch
Splunk Agent Mesh turns a raw security alert into an evidence-backed investigation report with MITRE ATT&CK mapping, blast radius analysis, and response recommendations — in minutes, not hours.

## Problem
SOC analysts face alert fatigue and slow mean-time-to-investigate. Correlating endpoint, DNS, auth, and proxy telemetry across tools is manual, slow, and error-prone. A skilled analyst may spend 30–60 minutes on a single alert just to determine if it warrants escalation.

## Solution
Splunk Agent Mesh is an agentic AI copilot embedded inside Splunk. When an analyst describes an alert or enters an entity of interest, Splunk Agent Mesh:

1. Generates targeted SPL searches from context.
2. Runs those searches against Splunk security data.
3. Correlates evidence across data sources.
4. Builds a chronological incident timeline.
5. Maps observed behaviors to MITRE ATT&CK techniques.
6. Scores severity and confidence.
7. Identifies blast radius (other users/hosts affected).
8. Recommends human-approved containment and response actions.
9. Generates reusable Splunk detection logic.

All AI-generated conclusions are tied to evidence retrieved from Splunk — the agent is not permitted to fabricate findings.

## Target Users
- Tier 1 / Tier 2 SOC analysts
- Incident responders
- Detection engineers (for the generated detection logic)

## MVP Scope
- Single-page React UI inside Splunk Web
- Investigation input form (describe alert / enter host or user)
- Demo mode: deterministic investigation result for the synthetic PowerShell scenario
- Settings page: configure LLM provider and API key (stored in Splunk secure credential storage)
- Backend FastAPI service with stub agent orchestration
- LLM provider abstraction (Anthropic, OpenRouter, OpenAI-compatible)
- Synthetic sample data and SPL detection examples

## Non-Goals (MVP)
- Automated response execution (all actions are recommendations requiring human approval)
- Real-time streaming of SPL results
- Multi-tenant or enterprise auth beyond Splunk's built-in auth
- Mobile/responsive layout
- Agent memory across sessions (stateless per investigation in MVP)

## Final Demo Experience
An analyst opens the Splunk Agent Mesh tab in Splunk, clicks "Load Suspicious PowerShell Demo," and within seconds sees:
- An agent progress feed showing each investigative step
- A severity High / 87% confidence summary
- A 6-event timeline from Office document open to data exfiltration
- MITRE ATT&CK techniques with confidence scores
- An evidence table with source, host, user, field, value, and interpretation
- A 4-action response plan with approval requirements
- A copy-paste SPL detection rule for Office-spawned encoded PowerShell
