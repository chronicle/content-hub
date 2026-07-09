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

"""Ping action for FireEye ETP integration."""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param

from ..core.fire_eye_etp_constants import PROVIDER_NAME
from ..core.fire_eye_etp_manager import FireEyeETPConfig, FireEyeETPManager


@output_handler
def main() -> None:
    """Execute the Ping action.

    Raises:
        ValueError: If neither client ID/secret nor API key is provided.

    """
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{PROVIDER_NAME} - Ping"

    # Extract integration parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client ID",
        is_mandatory=False,
        print_value=False,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        is_mandatory=False,
        print_value=False,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Key",
        is_mandatory=False,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("================= Main - Started =================")

    # Validate parameters before try block to avoid raise-within-try issues
    if not (api_key or (client_id and client_secret)):
        msg = "Either Client ID and Client Secret, or API Key (legacy) must be provided."
        raise ValueError(msg)

    output_message: str
    result: bool
    status: int

    config = FireEyeETPConfig(
        api_root=api_root,
        client_id=client_id,
        client_secret=client_secret,
        api_key=api_key,
        verify_ssl=verify_ssl,
    )
    try:
        manager = FireEyeETPManager(
            config=config,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.test_connectivity()
    except Exception as e:
        output_message = f"Failed to connect to the FireEye ETP server! Error is {e}"
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.exception(output_message)
    else:
        output_message = "Successfully connected to the FireEye ETP server with the provided connection parameters!"
        result = True
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("================= Main - Finished =================")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
