# Durable Investigation Records

STATE-001 defined the durable Splunk KV Store record used by later history,
restore, and URL-addressable session work. STATE-002 implemented the repository
and runtime checkpointing. STATE-003 will add list/load APIs for the history
sidebar and should reuse this record shape.

## Decision

Store one document per investigation in a Splunk KV Store collection named
`agent_mesh_investigations`. The document preserves investigation metadata,
ownership, lifecycle state, the user-visible emitted event stream, artifact
metadata, and revision fields.

Splunk remains the source of truth for search result rows. Durable investigation
records store search SIDs and metadata, not preview or final row sets.

## Collection

Use `_key = investigation_id` so direct load by session ID is a single KV Store
lookup.

```conf
# default/collections.conf
[agent_mesh_investigations]
enforceTypes = false
replicate = true
```

Recommended accelerated lookups for list, ownership, status, and cleanup:

```conf
# default/transforms.conf
[agent_mesh_investigations_owner_updated]
collection = agent_mesh_investigations
fields_list = owner.username, updated_at

[agent_mesh_investigations_owner_status_updated]
collection = agent_mesh_investigations
fields_list = owner.username, status, updated_at

[agent_mesh_investigations_expires]
collection = agent_mesh_investigations
fields_list = expires_at
```

The collection is app-owned. Backend APIs enforce user visibility even if the
backend credential can technically read more documents.

## Record Schema

Example shape:

```json
{
  "_key": "inv-2f6c5f8a4b2c",
  "schema_version": 1,
  "investigation_id": "inv-2f6c5f8a4b2c",
  "owner": {
    "username": "admin",
    "display_name": null,
    "auth_source": "splunk_session"
  },
  "created_at": "2026-06-03T14:22:10Z",
  "updated_at": "2026-06-03T14:24:33Z",
  "started_at": "2026-06-03T14:22:10Z",
  "completed_at": null,
  "expires_at": "2026-07-03T14:22:10Z",
  "status": "running",
  "status_reason": null,
  "last_sequence": 12,
  "record_revision": 18,
  "request": {
    "description": "Investigate suspicious PowerShell activity.",
    "host": "web-01",
    "user": "alice",
    "alert_name": "Suspicious PowerShell",
    "time_range": "-24h",
    "demo": false
  },
  "summary": {
    "title": "Suspicious PowerShell activity",
    "first_event_title": "Starting investigation",
    "final_summary": null,
    "event_count": 12,
    "artifact_count": 3,
    "active_agent_id": "spl_hunter"
  },
  "agent_order": ["spl_hunter"],
  "agents": {
    "spl_hunter": {
      "agent_id": "spl_hunter",
      "display_name": "Threat Hunter",
      "status": "iterating",
      "phase": "interpreting",
      "started_at": "2026-06-03T14:22:10Z",
      "completed_at": null,
      "error": null,
      "model": "claude-haiku-4-5-20251001",
      "iteration": 4
    }
  },
  "events": [
    {
      "sequence": 1,
      "agent_id": "spl_hunter",
      "emitted_at": "2026-06-03T14:22:11Z",
      "event": {
        "type": "narration",
        "title": "Starting investigation",
        "text": "I will inspect recent process activity first.",
        "payload": {}
      }
    },
    {
      "sequence": 2,
      "agent_id": "spl_hunter",
      "emitted_at": "2026-06-03T14:22:18Z",
      "artifact_id": "artifact-f38d0a21c9b4",
      "event": {
        "type": "splunk_search",
        "title": "Search suspicious process activity",
        "text": "I am checking process creation events for encoded PowerShell.",
        "payload": {
          "query": "index=endpoint host=web-01 powershell",
          "purpose": "Find suspicious PowerShell command lines.",
          "type": "table"
        }
      }
    }
  ],
  "artifacts": [
    {
      "id": "artifact-f38d0a21c9b4",
      "agent_id": "spl_hunter",
      "created_at": "2026-06-03T14:22:18Z",
      "updated_at": "2026-06-03T14:22:50Z",
      "status": "running",
      "revision": 3,
      "type": "splunk_search",
      "title": "Search suspicious process activity",
      "purpose": "Find suspicious PowerShell command lines.",
      "spl": "index=endpoint host=web-01 powershell",
      "sid": "1748956938.42",
      "visualization": {
        "type": "table",
        "x": null,
        "y": null
      },
      "fields": ["_time", "host", "user", "process", "CommandLine"],
      "row_count": 250,
      "preview_available": true,
      "final_available": false,
      "error": null
    }
  ],
  "audit": [
    {
      "sequence": 1,
      "at": "2026-06-03T14:22:10Z",
      "type": "investigation_started",
      "actor": "admin",
      "detail": {}
    }
  ]
}
```

