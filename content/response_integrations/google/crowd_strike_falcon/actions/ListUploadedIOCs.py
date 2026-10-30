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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv, string_to_multi_value

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    IOC_INDICATORS_MAX_PAGE_SIZE,
    LIST_UPLOADED_IOCS_SCRIPT_NAME,
    INTEGRATION_NAME,
    MAX_IOC_LIMIT,
    PRODUCT_NAME,
    LIST_UPLOADED_IOCS,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager


IOC_TYPE_DEFAULT_VALUES = string_to_multi_value("ipv4,ipv6,md5,sha256,domain")


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_UPLOADED_IOCS_SCRIPT_NAME

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

    ioc_type_filter = string_to_multi_value(
        extract_action_param(siemplify, param_name="IOC Type Filter", print_value=True)
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Value Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Value Filter String", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max IOCs To Return",
        input_type=int,
        print_value=True,
        default_value=MAX_IOC_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = (
        f"No custom IOCs were found for the provided criteria in {PRODUCT_NAME}."
    )
    result_value = False

    try:
        if not all(item.lower() in IOC_TYPE_DEFAULT_VALUES for item in ioc_type_filter):
            raise Exception(
                '"IOC Type Filter" contains an invalid value. Please check the spelling. '
                "Possible values: ipv4, ipv6, md5, sha256, domain."
            )

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )

        iocs = manager.get_uploaded_iocs(
            ioc_types=ioc_type_filter,
            ioc_value=filter_value,
            filter_strategy=filter_logic,
            limit=limit,
            page_size=IOC_INDICATORS_MAX_PAGE_SIZE,
        )

        if iocs:
            siemplify.result.add_data_table(
                LIST_UPLOADED_IOCS, construct_csv([ioc.to_csv() for ioc in iocs])
            )
            siemplify.result.add_result_json([ioc.to_json() for ioc in iocs])
            output_message = f"Successfully found custom IOCs for the provided criteria in {PRODUCT_NAME}."
            result_value = len(iocs)

    except Exception as e:
        output_message = (
            f"Error executing action '{LIST_UPLOADED_IOCS_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  iocs_count: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
