"""Canned per-agent markdown for demo mode.

The demo reads whichever agents are configured in agents.conf and returns
pre-written markdown for the ones it has content for. Unknown agents get a
placeholder so the demo never silently drops a tab.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..agents.agent_config import AgentConfig
from ..investigation_models import markdown_section


_DEMO_TIMESTAMP = "2026-05-21T18:00:00+00:00"


DEMO_MARKDOWN: dict[str, str] = {
    "triage": """## Severity: High

The described activity matches a typical post-exploitation chain: a finance
laptop executes encoded PowerShell after opening an Office document, then
contacts a rare external domain. This pattern is consistent with initial
access via phishing followed by command-and-control setup.

## Entities

- **Users**: `jsmith`
- **Hosts**: `FIN-LAPTOP-22`, `FIN-FILE-01`
- **Domains**: `cdn-update-check.com`
- **IPs**: `185.199.108.153`
- **Files**: `Q2_finance_exports.zip`

## Reasoning

`winword.exe` is rarely a legitimate parent of `powershell.exe`. The
`-EncodedCommand` flag is a strong obfuscation signal. Combined with the
follow-on DNS to a domain first seen <30 days ago, severity is **High**.
""",
    "spl_hunter": """## Recommended SPL searches

### 1. Encoded PowerShell on the host

```spl
index=endpoint host=FIN-LAPTOP-22 process_name=powershell.exe
  ("-enc" OR "-EncodedCommand")
| table _time host user parent_process_name command_line
```

### 2. Rare domain contact post-execution

```spl
index=dns host=FIN-LAPTOP-22
| stats earliest(_time) AS first_seen, count BY query
| where first_seen > relative_time(now(), "-30d")
```

### 3. Finance file-server access

```spl
index=auth dest_host=FIN-FILE-01 user=jsmith
| table _time src_host action
```

## Notes

These are starter queries — adapt the index names to your environment.
""",
    "timeline": """## Incident timeline

| Time (UTC) | Event |
|---|---|
| 14:02 | `jsmith` opens `Invoice_Q2.docx` from email attachment |
| 14:02 | `winword.exe` spawns `powershell.exe -EncodedCommand <b64>` |
| 14:03 | DNS lookup for `cdn-update-check.com` (first seen 6 days ago) |
| 14:05 | Outbound HTTPS to `185.199.108.153:443` |
| 14:08 | `jsmith` authenticates to `FIN-FILE-01` |
| 14:11 | `Q2_finance_exports.zip` created on `FIN-LAPTOP-22` |
| 14:14 | 48 MB transferred outbound |

The compressed sequence (~12 min) and absence of normal interactive activity
between steps strongly suggest scripted execution.
""",
    "blast_radius": """## Potential blast radius

### Directly affected

- `FIN-LAPTOP-22` — the originating host
- `FIN-FILE-01` — accessed via `jsmith` credentials
- `jsmith` — credentials may be exposed

### Recommended pivot searches

- Other hosts that resolved `cdn-update-check.com` in the last 7 days
- Other hosts where `winword.exe` spawned `powershell.exe -enc` in the last 30 days
- Any host where `jsmith` authenticated since the incident start

### Why this matters

A successful initial access can fan out quickly through shared credentials
and lateral movement. The pivot searches above bound the exposure.
""",
    "detection_gap": """## Recommended detection

**Title**: Encoded PowerShell spawned by Office application

```spl
index=endpoint process_name=powershell.exe
  parent_process_name IN ("winword.exe","excel.exe","outlook.exe","powerpnt.exe")
  ("-enc" OR "-EncodedCommand" OR "-e ")
| stats count BY host user parent_process_name command_line
```

**Severity**: high
**MITRE**: T1059.001 (PowerShell), T1027 (Obfuscation)

### Tuning notes

- Exclude known-good signed Office-add-in tooling by `command_line` substring.
- Roll into a notable in Enterprise Security once tuned.
""",
    "response": """## Recommended response actions

> All actions require analyst approval before execution.

1. **Isolate `FIN-LAPTOP-22`** from the corporate network.
   _Approval required: SOC lead._
2. **Disable `jsmith`** in the directory and force password reset.
   _Approval required: IAM team._
3. **Collect triage package** from `FIN-LAPTOP-22` (memory, prefetch, scheduled tasks, browser history).
   _Approval required: SOC analyst._
4. **Block `cdn-update-check.com`** at the proxy and `185.199.108.153` at the firewall.
   _Approval required: network team._
5. **Preserve mailbox** of `jsmith` for the last 30 days for phishing artifact review.
   _Approval required: legal hold lead._
""",
    "executive_brief": """## Executive summary

A finance laptop (`FIN-LAPTOP-22`) was used to open a malicious Office
document, execute obfuscated PowerShell, contact a newly-observed external
domain, access a finance file server with the user's credentials, and
exfiltrate roughly 48 MB of data to an external IP.

### Severity: High
### Confidence: 0.87

### MITRE ATT&CK

- **T1059.001** PowerShell — encoded command invocation
- **T1027** Obfuscated Files or Information — `-EncodedCommand` flag
- **T1105** Ingress Tool Transfer — rare domain contact post-execution
- **T1560.001** Archive Collected Data — `.zip` of finance exports
- **T1041** Exfiltration Over C2 Channel — 48 MB outbound transfer

### Recommended next steps

1. Host isolation and credential reset (see Response tab).
2. Detection rule rollout (see Detection Gap tab).
3. Blast-radius hunts across last 7 days (see Blast Radius tab).
""",
}


def _placeholder(display_name: str) -> str:
    return f"_No demo content configured for **{display_name}**._\n"


def build_demo_result(
    agents: list[AgentConfig],
    investigation_id: str = "demo-investigation-001",
    owner: str = "demo-user",
) -> dict:
    """Build a demo response that mirrors whichever agents are configured."""
    agent_order = [a.id for a in agents]
    outputs: dict[str, dict] = {}
    sections: list[dict] = []
    for cfg in agents:
        markdown = DEMO_MARKDOWN.get(cfg.id, _placeholder(cfg.display_name))
        outputs[cfg.id] = {
            "agent_id": cfg.id,
            "display_name": cfg.display_name,
            "status": "completed",
            "markdown": markdown,
            "model": cfg.model,
            "started_at": _DEMO_TIMESTAMP,
            "completed_at": _DEMO_TIMESTAMP,
            "error": None,
            "artifacts": [],
        }
        sections.append(markdown_section(f"section-{cfg.id}", cfg.display_name, markdown, cfg.id))
    return {
        "id": investigation_id,
        "owner": owner,
        "status": "complete",
        "started_at": _DEMO_TIMESTAMP,
        "completed_at": _DEMO_TIMESTAMP,
        "agent_order": agent_order,
        "agents": outputs,
        "sections": sections,
        "artifacts": [],
        "audit": [],
    }
