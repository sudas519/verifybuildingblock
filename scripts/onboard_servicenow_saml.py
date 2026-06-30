#!/usr/bin/env python3
"""
Onboard ServiceNow SAML Application to IBM Verify
==================================================
Creates the SAML application from config/servicenow-saml.yaml, optionally
uploads a signing certificate, downloads the IdP metadata, and assigns
any configured groups.

Usage:
    python3 scripts/onboard_servicenow_saml.py

Environment Variables (copy .env.example to .env and fill in):
    IBM_VERIFY_TENANT_URL     - https://emeabuildlab.verify.ibm.com
    IBM_VERIFY_CLIENT_ID      - API client ID
    IBM_VERIFY_CLIENT_SECRET  - API client secret
    COMPANY_ID                - IBM Verify company ID

Dependencies:
    pip install requests pyyaml
"""

import os
import sys
import base64
import json
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

class IBMVerifyAuth:
    def __init__(self, tenant_url: str, client_id: str, client_secret: str):
        self.tenant_url = tenant_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._expiry: datetime = datetime.min

    def get_access_token(self) -> str:
        if self._token and self._expiry > datetime.now():
            return self._token

        resp = requests.post(
            f"{self.tenant_url}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600) - 60)
        return self._token

    def headers(self, accept: str = "application/json") -> dict:
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
            "Accept": accept,
        }


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    with open(path) as f:
        cfg = yaml.safe_load(f)

    company_id = os.getenv("COMPANY_ID")
    if not company_id:
        raise EnvironmentError("COMPANY_ID environment variable is not set")
    cfg["company_id"] = company_id
    return cfg


# ---------------------------------------------------------------------------
# Application management
# ---------------------------------------------------------------------------

def get_existing_application(auth: IBMVerifyAuth, name: str) -> dict | None:
    """Return existing application by name, or None if not found."""
    resp = requests.get(
        f"{auth.tenant_url}/v2.0/applications",
        headers=auth.headers(),
        params={"search": name},
        timeout=30,
    )
    resp.raise_for_status()
    apps = resp.json().get("applications", [])
    for app in apps:
        if app.get("name") == name:
            return app
    return None


