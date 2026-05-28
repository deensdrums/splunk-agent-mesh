# Splunk Agent Mesh — 3-Minute Hackathon Demo Script

---

## [0:00] The Problem (20 seconds)

> "A SOC analyst gets an alert. PowerShell spawned from Word on a finance laptop. Is this a false positive, or is someone exfiltrating Q2 earnings data? Normally this is a 30-minute manual investigation — checking endpoint logs, DNS, auth logs, proxy data. Splunk Agent Mesh does it in seconds."

---

## [0:20] Launch Investigation (30 seconds)

- Open Splunk. Navigate to **Splunk Agent Mesh**.
- Type the investigation description (or click **"Load Suspicious PowerShell Demo"**).
- Click **"Start Investigation"**.

> "Watch the agents work — each section fills in as the agent completes."

---

## [0:50] Show Progressive Results (30 seconds)

- **Triage** section appears first — severity: High, entities extracted.
- **SPL Hunter** section follows — 2-4 searches proposed.
- As searches execute against Splunk, **charts appear inline** — column charts for timechart data, tables for listings.

> "Seven specialized agents, each with a defined job. They call Claude through our LLM provider abstraction, and they run real SPL searches against live Splunk data."

---

## [1:20] Show Live Search Results (30 seconds)

- Scroll to SPL Hunter artifacts — point out the Column charts rendered by `@splunk/visualizations`.
- Show the SPL query beneath each chart.
- Point out: these are real Splunk search results, not mocked data.

> "Every chart comes from a live Splunk search. The agent decides what to search AND how to visualize it — timechart data gets a column chart, categorical data gets a table."

---

## [1:50] Show Timeline + Blast Radius (20 seconds)

- Point to **Timeline** section — uses SPL Hunter's findings as context.
- Point to **Blast Radius** — identifies lateral movement risk.

> "Downstream agents see upstream findings. The timeline builds on the SPL Hunter's evidence. Blast radius considers the triage entities. It's a dependency graph, not independent silos."

---

## [2:10] Detection + Response (20 seconds)

- Show **Detection Gap** — a Splunk detection rule with the SPL inline.
- Show **Response** — prioritized actions, each requiring approval.

> "A reusable detection rule you can deploy today, plus a response plan where every action requires analyst sign-off. The system never acts autonomously."

---

## [2:30] Executive Brief + Platform Story (30 seconds)

- Show **Executive Brief** — plain-language summary, MITRE ATT&CK mapping, confidence score.
- Switch to `agents.conf` in an editor — show how each agent is just a stanza.

> "From alert to evidence-backed response in minutes. And the platform is just config — add a stanza, get a new agent. No code changes, no rebuild."

---

## [3:00] Closing Line

> "That's Splunk Agent Mesh — from alert to evidence-backed response in minutes, with live Splunk data, real AI reasoning, and a detection rule you can deploy today."

---

## Demo Reset

To reset between runs:
1. Click **Clear** to dismiss the current investigation.
2. Or refresh the page — investigation state is in-memory only.
