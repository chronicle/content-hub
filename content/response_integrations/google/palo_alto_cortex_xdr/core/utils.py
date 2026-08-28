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

import re
from typing import Iterable, TYPE_CHECKING

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.extraction import extract_script_param
from TIPCommon.types import ChronicleSOAR
from ..core import constants
from ..core.datamodels import IntegrationParameters


if TYPE_CHECKING:
    from TIPCommon.data_models import AlertCard


def get_integration_parameters(chronicle_soar: ChronicleSOAR) -> IntegrationParameters:
    """Get the parameters object for ProofPoint TAP auth and api manager
    Args:
        chronicle_soar (ChronicleSOAR): SiemplifyAction object.

    Returns:
        IntegrationParameters: IntegrationParameters object.
    """
    if isinstance(chronicle_soar, SiemplifyAction):
        input_dictionary = chronicle_soar.get_configuration(constants.INTEGRATION_NAME)
    elif isinstance(chronicle_soar, (SiemplifyConnectorExecution, SiemplifyJob)):
        input_dictionary = chronicle_soar.parameters
    else:
        raise ValueError("Provided SOAR instance is not supported.")

    api_root = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Api Key",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    api_key_id = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Api Key ID",
        is_mandatory=True,
    )
    verify_ssl = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    integration_params: IntegrationParameters = IntegrationParameters(
        api_root=api_root,
        api_key=api_key,
        api_key_id=api_key_id,
        verify_ssl=verify_ssl,
    )

    return integration_params

def get_incident_id_from_alert(
    chronicle_soar: ChronicleSOAR,
    alert: AlertCard,
) -> str | None:
    """
    Extracts a Palo Alto Cortex XDR incident ID from a single Google SecOps alert.
    It first checks the alert's additional_properties, then falls back to
    checking the case-level context.

    Args:
        chronicle_soar (ChronicleSOAR) : The Chronicle SOAR object used to
            interact with the platform.
        alert (AlertCard): A dictionary representing the Google SecOps alert.

    Returns:
        str | None: The Palo Alto Cortex XDR incident ID if found, otherwise None.
    """
    if alert.ticket_id:
        incident_id = alert.ticket_id
        if "_" in incident_id:
            incident_id = incident_id.split("_", 1)[0]

        if is_valid_alert_id(incident_id):
            return incident_id

    if hasattr(alert, "alert_group_identifier") and alert.alert_group_identifier:
        context_ticket_id = chronicle_soar.get_context_property(
            constants.ENTITY_TYPE,
            alert.alert_group_identifier,
            constants.ALERT_ID_CONTEXT_PROPERTY,
        )
        if is_valid_alert_id(context_ticket_id):
            return context_ticket_id

    return None


def strip_html_tags(text: str) -> str:
    """Removes HTML tags from a string."""
    if not isinstance(text, str):
        return text
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)


def is_valid_alert_id(incident_id: str) -> bool:
    """
    Check if an alert ID is a valid Palo Alto Cortex XDR Incident identifier.
    """
    if not incident_id or not incident_id.isdigit():
        return False

    if int(incident_id) == 0:
        return False

    return True

def merge_and_sort(
    list_1: Iterable[tuple[int, int]],
    list_2: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    """
    Merges two iterables of (id, timestamp) tuples, with list_2 taking
    precedence in case of duplicate ids, and sorts the result by timestamp.
    Args:
        list_1 (Iterable[tuple[int, int]]): First iterable.
        list_2 (Iterable[tuple[int, int]]): Second iterable, which takes
            precedence over list_1 for duplicate ids.
    Returns:
        list[tuple[int, int]]: Merged and sorted list of tuples.
    """
    merged: dict[int, int] = {}
    for _id, ts in list_1:
        merged[_id] = ts

    for _id, ts in list_2:
        merged[_id] = ts

    return sorted(merged.items(), key=lambda x: x[1])
