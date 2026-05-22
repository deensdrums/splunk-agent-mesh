# Splunk Agent Mesh — 3-Minute Hackathon Demo Script

---

## [0:00] The Problem (20 seconds)

> "A SOC analyst gets an alert. PowerShell spawned from Word on a finance laptop. Is this a false positive, or is someone exfiltrating Q2 earnings data? Normally this is a 30-minute manual investigation — checking endpoint logs, DNS, auth logs, proxy data. Splunk Agent Mesh does it in seconds."

---

## [0:20] Launch Investigation (30 seconds)

- Open Splunk. Navigate to **Splunk Agent Mesh** tab.
- Click **"Load Suspicious PowerShell Demo"** — the form fills with:
  - Description: *"winword.exe spawned PowerShell with encoded command on FIN-LAPTOP-22. User jsmith. Possible exfiltration."*
  - Host: `FIN-LAPTOP-22`, User: `jsmith`
- Click **"Start Investigation"**.

> "Watch the agents work."

---

## [0:50] Show Agents Running (30 seconds)

- **Agent Run Panel** animates:
  - ✓ Triage Agent — entities extracted, severity: High
  - ✓ SPL Hunter Agent — 5 searches run, 47 events retrieved
  - ✓ Timeline Agent — 6 events correlated
  - ✓ Blast Radius Agent — 1 additional host identified
  - ✓ Detection Gap Agent — detection generated
  - ✓ Response Agent — 4 actions recommended
  - ✓ Executive Brief — report complete

> "Seven specialized agents, each with a defined job. In production these call Claude through our LLM provider abstraction."

---

## [1:20] Show Evidence (30 seconds)

- Scroll to **Evidence Table**.
- Point out: *winword.exe → powershell.exe process chain*
- Point out: *encoded command `powershell -enc SQB...`*
- Point out: *48 MB outbound transfer 30 minutes later*

> "Every finding comes from Splunk data. The agent can't fabricate evidence — it's a hard constraint in the prompt contract."

---

## [1:50] Show Timeline (20 seconds)

- Scroll to **Incident Timeline**.
- Walk through the 6 events from document open to exfiltration.

> "From suspicious document open at 9:14 to 48 MB leaving the network at 9:44. Thirty minutes from initial access to data out the door."

---

## [2:10] MITRE + Summary (20 seconds)

- Point to **Investigation Summary**: Severity **High**, Confidence **87%**.
- Point to MITRE techniques: T1059.001 PowerShell (92%), T1027 Obfuscation (81%), T1105 Ingress Tool Transfer (76%).

> "Automatically mapped to MITRE ATT&CK. Confidence scores reflect the evidence quality."

---

## [2:30] Response Plan (15 seconds)

- Show **Response Plan**: Isolate host, disable jsmith session, block domain, hunt across environment.
- Point out the approval flags: *every action requires analyst sign-off*.

> "Splunk Agent Mesh never takes action automatically. Every recommendation requires human approval."

---

## [2:45] Detection Recommendation (15 seconds)

- Show **Detection Recommendation** SPL code block.
- Highlight that it catches Office-spawned encoded PowerShell across all hosts.

> "And here's the bonus: Splunk Agent Mesh generates a reusable Splunk detection so this never goes undetected again. Copy, save, deploy."

---

## [3:00] Closing Line

> "From alert to evidence-backed response in minutes — with a detection rule you can deploy today. That's Splunk Agent Mesh."

---

## Demo Reset

To reset between runs:
1. Click the "×" on any investigation result to clear state.
2. Or refresh the page — investigation state is not persisted in MVP.
