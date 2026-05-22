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

## Non-Goals (MVP)
- Cross-agent context. Agents are independent in v1 — each sees only the original request, not other agents' outputs.
- Skills/tool use. The stanza format reserves a `skills =` field, but it's parsed and ignored in v1.
- Streaming. Agents run sequentially server-side and the response arrives as one payload. All tabs update at once.
- Automated response execution. All actions are recommendations requiring human approval.
- Multi-tenant or per-user mesh customization.

## Future Direction
The architecture leaves clean extension points for:
- **Skills**: stanzas reference named tools (`splunk_search`, `web_search`, …). The runtime resolves and invokes them.
- **Structured output**: agents emit JSON-in-markdown or mixed outputs; the `MarkdownView`'s code-block renderer registry routes them to rich components.
- **Cross-agent context**: optional `depends_on = ` per stanza so dependent agents see prior outputs.
- **Streaming**: SSE/WebSocket per-agent updates instead of one-shot response.
- **Multiple meshes**: app supports more than one mesh, selectable from the UI.

## Final Demo Experience
A user opens Splunk Agent Mesh in Splunk Web, clicks "Load Suspicious PowerShell Demo," and within seconds sees:
- The input card populated with the demo scenario.
- Seven agent tabs below, each populating with rich markdown — severity classification, recommended SPL searches, an incident timeline table, blast-radius hunts, a detection rule, a numbered response plan, and an executive summary with MITRE techniques.
- Each tab is keyed by the configured agent id; if an admin edits `agents.conf` to add an eighth agent, an eighth tab appears with no UI changes.
