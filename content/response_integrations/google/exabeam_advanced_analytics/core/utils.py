from __future__ import annotations
from typing import List, Optional

from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from .consts import HTML_LINK, BOLD_TITLE
from .exceptions import ExabeamAdvancedAnalyticsValidationError


def load_csv_to_list(csv: str, param_name: str) -> List[str]:
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise ExabeamAdvancedAnalyticsValidationError if failed to parse csv string
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise ExabeamAdvancedAnalyticsValidationError(
            f'Failed to parse parameter "{param_name}"'
        )


def get_users_watchlist_missing_items(
    usernames: List[str], users_watchlist
) -> List[str]:
    """
    Return missing usernames from Users watchlist
    :param usernames: {[str]} List of usernames to search if missing in a watchlist
    :param users_watchlist: {UsersWatchlistDetails} The watchlist to search for missing usernames
    :return: {[str]} List of missing usernames that were not found in users watchlist
    """
    return [
        username
        for username in usernames
        if username.lower() not in [item.username for item in users_watchlist.items]
    ]


def get_assets_watchlist_missing_items(
    endpoints: List[str], assets_watchlist
) -> List[str]:
    """
    Return missing endpoints from Assets watchlist
    :param endpoints: {[str]} List of endpoints to search if missing in a watchlist. Can be ip addresses or hostnames
    :param assets_watchlist: {AssetsWatchlistDetails} The watchlist to search for missing endpoints
    :return: {[str]} List of missing endpoints that were not found in users watchlist
    """
    asset_items = [item.host_name for item in assets_watchlist.items if item.host_name]
    asset_items.extend(
        [item.ip_address for item in assets_watchlist.items if item.ip_address]
    )

    return [endpoint for endpoint in endpoints if endpoint.lower() not in asset_items]


def remove_empty_kwargs(**kwargs):
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def html_link(link: str):
    """ "
    Return html link that opens in a new tab
    :param link: {str} Link
    :return: {str} Html clickable link
    """
    return HTML_LINK.format(link=link)


def convert_hours_to_milliseconds(hours: int) -> int:
    """
    Convert hours to milliseconds
    :param hours: {int} Amount of hours to convert to milliseconds
    :return: {int} Equivalent amount in milliseconds
    """
    return hours * 60 * 60 * 1000


def is_notable_user(username: str, notable_users) -> bool:
    """
    Check if username is notable
    :param username: {str} Username to check if it's notable
    :param notable_users: {[datamodels.NotableUser]} List of notable users data models
    :return: {bool} True if username found in notable users list, otherwise False
    """
    return username.lower() in [user.username for user in notable_users]


def is_notable_asset(asset_id: str, notable_assets) -> bool:
    """
    Check if asset is notable
    :param asset_id: {str} Asset's identifier to check if it's notable, can be hostname of ip address of the asset
    :param notable_assets: {[datamodels.NotableAsset]} List of notable assets data models
    :return: {bool} True if asset found in notable assets list, otherwise False
    """
    asset_identifiers = [asset.host_name for asset in notable_assets]
    asset_identifiers.extend([asset.ip_address for asset in notable_assets])

    return asset_id.lower() in asset_identifiers


def convert_timestamp_to_iso_date_format(timestamp: int):
    """
    Convert unix timestamp in milliseconds to ISO-8601 date format. If failed to convert - return parameter timestamp
    :param timestamp: {int} Unix time in milliseconds
    :return: {str} Formatted timestamp as string
    """
    try:
        return convert_unixtime_to_datetime(timestamp).isoformat()
    except Exception:
        pass
    return timestamp


def build_html_table(
    title: str,
    column_headers: Optional[List[str]] = None,
    rows_data: Optional[List[dict]] = None,
):
    """
    Build html table. Table is formatted inside a div.
    :param title: {str} The title of the table
    :param column_headers: {[str]} Headers of the table
    :param rows_data: {[[str]]} List of rows of the table.
    :return: {str} HTML formatted table
    """
    table = BOLD_TITLE.format(text=title)
    table += f'\n<div style="display: flex; height:{len(rows_data) * 50}px;flex-direction: row">'
    table += '\n<table style="border-collapse:separate; width:100%; border-spacing: 0 0.5em;">\n<tbody>\n'

    # Create table's column headers
    table += "<tr>\n"
    for header in column_headers:
        table += f'<th style="text-align: left;">{header}</th>\n'
    table += "</tr>\n"

    # Create table's row data
    for row in rows_data:
        table += "<tr>\n"
        for column_name, row_value in row.items():
            table += f'<td width="{int(100 / len(row.items()))}%" style="overflow:scroll">{row_value}</td>\n'
        table += "</tr>\n"

    table += "</tbody>\n</table>\n</div>\n"
    return table
