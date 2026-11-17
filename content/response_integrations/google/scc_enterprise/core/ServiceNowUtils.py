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

import datetime

from TIPCommon.smp_time import change_timezone

from .ServiceNowConsts import UTC_TZ


def convert_sn_time_to_unix_utc_timestamp(
    sn_tz: str, ticket_time_field: str, ticket_time_format: str
) -> int:
    """Transform SN ISO time formatted string to unix timestamp in seconds

    This transformation takes the SN instance timezone into account
    when transforming

    Args:
        sn_tz: The ServiceNow server timezone
        ticket_time_field: the time to convert
        ticket_time_format: A date format string to parse `ticket_time_field`

    Returns:
        int: Unix timestamp in seconds
    """
    sn_dt = datetime.datetime.strptime(ticket_time_field, ticket_time_format)
    return int(change_timezone(sn_dt, sn_tz, UTC_TZ).timestamp())
