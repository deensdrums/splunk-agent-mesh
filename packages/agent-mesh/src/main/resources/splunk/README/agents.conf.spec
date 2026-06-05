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

subagent_kind = <string>
* Internal capability type for `agent_role = subagent` stanzas.
* Supported values:
*   generic - a delegated capability with no special lifecycle behavior.
*   report - produces a user-facing investigation report event from completed
*     investigation context.
*   labeler - classifies the completed investigation using a strict JSON rubric.
*   search_optimizer - rewrites SPL before execution when it can preserve
*     investigation intent.
* Default: generic.

invoke_policy = <string>
* Controls when a sub-agent is invoked by the harness.
* Supported values:
*   on_handoff - invoked only when the primary agent emits a handoff event.
*   before_search - invoked before each splunk_search action. Intended for
*     subagent_kind = search_optimizer.
*   after_final - invoked after the primary agent produces its final event; the
*     harness inserts generated events before the final event in the returned
*     event stream.
*   disabled - configured but never invoked.
* Default: on_handoff.

output_contract = <string>
* Expected response shape for request/response sub-agent calls.
* Supported values:
*   markdown - freeform markdown/text response.
*   json - strict JSON response validated by the harness for built-in subagent
*     kinds such as labeler and search_optimizer.
* Default: markdown.

required = <boolean>
* Whether a sub-agent failure should be treated as required work. Required
* sub-agents emit a failure finding when they fail validation or execution.
* Default: 0.

failure_policy = <string>
* Controls harness behavior when a sub-agent fails.
* Supported values:
*   continue - suppress the failed optional sub-agent output and continue.
*   warn - reserved for future user-visible warning behavior; currently behaves
*     like continue.
*   fail_run - emit a failure finding for the failed sub-agent.
* Default: continue.


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