def create_saml_application(auth: IBMVerifyAuth, cfg: dict) -> dict:
    """Create (or skip if exists) the SAML application."""
    existing = get_existing_application(auth, cfg["name"])
    if existing:
        print(f"  ⚠  Application '{cfg['name']}' already exists — skipping creation")
        print(f"     Application ID: {existing['id']}")
        return existing

    sso = cfg["sso"]
    payload = {
        "name": cfg["name"],
        "description": cfg.get("description", ""),
        "company": {"id": cfg["company_id"]},
        "sso": {
            "entityId": sso["entity_id"],
            "acsUrl": sso["acs_url"],
            "nameIdFormat": sso["name_id_format"],
            "signAssertion": sso.get("sign_assertion", True),
            "encryptAssertion": sso.get("encrypt_assertion", False),
            "signResponse": sso.get("sign_response", True),
            "signatureAlgorithm": sso.get("signature_algorithm", "RSA_SHA256"),
            "digestAlgorithm": sso.get("digest_algorithm", "SHA256"),
        },
        "attributeMapping": cfg.get("attribute_mapping", []),
    }

    # Only include SLO if configured
    if sso.get("slo_url"):
        payload["sso"]["sloUrl"] = sso["slo_url"]

    resp = requests.post(
        f"{auth.tenant_url}/v2.0/applications/saml",
        headers=auth.headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    app = resp.json()
    print(f"  ✓  Application created — ID: {app['id']}")
    return app


# ---------------------------------------------------------------------------
# Certificate upload
# ---------------------------------------------------------------------------

def upload_certificate(auth: IBMVerifyAuth, app_id: str, cert_cfg: dict) -> dict | None:
    cert_path = Path(cert_cfg["path"])
    if not cert_path.exists():
        print(f"  ⚠  Certificate not found at {cert_path} — skipping upload")
        return None

    cert_b64 = base64.b64encode(cert_path.read_bytes()).decode()
    resp = requests.post(
        f"{auth.tenant_url}/v2.0/applications/{app_id}/certificates",
        headers=auth.headers(),
        json={"certificate": cert_b64, "usage": cert_cfg.get("usage", "signing")},
        timeout=30,
    )
    resp.raise_for_status()
    cert_info = resp.json()
    print(f"  ✓  Certificate uploaded — ID: {cert_info['id']}")
    return cert_info


# ---------------------------------------------------------------------------
# IdP metadata download
# ---------------------------------------------------------------------------

def download_idp_metadata(auth: IBMVerifyAuth, app_id: str, output_path: str) -> None:
    resp = requests.get(
        f"{auth.tenant_url}/v2.0/applications/{app_id}/metadata",
        headers=auth.headers(accept="application/xml"),
        timeout=30,
    )
    resp.raise_for_status()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(resp.text)
    print(f"  ✓  IdP metadata saved → {output_path}")


# ---------------------------------------------------------------------------
# Group assignment
# ---------------------------------------------------------------------------

def assign_group(auth: IBMVerifyAuth, app_id: str, group_name: str) -> None:
    # Resolve group name → ID
    resp = requests.get(
        f"{auth.tenant_url}/v2.0/Groups",
        headers=auth.headers(),
        params={"filter": f'displayName eq "{group_name}"'},
        timeout=30,
    )
    resp.raise_for_status()
    groups = resp.json().get("Resources", [])
    if not groups:
        print(f"  ⚠  Group '{group_name}' not found — skipping")
        return

    group_id = groups[0]["id"]
    resp = requests.post(
        f"{auth.tenant_url}/v2.0/applications/{app_id}/entitlements",
        headers=auth.headers(),
        json={"groupId": group_id},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"  ✓  Group '{group_name}' assigned")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    required = [
        "IBM_VERIFY_TENANT_URL",
        "IBM_VERIFY_CLIENT_ID",
        "IBM_VERIFY_CLIENT_SECRET",
        "COMPANY_ID",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"✗ Missing environment variables: {', '.join(missing)}")
        print("  Copy .env.example to .env, fill in values, then: source .env")
        sys.exit(1)

    auth = IBMVerifyAuth(
        tenant_url=os.environ["IBM_VERIFY_TENANT_URL"],
        client_id=os.environ["IBM_VERIFY_CLIENT_ID"],
        client_secret=os.environ["IBM_VERIFY_CLIENT_SECRET"],
    )

    print("\n── Loading configuration ──────────────────────────────────")
    cfg = load_config("config/servicenow-saml.yaml")
    print(f"  Application : {cfg['name']}")
    print(f"  Entity ID   : {cfg['sso']['entity_id']}")
    print(f"  ACS URL     : {cfg['sso']['acs_url']}")
    print(f"  NameID      : {cfg['sso']['name_id_format']}")
    print(f"  Attributes  : {len(cfg.get('attribute_mapping', []))} mapped")

    print("\n── Creating SAML application ───────────────────────────────")
    app = create_saml_application(auth, cfg)
    app_id = app["id"]

    print("\n── Uploading certificate(s) ────────────────────────────────")
    for cert_cfg in cfg.get("certificates", []):
        upload_certificate(auth, app_id, cert_cfg)

    print("\n── Downloading IdP metadata ────────────────────────────────")
    download_idp_metadata(auth, app_id, "metadata/servicenow-idp-metadata.xml")

    print("\n── Assigning groups ────────────────────────────────────────")
    groups = cfg.get("user_assignment", {}).get("groups", [])
    if groups:
        for group in groups:
            assign_group(auth, app_id, group)
    else:
        print("  ℹ  No groups configured — add them to config/servicenow-saml.yaml")

    tenant = os.environ["IBM_VERIFY_TENANT_URL"].rstrip("/")
    print("\n══════════════════════════════════════════════════════════════")
    print("✓  ServiceNow SAML onboarding complete!")
    print("══════════════════════════════════════════════════════════════")
    print(f"\n  Application ID : {app_id}")
    print(f"  IdP Metadata   : metadata/servicenow-idp-metadata.xml")
    print(f"\n  IBM Verify IdP endpoints:")
    print(f"    SSO  : {tenant}/saml/sso/{app_id}")
    print(f"    SLO  : {tenant}/saml/slo/{app_id}")
    print(f"    Meta : {tenant}/saml/metadata/{app_id}")
    print(f"\n  Next steps:")
    print(f"    1. Import metadata/servicenow-idp-metadata.xml into ServiceNow")
    print(f"       (System Properties > SAML 2.0 Single Sign-On > Import IdP Metadata)")
    print(f"    2. Set the ServiceNow Entity ID to: https://servicenow.test.com")
    print(f"    3. Set the ACS URL in ServiceNow to:  https://servicenowagain.test.com")
    print(f"    4. Test SSO from ServiceNow or IBM Verify")
    print()


if __name__ == "__main__":
    main()
