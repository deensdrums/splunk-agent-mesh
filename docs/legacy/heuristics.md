# Legacy heuristics (pre-pivot)

These deterministic heuristics drove the v0 agents before the platform pivoted
to conf-driven LLM agents. They are archived here because they remain useful as
skill/tool seed material: as the mesh gains the ability to invoke tools, these
patterns become candidate built-in skills.

Full source is preserved in git history before commit c5c4e16.

---

## SPL templates (from `spl_hunter_agent.py`)

```spl
index=endpoint process_name=powershell.exe
  (command_line="*-enc*" OR command_line="*EncodedCommand*")
  {host_filter}
| table _time host user parent_process_name command_line
```

```spl
index=dns {host_filter}
| stats count by host query answer
| where count < 5
| table host query answer count
```

```spl
index=wineventlog EventCode=4624 Logon_Type=3 {user_filter}
| table _time host user dest_host
```

```spl
index=proxy {host_filter} bytes_out > 10000000
| table _time host user dest_ip bytes_out url
```

```spl
index=endpoint {host_filter}
  (target_filename="*.zip" OR target_filename="*.rar" OR target_filename="*.7z")
| table _time host user target_filename
```

## Triage severity keyword map (from `triage_agent.py`)

| Keyword(s) | Severity |
|---|---|
| `exfil`, `ransomware`, `lateral`, `critical` | Critical |
| `powershell`, `encoded`, `obfusc`, `malware`, `c2`, `beacon` | High |
| `suspicious`, `unusual`, `anomal` | Medium |
| _other_ | Low |

## Entity-extraction regexes (from `triage_agent.py`)

| Field | Pattern | Notes |
|---|---|---|
| Host | `\b([A-Z][A-Z0-9\-]{2,20})\b` | Too greedy — matched process names |
| User | `\b([a-z][a-z0-9]{2,15})\b` | Too greedy — matched common words |
| Domain | `\b[a-z0-9\-]+\.[a-z]{2,}\b` | OK |
| IP | `\b\d{1,3}(?:\.\d{1,3}){3}\b` | OK |

## MITRE map (from `executive_brief_agent.py`)

| Indicator | Technique | Confidence |
|---|---|---|
| `powershell.exe` + `-enc`/`encodedcommand` | T1059.001 PowerShell | 0.92 |
| `powershell.exe` + `-enc`/`encodedcommand` | T1027 Obfuscated Files or Information | 0.81 |
| DNS index + `first_seen_domain_days < 30` | T1105 Ingress Tool Transfer | 0.76 |
| `target_filename` ending `.zip`/`.rar` | T1560.001 Archive Collected Data | 0.80 |
| `bytes_out > 10_000_000` | T1041 Exfiltration Over C2 Channel | 0.83 |

## Detection templates (from `detection_gap_agent.py`)

**Office-spawned encoded PowerShell** — severity high, MITRE T1059.001, T1027
```spl
index=endpoint process_name=powershell.exe
  (command_line="*-enc*" OR command_line="*EncodedCommand*")
  (parent_process_name=winword.exe OR parent_process_name=excel.exe OR parent_process_name=outlook.exe)
| stats count min(_time) AS first_seen max(_time) AS last_seen
    BY host user parent_process_name command_line
```

**Unusually large outbound transfer** — severity high, MITRE T1041
```spl
index=proxy bytes_out > 10000000
| stats sum(bytes_out) AS total_bytes count BY host user dest_ip
| where total_bytes > 50000000
| sort -total_bytes
```

## Event-to-timeline classifier (from `timeline_agent.py`)

| Condition | Title |
|---|---|
| `process_name` + `parent_process_name` | `{parent} spawned {process}` |
| `query` (DNS) | `DNS query: {query}` |
| `event_id == 4624` + `dest_host` | `Authentication to {dest}` |
| `target_filename` | `File created: {filename}` |
| `bytes_out` | `Large outbound network transfer` |

## Response action templates (from `response_agent.py`)

- **Isolate host** — target: first compromised host. Requires approval.
- **Disable active sessions** — target: first compromised user. Requires approval.
- **Block domain** — target: first malicious domain. Requires approval.
- **Hunt across environment** — read-only, no approval needed.
- **Preserve forensic evidence** — added when severity is High/Critical.
