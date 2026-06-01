# Splunk Agent Mesh — Project Brief

## Project Name
Splunk Agent Mesh

## Hackathon Track
Splunk Agentic Ops Hackathon

## One-Sentence Pitch
Splunk Agent Mesh is an agentic SOC investigation copilot inside Splunk
Enterprise: describe an alert and a Threat Hunter agent investigates it live —
reasoning, running real SPL, and reporting — as a single streaming transcript.

## Problem
Alert triage is slow and manual. An analyst pivots across endpoint, DNS, auth,
proxy, and firewall data, forms hypotheses, and writes up findings — often 30+
minutes per alert. The reasoning is repeatable, but tooling rarely captures it.

## Solution
A single **Threat Hunter** agent runs a think → search → observe → report loop:

- It returns a strict **structured event stream** (`narration`,
  `splunk_search`, `result_summary`, `finding`, `handoff`, `final`) that a
  harness validates and acts on — proposing one action per turn, executing it
  against live Splunk, and feeding results back so the agent reacts to evidence.
- It delegates the written report to an internal **Reporting** sub-agent via a
  `handoff`, then summarizes that back into its own stream.
- The analyst sees one conversational transcript with inline charts and a live
  status bar — not a wall of disconnected agent tabs.

Agents are still defined as `agents.conf` stanzas, so the mesh is configurable;
the shipping mesh is intentionally focused on one visible agent plus one
internal sub-agent.

## Target Users
- SOC analysts triaging alerts.
- Detection engineers consuming the findings and recommended actions.
- Splunk admins who tune the agent via conf rather than code.

## How it works (at a glance)
- **Backend**: FastAPI (port 8765) reads `agents.conf` via Splunk REST, runs the
  agentic harness loop, executes searches with the analyst's delegated Splunk
  session, and streams structured events over SSE.
- **Frontend**: a React console that reveals events progressively, renders
  Splunk charts inline (`@splunk/visualizations`), and follows the live stream.
- **Auth**: in Splunk Web, requests flow through an authenticated
  `agent_mesh_bridge` REST endpoint; searches run as the analyst, and the
  browser fetches result rows directly from Splunk Web.

## MVP Scope
- Splunk app with three views: Investigation, Settings, About.
- Investigation view: an input card plus a single streaming Threat Hunter
  transcript with inline search artifacts and a status bar.
- `agents.conf` defining the Threat Hunter (primary, agentic) and the Reporting
  sub-agent, with five legacy SOC personas retained but disabled.
- LLM provider abstraction: Anthropic (active), OpenRouter, OpenAI-compatible.
- Deterministic demo mode with a canned event stream and one artifact.

## Non-Goals (current scope)
- Automated response execution — all actions are recommendations.
- Multi-tenant or per-user mesh customization.
- Multi-process / horizontally-scaled backend (single-process POC today).

## Implemented Features
- **Structured event contract** with harness-side validation and corrective
  retry.
- **Harness-driven agentic loop** (provider-agnostic; one action per turn;
  finalize-turn safety net).
- **Reporting sub-agent** invoked via `handoff` and summarized back.
- **Live, progressive Splunk search** with preview-row streaming and inline
  visualizations.
- **Delegated Splunk auth** via the REST bridge + signed SSE stream tokens +
  browser-side row fetching.
- **Console UI** with staggered event reveal and stick-to-bottom auto-follow.

## Future Direction
- Discovery tools for the agent (index/sourcetype/field summaries).
- A search-optimizer sub-agent that refines SPL before execution.
- Re-enabling specialized personas as additional primary agents when useful.
- Production credential storage (Splunk Passwords API) and multi-process
  hardening (shared stream-token secret + job store).

## Final Demo Experience
The analyst opens Splunk Agent Mesh, describes the alert (or clicks **Load
Suspicious PowerShell Demo**), and within seconds watches the Threat Hunter
work: it narrates its plan, runs SPL searches whose charts fill in live, calls
out findings, hands off to the reporting agent, and closes with a final summary
and recommended actions — all in one scrolling transcript.
