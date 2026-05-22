# Splunk Agent Mesh — Agent Design

All agents are orchestrated by the `Orchestrator` and run sequentially in MVP. Each agent has a clean interface for future parallelization or LLM integration.

---

## Triage Agent

**Purpose**: Initial classification of the investigation request. Extracts entities (host, user, domain, IP), assesses urgency, and selects which downstream agents to invoke.

**Inputs**:
- `description`: str — natural language description of the alert
- `host`: str | None
- `user`: str | None
- `alert_name`: str | None
- `time_range`: str | None

**Outputs**:
```json
{
  "entities": { "users": [], "hosts": [], "domains": [], "ips": [] },
  "initial_severity": "Low | Medium | High | Critical",
  "agents_to_run": ["spl_hunter", "timeline", "blast_radius", "detection_gap", "response"],
  "triage_notes": "string"
}
```

**Prompt Contract** (when LLM-backed):
- Extract named entities from description.
- Classify initial severity based on alert keywords and entities.
- Do not fabricate entities not mentioned in input.
- Return structured JSON only.

**Tool Access**: None (input parsing only)

**Failure Behavior**: Return default entity extraction from structured fields (host/user). Log warning. Continue with remaining agents.

---

## SPL Hunter Agent

**Purpose**: Generate and execute targeted SPL searches to retrieve evidence from Splunk.

**Inputs**:
- Triage output (entities, time range)
- Splunk client handle

**Outputs**:
```json
{
  "searches_run": [
    { "name": "string", "spl": "string", "result_count": 0, "events": [] }
  ],
  "raw_evidence": []
}
```

**Prompt Contract** (when LLM-backed):
- Generate SPL that targets the provided entities.
- Prefer indexed fields over extracted fields.
- Add time range constraints from triage.
- Do not invent SPL functions that do not exist.
- Return only valid SPL.

**Tool Access**: `splunk_client.run_search(spl, earliest, latest)`

**Failure Behavior**: Return empty evidence set with search errors noted. Timeline and other agents continue with available data.

---

## Timeline Agent

**Purpose**: Correlate raw events from multiple sources into a chronological incident timeline.

**Inputs**:
- Raw evidence from SPL Hunter
- Triage entities

**Outputs**:
```json
{
  "timeline": [
    {
      "time": "ISO8601",
      "title": "string",
      "description": "string",
      "source": "endpoint|dns|auth|proxy|firewall",
      "severity": "low|medium|high|critical"
    }
  ]
}
```

**Prompt Contract** (when LLM-backed):
- Assign a meaningful title and description to each event.
- Do not invent events not present in raw evidence.
- Sort chronologically.
- Classify severity per event based on behavior indicators.

**Tool Access**: None (post-processing of evidence)

**Failure Behavior**: Return empty timeline. Surface raw evidence in evidence table instead.

---

## Blast Radius Agent

**Purpose**: Identify other users, hosts, or systems that may be affected by or connected to the incident.

**Inputs**:
- Triage entities
- Timeline events
- Splunk client handle

**Outputs**:
```json
{
  "additional_hosts": [],
  "additional_users": [],
  "lateral_movement_indicators": [],
  "blast_radius_summary": "string"
}
```

**Prompt Contract** (when LLM-backed):
- Search for lateral movement from known affected hosts.
- Look for shared credentials, shared network segments.
- Do not include entities without evidence.

**Tool Access**: `splunk_client.run_search(blast_radius_spl)`

**Failure Behavior**: Return empty additional entities. Note in summary.

---

## Detection Gap Agent

**Purpose**: Generate a reusable Splunk detection rule (SPL + metadata) based on the observed attack pattern.

**Inputs**:
- Timeline events
- MITRE technique mappings (from Triage or Blast Radius)
- Evidence records

**Outputs**:
```json
{
  "title": "string",
  "spl": "string",
  "description": "string",
  "severity": "string",
  "mitre": ["T1059.001"]
}
```

**Prompt Contract** (when LLM-backed):
- Generate SPL using standard Splunk search commands.
- Use indexed fields only.
- Include stats command to aggregate by relevant fields.
- Map to MITRE techniques present in evidence.
- Detection should be broadly applicable, not narrowly scoped to the specific incident.

**Tool Access**: None (generation only)

**Failure Behavior**: Return a generic detection template relevant to the attack class.

---

## Response Agent

**Purpose**: Generate a prioritized, human-approved response plan with specific actions and risks.

**Inputs**:
- Triage entities
- Timeline
- Blast radius results
- Severity score

**Outputs**:
```json
{
  "response_plan": [
    {
      "action": "string",
      "target": "string",
      "risk": "string",
      "requires_approval": true
    }
  ]
}
```

**Prompt Contract** (when LLM-backed):
- All actions require `requires_approval: true` unless they are passive/read-only.
- Do not recommend irreversible destructive actions without explicit risk note.
- Prioritize containment over eradication.
- Every action must reference a specific target entity.

**Tool Access**: None (recommendation only; no execution)

**Failure Behavior**: Return a minimal safe response plan (isolate, preserve evidence).

---

## Executive Brief Agent

**Purpose**: Synthesize the full investigation into a concise executive summary with severity, confidence, and key findings.

**Inputs**:
- All agent outputs
- Raw evidence count

**Outputs**:
```json
{
  "title": "string",
  "severity": "Low|Medium|High|Critical",
  "confidence": 0.87,
  "summary": "string",
  "mitre": [
    { "technique_id": "T1059.001", "name": "string", "confidence": 0.92, "evidence": "string" }
  ]
}
```

**Prompt Contract** (when LLM-backed):
- Confidence score must reflect actual evidence count and quality.
- Summary must cite specific entities and behaviors from evidence.
- Do not state conclusions not supported by evidence.
- MITRE techniques must be observed, not hypothetical.

**Tool Access**: None (synthesis only)

**Failure Behavior**: Return a minimal summary with `confidence: 0.0` and note insufficient evidence.

---

## Orchestrator

**Purpose**: Run agents in sequence, aggregate outputs, handle failures, and produce the final `InvestigationResult`.

**Run order** (MVP sequential):
1. TriageAgent
2. SPLHunterAgent
3. TimelineAgent
4. BlastRadiusAgent
5. DetectionGapAgent
6. ResponseAgent
7. ExecutiveBriefAgent

**Failure policy**: Each agent failure is caught and logged. Orchestration continues with whatever data is available. Final result includes an `agent_errors` list.

**Demo mode**: When `demo=true` is passed, the orchestrator returns the static `demo_case.py` result without running any agents or making any API calls.
