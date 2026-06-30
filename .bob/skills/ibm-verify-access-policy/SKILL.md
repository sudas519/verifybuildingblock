---
name: ibm-verify-access-policy
description: Use when the user wants to author, configure, or deploy IBM Verify SaaS access policies — including risk-based authentication, step-up MFA rules, adaptive authentication, and assigning policies to applications.
metadata:
  disable-model-invocation: true
  argument-hint: "[policy-name]"
---

# IBM Verify SaaS — Access Policy Authoring & Deployment

Follow these steps to create and deploy an access policy in an IBM Verify SaaS tenant.

## Step 1 — Gather Prerequisites

Use `ask_followup_question` to collect:

- **Tenant URL** — e.g. `https://<tenant>.verify.ibm.com`
- **API client credentials** — client ID and client secret with the `manageAccessControl` entitlement (from env vars)
- **Policy goal** — e.g. "require MFA when risk score > 50", "step-up to TOTP for sensitive apps", "block access from high-risk countries"
- **Target application(s)** — the application ID(s) this policy will be assigned to
- **Fallback behaviour** — deny or allow if the policy engine cannot evaluate

Read credentials exclusively from environment variables (`IBM_VERIFY_CLIENT_ID`, `IBM_VERIFY_CLIENT_SECRET`).

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

## Step 3 — Choose the Policy Type

Present the options to the user if not already specified:

| Type | Use Case |
|---|---|
| **Risk-based** | Trigger step-up or deny based on a continuous risk score |
| **Step-up MFA** | Require a second factor for specific apps or operations |
| **Adaptive** | Combine device trust, network, and behaviour signals |
| **Time-based** | Restrict access to defined time windows |

Each type maps to different `conditions` in the policy payload (see Step 4).

## Step 4 — Author the Policy Payload

POST to `/v1.0/accesspolicies`. The general schema:

```json
{
  "name": "<policy-name>",
  "description": "<optional>",
  "enabled": true,
  "rules": [
    {
      "name": "<rule-name>",
      "conditions": [ ],
      "actions": [ ]
    }
  ],
  "defaultAction": {
    "type": "deny"
  }
}
```

### Risk-Based Policy (example)

```json
{
  "conditions": [
    {
      "attribute": "riskScore",
      "operator": "greaterThan",
      "value": 50
    }
  ],
  "actions": [
    {
      "type": "stepUpAuthentication",
      "method": "totp"
    }
  ]
}
```

### Step-Up MFA Policy (example)

```json
{
  "conditions": [
    {
      "attribute": "authenticationLevel",
      "operator": "lessThan",
      "value": 2
    }
  ],
  "actions": [
    {
      "type": "stepUpAuthentication",
      "method": "emailotp"
    }
  ]
}
```

### Adaptive / Network-Based Policy (example)

```json
{
  "conditions": [
    {
      "attribute": "ipRiskCategory",
      "operator": "in",
      "value": ["HIGH", "CRITICAL"]
    }
  ],
  "actions": [
    { "type": "deny" }
  ]
}
```

Build the rules array from the user's requirements. Use `write_file` to save the payload as a local JSON file for review before posting.

## Step 5 — Deploy the Policy

Use `execute_command` to POST the payload:

```bash
curl -s -X POST "https://<tenant>.verify.ibm.com/v1.0/accesspolicies" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @policy.json
```

Capture the returned policy `id`.

## Step 6 — Assign the Policy to Applications

PUT to `/v1.0/applications/<app-id>/accesspolicy`:

```json
{
  "policyId": "<policy-id>"
}
```

Repeat for each target application. Use `execute_command` for each assignment.

## Step 7 — Validate the Policy

1. GET `/v1.0/accesspolicies/<policy-id>` — confirm `enabled: true` and the rules match the authored payload.
2. GET `/v1.0/applications/<app-id>/accesspolicy` — confirm the policy is linked to each target application.
3. Advise the user to perform a live test login to the application and verify the expected step-up or deny behaviour triggers correctly.

## Step 8 — Handle Errors

| HTTP Status | Meaning | Action |
|---|---|---|
| 400 | Invalid policy schema | Show the `messageDescription` from the error body; correct the payload |
| 401 | Token expired | Re-authenticate and retry once |
| 403 | Missing entitlement | Verify `manageAccessControl` scope on the API client |
| 409 | Policy name conflict | Rename or update the existing policy |

## Step 9 — Report

Summarise the deployment:
- Policy name and ID
- Rules authored and their trigger conditions
- Actions configured (step-up method, deny, etc.)
- Applications the policy was assigned to
- Recommended live-test scenario the user should run to verify behaviour
