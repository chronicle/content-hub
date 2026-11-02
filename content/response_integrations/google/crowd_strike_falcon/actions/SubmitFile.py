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
import os.path
import sys
import json
import itertools

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
    SUBMIT_FILE_SCRIPT_NAME,
    API_ROOT_DEFAULT,
    DEFAULT_TIMEOUT,
    ENVIRONMENTS,
    NETWORKS,
    DEFAULT_ACTION_CONTEXT,
)
from crowd_strike_falcon.core.CrowdStrikeCommon import ActionResult, SubmitActionBase
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import (
    CrowdStrikeError,
    CrowdStrikeTimeoutError,
    CrowdStrikeUnsupportedType,
)


class SubmitFileAction(SubmitActionBase):
    def __init__(
        self,
        *args,
        archive_password: str,
        document_password: str,
        comment: str,
        confidential_submission: bool,
        **kwargs,
    ):
        self.confidential_submission = confidential_submission
        self.archive_password = archive_password
        self.document_password = document_password
        self.comment = comment

        super().__init__(*args, **kwargs)

    def prepare_submission_payloads(self, entity_names):
        submission_payloads = {}

        for entity_name in entity_names:
            if entity_name.endswith((".7z", ".zip")):
                submission_payload = self.prepare_archive_submission_payload(
                    entity_name
                )
            else:
                submission_payload = self.prepare_file_submission_payload(entity_name)

            if submission_payload is not None:
                submission_payloads[entity_name] = submission_payload

        return submission_payloads

    def prepare_archive_submission_payload(self, entity_name):
        try:
            archive_hash = self.manager.upload_archive(
                file_path=entity_name,
                comment=self.comment,
                is_confidential=self.confidential_submission,
                password=self.archive_password,
            )
            files = self.manager.get_archive_files(
                archive_hash=archive_hash,
                start_time=self.start_time,
                script_timeout=DEFAULT_TIMEOUT,
            )
            return [
                {
                    "sha256": file.sha256,
                    "environment_id": self.sandbox_environment,
                    "network_settings": self.network_environment,
                    "submit_name": file.name,
                    "enable_tor": True if self.network_environment == "tor" else False,
                }
                for file in files
            ]
        except CrowdStrikeTimeoutError:
            raise CrowdStrikeTimeoutError(self.get_timeout_error_message())
        except CrowdStrikeError as e:
            self.siemplify.LOGGER.error(
                f"Failed to upload archive {entity_name}, error is: {e}"
            )
            self.action_context["failed_extractions"][entity_name] = str(e)

    def prepare_file_submission_payload(self, entity_name):
        try:
            file_hash = self.manager.upload_file(
                file_path=entity_name,
                comment=self.comment,
                is_confidential=self.confidential_submission,
                password=self.document_password,
            )
            file_name = os.path.basename(entity_name)
            return [
                {
                    "sha256": file_hash,
                    "environment_id": self.sandbox_environment,
                    "network_settings": self.network_environment,
                    "submit_name": file_name,
                    "enable_tor": True if self.network_environment == "tor" else False,
                }
            ]
        except CrowdStrikeUnsupportedType as e:
            self.siemplify.LOGGER.error(
                f"Failed to upload file {entity_name}, error is: {e}"
            )
            self.action_context["submissions"][entity_name] = {
                "unsupported_submissions": [entity_name]
            }
        except CrowdStrikeError as e:
            self.siemplify.LOGGER.error(
                f"Failed to upload file {entity_name}, error is: {e}"
            )
            self.action_context["submissions"][entity_name] = {
                "failed_submissions": [entity_name]
            }

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
        unsupported_submissions = list(
            itertools.chain(
                *(
                    submission.get("unsupported_submissions", [])
                    for submission in self.action_context["submissions"].values()
                )
            )
        )

        failed_extractions = self.action_context["failed_extractions"]

        if finished_submissions:
            output_message += (
                "Successfully returned details about the following files using Crowdstrike: "
                f"{', '.join(finished_submissions)}"
            )
            json_result.update(finished_submissions)
            table_results = {
                entity_name: [
                    {
                        "Name": _finished_submission["sandbox"][0]["submit_name"],
                        "Threat Score": _finished_submission["sandbox"][0].get(
                            "threat_score"
                        ),
                        "Verdict": _finished_submission["verdict"],
                        "Tags": ",".join(
                            _finished_submission["sandbox"][0].get(
                                "classification_tags", []
                            )
                        ),
                    }
                    for _finished_submission in _finished_submissions
                ]
                for entity_name, _finished_submissions in finished_submissions.items()
            }
            result_value = True

            if failed_submissions:
                output_message += (
                    "\nAction wasn’t able to return details about the following files using Crowdstrike: "
                    f"{', '.join(failed_submissions)}"
                )
            if unsupported_submissions:
                output_message += (
                    "\nAction wasn’t able to submit the following samples, because file type is not supported: "
                    f"{', '.join(unsupported_submissions)}. "
                    "Please refer to the doc portal for a list of supported files."
                )
        elif unsupported_submissions and not failed_submissions:
            output_message = (
                "None of the samples were submitted, because file type is not supported. "
                "Please refer to the doc portal for a list of supported files."
            )
            result_value = False
        else:
            output_message = "No details about the files were retrieved"
            result_value = False

        for entity_name, error in failed_extractions.items():
            output_message += f"\nFile {entity_name} wasn’t extracted due to the following error: {error}"

        return ActionResult(
            json_result=json_result,
            table_results=table_results,
            result_value=result_value,
            output_message=output_message,
        )

    def remove_duplicates(self, submissions_payloads):
        for entity_name, submission_payloads in submissions_payloads.copy().items():

            submission_data = self.action_context["submissions"].get(
                entity_name, {"pending_submissions": [], "failed_submissions": []}
            )

            for submission_payload in submission_payloads.copy():
                submission_ids = self.manager.filter_submissions(
                    f"sandbox.sha256:'{submission_payload['sha256']}'"
                )
                if not submission_ids:
                    continue

                submission_id = submission_ids[0]
                self.siemplify.LOGGER.info(
                    f"The following entity {submission_payload['submit_name']} was already "
                    f"submitted for analysis."
                )
                submission_data["pending_submissions"].append(submission_id)
                submission_payloads.remove(submission_payload)

            if submission_payloads:
                submissions_payloads[entity_name] = submission_payloads
            else:
                del submissions_payloads[entity_name]

            self.action_context["submissions"][entity_name] = submission_data

        return submissions_payloads

    def get_timeout_error_message(self):
        pending_entities = (
            entity_name
            for entity_name, submission in self.action_context["submissions"].items()
            if submission.get("pending_submissions", [])
        )
        return (
            f"action ran into a timeout during execution. Pending files: "
            f"{', '.join(pending_entities)}. Please increase the timeout in IDE."
        )


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_FILE_SCRIPT_NAME

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
    file_paths = convert_comma_separated_to_list(
        extract_action_param(
            siemplify, param_name="File Paths", print_value=True, is_mandatory=True
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

    archive_password = extract_action_param(
        siemplify,
        param_name="Archive Password",
        print_value=False,
        remove_whitespaces=False,
    )
    document_password = extract_action_param(
        siemplify,
        param_name="Document Password",
        print_value=False,
        remove_whitespaces=False,
    )
    check_duplicate = extract_action_param(
        siemplify, param_name="Check Duplicate", print_value=True, input_type=bool
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)
    confidential_submission = extract_action_param(
        siemplify,
        param_name="Confidential Submission",
        print_value=True,
        input_type=bool,
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
        submit_action = SubmitFileAction(
            siemplify,
            start_time=start_time,
            manager=manager,
            check_duplicate=check_duplicate,
            sandbox_environment=sandbox_environment,
            network_environment=network_environment,
            comment=comment,
            confidential_submission=confidential_submission,
            action_context=action_context,
            archive_password=archive_password,
            document_password=document_password,
        )

        if is_first_run:
            submit_action.start_operation(file_paths)

        is_all_processed = submit_action.query_status()

        if is_all_processed:
            action_result = submit_action.generate_result()
            status = EXECUTION_STATE_COMPLETED

            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(action_result.json_result)
            )
            if action_result.table_results:
                for entity_name, table_result in action_result.table_results.items():
                    siemplify.result.add_data_table(
                        entity_name, construct_csv(table_result)
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
                f"Waiting for results for the following files: "
                f"{','.join(pending_entities)}"
            )
            action_result = ActionResult(
                result_value=json.dumps(action_context), output_message=output_message
            )
            status = EXECUTION_STATE_INPROGRESS

    except Exception as e:
        output_message = (
            f"Error executing action '{SUBMIT_FILE_SCRIPT_NAME}'. Reason: {e}"
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
