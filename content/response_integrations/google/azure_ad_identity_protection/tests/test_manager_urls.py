# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from urllib.parse import urljoin
from datetime import datetime

from azure_ad_identity_protection.tests.conftest import CONFIG
from azure_ad_identity_protection.core.AzureADIdentityProtectionManager import (
    AzureADIdentityProtectionManager,
)


CUSTOM_API_ROOT: str = CONFIG["API Root"].rstrip("/") + "/"
CUSTOM_LOGIN_ROOT: str = CONFIG["Login API Root"].rstrip("/") + "/"
TENANT_ID: str = CONFIG["Tenant ID"]

USER_ID: str = "test-user-id"
USERNAME: str = "user@example.com"


def test_get_auth_token_uses_login_root(
    aad_ip_manager: AzureADIdentityProtectionManager,
) -> None:
    """Checks that get_auth_token builds the URL using the Login API Root."""
    aad_ip_manager.get_auth_token()

    aad_ip_manager.session.post.assert_called_once()
    request_url: str = aad_ip_manager.session.post.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_LOGIN_ROOT,
        f"{TENANT_ID}/oauth2/v2.0/token"
    )
    assert request_url == expected_url


def test_test_connectivity_uses_api_root(
    aad_ip_manager: AzureADIdentityProtectionManager,
) -> None:
    """Checks that test_connectivity builds the URL using the API Root."""
    aad_ip_manager.test_connectivity()

    aad_ip_manager.session.get.assert_called_once()
    request_url: str = aad_ip_manager.session.get.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        "v1.0/identityProtection/riskDetections?top=1"
    )
    assert request_url == expected_url


def test_get_user_uses_api_root(
    aad_ip_manager: AzureADIdentityProtectionManager,
) -> None:
    """Checks that get_user builds the URL using the API Root."""
    aad_ip_manager.get_user(username=USERNAME, filter_key="userPrincipalName")

    aad_ip_manager.session.get.assert_called_once()
    request_url: str = aad_ip_manager.session.get.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        "v1.0/identityProtection/riskyUsers/"
    )
    assert request_url == expected_url


def test_update_user_state_to_compromised_uses_api_root(
    aad_ip_manager: AzureADIdentityProtectionManager,
) -> None:
    """Checks that update_user_state (compromised) builds the URL using the API Root."""
    aad_ip_manager.update_user_state(user_id=USER_ID, compromise=True)

    aad_ip_manager.session.post.assert_called_once()
    request_url: str = aad_ip_manager.session.post.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT, "v1.0/identityProtection/riskyUsers/confirmCompromised"
    )
    assert request_url == expected_url


def test_update_user_state_to_dismissed_uses_api_root(
    aad_ip_manager: AzureADIdentityProtectionManager,
) -> None:
    """Checks that update_user_state (dismissed) builds the URL using the API Root."""
    aad_ip_manager.update_user_state(user_id=USER_ID, compromise=False)

    aad_ip_manager.session.post.assert_called_once()
    request_url: str = aad_ip_manager.session.post.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT, "v1.0/identityProtection/riskyUsers/dismiss"
    )
    assert request_url == expected_url


def test_get_risk_detections_uses_api_root(
    aad_ip_manager: AzureADIdentityProtectionManager,
) -> None:
    """Checks that get_risk_detections builds the URL using the API Root."""
    aad_ip_manager.get_risk_detections(
        existing_ids=[], limit=10, start_timestamp=datetime.now(), lowest_severity="low"
    )

    aad_ip_manager.session.get.assert_called_once()
    request_url: str = aad_ip_manager.session.get.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        "v1.0/identityProtection/riskDetections"
    )
    assert request_url == expected_url
