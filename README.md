# IBM Verify Onboarding

A configuration-as-code workspace for onboarding SAML and OIDC applications into IBM Verify, managing users, and automating tenant configuration via IBM Verify APIs.

Built to run with **[Bob](https://www.ibm.com/bob)** — the IBM AI assistant. Opening this workspace in Bob activates the **🔐 IBM Verify Onboarding** custom mode automatically.

---

## What's in this repo

```
.
├── .env.example                          ← Credential template — copy to .env
├── config/
│   └── servicenow-saml.yaml              ← SAML application configuration
├── docs/
│   └── servicenow-saml-integration.md    ← Integration runbook & troubleshooting guide
├── scripts/
│   └── onboard_servicenow_saml.py        ← Automation script — creates app via IBM Verify API
└── .bob/
    └── skills/
        ├── ibm-verify-app-onboarding/    ← Bob skill: SAML/OIDC app onboarding
        ├── ibm-verify-access-policy/     ← Bob skill: access policy configuration
        └── ibm-verify-user-lifecycle/    ← Bob skill: user onboarding & lifecycle
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- An IBM Verify tenant (e.g. `https://your-tenant.verify.ibm.com`)
- An API client in IBM Verify with `client_credentials` grant type
  - Navigate to **Security → API Access → API Clients**

### 1. Clone the repo

```bash
git clone https://github.com/sudas519/verifybuildingblock.git
cd verifybuildingblock
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```bash
IBM_VERIFY_TENANT_URL=https://your-tenant.verify.ibm.com
IBM_VERIFY_CLIENT_ID=your-api-client-id
IBM_VERIFY_CLIENT_SECRET=your-api-client-secret
COMPANY_ID=your-company-id
```

### 3. Install dependencies

```bash
pip install requests pyyaml
```



## Security Notes

- **Never commit `.env`** — it is in `.gitignore`
- **Never commit `certs/`** — store certificates in a secrets vault
- **Never commit `metadata/`** — contains tenant-specific IdP metadata
- Rotate your API client secret regularly (recommended: every 90 days)

---

## Support

For IBM Verify API documentation see [IBM Verify Docs](https://docs.verify.ibm.com).
