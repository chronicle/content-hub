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

import pathlib
import pytest
from TIPCommon.types import SingleJson
from ..core.ZerofoxManager import ApiManager
from ..tests import common
from ..tests.core.product import Zerofox
from ..tests.core.session import ZerofoxSession


ALERT = common.LIST_ALERTS["alerts"][0]


class TestApiManager:
    """Unit tests for Integration's ApiManager methods."""

    def test_ping_success(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test ping success.

        Verify that the test_connectivity method successfully pings the Zerofox API and
        returns a 200 status code.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert = ALERT.copy()
        zerofox.add_alert(alert)

        manager.test_connectivity()

        assert len(script_session.request_history) == 1
        assert (
            script_session.request_history[0].request.real_url == common.LIST_ALERTS_URL
        )
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == zerofox.get_alerts()

    def test_ping_failure_invalid_token(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test ping failure due to invalid token.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert = ALERT.copy()
        alert["id"] = common.INVALID_ALERT_ID
        zerofox.add_alert(alert)
        with pytest.raises(Exception) as e:
            manager.test_connectivity()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 401
        assert script_session.request_history[0].response.json() == common.INVALID_TOKEN
        assert type(e.value).__name__ == "AuthenticationError"
        assert "Authentication failed: Invalid API token." in str(e.value)

    def test_add_note_to_alert_success(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test adding a note to an alert successfully.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        zerofox.add_alert(alert)
        alert_id: int = alert["id"]
        note: str = "Test Note"

        manager.add_note_to_alert(alert_id, note)

        assert zerofox.get_note(alert_id) == note
        assert len(script_session.request_history) == 1
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/append_notes/"
        )
        assert script_session.request_history[0].response.json() == {"notes": note}

    def test_add_note_to_alert_failure(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test adding a note to an alert failure.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        alert["id"] = alert_id = common.INVALID_ALERT_ID
        zerofox.add_alert(alert)
        note: str = "Test Note"

        with pytest.raises(Exception) as e:
            manager.add_note_to_alert(alert_id, note)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 403
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/append_notes/"
        )
        assert type(e.value).__name__ == "ZerofoxManagerError"
        assert "An error occurred: 403 Client Error:" in str(e.value)

    def test_close_alert_success(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test close alert successfully.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        zerofox.add_alert(alert)
        alert_id: int = alert["id"]

        manager.close_alert(alert_id)
        assert zerofox.get_alert(alert_id)["close"] is True
        assert len(script_session.request_history) == 1
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/close/"
        )

    def test_close_alert_failure(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test close alert failure.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        alert["id"] = alert_id = common.INVALID_ALERT_ID
        zerofox.add_alert(alert)

        with pytest.raises(Exception) as e:
            manager.close_alert(alert_id)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 403
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/close/"
        )
        assert type(e.value).__name__ == "ZerofoxManagerError"
        assert "An error occurred: 403 Client Error:" in str(e.value)

    def test_request_takedown_success(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test request takedown successfully.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        zerofox.add_alert(alert)
        alert_id: int = alert["id"]

        manager.request_takedown(alert_id)
        assert zerofox.get_alert(alert_id)["takedown"] is True
        assert len(script_session.request_history) == 1
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/request_takedown/"
        )

    def test_request_takedown_failure(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test request takedown failure.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        alert["id"] = alert_id = common.INVALID_ALERT_ID
        zerofox.add_alert(alert)

        with pytest.raises(Exception) as e:
            manager.request_takedown(alert_id)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 403
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/request_takedown/"
        )
        assert type(e.value).__name__ == "ZerofoxManagerError"
        assert "An error occurred: 403 Client Error:" in str(e.value)

    def test_add_evidence_to_alert_success(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test adding a evidence to an alert successfully.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        zerofox.add_alert(alert)
        alert_id: int = alert["id"]
        temp_file: str = common.create_temp_file()

        manager.add_evidence_to_alert(alert_id, temp_file)

        assert len(script_session.request_history) == 1
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/attachments/"
        )

    def test_add_evidence_to_alert_failure(
        self,
        manager: ApiManager,
        zerofox: Zerofox,
        script_session: ZerofoxSession,
    ) -> None:
        """Test adding a evidence to an alert failure.

        Args:
            manager (ApiManager): ApiManager object.
            zerofox (Zerofox): Zerofox product object.
            script_session (ZerofoxSession): ZerofoxSession object.
        """
        zerofox.cleanup_alerts()
        alert: SingleJson = ALERT.copy()
        alert["id"] = alert_id = common.INVALID_ALERT_ID
        zerofox.add_alert(alert)
        temp_file: str = common.create_temp_file()

        with pytest.raises(Exception) as e:
            manager.add_evidence_to_alert(alert_id, temp_file)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 403
        assert (
            script_session.request_history[0].request.real_url
            == f"/1.0/alerts/{alert_id}/attachments/"
        )
        assert type(e.value).__name__ == "ZerofoxManagerError"
        assert "An error occurred: 403 Client Error:" in str(e.value)
