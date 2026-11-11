from __future__ import annotations

import pytest

from scc_enterprise.core.ServiceNowConsts import (
    DATETIME_FORMAT,
    DEFAULT_TZ,
)
from scc_enterprise.core.ServiceNowUtils import (
    convert_sn_time_to_unix_utc_timestamp,
)


class TestConvertServieNowTimeToUnixUtcTimestamp:

    def test_non_matching_time_str_and_format_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _ = convert_sn_time_to_unix_utc_timestamp(
                sn_tz=DEFAULT_TZ,
                ticket_time_field="2024-03-19 10:58:44",
                ticket_time_format="%Y/%m/%d %H:%M:%S",
            )

    def test_default_dashes_format_does_not_fail(self) -> None:
        timestamp: int = convert_sn_time_to_unix_utc_timestamp(
            sn_tz=DEFAULT_TZ,
            ticket_time_field="2024-03-19 10:58:44",
            ticket_time_format=DATETIME_FORMAT,
        )

        assert isinstance(timestamp, int) and timestamp > 0

    def test_slashes_format_does_not_fail(self) -> None:
        timestamp: int = convert_sn_time_to_unix_utc_timestamp(
            sn_tz=DEFAULT_TZ,
            ticket_time_field="2024/03/19 10:58:44",
            ticket_time_format="%Y/%m/%d %H:%M:%S",
        )

        assert isinstance(timestamp, int) and timestamp > 0

    def test_shifted_datetime_with_adjusted_sn_tz_map_to_the_same_utc_timestamp(
            self,
    ) -> None:
        timestamp_1: int = convert_sn_time_to_unix_utc_timestamp(
            sn_tz="America/Chicago",  # UTC - 5
            ticket_time_field="2019-03-04 14:38:00",  # timestamp
            ticket_time_format=DATETIME_FORMAT,
        )
        timestamp_2: int = convert_sn_time_to_unix_utc_timestamp(
            sn_tz="America/New_York",  # UTC -4
            ticket_time_field="2019-03-04 15:38:00",  # timestamp + 1 (= -4 - (-5))
            ticket_time_format=DATETIME_FORMAT,
        )

        assert timestamp_1 == timestamp_2

    def test_same_datetime_with_different_tz_info_results_in_non_matching_utc_timestamp(
            self,
    ) -> None:
        timestamp_1: int = convert_sn_time_to_unix_utc_timestamp(
            sn_tz="America/Chicago",  # UTC - 5
            ticket_time_field="2019-03-04 14:38:00",  # timestamp
            ticket_time_format=DATETIME_FORMAT,
        )
        timestamp_2: int = convert_sn_time_to_unix_utc_timestamp(
            sn_tz="America/New_York",  # UTC -4
            ticket_time_field="2019-03-04 14:38:00",  # same timestamp
            ticket_time_format=DATETIME_FORMAT,
        )

        tz_diff_in_hour: int = 1
        minutes_in_hour: int = 60
        seconds_in_minute: int = 60
        tz_delta_in_seconds: int = tz_diff_in_hour * minutes_in_hour * seconds_in_minute
        timestamp_diff: int = timestamp_1 - timestamp_2

        assert timestamp_diff == tz_delta_in_seconds
