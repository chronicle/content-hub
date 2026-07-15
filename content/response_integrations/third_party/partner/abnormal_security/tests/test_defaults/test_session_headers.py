from __future__ import annotations

from ...core.AbnormalManager import AbnormalManager
from ...core.constants import (
    HEADER_SOAR_INTEGRATION_ORIGIN,
    SOAR_INTEGRATION_ORIGIN,
    USER_AGENT,
)


class TestSessionHeaders:
    def _manager(self) -> AbnormalManager:
        return AbnormalManager(api_url="https://api.abnormalplatform.com", api_key="test-key")

    def test_soar_integration_origin_header_is_set(self) -> None:
        # The Abnormal SOAR API reads Soar-Integration-Origin to identify the
        # calling platform and apply the Google SecOps egress subnet allowlist.
        headers = self._manager().session.headers
        assert headers[HEADER_SOAR_INTEGRATION_ORIGIN] == SOAR_INTEGRATION_ORIGIN
        assert SOAR_INTEGRATION_ORIGIN == "Google SecOps"

    def test_auth_and_user_agent_headers_are_set(self) -> None:
        headers = self._manager().session.headers
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["User-Agent"] == USER_AGENT
