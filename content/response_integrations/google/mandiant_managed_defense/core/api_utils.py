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

import collections
import urllib.parse

import requests

from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param
from . import constants
from . import datamodels
from . import AuthenticationManager as auth_manager
from . import MandiantMDManager as api_manager
from .exceptions import MandiantMDException


IntegrationParams = collections.namedtuple(
    "IntegrationParams", ["auth_params", "api_params"]
)


def get_integration_params(soar_action: SiemplifyAction) -> IntegrationParams:
    """Get Mandiant MD IntegrationParams object for auth params and api params

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object

    Returns:
        IntegrationParams: Named tuple IntegrationParams
    """
    api_root = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        soar_action,
        param_name="Client ID",
        provider_name=constants.PROVIDER_NAME,
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        soar_action,
        param_name="Client Secret",
        provider_name=constants.PROVIDER_NAME,
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    auth_params = auth_manager.SessionAuthenticationParameters(
        api_root=api_root,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
    )
    api_params = api_manager.ApiParameters(api_root=api_root)
    integration_params = IntegrationParams(
        auth_params=auth_params, api_params=api_params
    )

    return integration_params


def validate_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        MandiantMDException: If there is any error in the response
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise MandiantMDException(
            f"{error_msg}: {error} {error.response.content}"
        ) from error


def get_full_url(api_root: str, endpoint_id: str, **kwargs) -> str:
    """Construct the full URL using a URL identifier and optional variables

    Args:
        api_root: {str} api root
        endpoint_id: {str} endpoint identifier
        kwargs: {dict} variables passed for string formatting

    Returns:
        str: constructed full URL
    """
    return urllib.parse.urljoin(
        api_root, constants.ENDPOINTS[endpoint_id].format(**kwargs)
    )


def filter_alerts_by_source(
    source_name: str, alerts: list[datamodels.Alert]
) -> list[datamodels.Alert]:
    """Filter alerts by source name

    Args:
        source_name: {str} name of the source to filter alerts by
        alerts: {List[datamodels.Alert]} List of alerts to filter

    Returns:
        List[datamodels.Alert]: Filtered list of alerts
    """
    return [
        alert
        for alert in alerts
        if alert.source_name.casefold() == source_name.casefold()
    ]


def filter_events_by_type(
    event_types: set[str], events: list[datamodels.Event]
) -> list[datamodels.Event]:
    """Filter events by type

    Args:
        event_types: {set[str]} types to filter events by
        events: {List[datamodels.Event]} List of events to filter

    Returns:
        List[datamodels.Event]: Filtered list of events
    """

    return [event for event in events if event.event_type not in event_types]


def create_statuses_string(statuses: list[str]) -> str:
    """Convert the provided list to filter string.

    Example:
        ['value1', 'value2'] to (investigation_status = "value1")
        AND (investigation_status = "value2")

    Args:
        statuses: {List[str]} List like ['value1', 'value2']

    Returns:
        (investigation_status = "value1") AND (investigation_status = "value2")
    """
    statuses_list = [f"investigation_status = '{status}'" for status in statuses]
    return " AND ".join(statuses_list)


def create_filter_string(
    start_timestamp: str, end_timestamp: str, statuses: list[str] | None = None
) -> str:
    """Create filter string to API requests.

    Example:
        'investigation_status = 'resolved' AND investigation_status = 'open' AND
        modified>='2024-05-16T20:15:07Z' AND modified<='2024-05-17T08:15:07Z''

    Args:
        start_timestamp: {str} Start timestamp to fetch results from
        end_timestamp: {str} End timestamp for fetching results until
        statuses: List{str} List of status to search: [RUNNING, STOPPING...]

    Returns:
        String to filter the results from Mandiant MD
    """

    filters_ = [f"modified>='{start_timestamp}' AND modified<='{end_timestamp}'"]
    if statuses:
        filters_.append(create_statuses_string(statuses))

    return " AND ".join(filters_)
