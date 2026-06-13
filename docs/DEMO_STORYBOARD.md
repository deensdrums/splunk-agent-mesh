# Splunk Agent Mesh — 3-Minute Hackathon Demo Script

The UI is a single streaming **Threat Hunter** transcript, not per-agent tabs.
Everything below maps to events as they appear in that transcript.

---

## [0:00] The Problem (20 seconds)

> "A SOC analyst gets an alert: PowerShell spawned from Word on a finance
> laptop. False positive, or someone exfiltrating Q2 earnings? Normally that's a
> 30-minute manual pivot across endpoint, DNS, auth, and proxy data. Splunk
> Agent Mesh runs that investigation live, in seconds."

---

## [0:20] Launch the Investigation (25 seconds)

- Open Splunk → **Splunk Agent Mesh**.
- Type the alert description, or click **"Run Demo Investigation"** for the
  canned Log4Shell scenario.

> "One agent — the Threat Hunter — owns this investigation. Watch it think,
> search, and report in a single stream."

---

## [0:45] Watch It Reason and Search (45 seconds)

- A **narration** card appears: the Threat Hunter states its plan.
- A **Splunk Search** card appears with the SPL it's running; the chart fills in
  **live** as preview rows stream back (column chart for the timechart).
- A **Result Summary** card follows, then a **Finding** card with structured
  fields (host, user, technique, confidence).

> "This isn't a canned script. It proposes one search at a time, runs it against
> live Splunk as *me* — my session, my access — sees the results, and reacts.
> The chart you're watching is real Splunk data."

---

## [1:30] Delegation and Reporting (35 seconds)

- A **Handoff** card appears: "Reporting agent requested."
- Then a **Result Summary** card: the Threat Hunter summarizing the report the
  internal reporting agent produced (severity, confidence, MITRE techniques).

> "When it's ready to write up, the Threat Hunter delegates to an internal
> reporting agent — then folds that report back into its own voice. The analyst
> always sees one coherent narrator, not a pile of agents."

---

## [2:05] The Close (25 seconds)

- A **Final** card lands: a plain-language summary plus a numbered list of
  recommended actions (isolate host, reset credentials, block the C2).
- Point to the **status bar** at the bottom: investigation `complete`, Threat
  Hunter `completed`, event count, investigation id.

> "From alert to an evidence-backed summary with recommended next steps — every
> action gated on analyst approval. The system investigates; it never acts on
> its own."

---

## [2:30] The Platform Story (30 seconds)

- Open `agents.conf` in an editor.
- Show the `[agent:spl_hunter]` stanza: `agent_mode = agentic`, the response
  contract in the system prompt; and the `executive_brief` sub-agent
  (`agent_role = subagent`).

> "The agent is configuration. Its behavior — the prompt, the model, whether
> it's user-facing or an internal sub-agent — is a stanza an admin can tune and
> reload. No code changes, no rebuild."

---

## [3:00] Closing Line

> "That's Splunk Agent Mesh — one Threat Hunter, live Splunk data, real
> reasoning, and a report you can act on in minutes."

---

## Demo Reset / Notes

- Click **Clear** to dismiss the current investigation, or refresh the page —
  investigation state is in-memory only.
- **Demo mode** needs no API key or Splunk connection: it streams a canned event
  sequence (narration → search → finding → handoff → final) plus one artifact,
  using the same wire shape as a live run.
- For a **live** run, the analyst must be signed into Splunk Web (the search
  runs as that session) and an LLM API key must be configured in Settings.
