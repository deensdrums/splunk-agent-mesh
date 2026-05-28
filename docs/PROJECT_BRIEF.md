# Splunk Agent Mesh — Project Brief

## Project Name
Splunk Agent Mesh

## Hackathon Track
Splunk Agentic Ops Hackathon

## One-Sentence Pitch
Splunk Agent Mesh is a configurable agentic platform that runs inside Splunk Enterprise — define a mesh of AI agents in `agents.conf`, give them a user request, and each one writes back to the page.

## Problem
Multi-agent AI systems are useful but typically require code to add or tune an agent. Splunk operators want to compose agent meshes the same way they compose searches, lookups, and inputs: via stanza-based configuration that they can edit, version, and reload without touching code.

## Solution
Splunk Agent Mesh ships:
- A generic `LLMAgent` runtime that reads its behavior — display name, system prompt, model, temperature, order — from `[agent:<id>]` stanzas in `agents.conf`.
- A Splunk app UI that renders one tab per configured agent. Each agent emits markdown; the page sanitizes and renders it.
- A backend that integrates with Splunk Enterprise via the REST API for conf reads, credential storage, and (future) search execution.

The first example mesh is a SOC investigation mesh: triage, SPL hunter, timeline, blast radius, detection gap, response, executive brief. New meshes (cost-optimization, capacity planning, on-call triage, etc.) are just new sets of stanzas.

## Target Users
- Splunk admins composing agent meshes for their own teams.
- SOC analysts using the bundled SOC mesh.
- Detection engineers consuming the SPL/detection outputs.

## MVP Scope
- Splunk app with three top-level views: Investigation, Settings, About.
- Investigation view: input card (description + host + user + alert + time range), plus a tabbed area below — one tab per configured agent.
- `agents.conf` with seven SOC-flavored agent stanzas as the first example mesh.
- Agents emit markdown. The UI renders with `react-markdown` + sanitization.
- FastAPI backend reads `agents.conf` via Splunk REST API (file fallback for dev).
- LLM provider abstraction: Anthropic, OpenRouter, OpenAI-compatible.
- Deterministic demo mode that mirrors the configured mesh with canned markdown.

## Non-Goals (current scope)
- Automated response execution. All actions are recommendations requiring human approval.
- Multi-tenant or per-user mesh customization.
- Parallel agent execution (architecturally possible via DAG depth, not yet implemented).

## Implemented Features
- **Skills**: `splunk_search` skill — agents emit fenced SPL blocks, orchestrator executes them, results render as interactive charts and tables.
- **Cross-agent context**: `depends_on` field — orchestrator builds a DAG and passes upstream outputs to dependent agents.
- **SSE streaming**: per-agent progressive rendering via Server-Sent Events.
- **Visualization hints**: agents control chart type via fence tag suffixes (`spl_column`, `spl_table`, etc.).
- **`@splunk/visualizations`**: Column, Line, Pie chart rendering from Splunk's official library.

## Future Direction
- **Additional skills**: `web_search`, `mitre_lookup` (resolves technique IDs).
- **Parallel execution**: agents at the same DAG depth could run concurrently.
- **Multiple meshes**: app supports more than one mesh, selectable from the UI.

## Final Demo Experience
A user opens Splunk Agent Mesh in Splunk Web, fills in an investigation description (or clicks "Load Suspicious PowerShell Demo"), and within seconds sees:
- Agent sections populating progressively via SSE streaming.
- Rich markdown in each section — severity classification, recommended SPL searches, an incident timeline table, blast-radius analysis, a detection rule, a numbered response plan, and an executive summary with MITRE techniques.
- Interactive charts (Column, Line, Pie) and data tables rendered inline from live Splunk search results.
- If an admin edits `agents.conf` to add an eighth agent, an eighth section appears in the report with no UI changes.
