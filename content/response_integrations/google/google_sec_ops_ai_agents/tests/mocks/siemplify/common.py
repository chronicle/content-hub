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

import dataclasses
import pathlib
import time

from requests import HTTPError

from soar_sdk.SiemplifyDataModel import Alert
from TIPCommon.base.action import Action
from TIPCommon.consts import ACTION_TIMEOUT_THRESHOLD_IN_SEC, NUM_OF_MILLI_IN_MINUTE
from TIPCommon.data_models import AlertCard, SLA
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson

from integration_testing.common import get_def_file_content, set_is_first_run_to_true, set_is_first_run_to_false


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
MOCK_DATA_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_DATA_PATH)


class AlertFullDetails(Alert):
    def __init__(self, raw_data: SingleJson) -> None:
        self.raw_data = raw_data
        super().__init__(**raw_data)

    def to_json(self) -> SingleJson:
        return self.raw_data


class MockAttachmentResponse:
    """A simple mock of a requests.Response object for file downloads."""

    def __init__(self, content: bytes, status_code: int = 200):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self) -> None:
        """Raises :class:`HTTPError`, if one occurred."""
        if self.status_code >= 400:
            raise HTTPError(f"HTTP Error {self.status_code}", response=self)


@dataclasses.dataclass
class GeminiCaseSummary:
    raw_data: SingleJson
    _gemini_case_summary: bool = False

    @property
    def gemini_case_summary(self) -> bool:
        return self._gemini_case_summary

    @gemini_case_summary.setter
    def gemini_case_summary(self, value: bool) -> None:
        self._gemini_case_summary = value

    def to_json(self) -> SingleJson:
        return self.raw_data


def init_async_action(
    cls: type[Action],
    sync_timeout_ms: int = NUM_OF_MILLI_IN_MINUTE,
    async_timeout_ms: int = (NUM_OF_MILLI_IN_MINUTE * ACTION_TIMEOUT_THRESHOLD_IN_SEC),
) -> Action:
    """Init async action for tests."""
    set_is_first_run_to_true()
    action = cls()
    action.soar_action.script_timeout_deadline = unix_now() + sync_timeout_ms
    action.soar_action.execution_deadline_unix_time_ms = unix_now() + sync_timeout_ms
    action.soar_action.async_total_duration_deadline = unix_now() + async_timeout_ms

    return action


def minutes_from_now_to_ms(minutes: int) -> int:
    """
    Converts the given minutes from the current time into a Unix timestamp.

    Args:
        minutes (int): The number of minutes to add to the current time.

    Returns:
        int: The Unix timestamp in milliseconds representing the future time.
    """
    current_time_seconds: int = int(time.time())
    future_time_seconds: int = current_time_seconds + (minutes * 60)
    future_time_milliseconds: int = future_time_seconds * 1000

    return future_time_milliseconds


def calculate_future_time_milliseconds(milliseconds_to_add: int) -> int:
    """
    Calculates a future Unix timestamp (in milliseconds).

    Args:
        milliseconds_to_add: The remaining time in milliseconds to add
        to the current moment.

    Returns:
        int: The Unix timestamp in milliseconds representing the future time.
    """

    current_time_ms: int = unix_now()
    effective_remaining_time_ms = max(0, milliseconds_to_add)
    return current_time_ms + effective_remaining_time_ms


def calculate_remaining_time_ms(end_time_ms: int) -> int:
    """
    Calculates the remaining time in milliseconds until a specified end time.

    Args:
        end_time_ms: The end time as a Unix timestamp in milliseconds.

    Returns:
        The remaining time in milliseconds, or 0 if the end time has already passed.
    """
    current_time_ms = unix_now()
    return max(end_time_ms - current_time_ms, 0)


def build_sla_obj(
    sla_period_minutes: int | None = None,
    sla_critical_period_minutes: int | None = None,
    sla_remaining_time_since_last_pause_minutes: int | None = None,
) -> SLA:
    """
        Builds SLA object, can be used with current real time or fixed time.
    Args:
        sla_period_minutes: The SLA period in minutes.
        sla_critical_period_minutes: The SLA critical period in minutes.
        sla_remaining_time_since_last_pause_minutes: The SLA remaining time
        since last pause in minutes.

    Returns:
        SLA: The SLA object.
    """

    if sla_period_minutes is not None and sla_period_minutes is not None:
        return SLA(
            sla_expiration_time=minutes_from_now_to_ms(sla_period_minutes),
            critical_expiration_time=minutes_from_now_to_ms(
                sla_critical_period_minutes
            ),
            expiration_status=-1,
            remaining_time_since_last_pause=None,
        )

    return SLA(
        sla_expiration_time=None,
        critical_expiration_time=None,
        expiration_status=-1,
        remaining_time_since_last_pause=minutes_from_now_to_ms(
            sla_remaining_time_since_last_pause_minutes
        ),
    )


ALERT_IDENTIFIER: str = "SUSPICIOUS PHISHING EMAIL_E0BC6FDF-978E-4A11-9362-00696C3FC342"
ALERT_IDENTIFIER2: str = (
    "Phishing email detector3wM/eL7XV3hdthDGI3TUCzTZrm+gwID5DaLrxaRCT6U=_c8f65349-"
    "8519-4d4b-8aca-3e0075e61003"
)


ALERT_DATA: AlertCard = AlertCard.from_json(alert_card_json=MOCK_DATA.get("alertCards"))
ALERT_FULL_DETAILS = AlertFullDetails(MOCK_DATA.get("alert_full_details"))
FULL_ALERT_DATA: dict = MOCK_DATA.get("full alert_data")
CASE_META_DATA1: dict = MOCK_DATA.get("case_meta_data1")
CASE_META_DATA2: dict = MOCK_DATA.get("case_meta_data2")
GET_WALL_ACTIVITY: SingleJson = MOCK_DATA.get("get_wall_activity")
GEMINI_CASE_SUMMARY: GeminiCaseSummary = GeminiCaseSummary(
    MOCK_DATA.get("get_or_create_case_summary")
)
