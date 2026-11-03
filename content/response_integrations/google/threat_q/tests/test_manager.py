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

from threat_q.core.ThreatQManager import ThreatQManager
from threat_q.tests.conftest import CONFIG


def test_enrich_ip_builds_correct_filter_payload(
    threatq_manager: ThreatQManager,
) -> None:
    """Verify `get_ip_object` methods build the correct `indicators/query` payload."""
    expected_method = "POST"
    expected_url: str = urljoin(
        f"https://{CONFIG['ServerAddress']}", "api/indicators/query"
    )
    expected_params = {"sort": "-updated_at", "limit": 25, "offset": 0}
    expected_headers = {"Authorization": "Bearer mock_access_token"}
    expected_payload = {
        "criteria": {},
        "filters": {
            "+and": [
                {"value": "1.1.1.1"},
                {
                    "+or": [{"type_name": "IP Address"}, {"type_name": "IPv6 Address"}]
                }
            ]
        }
    }

    threatq_manager.get_ip_object("1.1.1.1")

    threatq_manager.session.request.assert_called_with(
        expected_method,
        expected_url,
        params=expected_params,
        headers=expected_headers,
        json=expected_payload,
    )


def test_enrich_url_builds_correct_filter_payload(
    threatq_manager: ThreatQManager,
) -> None:
    """Verify `get_url_object` methods build the correct `indicators/query` payload."""
    expected_method = "POST"
    expected_url: str = urljoin(
        f"https://{CONFIG['ServerAddress']}", "api/indicators/query"
    )
    expected_params = {"sort": "-updated_at", "limit": 25, "offset": 0}
    expected_headers = {"Authorization": "Bearer mock_access_token"}
    expected_payload = {
        "criteria": {},
        "filters": {
            "+and": [
                {"value": "https://example.com"},
                {
                    "+or": [{"type_name": "URL"}]
                }
            ]
        }
    }

    threatq_manager.get_url_object("https://example.com")

    threatq_manager.session.request.assert_called_with(
        expected_method,
        expected_url,
        params=expected_params,
        headers=expected_headers,
        json=expected_payload,
    )


def test_enrich_email_builds_correct_filter_payload(
    threatq_manager: ThreatQManager,
) -> None:
    """Verify `get_email_object` methods build the correct `indicators/query`
     payload."""
    expected_method = "POST"
    expected_url: str = urljoin(
        f"https://{CONFIG['ServerAddress']}", "api/indicators/query"
    )
    expected_params = {"sort": "-updated_at", "limit": 25, "offset": 0}
    expected_headers = {"Authorization": "Bearer mock_access_token"}
    expected_payload = {
        "criteria": {},
        "filters": {
            "+and": [
                {"value": "email@example.com"},
                {
                    "+or": [{"type_name": "Email Address"}]
                }
            ]
        }
    }

    threatq_manager.get_email_object("email@example.com")

    threatq_manager.session.request.assert_called_with(
        expected_method,
        expected_url,
        params=expected_params,
        headers=expected_headers,
        json=expected_payload,
    )


def test_enrich_hash_builds_correct_filter_payload(
    threatq_manager: ThreatQManager,
) -> None:
    """Verify `get_hash_object` methods build the correct `indicators/query` payload."""
    expected_method = "POST"
    expected_url: str = urljoin(
        f"https://{CONFIG['ServerAddress']}", "api/indicators/query"
    )
    expected_params = {"sort": "-updated_at", "limit": 25, "offset": 0}
    expected_headers = {"Authorization": "Bearer mock_access_token"}
    expected_payload = {
        "criteria": {},
        "filters": {
            "+and": [
                {"value": "hash"},
                {
                    "+or": [
                        {"type_name": "MD5"},
                        {"type_name": "Fuzzy Hash"},
                        {"type_name": "GOST Hash"},
                        {"type_name": "Hash ION"},
                        {"type_name": "SHA-1"},
                        {"type_name": "SHA-256"},
                        {"type_name": "SHA-384"},
                        {"type_name": "SHA-512"},
                    ]
                }
            ]
        }
    }

    threatq_manager.get_hash_object("hash")

    threatq_manager.session.request.assert_called_with(
        expected_method,
        expected_url,
        params=expected_params,
        headers=expected_headers,
        json=expected_payload,
    )


def test_enrich_cve_builds_correct_filter_payload(
    threatq_manager: ThreatQManager,
) -> None:
    """Verify `get_cve_object` methods build the correct `indicators/query` payload."""
    expected_method = "POST"
    expected_url: str = urljoin(
        f"https://{CONFIG['ServerAddress']}", "api/indicators/query"
    )
    expected_params = {"sort": "-updated_at", "limit": 25, "offset": 0}
    expected_headers = {"Authorization": "Bearer mock_access_token"}
    expected_payload = {
        "criteria": {},
        "filters": {
            "+and": [
                {"value": "cve"},
                {
                    "+or": [{"type_name": "CVE"}]
                }
            ]
        }
    }

    threatq_manager.get_cve_object("cve")

    threatq_manager.session.request.assert_called_with(
        expected_method,
        expected_url,
        params=expected_params,
        headers=expected_headers,
        json=expected_payload,
    )
