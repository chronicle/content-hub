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

"""Unit tests for FireEye ETP v2 parser and datamodels."""

from __future__ import annotations

from unittest.mock import MagicMock

from TIPCommon.transformation import dict_to_flat

from ..core.datamodels import Alert
from ..core.fire_eye_etp_manager import FireEyeETPConfig, FireEyeETPManager
from ..core.utils_manager import get_server_tzoffset, naive_time_converted_to_aware
from .mock_data import (
    MOCK_V2_ROOT_DETAIL_RESPONSE,
    MOCK_V2_WRAPPED_DETAIL_RESPONSE,
    SAMPLE_ALERTS,
)


def test_sample_alerts_parsing() -> None:
    """Verify that sample alert payloads parse correctly into Alert objects."""
    assert len(SAMPLE_ALERTS) > 0

    for raw_data in SAMPLE_ALERTS:
        alert = Alert(raw_data=raw_data, timezone_offset="0")
        assert alert.id is not None
        assert len(alert.id) > 0
        assert alert.timestamp is not None
        assert alert.severity is not None
        assert alert.priority in {40, 60, 80, 100}
        assert alert.etp_message_id is not None
        assert len(alert.etp_message_id) > 0
        assert alert.occurred_time_unix > 0

        # Verify malware extraction
        assert len(alert.malwares) >= 1
        first_malware = alert.malwares[0]
        assert "name" in first_malware
        assert "md5sum" in first_malware or "md5" in first_malware
        assert "sha256" in first_malware

        # Verify recipients extraction
        assert len(alert.recipients) >= 1

        # Verify events generation
        events = alert.events
        assert len(events) >= 1
        first_event = events[0]
        assert "alert" in first_event

        # Flatten event and verify key fields
        flat_event = dict_to_flat(first_event)
        assert "alert_id" in flat_event
        assert "md5sum" in flat_event or "md5" in flat_event
        assert "sha256" in flat_event

        # Verify recipient events
        recipient_events = alert.recipient_events
        assert len(recipient_events) == len(alert.recipients)
        assert recipient_events[0]["event_name"] == "FireEye ETP Recipient"


def test_manager_get_alert_details_handling() -> None:
    """Verify FireEyeETPManager.get_alert_details handles both root dict and {'data': dict}."""
    config = FireEyeETPConfig(
        api_root="https://etp.fireeye.com",
        api_key="dummy_key",
    )
    manager = FireEyeETPManager(config=config)

    # Mock session response for v2 root dict
    v2_root_response = MagicMock()
    v2_root_response.status_code = 200
    v2_root_response.json.return_value = MOCK_V2_ROOT_DETAIL_RESPONSE

    manager.session.get = MagicMock(return_value=v2_root_response)
    alert = manager.get_alert_details("alert-123", timezone_offset="0")
    assert alert.id == "alert-123"
    assert alert.severity == "majr"
    assert alert.priority == 80
    assert alert.etp_message_id == "<msg123>"
    assert len(alert.malwares) == 1
    assert len(alert.recipients) == 1

    # Mock session response for wrapped {'data': {...}}
    v2_wrapped_response = MagicMock()
    v2_wrapped_response.status_code = 200
    v2_wrapped_response.json.return_value = MOCK_V2_WRAPPED_DETAIL_RESPONSE
    manager.session.get = MagicMock(return_value=v2_wrapped_response)
    alert_wrapped = manager.get_alert_details("alert-456", timezone_offset="0")
    assert alert_wrapped.id == "alert-456"
    assert alert_wrapped.severity == "crit"
    assert alert_wrapped.priority == 100


def test_timezone_utilities() -> None:
    """Verify that get_server_tzoffset and naive_time_converted_to_aware handle edge cases."""
    # None timezone offset should default to 0
    tz_none = get_server_tzoffset(None)
    assert tz_none is not None

    # String, float, int offsets
    tz_str = get_server_tzoffset("2")
    assert tz_str is not None
    tz_neg = get_server_tzoffset("-5.5")
    assert tz_neg is not None

    # Compact timestamp format (14 digits)
    dt_compact = naive_time_converted_to_aware("20260820025319", "0")
    assert dt_compact.year == 2026
    assert dt_compact.month == 8
    assert dt_compact.day == 20
    assert dt_compact.hour == 2
    assert dt_compact.minute == 53
    assert dt_compact.second == 19

    # Standard ISO format
    dt_iso = naive_time_converted_to_aware("2026-08-20T02:54:32.000000", "0")
    assert dt_iso.year == 2026
    assert dt_iso.month == 8
    assert dt_iso.day == 20
