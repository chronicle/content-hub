from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from core.IPInfoManager import IPInfoManager, IPInfoManagerError


@pytest.fixture
def manager() -> IPInfoManager:
    return IPInfoManager(api_root="https://ipinfo.io/", token="test-token")


class TestGetIPInformationBatch:
    @pytest.mark.parametrize(
        ("bundle", "expected_url"),
        [
            ("Lite", "https://api.ipinfo.io/batch/lite"),
            ("Core", "https://api.ipinfo.io/batch"),
            ("Plus", "https://api.ipinfo.io/batch"),
            ("Max", "https://api.ipinfo.io/batch"),
        ],
    )
    def test_routes_to_correct_url_per_bundle(self, manager: IPInfoManager, bundle: str, expected_url: str) -> None:
        with patch.object(manager.session, "post", return_value=MagicMock(json=lambda: {})) as post:
            manager.get_ip_information_batch(["8.8.8.8"], bundle)

        post.assert_called_once_with(expected_url, json=["8.8.8.8"])

    def test_passes_ip_list_as_json_body(self, manager: IPInfoManager) -> None:
        ips = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
        with patch.object(manager.session, "post", return_value=MagicMock(json=lambda: {})) as post:
            manager.get_ip_information_batch(ips, "Core")

        _, kwargs = post.call_args
        assert kwargs["json"] == ips

    def test_returns_response_json_unchanged(self, manager: IPInfoManager) -> None:
        api_response = {
            "8.8.8.8": {"ip": "8.8.8.8", "geo": {"city": "Mountain View"}},
            "1.1.1.1": {"ip": "1.1.1.1", "geo": {"city": "Brisbane"}},
        }
        with patch.object(manager.session, "post", return_value=MagicMock(json=lambda: api_response)):
            result = manager.get_ip_information_batch(["8.8.8.8", "1.1.1.1"], "Core")

        assert result == api_response

    def test_bearer_auth_header_present_on_session(self, manager: IPInfoManager) -> None:
        assert manager.session.headers["Authorization"] == "Bearer test-token"

    def test_unknown_bundle_raises_manager_error(self, manager: IPInfoManager) -> None:
        with pytest.raises(IPInfoManagerError):
            manager.get_ip_information_batch(["8.8.8.8"], "Legacy")
