############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

import io
import json
import os
import sys

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    output_handler,
    unix_now,
)
from TIPCommon.exceptions import InvalidArgumentError
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.soar_ops import get_file
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    DEFAULT_ACTION_CONTEXT,
    DETONATE_FILE_SCRIPT_NAME,
    FILE_SOURCE_BUCKET,
    FILE_SOURCE_FILESYSTEM,
    PROVIDER_NAME,
    SANDBOX_API_URLS,
)
from ..core.datamodels import ActionResult
from ..core.RecordedFutureCommon import RecordedFutureSandboxCommon


class SubmitFileAction(RecordedFutureSandboxCommon):
    """Class with methods specific to uploading Files to Recorded Future Sandbox."""

    def generate_result(self):
        """Formats Sandbox Sample results."""
        json_result = {}
        table_results = []
        output_message = ""

        finished_submissions = {
            entity_name: submission["finished_submissions"]
            for entity_name, submission in self.action_context["submissions"].items()
            if submission.get("finished_submissions", [])
        }

        if finished_submissions:
            output_message += (
                "Successfully returned details about the following files: "
                f"{', '.join(finished_submissions)}"
            )
            json_result.update(finished_submissions)
            result_value = True
        else:
            output_message = "No details about the file were retrieved"
            result_value = False
        self.add_insights()
        return ActionResult(
            json_result=json_result,
            table_results=table_results,
            result_value=result_value,
            output_message=output_message,
        )

    def _add_insight(self, data, entity_name):
        """Adds insight for detonation."""
        self.siemplify.create_case_insight(
            PROVIDER_NAME,
            "Analyzed by Reported Future sandbox",
            self.detonation_html(data),
            entity_name,
            1,
            0,
        )

    def get_timeout_error_message(self):
        """Constructs error message for Action timeout."""
        pending_samples = (
            entity_name
            for entity_name, submission in self.action_context["submissions"].items()
            if submission.get("pending_submissions", [])
        )
        return (
            f"action ran into a timeout during execution. Pending files: "
            f"{', '.join(pending_samples)}. Please increase the timeout in IDE."
        )

    def submit_file(self, file_path: str, file_source: str):
        """Submits File to Recorded Future Sandbox."""
        self.check_timeout()
        filename = os.path.basename(file_path)
        submission_data = self.action_context["submissions"].get(
            filename,
            {"pending_submissions": [], "failed_submissions": []},
        )
        try:
            if file_source == FILE_SOURCE_FILESYSTEM:
                stream = open(file_path, "rb")  # noqa: SIM115
            elif file_source == FILE_SOURCE_BUCKET:
                stream = io.BytesIO(get_file(self.siemplify, identifier=file_path))
            else:
                raise InvalidArgumentError("Invalid File Source system inputted")
        except (InvalidArgumentError, FileNotFoundError) as e:
            self.siemplify.LOGGER.error(
                f"Failed to find or open {file_path}, error is: {e}",
            )
            submission_data["failed_submissions"].append(filename)
            return
        try:
            hatching_response = self.submit_sample_file(filename=filename, file=stream)
            submission_data["pending_submissions"].append(hatching_response["id"])
        except Exception as e:  # noqa: BLE001
            self.siemplify.LOGGER.error(f"Failed to submit {filename}, error is: {e}")
            submission_data["failed_submissions"].append(filename)
        self.action_context["submissions"][filename] = submission_data
        stream.close()

    def start_operation(self, file_path: str, file_source: str):
        """Method called to initiate Sandbox File submission."""
        self.check_timeout()
        self.submit_file(file_path=file_path, file_source=file_source)
        self.siemplify.LOGGER.info(f"Action context - {self.action_context}")
        # Return is the process finished for all pending submissions
        return self.is_all_reported()


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = DETONATE_FILE_SCRIPT_NAME
    start_time = unix_now()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    sandbox_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="SandboxApiUrl",
    )
    sandbox_api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="SandboxApiKey",
    )
    file_path = extract_action_param(
        siemplify,
        param_name="File Path",
        is_mandatory=True,
    )
    file_source = extract_action_param(
        siemplify=siemplify,
        param_name="File Source",
        default_value="GCP Bucket",
        is_mandatory=True,
        print_value=True,
    )
    profile = extract_action_param(siemplify, param_name="Profile", is_mandatory=False)
    password = extract_action_param(
        siemplify,
        param_name="Password",
        is_mandatory=False,
    )

    try:
        assert sandbox_url in SANDBOX_API_URLS
    except AssertionError:
        siemplify.LOGGER.error(
            f"Invalid Sandbox URL. Value must be one of: {SANDBOX_API_URLS}",
        )
        siemplify.end("Invalid Sandbox URL", False)

    action_context = json.loads(
        extract_action_param(
            siemplify,
            param_name="additional_data",
            default_value=DEFAULT_ACTION_CONTEXT,
        ),
    )
    submit_action = SubmitFileAction(
        siemplify,
        sandbox_url,
        sandbox_api_key,
        action_context,
        start_time,
        profile=profile,
        password=password,
    )

    try:
        if is_first_run:
            submit_action.start_operation(file_path=file_path, file_source=file_source)

        is_all_reported = submit_action.query_status()

        if is_all_reported:
            action_result = submit_action.generate_result()
            status = EXECUTION_STATE_COMPLETED
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(action_result.json_result),
            )
            if action_result.table_results:
                siemplify.result.add_data_table(
                    "Results",
                    construct_csv(action_result.table_results),
                )
        else:
            pending_files = (
                file_name
                for file_name, submission in submit_action.action_context["submissions"].items()
                if submission.get("pending_submissions", [])
            )
            output_message = (
                f"Waiting for results for the following files: {','.join(pending_files)}"
            )
            action_result = ActionResult(
                result_value=json.dumps(action_context),
                output_message=output_message,
            )
            status = EXECUTION_STATE_INPROGRESS
    except Exception as e:
        siemplify.LOGGER.error(f"Error performing action {DETONATE_FILE_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        action_result = ActionResult(result_value=False, output_message=output_message)

    siemplify.LOGGER.info("\n----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {action_result.result_value}"
        f"\n  output_message: {action_result.output_message}",
    )
    siemplify.end(action_result.output_message, action_result.result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
