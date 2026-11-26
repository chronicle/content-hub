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

from typing import Any

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
)

from ..core.FireEyeHXManager import (
    STOPPED_STATE,
    FireEyeHXManager,
    FireEyeHXManagerError,
    FireEyeHXNotFoundError,
)
from ..core.UtilsManager import (
    is_async_action_global_timeout_approaching,
    parse_bulk_acquisition_id,
)

INTEGRATION_NAME: str = "FireEyeHX"
INTEGRATION_DISPLAY_NAME: str = "FireEye HX"
SCRIPT_NAME: str = "Poll Bulk Acquisition"
NEW_HOST_STATE: str = "NEW"
QUEUED_HOST_STATE: str = "QUEUED"
REFRESH_HOST_STATE: str = "REFRESH"


def _init_manager(siemplify: SiemplifyAction) -> FireEyeHXManager:
    """Initialize and return a FireEyeHXManager instance using action configuration."""
    api_root: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl: bool = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    return FireEyeHXManager(
        api_root=api_root,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )


def _safe_host_count(value: Any) -> int:
    """Convert a running_state host count into a non-negative integer."""
    if value is None or isinstance(value, bool):
        return 0
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _count_running_state_hosts(acquisition_data: dict[str, Any]) -> tuple[int, int, int, int]:
    """Extract total, NEW, QUEUED, and REFRESH host counts from stats.running_state.

    Args:
        acquisition_data: Bulk acquisition payload returned by FireEye HX.

    Returns:
        Tuple of (total_hosts, new_hosts, queued_hosts, refresh_hosts).
    """
    stats = acquisition_data.get("stats")
    running_state = stats.get("running_state") if isinstance(stats, dict) else None
    if not isinstance(running_state, dict) or not running_state:
        return 0, 0, 0, 0

    total_hosts = 0
    new_hosts = 0
    queued_hosts = 0
    refresh_hosts = 0
    for host_state, raw_count in running_state.items():
        count = _safe_host_count(raw_count)
        total_hosts += count
        normalized_state = str(host_state).upper()
        if normalized_state == NEW_HOST_STATE:
            new_hosts += count
        elif normalized_state == QUEUED_HOST_STATE:
            queued_hosts += count
        elif normalized_state == REFRESH_HOST_STATE:
            refresh_hosts += count

    return total_hosts, new_hosts, queued_hosts, refresh_hosts


def _evaluate_poll_result(
    bulk_id: int,
    acquisition_data: dict[str, Any],
    is_timeout_approaching: bool = False,
) -> tuple[str, str, int, bool]:
    """Evaluate bulk acquisition data and determine the polling outcome.

    Args:
        bulk_id: Numeric bulk acquisition ID.
        acquisition_data: Bulk acquisition payload returned by FireEye HX.
        is_timeout_approaching: Whether the async action deadline is approaching.

    Returns:
        Tuple of (output_message, result_value, execution_status, should_add_json).

    Raises:
        FireEyeHXManagerError: If the API returned an unexpected empty payload.
    """
    if not acquisition_data:
        msg = (
            f'Empty response returned when fetching bulk acquisition with ID "{bulk_id}" '
            f"from {INTEGRATION_DISPLAY_NAME}."
        )
        raise FireEyeHXManagerError(msg)

    state = str(acquisition_data.get("state") or "UNKNOWN")
    if state.upper() == STOPPED_STATE:
        return (
            f'Successfully polled bulk acquisition with ID "{bulk_id}" in {INTEGRATION_DISPLAY_NAME}. '
            f"State: {state}. "
            f"Stopping polling because the bulk acquisition is in {STOPPED_STATE} state.",
            "true",
            EXECUTION_STATE_COMPLETED,
            True,
        )

    total_hosts, new_hosts, queued_hosts, refresh_hosts = _count_running_state_hosts(acquisition_data)
    if total_hosts == 0:
        return (
            f'Successfully polled bulk acquisition with ID "{bulk_id}" in {INTEGRATION_DISPLAY_NAME}. '
            f"State: {state}. "
            "Stopping polling because no target hosts were reported for the bulk acquisition.",
            "true",
            EXECUTION_STATE_COMPLETED,
            True,
        )

    pending_hosts = new_hosts + queued_hosts + refresh_hosts
    if pending_hosts == 0:
        return (
            f'Successfully polled bulk acquisition with ID "{bulk_id}" in {INTEGRATION_DISPLAY_NAME}. '
            f"State: {state}. "
            "Stopping polling because no hosts remain in NEW, QUEUED, or REFRESH state.",
            "true",
            EXECUTION_STATE_COMPLETED,
            True,
        )

    if is_timeout_approaching:
        return (
            f'Error executing action "{SCRIPT_NAME}". Reason: action ran into a timeout during execution. '
            f"Pending bulk acquisition: {bulk_id} ({pending_hosts} pending hosts out of {total_hosts}). "
            "Please increase the timeout in IDE and try again.",
            "false",
            EXECUTION_STATE_FAILED,
            False,
        )

    return (
        f"Waiting for results for the following bulk acquisition: {bulk_id}. "
        f"State: {state}. "
        f"Pending hosts: {pending_hosts} "
        f"(NEW: {new_hosts}, QUEUED: {queued_hosts}, REFRESH: {refresh_hosts}) out of {total_hosts}.",
        "false",
        EXECUTION_STATE_INPROGRESS,
        False,
    )


@output_handler
def main() -> None:
    """Asynchronously poll the status of a bulk acquisition job from FireEye HX."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    output_message = ""
    manager: FireEyeHXManager | None = None

    try:
        bulk_id: str = extract_action_param(
            siemplify,
            param_name="Bulk Acquisition ID",
            is_mandatory=True,
            input_type=str,
        )
        clean_bulk_id: int = parse_bulk_acquisition_id(bulk_id)
        manager = _init_manager(siemplify)

        try:
            acquisition_data = manager.get_bulk_acquisition(clean_bulk_id)
        except FireEyeHXNotFoundError as not_found_err:
            output_message = (
                f'Error executing action "{SCRIPT_NAME}". Reason: '
                f'Bulk acquisition with ID "{clean_bulk_id}" was not found in {INTEGRATION_DISPLAY_NAME}.'
            )
            siemplify.LOGGER.exception(not_found_err)
            status = EXECUTION_STATE_FAILED
            result_value = "false"
        else:
            timeout_approaching = is_async_action_global_timeout_approaching(siemplify, unix_now())
            if timeout_approaching:
                siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit if still pending.")
            output_message, result_value, status, should_add_json = _evaluate_poll_result(
                clean_bulk_id,
                acquisition_data,
                is_timeout_approaching=timeout_approaching,
            )
            if should_add_json:
                siemplify.result.add_result_json(acquisition_data)

    except Exception as err:
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {err}'
        siemplify.LOGGER.exception(err)
        status = EXECUTION_STATE_FAILED
        result_value = "false"

    finally:
        if manager:
            try:
                manager.logout()
            except Exception as logout_err:
                siemplify.LOGGER.warn(f"Failed to log out: {logout_err}")

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
