# ServiceNow SAML Integration — IBM Verify

## Overview

| Setting | Value |
|---|---|
| **IBM Verify Tenant** | `https://emeabuildlab.verify.ibm.com` |
| **SP Entity ID** | `https://servicenow.test.com` |
| **ACS URL** | `https://servicenowagain.test.com` |
| **NameID Format** | `emailAddress` |
| **Signature Algorithm** | `RSA-SHA256` |
| **Assertion Signed** | Yes |
| **Response Signed** | Yes |
| **Assertion Encrypted** | No |

---

## IBM Verify IdP Endpoints

Once the application is created, the following endpoints will be available:

| Endpoint | URL |
|---|---|
| **SSO (POST/Redirect)** | `https://emeabuildlab.verify.ibm.com/saml/sso/<app-id>` |
| **SLO** | `https://emeabuildlab.verify.ibm.com/saml/slo/<app-id>` |
| **IdP Metadata** | `https://emeabuildlab.verify.ibm.com/saml/metadata/<app-id>` |

> Replace `<app-id>` with the Application ID printed after running the onboarding script.

---

## Attribute Mapping

The following IBM Verify user attributes are included in every SAML assertion:

| IBM Verify Attribute | SAML Claim Name | Notes |
|---|---|---|
| `email` | `email` | Maps to NameID (emailAddress format) |
| `givenName` | `firstName` | |
| `familyName` | `lastName` | |
| `displayName` | `displayName` | |
| `mobileNumber` | `mobileNumber` | |
| `preferredLanguage` | `preferredLanguage` | |
| `jobTitle` | `jobTitle` | |
| `department` | `department` | |
| `organization` | `organization` | |

---

## Onboarding — Step by Step

### Prerequisites

1. Python 3.11+ installed
2. API Client created in IBM Verify:
   - Navigate to **Security → API Access → API Clients**
   - Grant type: `client_credentials`
   - Required scopes: `openid`, `applications`, `groups`
3. Your Company ID (visible in **Admin → Company Settings**)

### 1. Install dependencies

```bash
pip install requests pyyaml
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your real values
source .env
```

### 3. (Optional) Place SP signing certificate

If ServiceNow provides a signing certificate, place the PEM file at:

```
certs/servicenow-sp-signing.pem
```

If no certificate is available, the script will skip the upload step.

### 4. Run the onboarding script

```bash
python3 scripts/onboard_servicenow_saml.py
```

**Expected output:**

```
── Loading configuration ──────────────────────────────────
  Application : ServiceNow
  Entity ID   : https://servicenow.test.com
  ACS URL     : https://servicenowagain.test.com
  NameID      : urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress
  Attributes  : 9 mapped

── Creating SAML application ───────────────────────────────
  ✓  Application created — ID: abc123-...

── Downloading IdP metadata ────────────────────────────────
  ✓  IdP metadata saved → metadata/servicenow-idp-metadata.xml

══════════════════════════════════════════════════════════════
✓  ServiceNow SAML onboarding complete!
```

### 5. Configure ServiceNow

1. In ServiceNow go to **System Properties → SAML 2.0 Single Sign-On**
2. Click **Import IdP Metadata** and upload `metadata/servicenow-idp-metadata.xml`
3. Verify the following fields are auto-populated:

   | Field | Expected Value |
   |---|---|
   | Identity Provider's EntityID | IBM Verify tenant metadata entity ID |
   | Identity Provider's SingleSignOnService | IBM Verify SSO URL |
   | Identity Provider's certificate | Extracted from metadata |

4. Set **Service Provider's EntityID** to `https://servicenow.test.com`
5. Confirm **ACS URL** is `https://servicenowagain.test.com`
6. Map the `email` attribute to the ServiceNow user field `user_name` or `email`
7. Save and activate

---

## Testing the Integration

### SP-Initiated SSO

1. Navigate to the ServiceNow login page
2. Click **Log in with SSO**
3. You are redirected to `https://emeabuildlab.verify.ibm.com`
4. Authenticate with your IBM Verify credentials
5. You are redirected back to ServiceNow and logged in

### IdP-Initiated SSO (IBM Verify Launchpad)

1. Log in to `https://emeabuildlab.verify.ibm.com`
2. Open the **App Launchpad**
3. Click the **ServiceNow** tile
4. ServiceNow opens with an active session

### Validate the SAML Assertion

Use the browser's SAML tracer extension (e.g. SAML-tracer for Firefox/Chrome) to inspect the assertion and confirm:

- `NameID` is the user's email address
- All 9 attributes are present in `<AttributeStatement>`
- `<Signature>` is present on both the assertion and the response

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Invalid Signature` | Clock skew > 5 min | Synchronize clocks on SP and IdP |
| `AudienceRestriction` error | Entity ID mismatch | Confirm SP Entity ID is exactly `https://servicenow.test.com` |
| `Missing attribute` in ServiceNow | Attribute not populated on IBM Verify user | Populate the attribute on the user profile |
| `Access Denied` | User not entitled to app | Add user/group via IBM Verify → Application → Entitlements |
| Redirect loop | ACS URL mismatch | Confirm ACS URL is exactly `https://servicenowagain.test.com` |

---

## Maintenance

### Add user access

```bash
# Edit config/servicenow-saml.yaml
# Under user_assignment.groups, add group names, then re-run:
python3 scripts/onboard_servicenow_saml.py
```

### Certificate rotation

1. Obtain new SP certificate from ServiceNow
2. Replace `certs/servicenow-sp-signing.pem`
3. Re-run `python3 scripts/onboard_servicenow_saml.py`
4. Remove the old certificate from the IBM Verify application
5. Test SSO after rotation

### Update attribute mapping

Edit `config/servicenow-saml.yaml` under `attribute_mapping`, then re-run the script.

---

## File Structure

```
.
├── .env.example                        # Credential template (commit this)
├── .gitignore                          # Excludes .env, certs/, metadata/
├── config/
│   └── servicenow-saml.yaml            # Application configuration
├── scripts/
│   └── onboard_servicenow_saml.py      # Automation script
├── certs/                              # SP certificates (DO NOT COMMIT)
│   └── servicenow-sp-signing.pem
├── metadata/                           # Downloaded IdP metadata (auto-created)
│   └── servicenow-idp-metadata.xml
└── docs/
    └── servicenow-saml-integration.md  # This document
```
