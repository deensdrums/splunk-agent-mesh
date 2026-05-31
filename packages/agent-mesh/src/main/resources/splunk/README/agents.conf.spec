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
* Execution mode for the agent. Values:
*   single_shot — one LLM call, tools run post-hoc (default).
*   agentic — iterative tool-use loop via the Anthropic tool-use API.
*     The agent calls tools, observes results, and iterates until it
*     stops calling tools or reaches max_iterations.
* Default: single_shot.

max_iterations = <integer>
* Maximum number of tool-use iterations for agentic agents. Ignored for
* single_shot agents. Acts as a safety cap to prevent runaway loops.
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
*   splunk_search — extracts fenced SPL blocks from the agent's markdown output,
*     executes them against Splunk, and attaches results as structured artifacts.
*     Agents should use visualization-hinted fence tags (spl_column, spl_table,
*     spl_line, spl_bar, spl_pie, spl_single) to control chart rendering.

depends_on = <comma-separated list>
* Optional list of agent ids that must complete before this agent runs.
* The orchestrator builds a DAG from these edges and executes in topological order.
* Dependent agents receive prior agent markdown outputs and artifact metadata
* as additional context in their request.
