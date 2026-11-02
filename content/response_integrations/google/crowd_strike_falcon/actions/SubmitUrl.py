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
import sys
import json
import itertools
from urllib.parse import urlparse

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import convert_comma_separated_to_list, construct_csv

from crowd_strike_falcon.core.constants import (
    INTEGRATION_NAME,
    SUBMIT_URL_SCRIPT_NAME,
    API_ROOT_DEFAULT,
    ENVIRONMENTS,
    NETWORKS,
    DEFAULT_ACTION_CONTEXT,
)
from crowd_strike_falcon.core.CrowdStrikeCommon import ActionResult, SubmitActionBase
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager


class SubmitUrlAction(SubmitActionBase):
    def prepare_submission_payloads(self, entity_names):
        submission_payloads = {}

        for entity_name in entity_names:
            submission_payloads[entity_name] = [
                {
                    "url": entity_name,
                    "environment_id": self.sandbox_environment,
                    "network_settings": self.network_environment,
                    "submit_name": entity_name,
                    "enable_tor": True if self.network_environment == "tor" else False,
                }
            ]

        return submission_payloads

    def remove_duplicates(self, submission_payloads):
        for entity_name in submission_payloads.copy():
            filter_string = f"sandbox.url:'{urlparse(entity_name).netloc}'"
            self.siemplify.LOGGER.info(
                f"Searching existing entities for {entity_name} "
                f"with filter string {filter_string} ..."
            )
            submission_ids = self.manager.filter_submissions(filter_string)
            if not submission_ids:
                continue

            existing_submission = next(
                filter(
                    lambda s: s.get_entity_name() == entity_name,
                    self.manager.get_submissions(submission_ids),
                ),
                None,
            )
            if not existing_submission:
                continue

            self.siemplify.LOGGER.info(
                f"The following entity {entity_name} was already "
                f"submitted for analysis."
            )
            self.action_context["submissions"][entity_name] = {
                "pending_submissions": [existing_submission.id]
            }
            del submission_payloads[entity_name]

        return submission_payloads

    def generate_result(self) -> ActionResult:
        json_result = {}
        table_results = []
        output_message = ""

        finished_submissions = {
            entity_name: submission["finished_submissions"]
            for entity_name, submission in self.action_context["submissions"].items()
            if submission.get("finished_submissions", [])
        }
        failed_submissions = list(
            itertools.chain(
                *(
                    submission.get("failed_submissions", [])
                    for submission in self.action_context["submissions"].values()
                )
            )
        )

        if finished_submissions:
            output_message += (
                "Successfully returned details about the following urls using Crowdstrike: "
                f"{', '.join(finished_submissions)}"
            )
            json_result.update(finished_submissions)
            table_results.extend(
                [
                    {
                        "Name": entity_name,
                        "Threat Score": finished_submission[0]["sandbox"][0].get(
                            "threat_score"
                        ),
                        "Verdict": finished_submission[0]["verdict"],
                        "Tags": ",".join(
                            finished_submission[0]["sandbox"][0].get(
                                "classification_tags", []
                            )
                        ),
                    }
                    for entity_name, finished_submission in finished_submissions.items()
                ]
            )
            result_value = True

            if failed_submissions:
                output_message += (
                    "\nAction wasn’t able to return details about the following urls using Crowdstrike: "
                    f"{', '.join(failed_submissions)}"
                )
        else:
            output_message = "No details about the urls were retrieved"
            result_value = False

        return ActionResult(
            json_result=json_result,
            table_results=table_results,
            result_value=result_value,
            output_message=output_message,
        )

    def get_timeout_error_message(self):
        pending_entities = (
            entity_name
            for entity_name, submission in self.action_context["submissions"].items()
            if submission.get("pending_submissions", [])
        )
        return (
            f"action ran into a timeout during execution. Pending urls: "
            f"{', '.join(pending_entities)}. Please increase the timeout in IDE."
        )


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_URL_SCRIPT_NAME

    start_time = unix_now()

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration parameters
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

    # Action parameters
    urls = convert_comma_separated_to_list(
        extract_action_param(
            siemplify, param_name="URLs", print_value=True, is_mandatory=True
        )
    )
    sandbox_environment_dirty = extract_action_param(
        siemplify, param_name="Sandbox Environment", print_value=True
    )
    sandbox_environment = ENVIRONMENTS.get(sandbox_environment_dirty)

    network_environment_dirty = extract_action_param(
        siemplify, param_name="Network Environment", print_value=True
    )
    network_environment = NETWORKS.get(network_environment_dirty)

    check_duplicate = extract_action_param(
        siemplify, param_name="Check Duplicate", print_value=True, input_type=bool
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    action_context = json.loads(
        extract_action_param(
            siemplify,
            param_name="additional_data",
            default_value=DEFAULT_ACTION_CONTEXT,
        )
    )

    try:
        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            logger=siemplify.LOGGER,
            customer_id=customer_id,
        )
        submit_action = SubmitUrlAction(
            siemplify,
            start_time=start_time,
            manager=manager,
            check_duplicate=check_duplicate,
            sandbox_environment=sandbox_environment,
            network_environment=network_environment,
            action_context=action_context,
        )

        if is_first_run:
            submit_action.start_operation(urls)

        is_all_processed = submit_action.query_status()

        if is_all_processed:
            action_result = submit_action.generate_result()
            status = EXECUTION_STATE_COMPLETED

            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(action_result.json_result)
            )
            if action_result.table_results:
                siemplify.result.add_data_table(
                    "Results", construct_csv(action_result.table_results)
                )
        else:
            pending_entities = (
                entity_name
                for entity_name, submission in submit_action.action_context[
                    "submissions"
                ].items()
                if submission.get("pending_submissions", [])
            )
            output_message = (
                f"Waiting for results for the following urls: "
                f"{','.join(pending_entities)}"
            )
            action_result = ActionResult(
                result_value=json.dumps(action_context), output_message=output_message
            )
            status = EXECUTION_STATE_INPROGRESS

    except Exception as e:
        output_message = (
            f"Error executing action '{SUBMIT_URL_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

        action_result = ActionResult(result_value=False, output_message=output_message)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {action_result.result_value}"
        f"\n  output_message: {action_result.output_message}"
    )
    siemplify.end(action_result.output_message, action_result.result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
