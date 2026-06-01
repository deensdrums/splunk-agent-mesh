# agents.conf.spec
#
# This file describes the format of agents.conf, which defines the agents in
# the Splunk Agent Mesh.
#
# Each [agent:<id>] stanza configures one node in the mesh. Values can be
# overridden by setting them in $SPLUNK_HOME/etc/apps/splunk-agent-mesh/local/agents.conf.


[default]
* Default values applied to every [agent:*] stanza unless that stanza overrides them.

enabled = <boolean>
* Whether the agent is included in the mesh. Default: 1.

model = <string>
* The LLM model identifier passed through to the configured provider.
* Default: claude-sonnet-4-6.

temperature = <float>
* Sampling temperature (0.0-1.0). Lower = more deterministic. Default: 0.2.

max_tokens = <integer>
* Maximum tokens for the agent's response. Default: 2048.

output_format = markdown
* Reserved for future use. Only "markdown" is honored in v1.

agent_mode = <string>
* Execution mode. A primary (user-visible) agent must be "agentic": the harness
*   drives a think/search/observe loop, parsing the agent's JSON event stream
*   and executing one action per turn until it returns a final event.
* "single_shot" is the default value but has no execution path of its own; it is
*   the harmless default that sub-agents carry (sub-agents run via the primary
*   agent's handoff, calling the model directly).
* Default: single_shot.

max_iterations = <integer>
* Maximum number of harness loop turns for an agentic agent. Acts as a safety
* cap to prevent runaway loops.
* Default: 10.


[agent:<id>]
* One stanza per agent. The <id> portion is used as a stable identifier in the
* UI tabs, API responses, and demo data. It must be unique within the mesh.

display_name = <string>
* Human-readable name shown on the agent's tab. Default: the <id> portion.

description = <string>
* One-line description of what this agent does. Displayed in the UI on hover
* or in agent listings.

system_prompt = <string>
* The system prompt sent to the LLM. Use trailing backslashes to continue the
* value across multiple lines. Required — an agent with no system_prompt is
* skipped at read time with a warning.

order = <integer>
* Display and execution order. Lower values run first and appear leftmost in
* the tab list. Ties broken alphabetically by id. Default: 100.

skills = <comma-separated list>
* Lists named skills the agent may invoke. Currently supported:
*   splunk_search — the agent emits splunk_search events; the harness executes
*     each query against Splunk and attaches results as structured artifacts.
*     The event's payload.type (timechart, table, column, line, pie, single)
*     controls chart rendering.
