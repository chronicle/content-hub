from __future__ import annotations

import datetime

from TIPCommon.smp_time import change_timezone

from scc_enterprise.core.ServiceNowConsts import UTC_TZ


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
