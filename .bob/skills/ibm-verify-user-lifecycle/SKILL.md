---
name: ibm-verify-user-lifecycle
description: Use when the user wants to manage user lifecycle in IBM Verify SaaS — creating, updating, searching, or deprovisioning Cloud Directory users or federated identities via the IBM Verify SCIM and REST APIs.
metadata:
  disable-model-invocation: true
  argument-hint: "[create|update|deprovision|search] [username-or-id]"
---

# IBM Verify SaaS — User Lifecycle Management

Follow these steps to create, update, search, or deprovision users in an IBM Verify SaaS tenant.

## Step 1 — Gather Prerequisites

Use `ask_followup_question` to collect the following:

- **Tenant URL** — e.g. `https://<tenant>.verify.ibm.com`
- **Operation** — create, update, search, or deprovision
- **API client credentials** — client ID and client secret with the `manageUsers` entitlement (read from env vars)
- **User identity source** — Cloud Directory or a federated identity provider
- **User details** relevant to the operation (see per-operation steps below)

Never hardcode credentials. Always read them from environment variables (`IBM_VERIFY_CLIENT_ID`, `IBM_VERIFY_CLIENT_SECRET`).

## Step 2 — Obtain an Access Token

Use `execute_command`:

```bash
curl -s -X POST "https://<tenant>.verify.ibm.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "client_id=${IBM_VERIFY_CLIENT_ID}" \
  --data-urlencode "client_secret=${IBM_VERIFY_CLIENT_SECRET}" \
  --data-urlencode "scope=openid"
```

Extract and store `access_token`. Re-authenticate on `401`.

## Step 3 — Execute the Requested Operation

### Create a User

POST to `/v2.0/Users` (SCIM 2.0 endpoint):

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "<username>",
  "name": {
    "givenName": "<first>",
    "familyName": "<last>"
  },
  "emails": [
    { "value": "<email>", "primary": true }
  ],
  "password": "<temp-password>",
  "active": true
}
```

Capture the returned `id` for future operations. The `password` field is only used for Cloud Directory users — omit it for federated sources.

### Search for a User

GET to `/v2.0/Users?filter=userName+eq+"<username>"` or use `id`-based lookup:

```
GET /v2.0/Users/<id>
```

Use `execute_command` with `curl`. Parse and display the `id`, `userName`, `active` status, and `emails` from the response.

### Update a User

PATCH to `/v2.0/Users/<id>` using SCIM patch operations:

```json
{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "replace",
      "path": "emails[type eq \"work\"].value",
      "value": "<new-email>"
    }
  ]
}
```

Supported `op` values: `add`, `replace`, `remove`. Build the Operations array from the user-provided change list.

### Disable a User (Soft Deprovision)

PATCH to `/v2.0/Users/<id>`:

```json
{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    { "op": "replace", "path": "active", "value": false }
  ]
}
```

This preserves the account and all associated data while preventing login.

### Delete a User (Hard Deprovision)

DELETE to `/v2.0/Users/<id>`.

⚠️ Warn the user that this is irreversible before executing. Use `ask_followup_question` to confirm. Only proceed on explicit confirmation.

### Bulk Operations

For bulk create/update/deprovision, use the SCIM bulk endpoint POST `/v2.0/Bulk`:

```json
{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
  "Operations": [
    { "method": "POST", "path": "/Users", "data": { ... } },
    { "method": "DELETE", "path": "/Users/<id>" }
  ]
}
```

Batch at most 100 operations per request. Parse the `Operations` array in the response to check per-operation status codes.

## Step 4 — Handle Errors

| HTTP Status | Meaning | Action |
|---|---|---|
| 400 | Invalid payload | Show the `detail` field from the SCIM error response to the user |
| 401 | Token expired | Re-authenticate and retry once |
| 403 | Insufficient entitlements | Inform user to verify `manageUsers` scope on API client |
| 404 | User not found | Confirm the `id` or `userName` and retry |
| 409 | Conflict (duplicate userName) | Surface the conflict detail; suggest updating instead |

## Step 5 — Report

Summarise the outcome:
- Operation performed and target user(s)
- Resulting user `id`, `userName`, `active` status
- Any warnings (e.g. federated users whose attributes are managed by the IdP)
- Next steps (e.g. sending the user a password reset email via `/v1.0/passwordactions`)
