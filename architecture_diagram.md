# Splunk Agent Mesh — Architecture Diagrams

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Splunk Agent Mesh UI (React)             │   │
│  │                                                      │   │
│  │  Investigation Console  │  Settings  │  History Rail  │   │
│  └──────────┬──────────────┴─────┬──────┴───────┬───────┘   │
│             │ SSE stream         │ REST          │ REST      │
└─────────────┼────────────────────┼──────────────┼───────────┘
              │                    │              │
     ┌────────┼────────────────────┼──────────────┼────────┐
     │ Splunk │Web (:8000)         │              │        │
     │  ┌─────┴──────────────┐     │              │        │
     │  │ agent_mesh_bridge  │     │              │        │
     │  │ (REST endpoint)    │     │              │        │
     │  │                    │     │              │        │
     │  │ Adds X-Splunk-User │     │              │        │
     │  │ + X-Splunk-Token   │     │              │        │
     │  └─────┬──────────────┘     │              │        │
     │        │ loopback           │              │        │
     │  ┌─────┴────────────────────┴──────────────┴─────┐  │
     │  │         uvicorn / FastAPI (:8765)              │  │
     │  │                                               │  │
     │  │  Orchestrator ─► AgenticLLMAgent (harness)    │  │
     │  │                    │              │            │  │
     │  │         SubagentRunner      SplunkClient      │  │
     │  │         (optimizer,         (dispatch/poll     │  │
     │  │          labeler,            live searches)    │  │
     │  │          reporter)               │            │  │
     │  │               │                  │            │  │
     │  └───────────────┼──────────────────┼────────────┘  │
     │                  │                  │               │
     │                  │           ┌──────┴──────┐        │
     │                  │           │  splunkd    │        │
     │                  │           │  (:8089)    │        │
     │                  │           │             │        │
     │                  │           │  Indexes:   │        │
     │                  │           │  endpoint   │        │
     │                  │           │  dns, auth  │        │
     │                  │           │  proxy, fw  │        │
     │                  │           │             │        │
     │                  │           │  KV Store   │        │
     │                  │           └─────────────┘        │
     └──────────────────┼──────────────────────────────────┘
                        │
                ┌───────┴───────┐
                │  Anthropic    │
                │  Claude API   │
                └───────────────┘
```

---

## LLM Agentic Loop

```
                    ┌──────────────┐
                    │  User starts │
                    │ investigation│
                    └──────┬───────┘
                           │
                           ▼
                ┌──────────────────────┐
                │  Orchestrator.run()  │
                │  Load agents.conf    │
                │  Split primary /     │
                │  subagent configs    │
                └──────────┬───────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │       AgenticLLMAgent.run()         │
         │   (Threat Hunter harness loop)      │
         └──────────────────┬──────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  Send system prompt +      │◄──────────────────┐
              │  conversation to Claude    │                   │
              └─────────────┬──────────────┘                   │
                            │                                  │
                            ▼                                  │
              ┌─────────────────────────────┐                  │
              │  Parse + validate response  │                  │
              │  (must be {"events": [...]})│                  │
              └─────────────┬───────────────┘                  │
                            │                                  │
                    ┌───────┴────────┐                         │
                    │ Valid JSON?    │──── No ──► Append        │
                    └───────┬────────┘       corrective msg ───┘
                            │ Yes                   (retry)
                            │
                            ▼
                ┌───────────────────────┐
                │  Stream events to UI  │
                │  (narration, finding, │
                │   splunk_search, etc) │
                └───────────┬───────────┘
                            │
                ┌───────────┴───────────┐
                │  Check LAST event     │
                └───────────┬───────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    ┌─────────────┐  ┌────────────┐  ┌─────────────┐
    │splunk_search│  │  handoff   │  │   final /   │
    │             │  │            │  │  no action  │
    └──────┬──────┘  └─────┬──────┘  └──────┬──────┘
           │               │                │
           ▼               ▼                │
  ┌────────────────┐ ┌──────────────┐       │
  │Search Optimizer│ │ Sub-agent    │       │
  │ (sub-agent,    │ │ (reporter)   │       │
  │  optional)     │ │              │       │
  │       │        │ │ Summarizes   │       │
  │       ▼        │ │ findings ──► │       │
  │ Execute SPL    │ │ report text  │       │
  │ against Splunk │ └──────┬───────┘       │
  │       │        │        │               │
  │  Preview rows  │        │               │
  │  stream to UI  │        │               │
  └───────┬────────┘        │               │
          │                 │               │
          ▼                 ▼               │
  ┌──────────────────────────────┐         │
  │  Append results to context,  │         │
  │  increment iteration         │         │
  │  (max_iterations budget)     │         │
  └──────────────┬───────────────┘         │
                 │                         │
                 └──────────► (loop) ──────┤
                                           │
                                           ▼
                             ┌──────────────────────┐
                             │  Post-final agents   │
                             │  (labeler, reporter  │
                             │   if not yet called) │
                             └──────────┬───────────┘
                                        │
                                        ▼
                             ┌──────────────────────┐
                             │  Return completed    │
                             │  investigation       │
                             │  (events + artifacts)│
                             └──────────────────────┘
```
