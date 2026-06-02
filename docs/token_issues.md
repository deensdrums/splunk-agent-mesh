# Token / Credential Storage — Findings

Notes from debugging the **502 on "save password"** and the follow-on design
discussion about where the LLM API key should live. Problem-solving notes, not
an implementation plan.

---

## The immediate bug (502 with an inner 401)

Symptom: saving the LLM key via
`…/splunkd/__raw/services/agent_mesh_bridge/api/v1/settings` returns **502**,
and the JSON body contains a **401 "not properly authenticated."**

It is **not** the bridge or the delegated browser session — those work; the
request reached the backend and got a structured reply. It's the
**credential-storage backend.**

Confirmed at runtime: `GET /api/v1/settings` reports
`storage_backend: "SplunkSecureSettingsStore"`. So `SPLUNK_TOKEN` is set in
uvicorn's environment, which auto-selects the Splunk Passwords store. The save
path is:

```
save_settings (returns 502)
  └─ store.store_api_key()                 [SplunkSecureSettingsStore]
       └─ POST …/storage/passwords  with  Authorization: Bearer <SPLUNK_TOKEN>
            └─ Splunk returns 401 "call not properly authenticated"  (token invalid/expired)
```

`store_api_key` raises `RuntimeError`; `app.py:save_settings` maps any storage
error to **HTTP 502** (`"Storage backend error: …"`); the bridge passes the 502
through verbatim. Hence "502 outer, 401 inner."

### Why it surprised us
- Setting `SPLUNK_TOKEN` (done for search / conf-reading) **silently also flips
  credential storage** to the Splunk Passwords path.
- The docs claim `SplunkSecureSettingsStore` is "stubbed, using DevSettingsStore"
  — it is **not** stubbed; it makes real Passwords API calls. Docs are wrong here.
- `save_settings` maps a Splunk **auth 401** to a **502**, which hides the real
  cause. A 401/403 passthrough would have made it obvious.

### Fixes (POC)
- **Easiest — skip the Splunk vault entirely:**
  `AGENT_MESH_USE_SPLUNK_STORE=0 AGENT_MESH_API_KEY=<key> uvicorn …`
  (forces `DevSettingsStore`; key read from env; nothing written to disk; no
  Splunk call). Restart uvicorn — env is read at import.
- To keep using the **Save** button instead: `AGENT_MESH_USE_SPLUNK_STORE=0
  AGENT_MESH_DEV_MODE=1` (persists to `server/.agent_mesh_settings.json`,
  gitignored).
- To actually use Splunk storage: issue a **fresh** Splunk auth token for a role
  with `edit_storage_passwords` + `list_storage_passwords` and set `SPLUNK_TOKEN`.

---

## "Why not just authenticate to that endpoint with the browser token?"

The endpoint isn't rejecting browser auth. There are **three hops**, and the
failing one doesn't use the browser token at all:

1. Browser → Splunk Web → bridge — uses the browser session. ✅
2. Bridge → uvicorn — forwards the user's session as `X-Splunk-Token`. ✅
3. **uvicorn → Splunk Passwords vault** — **ignores** the forwarded token and
   uses uvicorn's own static `SPLUNK_TOKEN` (Bearer), which is expired. ❌

So at the failing step the backend is *holding* the browser token and not using
it. We could wire it through, but there are real reasons it isn't:

- **Capability, not transport.** Writing to `storage/passwords` needs
  `edit_storage_passwords`; a normal analyst session usually lacks it. The
  service token exists so the app can store credentials regardless of who's
  logged in.
- **Shared app secret.** The LLM key is one app-level secret
  (`agent_mesh:llm_api_key`), not per-user, so "user saves their own credential"
  is a slight conceptual mismatch.
- **Auth-scheme detail.** A browser **session key** authenticates as
  `Authorization: Splunk <key>`; the vault code sends `Bearer <token>`. The
  search path solved this with an `auth_scheme`; the password path didn't.

---

## "Could a Splunk-side script do the write, like the bridge?" + "Can uvicorn read the vault?"

Two halves: the **write** (save) is the easy half; the **read** (retrieve at
investigation time) is the half that bites.

### Write — yes, mostly
An in-Splunk handler (like `agent_mesh_bridge.py`) could perform the password
write using the session Splunk hands it, removing the static token from uvicorn
for that operation. **But it doesn't bypass capabilities** — it just shifts
*whose* capabilities apply from the service-token role to the **logged-in
analyst's** role. Analysts often lack `edit_storage_passwords`, so this becomes
a permissions question, not a plumbing one. (Fine if the POC user is admin.)

### Read — the real problem (answer to "is there an issue with uvicorn reading the vault?")
**Yes, several:**

1. **Reading the decrypted key (`clear_password`) typically needs
   `admin_all_objects`** — a *higher* bar than writing. An analyst who can save a
   key often still can't read it back; a delegated analyst session almost
   certainly can't.
2. **Timing.** uvicorn needs the key *while running an investigation* (to call
   the LLM). So whatever identity reads the vault must be privileged **and
   present at run time** — i.e. a long-lived privileged Splunk session/token,
   exactly what delegation was trying to avoid.
3. **uvicorn is outside Splunk.** It can only read over REST with some
   credential; there's no in-process privileged shortcut an in-Splunk handler
   would have.

### Why search delegated cleanly but credentials don't
Running a search uses the analyst's **normal** capabilities (they can already
search). Reading/writing secrets needs **elevated** capabilities the analyst —
and ideally a standalone sidecar service — shouldn't casually hold. The
delegation pattern that works for search does not transfer to credentials.

---

## The underlying tension

Splunk's password vault is the right home for secrets **Splunk itself**
consumes. The LLM key is consumed by **uvicorn**, which lives outside Splunk.
Storing it in the vault forces uvicorn to read it back out, which means fighting
Splunk's RBAC (`admin_all_objects`, a privileged session at run time) for a
secret only the sidecar uses.

### Options
- **uvicorn owns its own key** (env var / its own secret store), never touches
  the vault. Cleanest given uvicorn is the consumer — the "dev store" path is
  arguably the *correct* model for a sidecar service, not just a POC shortcut.
- **Service token with proper capabilities** (current `SplunkSecureSettingsStore`
  intent). Works, but reintroduces a long-lived privileged token outside Splunk —
  and it's the thing currently broken.
- **In-Splunk write handler** (the proposal). Makes *saving* cleaner and removes
  the static token from the write path, but does **not** solve read-at-runtime
  and still depends on the logged-in user's capabilities.

Net: an in-Splunk handler can improve *saving*, but it doesn't escape the core
tension — a non-Splunk process needs a privileged path to read a Splunk-stored
secret. For the POC, "uvicorn holds the key" sidesteps all of it.

---

## Related cleanups worth doing later (not done here)
- Correct the docs (`SECURE_SETTINGS.md`, `DECISIONS.md`) that call
  `SplunkSecureSettingsStore` "stubbed" — it makes real calls and auto-activates
  whenever `SPLUNK_TOKEN` is set.
- Make `save_settings` pass through Splunk auth failures (401/403) instead of
  collapsing them to 502, so the real cause is visible.
