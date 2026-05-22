"""Static demo investigation result for the Suspicious PowerShell scenario."""

DEMO_RESULT = {
    "id": "demo-investigation-001",
    "status": "complete",
    "title": "Suspicious PowerShell on FIN-LAPTOP-22",
    "severity": "High",
    "confidence": 0.87,
    "summary": (
        "Microsoft Word spawned encoded PowerShell on FIN-LAPTOP-22. "
        "The host contacted a rare external domain, accessed a finance file server, "
        "created a ZIP archive, and transferred a large amount of data externally."
    ),
    "affected_entities": {
        "users": ["jsmith"],
        "hosts": ["FIN-LAPTOP-22", "FIN-FILE-01"],
        "domains": ["cdn-update-check.com"],
        "ips": ["185.199.108.153"],
        "files": ["Q2_finance_exports.zip"],
    },
    "mitre": [
        {
            "technique_id": "T1059.001",
            "name": "PowerShell",
            "confidence": 0.92,
            "evidence": "powershell.exe launched with encoded command",
        },
        {
            "technique_id": "T1027",
            "name": "Obfuscated Files or Information",
            "confidence": 0.81,
            "evidence": "-EncodedCommand or -enc observed in command line",
        },
        {
            "technique_id": "T1105",
            "name": "Ingress Tool Transfer",
            "confidence": 0.76,
            "evidence": "Host contacted rare external domain after script execution",
        },
    ],
    "timeline": [
        {
            "time": "2026-05-18T09:14:10Z",
            "title": "Suspicious Office document opened",
            "description": "User jsmith opened a document shortly before process execution.",
            "source": "endpoint",
            "severity": "medium",
        },
        {
            "time": "2026-05-18T09:16:22Z",
            "title": "Office spawned encoded PowerShell",
            "description": "winword.exe launched powershell.exe with an encoded command.",
            "source": "endpoint",
            "severity": "high",
        },
        {
            "time": "2026-05-18T09:17:03Z",
            "title": "Rare domain contacted",
            "description": "FIN-LAPTOP-22 resolved cdn-update-check.com.",
            "source": "dns",
            "severity": "high",
        },
        {
            "time": "2026-05-18T09:35:44Z",
            "title": "Finance file server accessed",
            "description": "jsmith authenticated from FIN-LAPTOP-22 to FIN-FILE-01.",
            "source": "auth",
            "severity": "medium",
        },
        {
            "time": "2026-05-18T09:41:10Z",
            "title": "Finance archive created",
            "description": "Q2_finance_exports.zip was created on the endpoint.",
            "source": "endpoint",
            "severity": "high",
        },
        {
            "time": "2026-05-18T09:44:39Z",
            "title": "Large outbound transfer",
            "description": "Approximately 48 MB was sent to an unusual external IP.",
            "source": "proxy",
            "severity": "critical",
        },
    ],
    "evidence": [
        {
            "source": "endpoint",
            "time": "2026-05-18T09:16:22Z",
            "host": "FIN-LAPTOP-22",
            "user": "jsmith",
            "field": "process_chain",
            "value": "winword.exe -> powershell.exe",
            "interpretation": "Office spawning PowerShell is suspicious and often associated with phishing payloads.",
        },
        {
            "source": "endpoint",
            "time": "2026-05-18T09:16:22Z",
            "host": "FIN-LAPTOP-22",
            "user": "jsmith",
            "field": "command_line",
            "value": "powershell -enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0...",
            "interpretation": "Encoded PowerShell indicates obfuscation.",
        },
        {
            "source": "dns",
            "time": "2026-05-18T09:17:03Z",
            "host": "FIN-LAPTOP-22",
            "user": "jsmith",
            "field": "query",
            "value": "cdn-update-check.com",
            "interpretation": "Domain is rare in environment — first seen in last 30 days.",
        },
        {
            "source": "auth",
            "time": "2026-05-18T09:35:44Z",
            "host": "FIN-LAPTOP-22",
            "user": "jsmith",
            "field": "dest_host",
            "value": "FIN-FILE-01",
            "interpretation": "jsmith accessed finance file server shortly after PowerShell execution.",
        },
        {
            "source": "endpoint",
            "time": "2026-05-18T09:41:10Z",
            "host": "FIN-LAPTOP-22",
            "user": "jsmith",
            "field": "file_name",
            "value": "Q2_finance_exports.zip",
            "interpretation": "Archive creation after file server access suggests data staging.",
        },
        {
            "source": "proxy",
            "time": "2026-05-18T09:44:39Z",
            "host": "FIN-LAPTOP-22",
            "user": "jsmith",
            "field": "bytes_out",
            "value": "48593422",
            "interpretation": "Large outbound transfer after archive creation suggests possible exfiltration.",
        },
    ],
    "response_plan": [
        {
            "action": "Isolate host",
            "target": "FIN-LAPTOP-22",
            "risk": "May interrupt user productivity.",
            "requires_approval": True,
        },
        {
            "action": "Disable active sessions",
            "target": "jsmith",
            "risk": "May interrupt legitimate access.",
            "requires_approval": True,
        },
        {
            "action": "Block domain",
            "target": "cdn-update-check.com",
            "risk": "Low if domain is confirmed malicious or rare.",
            "requires_approval": True,
        },
        {
            "action": "Hunt across environment",
            "target": "All hosts",
            "risk": "Read-only search.",
            "requires_approval": False,
        },
    ],
    "detection_recommendation": {
        "title": "Office-spawned encoded PowerShell",
        "spl": (
            'index=endpoint process_name=powershell.exe '
            '(command_line="*-enc*" OR command_line="*EncodedCommand*") '
            '(parent_process_name=winword.exe OR parent_process_name=excel.exe OR parent_process_name=outlook.exe) '
            '| stats count min(_time) as first_seen max(_time) as last_seen by host user parent_process_name command_line'
        ),
        "description": "Detects suspicious Office child process behavior commonly associated with phishing payload execution.",
        "severity": "high",
        "mitre": ["T1059.001", "T1027"],
    },
    "agent_errors": [],
}