### Field Notes

- `schema_version` starts at `1` and gates future migrations.
- `status` is one of `pending`, `running`, `complete`, `failed`,
  `cancelled`, or `timed_out`.
- `last_sequence` is the highest durable event/audit sequence written.
- `record_revision` is the optimistic concurrency field owned by the backend.
- `events[].event` stores the full validated emitted event object, including
  payload fields that may not be rendered today, such as chart type, SPL,
  purpose, structured finding fields, or recommended actions.
- `artifacts[]` stores metadata needed to re-render or re-fetch results, not
  result rows.

## Not Stored

These values are intentionally excluded:

- Splunk session tokens. They are bearer credentials, expire independently, and
  should remain request/session scoped.
- LLM API keys and provider secrets. Those belong in the settings store, not
  investigation records.
- Transient preview rows from Splunk searches. Preview rows change frequently,
  can be large, and are already fetched directly by the browser from Splunk Web.
- Final search result rows by default. Splunk remains the source of truth; the
  durable record stores SID, SPL, fields, status, counts, and visualization
  metadata. Persisted row snapshots require a separate retention and size-limit
  story.
- Raw LLM prompts, hidden system prompts, or private conversation scratch state.
  The durable product record is the emitted event stream, not the private model
  transcript.
- Browser UI state such as scroll position, expanded panels, or open modals.
- Unredacted upstream exception bodies, request headers, or response bodies that
  may contain credentials or sensitive infrastructure detail.

## Retention

Default retention is 30 days. Each new record gets:

```text
expires_at = created_at + 30 days
```

Completed, failed, cancelled, and timed-out investigations remain loadable until
`expires_at`. Running investigations also receive `expires_at`, but stale
running records should be marked `timed_out` before normal expiry once timeout
handling is implemented.

STATE-003 should make list/load APIs filter expired records even before physical
deletion exists. Physical cleanup can be implemented opportunistically by the
backend on startup or before list queries for the POC. A production deployment
should prefer a scheduled Splunk-owned cleanup job or modular input.

## Per-User Visibility

The POC policy is per-user only:

- List and load APIs return records where `owner.username` equals the
  authenticated Splunk username.
- Demo and dev runs still set an owner, such as `dev-user`, and use the same
  ownership check.
- Admin/global history is out of scope until deliberately designed.

## Cancellation

Cancellation updates the existing record:

- `status = cancelled`
- `completed_at = now`
- `status_reason` explains who/what cancelled the run
- `record_revision` increments
- running artifacts move to `cancelled` when the harness can identify them

Already emitted events and artifact metadata remain durable. Cancellation does
not delete partial evidence.

## Partial Runs

Partial runs are first-class durable records. Failed or interrupted
investigations retain emitted events, artifact metadata, sanitized error state,
and the most recent agent status.

If uvicorn exits mid-run after persistence exists, the last checkpoint remains
loadable. A later timeout/recovery pass should mark stale `running` records as
`timed_out`.

## Checkpoint Timing

Runtime checkpointing now happens at these boundaries:

- record creation, after the investigation ID is assigned and before streaming
  begins
- each meaningful emitted event batch
- each artifact state transition: `pending`, `running`, `done`, `error`,
  `cancelled`, or `timed_out`
- each final investigation status transition: `complete`, `failed`,
  `cancelled`, or `timed_out`

KV Store writes should be bounded. SSE delivery should not wait indefinitely for
persistence. If a checkpoint fails, the backend should log it and surface a
clear persistence warning/status without corrupting the active stream.

## Concurrent Updates

The expected implementation has one active writer per investigation: the
running job. The repository still needs optimistic concurrency:

- `_key` is the investigation ID.
- `record_revision` increments on each successful checkpoint.
- `last_sequence` is monotonic and prevents duplicate event appends during
  retries.
- artifact updates are upserts by `artifact.id`; the highest artifact
  `revision` wins.
- on write conflict, reload the latest record, merge events/artifacts, increment
  `record_revision`, and retry with a bounded retry count.

This makes the later session-list and URL-restore APIs durable without requiring
the UI to understand conflict resolution.
