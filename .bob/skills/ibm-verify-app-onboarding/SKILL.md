---
name: ibm-verify-app-onboarding
description: Use when the user wants to onboard a SAML or OIDC application into IBM Verify SaaS — covers creating the application via API, configuring SSO settings, managing certificates and metadata, setting up attribute mappings, and testing the authentication flow.
metadata:
  disable-model-invocation: true
  argument-hint: "[saml|oidc] [app-name]"
---

# IBM Verify SaaS — Application Onboarding

Follow these steps to onboard a SAML or OIDC application into an IBM Verify SaaS tenant.

## Step 1 — Gather Prerequisites

Use `ask_followup_question` to collect the following before making any API calls:

- **Tenant URL** — e.g. `https://<tenant>.verify.ibm.com`
- **Protocol** — SAML 2.0 or OIDC
- **Application name** and optional description
- **API client credentials** — client ID and client secret for a client with the `manageApplication` entitlement (store in env vars, never hardcode)
- For **SAML**: SP entity ID, ACS URL, NameID format, attribute requirements
- For **OIDC**: redirect URIs, grant types, scopes, PKCE requirement

Never proceed without a tenant URL and valid credentials.

## Step 2 — Obtain an Access Token

Use `execute_command` to fetch an OAuth 2.0 token from IBM Verify:

```bash
curl -s -X POST "https://<tenant>.verify.ibm.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "client_id=${IBM_VERIFY_CLIENT_ID}" \
  --data-urlencode "client_secret=${IBM_VERIFY_CLIENT_SECRET}" \
  --data-urlencode "scope=openid"
```

Extract the `access_token` from the response. Store it in a shell variable for subsequent calls. Tokens are short-lived — re-authenticate if a call returns `401`.

## Step 3 — Create the Application

### SAML Application

POST to `/v1.0/applications` with `protocol: SAML20`:

```json
{
  "name": "<app-name>",
  "description": "<optional>",
  "protocol": "SAML20",
  "samlConfiguration": {
    "entityID": "<sp-entity-id>",
    "acsURL": "<acs-url>",
    "nameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    "signAssertion": true,
    "encryptAssertion": false
  }
}
```

### OIDC Application

POST to `/v1.0/applications` with `protocol: OIDC10`:

```json
{
  "name": "<app-name>",
  "description": "<optional>",
  "protocol": "OIDC10",
  "oidcConfiguration": {
    "redirectUris": ["<redirect-uri>"],
    "grantTypes": ["authorization_code"],
    "responsTypes": ["code"],
    "pkce": {
      "enabled": true,
      "required": true
    },
    "scopes": ["openid", "profile", "email"]
  }
}
```

Use `execute_command` with `curl` to POST the payload. Capture the returned `id` — it is needed for all subsequent steps.

## Step 4 — Configure Attribute Mappings

PUT to `/v1.0/applications/<id>/attributemappings` to define what identity attributes are sent to the application:

```json
{
  "attributes": [
    { "name": "email", "value": "${User.email}" },
    { "name": "firstName", "value": "${User.name.givenName}" },
    { "name": "lastName", "value": "${User.name.familyName}" }
  ]
}
```

Adjust the `value` expressions to match the SP's requirements. IBM Verify uses `${User.<scim-attr>}` syntax for SCIM-sourced attributes.

## Step 5 — Export / Import Metadata (SAML only)

- **Download IdP metadata** (provide to the SP): GET `/v1.0/applications/<id>/saml20/metadata`
- **Upload SP metadata** (optional, auto-populates config): POST `/v1.0/applications/<id>/saml20/metadata` with the SP metadata XML as `Content-Type: application/xml`

Use `execute_command` for both. Save the IdP metadata to a local file for delivery to the application team.

## Step 6 — Assign Users or Groups

PUT to `/v1.0/applications/<id>/access` to grant access:

```json
{
  "type": "group",
  "groupIds": ["<group-id>"]
}
```

Or assign individual users by replacing `"type": "group"` with `"type": "user"` and `"userIds"`.

## Step 7 — Test the Authentication Flow

1. Use `execute_command` to initiate an SP-initiated or IdP-initiated flow and verify a successful redirect and token/assertion.
2. For OIDC: use the authorization code flow to exchange a code for tokens, then call `/userinfo` to verify claims.
3. For SAML: validate the assertion signature and NameID format match the SP requirements.
4. Check for `200` or redirect responses — any `4xx`/`5xx` indicates misconfiguration; surface the error body to the user.

## Step 8 — Report

Summarise what was created:
- Application name and ID
- Protocol and key configuration (ACS URL / redirect URIs)
- Attribute mappings configured
- Groups or users assigned
- IdP metadata location (SAML) or `client_id` (OIDC)

Flag any manual steps the application team must complete (e.g. importing IdP metadata into the SP).
