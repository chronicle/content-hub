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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import INTEGRATION_NAME, ADVANCED_ARCHIVE_SEARCH_ACTION
from ..core.MimecastManager import MimecastManager
from ..core import UtilsManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADVANCED_ARCHIVE_SEARCH_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    integration_parameters = UtilsManager.get_integration_parameters(siemplify)

    xml_query = extract_action_param(
        siemplify, param_name="XML Query", print_value=True, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = MimecastManager(
            api_root=integration_parameters.api_root,
            app_id=integration_parameters.app_id,
            app_key=integration_parameters.app_key,
            access_key=integration_parameters.access_key,
            secret_key=integration_parameters.secret_key,
            client_id=integration_parameters.client_id,
            client_secret=integration_parameters.client_secret,
            verify_ssl=integration_parameters.verify_ssl,
            siemplify=siemplify,
        )

        archived_emails = manager.execute_query(xml_query=xml_query)

        if archived_emails:
            json_result = [
                archived_email.to_json() for archived_email in archived_emails
            ]
            data_table = [archived_email.to_csv() for archived_email in archived_emails]

            siemplify.result.add_result_json(json_result)

            siemplify.result.add_data_table(
                f"Results", data_table=construct_csv(data_table)
            )
            output_message = f"Successfully found archive emails for the provided criteria in {INTEGRATION_NAME}."

        else:
            output_message = f"No archive emails were found for the provided criteria in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = (
            f"Error executing action {ADVANCED_ARCHIVE_SEARCH_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
