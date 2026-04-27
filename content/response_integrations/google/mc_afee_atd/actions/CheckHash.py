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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, convert_dict_to_json_result_dict
from ..core.McAfeeATDManager import McAfeeATDManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param
from ..core.constants import INTEGRATION_NAME, CHECK_HASH_SCRIPT_NAME

TABLE_NAME = "Check Results"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CHECK_HASH_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    entities_to_update = []
    results = []
    errors = []
    json_results = {}

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.FILEHASH
    ]

    try:
        atd_manager = McAfeeATDManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        for entity in target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                is_blacklisted = atd_manager.is_hash_blacklist(
                    entity.identifier.lower()
                )
                json_results[entity.identifier] = is_blacklisted

                if is_blacklisted:
                    result_value = True
                results.append(
                    {
                        "File Hash": entity.identifier,
                        "Is Blacklisted": str(is_blacklisted),
                    }
                )
                entity.additional_properties.update(
                    {"ATD_is_blacklist": is_blacklisted}
                )
            except Exception as err:
                error_message = (
                    f'Error checking hash "{entity.identifier}", Error: {err}'
                )
                errors.append(error_message)
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(err)
            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        # Provide logout from McAfee ATD.
        atd_manager.logout()
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        if results:
            siemplify.result.add_data_table(TABLE_NAME, construct_csv(results))
            output_message = "Found results for target entities."
        else:
            output_message = "No results were found for target entities."
        if entities_to_update:
            siemplify.update_entities(entities_to_update)

        if errors:
            output_message = "{0} \n \n Errors: \n {1}".format(
                output_message, " \n ".join(errors)
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {CHECK_HASH_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{CHECK_HASH_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
