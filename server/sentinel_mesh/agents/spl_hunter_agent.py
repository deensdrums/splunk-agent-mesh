"""SPL Hunter Agent — generates and runs targeted SPL searches."""

import logging

logger = logging.getLogger(__name__)

SPL_TEMPLATES = {
    "powershell_encoded": (
        'index=endpoint process_name=powershell.exe '
        '(command_line="*-enc*" OR command_line="*EncodedCommand*") '
        '{host_filter}'
        '| table _time host user parent_process_name command_line'
    ),
    "dns_rare_domain": (
        'index=dns {host_filter}'
        '| stats count by host query answer '
        '| where count < 5 '
        '| table host query answer count'
    ),
    "auth_lateral": (
        'index=wineventlog EventCode=4624 Logon_Type=3 {user_filter}'
        '| table _time host user dest_host'
    ),
    "outbound_large": (
        'index=proxy {host_filter} bytes_out > 10000000 '
        '| table _time host user dest_ip bytes_out url'
    ),
    "file_archive": (
        'index=endpoint {host_filter} (target_filename="*.zip" OR target_filename="*.rar" OR target_filename="*.7z") '
        '| table _time host user target_filename'
    ),
}


class SPLHunterAgent:
    def __init__(self, llm=None, splunk_client=None):
        self.llm = llm
        self.splunk = splunk_client

    def run(self, ctx: dict) -> dict:
        entities = ctx.get("entities", {})
        host = entities.get("hosts", [None])[0]
        user = entities.get("users", [None])[0]

        host_filter = f'host="{host}" ' if host else ''
        user_filter = f'user="{user}" ' if user else ''

        searches_run = []
        all_evidence = []

        for name, template in SPL_TEMPLATES.items():
            spl = template.format(host_filter=host_filter, user_filter=user_filter)
            if self.splunk:
                result = self.splunk.run_search(spl)
                searches_run.append({
                    "name": name,
                    "spl": spl,
                    "result_count": len(result.events),
                    "error": result.error,
                })
                all_evidence.extend(result.events)
            else:
                searches_run.append({"name": name, "spl": spl, "result_count": 0, "error": "No Splunk client"})

        logger.info("SPLHunterAgent: ran %d searches, retrieved %d events.", len(searches_run), len(all_evidence))
        return {"searches_run": searches_run, "raw_events": all_evidence, "events": all_evidence}
