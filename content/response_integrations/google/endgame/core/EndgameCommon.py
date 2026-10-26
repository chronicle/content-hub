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

# IMPORTS
from __future__ import annotations
from .EndgameManager import EndgameManager
from TIPCommon import extract_configuration_param
import arrow
import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)

# CONSTS
PROVIDER = "Endgame"


class EndgameCommon:
    def __init__(self, siemplify, logger=None):
        self.logger = logger
        self.siemplify = siemplify

    def get_mapped_environment(self, original_env, map_file):
        """
        Get mapped environment alias from mapping file
        :param original_env: {str} The environment to try to resolve
        :param map_file
        :return: {str} The resolved alias (if no alias - returns the original env)
        """
        try:
            with open(map_file, "r+") as map_file:
                mappings = json.loads(map_file.read())
        except Exception as e:
            self.logger.error(f"Unable to read environment mappings: {str(e)}")
            mappings = {}

        if not isinstance(mappings, dict):
            self.logger.LOGGER.error(
                "Mappings are not in valid format. Environment will not be mapped."
            )
            return original_env

        return mappings.get(original_env, original_env)

    @staticmethod
    def validate_timestamp(last_run_timestamp, offset):
        """
        Validate timestamp in range
        :param last_run_timestamp: {arrow datetime} last run timestamp
        :param offset: {datetime} last run timestamp
        :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
        """
        # Check if first run
        if arrow.get(last_run_timestamp).shift(days=offset) < arrow.utcnow():
            return arrow.utcnow().shift(days=-offset)
        else:
            return last_run_timestamp

    def fetch_investigation_result(self):
        """
        Check investiogation status, if completed retrieve results
        :return:
        """
        self.siemplify.LOGGER.info(
            "================= Async - Param Init ================="
        )

        # INIT INTEGRATION CONFIGURATION:
        api_root = extract_configuration_param(
            self.siemplify,
            provider_name=PROVIDER,
            param_name="API Root",
            is_mandatory=True,
            input_type=str,
        )
        username = extract_configuration_param(
            self.siemplify,
            provider_name=PROVIDER,
            param_name="Username",
            is_mandatory=True,
            input_type=str,
        )
        password = extract_configuration_param(
            self.siemplify,
            provider_name=PROVIDER,
            param_name="Password",
            is_mandatory=True,
            input_type=str,
        )
        verify_ssl = extract_configuration_param(
            self.siemplify,
            provider_name=PROVIDER,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
        )

        self.siemplify.LOGGER.info(
            "----------------- Async - Started -----------------"
        )

        result_value = "false"
        output_message = ""
        results = []
        status = EXECUTION_STATE_COMPLETED

        action_details = json.loads(self.siemplify.parameters["additional_data"])
        investigation_id = action_details["investigation_id"]
        successful_entities = action_details["successful_entities"]
        missing_entities = action_details["missing_entities"]
        failed_entities = action_details["failed_entities"]

        try:
            endgame_manager = EndgameManager(
                api_root, username=username, password=password, use_ssl=verify_ssl
            )

            # Check if investigation completed
            if endgame_manager.is_investigation_complete(investigation_id):
                self.siemplify.LOGGER.info(
                    f"Investigation {investigation_id} has completed. Collecting results."
                )

                # Collect the results of the investigation
                investigation_results = endgame_manager.retrieve_investigation_results(
                    investigation_id
                )

                for task_id, investigation_result in list(
                    investigation_results.items()
                ):
                    for result in investigation_result.get("Results", []):
                        results.append(result)

                result_value = "true"
                status = EXECUTION_STATE_COMPLETED
                self.siemplify.result.add_result_json(results)

                if results:
                    output_message = f"Retrieved results from the following investigation in Endgame: {investigation_id}\n\n"
                else:
                    output_message = "There are no results for your investigation\n\n"

                output_message += "Successfully completed hunt on the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in successful_entities])
                )

                if missing_entities:
                    output_message += "\n\nThe following entities didn't match an any endpoint and were skipped:\n   {}".format(
                        "\n   ".join([entity for entity in missing_entities])
                    )

                if failed_entities:
                    output_message += "\n\nError occurred while initiating hunt on the following entities:\n   {}".format(
                        "\n   ".join([entity for entity in failed_entities])
                    )

            else:
                self.siemplify.LOGGER.info(
                    f"Investigation {investigation_id} has not completed yet. Waiting"
                )
                output_message = (
                    f"Investigation {investigation_id} has not completed yet. Waiting"
                )
                result_value = self.siemplify.parameters["additional_data"]
                status = EXECUTION_STATE_INPROGRESS

        except Exception as e:
            self.siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
            self.siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            result_value = "false"
            output_message = f"Action didn't complete due to error: {e}"

        finally:
            try:
                endgame_manager.logout()
            except Exception as e:
                self.siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
                self.siemplify.LOGGER.exception(e)

        self.siemplify.LOGGER.info(
            "----------------- Async - Finished -----------------"
        )
        self.siemplify.LOGGER.info(f"Status: {status}:")
        self.siemplify.LOGGER.info(f"Result Value: {result_value}")
        self.siemplify.LOGGER.info(f"Output Message: {output_message}")
        return output_message, result_value, status
