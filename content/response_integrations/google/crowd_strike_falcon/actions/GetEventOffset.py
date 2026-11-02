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
import uuid

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from crowd_strike_falcon.core.constants import (
    INTEGRATION_NAME,
    GET_EVENT_OFFSET_SCRIPT_NAME,
    API_ROOT_DEFAULT,
    SIEMPLIFY_PREFIX_FOR_APP,
    PRODUCT_NAME,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.utils import timestamp_to_iso


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_EVENT_OFFSET_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API Secret"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )
    customer_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    limit = extract_action_param(
        siemplify,
        param_name="Max Events To Process",
        input_type=int,
        print_value=True,
        is_mandatory=True,
    )
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = f"No events were found in {PRODUCT_NAME}."
    app_name = f"{SIEMPLIFY_PREFIX_FOR_APP}{str(uuid.uuid4()).replace('-', '')}"[:30]

    try:
        if limit < 1:
            raise Exception('"Max Events To Process" must be greater than 0.')

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )

        detections = manager.get_stream_detections_with_limit(
            app_name=app_name, offset=None, limit=limit
        )

        if detections:
            last_detection = sorted(detections, key=lambda det: det.offset)[-1]
            output_message = f"Successfully retrieved event offset in {PRODUCT_NAME}."
            siemplify.result.add_result_json(
                {
                    "offset": last_detection.offset,
                    "timestamp": timestamp_to_iso(last_detection.event_creation_time),
                }
            )
            result_value = True

    except Exception as e:
        output_message = (
            f"Error executing action '{GET_EVENT_OFFSET_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
